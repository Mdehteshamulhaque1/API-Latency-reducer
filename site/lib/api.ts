/* API client for site/ (Next.js 14 App Router, TypeScript, native fetch).
 *
 * - Reads NEXT_PUBLIC_API_URL (defaults to http://localhost:8000).
 * - JWT access/refresh tokens live in localStorage.
 * - On 401: refresh once, retry the original request once. If the refresh
 *   fails, tokens are cleared and a `login-needed` event is dispatched.
 * - Every helper below maps 1:1 to a route in app/api/v1/*.py. Do not add
 *   helpers for endpoints that do not exist in the backend.
 */

type InitOptions = RequestInit & {
  headers?: HeadersInit & { Authorization?: string }
}

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "")

/** Public backend origin, e.g. for linking to Prometheus metrics. */
export const API_BASE_URL = BASE_URL

const ACCESS_KEY = "access_token"
const REFRESH_KEY = "refresh_token"

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
            const rawLoc = "loc" in item ? (item as { loc: unknown }).loc : null
            const loc = Array.isArray(rawLoc)
              ? rawLoc.filter((p): p is string => typeof p === "string" && p !== "body")
              : []
            const field = loc.length > 0 ? `${loc[loc.length - 1]}: ` : ""
            return `${field}${String((item as { msg: unknown }).msg)}`
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
  if (res.status === 404) return "Not found"
  if (res.status === 429) return "Too many requests — please try again shortly"
  if (res.status >= 500) return "The gateway returned a server error"
  return `Request failed (${res.status})`
}

function clearTokens(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

function signalLoginNeeded(): void {
  if (typeof window === "undefined") return
  window.dispatchEvent(new Event("login-needed"))
}

async function request(path: string, init: InitOptions = {}): Promise<Response> {
  const url = new URL(path, BASE_URL)
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init.headers ?? {}),
  }
  const fetchInit: RequestInit = {
    ...init,
    headers,
    credentials: "include",
  }
  return fetch(url.toString(), fetchInit)
}

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {}
  const access = localStorage.getItem(ACCESS_KEY)
  if (!access) return {}
  return { Authorization: `Bearer ${access}` }
}

// Perform a request with automatic 401 refresh + single retry.
// Returns the Response object (or null if refresh failed and tokens cleared).
export async function requestWithRefresh(
  path: string,
  init: InitOptions = {},
): Promise<Response | null> {
  const res = await request(path, init)
  if (res.status !== 401) return res

  const refreshToken = typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY)
  if (!refreshToken) {
    clearTokens()
    signalLoginNeeded()
    return null
  }

  const refreshRes = await request("/api/v1/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!refreshRes.ok) {
    clearTokens()
    signalLoginNeeded()
    return null
  }

  let refreshData: AuthTokens
  try {
    refreshData = (await refreshRes.json()) as AuthTokens
  } catch {
    clearTokens()
    signalLoginNeeded()
    return null
  }

  localStorage.setItem(ACCESS_KEY, refreshData.access_token)
  if (refreshData.refresh_token) {
    localStorage.setItem(REFRESH_KEY, refreshData.refresh_token)
  }

  // Retry the original request once with the new token.
  return request(path, { ...init, headers: { ...(init.headers ?? {}), ...authHeaders() } })
}

/** Authenticated JSON call: throws ApiError on failure, returns parsed body. */
// ---------------------------------------------------------------------------
// Admin "view as user": GET reads that accept `as_user` (app/core/view_as.py)
// ---------------------------------------------------------------------------

const VIEW_AS_PATHS = [
  "/api/v1/analytics/summary",
  "/api/v1/analytics/endpoints",
  "/api/v1/analytics/benchmark",
  "/api/v1/analytics/slow-endpoints",
  "/api/v1/analytics/suggestions",
  "/api/v1/analytics/queries",
  "/api/v1/rate-limits/me",
  "/api/v1/rate-limits/events",
  "/api/v1/ai-usage/summary",
  "/api/v1/ai-usage/requests",
  "/api/v1/guardrails/summary",
  "/api/v1/guardrails/events",
  "/api/v1/answers/recent",
  "/api/v1/answers/top",
  "/api/v1/answers/stats",
  "/api/v1/answers/cache",
  "/api/v1/answers/costs",
  "/api/v1/answers/users",
  "/api/v1/pricing/users",
]

let viewAsKey: string | null = null

/** Scope every supported dashboard read to one user ("account:<id>" or "esone:7"); null shows everyone. Admin only. */
export function setViewAsUser(key: string | null): void {
  viewAsKey = key
}

function withViewAs(path: string, init: InitOptions): string {
  if (!viewAsKey || (init.method ?? "GET").toUpperCase() !== "GET") return path
  const bare = path.split("?")[0]
  if (!VIEW_AS_PATHS.some((scoped) => bare === scoped || bare.startsWith(`${scoped}/`))) return path
  return `${path}${path.includes("?") ? "&" : "?"}as_user=${encodeURIComponent(viewAsKey)}`
}

async function authed<T>(path: string, init: InitOptions = {}): Promise<T> {
  const res = await requestWithRefresh(withViewAs(path, init), {
    ...init,
    headers: { ...(init.headers ?? {}), ...authHeaders() },
  })
  if (!res) throw new ApiError("Session expired — please sign in again", 401)
  if (!res.ok) throw new ApiError(await readErrorMessage(res), res.status)
  return (await res.json()) as T
}

