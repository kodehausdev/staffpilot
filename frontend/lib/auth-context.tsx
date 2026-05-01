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
  user:        User | null
  tenantAdmin: TenantAdmin | null
  loading:     boolean
  signOut:     () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null, tenantAdmin: null, loading: true, signOut: async () => {}
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]               = useState<User | null>(null)
  const [tenantAdmin, setTenantAdmin] = useState<TenantAdmin | null>(null)
  const [loading, setLoading]         = useState(true)

  async function loadTenantAdmin(userId: string) {
    const { data } = await supabase
      .from('tenant_admins')
      .select('tenant_id, role, tenants(*)')
      .eq('user_id', userId)
      .limit(1)
    setTenantAdmin((data?.[0] ?? null) as TenantAdmin | null)
  }

  useEffect(() => {
    async function init() {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        setUser(session?.user ?? null)
        if (session?.user) await loadTenantAdmin(session.user.id)
      } catch (e) {
        console.error('[auth] init failed:', e)
      } finally {
        setLoading(false)
      }
    }

    init()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setUser(session?.user ?? null)
      if (session?.user) {
        await loadTenantAdmin(session.user.id)
      } else {
        setTenantAdmin(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  async function signOut() {
    await supabase.auth.signOut()
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, tenantAdmin, loading, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
