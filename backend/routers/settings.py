"""
Tenant settings — WhatsApp onboarding via Meta embedded signup code exchange.
"""
import httpx
from fastapi import APIRouter, HTTPException, Header
from db.supabase_client import get_supabase
from config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])

GRAPH_BASE = "https://graph.facebook.com/v20.0"


@router.post("/whatsapp/onboard")
async def onboard_whatsapp(
    request_data: dict,
    x_admin_key: str = Header(None),
):
    """
    Exchange Meta authorization code for WhatsApp phone_number_id.

    Input:  { tenant_id, meta_code }
    Output: { whatsapp_number: phone_number_id }
    """
    s = get_settings()

    # ── Auth ────────────────────────────────────────────────────────────────
    if x_admin_key != s.secret_key:
        raise HTTPException(status_code=403, detail="Unauthorized")

    tenant_id = request_data.get("tenant_id")
    meta_code = request_data.get("meta_code")

    if not tenant_id or not meta_code:
        raise HTTPException(status_code=400, detail="Missing tenant_id or meta_code")

    # ── Validate settings have Meta credentials ──────────────────────────────
    meta_app_id     = getattr(s, "meta_app_id",     None) or getattr(s, "META_APP_ID",     None)
    meta_app_secret = getattr(s, "meta_app_secret", None) or getattr(s, "META_APP_SECRET", None)

    if not meta_app_id or not meta_app_secret:
        raise HTTPException(
            status_code=500,
            detail="META_APP_ID or META_APP_SECRET not configured in backend environment"
        )

    try:
        with httpx.Client(timeout=15) as client:

            # ── Step 1: Exchange code → short-lived user access token ────────
            # NOTE: redirect_uri must be omitted for Embedded Signup code exchange
            # (unlike standard OAuth, Meta embedded signup codes don't use redirect_uri)
            token_res = client.get(
                f"{GRAPH_BASE}/oauth/access_token",
                params={
                    "client_id":     meta_app_id,
                    "client_secret": meta_app_secret,
                    "code":          meta_code,
                },
            )

            token_data = token_res.json()
            if token_res.status_code != 200 or "access_token" not in token_data:
                err = token_data.get("error", {})
                raise Exception(
                    f"Token exchange failed: {err.get('message', token_data)}"
                )

            access_token: str = token_data["access_token"]

            # ── Step 2: Get WhatsApp Business Accounts shared by the user ────
            waba_res = client.get(
                f"{GRAPH_BASE}/me/businesses",
                params={
                    "fields":       "owned_whatsapp_business_accounts{id,name,phone_numbers{id,display_phone_number,verified_name}}",
                    "access_token": access_token,
                },
            )

            waba_data = waba_res.json()
            if waba_res.status_code != 200 or "error" in waba_data:
                err = waba_data.get("error", {})
                raise Exception(
                    f"WABA fetch failed: {err.get('message', waba_data)}"
                )

            # ── Step 3: Extract first WABA + phone_number_id ──────────────────
            businesses   = waba_data.get("data", [])
            waba_id          = None
            phone_number_id  = None

            for business in businesses:
                waba_list = business.get("owned_whatsapp_business_accounts", {}).get("data", [])
                for waba in waba_list:
                    phones = waba.get("phone_numbers", {}).get("data", [])
                    if phones:
                        waba_id         = waba.get("id")
                        phone_number_id = phones[0].get("id")
                        break
                if phone_number_id:
                    break

            if not phone_number_id:
                raise Exception(
                    "No WhatsApp phone number found on the account. "
                    "Make sure you completed all steps in the Meta popup and have a phone number added."
                )

            # ── Step 4: Subscribe this app to the WABA's webhooks ─────────────
            # Required for a WABA your app has never touched before — without
            # this, messages sent to the new number never reach /webhook.
            # Subscribing is idempotent, so it's safe to call even if the WABA
            # (e.g. your own dev account) is already subscribed.
            subscribe_res = client.post(
                f"{GRAPH_BASE}/{waba_id}/subscribed_apps",
                params={"access_token": access_token},
            )
            subscribe_data = subscribe_res.json()
            webhook_subscribed = subscribe_res.status_code == 200 and subscribe_data.get("success") is True
            if not webhook_subscribed:
                err = subscribe_data.get("error", {})
                print(f"[settings] WABA subscribe failed for {waba_id}: {err.get('message', subscribe_data)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Meta API error: {str(e)}")

    # ── Step 5: Persist phone_number_id to tenants table ─────────────────────
    sb = get_supabase()
    try:
        result = (
            sb.table("tenants")
            .update({"whatsapp_number": phone_number_id})
            .eq("id", tenant_id)
            .execute()
        )
        if not result.data:
            raise Exception(f"Tenant {tenant_id} not found or update failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"whatsapp_number": phone_number_id, "webhook_subscribed": webhook_subscribed}