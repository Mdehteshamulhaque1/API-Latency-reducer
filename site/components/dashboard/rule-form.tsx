"use client"

import * as React from "react"
import { Loader2 } from "lucide-react"

import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Modal } from "@/components/ui/modal"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import type { CacheRule, CacheRuleInput } from "@/lib/api"
import { cn, formatSeconds } from "@/lib/utils"

// Mirrors app/schemas/rules.py constraints.
const PATTERN_MAX = 255
const MIN_CACHE_SIZE = 100

const TTL_PRESETS = [
  { label: "30s", value: 30 },
  { label: "5m", value: 300 },
  { label: "1h", value: 3600 },
  { label: "24h", value: 86400 },
]

interface FormState {
  endpoint_pattern: string
  description: string
  ttl: string
  priority: string
  max_cache_size: string
  enabled: boolean
  cache_by_user: boolean
  cache_by_query_params: boolean
  cache_by_headers: boolean
}

const DEFAULTS: FormState = {
  endpoint_pattern: "",
  description: "",
  ttl: "3600",
  priority: "0",
  max_cache_size: "1000",
  enabled: true,
  cache_by_user: false,
  cache_by_query_params: false,
  cache_by_headers: false,
}

function fromRule(rule: CacheRule): FormState {
  return {
    endpoint_pattern: rule.endpoint_pattern,
    description: rule.description ?? "",
    ttl: String(rule.ttl),
    priority: String(rule.priority),
    max_cache_size: String(rule.max_cache_size),
    enabled: rule.enabled,
    cache_by_user: rule.cache_by_user,
    cache_by_query_params: rule.cache_by_query_params,
    cache_by_headers: rule.cache_by_headers,
  }
}

function toInt(value: string): number | null {
  if (!/^\d+$/.test(value.trim())) return null
  return Number.parseInt(value, 10)
}

function validate(state: FormState): Partial<Record<keyof FormState, string>> {
  const errors: Partial<Record<keyof FormState, string>> = {}
  const pattern = state.endpoint_pattern.trim()
  if (pattern.length === 0) errors.endpoint_pattern = "Required"
  else if (pattern.length > PATTERN_MAX) errors.endpoint_pattern = `Max ${PATTERN_MAX} characters`

  const ttl = toInt(state.ttl)
  if (ttl === null || ttl < 0) errors.ttl = "Whole number of seconds, 0 or more"

  const priority = toInt(state.priority)
  if (priority === null || priority < 0) errors.priority = "Whole number, 0 or more"

  const size = toInt(state.max_cache_size)
  if (size === null || size < MIN_CACHE_SIZE) errors.max_cache_size = `At least ${MIN_CACHE_SIZE}`

  return errors
}

function toInput(state: FormState): CacheRuleInput {
  return {
    endpoint_pattern: state.endpoint_pattern.trim(),
    description: state.description.trim() ? state.description.trim() : null,
    ttl: toInt(state.ttl) ?? 0,
    priority: toInt(state.priority) ?? 0,
    max_cache_size: toInt(state.max_cache_size) ?? MIN_CACHE_SIZE,
    enabled: state.enabled,
    cache_by_user: state.cache_by_user,
    cache_by_query_params: state.cache_by_query_params,
    cache_by_headers: state.cache_by_headers,
  }
}

interface RuleFormModalProps {
  open: boolean
  onClose: () => void
  /** Editing when provided, creating otherwise. */
  rule: CacheRule | null
  onSubmit: (input: CacheRuleInput) => Promise<void>
}

