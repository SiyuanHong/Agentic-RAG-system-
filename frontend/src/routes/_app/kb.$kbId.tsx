import { createFileRoute, Link, Outlet, useNavigate } from '@tanstack/react-router'
import { useKB, useConversations, useDocuments } from '@/lib/hooks'
import { createConversation, deleteConversation } from '@/lib/api'
import { queryClient } from '@/lib/queryClient'
import { DocumentUpload } from '@/components/knowledge-base/DocumentUpload'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { MessageSquarePlus, MessageSquare, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

export const Route = createFileRoute('/_app/kb/$kbId')({
  component: KBDetailPage,
})

function KBDetailPage() {
  const { kbId } = Route.useParams()
  const navigate = useNavigate()
  const { data: kb } = useKB(kbId)
  const { data: conversations } = useConversations(kbId)
  const { data: docs } = useDocuments(kbId)

  const completedDocs = docs?.filter((d) => d.status === 'completed').length ?? 0

  async function handleNewChat() {
    try {
      const conv = await createConversation(kbId)
      queryClient.invalidateQueries({ queryKey: ['conversations', kbId] })
      navigate({
        to: '/kb/$kbId/chat/$conversationId',
        params: { kbId, conversationId: conv.id },
      })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create conversation')
    }
  }

  return (
    <div className="flex h-full">
      {/* KB sidebar panel */}
      <div className="flex w-80 flex-col border-r">
        <div className="p-4">
          <h2 className="text-lg font-semibold">{kb?.name ?? 'Loading...'}</h2>
          {kb?.description && (
            <p className="mt-1 text-sm text-muted-foreground">{kb.description}</p>
          )}
          <p className="mt-1 text-xs text-muted-foreground">
            {completedDocs} document{completedDocs !== 1 ? 's' : ''} indexed
          </p>
        </div>

        <Separator />
        <div className="p-4">
          <DocumentUpload kbId={kbId} />
        </div>

        <Separator />
        <div className="flex items-center justify-between p-4 pb-2">
          <h3 className="text-sm font-medium">Conversations</h3>
          <Button size="sm" variant="outline" onClick={handleNewChat}>
            <MessageSquarePlus className="mr-1 h-3 w-3" />
            New Chat
          </Button>
        </div>

        <div className="flex-1 overflow-auto px-2 pb-2">
          {conversations?.length === 0 ? (
            <p className="p-2 text-center text-sm text-muted-foreground">
              No conversations yet
            </p>
          ) : (
            conversations?.map((conv) => (
              <div key={conv.id} className="group flex items-center rounded-md hover:bg-muted">
                <Link
                  to="/kb/$kbId/chat/$conversationId"
                  params={{ kbId, conversationId: conv.id }}
                  className="flex min-w-0 flex-1 items-center gap-2 p-2 text-sm"
                  activeProps={{ className: 'bg-muted font-medium' }}
                >
                  <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate">{conv.title || 'New conversation'}</span>
                </Link>
                <Button
                  variant="ghost"
                  size="icon"
                  className="mr-1 h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive"
                  onClick={async (e) => {
                    e.stopPropagation()
                    try {
                      await deleteConversation(conv.id)
                      queryClient.invalidateQueries({ queryKey: ['conversations', kbId] })
                      queryClient.removeQueries({ queryKey: ['messages', conv.id] })
                      navigate({ to: '/kb/$kbId', params: { kbId } })
                      toast.success('Conversation deleted')
                    } catch {
                      toast.error('Failed to delete conversation')
                    }
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1">
        <Outlet />
      </div>
    </div>
  )
}
