"""
Tenant settings — WhatsApp onboarding via Meta Embedded Signup.

Token flow:
  1. FB.login() with config_id → returns a short-lived auth CODE (not a token)
  2. Exchange code → short-lived USER access token (this is the OBO token)
  3. Use OBO token to call debug_token → extract WABA ID from granular_scopes
     (only needs whatsapp_business_management — no business_management required)
  4. Use OBO token to fetch phone numbers from that WABA
  5. Save phone_number_id to tenants table

Why NOT to use your system user token here:
  - Your system token only has rights over YOUR own business assets
  - External tenants' WABAs are owned by THEIR business
  - The OBO token is scoped specifically to what THEY granted during the popup
  - Using your system token = (#100) Missing Permission on their assets
"""
import httpx
from fastapi import APIRouter, HTTPException, Header
from db.supabase_client import get_supabase
from config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])

GRAPH_BASE    = "https://graph.facebook.com/v20.0"
GRAPH_VERSION = "v20.0"


@router.post("/whatsapp/onboard")
async def onboard_whatsapp(
    request_data: dict,
    x_admin_key: str = Header(None),
):
    """
    Exchange Meta embedded signup auth code for a WhatsApp phone_number_id
    using the OBO (On-Behalf-Of) token pattern.

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

    # ── Validate Meta credentials are configured ─────────────────────────────
    meta_app_id     = getattr(s, "meta_app_id",     "") or getattr(s, "META_APP_ID",     "")
    meta_app_secret = getattr(s, "meta_app_secret", "") or getattr(s, "META_APP_SECRET", "")

    if not meta_app_id or not meta_app_secret:
        raise HTTPException(
            status_code=500,
            detail="META_APP_ID or META_APP_SECRET not configured in backend .env"
        )

    # App access token — used ONLY for debug_token calls, never for tenant assets
    app_access_token = f"{meta_app_id}|{meta_app_secret}"

    try:
        with httpx.Client(timeout=20) as client:

            # ── Step 1: Exchange auth code → OBO user access token ───────────
            # This is a short-lived token scoped to what the tenant granted.
            # Do NOT use redirect_uri — embedded signup codes don't require it.
            token_res = client.get(
                f"https://graph.facebook.com/{GRAPH_VERSION}/oauth/access_token",
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
                    f"Code exchange failed: {err.get('message', token_data)}"
                )

            # This is the OBO token — scoped to the tenant's granted permissions
            obo_token: str = token_data["access_token"]

            # ── Step 2: Debug OBO token to extract the WABA ID ───────────────
            # granular_scopes contains target_ids for whatsapp_business_management
            # which gives us the WABA ID without needing business_management permission.
            debug_res = client.get(
                f"https://graph.facebook.com/{GRAPH_VERSION}/debug_token",
                params={
                    "input_token":  obo_token,
                    "access_token": app_access_token,  # app token to inspect OBO token
                },
            )
            debug_data = debug_res.json()

            if debug_res.status_code != 200 or "error" in debug_data:
                err = debug_data.get("error", {})
                raise Exception(
                    f"Token debug failed: {err.get('message', debug_data)}"
                )

            token_info      = debug_data.get("data", {})
            granular_scopes = token_info.get("granular_scopes", [])

            # Extract WABA ID from the whatsapp_business_management scope
            waba_id = None
            for scope in granular_scopes:
                if scope.get("scope") == "whatsapp_business_management":
                    target_ids = scope.get("target_ids", [])
                    if target_ids:
                        waba_id = target_ids[0]
                        break

            if not waba_id:
                raise Exception(
                    "Could not extract WABA ID from token scopes. "
                    "Make sure the tenant completed all steps in the Meta popup "
                    "and granted whatsapp_business_management permission."
                )

            # ── Step 3: Fetch phone numbers from tenant's WABA ───────────────
            # Use the OBO token — NOT your system token.
            # The OBO token has rights to this specific WABA because the tenant
            # granted access during the embedded signup flow.
            phones_res = client.get(
                f"{GRAPH_BASE}/{waba_id}/phone_numbers",
                params={
                    "fields":       "id,display_phone_number,verified_name,status",
                    "access_token": obo_token,  # ← OBO token, not system token
                },
            )
            phones_data = phones_res.json()

            if phones_res.status_code != 200 or "error" in phones_data:
                err = phones_data.get("error", {})
                raise Exception(
                    f"Phone numbers fetch failed: {err.get('message', phones_data)}"
                )

            phones = phones_data.get("data", [])
            if not phones:
                raise Exception(
                    "No WhatsApp phone numbers found on this WABA. "
                    "The tenant needs to add a phone number in Meta Business Manager first."
                )

            # Take the first registered phone number
            first_phone     = phones[0]
            phone_number_id = first_phone["id"]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Meta API error: {str(e)}")

    # ── Step 4: Persist phone_number_id to tenants table ────────────────────
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

    return {
        "whatsapp_number":        phone_number_id,
        "display_phone_number":   first_phone.get("display_phone_number"),
        "verified_name":          first_phone.get("verified_name"),
    }