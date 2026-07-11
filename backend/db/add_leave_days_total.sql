-- Track fixed annual leave entitlement separately from leave_balance (which
-- decrements as leave is taken). Without this, "how many days left" and
-- "how many days in total" are indistinguishable questions to the bot.
-- Run after add_leave_decisions.sql.

alter table employees add column if not exists leave_days_total int;

-- Reconstruct each employee's true original entitlement: current remaining
-- balance + whatever they've already had approved. Plain leave_balance would
-- under-report for anyone who has taken leave already.
update employees e
set leave_days_total = e.leave_balance + coalesce((
  select sum(lr.days)
  from leave_requests lr
  where lr.employee_id = e.id and lr.status = 'approved'
), 0)
where leave_days_total is null;

alter table employees alter column leave_days_total set default 20;
alter table employees alter column leave_days_total set not null;
