import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

// Backend base URL, trailing-slash-safe — a NEXT_PUBLIC_BACKEND_URL with (or
// without) a trailing slash previously produced double-slash paths like
// "https://host//billing/verify", which FastAPI 404s on rather than normalizing.
export function backendUrl(path = ''): string {
  const base = (process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000').replace(/\/+$/, '')
  return path ? `${base}${path.startsWith('/') ? path : `/${path}`}` : base
}

export function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-NG', {
    day: 'numeric', month: 'short', year: 'numeric'
  })
}

export function formatCurrency(amount: number) {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency', currency: 'NGN', minimumFractionDigits: 0
  }).format(amount)
}

export const STATUS_COLORS: Record<string, string> = {
  pending:  'bg-amber-100 text-amber-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  cancelled:'bg-gray-100 text-gray-600',
  open:     'bg-amber-100 text-amber-800',
  closed:   'bg-green-100 text-green-800',
}

export const LEAVE_TYPE_COLORS: Record<string, string> = {
  annual:    'bg-blue-100 text-blue-800',
  sick:      'bg-orange-100 text-orange-800',
  maternity: 'bg-pink-100 text-pink-800',
  paternity: 'bg-purple-100 text-purple-800',
  unpaid:    'bg-gray-100 text-gray-700',
}

// Hardcoded demo tenant — replace with auth in production
export const DEMO_TENANT_ID = process.env.NEXT_PUBLIC_DEMO_TENANT_ID || ''

// Guards against a Supabase query hanging forever — e.g. a stale access token
// stuck refreshing after a long-idle tab, or GoTrueClient lock contention
// (see auth-context.tsx / supabase-server.ts). Without this, a page's
// `loading` state (set to false in a `finally`) never resolves and the
// spinner spins until the user clears site data. Aborts after `ms` so
// callers' `finally`/`catch` always runs.
export function withDeadline<T extends { abortSignal(signal: AbortSignal): any }>(query: T, ms = 8000) {
  const ac = new AbortController()
  const timer = setTimeout(() => ac.abort(), ms)
  return Promise.resolve(query.abortSignal(ac.signal)).finally(() => clearTimeout(timer))
}
