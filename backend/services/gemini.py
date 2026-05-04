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
    Classify a WhatsApp message into one of three layers plus specific intents.

    RAG layer    → hr_qa
    Action layer → leave_request | leave_status | last_approval | payslip | onboarding
    Insight layer→ who_on_leave | pending_approvals | leave_analytics
    Meta         → greeting | unknown
    """
    client = _get_client()
    prompt = f"""Classify this Nigerian employee WhatsApp message into exactly one intent label.

INTENTS AND RULES
=================

leave_request
  Employee is ACTIVELY SUBMITTING a new leave application right now.
  Examples: "I want leave", "apply for sick leave", "I need tomorrow off", "take annual leave next week"

leave_status
  Employee asks about THEIR OWN leave balance, history, or remaining days.
  Examples: "what's my leave balance", "how many days do I have left", "show my leave history",
            "have I taken any leave this year", "my leave summary"

last_approval
  Employee asks who approved or rejected their last (or a specific) leave request.
  Examples: "who approved my leave", "who rejected my request", "who actioned my last leave"

payslip
  Employee asks about THEIR OWN salary or payslip.
  Examples: "send my payslip", "my net pay", "show November payslip"
  NOT: asking about what other people earn.

onboarding
  New employee setup, first-day documents, onboarding checklist.

who_on_leave
  Asking which employees are currently on leave / absent today.
  Examples: "who is on leave", "who is not in office", "who is absent today", "who dey go leave"

pending_approvals
  Asking to see pending / unactioned leave requests.
  Examples: "show pending requests", "any pending leave", "who hasn't been approved",
            "pending approvals", "leave requests waiting"

leave_analytics
  Asking for department-level or company-wide leave statistics / trends.
  Examples: "which department takes the most leave", "leave trends", "leave stats this year",
            "department with highest leave", "leave report"

hr_qa
  Questions about company POLICY, rules, benefits, entitlements, or workplace procedures —
  including HMO, pension, notice period, allowances, disciplinary rules, perks, resignation,
  remote work, misconduct. Also: hypothetical/permissibility questions about leave.
  Examples: "how many sick days am I entitled to?", "what is the notice period?",
            "is half-day leave allowed?", "HMO cover dependants?",
            "I want to japa — what's the process?"

greeting
  Hi, hello, good morning, start, menu.

unknown
  Off-topic, gossip about other people's salaries, gibberish, slang with no HR meaning.

KEY DISTINCTIONS
================
- "What is the notice period?" → hr_qa  (policy, not a submission)
- "I want to take sick leave"  → leave_request  (active submission)
- "Is half-day leave allowed?" → hr_qa  (policy/permissibility)
- "What's my leave balance?"   → leave_status  (own data, NOT policy)
- "Who is on leave today?"     → who_on_leave  (company insight)
- "Show pending requests"      → pending_approvals
- "Who approved my leave?"     → last_approval
- "Who earns the most?"        → unknown  (gossip)

Reply with ONLY the intent label, nothing else.

Message: "{message}"
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0),
    )
    intent = response.text.strip().lower()
    valid = {
        "leave_request", "leave_status", "last_approval",
        "payslip", "onboarding", "hr_qa", "greeting",
        "who_on_leave", "pending_approvals", "leave_analytics",
        "unknown",
    }
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
