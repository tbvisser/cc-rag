import { useLocation } from 'react-router-dom'
import { Construction } from 'lucide-react'

export default function PlaceholderPage() {
  const { pathname } = useLocation()

  // Derive a readable title from the path
  const segments = pathname.split('/').filter(Boolean)
  const title = segments
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1).replace(/-/g, ' '))
    .join(' — ')

  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <Construction className="mx-auto h-12 w-12 text-muted-foreground/50" />
        <h2 className="mt-4 text-xl font-semibold">{title || 'Page'}</h2>
        <p className="mt-2 text-muted-foreground">
          Coming soon — this feature is under development.
        </p>
      </div>
    </div>
  )
}
