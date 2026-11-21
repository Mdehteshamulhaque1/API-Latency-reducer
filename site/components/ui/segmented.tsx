"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

export interface SegmentedOption<T extends string | number> {
  value: T
  label: string
}

interface SegmentedProps<T extends string | number> {
  value: T
  onChange: (value: T) => void
  options: ReadonlyArray<SegmentedOption<T>>
  ariaLabel: string
  className?: string
  disabled?: boolean
}

export function Segmented<T extends string | number>({
  value,
  onChange,
  options,
  ariaLabel,
  className,
  disabled,
}: SegmentedProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn("inline-flex items-stretch overflow-hidden rounded border border-rule-strong bg-paper", className)}
    >
      {options.map((option, index) => {
        const active = option.value === value
        return (
          <button
            key={String(option.value)}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(option.value)}
            className={cn(
              "px-2.5 py-1 font-mono text-[12px] transition-colors disabled:cursor-not-allowed disabled:opacity-50",
              index > 0 && "border-l border-rule",
              active ? "bg-ink text-paper" : "text-graphite hover:bg-frost hover:text-ink",
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

/** Analytics window presets mapped to the backend `hours` query (1..720). */
export const RANGE_OPTIONS: ReadonlyArray<SegmentedOption<number>> = [
  { value: 1, label: "1h" },
  { value: 6, label: "6h" },
  { value: 24, label: "24h" },
  { value: 168, label: "7d" },
  { value: 720, label: "30d" },
]

export function rangeLabel(hours: number): string {
  return RANGE_OPTIONS.find((option) => option.value === hours)?.label ?? `${hours}h`
}
