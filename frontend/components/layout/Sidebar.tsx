'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Users, CalendarOff,
  FileText, CreditCard, Settings,
  MessageSquare, LogOut, Loader2, ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth-context'

const NAV = [
  { href: '/dashboard',           icon: LayoutDashboard, label: 'Overview'       },
  { href: '/dashboard/leave',     icon: CalendarOff,     label: 'Leave requests' },
  { href: '/dashboard/employees', icon: Users,           label: 'Employees'      },
  { href: '/dashboard/payslips',  icon: CreditCard,      label: 'Payslips'       },
  { href: '/dashboard/docs',      icon: FileText,        label: 'HR documents'   },
  { href: '/dashboard/settings',  icon: Settings,        label: 'Settings'       },
]

const PLAN_STYLES: Record<string, string> = {
  starter:    'bg-sp-border text-sp-muted',
  growth:     'bg-sp-accent-dim text-sp-accent',
  enterprise: 'bg-purple-900/40 text-purple-400',
}

export default function Sidebar() {
  const path = usePathname()
  const { user, tenantAdmin, loading, signOut } = useAuth()

  const companyName = tenantAdmin?.tenants?.name ?? '—'
  const plan        = tenantAdmin?.tenants?.plan ?? 'starter'
  const email       = user?.email ?? ''
  const initials    = companyName !== '—'
    ? companyName.split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase()
    : email[0]?.toUpperCase() ?? 'A'

  return (
    <aside className="fixed top-0 left-0 h-screen w-60 bg-sp-surface border-r border-white/[0.06] flex flex-col">

      {/* Logo */}
      <div className="px-5 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-sp-accent flex items-center justify-center shrink-0">
            <MessageSquare size={13} className="text-white" />
          </div>
          <span className="font-semibold text-sp-text tracking-tight text-sm">StaffPilot</span>
        </div>
      </div>

      {/* Company + plan */}
      <div className="px-4 py-3 border-b border-white/[0.06]">
        {loading ? (
          <Loader2 size={13} className="animate-spin text-sp-muted" />
        ) : (
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium text-sp-text truncate">{companyName}</p>
            <span className={cn(
              'text-[10px] font-semibold px-1.5 py-0.5 rounded capitalize shrink-0',
              PLAN_STYLES[plan] ?? PLAN_STYLES.starter
            )}>
              {plan}
            </span>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = path === href || (href !== '/dashboard' && path.startsWith(href))
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-all',
                active
                  ? 'bg-sp-accent-dim text-sp-accent font-medium'
                  : 'text-sp-muted hover:text-sp-text hover:bg-white/[0.04]'
              )}
            >
              <Icon size={14} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* User profile anchor */}
      <div className="border-t border-white/[0.06] p-3">
        {!loading && (
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-white/[0.04] transition-all group">
            {/* Avatar */}
            <div className="w-8 h-8 rounded-full bg-sp-accent-dim border border-sp-accent/30 flex items-center justify-center text-sp-accent text-xs font-bold shrink-0">
              {initials}
            </div>

            {/* Name + email */}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-sp-text truncate leading-tight">{companyName}</p>
              <p className="text-[11px] text-sp-muted truncate leading-tight mt-0.5">{email}</p>
            </div>

            {/* Logout */}
            <button
              onClick={signOut}
              title="Sign out"
              className="text-sp-muted hover:text-red-400 transition-colors shrink-0 opacity-0 group-hover:opacity-100"
            >
              <LogOut size={13} />
            </button>
          </div>
        )}
      </div>
    </aside>
  )
}
