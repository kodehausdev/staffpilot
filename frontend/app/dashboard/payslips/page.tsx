'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useTenant } from '@/lib/use-tenant'
import { Card, Badge, Button, PageHeader, Spinner, EmptyState } from '@/components/ui'
import { formatCurrency, formatDate } from '@/lib/utils'
import { Plus, X, ExternalLink } from 'lucide-react'
import type { Payslip, Employee } from '@/lib/supabase'

const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
]

export default function PayslipsPage() {
  const { tenantId, loading: tenantLoading } = useTenant()
  const supabase = createClient()

  const [payslips, setPayslips]   = useState<Payslip[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading]     = useState(true)
  const [showForm, setShowForm]   = useState(false)
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')

  const now = new Date()
  const [form, setForm] = useState({
    employee_id: '',
    month: MONTHS[now.getMonth()],
    year: now.getFullYear(),
    gross_pay: '',
    net_pay: '',
    file_url: '',
  })

  useEffect(() => {
    if (!tenantId) return
    load()
  }, [tenantId])

  async function load() {
    setLoading(true)
    try {
      const [psRes, empRes] = await Promise.all([
        supabase
          .from('payslips')
          .select('*, employees(name, phone)')
          .eq('tenant_id', tenantId)
          .order('created_at', { ascending: false }),
        supabase
          .from('employees')
          .select('id, name, phone')
          .eq('tenant_id', tenantId)
          .eq('is_active', true),
      ])
      setPayslips(psRes.data ?? [])
      setEmployees(empRes.data ?? [])
    } finally {
      setLoading(false)
    }
  }

  async function addPayslip(e: React.FormEvent) {
    e.preventDefault()

    const gross = parseFloat(form.gross_pay)
    const net   = parseFloat(form.net_pay)

    if (!form.employee_id) return setError('Please select an employee')
    if (isNaN(gross) || gross <= 0) return setError('Enter a valid gross pay amount')
    if (isNaN(net)   || net   <= 0) return setError('Enter a valid net pay amount')
    if (net > gross)                return setError('Net pay cannot exceed gross pay')

    setSaving(true)
    setError('')

    const { error: err } = await supabase.from('payslips').insert({
      tenant_id:   tenantId,
      employee_id: form.employee_id,
      month:       form.month,
      year:        form.year,
      gross_pay:   gross,
      net_pay:     net,
      deductions:  {},
      file_url:    form.file_url || null,
    })

    if (err) {
      setError(err.message)
    } else {
      setForm({ employee_id: '', month: MONTHS[now.getMonth()], year: now.getFullYear(), gross_pay: '', net_pay: '', file_url: '' })
      setShowForm(false)
      load()
    }
    setSaving(false)
  }

  if (tenantLoading || loading) return <Spinner />

  return (
    <div>
      <PageHeader
        title="Payslips"
        sub="Monthly payslip records"
        action={
          <Button onClick={() => setShowForm(true)}>
            <Plus size={14} /> Add payslip
          </Button>
        }
      />

      {showForm && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-sp-text">New payslip</h2>
            <button onClick={() => setShowForm(false)} className="text-sp-muted hover:text-sp-text">
              <X size={14} />
            </button>
          </div>

          {error && <p className="mb-3 text-xs text-red-400">{error}</p>}

          <form onSubmit={addPayslip} className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs text-sp-muted mb-1 block">Employee *</label>
              <select
                required
                value={form.employee_id}
                onChange={e => setForm(p => ({ ...p, employee_id: e.target.value }))}
                className="input"
              >
                <option value="">Select employee…</option>
                {employees.map(emp => (
                  <option key={emp.id} value={emp.id}>{emp.name || emp.phone}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Month</label>
              <select
                value={form.month}
                onChange={e => setForm(p => ({ ...p, month: e.target.value }))}
                className="input"
              >
                {MONTHS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Year</label>
              <input
                type="number"
                value={form.year}
                onChange={e => setForm(p => ({ ...p, year: parseInt(e.target.value) || now.getFullYear() }))}
                className="input"
              />
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Gross pay (₦) *</label>
              <input
                required
                type="number"
                placeholder="150000"
                value={form.gross_pay}
                onChange={e => setForm(p => ({ ...p, gross_pay: e.target.value }))}
                className="input"
              />
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Net pay (₦) *</label>
              <input
                required
                type="number"
                placeholder="120000"
                value={form.net_pay}
                onChange={e => setForm(p => ({ ...p, net_pay: e.target.value }))}
                className="input"
              />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-sp-muted mb-1 block">PDF URL (optional)</label>
              <input
                type="url"
                placeholder="https://…"
                value={form.file_url}
                onChange={e => setForm(p => ({ ...p, file_url: e.target.value }))}
                className="input"
              />
            </div>
            <div className="col-span-2 flex justify-end gap-2 pt-1">
              <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Add payslip'}</Button>
            </div>
          </form>
        </Card>
      )}

      <Card className="p-0 overflow-hidden">
        {payslips.length === 0 ? (
          <div className="p-5"><EmptyState message="No payslips yet" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-sp-muted border-b border-sp-border">
                <th className="px-5 py-3 font-medium">Employee</th>
                <th className="px-4 py-3 font-medium">Period</th>
                <th className="px-4 py-3 font-medium">Gross pay</th>
                <th className="px-4 py-3 font-medium">Net pay</th>
                <th className="px-4 py-3 font-medium">Added</th>
                <th className="px-4 py-3 font-medium">PDF</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sp-border">
              {payslips.map(ps => {
                const emp = ps.employees as any
                return (
                  <tr key={ps.id} className="hover:bg-sp-border/30 transition-colors">
                    <td className="px-5 py-3 text-sp-text font-medium">{emp?.name || emp?.phone || '—'}</td>
                    <td className="px-4 py-3 text-sp-muted">{ps.month} {ps.year}</td>
                    <td className="px-4 py-3 text-sp-text">{formatCurrency(ps.gross_pay)}</td>
                    <td className="px-4 py-3 text-sp-accent font-medium">{formatCurrency(ps.net_pay)}</td>
                    <td className="px-4 py-3 text-sp-muted text-xs">{formatDate(ps.created_at)}</td>
                    <td className="px-4 py-3">
                      {ps.file_url ? (
                        <a
                          href={ps.file_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-sp-accent text-xs hover:underline"
                        >
                          View <ExternalLink size={11} />
                        </a>
                      ) : (
                        <span className="text-sp-muted text-xs">—</span>
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
