"use client"

import * as React from "react"

import { authGetAccessToken, authGetClaims, type UserRole } from "@/lib/api"

export interface AuthState {
  /** False until the first client-side read of localStorage. */
  ready: boolean
  token: string | null
  role: UserRole | null
  /** Unix epoch seconds, from the access token. */
  expiresAt: number | null
  /** admin or operator: may create and edit cache rules. */
  canEdit: boolean
  /** admin only: may delete cache rules. */
  isAdmin: boolean
}

const INITIAL: AuthState = {
  ready: false,
  token: null,
  role: null,
  expiresAt: null,
  canEdit: false,
  isAdmin: false,
}

function read(): AuthState {
  const token = authGetAccessToken()
  const claims = token ? authGetClaims() : null
  const role = claims?.role ?? null
  return {
    ready: true,
    token,
    role,
    expiresAt: claims?.exp ?? null,
    canEdit: role === "admin" || role === "operator",
    isAdmin: role === "admin",
  }
}

/**
 * Client-side auth snapshot. Reads localStorage inside an effect so server
 * and first client render agree (no hydration mismatch), then stays in sync
 * with login/logout events.
 */
export function useAuth(): AuthState {
  const [state, setState] = React.useState<AuthState>(INITIAL)

  React.useEffect(() => {
    const sync = () => setState(read())
    sync()
    window.addEventListener("auth-status-changed", sync)
    window.addEventListener("storage", sync)
    return () => {
      window.removeEventListener("auth-status-changed", sync)
      window.removeEventListener("storage", sync)
    }
  }, [])

  return state
}

/**
 * Poll a loader on an interval while the tab is visible. Returns a manual
 * `reload` plus loading/error state. Keeps the last good value on errors.
 */
export function usePolling<T>(
  loader: () => Promise<T>,
  intervalMs: number | null,
): {
  data: T | null
  loading: boolean
  error: string | null
  reload: () => Promise<void>
  updatedAt: number | null
} {
  const [data, setData] = React.useState<T | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [updatedAt, setUpdatedAt] = React.useState<number | null>(null)
  const inFlight = React.useRef(false)
  // A reload asked for while one is running is not dropped: it runs right
  // after, with the newest loader (for example once the monitored service is
  // known), so the last result shown always matches the current inputs.
  const pending = React.useRef(false)
  const latestLoader = React.useRef(loader)
  latestLoader.current = loader

  const reload = React.useCallback(async () => {
    if (inFlight.current) {
      pending.current = true
      return
    }
    inFlight.current = true
    setLoading(true)
    try {
      do {
        pending.current = false
        try {
          const next = await latestLoader.current()
          setData(next)
          setError(null)
          setUpdatedAt(Date.now())
        } catch (err) {
          setError(err instanceof Error ? err.message : "Request failed")
        }
      } while (pending.current)
    } finally {
      inFlight.current = false
      setLoading(false)
    }
  }, [loader])

  React.useEffect(() => {
    void reload()
  }, [reload])

  React.useEffect(() => {
    if (!intervalMs) return
    const tick = () => {
      if (document.visibilityState === "visible") void reload()
    }
    const id = window.setInterval(tick, intervalMs)
    return () => window.clearInterval(id)
  }, [intervalMs, reload])

  return { data, loading, error, reload, updatedAt }
}
