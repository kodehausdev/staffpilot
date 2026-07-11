"""
Admin REST API — used by the Next.js dashboard.
All routes require X-Admin-Key header (simple key auth for now).
Production: replace with Supabase JWT verification.
"""
from fastapi import APIRouter, HTTPException, Header, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import io
import PyPDF2
from db.supabase_client import get_supabase
from config import get_settings
from services.whatsapp import send_message
from services.gemini import embed_document_chunk
from services.gating import check_doc_limit, check_employee_limit
from services import session as session_svc

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin(x_admin_key: str = Header(...)):
    if x_admin_key != get_settings().secret_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")


# ─── Employees ───────────────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    tenant_id: str
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    role: str = "staff"
    department: Optional[str] = None
    leave_balance: int = 20


@router.post("/employees", dependencies=[Depends(verify_admin)])
def create_employee(body: EmployeeCreate):
    sb = get_supabase()
    phone = body.phone if body.phone.startswith("+") else f"+{body.phone}"
    result = sb.table("employees").insert({
        **body.model_dump(),
        "phone": phone,
        "is_active": True,
        # A brand-new employee hasn't taken any leave yet, so their total
        # entitlement equals whatever starting balance was set (supports
        # prorated new hires with a non-default leave_balance).
        "leave_days_total": body.leave_balance,
    }).execute()
    return result.data[0]


