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
    prompt = f"""Classify this Nigerian employee WhatsApp message into exactly one of these intents:
leave_request, hr_qa, payslip, onboarding, greeting, unknown

Rules:
- leave_request: employee wants to ACTIVELY START a leave application right now ("I want leave", "can I take sick leave", "apply for annual leave", "I need tomorrow off"). The employee is ready to submit, not just asking questions.
- hr_qa: questions about company policy, rules, benefits, entitlements, or workplace procedures — including HMO, pension, notice periods, allowances, disciplinary rules, misconduct, perks, resignation. ALSO: questions about how leave works, whether something is permissible, or what the process is — even if they mention leave days or balances.
- payslip: employee is asking about THEIR OWN salary or payslip ("send my payslip", "when is my salary", "what is my net pay", "show my payslip"). NOT gossip or curiosity about what OTHER people earn.
- onboarding: new employee setup, first day, documents to submit
- greeting: hi, hello, good morning, how are you
- unknown: personal chat, off-topic questions, gibberish, slang with no HR meaning, questions about other people's salaries

Key distinctions:
- "What is the notice period?" = hr_qa (policy question), NOT leave_request
- "I want to take sick leave" = leave_request (actual request to submit now)
- "I have accrued 17.5 days, is half-day leave permissible?" = hr_qa (policy question, NOT a leave request — they are asking HOW, not submitting)
- "can I take 3.5 days for my nephew's graduation?" = hr_qa (asking about policy/permissibility)
- "do I need to submit a letter?" = hr_qa (process question)
- "who earns the most in the office?" = unknown (gossip, not their own payslip)
- "who dey collect salary pass?" = unknown (gossip about others)
- "send my payslip" = payslip (their own)
- "my manager is harrassing me" = hr_qa
- "I want to japa" = hr_qa (resignation/notice period query)

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
