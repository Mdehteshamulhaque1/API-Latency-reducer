"use client"

import { useEffect, useState } from "react"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"

import { EASE } from "@/components/motion/reveal"
import { cn } from "@/lib/utils"

const TOASTS = [
  {
    method: "GET",
    path: "/v1/products",
    result: "CACHE HIT",
    ms: 4,
    tone: "ok",
  },
  {
    method: "GET",
    path: "/v1/search?q=cdn",
    result: "MISS → STORED",
    ms: 38,
    tone: "accent",
  },
  {
    method: "GET",
    path: "/v1/users/me",
    result: "CACHE HIT",
    ms: 3,
    tone: "ok",
  },
]

function CacheToast() {
  const [index, setIndex] = useState(0)
  const reduce = useReducedMotion()

  useEffect(() => {
    if (reduce) return
    const id = setInterval(() => setIndex((i) => (i + 1) % TOASTS.length), 2800)
    return () => clearInterval(id)
  }, [reduce])

  const toast = TOASTS[index]

  return (
    <div className="pointer-events-none absolute -left-5 top-16 hidden w-56 sm:block">
      <AnimatePresence mode="wait">
        <motion.div
          key={index}
          initial={reduce ? false : { opacity: 0, y: 10, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={reduce ? undefined : { opacity: 0, y: -8, scale: 0.96 }}
          transition={{ duration: 0.4, ease: EASE }}
          className="glass rounded-lg p-3 shadow-panel"
        >
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-faint">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                toast.tone === "ok" ? "bg-ok" : "bg-accent-cyan",
              )}
            />
            Redis · {toast.result}
          </div>
          <div className="mt-1.5 truncate font-mono text-[11px] text-zinc-300">
            {toast.method} {toast.path}
          </div>
          <div className="mt-1 font-mono text-[10px] text-zinc-500">
            served in <span className="text-accent-cyan">{toast.ms}ms</span>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

/* ---------- mini sparkline ---------- */

const W = 96
const H = 28

function Sparkline({
  data,
  tone,
}: {
  data: number[]
  tone: "cyan" | "indigo"
}) {
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const d = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * W
      const y = H - 2 - ((v - min) / range) * (H - 4)
      return `${i === 0 ? "M" : "L"} ${x},${y}`
    })
    .join(" ")
  const stroke = tone === "cyan" ? "#22D3EE" : "#818CF8"
  const gid = `live-spark-${tone}`

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-7 w-full" fill="none">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor={stroke} />
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
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.4, delay: 0.7, ease: EASE }}
      />
    </svg>
  )
}

/* ---------- live metrics ---------- */

const STATS = [
  {
    label: "Total requests",
    value: "12.4k",
    delta: "+18%",
    data: [20, 34, 28, 44, 52, 48, 66, 74, 68, 88],
    tone: "cyan" as const,
  },
  {
    label: "Avg latency",
    value: "96ms",
    delta: "-43%",
    data: [70, 64, 55, 60, 48, 44, 40, 38, 34, 30],
    tone: "indigo" as const,
  },
  {
    label: "Cache hit",
    value: "72%",
    delta: "+6.4%",
    data: [30, 40, 36, 48, 52, 60, 58, 66, 70, 72],
    tone: "cyan" as const,
  },
]

export function LivePanel() {
  const reduce = useReducedMotion()

  return (
    <div className="relative">
      {/* Ambient glow behind the panel */}
      <div
        aria-hidden
        className="absolute -inset-6 rounded-3xl bg-accent-gradient-soft opacity-70 blur-2xl"
      />

      <motion.div
        initial={reduce ? false : { opacity: 0, y: 32, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.9, delay: 0.4, ease: EASE }}
        className="frame-brutal relative rotate-[0.4deg] rounded-2xl"
      >
        <CacheToast />

        {/* overlapping sticker tag — deliberate brutalist misalignment */}
        <span className="sticker absolute -top-3.5 right-6 z-10 rotate-2 bg-panel text-[9px]">
          live edge
        </span>

        <div className="glass relative rounded-[14px] p-4 shadow-panel">
          {/* panel header */}
          <div className="flex items-center justify-between font-mono text-[10px] text-faint">
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              streaming now
            </span>
            <span className="text-zinc-500">200 OK</span>
          </div>

          {/* live stats */}
          <div className="mt-3 space-y-2.5">
            {STATS.map((s) => (
              <div
                key={s.label}
                className="flex items-center justify-between gap-4 rounded-lg border border-white/[0.06] bg-black/30 px-3 py-2"
              >
                <div className="min-w-0">
                  <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-faint">
                    {s.label}
                  </div>
                  <div className="mt-0.5 flex items-baseline gap-1.5">
                    <span className="font-mono text-lg font-semibold tabular-nums text-zinc-100">
                      {s.value}
                    </span>
                    <span className="font-mono text-[9px] tabular-nums text-emerald-300">
                      {s.delta}
                    </span>
                  </div>
                </div>
                <div className="w-24 shrink-0">
                  <Sparkline data={s.data} tone={s.tone} />
                </div>
              </div>
            ))}
          </div>

          {/* Footer strip */}
          <div className="mt-3 flex items-center justify-between border-t border-white/[0.06] pt-2.5 font-mono text-[10px] text-faint">
            <span>via fastapi + redis</span>
            <span className="text-zinc-500">99.9% uptime</span>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
