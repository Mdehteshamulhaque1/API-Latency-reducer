/* API client for the Esone frontend. Plain browser TypeScript compiled with tsc,
 * no framework. Talks to the Esone API in backend/ (see its README for routes).
 *
 * The API origin comes from <meta name="esone-api-url">, which the Python page
 * server fills from ESONE_WEB_API_URL. Defaults to http://localhost:8000.
 *
 * JWT access/refresh tokens are stored in localStorage; automatic refresh on 401.
 * On 401: refresh once (shared between concurrent calls), retry the original
 * request once; if the refresh fails, clear tokens and notify the UI. No loops.
 */

/** Normalise the API URL: trim, drop trailing slashes, add https:// if the scheme was left out. */
function resolveBaseUrl(raw: string | null | undefined): string {
  const value = (raw ?? "").trim().replace(/\/+$/, "")
  if (!value) return "http://localhost:8000"
  return /^https?:\/\//i.test(value) ? value : `https://${value}`
}

const META = document.querySelector<HTMLMetaElement>('meta[name="esone-api-url"]')

/** Public backend origin, shown in the session console. */
export const API_BASE_URL = resolveBaseUrl(META?.content)

/** Error raised for non-2xx API responses, carrying the backend's message. */
export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

/** Extract a human-readable message from a FastAPI error response. */
async function readErrorMessage(res: Response): Promise<string> {
  try {
    const data: unknown = await res.json()
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail: unknown }).detail
      if (typeof detail === "string") return detail
      if (Array.isArray(detail)) {
        const parts = detail.map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg)
          }
          return typeof item === "string" ? item : "Invalid value"
        })
        if (parts.length > 0) return parts.join(", ")
      }
    }
  } catch {
    /* response had no JSON body */
  }
  if (res.status === 401) return "Invalid username or password"
  if (res.status === 403) return "You do not have permission to do that"
  if (res.status === 429) return "Too many requests. Please try again shortly"
  return `Request failed (${res.status})`
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  // Concatenate rather than resolve: the base may carry a path (for example
  // the API Optimizer proxy, http://host/proxy/esone), which `new URL(path,
  // base)` would discard for an absolute path like /api/v1/chat.
  const url = new URL(`${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`)
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init.headers ?? {}),
  }
  // Bearer tokens only; no cookies, so no credentialed CORS mode is needed.
  return fetch(url.toString(), { ...init, headers })
}

function authHeaders(): Record<string, string> {
  const access = localStorage.getItem("access_token")
  return access ? { Authorization: `Bearer ${access}` } : {}
}

/** Name of the window event fired whenever tokens are stored or cleared. */
export const AUTH_EVENT = "auth-status-changed"

function notifyAuthChanged(): void {
  window.dispatchEvent(new Event(AUTH_EVENT))
}

function clearTokens(): void {
  localStorage.removeItem("access_token")
  localStorage.removeItem("refresh_token")
  notifyAuthChanged()
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type?: string
  expires_in?: number
}

/* The backend rotates refresh tokens and treats a second use of the same one
 * as theft (it revokes every session). Two requests that hit 401 at the same
 * time must therefore share one refresh call instead of each sending the token. */
let refreshInFlight: Promise<boolean> | null = null

/** Exchange the stored refresh token for a new pair. Resolves false (and clears tokens) on failure. */
function refreshTokens(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight
  refreshInFlight = (async () => {
    const refresh = localStorage.getItem("refresh_token")
    if (!refresh) {
      clearTokens()
      return false
    }
    try {
      const res = await request("/api/v1/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refresh }),
      })
      if (!res.ok) {
        clearTokens()
        return false
      }
      const data = (await res.json()) as AuthTokens
      localStorage.setItem("access_token", data.access_token)
      if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token)
      notifyAuthChanged()
      return true
    } catch {
      // Network failure: keep the stored tokens, the next call can try again.
      return false
    } finally {
      refreshInFlight = null
    }
  })()
  return refreshInFlight
}

/** Perform a request with automatic 401 refresh and a single retry. Null when the session is gone. */
export async function requestWithRefresh(path: string, init: RequestInit = {}): Promise<Response | null> {
  const res = await request(path, init)
  if (res.status !== 401) return res
  if (!(await refreshTokens())) return null
  return request(path, { ...init, headers: { ...(init.headers ?? {}), ...authHeaders() } })
}

