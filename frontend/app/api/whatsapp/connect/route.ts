import { NextRequest, NextResponse } from 'next/server'
import { requireTenantAdmin } from '@/lib/supabase-route'
import { backendUrl } from '@/lib/utils'

export async function POST(req: NextRequest) {
  console.log('=== [NEXT.JS BRIDGE] CONNECT API HIT ===')

  try {
    const body = await req.json()
    console.log('[NEXT.JS BRIDGE] Incoming Payload Data:', body)

    const { tenant_id, code } = body

    if (!tenant_id || !code) {
      console.warn('[NEXT.JS BRIDGE] Missing requirements. Tenant:', tenant_id, 'Code:', !!code)
      return NextResponse.json({ error: 'tenant_id and code are required' }, { status: 400 })
    }

    const admin = await requireTenantAdmin(tenant_id)
    if (!admin) {
      return NextResponse.json({ error: 'Not authorized for this tenant' }, { status: 403 })
    }

    const targetBackendUrl = backendUrl('/settings/whatsapp/onboard')
    console.log('[NEXT.JS BRIDGE] Forwarding Request To FastAPI:', targetBackendUrl)

    // Forwarding payload securely to the FastAPI application layer
    const backendRes = await fetch(targetBackendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': process.env.BACKEND_ADMIN_KEY || ''
      },
      body: JSON.stringify({
        tenant_id: tenant_id,
        meta_code: code
      })
    })

    console.log('[NEXT.JS BRIDGE] FastAPI Response Status Code:', backendRes.status)
    const backendData = await backendRes.json()
    console.log('[NEXT.JS BRIDGE] FastAPI Response Body Data:', backendData)

    if (!backendRes.ok) {
      return NextResponse.json(
        { error: backendData.detail || 'Failed to exchange Meta token on backend.' }, 
        { status: backendRes.status }
      )
    }

    return NextResponse.json({
      phone_number_id:     backendData.whatsapp_number,
      webhook_subscribed:  backendData.webhook_subscribed,
    })

  } catch (err: any) {
    console.error('[NEXT.JS BRIDGE] Catastrophic connection failure:', err)
    return NextResponse.json({ error: err?.message ?? 'Internal bridge error' }, { status: 500 })
  }
}
