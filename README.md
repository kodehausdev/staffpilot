# CordHR

AI-powered WhatsApp HR assistant for Nigerian SMEs. Leave requests, payslips,
HR policy Q&A, and new-hire onboarding — all handled by staff on WhatsApp,
where they already are. Built by [Optipropose Studio](https://optipropose.com), Abuja, Nigeria.

**Live:** [cordhr.optipropose.com](https://cordhr.optipropose.com)

## What it does

- Employees message a company WhatsApp number to request leave, check their
  payslip, ask HR policy questions, or complete onboarding — no app to
  install.
- Managers approve or reject leave requests by replying `APPROVE <ref>` /
  `REJECT <ref>` on WhatsApp.
- HR admins get a web dashboard for employee management, payslip uploads,
  HR document management (feeds the WhatsApp Q&A via RAG), and billing.
- Multi-tenant by design — each company gets its own WhatsApp number, and
  every conversation, document, and record is isolated per tenant.

## Stack

FastAPI (Python) backend on Railway · Next.js dashboard on Vercel · Supabase
(Postgres + pgvector) · Gemini for conversation + embeddings · Meta WhatsApp
Cloud API · Paystack billing.

## Plans

| Plan | Price | Staff | Features |
|---|---|---|---|
| Starter | ₦50,000/mo | up to 30 | Leave, HR Q&A |
| Growth | ₦150,000/mo | up to 150 | + Payslips, onboarding |
| Enterprise | Custom | Unlimited | + Broadcast messaging |

## Development

See `CLAUDE.md` for local setup, environment variables, architecture
details, and current known issues/gotchas.

---

Optipropose Studio — Abuja, Nigeria
