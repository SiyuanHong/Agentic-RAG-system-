import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

export interface ThinkingStep {
  node: string
  data: string
}

const NODE_LABELS: Record<string, string> = {
  router: 'Classifying query',
  retrieve: 'Searching documents',
  answerer: 'Generating answer',
  checker: 'Verifying answer',
}

export function ThinkingStream({
  steps,
  isStreaming,
}: {
  steps: ThinkingStep[]
  isStreaming: boolean
}) {
  const [expanded, setExpanded] = useState(true)

  if (steps.length === 0) return null

  return (
    <div className="mb-2 rounded-md border bg-muted/50 text-sm">
      <button
        className="flex w-full items-center gap-1 px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        Agent Steps
        {isStreaming && (
          <span className="ml-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
        )}
      </button>

      {expanded && (
        <div className="space-y-1 px-3 pb-2">
          {steps.map((step, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary/40" />
              <span className="font-medium">{NODE_LABELS[step.node] ?? step.node}</span>
              <StepDetail step={step} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function parseStepData(data: string): Record<string, unknown> | null {
  try {
    return JSON.parse(data) as Record<string, unknown>
  } catch {
    return null
  }
}

function StepDetail({ step }: { step: ThinkingStep }) {
  const parsed = parseStepData(step.data)
  if (!parsed) return null

  if (step.node === 'retrieve' && Array.isArray(parsed.retrieved_chunks)) {
    return (
      <span className="text-muted-foreground">
        — found {parsed.retrieved_chunks.length} chunks
      </span>
    )
  }
  if (step.node === 'checker' && parsed.checker_result) {
    return (
      <span className="text-muted-foreground">
        — {String(parsed.checker_result)}
        {parsed.iteration_count ? ` (iter ${String(parsed.iteration_count)})` : ''}
      </span>
    )
  }
  return null
}
