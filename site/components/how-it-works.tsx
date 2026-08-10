"use client"

import { useRef } from "react"
import { motion, useScroll, useTransform } from "framer-motion"
import {
  Activity,
  Check,
  Database,
  FileText,
  KeyRound,
  Timer,
  X,
  Zap,
} from "lucide-react"

import { Reveal } from "@/components/motion/reveal"
import { SectionHeading } from "@/components/section-heading"
import { cn } from "@/lib/utils"

interface Step {
  title: string
  detail: string
  code: string
  time: string
  icon: React.ReactNode
}

const STEPS: Step[] = [
  {
    title: "Request arrives",
    detail: "Client calls a protected endpoint.",
    code: "POST /api/v1/checkout",
    time: "t+0",
    icon: <Zap className="h-3.5 w-3.5" />,
  },
  {
    title: "JWT validated",
    detail: "Signature, expiry, and token type checked.",
    code: "Bearer eyJhbGciOi…",
    time: "t+0.4ms",
    icon: <KeyRound className="h-3.5 w-3.5" />,
  },
  {
    title: "Rate limit checked",
    detail: "Token bucket decremented atomically.",
    code: "bucket.check(user:12)",
    time: "t+0.8ms",
    icon: <Timer className="h-3.5 w-3.5" />,
  },
  {
    title: "Cache lookup",
    detail: "Redis queried with a rule-derived key.",
    code: "GET rule:/v1/checkout*",
    time: "t+1.1ms",
    icon: <Database className="h-3.5 w-3.5" />,
  },
]

const NORMAL_STEPS: Step[] = [
  {
    title: "Response returned",
    detail: "Cached payload streams back with metrics.",
    code: "200 OK · 4ms total",
    time: "t+1.2ms",
    icon: <Check className="h-3.5 w-3.5" />,
  },
]

const FORK_STEPS: Step[] = [
  {
    title: "Business logic runs",
    detail: "On miss, the request proceeds to the handler.",
    code: "await service.checkout(payload)",
    time: "t+2ms",
    icon: <FileText className="h-3.5 w-3.5" />,
  },
  {
    title: "SQL executed",
    detail: "MySQL answers the query and commits writes.",
    code: "INSERT INTO orders …",
    time: "t+38ms",
    icon: <Database className="h-3.5 w-3.5" />,
  },
  {
    title: "Response re-cached",
    detail: "Fresh result written back with a TTL.",
    code: "SET … EX 300",
    time: "t+39ms",
    icon: <Zap className="h-3.5 w-3.5" />,
  },
  {
    title: "Metrics recorded",
    detail: "Latency, cache status, and user published to analytics.",
    code: "publish request.p95",
    time: "t+39.4ms",
    icon: <Activity className="h-3.5 w-3.5" />,
  },
]

function StepRow({
  step,
  active,
  num,
}: {
  step: Step
  active?: boolean
  num?: number
}) {
  return (
    <motion.li
      initial={{ opacity: 0, x: -16 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="relative flex gap-4"
    >
      <div className="flex w-14 shrink-0 flex-col items-center gap-1.5">
        {num !== undefined && (
          <span className="select-none text-[2.6rem] font-extrabold leading-[0.8] tracking-[-0.04em] text-zinc-50/[0.07]">
            {String(num).padStart(2, "0")}
          </span>
        )}
        <div
          className={cn(
            "hairline flex h-8 w-8 items-center justify-center rounded-lg bg-panel",
            active && "border-emerald-400/40 text-emerald-300",
          )}
        >
          {step.icon}
        </div>
      </div>
      <div className="flex-1 rounded-lg border border-white/[0.08] bg-white/[0.02] p-3.5 transition-colors hover:border-white/20">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-mono text-[13px] font-medium text-zinc-100">
            {step.title}
          </h3>
          <span className="font-mono text-[10px] tabular-nums text-faint">
            {step.time}
          </span>
        </div>
        <p className="mt-0.5 text-[12px] text-dim">{step.detail}</p>
        <code className="mt-2 inline-block rounded border border-white/[0.06] bg-black/40 px-2 py-0.5 font-mono text-[10px] text-zinc-500">
          {step.code}
        </code>
      </div>
    </motion.li>
  )
}

export function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 0.75", "end 0.65"],
  })
  const fillHeight = useTransform(scrollYProgress, [0, 1], ["0%", "100%"])

  return (
    <section id="how-it-works" className="relative scroll-mt-24 py-24">
      <div className="container">
        <SectionHeading
          eyebrow="03 · how it works"
          title={
            <>
              A single request, from
              <span className="text-gradient"> entry to exit.</span>
            </>
          }
          description="Middleware runs in strict order. Caching short-circuits the happy path; misses pay a database round-trip — once."
        />

        <div ref={ref} className="relative mx-auto mt-14 max-w-2xl">
          {/* progress line */}
          <div className="absolute left-4 top-2 h-[calc(100%-16px)] w-px bg-white/[0.08]" />
          <motion.div
            style={{ height: fillHeight }}
            className="absolute left-4 top-2 w-px bg-gradient-to-b from-accent-indigo via-accent-cyan to-emerald-400"
          />

          <ol className="relative space-y-5 pl-12">
            {STEPS.map((s, i) => (
              <StepRow key={s.title} step={s} num={i + 1} />
            ))}

            {/* cache fork */}
            <motion.li
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="relative"
            >
              <div className="mb-2 flex items-end gap-3 pl-1">
                <span className="select-none text-[2.6rem] font-extrabold leading-[0.8] tracking-[-0.04em] text-zinc-50/[0.07]">
                  05
                </span>
                <span className="pb-0.5 font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
                  cache decision
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="relative rounded-lg border border-emerald-400/30 bg-emerald-400/[0.05] p-3.5">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded border border-emerald-400/40 text-emerald-300">
                      <Check className="h-3 w-3" />
                    </span>
                    <h3 className="font-mono text-[13px] font-medium text-emerald-200">
                      HIT
                    </h3>
                  </div>
                  <p className="mt-1.5 text-[12px] text-dim">
                    Served from Redis — no DB call.
                  </p>
                  <div className="mt-2 flex items-center justify-between">
                    <code className="font-mono text-[10px] text-emerald-300/80">
                      200 OK · 4ms
                    </code>
                    <span className="font-mono text-[10px] text-faint">t+1.2ms</span>
                  </div>
                </div>

                <div className="relative rounded-lg border border-white/[0.08] bg-white/[0.02] p-3.5 opacity-80">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded border border-white/15 text-zinc-400">
                      <X className="h-3 w-3" />
                    </span>
                    <h3 className="font-mono text-[13px] font-medium text-zinc-300">
                      MISS
                    </h3>
                  </div>
                  <p className="mt-1.5 text-[12px] text-dim">
                    Falls through to business logic.
                  </p>
                  <div className="mt-2 flex items-center justify-between">
                    <code className="font-mono text-[10px] text-zinc-500">
                      forward…
                    </code>
                    <span className="font-mono text-[10px] text-faint">t+2ms</span>
                  </div>
                </div>
              </div>
            </motion.li>

            {NORMAL_STEPS.map((s, i) => (
              <StepRow key={s.title} step={s} num={i + 6} />
            ))}
          </ol>

          {/* miss fork detail */}
          <Reveal delay={0.1}>
            <div className="mt-10 rounded-xl border border-white/[0.08] bg-black/20 p-5">
              <div className="mb-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
                <span className="text-zinc-500">├─ on miss (cold path)</span>
              </div>
              <div className="space-y-2">
                {FORK_STEPS.map((s, i) => (
                  <StepRow key={s.title} step={s} num={i + 7} />
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
