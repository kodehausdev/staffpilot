'use client'
import { useAuth } from './auth-context'

/**
 * Returns the current tenant_id from auth context.
 * Falls back to NEXT_PUBLIC_DEMO_TENANT_ID for local dev without auth.
 */
export function useTenant() {
  const { tenantAdmin, tenantLoading } = useAuth()
  const tenantId = tenantAdmin?.tenant_id ?? ''
  const plan     = tenantAdmin?.tenants?.plan ?? 'starter'
  return { tenantId, plan, loading: tenantLoading }
}

2
