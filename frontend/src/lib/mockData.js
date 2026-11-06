/* Deterministic demo data used when the FastAPI backend is not reachable,
   so the dashboard is always presentable. */

const pad = (n) => String(n).padStart(2, '0')
const iso = (d) => d.toISOString()

function buildLatencySeries(hours = 24) {
  const points = []
  const buckets = Math.max(6, Math.min(12, hours))
  const bucketMinutes = Math.max(30, Math.round((hours * 60) / buckets))
  const now = new Date()
  let base = 160
  for (let i = buckets; i >= 1; i--) {
    const t = new Date(now.getTime() - i * bucketMinutes * 60 * 1000)
    const wave = Math.sin(i * 1.7) * 45 + Math.cos(i * 0.6) * 20
    base = Math.max(40, base + wave * 0.5 + (i % 3) * 6)
    points.push({
      timestamp: iso(t),
      avg_response_time_ms: Math.round(base),
      request_count: 40 + ((i * 37) % 260),
      error_count: (i * 11) % 7,
    })
  }
  return points
}

function buildDistribution(hours = 24) {
  const buckets = Math.max(6, Math.min(12, hours))
  const bucketMinutes = Math.max(30, Math.round((hours * 60) / buckets))
  const now = new Date()
  const out = []
  let base = 140
  for (let i = buckets; i >= 1; i--) {
    const t = new Date(now.getTime() - i * bucketMinutes * 60 * 1000)
    base = Math.max(50, base + Math.sin(i * 2.2) * 30 - 8)
    out.push({
      timestamp: iso(t),
      avg_response_time_ms: Math.round(base),
      p95_response_time_ms: Math.round(base * 1.75),
      p99_response_time_ms: Math.round(base * 2.4),
      request_count: 40 + ((i * 29) % 240),
      error_count: (i * 13) % 6,
    })
  }
  return out
}

export function mockSummary(hours = 24) {
  const totalRequests = 128400 + (hours % 13) * 740
  const totalErrors = Math.round(totalRequests * 0.021)
  const cacheHits = Math.round(totalRequests * 0.72)
  const series = buildLatencySeries(hours)
  return {
    total_requests: totalRequests,
    total_errors: totalErrors,
    cache_hit_rate: 72.4,
    avg_response_time_ms: 148,
    slowest_endpoint: '/api/v1/analytics/summary',
    slowest_response_time_ms: 1240,
    error_rate: 2.1,
    request_rate_per_minute: 92.5,
    cache_miss_rate: 27.6,
    top_endpoints: [
      { endpoint: '/api/v1/analytics/summary', count: 43120, avg_time: 142, errors: 512, cache_hit_rate: 86.2 },
      { endpoint: '/api/v1/rules', count: 28410, avg_time: 96, errors: 89, cache_hit_rate: 91.4 },
      { endpoint: '/api/v1/auth/refresh', count: 19220, avg_time: 74, errors: 31, cache_hit_rate: 0 },
      { endpoint: '/api/v1/health', count: 15080, avg_time: 12, errors: 0, cache_hit_rate: 0 },
      { endpoint: '/api/v1/analytics/benchmark', count: 9210, avg_time: 310, errors: 44, cache_hit_rate: 58.1 },
      { endpoint: '/api/v1/analytics/slow-endpoints', count: 6870, avg_time: 402, errors: 96, cache_hit_rate: 44.3 },
    ],
    recent_requests: Array.from({ length: 10 }, (_, i) => ({
      endpoint: ['/api/v1/analytics/summary', '/api/v1/rules', '/api/v1/health', '/api/v1/auth/refresh', '/api/v1/analytics/slow-endpoints'][i % 5],
      method: i % 3 === 0 ? 'POST' : 'GET',
      status_code: i === 7 ? 429 : 200,
      response_time_ms: 12 + ((i * 47) % 480),
      cache_hit: i % 3 !== 0,
      created_at: iso(new Date(Date.now() - i * 64000)),
    })),
    latency_series: series,
    latency_distribution: buildDistribution(hours),
    slow_endpoint_ranking: [
      { endpoint: '/api/v1/analytics/summary', count: 43120, avg_time: 142, p95_time: 610, p99_time: 1120, errors: 512, cache_hit_rate: 86.2, error_rate: 1.2 },
      { endpoint: '/api/v1/analytics/benchmark', count: 9210, avg_time: 310, p95_time: 980, p99_time: 1870, errors: 44, cache_hit_rate: 58.1, error_rate: 0.5 },
      { endpoint: '/api/v1/analytics/slow-endpoints', count: 6870, avg_time: 402, p95_time: 1240, p99_time: 2210, errors: 96, cache_hit_rate: 44.3, error_rate: 1.4 },
    ],
    slow_endpoints: [
      { endpoint: '/api/v1/analytics/benchmark', count: 9210, avg_time: 310, errors: 44, cache_hit_rate: 58.1 },
      { endpoint: '/api/v1/analytics/slow-endpoints', count: 6870, avg_time: 402, errors: 96, cache_hit_rate: 44.3 },
    ],
    optimization_suggestions: [
      {
        title: 'Increase cache coverage',
        severity: 'high',
        reason: 'Cache hit rate is 72.4% across 128,400 requests.',
        action: 'Apply route-wise caching to high-traffic GET endpoints and warm them on startup.',
      },
      {
        title: 'Cache slow responses',
        severity: 'high',
        endpoint: '/api/v1/analytics/benchmark',
        reason: '/api/v1/analytics/benchmark has a p95 latency of 980ms and low cache hit rate.',
        action: 'Cache repeated GET responses and apply a tighter caching policy for the slowest endpoints.',
      },
      {
        title: 'Reduce average latency',
        severity: 'medium',
        reason: 'Average response time is 148ms.',
        action: 'Move expensive work to background tasks and reduce synchronous database work.',
      },
      {
        title: 'Harden error handling',
        severity: 'medium',
        reason: 'Error rate is 2.10%.',
        action: 'Add retries for transient upstream calls and normalize exception responses.',
      },
    ],
    benchmark: {
      baseline_avg_response_time_ms: 214,
      optimized_avg_response_time_ms: 148,
      improvement_percent: 30.8,
      sample_size: 128400,
      before_window: 'yesterday 00:00 -> today 12:00',
      after_window: 'today 12:00 -> now',
    },
  }
}

export const mockRules = [
  { id: 1, endpoint_pattern: '/api/v1/analytics', ttl: 300, enabled: true, cache_by_user: false, cache_by_query_params: true, cache_by_headers: false, max_cache_size: 1000, priority: 10, description: 'Hot analytics routes, short TTL' },
  { id: 2, endpoint_pattern: '/api/v1/rules', ttl: 600, enabled: true, cache_by_user: false, cache_by_query_params: true, cache_by_headers: false, max_cache_size: 500, priority: 8, description: 'Rule listings are mostly static' },
  { id: 3, endpoint_pattern: '/api/v1/health', ttl: 30, enabled: true, cache_by_user: false, cache_by_query_params: false, cache_by_headers: false, max_cache_size: 100, priority: 20, description: 'Fresh health signal' },
  { id: 4, endpoint_pattern: '/api/v1/users', ttl: 60, enabled: false, cache_by_user: true, cache_by_query_params: true, cache_by_headers: false, max_cache_size: 1000, priority: 5, description: 'User-specific payloads, per-user cache' },
]

export const mockHealth = {
  status: 'healthy',
  version: '1.0.0',
  database: 'healthy',
  redis: 'healthy',
}
