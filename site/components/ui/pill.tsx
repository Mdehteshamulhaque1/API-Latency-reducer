import * as React from "react"

import { cn } from "@/lib/utils"

/**
 * Tone names are kept from the previous design so call sites still compile;
 * they now map onto the four state colors (relay, warn, signal, steel) plus
 * a neutral.
 */
export type PillTone = "emerald" | "amber" | "red" | "indigo" | "cyan" | "zinc"

const TONES: Record<PillTone, string> = {
  emerald: "border-relay/40 text-relay",
  amber: "border-warn/40 text-warn",
  red: "border-signal/40 text-signal",
  indigo: "border-steel/40 text-steel",
  cyan: "border-steel/40 text-steel",
  zinc: "border-rule-strong text-graphite",
}

const DOTS: Record<PillTone, string> = {
  emerald: "bg-relay",
  amber: "bg-warn",
  red: "bg-signal",
  indigo: "bg-steel",
  cyan: "bg-steel",
  zinc: "bg-rule-strong",
}

interface PillProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: PillTone
  dot?: boolean
}

/** Small outlined status chip: "enabled", "hit", "healthy", "200". */
export function Pill({ tone = "zinc", dot, className, children, ...props }: PillProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded border bg-paper px-1.5 py-px font-mono text-[11px] leading-5",
        TONES[tone],
        className,
      )}
      {...props}
    >
      {dot && <span className={cn("h-1.5 w-1.5 rounded-full", DOTS[tone])} />}
      {children}
    </span>
  )
}

export function MethodPill({ method }: { method: string }) {
  const upper = method.toUpperCase()
  const tone: PillTone = upper === "DELETE" ? "red" : upper === "GET" ? "zinc" : "indigo"
  return <Pill tone={tone}>{upper}</Pill>
}

export function StatusCodePill({ status }: { status: number }) {
  const tone: PillTone = status >= 500 ? "red" : status >= 400 ? "amber" : "emerald"
  return <Pill tone={tone}>{status}</Pill>
}