export function RuleFormModal({ open, onClose, rule, onSubmit }: RuleFormModalProps) {
  const [state, setState] = React.useState<FormState>(DEFAULTS)
  const [touched, setTouched] = React.useState(false)
  const [submitting, setSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!open) return
    setState(rule ? fromRule(rule) : DEFAULTS)
    setTouched(false)
    setError(null)
    setSubmitting(false)
  }, [open, rule])

  const errors = validate(state)
  const valid = Object.keys(errors).length === 0
  const ttlValue = toInt(state.ttl)

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setState((current) => ({ ...current, [key]: value }))
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setTouched(true)
    if (!valid || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      await onSubmit(toInput(state))
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the rule")
      setSubmitting(false)
    }
  }

  const fieldError = (key: keyof FormState) => (touched ? errors[key] : undefined)

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={rule ? "Edit cache rule" : "New cache rule"}
      description={
        rule
          ? `Changes apply immediately; the enabled-rules cache is invalidated on save.`
          : "Responses for matching endpoints are stored in Redis for the TTL below."
      }
      footer={
        <>
          <Button variant="ghost" size="sm" type="button" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            type="submit"
            form="rule-form"
            disabled={submitting || (touched && !valid)}
            className="gap-2"
          >
            {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {rule ? "Save changes" : "Create rule"}
          </Button>
        </>
      }
    >
      <form id="rule-form" onSubmit={handleSubmit} className="space-y-5" noValidate>
        {error && <Alert variant="destructive">{error}</Alert>}

        <div className="space-y-2">
          <Label htmlFor="rule-pattern">Endpoint pattern</Label>
          <Input
            id="rule-pattern"
            value={state.endpoint_pattern}
            onChange={(event) => update("endpoint_pattern", event.target.value)}
            placeholder="/api/v1/products/*"
            maxLength={PATTERN_MAX}
            autoFocus
            className={cn(fieldError("endpoint_pattern") && "border-signal/40")}
          />
          <p className="text-[11px] text-faint">
            {fieldError("endpoint_pattern") ??
              "Matched against the request path. Higher priority rules win when several match."}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="rule-description">Description (optional)</Label>
          <Textarea
            id="rule-description"
            rows={2}
            value={state.description}
            onChange={(event) => update("description", event.target.value)}
            placeholder="Why this endpoint is safe to cache"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="rule-ttl">TTL (seconds)</Label>
          <div className="flex gap-2">
            <Input
              id="rule-ttl"
              type="number"
              inputMode="numeric"
              min={0}
              value={state.ttl}
              onChange={(event) => update("ttl", event.target.value)}
              className={cn("flex-1", fieldError("ttl") && "border-signal/40")}
            />
            <div className="flex gap-1">
              {TTL_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() => update("ttl", String(preset.value))}
                  className={cn(
                    "rounded border px-2 font-mono text-[11px] transition-colors",
                    ttlValue === preset.value
                      ? "border-steel/40 bg-steel/10 text-steel"
                      : "border-rule text-graphite hover:border-rule-strong hover:text-ink",
                  )}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
          <p className="text-[11px] text-faint">
            {fieldError("ttl") ??
              (ttlValue !== null ? `Entries expire after ${formatSeconds(ttlValue)}.` : "")}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="rule-priority">Priority</Label>
            <Input
              id="rule-priority"
              type="number"
              inputMode="numeric"
              min={0}
              value={state.priority}
              onChange={(event) => update("priority", event.target.value)}
              className={cn(fieldError("priority") && "border-signal/40")}
            />
            <p className="text-[11px] text-faint">{fieldError("priority") ?? "Higher wins on overlap."}</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="rule-size">Max cache size</Label>
            <Input
              id="rule-size"
              type="number"
              inputMode="numeric"
              min={MIN_CACHE_SIZE}
              value={state.max_cache_size}
              onChange={(event) => update("max_cache_size", event.target.value)}
              className={cn(fieldError("max_cache_size") && "border-signal/40")}
            />
            <p className="text-[11px] text-faint">
              {fieldError("max_cache_size") ?? `Entries kept per rule, minimum ${MIN_CACHE_SIZE}.`}
            </p>
          </div>
        </div>

        <fieldset className="space-y-2">
          <legend className="mb-2 block text-[12px] text-graphite">
            Cache key includes
          </legend>
          {(
            [
              {
                key: "cache_by_user",
                label: "Authenticated user",
                hint: "Separate entries per user. Required for personalised responses.",
              },
              {
                key: "cache_by_query_params",
                label: "Query parameters",
                hint: "Different ?filters produce different entries.",
              },
              {
                key: "cache_by_headers",
                label: "Request headers",
                hint: "Vary by headers such as Accept-Language.",
              },
            ] as const
          ).map((item) => (
            <label
              key={item.key}
              className="flex cursor-pointer items-start justify-between gap-4 rounded border border-rule bg-frost p-3"
            >
              <span>
                <span className="block text-sm text-ink">{item.label}</span>
                <span className="mt-0.5 block text-[11px] text-faint">{item.hint}</span>
              </span>
              <Switch
                checked={state[item.key]}
                onCheckedChange={(checked) => update(item.key, checked)}
                label={item.label}
              />
            </label>
          ))}
        </fieldset>

        <label className="flex cursor-pointer items-center justify-between gap-4 rounded border border-rule bg-frost p-3">
          <span>
            <span className="block text-sm text-ink">Enabled</span>
            <span className="mt-0.5 block text-[11px] text-faint">
              Paused rules stay configured but do not cache anything.
            </span>
          </span>
          <Switch
            checked={state.enabled}
            onCheckedChange={(checked) => update("enabled", checked)}
            label="Enabled"
          />
        </label>
      </form>
    </Modal>
  )
}
