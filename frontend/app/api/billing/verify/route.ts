import { NextRequest, NextResponse } from 'next/server'
import { backendUrl } from '@/lib/utils'

export async function GET(req: NextRequest) {
  const reference = req.nextUrl.searchParams.get('reference')
  if (!reference) {
    return NextResponse.json({ error: 'Missing reference' }, { status: 400 })
  }

  const res = await fetch(backendUrl(`/billing/verify?reference=${encodeURIComponent(reference)}`))
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
