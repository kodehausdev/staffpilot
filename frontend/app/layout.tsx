import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from '@/lib/auth-context'

export const metadata: Metadata = {
  title: 'CordHR — HR Dashboard',
  description: 'AI-powered WhatsApp HR assistant for modern teams',
  other: {
    'facebook-domain-verification': 'kbfad64xdja1huc5smqvdxo21fnz2v',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-sp-bg text-sp-text font-sans antialiased">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
