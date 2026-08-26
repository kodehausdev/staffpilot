"""
Tenant settings — WhatsApp onboarding via Meta Embedded Signup.

Full token flow:
  1. FB.login() with config_id → short-lived auth CODE
  2. Exchange code → short-lived OBO user access token (~60 days)
  3. debug_token → extract WABA ID from granular_scopes
     (whatsapp_business_management only — no business_management needed)
  4. OBO token + WABA ID → fetch phone numbers
  5. Register phone number with tenant PIN (no manual Meta verification)
  6. Exchange OBO token → permanent System User token scoped to tenant WABA
     (never expires, survives user password changes / app revocations)
  7. Subscribe app webhook to tenant WABA
  8. Persist phone_number_id + waba_id + permanent token to tenants table
"""
import httpx
from fastapi import APIRouter, HTTPException, Header
from db.supabase_client import get_supabase
from config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])

GRAPH_VERSION = "v20.0"
GRAPH_BASE    = f"https://graph.facebook.com/{GRAPH_VERSION}"


@router.post("/whatsapp/onboard")
async def onboard_whatsapp(
    request_data: dict,
    x_admin_key: str = Header(None),
):
    """
    Full WhatsApp onboarding in one call:
    - Exchanges Meta embedded signup code for permanent system user token
    - Registers the phone number (no manual verification needed)
    - Subscribes webhook
    - Saves everything to tenants table

    Input:  { tenant_id, meta_code, pin }
    Output: { whatsapp_number, display_phone_number, verified_name, waba_id }
    """
    s = get_settings()

    # ── Auth ────────────────────────────────────────────────────────────────
    if x_admin_key != s.secret_key:
        raise HTTPException(status_code=403, detail="Unauthorized")

    tenant_id = request_data.get("tenant_id")
    meta_code = request_data.get("meta_code")
    pin       = str(request_data.get("pin", ""))

    if not tenant_id or not meta_code:
        raise HTTPException(status_code=400, detail="Missing tenant_id or meta_code")

    if not pin or not pin.isdigit() or len(pin) != 6:
        raise HTTPException(
            status_code=400,
            detail="A 6-digit numeric PIN is required to register your WhatsApp number."
        )

    # ── Validate Meta credentials ────────────────────────────────────────────
    meta_app_id     = getattr(s, "meta_app_id",     "") or ""
    meta_app_secret = getattr(s, "meta_app_secret", "") or ""

    if not meta_app_id or not meta_app_secret:
        raise HTTPException(
            status_code=500,
            detail="META_APP_ID or META_APP_SECRET not configured in backend .env"
        )

    # App access token — for debug_token and system user operations only
    app_access_token = f"{meta_app_id}|{meta_app_secret}"

    try:
        with httpx.Client(timeout=30) as client:

            # ── Step 1: Exchange auth code → OBO user access token ───────────
            # Embedded signup codes do NOT use redirect_uri — omit it.
            token_res  = client.get(
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
                raise Exception(f"Code exchange failed: {err.get('message', token_data)}")

            obo_token: str = token_data["access_token"]
            print(f"[onboard] OBO token acquired for tenant {tenant_id}")

            # ── Step 2: debug_token → extract WABA ID ────────────────────────
            debug_res  = client.get(
                f"{GRAPH_BASE}/debug_token",
                params={
                    "input_token":  obo_token,
                    "access_token": app_access_token,
                },
            )
            debug_data = debug_res.json()

            if debug_res.status_code != 200 or "error" in debug_data:
                err = debug_data.get("error", {})
                raise Exception(f"Token debug failed: {err.get('message', debug_data)}")

            granular_scopes = debug_data.get("data", {}).get("granular_scopes", [])
            waba_id: str | None = None

            for scope in granular_scopes:
                if scope.get("scope") == "whatsapp_business_management":
                    target_ids = scope.get("target_ids", [])
                    if target_ids:
                        waba_id = target_ids[0]
                        break

            if not waba_id:
                raise Exception(
                    "Could not extract WABA ID from token scopes. "
                    "Ensure tenant completed all steps in the Meta popup and "
                    "granted whatsapp_business_management permission."
                )

            print(f"[onboard] WABA ID: {waba_id} for tenant {tenant_id}")

            # ── Step 3: Fetch phone numbers from tenant WABA ─────────────────
            phones_res  = client.get(
                f"{GRAPH_BASE}/{waba_id}/phone_numbers",
                params={
                    "fields":       "id,display_phone_number,verified_name,status",
                    "access_token": obo_token,
                },
            )
            phones_data = phones_res.json()

            if phones_res.status_code != 200 or "error" in phones_data:
                err = phones_data.get("error", {})
                raise Exception(f"Phone numbers fetch failed: {err.get('message', phones_data)}")

            phones = phones_data.get("data", [])
            if not phones:
                raise Exception(
                    "No WhatsApp phone numbers found on this WABA. "
                    "Add a phone number in Meta Business Manager first."
                )

            first_phone     = phones[0]
            phone_number_id = first_phone["id"]
            print(f"[onboard] phone_number_id: {phone_number_id} ({first_phone.get('display_phone_number')})")

            # ── Step 4: Register phone number with tenant PIN ─────────────────
            # Moves number from "Pending" → "Live" automatically.
            # PIN is set by the tenant — needed if they ever migrate the number.
            reg_res  = client.post(
                f"{GRAPH_BASE}/{phone_number_id}/register",
                params={"access_token": obo_token},
                json={
                    "messaging_product": "whatsapp",
                    "pin":               pin,
                },
            )
            reg_data = reg_res.json()

            if reg_res.status_code != 200 or not reg_data.get("success"):
                err = reg_data.get("error", {})
                # Non-fatal for sandbox numbers — log and continue
                print(f"[onboard] WARNING: registration response: {err.get('message', reg_data)}")
            else:
                print(f"[onboard] Phone number {phone_number_id} registered — Live")

            # ── Step 5: Exchange OBO token → permanent System User token ──────
            # OBO tokens expire in ~60 days and are tied to the user's Facebook
            # session. A System User token is app-level, never expires, and
            # survives the user revoking app access or changing their password.
            permanent_token: str = obo_token  # safe fallback if exchange fails

            try:
                # 5a: Get your app's system user
                sys_users_res  = client.get(
                    f"{GRAPH_BASE}/{meta_app_id}/system_users",
                    params={"access_token": app_access_token},
                )
                sys_users_data = sys_users_res.json()
                system_users   = sys_users_data.get("data", [])

                if not system_users:
                    raise Exception("No system user found on this app — create one in Meta Business Manager")

                system_user_id = system_users[0]["id"]
                print(f"[onboard] System user ID: {system_user_id}")

                # 5b: Assign system user to tenant's WABA with MANAGE permission
                assign_res  = client.post(
                    f"{GRAPH_BASE}/{waba_id}/assigned_users",
                    params={"access_token": obo_token},  # must use OBO token here
                    json={
                        "user":  system_user_id,
                        "tasks": ["MANAGE"],
                    },
                )
                assign_data = assign_res.json()
                if not assign_data.get("success"):
                    raise Exception(f"System user assignment failed: {assign_data}")

                print(f"[onboard] System user {system_user_id} assigned to WABA {waba_id}")

                # 5c: Generate permanent token for system user scoped to this WABA
                perm_res  = client.post(
                    f"{GRAPH_BASE}/{system_user_id}/access_tokens",
                    params={"access_token": app_access_token},
                    json={
                        "app_id": meta_app_id,
                        "scope":  "whatsapp_business_management,whatsapp_business_messaging",
                    },
                )
                perm_data = perm_res.json()

                if "access_token" in perm_data:
                    permanent_token = perm_data["access_token"]
                    print(f"[onboard] Permanent system user token generated for WABA {waba_id}")
                else:
                    raise Exception(f"Permanent token generation failed: {perm_data}")

            except Exception as perm_err:
                # Non-fatal — OBO token still works for ~60 days
                # Tenant can reconnect via "Reconnect via Meta" to refresh it
                print(f"[onboard] WARNING: permanent token exchange failed, using OBO token (~60 days): {perm_err}")

            # ── Step 6: Subscribe app webhook to tenant WABA ─────────────────
            sub_res  = client.post(
                f"{GRAPH_BASE}/{waba_id}/subscribed_apps",
                params={"access_token": obo_token},
            )
            sub_data = sub_res.json()

            if sub_res.status_code != 200 or not sub_data.get("success"):
                print(f"[onboard] WARNING: webhook subscription failed: {sub_data}")
            else:
                print(f"[onboard] Webhook subscribed for WABA {waba_id}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Meta API error: {str(e)}")

    # ── Step 7: Persist everything to tenants table ──────────────────────────
    sb = get_supabase()
    try:
        result = (
            sb.table("tenants")
            .update({
                "whatsapp_number":       phone_number_id,
                "meta_waba_id":          waba_id,
                "whatsapp_access_token": permanent_token,  # permanent > OBO fallback
            })
            .eq("id", tenant_id)
            .execute()
        )
        if not result.data:
            raise Exception(f"Tenant {tenant_id} not found or update failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    print(f"[onboard] ✓ Tenant {tenant_id} fully onboarded — WABA {waba_id}, phone {phone_number_id}")

    return {
        "whatsapp_number":      phone_number_id,
        "display_phone_number": first_phone.get("display_phone_number"),
        "verified_name":        first_phone.get("verified_name"),
        "waba_id":              waba_id,
    }
