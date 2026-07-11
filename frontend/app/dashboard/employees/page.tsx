'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useTenant } from '@/lib/use-tenant'
import { Card, Badge, Button, PageHeader, Spinner, EmptyState } from '@/components/ui'
import { formatDate } from '@/lib/utils'
import { UserPlus, X } from 'lucide-react'
import type { Employee } from '@/lib/supabase'

const ROLE_COLORS: Record<string, string> = {
  staff:     'bg-sp-border text-sp-muted',
  manager:   'bg-blue-900/40 text-blue-400',
  hr_admin:  'bg-purple-900/40 text-purple-400',
}

const ROLES = ['staff', 'manager', 'hr_admin'] as const

export default function EmployeesPage() {
  const { tenantId, loading: tenantLoading } = useTenant()
  const supabase = createClient()

  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading]     = useState(true)
  const [showForm, setShowForm]   = useState(false)
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')

  const [form, setForm] = useState({
    phone: '', name: '', email: '', role: 'staff' as typeof ROLES[number],
    department: '', leave_balance: 20,
  })

  useEffect(() => {
    if (!tenantId) return
    load()
  }, [tenantId])

  async function load() {
    setLoading(true)
    try {
      const { data } = await supabase
        .from('employees')
        .select('*')
        .eq('tenant_id', tenantId)
        .order('created_at', { ascending: false })
      setEmployees(data ?? [])
    } finally {
      setLoading(false)
    }
  }

  async function addEmployee(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    const rawPhone = form.phone.trim()
    if (!rawPhone) return setError('WhatsApp phone number is required')
    if (!/^[+\d][\d\s\-]{6,}$/.test(rawPhone)) return setError('Enter a valid phone number')
    if (form.leave_balance < 0 || isNaN(form.leave_balance)) return setError('Leave balance must be 0 or more')

    setSaving(true)
    const phone = rawPhone.startsWith('+') ? rawPhone : `+234${rawPhone.replace(/^0/, '')}`

    const { error: err } = await supabase.from('employees').insert({
      tenant_id:     tenantId,
      phone,
      name:          form.name || null,
      email:         form.email || null,
      role:          form.role,
      department:    form.department || null,
      leave_balance: form.leave_balance,
      leave_days_total: form.leave_balance,
      is_active:     true,
    })

    if (err) {
      setError(err.message)
    } else {
      setForm({ phone: '', name: '', email: '', role: 'staff', department: '', leave_balance: 20 })
      setShowForm(false)
      load()
    }
    setSaving(false)
  }

  async function deactivate(id: string) {
    await supabase.from('employees').update({ is_active: false }).eq('id', id)
    setEmployees(prev => prev.map(e => e.id === id ? { ...e, is_active: false } : e))
  }

  async function reactivate(id: string) {
    await supabase.from('employees').update({ is_active: true }).eq('id', id)
    setEmployees(prev => prev.map(e => e.id === id ? { ...e, is_active: true } : e))
  }

  if (tenantLoading || loading) return <Spinner />

  return (
    <div>
      <PageHeader
        title="Employees"
        sub={`${employees.filter(e => e.is_active).length} active staff`}
        action={
          <Button onClick={() => setShowForm(true)}>
            <UserPlus size={14} /> Add employee
          </Button>
        }
      />

      {showForm && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-sp-text">New employee</h2>
            <button onClick={() => setShowForm(false)} className="text-sp-muted hover:text-sp-text">
              <X size={14} />
            </button>
          </div>

          {error && <p className="mb-3 text-xs text-red-400">{error}</p>}

          <form onSubmit={addEmployee} className="grid grid-cols-2 gap-3">
            <div className="col-span-2 sm:col-span-1">
              <label className="text-xs text-sp-muted mb-1 block">WhatsApp phone *</label>
              <input
                required
                placeholder="+2348012345678 or 08012345678"
                value={form.phone}
                onChange={e => setForm(p => ({ ...p, phone: e.target.value }))}
                className="input"
              />
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Full name</label>
              <input
                placeholder="Amaka Okonkwo"
                value={form.name}
                onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                className="input"
              />
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Email</label>
              <input
                type="email"
                placeholder="amaka@company.com"
                value={form.email}
                onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
                className="input"
              />
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Role</label>
              <select
                value={form.role}
                onChange={e => setForm(p => ({ ...p, role: e.target.value as typeof ROLES[number] }))}
                className="input"
              >
                {ROLES.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Department</label>
              <input
                placeholder="Finance, Sales…"
                value={form.department}
                onChange={e => setForm(p => ({ ...p, department: e.target.value }))}
                className="input"
              />
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Annual leave balance (days)</label>
              <input
                type="number"
                min={0}
                value={form.leave_balance}
                onChange={e => setForm(p => ({ ...p, leave_balance: parseInt(e.target.value) || 0 }))}
                className="input"
              />
            </div>
            <div className="col-span-2 flex justify-end gap-2 pt-1">
              <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Add employee'}</Button>
            </div>
          </form>
        </Card>
      )}

      <Card className="p-0 overflow-hidden">
        {employees.length === 0 ? (
          <div className="p-5"><EmptyState message="No employees yet — add your first one above" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-sp-muted border-b border-sp-border">
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Phone</th>
                <th className="px-4 py-3 font-medium">Dept</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Leave balance</th>
                <th className="px-4 py-3 font-medium">Joined</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-sp-border">
              {employees.map(emp => (
                <tr key={emp.id} className="hover:bg-sp-border/30 transition-colors">
                  <td className="px-5 py-3 text-sp-text font-medium">{emp.name || '—'}</td>
                  <td className="px-4 py-3 text-sp-muted font-mono text-xs">{emp.phone}</td>
                  <td className="px-4 py-3 text-sp-muted text-xs">{emp.department || '—'}</td>
                  <td className="px-4 py-3">
                    <Badge className={ROLE_COLORS[emp.role] ?? ''}>{emp.role.replace('_', ' ')}</Badge>
                  </td>
                  <td className="px-4 py-3 text-sp-muted">{emp.leave_balance}d</td>
                  <td className="px-4 py-3 text-sp-muted text-xs">{formatDate(emp.created_at)}</td>
                  <td className="px-4 py-3">
                    <Badge className={emp.is_active ? 'bg-green-900/30 text-green-400' : 'bg-sp-border text-sp-muted'}>
                      {emp.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    {emp.is_active ? (
                      <Button size="sm" variant="ghost" onClick={() => deactivate(emp.id)}>
                        Deactivate
                      </Button>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => reactivate(emp.id)}>
                        Reactivate
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
