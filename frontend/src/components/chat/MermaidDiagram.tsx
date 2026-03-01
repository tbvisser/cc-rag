import { useEffect, useRef, useState, useId } from 'react'
import mermaid from 'mermaid'

interface MermaidDiagramProps {
  code: string
}

export function MermaidDiagram({ code }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const uniqueId = `mermaid-${useId().replace(/:/g, '')}`

  useEffect(() => {
    const isDark = document.documentElement.classList.contains('dark')

    mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? 'dark' : 'default',
      securityLevel: 'strict',
    })

    let cancelled = false

    async function render() {
      try {
        const { svg } = await mermaid.render(uniqueId, code)
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to render diagram')
        }
        // mermaid.render creates a temp element on failure — clean it up
        document.getElementById('d' + uniqueId)?.remove()
      }
    }

    render()

    return () => {
      cancelled = true
    }
  }, [code, uniqueId])

  if (error) {
    return (
      <pre className="rounded-md bg-muted p-4 text-sm overflow-x-auto">
        <code>{code}</code>
      </pre>
    )
  }

  return <div ref={containerRef} className="my-2 flex justify-center [&>svg]:max-w-full" />
}
