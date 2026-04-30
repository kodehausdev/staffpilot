#!/usr/bin/env python3
"""
Seed a full demo company — use this to prep for client demos in Abuja.

Usage:
  python seed_demo.py

Creates:
  - 1 tenant: "Apex Consulting Ltd"
  - 6 employees across departments
  - 5 leave requests (mix of statuses)
  - 3 payslip records
"""
import sys, os

_backend_dir = os.path.join(os.path.dirname(__file__), "../backend")
sys.path.insert(0, _backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(_backend_dir, ".env"))

from db.supabase_client import get_supabase
from datetime import date, timedelta
import json

sb = get_supabase()

# ── Tenant ────────────────────────────────────────────────────────────────────
print("Creating tenant...")
tenant = sb.table("tenants").insert({
    "name":             "Apex Consulting Ltd",
    "whatsapp_number":  "whatsapp:+14155550100",
    "plan":             "growth",
}).execute().data[0]
tid = tenant["id"]
print(f"  Tenant ID: {tid}")

# ── Employees ─────────────────────────────────────────────────────────────────
print("Creating employees...")
EMP_DATA = [
    {"name": "Chidi Okeke",     "phone": "+2348011111111", "role": "hr_admin",  "department": "HR",        "leave_balance": 20},
    {"name": "Aisha Bello",     "phone": "+2348022222222", "role": "manager",   "department": "Finance",   "leave_balance": 18},
    {"name": "Tunde Adeyemi",   "phone": "+2348033333333", "role": "staff",     "department": "Finance",   "leave_balance": 15},
    {"name": "Ngozi Eze",       "phone": "+2348044444444", "role": "staff",     "department": "IT",        "leave_balance": 20},
    {"name": "Emeka Okonkwo",   "phone": "+2348055555555", "role": "staff",     "department": "IT",        "leave_balance": 12},
    {"name": "Fatima Usman",    "phone": "+2348066666666", "role": "manager",   "department": "Operations","leave_balance": 19},
]

employees = []
for e in EMP_DATA:
    row = sb.table("employees").insert({**e, "tenant_id": tid}).execute().data[0]
    employees.append(row)
    print(f"  {row['name']} ({row['role']})")

emp_map = {e["name"]: e for e in employees}

# ── Leave requests ─────────────────────────────────────────────────────────────
print("Creating leave requests...")
today = date.today()

LEAVES = [
    {
        "employee_id": emp_map["Tunde Adeyemi"]["id"],
        "leave_type": "annual",
        "start_date": str(today + timedelta(days=7)),
        "end_date":   str(today + timedelta(days=11)),
        "days": 5,
        "reason": "Family vacation",
        "status": "pending",
    },
    {
        "employee_id": emp_map["Ngozi Eze"]["id"],
        "leave_type": "sick",
        "start_date": str(today - timedelta(days=3)),
        "end_date":   str(today - timedelta(days=1)),
        "days": 3,
        "reason": "Malaria treatment",
        "status": "approved",
        "manager_id": emp_map["Chidi Okeke"]["id"],
    },
    {
        "employee_id": emp_map["Emeka Okonkwo"]["id"],
        "leave_type": "annual",
        "start_date": str(today + timedelta(days=14)),
        "end_date":   str(today + timedelta(days=18)),
        "days": 5,
        "reason": "Wedding",
        "status": "approved",
        "manager_id": emp_map["Aisha Bello"]["id"],
    },
    {
        "employee_id": emp_map["Fatima Usman"]["id"],
        "leave_type": "annual",
        "start_date": str(today - timedelta(days=10)),
        "end_date":   str(today - timedelta(days=6)),
        "days": 5,
        "reason": "Personal",
        "status": "rejected",
        "manager_id": emp_map["Chidi Okeke"]["id"],
    },
    {
        "employee_id": emp_map["Tunde Adeyemi"]["id"],
        "leave_type": "sick",
        "start_date": str(today - timedelta(days=30)),
        "end_date":   str(today - timedelta(days=29)),
        "days": 2,
        "reason": "Flu",
        "status": "approved",
        "manager_id": emp_map["Aisha Bello"]["id"],
    },
]

for leave in LEAVES:
    sb.table("leave_requests").insert({**leave, "tenant_id": tid}).execute()
    print(f"  {leave['leave_type']} leave — {leave['status']}")

# ── Payslips ──────────────────────────────────────────────────────────────────
print("Creating payslips...")
MONTHS = ["March 2025", "February 2025", "January 2025"]
PAYSLIP_EMPS = [emp_map["Tunde Adeyemi"], emp_map["Ngozi Eze"], emp_map["Emeka Okonkwo"]]

for month in MONTHS:
    for emp in PAYSLIP_EMPS:
        gross = 450_000
        tax   = 56_250   # 12.5%
        pension = 22_500  # 5%
        net   = gross - tax - pension
        sb.table("payslips").insert({
            "employee_id": emp["id"],
            "tenant_id": tid,
            "month": month,
            "year": int(month.split()[-1]),
            "gross_pay": gross,
            "net_pay": net,
            "deductions": {"tax": tax, "pension": pension},
        }).execute()
    print(f"  Payslips for {month}")

print(f"\n✅ Demo seed complete!")
print(f"   Tenant ID: {tid}")
print(f"   Copy this to NEXT_PUBLIC_DEMO_TENANT_ID in frontend/.env.local")
