"use client"

import * as React from "react"

import { setViewAsUser, type UserKind } from "@/lib/api"
import { useAuth } from "@/lib/use-auth"

const STORAGE_KEY = "apiopt.view-as"

/** The user an admin is viewing the dashboard as. */
export interface ViewedUser {
  /** "account:<id>" or an end-user reference such as "esone:7" (the backend's as_user). */
  key: string
  label: string
  kind: UserKind
  /** Owning service for end users ("esone"), else null. */
  service: string | null
}

export interface ViewAsState {
  /** False until the stored choice was read; pages wait so their first fetch is already scoped. */
  ready: boolean
  /** Only admins may view as another user. */
  available: boolean
  user: ViewedUser | null
  setUser: (user: ViewedUser | null) => void
}

function isViewedUser(value: unknown): value is ViewedUser {
  if (!value || typeof value !== "object") return false
  const v = value as Record<string, unknown>
  return (
    typeof v.key === "string" &&
    typeof v.label === "string" &&
    (v.kind === "account" || v.kind === "end_user") &&
    (v.service === null || typeof v.service === "string")
  )
}

function readStored(): ViewedUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    return isViewedUser(parsed) ? parsed : null
  } catch {
    return null
  }
}

function writeStored(user: ViewedUser | null) {
  try {
    if (user) localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* blocked storage: the choice just does not survive a reload */
  }
}

const ViewAsContext = React.createContext<ViewAsState>({
  ready: true,
  available: false,
  user: null,
  setUser: () => undefined,
})

/**
 * Admin "view as user" for the whole dashboard (mounted by the shell). The
 * selection is pushed into lib/api.ts, which appends `as_user` to every read
 * that supports it, so each page shows that one user's data.
 */
export function ViewAsProvider({ children }: { children: React.ReactNode }) {
  const auth = useAuth()
  const [user, setUserState] = React.useState<ViewedUser | null>(null)
  const [ready, setReady] = React.useState(false)

  React.useEffect(() => {
    if (!auth.ready) return
    const restored = auth.isAdmin ? readStored() : null
    setViewAsUser(restored?.key ?? null)
    setUserState(restored)
    setReady(true)
  }, [auth.ready, auth.isAdmin])

  const setUser = React.useCallback(
    (next: ViewedUser | null) => {
      if (!auth.isAdmin) return
      // Set the API scope before the state change remounts the pages.
      setViewAsUser(next?.key ?? null)
      writeStored(next)
      setUserState(next)
    },
    [auth.isAdmin],
  )

  const value = React.useMemo<ViewAsState>(
    () => ({ ready, available: auth.isAdmin, user: auth.isAdmin ? user : null, setUser }),
    [ready, auth.isAdmin, user, setUser],
  )
  return React.createElement(ViewAsContext.Provider, { value }, children)
}

export function useViewAs(): ViewAsState {
  return React.useContext(ViewAsContext)
}
