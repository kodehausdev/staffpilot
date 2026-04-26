from google import genai
from google.genai import types
from config import get_settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=get_settings().gemini_api_key)
    return _client


def generate(prompt: str, system: str = None, temperature: float = 0.3) -> str:
    """Generate a response from Gemini Flash."""
    client = _get_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system or "You are a helpful HR assistant. Be concise and professional.",
            temperature=temperature,
        ),
    )
    return response.text.strip()


def classify_intent(message: str) -> str:
    """
    Classify a WhatsApp message into a flow intent.
    Returns one of: leave_request | hr_qa | payslip | onboarding | greeting | unknown
    """
    client = _get_client()
    prompt = f"""Classify this employee WhatsApp message into exactly one of these intents:
leave_request, hr_qa, payslip, onboarding, greeting, unknown

Rules:
- leave_request: asking to take time off, annual leave, sick leave, absence
- hr_qa: questions about company policy, rules, entitlements, procedures
- payslip: asking about salary, payslip, payment, deductions
- onboarding: new employee setup, first day, documents to submit
- greeting: hi, hello, good morning, how are you
- unknown: anything else

Reply with ONLY the intent label, nothing else.

Message: "{message}"
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0),
    )
    intent = response.text.strip().lower()
    valid = {"leave_request", "hr_qa", "payslip", "onboarding", "greeting", "unknown"}
    return intent if intent in valid else "unknown"


def embed_text(text: str) -> list[float]:
    """Generate embedding for a query using text-embedding-004."""
    client = _get_client()
    result = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return result.embeddings[0].values


def embed_document_chunk(text: str) -> list[float]:
    """Embed a document chunk for storage."""
    client = _get_client()
    result = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return result.embeddings[0].values
