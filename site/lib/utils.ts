import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Coerce an unknown API value to a finite number. */
export function num(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback
}

/** 12.3ms · 1.20s */
export function formatMs(ms: number, digits = 1): string {
  if (!Number.isFinite(ms)) return "—"
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`
  return `${ms.toFixed(digits)}ms`
}

export function formatPercent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return "—"
  return `${value.toFixed(digits)}%`
}

/** 3600 -> "1h", 90 -> "1m 30s", 0 -> "0s" */
export function formatSeconds(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "—"
  if (seconds === 0) return "0s"
  const parts: string[] = []
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  if (days) parts.push(`${days}d`)
  if (hours) parts.push(`${hours}h`)
  if (minutes) parts.push(`${minutes}m`)
  if (secs && parts.length < 2) parts.push(`${secs}s`)
  return parts.slice(0, 2).join(" ")
}

/** Parse a backend timestamp that may lack a timezone (treated as UTC). */
export function parseUtc(value: string | number | Date): Date {
  if (typeof value !== "string") return new Date(value)
  const hasZone = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(value)
  return new Date(hasZone ? value : `${value}Z`)
}

export function formatTime(value: string | number | Date): string {
  const date = parseUtc(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
}

export function formatDateTime(value: string | number | Date): string {
  const date = parseUtc(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

/** "just now", "4m ago", "3h ago", "2d ago" */
export function formatRelative(value: string | number | Date, now: number = Date.now()): string {
  const date = parseUtc(value)
  if (Number.isNaN(date.getTime())) return "—"
  const diff = Math.max(0, now - date.getTime())
  const seconds = Math.floor(diff / 1000)
  if (seconds < 45) return "just now"
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 48) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}
