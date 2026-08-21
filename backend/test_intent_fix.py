#!/usr/bin/env python3
"""
Checks the specific messages that were falling through to the generic
fallback -- confirms the classify_intent prompt fix routes them correctly.

Usage:
    OPENROUTER_API_KEY=sk-or-... python3 test_intent_fix.py
"""
import os
import sys

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    print("Set OPENROUTER_API_KEY in your environment first.")
    sys.exit(1)

sys.path.insert(0, ".")
import services.llama as llama

cases = [
    ("my manager dey toast me, what do I do?", "hr_qa"),
    ("my manager dey toast me, should I let her hit and get promoted", "hr_qa"),
    ("what can you share?", "casual"),
    ("Cord, why does Tolu earn more than me? we have same role", "unknown"),
    ("what is it with kodehaus", "unknown"),
]

print("Testing classify_intent() against the messages that broke earlier:\n")
all_pass = True
for message, expected in cases:
    got = llama.classify_intent(message)
    ok = got == expected
    all_pass = all_pass and ok
    mark = "PASS" if ok else "FAIL"
    print(f'  [{mark}] "{message}"')
    print(f'         expected: {expected}  |  got: {got}')

print("\nAll passed." if all_pass else "\nSome mismatches -- check the prompt further.")
