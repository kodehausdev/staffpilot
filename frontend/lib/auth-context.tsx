'use client'
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { createBrowserClient } from '@supabase/ssr'
import type { User } from '@supabase/supabase-js'

// Single instance — avoids creating a new client on every render
const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

type TenantAdmin = {
  tenant_id: string
  role: string
  tenants: {
    id: string
    name: string
    plan: string
    whatsapp_number: string | null
  }
}

type AuthContextType = {
  user:          User | null
  tenantAdmin:   TenantAdmin | null
  loading:       boolean
  tenantLoading: boolean
  signOut:       () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null, tenantAdmin: null, loading: true, tenantLoading: true, signOut: async () => {}
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]               = useState<User | null>(null)
  const [tenantAdmin, setTenantAdmin] = useState<TenantAdmin | null>(null)
  const [loading, setLoading]         = useState(true)
  const [tenantLoading, setTenantLoading] = useState(true)

  async function loadTenantAdmin(userId: string) {
    setTenantLoading(true)
    const ac = new AbortController()
    const timer = setTimeout(() => ac.abort(), 6000)
    try {
      const { data } = await supabase
        .from('tenant_admins')
        .select('tenant_id, role, tenants(*)')
        .eq('user_id', userId)
        .limit(1)
        .abortSignal(ac.signal)
      clearTimeout(timer)
      setTenantAdmin((data?.[0] ?? null) as TenantAdmin | null)
    } catch (e) {
      clearTimeout(timer)
      console.error('[auth] loadTenantAdmin:', e)
    } finally {
      setTenantLoading(false)
    }
  }

  useEffect(() => {
    async function init() {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        setUser(session?.user ?? null)
        setLoading(false)  // auth resolved — unblock the UI
        if (session?.user) {
          await loadTenantAdmin(session.user.id)
        } else {
          setTenantLoading(false)
        }
      } catch (e) {
        console.error('[auth] init failed:', e)
        setLoading(false)
        setTenantLoading(false)
      }
    }

    init()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'INITIAL_SESSION') return  // init() handles this
      setUser(session?.user ?? null)
      if (session?.user) {
        await loadTenantAdmin(session.user.id)
      } else {
        setTenantAdmin(null)
        setTenantLoading(false)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  async function signOut() {
    await supabase.auth.signOut()
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, tenantAdmin, loading, tenantLoading, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