/** Authenticated multipart upload (no JSON content type; the browser sets the boundary). */
async function authedUpload<T>(path: string, form: FormData): Promise<T> {
  const url = new URL(path, BASE_URL)
  const send = (headers: HeadersInit) =>
    fetch(url.toString(), { method: "POST", body: form, headers, credentials: "include" })
  let res = await send(authHeaders())
  if (res.status === 401) {
    const refreshed = await requestWithRefresh("/api/v1/ping", { method: "GET" })
    if (!refreshed) throw new ApiError("Session expired — please sign in again", 401)
    res = await send(authHeaders())
  }
  if (!res.ok) throw new ApiError(await readErrorMessage(res), res.status)
  return (await res.json()) as T
}

function withQuery(path: string, params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue
    search.set(key, String(value))
  }
  const query = search.toString()
  return query ? `${path}?${query}` : path
}

// ---------------------------------------------------------------------------
// Auth (app/api/v1/auth.py)
// ---------------------------------------------------------------------------

export type UserRole = "admin" | "operator" | "viewer" | "guest"

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type?: string
  expires_in?: number
}

export interface UserResponse {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
}

export async function authLogin(username: string, password: string): Promise<AuthTokens> {
  const res = await request("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) throw new ApiError(await readErrorMessage(res), res.status)
  return (await res.json()) as AuthTokens
}

/**
 * Register a new account, then sign in to obtain tokens.
 * POST /auth/register returns the created user (not tokens), so a follow-up
 * login is required to start a session.
 */
export async function authRegister(
  username: string,
  email: string,
  password: string,
): Promise<AuthTokens> {
  const res = await request("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  })
  if (!res.ok) throw new ApiError(await readErrorMessage(res), res.status)
  return authLogin(username, password)
}

export async function authRefresh(): Promise<{ access_token: string }> {
  const res = await request("/api/v1/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: localStorage.getItem(REFRESH_KEY) }),
  })
  if (!res.ok) throw new ApiError(await readErrorMessage(res), res.status)
  const data = (await res.json()) as AuthTokens
  localStorage.setItem(ACCESS_KEY, data.access_token)
  if (data.refresh_token) localStorage.setItem(REFRESH_KEY, data.refresh_token)
  return { access_token: data.access_token }
}

/**
 * Clear the session locally and, best effort, revoke both tokens on the
 * server (POST /auth/logout). Local state is cleared even if the call fails.
 */
export function authLogout(): void {
  viewAsKey = null
  if (typeof window !== "undefined") {
    try {
      localStorage.removeItem("apiopt.view-as")
    } catch {
      /* blocked storage */
    }
  }
  const access = authGetAccessToken()
  const refresh = typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY)
  clearTokens()
  if (!access || !refresh) return
  void request("/api/v1/auth/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${access}` },
    body: JSON.stringify({ refresh_token: refresh }),
  }).catch(() => undefined)
}

export function authStoreTokens(tokens: AuthTokens): void {
  localStorage.setItem(ACCESS_KEY, tokens.access_token)
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token)
}

export function authGetAccessToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(ACCESS_KEY)
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

export interface TokenClaims {
  sub: string | null
  role: UserRole | null
  /** Unix epoch seconds. */
  exp: number | null
}

export function authGetClaims(): TokenClaims | null {
  const token = authGetAccessToken()
  if (!token) return null
  const payload = decodeTokenPayload(token)
  if (!payload) return null
  const role = payload.role
  const exp = payload.exp
  const sub = payload.sub
  return {
    sub: typeof sub === "string" ? sub : null,
    role:
      role === "admin" || role === "operator" || role === "viewer" || role === "guest"
        ? role
        : null,
    exp: typeof exp === "number" ? exp : null,
  }
}

// ---------------------------------------------------------------------------
// Cache rules (app/api/v1/rules.py)
// ---------------------------------------------------------------------------

/** CacheRuleResponse (app/schemas/rules.py). */
export interface CacheRule {
  id: number
  endpoint_pattern: string
  /** Seconds; 0 means the rule caches without a TTL override. */
  ttl: number
  enabled: boolean
  cache_by_user: boolean
  cache_by_query_params: boolean
  cache_by_headers: boolean
  /** Largest cacheable body, in KB. */
  max_cache_size: number
  priority: number
  description: string | null
  created_at: string
  updated_at: string
}

export type CacheRuleInput = Omit<CacheRule, "id" | "created_at" | "updated_at">
export type CacheRulePatch = Partial<CacheRuleInput>

export async function apiRules(): Promise<CacheRule[]> {
  const data = await authed<unknown>("/api/v1/rules", { method: "GET" })
  return Array.isArray(data) ? (data as CacheRule[]) : []
}

/** Requires the admin or operator role. */
export async function apiCreateRule(input: CacheRuleInput): Promise<CacheRule> {
  return authed<CacheRule>("/api/v1/rules", {
    method: "POST",
    body: JSON.stringify(input),
  })
}

/** Requires the admin or operator role. Only the provided fields change. */
export async function apiUpdateRule(id: number, patch: CacheRulePatch): Promise<CacheRule> {
  return authed<CacheRule>(`/api/v1/rules/${id}`, {
    method: "PUT",
    body: JSON.stringify(patch),
  })
}

/** Requires the admin role. */
export async function apiDeleteRule(id: number): Promise<{ message: string }> {
  return authed<{ message: string }>(`/api/v1/rules/${id}`, { method: "DELETE" })
}

