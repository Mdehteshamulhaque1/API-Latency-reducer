import { Reveal } from "@/components/motion/reveal"
import { cn } from "@/lib/utils"

type Tone = "indigo" | "violet" | "cyan" | "sky" | "emerald" | "rose"

const TONE_STICKER: Record<Tone, string> = {
  indigo: "border-accent-indigo/50 text-indigo-200",
  violet: "border-violet-400/50 text-violet-200",
  cyan: "border-accent-cyan/50 text-cyan-200",
  sky: "border-sky-400/50 text-sky-200",
  emerald: "border-ok/50 text-emerald-200",
  rose: "border-rose-400/50 text-rose-200",
}

const TONE_DOT: Record<Tone, string> = {
  indigo: "bg-accent-indigo",
  violet: "bg-violet-400",
  cyan: "bg-accent-cyan",
  sky: "bg-sky-400",
  emerald: "bg-ok",
  rose: "bg-rose-400",
}

const TONE_GLOW: Record<Tone, string> = {
  indigo: "bg-[radial-gradient(closest-side,rgba(99,102,241,0.16),transparent)]",
  violet: "bg-[radial-gradient(closest-side,rgba(167,139,250,0.16),transparent)]",
  cyan: "bg-[radial-gradient(closest-side,rgba(34,211,238,0.16),transparent)]",
  sky: "bg-[radial-gradient(closest-side,rgba(56,189,248,0.16),transparent)]",
  emerald: "bg-[radial-gradient(closest-side,rgba(52,211,153,0.16),transparent)]",
  rose: "bg-[radial-gradient(closest-side,rgba(251,113,133,0.16),transparent)]",
}

interface SectionHeadingProps {
  eyebrow: string
  title: React.ReactNode
  description?: string
  align?: "left" | "center"
  tone?: Tone
  className?: string
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "center",
  tone = "indigo",
  className,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "relative flex flex-col gap-4",
        align === "center" && "items-center text-center",
        className,
      )}
    >
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute -top-10 left-1/2 h-44 w-[min(92vw,44rem)] -translate-x-1/2 rounded-full blur-[80px]",
          TONE_GLOW[tone],
        )}
      />
      <Reveal>
        <span
          className={cn(
            "inline-flex items-center gap-2.5 rounded-md border-2 bg-surface px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] shadow-[3px_3px_0_0_rgba(231,231,234,0.85)]",
            TONE_STICKER[tone],
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", TONE_DOT[tone])} />
          {eyebrow}
        </span>
      </Reveal>
      <Reveal delay={0.08}>
        <h2 className="max-w-2xl text-balance text-[clamp(1.9rem,4vw,3.25rem)] font-bold tracking-[-0.03em] text-zinc-50">
          {title}
        </h2>
      </Reveal>
      {description && (
        <Reveal delay={0.16}>
          <p className="max-w-xl text-pretty text-[15px] leading-relaxed text-dim">
            {description}
          </p>
        </Reveal>
      )}
    </div>
  )
}
