import { Header } from '@/components/layout/Header'
import { Sidebar } from '@/components/layout/Sidebar'
import { MessageList } from '@/components/chat/MessageList'
import { MessageInput } from '@/components/chat/MessageInput'
import { useChat } from '@/hooks/useChat'

export default function Chat() {
  const {
    threads,
    activeThreadId,
    messages,
    streamingContent,
    streamingSources,
    loading,
    error,
    isStreaming,
    selectThread,
    createThread,
    deleteThread,
    sendMessage,
    clearError,
  } = useChat()

  return (
    <div className="flex h-screen flex-col">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          threads={threads}
          activeThreadId={activeThreadId}
          onSelectThread={selectThread}
          onNewThread={createThread}
          onDeleteThread={deleteThread}
        />
        <main className="flex flex-1 flex-col">
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
          ) : activeThreadId ? (
            <>
              <MessageList messages={messages} streamingContent={streamingContent} streamingSources={streamingSources} />
              <MessageInput onSend={sendMessage} disabled={isStreaming} />
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <div className="text-center">
                <h2 className="text-xl font-semibold">Welcome</h2>
                <p className="mt-2 text-muted-foreground">
                  Select a conversation or start a new one.
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