// ---------------------------------------------------------------------------
// Analytics (app/api/v1/analytics.py)
// ---------------------------------------------------------------------------

/** Which application a request-log row belongs to, and whether it served the request or made it. */
export type RequestDirection = "inbound" | "outbound"

export interface RecentRequest {
  endpoint: string
  method: string
  status_code: number
  response_time_ms: number
  cache_hit: boolean
  created_at: string
  service: string
  direction: RequestDirection
  upstream_host: string | null
}

/** One application with request rows in the window (GET /api/v1/analytics/services). */
export interface MonitoredService {
  service: string
  /** True for the API Optimizer's own traffic. */
  is_self: boolean
  requests: number
  inbound: number
  outbound: number
  errors: number
  avg_response_time_ms: number
  last_seen: string | null
  /** Gateway account the service ships with; its LLM calls and guardrail events belong to it. */
  account_user_id: number | null
}

/** Who a scoped read covers: everyone (admin), the caller, or a monitored service. */
export type ReadScope = "all" | "own" | "service"

/** Scope shared by the analytics reads: a monitored service's rows, optionally one direction. */
export interface AnalyticsScope {
  /** Monitored service name (e.g. "esone"). Omit for the caller's own gateway requests. */
  service?: string
  direction?: RequestDirection
}

export interface LatencyPoint {
  timestamp: string
  avg_response_time_ms: number
  request_count: number
  error_count: number
}

export interface LatencyDistributionPoint extends LatencyPoint {
  p95_response_time_ms: number
  p99_response_time_ms: number
}

export interface TopEndpoint {
  endpoint: string
  count: number
  avg_time: number
  errors: number
  cache_hit_rate: number
}

export interface SlowEndpoint extends TopEndpoint {
  p95_time: number
  p99_time: number
  error_rate: number
}

export type SuggestionSeverity = "low" | "medium" | "high"

export interface OptimizationSuggestion {
  title: string
  severity: SuggestionSeverity
  endpoint: string | null
  reason: string
  action: string
}

export interface BenchmarkReport {
  baseline_avg_response_time_ms: number
  optimized_avg_response_time_ms: number
  improvement_percent: number
  sample_size: number
  before_window: string
  after_window: string
}

export interface AnalyticsSummary {
  total_requests: number
  total_errors: number
  rate_limited_requests: number
  cache_hit_rate: number
  avg_response_time_ms: number
  slowest_endpoint: string | null
  slowest_response_time_ms: number | null
  top_endpoints: TopEndpoint[]
  error_rate: number
  request_rate_per_minute: number
  cache_miss_rate: number
  recent_requests: RecentRequest[]
  latency_series: LatencyPoint[]
  slow_endpoint_ranking: SlowEndpoint[]
  overall_p50_response_time_ms: number
  overall_p95_response_time_ms: number
  overall_p99_response_time_ms: number
  latency_distribution: LatencyDistributionPoint[]
  slow_endpoints: TopEndpoint[]
  optimization_suggestions: OptimizationSuggestion[]
  benchmark: BenchmarkReport | null
}

/** Raw request log row (APILog.to_dict()). */
export interface ApiLog {
  id: number
  user_id: number | null
  method: string
  endpoint: string
  path: string
  status_code: number
  response_time_ms: number
  cache_hit: boolean
  cache_key: string | null
  client_ip: string
  correlation_id: string
  request_size_bytes: number
  response_size_bytes: number
  query_params: string | null
  service: string
  direction: RequestDirection
  upstream_host: string | null
  error_message: string | null
  created_at: string
}

/** Valid `hours` window for every analytics route: 1..720. */
export function clampHours(hours: number): number {
  if (!Number.isFinite(hours)) return 24
  return Math.min(720, Math.max(1, Math.round(hours)))
}

export async function apiAnalyticsServices(hours = 24): Promise<MonitoredService[]> {
  const data = await authed<unknown>(
    withQuery("/api/v1/analytics/services", { hours: clampHours(hours) }),
    { method: "GET" },
  )
  return Array.isArray(data) ? (data as MonitoredService[]) : []
}

/** One kind of request in GET /api/v1/analytics/queries (app/schemas/analytics.py QueryCategory). */
export interface QueryCategory {
  key: string
  label: string
  /** query = questions users asked; supporting = sign-in, history, health; outbound = calls the service made. */
  group: "query" | "supporting" | "outbound"
  description: string
  requests: number
  errors: number
  avg_response_time_ms: number
  endpoints: { method: string; endpoint: string; requests: number }[]
}

export interface QueryBreakdown {
  hours: number
  total_requests: number
  real_queries: number
  supporting_requests: number
  outbound_calls: number
  categories: QueryCategory[]
  searches: {
    questions: number
    cache_hits: number
    fresh_answers: number
    errors: number
    avg_latency_ms: number
    total_tokens: number
    billable_tokens: number
    cost_inr: number
    rate_per_token_inr: number
  }
}

/** GET /api/v1/analytics/queries: real queries apart from sign-in, history and health traffic, with search cost. */
export async function apiQueryBreakdown(hours = 24, service?: string): Promise<QueryBreakdown> {
  return authed<QueryBreakdown>(
    withQuery("/api/v1/analytics/queries", { hours: clampHours(hours), service: service || undefined }),
    { method: "GET" },
  )
}

