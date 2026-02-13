import { Outlet } from 'react-router-dom'
import { SidebarProvider } from '@/contexts/SidebarContext'
import { AppSidebar } from './AppSidebar'
import { TopBar } from './TopBar'

export function AppLayout() {
  return (
    <SidebarProvider>
      <div className="flex h-screen">
        <AppSidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <TopBar />
          <main className="flex-1 overflow-hidden">
            <Outlet />
          </main>
        </div>
      </div>
    </SidebarProvider>
  )
}
