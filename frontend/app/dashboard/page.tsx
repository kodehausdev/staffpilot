'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase-server'
import { useTenant } from '@/lib/use-tenant'
import { useAuth } from '@/lib/auth-context'
import { Badge, Spinner } from '@/components/ui'
import { formatCurrency, STATUS_COLORS, LEAVE_TYPE_COLORS, withDeadline } from '@/lib/utils'
import type { Employee, LeaveRequest, Payslip } from '@/lib/supabase'
import { ArrowRight, UserPlus, Upload, Plus, CreditCard, CalendarOff, ChevronDown } from 'lucide-react'

type DeptCount = { department: string; count: number }

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function DashboardPage() {
  const { tenantId, plan, loading: tenantLoading } = useTenant()
  const { tenantAdmin, user } = useAuth()
  const supabase = createClient()
  const router   = useRouter()

  const [stats, setStats]                   = useState({ employees: 0, pending: 0, approved: 0, docs: 0 })
  const [recentLeave, setRecentLeave]       = useState<LeaveRequest[]>([])
  const [recentPayslips, setRecentPayslips] = useState<Payslip[]>([])
  const [deptBreakdown, setDeptBreakdown]   = useState<DeptCount[]>([])
  const [loading, setLoading]               = useState(true)
  const [deptExpanded, setDeptExpanded]     = useState(false)

  useEffect(() => {
    if (!tenantId) {
      if (!tenantLoading) setLoading(false)
      return
    }
    load()
  }, [tenantId, tenantLoading])

  async function load() {
    try {
      const [empRes, leaveRes, allLeaveRes, payslipRes, docsRes] = await Promise.all([
        withDeadline(supabase.from('employees').select('id, department, is_active').eq('tenant_id', tenantId)),
        withDeadline(supabase.from('leave_requests').select('*, employees!employee_id(name, phone)').eq('tenant_id', tenantId).order('created_at', { ascending: false }).limit(5)),
        withDeadline(supabase.from('leave_requests').select('status').eq('tenant_id', tenantId)),
        withDeadline(supabase.from('payslips').select('*, employees(name)').eq('tenant_id', tenantId).order('created_at', { ascending: false }).limit(3)),
        withDeadline(supabase.from('hr_documents').select('id', { count: 'exact', head: true }).eq('tenant_id', tenantId)),
      ])

      const emps     = (empRes.data ?? []) as Pick<Employee, 'id' | 'department' | 'is_active'>[]
      const active   = emps.filter(e => e.is_active)
      const leave    = (leaveRes.data ?? []) as LeaveRequest[]
      const allLeave = (allLeaveRes.data ?? []) as Pick<LeaveRequest, 'status'>[]

      const deptMap: Record<string, number> = {}
      active.forEach(e => {
        const d = e.department || 'Unassigned'
        deptMap[d] = (deptMap[d] || 0) + 1
      })

      setStats({
        employees: active.length,
        pending:   allLeave.filter(l => l.status === 'pending').length,
        approved:  allLeave.filter(l => l.status === 'approved').length,
        docs:      docsRes.count ?? 0,
      })
      setRecentLeave(leave)
      setRecentPayslips(payslipRes.data ?? [])
      setDeptBreakdown(
        Object.entries(deptMap)
          .map(([department, count]) => ({ department, count }))
          .sort((a, b) => b.count - a.count)
      )
    } finally {
      setLoading(false)
    }
  }

  if (tenantLoading || loading) return <Spinner />
  if (!tenantId) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3 text-center">
      <p className="text-sp-text font-medium">Account not linked to a company</p>
      <p className="text-sm text-sp-muted">Your account exists but isn't connected to a tenant yet.<br />Contact support or try signing out and signing up again.</p>
    </div>
  )

  const firstName   = tenantAdmin?.full_name?.trim().split(' ')[0] || user?.email?.split('@')[0] || ''
  const companyName = tenantAdmin?.tenants?.name ?? '—'
  const visibleDepts = deptExpanded ? deptBreakdown : deptBreakdown.slice(0, 4)

  return (
    <div className="flex flex-col gap-4 h-full">

      {/* ── Slim header ─────────────────────────────────────────── */}
      <div className="flex items-baseline justify-between">
        <div>
          <p className="text-xs text-sp-muted mb-0.5">{greeting()}{firstName ? `, ${firstName}` : ''}</p>
          <h1 className="text-lg font-semibold text-sp-text tracking-tight leading-none">Overview</h1>
        </div>
        <p className="text-xs text-sp-muted">{companyName} · {plan} plan</p>
      </div>

      {/* ── Horizontal stat strip ───────────────────────────────── */}
      <div className="bento-luxury flex divide-x divide-white/[0.06] py-3.5 px-0 overflow-hidden">
        {[
          { label: 'Active staff',   value: stats.employees },
          { label: 'Pending leave',  value: stats.pending,  muted: stats.pending === 0 },
          { label: 'Approved leave', value: stats.approved  },
          { label: 'HR documents',   value: stats.docs      },
        ].map(({ label, value, muted }) => (
          <div key={label} className="flex-1 flex flex-col items-center justify-center px-4">
            <p className={`text-2xl font-semibold tracking-tight leading-none ${muted ? 'text-sp-muted' : 'text-sp-text'}`}>
              {value}
            </p>
            <p className="text-[11px] text-sp-muted mt-1 uppercase tracking-wider">{label}</p>
          </div>
        ))}
      </div>

      {/* ── Main: 2/3 live data + 1/3 tools ────────────────────── */}
      <div className="grid grid-cols-3 gap-4 flex-1 items-start">

        {/* LEFT — leave requests (full height) */}
        <div className="col-span-2">
          <div className="bento-luxury">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-sp-text uppercase tracking-widest">Leave requests</span>
                <span className="flex items-center gap-1 text-[11px] text-sp-muted">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sp-accent opacity-60" />
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-sp-accent" />
                  </span>
                  Bot active
                </span>
              </div>
              {recentLeave.length > 0 && (
                <button onClick={() => router.push('/dashboard/leave')}
                  className="text-xs text-sp-muted hover:text-sp-text flex items-center gap-1 transition-colors">
                  View all <ArrowRight size={11} />
                </button>
              )}
            </div>

            {recentLeave.length === 0 ? (
              <div className="flex items-center gap-3 py-4 px-1">
                <CalendarOff size={16} className="text-sp-border shrink-0" />
                <p className="text-sm text-sp-muted">
                  No leave requests yet — employees trigger these via WhatsApp
                </p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-sp-muted border-b border-white/[0.06]">
                    <th className="pb-2 font-medium">Employee</th>
                    <th className="pb-2 font-medium">Type</th>
                    <th className="pb-2 font-medium">Dates</th>
                    <th className="pb-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {recentLeave.map(lr => {
                    const emp = lr.employees as any
                    return (
                      <tr key={lr.id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-2 text-sp-text">{emp?.name || emp?.phone || '—'}</td>
                        <td className="py-2">
                          <Badge className={`${LEAVE_TYPE_COLORS[lr.leave_type] ?? ''} capitalize`}>
                            {lr.leave_type}
                          </Badge>
                        </td>
                        <td className="py-2 text-sp-muted text-xs whitespace-nowrap">
                          {lr.start_date} → {lr.end_date}
                        </td>
                        <td className="py-2">
                          <Badge className={STATUS_COLORS[lr.status] ?? ''}>{lr.status}</Badge>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* RIGHT — tools, payslips & dept */}
        <div className="col-span-1 flex flex-col gap-4">

          {/* Quick actions */}
          <div className="bento-luxury">
            <p className="text-xs font-semibold text-sp-text uppercase tracking-widest mb-3">Quick actions</p>
            <div className="space-y-0.5">
              {[
                { icon: <UserPlus size={13} />,   label: 'Add employee',  href: '/dashboard/employees' },
                { icon: <Upload size={13} />,     label: 'Upload HR doc', href: '/dashboard/docs'      },
                { icon: <Plus size={13} />,       label: 'Add payslip',   href: '/dashboard/payslips'  },
                { icon: <CreditCard size={13} />, label: 'View payslips', href: '/dashboard/payslips'  },
              ].map(({ icon, label, href }) => (
                <button
                  key={label}
                  onClick={() => router.push(href)}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm text-sp-muted hover:text-sp-text hover:bg-white/[0.03] transition-all group text-left"
                >
                  <span className="text-sp-muted group-hover:text-sp-text transition-colors">{icon}</span>
                  {label}
                  <ArrowRight size={10} className="ml-auto opacity-0 group-hover:opacity-30 transition-opacity" />
                </button>
              ))}
            </div>
          </div>

          {/* Recent payslips */}
          <div className="bento-luxury">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-sp-text uppercase tracking-widest">Recent payslips</span>
              {recentPayslips.length > 0 && (
                <button onClick={() => router.push('/dashboard/payslips')}
                  className="text-xs text-sp-muted hover:text-sp-text flex items-center gap-1 transition-colors">
                  View all <ArrowRight size={11} />
                </button>
              )}
            </div>
            {recentPayslips.length === 0 ? (
              <div className="flex items-center gap-2 py-2 px-1">
                <CreditCard size={14} className="text-sp-border shrink-0" />
                <p className="text-xs text-sp-muted">No payslips added yet</p>
              </div>
            ) : (
              <div className="divide-y divide-white/[0.04]">
                {recentPayslips.map(ps => {
                  const emp = ps.employees as any
                  return (
                    <div key={ps.id} className="flex items-center justify-between py-2 hover:bg-white/[0.02] transition-colors rounded">
                      <div className="min-w-0 mr-2">
                        <p className="text-xs font-medium text-sp-text truncate">{emp?.name || '—'}</p>
                        <p className="text-[11px] text-sp-muted">{ps.month}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-xs font-semibold text-sp-accent">{formatCurrency(ps.net_pay)}</p>
                        <p className="text-[11px] text-sp-muted">gross {formatCurrency(ps.gross_pay)}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Staff by dept */}
          <div className="bento-luxury">
            <p className="text-xs font-semibold text-sp-text uppercase tracking-widest mb-3">Staff by dept</p>
            {deptBreakdown.length === 0 ? (
              <p className="text-xs text-sp-muted">No employees yet</p>
            ) : (
              <div className="space-y-2.5">
                {visibleDepts.map(({ department, count }) => (
                  <div key={department} className="flex items-center gap-2.5">
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-sp-muted truncate">{department}</span>
                        <span className="text-sp-muted ml-2 shrink-0">{count}</span>
                      </div>
                      <div className="h-0.5 bg-white/[0.06] rounded-full">
                        <div
                          className="h-full bg-sp-muted/50 rounded-full transition-all duration-500"
                          style={{ width: `${Math.round((count / deptBreakdown[0].count) * 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
                {deptBreakdown.length > 4 && (
                  <button
                    onClick={() => setDeptExpanded(e => !e)}
                    className="flex items-center gap-1 text-xs text-sp-muted hover:text-sp-text transition-colors pt-0.5"
                  >
                    <ChevronDown size={11} className={`transition-transform duration-200 ${deptExpanded ? 'rotate-180' : ''}`} />
                    {deptExpanded ? 'Show less' : `+${deptBreakdown.length - 4} more`}
                  </button>
                )}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
