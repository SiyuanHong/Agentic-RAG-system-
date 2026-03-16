import { useState, useMemo, useCallback } from 'react'
import Markdown, { type Components } from 'react-markdown'
import { ChevronDown, ChevronRight, FileText } from 'lucide-react'
import { getToken } from '@/lib/auth'
import type { MessageResponse, SourceInfo } from '@/lib/types'

interface MessageBubbleProps {
  message: MessageResponse
  kbId: string
}

/**
 * Fetch a document file with JWT auth, then open it in a new tab.
 * For PDFs, appends #page=X to navigate to the right page.
 */
async function openDocFile(kbId: string, documentId: string, page?: number, filename?: string) {
  const url = `/api/knowledge-bases/${kbId}/documents/${documentId}/file`
  const token = getToken()
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    console.error('Failed to fetch document file:', res.status)
    return
  }
  const blob = await res.blob()
  let blobUrl = URL.createObjectURL(blob)
  // Only add #page= for PDFs
  if (page && filename?.toLowerCase().endsWith('.pdf')) {
    blobUrl += `#page=${page}`
  }
  window.open(blobUrl, '_blank')
}

export function MessageBubble({ message, kbId }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  // Build a lookup from filename -> source info
  const sourcesByFilename = useMemo(() => {
    const map = new Map<string, SourceInfo>()
    if (message.sources) {
      for (const s of message.sources) {
        if (s.filename) {
          map.set(s.filename, s as SourceInfo)
        }
      }
    }
    return map
  }, [message.sources])

  // Custom markdown components to make citation links clickable
  const markdownComponents = useMemo<Components>(() => ({
    // Override paragraph to post-process citation patterns
    p: ({ children, ...props }) => {
      const processed = processChildren(children, kbId, sourcesByFilename)
      return <p {...props}>{processed}</p>
    },
    li: ({ children, ...props }) => {
      const processed = processChildren(children, kbId, sourcesByFilename)
      return <li {...props}>{processed}</li>
    },
  }), [kbId, sourcesByFilename])

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <Markdown components={markdownComponents}>{message.content}</Markdown>
          </div>
        )}
        {message.sources && message.sources.length > 0 && (
          <Sources sources={message.sources as SourceInfo[]} kbId={kbId} />
        )}
      </div>
    </div>
  )
}

/**
 * Process React children to find citation patterns like [filename, p.X]
 * and replace them with clickable buttons that fetch with auth.
 */
function processChildren(
  children: React.ReactNode,
  kbId: string,
  sourcesByFilename: Map<string, SourceInfo>,
): React.ReactNode {
  if (!children) return children

  const childArray = Array.isArray(children) ? children : [children]
  return childArray.map((child, idx) => {
    if (typeof child !== 'string') return child

    // Match patterns: [filename, p.X] or [filename, p.X, p.Y] or [filename]
    const citationRegex = /\[([^[\]]+?\.\w+)(?:,\s*(p\.\d+(?:,\s*p\.\d+)*))?]/g
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = citationRegex.exec(child)) !== null) {
      // Add text before the match
      if (match.index > lastIndex) {
        parts.push(child.slice(lastIndex, match.index))
      }

      const filename = match[1]
      const pageStr = match[2] // e.g. "p.5" or "p.5, p.6"
      const source = sourcesByFilename.get(filename)

      if (source && source.document_id) {
        // Extract first page number for the link
        const pageMatch = pageStr?.match(/p\.(\d+)/)
        const page = pageMatch ? parseInt(pageMatch[1], 10) : undefined
        const docId = source.document_id

        parts.push(
          <CitationButton
            key={`${idx}-${match.index}`}
            kbId={kbId}
            documentId={docId}
            page={page}
            filename={filename}
            label={match[0]}
          />
        )
      } else {
        // No source mapping — render as plain text
        parts.push(match[0])
      }

      lastIndex = match.index + match[0].length
    }

    // Add remaining text
    if (lastIndex < child.length) {
      parts.push(child.slice(lastIndex))
    }

    return parts.length === 1 ? parts[0] : parts
  })
}

function CitationButton({
  kbId,
  documentId,
  page,
  filename,
  label,
}: {
  kbId: string
  documentId: string
  page?: number
  filename: string
  label: string
}) {
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      openDocFile(kbId, documentId, page, filename)
    },
    [kbId, documentId, page, filename],
  )

  return (
    <button
      type="button"
      onClick={handleClick}
      className="inline-flex items-center gap-0.5 rounded bg-primary/10 px-1 py-0.5 text-xs font-medium text-primary hover:bg-primary/20 transition-colors cursor-pointer"
      title={`Open ${filename}${page ? ` at page ${page}` : ''}`}
    >
      <FileText className="h-3 w-3" />
      {label}
    </button>
  )
}

function Sources({ sources, kbId }: { sources: SourceInfo[]; kbId: string }) {
  const [open, setOpen] = useState(false)

  // Deduplicate by document_id
  const uniqueDocs = useMemo(() => {
    const seen = new Map<string, SourceInfo>()
    for (const s of sources) {
      const key = s.document_id || s.chunk_id || ''
      if (!seen.has(key)) {
        seen.set(key, s)
      } else {
        // Merge page numbers
        const existing = seen.get(key)!
        const pages = new Set([...(existing.page_numbers || []), ...(s.page_numbers || [])])
        seen.set(key, { ...existing, page_numbers: [...pages].sort((a, b) => a - b) })
      }
    }
    return [...seen.values()]
  }, [sources])

  return (
    <div className="mt-2 border-t pt-1">
      <button
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        {uniqueDocs.length} source{uniqueDocs.length !== 1 ? 's' : ''}
      </button>
      {open && (
        <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
          {uniqueDocs.map((s, i) => {
            const hasFile = s.document_id && s.filename
            const pages = s.page_numbers?.length ? s.page_numbers : null
            const label = hasFile
              ? `${s.filename}${pages ? ` (p. ${pages.join(', ')})` : ''}`
              : `Chunk ${String(s.chunk_id ?? '').slice(0, 8)}...`

            if (hasFile) {
              return (
                <li key={i}>
                  <button
                    type="button"
                    onClick={() => openDocFile(kbId, s.document_id!, pages?.[0], s.filename)}
                    className="flex items-center gap-1 text-primary hover:underline cursor-pointer"
                  >
                    <FileText className="h-3 w-3" />
                    {label}
                  </button>
                </li>
              )
            }

            return <li key={i}>{label}</li>
          })}
        </ul>
      )}
    </div>
  )
}
