import * as React from "react"

import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface PanelProps {
  title: string
  description?: string
  icon?: React.ReactNode
  actions?: React.ReactNode
  /** Remove body padding (for tables and lists that run edge to edge). */
  flush?: boolean
  className?: string
  children: React.ReactNode
}

/** Ruled panel with a header row: title, description, right-side actions. */
export function Panel({ title, description, icon, actions, flush, className, children }: PanelProps) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <div className="flex items-start justify-between gap-3 border-b border-rule px-5 py-3.5">
        <div className="flex min-w-0 items-start gap-2.5">
          {icon && <span className="mt-0.5 shrink-0 text-graphite">{icon}</span>}
          <div className="min-w-0">
            <h2 className="font-sans text-sm font-medium text-ink">{title}</h2>
            {description && <p className="mt-0.5 text-[12px] text-graphite">{description}</p>}
          </div>
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      <div className={cn(!flush && "p-5")}>{children}</div>
    </Card>
  )
}
