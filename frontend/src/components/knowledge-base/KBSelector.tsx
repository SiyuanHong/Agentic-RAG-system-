import { Link } from '@tanstack/react-router'
import { useKBs } from '@/lib/hooks'
import { Database, Plus } from 'lucide-react'

export function KBSelector() {
  const { data: kbs, isLoading } = useKBs()

  return (
    <div className="p-2">
      <div className="mb-2 flex items-center justify-between px-2">
        <span className="text-xs font-medium uppercase tracking-wider text-sidebar-foreground/60">
          Knowledge Bases
        </span>
        <Link to="/kb/new" className="rounded p-1 hover:bg-sidebar-accent">
          <Plus className="h-3.5 w-3.5" />
        </Link>
      </div>

      {isLoading ? (
        <p className="px-2 text-sm text-sidebar-foreground/60">Loading...</p>
      ) : kbs?.length === 0 ? (
        <p className="px-2 text-sm text-sidebar-foreground/60">None yet</p>
      ) : (
        kbs?.map((kb) => (
          <Link
            key={kb.id}
            to="/kb/$kbId"
            params={{ kbId: kb.id }}
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-sidebar-accent"
            activeProps={{ className: 'bg-sidebar-accent font-medium' }}
          >
            <Database className="h-4 w-4 shrink-0 opacity-70" />
            <span className="truncate">{kb.name}</span>
            <span className="ml-auto text-xs opacity-50">{kb.document_count}</span>
          </Link>
        ))
      )}
    </div>
  )
}
