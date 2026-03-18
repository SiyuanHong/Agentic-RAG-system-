import createClient from 'openapi-fetch'
import type { paths, components } from './api-schema'
import { getToken, clearToken, isTokenValid } from './auth'

// Re-export schema types for convenience
export type KBResponse = components['schemas']['KBResponse']
export type DocumentResponse = components['schemas']['DocumentResponse']
export type DocumentStatus = components['schemas']['DocumentStatus']
export type ConversationResponse = components['schemas']['ConversationResponse']
export type MessageResponse = components['schemas']['MessageResponse']
export type MessageRole = components['schemas']['MessageRole']
export type AuthResponse = components['schemas']['AuthResponse']

// ─── Skill types (manual — not in OpenAPI schema yet) ──
export interface SkillResponse {
  id: string
  name: string
  filename: string
  created_at: string | null
}

// SSE event type (not in OpenAPI schema — backend streams these)
export interface SSEEvent {
  event: 'thinking' | 'cache_hit' | 'token' | 'answer' | 'sources' | 'done'
  node?: string
  data?: string
}

export type SourceInfo = components['schemas']['SourceInfoResponse']

const client = createClient<paths>({
  baseUrl: '',
})

// Auth middleware: attach JWT + handle 401 + proactive expiry check
client.use({
  async onRequest({ request }) {
    const url = new URL(request.url, window.location.origin)
    const isAuthRoute = url.pathname.startsWith('/auth/')
    if (!isAuthRoute && !isTokenValid()) {
      clearToken()
      window.location.href = '/login'
      throw new Error('Token expired')
    }
    const token = getToken()
    if (token) {
      request.headers.set('Authorization', `Bearer ${token}`)
    }
    return request
  },
  async onResponse({ request, response }) {
    const url = new URL(request.url, window.location.origin)
    const isAuthRoute = url.pathname.startsWith('/auth/')
    if (!isAuthRoute && response.status === 401) {
      clearToken()
      window.location.href = '/login'
    }
    return response
  },
})

// ─── Auth ──────────────────────────────────────────────

function extractErrorMessage(error: unknown, fallback: string): string {
  const err = error as Record<string, unknown> | undefined
  if (err?.detail && typeof err.detail === 'string') return err.detail
  if (err?.detail && Array.isArray(err.detail)) {
    const first = err.detail[0] as Record<string, unknown> | undefined
    if (first?.msg && typeof first.msg === 'string') return first.msg
  }
  return fallback
}

export async function login(email: string, password: string) {
  const { data, error } = await client.POST('/auth/login', {
    body: { email, password },
  })
  if (error) throw new Error(extractErrorMessage(error, 'Login failed'))
  return data
}

export async function register(email: string, password: string) {
  const { data, error } = await client.POST('/auth/register', {
    body: { email, password },
  })
  if (error) throw new Error(extractErrorMessage(error, 'Registration failed'))
  return data
}

// ─── Knowledge Bases ───────────────────────────────────

export async function fetchKBs() {
  const { data, error } = await client.GET('/api/knowledge-bases/')
  if (error) throw new Error('Failed to fetch knowledge bases')
  return data
}

export async function fetchKB(kbId: string) {
  const { data, error } = await client.GET('/api/knowledge-bases/{kb_id}', {
    params: { path: { kb_id: kbId } },
  })
  if (error) throw new Error('Failed to fetch knowledge base')
  return data
}

export async function createKB(name: string, description?: string) {
  const { data, error } = await client.POST('/api/knowledge-bases/', {
    body: { name, description },
  })
  if (error) throw new Error('Failed to create knowledge base')
  return data
}

export async function deleteKB(kbId: string) {
  const { error } = await client.DELETE('/api/knowledge-bases/{kb_id}', {
    params: { path: { kb_id: kbId } },
  })
  if (error) throw new Error('Failed to delete knowledge base')
}

// ─── Documents ─────────────────────────────────────────

export async function fetchDocuments(kbId: string) {
  const { data, error } = await client.GET('/api/knowledge-bases/{kb_id}/documents/', {
    params: { path: { kb_id: kbId } },
  })
  if (error) throw new Error('Failed to fetch documents')
  return data
}

export async function uploadDocument(kbId: string, file: File) {
  // openapi-fetch handles multipart via bodySerializer for FormData
  const { data, error } = await client.POST('/api/knowledge-bases/{kb_id}/documents/', {
    params: { path: { kb_id: kbId } },
    body: { file } as never,
    bodySerializer: (body: Record<string, unknown>) => {
      const fd = new FormData()
      fd.append('file', body.file as File)
      return fd
    },
  })
  if (error) throw new Error('Failed to upload document')
  return data
}

export async function deleteDocument(kbId: string, docId: string) {
  const token = getToken()
  const res = await fetch(`/api/knowledge-bases/${kbId}/documents/${docId}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!res.ok) throw new Error('Failed to delete document')
}

// ─── Skills ───────────────────────────────────────────

export async function fetchSkills(): Promise<SkillResponse[]> {
  const token = getToken()
  const res = await fetch('/api/skills/', {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!res.ok) throw new Error('Failed to fetch skills')
  return res.json()
}

export async function uploadSkill(file: File): Promise<SkillResponse> {
  const token = getToken()
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch('/api/skills/', {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: fd,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(body.detail || 'Failed to upload skill')
  }
  return res.json()
}

export async function deleteSkill(skillId: string): Promise<void> {
  const token = getToken()
  const res = await fetch(`/api/skills/${skillId}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!res.ok) throw new Error('Failed to delete skill')
}

// ─── Conversations ─────────────────────────────────────

export async function fetchConversations(kbId: string) {
  const { data, error } = await client.GET('/api/chat/conversations', {
    params: { query: { kb_id: kbId } },
  })
  if (error) throw new Error('Failed to fetch conversations')
  return data
}

export async function createConversation(kbId: string) {
  const { data, error } = await client.POST('/api/chat/conversations', {
    body: { kb_id: kbId },
  })
  if (error) throw new Error('Failed to create conversation')
  return data
}

export async function deleteConversation(conversationId: string) {
  const token = getToken()
  const res = await fetch(`/api/chat/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!res.ok) throw new Error('Failed to delete conversation')
}

// ─── Messages ──────────────────────────────────────────

export async function fetchMessages(conversationId: string) {
  const { data, error } = await client.GET('/api/chat/conversations/{conversation_id}/messages', {
    params: { path: { conversation_id: conversationId } },
  })
  if (error) throw new Error('Failed to fetch messages')
  return data
}

// ─── Chat Stream (SSE — raw fetch, not openapi-fetch) ──

export async function streamChat(conversationId: string, query: string, skillId?: string | null): Promise<Response> {
  const token = getToken()
  const body: Record<string, unknown> = { query }
  if (skillId) body.skill_id = skillId

  const res = await fetch(`/api/chat/conversations/${conversationId}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })

  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail || res.statusText)
  }

  return res
}
