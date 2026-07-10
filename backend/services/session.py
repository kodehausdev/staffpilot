"""
Session manager — stores conversation state in Supabase.
Stateless backend: every request reloads from DB.
"""
from db.supabase_client import get_supabase
from typing import Optional


def get_session(employee_id: str) -> dict:
    """Load or create session for an employee."""
    sb = get_supabase()
    result = (
        sb.table("sessions")
        .select("*")
        .eq("employee_id", employee_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    # Create fresh session
    new_session = {
        "employee_id": employee_id,
        "current_flow": None,
        "flow_step": None,
        "context": {},
    }
    sb.table("sessions").insert(new_session).execute()
    return new_session


def update_session(
    employee_id: str,
    flow: Optional[str] = None,
    step: Optional[str] = None,
    context: Optional[dict] = None,
) -> None:
    sb = get_supabase()
    payload = {"updated_at": "now()"}
    if flow is not None:
        payload["current_flow"] = flow
    if step is not None:
        payload["flow_step"] = step
    if context is not None:
        payload["context"] = context
    sb.table("sessions").update(payload).eq("employee_id", employee_id).execute()



# Context keys that outlive any single flow — guardrail counters and
# gate-followup state, not flow-scoped draft data. clear_session() must not
# wipe these, or e.g. answering a payslip question resets the salary-wall
# escalation counter back to zero.
_CROSS_CUTTING_KEYS = ("salary_attempts", "last_gate", "insult_attempts")


def clear_session(employee_id: str) -> None:
    """Reset flow state after a flow completes — preserves cross-cutting
    guardrail context (see _CROSS_CUTTING_KEYS) which isn't flow-scoped."""
    sb = get_supabase()
    old_ctx = get_session(employee_id).get("context") or {}
    preserved = {k: v for k, v in old_ctx.items() if k in _CROSS_CUTTING_KEYS}
    sb.table("sessions").update({
        "current_flow": None,
        "flow_step":    None,
        "context":      preserved,
        "updated_at":   "now()",
    }).eq("employee_id", employee_id).execute()


def update_context(employee_id: str, key: str, value) -> dict:
    """Merge a single key into the session context."""
    session = get_session(employee_id)
    ctx = session.get("context") or {}
    ctx[key] = value
    update_session(employee_id, context=ctx)
    return ctx
