import * as React from "react"

import { cn } from "@/lib/utils"

type AlertVariant = "default" | "destructive" | "success"

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant
}

/** Inline notice. The left rule carries the state color; the text stays ink. */
export const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = "default", ...props }, ref) => (
    <div
      ref={ref}
      role="alert"
      className={cn(
        "rounded border border-rule border-l-2 bg-paper px-3.5 py-2.5 text-sm leading-relaxed text-ink",
        variant === "destructive" && "border-l-signal",
        variant === "success" && "border-l-relay",
        variant === "default" && "border-l-steel",
        className,
      )}
      {...props}
    />
  ),
)
Alert.displayName = "Alert"
