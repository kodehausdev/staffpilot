"""
Meta WhatsApp Cloud API client.
Replaces Twilio — no per-message fees, direct Meta integration.
Supports both global and tenant-specific phone numbers and access tokens.

Token strategy:
  - Your own number (whatsapp_phone_number_id in .env) → system access token
  - Tenant's own WABA number → their OBO token stored in tenants.whatsapp_access_token
    (saved during Embedded Signup onboarding)
"""
import httpx
import re
from config import get_settings
from db.supabase_client import get_supabase

GRAPH_URL = "https://graph.facebook.com/v20.0"


def _get_tenant_config(tenant_id: str) -> dict:
    """
    Returns { phone_number_id, access_token } for a tenant.
    Falls back to system config if tenant has no own token stored.
    """
    s   = get_settings()
    sb  = get_supabase()

    result = (
        sb.table("tenants")
        .select("whatsapp_number, whatsapp_access_token")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )

    if result.data:
        row              = result.data[0]
        phone_number_id  = row.get("whatsapp_number")
        tenant_token     = row.get("whatsapp_access_token")

        if phone_number_id and tenant_token:
            return {
                "phone_number_id": phone_number_id,
                "access_token":    tenant_token,   # OBO token from their embedded signup
            }

        if phone_number_id:
            # Tenant has a number but no stored token (manual entry) — fall back to system token
            return {
                "phone_number_id": phone_number_id,
                "access_token":    s.whatsapp_access_token,
            }

    # No tenant config at all — use system defaults
    return {
        "phone_number_id": s.whatsapp_phone_number_id,
        "access_token":    s.whatsapp_access_token,
    }


def send_message(to_phone: str, body: str, tenant_id: str | None = None) -> None:
    """
    Send a WhatsApp text message via Meta Cloud API.

    to_phone:  phone number with country code, e.g. +2348XXXXXXXXX
    body:      message text
    tenant_id: if provided, uses that tenant's own WABA number and token
    """
    config = _get_tenant_config(tenant_id) if tenant_id else {
        "phone_number_id": get_settings().whatsapp_phone_number_id,
        "access_token":    get_settings().whatsapp_access_token,
    }

    phone = to_phone.replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]

    with httpx.Client() as client:
        resp = client.post(
            f"{GRAPH_URL}/{config['phone_number_id']}/messages",
            headers={
                "Authorization": f"Bearer {config['access_token']}",
                "Content-Type":  "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "recipient_type":    "individual",
                "to":                phone,
                "type":              "text",
                "text":              {"body": strip_markdown(body)},
            },
        )

    if resp.status_code != 200:
        print(f"[WhatsApp] Send failed: {resp.status_code} {resp.text}")


def send_template(
    to_phone: str,
    template_name: str,
    lang: str = "en",
    tenant_id: str | None = None,
) -> None:
    """Send a template message (needed for first-contact or outside 24hr window)."""
    config = _get_tenant_config(tenant_id) if tenant_id else {
        "phone_number_id": get_settings().whatsapp_phone_number_id,
        "access_token":    get_settings().whatsapp_access_token,
    }

    phone = to_phone.replace("+", "").replace(" ", "")

    with httpx.Client() as client:
        client.post(
            f"{GRAPH_URL}/{config['phone_number_id']}/messages",
            headers={
                "Authorization": f"Bearer {config['access_token']}",
                "Content-Type":  "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to":                phone,
                "type":              "template",
                "template": {
                    "name":     template_name,
                    "language": {"code": lang},
                },
            },
        )


def strip_markdown(text: str) -> str:
    """WhatsApp doesn't render markdown headings/code — strip them."""
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)        # bold → WA bold
    text = re.sub(r'#{1,6}\s*', '', text)                  # headers
    text = re.sub(r'`{3}.*?`{3}', '', text, flags=re.DOTALL)  # code blocks
    text = re.sub(r'`(.*?)`', r'\1', text)                 # inline code
    return text.strip()


def extract_phone(raw: str) -> str:
    """Normalize phone number to E.164 with + prefix."""
    digits = re.sub(r'\D', '', raw)
    return f"+{digits}"


def parse_webhook(body: dict) -> list[dict]:
    """
    Parse incoming Meta webhook payload.
    Returns list of message dicts: { from, to, text, message_id }
    """
    messages = []
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                phone_number_id = value.get("metadata", {}).get("phone_number_id", "")

                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        continue  # skip images/audio for now
                    messages.append({
                        "from":       f"+{msg['from']}",
                        "to":         phone_number_id,
                        "text":       msg["text"]["body"],
                        "message_id": msg["id"],
                    })
    except Exception as e:
        print(f"[WhatsApp] Parse error: {e}")
    return messages
