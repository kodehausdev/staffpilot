import { NextRequest, NextResponse } from 'next/server'
import { backendUrl } from '@/lib/utils'

export async function POST(req: NextRequest) {
  const adminKey   = process.env.BACKEND_ADMIN_KEY

  if (!adminKey) {
    return NextResponse.json({ error: 'Server misconfigured: missing BACKEND_ADMIN_KEY' }, { status: 500 })
  }

  // Read fields and file from the incoming form
  const incoming = await req.formData()
  const file      = incoming.get('file') as File | null
  const title     = incoming.get('title') as string | null
  const tenantId  = incoming.get('tenant_id') as string | null

  if (!file || !title || !tenantId) {
    return NextResponse.json({ error: 'Missing file, title, or tenant_id' }, { status: 400 })
  }

  // Rebuild FormData so Node.js sets the correct multipart boundary
  const outgoing = new FormData()
  outgoing.append('file',      file,     file.name)
  outgoing.append('title',     title)
  outgoing.append('tenant_id', tenantId)

  let res: Response
  try {
    res = await fetch(backendUrl('/admin/docs/upload'), {
      method:  'POST',
      headers: { 'X-Admin-Key': adminKey },
      body:    outgoing,
    })
  } catch (err: any) {
    console.error('[docs/upload] fetch to backend failed:', err)
    return NextResponse.json({ error: 'Could not reach backend: ' + err.message }, { status: 502 })
  }

  const text = await res.text()
  console.log('[docs/upload] backend status:', res.status, 'body:', text)

  let data: unknown
  try { data = JSON.parse(text) } catch { data = { detail: text } }

  return NextResponse.json(data, { status: res.status })
}
