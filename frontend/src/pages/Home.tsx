import { useState, KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { apiFetch } from '@/lib/api'
import { Plus, Search, ChevronDown, ArrowUp, FileText, PenSquare, Globe, Code2, Heart, Sparkles } from 'lucide-react'

const tabs = [
  { label: 'Overview', icon: FileText },
  { label: 'Map', icon: PenSquare },
  { label: 'Analytics', icon: Globe },
  { label: 'Schema', icon: Code2 },
  { label: 'Risk', icon: Heart },
  { label: "verticallm's choice", icon: Sparkles },
]

export default function Home() {
  const { user, session } = useAuth()
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  const displayName = user?.user_metadata?.display_name || user?.email?.split('@')[0] || 'there'
  const token = session?.access_token

  const handleSend = async (message?: string) => {
    const content = message || input.trim()
    if (!content || !token || sending) return

    setSending(true)
    try {
      const data = await apiFetch<{ id: string }>(
        '/api/threads',
        { method: 'POST' },
        token
      )
      navigate(`/chat/${data.id}?prompt=${encodeURIComponent(content)}`)
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-full flex-col items-center justify-center p-6">
      <div className="w-full max-w-2xl space-y-8">
        {/* Greeting */}
        <div className="text-center">
          <h1 className="text-3xl font-semibold tracking-tight">
            Hi {displayName}, how can I help you today?
          </h1>
        </div>

        {/* Chat input bar */}
        <div className="rounded-2xl border bg-background shadow-sm">
          <div className="flex items-center gap-2 px-4 py-3">
            <button className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-muted-foreground hover:bg-accent transition-colors">
              <Plus className="h-4 w-4" />
            </button>
            <div className="flex items-center gap-1.5 rounded-full bg-muted/60 px-2.5 py-1 text-xs text-muted-foreground">
              <Search className="h-3 w-3" />
              <span>Research</span>
            </div>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your supply chain..."
              rows={1}
              disabled={sending}
              className="flex-1 resize-none bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
            />
            <div className="flex items-center gap-2">
              <button className="flex items-center gap-1 rounded-full bg-muted/60 px-2.5 py-1 text-xs text-muted-foreground">
                <span>verticallm 1.0</span>
                <ChevronDown className="h-3 w-3" />
              </button>
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || sending}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all hover:bg-primary/90 disabled:opacity-30 disabled:bg-muted disabled:text-muted-foreground"
              >
                <ArrowUp className="h-4 w-4 stroke-[2.5]" />
              </button>
            </div>
          </div>
        </div>

        {/* Dashboard carousel */}
        <div>
          <img
            src="/dashboard-carousel.png"
            alt="Dashboard overview"
            className="w-full rounded-2xl"
          />
        </div>

        {/* Tab bar */}
        <div className="flex flex-wrap items-center justify-center gap-2">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.label}
                className="inline-flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm transition-colors hover:bg-muted"
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
