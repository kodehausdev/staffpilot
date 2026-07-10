-- Leave decision follow-through: decline reasons + post-decline tickets.
-- Run after storage_setup.sql.

alter table leave_requests add column if not exists decline_reason text;

-- ─────────────────────────────────────────────
-- TICKETS (staff-flagged follow-ups, e.g. after a declined leave request)
-- ─────────────────────────────────────────────
create table if not exists tickets (
  id                uuid primary key default gen_random_uuid(),
  tenant_id         uuid not null references tenants(id) on delete cascade,
  employee_id       uuid not null references employees(id) on delete cascade,
  leave_request_id  uuid references leave_requests(id) on delete set null,
  subject           text not null,
  description       text,
  status            text default 'open' check (status in ('open','closed')),
  created_at        timestamptz default now(),
  resolved_at       timestamptz
);

create index if not exists idx_tickets_tenant on tickets(tenant_id);
