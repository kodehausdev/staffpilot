import { cn } from '@/lib/utils'
import { ReactNode } from 'react'

// ── Card ──────────────────────────────────────────
export function Card({
  children, className
}: { children: ReactNode; className?: string }) {
  return (
    <div className={cn(
      'bg-sp-surface border border-sp-border rounded-xl p-5',
      className
    )}>
      {children}
    </div>
  )
}

// ── Stat card ─────────────────────────────────────
export function StatCard({
  label, value, sub, accent
}: { label: string; value: string | number; sub?: string; accent?: boolean }) {
  return (
    <Card>
      <p className="text-xs text-sp-muted uppercase tracking-widest mb-1">{label}</p>
      <p className={cn(
        'text-3xl font-semibold tracking-tight',
        accent ? 'text-sp-accent' : 'text-sp-text'
      )}>
        {value}
      </p>
      {sub && <p className="text-xs text-sp-muted mt-1">{sub}</p>}
    </Card>
  )
}

// ── Badge ─────────────────────────────────────────
export function Badge({
  children, className
}: { children: ReactNode; className?: string }) {
  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium',
      className
    )}>
      {children}
    </span>
  )
}

// ── Button ────────────────────────────────────────
export function Button({
  children, onClick, variant = 'primary', size = 'md', disabled, className, type = 'button'
}: {
  children: ReactNode
  onClick?: () => void
  variant?: 'primary' | 'ghost' | 'danger' | 'outline'
  size?: 'sm' | 'md'
  disabled?: boolean
  className?: string
  type?: 'button' | 'submit'
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-lg font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed',
        size === 'sm' ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-sm',
        variant === 'primary' && 'bg-sp-accent text-white hover:bg-emerald-400',
        variant === 'ghost'   && 'text-sp-muted hover:text-sp-text hover:bg-sp-border',
        variant === 'danger'  && 'bg-red-900/40 text-red-400 hover:bg-red-900/70',
        variant === 'outline' && 'border border-sp-border text-sp-text hover:bg-sp-border',
        className
      )}
    >
      {children}
    </button>
  )
}

// ── Page header ───────────────────────────────────
export function PageHeader({
  title, sub, action
}: { title: string; sub?: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-7">
      <div>
        <h1 className="text-xl font-semibold text-sp-text tracking-tight">{title}</h1>
        {sub && <p className="text-sm text-sp-muted mt-0.5">{sub}</p>}
      </div>
      {action}
    </div>
  )
}

// ── Empty state ───────────────────────────────────
export function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-16 text-sp-muted text-sm">{message}</div>
  )
}

// ── Loading spinner ───────────────────────────────
export function Spinner() {
  return (
    <div className="flex justify-center py-12">
      <div className="w-5 h-5 border-2 border-sp-border border-t-sp-accent rounded-full animate-spin" />
    </div>
  )
}