export async function apiAnalyticsSummary(hours = 24, scope: AnalyticsScope = {}): Promise<AnalyticsSummary> {
  return authed<AnalyticsSummary>(
    withQuery("/api/v1/analytics/summary", {
      hours: clampHours(hours),
      service: scope.service || undefined,
      direction: scope.direction,
    }),
    { method: "GET" },
  )
}

export interface EndpointLogQuery extends AnalyticsScope {
  /** Substring match against APILog.endpoint. */
  pattern?: string
  /** Exact HTTP method, e.g. "POST". */
  method?: string
  hours?: number
  /** 1..500 */
  limit?: number
}

export async function apiAnalyticsEndpoints(query: EndpointLogQuery = {}): Promise<ApiLog[]> {
  const data = await authed<unknown>(
    withQuery("/api/v1/analytics/endpoints", {
      endpoint_pattern: query.pattern?.trim() || undefined,
      method: query.method || undefined,
      hours: query.hours === undefined ? undefined : clampHours(query.hours),
      limit: query.limit === undefined ? undefined : Math.min(500, Math.max(1, query.limit)),
      service: query.service || undefined,
      direction: query.direction,
    }),
    { method: "GET" },
  )
  return Array.isArray(data) ? (data as ApiLog[]) : []
}

export async function apiAnalyticsBenchmark(hours = 24, scope: AnalyticsScope = {}): Promise<BenchmarkReport> {
  return authed<BenchmarkReport>(
    withQuery("/api/v1/analytics/benchmark", { hours: clampHours(hours), service: scope.service || undefined }),
    { method: "GET" },
  )
}

export interface BenchmarkRunResult {
  status: string
  hours: number
  report: BenchmarkReport
}

/** Computes the report now and schedules a background persist task. */
export async function apiRunBenchmark(hours = 24): Promise<BenchmarkRunResult> {
  return authed<BenchmarkRunResult>(
    withQuery("/api/v1/analytics/benchmark/run", { hours: clampHours(hours) }),
    { method: "POST" },
  )
}

export async function apiSuggestions(hours = 24, scope: AnalyticsScope = {}): Promise<OptimizationSuggestion[]> {
  const data = await authed<unknown>(
    withQuery("/api/v1/analytics/suggestions", { hours: clampHours(hours), service: scope.service || undefined }),
    { method: "GET" },
  )
  return Array.isArray(data) ? (data as OptimizationSuggestion[]) : []
}

// ---------------------------------------------------------------------------
// Cache management (app/api/v1/cache.py)
// ---------------------------------------------------------------------------

export interface CacheStats {
  available: boolean
  cache_hits: number
  cache_misses: number
  lookups: number
  cache_hit_rate: number
  response_entries: number
  chat_entries: number
  default_ttl_seconds: number
  enabled_rules: number
  total_rules: number
}

export async function apiCacheStats(): Promise<CacheStats> {
  return authed<CacheStats>("/api/v1/cache/stats", { method: "GET" })
}

export interface CacheInvalidateInput {
  endpoint_pattern?: string
  include_chat?: boolean
}

/** Requires the admin or operator role. */
export async function apiCacheInvalidate(
  input: CacheInvalidateInput = {},
): Promise<{ scope: string; deleted: number }> {
  return authed<{ scope: string; deleted: number }>("/api/v1/cache/invalidate", {
    method: "POST",
    body: JSON.stringify(input),
  })
}

// ---------------------------------------------------------------------------
// Rate limits (app/api/v1/rate_limits.py)
// ---------------------------------------------------------------------------

export interface RateLimitTierInfo {
  /** anonymous | user | privileged */
  name: string
  applies_to: string
  capacity: number
  period_seconds: number
  refill_per_second: number
  /** RateLimit-Policy value: "<limit>;w=<window seconds>". */
  policy: string
}

export interface RateLimitConfig {
  enabled: boolean
  algorithm: string
  /** The caller's own tier; capacity and period_seconds describe it. */
  your_tier: string
  capacity: number
  period_seconds: number
  refill_per_second: number
  tiers: RateLimitTierInfo[]
  identifier_strategy: string
  failure_policy: string
  headers: string[]
  excluded_paths: string[]
}

export interface RateLimitUsage {
  identifier: string
  tier: string
  limit: number
  period_seconds: number
  remaining: number
  used: number
  reset_in_seconds: number
  has_bucket: boolean
  error: string | null
}

export interface RateLimitEvent {
  id: number
  created_at: string
  method: string
  endpoint: string
  client_ip: string
  user_id: number | null
  correlation_id: string
}

export interface RateLimitEventSummary {
  hours: number
  total_requests: number
  rate_limited_requests: number
  rate_limited_percent: number
  scope: ReadScope
  events: RateLimitEvent[]
}

export async function apiRateLimitConfig(): Promise<RateLimitConfig> {
  return authed<RateLimitConfig>("/api/v1/rate-limits/config", { method: "GET" })
}

export async function apiRateLimitMe(): Promise<RateLimitUsage> {
  return authed<RateLimitUsage>("/api/v1/rate-limits/me", { method: "GET" })
}

export async function apiRateLimitEvents(hours = 24, limit = 50, scope: AnalyticsScope = {}): Promise<RateLimitEventSummary> {
  return authed<RateLimitEventSummary>(
    withQuery("/api/v1/rate-limits/events", {
      hours: clampHours(hours),
      limit: Math.min(500, Math.max(1, limit)),
      service: scope.service || undefined,
    }),
    { method: "GET" },
  )
}

// ---------------------------------------------------------------------------
// AI usage (app/api/v1/ai_usage.py)
// ---------------------------------------------------------------------------