@router.get("/employees/{tenant_id}", dependencies=[Depends(verify_admin)])
def list_employees(tenant_id: str):
    sb = get_supabase()
    result = (
        sb.table("employees")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


# ─── Leave ────────────────────────────────────────────────────────────────────

class LeaveDecision(BaseModel):
    status: str   # approved | rejected
    reviewer_id: Optional[str] = None   # employees.id of a WhatsApp manager, if any — dashboard admins aren't employees, so this is usually omitted
    reason: Optional[str] = None        # admin's stated reason for declining (optional)


@router.patch("/leave/{request_id}", dependencies=[Depends(verify_admin)])
def decide_leave(request_id: str, body: LeaveDecision):
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be approved or rejected")

    sb = get_supabase()

    # Fetch request
    req_res = sb.table("leave_requests").select("*").eq("id", request_id).limit(1).execute()
    if not req_res.data:
        raise HTTPException(status_code=404, detail="Request not found")
    req = req_res.data[0]

    if req["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already {req['status']}")

    # Only bites when reviewer identity is actually known (the dashboard
    # doesn't send reviewer_id today — tenant_admins aren't employees) but
    # guards the endpoint itself against self-approval whenever it is.
    if body.reviewer_id and body.reviewer_id == req["employee_id"]:
        raise HTTPException(status_code=403, detail="Cannot approve or reject your own leave request.")

    # Update status
    update_payload = {
        "status": body.status,
        "reviewed_at": "now()",
    }
    if body.reviewer_id:
        update_payload["manager_id"] = body.reviewer_id
    if body.status == "rejected" and body.reason:
        update_payload["decline_reason"] = body.reason

    sb.table("leave_requests").update(update_payload).eq("id", request_id).execute()

    emp = (
        sb.table("employees")
        .select("id,phone,name,leave_balance,tenant_id")
        .eq("id", req["employee_id"])
        .limit(1)
        .execute()
    ).data[0]

    # Deduct balance if approved
    if body.status == "approved":
        new_balance = max(0, emp["leave_balance"] - req["days"])
        sb.table("employees").update({"leave_balance": new_balance}).eq("id", req["employee_id"]).execute()
        _notify_approved(emp, req)
    else:
        _notify_rejected(emp, req, body.reason)

    return {"ok": True, "status": body.status}


def _notify_approved(emp: dict, req: dict) -> None:
    send_message(
        emp["phone"],
        f"✅ Your {req['leave_type'].title()} leave request "
        f"({req['start_date']} → {req['end_date']}, {req['days']} days) "
        f"has been *APPROVED*.",
        tenant_id=emp["tenant_id"],
    )


def _notify_rejected(emp: dict, req: dict, reason: Optional[str]) -> None:
    lines = [
        f"❌ Your {req['leave_type'].title()} leave request "
        f"({req['start_date']} → {req['end_date']}) has been *REJECTED*."
    ]
    if reason:
        lines.append(f"Reason: {reason}")
    lines.append("Want me to flag this for your HR admin to review? Reply yes or no.")
    send_message(emp["phone"], "\n\n".join(lines), tenant_id=emp["tenant_id"])

    # Merge into existing context rather than overwriting — update_session's
    # context= replaces the whole dict, and clobbering it here would silently
    # wipe cross-cutting guardrail counters (salary_attempts, insult_attempts,
    # last_gate) the same way clear_session() used to before that was fixed.
    sess = session_svc.get_session(emp["id"])
    ctx = sess.get("context") or {}
    ctx.update({
        "pending_ticket_leave_id": req["id"],
        "pending_ticket_reason":   reason,
        "pending_ticket_subject":  f"Leave declined — {req['leave_type'].title()} ({req['start_date']} → {req['end_date']})",
    })
    session_svc.update_session(emp["id"], flow="ticket_prompt", step=None, context=ctx)


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats/{tenant_id}", dependencies=[Depends(verify_admin)])
def get_stats(tenant_id: str):
    sb = get_supabase()

    employees = sb.table("employees").select("id", count="exact").eq("tenant_id", tenant_id).eq("is_active", True).execute()
    leave_all  = sb.table("leave_requests").select("status").eq("tenant_id", tenant_id).execute()
    docs       = sb.table("hr_documents").select("id", count="exact").eq("tenant_id", tenant_id).execute()

    statuses = [r["status"] for r in (leave_all.data or [])]
    return {
        "employees":         employees.count or 0,
        "leave_pending":     statuses.count("pending"),
        "leave_approved":    statuses.count("approved"),
        "leave_rejected":    statuses.count("rejected"),
        "hr_docs":           docs.count or 0,
    }


# ─── Tenants ─────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str
    whatsapp_number: str
    plan: str = "starter"


@router.post("/tenants", dependencies=[Depends(verify_admin)])
def create_tenant(body: TenantCreate):
    sb = get_supabase()
    result = sb.table("tenants").insert(body.model_dump()).execute()
    return result.data[0]


@router.get("/tenants", dependencies=[Depends(verify_admin)])
def list_tenants():
    sb = get_supabase()
    result = sb.table("tenants").select("*").order("created_at", desc=True).execute()
    return result.data


# ─── Docs upload + RAG ingestion ─────────────────────────────────────────────

@router.post("/docs/upload", dependencies=[Depends(verify_admin)])
async def upload_doc(
    file:      UploadFile = File(...),
    title:     str        = Form(...),
    tenant_id: str        = Form(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    check_doc_limit(tenant_id)

    content = await file.read()
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        full_text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        ).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {e}")

    if not full_text:
        raise HTTPException(status_code=422, detail="PDF has no extractable text")

    # Chunk: ~800 chars with 100-char overlap
    chunk_size, overlap = 800, 100
    chunks: list[str] = []
    start = 0
    while start < len(full_text):
        end = start + chunk_size
        chunks.append(full_text[start:end].strip())
        start += chunk_size - overlap
    chunks = [c for c in chunks if len(c) > 50]  # drop tiny trailing fragments

    sb = get_supabase()

    # Insert hr_document record
    doc_res = sb.table("hr_documents").insert({
        "tenant_id": tenant_id,
        "title":     title,
        "file_path": None,
    }).execute()
    doc_id = doc_res.data[0]["id"]

    # Embed and store each chunk
    for i, chunk in enumerate(chunks):
        embedding = embed_document_chunk(chunk)
        sb.table("doc_chunks").insert({
            "tenant_id":   tenant_id,
            "document_id": doc_id,
            "content":     chunk,
            "embedding":   embedding,
            "chunk_index": i,
        }).execute()

    return {"ok": True, "doc_id": doc_id, "chunks": len(chunks)}


@router.delete("/docs/{doc_id}", dependencies=[Depends(verify_admin)])
def delete_doc(doc_id: str):
    sb = get_supabase()
    # doc_chunks cascade-deletes via FK
    sb.table("hr_documents").delete().eq("id", doc_id).execute()
    return {"ok": True}


# ─── Payslip broadcast ───────────────────────────────────────────────────────

class PayslipBroadcast(BaseModel):
    tenant_id: str
    month: str   # "April"
    year: int


@router.post("/broadcast/payslips", dependencies=[Depends(verify_admin)])
def broadcast_payslips(body: PayslipBroadcast):
    sb = get_supabase()

    slips = (
        sb.table("payslips")
        .select("*, employees(name, phone)")
        .eq("tenant_id", body.tenant_id)
        .eq("month", body.month)
        .eq("year", body.year)
        .execute()
    ).data or []

    sent, failed = 0, 0
    for slip in slips:
        emp = slip.get("employees") or {}
        phone = emp.get("phone")
        if not phone:
            failed += 1
            continue
        name = (emp.get("name") or "").split()[0] or "there"
        msg  = (
            f"💚 {name}, your {body.month} {body.year} payslip is ready!\n\n"
            f"Reply *payslip* to see your breakdown privately. 💰"
        )
        try:
            send_message(phone, msg)
            sent += 1
        except Exception:
            failed += 1

    return {"sent": sent, "failed": failed, "total": len(slips)}


# ─── Broadcast message ────────────────────────────────────────────────────────

class BroadcastMsg(BaseModel):
    tenant_id: str
    message: str
    department: Optional[str] = None   # None = all staff


@router.post("/broadcast", dependencies=[Depends(verify_admin)])
def broadcast(body: BroadcastMsg):
    sb = get_supabase()
    q = sb.table("employees").select("phone").eq("tenant_id", body.tenant_id).eq("is_active", True)
    if body.department:
        q = q.eq("department", body.department)
    employees = q.execute().data or []

    sent = 0
    for emp in employees:
        try:
            send_message(emp["phone"], body.message)
            sent += 1
        except Exception:
            pass

    return {"sent": sent, "total": len(employees)}
