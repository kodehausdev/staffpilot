'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useTenant } from '@/lib/use-tenant'
import { useAuth } from '@/lib/auth-context'
import { Button, Badge, PageHeader, Spinner } from '@/components/ui'
import { Save, MessageSquare, CreditCard } from 'lucide-react'

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

export default function SettingsPage() {
  const { tenantAdmin, user }       = useAuth()
  const { tenantId, plan, loading: tenantLoading } = useTenant()
  const supabase = createClient()

  const [name, setName]         = useState('')
  const [waNumber, setWaNumber] = useState('')
  const [saving, setSaving]     = useState(false)
  const [saved, setSaved]       = useState(false)
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(true)

  useEffect(() => {
    if (!tenantId) return
    supabase
      .from('tenants')
      .select('name, whatsapp_number')
      .eq('id', tenantId)
      .single()
      .then(({ data }) => {
        if (data) {
          setName(data.name ?? '')
          setWaNumber(data.whatsapp_number ?? '')
        }
        setLoading(false)
      })
  }, [tenantId])

  async function save(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSaved(false)

    try {
      const { error: err } = await supabase
        .from('tenants')
        .update({ name, whatsapp_number: waNumber })
        .eq('id', tenantId)

      if (err) {
        setError(err.message)
      } else {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
      }
    } catch (e: any) {
      setError(e?.message ?? 'Save failed — please try again')
    } finally {
      setSaving(false)
    }
  }

  if (tenantLoading || loading) return <Spinner />

  const limits = PLAN_LIMITS[plan] ?? PLAN_LIMITS.starter

  return (
    <div>
      <PageHeader title="Settings" sub="Company configuration and billing" />

      <div className="space-y-6">
        {/* Company info */}
        <div className="bento-luxury">
          <h2 className="text-sm font-semibold text-sp-text mb-4">Company details</h2>

          {error  && <p className="mb-3 text-xs text-red-400">{error}</p>}
          {saved  && <p className="mb-3 text-xs text-green-400">Saved successfully.</p>}

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
                Meta phone_number_id from your WhatsApp Business API — not the display number.
              </p>
            </div>
            <Button type="submit" variant="outline" disabled={saving} className="mt-1">
              <Save size={13} />
              {saving ? 'Saving…' : 'Save changes'}
            </Button>
          </form>
        </div>

        {/* Plan */}
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
                <UpgradeCard
                  name="Enterprise"
                  price="Custom pricing"
                  staff={999}
                  tenantId={tenantId}
                  targetPlan="enterprise"
                />
              </div>
            </div>
          )}
        </div>

        {/* Account */}
        <div className="bento-luxury">
          <h2 className="text-sm font-semibold text-sp-text mb-3">Account</h2>
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

function UpgradeCard({
  name, price, staff, tenantId, targetPlan,
}: {
  name: string; price: string; staff: number; tenantId: string; targetPlan: string
}) {
  const [loading, setLoading] = useState(false)

  async function subscribe() {
    setLoading(true)
    const res = await fetch('/api/billing/subscribe', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ tenant_id: tenantId, plan: targetPlan }),
    })
    const data = await res.json()
    if (data.authorization_url) {
      window.location.href = data.authorization_url
    }
    setLoading(false)
  }

  return (
    <div className="bento-luxury p-4">
      <p className="text-sm font-semibold text-sp-text">{name}</p>
      <p className="text-xs text-sp-muted mt-0.5">Up to {staff === 999 ? 'unlimited' : staff} staff</p>
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
