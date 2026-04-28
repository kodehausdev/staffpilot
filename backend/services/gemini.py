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
- leave_request: employee is REQUESTING to take time off ("I want leave", "can I take sick leave", "apply for annual leave")
- hr_qa: questions about company policy, rules, entitlements, or procedures — including questions about leave policy, notice periods, allowances, disciplinary rules
- payslip: asking about salary, payslip, payment, deductions
- onboarding: new employee setup, first day, documents to submit
- greeting: hi, hello, good morning, how are you
- unknown: anything else

Key distinction: "What is the notice period for sick leave?" is hr_qa (policy question), NOT leave_request.
"I want to take sick leave" is leave_request (an actual request).

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
    result = _get_client().models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY", output_dimensionality=768),
    )
    return result.embeddings[0].values


def embed_document_chunk(text: str) -> list[float]:
    result = _get_client().models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768),
    )
    return result.embeddings[0].values
