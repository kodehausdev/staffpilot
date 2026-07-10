import { NextRequest, NextResponse } from 'next/server'
import { backendUrl } from '@/lib/utils'

export async function POST(req: NextRequest) {
  const { id, status, reason } = await req.json()

  const res = await fetch(backendUrl(`/admin/leave/${id}`), {
    method:  'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'x-admin-key':  process.env.BACKEND_ADMIN_KEY ?? '',
    },
    body: JSON.stringify({ status, reason }),
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
