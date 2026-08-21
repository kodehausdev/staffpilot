"""
Llama 3.3 70B service — Meta's model, served via OpenRouter.

Three providers down before landing here:
- Groq deprecated and fully removed llama-3.3-70b-versatile in mid-2026,
  replacing it with non-Meta models (openai/gpt-oss-120b, qwen).
- Together AI serves the real model but requires a funded account.
- OpenRouter's free tier (meta-llama/llama-3.3-70b-instruct:free) was
  itself delisted in early August 2026 -- confirmed via a live 404 telling
  us to use the paid slug instead.

Landed on OpenRouter's paid endpoint: meta-llama/llama-3.3-70b-instruct.
Same model, pay-as-you-go pricing (roughly $0.10-$1/M tokens depending on
which upstream provider OpenRouter routes to) -- a $5 top-up at
openrouter.ai/credits comfortably covers a full night of testing plus a
live demo. Uses the OpenAI SDK pointed at OpenRouter's base URL, since
OpenRouter is OpenAI-compatible.
"""
from openai import OpenAI
from config import get_settings

_client: OpenAI | None = None
MODEL = "meta-llama/llama-3.3-70b-instruct"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=get_settings().openrouter_api_key,
        )
    return _client


def generate(prompt: str, system: str = None, temperature: float = 0.3) -> str:
    """Generate a response from Meta's Llama 3.3 70B via OpenRouter."""
    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system or "You are a helpful HR assistant. Be concise and professional."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


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
  Examples: "who is on leave", "who is not in office", "who is absent today", "who dey go leave", "who is out of office", " who is on vacation", "I fit see who is on leave today?", "who is on leave today", "who is on leave this week", "who is on leave this month"

pending_approvals
  Asking to see pending / unactioned leave requests.
  Examples: "show pending requests", "any pending leave", "who hasn't been approved",
            "pending approvals", "leave requests waiting", "omo, show me pending leave requests", "who is waiting for approval"

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
  Also: the employee describing harassment, inappropriate advances, unsafe treatment, or
  ethical pressure from a manager/colleague and asking what they should do — this always
  routes here (the grievance policy and EAP details apply), never to unknown.
  Examples: "how many sick days am I entitled to?", "what is the notice period?",
            "is half-day leave allowed?", "HMO cover dependants?",
            "I want to japa — what's the process?",
            "my manager is pressuring me for something inappropriate, what do I do?",
            "my supervisor keeps making advances at me", "is it safe to report my manager?"

greeting
  Hi, hello, good morning, start, menu, wassup, hey, howdy, good evening, good afternoon, greetings, welcome, salutations,
  or any other friendly opening or closing message. Also: asking the bot's own name.

casual
  Small talk, exclamations/reactions, or meta-commentary about the conversation
  itself — not a real HR request, but not gibberish or off-topic either. Includes
  self-reflective questions answerable from the employee's own role/department
  (not requiring policy docs or other people's data). Also: short follow-up
  questions asking what the bot itself can do or help with.
  Examples: "wow", "omo", "lol", "hey buds", "so I'm the boss?",
            "you said that earlier", "ok, you were accurate today", "haha nice",
            "what can you share?", "what else can you do?"
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
- "Who approved my leave?"     → last_approval (own data)
- "Who earns the most?"        → unknown  (gossip) 
- "wow" / "omo" / "so I'm the boss?" → casual  (banter, not a real request) 
- "Who is in the IT dept?"     → dept_roster  (headcount, not gossip)- "How many sick days am I entitled to?" → hr_qa  (policy)
- "My manager is harassing me, what do I do?" → hr_qa  (grievance/EAP policy applies)
- "What can you share?" / "What else can you do?" → casual  (meta-question about the bot) 
- "I want to japa — what's the process?" → hr_qa  (policy, not a leave request)
- "I want to take annual leave next week" → leave_request  (active submission)
- "I want to take annual leave next week, but my manager is pressuring me to work" → hr_qa  (grievance/EAP policy applies)
- "I want to take annual leave next week, but my manager is pressuring me to work, and I want to know if that's allowed" → hr_qa  (policy/permissibility)
- "My supervisor keeps making advances at me, what should I do?" → hr_qa  (grievance/EAP policy applies)
- "My supervisor keeps making advances at me, and I want to know if that's allowed" → hr_qa  (policy/permissibility)
- "Should I report my manager for harassment?" → hr_qa  (grievance/EAP policy applies)
- "Should I report my manager for harassment, and what is the process?" → hr_qa  (grievance/EAP policy applies)
- "What are the benefits of the company's HMO?" → hr_qa  (policy, not a delivery request)
- "What are the benefits of the company's HMO, and how do I access them?" → hr_qa  (policy, not a delivery request)
- "Is it safe to report my manager for harassment?" → hr_qa  (grievance/EAP policy applies)
- "What company policies apply to remote work?" → hr_qa  (policy, not a delivery request)
- "What is the name of this bot?" → greeting  (asking the bot's own name)
- "What is the name of this bot, and what can it do?" → casual  (meta-question about the bot)
- "what is the notice period for resignation?" → hr_qa  (policy)
- "whos the founder of this company?" → unknown  (not HR-related)
- "The company is planning a team-building event next month, what are the details?" → hr_qa  (policy/procedure)
- "what company do i work for?" → hr_qa  (policy/procedure)



Reply with ONLY the intent label, nothing else.

Message: "{message}"
"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    intent = response.choices[0].message.content.strip().lower()
    valid = {
        "leave_request", "leave_status", "last_approval",
        "payslip", "onboarding", "hr_qa", "greeting", "casual",
        "who_on_leave", "pending_approvals", "leave_analytics", "dept_roster",
        "unknown",
    }
    return intent if intent in valid else "unknown"
