'use client'

import { useEffect, useState, useMemo } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useTenant } from '@/lib/use-tenant'
import { useAuth } from '@/lib/auth-context'
import { Button, Badge, PageHeader, Spinner } from '@/components/ui'
import { Save, MessageSquare, CreditCard, CheckCircle2, AlertTriangle, Clock, ChevronDown } from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────

declare global {
  interface Window {
    fbAsyncInit: () => void
    FB: any
  }
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PLAN_STYLES: Record<string, string> = {
  starter:    'bg-sp-border text-sp-muted',
  growth:     'bg-sp-accent-dim text-sp-accent',
  enterprise: 'bg-purple-900/40 text-purple-400',
}

const PLAN_LIMITS: Record<string, { staff: number; price: string }> = {
  starter:    { staff: 30,  price: '₦50,000/mo'  },
  growth:     { staff: 150, price: '₦150,000/mo' },
  enterprise: { staff: 999, price: 'Custom'       },
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const { tenantAdmin, user, refreshTenantAdmin }                = useAuth()
  const { tenantId: hookTenantId, plan, loading: tenantLoading } = useTenant()
  const supabase                                                 = useMemo(() => createClient(), [])

  // Fallback to auth context if useTenant hasn't hydrated yet
  const tenantId = hookTenantId || tenantAdmin?.tenant_id || ''

  const [name, setName]               = useState('')
  const [waNumber, setWaNumber]       = useState('')
  const [saving, setSaving]           = useState(false)
  const [saved, setSaved]             = useState(false)
  const [error, setError]             = useState('')
  const [loading, setLoading]         = useState(true)
  const [sdkReady, setSdkReady]       = useState(false)
  const [waConnected, setWaConnected] = useState(false)
  const [subscribeWarning, setSubscribeWarning] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [fullName, setFullName]         = useState('')
  const [savingProfile, setSavingProfile] = useState(false)
  const [profileSaved, setProfileSaved]   = useState(false)

  const tenantCreatedAt = tenantAdmin?.tenants?.created_at
  const hoursLeft = tenantCreatedAt
    ? Math.max(0, 24 - Math.floor((Date.now() - new Date(tenantCreatedAt).getTime()) / 36e5))
    : null

  // ── Sync profile name from auth context once it loads ─────────────────────
  useEffect(() => {
    setFullName(tenantAdmin?.full_name ?? '')
  }, [tenantAdmin?.full_name])

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault()
    setSavingProfile(true)
    setProfileSaved(false)
    try {
      const res = await fetch('/api/profile/save', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ full_name: fullName }),
      })
      if (res.ok) {
        await refreshTenantAdmin()
        setProfileSaved(true)
        setTimeout(() => setProfileSaved(false), 3000)
      }
    } finally {
      setSavingProfile(false)
    }
  }

  // ── Load tenant data ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!tenantId) {
      if (!tenantLoading) setLoading(false)
      return
    }
    supabase
      .from('tenants')
      .select('name, whatsapp_number')
      .eq('id', tenantId)
      .single()
      .then(({ data }: { data: { name: string | null; whatsapp_number: string | null } | null }) => {
        if (data) {
          setName(data.name ?? '')
          setWaNumber(data.whatsapp_number ?? '')
          setWaConnected(!!data.whatsapp_number)
        }
        setLoading(false)
      })
        }, [tenantId, tenantLoading, supabase])

  // ── Meta JS SDK — runs once on mount only ─────────────────────────────────
  useEffect(() => {
    // Listen for phone_number_id sent via postMessage from Meta popup
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== 'https://www.facebook.com') return
      try {
        const msg = typeof event.data === 'string' ? JSON.parse(event.data) : event.data
        if (msg?.type === 'WA_EMBEDDED_SIGNUP' && msg?.event === 'FINISH') {
          const phoneNumberId = msg?.data?.phone_number_id
          if (phoneNumberId) savePhoneNumberId(phoneNumberId)
        }
      } catch {}
    }
    window.addEventListener('message', handleMessage)

    const initSDK = () => {
      window.FB.init({
        appId:   process.env.NEXT_PUBLIC_META_APP_ID!,
        cookie:  true,
        xfbml:   true,
        version: 'v20.0',
      })
      setSdkReady(true)
    }

    if (window.FB) {
      // SDK already on page (hot reload / back navigation)
      initSDK()
    } else {
      window.fbAsyncInit = initSDK
      if (!document.getElementById('facebook-jssdk')) {
        const script  = document.createElement('script')
        script.id     = 'facebook-jssdk'
        script.src    = 'https://connect.facebook.net/en_US/sdk.js'
        script.async  = true
        script.defer  = true
        document.head.appendChild(script)
      }
    }

    return () => window.removeEventListener('message', handleMessage)
  }, []) // ← empty deps: SDK only injected once

  // ── Embedded signup trigger ────────────────────────────────────────────────
  function handleEmbeddedSignup() {
    if (!window.FB) {
      setError('Meta SDK is still loading — please wait a moment.')
      return
    }

    // Safety net: re-init if FB object exists but init() never completed
    try {
      window.FB.getLoginStatus(() => {})
    } catch {
      window.FB.init({
        appId:   process.env.NEXT_PUBLIC_META_APP_ID!,
        cookie:  true,
        xfbml:   true,
        version: 'v20.0',
      })
    }

    setError('')
    window.FB.login(
      (response: any) => {
        if (response.authResponse?.code) {
          exchangeCode(response.authResponse.code)
        } else if (response.status !== 'unknown') {
          setError('WhatsApp connection was cancelled. Try again.')
        }
      },
      {
        config_id:                      process.env.NEXT_PUBLIC_META_CONFIG_ID!,
        response_type:                  'code',
        override_default_response_type: true,
        extras: { sessionInfoVersion:   2 },
      },
    )
  }

  // ── Exchange Meta code → phone_number_id via backend ──────────────────────
  async function exchangeCode(code: string) {
    if (!tenantId) {
      setError('Session not ready — please refresh and try again.')
      return
    }
    setSaving(true)
    setError('')
    try {
      const res = await fetch('/api/whatsapp/connect', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ tenant_id: tenantId, code }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error ?? 'Failed to connect WhatsApp — check server logs.')
      } else {
        setWaNumber(data.phone_number_id)
        setWaConnected(true)
        setSubscribeWarning(data.webhook_subscribed === false)
        setSaved(true)
        setTimeout(() => setSaved(false), 4000)
      }
    } catch (e: any) {
      setError(e?.message ?? 'Network error.')
    } finally {
      setSaving(false)
    }
  }

  // ── Fallback: Meta sends phone_number_id directly via postMessage ──────────
  async function savePhoneNumberId(phoneNumberId: string) {
    if (!tenantId) return
    setSaving(true)
    setError('')
    try {
      const res = await fetch('/api/settings/save', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ tenant_id: tenantId, whatsapp_number: phoneNumberId }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error ?? 'Failed to save WhatsApp number.')
      } else {
        setWaNumber(phoneNumberId)
        setWaConnected(true)
        setSaved(true)
        setTimeout(() => setSaved(false), 4000)
      }
    } catch (e: any) {
      setError(e?.message ?? 'Network error.')
    } finally {
      setSaving(false)
    }
  }

  // ── Manual save ────────────────────────────────────────────────────────────
  async function save(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      const res = await fetch('/api/settings/save', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ tenant_id: tenantId, name, whatsapp_number: waNumber }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error ?? 'Save failed — please try again')
      } else {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
      }
    } catch (e: any) {
      setError(e?.message ?? 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  // ─────────────────────────────────────────────────────────────────────────

  if (tenantLoading || loading) return <Spinner />

  const limits = PLAN_LIMITS[plan] ?? PLAN_LIMITS.starter

  return (
    <div>
      <PageHeader title="Settings" sub="Company configuration and billing" />

      <div className="space-y-6">

        {/* ── Company details ── */}
        <div className="bento-luxury">
          <h2 className="text-sm font-semibold text-sp-text mb-4">Company details</h2>

          {error && <p className="mb-3 text-xs text-red-400">{error}</p>}
          {saved && (
            <p className="mb-3 text-xs text-green-400 flex items-center gap-1.5">
              <CheckCircle2 size={12} /> WhatsApp connected successfully.
            </p>
          )}

          {/* WhatsApp activation */}
          <div className="mb-6 pb-6 border-b border-sp-border/50 max-w-md">
            <label className="text-xs text-sp-muted mb-2 block font-medium">
              WhatsApp Business
            </label>

            {waConnected ? (
              <div className="flex items-center gap-3 rounded-xl border border-green-500/30 bg-green-500/10 px-4 py-3">
                <CheckCircle2 size={15} className="text-green-400 shrink-0" />
                <div>
                  <p className="text-xs font-medium text-green-400">Connected</p>
                  <p className="text-[11px] text-sp-muted font-mono mt-0.5">{waNumber}</p>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3">
                <Clock size={15} className="text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-medium text-amber-400">Activation in progress</p>
                  <p className="text-[11px] text-sp-muted mt-0.5">
                    {hoursLeft !== null && hoursLeft > 0
                      ? `We assign your number by hand — expect it live within ${hoursLeft}h.`
                      : "We assign your number by hand — we've been notified this one's overdue."}
                  </p>
                </div>
              </div>
            )}

            {subscribeWarning && (
              <div className="mt-2 flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2.5">
                <AlertTriangle size={13} className="text-amber-400 shrink-0 mt-0.5" />
                <p className="text-[11px] text-amber-400">
                  Number connected, but Meta didn't confirm the webhook subscription — messages to this
                  number may not reach the bot yet. Try Reconnect below, or contact support if it persists.
                </p>
              </div>
            )}

            {/* Advanced: bring-your-own WABA via Meta embedded signup */}
            <button
              type="button"
              onClick={() => setShowAdvanced(v => !v)}
              className="mt-3 flex items-center gap-1 text-[11px] text-sp-muted hover:text-sp-text transition-colors"
            >
              <ChevronDown size={11} className={`transition-transform duration-200 ${showAdvanced ? 'rotate-180' : ''}`} />
              Already have your own verified Meta Business Account?
            </button>

            {showAdvanced && (
              <div className="mt-3">
                <button
                  type="button"
                  onClick={handleEmbeddedSignup}
                  disabled={saving || !sdkReady}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#25D366] hover:bg-[#1ead58] active:bg-[#17a050] disabled:opacity-50 disabled:cursor-not-allowed text-black font-semibold text-xs py-3 px-4 transition-all"
                >
                  <MessageSquare size={14} fill="currentColor" />
                  {saving ? 'Connecting…' : !sdkReady ? 'Loading…' : waConnected ? 'Reconnect via Meta' : 'Connect WhatsApp via Meta'}
                </button>
                <p className="text-[11px] text-sp-muted mt-2">
                  Opens a Meta popup. Sign in and select your own WhatsApp Business account — this
                  overrides the number we assign you.
                </p>
              </div>
            )}
          </div>

          {/* Manual form */}
          <form onSubmit={save} className="space-y-3 max-w-md">
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Company name</label>
              <input
                required
                value={name}
                onChange={e => setName(e.target.value)}
                className="input w-full"
              />
            </div>
            <div>
              <label className="text-xs text-sp-muted mb-1 block flex items-center gap-1.5">
                <MessageSquare size={11} /> WhatsApp phone number ID
              </label>
              <input
                value={waNumber}
                onChange={e => setWaNumber(e.target.value)}
                placeholder="961583850382092"
                className="input w-full font-mono text-xs"
              />
              <p className="text-[11px] text-sp-muted mt-1">
                Meta phone_number_id — not the display number. Auto-filled after connecting above.
              </p>
            </div>
            <Button type="submit" variant="outline" disabled={saving} className="mt-1">
              <Save size={13} />
              {saving ? 'Saving…' : 'Save changes'}
            </Button>
          </form>
        </div>

        {/* ── Plan ── */}
        <div className="bento-luxury">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-sm font-semibold text-sp-text mb-1">Current plan</h2>
              <p className="text-xs text-sp-muted">Up to {limits.staff} staff · {limits.price}</p>
            </div>
            <Badge className={`${PLAN_STYLES[plan] ?? PLAN_STYLES.starter} text-sm px-3 py-1 capitalize`}>
              {plan}
            </Badge>
          </div>

          {plan !== 'enterprise' && (
            <div className="mt-5 pt-5 border-t border-sp-border">
              <p className="text-sm text-sp-text mb-3">Upgrade your plan</p>
              <div className="grid grid-cols-2 gap-3 max-w-sm">
                {plan === 'starter' && (
                  <UpgradeCard
                    name="Growth"
                    price="₦150,000/mo"
                    staff={150}
                    tenantId={tenantId}
                    targetPlan="growth"
                  />
                )}
                <EnterpriseCard />
              </div>
            </div>
          )}
        </div>

        {/* ── Account ── */}
        <div className="bento-luxury">
          <h2 className="text-sm font-semibold text-sp-text mb-3">Account</h2>

          <form onSubmit={saveProfile} className="mb-4 pb-4 border-b border-sp-border/50 max-w-md">
            <label className="text-xs text-sp-muted mb-1 block">Full name</label>
            <div className="flex items-center gap-2">
              <input
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                placeholder="What should we call you?"
                className="input w-full"
              />
              <Button type="submit" variant="outline" size="sm" disabled={savingProfile || !fullName.trim()}>
                {savingProfile ? 'Saving…' : 'Save'}
              </Button>
            </div>
            {profileSaved && (
              <p className="mt-1.5 text-[11px] text-green-400 flex items-center gap-1">
                <CheckCircle2 size={11} /> Saved — your dashboard greeting will use this now.
              </p>
            )}
            <p className="text-[11px] text-sp-muted mt-1">Used for your dashboard greeting only, not shared with staff.</p>
          </form>

          <div className="space-y-1.5 text-sm">
            <div className="flex justify-between">
              <span className="text-sp-muted">Email</span>
              <span className="text-sp-text">{user?.email ?? '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sp-muted">Role</span>
              <span className="text-sp-text capitalize">{tenantAdmin?.role ?? '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sp-muted">Tenant ID</span>
              <span className="text-sp-muted font-mono text-xs">{tenantId}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function UpgradeCard({
  name, price, staff, tenantId, targetPlan,
}: {
  name: string; price: string; staff: number; tenantId: string; targetPlan: string
}) {
  const [loading, setLoading] = useState(false)

  async function subscribe() {
    setLoading(true)
    try {
      const res = await fetch('/api/billing/subscribe', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ tenant_id: tenantId, plan: targetPlan }),
      })
      const data = await res.json()
      if (data.authorization_url) window.location.href = data.authorization_url
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bento-luxury p-4">
      <p className="text-sm font-semibold text-sp-text">{name}</p>
      <p className="text-xs text-sp-muted mt-0.5">Up to {staff} staff</p>
      <p className="text-xs text-sp-accent mt-1 font-medium">{price}</p>
      <Button
        size="sm"
        variant="outline"
        className="mt-3 w-full justify-center"
        onClick={subscribe}
        disabled={loading}
      >
        <CreditCard size={12} />
        {loading ? 'Redirecting…' : 'Upgrade'}
      </Button>
    </div>
  )
}

function EnterpriseCard() {
  return (
    <div className="bento-luxury p-4">
      <p className="text-sm font-semibold text-sp-text">Enterprise</p>
      <p className="text-xs text-sp-muted mt-0.5">Unlimited staff</p>
      <p className="text-xs text-sp-accent mt-1 font-medium">Custom pricing</p>
      <a
        href="mailto:hi.kodehaus@gmail.com?subject=CordHR Enterprise"
        className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg border border-sp-border px-3 py-1.5 text-xs text-sp-muted transition-colors hover:border-sp-accent hover:text-sp-accent"
      >
        Contact sales
      </a>
    </div>
  )
}