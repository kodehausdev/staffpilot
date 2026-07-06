-- Adds a display name to tenant_admins, separate from their login email.
-- Run in Supabase SQL editor after auth_billing_schema.sql.

alter table tenant_admins add column if not exists full_name text;
