export function formatMs(ms) {
  if (ms == null) return '—'
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.round(ms)}ms`
}

export function formatNumber(n) {
  if (n == null) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return String(n)
}

export function formatPercent(n, decimals = 1) {
  if (n == null) return '0%'
  return `${n.toFixed(decimals)}%`
}

export function formatTimestamp(iso, opts = { hour: '2-digit', minute: '2-digit' }) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 16).replace('T', ' ')
  return d.toLocaleString('en-US', opts)
}

export function severityTone(severity) {
  if (severity === 'high') return 'red'
  if (severity === 'medium') return 'amber'
  return 'green'
}
