import { useState, useCallback, useEffect, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { apiFetch, apiStreamUrl } from '@/lib/api'
import { useSSE } from './useSSE'
import type { SSESource, SSEImageRef, SSEToolCall, SSEToolResult, SSESubAgentEvent } from './useSSE'
import type { Thread, Message, Attachment } from '@/types/chat'

export interface ToolStep {
  type: 'call' | 'result'
  name: string
  arguments?: Record<string, unknown>
  result?: string
  subSteps?: ToolStep[]
  subContent?: string
}

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
  const [streamingImages, setStreamingImages] = useState<SSEImageRef[]>([])
  const [streamingToolSteps, setStreamingToolSteps] = useState<ToolStep[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { startStream, stopStream, isStreaming } = useSSE()
  const fetchIdRef = useRef(0)
  const streamingImagesRef = useRef<SSEImageRef[]>([])

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

      stopStream()
      setMessages([])
      setStreamingContent('')
      setStreamingSources([])
      setStreamingImages([])
      setStreamingToolSteps([])
      setLoading(true)

      const fetchId = ++fetchIdRef.current

      try {
        const data = await apiFetch<ThreadWithMessages>(
          `/api/threads/${threadId}`,
          {},
          token
        )
        if (fetchId !== fetchIdRef.current) return // stale (StrictMode double-invoke)
        setMessages(data.messages)
        setActiveThreadId(threadId)
      } catch (err) {
        if (fetchId !== fetchIdRef.current) return
        setError(err instanceof Error ? err.message : 'Failed to fetch thread')
      } finally {
        if (fetchId === fetchIdRef.current) {
          setLoading(false)
        }
      }
    },
    [token, stopStream]
  )

  const createThread = useCallback(async (): Promise<string | undefined> => {
    if (!token) return undefined

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
      return data.id
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create thread')
      return undefined
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
    async (content: string, attachments?: Attachment[]) => {
      if (!token || !activeThreadId) return

      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content,
        attachments,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMessage])
      setStreamingContent('')
      setStreamingSources([])
      setStreamingImages([])
      setStreamingToolSteps([])

      const url = apiStreamUrl(`/api/threads/${activeThreadId}/messages`)

      await startStream(
        url,
        { content, attachments },
        token,
        {
          onMessage: (data) => {
            setStreamingContent((prev) => prev + data)
          },
          onSources: (sources) => {
            setStreamingSources(sources)
          },
          onImages: (images) => {
            setStreamingImages(images)
            streamingImagesRef.current = images
          },
          onToolCall: (toolCall: SSEToolCall) => {
            setStreamingToolSteps((prev) => [...prev, { type: 'call', name: toolCall.name, arguments: toolCall.arguments }])
          },
          onToolResult: (toolResult: SSEToolResult) => {
            setStreamingToolSteps((prev) => [...prev, { type: 'result', name: toolResult.name, result: toolResult.result }])
          },
          onSubAgentEvent: (event: SSESubAgentEvent) => {
            setStreamingToolSteps((prev) => {
              const updated = [...prev]
              // Find the last analyze_document call step
              let parentIdx = -1
              for (let i = updated.length - 1; i >= 0; i--) {
                if (updated[i].type === 'call' && updated[i].name === 'analyze_document') {
                  parentIdx = i
                  break
                }
              }
              if (parentIdx === -1) return prev

              const parent = { ...updated[parentIdx] }
              if (event.type === 'tool_call' && event.tool_call) {
                parent.subSteps = [...(parent.subSteps || []), { type: 'call', name: event.tool_call.name, arguments: event.tool_call.arguments }]
              } else if (event.type === 'tool_result' && event.tool_result) {
                parent.subSteps = [...(parent.subSteps || []), { type: 'result', name: event.tool_result.name, result: event.tool_result.result }]
              } else if (event.type === 'content' && event.content) {
                parent.subContent = (parent.subContent || '') + event.content
              }
              updated[parentIdx] = parent
              return updated
            })
          },
          onError: (err) => {
            setError(err.message)
          },
          onComplete: () => {
            // Capture ref value before clearing — the setState updater runs
            // later during render, so the ref would already be empty by then.
            const capturedImages = streamingImagesRef.current
            setStreamingContent((prev) => {
              if (prev) {
                const imageAttachments: Attachment[] = capturedImages.map((img) => ({
                  type: 'document_image',
                  url: img.url,
                  alt: img.alt,
                }))
                const assistantMessage: Message = {
                  id: `assistant-${Date.now()}`,
                  role: 'assistant',
                  content: prev,
                  attachments: imageAttachments.length > 0 ? imageAttachments : undefined,
                  created_at: new Date().toISOString(),
                }
                setMessages((msgs) => [...msgs, assistantMessage])
              }
              return ''
            })
            setStreamingSources([])
            setStreamingImages([])
            setStreamingToolSteps([])
            streamingImagesRef.current = []
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
    streamingImages,
    streamingToolSteps,
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
