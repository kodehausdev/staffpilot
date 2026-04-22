#!/usr/bin/env python3
"""
Seed a new company (tenant) and their employees.

Usage:
  python seed_tenant.py --name "Acme Ltd" --number "whatsapp:+2348XXXXXXXXX"
"""
import argparse
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from db.supabase_client import get_supabase


def seed_tenant(name: str, whatsapp_number: str) -> str:
    sb = get_supabase()
    result = sb.table("tenants").insert({
        "name": name,
        "whatsapp_number": whatsapp_number,
        "plan": "starter",
    }).execute()
    tenant_id = result.data[0]["id"]
    print(f"✅ Tenant created: {name}")
    print(f"   ID: {tenant_id}")
    return tenant_id


def seed_employees(tenant_id: str, employees: list[dict]) -> None:
    sb = get_supabase()
    for emp in employees:
        emp["tenant_id"] = tenant_id
        result = sb.table("employees").upsert(emp, on_conflict="tenant_id,phone").execute()
        print(f"   ✅ Employee: {emp.get('name') or emp['phone']} ({emp.get('role','staff')})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Company name")
    parser.add_argument("--number", required=True, help="Twilio WhatsApp number")
    parser.add_argument(
        "--employees",
        help="JSON array of employee objects with phone, name, role fields",
        default="[]"
    )
    args = parser.parse_args()

    tenant_id = seed_tenant(args.name, args.number)

    employees = json.loads(args.employees)
    if employees:
        print(f"\nSeeding {len(employees)} employees...")
        seed_employees(tenant_id, employees)

    print(f"\n🚀 Ready! Tenant ID: {tenant_id}")
    print(f"   Next: run ingest_docs.py to upload HR policy documents")
