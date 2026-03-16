import { createFileRoute, Link } from '@tanstack/react-router'
import { useKBs } from '@/lib/hooks'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plus, Database } from 'lucide-react'

export const Route = createFileRoute('/_app/')({
  component: LandingPage,
})

function LandingPage() {
  const { data: kbs, isLoading } = useKBs()

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold">Knowledge Bases</h2>
        <Link to="/kb/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Knowledge Base
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : kbs?.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Database className="mb-4 h-12 w-12 text-muted-foreground" />
          <h3 className="text-lg font-medium">No knowledge bases yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Create one to start uploading documents and chatting.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {kbs?.map((kb) => (
            <Link key={kb.id} to="/kb/$kbId" params={{ kbId: kb.id }}>
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <CardHeader>
                  <CardTitle>{kb.name}</CardTitle>
                  <CardDescription>
                    {kb.description || 'No description'}
                    <span className="mt-1 block text-xs">
                      {kb.document_count} document{kb.document_count !== 1 ? 's' : ''}
                    </span>
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
