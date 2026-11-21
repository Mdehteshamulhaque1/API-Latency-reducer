import * as React from "react"

import { cn } from "@/lib/utils"

/** Scroll wrapper + table with ruled rows. */
export function Table({
  className,
  minWidth = 560,
  ...props
}: React.TableHTMLAttributes<HTMLTableElement> & { minWidth?: number }) {
  return (
    <div className="overflow-x-auto">
      <table className={cn("w-full text-left text-sm", className)} style={{ minWidth }} {...props} />
    </div>
  )
}

export function THead({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn("bg-frost/60", className)} {...props} />
}

export function TBody({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn("divide-y divide-rule", className)} {...props} />
}

export function TR({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("transition-colors hover:bg-frost/50", className)} {...props} />
}

export function TH({
  className,
  align = "left",
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement> & { align?: "left" | "right" }) {
  return (
    <th
      className={cn(
        "border-b border-rule px-4 py-2.5 text-[12px] font-medium text-graphite first:pl-5 last:pr-5",
        align === "right" && "text-right",
        className,
      )}
      {...props}
    />
  )
}

export function TD({
  className,
  align = "left",
  mono,
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement> & { align?: "left" | "right"; mono?: boolean }) {
  return (
    <td
      className={cn(
        "px-4 py-2.5 text-ink first:pl-5 last:pr-5",
        mono && "font-mono text-[13px]",
        align === "right" && "text-right",
        className,
      )}
      {...props}
    />
  )
}
