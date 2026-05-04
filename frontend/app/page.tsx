'use client'
import { useState } from 'react'
import Link from 'next/link'
import {
  MessageSquare, ArrowRight, CheckCircle,
  CalendarOff, CreditCard, FileText, HelpCircle,
  Zap, Users, Shield,
} from 'lucide-react'

const PAIN = [
  {
    problem: 'Leave requests lost in group chats',
    fix: 'Employees text the bot. Manager approves. Done.',
  },
  {
    problem: 'Payslips shared as blurry photos',
    fix: 'Clean payslip delivered on WhatsApp, every month.',
  },
  {
    problem: 'HR policy? Nobody knows where the doc is',
    fix: 'Employees ask. AI answers — from your actual handbook.',
  },
]

const STEPS = [
  {
    n: '01',
    title: 'Sign up & add your team',
    body: 'Create your company account and add employees in under 5 minutes. Import via CSV or add one by one.',
  },
  {
    n: '02',
    title: 'Upload your HR handbook',
    body: 'Drop in your policy PDF. CordHR reads it so your employees can ask any HR question and get accurate answers.',
  },
  {
    n: '03',
    title: 'Your team starts texting',
    body: 'Share the WhatsApp number. From day one, employees handle leave, payslips, and HR questions without bothering you.',
  },
]

const FEATURES = [
  {
    icon: CalendarOff,
    title: 'Leave management',
    body: 'Employees request leave via WhatsApp. Managers approve or reject with a single reply. Balance updates automatically.',
  },
  {
    icon: CreditCard,
    title: 'Payslips on WhatsApp',
    body: 'Upload monthly payslips to the dashboard. Employees receive them instantly — no email, no portal login.',
  },
  {
    icon: FileText,
    title: 'HR Q&A',
    body: 'Upload your employee handbook once. CordHR answers policy questions around the clock so you don\'t have to.',
  },
  {
    icon: Shield,
    title: 'Multi-tenant security',
    body: 'Every company\'s data is completely isolated. Row-level security ensures your data never touches another account.',
  },
]

const PLANS = [
  {
    name: 'Starter',
    tagline: 'Stop answering the same HR questions every day.',
    monthly: 35000,
    annual: 350000,
    staff: 10,
    overage: 2000,
    features: [
      'WhatsApp HR bot',
      'Leave requests & tracking',
      'Payslips on WhatsApp',
      'Company handbook Q&A',
      'Admin dashboard',
      'Email support',
    ],
    popular: false,
    cta: 'Start free',
  },
  {
    name: 'Growth',
    tagline: 'Run HR like a system, not a struggle.',
    monthly: 150000,
    annual: 1500000,
    staff: 50,
    overage: 1500,
    features: [
      'Everything in Starter',
      'Up to 50 employees',
      'Advanced multi-doc RAG',
      'Role-based access (Admin, HR, Manager)',
      'HR document management',
      'Activity logs',
      'Priority support',
    ],
    popular: true,
    cta: 'Start free',
  },
  {
    name: 'Scale',
    tagline: 'Turn HR into infrastructure.',
    monthly: 400000,
    annual: 4000000,
    staff: null,
    overage: null,
    features: [
      'Everything in Growth',
      'Unlimited employees',
      'Custom approval workflows',
      'Founder/exec WhatsApp commands',
      'Analytics & leave trend insights',
      'API access',
      'Dedicated onboarding',
    ],
    popular: false,
    cta: 'Contact us',
  },
]

function fmt(n: number) {
  return '₦' + n.toLocaleString('en-NG')
}

