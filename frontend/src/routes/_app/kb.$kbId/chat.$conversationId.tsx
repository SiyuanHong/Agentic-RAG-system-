import { createFileRoute } from '@tanstack/react-router'
import { ChatWindow } from '@/components/chat/ChatWindow'

export const Route = createFileRoute('/_app/kb/$kbId/chat/$conversationId')({
  component: ChatPage,
})

function ChatPage() {
  const { kbId, conversationId } = Route.useParams()
  return <ChatWindow kbId={kbId} conversationId={conversationId} />
}
