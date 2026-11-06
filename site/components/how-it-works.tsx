"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import {
  ArrowDown,
  Check,
  Database,
  KeyRound,
  Timer,
  X,
  Zap,
} from "lucide-react"

import { Reveal } from "@/components/motion/reveal"
import { SectionHeading } from "@/components/section-heading"
import { cn } from "@/lib/utils"

/* ---------- animation 1 · request packet traveling the middleware chain ---------- */

const CHAIN = [
  { id: "auth", label: "Auth", icon: <KeyRound className="h-4 w-4" />, ms: "0.4ms" },
  { id: "ratelimit", label: "Rate Limit", icon: <Timer className="h-4 w-4" />, ms: "0.8ms" },
  { id: "cache", label: "Cache", icon: <Database className="h-4 w-4" />, ms: "1.1ms" },
]

function PacketAnimation() {
  const [stage, setStage] = useState(0)
  const maxStage = CHAIN.length + 1

  useEffect(() => {
    const t = setInterval(() => {
      setStage((s) => (s + 1) % (maxStage + 1))
    }, 1100)
    return () => clearInterval(t)
  }, [maxStage])

  const travelling = stage > 0 && stage <= CHAIN.length
  const done = stage > CHAIN.length

  return (
    <div className="flex flex-col gap-4">
      <div className="relative flex items-center justify-between">
        <div className="absolute left-0 right-0 top-1/2 h-px -translate-y-1/2 bg-white/[0.08]" />
        <span className="sticker relative z-10 border-accent-cyan/40 bg-panel">
          <Zap className="h-3 w-3 text-accent-cyan" /> request
        </span>
        {CHAIN.map((n, i) => {
          const reached = stage > i
          return (
            <div key={n.id} className="relative z-10 flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "flex h-12 w-12 items-center justify-center rounded-xl border transition-all duration-300",
                  reached
                    ? "border-accent-cyan/60 bg-accent-cyan/15 text-accent-cyan"
                    : "border-white/10 bg-panel text-zinc-500",
                )}
              >
                {n.icon}
              </div>
              <span
                className={cn(
                  "font-mono text-[9px] uppercase tracking-wider transition-colors",
                  reached ? "text-zinc-200" : "text-faint",
                )}
              >
                {n.label}
              </span>
              <span className="font-mono text-[9px] tabular-nums text-faint">{n.ms}</span>
            </div>
          )
        })}
        <div
          className={cn(
            "relative z-10 flex h-12 w-12 items-center justify-center rounded-xl border transition-all duration-300",
            done
              ? "border-emerald-400/60 bg-emerald-400/15 text-emerald-300"
              : "border-white/10 bg-panel text-zinc-500",
          )}
        >
          {done ? <Check className="h-4 w-4" /> : <ArrowDown className="h-4 w-4 rotate-[-90deg]" />}
        </div>
      </div>

      {/* moving packet */}
      <div className="relative h-6">
        {travelling && (
          <motion.div
            key={stage}
            initial={{ left: "0%", opacity: 0 }}
            animate={{ left: `${(stage / maxStage) * 100}%`, opacity: [0, 1, 1, 0] }}
            transition={{ duration: 1, ease: "easeInOut" }}
            className="absolute top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-accent-cyan shadow-glow-cyan"
          />
        )}
        {done && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute right-0 top-1/2 flex -translate-y-1/2 items-center gap-1.5 rounded-full border border-emerald-400/40 bg-emerald-400/10 px-3 py-1 font-mono text-[10px] text-emerald-300"
          >
            <Check className="h-3 w-3" /> 200 · 4ms
          </motion.div>
        )}
      </div>
    </div>
  )
}

/* ---------- animation 2 · cache HIT vs MISS toggle ---------- */

function CacheAnimation() {
  const [mode, setMode] = useState<"hit" | "miss">("hit")

  return (
    <div>
      <div className="mb-3 flex items-center gap-1 rounded-lg border border-white/[0.08] bg-black/30 p-1">
        {(["hit", "miss"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors",
              mode === m
                ? m === "hit"
                  ? "bg-emerald-400/20 text-emerald-200"
                  : "bg-amber-400/20 text-amber-200"
                : "text-zinc-500 hover:text-zinc-300",
            )}
          >
            {m === "hit" ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
            {m}
          </button>
        ))}
      </div>

      <motion.div
        key={mode}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className={cn(
          "rounded-lg border p-4 font-mono",
          mode === "hit"
            ? "border-emerald-400/30 bg-emerald-400/[0.05]"
            : "border-amber-400/30 bg-amber-400/[0.05]",
        )}
      >
        <div className="flex items-center justify-between">
          <span className={mode === "hit" ? "text-emerald-300" : "text-amber-300"}>
            {mode === "hit" ? "HIT · served from Redis" : "MISS · falls through to DB"}
          </span>
          <span className="text-2xl font-extrabold tabular-nums text-zinc-100">
            {mode === "hit" ? "4ms" : "38ms"}
          </span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-white/[0.06]">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: mode === "hit" ? "8%" : "78%" }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className={cn(
              "h-full rounded-full",
              mode === "hit"
                ? "bg-gradient-to-r from-emerald-400 to-accent-cyan"
                : "bg-gradient-to-r from-amber-400 to-orange-400",
            )}
          />
        </div>
        <p className="mt-3 text-[12px] text-dim">
          {mode === "hit"
            ? "The cached payload streams straight back — the database is never touched."
            : "The request pays one MySQL round-trip, then the fresh result is written back with a TTL."}
        </p>
      </motion.div>
    </div>
  )
}

