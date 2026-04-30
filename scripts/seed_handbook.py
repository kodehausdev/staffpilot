#!/usr/bin/env python3
"""
Seed the Apex Consulting employee handbook directly into Supabase.
No PDF needed — text is chunked and embedded in-place.

Usage:
  python seed_handbook.py --tenant-id <uuid>

Tip: run seed_demo.py first to get a tenant ID, then run this.
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from db.supabase_client import get_supabase
from services.gemini import embed_document_chunk

CHUNK_SIZE    = 800
CHUNK_OVERLAP = 100

# ── Handbook content ──────────────────────────────────────────────────────────
# Written as plain text sections so the RAG can answer natural WhatsApp questions
# like "do I have HMO?", "can I work from home?", "when do I get my bonus?"

HANDBOOK = """
APEX CONSULTING LTD — EMPLOYEE HANDBOOK 2026
Welcome. This handbook covers your rights, benefits, and perks as an Apex employee.
Please read it fully — most people are surprised by what they're entitled to.


SECTION 1: LEAVE ENTITLEMENTS

Annual Leave
Every confirmed employee is entitled to 20 working days of paid annual leave per year.
Leave days not taken by December 31 can be carried forward for up to 6 months into the next year.
Leave requests must be submitted at least 5 working days in advance through the HR system or WhatsApp bot.

Sick Leave
You are entitled to 12 days of paid sick leave per year.
A medical certificate is required for any absence longer than 2 consecutive days.
Sick leave does not carry forward — it resets on January 1 each year.

Maternity Leave
Female employees are entitled to 3 months (12 weeks) of fully paid maternity leave.
You may begin maternity leave up to 4 weeks before your expected delivery date.
Your job and salary level are protected for the full period of maternity leave.

Paternity Leave
Male employees are entitled to 5 working days of fully paid paternity leave upon the birth of a child.
This must be taken within 4 weeks of the child's birth.

Compassionate Leave
If an immediate family member (parent, spouse, child, sibling) passes away, you are entitled to 3 working days of paid compassionate leave.
For extended family, 1 day is granted.

Exam and Study Leave
Employees sitting professional exams (ICAN, ACCA, CIPM, PMP, etc.) are entitled to 3 days paid leave per exam sitting.
Submit your exam timetable to HR at least 2 weeks in advance.

Birthday Leave
You get one day off on your birthday — or the nearest working day if your birthday falls on a weekend or public holiday.
No application required. Just notify your line manager.


SECTION 2: HEALTH — HMO COVERAGE

Apex Consulting provides comprehensive HMO (Health Maintenance Organisation) coverage for all confirmed employees.

What is covered?
- Outpatient consultations at any accredited clinic or hospital
- Inpatient (admission) care including surgery and specialist referrals
- Prescription drugs (covered up to ₦50,000 per year)
- Ante-natal care (for pregnant employees and spouses)
- Dental: scaling, polishing, 2 fillings per year
- Optical: eye test + one pair of glasses or contact lenses per year
- Emergency care 24/7 at any government or approved private hospital

Who is covered?
Your HMO plan covers you plus up to 2 dependants (spouse and/or children under 18).
Additional dependants can be added at a subsidised rate — speak to HR.

How to access your HMO
Your HMO card will be provided within 30 days of your start date.
Present your card at any accredited hospital or clinic.
For emergencies, go to any A&E — you will be covered. Show your staff ID if you do not have your card.
HMO provider: Reliance HMO. Helpline: 0700-RELIANCE (0700-735-42623).

What is NOT covered?
Cosmetic procedures, fertility treatments, eye surgery (LASIK), and pre-existing conditions in the first 6 months.


SECTION 3: PENSION (PFA CONTRIBUTIONS)

Every employee is enrolled in the Contributory Pension Scheme as required by Nigerian law.

How it works:
- Apex contributes 10% of your monthly basic salary to your Pension Fund Administrator (PFA)
- You contribute 8% of your monthly basic salary (deducted from payroll automatically)
- Total pension contribution = 18% of your basic salary every month

