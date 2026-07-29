'use client'

import { useState, Suspense, useMemo } from 'react'
import { createClient } from '@/lib/supabase-server'
import { useRouter, useSearchParams } from 'next/navigation'
import { MessageSquare, Eye, EyeOff, Loader2 } from 'lucide-react'

function LoginFormContent() {
  const router = useRouter()
  const params = useSearchParams()
  const next = params.get('next') || '/dashboard'
  
  // Safe client memoization to prevent rendering thread freeze
  const supabase = useMemo(() => createClient(), [])

  const [mode, setMode]         = useState<'login' | 'signup' | 'forgot'>('login')
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [company, setCompany]   = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [success, setSuccess]   = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      if (mode === 'forgot') {
        const { error: resetErr } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/reset-password`,
        })

        if (resetErr) {
          setError(resetErr.message)
        } else {
          setSuccess('If an account exists for that email, a reset link is on its way.')
        }
      } else if (mode === 'login') {
        const { data, error: loginErr } = await supabase.auth.signInWithPassword({ 
          email, 
          password 
        })

        if (loginErr) {
          setError(loginErr.message)
        } else if (data?.session) {
          router.push(next)
          router.refresh()
        }
      } else {
        const { data, error: signupErr } = await supabase.auth.signUp({
          email, 
          password,
          options: { data: { company_name: company } }
        })

        if (signupErr) {
          setError(signupErr.message)
        } else if (data?.user) {
          const res = await fetch('/api/auth/setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: data.user.id,
              email,
              company: company || email.split('@')[0],
            }),
          })
          
          if (res.ok) {
            setSuccess('Account created! Check your email to confirm, then log in.')
            setMode('login')
          } else {
            setError('Account created but setup failed. Contact support.')
          }
        }
      }
    } catch (err) {
      setError('An unexpected network error occurred. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full max-w-sm">
      <div className="flex items-center gap-2.5 justify-center mb-8">
        <div className="w-9 h-9 rounded-xl bg-sp-accent flex items-center justify-center">
          <MessageSquare size={18} className="text-white" />
        </div>
        <span className="text-xl font-semibold text-sp-text tracking-tight">CordHR</span>
      </div>

      <div className="bg-sp-surface border border-sp-border rounded-2xl p-7">
        <h1 className="text-lg font-semibold text-sp-text mb-1">
          {mode === 'login' ? 'Welcome back' : mode === 'signup' ? 'Create your account' : 'Reset your password'}
        </h1>
        <p className="text-sm text-sp-muted mb-6">
          {mode === 'login'
            ? 'Sign in to your HR dashboard'
            : mode === 'signup'
            ? 'Get your company set up in 2 minutes'
            : "Enter your email and we'll send you a reset link"}
        </p>

        {error && <div className="mb-4 px-3 py-2.5 rounded-lg bg-red-900/30 text-red-400 text-sm">{error}</div>}
        {success && <div className="mb-4 px-3 py-2.5 rounded-lg bg-green-900/30 text-green-400 text-sm">{success}</div>}

        <form onSubmit={handleSubmit} className="space-y-3">
          {mode === 'signup' && (
            <div>
              <label className="text-xs text-sp-muted mb-1 block">Company name</label>
              <input
                type="text"
                required
                placeholder="Apex Consulting Ltd"
                value={company}
                onChange={e => setCompany(e.target.value)}
                className="w-full bg-sp-bg border border-sp-border rounded-lg px-3.5 py-2.5 text-sm text-sp-text placeholder-sp-muted focus:outline-none focus:border-sp-accent transition"
              />
            </div>
          )}

          <div>
            <label className="text-xs text-sp-muted mb-1 block">Work email</label>
            <input
              type="email"
              required
              placeholder="hr@company.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-sp-bg border border-sp-border rounded-lg px-3.5 py-2.5 text-sm text-sp-text placeholder-sp-muted focus:outline-none focus:border-sp-accent transition"
            />
          </div>

          {mode !== 'forgot' && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-sp-muted block">Password</label>
                {mode === 'login' && (
                  <button
                    type="button"
                    onClick={() => { setMode('forgot'); setError(''); setSuccess('') }}
                    className="text-xs text-sp-accent hover:underline"
                  >
                    Forgot password?
                  </button>
                )}
              </div>
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
          )}

          {/* CHANGED TYPE TO SUBMIT TO FIRE ONSUBMIT */}
          <button
            type="submit"
            disabled={loading}
            className="w-full mt-1 py-2.5 rounded-lg bg-sp-accent text-white text-sm font-medium hover:bg-emerald-400 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            {mode === 'login' ? 'Sign in' : mode === 'signup' ? 'Create account' : 'Send reset link'}
          </button>
        </form>

        <div className="mt-5 pt-5 border-t border-sp-border text-center">
          {mode === 'forgot' ? (
            <p className="text-xs text-sp-muted">
              Remembered it?{' '}
              <button
                type="button"
                onClick={() => { setMode('login'); setError(''); setSuccess('') }}
                className="text-sp-accent hover:underline"
              >
                Sign in
              </button>
            </p>
          ) : (
            <p className="text-xs text-sp-muted">
              {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
              <button
                type="button"
                onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); setSuccess('') }}
                className="text-sp-accent hover:underline"
              >
                {mode === 'login' ? 'Sign up' : 'Sign in'}
              </button>
            </p>
          )}
        </div>
      </div>

      <p className="text-center text-xs text-sp-muted mt-5">
        Powered by Optipropose Studio · Abuja, Nigeria
      </p>
    </div>
  )
}

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-sp-bg flex items-center justify-center p-4">
      <Suspense fallback={<div className="text-sp-muted text-sm">Loading...</div>}>
        <LoginFormContent />
      </Suspense>
    </div>
  )
}
