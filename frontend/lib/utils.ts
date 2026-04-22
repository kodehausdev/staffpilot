import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
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
