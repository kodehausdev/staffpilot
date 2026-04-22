-- Auth + Billing schema additions

-- ─────────────────────────────────────────────
-- TENANT ADMINS (links Supabase Auth users → tenants)
-- ─────────────────────────────────────────────
create table tenant_admins (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenants(id) on delete cascade,
  user_id     uuid not null,             -- Supabase auth.users.id
  email       text not null,
  role        text default 'admin' check (role in ('owner', 'admin')),
  created_at  timestamptz default now(),
  unique(tenant_id, user_id)
);

-- RLS: admins can only see their own tenant rows
alter table tenant_admins enable row level security;

create policy "Admins see own tenant"
  on tenant_admins for select
  using (user_id = auth.uid());

-- Allow admins to read their tenant
create policy "Admins read own tenant"
  on tenants for select
  using (
    exists (
      select 1 from tenant_admins
      where tenant_admins.tenant_id = tenants.id
      and tenant_admins.user_id = auth.uid()
    )
  );

-- ─────────────────────────────────────────────
-- SUBSCRIPTIONS (Paystack billing state)
-- ─────────────────────────────────────────────
create table subscriptions (
  id                    uuid primary key default gen_random_uuid(),
  tenant_id             uuid not null references tenants(id) on delete cascade unique,
  paystack_customer_id  text,
  paystack_sub_code     text,                -- Paystack subscription code
  plan                  text not null default 'starter',
  status                text not null default 'active'
                          check (status in ('active','past_due','cancelled','trialing')),
  current_period_start  timestamptz,
  current_period_end    timestamptz,
  cancel_at_period_end  boolean default false,
  created_at            timestamptz default now(),
  updated_at            timestamptz default now()
);

-- ─────────────────────────────────────────────
-- BILLING EVENTS (audit log of Paystack webhooks)
-- ─────────────────────────────────────────────
create table billing_events (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid references tenants(id) on delete set null,
  event_type    text not null,             -- e.g. charge.success, subscription.disable
  payload       jsonb not null default '{}',
  processed_at  timestamptz default now()
);

-- ─────────────────────────────────────────────
-- PLAN LIMITS (lookup table)
-- ─────────────────────────────────────────────
create table plan_limits (
  plan              text primary key,
  max_employees     int not null,
  has_payslips      boolean default false,
  has_onboarding    boolean default false,
  has_broadcast     boolean default false,
  monthly_price_ngn int not null           -- in Naira
);

insert into plan_limits values
  ('starter',    30,  false, false, false, 50000),
  ('growth',     150, true,  true,  false, 150000),
  ('enterprise', -1,  true,  true,  true,  0);      -- -1 = unlimited, 0 = custom pricing

-- ─────────────────────────────────────────────
-- HELPER: check if tenant can access a feature
-- ─────────────────────────────────────────────
create or replace function tenant_can(tenant_id uuid, feature text)
returns boolean language sql stable as $$
  select case feature
    when 'payslips'    then (select has_payslips    from plan_limits pl join tenants t on t.plan = pl.plan where t.id = tenant_id)
    when 'onboarding'  then (select has_onboarding  from plan_limits pl join tenants t on t.plan = pl.plan where t.id = tenant_id)
    when 'broadcast'   then (select has_broadcast   from plan_limits pl join tenants t on t.plan = pl.plan where t.id = tenant_id)
    else true
  end;
$$;
