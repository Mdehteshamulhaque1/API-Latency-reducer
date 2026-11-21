import * as React from "react"

import { cn } from "@/lib/utils"

/** Tone names kept from the previous design; they map to state colors. */
type StatTone = "indigo" | "cyan" | "emerald" | "amber"

const TONE_TEXT: Record<StatTone, string> = {
  indigo: "text-ink",
  cyan: "text-ink",
  emerald: "text-relay",
  amber: "text-warn",
}

interface StatCardProps {
  label: string
  value: React.ReactNode
  hint?: string
  tone?: StatTone
  icon?: React.ReactNode
  className?: string
}

/**
 * One readout. Place several inside a `.housing housing-row` wrapper so they
 * share one frame and are divided by rules, like a bank of gauges.
 */
export function StatCard({ label, value, hint, tone = "indigo", icon, className }: StatCardProps) {
  return (
    <div className={cn("min-w-0 bg-paper px-5 py-4", className)}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-[12px] text-graphite">{label}</p>
        {icon && <span className="text-faint">{icon}</span>}
      </div>
      <p className={cn("mt-2 font-mono text-[28px] font-medium leading-none tracking-tight", TONE_TEXT[tone])}>{value}</p>
      {hint && <p className="mt-2 text-[12px] text-faint">{hint}</p>}
    </div>
  )
}
