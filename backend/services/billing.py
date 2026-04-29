"""
Paystack billing service.
All Paystack API calls go through here so the router stays thin.
"""
import hmac
import hashlib
import httpx
from datetime import datetime, timezone, timedelta

from config import get_settings
from db.supabase_client import get_supabase

PAYSTACK_BASE = "https://api.paystack.co"

PLAN_AMOUNTS = {
    "starter": 5_000_000,   # ₦50,000 in kobo
    "growth":  15_000_000,  # ₦150,000 in kobo
}


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_settings().paystack_secret_key}",
        "Content-Type":  "application/json",
    }


# ── Initialise transaction ────────────────────────────────────────────────────

def initialize_subscription(tenant_id: str, email: str, plan: str, callback_url: str) -> dict:
    amount = PLAN_AMOUNTS.get(plan)
    if not amount:
        raise ValueError(f"No amount configured for plan '{plan}'")

    res  = httpx.post(f"{PAYSTACK_BASE}/transaction/initialize", headers=_headers(), json={
        "email":        email,
        "amount":       amount,
        "currency":     "NGN",
        "callback_url": callback_url,
        "channels":     ["card", "bank", "ussd", "bank_transfer"],
        "metadata":     {"tenant_id": tenant_id, "plan": plan},
    })
    data = res.json()
    if not data.get("status"):
        raise ValueError(data.get("message", "Paystack initialisation failed"))

    return {
        "authorization_url": data["data"]["authorization_url"],
        "reference":         data["data"]["reference"],
    }


# ── Verify transaction (post-payment redirect) ────────────────────────────────

def verify_transaction(reference: str) -> dict:
    res  = httpx.get(f"{PAYSTACK_BASE}/transaction/verify/{reference}", headers=_headers())
    data = res.json()
    if not data.get("status"):
        raise ValueError(data.get("message", "Verification failed"))
    return data["data"]


# ── Webhook signature check ───────────────────────────────────────────────────

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    secret = get_settings().paystack_webhook_secret
    if not secret:
        return True  # dev mode — skip signature check
    expected = hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Process incoming webhook event ───────────────────────────────────────────

def process_webhook(event: str, data: dict) -> None:
    sb       = get_supabase()
    metadata = data.get("metadata") or {}
    tenant_id = (
        metadata.get("tenant_id")
        or (data.get("customer") or {}).get("metadata", {}).get("tenant_id")
    )

    if tenant_id:
        sb.table("billing_events").insert({
            "tenant_id":  tenant_id,
            "event_type": event,
            "payload":    data,
        }).execute()

    if event == "charge.success":
        plan = metadata.get("plan")
        if tenant_id and plan:
            _activate_subscription(sb, tenant_id, plan, data)

    elif event in ("subscription.disable", "subscription.not_renew"):
        if tenant_id:
            _set_status(sb, tenant_id, "cancelled")
            sb.table("tenants").update({"plan": "starter"}).eq("id", tenant_id).execute()

    elif event == "invoice.payment_failed":
        if tenant_id:
            _set_status(sb, tenant_id, "past_due")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _activate_subscription(sb, tenant_id: str, plan: str, data: dict) -> None:
    now      = datetime.now(timezone.utc)
    customer = data.get("customer") or {}

    sb.table("subscriptions").upsert({
        "tenant_id":            tenant_id,
        "paystack_customer_id": str(customer.get("id", "")),
        "paystack_sub_code":    data.get("subscription_code"),
        "plan":                 plan,
        "status":               "active",
        "current_period_start": now.isoformat(),
        "current_period_end":   (now + timedelta(days=30)).isoformat(),
        "cancel_at_period_end": False,
        "updated_at":           now.isoformat(),
    }, on_conflict="tenant_id").execute()

    sb.table("tenants").update({"plan": plan}).eq("id", tenant_id).execute()


def _set_status(sb, tenant_id: str, status: str) -> None:
    sb.table("subscriptions").update({
        "status":     status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("tenant_id", tenant_id).execute()


# ── Public query helpers ──────────────────────────────────────────────────────

def get_subscription(tenant_id: str) -> dict | None:
    result = get_supabase().table("subscriptions").select("*").eq("tenant_id", tenant_id).limit(1).execute()
    return result.data[0] if result.data else None


def cancel_subscription(tenant_id: str) -> bool:
    sub = get_subscription(tenant_id)
    if not sub:
        return False

    if sub.get("paystack_sub_code"):
        httpx.post(f"{PAYSTACK_BASE}/subscription/disable", headers=_headers(), json={
            "code":  sub["paystack_sub_code"],
            "token": sub.get("email_token", ""),
        })

    _set_status(get_supabase(), tenant_id, "cancelled")
    get_supabase().table("tenants").update({"plan": "starter"}).eq("id", tenant_id).execute()
    return True
