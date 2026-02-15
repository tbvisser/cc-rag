import { useState } from 'react'
import { ChevronDown, ChevronRight, Search, Database, Globe, FileSearch, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import type { ToolStep } from '@/hooks/useChat'

const TOOL_META: Record<string, { label: string; icon: typeof Search }> = {
  retrieve_documents: { label: 'Document Search', icon: Search },
  text_to_sql: { label: 'SQL Query', icon: Database },
  web_search: { label: 'Web Search', icon: Globe },
  analyze_document: { label: 'Document Analysis', icon: FileSearch },
}

interface ToolCallCardProps {
  steps: ToolStep[]
}

export function ToolCallCards({ steps }: ToolCallCardProps) {
  // Pair tool_call + tool_result by matching sequential events
  const pairs: { call: ToolStep; result?: ToolStep }[] = []
  for (const step of steps) {
    if (step.type === 'call') {
      pairs.push({ call: step })
    } else if (step.type === 'result' && pairs.length > 0) {
      // Attach result to the last call with the same name that has no result
      const match = [...pairs].reverse().find((p) => p.call.name === step.name && !p.result)
      if (match) {
        match.result = step
      }
    }
  }

  if (pairs.length === 0) return null

  return (
    <div className="flex flex-col gap-2 pl-11">
      {pairs.map((pair, i) => (
        <SingleToolCard key={i} call={pair.call} result={pair.result} />
      ))}
    </div>
  )
}

function SingleToolCard({ call, result }: { call: ToolStep; result?: ToolStep }) {
  const [expanded, setExpanded] = useState(false)
  const meta = TOOL_META[call.name] || { label: call.name, icon: Search }
  const Icon = meta.icon
  const isPending = !result
  const isAnalyzeDocument = call.name === 'analyze_document'
  const hasSubAgent = isAnalyzeDocument && (call.subSteps?.length || call.subContent)

  return (
    <div className="rounded-lg border bg-muted/50 text-sm">
      <button
        onClick={() => setExpanded((p) => !p)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/80 rounded-lg"
      >
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        )}
        <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span className="font-medium">{meta.label}</span>
        {isAnalyzeDocument && call.arguments?.filename != null && (
          <span className="truncate text-muted-foreground">
            {String(call.arguments.filename)}
          </span>
        )}
        {!isAnalyzeDocument && call.arguments && (
          <span className="truncate text-muted-foreground">
            {String(Object.values(call.arguments)[0])}
          </span>
        )}
        {isPending && <Loader2 className="ml-auto h-3.5 w-3.5 animate-spin text-muted-foreground" />}
      </button>

      {/* Sub-agent section — always visible when present */}
      {hasSubAgent && (
        <div className="border-t px-3 py-2 space-y-2">
          <span className="text-xs font-medium text-muted-foreground">Sub-agent</span>
          {call.subSteps && call.subSteps.length > 0 && (
            <div className="border-l-2 border-muted-foreground/20 pl-3">
              <ToolCallCards steps={call.subSteps} />
            </div>
          )}
          {call.subContent && (
            <div className="text-xs text-muted-foreground prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{call.subContent}</ReactMarkdown>
            </div>
          )}
        </div>
      )}

      {expanded && (
        <div className="border-t px-3 py-2 space-y-2">
          {call.arguments && (
            <div>
              <span className="text-xs font-medium text-muted-foreground">Arguments</span>
              <pre className="mt-1 text-xs bg-background rounded p-2 overflow-x-auto">
                {JSON.stringify(call.arguments, null, 2)}
              </pre>
            </div>
          )}
          {result?.result && (
            <div>
              <span className="text-xs font-medium text-muted-foreground">Result</span>
              <pre className="mt-1 text-xs bg-background rounded p-2 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
                {result.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
