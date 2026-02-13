import { FileText, Trash2, Loader2, CheckCircle2, XCircle, Clock, RotateCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { Document } from '@/hooks/useDocuments'

interface DocumentListProps {
  documents: Document[]
  onDelete: (documentId: string) => void
  onReingest?: (documentId: string) => void
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function StatusBadge({ status, errorMessage }: { status: Document['status']; errorMessage: string | null }) {
  switch (status) {
    case 'pending':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
          <Clock className="h-3 w-3" />
          Pending
        </span>
      )
    case 'processing':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
          <Loader2 className="h-3 w-3 animate-spin" />
          Processing
        </span>
      )
    case 'completed':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400">
          <CheckCircle2 className="h-3 w-3" />
          Ready
        </span>
      )
    case 'failed':
      return (
        <span
          className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900/30 dark:text-red-400"
          title={errorMessage || 'Processing failed'}
        >
          <XCircle className="h-3 w-3" />
          Failed
        </span>
      )
  }
}

export function DocumentList({ documents, onDelete, onReingest }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileText className="h-12 w-12 text-muted-foreground/50" />
        <p className="mt-3 text-sm text-muted-foreground">
          No documents uploaded yet
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Upload documents above to use them for RAG
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className="group flex items-center gap-3 rounded-lg border bg-card p-3 transition-colors hover:bg-accent/50"
        >
          <div className="rounded-md bg-muted p-2">
            <FileText className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="truncate text-sm font-medium">{doc.filename}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-muted-foreground">
                {formatFileSize(doc.file_size)}
              </span>
              {doc.chunk_count !== null && doc.status === 'completed' && (
                <span className="text-xs text-muted-foreground">
                  {doc.chunk_count} chunks
                </span>
              )}
            </div>
            {doc.status === 'completed' && doc.metadata?.summary && (
              <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                {doc.metadata.summary}
              </p>
            )}
            {doc.status === 'completed' && doc.metadata && (
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                {doc.metadata.document_type && (
                  <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                    {doc.metadata.document_type}
                  </span>
                )}
                {doc.metadata.topics?.slice(0, 3).map((topic) => (
                  <span
                    key={topic}
                    className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            )}
          </div>
          <StatusBadge status={doc.status} errorMessage={doc.error_message} />
          {onReingest && (doc.status === 'completed' || doc.status === 'failed') && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100"
              title="Re-process document"
              onClick={() => onReingest(doc.id)}
            >
              <RotateCw className="h-4 w-4 text-muted-foreground hover:text-blue-500" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100"
            onClick={() => onDelete(doc.id)}
          >
            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
          </Button>
        </div>
      ))}
    </div>
  )
}
