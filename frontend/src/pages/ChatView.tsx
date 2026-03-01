import { useEffect, useCallback, useRef, useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { MessageList } from '@/components/chat/MessageList'
import { MessageInput } from '@/components/chat/MessageInput'
import { useChat } from '@/hooks/useChat'
import { useAuth } from '@/contexts/AuthContext'

function getUserInitials(user: { user_metadata?: Record<string, unknown>; email?: string } | null): string {
  const displayName = (user?.user_metadata?.display_name as string) || ''
  if (displayName) {
    const parts = displayName.trim().split(/\s+/)
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    return parts[0][0].toUpperCase()
  }
  const email = user?.email || ''
  if (email) return email[0].toUpperCase()
  return 'U'
}

export default function ChatView() {
  const { threadId } = useParams<{ threadId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { session, user } = useAuth()
  const promptHandled = useRef(false)
  const prevLoadingRef = useRef(false)
  const userInitials = getUserInitials(user)

  const [creating, setCreating] = useState(false)

  const {
    messages,
    streamingContent,
    streamingSources,
    streamingImages,
    streamingToolSteps,
    loading,
    error,
    isStreaming,
    activeThreadId,
    selectThread,
    createThread,
    sendMessage,
    clearError,
  } = useChat()

  // Stable ref for selectThread to avoid re-firing when function reference changes
  const selectThreadRef = useRef(selectThread)
  selectThreadRef.current = selectThread

  // Load thread when threadId changes (not when selectThread reference changes)
  useEffect(() => {
    if (threadId) {
      promptHandled.current = false
      // Reset so auto-send only responds to fetchThread's loading transition,
      // not a stale transition from createThread.
      prevLoadingRef.current = false
      selectThreadRef.current(threadId)
    }
  }, [threadId])

  // Auto-send prompt from query param — only after thread loading finishes
  useEffect(() => {
    const wasLoading = prevLoadingRef.current
    prevLoadingRef.current = loading

    const prompt = searchParams.get('prompt')
    if (
      prompt &&
      threadId &&
      activeThreadId === threadId &&
      !promptHandled.current &&
      wasLoading && !loading &&
      messages.length === 0
    ) {
      promptHandled.current = true
      setSearchParams({}, { replace: true })
      sendMessage(prompt)
    }
  }, [searchParams, threadId, activeThreadId, loading, messages.length, sendMessage, setSearchParams])

  if (!threadId) {
    return (
      <div className="flex h-full flex-col">
        <MessageList messages={[]} userInitials={userInitials} />
        <MessageInput
          onSend={async (content) => {
            if (creating) return
            setCreating(true)
            try {
              const newId = await createThread()
              if (newId) {
                navigate(`/chat/${newId}?prompt=${encodeURIComponent(content)}`)
              }
            } finally {
              setCreating(false)
            }
          }}
          disabled={loading || creating}
        />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {error && (
        <div className="m-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
          <button onClick={clearError} className="ml-2 underline">
            Dismiss
          </button>
        </div>
      )}
      {loading ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      ) : (
        <>
          <MessageList
            messages={messages}
            streamingContent={streamingContent}
            streamingSources={streamingSources}
            streamingImages={streamingImages}
            streamingToolSteps={streamingToolSteps}
            isStreaming={isStreaming}
            userInitials={userInitials}
          />
          <MessageInput
            onSend={sendMessage}
            disabled={isStreaming}
            threadId={threadId}
            token={session?.access_token}
          />
        </>
      )}
    </div>
  )
}
