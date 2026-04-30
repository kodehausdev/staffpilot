import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

const SIGNED_URL_TTL = 60 * 60 * 24 * 365  // 1 year in seconds

export async function POST(req: NextRequest) {
  const form      = await req.formData()
  const file      = form.get('file') as File | null
  const payslipId = form.get('payslip_id') as string | null

  if (!file || !payslipId) {
    return NextResponse.json({ error: 'Missing file or payslip_id' }, { status: 400 })
  }
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    return NextResponse.json({ error: 'Only PDF files are supported' }, { status: 400 })
  }

  // Fetch the payslip to get tenant + employee + month for a clean path
  const { data: slip, error: slipErr } = await supabase
    .from('payslips')
    .select('tenant_id, employee_id, month, year')
    .eq('id', payslipId)
    .single()

  if (slipErr || !slip) {
    return NextResponse.json({ error: 'Payslip not found' }, { status: 404 })
  }

  const path = `${slip.tenant_id}/${slip.employee_id}/${slip.month}-${slip.year}.pdf`

  const bytes  = await file.arrayBuffer()
  const buffer = Buffer.from(bytes)

  const { error: uploadErr } = await supabase.storage
    .from('payslips')
    .upload(path, buffer, { contentType: 'application/pdf', upsert: true })

  if (uploadErr) {
    return NextResponse.json({ error: uploadErr.message }, { status: 500 })
  }

  const { data: signed, error: signErr } = await supabase.storage
    .from('payslips')
    .createSignedUrl(path, SIGNED_URL_TTL)

  if (signErr || !signed) {
    return NextResponse.json({ error: 'Could not generate download URL' }, { status: 500 })
  }

  await supabase
    .from('payslips')
    .update({ file_url: signed.signedUrl })
    .eq('id', payslipId)

  return NextResponse.json({ url: signed.signedUrl })
}
