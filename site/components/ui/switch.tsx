"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

interface SwitchProps {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  disabled?: boolean
  label?: string
  className?: string
  id?: string
}

export function Switch({ checked, onCheckedChange, disabled, label, className, id }: SwitchProps) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
        checked ? "border-ink bg-ink" : "border-rule-strong bg-frost",
        className,
      )}
    >
      <span
        className={cn(
          "inline-block h-3.5 w-3.5 rounded-full transition-transform",
          checked ? "translate-x-[18px] bg-paper" : "translate-x-[3px] bg-graphite",
        )}
      />
    </button>
  )
}
