"use client"

import * as React from "react"
import { Pencil, Plus, RefreshCw, Search, SlidersHorizontal, Trash2 } from "lucide-react"

import { RuleFormModal } from "@/components/dashboard/rule-form"
import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { Modal } from "@/components/ui/modal"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { Pill } from "@/components/ui/pill"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Switch } from "@/components/ui/switch"
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table"
import {
  apiCreateRule,
  apiDeleteRule,
  apiRules,
  apiUpdateRule,
  type CacheRule,
  type CacheRuleInput,
} from "@/lib/api"
import { useAuth } from "@/lib/use-auth"
import { cn, formatRelative, formatSeconds } from "@/lib/utils"

type Toast = { tone: "success" | "destructive"; message: string }

export default function RulesPage() {
  const auth = useAuth()
  const [rules, setRules] = React.useState<CacheRule[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [toast, setToast] = React.useState<Toast | null>(null)
  const [query, setQuery] = React.useState("")
  const [formOpen, setFormOpen] = React.useState(false)
  const [editing, setEditing] = React.useState<CacheRule | null>(null)
  const [deleting, setDeleting] = React.useState<CacheRule | null>(null)
  const [deleteBusy, setDeleteBusy] = React.useState(false)
  const [togglingId, setTogglingId] = React.useState<number | null>(null)

  const loadRules = React.useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setRules(await apiRules())
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load rules")
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    void loadRules()
  }, [loadRules])

  React.useEffect(() => {
    if (!toast) return
    const id = window.setTimeout(() => setToast(null), 4000)
    return () => window.clearTimeout(id)
  }, [toast])

  const visible = React.useMemo(() => {
    const needle = query.trim().toLowerCase()
    const filtered = needle
      ? rules.filter(
          (rule) =>
            rule.endpoint_pattern.toLowerCase().includes(needle) ||
            (rule.description ?? "").toLowerCase().includes(needle),
        )
      : rules
    return [...filtered].sort((a, b) => b.priority - a.priority || a.id - b.id)
  }, [rules, query])

  const enabledCount = rules.filter((rule) => rule.enabled).length
  const averageTtl = rules.length
    ? Math.round(rules.reduce((sum, rule) => sum + rule.ttl, 0) / rules.length)
    : 0
  const keyedRules = rules.filter(
    (rule) => rule.cache_by_user || rule.cache_by_query_params || rule.cache_by_headers,
  ).length

  function openCreate() {
    setEditing(null)
    setFormOpen(true)
  }

  function openEdit(rule: CacheRule) {
    setEditing(rule)
    setFormOpen(true)
  }

  async function handleSubmit(input: CacheRuleInput) {
    if (editing) {
      const updated = await apiUpdateRule(editing.id, input)
      setRules((current) => current.map((rule) => (rule.id === updated.id ? updated : rule)))
      setToast({ tone: "success", message: `Updated ${updated.endpoint_pattern}` })
    } else {
      const created = await apiCreateRule(input)
      setRules((current) => [...current, created])
      setToast({ tone: "success", message: `Created ${created.endpoint_pattern}` })
    }
  }

  async function handleToggle(rule: CacheRule, enabled: boolean) {
    setTogglingId(rule.id)
    try {
      const updated = await apiUpdateRule(rule.id, { enabled })
      setRules((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setToast({
        tone: "destructive",
        message: err instanceof Error ? err.message : "Could not update the rule",
      })
    } finally {
      setTogglingId(null)
    }
  }

  async function handleDelete() {
    if (!deleting) return
    setDeleteBusy(true)
    try {
      await apiDeleteRule(deleting.id)
      setRules((current) => current.filter((rule) => rule.id !== deleting.id))
      setToast({ tone: "success", message: `Deleted ${deleting.endpoint_pattern}` })
      setDeleting(null)
    } catch (err) {
      setToast({
        tone: "destructive",
        message: err instanceof Error ? err.message : "Could not delete the rule",
      })
    } finally {
      setDeleteBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="configuration"
        title="Cache rules"
        description="Rules decide which endpoints are cached in Redis, how cache keys are built, and how long entries live."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={loadRules} disabled={loading} className="gap-2">
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
              Refresh
            </Button>
            {auth.canEdit && (
              <Button variant="primary" size="sm" onClick={openCreate} className="gap-2">
                <Plus className="h-3.5 w-3.5" />
                New rule
              </Button>
            )}
          </>
        }
      />

      {error && (
        <Alert variant="destructive" className="mb-6">
          {error}
        </Alert>
      )}
      {toast && (
        <Alert variant={toast.tone} className="mb-6">
          {toast.message}
        </Alert>
      )}

      <div className="housing housing-row grid sm:grid-cols-3">
        {loading && rules.length === 0 ? (
          Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-[120px]" />)
        ) : (
          <>
            <StatCard
              label="Active rules"
              value={`${enabledCount}/${rules.length}`}
              hint="enabled of total"
              tone="emerald"
              icon={<SlidersHorizontal className="h-4 w-4" />}
            />
            <StatCard
              label="Average TTL"
              value={rules.length ? formatSeconds(averageTtl) : "—"}
              hint="across all rules"
              tone="cyan"
            />
            <StatCard
              label="Keyed rules"
              value={String(keyedRules)}
              hint="vary by user, query, or headers"
              tone="indigo"
            />
          </>
        )}
      </div>

      <Panel
        className="mt-6"
        title="Configured rules"
        description={`${visible.length} shown, sorted by priority`}
        icon={<SlidersHorizontal className="h-4 w-4" />}
        actions={
          <div className="relative w-56">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter patterns"
              className="h-8 pl-8 text-[13px]"
              aria-label="Filter rules"
            />
          </div>
        }
        flush
      >
        {loading && rules.length === 0 ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-11 w-full" />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            compact
            icon={<SlidersHorizontal className="h-5 w-5" />}
            title={rules.length === 0 ? "No cache rules yet" : "No rules match your filter"}
            body={
              rules.length === 0
                ? "Without rules the cache middleware passes every request straight to the upstream."
                : "Try a different pattern or clear the filter."
            }
            action={
              rules.length === 0 && auth.canEdit ? (
                <Button variant="primary" size="sm" onClick={openCreate} className="gap-2">
                  <Plus className="h-3.5 w-3.5" />
                  Create the first rule
                </Button>
              ) : undefined
            }
          />
        ) : (
          <Table minWidth={820}>
            <THead>
              <tr>
                <TH>Endpoint pattern</TH>
                <TH>TTL</TH>
                <TH>Priority</TH>
                <TH>Cache key</TH>
                <TH>Max size</TH>
                <TH>Updated</TH>
                <TH>Enabled</TH>
                {auth.canEdit && <TH align="right">Actions</TH>}
              </tr>
            </THead>
            <TBody>
              {visible.map((rule) => {
                const keyParts = [
                  rule.cache_by_user ? "user" : null,
                  rule.cache_by_query_params ? "query" : null,
                  rule.cache_by_headers ? "headers" : null,
                ].filter((part): part is string => part !== null)

                return (
                  <TR key={rule.id} className={cn(!rule.enabled && "opacity-60")}>
                    <TD>
                      <p className="font-mono text-[13px] text-ink">{rule.endpoint_pattern}</p>
                      {rule.description && (
                        <p className="mt-0.5 max-w-xs truncate text-xs text-faint">{rule.description}</p>
                      )}
                    </TD>
                    <TD mono title={`${rule.ttl} seconds`}>
                      {formatSeconds(rule.ttl)}
                    </TD>
                    <TD mono>{rule.priority}</TD>
                    <TD>
                      {keyParts.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {keyParts.map((part) => (
                            <span
                              key={part}
                              className="rounded border border-rule bg-frost px-1.5 py-0.5 font-mono text-[10px] text-graphite"
                            >
                              {part}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-faint">path only</span>
                      )}
                    </TD>
                    <TD mono>{rule.max_cache_size.toLocaleString()}</TD>
                    <TD className="text-xs text-faint" title={rule.updated_at}>
                      {formatRelative(rule.updated_at)}
                    </TD>
                    <TD>
                      {auth.canEdit ? (
                        <Switch
                          checked={rule.enabled}
                          disabled={togglingId === rule.id}
                          onCheckedChange={(checked) => handleToggle(rule, checked)}
                          label={`${rule.enabled ? "Disable" : "Enable"} ${rule.endpoint_pattern}`}
                        />
                      ) : (
                        <Pill tone={rule.enabled ? "emerald" : "zinc"}>
                          {rule.enabled ? "enabled" : "paused"}
                        </Pill>
                      )}
                    </TD>
                    {auth.canEdit && (
                      <TD align="right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="subtle"
                            size="sm"
                            className="gap-1.5 text-ink"
                            onClick={() => openEdit(rule)}
                          >
                            <Pencil className="h-3 w-3" />
                            Edit
                          </Button>
                          {auth.isAdmin && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="gap-1.5 text-signal hover:bg-signal/10 hover:text-signal"
                              onClick={() => setDeleting(rule)}
                            >
                              <Trash2 className="h-3 w-3" />
                              Delete
                            </Button>
                          )}
                        </div>
                      </TD>
                    )}
                  </TR>
                )
              })}
            </TBody>
          </Table>
        )}
      </Panel>

      {auth.ready && !auth.canEdit && (
        <p className="mt-4 text-xs text-faint">
          You have view-only access. The operator role can create and edit rules; only admins can delete them.
        </p>
      )}

      <RuleFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        rule={editing}
        onSubmit={handleSubmit}
      />

      <Modal
        open={deleting !== null}
        onClose={() => (deleteBusy ? undefined : setDeleting(null))}
        title="Delete cache rule?"
        description="Cached entries already in Redis expire on their own; new requests stop being cached immediately."
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setDeleting(null)} disabled={deleteBusy}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleDelete}
              disabled={deleteBusy}
              className="gap-2 bg-none bg-signal shadow-none hover:bg-signal"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {deleteBusy ? "Deleting…" : "Delete rule"}
            </Button>
          </>
        }
      >
        {deleting && (
          <p className="rounded border border-rule bg-frost p-3 font-mono text-[13px] text-ink">
            {deleting.endpoint_pattern}
          </p>
        )}
      </Modal>
    </>
  )
}
