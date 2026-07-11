-- tickets ended up with RLS enabled and zero policies (likely from Supabase's
-- Security Advisor auto-flagging a public table with no RLS) — that's
-- default-deny for the anon/authenticated roles the dashboard reads with,
-- so tickets exist in the DB but never show up in the UI. Add real
-- tenant-scoped policies, mirroring the tenant_admins/tenants pattern in
-- auth_billing_schema.sql, rather than just disabling RLS.

alter table tickets enable row level security;

create policy "Admins see own tenant tickets"
  on tickets for select
  using (
    exists (
      select 1 from tenant_admins
      where tenant_admins.tenant_id = tickets.tenant_id
      and tenant_admins.user_id = auth.uid()
    )
  );

create policy "Admins update own tenant tickets"
  on tickets for update
  using (
    exists (
      select 1 from tenant_admins
      where tenant_admins.tenant_id = tickets.tenant_id
      and tenant_admins.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from tenant_admins
      where tenant_admins.tenant_id = tickets.tenant_id
      and tenant_admins.user_id = auth.uid()
    )
  );
