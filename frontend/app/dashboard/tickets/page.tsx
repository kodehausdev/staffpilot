'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useTenant } from '@/lib/use-tenant'
import { Card, Badge, Button, PageHeader, Spinner, EmptyState } from '@/components/ui'
import { formatDate, STATUS_COLORS } from '@/lib/utils'
import type { Ticket } from '@/lib/supabase'

type Filter = 'all' | 'open' | 'closed'

const FILTERS: Filter[] = ['all', 'open', 'closed']

export default function TicketsPage() {
  const { tenantId, loading: tenantLoading } = useTenant()
  const supabase = createClient()

  const [tickets, setTickets] = useState<Ticket[]>([])
  const [filter, setFilter]   = useState<Filter>('all')
  const [loading, setLoading] = useState(true)
  const [acting, setActing]   = useState<string | null>(null)

  useEffect(() => {
    if (!tenantId) return
    load()
  }, [tenantId])

  async function load() {
    setLoading(true)
    try {
      const { data } = await supabase
        .from('tickets')
        .select('*, employees!employee_id(name, phone, department)')
        .eq('tenant_id', tenantId)
        .order('created_at', { ascending: false })
      setTickets(data ?? [])
    } finally {
      setLoading(false)
    }
  }

  async function close(id: string) {
    setActing(id)
    await supabase
      .from('tickets')
      .update({ status: 'closed', resolved_at: new Date().toISOString() })
      .eq('id', id)
    setTickets(prev => prev.map(t => t.id === id ? { ...t, status: 'closed' } : t))
    setActing(null)
  }

  const visible = filter === 'all' ? tickets : tickets.filter(t => t.status === filter)

  if (tenantLoading || loading) return <Spinner />

  return (
    <div>
      <PageHeader title="Tickets" sub={`${tickets.filter(t => t.status === 'open').length} open`} />

      <div className="flex gap-2 mb-5">
        {FILTERS.map(f => {
          const count = f === 'all' ? tickets.length : tickets.filter(t => t.status === f).length
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
          <div className="p-5"><EmptyState message={`No ${filter === 'all' ? '' : filter} tickets`} /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-sp-muted border-b border-sp-border">
                <th className="px-5 py-3 font-medium">Employee</th>
                <th className="px-4 py-3 font-medium">Subject</th>
                <th className="px-4 py-3 font-medium">Description</th>
                <th className="px-4 py-3 font-medium">Opened</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sp-border">
              {visible.map(t => {
                const emp = t.employees as any
                return (
                  <tr key={t.id} className="hover:bg-sp-border/30 transition-colors">
                    <td className="px-5 py-3 text-sp-text font-medium">{emp?.name || emp?.phone || '—'}</td>
                    <td className="px-4 py-3 text-sp-text text-xs max-w-[220px] truncate">{t.subject}</td>
                    <td className="px-4 py-3 text-sp-muted text-xs max-w-[260px] truncate">{t.description || '—'}</td>
                    <td className="px-4 py-3 text-sp-muted text-xs whitespace-nowrap">{formatDate(t.created_at)}</td>
                    <td className="px-4 py-3">
                      <Badge className={STATUS_COLORS[t.status] ?? ''}>{t.status}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      {t.status === 'open' && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={acting === t.id}
                          onClick={() => close(t.id)}
                        >
                          Mark resolved
                        </Button>
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
