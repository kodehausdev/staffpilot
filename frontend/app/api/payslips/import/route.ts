import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  const body = await req.json()
  const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/admin/payslips/import`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Key': process.env.BACKEND_ADMIN_KEY ?? '' },
    body:    JSON.stringify(body),
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