export interface AIModelUsage {
  served_model: string
  requests: number
  successes: number
  cache_hits: number
  errors: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  avg_latency_ms: number
  estimated_cost_usd: number
}

export interface AIUsagePoint {
  timestamp: string
  requests: number
  errors: number
  total_tokens: number
  estimated_cost_usd: number
}

export interface AIUsageSummary {
  hours: number
  scope: ReadScope
  requests: number
  successes: number
  cache_hits: number
  errors: number
  fallbacks: number
  error_rate: number
  cache_hit_rate: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  avg_latency_ms: number
  estimated_cost_usd: number
  cost_is_estimate: boolean
  pricing_source: string
  by_model: AIModelUsage[]
  series: AIUsagePoint[]
}

export interface AIRequestLogItem {
  id: number
  created_at: string
  user_id: number | null
  correlation_id: string | null
  feature: string
  provider: string
  requested_model: string | null
  served_model: string | null
  outcome: "success" | "cache_hit" | "error"
  fallback_used: boolean
  error_code: string | null
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  latency_ms: number
  estimated_cost_usd: number
}

export async function apiAiUsageSummary(hours = 24, scope: AnalyticsScope = {}): Promise<AIUsageSummary> {
  return authed<AIUsageSummary>(
    withQuery("/api/v1/ai-usage/summary", { hours: clampHours(hours), service: scope.service || undefined }),
    { method: "GET" },
  )
}

export async function apiAiUsageRequests(
  hours = 24,
  limit = 50,
  scope: AnalyticsScope = {},
): Promise<{ hours: number; scope: ReadScope; items: AIRequestLogItem[] }> {
  return authed<{ hours: number; scope: ReadScope; items: AIRequestLogItem[] }>(
    withQuery("/api/v1/ai-usage/requests", {
      hours: clampHours(hours),
      limit: Math.min(500, Math.max(1, limit)),
      service: scope.service || undefined,
    }),
    { method: "GET" },
  )
}

export interface ChatModelPricing {
  model: string
  prompt_per_million: number
  completion_per_million: number
}

export interface EmbeddingModelPricing {
  model: string
  price_per_million: number
}

export interface PricingDefaults {
  chat_prompt_per_million: number
  chat_completion_per_million: number
  embedding_per_million: number
}

export interface TokenBilling {
  currency: string
  rate_per_token: number
  unit: string
  note: string
}

export interface PricingTable {
  currency: string
  effective_date: string
  unit: string
  source: string
  is_estimate: boolean
  note: string
  defaults: PricingDefaults
  billing: TokenBilling
  chat_models: ChatModelPricing[]
  embedding_models: EmbeddingModelPricing[]
}

export interface UserTokenUsage {
  user_id: number | null
  username: string | null
  email: string | null
  role: string | null
  end_user: string | null
  answers: number
  cached_answers: number
  uncached_answers: number
  total_tokens: number
  billable_tokens: number
  cost_inr: number
}

export interface UserTokenUsageResponse {
  /** "all" for admins, "own" for everyone else. */
  scope: string
  currency: string
  rate_per_token: number
  unit: string
  note: string
  total_billable_tokens: number
  total_cost_inr: number
  items: UserTokenUsage[]
}

export async function apiPricing(): Promise<PricingTable> {
  return authed<PricingTable>("/api/v1/pricing", { method: "GET" })
}

export async function apiPricingUsers(): Promise<UserTokenUsageResponse> {
  return authed<UserTokenUsageResponse>("/api/v1/pricing/users", { method: "GET" })
}

// ---------------------------------------------------------------------------
// Guardrails (app/api/v1/guardrails.py)
// ---------------------------------------------------------------------------

export type GuardrailCategory =
  | "injection_detected"
  | "injection_blocked"
  | "pii_masked"
  | "output_invalid"
  | "low_grounding"
  | "retrieval_failed"
  | "ai_request_failed"
  | "document_flagged"
  | "upload_rejected"

export interface GuardrailSummary {
  hours: number
  scope: ReadScope
  total_events: number
  blocked_requests: number
  high_severity: number
  by_category: Record<GuardrailCategory, number>
  by_feature: Record<string, number>
  injection_blocking_enabled: boolean
  pii_masking_enabled: boolean
  note: string
}

export interface GuardrailEvent {
  id: number
  created_at: string
  user_id: number | null
  correlation_id: string | null
  category: GuardrailCategory
  severity: "low" | "medium" | "high"
  feature: string
  detail: string
  blocked: boolean
}

export interface GuardrailCheck {
  injection_severity: "none" | "low" | "medium" | "high"
  injection_rules: string[]
  would_block: boolean
  pii_counts: Record<string, number>
  masked_text: string
}

export async function apiGuardrailSummary(hours = 24, scope: AnalyticsScope = {}): Promise<GuardrailSummary> {
  return authed<GuardrailSummary>(
    withQuery("/api/v1/guardrails/summary", { hours: clampHours(hours), service: scope.service || undefined }),
    { method: "GET" },
  )
}

export async function apiGuardrailEvents(
  hours = 24,
  limit = 50,
  scope: AnalyticsScope = {},
): Promise<{ hours: number; scope: ReadScope; items: GuardrailEvent[] }> {
  return authed<{ hours: number; scope: ReadScope; items: GuardrailEvent[] }>(
    withQuery("/api/v1/guardrails/events", {
      hours: clampHours(hours),
      limit: Math.min(500, Math.max(1, limit)),
      service: scope.service || undefined,
    }),
    { method: "GET" },
  )
}

