"""
Leave request flow — upgraded with:
  • Interactive buttons for leave type selection
  • Flexible date parsing (23 Sept / 23-30 Sept / 23/09/2026 / 23 September)
  • Date range detection — "23-30 Sept" skips the end date question
  • Confirm step with interactive buttons (Confirm / Adjust / Cancel)
"""
from __future__ import annotations

import re
from datetime import datetime, date, timedelta
from db.supabase_client import get_supabase
from services.session import get_session, update_session, update_context, clear_session
from services.whatsapp import send_message, send_buttons, send_list

# ─── Constants ────────────────────────────────────────────────────────────────

LEAVE_TYPES = {
    "annual":    "Annual",
    "sick":      "Sick",
    "maternity": "Maternity",
    "paternity": "Paternity",
    "unpaid":    "Unpaid",
}

# Legacy number shortcuts still work
LEAVE_NUMBER_MAP = {
    "1": "annual",
    "2": "sick",
    "3": "maternity",
    "4": "paternity",
    "5": "unpaid",
}

ESCAPE_WORDS = {
    "hi", "hello", "hey", "menu", "back",
    "cancel", "stop", "exit", "restart", "start",
}

MAIN_MENU = (
    "No problem! Here's what I can help you with:\n\n"
    "• *Leave requests* — type 'leave'\n"
    "• *HR policy questions* — just ask\n"
    "• *Payslip info* — type 'payslip'\n\n"
    "What do you need?"
)

_EMPATHY_WORDS = {
    "anxiety", "anxious", "mental health", "stress", "stressed", "burnout",
    "overwhelmed", "not feeling", "tired", "exhausted", "unwell", "sick",
    "struggling", "situation", "ghost work", "ghost",
}

# Month name → number mapping for flexible date parsing
_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


# ─── Date parsing ─────────────────────────────────────────────────────────────

def _parse_date(text: str) -> date | None:
    """
    Parse a single date from natural language. Accepts:
      - 23/09/2026  or  23-09-2026  or  23.09.2026
      - 23 Sept 2026  or  23 September 2026
      - 23 Sept       (assumes current or next occurrence of that month)
      - Sept 23       (month-first variant)
    Returns a date object or None if unrecognised.
    """
    text = text.strip().lower()

    # Try strict numeric formats first: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    # Try "23 sept 2026" or "23 september 2026"
    m = re.match(r"(\d{1,2})\s+([a-z]+)(?:\s+(\d{4}))?", text)
    if m:
        day      = int(m.group(1))
        mon_str  = m.group(2)
        year_str = m.group(3)
        month    = _MONTHS.get(mon_str)
        if month:
            year = int(year_str) if year_str else _infer_year(month, day)
            try:
                return date(year, month, day)
            except ValueError:
                pass

    # Try "sept 23 2026" or "sept 23"
    m = re.match(r"([a-z]+)\s+(\d{1,2})(?:\s+(\d{4}))?", text)
    if m:
        mon_str  = m.group(1)
        day      = int(m.group(2))
        year_str = m.group(3)
        month    = _MONTHS.get(mon_str)
        if month:
            year = int(year_str) if year_str else _infer_year(month, day)
            try:
                return date(year, month, day)
            except ValueError:
                pass

    return None


def _infer_year(month: int, day: int) -> int:
    """If no year given, use current year — or next year if the date has passed."""
    today = date.today()
    year  = today.year
    try:
        candidate = date(year, month, day)
        if candidate < today:
            return year + 1
    except ValueError:
        pass
    return year


