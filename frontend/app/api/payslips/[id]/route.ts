import { NextRequest, NextResponse } from 'next/server'

export async function DELETE(req: NextRequest, { params }: { params: { id: string } }) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/admin/payslips/${params.id}`, {
    method:  'DELETE',
    headers: { 'X-Admin-Key': process.env.BACKEND_ADMIN_KEY ?? '' },
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