export async function authLogin(username: string, password: string): Promise<AuthTokens> {
  const res = await request("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) throw new ApiError(await readErrorMessage(res), res.status)
  return res.json() as Promise<AuthTokens>
}

/**
 * Register a new account, then sign in to obtain tokens.
 * The register endpoint returns the created user, not tokens, so a login follows.
 */
export async function authRegister(username: string, email: string, password: string): Promise<AuthTokens> {
  const res = await request("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  })
  if (!res.ok) throw new ApiError(await readErrorMessage(res), res.status)
  return authLogin(username, password)
}

/** Rotate the token pair now (the session console's "Rotate tokens" button). */
export async function authRefresh(): Promise<{ access_token: string }> {
  const ok = await refreshTokens()
  const access = ok ? authGetAccessToken() : null
  if (!access) throw new ApiError("Session expired. Please sign in again", 401)
  return { access_token: access }
}

export function authLogout(): void {
  const refresh = localStorage.getItem("refresh_token")
  localStorage.removeItem("access_token")
  localStorage.removeItem("refresh_token")
  notifyAuthChanged()
  if (refresh) {
    // Best effort: revoke the refresh token on the server. Local state is already cleared.
    void request("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refresh }),
    }).catch(() => undefined)
  }
}

export function authStoreTokens(tokens: AuthTokens): void {
  localStorage.setItem("access_token", tokens.access_token)
  localStorage.setItem("refresh_token", tokens.refresh_token)
  notifyAuthChanged()
}

export function authGetAccessToken(): string | null {
  return localStorage.getItem("access_token")
}

/** Decode a JWT payload without verifying the signature (UI display only). */
function decodeTokenPayload(token: string): Record<string, unknown> | null {
  try {
    const segment = token.split(".")[1]
    if (!segment) return null
    const base64 = segment.replace(/-/g, "+").replace(/_/g, "/")
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=")
    const json = decodeURIComponent(
      Array.from(atob(padded))
        .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
        .join(""),
    )
    const payload: unknown = JSON.parse(json)
    return payload && typeof payload === "object" ? (payload as Record<string, unknown>) : null
  } catch {
    return null
  }
}

/** Claims the backend places in every JWT (see backend/esone_api/security.py). */
export interface TokenClaims {
  sub: string | null
  role: string | null
  type: string | null
  /** Expiry as a Unix timestamp in seconds, or null when absent. */
  exp: number | null
}

function toClaims(payload: Record<string, unknown>): TokenClaims {
  const str = (v: unknown) => (typeof v === "string" ? v : null)
  const exp = payload.exp
  return {
    sub: str(payload.sub),
    role: str(payload.role),
    type: str(payload.type),
    exp: typeof exp === "number" ? exp : null,
  }
}

/** Decoded claims of the stored access token, or null when signed out. */
export function authGetClaims(): TokenClaims | null {
  const token = authGetAccessToken()
  if (!token) return null
  const payload = decodeTokenPayload(token)
  return payload ? toClaims(payload) : null
}

export function authGetRole(): string | null {
  const token = authGetAccessToken()
  if (!token) return null
  const role = decodeTokenPayload(token)?.role
  return typeof role === "string" ? role : null
}

// ----- Esone API helpers (backend/) -----

async function authed(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await requestWithRefresh(path, {
    ...init,
    headers: { ...(init.headers ?? {}), ...authHeaders() },
  })
  if (!res) throw new ApiError("Session expired. Please sign in again", 401)
  if (!res.ok) throw new ApiError(await readErrorMessage(res), res.status)
  return res
}

export interface UserProfile {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
  created_at: string
}

/** GET /api/v1/users/me */
export async function apiMe(): Promise<UserProfile> {
  const res = await authed("/api/v1/users/me", { method: "GET" })
  return res.json() as Promise<UserProfile>
}

/** POST /api/v1/users/me/password. Revokes every refresh token for the account. */
export async function apiChangePassword(currentPassword: string, newPassword: string): Promise<void> {
  await authed("/api/v1/users/me/password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
}

export interface UserList {
  items: UserProfile[]
  total: number
  limit: number
  offset: number
}

/** GET /api/v1/admin/users (admin only) */
export async function apiAdminUsers(limit = 50, offset = 0): Promise<UserList> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  const res = await authed(`/api/v1/admin/users?${params.toString()}`, { method: "GET" })
  return res.json() as Promise<UserList>
}

export type Role = "admin" | "operator" | "viewer"

export interface AdminUserPatch {
  role?: Role
  is_active?: boolean
}

/** PATCH /api/v1/admin/users/{id} (admin only) */
export async function apiAdminUpdateUser(id: number, patch: AdminUserPatch): Promise<UserProfile> {
  const res = await authed(`/api/v1/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(patch) })
  return res.json() as Promise<UserProfile>
}

// ----- chat: questions answered by the API Optimizer (backend/esone_api/routers/chat.py) -----

export interface AnswerSource {
  title: string
  url: string
  /** Provider the page came from: wikipedia, duckduckgo, wikidata or web (null for older rows). */
  source: string | null
}

export interface AnswerResponse {
  question: string
  answer: string
  answered_by: "cache" | "model" | "crawler"
  cached: boolean
  similarity: number | null
  matched_question: string | null
  match_method: string | null
  sources: AnswerSource[]
  latency_ms: number
  crawl_ms: number | null
  compose_method: string | null
  embedding_used: boolean
  cache_lookup_ms: number
  llm_ms: number
  total_tokens: number
  estimated_cost_usd: number
  served_model: string | null
  /** False when the question carried personal data: answered, but kept out of the shared cache. */
  cacheable: boolean
}

/** POST /api/v1/chat (signed in). Esone forwards the question to the Optimizer's answers pipeline. */
export async function apiAsk(question: string): Promise<AnswerResponse> {
  const res = await authed("/api/v1/chat", { method: "POST", body: JSON.stringify({ question }) })
  return res.json() as Promise<AnswerResponse>
}

/** One earlier question of the signed-in user (backend/esone_api/routers/chat.py). */
export interface ChatHistoryItem {
  id: number
  created_at: string
  question: string
  answer: string
  /** ok | error */
  status: string
  error_message: string | null
  answered_by: "cache" | "model" | "crawler"
  cached: boolean
  /** exact | semantic | miss | none */
  cache_type: string
  match_method: string | null
  similarity: number | null
  compose_method: string | null
  sources: AnswerSource[]
  sources_count: number
  latency_ms: number
  cache_lookup_ms: number
  crawl_ms: number | null
  llm_ms: number
  total_tokens: number
  estimated_cost_usd: number
  served_model: string | null
  correlation_id: string | null
}

export interface NameCount {
  name: string
  count: number
}

export interface ChatLatencyPoint {
  at: string
  latency_ms: number
  cached: boolean
}

/** The signed-in user's own chat activity (backend/esone_api/routers/chat.py, GET /chat/stats). */
export interface ChatStats {
  hours: number
  total_queries: number
  answered: number
  errors: number
  cache_hits: number
  exact_hits: number
  semantic_hits: number
  misses: number
  cache_hit_rate: number
  avg_latency_ms: number
  avg_latency_cached_ms: number
  avg_latency_crawled_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  p99_latency_ms: number
  total_tokens: number
  estimated_cost_usd: number
  sources_used: number
  by_source: NameCount[]
  by_model: NameCount[]
  by_error: NameCount[]
  latency_series: ChatLatencyPoint[]
  recent: ChatHistoryItem[]
  recent_errors: ChatHistoryItem[]
  /** INR charged to this user: tokens of answers not served from the cache. */
  billable_tokens: number
  cost_inr: number
}

/** GET /api/v1/chat/stats (signed in): only the caller's own rows. */
export async function apiChatStats(hours = 24 * 30): Promise<ChatStats> {
  const res = await authed(`/api/v1/chat/stats?hours=${hours}`, { method: "GET" })
  return res.json() as Promise<ChatStats>
}

export interface ChatHistory {
  /** Oldest first, so the list reads like the conversation. */
  items: ChatHistoryItem[]
  total: number
}

/** GET /api/v1/chat/history (signed in). */
export async function apiChatHistory(limit = 50): Promise<ChatHistory> {
  const res = await authed(`/api/v1/chat/history?limit=${limit}`, { method: "GET" })
  return res.json() as Promise<ChatHistory>
}

/** DELETE /api/v1/chat/history (signed in): forget the user's earlier questions. */
export async function apiChatHistoryClear(): Promise<{ deleted: number }> {
  const res = await authed("/api/v1/chat/history", { method: "DELETE" })
  return res.json() as Promise<{ deleted: number }>
}
