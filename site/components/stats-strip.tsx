"use client"

import { CountUp } from "@/components/motion/count-up"
import { Reveal } from "@/components/motion/reveal"

const STATS = [
  { value: 128.4, decimals: 1, suffix: "k", label: "requests optimized" },
  { value: 43, suffix: "%", label: "avg latency reduction" },
  { value: 72, suffix: "%", label: "cache hit rate" },
  { value: 99.9, decimals: 1, suffix: "%", label: "uptime" },
]

export function StatsStrip() {
  return (
    <section className="relative border-y border-white/[0.07] bg-surface/60">
      <Reveal>
        <div className="container grid grid-cols-2 divide-x divide-white/[0.07] md:grid-cols-4">
          {STATS.map((s) => (
            <div
              key={s.label}
              className="flex flex-col gap-1.5 px-6 py-7 sm:items-start sm:text-left"
            >
              <span className="font-mono text-[clamp(1.5rem,3vw,2.25rem)] font-extrabold tabular-nums text-zinc-50 sm:text-[26px]">
                <CountUp
                  value={s.value}
                  decimals={s.decimals ?? 0}
                  suffix={s.suffix}
                />
              </span>
              <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-faint">
                {s.label}
              </span>
            </div>
          ))}
        </div>
      </Reveal>
    </section>
  )
}
