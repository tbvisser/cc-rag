import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import type { NavItem } from '@/lib/navigation'
import { useSidebar } from '@/hooks/useSidebar'

interface SidebarItemProps {
  item: NavItem
}

export function SidebarItem({ item }: SidebarItemProps) {
  const { pathname } = useLocation()
  const { isCollapsed } = useSidebar()
  const isActive = pathname === item.path
  const Icon = item.icon

  return (
    <Link
      to={item.path}
      title={isCollapsed ? item.label : undefined}
      className={cn(
        'flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors',
        isActive
          ? 'bg-accent text-accent-foreground font-medium'
          : item.hasBackend
            ? 'text-foreground hover:bg-accent/50'
            : 'text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground',
        isCollapsed && 'justify-center px-0'
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!isCollapsed && <span className="truncate">{item.label}</span>}
    </Link>
  )
}
