"""
Meta WhatsApp Cloud API webhook.

GET  /webhook  → verification handshake
POST /webhook  → incoming messages
"""
import re
import random
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from db.supabase_client import get_supabase
from services import session as session_svc
from services import leave, qa, payslip, onboarding, insights
from services.gemini import classify_intent
from services.whatsapp import send_message, parse_webhook
from services.gating import whatsapp_gate
from config import get_settings

router = APIRouter()

GREETING_MSG = (
    "Hi {name} 👋 I'm CordHR — your company HR assistant.\n\n"
    "I can help with:\n"
    "• *Leave requests* — type 'leave'\n"
    "• *HR policy questions* — just ask\n"
    "• *Your payslip* — type 'payslip'\n\n"
    "What do you need?"
)

# Salary & compensation — hardcoded wall, never delegated to RAG or DB
_SALARY_PATTERNS = (
    "all salaries", "all salary", "list salaries", "list salary",
    "employee salary", "payroll list", "highest paid", "top paid",
    "who earns", "earns most", "earns the most", "total payroll",
    "payroll cost", "average salary", "salary data", "sample salary",
    "salary of ", "rank salary", "compare salary",
    "list all employee", "show all employee", "top 3 paid", "top 5 paid",
    "what instructions", "your instructions", "your developer",
    "admin override", "override=", "override list", "/admin",  # command injection variants
)

# Prompt injection / jailbreak attempts
_INJECTION_PATTERNS = (
    "ignore all previous", "ignore previous instruction",
    "new rule:", "you are now", "pretend you are",
    "system error", "transparency mode", "debug mode",
    "salarybot", "new instruction:", "update your system",
    "i'm updating your", "i am updating your",
)

