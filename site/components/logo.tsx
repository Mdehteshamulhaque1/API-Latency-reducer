import { cn } from "@/lib/utils"

/** Custom mark: a bolt/signal drawn as strokes inside a rounded square. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "relative flex h-8 w-8 items-center justify-center rounded-lg border border-white/15 bg-gradient-to-br from-accent-indigo/25 to-accent-cyan/10",
        className,
      )}
    >
      <svg
        viewBox="0 0 24 24"
        className="h-4 w-4"
        fill="none"
        stroke="url(#logo-grad)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <defs>
          <linearGradient id="logo-grad" x1="0" y1="0" x2="24" y2="24">
            <stop stopColor="#818CF8" />
            <stop offset="1" stopColor="#22D3EE" />
          </linearGradient>
        </defs>
        <path d="M13 2 4.5 13.5H11L9.5 22 19 10h-6.5L13 2Z" />
      </svg>
      <span className="absolute inset-0 rounded-lg ring-1 ring-inset ring-white/5" />
    </div>
  )
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark />
      <span className="text-[15px] font-semibold tracking-[-0.02em] text-zinc-100">
        API Optimizer
      </span>
    </span>
  )
}
