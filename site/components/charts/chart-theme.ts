/**
 * Shared chart tokens for the light instrument surface (#FFFFFF panels).
 * Series colors follow the product's state rule: signal orange only for
 * latency tails and errors, relay green only for cache hits, steel for the
 * neutral series.
 */
export const CHART = {
  surface: "#FFFFFF",
  grid: "#E3E8ED",
  axis: "#7A8591",
  cursor: "#AEB7C2",
  /** Latency series: avg / p95 / p99 (fixed order, never cycled). */
  avg: "#2F5D8A",
  p95: "#E4572E",
  p99: "#141B22",
  /** Cache split. */
  hit: "#1F8A5B",
  miss: "#C5CDD6",
  /** Traffic split. */
  ok: "#2F5D8A",
  error: "#E4572E",
} as const

export const TOOLTIP_STYLE = {
  background: "#FFFFFF",
  border: "1px solid #141B22",
  borderRadius: 2,
  fontSize: 12,
  padding: "8px 10px",
  boxShadow: "none",
} as const

export const TOOLTIP_LABEL_STYLE = { color: "#5B6672", marginBottom: 4 } as const
export const TOOLTIP_ITEM_STYLE = { color: "#141B22", padding: 0 } as const

export const AXIS_TICK = { fill: CHART.axis, fontSize: 11, fontFamily: "var(--font-mono)" } as const

export function msTick(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(1)}s` : `${Math.round(value)}ms`
}
