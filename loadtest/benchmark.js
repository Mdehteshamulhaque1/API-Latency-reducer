/*
 * k6 load-test benchmark: cache OFF vs ON against the demo latency endpoint.
 *
 * Usage:
 *   k6 run loadtest/benchmark.js                 # cache ON  (default)
 *   CACHE=off k6 run loadtest/benchmark.js       # cache OFF
 *
 * The demo rule for /api/v1/demo/latency is toggled in setup() so both runs
 * use an identical load profile; only the cache flag differs. teardown()
 * restores the rule to its enabled state.
 *
 * Env vars (optional):
 *   BASE_URL   base URL incl. /api/v1   (default http://127.0.0.1:8000/api/v1)
 *   CACHE      "on" | "off"             (default "on")
 *   VUS        concurrent virtual users (default 20)
 *   DURATION   test duration            (default "30s")
 *   SLEEP      per-iteration sleep      (default 0.1)
 *   ADMIN_USER / ADMIN_PASS             (default admin / Admin@123)
 */
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Counter, Rate } from 'k6/metrics'

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000/api/v1'
const CACHE_MODE = (__ENV.CACHE || 'on').toLowerCase()
const ADMIN_USER = __ENV.ADMIN_USER || 'admin'
const ADMIN_PASS = __ENV.ADMIN_PASS || 'Admin@123'
const SLEEP_SEC = Number(__ENV.SLEEP || 0.1)

const cacheHits = new Counter('cache_hits')
const cacheMisses = new Counter('cache_misses')
const cacheHitRate = new Rate('cache_hit_rate')

export const options = {
  scenarios: {
    load: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 20),
      duration: __ENV.DURATION || '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
  },
}

export function setup() {
  const login = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ username: ADMIN_USER, password: ADMIN_PASS }),
    { headers: { 'Content-Type': 'application/json' } }
  )
  check(login, { 'admin login ok': (r) => r.status === 200 })
  const tokens = login.json()
  const authHeaders = {
    Authorization: `Bearer ${tokens.access_token}`,
    'Content-Type': 'application/json',
  }

  const rules = http.get(`${BASE_URL}/rules`, { headers: authHeaders }).json()
  const demoRule = rules.find((r) => (r.endpoint_pattern || '').includes('/demo/latency'))
  if (!demoRule) {
    throw new Error('No cache rule for /api/v1/demo/latency found. Create it (see README) before benchmarking.')
  }

  const enabled = CACHE_MODE === 'on'
  const toggle = http.put(
    `${BASE_URL}/rules/${demoRule.id}`,
    JSON.stringify({ enabled }),
    { headers: authHeaders }
  )
  check(toggle, { 'cache rule toggled': (r) => r.status === 200 })

  return { demoRuleId: demoRule.id, mode: CACHE_MODE }
}

export default function () {
  const res = http.get(`${BASE_URL}/demo/latency`)
  check(res, { 'status 200': (r) => r.status === 200 })

  const hit = (res.headers['X-Cache-Hit'] || res.headers['x-cache-hit'] || '') === 'true'
  if (hit) {
    cacheHits.add(1)
    cacheHitRate.add(true)
  } else {
    cacheMisses.add(1)
    cacheHitRate.add(false)
  }

  if (SLEEP_SEC > 0) sleep(SLEEP_SEC)
}

export function teardown(data) {
  if (!data || !data.demoRuleId) return
  const login = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ username: ADMIN_USER, password: ADMIN_PASS }),
    { headers: { 'Content-Type': 'application/json' } }
  )
  const tokens = login.json()
  http.put(
    `${BASE_URL}/rules/${data.demoRuleId}`,
    JSON.stringify({ enabled: true }),
    { headers: { Authorization: `Bearer ${tokens.access_token}`, 'Content-Type': 'application/json' } }
  )
}
