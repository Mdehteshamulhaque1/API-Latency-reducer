import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded border font-mono text-[11px] leading-5 tracking-wide",
  {
    variants: {
      variant: {
        live: "border-ok/30 bg-ok/[0.08] text-ok",
        accent: "border-accent-indigo/30 bg-accent-indigo/[0.12] text-indigo-300",
        neutral: "border-white/10 bg-white/[0.04] text-zinc-400",
      },
      size: {
        sm: "px-1.5 py-px",
        md: "px-2 py-0.5",
      },
    },
    defaultVariants: {
      variant: "neutral",
      size: "md",
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, size }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
