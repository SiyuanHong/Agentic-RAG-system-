import { useState, useRef, useEffect, useCallback } from 'react'
import { useMessages } from '@/lib/hooks'
import { streamChat } from '@/lib/api'
import { parseSSE } from '@/lib/sse'
import { queryClient } from '@/lib/queryClient'
import { MessageBubble } from './MessageBubble'
import { ThinkingStream, type ThinkingStep } from './ThinkingStream'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Send } from 'lucide-react'
import { toast } from 'sonner'
import type { MessageResponse, SourceInfo } from '@/lib/types'

export function ChatWindow({ kbId, conversationId }: { kbId: string; conversationId: string }) {
  const { data: serverMessages } = useMessages(conversationId)
  const [pendingMessages, setPendingMessages] = useState<MessageResponse[]>([])
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [isCacheHit, setIsCacheHit] = useState(false)
  const [input, setInput] = useState('')
  const [currentSources, setCurrentSources] = useState<SourceInfo[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  const messages = [...(serverMessages ?? []), ...pendingMessages]

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages.length, thinkingSteps.length, scrollToBottom])

  async function handleSend(e: React.FormEvent) {
    e.preventDefault()
    const query = input.trim()
    if (!query || isStreaming) return

    setInput('')
    setIsCacheHit(false)
    setThinkingSteps([])
    setCurrentSources([])

    // Optimistically add user message
    const userMsg: MessageResponse = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      sources: null,
    }
    setPendingMessages([userMsg])
    setIsStreaming(true)

    try {
      const response = await streamChat(conversationId, query)
      let finalAnswer = ''

      let streamSources: SourceInfo[] = []
      for await (const event of parseSSE(response)) {
        switch (event.event) {
          case 'thinking':
            if (event.node && event.data) {
              setThinkingSteps((prev) => [
                ...prev,
                { node: event.node!, data: event.data! },
              ])
            }
            break
          case 'sources':
            if (event.data) {
              try {
                streamSources = JSON.parse(event.data) as SourceInfo[]
                setCurrentSources(streamSources)
              } catch { /* ignore */ }
            }
            break
          case 'cache_hit':
            setIsCacheHit(true)
            break
          case 'token':
            if (event.data) finalAnswer = event.data
            break
          case 'answer':
            if (event.data) finalAnswer = event.data
            break
          case 'done':
            break
        }
      }

      // Add assistant message locally
      if (finalAnswer) {
        const assistantMsg: MessageResponse = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: finalAnswer,
          sources: streamSources.length > 0 ? streamSources : null,
        }
        setPendingMessages([userMsg, assistantMsg])
      }

      // Refresh from server
      await queryClient.invalidateQueries({
        queryKey: ['messages', conversationId],
      })
      // Also refresh conversations list (title may have updated)
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      setPendingMessages([])
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Stream failed')
      setPendingMessages([])
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1 p-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {messages.length === 0 && !isStreaming && (
            <div className="flex flex-col items-center justify-center py-20 text-center text-muted-foreground">
              <p className="text-lg font-medium">Start a conversation</p>
              <p className="mt-1 text-sm">Ask a question about your documents</p>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} kbId={kbId} />
          ))}

          {isStreaming && (
            <>
              {isCacheHit && (
                <div className="text-center text-xs text-muted-foreground">
                  Using cached answer
                </div>
              )}
              <ThinkingStream steps={thinkingSteps} isStreaming={isStreaming} />
            </>
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <div className="border-t p-4">
        <form onSubmit={handleSend} className="mx-auto flex max-w-3xl gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            disabled={isStreaming}
            className="flex-1"
          />
          <Button type="submit" size="icon" disabled={isStreaming || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}
