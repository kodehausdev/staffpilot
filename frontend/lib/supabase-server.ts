import { createServerClient } from '@supabase/ssr'
import { createBrowserClient } from '@supabase/ssr'
import type { IncomingMessage, ServerResponse } from 'http'

const url  = process.env.NEXT_PUBLIC_SUPABASE_URL!
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Singleton browser client — shared across all client components
let _client: ReturnType<typeof createBrowserClient> | null = null
export function createClient() {
  if (!_client) _client = createBrowserClient(url, anon)
  return _client
}

// Server client for Pages Router — pass req/res from getServerSideProps
export function createServerSupabase(req: IncomingMessage & { cookies: Partial<{ [key: string]: string }> }, res: ServerResponse) {
  return createServerClient(url, anon, {
    cookies: {
      getAll: () =>
        Object.entries(req.cookies).map(([name, value]) => ({ name, value: value ?? '' })),
      setAll: (cookiesToSet) => {
        cookiesToSet.forEach(({ name, value, options }) => {
          const opts = options as Record<string, unknown>
          const parts = [`${name}=${encodeURIComponent(value)}`]
          if (opts?.maxAge)    parts.push(`Max-Age=${opts.maxAge}`)
          if (opts?.path)      parts.push(`Path=${opts.path}`)
          if (opts?.domain)    parts.push(`Domain=${opts.domain}`)
          if (opts?.httpOnly)  parts.push('HttpOnly')
          if (opts?.secure)    parts.push('Secure')
          if (opts?.sameSite)  parts.push(`SameSite=${opts.sameSite}`)
          res.setHeader('Set-Cookie', parts.join('; '))
        })
      },
    },
  })
}

// Get current session — call from getServerSideProps
export async function getSession(req: IncomingMessage & { cookies: Partial<{ [key: string]: string }> }, res: ServerResponse) {
  const supabase = createServerSupabase(req, res)
  const { data: { session } } = await supabase.auth.getSession()
  return session
}

// Get current tenant — call from getServerSideProps
export async function getCurrentTenant(req: IncomingMessage & { cookies: Partial<{ [key: string]: string }> }, res: ServerResponse) {
  const session = await getSession(req, res)
  if (!session) return null

  const supabase = createServerSupabase(req, res)
  const { data } = await supabase
    .from('tenant_admins')
    .select('tenant_id, role, tenants(*)')
    .eq('user_id', session.user.id)
    .limit(1)
    .single()

  return data
}
