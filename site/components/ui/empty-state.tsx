import * as React from "react"

import { cn } from "@/lib/utils"

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  body?: string
  action?: React.ReactNode
  className?: string
  /** Compact variant for inside table panels. */
  compact?: boolean
}

export function EmptyState({ icon, title, body, action, className, compact }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        compact ? "px-5 py-8" : "rounded border border-dashed border-rule-strong px-6 py-12",
        className,
      )}
    >
      {icon && (
        <span className="mb-3 flex h-10 w-10 items-center justify-center rounded border border-rule text-graphite">
          {icon}
        </span>
      )}
      <p className="text-sm font-medium text-ink">{title}</p>
      {body && <p className="mt-1 max-w-sm text-[13px] leading-relaxed text-graphite">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
