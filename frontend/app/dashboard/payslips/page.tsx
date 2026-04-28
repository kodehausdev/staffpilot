'use client'
import { useEffect, useRef, useState } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useTenant } from '@/lib/use-tenant'
import { Card, Button, PageHeader, Spinner, EmptyState } from '@/components/ui'
import { formatCurrency, formatDate } from '@/lib/utils'
import { Plus, X, ExternalLink, Upload, Download, AlertCircle, CheckCircle2, Send } from 'lucide-react'
import type { Payslip, Employee } from '@/lib/supabase'

const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
]

// ── CSV format definitions ──────────────────────────────────────────────────
type FormatKey = 'generic' | 'sage' | 'workpay' | 'brightpay'

const FORMATS: Record<FormatKey, { label: string; columns: string[]; note: string }> = {
  generic: {
    label: 'Generic CSV / Excel',
    columns: ['phone', 'month', 'year', 'gross_pay', 'net_pay'],
    note: 'Works with any spreadsheet. Phone must be E.164 (+234...)',
  },
  sage: {
    label: 'Sage Payroll',
    columns: ['Employee Ref', 'Pay Period', 'Basic Pay', 'Net Pay'],
    note: 'Export from Sage: Reports → Payroll Summary → CSV',
  },
  workpay: {
    label: 'Workpay',
    columns: ['employee_phone', 'payroll_month', 'gross_salary', 'net_salary'],
    note: 'Export from Workpay: Payroll → Run Payroll → Download CSV',
  },
  brightpay: {
    label: 'BrightPay',
    columns: ['Mobile', 'Period', 'Gross', 'Net'],
    note: 'Export from BrightPay: Reports → Employee Summary → Export',
  },
}

// Normalise a parsed CSV row into a common shape
function normaliseRow(row: Record<string, string>, format: FormatKey, employees: Employee[]) {
  const v = (keys: string[]) => {
    for (const k of keys) {
      const val = row[k] ?? row[k.toLowerCase()]
      if (val !== undefined) return val.trim()
    }
    return ''
  }

  let phone = ''
  let monthRaw = ''
  let year = new Date().getFullYear()
  let gross = 0
  let net = 0

  if (format === 'generic') {
    phone    = v(['phone'])
    monthRaw = v(['month'])
    year     = parseInt(v(['year'])) || year
    gross    = parseFloat(v(['gross_pay']).replace(/,/g, '')) || 0
    net      = parseFloat(v(['net_pay']).replace(/,/g, ''))   || 0
  } else if (format === 'sage') {
    phone    = v(['Employee Ref', 'employee ref'])            // Sage uses ref — matched below
    monthRaw = v(['Pay Period', 'pay period'])
    gross    = parseFloat(v(['Basic Pay', 'basic pay']).replace(/,/g, '')) || 0
    net      = parseFloat(v(['Net Pay', 'net pay']).replace(/,/g, ''))     || 0
  } else if (format === 'workpay') {
    phone    = v(['employee_phone'])
    monthRaw = v(['payroll_month'])
    gross    = parseFloat(v(['gross_salary']).replace(/,/g, '')) || 0
    net      = parseFloat(v(['net_salary']).replace(/,/g, ''))   || 0
  } else if (format === 'brightpay') {
    phone    = v(['Mobile', 'mobile'])
    monthRaw = v(['Period', 'period'])
    gross    = parseFloat(v(['Gross', 'gross']).replace(/,/g, '')) || 0
    net      = parseFloat(v(['Net', 'net']).replace(/,/g, ''))     || 0
  }

  // Resolve month + year from monthRaw (e.g. "April 2026", "04/2026", "2026-04")
  let month = monthRaw
  const yearMatch = monthRaw.match(/\d{4}/)
  if (yearMatch) year = parseInt(yearMatch[0])
  const monthName = MONTHS.find(m => monthRaw.toLowerCase().includes(m.toLowerCase()))
  if (monthName) month = monthName

  // Match phone to employee (normalise to digits only for comparison)
  const digits = (s: string) => s.replace(/\D/g, '')
  const employee = employees.find(e => e.phone && digits(e.phone).endsWith(digits(phone).slice(-9)))

  return { phone, month, year, gross, net, employee: employee ?? null }
}