export async function apiGuardrailCheck(text: string): Promise<GuardrailCheck> {
  return authed<GuardrailCheck>("/api/v1/guardrails/check", {
    method: "POST",
    body: JSON.stringify({ text }),
  })
}

// ---------------------------------------------------------------------------
// Knowledge base (app/api/v1/documents.py)
// ---------------------------------------------------------------------------

export interface DocumentItem {
  id: number
  filename: string
  content_type: string
  size_bytes: number
  status: "pending" | "ready" | "failed"
  error_message: string | null
  chunk_count: number
  character_count: number
  flagged: boolean
  flag_detail: string | null
  embedding_model: string | null
  owner_id: number | null
  created_at: string
}

export interface DocumentList {
  items: DocumentItem[]
  total: number
  vector_entries: number | null
  max_upload_mb: number
  supported_types: string[]
}

export interface SourceChunk {
  document_id: number
  filename: string
  position: number
  text: string
  similarity: number
  flagged: boolean
}

export interface KnowledgeAnswer {
  question: string
  answer: string
  insufficient_context: boolean
  sources: SourceChunk[]
  grounding_score: number
  model: string | null
  cached: boolean
  prompt_tokens: number
  completion_tokens: number
  estimated_cost_usd: number
  latency_ms: number
}

export async function apiDocuments(): Promise<DocumentList> {
  return authed<DocumentList>("/api/v1/documents", { method: "GET" })
}

/** Requires the admin or operator role. */
export async function apiUploadDocument(file: File): Promise<DocumentItem> {
  const form = new FormData()
  form.append("file", file, file.name)
  return authedUpload<DocumentItem>("/api/v1/documents", form)
}

/** Requires the admin or operator role. */
export async function apiDeleteDocument(id: number): Promise<{ message: string }> {
  return authed<{ message: string }>(`/api/v1/documents/${id}`, { method: "DELETE" })
}

export async function apiKnowledgeSearch(
  query: string,
  topK = 5,
): Promise<{ query: string; results: SourceChunk[] }> {
  return authed<{ query: string; results: SourceChunk[] }>("/api/v1/knowledge-base/search", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK }),
  })
}

export async function apiKnowledgeAsk(question: string, topK = 5): Promise<KnowledgeAnswer> {
  return authed<KnowledgeAnswer>("/api/v1/knowledge-base/ask", {
    method: "POST",
    body: JSON.stringify({ question, top_k: topK }),
  })
}

// ---------------------------------------------------------------------------
// Assistant (app/api/v1/assistant.py)
// ---------------------------------------------------------------------------

export interface AssistantAnswer {
  question: string
  answer: string | null
  llm_available: boolean
  llm_error: string | null
  tools_used: string[]
  facts: Record<string, Record<string, unknown>>
  sources: SourceChunk[]
  grounding_score: number
  model: string | null
  cached: boolean
  prompt_tokens: number
  completion_tokens: number
  estimated_cost_usd: number
  latency_ms: number
  guardrail_notes: string[]
}

export interface CacheRecommendation {
  endpoint: string
  kind: "cache" | "tune" | "do_not_cache" | "keep"
  title: string
  reason: string
  suggested_ttl_seconds: [number, number] | null
  evidence: Record<string, unknown>
  advisory: boolean
}

export interface CacheRecommendationReport {
  hours: number
  analysed_endpoints: number
  recommendations: CacheRecommendation[]
  explanation: string | null
  llm_available: boolean
  note: string
}

export interface TroubleshootInput {
  status_code?: number
  endpoint?: string
  symptom?: string
  hours?: number
  /** Monitored service to diagnose instead of this gateway. */
  service?: string
}

export interface TroubleshootReport {
  status_code: number | null
  endpoint: string | null
  symptom: string | null
  hours: number
  evidence: Record<string, Record<string, unknown>>
  known_causes: { cause: string; check: string }[]
  sources: SourceChunk[]
  explanation: string | null
  llm_available: boolean
  model: string | null
  estimated_cost_usd: number
}

export async function apiAssistantSuggestions(): Promise<{ questions: string[] }> {
  return authed<{ questions: string[] }>("/api/v1/assistant/suggested-questions", { method: "GET" })
}

export async function apiAssistantAsk(
  question: string,
  hours = 24,
  includeDocs = true,
  scope: AnalyticsScope = {},
): Promise<AssistantAnswer> {
  return authed<AssistantAnswer>("/api/v1/assistant/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      hours: clampHours(hours),
      include_docs: includeDocs,
      service: scope.service || undefined,
    }),
  })
}

export async function apiCacheRecommendations(
  hours = 24,
  narrative = true,
  scope: AnalyticsScope = {},
): Promise<CacheRecommendationReport> {
  return authed<CacheRecommendationReport>(
    withQuery("/api/v1/assistant/cache-recommendations", {
      hours: clampHours(hours),
      narrative: narrative ? "true" : "false",
      service: scope.service || undefined,
    }),
    { method: "GET" },
  )
}

export async function apiTroubleshoot(input: TroubleshootInput): Promise<TroubleshootReport> {
  return authed<TroubleshootReport>("/api/v1/assistant/troubleshoot", {
    method: "POST",
    body: JSON.stringify({ ...input, hours: clampHours(input.hours ?? 24) }),
  })
}

