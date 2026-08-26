import { NextRequest, NextResponse } from 'next/server'
import { requireTenantAdmin } from '@/lib/supabase-route'
import { backendUrl } from '@/lib/utils'

export async function POST(req: NextRequest) {
  console.log('=== [NEXT.JS BRIDGE] CONNECT API HIT ===')

  try {
    const body = await req.json()
    const { tenant_id, code, pin } = body

    if (!tenant_id || !code) {
      return NextResponse.json({ error: 'tenant_id and code are required' }, { status: 400 })
    }

    if (!pin || !/^\d{6}$/.test(pin)) {
      return NextResponse.json({ error: 'A 6-digit PIN is required.' }, { status: 400 })
    }

    const admin = await requireTenantAdmin(tenant_id)
    if (!admin) {
      return NextResponse.json({ error: 'Not authorized for this tenant' }, { status: 403 })
    }

    const targetBackendUrl = backendUrl('/settings/whatsapp/onboard')
    console.log('[NEXT.JS BRIDGE] Forwarding to FastAPI:', targetBackendUrl)

    const backendRes = await fetch(targetBackendUrl, {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key':  process.env.BACKEND_ADMIN_KEY || '',
      },
      body: JSON.stringify({
        tenant_id: tenant_id,
        meta_code: code,
        pin:       pin,
      }),
    })

    const backendData = await backendRes.json()
    console.log('[NEXT.JS BRIDGE] FastAPI response:', backendRes.status, backendData)

    if (!backendRes.ok) {
      return NextResponse.json(
        { error: backendData.detail || 'Failed to connect WhatsApp account.' },
        { status: backendRes.status }
      )
    }

    return NextResponse.json({
      phone_number_id:      backendData.whatsapp_number,
      display_phone_number: backendData.display_phone_number,
      verified_name:        backendData.verified_name,
      waba_id:              backendData.waba_id,
    })

  } catch (err: any) {
    console.error('[NEXT.JS BRIDGE] Error:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal bridge error' }, { status: 500 })
  }
}
