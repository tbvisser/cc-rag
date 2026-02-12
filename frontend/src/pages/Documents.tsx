import { Header } from '@/components/layout/Header'
import { DocumentUpload } from '@/components/documents/DocumentUpload'
import { DocumentList } from '@/components/documents/DocumentList'
import { useDocuments } from '@/hooks/useDocuments'

export default function Documents() {
  const {
    documents,
    loading,
    uploading,
    error,
    uploadDocument,
    deleteDocument,
    clearError,
  } = useDocuments()

  return (
    <div className="flex h-screen flex-col">
      <Header />
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl p-6">
          <h2 className="text-xl font-semibold">Documents</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Upload documents to use as context for RAG-powered chat.
          </p>

          {error && (
            <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {error}
              <button onClick={clearError} className="ml-2 underline">
                Dismiss
              </button>
            </div>
          )}

          <div className="mt-6">
            <DocumentUpload onUpload={uploadDocument} uploading={uploading} />
          </div>

          <div className="mt-6">
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="text-muted-foreground">Loading documents...</div>
              </div>
            ) : (
              <DocumentList documents={documents} onDelete={deleteDocument} />
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
