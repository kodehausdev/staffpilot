import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

export async function POST(req: NextRequest) {
  const { tenant_id, plan } = await req.json()

  if (!tenant_id || !plan) {
    return NextResponse.json({ error: 'Missing fields' }, { status: 400 })
  }

  const paystackKey = process.env.PAYSTACK_SECRET_KEY
  if (!paystackKey) {
    return NextResponse.json({ error: 'Billing not configured' }, { status: 503 })
  }

  // Fetch tenant email via tenant_admins
  const { data: adminRow } = await supabase
    .from('tenant_admins')
    .select('email')
    .eq('tenant_id', tenant_id)
    .eq('role', 'owner')
    .single()

  const PLAN_AMOUNTS: Record<string, number> = {
    growth:     15000000, // ₦150,000 in kobo
    enterprise: 0,
  }

  const amount = PLAN_AMOUNTS[plan]
  if (!amount) {
    return NextResponse.json({ error: 'Invalid plan' }, { status: 400 })
  }

  const res = await fetch('https://api.paystack.co/transaction/initialize', {
    method:  'POST',
    headers: {
      Authorization:  `Bearer ${paystackKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email:       adminRow?.email ?? 'unknown@example.com',
      amount,
      metadata:    { tenant_id, plan },
      callback_url: `${process.env.NEXT_PUBLIC_APP_URL}/billing/success`,
    }),
  })

  const data = await res.json()
  if (!data.status) {
    return NextResponse.json({ error: data.message }, { status: 500 })
  }

  return NextResponse.json({ authorization_url: data.data.authorization_url })
}
