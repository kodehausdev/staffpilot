import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

// Service role — can write to tenant_admins
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function POST(req: NextRequest) {
  const { user_id, email, company } = await req.json()

  if (!user_id || !email) {
    return NextResponse.json({ error: 'Missing fields' }, { status: 400 })
  }

  try {
    // If this user already has a tenant, return it — don't create a duplicate
    const { data: existing } = await supabase
      .from('tenant_admins')
      .select('tenant_id')
      .eq('user_id', user_id)
      .single()

    if (existing?.tenant_id) {
      return NextResponse.json({ tenant_id: existing.tenant_id })
    }

    // 1. Create tenant
    const { data: tenant, error: tenantErr } = await supabase
      .from('tenants')
      .insert({ name: company || email.split('@')[0], plan: 'starter' })
      .select()
      .single()

    if (tenantErr) throw tenantErr

    // 2. Link user as owner
    const { error: adminErr } = await supabase
      .from('tenant_admins')
      .insert({ tenant_id: tenant.id, user_id, email, role: 'owner' })

    if (adminErr) throw adminErr

    // 3. Create starter subscription record
    await supabase.from('subscriptions').insert({
      tenant_id: tenant.id,
      plan:      'starter',
      status:    'active',
    })

    return NextResponse.json({ tenant_id: tenant.id })
  } catch (err: any) {
    console.error('Setup error:', err)
    return NextResponse.json({ error: err.message }, { status: 500 })
  }
}