Choosing your PFA
You have the right to choose your own PFA. Popular options include Stanbic IBTC, ARM Pension, Leadway Pensure, and AXA Mansard.
If you already have a Retirement Savings Account (RSA) from a previous employer, simply provide your RSA PIN to HR.

When can you access it?
You can access your pension savings at age 50, upon retirement, or if you are out of employment for more than 4 months.
You can also access 25% of your pension balance to pay for a mortgage.

Check your balance
Download your PFA's app or log onto their website using your RSA PIN to check your balance anytime.


SECTION 4: GROUP LIFE INSURANCE

Apex Consulting provides group life insurance for all employees at no cost to you.

Coverage amount: 3× your annual gross salary.
If the unthinkable happens, your nominated beneficiary will receive this lump sum payment.

What you need to do:
Complete the beneficiary nomination form with HR. If you have not done this yet, please do so immediately.
You can nominate any person (spouse, parent, child, sibling) as your beneficiary.
You may update your beneficiary at any time by notifying HR in writing.


SECTION 5: PERFORMANCE BONUS

Annual Bonus
Apex pays a performance bonus every January based on the previous year's performance review.
Bonus range: 5% to 15% of your annual gross salary, depending on your performance rating.
Rating scale: Outstanding (15%), Exceeds Expectations (12%), Meets Expectations (8%), Below Expectations (5%).

Mid-year incentives
High-performing teams may receive a mid-year incentive payment in July at management's discretion.
These are announced quarterly based on company revenue targets.


SECTION 6: 13TH MONTH SALARY (CHRISTMAS BONUS)

Every employee receives a 13th month salary paid in December, before Christmas.
This is equal to one month's basic salary.
Employees who joined mid-year receive a pro-rated 13th month based on months worked.
For example, if you joined in July, you will receive 6/12 of your monthly basic salary.
The 13th month is subject to the usual tax and pension deductions.


SECTION 7: TRAINING AND DEVELOPMENT

Apex invests in your growth. Every employee has a training budget of ₦200,000 per year.

This can be used for:
- Professional certifications (ICAN, ACCA, PMP, CIPM, AWS, Google, Microsoft, etc.)
- Online courses (Coursera, Udemy, LinkedIn Learning)
- Industry conferences and workshops
- Books and learning materials

How to access your training budget:
Submit a training request form to your line manager and HR at least 2 weeks before the course begins.
Once approved, Apex will pay directly or reimburse you within 7 working days of submitting receipts.
Unused training budget does not carry forward to the next year.


SECTION 8: REMOTE WORK POLICY

Eligible employees may work from home up to 2 days per week.
Eligibility: confirmed employees who have completed at least 6 months with the company.

Requirements for remote work:
- Reliable internet connection (minimum 5 Mbps)
- A quiet, dedicated workspace
- Available on Slack/Teams during core hours: 9am–5pm
- Attendance at all in-person meetings when required

Remote work is a privilege, not a right. It may be suspended if performance or availability is affected.
Inform your line manager at least 24 hours in advance of a remote day.


SECTION 9: STAFF LOAN / SALARY ADVANCE

Apex offers interest-free salary advances to confirmed employees.

How much can I borrow?
Up to 50% of your monthly gross salary as an advance against the current month.
For larger needs, a staff loan of up to 3× monthly gross salary is available for emergencies.

Repayment:
Salary advance: deducted in full from the following month's salary.
Staff loan: repaid over 3 to 6 months via automatic payroll deductions.

Eligibility:
You must have completed at least 3 months of confirmed employment.
You must not have any existing outstanding loan balance.

To apply: speak to HR or message the HR bot on WhatsApp.


SECTION 10: TRANSPORT ALLOWANCE

All employees receive a monthly transport allowance of ₦15,000, included in your gross salary package.

Field and client-facing staff receive an additional ₦10,000 field allowance per month.

If you use your personal vehicle for official work trips, you are reimbursed at ₦50 per kilometre.
Submit a mileage claim form to Finance within 5 working days of the trip.


SECTION 11: MEAL SUBSIDY

Office staff
The Apex staff canteen is subsidised. Hot meals are available for ₦500 (market rate ₦2,500).
The canteen is open Monday to Friday, 12pm–2pm.

