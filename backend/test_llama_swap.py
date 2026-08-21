#!/usr/bin/env python3
"""
Quick standalone check that OpenRouter's free Meta Llama 3.3 70B endpoint
is wired up correctly.

Usage:
    pip install openai
    OPENROUTER_API_KEY=sk-or-... python3 test_llama_swap.py

Get a free key at https://openrouter.ai/keys — no card required.
Free tier is rate limited (~50 requests/day on a fresh account), which is
fine for this test and for tonight's demo, but keep that ceiling in mind.
"""
import os
import sys

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    print("Set OPENROUTER_API_KEY in your environment first.")
    sys.exit(1)

from openai import OpenAI

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
MODEL = "meta-llama/llama-3.3-70b-instruct:free"

print(f"Testing {MODEL} via OpenRouter...\n")

# 1) Basic generation
resp = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": "You are a helpful HR assistant. Be concise and professional."},
        {"role": "user", "content": "In one short sentence, what is annual leave?"},
    ],
    temperature=0.3,
)
print("generate() check:")
print(" ", resp.choices[0].message.content.strip())
print()

# 2) Intent classification -- mirrors services/llama.py classify_intent()
test_messages = [
    "I want to apply for annual leave next week",
    "what's my leave balance",
    "who is on leave today",
    "hi there",
    "omo this bot sharp die",
]
print("classify_intent() checks:")
for msg in test_messages:
    prompt = f'Classify this Nigerian employee WhatsApp message into exactly one intent label: leave_request, leave_status, last_approval, payslip, onboarding, who_on_leave, pending_approvals, leave_analytics, dept_roster, hr_qa, greeting, casual, or unknown. Reply with ONLY the label.\n\nMessage: "{msg}"'
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    print(f'  "{msg}" -> {r.choices[0].message.content.strip()}')

print("\nIf these look right, the Llama swap is working end to end.")
