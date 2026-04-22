# StaffPilot — CLAUDE.md

AI-powered WhatsApp HR & Operations Bot for Nigerian SMEs.
Built by Kodehaus (Pete / Seyi Fatoki), Abuja Nigeria.

---

## Project location

```
C:\Users\SEYI\FlightDeck\
└── staffpilot\
    ├── backend\      ← FastAPI Python server
    ├── frontend\     ← Next.js 16 dashboard
    └── scripts\      ← seed + ingest utilities
```

---

## Tech stack

| Layer        | Tool                                      |
|--------------|-------------------------------------------|
| Backend      | Python 3.11 / FastAPI                     |
| WhatsApp     | Meta WhatsApp Cloud API (no Twilio)       |
| Database     | Supabase (Postgres + pgvector)            |
| AI           | Gemini 1.5 Flash                          |
| Embeddings   | Google text-embedding-004                 |
| Admin UI     | Next.js 16, Tailwind, TypeScript          |
| Auth         | Supabase Auth (email/password)            |
| Billing      | Paystack                                  |
| Hosting API  | AWS App Runner                            |
| Hosting UI   | Vercel                                    |

---

## Running locally

```bash
# Backend — always activate venv first
C:\Users\SEYI\FlightDeck\.venv\Scripts\Activate.ps1
cd staffpilot\backend
uvicorn main:app --reload --port 8000

# Expose webhook (second terminal)
cd C:\Users\SEYI\FlightDeck
ngrok http 8000

# Frontend (third terminal)
cd staffpilot\frontend
npm run dev
```

---

## Environment variables

### backend\.env
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
GEMINI_API_KEY=AIza...
WHATSAPP_ACCESS_TOKEN=EAAxxxxx
WHATSAPP_PHONE_NUMBER_ID=961583850382092
WHATSAPP_BUSINESS_ACCOUNT_ID=950214971037546
WHATSAPP_VERIFY_TOKEN=staffpilot_hookup
SECRET_KEY=change-this-in-production
FRONTEND_URL=http://localhost:3000
PAYSTACK_SECRET_KEY=
PAYSTACK_WEBHOOK_SECRET=
```

### frontend\.env.local
```
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
NEXT_PUBLIC_DEMO_TENANT_ID=
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
BACKEND_ADMIN_KEY=change-this-in-production
```

---

## Backend structure

```
backend\
├── main.py                   # FastAPI app — registers all routers
├── config.py                 # Settings loaded from .env
├── requirements.txt
├── Dockerfile
├── apprunner.yaml
├── db\
│   ├── supabase_client.py    # get_supabase() — service role client
│   ├── schema.sql            # Run first in Supabase SQL editor
│   ├── auth_billing_schema.sql  # Run second
│   └── storage_setup.sql    # Run third
├── routers\
│   ├── webhook.py            # GET+POST /webhook — Meta WhatsApp
│   ├── admin.py              # /admin/* — employee CRUD, stats, broadcast
│   └── billing.py           # /billing/* — Paystack (commented out for now)
└── services\
    ├── whatsapp.py           # send_message(), parse_webhook(), strip_markdown()
    ├── gemini.py             # generate(), classify_intent(), embed_text()
    ├── session.py            # get_session(), update_session(), clear_session()
    ├── leave.py              # Leave request state machine
    ├── qa.py                 # RAG Q&A — embed question, search pgvector, ask Gemini
    ├── payslip.py            # Payslip fetch and send
    ├── onboarding.py         # New hire checklist flow
    └── gating.py             # Plan feature gating — whatsapp_gate(), check_feature()
