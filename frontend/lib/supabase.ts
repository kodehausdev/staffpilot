import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Types
export type Tenant = {
  id: string
  name: string
  whatsapp_number: string
  plan: 'starter' | 'growth' | 'enterprise'
  is_active: boolean
  created_at: string
}

export type Employee = {
  id: string
  tenant_id: string
  phone: string
  name: string | null
  email: string | null
  role: 'staff' | 'manager' | 'hr_admin'
  department: string | null
  leave_balance: number
  is_active: boolean
  created_at: string
}

export type LeaveRequest = {
  id: string
  employee_id: string
  tenant_id: string
  leave_type: 'annual' | 'sick' | 'maternity' | 'paternity' | 'unpaid'
  start_date: string
  end_date: string
  days: number
  reason: string | null
  status: 'pending' | 'approved' | 'rejected' | 'cancelled'
  manager_id: string | null
  reviewed_at: string | null
  created_at: string
  employees?: Employee
}

export type HrDocument = {
  id: string
  tenant_id: string
  title: string
  file_path: string | null
  uploaded_at: string
}

export type Payslip = {
  id: string
  employee_id: string
  tenant_id: string
  month: string
  year: number | null
  gross_pay: number
  net_pay: number
  deductions: Record<string, number>
  file_url: string | null
  created_at: string
  employees?: Employee
}
