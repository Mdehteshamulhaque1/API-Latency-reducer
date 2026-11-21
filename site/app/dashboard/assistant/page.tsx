"use client"

import * as React from "react"
import { Bot, Bug, ChevronDown, ChevronRight, Loader2, Send, Sparkles, Stethoscope } from "lucide-react"

import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { Pill } from "@/components/ui/pill"
import { RANGE_OPTIONS, Segmented } from "@/components/ui/segmented"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import {
  apiAssistantAsk,
  apiAssistantSuggestions,
  apiTroubleshoot,
  type AssistantAnswer,
  type SourceChunk,
  type TroubleshootReport,
} from "@/lib/api"
import { cn, formatMs, formatPercent } from "@/lib/utils"
import { useMonitoredService } from "@/lib/use-service"

function FactsBlock({ facts }: { facts: Record<string, Record<string, unknown>> }) {
  const [open, setOpen] = React.useState<string | null>(null)
  const entries = Object.entries(facts)
  if (entries.length === 0) return null
  return (
    <div className="space-y-1.5">
      {entries.map(([name, data], index) => {
        const expanded = open === name
        return (
          <div key={name} className="rounded border border-rule bg-frost">
            <button
              type="button"
              onClick={() => setOpen(expanded ? null : name)}
              className="flex w-full items-center justify-between px-3 py-2 text-left text-xs text-ink"
            >
              <span className="flex items-center gap-2 font-mono">
                <span className="text-steel">[F{index + 1}]</span>
                {name.replace(/_/g, " ")}
              </span>
              {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            </button>
            {expanded && (
              <pre className="max-h-64 overflow-auto border-t border-rule p-3 font-mono text-[11px] leading-relaxed text-graphite">
                {JSON.stringify(data, null, 2)}
              </pre>
            )}
          </div>
        )
      })}
    </div>
  )
}

function Sources({ sources, prefix }: { sources: SourceChunk[]; prefix: string }) {
  if (sources.length === 0) return null
  return (
    <ul className="space-y-1.5">
      {sources.map((source, index) => (
        <li key={`${source.document_id}-${source.position}`} className="rounded border border-rule bg-frost p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="font-mono text-[11px] text-ink">
              <span className="text-steel">[{prefix}{index + 1}]</span> {source.filename}, chunk {source.position}
            </p>
            <div className="flex items-center gap-1.5">
              {source.flagged && <Pill tone="indigo">flagged</Pill>}
              <Pill tone="zinc">{formatPercent(source.similarity * 100, 0)} match</Pill>
            </div>
          </div>
          <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-graphite">{source.text}</p>
        </li>
      ))}
    </ul>
  )
}

function AnswerMeta({ model, cached, latency, cost, grounding }: { model: string | null; cached: boolean; latency: number; cost: number; grounding: number }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {model && <Pill tone="zinc">{model}</Pill>}
      <Pill tone={cached ? "emerald" : "indigo"}>{cached ? "cache hit" : "generated"}</Pill>
      <Pill tone="cyan">{formatMs(latency)}</Pill>
      {cost > 0 && <Pill tone="zinc">~${cost.toFixed(5)} est.</Pill>}
      <Pill tone={grounding >= 0.5 ? "emerald" : grounding >= 0.3 ? "amber" : "red"} title="Share of answer sentences supported by facts and sources">
        grounding {formatPercent(grounding * 100, 0)}
      </Pill>
    </div>
  )
}

