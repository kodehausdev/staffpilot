// Server-only helpers for App Router route handlers (app/api/**/route.ts).
// Kept separate from supabase-server.ts because it imports "next/headers",
// which breaks bundling for any client component that transitively imports
// that file (e.g. login/page.tsx, dashboard/settings/page.tsx via createClient()).
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

const url  = process.env.NEXT_PUBLIC_SUPABASE_URL!
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Route handler client — reads the session cookie set by middleware.
export async function createRouteHandlerClient() {
  const cookieStore = await cookies()
  return createServerClient(url, anon, {
    cookies: {
      getAll: () => cookieStore.getAll(),
      // Route handlers can't set cookies on an incoming request; refresh is
      // handled by middleware, so this is a no-op here.
      setAll: () => {},
    },
  })
}

// Confirms the currently signed-in user is an admin of `tenant_id`.
// Returns the user on success, or null if unauthenticated / not a member of that tenant.
export async function requireTenantAdmin(tenant_id: string) {
  const supabase = await createRouteHandlerClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return null

  const { data } = await supabase
    .from('tenant_admins')
    .select('tenant_id')
    .eq('user_id', user.id)
    .eq('tenant_id', tenant_id)
    .limit(1)
    .maybeSingle()

  return data ? user : null
}
