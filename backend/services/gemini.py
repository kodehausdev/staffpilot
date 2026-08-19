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
        model="gemini-3.6-flash",
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
  NOT: "how do I access my payslip?" → that is hr_qa (process question, not a delivery request)
  NOT: asking about what other people earn.

onboarding
  New employee actively going through first-day document collection.
  Examples: "I'm new, what do I submit?", "onboard me", "how do I register as new staff"
  NOT: "what's my department?" → that is unknown (profile data, not onboarding)
  NOT: "what's your name?" → that is greeting

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

dept_roster
  Asking for the list of employees IN a specific department — a roster/headcount
  request, not the asker's own profile.
  Examples: "who is in the IT department", "list of employees in sales",
            "show me the marketing team", "IT dept employee list", "who's on the ops team"
  NOT: "what's my department?" → that is unknown (own profile data, handled separately)

hr_qa
  Questions about company POLICY, rules, benefits, entitlements, or workplace procedures —
  including HMO, pension, notice period, allowances, disciplinary rules, perks, resignation,
  remote work, misconduct. Also: hypothetical/permissibility questions about leave.
  Examples: "how many sick days am I entitled to?", "what is the notice period?",
            "is half-day leave allowed?", "HMO cover dependants?",
            "I want to japa — what's the process?"

greeting
  Hi, hello, good morning, start, menu.

casual
  Small talk, exclamations/reactions, or meta-commentary about the conversation
  itself — not a real HR request, but not gibberish or off-topic either. Includes
  self-reflective questions answerable from the employee's own role/department
  (not requiring policy docs or other people's data).
  Examples: "wow", "omo", "lol", "hey buds", "so I'm the boss?",
            "you said that earlier", "ok, you were accurate today", "haha nice"
  NOT: "what's my department?" / "what's my name?" → handled by a direct
       hardcoded lookup, not this
  NOT: gossip about other employees, salary fishing, gibberish/nonsense strings
       → that is unknown

unknown
  Off-topic, gossip about other people's salaries, gibberish, slang with no HR meaning.

KEY DISTINCTIONS
================
- "What is the notice period?" → hr_qa  (policy)
- "I want to take sick leave"  → leave_request  (active submission)
- "Is half-day leave allowed?" → hr_qa  (policy/permissibility)
- "How do I access my payslip?" → hr_qa  (process question, NOT a delivery request)
- "Send my payslip"            → payslip  (delivery request)
- "What's my leave balance?"   → leave_status  (own data)
- "What's my department?"      → unknown  (handled separately, not onboarding)
- "What's my name?"            → unknown  (handled separately, not casual)
- "What's your name?" (asking the bot's own name) → greeting
- "Who is on leave today?"     → who_on_leave  (insight)
- "Show pending requests"      → pending_approvals
- "Who approved my leave?"     → last_approval
- "Who earns the most?"        → unknown  (gossip)
- "wow" / "omo" / "so I'm the boss?" → casual  (banter, not a real request)
- "Who is in the IT dept?"     → dept_roster  (headcount, not gossip)

Reply with ONLY the intent label, nothing else.

Message: "{message}"
"""
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0),
    )
    intent = response.text.strip().lower()
    valid = {
        "leave_request", "leave_status", "last_approval",
        "payslip", "onboarding", "hr_qa", "greeting", "casual",
        "who_on_leave", "pending_approvals", "leave_analytics", "dept_roster",
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
