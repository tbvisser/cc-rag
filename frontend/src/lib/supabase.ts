import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// Debug: Log all VITE_ env vars
console.log('All Vite env vars:', import.meta.env)
console.log('VITE_SUPABASE_URL value:', JSON.stringify(supabaseUrl))
console.log('VITE_SUPABASE_ANON_KEY value:', supabaseAnonKey ? `${supabaseAnonKey.substring(0, 20)}...` : 'undefined')

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables:', {
    VITE_SUPABASE_URL: supabaseUrl ? 'set' : 'MISSING',
    VITE_SUPABASE_ANON_KEY: supabaseAnonKey ? 'set' : 'MISSING',
  })
}

export const supabase = createClient(supabaseUrl || '', supabaseAnonKey || '')
