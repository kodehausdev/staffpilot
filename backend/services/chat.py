"""
Casual chat lane — small talk, exclamations, meta-commentary about the
conversation, or self-reflective questions about the employee's own role.
No RAG, no DB lookups beyond the employee's own basic profile fields already
in hand. This exists so banter doesn't fall through to the flat capability
list every time — that's what made the bot look "stuck" on anything that
wasn't a recognized command.
"""
from services.gemini import generate
from services.whatsapp import send_message
from services.session import update_context
from services.qa import _sanitize_response


def handle(employee: dict, text: str, last_message: str | None = None) -> None:
    phone      = employee["phone"]
    tenant_id  = employee["tenant_id"]
    first_name = (employee.get("name") or "").split()[0] or "there"
    role       = (employee.get("role") or "staff").replace("_", " ").title()
    department = employee.get("department") or "unassigned"
    prior_context = f"\nTheir previous message (for context only, do not repeat it): {last_message}" if last_message else ""

    prompt = f"""You are CordHR — an HR assistant for a Nigerian company, communicating via WhatsApp.
This message is small talk or a casual aside, not a real HR request.

{first_name}'s profile: {role}, {department} department.
{prior_context}

VOICE: Calm, modern, friendly, brief. Nigerian WhatsApp register is normal here
(e.g. "omo" is a casual exclamation, not gibberish) — match their energy, don't
be stiff. One emoji max, only if it fits. Keep it to 1-2 lines.

If their message is a laugh or joke (lol, lmao, 😂, haha, etc.), join in briefly
— then close with a light, natural nudge back to helpfulness, e.g. "Alright
alright 😂 anything else I can help with?" Don't leave a joke hanging with
nothing after it. Don't bolt this nudge onto every casual reply though — only
after humor, where the conversation actually needs a way back.

HARD RULES:
1. Don't invent company data, policy details, salary figures, or other
   employees' information — the only facts you have are {first_name}'s own
   name, role, and department shown above.
2. If they ask something that actually needs real data (leave balance,
   payslip, policy), don't guess — nudge them to ask it directly.
3. You are CordHR. Never refer to yourself as StaffPilot or any other name.

{first_name}'s message: {text}

Reply:"""

    answer = generate(prompt, temperature=0.5)
    answer = _sanitize_response(answer)
    send_message(phone, answer, tenant_id=tenant_id)
    update_context(employee["id"], "last_message", text)
