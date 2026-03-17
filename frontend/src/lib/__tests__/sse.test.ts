import { describe, it, expect } from 'vitest'
import { parseSSE } from '../sse'
import type { SSEEvent } from '../types'

function makeResponse(body: string): Response {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(body))
      controller.close()
    },
  })
  return new Response(stream)
}

async function collectEvents(response: Response): Promise<SSEEvent[]> {
  const events: SSEEvent[] = []
  for await (const event of parseSSE(response)) {
    events.push(event)
  }
  return events
}

describe('parseSSE', () => {
  it('parses a single SSE data line', async () => {
    const response = makeResponse('data: {"event":"thinking","node":"router","data":"test"}\n\n')
    const events = await collectEvents(response)
    expect(events).toHaveLength(1)
    expect(events[0].event).toBe('thinking')
    expect(events[0].node).toBe('router')
  })

  it('parses multiple events', async () => {
    const body = [
      'data: {"event":"thinking","node":"router","data":"step1"}',
      '',
      'data: {"event":"answer","data":"The answer"}',
      '',
      'data: {"event":"done"}',
      '',
    ].join('\n')
    const response = makeResponse(body)
    const events = await collectEvents(response)
    expect(events).toHaveLength(3)
    expect(events[0].event).toBe('thinking')
    expect(events[1].event).toBe('answer')
    expect(events[2].event).toBe('done')
  })

  it('skips malformed JSON lines', async () => {
    const body = [
      'data: {"event":"thinking","data":"ok"}',
      'data: not-valid-json',
      'data: {"event":"done"}',
      '',
    ].join('\n')
    const response = makeResponse(body)
    const events = await collectEvents(response)
    expect(events).toHaveLength(2)
    expect(events[0].event).toBe('thinking')
    expect(events[1].event).toBe('done')
  })

  it('throws error on null body', async () => {
    const response = new Response(null)
    // Override body to be null
    Object.defineProperty(response, 'body', { value: null })
    await expect(async () => {
      const events: SSEEvent[] = []
      for await (const event of parseSSE(response)) {
        events.push(event)
      }
    }).rejects.toThrow('Response body is null')
  })
})
