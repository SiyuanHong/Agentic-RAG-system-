import { useQuery } from '@tanstack/react-query'
import {
  fetchKBs,
  fetchKB,
  fetchDocuments,
  fetchConversations,
  fetchMessages,
} from './api'

export function useKBs() {
  return useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: fetchKBs,
  })
}

export function useKB(kbId: string) {
  return useQuery({
    queryKey: ['knowledge-bases', kbId],
    queryFn: () => fetchKB(kbId),
  })
}

export function useDocuments(kbId: string) {
  const query = useQuery({
    queryKey: ['documents', kbId],
    queryFn: () => fetchDocuments(kbId),
    refetchInterval: (query) => {
      const docs = query.state.data
      if (!docs) return false
      const hasActive = docs.some(
        (d) => d.status === 'pending' || d.status === 'processing',
      )
      return hasActive ? 5000 : false
    },
  })
  return query
}

export function useConversations(kbId: string) {
  return useQuery({
    queryKey: ['conversations', kbId],
    queryFn: () => fetchConversations(kbId),
  })
}

export function useMessages(conversationId: string) {
  return useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => fetchMessages(conversationId),
  })
}