export default function AssistantPage() {
  const [hours, setHours] = React.useState(24)
  const monitored = useMonitoredService()
  const service = monitored.service ?? undefined
  const [includeDocs, setIncludeDocs] = React.useState(true)
  const [question, setQuestion] = React.useState("")
  const [suggestions, setSuggestions] = React.useState<string[]>([])
  const [history, setHistory] = React.useState<AssistantAnswer[]>([])
  const [asking, setAsking] = React.useState(false)
  const [askError, setAskError] = React.useState<string | null>(null)

  const [status, setStatus] = React.useState("")
  const [endpoint, setEndpoint] = React.useState("")
  const [symptom, setSymptom] = React.useState("")
  const [report, setReport] = React.useState<TroubleshootReport | null>(null)
  const [diagnosing, setDiagnosing] = React.useState(false)
  const [diagError, setDiagError] = React.useState<string | null>(null)

  React.useEffect(() => {
    apiAssistantSuggestions()
      .then((data) => setSuggestions(data.questions))
      .catch(() => setSuggestions([]))
  }, [])

  async function ask(text: string) {
    const trimmed = text.trim()
    if (!trimmed || asking) return
    setAsking(true)
    setAskError(null)
    try {
      const answer = await apiAssistantAsk(trimmed, hours, includeDocs, { service })
      setHistory((current) => [answer, ...current])
      setQuestion("")
    } catch (err) {
      setAskError(err instanceof Error ? err.message : "The assistant request failed")
    } finally {
      setAsking(false)
    }
  }

  async function diagnose(event: React.FormEvent) {
    event.preventDefault()
    if (diagnosing) return
    const code = status.trim() ? Number.parseInt(status, 10) : undefined
    if (code !== undefined && (!Number.isInteger(code) || code < 400 || code > 599)) {
      setDiagError("Status code must be between 400 and 599")
      return
    }
    setDiagnosing(true)
    setDiagError(null)
    try {
      setReport(
        await apiTroubleshoot({
          status_code: code,
          endpoint: endpoint.trim() || undefined,
          symptom: symptom.trim() || undefined,
          hours,
          service,
        }),
      )
    } catch (err) {
      setDiagError(err instanceof Error ? err.message : "Troubleshooting failed")
    } finally {
      setDiagnosing(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="ai assistant"
        title={monitored.monitoring ? `${monitored.label} performance assistant` : "Performance assistant"}
        description={
          monitored.monitoring
            ? `Ask questions about ${monitored.label}'s measured traffic. Answers are built from numbered facts collected from its request log; the facts are always shown next to the narrative.`
            : "Ask questions about your measured traffic. Answers are built from numbered facts the backend collected; the facts are always shown next to the narrative."
        }
        actions={
          <>
            <Segmented value={hours} onChange={setHours} options={RANGE_OPTIONS} ariaLabel="Analysis window" />
            <label className="flex items-center gap-2 text-xs text-graphite">
              <Switch checked={includeDocs} onCheckedChange={setIncludeDocs} label="Search documentation" />
              docs
            </label>
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-4">
          <Panel title="Ask" description="One question at a time, answered from measured data" icon={<Bot className="h-4 w-4" />}>
            {askError && (
              <Alert variant="destructive" className="mb-3">
                {askError}
              </Alert>
            )}
            <form
              onSubmit={(event) => {
                event.preventDefault()
                void ask(question)
              }}
              className="space-y-3"
            >
              <Textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={3}
                maxLength={2000}
                placeholder="Which endpoint has the highest p95 latency?"
                disabled={asking}
              />
              <div className="flex items-center justify-between gap-3">
                <p className="text-[11px] text-faint">Guardrails screen every question before it reaches the model.</p>
                <Button type="submit" variant="primary" size="sm" disabled={asking || question.trim().length < 3} className="gap-2">
                  {asking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                  Ask
                </Button>
              </div>
            </form>
            {suggestions.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1.5">
                {suggestions.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => void ask(item)}
                    disabled={asking}
                    className="rounded-full border border-rule bg-frost px-2.5 py-1 text-[11px] text-ink transition-colors hover:border-rule-strong hover:text-ink disabled:opacity-50"
                  >
                    {item}
                  </button>
                ))}
              </div>
            )}
          </Panel>

          {history.length === 0 && !asking ? (
            <EmptyState
              icon={<Sparkles className="h-5 w-5" />}
              title="No questions yet"
              body="Pick a suggested question or ask your own. Every answer lists the facts it was built from."
            />
          ) : (
            history.map((item, index) => (
              <Panel
                key={`${item.question}-${index}`}
                title={item.question}
                description={`tools: ${item.tools_used.map((t) => t.replace(/_/g, " ")).join(", ")}`}
              >
                {item.guardrail_notes.length > 0 && (
                  <Alert variant="default" className="mb-3">
                    {item.guardrail_notes.join(" ")}
                  </Alert>
                )}
                {item.llm_available && item.answer ? (
                  <>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">{item.answer}</p>
                    <div className="mt-3">
                      <AnswerMeta model={item.model} cached={item.cached} latency={item.latency_ms} cost={item.estimated_cost_usd} grounding={item.grounding_score} />
                    </div>
                  </>
                ) : (
                  <Alert variant="default">{item.llm_error ?? "The model did not return an answer."} The measured facts below are still accurate.</Alert>
                )}
                <p className="mono-label mb-2 mt-4">measured facts</p>
                <FactsBlock facts={item.facts} />
                {item.sources.length > 0 && (
                  <>
                    <p className="mono-label mb-2 mt-4">documentation</p>
                    <Sources sources={item.sources} prefix="D" />
                  </>
                )}
              </Panel>
            ))
          )}
        </div>

        <div className="space-y-4">
          <Panel title="Troubleshoot" description="Evidence first, hypotheses second" icon={<Stethoscope className="h-4 w-4" />}>
            {diagError && (
              <Alert variant="destructive" className="mb-3">
                {diagError}
              </Alert>
            )}
            <form onSubmit={diagnose} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="ts-status">Status code</Label>
                  <Input id="ts-status" inputMode="numeric" placeholder="429" value={status} onChange={(event) => setStatus(event.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="ts-endpoint">Endpoint contains</Label>
                  <Input id="ts-endpoint" placeholder="/api/v1/chat" value={endpoint} onChange={(event) => setEndpoint(event.target.value)} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ts-symptom">Symptom</Label>
                <Input id="ts-symptom" placeholder="high latency, cache misses, redis errors…" value={symptom} onChange={(event) => setSymptom(event.target.value)} maxLength={500} />
              </div>
              <Button type="submit" variant="outline" size="sm" disabled={diagnosing} className="gap-2">
                {diagnosing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Bug className="h-3.5 w-3.5" />}
                Diagnose
              </Button>
            </form>
          </Panel>

          {report && (
            <Panel
              title="Diagnosis"
              description={[
                report.status_code ? `status ${report.status_code}` : null,
                report.endpoint ? `endpoint ~ ${report.endpoint}` : null,
                report.symptom ? `symptom: ${report.symptom}` : null,
              ]
                .filter(Boolean)
                .join(", ") || "general"}
            >
              {report.llm_available && report.explanation ? (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">{report.explanation}</p>
              ) : (
                <Alert variant="default">The model is unavailable; the evidence and known causes below are still accurate.</Alert>
              )}
              <p className="mono-label mb-2 mt-4">evidence</p>
              <FactsBlock facts={report.evidence} />
              {report.known_causes.length > 0 && (
                <>
                  <p className="mono-label mb-2 mt-4">known causes in this codebase</p>
                  <ol className="space-y-2">
                    {report.known_causes.map((cause, index) => (
                      <li key={index} className={cn("rounded border border-rule bg-frost p-3 text-xs")}>
                        <p className="text-ink">
                          <span className="font-mono text-steel">[K{index + 1}]</span> {cause.cause}
                        </p>
                        <p className="mt-1 text-graphite">Check: {cause.check}</p>
                      </li>
                    ))}
                  </ol>
                </>
              )}
              {report.sources.length > 0 && (
                <>
                  <p className="mono-label mb-2 mt-4">documentation</p>
                  <Sources sources={report.sources} prefix="D" />
                </>
              )}
            </Panel>
          )}
        </div>
      </div>
    </>
  )
}
