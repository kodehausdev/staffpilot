#!/usr/bin/env python3
"""
Seed demo data into the existing Kodehaus Corp tenant.

Usage:
  python seed_kodehaus.py

Adds:
  - 6 employees across departments
  - 6 leave requests (mix of statuses and types)
  - 9 payslips (3 employees × 3 months)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

# Load backend .env before importing settings
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../backend/.env"))

from db.supabase_client import get_supabase
from datetime import date, timedelta

sb = get_supabase()

# ── Find the existing Kodehaus Corp tenant ────────────────────────────────────
# Pass tenant ID as first arg to skip lookup: python seed_kodehaus.py <tenant_id>
if len(sys.argv) > 1:
    tid = sys.argv[1].strip()
    tenant = sb.table("tenants").select("id, name").eq("id", tid).limit(1).execute().data
    if not tenant:
        print(f"❌  No tenant found with ID: {tid}")
        sys.exit(1)
    tenant = tenant[0]
else:
    print("Looking up Kodehaus Corp tenant...")
    all_tenants = sb.table("tenants").select("id, name").execute().data or []
    tenant = next((t for t in all_tenants if "kodehaus" in t["name"].lower()), None)
    if not tenant:
        print("❌  Tenant not found.")
        print("   Pass your tenant ID directly: python seed_kodehaus.py <tenant_id>")
        sys.exit(1)

tid = tenant["id"]
print(f"  Found: {tenant['name']} (ID: {tid})")

# ── Employees ─────────────────────────────────────────────────────────────────
print("\nAdding employees...")
EMP_DATA = [
    {"name": "Amaka Okonkwo",   "phone": "+2348011100001", "role": "hr_admin",  "department": "HR",          "leave_balance": 20},
    {"name": "Babatunde Lawal", "phone": "+2348022200002", "role": "manager",   "department": "Engineering", "leave_balance": 18},
    {"name": "Chisom Eze",      "phone": "+2348033300003", "role": "staff",     "department": "Engineering", "leave_balance": 15},
    {"name": "Damilola Adeyemi","phone": "+2348044400004", "role": "staff",     "department": "Design",      "leave_balance": 20},
    {"name": "Emeka Nwosu",     "phone": "+2348055500005", "role": "manager",   "department": "Sales",       "leave_balance": 17},
    {"name": "Funke Abiodun",   "phone": "+2348066600006", "role": "staff",     "department": "Sales",       "leave_balance": 14},
]

employees = {}
for e in EMP_DATA:
    # Skip if phone already exists for this tenant
    existing = sb.table("employees").select("id").eq("tenant_id", tid).eq("phone", e["phone"]).execute()
    if existing.data:
        employees[e["name"]] = existing.data[0]
        print(f"  (skipped — already exists) {e['name']}")
        continue
    row = sb.table("employees").insert({**e, "tenant_id": tid}).execute().data[0]
    employees[e["name"]] = row
    print(f"  ✓ {row['name']} — {e['role']}, {e['department']}")

# ── Leave requests ─────────────────────────────────────────────────────────────
print("\nAdding leave requests...")
today = date.today()

LEAVES = [
    {
        "employee_id": employees["Chisom Eze"]["id"],
        "leave_type":  "annual",
        "start_date":  str(today + timedelta(days=5)),
        "end_date":    str(today + timedelta(days=9)),
        "days":        5,
        "reason":      "Family vacation in Lagos",
        "status":      "pending",
    },
    {
        "employee_id": employees["Damilola Adeyemi"]["id"],
        "leave_type":  "sick",
        "start_date":  str(today - timedelta(days=2)),
        "end_date":    str(today - timedelta(days=1)),
        "days":        2,
        "reason":      "Malaria treatment",
        "status":      "approved",
        "manager_id":  employees["Babatunde Lawal"]["id"],
    },
    {
        "employee_id": employees["Funke Abiodun"]["id"],
        "leave_type":  "annual",
        "start_date":  str(today + timedelta(days=12)),
        "end_date":    str(today + timedelta(days=16)),
        "days":        5,
        "reason":      "Sister's wedding",
        "status":      "approved",
        "manager_id":  employees["Emeka Nwosu"]["id"],
    },
    {
        "employee_id": employees["Emeka Nwosu"]["id"],
        "leave_type":  "annual",
        "start_date":  str(today - timedelta(days=15)),
        "end_date":    str(today - timedelta(days=11)),
        "days":        5,
        "reason":      "Personal",
        "status":      "rejected",
        "manager_id":  employees["Amaka Okonkwo"]["id"],
    },
    {
        "employee_id": employees["Chisom Eze"]["id"],
        "leave_type":  "sick",
        "start_date":  str(today - timedelta(days=40)),
        "end_date":    str(today - timedelta(days=38)),
        "days":        3,
        "reason":      "Typhoid fever",
        "status":      "approved",
        "manager_id":  employees["Babatunde Lawal"]["id"],
    },
    {
        "employee_id": employees["Damilola Adeyemi"]["id"],
        "leave_type":  "unpaid",
        "start_date":  str(today + timedelta(days=20)),
        "end_date":    str(today + timedelta(days=21)),
        "days":        2,
        "reason":      "Travelling to Abuja for visa appointment",
        "status":      "pending",
    },
]

for leave in LEAVES:
    sb.table("leave_requests").insert({**leave, "tenant_id": tid}).execute()
    print(f"  ✓ {leave['leave_type'].title()} — {leave['status']}")

# ── Payslips ──────────────────────────────────────────────────────────────────
print("\nAdding payslips...")

PAYSLIP_EMPS = [
    {"emp": employees["Chisom Eze"],       "gross": 350_000},
    {"emp": employees["Damilola Adeyemi"], "gross": 300_000},
    {"emp": employees["Funke Abiodun"],    "gross": 280_000},
]

MONTHS = [
    ("March 2025", 2025),
    ("February 2025", 2025),
    ("January 2025", 2025),
]

for month_str, year in MONTHS:
    for item in PAYSLIP_EMPS:
        emp   = item["emp"]
        gross = item["gross"]
        tax     = round(gross * 0.125)   # 12.5% PAYE
        pension = round(gross * 0.08)    # 8% pension
        net     = gross - tax - pension

        # Skip if duplicate (unique constraint on employee_id + month)
        existing = sb.table("payslips").select("id").eq("employee_id", emp["id"]).eq("month", month_str).execute()
        if existing.data:
            print(f"  (skipped — exists) {emp['name']} — {month_str}")
            continue

        sb.table("payslips").insert({
            "employee_id": emp["id"],
            "tenant_id":   tid,
            "month":       month_str,
            "year":        year,
            "gross_pay":   gross,
            "net_pay":     net,
            "deductions":  {"paye_tax": tax, "pension": pension},
        }).execute()
        print(f"  ✓ {emp['name']} — {month_str} (₦{net:,} net)")

print(f"\n✅  Seed complete for {tenant['name']}!")
