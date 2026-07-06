"""
Leave request flow.
Steps: type → start_date → end_date → reason → confirm
"""
from datetime import datetime, date
from db.supabase_client import get_supabase
from services.session import get_session, update_session, update_context, clear_session
from services.whatsapp import send_message

LEAVE_TYPES = {
    "1": "annual",
    "2": "sick",
    "3": "maternity",
    "4": "paternity",
    "5": "unpaid",
}

ESCAPE_WORDS = {"hi", "hello", "hey", "menu", "back", "cancel", "stop", "exit", "restart", "start"}

MAIN_MENU = (
    "No problem! Here's what I can help you with:\n\n"
    "• *Leave requests* — type 'leave'\n"
    "• *HR policy questions* — just ask\n"
    "• *Payslip info* — type 'payslip'\n\n"
    "What do you need?"
)


def handle(employee: dict, session: dict, message: str) -> None:
    step = session.get("flow_step") or "type"
    ctx = session.get("context") or {}
    phone = employee["phone"]
    tid = employee["tenant_id"]

    if step != "type" and message.strip().lower() in ESCAPE_WORDS:
        clear_session(employee["id"])
        send_message(phone, MAIN_MENU, tenant_id=tid)
        return

    if step == "type":
        _ask_type(phone, employee["id"], tid, message)

    elif step == "start_date":
        choice = message.strip()
        if choice not in LEAVE_TYPES:
            # Long message in the middle of the flow — likely a question, not a menu choice
            if len(message.split()) > 6:
                send_message(phone,
                    "Looks like you have a question! Type *cancel* to exit the leave request "
                    "and ask freely, or reply 1–5 to continue.\n\n"
                    "1 - Annual  2 - Sick  3 - Maternity  4 - Paternity  5 - Unpaid",
                    tenant_id=tid
                )
            else:
                send_message(phone, "Please reply with a number 1–5.", tenant_id=tid)
            return
        update_context(employee["id"], "leave_type", LEAVE_TYPES[choice])
        update_session(employee["id"], step="end_date")
        send_message(phone, "What is your start date? (format: DD/MM/YYYY)", tenant_id=tid)

    elif step == "end_date":
        try:
            start = datetime.strptime(message.strip(), "%d/%m/%Y").date()
        except ValueError:
            send_message(phone, "Invalid date. Please use DD/MM/YYYY format.", tenant_id=tid)
            return
        if start < date.today():
            send_message(phone, "Start date can't be in the past. Try again.", tenant_id=tid)
            return
        update_context(employee["id"], "start_date", str(start))
        update_session(employee["id"], step="reason")
        send_message(phone, "What is your end date? (format: DD/MM/YYYY)", tenant_id=tid)

    elif step == "reason":
        try:
            end = datetime.strptime(message.strip(), "%d/%m/%Y").date()
            start = date.fromisoformat(ctx["start_date"])
        except (ValueError, KeyError):
            send_message(phone, "Invalid date. Please use DD/MM/YYYY format.", tenant_id=tid)
            return
        if end < start:
            send_message(phone, "End date must be after start date.", tenant_id=tid)
            return
        days = (end - start).days + 1
        if employee["leave_balance"] < days:
            send_message(
                phone,
                f"You only have {employee['leave_balance']} leave days remaining "
                f"but requested {days} days. Please adjust your end date, or type 'back' to start over.",
                tenant_id=tid
            )
            return
        update_context(employee["id"], "end_date", str(end))
        update_context(employee["id"], "days", days)
        update_session(employee["id"], step="confirm")
        send_message(phone, f"That's {days} day(s). What's the reason? (or type 'skip')", tenant_id=tid)

    elif step == "confirm":
        reason = None if message.strip().lower() == "skip" else message.strip()
        update_context(employee["id"], "reason", reason)
        ctx = get_session(employee["id"])["context"]
        _submit_request(employee, ctx, phone)

    else:
        # Unknown step — restart
        clear_session(employee["id"])
        send_message(phone, "Something went wrong. Let's start over. Type 'leave' to begin.", tenant_id=tid)


_EMPATHY_WORDS = {
    "anxiety", "anxious", "mental health", "stress", "stressed", "burnout",
    "overwhelmed", "not feeling", "tired", "exhausted", "unwell", "sick",
    "struggling", "situation", "ghost work", "ghost",
}


def _ask_type(phone: str, employee_id: str, tenant_id: str, trigger: str = "") -> None:
    trigger_lower = trigger.lower()
    prefix = (
        "I hear you — taking care of yourself matters. 🤝\n\n"
        if any(w in trigger_lower for w in _EMPATHY_WORDS)
        else ""
    )
    update_session(employee_id, flow="leave_request", step="start_date")
    send_message(
        phone,
        f"{prefix}What type of leave?\n\n"
        "1 - Annual\n"
        "2 - Sick\n"
        "3 - Maternity\n"
        "4 - Paternity\n"
        "5 - Unpaid\n\n"
        "Reply with the number.",
        tenant_id=tenant_id
    )


def _submit_request(employee: dict, ctx: dict, phone: str) -> None:
    required = ("leave_type", "start_date", "end_date", "days")
    if not all(k in ctx for k in required):
        clear_session(employee["id"])
        send_message(phone, MAIN_MENU, tenant_id=employee["tenant_id"])
        return

    sb = get_supabase()

    # Insert leave request
    record = {
        "employee_id": employee["id"],
        "tenant_id": employee["tenant_id"],
        "leave_type": ctx["leave_type"],
        "start_date": ctx["start_date"],
        "end_date": ctx["end_date"],
        "days": ctx["days"],
        "reason": ctx.get("reason"),
        "status": "pending",
    }
    result = sb.table("leave_requests").insert(record).execute()

    # Notify manager
    manager = _get_manager(employee["tenant_id"])
    if manager:
        _notify_manager(manager["phone"], employee, ctx, result.data[0]["id"])

    clear_session(employee["id"])
    send_message(
        phone,
        f"✅ Leave request submitted!\n\n"
        f"Type: {ctx['leave_type'].title()}\n"
        f"From: {ctx['start_date']}\n"
        f"To: {ctx['end_date']}\n"
        f"Days: {ctx['days']}\n\n"
        f"Your manager has been notified.",
        tenant_id=employee["tenant_id"]
    )


def _get_manager(tenant_id: str) -> dict | None:
    sb = get_supabase()
    result = (
        sb.table("employees")
        .select("*")
        .eq("tenant_id", tenant_id)
        .in_("role", ["manager", "hr_admin"])
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _notify_manager(manager_phone: str, employee: dict, ctx: dict, request_id: str) -> None:
    send_message(
        manager_phone,
        f"📋 Leave Request\n\n"
        f"From: {employee.get('name') or employee['phone']}\n"
        f"Type: {ctx['leave_type'].title()}\n"
        f"From: {ctx['start_date']} to {ctx['end_date']} ({ctx['days']} days)\n"
        f"Reason: {ctx.get('reason') or 'Not provided'}\n\n"
        f"Reply APPROVE {request_id[:8]} or REJECT {request_id[:8]}",
        tenant_id=employee["tenant_id"]
    )
