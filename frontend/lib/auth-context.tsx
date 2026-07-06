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
  full_name: string | null
  tenants: {
    id: string
    name: string
    plan: string
    whatsapp_number: string | null
    created_at: string
  }
}

type AuthContextType = {
  user:               User | null
  tenantAdmin:        TenantAdmin | null
  loading:            boolean
  tenantLoading:      boolean
  signOut:            () => Promise<void>
  refreshTenantAdmin: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null, tenantAdmin: null, loading: true, tenantLoading: true,
  signOut: async () => {}, refreshTenantAdmin: async () => {},
})


export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any | null>(null)
  const [tenantAdmin, setTenantAdmin] = useState<TenantAdmin | null>(null)
  const [loading, setLoading] = useState(true)
  const [tenantLoading, setTenantLoading] = useState(true)

  async function loadTenantAdmin(userId: string) {
    setTenantLoading(true)
    const ac = new AbortController()
    const timer = setTimeout(() => ac.abort(), 6000)
    
    try {
      const { data } = await supabase
        .from('tenant_admins')
        .select('tenant_id, role, full_name, tenants(*)')
        .eq('user_id', userId)
        .limit(1)
        .abortSignal(ac.signal)
      
      clearTimeout(timer)
      setTenantAdmin((data?.[0] ?? null) as TenantAdmin | null)
    } catch (e: any) {
      clearTimeout(timer)
      if (e.name !== 'AbortError') {
        console.error('[auth] loadTenantAdmin failed:', e)
      }
    } finally {
      setTenantLoading(false)
    }
  }

 useEffect(() => {
  // Keep track of the current active user ID to compare against token refreshes
  let currentUserId: string | null = null;

  const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
    const currentUser = session?.user ?? null;
    setUser(currentUser);

    // FIX: Only fetch tenant data if the user logged in or switched accounts
    if (currentUser) {
      if (currentUser.id !== currentUserId) {
        currentUserId = currentUser.id; // Update our tracker variable
        await loadTenantAdmin(currentUser.id);
      }
    } else {
      currentUserId = null;
      setTenantAdmin(null);
      setTenantLoading(false);
    }
    
    setLoading(false);
  });

  return () => {
    subscription.unsubscribe();
  };
}, []);


  async function signOut() {
    await supabase.auth.signOut()
    window.location.href = '/login'
  }

  async function refreshTenantAdmin() {
    if (user) await loadTenantAdmin(user.id)
  }

  return (
    <AuthContext.Provider value={{ user, tenantAdmin, loading, tenantLoading, signOut, refreshTenantAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
