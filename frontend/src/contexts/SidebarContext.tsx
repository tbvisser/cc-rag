import { createContext, useState, useCallback, useEffect, ReactNode } from 'react'

interface SidebarContextType {
  isCollapsed: boolean
  openSections: Set<string>
  toggleSidebar: () => void
  toggleSection: (id: string) => void
}

export const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

const COLLAPSED_KEY = 'sidebar-collapsed'
const SECTIONS_KEY = 'sidebar-open-sections'

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const stored = localStorage.getItem(COLLAPSED_KEY)
    return stored === 'true'
  })

  const [openSections, setOpenSections] = useState<Set<string>>(() => {
    try {
      const stored = localStorage.getItem(SECTIONS_KEY)
      return stored ? new Set(JSON.parse(stored)) : new Set<string>()
    } catch {
      return new Set<string>()
    }
  })

  useEffect(() => {
    localStorage.setItem(COLLAPSED_KEY, String(isCollapsed))
  }, [isCollapsed])

  useEffect(() => {
    localStorage.setItem(SECTIONS_KEY, JSON.stringify([...openSections]))
  }, [openSections])

  const toggleSidebar = useCallback(() => {
    setIsCollapsed((prev) => !prev)
  }, [])

  const toggleSection = useCallback((id: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  return (
    <SidebarContext.Provider value={{ isCollapsed, openSections, toggleSidebar, toggleSection }}>
      {children}
    </SidebarContext.Provider>
  )
}
