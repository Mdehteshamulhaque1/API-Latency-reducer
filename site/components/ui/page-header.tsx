import * as React from "react"

import { cn } from "@/lib/utils"

interface PageHeaderProps {
  /** Kept for compatibility; no longer rendered. The sidebar already names the section. */
  eyebrow?: string
  title: string
  description?: string
  actions?: React.ReactNode
  className?: string
}

export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-rule-strong pb-5", className)}>
      <div>
        <h1 className="text-[28px] font-semibold leading-tight tracking-[-0.01em] text-ink">{title}</h1>
        {description && <p className="mt-1.5 max-w-xl text-sm text-graphite">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
