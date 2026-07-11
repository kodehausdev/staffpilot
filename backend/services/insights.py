"""
Insight Layer — live company data queries for the WhatsApp bot.

RAG answers "what does the policy say?"
This answers "what is actually happening right now?"
"""
from datetime import date
from db.supabase_client import get_supabase


def get_currently_on_leave(tenant_id: str) -> list[dict]:
    today = date.today().isoformat()
    sb = get_supabase()
    result = (
        sb.table("leave_requests")
        .select("leave_type, start_date, end_date, employees!employee_id(name, department)")
        .eq("tenant_id", tenant_id)
        .eq("status", "approved")
        .lte("start_date", today)
        .gte("end_date", today)
        .execute()
    )
    return result.data or []


def get_pending_requests(tenant_id: str) -> list[dict]:
    sb = get_supabase()
    result = (
        sb.table("leave_requests")
        .select("id, leave_type, start_date, end_date, days, employees!employee_id(name, department)")
        .eq("tenant_id", tenant_id)
        .eq("status", "pending")
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def get_leave_analytics(tenant_id: str) -> dict[str, int]:
    """Leave days taken per department this calendar year (approved only)."""
    year_start = f"{date.today().year}-01-01"
    sb = get_supabase()
    result = (
        sb.table("leave_requests")
        .select("days, employees!employee_id(department)")
        .eq("tenant_id", tenant_id)
        .eq("status", "approved")
        .gte("start_date", year_start)
        .execute()
    )
    dept_days: dict[str, int] = {}
    for req in (result.data or []):
        emp = req.get("employees") or {}
        dept = emp.get("department") or "Unassigned"
        dept_days[dept] = dept_days.get(dept, 0) + (req.get("days") or 1)
    return dict(sorted(dept_days.items(), key=lambda x: x[1], reverse=True))


def get_own_leave_status(employee_id: str, tenant_id: str) -> dict:
    """Employee's leave balance + 3 most recent requests."""
    sb = get_supabase()
    emp_res = sb.table("employees").select("name, leave_balance, leave_days_total").eq("id", employee_id).limit(1).execute()
    recent_res = (
        sb.table("leave_requests")
        .select("leave_type, start_date, end_date, days, status")
        .eq("employee_id", employee_id)
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(3)
        .execute()
    )
    emp = emp_res.data[0] if emp_res.data else {}
    return {
        "name":    emp.get("name", ""),
        "balance": emp.get("leave_balance", 0),
        "total":   emp.get("leave_days_total", 20),
        "recent":  recent_res.data or [],
    }


def get_known_departments(tenant_id: str) -> list[str]:
    """Distinct department values actually in use for this tenant."""
    sb = get_supabase()
    result = (
        sb.table("employees")
        .select("department")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .execute()
    )
    depts = {r["department"] for r in (result.data or []) if r.get("department")}
    return sorted(depts)


def match_department_in_text(tenant_id: str, text: str) -> str | None:
    """Finds which of the tenant's real departments (if any) is named in text —
    avoids needing free-text NLU for something with a small, known vocabulary."""
    text_lower = text.lower()
    for dept in get_known_departments(tenant_id):
        if dept.lower() in text_lower:
            return dept
    return None


def get_department_roster(tenant_id: str, department: str) -> list[dict]:
    sb = get_supabase()
    result = (
        sb.table("employees")
        .select("name, phone, role")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .ilike("department", department)
        .order("name")
        .execute()
    )
    return result.data or []


def get_last_leave_approval(employee_id: str, tenant_id: str) -> dict | None:
    """Returns the most recent approved/rejected request with approver name."""
    sb = get_supabase()
    result = (
        sb.table("leave_requests")
        .select("leave_type, start_date, end_date, status, reviewed_at, employees!manager_id(name)")
        .eq("employee_id", employee_id)
        .eq("tenant_id", tenant_id)
        .in_("status", ["approved", "rejected"])
        .order("reviewed_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# ── Response formatters ──────────────────────────────────────────────────────

def fmt_currently_on_leave(records: list[dict]) -> str:
    if not records:
        return "No one is currently on leave today. 👍"
    lines = ["*Currently on leave:*"]
    for r in records:
        emp  = r.get("employees") or {}
        name = emp.get("name", "Unknown")
        dept = emp.get("department", "")
        tag  = f" ({dept})" if dept else ""
        lines.append(f"• {name}{tag} — {r['leave_type'].title()} ({r['start_date']} → {r['end_date']})")
    return "\n".join(lines)


def fmt_pending_requests(records: list[dict]) -> str:
    if not records:
        return "No pending leave requests right now. ✅"
    lines = [f"*📋 {len(records)} pending leave request{'s' if len(records) != 1 else ''}:*"]
    for i, r in enumerate(records, 1):
        emp  = r.get("employees") or {}
        name = emp.get("name", "Unknown")
        ref  = r["id"][:6]
        lines.append(
            f"{i}. {name} — {r['leave_type'].title()} "
            f"({r['start_date']} → {r['end_date']}, {r.get('days', '?')} days) [ref: {ref}]"
        )
    lines.append("\nReply *APPROVE <ref>* or *REJECT <ref>* to action a request.")
    return "\n".join(lines)


def fmt_leave_analytics(dept_days: dict[str, int]) -> str:
    if not dept_days:
        return "No approved leave data yet this year."
    lines = [f"*Leave usage this year ({date.today().year}):*"]
    for i, (dept, days) in enumerate(dept_days.items(), 1):
        lines.append(f"{i}. {dept} — {days} day{'s' if days != 1 else ''}")
    return "\n".join(lines)


def fmt_own_leave_status(data: dict) -> str:
    name    = data.get("name", "")
    balance = data.get("balance", 0)
    total   = data.get("total", 0)
    recent  = data.get("recent", [])
    lines   = [f"Hi {name}! 👋 Here's your leave summary:"]
    lines.append(f"*Balance:* {balance} of {total} day{'s' if total != 1 else ''} remaining\n")
    if recent:
        lines.append("*Recent requests:*")
        status_icon = {"approved": "✅", "rejected": "❌", "pending": "⏳"}
        for r in recent:
            icon = status_icon.get(r["status"], "•")
            lines.append(
                f"{icon} {r['leave_type'].title()} ({r['start_date']} → {r['end_date']}, "
                f"{r.get('days', '?')} days) — {r['status'].title()}"
            )
    else:
        lines.append("No leave requests on record yet.")
    return "\n".join(lines)


def fmt_department_roster(records: list[dict], department: str) -> str:
    if not records:
        return f"No active employees found in {department}."
    lines = [f"*👥 {department} ({len(records)}):*"]
    for r in records:
        name = r.get("name") or r["phone"]
        role = (r.get("role") or "staff").replace("_", " ").title()
        lines.append(f"• {name} — {role}")
    return "\n".join(lines)


def fmt_last_approval(record: dict | None) -> str:
    if not record:
        return "You haven't had any leave approved or rejected yet."
    mgr   = (record.get("employees") or {}).get("name", "your manager")
    verb  = "approved" if record["status"] == "approved" else "rejected"
    date_ = (record.get("reviewed_at") or "")[:10]
    return (
        f"Your last leave request ({record['leave_type'].title()}, "
        f"{record['start_date']} → {record['end_date']}) was *{verb}* "
        f"by *{mgr}*{f' on {date_}' if date_ else ''}."
    )
