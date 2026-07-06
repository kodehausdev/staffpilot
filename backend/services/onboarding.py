"""
Onboarding flow for new hires.
Guides them through document submission checklist via WhatsApp.
"""
from services.session import update_session, clear_session
from services.whatsapp import send_message

CHECKLIST = [
    ("nin",         "National Identification Number (NIN)"),
    ("account",     "Bank account number + bank name"),
    ("next_of_kin", "Next of kin name + phone number"),
    ("guarantor",   "Guarantor name + phone number"),
    ("address",     "Residential address"),
]

STEPS = [key for key, _ in CHECKLIST]

WELCOME = (
    "👋 Welcome to the team! I'm your onboarding assistant.\n\n"
    "I'll collect some information to complete your file. "
    "You can type 'skip' for any item and provide it later.\n\n"
    "Let's start:"
)


def handle(employee: dict, session: dict, message: str) -> None:
    step = session.get("flow_step")
    ctx  = session.get("context") or {}
    phone = employee["phone"]

    if step is None or step == "start":
        _begin(employee)
        return

    # Save previous answer
    if step in STEPS:
        value = None if message.strip().lower() == "skip" else message.strip()
        ctx[step] = value
        update_session(employee["id"], context=ctx)

    # Advance to next step
    current_idx = STEPS.index(step) if step in STEPS else -1
    next_idx = current_idx + 1

    if next_idx < len(STEPS):
        next_key, next_label = CHECKLIST[next_idx]
        update_session(employee["id"], step=next_key)
        send_message(phone, f"Got it ✓\n\nNext: {next_label}\n(or type 'skip')", tenant_id=employee["tenant_id"])
    else:
        _complete(employee, ctx)


def _begin(employee: dict) -> None:
    first_key, first_label = CHECKLIST[0]
    update_session(
        employee["id"],
        flow="onboarding",
        step=first_key,
        context={},
    )
    send_message(
        employee["phone"],
        f"{WELCOME}\n\n{first_label}\n(or type 'skip')",
        tenant_id=employee["tenant_id"]
    )


def _complete(employee: dict, ctx: dict) -> None:
    phone = employee["phone"]
    provided = [label for key, label in CHECKLIST if ctx.get(key)]
    skipped  = [label for key, label in CHECKLIST if not ctx.get(key)]

    summary = f"✅ Onboarding info collected!\n\nProvided ({len(provided)}):\n"
    for item in provided:
        summary += f"  • {item}\n"

    if skipped:
        summary += f"\nPending ({len(skipped)}):\n"
        for item in skipped:
            summary += f"  • {item}\n"
        summary += "\nPlease send the pending items to your HR admin directly."

    summary += "\nWelcome aboard! 🎉"
    send_message(phone, summary, tenant_id=employee["tenant_id"])

    # TODO: notify HR admin with collected data
    clear_session(employee["id"])
