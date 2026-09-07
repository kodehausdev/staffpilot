"""
Meta WhatsApp Cloud API client.
Replaces Twilio — no per-message fees, direct Meta integration.
Supports both global and tenant-specific phone numbers.
"""
import httpx
import re
from config import get_settings
from db.supabase_client import get_supabase

GRAPH_URL = "https://graph.facebook.com/v20.0"


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


# ─── Interactive Messages ─────────────────────────────────────────────────────
#
# WhatsApp supports three types of interactive messages — all work within the
# 24hr conversation window (no template approval needed):
#
#   1. BUTTONS   — up to 3 clickable reply buttons  (most common)
#   2. LIST      — up to 10 options in a scrollable menu
#   3. CTA_URL   — single button that opens a website
#
# How it works:
#   - You send a message with type="interactive"
#   - The payload has an "action" block describing the buttons/list
#   - When user taps a button, Meta sends a webhook with type="interactive"
#     and the button's "id" in the payload — you read that id and route accordingly
#
# Anatomy of a button payload:
#   {
#     "type": "interactive",
#     "interactive": {
#       "type": "button",           ← "button" | "list" | "cta_url"
#       "header": {...},            ← optional: text, image, video, document
#       "body": {"text": "..."},    ← required: main message
#       "footer": {"text": "..."},  ← optional: small grey text below
#       "action": {
#         "buttons": [              ← up to 3 for type=button
#           {
#             "type": "reply",
#             "reply": {
#               "id": "leave",      ← what YOU get in the webhook when tapped
#               "title": "📅 Leave" ← what the USER sees on the button (≤20 chars)
#             }
#           }
#         ]
#       }
#     }
#   }
#
# Anatomy of incoming interactive webhook:
#   body["entry"][0]["changes"][0]["value"]["messages"][0] = {
#     "type": "interactive",
#     "interactive": {
#       "type": "button_reply",
#       "button_reply": {
#         "id": "leave",     ← the id you set
#         "title": "📅 Leave"
#       }
#     }
#   }
# ─────────────────────────────────────────────────────────────────────────────


def _get_send_config(tenant_id: str | None) -> tuple[str, str]:
    """
    Returns (phone_number_id, access_token) for any send function.
    Centralises token/number resolution so all send functions stay DRY.
    """
    s = get_settings()
    if not tenant_id:
        return s.whatsapp_phone_number_id, s.whatsapp_access_token

    sb     = get_supabase()
    result = (
        sb.table("tenants")
        .select("whatsapp_number, whatsapp_access_token")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if result.data:
        row   = result.data[0]
        ph_id = row.get("whatsapp_number")
        token = row.get("whatsapp_access_token")
        if ph_id and token:
            return ph_id, token
        if ph_id:
            return ph_id, s.whatsapp_access_token

    return s.whatsapp_phone_number_id, s.whatsapp_access_token


def send_buttons(
    to_phone:   str,
    body:       str,
    buttons:    list[dict],          # [{"id": "leave", "title": "📅 Leave"}, ...]
    tenant_id:  str | None = None,
    header:     str | None = None,   # optional bold text above body
    footer:     str | None = None,   # optional grey text below buttons
) -> None:
    """
    Send a message with up to 3 quick-reply buttons.

    ── Parameters ───────────────────────────────────────────────────────────
    to_phone   : recipient in E.164 format, e.g. "+2348XXXXXXXXX"
    body       : main message text (shown above buttons)
    buttons    : list of dicts, each with "id" (≤256 chars) and "title" (≤20 chars)
                 Max 3 buttons. The "id" is what you get back in the webhook.
    tenant_id  : optional — uses tenant's own WABA number/token if provided
    header     : optional bold line above body (plain text only for button type)
    footer     : optional small grey line below the buttons

    ── Example usage ────────────────────────────────────────────────────────
    send_buttons(
        to_phone="+2348012345678",
        body="Hi Remi 👋 What do you need?",
        buttons=[
            {"id": "leave",   "title": "📅 Leave request"},
            {"id": "payslip", "title": "💰 My payslip"},
            {"id": "policy",  "title": "📋 HR policy"},
        ],
        footer="CordHR · Your company HR assistant",
        tenant_id=employee["tenant_id"],
    )

    ── Handling the response in webhook.py ──────────────────────────────────
    In parse_webhook(), also handle type="interactive":

        if msg.get("type") == "interactive":
            btn_id = msg["interactive"]["button_reply"]["id"]
            # route by btn_id: "leave" | "payslip" | "policy" etc.
    """
    phone_number_id, access_token = _get_send_config(tenant_id)
    phone = re.sub(r"\D", "", to_phone)

    # Build the interactive payload
    interactive: dict = {
        "type":   "button",
        "body":   {"text": body},
        "action": {
            "buttons": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                for b in buttons[:3]  # Meta hard-limits to 3
            ]
        },
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}

    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{GRAPH_URL}/{phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "recipient_type":    "individual",
                "to":                phone,
                "type":              "interactive",
                "interactive":       interactive,
            },
        )

    if resp.status_code != 200:
        print(f"[WhatsApp] send_buttons failed: {resp.status_code} {resp.text}")


