import { useAuth } from '@/contexts/AuthContext'
import { useLocation, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LogOut, MessageSquare, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  const { pathname } = useLocation()
  const isActive = pathname === to

  return (
    <Link
      to={to}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
        isActive
          ? 'bg-accent text-accent-foreground'
          : 'text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground'
      )}
    >
      {children}
    </Link>
  )
}

export function Header() {
  const { user, signOut } = useAuth()

  return (
    <header className="border-b bg-background">
      <div className="flex h-14 items-center justify-between px-4">
        <div className="flex items-center">
          <h1 className="w-64 text-2xl" style={{ fontFamily: 'Poppins, sans-serif', fontWeight: 700 }}>Verticallm</h1>
          <nav className="flex items-center gap-1">
            <NavLink to="/">
              <MessageSquare className="h-4 w-4" />
              Chat
            </NavLink>
            <NavLink to="/documents">
              <FileText className="h-4 w-4" />
              Documents
            </NavLink>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">{user?.email}</span>
          <Button variant="ghost" size="icon" onClick={signOut} title="Sign out">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  )
}
