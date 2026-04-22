"""
Payslip query flow.
Fetches latest payslip or a specific month.
"""
from db.supabase_client import get_supabase
from services.whatsapp import send_message
from services.session import clear_session


def handle(employee: dict, message: str) -> None:
    phone = employee["phone"]
    sb = get_supabase()

    # Check if message contains a specific month
    month = _extract_month(message)

    query = (
        sb.table("payslips")
        .select("*")
        .eq("employee_id", employee["id"])
    )

    if month:
        query = query.ilike("month", f"%{month}%")
    else:
        query = query.order("created_at", desc=True)

    result = query.limit(1).execute()

    if not result.data:
        msg = f"No payslip found" + (f" for {month}" if month else "") + "."
        send_message(phone, msg + " Contact HR if you think this is an error.")
        clear_session(employee["id"])
        return

    slip = result.data[0]
    deductions = slip.get("deductions") or {}

    response = (
        f"Payslip — {slip['month']}\n\n"
        f"Gross Pay: ₦{slip['gross_pay']:,.2f}\n"
    )

    if deductions:
        for key, val in deductions.items():
            response += f"{key.title()}: -₦{val:,.2f}\n"

    response += f"\nNet Pay: ₦{slip['net_pay']:,.2f}"

    if slip.get("file_url"):
        response += f"\n\nDownload: {slip['file_url']}"

    send_message(phone, response)
    clear_session(employee["id"])


MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]


def _extract_month(text: str) -> str | None:
    text_lower = text.lower()
    for month in MONTHS:
        if month in text_lower:
            return month.title()
    return None