Remote and WFH staff
You receive a ₦3,000 monthly meal voucher, credited to your Opay or Paystack wallet by the 5th of each month.

This benefit is available to all confirmed employees.


SECTION 12: COMPANY ASSETS AND TECH PERKS

Laptop
All employees are issued a company laptop within their first week.
The laptop remains company property and must be returned upon resignation or termination.
You are responsible for keeping it safe and reporting any damage immediately.

Phone Allowance
Senior managers and above receive a monthly phone/data allowance of ₦10,000.
All other staff receive ₦5,000 monthly data allowance, paid with salary.

Internet at home
Remote-eligible employees receive a ₦8,000 monthly internet subsidy from month 1.


SECTION 13: EMPLOYEE ASSISTANCE PROGRAMME (EAP)

Apex cares about your mental health.
All employees have access to free, confidential counselling through our Employee Assistance Programme.
Up to 6 sessions per year with a licensed therapist or counsellor — fully covered by the company.

How to access:
Contact HR to be referred. Everything is completely confidential.
You can also call the EAP helpline directly: 0800-APEX-EAP (toll-free, available 24/7).

Topics covered: stress, anxiety, relationship issues, grief, financial stress, work-life balance.


SECTION 14: WORK ANNIVERSARY RECOGNITION

1 year:    ₦20,000 gift card + personalised letter from the CEO
3 years:   ₦50,000 gift card + extra 3 days annual leave for the year
5 years:   ₦100,000 gift card + 1-week vacation leave bonus + name on the Wall of Honour
10 years:  ₦250,000 gift card + additional 5 days annual leave permanently added to your entitlement


SECTION 15: HOW TO ASK HR QUESTIONS

You do not need to come to the HR office for most requests. Use the StaffPilot WhatsApp bot — just message this number and ask anything:
- Check your leave balance
- Request leave
- Ask about your benefits
- Get your payslip
- Ask any HR policy question

The bot is available 24/7. Your HR manager is also available Monday to Friday, 8am–6pm.
""".strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        end   = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if len(chunk) > 50:
            chunks.append(chunk)
        start = end - CHUNK_OVERLAP
    return chunks


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID from Supabase")
    args = parser.parse_args()

    sb    = get_supabase()
    tid   = args.tenant_id
    title = "Apex Consulting Employee Handbook 2026"

    # Delete any existing handbook for a clean re-seed
    existing = sb.table("hr_documents").select("id").eq("tenant_id", tid).eq("title", title).execute()
    for doc in (existing.data or []):
        sb.table("hr_documents").delete().eq("id", doc["id"]).execute()
        print(f"  Deleted old handbook: {doc['id']}")

    chunks = chunk_text(HANDBOOK)
    print(f"📄 {title}")
    print(f"   {len(HANDBOOK):,} characters → {len(chunks)} chunks")

    doc_res = sb.table("hr_documents").insert({
        "tenant_id": tid,
        "title":     title,
        "file_path": None,
    }).execute()
    doc_id = doc_res.data[0]["id"]
    print(f"   Document ID: {doc_id}")

    for i, chunk in enumerate(chunks):
        print(f"   Embedding chunk {i+1}/{len(chunks)}…", end="\r")
        embedding = embed_document_chunk(chunk)
        sb.table("doc_chunks").insert({
            "tenant_id":   tid,
            "document_id": doc_id,
            "content":     chunk,
            "embedding":   embedding,
            "chunk_index": i,
        }).execute()

    print(f"\n✅ Handbook seeded — {len(chunks)} chunks ready for WhatsApp Q&A")
    print()
    print("Test questions to try on the bot:")
    print("  • do I have HMO?")
    print("  • how many days annual leave do I get?")
    print("  • can I work from home?")
    print("  • when do I get my Christmas bonus?")
    print("  • what happens to my pension?")
    print("  • can I get a salary advance?")
    print("  • is there a training budget?")
    print("  • do I get a birthday off?")
    print("  • what is covered by my HMO?")
    print("  • how much group life insurance do I have?")


if __name__ == "__main__":
    main()
