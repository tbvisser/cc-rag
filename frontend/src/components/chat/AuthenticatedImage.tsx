import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
import { X } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface AuthenticatedImageProps {
  src: string
  alt?: string
  className?: string
  zoomable?: boolean
}

export function AuthenticatedImage({ src, alt, className, zoomable = true }: AuthenticatedImageProps) {
  const { session } = useAuth()
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [zoomed, setZoomed] = useState(false)

  const needsAuth = src.startsWith('/api/')

  useEffect(() => {
    if (!needsAuth) return

    const token = session?.access_token
    if (!token) {
      setError(true)
      return
    }

    let revoke: string | null = null
    setLoading(true)
    setError(false)

    fetch(`${API_URL}${src}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch image')
        return res.blob()
      })
      .then((blob) => {
        revoke = URL.createObjectURL(blob)
        setBlobUrl(revoke)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))

    return () => {
      if (revoke) URL.revokeObjectURL(revoke)
    }
  }, [src, needsAuth, session?.access_token])

  const handleClose = useCallback(() => setZoomed(false), [])

  const resolvedSrc = needsAuth ? blobUrl : src

  if (loading) {
    return <div className={cn('animate-pulse rounded-lg bg-muted', className)} style={{ minHeight: 80, minWidth: 80 }} />
  }

  if (error || (needsAuth && !blobUrl)) {
    return (
      <div className={cn('flex items-center justify-center rounded-lg bg-muted text-xs text-muted-foreground', className)} style={{ minHeight: 80, minWidth: 80 }}>
        Image unavailable
      </div>
    )
  }

  return (
    <>
      <img
        src={resolvedSrc || ''}
        alt={alt || ''}
        className={cn(className, zoomable && 'cursor-zoom-in')}
        loading="lazy"
        onClick={zoomable ? () => setZoomed(true) : undefined}
      />
      {zoomed && (
        <ImageLightbox src={resolvedSrc || ''} alt={alt || ''} onClose={handleClose} />
      )}
    </>
  )
}

function ImageLightbox({ src, alt, onClose }: { src: string; alt: string; onClose: () => void }) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute right-4 top-4 rounded-full bg-black/50 p-2 text-white hover:bg-black/70"
      >
        <X className="h-5 w-5" />
      </button>
      <img
        src={src}
        alt={alt}
        className="max-h-[85vh] max-w-[85vw] min-h-[50vh] rounded-lg object-contain"
        style={{ imageRendering: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  )
}
