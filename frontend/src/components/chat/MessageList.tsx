import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { User, Bot, FileText } from 'lucide-react'
import type { SSESource } from '@/hooks/useSSE'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

interface MessageListProps {
  messages: Message[]
  streamingContent?: string
  streamingSources?: SSESource[]
}

export function MessageList({ messages, streamingContent, streamingSources }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  if (messages.length === 0 && !streamingContent) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold">Start a conversation</h2>
          <p className="mt-2 text-muted-foreground">
            Send a message to begin chatting with the AI assistant.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="mx-auto max-w-3xl space-y-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {streamingContent && (
          <>
            {streamingSources && streamingSources.length > 0 && (
              <SourcesBadge sources={streamingSources} />
            )}
            <MessageBubble
              message={{
                id: 'streaming',
                role: 'assistant',
                content: streamingContent,
                created_at: new Date().toISOString(),
              }}
              isStreaming
            />
          </>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function SourcesBadge({ sources }: { sources: SSESource[] }) {
  // Deduplicate by filename
  const unique = [...new Map(sources.map((s) => [s.filename, s])).values()]

  return (
    <div className="flex flex-wrap gap-1.5 pl-11">
      {unique.map((source) => (
        <span
          key={source.filename}
          className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground"
        >
          <FileText className="h-3 w-3" />
          {source.filename}
        </span>
      ))}
    </div>
  )
}

function MessageBubble({
  message,
  isStreaming,
}: {
  message: Message
  isStreaming?: boolean
}) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          'rounded-lg px-4 py-2',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {isStreaming && (
          <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-current" />
        )}
      </div>
    </div>
  )
}
