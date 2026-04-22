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

STEPS = ["type", "start_date", "end_date", "reason", "confirm"]


def handle(employee: dict, session: dict, message: str) -> None:
    step = session.get("flow_step") or "type"
    ctx = session.get("context") or {}
    phone = employee["phone"]

    if step == "type":
        _ask_type(phone, employee["id"])

    elif step == "start_date":
        choice = message.strip()
        if choice not in LEAVE_TYPES:
            send_message(phone, "Please reply with a number 1–5.")
            return
        update_context(employee["id"], "leave_type", LEAVE_TYPES[choice])
        update_session(employee["id"], step="start_date")
        send_message(phone, "What is your start date? (format: DD/MM/YYYY)")

    elif step == "end_date":
        try:
            start = datetime.strptime(message.strip(), "%d/%m/%Y").date()
        except ValueError:
            send_message(phone, "Invalid date. Please use DD/MM/YYYY format.")
            return
        if start < date.today():
            send_message(phone, "Start date can't be in the past. Try again.")
            return
        update_context(employee["id"], "start_date", str(start))
        update_session(employee["id"], step="end_date")
        send_message(phone, "What is your end date? (format: DD/MM/YYYY)")

    elif step == "reason":
        try:
            end = datetime.strptime(message.strip(), "%d/%m/%Y").date()
            start = date.fromisoformat(ctx["start_date"])
        except (ValueError, KeyError):
            send_message(phone, "Invalid date. Please use DD/MM/YYYY format.")
            return
        if end < start:
            send_message(phone, "End date must be after start date.")
            return
        days = (end - start).days + 1
        if employee["leave_balance"] < days:
            send_message(
                phone,
                f"You only have {employee['leave_balance']} leave days remaining "
                f"but requested {days} days. Please adjust your dates."
            )
            return
        update_context(employee["id"], "end_date", str(end))
        update_context(employee["id"], "days", days)
        update_session(employee["id"], step="reason")
        send_message(phone, f"That's {days} day(s). What's the reason? (or type 'skip')")

    elif step == "confirm":
        reason = None if message.strip().lower() == "skip" else message.strip()
        update_context(employee["id"], "reason", reason)
        ctx = get_session(employee["id"])["context"]
        _submit_request(employee, ctx, phone)

    else:
        # Unknown step — restart
        clear_session(employee["id"])
        send_message(phone, "Something went wrong. Let's start over. Type 'leave' to begin.")


def _ask_type(phone: str, employee_id: str) -> None:
    update_session(employee_id, flow="leave_request", step="start_date")
    send_message(
        phone,
        "What type of leave?\n\n"
        "1 - Annual\n"
        "2 - Sick\n"
        "3 - Maternity\n"
        "4 - Paternity\n"
        "5 - Unpaid\n\n"
        "Reply with the number."
    )


def _submit_request(employee: dict, ctx: dict, phone: str) -> None:
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
        f"Your manager has been notified."
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
        f"Reply APPROVE {request_id[:8]} or REJECT {request_id[:8]}"
    )
