import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import { Bot, FileText, ImageIcon } from 'lucide-react'
import type { SSESource, SSEImageRef } from '@/hooks/useSSE'
import { AuthenticatedImage } from './AuthenticatedImage'

import type { Message, Attachment } from '@/types/chat'

interface MessageListProps {
  messages: Message[]
  streamingContent?: string
  streamingSources?: SSESource[]
  streamingImages?: SSEImageRef[]
  isStreaming?: boolean
  userInitials?: string
}

export function MessageList({ messages, streamingContent, streamingSources, streamingImages, isStreaming, userInitials }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  if (messages.length === 0 && !streamingContent && !isStreaming) {
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

  const showThinking = isStreaming && !streamingContent

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="mx-auto max-w-3xl space-y-4">
        {messages.map((message) => {
          const docImages = message.role === 'assistant'
            ? (message.attachments?.filter(a => a.type === 'document_image') || [])
            : []
          return (
            <div key={message.id}>
              <MessageBubble message={message} userInitials={userInitials} />
              {docImages.length > 0 && <DocumentImages images={docImages} />}
            </div>
          )
        })}
        {showThinking && <ThinkingIndicator />}
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
            {streamingImages && streamingImages.length > 0 && (
              <DocumentImages images={streamingImages.map((img) => ({ type: 'document_image', url: img.url, alt: img.alt }))} />
            )}
          </>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function ThinkingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
        <Bot className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="rounded-lg bg-muted px-4 py-3">
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:0ms]" />
          <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:150ms]" />
          <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:300ms]" />
        </div>
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

function DocumentImages({ images }: { images: Attachment[] }) {
  if (images.length === 0) return null

  return (
    <div className="pl-11 mt-2">
      <span className="flex items-center gap-1 text-xs text-muted-foreground mb-1.5">
        <ImageIcon className="h-3 w-3" />
        Document images
      </span>
      <div className="flex flex-wrap gap-2">
        {images.map((img, i) => (
          <AuthenticatedImage
            key={i}
            src={img.url}
            alt={img.alt || `Document image ${i + 1}`}
            className="h-40 w-40 rounded-md object-cover border"
          />
        ))}
      </div>
    </div>
  )
}

function MessageBubble({
  message,
  isStreaming,
  userInitials,
}: {
  message: Message
  isStreaming?: boolean
  userInitials?: string
}) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground'
        )}
      >
        {isUser ? (userInitials || 'U') : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          'rounded-lg px-4 py-2',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        )}
      >
        {/* Render user-attached images */}
        {message.attachments?.filter(a => a.type === 'image').map((att, i) => (
          <AuthenticatedImage
            key={i}
            src={att.url}
            alt={att.alt || 'Attached image'}
            className="max-w-full rounded-lg mb-2"
          />
        ))}
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                img: ({ src, alt }) => (
                  <AuthenticatedImage
                    src={src || ''}
                    alt={alt || ''}
                    className="max-w-full rounded-lg my-2"
                  />
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
        {isStreaming && (
          <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-current" />
        )}
      </div>
    </div>
  )
}