def send_list(
    to_phone:     str,
    body:         str,
    button_label: str,               # text on the button that opens the list, e.g. "Choose option"
    sections:     list[dict],        # see structure below
    tenant_id:    str | None = None,
    header:       str | None = None,
    footer:       str | None = None,
) -> None:
    """
    Send a scrollable list menu — up to 10 items across multiple sections.
    Best for more than 3 options (use send_buttons for ≤3).

    ── sections structure ───────────────────────────────────────────────────
    sections = [
        {
            "title": "Leave",          ← section header (optional but recommended)
            "rows": [
                {
                    "id":          "annual_leave",
                    "title":       "Annual leave",      ← ≤24 chars
                    "description": "Request time off",  ← optional, ≤72 chars
                },
                {
                    "id":          "sick_leave",
                    "title":       "Sick leave",
                },
            ]
        },
        {
            "title": "Other",
            "rows": [
                {"id": "payslip", "title": "My payslip"},
                {"id": "policy",  "title": "HR policy Q&A"},
            ]
        }
    ]

    ── Example usage ────────────────────────────────────────────────────────
    send_list(
        to_phone="+2348012345678",
        body="What do you need help with today?",
        button_label="See options",
        sections=[
            {"title": "Leave", "rows": [
                {"id": "annual", "title": "Annual leave"},
                {"id": "sick",   "title": "Sick leave"},
            ]},
            {"title": "Other", "rows": [
                {"id": "payslip", "title": "My payslip"},
                {"id": "policy",  "title": "HR policy"},
            ]},
        ],
        tenant_id=employee["tenant_id"],
    )
    """
    phone_number_id, access_token = _get_send_config(tenant_id)
    phone = re.sub(r"\D", "", to_phone)

    interactive: dict = {
        "type": "list",
        "body": {"text": body},
        "action": {
            "button":   button_label,
            "sections": sections,
        },
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}

    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{GRAPH_URL}/{phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "recipient_type":    "individual",
                "to":                phone,
                "type":              "interactive",
                "interactive":       interactive,
            },
        )

    if resp.status_code != 200:
        print(f"[WhatsApp] send_list failed: {resp.status_code} {resp.text}")


def send_cta_url(
    to_phone:     str,
    body:         str,
    button_label: str,   # text on the button, e.g. "Visit website"
    url:          str,   # the URL to open
    tenant_id:    str | None = None,
    header:       str | None = None,
    footer:       str | None = None,
) -> None:
    """
    Send a message with a single URL button — opens a website when tapped.
    Perfect for "Sign up", "View dashboard", "Read policy" CTAs.

    ── Example usage ────────────────────────────────────────────────────────
    send_cta_url(
        to_phone="+2348012345678",
        body="Ready to set up CordHR for your company?",
        button_label="Get started free",
        url="https://cordhr.optipropose.com",
    )
    """
    phone_number_id, access_token = _get_send_config(tenant_id)
    phone = re.sub(r"\D", "", to_phone)

    interactive: dict = {
        "type": "cta_url",
        "body": {"text": body},
        "action": {
            "name":       "cta_url",
            "parameters": {
                "display_text": button_label,
                "url":          url,
            },
        },
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}

    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{GRAPH_URL}/{phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "recipient_type":    "individual",
                "to":                phone,
                "type":              "interactive",
                "interactive":       interactive,
            },
        )

    if resp.status_code != 200:
        print(f"[WhatsApp] send_cta_url failed: {resp.status_code} {resp.text}")


def send_template_with_button(to_phone: str) -> None:
    """
    Send the CordHR demo template (cordhr_demo) with Visit Website button.
    Uses CordHR's own system token and phone_number_id — always.
    Template must be Active in WhatsApp Manager before this will work.
    """
    s = get_settings()

    # Strip to digits only — no +, no spaces
    phone = re.sub(r"\D", "", to_phone)

    print(f"[demo] Calling template API: phone_number_id={s.whatsapp_phone_number_id} to={phone}")

    with httpx.Client(timeout=15) as client:
        resp = client.post(
            f"{GRAPH_URL}/{s.whatsapp_phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {s.whatsapp_access_token}",
                "Content-Type":  "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to":                phone,
                "type":              "template",
                "template": {
                    "name":     "cordhr_demo",
                    "language": {"code": "en"},
                },
            },
        )

    print(f"[demo] Template API response: {resp.status_code} {resp.text}")

    if resp.status_code != 200:
        raise Exception(f"Template send failed: {resp.status_code} {resp.text}")


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

    Handles two message types:
      - text:        normal typed message
      - interactive: button tap / list selection
                     text is set to the button/row id so existing intent
                     routing works without any changes — tapping
                     "📅 Leave request" sets text = "leave", which the
                     intent classifier already knows how to handle.
    """
    messages = []
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value           = change.get("value", {})
                phone_number_id = value.get("metadata", {}).get("phone_number_id", "")

                for msg in value.get("messages", []):
                    msg_type = msg.get("type")

                    if msg_type == "text":
                        messages.append({
                            "from":       f"+{msg['from']}",
                            "to":         phone_number_id,
                            "text":       msg["text"]["body"],
                            "message_id": msg["id"],
                        })

                    elif msg_type == "interactive":
                        # User tapped a button or selected a list row.
                        # Extract the id and treat it as the message text —
                        # this way all existing routing works unchanged.
                        interactive = msg.get("interactive", {})
                        i_type      = interactive.get("type")

                        if i_type == "button_reply":
                            text = interactive["button_reply"]["id"]
                        elif i_type == "list_reply":
                            text = interactive["list_reply"]["id"]
                        else:
                            continue

                        messages.append({
                            "from":       f"+{msg['from']}",
                            "to":         phone_number_id,
                            "text":       text,
                            "message_id": msg["id"],
                        })
                    # skip images, audio, documents for now

    except Exception as e:
        print(f"[WhatsApp] Parse error: {e}")
    return messages