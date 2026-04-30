'use client'
import { useEffect, useState, useRef } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useTenant } from '@/lib/use-tenant'
import { Card, Button, PageHeader, Spinner, EmptyState } from '@/components/ui'
import { formatDate } from '@/lib/utils'
import { Upload, Trash2, FileText, AlertCircle } from 'lucide-react'
import type { HrDocument } from '@/lib/supabase'

const DOC_LIMITS: Record<string, number> = {
  starter:    3,
  growth:     10,
  enterprise: -1,
}

export default function DocsPage() {
  const { tenantId, plan, loading: tenantLoading } = useTenant()
  const supabase = createClient()
  const fileRef  = useRef<HTMLInputElement>(null)

  const [docs, setDocs]           = useState<HrDocument[]>([])
  const [loading, setLoading]     = useState(true)
  const [uploading, setUploading] = useState(false)
  const [title, setTitle]         = useState('')
  const [error, setError]         = useState('')
  const [success, setSuccess]     = useState('')
  const [deleting, setDeleting]   = useState<string | null>(null)

  useEffect(() => { if (tenantId) load() }, [tenantId])

  async function load() {
    setLoading(true)
    try {
      const { data } = await supabase
        .from('hr_documents')
        .select('*')
        .eq('tenant_id', tenantId)
        .order('uploaded_at', { ascending: false })
      setDocs(data ?? [])
    } finally {
      setLoading(false)
    }
  }

  async function upload(e: React.FormEvent) {
    e.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file || !title.trim()) return

    setUploading(true)
    setError('')
    setSuccess('')

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('title', title)
      formData.append('tenant_id', tenantId)

      const res  = await fetch('/api/docs/upload', { method: 'POST', body: formData })
      const body = await res.json().catch(() => ({}))

      if (!res.ok) throw new Error(body.detail || 'Upload failed')

      setTitle('')
      if (fileRef.current) fileRef.current.value = ''
      setSuccess(`"${title}" uploaded and indexed — employees can now ask questions about it on WhatsApp.`)
      load()
    } catch (err: any) {
      setError(err.message)
    }
    setUploading(false)
  }

  async function deleteDoc(doc: HrDocument) {
    setDeleting(doc.id)
    await supabase.from('hr_documents').delete().eq('id', doc.id)
    setDocs(prev => prev.filter(d => d.id !== doc.id))
    setDeleting(null)
  }

  if (tenantLoading || loading) return <Spinner />

  const docLimit  = DOC_LIMITS[plan] ?? 3
  const atLimit   = docLimit !== -1 && docs.length >= docLimit
  const limitLabel = docLimit === -1 ? 'Unlimited' : `${docs.length} / ${docLimit}`

  return (
    <div>
      <PageHeader
        title="HR documents"
        sub="Upload PDFs — they're indexed so employees can ask questions via WhatsApp"
      />

      {/* Upload card */}
      <Card className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-sp-text">Upload document</h2>
          <span className={`text-xs px-2 py-0.5 rounded-full ${atLimit ? 'bg-red-500/10 text-red-400' : 'bg-sp-border text-sp-muted'}`}>
            {limitLabel} documents
          </span>
        </div>

        {error   && <p className="mb-3 text-xs text-red-400">{error}</p>}
        {success && <p className="mb-3 text-xs text-green-400">{success}</p>}

        {atLimit ? (
          <div className="flex items-start gap-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3">
            <AlertCircle size={14} className="shrink-0 text-yellow-400 mt-0.5" />
            <div>
              <p className="text-xs text-yellow-300 font-medium">Document limit reached</p>
              <p className="text-xs text-yellow-400/80 mt-0.5">
                Your {plan} plan allows up to {docLimit} documents. Delete an existing one to upload a new version, or upgrade your plan for more.
              </p>
            </div>
          </div>
        ) : (
          <form onSubmit={upload} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label className="text-xs text-sp-muted mb-1 block">Document title *</label>
              <input
                required
                placeholder="Employee handbook 2026, Leave policy…"
                value={title}
                onChange={e => setTitle(e.target.value)}
                className="input w-full"
              />
            </div>
            <div className="flex-1">
              <label className="text-xs text-sp-muted mb-1 block">PDF file *</label>
              <input
                required
                ref={fileRef}
                type="file"
                accept=".pdf"
                className="block w-full text-sm text-sp-muted file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-sp-border file:text-sp-text hover:file:bg-sp-accent-dim cursor-pointer"
              />
            </div>
            <Button type="submit" disabled={uploading} className="shrink-0">
              <Upload size={14} />
              {uploading ? 'Indexing…' : 'Upload & index'}
            </Button>
          </form>
        )}

        {/* How it works hint */}
        {!atLimit && docs.length === 0 && (
          <p className="mt-3 text-[11px] text-sp-muted">
            Upload a PDF and employees can instantly ask questions like "do I have HMO?" or "how many sick days do I get?" via WhatsApp.
          </p>
        )}
      </Card>

      {/* Documents table */}
      <Card className="p-0 overflow-hidden">
        {docs.length === 0 ? (
          <div className="p-5"><EmptyState message="No documents uploaded yet" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-sp-muted border-b border-sp-border">
                <th className="px-5 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Uploaded</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sp-border">
              {docs.map(doc => (
                <tr key={doc.id} className="hover:bg-sp-border/30 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2.5">
                      <FileText size={14} className="text-sp-muted shrink-0" />
                      <span className="text-sp-text font-medium">{doc.title}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sp-muted text-xs">{formatDate(doc.uploaded_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => deleteDoc(doc)}
                      disabled={deleting === doc.id}
                    >
                      <Trash2 size={12} />
                      {deleting === doc.id ? 'Deleting…' : 'Delete'}
                    </Button>
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
