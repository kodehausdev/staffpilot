'use client'
import { useEffect, useState, useRef } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useTenant } from '@/lib/use-tenant'
import { Card, Button, PageHeader, Spinner, EmptyState } from '@/components/ui'
import { formatDate } from '@/lib/utils'
import { Upload, Trash2, FileText } from 'lucide-react'
import type { HrDocument } from '@/lib/supabase'

export default function DocsPage() {
  const { tenantId, loading: tenantLoading } = useTenant()
  const supabase  = createClient()
  const fileRef   = useRef<HTMLInputElement>(null)

  const [docs, setDocs]       = useState<HrDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [title, setTitle]     = useState('')
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    if (!tenantId) return
    load()
  }, [tenantId])

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

      const res = await fetch('/api/docs/upload', {
        method: 'POST',
        body:   formData,
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Upload failed')
      }

      setTitle('')
      if (fileRef.current) fileRef.current.value = ''
      setSuccess(`"${title}" uploaded and indexed for AI Q&A.`)
      load()
    } catch (err: any) {
      setError(err.message)
    }
    setUploading(false)
  }

  async function deleteDoc(doc: HrDocument) {
    await supabase.from('hr_documents').delete().eq('id', doc.id)
    setDocs(prev => prev.filter(d => d.id !== doc.id))
  }

  if (tenantLoading || loading) return <Spinner />

  return (
    <div>
      <PageHeader
        title="HR documents"
        sub="Upload PDFs — they're indexed so employees can ask questions via WhatsApp"
      />

      <Card className="mb-6">
        <h2 className="text-sm font-semibold text-sp-text mb-4">Upload document</h2>

        {error   && <p className="mb-3 text-xs text-red-400">{error}</p>}
        {success && <p className="mb-3 text-xs text-green-400">{success}</p>}

        <form onSubmit={upload} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="text-xs text-sp-muted mb-1 block">Document title *</label>
            <input
              required
              placeholder="Leave policy 2024, Employee handbook…"
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
            {uploading ? 'Uploading…' : 'Upload & index'}
          </Button>
        </form>
      </Card>

      <Card className="p-0 overflow-hidden">
        {docs.length === 0 ? (
          <div className="p-5"><EmptyState message="No documents uploaded yet" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-sp-muted border-b border-sp-border">
                <th className="px-5 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Uploaded</th>
                <th className="px-4 py-3" />
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
                    >
                      <Trash2 size={12} /> Delete
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
