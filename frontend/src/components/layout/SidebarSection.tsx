import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSidebar } from '@/hooks/useSidebar'
import { SidebarItem } from './SidebarItem'
import type { NavSection } from '@/lib/navigation'

interface SidebarSectionProps {
  section: NavSection
}

export function SidebarSection({ section }: SidebarSectionProps) {
  const { isCollapsed, openSections, toggleSection } = useSidebar()
  const isOpen = openSections.has(section.id)
  const Icon = section.icon

  if (isCollapsed) {
    return (
      <div className="flex flex-col items-center gap-0.5 py-1">
        <button
          onClick={() => toggleSection(section.id)}
          title={section.label}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
        >
          <Icon className="h-4 w-4" />
        </button>
      </div>
    )
  }

  return (
    <div className="py-1">
      <button
        onClick={() => toggleSection(section.id)}
        className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground"
      >
        <ChevronRight
          className={cn(
            'h-3.5 w-3.5 shrink-0 transition-transform duration-200',
            isOpen && 'rotate-90'
          )}
        />
        <Icon className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{section.label}</span>
      </button>
      <div
        className="grid transition-[grid-template-rows] duration-200"
        style={{ gridTemplateRows: isOpen ? '1fr' : '0fr' }}
      >
        <div className="overflow-hidden">
          <div className="ml-3 mt-0.5 space-y-0.5 border-l pl-2">
            {section.items.map((item) => (
              <SidebarItem key={item.id} item={item} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
