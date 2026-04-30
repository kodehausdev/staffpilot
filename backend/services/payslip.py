"""
Payslip query flow.
Fetches latest payslip or a specific month.
"""
from db.supabase_client import get_supabase
from services.whatsapp import send_message
from services.session import clear_session
from services.encryption import decrypt_amount, decrypt_dict


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
        if month:
            send_message(phone, f"Abeg, I no see any payslip for {month} on your account. "
                                f"If you think something's off, reach your HR admin to sort it.")
        else:
            send_message(phone, "I no see any payslip on your account yet 😭 "
                                "If salary should don enter, abeg ping HR admin — they'll check it fast.")
        clear_session(employee["id"])
        return

    slip       = result.data[0]
    gross_pay  = decrypt_amount(slip.get("gross_pay"))
    net_pay    = decrypt_amount(slip.get("net_pay"))
    deductions = decrypt_dict(slip.get("deductions"))

    response = (
        f"Payslip — {slip['month']}\n\n"
        f"Gross Pay: ₦{gross_pay:,.2f}\n"
    )

    if deductions:
        for key, val in deductions.items():
            response += f"{key.title()}: -₦{val:,.2f}\n"

    response += f"\nNet Pay: ₦{net_pay:,.2f}"

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
