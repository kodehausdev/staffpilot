'use client'
import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Sidebar from '@/components/layout/Sidebar'
import { useAuth } from '@/lib/auth-context'
import { Spinner } from '@/components/ui'
import { Clock } from 'lucide-react'

function hoursSince(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 36e5)
}

function ActivationBanner() {
  const { tenantAdmin } = useAuth()
  const tenant = tenantAdmin?.tenants

  if (!tenant || tenant.whatsapp_number) return null

  const hoursLeft = Math.max(0, 24 - hoursSince(tenant.created_at))

  return (
    <div className="mb-5 flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3">
      <Clock size={15} className="text-amber-400 shrink-0" />
      <p className="text-xs text-amber-400">
        <span className="font-medium">Your WhatsApp number is being activated.</span>{' '}
        {hoursLeft > 0
          ? `We're setting it up on our end — expect it live within ${hoursLeft}h.`
          : "This is taking longer than usual — we've been notified and are on it."}{' '}
        Already have your own verified Meta Business Account? You can connect it yourself
        under <span className="font-medium">Settings</span>.
      </p>
    </div>
  )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!loading && !user) router.replace('/login')
  }, [user, loading])

  if (loading) return (
    <div className="min-h-screen bg-sp-bg flex items-center justify-center">
      <Spinner />
    </div>
  )

  if (!user) return null

  return (
    <div className="min-h-screen bg-sp-bg flex">
      <Sidebar />
      <main className="ml-60 flex-1 p-8">
        <div className="max-w-5xl mx-auto">
          {pathname !== '/dashboard/settings' && <ActivationBanner />}
          {children}
        </div>
      </main>
    </div>
  )
}
