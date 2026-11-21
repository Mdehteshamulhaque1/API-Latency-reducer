import { cn } from "@/lib/utils"

/**
 * Mark: a latency trace that drops to a flat line, drawn in ink inside a
 * ruled square. The flat segment is the point of the product.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded border border-ink bg-paper", className)}
      aria-hidden
    >
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
        <path d="M3 15 7 7l3 10 3-6 2 3h6" className="text-ink" />
      </svg>
    </span>
  )
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5 text-ink", className)}>
      <LogoMark />
      <span className="font-display text-[15px] font-semibold tracking-[-0.01em]">API Optimizer</span>
    </span>
  )
}
