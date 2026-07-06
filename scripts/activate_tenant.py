#!/usr/bin/env python3
"""
Assign a Meta phone_number_id to an existing (pending) tenant, and list
tenants still waiting on activation.

Usage:
  # See who's waiting
  python activate_tenant.py --pending

  # Activate one (phone_number_id is the Meta Graph ID, not the display number)
  python activate_tenant.py --tenant-id UUID --number 961583850382092

  # Or look up by company name if you don't have the UUID handy
  python activate_tenant.py --name "Acme Ltd" --number 961583850382092
"""
import argparse
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 console can't print the emoji below

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../backend")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)  # config.py's env_file=".env" is resolved against cwd, not this file

from db.supabase_client import get_supabase


def list_pending() -> None:
    sb = get_supabase()
    result = (
        sb.table("tenants")
        .select("id, name, created_at")
        .is_("whatsapp_number", "null")
        .order("created_at")
        .execute()
    )
    rows = result.data or []
    if not rows:
        print("✅ No tenants waiting on WhatsApp activation.")
        return
    print(f"⏳ {len(rows)} tenant(s) waiting on activation:\n")
    for t in rows:
        print(f"   {t['name']:<30} {t['id']}   signed up {t['created_at']}")


def activate(tenant_id: str | None, name: str | None, number: str) -> None:
    sb = get_supabase()
    query = sb.table("tenants").update({"whatsapp_number": number})
    if tenant_id:
        query = query.eq("id", tenant_id)
    else:
        query = query.eq("name", name)
    result = query.execute()

    if not result.data:
        print(f"❌ No tenant matched ({tenant_id or name}). Nothing updated.")
        sys.exit(1)

    tenant = result.data[0]
    print(f"✅ Activated: {tenant['name']} ({tenant['id']})")
    print(f"   phone_number_id: {number}")
    print("   Reminder: confirm the app is subscribed to this WABA's webhooks")
    print("   (POST /{waba_id}/subscribed_apps) or messages won't reach the bot.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pending", action="store_true", help="List tenants awaiting activation")
    parser.add_argument("--tenant-id", help="Tenant UUID to activate")
    parser.add_argument("--name", help="Tenant company name to activate (if UUID not on hand)")
    parser.add_argument("--number", help="Meta phone_number_id to assign")
    args = parser.parse_args()

    if args.pending:
        list_pending()
    elif args.number and (args.tenant_id or args.name):
        activate(args.tenant_id, args.name, args.number)
    else:
        parser.error("Pass --pending to list, or --number with --tenant-id/--name to activate.")
