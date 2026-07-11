-- StaffPilot DB Schema
-- Run this in Supabase SQL editor

-- Enable pgvector
create extension if not exists vector;

-- ─────────────────────────────────────────────
-- TENANTS
-- ─────────────────────────────────────────────
create table tenants (
  id                  uuid primary key default gen_random_uuid(),
  name                text not null,
  whatsapp_number     text unique,       -- Twilio number assigned (e.g. whatsapp:+14155551234)
  plan                text default 'starter' check (plan in ('starter','growth','enterprise')),
  is_active           boolean default true,
  created_at          timestamptz default now()
);

-- ─────────────────────────────────────────────
-- EMPLOYEES
-- ─────────────────────────────────────────────
create table employees (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenants(id) on delete cascade,
  phone           text not null,          -- +2348XXXXXXXXX (no whatsapp: prefix)
  name            text,
  email           text,
  role            text default 'staff' check (role in ('staff','manager','hr_admin')),
  department      text,
  leave_balance   int default 20,         -- remaining annual leave days (decrements as leave is taken)
  leave_days_total int default 20 not null, -- fixed annual entitlement, distinct from leave_balance
  is_active       boolean default true,
  created_at      timestamptz default now(),
  unique(tenant_id, phone)
);

-- ─────────────────────────────────────────────
-- SESSIONS (conversation state)
-- ─────────────────────────────────────────────
create table sessions (
  id              uuid primary key default gen_random_uuid(),
  employee_id     uuid not null references employees(id) on delete cascade,
  current_flow    text,                   -- leave | qa | payslip | onboarding | null
  flow_step       text,                   -- step within flow
  context         jsonb default '{}',     -- temp data collected mid-flow
  updated_at      timestamptz default now()
);

create unique index sessions_employee_idx on sessions(employee_id);

-- ─────────────────────────────────────────────
-- LEAVE REQUESTS
-- ─────────────────────────────────────────────
create table leave_requests (
  id              uuid primary key default gen_random_uuid(),
  employee_id     uuid not null references employees(id) on delete cascade,
  tenant_id       uuid not null references tenants(id) on delete cascade,
  leave_type      text check (leave_type in ('annual','sick','maternity','paternity','unpaid')),
  start_date      date,
  end_date        date,
  days            int,
  reason          text,
  status          text default 'pending' check (status in ('pending','approved','rejected','cancelled')),
  manager_id      uuid references employees(id),
  reviewed_at     timestamptz,
  created_at      timestamptz default now()
);

-- ─────────────────────────────────────────────
-- HR DOCUMENTS
-- ─────────────────────────────────────────────
create table hr_documents (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenants(id) on delete cascade,
  title           text not null,
  file_path       text,                   -- Supabase storage path
  uploaded_by     uuid references employees(id),
  uploaded_at     timestamptz default now()
);

-- ─────────────────────────────────────────────
-- DOCUMENT CHUNKS + EMBEDDINGS (RAG)
-- ─────────────────────────────────────────────
create table doc_chunks (
  id              uuid primary key default gen_random_uuid(),
  tenant_id       uuid not null references tenants(id) on delete cascade,
  document_id     uuid not null references hr_documents(id) on delete cascade,
  content         text not null,
  embedding       vector(768),            -- Google text-embedding-004
  chunk_index     int,
  created_at      timestamptz default now()
);

create index doc_chunks_tenant_idx on doc_chunks(tenant_id);
create index doc_chunks_embedding_idx on doc_chunks using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- ─────────────────────────────────────────────
-- PAYSLIPS
-- ─────────────────────────────────────────────
create table payslips (
  id              uuid primary key default gen_random_uuid(),
  employee_id     uuid not null references employees(id) on delete cascade,
  tenant_id       uuid not null references tenants(id) on delete cascade,
  month           text not null,          -- "March 2025"
  year            int,
  gross_pay       numeric(12,2),
  net_pay         numeric(12,2),
  deductions      jsonb default '{}',     -- {tax: X, pension: Y}
  file_url        text,                   -- Supabase storage public URL
  created_at      timestamptz default now(),
  unique(employee_id, month)
);

-- ─────────────────────────────────────────────
-- HELPER FUNCTION: search doc chunks by tenant
-- ─────────────────────────────────────────────
create or replace function match_doc_chunks(
  query_embedding vector(768),
  match_tenant_id uuid,
  match_count int default 5
)
returns table (
  id uuid,
  content text,
  similarity float
)
language sql stable
as $$
  select
    doc_chunks.id,
    doc_chunks.content,
    1 - (doc_chunks.embedding <=> query_embedding) as similarity
  from doc_chunks
  where doc_chunks.tenant_id = match_tenant_id
  order by doc_chunks.embedding <=> query_embedding
  limit match_count;
$$;
