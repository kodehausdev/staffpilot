-- Payslip encryption migration
-- Converts gross_pay, net_pay, deductions from plain values to ciphertext (text).
-- Run this ONCE in Supabase SQL editor BEFORE deploying the encrypted backend.
-- All existing payslip rows will be wiped (pre-production only — no real data yet).

-- Wipe existing test data (safe pre-production)
delete from payslips;

-- Change column types to text to hold Fernet ciphertext
alter table payslips alter column gross_pay  type text using null;
alter table payslips alter column net_pay    type text using null;
alter table payslips alter column deductions type text using null;