/* ---------- animation 3 · latency before / after ---------- */

function LatencyAnimation() {
  const [run, setRun] = useState(false)

  useEffect(() => {
    const t = setInterval(() => setRun((r) => !r), 2600)
    return () => clearInterval(t)
  }, [])

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">
          same request · cache off vs on
        </span>
        <span className="font-mono text-[10px] text-zinc-500">~10 VUs · 30s</span>
      </div>

      <div className="space-y-3">
        <div>
          <div className="mb-1 flex items-center justify-between font-mono text-[11px]">
            <span className="text-zinc-400">cache off</span>
            <span className="tabular-nums text-zinc-500">183 ms</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-white/[0.06]">
            <motion.div
              initial={{ width: "100%" }}
              animate={{ width: run ? "30%" : "100%" }}
              transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1] }}
              className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-400"
            />
          </div>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between font-mono text-[11px]">
            <span className="text-zinc-400">cache on</span>
            <span className="tabular-nums text-emerald-300">7.5 ms</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-white/[0.06]">
            <motion.div
              initial={{ width: "4%" }}
              animate={{ width: run ? "4%" : "42%" }}
              transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1] }}
              className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-accent-cyan"
            />
          </div>
        </div>

        <p className="rounded-lg border border-emerald-400/20 bg-emerald-400/[0.05] px-3 py-2 font-mono text-[11px] text-emerald-200">
          ≈ 24× faster · −95.9% latency
        </p>
      </div>
    </div>
  )
}

/* ---------- single compact flow ---------- */

const FLOW = [
  {
    title: "Request arrives",
    detail: "Client calls a protected endpoint. Auth and rate limits run first.",
    icon: <Zap className="h-4 w-4" />,
    tone: "text-accent-cyan" as const,
  },
  {
    title: "Cache lookup",
    detail: "Redis is queried with a rule-derived key before any business logic.",
    icon: <Database className="h-4 w-4" />,
    tone: "text-accent-indigo" as const,
  },
  {
    title: "Serve or write-through",
    detail: "Hits stream straight back; misses hit MySQL once, then re-cache with a TTL.",
    icon: <Check className="h-4 w-4" />,
    tone: "text-emerald-300" as const,
  },
]

export function HowItWorks() {
  return (
    <section id="how" className="relative scroll-mt-24 py-24">
      <div className="container">
        <SectionHeading
          tone="cyan"
          eyebrow="03 · how it works"
          title={
            <>
              One request.
              <span className="text-gradient-cyan"> Four layers of speed.</span>
            </>
          }
          description="Middleware runs in strict order. Caching short-circuits the happy path; misses pay a database round-trip — once."
        />

        <div className="mt-14 grid gap-6 lg:grid-cols-3">
          <Reveal>
            <div className="frame-brutal flex h-full flex-col rounded-xl bg-panel p-5">
              <span className="mono-label flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded bg-accent-cyan/15 text-accent-cyan">
                  01
                </span>
                travel the pipeline
              </span>
              <div className="mt-6 flex-1">
                <PacketAnimation />
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="frame-brutal flex h-full flex-col rounded-xl bg-panel p-5">
              <span className="mono-label flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded bg-emerald-400/15 text-emerald-300">
                  02
                </span>
                cache hit vs miss
              </span>
              <div className="mt-6 flex-1">
                <CacheAnimation />
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.2}>
            <div className="frame-brutal flex h-full flex-col rounded-xl bg-panel p-5">
              <span className="mono-label flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded bg-accent-indigo/15 text-accent-indigo">
                  03
                </span>
                the payoff
              </span>
              <div className="mt-6 flex-1">
                <LatencyAnimation />
              </div>
            </div>
          </Reveal>
        </div>

        <Reveal delay={0.15}>
          <div className="mx-auto mt-10 max-w-3xl rounded-xl border border-white/[0.08] bg-black/20 p-5 sm:p-6">
            <div className="mb-4 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
              <span className="text-zinc-500">├─ the strict order</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {FLOW.map((s, i) => (
                <motion.div
                  key={s.title}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-60px" }}
                  transition={{ duration: 0.5, delay: i * 0.12, ease: [0.16, 1, 0.3, 1] }}
                  className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-4"
                >
                  <div className="flex items-center gap-2">
                    <span className={cn("flex h-8 w-8 items-center justify-center rounded-lg bg-panel", s.tone)}>
                      {s.icon}
                    </span>
                    <span className="font-mono text-[9px] tabular-nums text-faint">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                  </div>
                  <h3 className="mt-3 font-mono text-[13px] font-medium text-zinc-100">
                    {s.title}
                  </h3>
                  <p className="mt-1 text-[12px] leading-relaxed text-dim">{s.detail}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
