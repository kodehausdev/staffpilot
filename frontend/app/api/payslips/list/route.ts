import { NextRequest, NextResponse } from 'next/server'

export async function GET(req: NextRequest) {
  const tenantId = req.nextUrl.searchParams.get('tenant_id')
  if (!tenantId) return NextResponse.json({ error: 'Missing tenant_id' }, { status: 400 })

  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_URL}/admin/payslips?tenant_id=${encodeURIComponent(tenantId)}`,
    { headers: { 'X-Admin-Key': process.env.BACKEND_ADMIN_KEY ?? '' } }
  )
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