export default function LandingPage() {
  const [annual, setAnnual] = useState(false)

  return (
    <div className="min-h-screen bg-sp-bg text-sp-text">

      {/* ── Nav ─────────────────────────────────────── */}
      <header className="border-b border-white/[0.06] px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sp-accent flex items-center justify-center">
              <MessageSquare size={15} className="text-white" />
            </div>
            <span className="font-semibold text-sp-text tracking-tight">CordHR</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm text-sp-muted hover:text-sp-text transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/login"
              className="text-sm bg-sp-accent text-white px-4 py-2 rounded-lg hover:bg-emerald-400 transition-colors font-medium"
            >
              Get started free
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 pt-24 pb-20 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-sp-accent/10 border border-sp-accent/20 text-sp-accent text-xs font-medium mb-8">
          <Zap size={11} />
          Built for Nigerian SMEs
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-none mb-6">
          HR that's actually{' '}
          <span className="text-sp-accent">cordial.</span>
        </h1>

        <p className="text-lg md:text-xl text-sp-muted max-w-2xl mx-auto mb-10 leading-relaxed">
          Leave. Payslips. HR questions. Your team handles it all on WhatsApp —
          where they already are.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/login"
            className="flex items-center gap-2 bg-sp-accent text-white px-6 py-3 rounded-xl font-medium hover:bg-emerald-400 transition-colors text-sm"
          >
            Get started free <ArrowRight size={15} />
          </Link>
          <a
            href="mailto:hi.kodehaus@gmail.com?subject=CordHR Demo"
            className="flex items-center gap-2 border border-sp-border text-sp-muted px-6 py-3 rounded-xl font-medium hover:text-sp-text hover:border-white/20 transition-colors text-sm"
          >
            Book a demo
          </a>
        </div>

        {/* WhatsApp mockup */}
        <div className="mt-20 flex justify-center">
          <div className="w-72 bg-[#111] rounded-3xl border border-white/10 shadow-2xl overflow-hidden">
            {/* Phone header */}
            <div className="bg-[#1a1a1a] px-4 py-3 flex items-center gap-3 border-b border-white/[0.06]">
              <div className="w-8 h-8 rounded-full bg-sp-accent flex items-center justify-center shrink-0">
                <MessageSquare size={13} className="text-white" />
              </div>
              <div>
                <p className="text-xs font-semibold text-sp-text">CordHR Bot</p>
                <p className="text-[10px] text-sp-accent">● Online</p>
              </div>
            </div>
            {/* Chat */}
            <div className="px-3 py-4 space-y-2.5 text-[11px]">
              <Bubble from="employee" text="Hi, I need 3 days leave from Dec 10" />
              <Bubble from="bot" text="✓ Leave request submitted for Dec 10–12. Your manager has been notified." />
              <Bubble from="employee" text="What's my leave balance?" />
              <Bubble from="bot" text="You have 12 days annual leave remaining." />
              <Bubble from="employee" text="Send me my November payslip" />
              <Bubble from="bot" text="💰 November — Net ₦238,500. Gross ₦280,000." />
            </div>
          </div>
        </div>
      </section>

      {/* ── Pain → Fix ──────────────────────────────── */}
      <section className="bg-sp-surface/50 border-y border-white/[0.06] py-20">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-14">
            Sound familiar?
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {PAIN.map(({ problem, fix }) => (
              <div key={problem} className="bg-sp-surface rounded-2xl border border-white/[0.06] p-6 space-y-4">
                <p className="text-sp-muted line-through text-sm">{problem}</p>
                <div className="flex items-start gap-2">
                  <CheckCircle size={15} className="text-sp-accent mt-0.5 shrink-0" />
                  <p className="text-sp-text text-sm font-medium">{fix}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ────────────────────────────── */}
      <section className="py-24">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold mb-3">Up and running in a day</h2>
            <p className="text-sp-muted">No IT team required.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {STEPS.map(({ n, title, body }) => (
              <div key={n} className="relative">
                <span className="text-5xl font-black text-white/[0.04] select-none leading-none">{n}</span>
                <div className="-mt-4">
                  <h3 className="font-semibold text-sp-text mb-2">{title}</h3>
                  <p className="text-sm text-sp-muted leading-relaxed">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ────────────────────────────────── */}
      <section className="bg-sp-surface/50 border-y border-white/[0.06] py-24">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-14">
            Everything your HR team needs
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <div key={title} className="bg-sp-surface rounded-2xl border border-white/[0.06] p-6 flex gap-4">
                <div className="w-10 h-10 rounded-xl bg-sp-accent/10 border border-sp-accent/20 flex items-center justify-center shrink-0">
                  <Icon size={18} className="text-sp-accent" />
                </div>
                <div>
                  <h3 className="font-semibold text-sp-text mb-1">{title}</h3>
                  <p className="text-sm text-sp-muted leading-relaxed">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ─────────────────────────────────── */}
      <section className="py-24">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-10">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Simple pricing</h2>

            {/* Toggle */}
            <div className="inline-flex items-center gap-3 bg-sp-surface border border-white/[0.06] rounded-xl p-1">
              <button
                onClick={() => setAnnual(false)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  !annual ? 'bg-sp-accent text-white' : 'text-sp-muted hover:text-sp-text'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setAnnual(true)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                  annual ? 'bg-sp-accent text-white' : 'text-sp-muted hover:text-sp-text'
                }`}
              >
                Annual
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                  annual ? 'bg-white/20' : 'bg-sp-accent/20 text-sp-accent'
                }`}>
                  2 months free
                </span>
              </button>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-6 items-start">
            {PLANS.map(({ name, tagline, monthly, annual: yr, staff, overage, features, popular, cta }) => (
              <div
                key={name}
                className={`relative rounded-2xl border p-7 flex flex-col ${
                  popular
                    ? 'bg-sp-surface border-sp-accent shadow-[0_0_40px_-10px] shadow-sp-accent/20'
                    : 'bg-sp-surface border-white/[0.06]'
                }`}
              >
                {popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-sp-accent text-white text-[11px] font-bold px-3 py-1 rounded-full">
                      Most Popular
                    </span>
                  </div>
                )}

                <p className="text-sm font-semibold text-sp-text mb-0.5">{name}</p>
                <p className="text-[11px] text-sp-muted mb-4 leading-snug">{tagline}</p>

                <div className="mb-1">
                  <span className="text-4xl font-black text-sp-text">
                    {fmt(annual ? yr : monthly)}
                  </span>
                  <span className="text-sp-muted text-sm ml-1">
                    /{annual ? 'yr' : 'mo'}
                    {name === 'Scale' && '+'}
                  </span>
                </div>

                <div className="flex items-center gap-3 mb-6">
                  <p className="text-xs text-sp-muted flex items-center gap-1">
                    <Users size={11} />
                    {staff ? `Up to ${staff} employees` : 'Unlimited employees'}
                  </p>
                  {overage && (
                    <p className="text-[10px] text-sp-muted bg-white/[0.04] border border-white/[0.06] px-2 py-0.5 rounded-full">
                      +{fmt(overage)}/extra
                    </p>
                  )}
                </div>

                <ul className="space-y-2.5 mb-8 flex-1">
                  {features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-sm text-sp-muted">
                      <CheckCircle size={13} className="text-sp-accent mt-0.5 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>

                {cta === 'Contact us' ? (
                  <a
                    href="mailto:hi.kodehaus@gmail.com?subject=CordHR Scale"
                    className="w-full text-center py-2.5 rounded-xl border border-white/[0.06] text-sm text-sp-muted hover:text-sp-text hover:border-white/20 transition-colors font-medium"
                  >
                    Contact us
                  </a>
                ) : (
                  <Link
                    href="/login"
                    className={`w-full text-center py-2.5 rounded-xl text-sm font-medium transition-colors ${
                      popular
                        ? 'bg-sp-accent text-white hover:bg-emerald-400'
                        : 'border border-white/[0.06] text-sp-muted hover:text-sp-text hover:border-white/20'
                    }`}
                  >
                    {cta}
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────────── */}
      <section className="border-t border-white/[0.06] py-24">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Stop managing HR<br />in a group chat.
          </h2>
          <p className="text-sp-muted mb-8">
            Your team is already on WhatsApp. CordHR meets them there.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 bg-sp-accent text-white px-8 py-3.5 rounded-xl font-medium hover:bg-emerald-400 transition-colors"
          >
            Get started free <ArrowRight size={16} />
          </Link>
          <p className="text-xs text-sp-muted mt-4">No credit card required</p>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────── */}
      <footer className="border-t border-white/[0.06] py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-sp-muted">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-md bg-sp-accent flex items-center justify-center">
              <MessageSquare size={10} className="text-white" />
            </div>
            <span>© {new Date().getFullYear()} Optipropose Studio. All rights reserved.</span>
          </div>
          <div className="flex items-center gap-5">
            <a href="https://optipropose.com" target="_blank" rel="noopener noreferrer" className="hover:text-sp-text transition-colors">OptiPropose</a>
            <Link href="/login" className="hover:text-sp-text transition-colors">Sign in</Link>
            <a href="https://optipropose.com/privacy" target="_blank" rel="noopener noreferrer" className="hover:text-sp-text transition-colors">Privacy</a>
            <a href="https://optipropose.com/terms" target="_blank" rel="noopener noreferrer" className="hover:text-sp-text transition-colors">Terms</a>
            <a href="mailto:hi.kodehaus@gmail.com" className="hover:text-sp-text transition-colors">Contact</a>
          </div>
        </div>
      </footer>

    </div>
  )
}

function Bubble({ from, text }: { from: 'bot' | 'employee'; text: string }) {
  const isBot = from === 'bot'
  return (
    <div className={`flex ${isBot ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-[85%] px-3 py-2 rounded-2xl leading-snug ${
          isBot
            ? 'bg-[#1e1e1e] text-sp-text rounded-tl-sm'
            : 'bg-sp-accent text-white rounded-tr-sm'
        }`}
      >
        {text}
      </div>
    </div>
  )
}
