"""
HR Q&A via RAG — embed question, find relevant chunks, ask Gemini.
"""
from db.supabase_client import get_supabase
from services.gemini import generate, embed_text
from services.whatsapp import send_message
from services.session import clear_session


def handle(employee: dict, message: str) -> None:
    phone = employee["phone"]
    tenant_id = employee["tenant_id"]

    send_message(phone, "Let me check your company's HR policy...")

    chunks = _retrieve_chunks(message, tenant_id)

    if not chunks:
        send_message(
            phone,
            "I couldn't find relevant policy documents for that question. "
            "Please contact your HR admin directly."
        )
        clear_session(employee["id"])
        return

    context = "\n\n---\n\n".join([c["content"] for c in chunks])

    prompt = f"""You are an HR assistant for a Nigerian company.
Answer the employee's question using ONLY the provided HR policy documents.
Be concise — 3 sentences max. If the answer is not in the documents, say so.

HR Policy Documents:
{context}

Employee question: {message}

Answer:"""

    answer = generate(prompt, temperature=0.1)
    send_message(phone, answer)
    clear_session(employee["id"])


def _retrieve_chunks(query: str, tenant_id: str, k: int = 4) -> list[dict]:
    """Vector similarity search scoped to tenant."""
    sb = get_supabase()
    embedding = embed_text(query)

    result = sb.rpc(
        "match_doc_chunks",
        {
            "query_embedding": embedding,
            "match_tenant_id": tenant_id,
            "match_count": k,
        }
    ).execute()

    # Filter for reasonable similarity (>0.5)
    chunks = [c for c in (result.data or []) if c.get("similarity", 0) > 0.5]
    return chunks
