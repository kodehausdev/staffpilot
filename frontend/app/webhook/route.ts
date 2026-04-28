import { NextRequest, NextResponse } from 'next/server'

const VERIFY_TOKEN = process.env.WHATSAPP_VERIFY_TOKEN ?? 'staffpilot_hookup'
const BACKEND_URL  = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000'

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const mode      = searchParams.get('hub.mode')
  const token     = searchParams.get('hub.verify_token')
  const challenge = searchParams.get('hub.challenge')

  if (mode === 'subscribe' && token === VERIFY_TOKEN && challenge) {
    return new NextResponse(challenge, { status: 200 })
  }
  return new NextResponse('Forbidden', { status: 403 })
}

export async function POST(req: NextRequest) {
  const body = await req.text()
  const res  = await fetch(`${BACKEND_URL}/webhook`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
