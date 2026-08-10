"use client"

import { motion } from "framer-motion"
import { ArrowDownRight, ArrowUpRight, Database, TrendingUp } from "lucide-react"

import { CountUp } from "@/components/motion/count-up"
import { Reveal } from "@/components/motion/reveal"
import { SectionHeading } from "@/components/section-heading"
import { cn } from "@/lib/utils"

/* ---------- sparkline ---------- */

function Sparkline({ data, id, tone = "cyan" }: { data: number[]; id: string; tone?: "cyan" | "indigo" | "emerald" }) {
  const W = 120
  const H = 36
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const d = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * W
      const y = H - 4 - ((v - min) / range) * (H - 8)
      return `${i === 0 ? "M" : "L"} ${x},${y}`
    })
    .join(" ")
  const start = tone === "cyan" ? "#22D3EE" : tone === "emerald" ? "#34D399" : "#818CF8"
  const gid = `spark-${id.replace(/\s+/g, "-")}`

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-9 w-full overflow-visible" fill="none">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor={start} />
          <stop offset="100%" stopColor="#22D3EE" />
        </linearGradient>
      </defs>
      <motion.path
        d={d}
        stroke={`url(#${gid})`}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        whileInView={{ pathLength: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
      />
    </svg>
  )
}

/* ---------- data ---------- */

const CARDS = [
  {
    label: "Total requests",
    value: 128.4,
    decimals: 1,
    suffix: "k",
    delta: "+18.2%",
    good: true,
    data: [20, 34, 28, 44, 52, 48, 66, 74, 68, 88],
    tone: "cyan" as const,
    className: "lg:col-span-3",
  },
  {
    label: "Avg response time",
    value: 96,
    suffix: "ms",
    delta: "-43.1%",
    good: true,
    data: [70, 64, 55, 60, 48, 44, 40, 38, 34, 30],
    tone: "indigo" as const,
    className: "lg:col-span-3",
  },
  {
    label: "Cache hit ratio",
    value: 72,
    suffix: "%",
    delta: "+6.4%",
    good: true,
    data: [30, 40, 36, 48, 52, 60, 58, 66, 70, 72],
    tone: "cyan" as const,
    className: "lg:col-span-2",
  },
  {
    label: "Error rate",
    value: 0.31,
    decimals: 2,
    suffix: "%",
    delta: "-0.2%",
    good: true,
    data: [10, 12, 9, 8, 7, 6, 5, 4, 4, 3],
    tone: "emerald" as const,
    className: "lg:col-span-2",
  },
  {
    label: "P95 latency",
    value: 128,
    suffix: "ms",
    delta: "-38%",
    good: true,
    data: [60, 58, 50, 52, 44, 40, 38, 32, 30, 26],
    tone: "cyan" as const,
    className: "lg:col-span-2",
  },
  {
    label: "P99 latency",
    value: 310,
    suffix: "ms",
    delta: "-27%",
    good: true,
    data: [80, 76, 70, 66, 62, 58, 52, 48, 44, 40],
    tone: "indigo" as const,
    className: "lg:col-span-3",
  },
  {
    label: "Slowest endpoint",
    value: 212,
    suffix: "ms",
    delta: "POST /v1/checkout",
    good: false,
    data: [50, 46, 44, 40, 38, 36, 34, 32, 30, 28],
    tone: "cyan" as const,
    className: "lg:col-span-3",
  },
]

export function MetricsBento() {
  return (
    <section id="metrics" className="relative scroll-mt-24 py-24">
      <div className="container">
        <SectionHeading
          tone="emerald"
          eyebrow="05 · live metrics"
          title={
            <>
              Proof, rendered in
              <span className="text-gradient-emerald"> real numbers.</span>
            </>
          }
          description="The pipeline publishes every request to Prometheus-compatible metrics. These are the kind of numbers you'll be looking at."
        />

        <div className="mt-14 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
          {CARDS.map((c, i) => (
            <Reveal key={c.label} delay={(i % 3) * 0.07} className={c.className}>
              <div className="frame-brutal group h-full rounded-xl bg-panel p-5 transition-all duration-300 hover:shadow-brutal-lg">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
                    {c.label}
                  </span>
                  <span
                    className={cn(
                      "flex items-center gap-1 font-mono text-[10px] tabular-nums",
                      c.good ? "text-emerald-300" : "text-amber-300",
                    )}
                  >
                    {c.good ? (
                      <ArrowDownRight className="h-3 w-3" />
                    ) : (
                      <ArrowUpRight className="h-3 w-3" />
                    )}
                    {c.delta}
                  </span>
                </div>
                <div className="mt-3 flex items-end justify-between gap-4">
                  <span className="text-gradient-emerald font-mono text-2xl font-extrabold tabular-nums sm:text-[26px]">
                    <CountUp
                      value={c.value}
                      decimals={c.decimals ?? 0}
                      suffix={c.suffix}
                    />
                  </span>
                  <div className="w-24">
                    <Sparkline data={c.data} id={c.label} tone={c.tone} />
                  </div>
                </div>
              </div>
            </Reveal>
          ))}

          {/* API quota full-width card */}
          <Reveal className="sm:col-span-2 lg:col-span-6" delay={0.1}>
            <div className="frame-brutal-accent rounded-xl bg-panel p-5 transition-shadow duration-300 hover:shadow-brutal-accent-lg">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.04]">
                    <TrendingUp className="h-4 w-4 text-accent-cyan" />
                  </span>
                  <div>
                    <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
                      API usage quota
                    </div>
                    <div className="mt-0.5 font-mono text-sm text-zinc-300">
                      812k / 1.0M requests used
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex w-40 flex-col items-end gap-1">
                    <span className="font-mono text-[10px] tabular-nums text-zinc-400">
                      81% · resets in 6d 04h
                    </span>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-r from-accent-indigo to-accent-cyan"
                        initial={{ width: 0 }}
                        whileInView={{ width: "81%" }}
                        viewport={{ once: true }}
                        transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
                      />
                    </div>
                  </div>
                  <Database className="h-4 w-4 text-zinc-600" />
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