# Salary refusals — rotated so repeated blocks don't sound like a broken record
_SALARY_REFUSALS = [
    "Salary data is confidential and not available here. I can help with your own payslip — just type 'payslip'.",
    "Compensation details are confidential. For your own payslip, type 'payslip'.",
    "That's not something I can share. Salary information is restricted.",
    "Salary details aren't available here. You can access your own payslip by typing 'payslip'.",
]


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

    # Universal flow escape — works inside any active flow
    _CANCEL = {"cancel", "stop", "exit", "quit", "back", "abort", "end", "nevermind", "never mind", "stop it", "stop this"}
    if current_flow and text.lower().strip("!?. ") in _CANCEL:
        session_svc.update_session(employee["id"], flow=None, step=None, context={})
        send_message(from_phone, "Stopped. What else can I help you with?")
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

    _GRATITUDE = {
        "thanks", "thank you", "ty", "10q", "thx", "👍", "🙏",
        "ok thanks", "ok thank you", "noted", "noted thanks",
        "ok", "okay", "k", "fine", "aight", "alright", "cool", "got it",
    }
    if text.lower().strip("!?. ") in _GRATITUDE:
        send_message(from_phone, "Got it. Anything else I can help with?")
        return

    # Prompt injection — before salary check so these never reach AI
    if any(p in text.lower() for p in _INJECTION_PATTERNS):
        send_message(from_phone, "I'm CordHR — I don't respond to instruction overrides. What can I help you with?")
        return

    # Salary & compensation — hardcoded wall with session-based escalation
    if any(p in text.lower() for p in _SALARY_PATTERNS):
        _ctx = sess.get("context") or {}
        attempts = _ctx.get("salary_attempts", 0) + 1
        session_svc.update_session(employee["id"], context={**_ctx, "salary_attempts": attempts})
        if attempts >= 4:
            send_message(from_phone, "This topic has been flagged. Contact your HR admin directly for payroll queries.")
        elif attempts >= 3:
            send_message(from_phone, "Salary data is restricted regardless of how the request is framed. Contact your HR admin directly.")
        else:
            send_message(from_phone, random.choice(_SALARY_REFUSALS))
        return

    # Social engineering — authority or identity claims don't change behaviour
    _AUTHORITY_CLAIMS = (
        "this is your developer", "i am your developer", "i am the developer",
        "this is the ceo", "i am the ceo", "i am ceo", "this is ceo",
        "developer mode", "admin mode", "i created you", "i built you",
        "this is kodehaus", "i am kodehaus",
    )
    if any(p in text.lower() for p in _AUTHORITY_CLAIMS):
        send_message(from_phone, "I'm here to help with HR questions. What do you need?")
        return

    # Own profile data — answer directly from employee record, don't go to AI
    _DEPT_PHRASES = (
        "my department", "my dept", "what department", "what dept",
        "which department am i", "which dept am i", "what team am i", "which team am i",
        "whats my dept", "what's my dept", "whats my department",
    )
    if any(p in text.lower() for p in _DEPT_PHRASES):
        dept = employee.get("department")
        role = employee.get("role", "staff").replace("_", " ").title()
        if dept:
            send_message(from_phone, f"You're in *{dept}* — role: {role}.")
        else:
            send_message(from_phone, "Your department isn't set in the system yet. Ask your HR admin to update your profile.")
        return

    # Chat privacy — hardcoded, not a policy question
    _PRIVACY_PHRASES = (
        "is this chat", "this chat save", "will you report", "you go report",
        "go you tell", "will hr know", "is this private", "is this confidential",
        "you dey record", "you go record", "snitch", "will hr tell",
    )
    if any(p in text.lower() for p in _PRIVACY_PHRASES):
        send_message(from_phone,
            "Your chats here are private — I don't share your questions with HR or anyone else. "
            "Ask freely. 🤝")
        return

    # Plan gate follow-up — explain restriction before AI can confuse it
    _WHY_WORDS = {"why", "wetin", "how come", "explain", "reason", "why not", "why cant", "why can't"}
    _ctx = sess.get("context") or {}
    _last_gate = _ctx.get("last_gate")
    if _last_gate and any(w in text.lower() for w in _WHY_WORDS):
        _GATE_NAMES = {"payslips": "Payslips", "onboarding": "Onboarding"}
        _feature_label = _GATE_NAMES.get(_last_gate, _last_gate.title())
        send_message(
            from_phone,
            f"{_feature_label} isn't included in your company's current plan. "
            f"Your HR admin can enable it with a plan upgrade."
        )
        session_svc.update_session(employee["id"], context={})
        return

    intent = classify_intent(text)

    # Normalise text for greeting detection — handles "ok. start", "hey!" etc.
    _text_words = set(re.sub(r'[^\w\s]', ' ', text.lower()).split())
    _GREETING_WORDS = {"hi", "hello", "hey", "start", "begin", "menu"}
    _is_greeting = intent == "greeting" or (bool(_text_words & _GREETING_WORDS) and len(_text_words) <= 3)

    role = employee.get("role", "staff")  # staff | manager | hr_admin

    # ── GREETING ────────────────────────────────────────────────────────────
    if _is_greeting:
        name = employee.get("name") or "there"
        send_message(from_phone, GREETING_MSG.format(name=name))

    # ── ACTION LAYER — user-specific data ───────────────────────────────────

    elif intent == "leave_request" or text.lower() == "leave":
        session_svc.update_session(employee["id"], flow="leave_request", step="type")
        leave.handle(employee, sess, text)

    elif intent == "leave_status":
        data = insights.get_own_leave_status(employee["id"], employee["tenant_id"])
        send_message(from_phone, insights.fmt_own_leave_status(data))

    elif intent == "last_approval":
        record = insights.get_last_leave_approval(employee["id"], employee["tenant_id"])
        send_message(from_phone, insights.fmt_last_approval(record))

    elif intent == "payslip" or text.lower() == "payslip":
        gate_msg = whatsapp_gate(employee["tenant_id"], "payslips")
        if gate_msg:
            send_message(from_phone, gate_msg)
            session_svc.update_session(employee["id"], context={"last_gate": "payslips"})
        else:
            payslip.handle(employee, text)

    elif intent == "onboarding" or text.lower() == "onboard":
        gate_msg = whatsapp_gate(employee["tenant_id"], "onboarding")
        if gate_msg:
            send_message(from_phone, gate_msg)
            session_svc.update_session(employee["id"], context={"last_gate": "onboarding"})
        else:
            onboarding.handle(employee, sess, text)

    # ── INSIGHT LAYER — company intelligence, role-gated ────────────────────

    elif intent == "who_on_leave":
        if role not in ("manager", "hr_admin"):
            send_message(from_phone,
                "Company leave information is only available to managers and HR admins. "
                "You can check your own leave status by typing 'my leave'.")
        else:
            records = insights.get_currently_on_leave(employee["tenant_id"])
            send_message(from_phone, insights.fmt_currently_on_leave(records))

    elif intent == "pending_approvals":
        if role not in ("manager", "hr_admin"):
            send_message(from_phone,
                "Pending approvals are only visible to managers and HR admins. "
                "Type 'my leave' to check your own requests.")
        else:
            records = insights.get_pending_requests(employee["tenant_id"])
            send_message(from_phone, insights.fmt_pending_requests(records))

    elif intent == "leave_analytics":
        if role != "hr_admin":
            send_message(from_phone,
                "Leave analytics are only available to HR admins.")
        else:
            dept_days = insights.get_leave_analytics(employee["tenant_id"])
            send_message(from_phone, insights.fmt_leave_analytics(dept_days))

    # ── RAG LAYER — policy and handbook questions ────────────────────────────

    elif intent == "hr_qa":
        last = (sess.get("context") or {}).get("last_message")
        qa.handle(employee, text, last_message=last)

    elif len(text.split()) >= 3:
        # Long enough to attempt RAG — policy question phrased unusually
        last = (sess.get("context") or {}).get("last_message")
        qa.handle(employee, text, last_message=last)

    else:
        send_message(from_phone, "I can help with leave, payslips, and HR policy questions. What do you need?")


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