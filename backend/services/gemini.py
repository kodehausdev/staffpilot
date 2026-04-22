import google.generativeai as genai
from config import get_settings

_configured = False


def _setup():
    global _configured
    if not _configured:
        genai.configure(api_key=get_settings().gemini_api_key)
        _configured = True


def generate(prompt: str, system: str = None, temperature: float = 0.3) -> str:
    """Generate a response from Gemini Flash."""
    _setup()
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system or "You are a helpful HR assistant. Be concise and professional.",
    )
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=temperature),
    )
    return response.text.strip()


def classify_intent(message: str) -> str:
    """
    Classify a WhatsApp message into a flow intent.
    Returns one of: leave_request | hr_qa | payslip | onboarding | greeting | unknown
    """
    _setup()
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
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.0),
    )
    intent = response.text.strip().lower()
    valid = {"leave_request", "hr_qa", "payslip", "onboarding", "greeting", "unknown"}
    return intent if intent in valid else "unknown"


def embed_text(text: str) -> list[float]:
    """Generate embedding using Google text-embedding-004."""
    _setup()
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]


def embed_document_chunk(text: str) -> list[float]:
    """Embed a document chunk for storage."""
    _setup()
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]
