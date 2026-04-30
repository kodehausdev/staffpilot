import { NextRequest, NextResponse } from 'next/server'

export async function GET(req: NextRequest) {
  const reference = req.nextUrl.searchParams.get('reference')
  if (!reference) {
    return NextResponse.json({ error: 'Missing reference' }, { status: 400 })
  }

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL
  const res = await fetch(`${backendUrl}/billing/verify?reference=${encodeURIComponent(reference)}`)
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
