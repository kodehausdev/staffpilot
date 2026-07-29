'use client'

import { useEffect, useState, useMemo } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useRouter } from 'next/navigation'
import { MessageSquare, Eye, EyeOff, Loader2, CheckCircle2 } from 'lucide-react'

export default function ResetPasswordPage() {
  const router = useRouter()
  const supabase = useMemo(() => createClient(), [])

  // The recovery link's tokens are parsed from the URL and turned into a
  // session automatically (detectSessionInUrl on the browser client) — but
  // that happens async, so we can't just check getSession() once on mount.
  const [ready, setReady]       = useState(false)
  const [validLink, setValidLink] = useState(false)
  const [password, setPassword]   = useState('')
  const [confirm, setConfirm]     = useState('')
  const [showPw, setShowPw]       = useState(false)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const [done, setDone]           = useState(false)

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY' || session) {
        setValidLink(true)
        setReady(true)
      }
    })

    // Fallback in case the event already fired before this listener attached
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) setValidLink(true)
      setReady(true)
    })

    return () => subscription.unsubscribe()
  }, [supabase])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)
    try {
      const { error: updateErr } = await supabase.auth.updateUser({ password })
      if (updateErr) {
        setError(updateErr.message)
      } else {
        setDone(true)
      }
    } catch {
      setError('An unexpected network error occurred. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-sp-bg flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2.5 justify-center mb-8">
          <div className="w-9 h-9 rounded-xl bg-sp-accent flex items-center justify-center">
            <MessageSquare size={18} className="text-white" />
          </div>
          <span className="text-xl font-semibold text-sp-text tracking-tight">CordHR</span>
        </div>

        <div className="bg-sp-surface border border-sp-border rounded-2xl p-7">
          {!ready ? (
            <div className="flex justify-center py-6">
              <Loader2 size={24} className="animate-spin text-sp-muted" />
            </div>
          ) : done ? (
            <div className="text-center">
              <div className="w-14 h-14 rounded-full bg-sp-accent-dim flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 size={28} className="text-sp-accent" />
              </div>
              <h1 className="text-lg font-semibold text-sp-text mb-1">Password updated</h1>
              <p className="text-sm text-sp-muted mb-6">You're all set. Head to your dashboard.</p>
              <button
                onClick={() => router.push('/dashboard')}
                className="w-full py-2.5 rounded-lg bg-sp-accent text-white text-sm font-medium hover:bg-emerald-400 transition"
              >
                Go to dashboard
              </button>
            </div>
          ) : !validLink ? (
            <div className="text-center">
              <h1 className="text-lg font-semibold text-sp-text mb-1">Link expired</h1>
              <p className="text-sm text-sp-muted mb-6">
                This reset link is invalid or has expired. Request a new one from the sign-in page.
              </p>
              <button
                onClick={() => router.push('/login')}
                className="w-full py-2.5 rounded-lg border border-sp-border text-sp-text text-sm font-medium hover:border-sp-accent hover:text-sp-accent transition"
              >
                Back to sign in
              </button>
            </div>
          ) : (
            <>
              <h1 className="text-lg font-semibold text-sp-text mb-1">Set a new password</h1>
              <p className="text-sm text-sp-muted mb-6">Choose something you haven't used before.</p>

              {error && <div className="mb-4 px-3 py-2.5 rounded-lg bg-red-900/30 text-red-400 text-sm">{error}</div>}

              <form onSubmit={handleSubmit} className="space-y-3">
                <div>
                  <label className="text-xs text-sp-muted mb-1 block">New password</label>
                  <div className="relative">
                    <input
                      type={showPw ? 'text' : 'password'}
                      required
                      minLength={8}
                      placeholder="Min. 8 characters"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      className="w-full bg-sp-bg border border-sp-border rounded-lg px-3.5 py-2.5 pr-10 text-sm text-sp-text placeholder-sp-muted focus:outline-none focus:border-sp-accent transition"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(!showPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-sp-muted hover:text-sp-text"
                    >
                      {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-sp-muted mb-1 block">Confirm password</label>
                  <input
                    type={showPw ? 'text' : 'password'}
                    required
                    minLength={8}
                    placeholder="Re-enter password"
                    value={confirm}
                    onChange={e => setConfirm(e.target.value)}
                    className="w-full bg-sp-bg border border-sp-border rounded-lg px-3.5 py-2.5 text-sm text-sp-text placeholder-sp-muted focus:outline-none focus:border-sp-accent transition"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full mt-1 py-2.5 rounded-lg bg-sp-accent text-white text-sm font-medium hover:bg-emerald-400 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading && <Loader2 size={14} className="animate-spin" />}
                  Update password
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-xs text-sp-muted mt-5">
          Powered by Optipropose Studio · Abuja, Nigeria
        </p>
      </div>
    </div>
  )
}
