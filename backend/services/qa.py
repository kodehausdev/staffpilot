"""
HR Q&A via RAG — embed question, find relevant chunks, ask Gemini.
"""
import re
from db.supabase_client import get_supabase
from services.gemini import generate, embed_text
from services.whatsapp import send_message
from services.session import clear_session

# Covers all standard emoji blocks
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U00002702-\U000027B0"
    "]+",
    flags=re.UNICODE,
)


def handle(employee: dict, message: str) -> None:
    phone     = employee["phone"]
    tenant_id = employee["tenant_id"]

    chunks = _retrieve_chunks(message, tenant_id)

    if not chunks:
        send_message(
            phone,
            "Omo I no see that one for policy 😭 Abeg check with HR admin, they go sort you fast."
        )
        clear_session(employee["id"])
        return

    context = "\n\n---\n\n".join([c["content"] for c in chunks])

    full_name    = employee.get("name") or ""
    first_name   = full_name.split()[0] if full_name else "there"
    leave_balance = employee.get("leave_balance", "unknown")
    department   = employee.get("department") or "your team"

    prompt = f"""You are an HR assistant for a Nigerian company, talking to Gen Z staff on WhatsApp.

Employee context:
- Name: {first_name}
- Department: {department}
- Leave days remaining: {leave_balance}

Rules:
1. Reply like a smart friend, not a textbook. 2-3 lines max.
2. Match the user's tone: if their message is casual or informal, you can sprinkle pidgin ("omo", "abeg", "sha") — one word max per reply. If they write in plain formal English, reply in plain English. Never force pidgin.
3. If the message sounds frustrated or tired, acknowledge that first, then answer.
4. Never dump the full policy. Summarize the key point + use employee context to personalize.
5. One emoji max. Only if it fits naturally 😭🤝💚
6. Answer using ONLY the HR policy documents below. If the answer isn't there, say so honestly.

HR Policy Documents:
{context}

{first_name}'s question: {message}

Reply:"""

    answer = generate(prompt, temperature=0.3)
    answer = _sanitize_response(answer)
    send_message(phone, answer)
    clear_session(employee["id"])


def _sanitize_response(text: str) -> str:
    """Enforce: max 1 emoji, max 3 lines, max 40 words."""
    matches = list(_EMOJI_RE.finditer(text))
    if len(matches) > 1:
        for m in matches[1:]:
            text = text[:m.start()] + text[m.end():]

    lines = [ln for ln in text.split("\n") if ln.strip()]
    text  = "\n".join(lines[:3])

    words = text.split()
    if len(words) > 40:
        text = " ".join(words[:40]) + "... You want the full details?"

    return text.strip()


def _retrieve_chunks(query: str, tenant_id: str, k: int = 4) -> list[dict]:
    sb = get_supabase()
    embedding = embed_text(query)

    result = sb.rpc(
        "match_doc_chunks",
        {
            "query_embedding": embedding,
            "match_tenant_id": tenant_id,
            "match_count":     k,
        }
    ).execute()

    return [c for c in (result.data or []) if c.get("similarity", 0) > 0.5]
