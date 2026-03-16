import type { SSEEvent } from './types'

export async function* parseSSE(response: Response): AsyncGenerator<SSEEvent> {
  if (!response.body) throw new Error('Response body is null')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  function* processLines(lines: string[]) {
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data: ')) continue

      const json = trimmed.slice(6)
      if (!json) continue

      try {
        yield JSON.parse(json) as SSEEvent
      } catch {
        // skip malformed lines
      }
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()!

    yield* processLines(lines)
  }

  // Flush remaining buffer
  if (buffer.trim()) {
    yield* processLines([buffer])
  }
}
