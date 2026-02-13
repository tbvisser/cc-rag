import { useEffect, useState, useCallback } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Plus, Search, MessageSquare, Trash2, Upload } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSidebar } from '@/hooks/useSidebar'
import { useAuth } from '@/contexts/AuthContext'
import { apiFetch } from '@/lib/api'
import { navSections, bottomNavItems } from '@/lib/navigation'
import { SidebarSection } from './SidebarSection'
import { SidebarItem } from './SidebarItem'
import type { Thread } from '@/types/chat'

export function AppSidebar() {
  const { isCollapsed } = useSidebar()
  const { session } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [threads, setThreads] = useState<Thread[]>([])
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const token = session?.access_token

  const fetchThreads = useCallback(async () => {
    if (!token) return
    try {
      const data = await apiFetch<Thread[]>('/api/threads', {}, token)
      setThreads(data)
    } catch {
      // Silently fail — threads are non-critical for sidebar
    }
  }, [token])

  useEffect(() => {
    fetchThreads()
  }, [fetchThreads])

  // Refresh threads when navigating to a chat page
  useEffect(() => {
    if (location.pathname.startsWith('/chat')) {
      fetchThreads()
    }
  }, [location.pathname, location.key, fetchThreads])

  const handleNewChat = () => {
    navigate('/chat')
  }

  const handleDeleteThread = async (threadId: string) => {
    if (!token) return
    try {
      await apiFetch(`/api/threads/${threadId}`, { method: 'DELETE' }, token)
      setThreads((prev) => prev.filter((t) => t.id !== threadId))
      if (location.pathname === `/chat/${threadId}`) {
        navigate('/chat')
      }
    } catch {
      // Silently fail
    }
  }

  const activeThreadId = location.pathname.startsWith('/chat/')
    ? location.pathname.split('/chat/')[1]
    : null

  const filteredThreads = searchQuery
    ? threads.filter((t) =>
        (t.title || 'New conversation').toLowerCase().includes(searchQuery.toLowerCase())
      )
    : threads.slice(0, 10)

  return (
    <aside
      className={cn(
        'flex h-full flex-col border-r bg-muted/30 transition-all duration-300 overflow-hidden',
        isCollapsed ? 'w-16' : 'w-60'
      )}
    >
      {/* Logo */}
      <div className={cn('flex items-center px-4 pt-4 pb-2', isCollapsed && 'justify-center px-2')}>
        <Link to="/" className="text-xl font-bold" style={{ fontFamily: 'Poppins, sans-serif' }}>
          {isCollapsed ? 'V' : 'verticallm'}
        </Link>
      </div>

      {/* New Chat + Search */}
      <div className={cn('space-y-1 px-2', isCollapsed && 'px-1')}>
        <button
          onClick={handleNewChat}
          className={cn(
            'flex w-full items-center gap-2 rounded-md border border-dashed border-border px-2.5 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors',
            isCollapsed && 'justify-center px-0'
          )}
        >
          <Plus className="h-4 w-4 shrink-0" />
          {!isCollapsed && <span>New Chat</span>}
        </button>
        {!isCollapsed && (
          <button
            onClick={() => setSearchOpen((p) => !p)}
            className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground hover:bg-accent/50 transition-colors"
          >
            <Search className="h-4 w-4 shrink-0" />
            <span>Search Chats</span>
          </button>
        )}
        {!isCollapsed && searchOpen && (
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search..."
            className="w-full rounded-md border border-input bg-background px-2.5 py-1 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            autoFocus
          />
        )}
        <Link
          to="/schema/upload"
          className={cn(
            'flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition-colors',
            location.pathname === '/schema/upload'
              ? 'bg-accent text-accent-foreground font-medium'
              : 'text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground',
            isCollapsed && 'justify-center px-0'
          )}
        >
          <Upload className="h-4 w-4 shrink-0" />
          {!isCollapsed && <span>Upload Documents</span>}
        </Link>
      </div>

      {/* Recent Threads */}
      {!isCollapsed && filteredThreads.length > 0 && (
        <div className="mt-2 px-2">
          <p className="px-2.5 pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Recent
          </p>
          <ul className="space-y-0.5">
            {filteredThreads.map((thread) => (
              <li key={thread.id}>
                <Link
                  to={`/chat/${thread.id}`}
                  className={cn(
                    'group flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition-colors hover:bg-accent',
                    activeThreadId === thread.id && 'bg-accent font-medium'
                  )}
                >
                  <MessageSquare className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="flex-1 truncate text-left">
                    {thread.title || 'New conversation'}
                  </span>
                  <button
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      handleDeleteThread(thread.id)
                    }}
                    className="opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                  </button>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Scrollable nav sections */}
      <div className="mt-2 flex-1 overflow-y-auto px-2">
        <div className={cn('space-y-0.5', isCollapsed && 'space-y-1')}>
          {navSections.map((section) => (
            <SidebarSection key={section.id} section={section} />
          ))}
        </div>
      </div>

      {/* Bottom items */}
      <div className={cn('border-t px-2 py-2 space-y-0.5', isCollapsed && 'px-1')}>
        {bottomNavItems.map((item) => (
          <SidebarItem key={item.id} item={item} />
        ))}
      </div>
    </aside>
  )
}
