"""
Meta WhatsApp Cloud API webhook.

GET  /webhook  → verification handshake
POST /webhook  → incoming messages
"""
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from db.supabase_client import get_supabase
from services import session as session_svc
from services import leave, qa, payslip, onboarding
from services.gemini import classify_intent
from services.whatsapp import send_message, parse_webhook
from services.gating import whatsapp_gate
from config import get_settings

router = APIRouter()

GREETING_MSG = (
    "👋 Hi {name}! I'm your HR assistant.\n\n"
    "I can help you with:\n"
    "• *Leave requests* — type 'leave'\n"
    "• *HR policy questions* — just ask\n"
    "• *Payslip info* — type 'payslip'\n\n"
    "What do you need?"
)


@router.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    s = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == s.whatsapp_verify_token:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    messages = parse_webhook(body)
    for msg in messages:
        background_tasks.add_task(_handle_message, msg["from"], msg["to"], msg["text"])
    return {"status": "ok"}


async def _handle_message(from_phone: str, to_number_id: str, text: str):
    try:
        await _process_message(from_phone, to_number_id, text)
    except Exception as exc:
        print(f"[webhook] Unhandled error for {from_phone}: {exc}")
        try:
            send_message(from_phone, "Something went wrong on our end. Please try again in a moment.")
        except Exception:
            pass


async def _process_message(from_phone: str, to_number_id: str, text: str):
    text = text.strip()

    tenant = _get_tenant_by_number_id(to_number_id)
    if not tenant:
        send_message(from_phone, "This number is not configured. Contact support.")
        return

    employee = _get_employee(from_phone, tenant["id"])
    if not employee:
        send_message(from_phone,
            "You're not registered in this system.\n"
            "Please ask your HR admin to add you.")
        return

    sess = session_svc.get_session(employee["id"])
    current_flow = sess.get("current_flow")

    if _handle_manager_command(text, employee, from_phone):
        return

    if current_flow == "leave_request":
        if text.lower() == "leave":
            session_svc.update_session(employee["id"], flow="leave_request", step="type", context={})
            sess = {"flow_step": "type", "context": {}}
        leave.handle(employee, sess, text)
        return

    if current_flow == "onboarding":
        onboarding.handle(employee, sess, text)
        return

    _GRATITUDE = {"thanks", "thank you", "ty", "10q", "thx", "👍", "🙏", "ok thanks", "ok thank you", "noted", "noted thanks"}
    if text.lower().strip("!. ") in _GRATITUDE:
        send_message(from_phone, "No wahala! Anything else I can help with?")
        return

    intent = classify_intent(text)

    if intent == "greeting" or text.lower() in ("hi", "hello", "hey", "start"):
        name = employee.get("name") or "there"
        send_message(from_phone, GREETING_MSG.format(name=name))

    elif intent == "leave_request" or text.lower() == "leave":
        session_svc.update_session(employee["id"], flow="leave_request", step="type")
        leave.handle(employee, sess, text)

    elif intent == "hr_qa":
        last = (sess.get("context") or {}).get("last_message")
        qa.handle(employee, text, last_message=last)

    elif intent == "payslip" or text.lower() == "payslip":
        gate_msg = whatsapp_gate(employee["tenant_id"], "payslips")
        if gate_msg:
            send_message(from_phone, gate_msg)
        else:
            payslip.handle(employee, text)

    elif intent == "onboarding" or text.lower() == "onboard":
        gate_msg = whatsapp_gate(employee["tenant_id"], "onboarding")
        if gate_msg:
            send_message(from_phone, gate_msg)
        else:
            onboarding.handle(employee, sess, text)

    elif len(text.split()) >= 3:
        # Long enough to attempt RAG — might be a policy question phrased unusually
        last = (sess.get("context") or {}).get("last_message")
        qa.handle(employee, text, last_message=last)

    else:
        send_message(from_phone, "That's not really my lane 😅 — I handle leave, payslips, and HR policy questions. What can I help with?")


def _get_tenant_by_number_id(phone_number_id: str) -> dict | None:
    sb = get_supabase()
    result = (
        sb.table("tenants")
        .select("*")
        .eq("whatsapp_number", phone_number_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _get_employee(phone: str, tenant_id: str) -> dict | None:
    sb = get_supabase()
    result = (
        sb.table("employees")
        .select("*")
        .eq("phone", phone)
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _handle_manager_command(text: str, employee: dict, phone: str) -> bool:
    parts = text.strip().upper().split()
    if len(parts) != 2 or parts[0] not in ("APPROVE", "REJECT"):
        return False
    if employee.get("role") not in ("manager", "hr_admin"):
        send_message(phone, "You don't have permission to approve leave requests.")
        return True

    action = parts[0].lower()
    ref    = parts[1].lower()
    sb     = get_supabase()

    result  = sb.table("leave_requests").select("*").eq("status", "pending").execute()
    matches = [r for r in (result.data or []) if r["id"].startswith(ref)]

    if not matches:
        send_message(phone, f"No pending request found for '{ref}'.")
        return True

    req        = matches[0]
    new_status = "approved" if action == "approve" else "rejected"
    sb.table("leave_requests").update({
        "status":      new_status,
        "manager_id":  employee["id"],
        "reviewed_at": "now()",
    }).eq("id", req["id"]).execute()

    emp_res = sb.table("employees").select("phone,name,leave_balance").eq("id", req["employee_id"]).limit(1).execute()
    if emp_res.data:
        emp = emp_res.data[0]
        if new_status == "approved":
            new_bal = max(0, emp["leave_balance"] - req["days"])
            sb.table("employees").update({"leave_balance": new_bal}).eq("id", req["employee_id"]).execute()
            send_message(emp["phone"],
                f"✅ Your {req['leave_type'].title()} leave "
                f"({req['start_date']} → {req['end_date']}, {req['days']} days) has been *APPROVED*.")
        else:
            send_message(emp["phone"],
                f"❌ Your {req['leave_type'].title()} leave "
                f"({req['start_date']} → {req['end_date']}) has been *REJECTED*.")

    send_message(phone, f"Done. Leave request {new_status}.")
    return True