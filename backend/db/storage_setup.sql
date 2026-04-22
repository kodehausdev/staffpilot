-- Run this in Supabase SQL editor AFTER schema.sql
-- Sets up Storage buckets + policies

-- 1. HR Documents bucket (private — signed URLs only)
insert into storage.buckets (id, name, public)
values ('hr-documents', 'hr-documents', false)
on conflict do nothing;

-- 2. Payslips bucket (private)
insert into storage.buckets (id, name, public)
values ('payslips', 'payslips', false)
on conflict do nothing;

-- Policies: service role can do everything (backend uses service role key)
create policy "Service role full access to hr-documents"
on storage.objects for all
using (bucket_id = 'hr-documents')
with check (bucket_id = 'hr-documents');

create policy "Service role full access to payslips"
on storage.objects for all
using (bucket_id = 'payslips')
with check (bucket_id = 'payslips');
