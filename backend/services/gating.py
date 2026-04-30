"""
Plan feature gating.
Call check_feature() in any route or service that needs plan enforcement.
"""
from fastapi import HTTPException
from db.supabase_client import get_supabase

PLAN_FEATURES = {
    "starter": {
        "max_employees": 30,
        "max_hr_docs":   3,
        "payslips":      False,
        "onboarding":    False,
        "broadcast":     False,
        "hr_qa":         True,
        "leave":         True,
    },
    "growth": {
        "max_employees": 150,
        "max_hr_docs":   10,
        "payslips":      True,
        "onboarding":    True,
        "broadcast":     False,
        "hr_qa":         True,
        "leave":         True,
    },
    "enterprise": {
        "max_employees": -1,   # unlimited
        "max_hr_docs":   -1,   # unlimited
        "payslips":      True,
        "onboarding":    True,
        "broadcast":     True,
        "hr_qa":         True,
        "leave":         True,
    },
}

UPGRADE_MSGS = {
    "payslips":   "Payslip queries require the Growth plan (₦150,000/mo). Ask your admin to upgrade.",
    "onboarding": "Onboarding flow requires the Growth plan. Ask your admin to upgrade.",
    "broadcast":  "Broadcast messaging requires the Enterprise plan. Contact us to upgrade.",
}


def get_plan(tenant_id: str) -> str:
    """Fetch current plan from DB."""
    sb = get_supabase()
    result = sb.table("tenants").select("plan").eq("id", tenant_id).limit(1).execute()
    return result.data[0]["plan"] if result.data else "starter"


def can_use(tenant_id: str, feature: str) -> bool:
    plan = get_plan(tenant_id)
    return PLAN_FEATURES.get(plan, {}).get(feature, False)


def check_feature(tenant_id: str, feature: str) -> None:
    """
    Raise HTTPException if tenant's plan doesn't include the feature.
    Use in API routes: check_feature(tenant_id, "payslips")
    """
    if not can_use(tenant_id, feature):
        plan = get_plan(tenant_id)
        msg  = UPGRADE_MSGS.get(feature, f"Feature '{feature}' not available on {plan} plan.")
        raise HTTPException(status_code=402, detail=msg)


def check_employee_limit(tenant_id: str) -> None:
    """Raise if tenant has hit their employee cap."""
    plan  = get_plan(tenant_id)
    limit = PLAN_FEATURES.get(plan, {}).get("max_employees", 30)
    if limit == -1:
        return

    sb    = get_supabase()
    count = sb.table("employees").select("id", count="exact").eq("tenant_id", tenant_id).eq("is_active", True).execute()
    if (count.count or 0) >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"You've reached your {plan} plan limit of {limit} employees. Upgrade to add more."
        )


def check_doc_limit(tenant_id: str) -> None:
    """Raise if tenant has hit their HR document cap."""
    plan  = get_plan(tenant_id)
    limit = PLAN_FEATURES.get(plan, {}).get("max_hr_docs", 3)
    if limit == -1:
        return

    sb    = get_supabase()
    count = sb.table("hr_documents").select("id", count="exact").eq("tenant_id", tenant_id).execute()
    if (count.count or 0) >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"Your {plan} plan allows up to {limit} HR documents. Delete an existing document or upgrade your plan."
        )


def whatsapp_gate(tenant_id: str, feature: str) -> str | None:
    """
    For WhatsApp flows — return an upgrade message string instead of raising.
    Returns None if feature is allowed.
    """
    if not can_use(tenant_id, feature):
        return UPGRADE_MSGS.get(feature, f"This feature requires a plan upgrade.")
    return None