def _parse_date_range(text: str) -> tuple[date, date] | None:
    """
    Detect a date range in a single message. Accepts:
      - "23-30 Sept"
      - "23 to 30 September"
      - "23/09 - 30/09/2026"
      - "23 Sept - 30 Sept 2026"
    Returns (start, end) or None if not a range.
    """
    text = text.strip()

    # Pattern: two date-like tokens separated by - or "to"
    separators = [" to ", " - ", "-", "–"]
    for sep in separators:
        parts = text.split(sep, 1)
        if len(parts) == 2:
            left  = parts[0].strip()
            right = parts[1].strip()

            # If right side is missing the month, inherit from left
            # e.g. "23-30 Sept" → left="23", right="30 Sept"
            if re.match(r"^\d{1,2}$", left) and right:
                # left is just a day number — look for month on right
                m = re.match(r"(\d{1,2})\s+([a-z]+)(?:\s+\d{4})?", right.lower())
                if m:
                    left = f"{left} {m.group(2)}"
                    if len(right.split()) > 2:
                        # grab year if present
                        yr = re.search(r"\d{4}", right)
                        if yr:
                            left += f" {yr.group()}"

            start = _parse_date(left)
            end   = _parse_date(right)
            if start and end and end >= start:
                return start, end

    return None


# ─── Main handler ─────────────────────────────────────────────────────────────

def handle(employee: dict, session: dict, message: str) -> None:
    step  = session.get("flow_step") or "type"
    ctx   = session.get("context") or {}
    phone = employee["phone"]
    tid   = employee["tenant_id"]

    if step != "type" and message.strip().lower() in ESCAPE_WORDS:
        clear_session(employee["id"])
        send_message(phone, MAIN_MENU, tenant_id=tid)
        return

    if step == "type":
        _ask_type(phone, employee["id"], tid, message)

    elif step == "start_date":
        _handle_type_choice(employee, ctx, message, phone, tid)

    elif step == "end_date":
        _handle_start_date(employee, ctx, message, phone, tid)

    elif step == "reason":
        _handle_end_date(employee, ctx, message, phone, tid)

    elif step == "confirm":
        _handle_confirm(employee, ctx, message, phone, tid)

    else:
        clear_session(employee["id"])
        send_message(phone, "Something went wrong. Type 'leave' to start over.", tenant_id=tid)


# ─── Step handlers ────────────────────────────────────────────────────────────

def _handle_type_choice(employee, ctx, message, phone, tid):
    """Step: user picks leave type (button id, number, or text)."""
    raw = message.strip().lower()

    # Accept button id directly (e.g. "annual", "sick")
    leave_type = LEAVE_TYPES.get(raw)

    # Accept legacy number shortcuts
    if not leave_type:
        mapped = LEAVE_NUMBER_MAP.get(raw)
        if mapped:
            leave_type = LEAVE_TYPES.get(mapped)
            raw = mapped

    # Accept plain text close matches
    if not leave_type:
        for key in LEAVE_TYPES:
            if key in raw:
                leave_type = LEAVE_TYPES[key]
                raw = key
                break

    if not leave_type:
        if len(message.split()) > 6:
            send_message(
                phone,
                "Looks like you have a question! Type *cancel* to exit and ask freely, "
                "or tap a leave type to continue.",
                tenant_id=tid,
            )
        else:
            _ask_type(phone, employee["id"], tid)
        return

    update_context(employee["id"], "leave_type", raw)
    update_session(employee["id"], step="end_date")

    send_message(
        phone,
        "What are your leave dates?\n\n"
        "You can send a range in one go:\n"
        "• *23-30 Sept*\n"
        "• *23 to 30 September 2026*\n"
        "• *23/09/2026 - 30/09/2026*\n\n"
        "Or just send the start date and I'll ask for the end date next.",
        tenant_id=tid,
    )


def _handle_start_date(employee, ctx, message, phone, tid):
    """Step: user sends start date — or a full date range."""
    text = message.strip()

    # Try to detect a date range first — skip end_date step entirely
    date_range = _parse_date_range(text)
    if date_range:
        start, end = date_range
        if start < date.today():
            send_message(phone, "Start date can't be in the past. Try again.", tenant_id=tid)
            return
        days = (end - start).days + 1
        if employee["leave_balance"] < days:
            send_message(
                phone,
                f"You only have {employee['leave_balance']} leave days remaining "
                f"but that's {days} days. Please adjust your dates.",
                tenant_id=tid,
            )
            return
        update_context(employee["id"], "start_date", str(start))
        update_context(employee["id"], "end_date",   str(end))
        update_context(employee["id"], "days",       days)
        update_session(employee["id"], step="confirm")
        _ask_confirm(phone, employee, ctx | {"start_date": str(start), "end_date": str(end), "days": days}, tid)
        return

    # Single date
    start = _parse_date(text)
    if not start:
        send_message(
            phone,
            "I didn't catch that date. Try formats like:\n"
            "• *23 Sept*\n• *23/09/2026*\n• *23-30 Sept* (for a range)",
            tenant_id=tid,
        )
        return
    if start < date.today():
        send_message(phone, "Start date can't be in the past. Try again.", tenant_id=tid)
        return

    update_context(employee["id"], "start_date", str(start))
    update_session(employee["id"], step="reason")
    send_message(
        phone,
        f"Start date: *{start.strftime('%d %B %Y')}* ✓\n\nWhat's your end date?",
        tenant_id=tid,
    )


