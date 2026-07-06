'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { CheckCircle2, XCircle, Loader2, ArrowRight } from 'lucide-react'

const PLAN_LABEL: Record<string, string> = { starter: 'Starter', growth: 'Growth', enterprise: 'Enterprise' }
const PLAN_STAFF: Record<string, number> = { starter: 30, growth: 150, enterprise: 999 }

function SuccessContent() {
  const params = useSearchParams()
  const router = useRouter()
  const { tenantAdmin, refreshTenantAdmin } = useAuth()

  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying')
  const [plan, setPlan]     = useState('')
  const [error, setError]   = useState('')

  useEffect(() => {
    const reference = params.get('reference') || params.get('trxref')
    if (!reference) {
      setStatus('error')
      setError('No payment reference was provided.')
      return
    }
    fetch(`/api/billing/verify?reference=${encodeURIComponent(reference)}`)
      .then(async r => ({ ok: r.ok, data: await r.json() }))
      .then(async ({ ok, data }) => {
        if (!ok) {
          setStatus('error')
          setError(data.error ?? 'Payment could not be verified.')
          return
        }
        // Wait for the refreshed plan to actually land in context before the
        // "Go to dashboard" button becomes clickable — otherwise a fast click
        // can navigate to Settings before the new plan is there to show,
        // and it looks stale until a hard reload re-fetches from scratch.
        await refreshTenantAdmin()
        setPlan(data.plan ?? '')
        setStatus('success')
      })
      .catch(() => {
        setStatus('error')
        setError('Network error while verifying payment.')
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const companyName = tenantAdmin?.tenants?.name ?? 'Your company'
  const planLabel    = PLAN_LABEL[plan] ?? plan
  const staffLimit    = PLAN_STAFF[plan]

  return (
    <div className="w-full max-w-sm">
      <div className="bg-sp-surface border border-sp-border rounded-2xl p-7 text-center">

        {status === 'verifying' && (
          <>
            <Loader2 size={28} className="animate-spin text-sp-muted mx-auto mb-4" />
            <p className="text-sm text-sp-muted">Confirming your payment…</p>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle size={40} className="text-red-400 mx-auto mb-4" />
            <h1 className="text-lg font-semibold text-sp-text mb-1">Couldn't confirm payment</h1>
            <p className="text-sm text-sp-muted mb-6">{error}</p>
            <button
              onClick={() => router.push('/dashboard/settings')}
              className="w-full py-2.5 rounded-lg border border-sp-border text-sp-text text-sm font-medium hover:border-sp-accent hover:text-sp-accent transition"
            >
              Back to Settings
            </button>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="w-14 h-14 rounded-full bg-sp-accent-dim flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 size={28} className="text-sp-accent" />
            </div>
            <h1 className="text-lg font-semibold text-sp-text mb-1">{companyName} is upgraded!</h1>
            <p className="text-sm text-sp-muted mb-6">
              {planLabel} plan{staffLimit ? ` · up to ${staffLimit} staff` : ''}
            </p>

            <div className="space-y-2.5 text-left mb-7">
              {[
                'Payment received',
                `Plan upgraded to ${planLabel}`,
                'Staff & feature limits increased',
              ].map(item => (
                <div key={item} className="flex items-center gap-2.5 text-sm text-sp-text">
                  <CheckCircle2 size={15} className="text-green-400 shrink-0" />
                  {item}
                </div>
              ))}
            </div>

            <button
              onClick={() => router.push('/dashboard/settings')}
              className="w-full py-2.5 rounded-lg bg-sp-accent text-white text-sm font-medium hover:bg-emerald-400 transition flex items-center justify-center gap-2"
            >
              Go to dashboard <ArrowRight size={14} />
            </button>
          </>
        )}
      </div>

      <p className="text-center text-xs text-sp-muted mt-5">
        Powered by Optipropose Studio · Abuja, Nigeria
      </p>
    </div>
  )
}

export default function BillingSuccessPage() {
  return (
    <div className="min-h-screen bg-sp-bg flex items-center justify-center p-4">
      <Suspense fallback={<div className="text-sp-muted text-sm">Loading...</div>}>
        <SuccessContent />
      </Suspense>
    </div>
  )
}
