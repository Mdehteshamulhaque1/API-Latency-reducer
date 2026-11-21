"use client"

import * as React from "react"
import { Check, ChevronDown, Search, User, X } from "lucide-react"

import { apiUsers, ApiError, type UserListItem } from "@/lib/api"
import { serviceLabel } from "@/lib/use-service"
import { useViewAs, type ViewAsState, type ViewedUser } from "@/lib/use-view-as"
import { cn } from "@/lib/utils"

function toViewed(item: UserListItem): ViewedUser {
  return {
    key: item.key,
    label: item.username ?? item.key,
    kind: item.kind,
    service: item.service,
  }
}

function kindLabel(user: { kind: ViewedUser["kind"]; service: string | null }, role?: string | null): string {
  if (user.kind === "end_user") return `${user.service ? serviceLabel(user.service) : "Service"} user`
  return role ?? "account"
}

/**
 * Admin-only picker in the top bar: "All users" or one user. Picking a user
 * scopes every dashboard page to that person (see lib/use-view-as.ts).
 */
export function UserSwitch({ className, align = "right" }: { className?: string; align?: "left" | "right" }) {
  const viewAs = useViewAs()
  const [open, setOpen] = React.useState(false)
  const [users, setUsers] = React.useState<UserListItem[] | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [search, setSearch] = React.useState("")
  const rootRef = React.useRef<HTMLDivElement>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)

  React.useEffect(() => {
    if (!open) return
    let cancelled = false
    setError(null)
    apiUsers({ hours: 720 })
      .then((page) => {
        if (!cancelled) setUsers(page.items)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load users")
      })
    inputRef.current?.focus()
    const onPointer = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false)
    }
    document.addEventListener("mousedown", onPointer)
    document.addEventListener("keydown", onKey)
    return () => {
      cancelled = true
      document.removeEventListener("mousedown", onPointer)
      document.removeEventListener("keydown", onKey)
    }
  }, [open])

  if (!viewAs.available) return null

  const term = search.trim().toLowerCase()
  const filtered = (users ?? []).filter(
    (item) =>
      !term ||
      [item.username, item.email, item.key, item.service].some((field) => field?.toLowerCase().includes(term)),
  )

  function pick(next: ViewedUser | null) {
    viewAs.setUser(next)
    setOpen(false)
    setSearch("")
  }

  const current = viewAs.user
  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="View the dashboard as one user"
        className={cn(
          "flex h-8 max-w-[220px] items-center gap-2 rounded border px-2.5 text-[13px] transition-colors",
          current ? "border-steel/60 text-steel" : "border-rule-strong text-graphite hover:border-ink hover:text-ink",
        )}
      >
        <User className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{current ? current.label : "All users"}</span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0" />
      </button>

      {open && (
        <div
          className={cn(
            "absolute top-10 z-50 w-[300px] max-w-[calc(100vw-2rem)] rounded border border-rule-strong bg-paper shadow-lg",
            align === "right" ? "right-0" : "left-0",
          )}
        >
          <div className="flex items-center gap-2 border-b border-rule px-3">
            <Search className="h-3.5 w-3.5 text-faint" />
            <input
              ref={inputRef}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search name, email or id"
              aria-label="Search users"
              className="h-10 w-full bg-transparent text-sm text-ink placeholder:text-faint focus:outline-none"
            />
          </div>
          <ul role="listbox" aria-label="Users" className="max-h-80 overflow-y-auto py-1">
            <li>
              <button
                type="button"
                role="option"
                aria-selected={current === null}
                onClick={() => pick(null)}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-ink hover:bg-frost"
              >
                <span>All users</span>
                {current === null && <Check className="h-3.5 w-3.5" />}
              </button>
            </li>
            {error && <li className="px-3 py-2 text-[13px] text-signal">{error}</li>}
            {!error && users === null && <li className="px-3 py-2 text-[13px] text-graphite">Loading users</li>}
            {!error && users !== null && filtered.length === 0 && (
              <li className="px-3 py-2 text-[13px] text-graphite">No user matches</li>
            )}
            {filtered.map((item) => {
              const selected = current?.key === item.key
              return (
                <li key={item.key}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={selected}
                    onClick={() => pick(toViewed(item))}
                    className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-frost"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm text-ink">{item.username ?? item.key}</span>
                      <span className="block truncate text-[12px] text-graphite">
                        {kindLabel(item, item.role)} · {item.email ?? item.key}
                      </span>
                    </span>
                    {selected && <Check className="h-3.5 w-3.5 shrink-0" />}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}

/** Strip under the top bar while an admin views the dashboard as one user. */
export function ViewAsBanner({ state }: { state: ViewAsState }) {
  const user = state.user
  if (!user) return null
  const endUser = user.kind === "end_user"
  return (
    <div className="border-b border-steel/30 bg-paper px-4 py-2.5 sm:px-6">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-x-4 gap-y-1.5">
        <p className="text-[13px] text-graphite">
          Viewing as <span className="text-ink">{user.label}</span>{" "}
          <span className="text-faint">({kindLabel(user)} · {user.key})</span>. Every page shows only this user&apos;s
          data; cache rules, documents and system status are shared.
          {endUser &&
            ` ${user.service ? serviceLabel(user.service) : "The service"} reports this person's requests, so Overview, Analytics and Rate limits show their API activity, and Cache, LLM gateway and Pricing their searches and charges. AI usage and Guardrails stay empty: model calls are recorded under the service's account.`}
        </p>
        <button
          type="button"
          onClick={() => state.setUser(null)}
          className="inline-flex items-center gap-1.5 rounded border border-rule-strong px-2.5 py-1 text-[13px] text-graphite transition-colors hover:border-ink hover:text-ink"
        >
          <X className="h-3.5 w-3.5" />
          Show all users
        </button>
      </div>
    </div>
  )
}