// ---------------------------------------------------------------------------
// Health (app/api/v1/health.py) — unauthenticated routes
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string
  version: string
  database: string
  redis: string
}

export async function apiHealth(): Promise<HealthResponse> {
  const res = await request("/api/v1/health", { method: "GET" })
  if (!res.ok) throw new ApiError(await readErrorMessage(res), res.status)
  return (await res.json()) as HealthResponse
}

/** Round-trip to GET /api/v1/ping, measured in the browser. */
export async function apiPing(): Promise<{ message: string; round_trip_ms: number }> {
  const started = performance.now()
  const res = await request("/api/v1/ping", { method: "GET" })
  const round_trip_ms = performance.now() - started
  if (!res.ok) throw new ApiError(await readErrorMessage(res), res.status)
  const data = (await res.json()) as { message: string }
  return { message: data.message, round_trip_ms }
}

// ---------------------------------------------------------------------------
// Answers history (app/api/v1/answers.py): what was asked, what was answered
// ---------------------------------------------------------------------------

export interface AnswerSourceRef {
  title: string
  url: string
  /** Provider the page came from: wikipedia | duckduckgo | wikidata | web. */
  source: string | null
}

/** One asked question and the answer it received. */
export interface AnswerLogItem {
  id: number
  created_at: string
  user_id: number | null
  /** End user of a monitored service (e.g. "esone:42"), when it passed one. */
  end_user: string | null
  correlation_id: string | null
  question: string
  answer: string
  /** ok | error | blocked */
  status: string
  error_code: string | null
  answered_by: "cache" | "model" | "crawler" | "none"
  /** False when no source had anything and the fixed "could not find" reply was returned. */
  found: boolean
  /** exact_hit | semantic_hit | miss | bypassed */
  cache_status: string
  match_method: string | null
  similarity: number | null
  compose_method: string | null
  primary_source: string | null
  sources: AnswerSourceRef[]
  cache_key: string | null
  latency_ms: number
  cache_lookup_ms: number
  embedding_ms: number
  crawl_ms: number | null
  llm_ms: number
  prompt_tokens: number
  completion_tokens: number
  embedding_tokens: number
  total_tokens: number
  llm_cost_usd: number
  embedding_cost_usd: number
  total_cost_usd: number
  estimated_cost_usd: number
  saved_cost_usd: number
  served_model: string | null
  waited_for_generation: boolean
  /** INR charged for this answer (0 for cache hits). */
  billable_tokens: number
  cost_inr: number
}

export interface AnswerLogPage {
  hours: number
  scope: ReadScope
  end_user: string | null
  cache_status: string | null
  /** The Redis list of the last hour, or the database for longer windows. */
  served_from: "redis" | "database"
  offset: number
  limit: number
  total: number
  items: AnswerLogItem[]
}

export interface TopQuestion {
  question: string
  question_hash: string
  asked: number
  cache_hits: number
  avg_latency_ms: number
  last_asked: string
  last_answer: string
}

export interface TopQuestionsPage {
  hours: number
  scope: ReadScope
  items: TopQuestion[]
}

export interface SourceCount {
  name: string
  count: number
}

export interface AnswerStats {
  hours: number
  scope: ReadScope
  end_user: string | null
  questions: number
  unique_questions: number
  end_users: number
  cache_hits: number
  exact_hits: number
  semantic_hits: number
  crawled: number
  not_found: number
  errors: number
  blocked: number
  bypassed: number
  cache_hit_rate: number
  avg_latency_ms: number
  avg_latency_cached_ms: number
  avg_latency_crawled_ms: number
  avg_cache_lookup_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  p99_latency_ms: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  embedding_tokens: number
  llm_cost_usd: number
  embedding_cost_usd: number
  total_cost_usd: number
  estimated_cost_usd: number
  saved_cost_usd: number
  cost_note: string
  cache_ttl_seconds: number
  recent_window_seconds: number
  by_source: SourceCount[]
  by_match: SourceCount[]
  by_model: SourceCount[]
}

/** Scope for the answer-history reads: a monitored service, optionally one of its end users. */
export interface AnswersScope extends AnalyticsScope {
  endUser?: string
  cacheStatus?: string
}

/** GET /api/v1/answers/cache: the shared cache right now plus its hit/miss record. */
export interface CacheOverview {
  hours: number
  scope: ReadScope
  redis_available: boolean
  active_entries: number
  stored_total: number
  expired_estimate: number
  bytes_used: number
  entries_scanned: number
  total_entry_hits: number
  oldest_entry_at: string | null
  ttl_seconds: number
  volatile_ttl_seconds: number
  similarity_threshold: number
  expiry_policy: string
  exact_hits: number
  semantic_hits: number
  misses: number
  bypassed: number
  cache_hit_rate: number
  avg_cache_lookup_ms: number
  avg_latency_hit_ms: number
  avg_latency_miss_ms: number
}

/** GET /api/v1/answers/costs: LLM vs embedding spend and estimated savings (estimates, not billing). */
export interface CostAnalytics {
  hours: number
  scope: ReadScope
  end_user: string | null
  currency: string
  pricing_effective_date: string
  cost_note: string
  llm_cost_usd: number
  embedding_cost_usd: number
  total_cost_usd: number
  saved_cost_usd: number
  prompt_tokens: number
  completion_tokens: number
  embedding_tokens: number
  total_tokens: number
  llm_calls_made: number
  llm_calls_avoided: number
  requests: number
  hits: number
  misses: number
  avg_cost_per_hit_usd: number
  avg_cost_per_miss_usd: number
  avg_latency_hit_ms: number
  avg_latency_miss_ms: number
  by_model: SourceCount[]
}

