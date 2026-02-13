import { useState, useRef, KeyboardEvent } from 'react'
import { ArrowUp, Search, ChevronDown, ImageIcon, X } from 'lucide-react'
import type { Attachment } from '@/types/chat'

interface MessageInputProps {
  onSend: (content: string, attachments?: Attachment[]) => void
  disabled?: boolean
  threadId?: string
  token?: string
}

export function MessageInput({ onSend, disabled, threadId, token }: MessageInputProps) {
  const [content, setContent] = useState('')
  const [pendingImage, setPendingImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSend = async () => {
    const trimmed = content.trim()
    if ((!trimmed && !pendingImage) || disabled || uploading) return

    let attachments: Attachment[] | undefined

    if (pendingImage && threadId && token) {
      setUploading(true)
      try {
        const { uploadChatImage } = await import('@/lib/api')
        const result = await uploadChatImage(threadId, pendingImage, token)
        attachments = [{
          type: 'image',
          url: result.url,
          storage_path: result.storage_path,
        }]
      } catch {
        // If upload fails, send without attachment
      } finally {
        setUploading(false)
      }
    }

    onSend(trimmed || '(image)', attachments)
    setContent('')
    clearImage()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !file.type.startsWith('image/')) return

    setPendingImage(file)
    const reader = new FileReader()
    reader.onload = (ev) => setImagePreview(ev.target?.result as string)
    reader.readAsDataURL(file)
    // Reset file input so the same file can be re-selected
    e.target.value = ''
  }

  const clearImage = () => {
    setPendingImage(null)
    setImagePreview(null)
  }

  return (
    <div className="border-t bg-background p-4">
      <div className="mx-auto max-w-3xl">
        {imagePreview && (
          <div className="mb-2 relative inline-block">
            <img
              src={imagePreview}
              alt="Preview"
              className="h-20 rounded-lg border object-cover"
            />
            <button
              onClick={clearImage}
              className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground text-xs"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
        <div className="flex items-center gap-2 rounded-2xl border bg-background px-3 py-2 shadow-sm">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-muted-foreground hover:bg-accent transition-colors"
            title="Attach image"
          >
            <ImageIcon className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-1.5 rounded-full bg-muted/60 px-2.5 py-1 text-xs text-muted-foreground">
            <Search className="h-3 w-3" />
            <span>Research</span>
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={disabled || uploading}
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          />
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1 rounded-full bg-muted/60 px-2.5 py-1 text-xs text-muted-foreground">
              <span>verticallm 1.0</span>
              <ChevronDown className="h-3 w-3" />
            </button>
            <button
              onClick={handleSend}
              disabled={disabled || uploading || (!content.trim() && !pendingImage)}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all hover:bg-primary/90 disabled:opacity-30 disabled:bg-muted disabled:text-muted-foreground"
            >
              <ArrowUp className="h-4 w-4 stroke-[2.5]" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
