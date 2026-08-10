"use client"

import type { CSSProperties, ReactNode } from "react"

import { motion } from "framer-motion"
import {
  Activity,
  Database,
  Layers,
  Lock,
  Monitor,
  Timer,
  Zap,
} from "lucide-react"

import { Reveal } from "@/components/motion/reveal"
import { SectionHeading } from "@/components/section-heading"
import { cn } from "@/lib/utils"

const VB = { w: 960, h: 440 }

interface Node {
  id: string
  x: number
  y: number
  w: number
  h: number
  label: string
  sub: string
  icon: ReactNode
  accent: string
}

const NODES: Node[] = [
  { id: "client", x: 110, y: 220, w: 140, h: 62, label: "Client", sub: "your app", icon: <Monitor className="h-4 w-4" />, accent: "text-zinc-300" },
  { id: "fastapi", x: 300, y: 220, w: 140, h: 62, label: "FastAPI", sub: "middleware chain", icon: <Zap className="h-4 w-4" />, accent: "text-accent-cyan" },
  { id: "auth", x: 500, y: 92, w: 128, h: 54, label: "Auth", sub: "JWT validate", icon: <Lock className="h-4 w-4" />, accent: "text-violet-300" },
  { id: "cache", x: 500, y: 220, w: 128, h: 54, label: "Cache", sub: "Redis lookup", icon: <Database className="h-4 w-4" />, accent: "text-accent-cyan" },
  { id: "ratelimit", x: 500, y: 348, w: 128, h: 54, label: "Rate Limit", sub: "token bucket", icon: <Timer className="h-4 w-4" />, accent: "text-orange-300" },
  { id: "analytics", x: 662, y: 348, w: 112, h: 50, label: "Analytics", sub: "log + monitor", icon: <Activity className="h-4 w-4" />, accent: "text-emerald-300" },
  { id: "redis", x: 790, y: 152, w: 118, h: 52, label: "Redis", sub: "store · TTL", icon: <Database className="h-4 w-4" />, accent: "text-red-300" },
  { id: "mysql", x: 790, y: 292, w: 118, h: 52, label: "MySQL", sub: "source of truth", icon: <Layers className="h-4 w-4" />, accent: "text-blue-300" },
]

function nodeStyle(n: Node): CSSProperties {
  return {
    left: `${((n.x - n.w / 2) / VB.w) * 100}%`,
    top: `${((n.y - n.h / 2) / VB.h) * 100}%`,
    width: `${(n.w / VB.w) * 100}%`,
    height: `${(n.h / VB.h) * 100}%`,
  }
}

interface Packet {
  path: string
  color: string
  dur: number
}

const PACKETS: Packet[] = [
  { path: "M 370 220 L 435 220", color: "#22D3EE", dur: 1.4 },
  { path: "M 435 250 L 370 250", color: "#34D399", dur: 1.4 },
  { path: "M 180 220 L 230 220", color: "#F8FAFC", dur: 2.6 },
  { path: "M 565 220 L 700 165", color: "#FBBF24", dur: 1.9 },
  { path: "M 370 195 L 435 100", color: "#A78BFA", dur: 2.3 },
  { path: "M 790 178 L 790 262", color: "#818CF8", dur: 2.8 },
]

const STATIC_PATHS = [
  "M 230 252 L 180 252",
  "M 370 245 L 435 340",
  "M 565 345 L 605 340",
  "M 715 335 L 730 290",
  "M 700 185 L 565 245",
]

export function ArchitectureDiagram() {
  return (
    <section id="architecture" className="relative scroll-mt-24 py-24">
      <div className="container">
        <SectionHeading
          eyebrow="02 · architecture"
          title={
            <>
              See a request travel the
              <span className="text-gradient"> request pipeline.</span>
            </>
          }
          description="Auth, rate limiting, and caching run as middleware — most traffic short-circuits back to the client before ever hitting MySQL."
        />

        <Reveal delay={0.1}>
          <div className="frame-brutal relative mx-auto mt-14 max-w-4xl rounded-2xl bg-panel/40 p-4 backdrop-blur sm:p-6">
            <span className="sticker absolute -top-3.5 left-6 z-10 rotate-[-1deg] bg-panel">
              fig. 02 — request pipeline
            </span>
            <div className="overflow-x-auto pb-2 pt-3">
              <div className="relative aspect-[960/440] min-w-[720px]">
              {/* ambient glow */}
              <div className="pointer-events-none absolute inset-0 rounded-2xl bg-[radial-gradient(50%_60%_at_50%_40%,rgba(99,102,241,0.14),transparent_70%)]" />

              {/* connections + packets */}
              <svg
                viewBox={`0 0 ${VB.w} ${VB.h}`}
                className="absolute inset-0 h-full w-full"
                fill="none"
              >
                {STATIC_PATHS.map((d) => (
                  <path
                    key={d}
                    d={d}
                    stroke="rgba(255,255,255,0.08)"
                    strokeWidth="1.5"
                  />
                ))}
                <path
                  d="M 370 220 L 435 220"
                  stroke="rgba(34,211,238,0.5)"
                  strokeWidth="1.5"
                  className="dash-flow"
                />
                <path
                  d="M 565 220 L 700 165"
                  stroke="rgba(251,191,36,0.35)"
                  strokeWidth="1.5"
                  className="dash-flow"
                />
                <path
                  d="M 435 250 L 370 250"
                  stroke="rgba(52,211,153,0.45)"
                  strokeWidth="1.5"
                  className="dash-flow"
                />
                <path
                  d="M 180 220 L 230 220"
                  stroke="rgba(255,255,255,0.25)"
                  strokeWidth="1.5"
                  className="dash-flow"
                />

                {PACKETS.map((p, i) => (
                  <circle key={i} r="3" fill={p.color}>
                    <animateMotion
                      dur={`${p.dur}s`}
                      repeatCount="indefinite"
                      path={p.path}
                    />
                  </circle>
                ))}
              </svg>

              {/* nodes */}
              {NODES.map((n, i) => (
                <motion.div
                  key={n.id}
                  className="absolute"
                  style={nodeStyle(n)}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.15 + i * 0.06, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                >
                  <div
                    className={cn(
                      "frame-brutal group flex h-full w-full items-center gap-2.5 rounded-lg bg-panel/90 px-3 backdrop-blur transition-all duration-300 hover:z-10 hover:scale-[1.06] hover:shadow-brutal-lg",
                    )}
                  >
                    <span className={n.accent}>{n.icon}</span>
                    <div className="flex flex-col leading-tight">
                      <span className="font-mono text-[12px] font-medium text-zinc-100">
                        {n.label}
                      </span>
                      <span className="font-mono text-[9px] uppercase tracking-wider text-faint">
                        {n.sub}
                      </span>
                    </div>
                  </div>
                </motion.div>
              ))}

              {/* path labels */}
              <span className="absolute left-[44%] top-[41%] rounded border border-emerald-400/20 bg-emerald-400/10 px-1.5 py-0.5 font-mono text-[9px] text-emerald-300">
                HIT · 4ms
              </span>
              <span className="absolute left-[57%] top-[30%] rounded border border-amber-400/20 bg-amber-400/10 px-1.5 py-0.5 font-mono text-[9px] text-amber-300">
                MISS → write
              </span>
            </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

