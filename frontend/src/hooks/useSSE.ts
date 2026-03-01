import { useCallback, useRef, useState } from 'react'

export interface SSESource {
  filename: string
  similarity: number
}

export interface SSEImageRef {
  url: string
  alt: string
  label?: string
  doc_id: string
  index: number
  page?: number
}

export interface SSEToolCall {
  name: string
  arguments: Record<string, unknown>
}

export interface SSEToolResult {
  name: string
  result: string
}

export interface SSESubAgentEvent {
  type: 'tool_call' | 'tool_result' | 'content'
  tool_call?: SSEToolCall
  tool_result?: SSEToolResult
  content?: string
}

interface UseSSEOptions {
  onMessage: (data: string) => void
  onSources?: (sources: SSESource[]) => void
  onImages?: (images: SSEImageRef[]) => void
  onToolCall?: (toolCall: SSEToolCall) => void
  onToolResult?: (toolResult: SSEToolResult) => void
  onSubAgentEvent?: (event: SSESubAgentEvent) => void
  onError?: (error: Error) => void
  onComplete?: () => void
}

export function useSSE() {
  const [isStreaming, setIsStreaming] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const startStream = useCallback(
    async (url: string, body: object, token: string, options: UseSSEOptions) => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }

      abortControllerRef.current = new AbortController()
      setIsStreaming(true)

      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(body),
          signal: abortControllerRef.current.signal,
        })

        if (!response.ok) {
          const error = await response.json().catch(() => ({ detail: 'Stream failed' }))
          throw new Error(error.detail || 'Stream failed')
        }

        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('No response body')
        }

        const decoder = new TextDecoder()
        let buffer = ''
        let completed = false

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()
              if (data === '[DONE]') {
                completed = true
                options.onComplete?.()
              } else {
                try {
                  const parsed = JSON.parse(data)
                  if (parsed.sub_agent_event) {
                    options.onSubAgentEvent?.(parsed.sub_agent_event)
                  } else if (parsed.tool_call) {
                    options.onToolCall?.(parsed.tool_call)
                  } else if (parsed.tool_result) {
                    options.onToolResult?.(parsed.tool_result)
                  } else if (parsed.images) {
                    options.onImages?.(parsed.images)
                  } else if (parsed.sources) {
                    options.onSources?.(parsed.sources)
                  } else if (parsed.content) {
                    options.onMessage(parsed.content)
                  }
                } catch {
                  // Not JSON, treat as raw text
                  options.onMessage(data)
                }
              }
            }
          }
        }

        // Flush any remaining buffer (partial line without trailing newline)
        if (buffer.trim().startsWith('data: ')) {
          const data = buffer.trim().slice(6).trim()
          if (data === '[DONE]') {
            completed = true
          } else if (data) {
            try {
              const parsed = JSON.parse(data)
              if (parsed.sub_agent_event) {
                options.onSubAgentEvent?.(parsed.sub_agent_event)
              } else if (parsed.tool_call) {
                options.onToolCall?.(parsed.tool_call)
              } else if (parsed.tool_result) {
                options.onToolResult?.(parsed.tool_result)
              } else if (parsed.images) {
                options.onImages?.(parsed.images)
              } else if (parsed.sources) {
                options.onSources?.(parsed.sources)
              } else if (parsed.content) {
                options.onMessage(parsed.content)
              }
            } catch {
              options.onMessage(data)
            }
          }
        }

        if (!completed) {
          options.onComplete?.()
        }
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          options.onError?.(error)
        }
      } finally {
        setIsStreaming(false)
        abortControllerRef.current = null
      }
    },
    []
  )

  const stopStream = useCallback(() => {
    abortControllerRef.current?.abort()
    setIsStreaming(false)
  }, [])

  return { startStream, stopStream, isStreaming }
}
