'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useTenant } from '@/lib/use-tenant'
import { Card, Badge, Button, PageHeader, Spinner, EmptyState } from '@/components/ui'
import { formatDate, STATUS_COLORS, LEAVE_TYPE_COLORS, withDeadline } from '@/lib/utils'
import type { LeaveRequest } from '@/lib/supabase'

type Filter = 'all' | 'pending' | 'approved' | 'rejected'

const FILTERS: Filter[] = ['all', 'pending', 'approved', 'rejected']

export default function LeavePage() {
  const { tenantId, loading: tenantLoading } = useTenant()
  const supabase = createClient()

  const [requests, setRequests] = useState<LeaveRequest[]>([])
  const [filter, setFilter]     = useState<Filter>('all')
  const [loading, setLoading]   = useState(true)
  const [acting, setActing]     = useState<string | null>(null)
  const [rejecting, setRejecting] = useState<string | null>(null)
  const [reason, setReason]       = useState('')

  useEffect(() => {
    if (!tenantId) return
    load()
  }, [tenantId])

  async function load() {
    setLoading(true)
    try {
      console.log('[leave] tenantId:', tenantId)
      const { data, error } = await withDeadline(supabase
        .from('leave_requests')
        .select('*, employees!employee_id(name, phone, department)')
        .eq('tenant_id', tenantId)
        .order('created_at', { ascending: false }))
      console.log('[leave] data:', data, 'error:', error)
      setRequests(data ?? [])
    } finally {
      setLoading(false)
    }
  }

  async function updateStatus(id: string, status: 'approved' | 'rejected', declineReason?: string) {
    setActing(id)
    try {
      const res = await fetch('/api/leave/decide', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ id, status, reason: declineReason }),
      })
      if (!res.ok) throw new Error(await res.text())
      setRequests(prev => prev.map(r => r.id === id ? { ...r, status, decline_reason: declineReason ?? null } : r))
    } finally {
      setActing(null)
      setRejecting(null)
      setReason('')
    }
  }

  const visible = filter === 'all' ? requests : requests.filter(r => r.status === filter)

  if (tenantLoading || loading) return <Spinner />

  return (
    <div>
      <PageHeader title="Leave requests" sub={`${requests.filter(r => r.status === 'pending').length} pending approval`} />

      <div className="flex gap-2 mb-5">
        {FILTERS.map(f => {
          const count = f === 'all' ? requests.length : requests.filter(r => r.status === f).length
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
                filter === f
                  ? 'bg-sp-accent-dim text-sp-accent'
                  : 'text-sp-muted hover:text-sp-text hover:bg-sp-border'
              }`}
            >
              {f}
              {count > 0 && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${
                  filter === f ? 'bg-sp-accent/20 text-sp-accent' : 'bg-sp-border text-sp-muted'
                }`}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      <Card className="p-0 overflow-hidden">
        {visible.length === 0 ? (
          <div className="p-5"><EmptyState message={`No ${filter === 'all' ? '' : filter} leave requests`} /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-sp-muted border-b border-sp-border">
                <th className="px-5 py-3 font-medium">Employee</th>
                <th className="px-4 py-3 font-medium">Dept</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Dates</th>
                <th className="px-4 py-3 font-medium">Days</th>
                <th className="px-4 py-3 font-medium">Reason</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sp-border">
              {visible.map(lr => {
                const emp = lr.employees as any
                return (
                  <tr key={lr.id} className="hover:bg-sp-border/30 transition-colors">
                    <td className="px-5 py-3 text-sp-text font-medium">{emp?.name || emp?.phone || '—'}</td>
                    <td className="px-4 py-3 text-sp-muted text-xs">{emp?.department || '—'}</td>
                    <td className="px-4 py-3">
                      <Badge className={LEAVE_TYPE_COLORS[lr.leave_type] ?? ''}>{lr.leave_type}</Badge>
                    </td>
                    <td className="px-4 py-3 text-sp-muted text-xs whitespace-nowrap">
                      {formatDate(lr.start_date)} – {formatDate(lr.end_date)}
                    </td>
                    <td className="px-4 py-3 text-sp-muted">{lr.days}</td>
                    <td className="px-4 py-3 text-sp-muted text-xs max-w-[160px] truncate">{lr.reason || '—'}</td>
                    <td className="px-4 py-3">
                      <Badge className={STATUS_COLORS[lr.status] ?? ''}>{lr.status}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      {lr.status === 'pending' && rejecting === lr.id ? (
                        <div className="flex flex-col gap-1.5 min-w-[200px]">
                          <textarea
                            autoFocus
                            value={reason}
                            onChange={e => setReason(e.target.value)}
                            placeholder="Reason (optional)"
                            rows={2}
                            className="text-xs px-2 py-1.5 rounded-md bg-sp-bg border border-sp-border text-sp-text placeholder:text-sp-muted resize-none focus:outline-none focus:ring-1 focus:ring-sp-accent"
                          />
                          <div className="flex gap-1.5">
                            <Button
                              size="sm"
                              variant="danger"
                              disabled={acting === lr.id}
                              onClick={() => updateStatus(lr.id, 'rejected', reason.trim() || undefined)}
                            >
                              Confirm reject
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={acting === lr.id}
                              onClick={() => { setRejecting(null); setReason('') }}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : lr.status === 'pending' && (
                        <div className="flex gap-1.5">
                          <Button
                            size="sm"
                            variant="primary"
                            disabled={acting === lr.id}
                            onClick={() => updateStatus(lr.id, 'approved')}
                          >
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            disabled={acting === lr.id}
                            onClick={() => setRejecting(lr.id)}
                          >
                            Reject
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
