import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { apiFetch, apiStreamUrl } from '@/lib/api'
import { useSSE } from './useSSE'
import type { SSESource } from './useSSE'
import type { Thread } from '@/components/layout/Sidebar'
import type { Message } from '@/components/chat/MessageList'

interface ThreadWithMessages {
  id: string
  title: string | null
  messages: Message[]
}

export function useChat() {
  const { session } = useAuth()
  const [threads, setThreads] = useState<Thread[]>([])
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingSources, setStreamingSources] = useState<SSESource[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { startStream, stopStream, isStreaming } = useSSE()

  const token = session?.access_token

  const fetchThreads = useCallback(async () => {
    if (!token) return

    try {
      const data = await apiFetch<Thread[]>('/api/threads', {}, token)
      setThreads(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch threads')
    }
  }, [token])

  const fetchThread = useCallback(
    async (threadId: string) => {
      if (!token) return

      setLoading(true)
      try {
        const data = await apiFetch<ThreadWithMessages>(
          `/api/threads/${threadId}`,
          {},
          token
        )
        setMessages(data.messages)
        setActiveThreadId(threadId)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch thread')
      } finally {
        setLoading(false)
      }
    },
    [token]
  )

  const createThread = useCallback(async () => {
    if (!token) return

    setLoading(true)
    try {
      const data = await apiFetch<{ id: string }>(
        '/api/threads',
        { method: 'POST' },
        token
      )
      await fetchThreads()
      setActiveThreadId(data.id)
      setMessages([])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create thread')
    } finally {
      setLoading(false)
    }
  }, [token, fetchThreads])

  const deleteThread = useCallback(
    async (threadId: string) => {
      if (!token) return

      try {
        await apiFetch(`/api/threads/${threadId}`, { method: 'DELETE' }, token)
        await fetchThreads()
        if (activeThreadId === threadId) {
          setActiveThreadId(null)
          setMessages([])
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete thread')
      }
    },
    [token, activeThreadId, fetchThreads]
  )

  const sendMessage = useCallback(
    async (content: string) => {
      if (!token || !activeThreadId) return

      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMessage])
      setStreamingContent('')
      setStreamingSources([])

      const url = apiStreamUrl(`/api/threads/${activeThreadId}/messages`)

      await startStream(
        url,
        { content },
        token,
        {
          onMessage: (data) => {
            setStreamingContent((prev) => prev + data)
          },
          onSources: (sources) => {
            setStreamingSources(sources)
          },
          onError: (err) => {
            setError(err.message)
          },
          onComplete: () => {
            setStreamingContent((prev) => {
              if (prev) {
                const assistantMessage: Message = {
                  id: `assistant-${Date.now()}`,
                  role: 'assistant',
                  content: prev,
                  created_at: new Date().toISOString(),
                }
                setMessages((msgs) => [...msgs, assistantMessage])
              }
              return ''
            })
            setStreamingSources([])
            fetchThreads() // Refresh to get updated title
          },
        }
      )
    },
    [token, activeThreadId, startStream, fetchThreads]
  )

  useEffect(() => {
    fetchThreads()
  }, [fetchThreads])

  return {
    threads,
    activeThreadId,
    messages,
    streamingContent,
    streamingSources,
    loading,
    error,
    isStreaming,
    selectThread: fetchThread,
    createThread,
    deleteThread,
    sendMessage,
    stopStream,
    clearError: () => setError(null),
  }
}
