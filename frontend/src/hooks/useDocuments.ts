import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { apiFetch } from '@/lib/api'
import { useDocumentStatus } from './useDocumentStatus'

export interface Document {
  id: string
  user_id: string
  filename: string
  file_type: string
  file_size: number
  storage_path: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  error_message: string | null
  chunk_count: number | null
  created_at: string
  updated_at: string
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useDocuments() {
  const { session } = useAuth()
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const token = session?.access_token

  const fetchDocuments = useCallback(async () => {
    if (!token) return

    setLoading(true)
    try {
      const data = await apiFetch<Document[]>('/api/documents', {}, token)
      setDocuments(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch documents')
    } finally {
      setLoading(false)
    }
  }, [token])

  const uploadDocument = useCallback(
    async (file: File) => {
      if (!token) return

      setUploading(true)
      setError(null)
      try {
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch(`${API_URL}/api/documents`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        })

        if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: 'Upload failed' }))
          throw new Error(err.detail || 'Upload failed')
        }

        await fetchDocuments()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to upload document')
      } finally {
        setUploading(false)
      }
    },
    [token, fetchDocuments]
  )

  const deleteDocument = useCallback(
    async (documentId: string) => {
      if (!token) return

      try {
        await apiFetch(`/api/documents/${documentId}`, { method: 'DELETE' }, token)
        setDocuments((prev) => prev.filter((d) => d.id !== documentId))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete document')
      }
    },
    [token]
  )

  const handleDocumentUpdate = useCallback((updated: Document) => {
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === updated.id ? { ...doc, ...updated } : doc
      )
    )
  }, [])

  useDocumentStatus(handleDocumentUpdate)

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  return {
    documents,
    loading,
    uploading,
    error,
    uploadDocument,
    deleteDocument,
    refreshDocuments: fetchDocuments,
    clearError: () => setError(null),
  }
}
