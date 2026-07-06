# CordHR — CLAUDE.md

AI-powered WhatsApp HR & Operations Bot for Nigerian SMEs.
Brand: CordHR (pronounced "cordial") by Optipropose Studio, Abuja Nigeria.

---

## Project location

```
C:\Users\SEYI\FlightDeck\
└── staffpilot\
    ├── backend\      ← FastAPI Python server
    ├── frontend\     ← Next.js 16 dashboard
    └── scripts\      ← seed + ingest + tenant-activation utilities
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
| Hosting API  | Railway (auto-deploys from `main`)        |
| Hosting UI   | Vercel (auto-deploys from `main`)         |

**Production URLs:**
- Frontend: `https://cordhr.optipropose.com` (custom domain; `https://codhr-cordial.vercel.app` still resolves too — both point at the same Vercel deployment)
- Backend: `https://staffpilot-production-579d.up.railway.app`

---

## Running locally

```bash
# Backend — always activate venv first
C:\Users\SEYI\FlightDeck\.venv\Scripts\Activate.ps1
cd staffpilot\backend
uvicorn main:app --reload --port 8000

# Expose webhook (second terminal) — only needed if testing WhatsApp
# against your local backend instead of Railway
cd C:\Users\SEYI\FlightDeck
ngrok http 8000

# Frontend (third terminal)
cd staffpilot\frontend
npm run dev
```

**Note:** `.env` changes require a full restart of `uvicorn`, not just a file
save — `config.py` caches `Settings()` with `@lru_cache()`, and `--reload`
only watches `.py` files.

---

## Environment variables

### backend\.env
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
GEMINI_API_KEY=AIza...
WHATSAPP_ACCESS_TOKEN=EAAxxxxx           # system-user token — see "WhatsApp activation" below
WHATSAPP_PHONE_NUMBER_ID=<phone_number_id for the global/default tenant>
WHATSAPP_BUSINESS_ACCOUNT_ID=<your WABA id>
META_APP_ID=<Meta app id>
META_APP_SECRET=<Meta app secret>
META_CONFIG_ID=<embedded signup config id — advanced/optional path only>
WHATSAPP_VERIFY_TOKEN=staffpilot_hookup
SECRET_KEY=change-this-in-production
FRONTEND_URL=https://cordhr.optipropose.com
PAYSTACK_SECRET_KEY=
PAYSTACK_WEBHOOK_SECRET=
```

### frontend\.env.local
```
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
NEXT_PUBLIC_DEMO_TENANT_ID=
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000     # prod: Railway URL above
NEXT_PUBLIC_APP_URL=http://localhost:3000         # prod: https://cordhr.optipropose.com
BACKEND_ADMIN_KEY=change-this-in-production
PAYSTACK_SECRET_KEY=sk_test_xxxx
```

**Gotcha:** never concatenate `NEXT_PUBLIC_BACKEND_URL` directly — a trailing
slash in the env var produces a double-slash path (`host//billing/verify`)
that FastAPI 404s on instead of normalizing. Always go through
`backendUrl(path)` from `lib/utils.ts`, which strips trailing slashes once.

---

## Backend structure

```
backend\
├── main.py                   # FastAPI app — registers all routers
├── config.py                 # Settings loaded from .env (@lru_cache — needs process restart on .env change)
├── requirements.txt
├── Dockerfile
├── apprunner.yaml
├── db\
│   ├── supabase_client.py    # get_supabase() — service role client
│   ├── schema.sql            # Run first in Supabase SQL editor
│   ├── auth_billing_schema.sql  # Run second
│   ├── add_profile_name.sql  # Run third — tenant_admins.full_name
│   └── storage_setup.sql     # Run fourth
├── routers\
│   ├── webhook.py            # GET+POST /webhook — Meta WhatsApp
│   ├── admin.py               # /admin/* — employee CRUD, stats, broadcast
│   ├── billing.py            # /billing/* — Paystack subscribe/verify/webhook
│   └── settings.py           # /settings/whatsapp/onboard — embedded-signup code exchange (advanced/optional path)
└── services\
    ├── whatsapp.py           # send_message(), parse_webhook(), strip_markdown() — send_message ALWAYS needs tenant_id or it silently uses the global default number
    ├── gemini.py              # generate(), classify_intent(), embed_text()
    ├── session.py             # get_session(), update_session(), clear_session() — clear_session() preserves cross-cutting keys (salary_attempts, last_gate), see gotchas
    ├── leave.py                # Leave request state machine
    ├── qa.py                  # RAG Q&A — embed question, search pgvector, ask Gemini
    ├── payslip.py             # Payslip fetch and send
    ├── onboarding.py          # New hire checklist flow
    ├── insights.py            # Leave/analytics read models for manager+admin roles
    ├── billing.py              # Paystack initialize/verify/webhook handling, subscription activation
    └── gating.py              # PLAN_FEATURES table + whatsapp_gate() — plan feature gating
```

---

## Frontend structure

