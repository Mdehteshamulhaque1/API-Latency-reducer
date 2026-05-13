import apiClient from './api'

export interface RecentRequest {
  endpoint: string
  method: string
  status_code: number
  response_time_ms: number
  cache_hit: boolean
  created_at: string
}

export interface LatencyPoint {
  timestamp: string
  avg_response_time_ms: number
  request_count: number
  error_count: number
}

export interface OptimizationSuggestion {
  title: string
  severity: 'low' | 'medium' | 'high'
  endpoint?: string | null
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
  cache_hit_rate: number
  cache_miss_rate: number
  avg_response_time_ms: number
  slowest_endpoint: string | null
  slowest_response_time_ms: number | null
  request_rate_per_minute: number
  error_rate: number
  top_endpoints: Array<{
    endpoint: string
    count: number
    avg_time: number
    errors: number
    cache_hit_rate?: number
  }>
  recent_requests: RecentRequest[]
  latency_series: LatencyPoint[]
  slow_endpoints: Array<{
    endpoint: string
    count: number
    avg_time: number
    errors: number
    cache_hit_rate?: number
  }>
  optimization_suggestions: OptimizationSuggestion[]
  benchmark?: BenchmarkReport | null
}

export interface CacheRule {
  id: number
  endpoint_pattern: string
  ttl: number
  enabled: boolean
  cache_by_user: boolean
  cache_by_query_params: boolean
  cache_by_headers: boolean
  max_cache_size: number
  priority: number
  description?: string
  created_at: string
  updated_at: string
}

export interface APILog {
  id: number
  method: string
  endpoint: string
  status_code: number
  response_time_ms: number
  cache_hit: boolean
  client_ip: string
  correlation_id: string
  created_at: string
}

export const analyticsService = {
  getSummary: async (hours: number = 24) => {
    const response = await apiClient.get<AnalyticsSummary>('/api/v1/analytics/summary', {
      params: { hours },
    })
    return response.data
  },

  getEndpointLogs: async (endpoint: string, limit: number = 100, hours: number = 24) => {
    const response = await apiClient.get<APILog[]>('/api/v1/analytics/endpoints', {
      params: { endpoint_pattern: endpoint, limit, hours },
    })
    return response.data
  },

  getBenchmarkReport: async (hours: number = 24) => {
    const response = await apiClient.get<BenchmarkReport>('/api/v1/analytics/benchmark', {
      params: { hours },
    })
    return response.data
  },

  runBenchmarkReport: async (hours: number = 24) => {
    const response = await apiClient.post<{
      status: string
      hours: number
      report: BenchmarkReport
    }>('/api/v1/analytics/benchmark/run', undefined, {
      params: { hours },
    })
    return response.data
  },

  getOptimizationSuggestions: async (hours: number = 24) => {
    const response = await apiClient.get<OptimizationSuggestion[]>('/api/v1/analytics/suggestions', {
      params: { hours },
    })
    return response.data
  },
}

export const rulesService = {
  listRules: async (skip: number = 0, limit: number = 100) => {
    const response = await apiClient.get<CacheRule[]>('/api/v1/rules', {
      params: { skip, limit },
    })
    return response.data
  },

  getRule: async (id: number) => {
    const response = await apiClient.get<CacheRule>(`/api/v1/rules/${id}`)
    return response.data
  },

  createRule: async (data: Partial<CacheRule>) => {
    const response = await apiClient.post<CacheRule>('/api/v1/rules', data)
    return response.data
  },

  updateRule: async (id: number, data: Partial<CacheRule>) => {
    const response = await apiClient.put<CacheRule>(`/api/v1/rules/${id}`, data)
    return response.data
  },

  deleteRule: async (id: number) => {
    await apiClient.delete(`/api/v1/rules/${id}`)
  },
}