def _handle_end_date(employee, ctx, message, phone, tid):
    """Step: user sends end date."""
    text  = message.strip()
    end   = _parse_date(text)

    if not end:
        send_message(
            phone,
            "I didn't catch that date. Try something like *30 Sept* or *30/09/2026*.",
            tenant_id=tid,
        )
        return

    try:
        start = date.fromisoformat(ctx["start_date"])
    except (KeyError, ValueError):
        clear_session(employee["id"])
        send_message(phone, "Something went wrong. Type 'leave' to start over.", tenant_id=tid)
        return

    if end < start:
        send_message(phone, "End date must be after start date. Try again.", tenant_id=tid)
        return

    days = (end - start).days + 1
    if employee["leave_balance"] < days:
        send_message(
            phone,
            f"You only have {employee['leave_balance']} leave days remaining "
            f"but that's {days} days. Please adjust your end date.",
            tenant_id=tid,
        )
        return

    update_context(employee["id"], "end_date", str(end))
    update_context(employee["id"], "days",     days)
    update_session(employee["id"], step="confirm")

    merged_ctx = {**ctx, "end_date": str(end), "days": days}
    _ask_confirm(phone, employee, merged_ctx, tid)


def _ask_confirm(phone, employee, ctx, tid):
    """Show a summary and ask for confirmation with interactive buttons."""
    leave_type = ctx.get("leave_type", "").title()
    start      = ctx.get("start_date", "")
    end        = ctx.get("end_date", "")
    days       = ctx.get("days", 0)

    try:
        start_fmt = date.fromisoformat(start).strftime("%d %B %Y")
        end_fmt   = date.fromisoformat(end).strftime("%d %B %Y")
    except ValueError:
        start_fmt = start
        end_fmt   = end

    send_buttons(
        to_phone=phone,
        body=(
            f"Here's your leave summary:\n\n"
            f"📋 *Type:* {leave_type}\n"
            f"📅 *From:* {start_fmt}\n"
            f"📅 *To:* {end_fmt}\n"
            f"🗓 *Days:* {days}\n\n"
            f"Shall I submit this?"
        ),
        buttons=[
            {"id": "confirm_leave", "title": "✅ Confirm"},
            {"id": "cancel",        "title": "❌ Cancel"},
            {"id": "adjust_leave",  "title": "✏️ Adjust dates"},
        ],
        footer="You have " + str(employee.get("leave_balance", 0)) + " days remaining",
        tenant_id=tid,
    )


def _handle_confirm(employee, ctx, message, phone, tid):
    """Step: user confirms, cancels or adjusts."""
    raw = message.strip().lower()

    if raw in ("confirm_leave", "confirm", "yes", "ok", "okay", "submit", "send"):
        ctx = get_session(employee["id"])["context"]
        _submit_request(employee, ctx, phone)

    elif raw in ("adjust_leave", "adjust", "change", "edit"):
        # Go back to date entry
        update_session(employee["id"], step="end_date")
        send_message(
            phone,
            "No problem — what should the dates be?\n\n"
            "Send a range like *23-30 Sept* or just the start date.",
            tenant_id=tid,
        )

    elif raw in ("cancel", "no", "cancel_leave", "stop"):
        clear_session(employee["id"])
        send_message(phone, "Leave request cancelled. What else can I help with?", tenant_id=tid)

    else:
        # Unexpected input — re-show buttons
        ctx = get_session(employee["id"])["context"]
        send_buttons(
            to_phone=phone,
            body="Tap a button to confirm, cancel or adjust your request.",
            buttons=[
                {"id": "confirm_leave", "title": "✅ Confirm"},
                {"id": "cancel",        "title": "❌ Cancel"},
                {"id": "adjust_leave",  "title": "✏️ Adjust dates"},
            ],
            tenant_id=tid,
        )


