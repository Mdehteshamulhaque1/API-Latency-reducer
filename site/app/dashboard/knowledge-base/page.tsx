"use client"

import * as React from "react"
import { BookOpen, FileText, Loader2, MessageCircleQuestion, RefreshCw, Search, Trash2, Upload } from "lucide-react"

import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { Modal } from "@/components/ui/modal"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { Pill, type PillTone } from "@/components/ui/pill"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import {
  apiDeleteDocument,
  apiDocuments,
  apiKnowledgeAsk,
  apiKnowledgeSearch,
  apiUploadDocument,
  type DocumentItem,
  type DocumentList,
  type KnowledgeAnswer,
  type SourceChunk,
} from "@/lib/api"
import { useAuth, usePolling } from "@/lib/use-auth"
import { cn, formatMs, formatPercent, formatRelative } from "@/lib/utils"

const STATUS_TONE: Record<DocumentItem["status"], PillTone> = {
  ready: "emerald",
  pending: "amber",
  failed: "red",
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${bytes} B`
}

function ChunkList({ chunks }: { chunks: SourceChunk[] }) {
  return (
    <ul className="space-y-2">
      {chunks.map((chunk, index) => (
        <li key={`${chunk.document_id}-${chunk.position}`} className="rounded border border-rule bg-frost p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="font-mono text-[11px] text-ink">
              <span className="text-steel">[{index + 1}]</span> {chunk.filename}, chunk {chunk.position}
            </p>
            <div className="flex items-center gap-1.5">
              {chunk.flagged && <Pill tone="indigo">flagged</Pill>}
              <Pill tone="zinc">{formatPercent(chunk.similarity * 100, 0)} match</Pill>
            </div>
          </div>
          <p className="mt-1.5 whitespace-pre-wrap text-xs leading-relaxed text-graphite">{chunk.text}</p>
        </li>
      ))}
    </ul>
  )
}

export default function KnowledgeBasePage() {
  const auth = useAuth()
  const loader = React.useCallback(() => apiDocuments(), [])
  const { data, loading, error, reload, updatedAt } = usePolling<DocumentList>(loader, null)

  const fileInput = React.useRef<HTMLInputElement | null>(null)
  const [uploading, setUploading] = React.useState(false)
  const [notice, setNotice] = React.useState<{ tone: "success" | "destructive"; text: string } | null>(null)
  const [deleting, setDeleting] = React.useState<DocumentItem | null>(null)
  const [deleteBusy, setDeleteBusy] = React.useState(false)

  const [query, setQuery] = React.useState("")
  const [searching, setSearching] = React.useState(false)
  const [results, setResults] = React.useState<SourceChunk[] | null>(null)
  const [searchError, setSearchError] = React.useState<string | null>(null)

  const [question, setQuestion] = React.useState("")
  const [asking, setAsking] = React.useState(false)
  const [answer, setAnswer] = React.useState<KnowledgeAnswer | null>(null)
  const [askError, setAskError] = React.useState<string | null>(null)

  const documents = React.useMemo(() => data?.items ?? [], [data])
  const readyCount = documents.filter((d) => d.status === "ready").length
  const chunkCount = documents.reduce((sum, d) => sum + d.chunk_count, 0)
  const initial = loading && !data

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setUploading(true)
    setNotice(null)
    try {
      const created = await apiUploadDocument(file)
      setNotice({
        tone: "success",
        text: `${created.filename} indexed into ${created.chunk_count} chunks${created.flagged ? " (instruction-like text was flagged)" : ""}.`,
      })
      await reload()
    } catch (err) {
      setNotice({ tone: "destructive", text: err instanceof Error ? err.message : "Upload failed" })
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ""
    }
  }

  async function handleDelete() {
    if (!deleting) return
    setDeleteBusy(true)
    try {
      await apiDeleteDocument(deleting.id)
      setNotice({ tone: "success", text: `Deleted ${deleting.filename}.` })
      setDeleting(null)
      await reload()
    } catch (err) {
      setNotice({ tone: "destructive", text: err instanceof Error ? err.message : "Delete failed" })
    } finally {
      setDeleteBusy(false)
    }
  }

  async function handleSearch(event: React.FormEvent) {
    event.preventDefault()
    if (query.trim().length < 2 || searching) return
    setSearching(true)
    setSearchError(null)
    try {
      setResults((await apiKnowledgeSearch(query.trim(), 5)).results)
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Search failed")
    } finally {
      setSearching(false)
    }
  }

  async function handleAsk(event: React.FormEvent) {
    event.preventDefault()
    if (question.trim().length < 3 || asking) return
    setAsking(true)
    setAskError(null)
    try {
      setAnswer(await apiKnowledgeAsk(question.trim(), 5))
    } catch (err) {
      setAskError(err instanceof Error ? err.message : "The question failed")
    } finally {
      setAsking(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="knowledge base"
        title="Documentation search"
        description="Upload PDF, text, or Markdown files, search them by meaning, and ask questions answered only from their content."
        actions={
          <>
            {updatedAt && <span className="mono-label hidden sm:inline">updated {formatRelative(updatedAt)}</span>}
            <Button variant="outline" size="sm" onClick={reload} disabled={loading} className="gap-2">
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
              Refresh
            </Button>
            {auth.canEdit && (
              <>
                <input
                  ref={fileInput}
                  type="file"
                  accept=".pdf,.txt,.md,.markdown"
                  className="hidden"
                  onChange={handleUpload}
                />
                <Button variant="primary" size="sm" onClick={() => fileInput.current?.click()} disabled={uploading} className="gap-2">
                  {uploading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
                  {uploading ? "Indexing…" : "Upload"}
                </Button>
              </>
            )}
          </>
        }
      />

      {error && (
        <Alert variant="destructive" className="mb-6">
          {error}
        </Alert>
      )}
      {notice && (
        <Alert variant={notice.tone} className="mb-6">
          {notice.text}
        </Alert>
      )}

      <div className="housing housing-row grid sm:grid-cols-3">
        {initial ? (
          Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-[120px]" />)
        ) : (
          <>
            <StatCard label="Documents" value={`${readyCount}/${documents.length}`} hint="ready of uploaded" tone="indigo" icon={<FileText className="h-4 w-4" />} />
            <StatCard label="Chunks" value={chunkCount.toLocaleString()} hint={data?.vector_entries !== null && data?.vector_entries !== undefined ? `${data.vector_entries.toLocaleString()} vectors stored` : "vector store unavailable"} tone="cyan" icon={<BookOpen className="h-4 w-4" />} />
            <StatCard label="Upload limit" value={`${data?.max_upload_mb ?? 0} MB`} hint={(data?.supported_types ?? []).join(", ")} tone="indigo" icon={<Upload className="h-4 w-4" />} />
          </>
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Panel title="Search" description="Semantic similarity over every chunk" icon={<Search className="h-4 w-4" />}>
          <form onSubmit={handleSearch} className="flex gap-2">
            <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="how do I invalidate the cache" maxLength={1000} />
            <Button type="submit" variant="subtle" size="md" disabled={searching || query.trim().length < 2} className="gap-2">
              {searching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
              Search
            </Button>
          </form>
          {searchError && (
            <Alert variant="destructive" className="mt-3">
              {searchError}
            </Alert>
          )}
          <div className="mt-4">
            {results === null ? (
              <p className="text-xs text-faint">Results show the matching chunk, its file, and a similarity score.</p>
            ) : results.length === 0 ? (
              <EmptyState compact title="No similar passages" body="Try different words, or upload the relevant document." />
            ) : (
              <ChunkList chunks={results} />
            )}
          </div>
        </Panel>

        <Panel title="Ask the documents" description="Answers cite sources or say there is not enough information" icon={<MessageCircleQuestion className="h-4 w-4" />}>
          <form onSubmit={handleAsk} className="space-y-3">
            <Textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={2} maxLength={2000} placeholder="What does the Retry-After header mean?" />
            <div className="flex justify-end">
              <Button type="submit" variant="primary" size="sm" disabled={asking || question.trim().length < 3} className="gap-2">
                {asking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <MessageCircleQuestion className="h-3.5 w-3.5" />}
                Ask
              </Button>
            </div>
          </form>
          {askError && (
            <Alert variant="destructive" className="mt-3">
              {askError}
            </Alert>
          )}
          {answer && (
            <div className="mt-4 space-y-3">
              <div className={cn("rounded border p-3 text-sm leading-relaxed", answer.insufficient_context ? "border-warn/40 bg-warn/10 text-warn" : "border-rule bg-frost text-ink")}>
                <p className="whitespace-pre-wrap">{answer.answer}</p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {answer.model && <Pill tone="zinc">{answer.model}</Pill>}
                {!answer.insufficient_context && (
                  <>
                    <Pill tone={answer.cached ? "emerald" : "indigo"}>{answer.cached ? "cache hit" : "generated"}</Pill>
                    <Pill tone="cyan">{formatMs(answer.latency_ms)}</Pill>
                    <Pill tone={answer.grounding_score >= 0.5 ? "emerald" : "amber"}>grounding {formatPercent(answer.grounding_score * 100, 0)}</Pill>
                    {answer.estimated_cost_usd > 0 && <Pill tone="zinc">~${answer.estimated_cost_usd.toFixed(5)} est.</Pill>}
                  </>
                )}
              </div>
              {answer.sources.length > 0 && <ChunkList chunks={answer.sources} />}
            </div>
          )}
        </Panel>
      </div>

      <Panel className="mt-4" title="Documents" description="Indexed files and their ingestion status" icon={<FileText className="h-4 w-4" />} flush>
        {initial ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : documents.length === 0 ? (
          <EmptyState
            compact
            icon={<Upload className="h-5 w-5" />}
            title="No documents yet"
            body={auth.canEdit ? "Upload a PDF, TXT, or Markdown file to start." : "An operator or admin can upload documents."}
          />
        ) : (
          <Table minWidth={760}>
            <THead>
              <tr>
                <TH>File</TH>
                <TH>Status</TH>
                <TH align="right">Chunks</TH>
                <TH align="right">Size</TH>
                <TH>Model</TH>
                <TH>Uploaded</TH>
                {auth.canEdit && <TH align="right">Actions</TH>}
              </tr>
            </THead>
            <TBody>
              {documents.map((doc) => (
                <TR key={doc.id}>
                  <TD>
                    <p className="font-mono text-[13px] text-ink">{doc.filename}</p>
                    {doc.flagged && (
                      <p className="mt-0.5 text-[11px] text-warn" title={doc.flag_detail ?? ""}>
                        instruction-like text flagged
                      </p>
                    )}
                    {doc.error_message && <p className="mt-0.5 text-[11px] text-signal">{doc.error_message}</p>}
                  </TD>
                  <TD>
                    <Pill tone={STATUS_TONE[doc.status]} dot>
                      {doc.status}
                    </Pill>
                  </TD>
                  <TD mono align="right">{doc.chunk_count}</TD>
                  <TD mono align="right">{formatBytes(doc.size_bytes)}</TD>
                  <TD mono className="text-faint">{doc.embedding_model ?? "—"}</TD>
                  <TD className="text-xs text-faint">{formatRelative(doc.created_at)}</TD>
                  {auth.canEdit && (
                    <TD align="right">
                      <Button variant="ghost" size="sm" className="gap-1.5 text-signal hover:bg-signal/10 hover:text-signal" onClick={() => setDeleting(doc)}>
                        <Trash2 className="h-3 w-3" />
                        Delete
                      </Button>
                    </TD>
                  )}
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Panel>

      <Modal
        open={deleting !== null}
        onClose={() => (deleteBusy ? undefined : setDeleting(null))}
        title="Delete document?"
        description="Its chunks and vectors are removed; answers will no longer cite it."
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setDeleting(null)} disabled={deleteBusy}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleDelete} disabled={deleteBusy} className="gap-2 bg-none bg-signal shadow-none hover:bg-signal">
              <Trash2 className="h-3.5 w-3.5" />
              {deleteBusy ? "Deleting…" : "Delete"}
            </Button>
          </>
        }
      >
        {deleting && <p className="rounded border border-rule bg-frost p-3 font-mono text-[13px] text-ink">{deleting.filename}</p>}
      </Modal>
    </>
  )
}