function parseCSV(text: string): Record<string, string>[] {
  const lines = text.trim().split(/\r?\n/)
  if (lines.length < 2) return []
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  return lines.slice(1).map(line => {
    const vals = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''))
    return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? '']))
  })
}

function buildTemplate(format: FormatKey): string {
  const cols = FORMATS[format].columns
  const example: Record<FormatKey, string> = {
    generic:   `+2348012345678,April,2026,450000,340000`,
    sage:      `EMP001,April 2026,450000,340000`,
    workpay:   `+2348012345678,April 2026,450000,340000`,
    brightpay: `+2348012345678,April 2026,450000,340000`,
  }
  return [cols.join(','), example[format]].join('\n')
}

// ── Component ───────────────────────────────────────────────────────────────
export default function PayslipsPage() {
  const { tenantId, loading: tenantLoading } = useTenant()
  const supabase = createClient()

  const now = new Date()

  const [payslips, setPayslips]   = useState<Payslip[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading]     = useState(true)
  const [showForm, setShowForm]       = useState(false)
  const [showImport, setShowImport]   = useState(false)
  const [showBroadcast, setShowBroadcast] = useState(false)
  const [saving, setSaving]           = useState(false)
  const [error, setError]             = useState('')

  // Broadcast state
  const [bcastMonth, setBcastMonth]   = useState(MONTHS[now.getMonth()])
  const [bcastYear, setBcastYear]     = useState(now.getFullYear())
  const [bcastResult, setBcastResult] = useState<{ sent: number; failed: number; total: number } | null>(null)
  const [bcasting, setBcasting]       = useState(false)
  const [form, setForm] = useState({
    employee_id: '',
    month: MONTHS[now.getMonth()],
    year: now.getFullYear(),
    gross_pay: '',
    net_pay: '',
    file_url: '',
  })

  // Import state
  const [importFormat, setImportFormat] = useState<FormatKey>('generic')
  const [importRows, setImportRows]     = useState<ReturnType<typeof normaliseRow>[]>([])
  const [importing, setImporting]       = useState(false)
  const [importDone, setImportDone]     = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => { if (tenantId) load() }, [tenantId])

  async function load() {
    setLoading(true)
    try {
      const [psRes, empRes] = await Promise.all([
        supabase.from('payslips').select('*, employees(name, phone)')
          .eq('tenant_id', tenantId).order('created_at', { ascending: false }),
        supabase.from('employees').select('id, name, phone')
          .eq('tenant_id', tenantId).eq('is_active', true),
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
    if (!form.employee_id)            return setError('Please select an employee')
    if (isNaN(gross) || gross <= 0)   return setError('Enter a valid gross pay amount')
    if (isNaN(net)   || net   <= 0)   return setError('Enter a valid net pay amount')
    if (net > gross)                  return setError('Net pay cannot exceed gross pay')
    setSaving(true); setError('')
    const { error: err } = await supabase.from('payslips').insert({
      tenant_id: tenantId, employee_id: form.employee_id,
      month: form.month, year: form.year,
      gross_pay: gross, net_pay: net, deductions: {},
      file_url: form.file_url || null,
    })
    if (err) { setError(err.message) }
    else { setForm({ employee_id: '', month: MONTHS[now.getMonth()], year: now.getFullYear(), gross_pay: '', net_pay: '', file_url: '' }); setShowForm(false); load() }
    setSaving(false)
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = ev => {
      const rows = parseCSV(ev.target?.result as string)
      setImportRows(rows.map(r => normaliseRow(r, importFormat, employees)))
    }
    reader.readAsText(file)
  }

  function downloadTemplate() {
    const csv  = buildTemplate(importFormat)
    const blob = new Blob([csv], { type: 'text/csv' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = `staffpilot_${importFormat}_template.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  async function runImport() {
    const valid = importRows.filter(r => r.employee && r.gross > 0 && r.net > 0 && r.month)
    if (!valid.length) return
    setImporting(true)
    const records = valid.map(r => ({
      tenant_id:   tenantId,
      employee_id: r.employee!.id,
      month:       r.month,
      year:        r.year,
      gross_pay:   r.gross,
      net_pay:     r.net,
      deductions:  {},
    }))
    await supabase.from('payslips').upsert(records, { onConflict: 'employee_id,month' })
    setImporting(false); setImportDone(true)
    setTimeout(() => { setShowImport(false); setImportRows([]); setImportDone(false); load() }, 1500)
  }

  async function sendBroadcast() {
    setBcasting(true)
    setBcastResult(null)
    const res  = await fetch('/api/payslips/broadcast', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ tenant_id: tenantId, month: bcastMonth, year: bcastYear }),
    })
    const data = await res.json()
    setBcastResult(data)
    setBcasting(false)
  }

  // Payslips for the selected broadcast month (for the preview count)
  const broadcastPreview = payslips.filter(
    ps => ps.month === bcastMonth && ps.year === bcastYear
  )

  if (tenantLoading || loading) return <Spinner />

  const validRows   = importRows.filter(r => r.employee && r.gross > 0 && r.net > 0)
  const skippedRows = importRows.filter(r => !r.employee || r.gross <= 0 || r.net <= 0)

  return (
    <div>
      <PageHeader
        title="Payslips"
        sub="Monthly payslip records"
        action={
          <div className="flex gap-2">
            <Button variant="ghost" onClick={() => { setShowBroadcast(true); setShowImport(false); setShowForm(false); setBcastResult(null) }}>
              <Send size={14} /> Send payday message
            </Button>
            <Button variant="ghost" onClick={() => { setShowImport(true); setShowForm(false); setShowBroadcast(false) }}>
              <Upload size={14} /> Import CSV
            </Button>
            <Button onClick={() => { setShowForm(true); setShowImport(false); setShowBroadcast(false) }}>
              <Plus size={14} /> Add payslip
            </Button>
          </div>
        }
      />

      {/* ── Payday broadcast panel ── */}
      {showBroadcast && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-sp-text">Send payday message</h2>
              <p className="text-xs text-sp-muted mt-0.5">Sends each employee their payslip summary on WhatsApp</p>
            </div>
            <button onClick={() => { setShowBroadcast(false); setBcastResult(null) }} className="text-sp-muted hover:text-sp-text"><X size={14} /></button>
          </div>

          <div className="flex gap-3 mb-4">
            <div className="flex-1">
              <label className="text-xs text-sp-muted mb-1 block">Month</label>
              <select value={bcastMonth} onChange={e => { setBcastMonth(e.target.value); setBcastResult(null) }} className="input">
                {MONTHS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div className="w-28">
              <label className="text-xs text-sp-muted mb-1 block">Year</label>
              <input type="number" value={bcastYear} onChange={e => { setBcastYear(parseInt(e.target.value) || now.getFullYear()); setBcastResult(null) }} className="input" />
            </div>
          </div>

          {/* Preview */}
          <div className="mb-4 rounded-lg border border-sp-border p-3">
            {broadcastPreview.length === 0 ? (
              <p className="text-xs text-sp-muted">No payslips loaded for {bcastMonth} {bcastYear}. Import or add them first.</p>
            ) : (
              <>
                <p className="text-xs text-sp-text mb-2 font-medium">{broadcastPreview.length} employee{broadcastPreview.length !== 1 ? 's' : ''} will receive a WhatsApp message:</p>
                <div className="space-y-1 max-h-36 overflow-y-auto">
                  {broadcastPreview.map(ps => {
                    const emp = ps.employees as any
                    return (
                      <div key={ps.id} className="flex items-center justify-between text-xs">
                        <span className="text-sp-text">{emp?.name || emp?.phone || '—'}</span>
                        <span className="text-sp-accent font-medium">₦{(ps.net_pay ?? 0).toLocaleString()}</span>
                      </div>
                    )
                  })}
                </div>
              </>
            )}
          </div>

          {/* Result */}
          {bcastResult && (
            <div className={`mb-4 rounded-lg p-3 text-xs ${bcastResult.failed === 0 ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
              {bcastResult.failed === 0
                ? `✓ Sent to all ${bcastResult.sent} employee${bcastResult.sent !== 1 ? 's' : ''}. They're seeing it on WhatsApp now.`
                : `Sent ${bcastResult.sent} of ${bcastResult.total}. ${bcastResult.failed} failed — check those employees have a valid phone number.`}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => { setShowBroadcast(false); setBcastResult(null) }}>Cancel</Button>
            <Button
              onClick={sendBroadcast}
              disabled={broadcastPreview.length === 0 || bcasting || !!bcastResult}
            >
              {bcasting ? 'Sending…' : bcastResult ? '✓ Sent' : `Send to ${broadcastPreview.length} employee${broadcastPreview.length !== 1 ? 's' : ''}`}
            </Button>
          </div>
        </Card>
      )}

      {/* ── Manual add form ── */}
      {showForm && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-sp-text">New payslip</h2>
            <button onClick={() => setShowForm(false)} className="text-sp-muted hover:text-sp-text"><X size={14} /></button>
          </div>
          {error && <p className="mb-3 text-xs text-red-400">{error}</p>}
          <form onSubmit={addPayslip} className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs text-sp-muted mb-1 block">Employee *</label>
              <select required value={form.employee_id} onChange={e => setForm(p => ({ ...p, employee_id: e.target.value }))} className="input">
                <option value="">Select employee…</option>
                {employees.map(emp => <option key={emp.id} value={emp.id}>{emp.name || emp.phone}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Month</label>
              <select value={form.month} onChange={e => setForm(p => ({ ...p, month: e.target.value }))} className="input">
                {MONTHS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Year</label>
              <input type="number" value={form.year} onChange={e => setForm(p => ({ ...p, year: parseInt(e.target.value) || now.getFullYear() }))} className="input" />
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Gross pay (₦) *</label>
              <input required type="number" placeholder="450000" value={form.gross_pay} onChange={e => setForm(p => ({ ...p, gross_pay: e.target.value }))} className="input" />
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Net pay (₦) *</label>
              <input required type="number" placeholder="340000" value={form.net_pay} onChange={e => setForm(p => ({ ...p, net_pay: e.target.value }))} className="input" />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-sp-muted mb-1 block">PDF URL (optional)</label>
              <input type="url" placeholder="https://…" value={form.file_url} onChange={e => setForm(p => ({ ...p, file_url: e.target.value }))} className="input" />
            </div>
            <div className="col-span-2 flex justify-end gap-2 pt-1">
              <Button variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Add payslip'}</Button>
            </div>
          </form>
        </Card>
      )}

      {/* ── CSV Import panel ── */}
      {showImport && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-sp-text">Import payslips from CSV</h2>
            <button onClick={() => { setShowImport(false); setImportRows([]) }} className="text-sp-muted hover:text-sp-text"><X size={14} /></button>
          </div>

          {/* Format selector */}
          <div className="mb-4">
            <label className="text-xs text-sp-muted mb-2 block">Your payroll software</label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {(Object.keys(FORMATS) as FormatKey[]).map(key => (
                <button
                  key={key}
                  onClick={() => { setImportFormat(key); setImportRows([]) }}
                  className={`rounded-lg border px-3 py-2 text-xs text-left transition-colors ${
                    importFormat === key
                      ? 'border-sp-accent bg-sp-accent/10 text-sp-accent'
                      : 'border-sp-border text-sp-muted hover:border-sp-accent/50'
                  }`}
                >
                  {FORMATS[key].label}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-sp-muted">{FORMATS[importFormat].note}</p>
          </div>

          {/* Template download */}
          <div className="mb-4 flex items-center gap-3 rounded-lg border border-dashed border-sp-border p-3">
            <Download size={14} className="shrink-0 text-sp-muted" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-sp-text">Expected columns: <span className="text-sp-accent font-mono">{FORMATS[importFormat].columns.join(', ')}</span></p>
            </div>
            <Button variant="ghost" onClick={downloadTemplate} className="shrink-0 text-xs">
              Download template
            </Button>
          </div>

          {/* File upload */}
          <div
            className="mb-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-sp-border p-6 text-center hover:border-sp-accent/50 transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            <Upload size={20} className="mb-2 text-sp-muted" />
            <p className="text-xs text-sp-text">Click to upload your CSV file</p>
            <p className="text-xs text-sp-muted mt-1">or drag and drop</p>
            <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
          </div>

          {/* Preview */}
          {importRows.length > 0 && (
            <div className="mb-4">
              <div className="flex items-center gap-3 mb-2">
                <p className="text-xs text-sp-text flex-1">
                  <span className="text-green-400 font-medium">{validRows.length} ready</span>
                  {skippedRows.length > 0 && <span className="text-red-400 ml-2">{skippedRows.length} will be skipped (no matching employee or missing pay)</span>}
                </p>
              </div>
              <div className="max-h-48 overflow-y-auto rounded-lg border border-sp-border text-xs">
                <table className="w-full">
                  <thead className="sticky top-0 bg-sp-surface">
                    <tr className="text-left text-sp-muted border-b border-sp-border">
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Employee</th>
                      <th className="px-3 py-2">Period</th>
                      <th className="px-3 py-2">Gross</th>
                      <th className="px-3 py-2">Net</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-sp-border">
                    {importRows.map((r, i) => (
                      <tr key={i} className={r.employee && r.gross > 0 ? '' : 'opacity-40'}>
                        <td className="px-3 py-2">
                          {r.employee && r.gross > 0
                            ? <CheckCircle2 size={12} className="text-green-400" />
                            : <AlertCircle size={12} className="text-red-400" />}
                        </td>
                        <td className="px-3 py-2 text-sp-text">{r.employee?.name ?? r.phone ?? '—'}</td>
                        <td className="px-3 py-2 text-sp-muted">{r.month} {r.year}</td>
                        <td className="px-3 py-2 text-sp-text">{r.gross > 0 ? formatCurrency(r.gross) : '—'}</td>
                        <td className="px-3 py-2 text-sp-accent">{r.net > 0 ? formatCurrency(r.net) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => { setShowImport(false); setImportRows([]) }}>Cancel</Button>
            <Button
              onClick={runImport}
              disabled={validRows.length === 0 || importing || importDone}
            >
              {importDone ? '✓ Imported' : importing ? 'Importing…' : `Import ${validRows.length} payslip${validRows.length !== 1 ? 's' : ''}`}
            </Button>
          </div>
        </Card>
      )}

      {/* ── Table ── */}
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
                    <td className="px-4 py-3 text-sp-muted">
                      {/\d{4}/.test(ps.month ?? '') ? ps.month : `${ps.month} ${ps.year}`}
                    </td>
                    <td className="px-4 py-3 text-sp-text">{formatCurrency(ps.gross_pay)}</td>
                    <td className="px-4 py-3 text-sp-accent font-medium">{formatCurrency(ps.net_pay)}</td>
                    <td className="px-4 py-3 text-sp-muted text-xs">{formatDate(ps.created_at)}</td>
                    <td className="px-4 py-3">
                      {ps.file_url ? (
                        <a href={ps.file_url} target="_blank" rel="noreferrer"
                          className="inline-flex items-center gap-1 text-sp-accent text-xs hover:underline">
                          View <ExternalLink size={11} />
                        </a>
                      ) : <span className="text-sp-muted text-xs">—</span>}
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
