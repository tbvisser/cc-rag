import { useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import type { RealtimePostgresUpdatePayload } from '@supabase/supabase-js'
import type { Document } from './useDocuments'

export function useDocumentStatus(
  onDocumentUpdate: (document: Document) => void
) {
  useEffect(() => {
    const channel = supabase
      .channel('document-status')
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'documents',
        },
        (payload: RealtimePostgresUpdatePayload<Document>) => {
          onDocumentUpdate(payload.new as Document)
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [onDocumentUpdate])
}