```

---

## Frontend structure

```
frontend\
├── app\
│   ├── layout.tsx            # Root layout — wraps with AuthProvider
│   ├── page.tsx              # Redirects / → /dashboard
│   ├── login\
│   │   └── page.tsx          # Login + signup page
│   ├── dashboard\
│   │   ├── layout.tsx        # Dashboard layout with Sidebar
│   │   ├── page.tsx          # Overview — stats + recent leave
│   │   ├── leave\page.tsx    # Leave requests table + approve/reject
│   │   ├── employees\page.tsx  # Employee management + add form
│   │   ├── payslips\page.tsx # Payslip upload + management
│   │   ├── docs\page.tsx     # HR document upload (PDF → RAG)
│   │   └── settings\page.tsx # Tenant config + Paystack billing
│   └── api\
│       ├── auth\setup\route.ts      # Creates tenant + tenant_admin on signup
│       └── billing\subscribe\route.ts  # Paystack subscribe proxy
├── components\
│   ├── layout\Sidebar.tsx    # Nav sidebar — uses useAuth() for company name
│   └── ui\index.tsx          # Card, Button, Badge, StatCard, Spinner, etc.
├── lib\
│   ├── supabase.ts           # Browser Supabase client + all TypeScript types
│   ├── supabase-server.ts    # SSR Supabase client + getSession() + getCurrentTenant()
│   ├── auth-context.tsx      # AuthProvider + useAuth() hook
│   ├── use-tenant.ts         # useTenant() — returns tenantId + plan
│   └── utils.ts              # cn(), formatDate(), formatCurrency(), STATUS_COLORS
└── middleware.ts             # Route protection — redirects unauthenticated users from /dashboard
```

---

## Database schema (Supabase)

Key tables:
- `tenants` — one row per company, `whatsapp_number` = Meta phone_number_id
- `employees` — staff, phone = WhatsApp number with country code (+234...)
- `sessions` — one row per employee, stores current_flow + flow_step + context JSON
- `leave_requests` — leave requests with status pending/approved/rejected
- `hr_documents` — uploaded PDFs per tenant
- `doc_chunks` — chunked PDF content with pgvector embeddings
- `payslips` — monthly payslip records with optional PDF URL
- `tenant_admins` — links Supabase auth users to tenants
- `subscriptions` — Paystack billing state per tenant
- `plan_limits` — starter/growth/enterprise feature flags

---

## WhatsApp bot flows

| Employee says | Flow |
|---|---|
| hi / hello | Greeting with menu |
| leave / "I want leave" | 5-step leave request state machine |
| "how many days sick leave" | RAG Q&A over HR docs |
| payslip | Fetch latest payslip record |
| onboard | New hire checklist |
| APPROVE xxxx | Manager approves leave (managers only) |
| REJECT xxxx | Manager rejects leave (managers only) |

---

## Multi-tenancy

Every incoming WhatsApp message:
1. `msg.to` = Meta `phone_number_id` → looked up in `tenants.whatsapp_number`
2. `msg.from` = employee phone → looked up in `employees.phone` filtered by `tenant_id`
3. ALL DB queries filter by `tenant_id` — never cross-tenant data

---

## Plan gating

```python
# In WhatsApp flows:
gate_msg = whatsapp_gate(employee["tenant_id"], "payslips")
if gate_msg:
    send_message(phone, gate_msg)  # "Requires Growth plan..."
else:
    payslip.handle(employee, text)
```

Plans: starter (₦50k/mo, 30 staff) | growth (₦150k/mo, 150 staff) | enterprise (custom)

---

## Important gotchas

- **Python 3.11** — 3.14 breaks google-generativeai (protobuf incompatibility)
- **venv is at FlightDeck root** `C:\Users\SEYI\FlightDeck\.venv` — always activate before running backend
- **Next.js 14** — standard `middleware.ts` at frontend root, default export named `middleware`
- **Meta phone_number_id** stored in `tenants.whatsapp_number` (not the display number)
- **Employee phones** stored as `+2348XXXXXXXXX` (E.164 with + prefix)
- **Session state** is in Supabase — backend is stateless, works with App Runner
- **Billing router** is commented out in `main.py` until Paystack is configured
- **Meta Business Account** — verification submitted, in review (submitted Mon Apr 21 2026)
- **pgvector** — use `match_doc_chunks()` RPC function for similarity search, always filter by tenant_id

---

## Seeding data

```bash
# Full demo company (Apex Consulting Ltd, 6 employees, leave requests, payslips)
cd scripts
python seed_demo.py
# Prints tenant ID — copy to frontend .env.local as NEXT_PUBLIC_DEMO_TENANT_ID

# Single new client onboarding
python seed_tenant.py --name "Acme Ltd" --number "961583850382092"

# Ingest HR policy PDF
python ingest_docs.py --tenant-id UUID --file handbook.pdf --title "Employee Handbook"
```

---

## Current status (Apr 21 2026)

- [x] Backend boots on Python 3.11
- [x] Meta webhook verified and receiving messages
- [x] WhatsApp messages parsed correctly
- [x] Bot replies blocked — Meta Business Account in review (error 131031)
- [x] Frontend login + signup working
- [x] Supabase auth sending confirmation emails
- [ ] Dashboard pages need page.tsx files populated
- [ ] Supabase schema not yet run (waiting for project slot)
- [ ] Meta verification pending (2 business days)