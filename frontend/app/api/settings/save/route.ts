import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'
import { requireTenantAdmin } from '@/lib/supabase-route'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function POST(req: NextRequest) {
  const { tenant_id, name, whatsapp_number, meta_code } = await req.json()

  if (!tenant_id) {
    return NextResponse.json({ error: 'Missing tenant_id' }, { status: 400 })
  }

  const admin = await requireTenantAdmin(tenant_id)
  if (!admin) {
    return NextResponse.json({ error: 'Not authorized for this tenant' }, { status: 403 })
  }

  // If meta_code provided: exchange it for phone_number_id via backend
  if (meta_code) {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/settings/whatsapp/onboard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id, meta_code }),
      })
      
      if (!res.ok) {
        const data = await res.json()
        return NextResponse.json({ error: data.error || 'Failed to connect WhatsApp account' }, { status: 400 })
      }
      
      const data = await res.json()
      const exchanged_whatsapp_number = data.whatsapp_number
      
      // Update tenant name if provided
      if (name) {
        const { error } = await supabase
          .from('tenants')
          .update({ name })
          .eq('id', tenant_id)
        
        if (error) {
          return NextResponse.json({ error: error.message }, { status: 500 })
        }
      }
      
      return NextResponse.json({ ok: true, whatsapp_number: exchanged_whatsapp_number })
    } catch (e: any) {
      return NextResponse.json({ error: e?.message || 'Code exchange failed' }, { status: 500 })
    }
  }

  // Fallback: manual whatsapp_number update (no code exchange)
  const { error } = await supabase
    .from('tenants')
    .update({ name, whatsapp_number })
    .eq('id', tenant_id)

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ ok: true, whatsapp_number })
}
