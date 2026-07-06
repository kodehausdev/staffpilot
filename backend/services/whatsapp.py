"""
Meta WhatsApp Cloud API client.
Replaces Twilio — no per-message fees, direct Meta integration.
Supports both global and tenant-specific phone numbers.
"""
import httpx
import re
from config import get_settings
from db.supabase_client import get_supabase

GRAPH_URL = "https://graph.facebook.com/v19.0"


def _get_tenant_phone_id(tenant_id: str) -> str | None:
    """Look up tenant's WhatsApp phone_number_id from database."""
    sb = get_supabase()
    result = (
        sb.table("tenants")
        .select("whatsapp_number")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0].get("whatsapp_number")
    return None


def send_message(to_phone: str, body: str, tenant_id: str | None = None) -> None:
    """
    Send a WhatsApp text message via Meta Cloud API.
    
    to_phone: phone number WITH country code, e.g. +2348XXXXXXXXX
    body: message text
    tenant_id: optional tenant ID for tenant-specific phone number; defaults to global if not provided
    """
    s = get_settings()

    # Determine which phone_number_id to use
    phone_number_id = s.whatsapp_phone_number_id  # default: global
    if tenant_id:
        tenant_phone_id = _get_tenant_phone_id(tenant_id)
        if tenant_phone_id:
            phone_number_id = tenant_phone_id

    # Strip any non-digit chars except leading +
    phone = to_phone.replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]

    with httpx.Client() as client:
        resp = client.post(
            f"{GRAPH_URL}/{phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {s.whatsapp_access_token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone,
                "type": "text",
                "text": {"body": strip_markdown(body)},
            },
        )

    if resp.status_code != 200:
        print(f"[WhatsApp] Send failed: {resp.status_code} {resp.text}")


def send_template(to_phone: str, template_name: str, lang: str = "en", tenant_id: str | None = None) -> None:
    """Send a template message (needed for first-contact or 24hr window)."""
    s = get_settings()
    phone = to_phone.replace("+", "").replace(" ", "")

    # Determine which phone_number_id to use
    phone_number_id = s.whatsapp_phone_number_id  # default: global
    if tenant_id:
        tenant_phone_id = _get_tenant_phone_id(tenant_id)
        if tenant_phone_id:
            phone_number_id = tenant_phone_id

    with httpx.Client() as client:
        client.post(
            f"{GRAPH_URL}/{phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {s.whatsapp_access_token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": lang},
                },
            },
        )


def strip_markdown(text: str) -> str:
    """WhatsApp doesn't render markdown headings/code — strip them."""
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)   # bold → WA bold
    text = re.sub(r'#{1,6}\s*', '', text)              # headers
    text = re.sub(r'`{3}.*?`{3}', '', text, flags=re.DOTALL)  # code blocks
    text = re.sub(r'`(.*?)`', r'\1', text)             # inline code
    return text.strip()


def extract_phone(raw: str) -> str:
    """Normalize phone number to E.164 with + prefix."""
    digits = re.sub(r'\D', '', raw)
    return f"+{digits}"


def parse_webhook(body: dict) -> list[dict]:
    """
    Parse incoming Meta webhook payload.
    Returns list of message dicts: {from, to, text, message_id}
    """
    messages = []
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                waba_id = value.get("metadata", {}).get("phone_number_id", "")

                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        continue   # skip images/audio for now
                    messages.append({
                        "from":       f"+{msg['from']}",
                        "to":         waba_id,
                        "text":       msg["text"]["body"],
                        "message_id": msg["id"],
                    })
    except Exception as e:
        print(f"[WhatsApp] Parse error: {e}")
    return messages