/** GET /api/v1/answers/users: one caller's totals. */
export interface UserQueryStats {
  user: string
  user_id: number | null
  end_user: string | null
  queries: number
  exact_hits: number
  semantic_hits: number
  misses: number
  bypassed: number
  errors: number
  llm_calls: number
  total_tokens: number
  embedding_tokens: number
  total_cost_usd: number
  saved_cost_usd: number
  avg_latency_ms: number
  last_seen: string
}

export interface UserQueryStatsPage {
  hours: number
  scope: ReadScope
  offset: number
  limit: number
  total: number
  cost_note: string
  items: UserQueryStats[]
}

export async function apiAnswersCache(hours = 24, scope: AnalyticsScope = {}): Promise<CacheOverview> {
  return authed<CacheOverview>(
    withQuery("/api/v1/answers/cache", { hours: clampHours(hours), service: scope.service || undefined }),
    { method: "GET" },
  )
}

export async function apiAnswersCosts(hours = 24, scope: AnswersScope = {}): Promise<CostAnalytics> {
  return authed<CostAnalytics>(
    withQuery("/api/v1/answers/costs", {
      hours: clampHours(hours),
      service: scope.service || undefined,
      end_user: scope.endUser || undefined,
    }),
    { method: "GET" },
  )
}

export async function apiAnswersUsers(hours = 24, limit = 50, offset = 0, scope: AnalyticsScope = {}): Promise<UserQueryStatsPage> {
  return authed<UserQueryStatsPage>(
    withQuery("/api/v1/answers/users", { hours: clampHours(hours), limit, offset, service: scope.service || undefined }),
    { method: "GET" },
  )
}

export async function apiAnswersRecent(hours = 1, limit = 50, scope: AnswersScope = {}, offset = 0): Promise<AnswerLogPage> {
  return authed<AnswerLogPage>(
    withQuery("/api/v1/answers/recent", {
      hours: clampHours(hours),
      limit,
      offset: offset || undefined,
      service: scope.service || undefined,
      end_user: scope.endUser || undefined,
      cache_status: scope.cacheStatus || undefined,
    }),
    { method: "GET" },
  )
}

export async function apiAnswersTop(hours = 24, limit = 10, scope: AnswersScope = {}): Promise<TopQuestionsPage> {
  return authed<TopQuestionsPage>(
    withQuery("/api/v1/answers/top", {
      hours: clampHours(hours),
      limit,
      service: scope.service || undefined,
      end_user: scope.endUser || undefined,
    }),
    { method: "GET" },
  )
}

export async function apiAnswersStats(hours = 24, scope: AnswersScope = {}): Promise<AnswerStats> {
  return authed<AnswerStats>(
    withQuery("/api/v1/answers/stats", {
      hours: clampHours(hours),
      service: scope.service || undefined,
      end_user: scope.endUser || undefined,
    }),
    { method: "GET" },
  )
}

// ---------------------------------------------------------------------------
// Admin user directory (app/api/v1/users.py). Admin only.
// ---------------------------------------------------------------------------

export type UserKind = "account" | "end_user"

export interface UserListItem {
  /** "account:<id>" or an end-user reference such as "esone:7"; pass it to apiUserDetail. */
  key: string
  kind: UserKind
  user_id: number | null
  end_user: string | null
  service: string | null
  username: string | null
  email: string | null
  role: string | null
  is_active: boolean | null
  created_at: string | null
  last_seen_at: string | null
  api_requests: number
  searches: number
  cache_hits: number
  total_tokens: number
  billable_tokens: number
  cost_inr: number
}

export interface UserListPage {
  hours: number
  total: number
  offset: number
  limit: number
  items: UserListItem[]
}

export interface UserProfile {
  key: string
  kind: UserKind
  user_id: number | null
  end_user: string | null
  service: string | null
  username: string | null
  email: string | null
  role: string | null
  is_active: boolean | null
  created_at: string | null
  last_seen_at: string | null
}

export interface UserBilling {
  currency: string
  rate_per_token: number
  billable_tokens: number
  cost_inr: number
  paid_answers: number
  free_answers: number
}

export interface UserDetail {
  hours: number
  profile: UserProfile
  /** What is not available for this kind of user, in plain words. */
  notes: string[]
  traffic: AnalyticsSummary | null
  rate_limit: RateLimitUsage | null
  answers: AnswerStats
  recent_answers: AnswerLogItem[]
  billing: UserBilling
  ai_usage: AIUsageSummary | null
  ai_calls: AIRequestLogItem[]
  guardrails: GuardrailSummary | null
  guardrail_events: GuardrailEvent[]
}

export async function apiUsers(
  query: { hours?: number; search?: string; kind?: UserKind } = {},
): Promise<UserListPage> {
  return authed<UserListPage>(
    withQuery("/api/v1/users", {
      hours: query.hours === undefined ? undefined : clampHours(query.hours),
      search: query.search?.trim() || undefined,
      kind: query.kind,
      limit: 500,
    }),
    { method: "GET" },
  )
}

export async function apiUserDetail(key: string, hours = 720): Promise<UserDetail> {
  return authed<UserDetail>(withQuery("/api/v1/users/detail", { key, hours: clampHours(hours) }), { method: "GET" })
}
