'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/components/layout/Sidebar'
import { useAuth } from '@/lib/auth-context'
import { Spinner } from '@/components/ui'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) router.replace('/login')
  }, [user, loading])

  if (loading) return (
    <div className="min-h-screen bg-sp-bg flex items-center justify-center">
      <Spinner />
    </div>
  )

  if (!user) return null

  return (
    <div className="min-h-screen bg-sp-bg flex">
      <Sidebar />
      <main className="ml-60 flex-1 p-8">
        <div className="max-w-5xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  )
}