# ─── Ask type ────────────────────────────────────────────────────────────────

def _ask_type(phone: str, employee_id: str, tenant_id: str, trigger: str = "") -> None:
    trigger_lower = trigger.lower()
    prefix = (
        "I hear you — taking care of yourself matters. 🤝\n\n"
        if any(w in trigger_lower for w in _EMPATHY_WORDS)
        else ""
    )
    update_session(employee_id, flow="leave_request", step="start_date")

    # Use list for 5 options (more than 3 → list is cleaner than buttons)
    send_list(
        to_phone=phone,
        body=f"{prefix}What type of leave do you need?",
        button_label="Choose leave type",
        sections=[
            {
                "title": "Leave types",
                "rows": [
                    {"id": "annual",    "title": "Annual leave",    "description": "Planned time off"},
                    {"id": "sick",      "title": "Sick leave",      "description": "Illness or medical"},
                    {"id": "maternity", "title": "Maternity leave", "description": "New mother"},
                    {"id": "paternity", "title": "Paternity leave", "description": "New father"},
                    {"id": "unpaid",    "title": "Unpaid leave",    "description": "Unpaid absence"},
                ],
            }
        ],
        footer="Tap to select",
        tenant_id=tenant_id,
    )


# ─── Submit ──────────────────────────────────────────────────────────────────

def _submit_request(employee: dict, ctx: dict, phone: str) -> None:
    required = ("leave_type", "start_date", "end_date", "days")
    if not all(k in ctx for k in required):
        clear_session(employee["id"])
        send_message(phone, MAIN_MENU, tenant_id=employee["tenant_id"])
        return

    sb = get_supabase()
    record = {
        "employee_id": employee["id"],
        "tenant_id":   employee["tenant_id"],
        "leave_type":  ctx["leave_type"],
        "start_date":  ctx["start_date"],
        "end_date":    ctx["end_date"],
        "days":        ctx["days"],
        "reason":      ctx.get("reason"),
        "status":      "pending",
    }
    result = sb.table("leave_requests").insert(record).execute()

    manager = _get_manager(employee["tenant_id"])
    if manager:
        _notify_manager(manager["phone"], employee, ctx, result.data[0]["id"])

    clear_session(employee["id"])

    try:
        start_fmt = date.fromisoformat(ctx["start_date"]).strftime("%d %B %Y")
        end_fmt   = date.fromisoformat(ctx["end_date"]).strftime("%d %B %Y")
    except ValueError:
        start_fmt = ctx["start_date"]
        end_fmt   = ctx["end_date"]

    send_message(
        phone,
        f"✅ Leave request submitted!\n\n"
        f"Type: {ctx['leave_type'].title()}\n"
        f"From: {start_fmt}\n"
        f"To:   {end_fmt}\n"
        f"Days: {ctx['days']}\n\n"
        f"Your manager has been notified.",
        tenant_id=employee["tenant_id"],
    )


def _get_manager(tenant_id: str) -> dict | None:
    sb     = get_supabase()
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
    try:
        start_fmt = date.fromisoformat(ctx["start_date"]).strftime("%d %B %Y")
        end_fmt   = date.fromisoformat(ctx["end_date"]).strftime("%d %B %Y")
    except ValueError:
        start_fmt = ctx["start_date"]
        end_fmt   = ctx["end_date"]

    send_message(
        manager_phone,
        f"📋 Leave Request\n\n"
        f"From: {employee.get('name') or employee['phone']}\n"
        f"Type: {ctx['leave_type'].title()}\n"
        f"From: {start_fmt} to {end_fmt} ({ctx['days']} days)\n"
        f"Reason: {ctx.get('reason') or 'Not provided'}\n\n"
        f"Reply APPROVE {request_id[:8]} or REJECT {request_id[:8]}",
        tenant_id=employee["tenant_id"],
    )
