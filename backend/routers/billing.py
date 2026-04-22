"""
Billing router — Paystack integration.
POST /billing/subscribe   → initiate upgrade
GET  /billing/verify      → post-payment redirect handler
POST /billing/webhook     → Paystack event webhook
GET  /billing/status/{id} → current subscription state
POST /billing/cancel/{id} → cancel subscription
"""
from fastapi import APIRouter, Request, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional
from services import billing
from services.gating import get_plan
from db.supabase_client import get_supabase
from config import get_settings

router = APIRouter(prefix="/billing", tags=["billing"])


# ── Subscribe ─────────────────────────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    tenant_id: str
    email: str
    plan: str
    callback_url: Optional[str] = None


@router.post("/subscribe")
def subscribe(body: SubscribeRequest):
    if body.plan not in ("starter", "growth", "enterprise"):
        raise HTTPException(400, "Invalid plan")
    if body.plan == "enterprise":
        raise HTTPException(400, "Contact sales for enterprise pricing")

    s = get_settings()
    callback = body.callback_url or f"{s.frontend_url}/dashboard/settings?billing=success"

    try:
        result = billing.initialize_subscription(
            tenant_id=body.tenant_id,
            email=body.email,
            plan=body.plan,
            callback_url=callback,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return result


# ── Verify (post-payment redirect) ────────────────────────────────────────────

@router.get("/verify")
def verify(reference: str):
    try:
        data = billing.verify_transaction(reference)
    except Exception as e:
        raise HTTPException(400, f"Verification failed: {e}")

    if data.get("status") != "success":
        raise HTTPException(402, "Payment was not successful")

    # Activate — metadata on the transaction carries tenant_id + plan
    metadata  = data.get("metadata") or {}
    tenant_id = metadata.get("tenant_id")
    plan      = metadata.get("plan")

    if tenant_id and plan:
        billing._activate_subscription(get_supabase(), tenant_id, plan, data)

    return {"status": "activated", "plan": plan}


# ── Webhook ───────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(...),
):
    payload = await request.body()

    if not billing.verify_webhook_signature(payload, x_paystack_signature):
        raise HTTPException(400, "Invalid signature")

    body = await request.json()
    event = body.get("event", "")
    data  = body.get("data", {})

    billing.process_webhook(event, data)
    return {"received": True}


# ── Subscription status ───────────────────────────────────────────────────────

@router.get("/status/{tenant_id}")
def get_status(tenant_id: str):
    sub  = billing.get_subscription(tenant_id)
    plan = get_plan(tenant_id)
    return {
        "plan":         plan,
        "subscription": sub,
    }


# ── Cancel ────────────────────────────────────────────────────────────────────

@router.post("/cancel/{tenant_id}")
def cancel(tenant_id: str):
    ok = billing.cancel_subscription(tenant_id)
    if not ok:
        raise HTTPException(400, "Could not cancel — no active subscription found")
    return {"cancelled": True}