```
frontend\
├── app\
│   ├── layout.tsx            # Root layout — wraps with AuthProvider
│   ├── page.tsx               # Redirects / → /dashboard
│   ├── login\page.tsx         # Login + signup page
│   ├── billing\success\page.tsx  # Post-Paystack receipt page — verifies + shows plan, replaces the old ?upgraded=1 settings-page banner
│   ├── webhook\route.ts       # Optional Next.js-side webhook proxy → backend /webhook
│   ├── dashboard\
│   │   ├── layout.tsx        # Dashboard layout with Sidebar + activation-pending banner
│   │   ├── page.tsx           # Overview — stats + recent leave + profile-name greeting
│   │   ├── leave\page.tsx    # Leave requests table + approve/reject
│   │   ├── employees\page.tsx  # Employee management + add form
│   │   ├── payslips\page.tsx # Payslip upload + management
│   │   ├── docs\page.tsx     # HR document upload (PDF → RAG)
│   │   └── settings\page.tsx # Company config, WhatsApp activation status, profile name, billing
│   └── api\
│       ├── auth\setup\route.ts        # Creates tenant + tenant_admin on signup
│       ├── profile\save\route.ts      # Saves tenant_admins.full_name for the logged-in user
│       ├── settings\save\route.ts     # Tenant name/whatsapp_number updates
│       ├── billing\subscribe\route.ts # Paystack subscribe — builds callback_url from NEXT_PUBLIC_APP_URL
│       ├── billing\verify\route.ts    # Post-payment verification proxy → backend /billing/verify
│       └── whatsapp\connect\route.ts  # Embedded-signup code exchange proxy (advanced/optional path)
├── components\
│   ├── layout\Sidebar.tsx    # Nav sidebar — uses useAuth() for company name
│   └── ui\index.tsx          # Card, Button, Badge, StatCard, Spinner, etc.
├── lib\
│   ├── supabase.ts           # Browser Supabase client + all TypeScript types
│   ├── supabase-server.ts    # SSR Supabase client + getSession() + getCurrentTenant()
│   ├── supabase-route.ts     # Route-handler Supabase client + requireTenantAdmin() (separate from supabase-server.ts — importing next/headers breaks client component bundling)
│   ├── auth-context.tsx      # AuthProvider + useAuth() hook — exposes refreshTenantAdmin() to re-pull tenant/plan/profile after a mutation
│   ├── use-tenant.ts         # useTenant() — returns tenantId + plan
│   └── utils.ts              # cn(), formatDate(), formatCurrency(), STATUS_COLORS, backendUrl()
└── middleware.ts             # Route protection — redirects unauthenticated users from /dashboard
```

---

## Database schema (Supabase)

Key tables:
- `tenants` — one row per company, `whatsapp_number` = Meta phone_number_id (null while pending activation)
- `tenant_admins` — links Supabase auth users to tenants, `full_name` = display name for dashboard greeting (nullable, falls back to email prefix)
- `employees` — staff, phone = WhatsApp number with country code (+234...)
- `sessions` — one row per employee, stores current_flow + flow_step + context JSON
- `leave_requests` — leave requests with status pending/approved/rejected — **always filter by tenant_id**, not just status, when matching a manager's APPROVE/REJECT reference
- `hr_documents` — uploaded PDFs per tenant
- `doc_chunks` — chunked PDF content with pgvector embeddings
- `payslips` — monthly payslip records with optional PDF URL
- `subscriptions` — Paystack billing state per tenant
- `plan_limits` — starter/growth/enterprise feature flags

---

## WhatsApp bot flows

| Employee says | Flow |
|---|---|
| hi / hello | Greeting with menu |
| leave / "I want leave" | 5-step leave request state machine |
| "how many days sick leave" | RAG Q&A over HR docs |
| payslip | Fetch latest payslip record (gated: Growth+) |
| onboard | New hire checklist (gated: Growth+) |
| APPROVE xxxx | Manager approves leave (managers only, tenant-scoped) |
| REJECT xxxx | Manager rejects leave (managers only, tenant-scoped) |
| salary questions | Hardcoded refusal wall, escalates over 4 attempts (see gotchas) |

---

## Multi-tenancy

Every incoming WhatsApp message:
1. `msg.to` = Meta `phone_number_id` → looked up in `tenants.whatsapp_number`
2. `msg.from` = employee phone → looked up in `employees.phone` filtered by `tenant_id`
3. ALL DB queries filter by `tenant_id` — never cross-tenant data
4. **Every reply must pass `tenant_id` to `send_message()`** — without it, `send_message` falls back to the global `WHATSAPP_PHONE_NUMBER_ID`, so a perfectly correct reply can go out on the *wrong tenant's number*. This was a real, systemic bug (fixed once already) — if you add a new flow/handler that calls `send_message`, always thread `tenant_id` (or `employee["tenant_id"]`) through.

---

## WhatsApp number activation

Meta's **Embedded Signup** (self-serve, tenant brings their own WABA via a
Facebook Login popup) is implemented in Settings as an advanced/optional
path, but it requires Meta App Review (Advanced Access on
`whatsapp_business_management` / `business_management`) that this app
doesn't have yet. Until then, **the real onboarding path is manual**:

