import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { createKB } from '@/lib/api'
import { queryClient } from '@/lib/queryClient'
import { toast } from 'sonner'

export const Route = createFileRoute('/_app/kb/new')({
  component: NewKBPage,
})

function NewKBPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const kb = await createKB(name, description || undefined)
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] })
      toast.success('Knowledge base created')
      navigate({ to: '/kb/$kbId', params: { kbId: kb.id } })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-start justify-center p-8">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>New Knowledge Base</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Q3 2024 Contracts"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Input
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What documents will this contain?"
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={loading}>
                {loading ? 'Creating...' : 'Create'}
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate({ to: '/' })}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
