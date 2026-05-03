import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function POST(req: NextRequest) {
  const { tenant_id, name, whatsapp_number } = await req.json()

  if (!tenant_id) {
    return NextResponse.json({ error: 'Missing tenant_id' }, { status: 400 })
  }

  const { error } = await supabase
    .from('tenants')
    .update({ name, whatsapp_number })
    .eq('id', tenant_id)

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ ok: true })
}
