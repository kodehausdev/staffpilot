"""
Post-decline ticket flow — after a leave request is rejected, the employee is
asked (via WhatsApp) whether they'd like the decision flagged for HR review.
A "yes" logs the decline reason as a ticket; no further back-and-forth.
"""
from db.supabase_client import get_supabase
from services.whatsapp import send_message
from services.session import clear_session

_YES = {"yes", "y", "yeah", "yep", "sure", "ok", "okay", "please", "yes please"}
_NO  = {"no", "n", "nah", "nope", "no thanks", "not now"}


def handle(employee: dict, sess: dict, text: str) -> None:
    phone     = employee["phone"]
    tenant_id = employee["tenant_id"]
    ctx       = sess.get("context") or {}
    answer    = text.lower().strip("!?. ")

    if answer in _YES:
        sb = get_supabase()
        sb.table("tickets").insert({
            "tenant_id":        tenant_id,
            "employee_id":      employee["id"],
            "leave_request_id": ctx.get("pending_ticket_leave_id"),
            "subject":          ctx.get("pending_ticket_subject") or "Leave decision follow-up",
            "description":      ctx.get("pending_ticket_reason") or "No reason given.",
        }).execute()
        send_message(phone, "Got it — I've flagged this for your HR admin to review.", tenant_id=tenant_id)
        clear_session(employee["id"])
        return

    if answer in _NO:
        send_message(phone, "No problem. Let me know if you need anything else.", tenant_id=tenant_id)
        clear_session(employee["id"])
        return

    send_message(phone, "Just to confirm — would you like me to flag this for HR? Reply yes or no.", tenant_id=tenant_id)
