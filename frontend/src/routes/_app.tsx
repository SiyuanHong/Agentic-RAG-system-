import { createFileRoute, Outlet, redirect, useNavigate } from '@tanstack/react-router'
import { getToken, clearToken } from '@/lib/auth'
import { KBSelector } from '@/components/knowledge-base/KBSelector'
import { BookOpen, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'

export const Route = createFileRoute('/_app')({
  beforeLoad: () => {
    if (!getToken()) {
      throw redirect({ to: '/login' })
    }
  },
  component: AppLayout,
})

function AppLayout() {
  const navigate = useNavigate()

  function handleLogout() {
    clearToken()
    navigate({ to: '/login' })
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="flex w-72 flex-col bg-sidebar-background text-sidebar-foreground">
        <div className="flex items-center gap-2 p-4">
          <BookOpen className="h-6 w-6" />
          <h1 className="text-lg font-semibold">Agentic RAG</h1>
        </div>
        <Separator className="bg-sidebar-border" />
        <ScrollArea className="flex-1">
          <KBSelector />
        </ScrollArea>
        <Separator className="bg-sidebar-border" />
        <div className="p-2">
          <Button
            variant="ghost"
            className="w-full justify-start text-sidebar-foreground hover:bg-sidebar-accent"
            onClick={handleLogout}
          >
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-background">
        <Outlet />
      </main>
    </div>
  )
}