1. Tenant signs up → lands in a pending-activation state (dashboard banner + Settings shows "Activation in progress").
2. You register a real phone number under **your own** WABA in WhatsApp
   Manager (OTP-verified) — capped at **2 numbers per business until
   Business Verification completes**, 20 after.
3. Run `scripts/activate_tenant.py --tenant-id UUID --number <phone_number_id>`
   (or `--pending` to list who's waiting).
4. Confirm the app is subscribed to that WABA's webhooks
   (`POST /{waba_id}/subscribed_apps`) — usually already true if the number
   was added under an app-connected WABA.

**Auth token:** `WHATSAPP_ACCESS_TOKEN` must be a **System User token**
(Business Settings → Users → System Users → assign the WABA → Generate
Token, expiration **Never**), not a token from the embedded-signup OAuth
exchange — those are long-lived (60-day) user tokens that silently expire
and take the whole integration down with them. Check via Meta's
`debug_token` endpoint if unsure: `type` should be `SYSTEM_USER` and
`expires_at` should be `0`.

---

## Plan gating

```python
# In WhatsApp flows:
gate_msg = whatsapp_gate(employee["tenant_id"], "payslips")
if gate_msg:
    send_message(phone, gate_msg, tenant_id=employee["tenant_id"])
else:
    payslip.handle(employee, text)
```

Plans: starter (₦50k/mo, 30 staff, no payslips/onboarding) | growth
(₦150k/mo, 150 staff, payslips + onboarding) | enterprise (custom, +
broadcast)

---

## Important gotchas

- **Python 3.11** — 3.14 breaks google-generativeai (protobuf incompatibility)
- **venv is at FlightDeck root** `C:\Users\SEYI\FlightDeck\.venv` — always activate before running backend
- **`.env` changes need a process restart**, not just a save — see "Running locally"
- **Next.js 16** — `middleware.ts` at frontend root is deprecated in favor of `proxy.ts` (Next's naming, not ours); still works, just prints a build warning
- **Meta phone_number_id** stored in `tenants.whatsapp_number` (not the display number)
- **Employee phones** stored as `+2348XXXXXXXXX` (E.164 with + prefix)
- **Session state** is in Supabase — backend is stateless, works with App Runner/Railway
- **`clear_session()` preserves `salary_attempts` and `last_gate`** (see `session._CROSS_CUTTING_KEYS`) through a flow-completion reset — don't revert this to a wholesale `context: {}` wipe, it silently defeats the salary-wall escalation by letting any unrelated command reset the counter
- **`send_message()` needs `tenant_id`** on every call — see Multi-tenancy above
- **`backendUrl()` helper (`lib/utils.ts`)** — always use it instead of concatenating `NEXT_PUBLIC_BACKEND_URL` directly (trailing-slash gotcha)
- **`NEXT_PUBLIC_APP_URL`** drives the Paystack `callback_url` — must match whatever domain is actually canonical (currently `https://cordhr.optipropose.com`), or post-payment redirect 404s
- **Only 2 phone numbers per WABA** until Business Verification completes — currently both slots used (the free Meta Test Number + one real Nigeria number)
- **Meta Business Account verification** — has been resubmitted multiple times; check Business Settings → Security Center for current status/reason rather than assuming it's still pending
- **pgvector** — use `match_doc_chunks()` RPC function for similarity search, always filter by tenant_id

---

## Seeding & ops scripts

```bash
cd scripts

# Full demo company (Apex Consulting Ltd, 6 employees, leave requests, payslips)
python seed_demo.py
# Prints tenant ID — copy to frontend .env.local as NEXT_PUBLIC_DEMO_TENANT_ID

# Single new client, with a real number already in hand
python seed_tenant.py --name "Acme Ltd" --number "<phone_number_id>"

# List tenants waiting on WhatsApp activation
python activate_tenant.py --pending

# Assign a registered phone_number_id to a pending tenant
python activate_tenant.py --tenant-id UUID --number "<phone_number_id>"
# or: --name "Company Name" instead of --tenant-id

# Ingest HR policy PDF
python ingest_docs.py --tenant-id UUID --file handbook.pdf --title "Employee Handbook"
```

---

## Current status (Jul 6 2026)

- [x] Backend live on Railway, frontend live on Vercel + custom domain (`cordhr.optipropose.com`)
- [x] Multi-tenant WhatsApp confirmed live end-to-end on two real numbers (free Test Number + a real Nigeria number), replies correctly isolated per tenant
- [x] Manual activation flow (`activate_tenant.py`) replacing embedded-signup as the primary onboarding path
- [x] Paystack subscribe → verify → branded `/billing/success` receipt page working
- [x] Profile display name (Settings → Account) feeding the dashboard greeting
- [x] Salary-wall guardrail escalation confirmed working (context-preservation bug fixed)
- [ ] Meta Business Verification — resubmitted multiple times, check current status before assuming
- [ ] Only 2 WABA number slots available until verification clears — blocks onboarding a 3rd real tenant
- [ ] Embedded Signup (self-serve bring-your-own-WABA) still blocked on Meta App Review — manual path is the only one that works today
