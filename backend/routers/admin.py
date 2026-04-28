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
    reviewer_id: str


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

    # Update status
    sb.table("leave_requests").update({
        "status": body.status,
        "manager_id": body.reviewer_id,
        "reviewed_at": "now()",
    }).eq("id", request_id).execute()

    # Deduct balance if approved
    if body.status == "approved":
        emp = sb.table("employees").select("phone,name,leave_balance").eq("id", req["employee_id"]).limit(1).execute().data[0]
        new_balance = max(0, emp["leave_balance"] - req["days"])
        sb.table("employees").update({"leave_balance": new_balance}).eq("id", req["employee_id"]).execute()
        _notify_employee(emp["phone"], req, "approved")
    else:
        emp = sb.table("employees").select("phone").eq("id", req["employee_id"]).limit(1).execute().data[0]
        _notify_employee(emp["phone"], req, "rejected")

    return {"ok": True, "status": body.status}


def _notify_employee(phone: str, req: dict, status: str) -> None:
    emoji = "✅" if status == "approved" else "❌"
    send_message(
        phone,
        f"{emoji} Your {req['leave_type'].title()} leave request "
        f"({req['start_date']} → {req['end_date']}, {req['days']} days) "
        f"has been {status.upper()}."
    )


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
        name  = (emp.get("name") or "").split()[0] or "there"
        gross = slip.get("gross_pay") or 0
        net   = slip.get("net_pay")   or 0
        msg = (
            f"💚 {name}, your {body.month} {body.year} salary don land!\n\n"
            f"Gross: ₦{gross:,.0f}\n"
            f"Net:   ₦{net:,.0f}\n\n"
            f"Any question? Just ask me here 🤝"
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
