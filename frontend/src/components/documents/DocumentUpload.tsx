import { useCallback, useState, useRef } from 'react'
import { Upload, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface DocumentUploadProps {
  onUpload: (file: File) => void
  uploading: boolean
}

const ACCEPTED_TYPES = [
  'text/plain',
  'text/markdown',
  'text/csv',
  'application/pdf',
  'application/json',
]

export function DocumentUpload({ onUpload, uploading }: DocumentUploadProps) {
  const [dragActive, setDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    (file: File) => {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        alert(`File type "${file.type || 'unknown'}" is not supported.\nSupported: .txt, .md, .csv, .pdf, .json`)
        return
      }
      onUpload(file)
    },
    [onUpload]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragActive(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
  }, [])

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) handleFile(file)
      if (inputRef.current) inputRef.current.value = ''
    },
    [handleFile]
  )

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={cn(
        'flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors',
        dragActive
          ? 'border-primary bg-primary/5'
          : 'border-muted-foreground/25 hover:border-muted-foreground/50',
        uploading && 'pointer-events-none opacity-50'
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.md,.csv,.pdf,.json"
        onChange={handleInputChange}
        className="hidden"
      />

      {uploading ? (
        <>
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-muted-foreground border-t-primary" />
          <p className="mt-3 text-sm text-muted-foreground">Uploading...</p>
        </>
      ) : (
        <>
          <div className="rounded-full bg-muted p-3">
            {dragActive ? (
              <FileText className="h-6 w-6 text-primary" />
            ) : (
              <Upload className="h-6 w-6 text-muted-foreground" />
            )}
          </div>
          <p className="mt-3 text-sm font-medium">
            {dragActive ? 'Drop file here' : 'Drag & drop a file here'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            .txt, .md, .csv, .pdf, .json (max 50MB)
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => inputRef.current?.click()}
          >
            Browse files
          </Button>
        </>
      )}
    </div>
  )
}
