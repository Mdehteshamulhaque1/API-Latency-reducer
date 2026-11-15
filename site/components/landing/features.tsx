"use client"

import type { ReactNode } from "react"
import {
  Activity,
  BarChart3,
  Boxes,
  BookOpen,
  Lock,
  ShieldCheck,
  Timer,
  Zap,
} from "lucide-react"

import { TiltCard } from "@/components/motion/tilt-card"
import { SectionHeading } from "@/components/section-heading"
import { Reveal } from "@/components/motion/reveal"
import { cn } from "@/lib/utils"

/* ---------- micro-visualizations (revealed on hover) ---------- */

function RedisVisual() {
  return (
    <div className="space-y-2 font-mono text-[11px]">
      <div className="flex items-center gap-2">
        <span className="text-faint">GET</span>
        <span className="text-zinc-300">/v1/products?page=2</span>
      </div>
      <div className="rounded-md border border-ok/20 bg-ok/[0.06] p-2">
        <div className="flex items-center justify-between">
          <span className="text-ok">HIT · served from redis</span>
          <span className="tabular-nums text-zinc-500">4ms</span>
        </div>
        <div className="mt-1 truncate text-[10px] text-faint">
          key: rule:/v1/products*:hash(user:12,page)
        </div>
      </div>
    </div>
  )
}

function AnalyticsVisual() {
  const bars = [34, 52, 40, 66, 58, 78, 62, 90]
  return (
    <div className="flex h-14 items-end gap-1.5">
      {bars.map((h, i) => (
        <div
          key={i}
          className="w-full rounded-t-[2px] bg-gradient-to-t from-accent-indigo/70 to-accent-cyan/80 transition-all duration-500 group-hover:from-accent-indigo group-hover:to-accent-cyan"
          style={{
            height: `${h}%`,
            transitionDelay: `${i * 40}ms`,
          }}
        />
      ))}
    </div>
  )
}

function BucketVisual() {
  return (
    <div className="flex items-end gap-3 font-mono text-[10px] text-faint">
      <div className="relative h-16 w-24 overflow-hidden rounded-md border border-white/15 bg-black/40">
        <div className="token-fill absolute bottom-0 left-0 right-0 h-[18%] bg-gradient-to-t from-accent-indigo/80 to-accent-cyan/80 transition-all duration-700 ease-expo group-hover:h-[82%]" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-zinc-400">bucket: 100 req/h</span>
        <span className="tabular-nums text-accent-cyan">tokens refilling…</span>
      </div>
    </div>
  )
}

function JwtVisual() {
  return (
    <div className="space-y-1.5 font-mono text-[10px]">
      <div className="flex gap-1">
        <span className="truncate rounded border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-violet-300">eyJhbGciOiJI</span>
        <span className="truncate rounded border border-accent-indigo/30 bg-accent-indigo/10 px-1.5 py-0.5 text-indigo-300">eyJzdWIiOiIxIiwidHlw</span>
        <span className="truncate rounded border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-zinc-500">sig</span>
      </div>
      <div className="text-zinc-400">
        <span className="text-faint">payload →</span> {"type"}:&quot;access&quot; · sub:1
      </div>
    </div>
  )
}

function PerfVisual() {
  return (
    <svg viewBox="0 0 120 36" className="h-9 w-full overflow-visible" fill="none">
      <path
        d="M2 30 L18 26 L34 28 L50 18 L66 20 L82 12 L98 14 L118 5"
        stroke="#22D3EE"
        strokeWidth="1.6"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1}
        className="transition-all duration-700 ease-expo group-hover:stroke-dashoffset-0"
      />
      <path
        d="M2 30 L18 28 L34 24 L50 22 L66 18 L82 16 L98 12 L118 9"
        stroke="rgba(255,255,255,0.15)"
        strokeWidth="1.2"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1}
        className="transition-all delay-100 duration-700 ease-expo group-hover:stroke-dashoffset-0"
      />
      <g className="font-mono text-[7px]" fill="#5D6270">
        <text x="0" y="18">p95</text>
        <text x="0" y="36">p50</text>
      </g>
    </svg>
  )
}

function RbacVisual() {
  const roles = [
    { name: "admin", ok: true },
    { name: "operator", ok: true },
    { name: "viewer", ok: false },
  ]
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {roles.map((r) => (
        <span
          key={r.name}
          className={cn(
            "rounded border px-2 py-0.5 font-mono text-[10px] transition-colors",
            r.name === "admin"
              ? "border-accent-indigo/40 bg-accent-indigo/10 text-indigo-300 group-hover:border-accent-indigo group-hover:text-white"
              : "border-white/10 text-zinc-500",
          )}
        >
          {r.name}
        </span>
      ))}
      <span className="ml-1 font-mono text-[10px] text-faint">viewer → 403</span>
    </div>
  )
}

function DockerVisual() {
  const layers = ["FROM", "COPY", "RUN", "EXPOSE", "CMD"]
  return (
    <div className="flex flex-col gap-1 font-mono text-[10px]">
      {layers.map((l, i) => (
        <div key={l} className="flex items-center gap-2">
          <span
            className={cn(
              "h-2.5 w-2.5 rounded-[2px] border transition-colors duration-300",
              "border-accent-cyan/50 bg-accent-cyan/20",
            )}
            style={{ transitionDelay: `${i * 60}ms`, opacity: 0.4 + i * 0.08 }}
          />
          <span className="text-zinc-400">{l} …</span>
        </div>
      ))}
    </div>
  )
}

function DocsVisual() {
  const lines = [
    { code: "POST /api/v1/auth/login", dim: false },
    { code: "├─ 200 · access_token ✓", dim: true },
    { code: "GET /api/v1/rules", dim: false },
    { code: "├─ 403 · role required", dim: true },
  ]
  return (
    <div className="space-y-1 rounded-md border border-white/10 bg-black/40 p-2.5 font-mono text-[10px]">
      {lines.map((l, i) => (
        <div key={i} className={cn(l.dim ? "text-zinc-600" : "text-zinc-300")}>
          {l.code}
        </div>
      ))}
    </div>
  )
}

/* ---------- feature data ---------- */

interface Feature {
  title: string
  desc: string
  icon: ReactNode
  hint: string
  visual: ReactNode
  className: string
}

const FEATURES: Feature[] = [
  {
    title: "Redis Response Caching",
    desc: "Rules-driven cache with TTL, per-user and per-query keys, and automatic invalidation. Most reads never touch your database.",
    icon: <Zap className="h-4 w-4 text-accent-cyan" />,
    hint: "GET /v1/products",
    visual: <RedisVisual />,
    className: "lg:col-span-3 lg:row-span-2",
  },
  {
    title: "Request Analytics",
    desc: "Every request logged with latency, cache status, and user — aggregated in real time.",
    icon: <BarChart3 className="h-4 w-4 text-accent-indigo" />,
    hint: "12.4k req / day",
    visual: <AnalyticsVisual />,
    className: "lg:col-span-3",
  },
  {
    title: "Token Bucket Rate Limiter",
    desc: "Atomic per-user, per-IP, and per-key limits — enforced before your business logic runs.",
    icon: <Timer className="h-4 w-4 text-accent-cyan" />,
    hint: "100 req / hour",
    visual: <BucketVisual />,
    className: "lg:col-span-3",
  },
  {
    title: "JWT Authentication",
    desc: "Access and refresh tokens with strict type-checking and role claims built in.",
    icon: <Lock className="h-4 w-4 text-accent-indigo" />,
    hint: "HS256 · 30m",
    visual: <JwtVisual />,
    className: "lg:col-span-2",
  },
  {
    title: "Performance Monitoring",
    desc: "P50 / P95 / P99 latency percentiles and slow-endpoint rankings out of the box.",
    icon: <Activity className="h-4 w-4 text-accent-cyan" />,
    hint: "p95 128ms",
    visual: <PerfVisual />,
    className: "lg:col-span-2",
  },
  {
    title: "Role-Based Access Control",
    desc: "Admin, operator, and viewer roles gate every mutation. No privilege escalation.",
    icon: <ShieldCheck className="h-4 w-4 text-accent-indigo" />,
    hint: "admin / operator / viewer",
    visual: <RbacVisual />,
    className: "lg:col-span-2",
  },
  {
    title: "Docker Support",
    desc: "Single-container deploy with health checks. Redis and MySQL attach as services.",
    icon: <Boxes className="h-4 w-4 text-accent-cyan" />,
    hint: "Dockerfile · :8000",
    visual: <DockerVisual />,
    className: "lg:col-span-3",
  },
  {
    title: "API Documentation",
    desc: "Auto-generated interactive OpenAPI docs with auth, schemas, and examples.",
    icon: <BookOpen className="h-4 w-4 text-accent-indigo" />,
    hint: "OpenAPI 3 · /docs",
    visual: <DocsVisual />,
    className: "lg:col-span-3",
  },
]

function FeatureCard({ feature, index }: { feature: Feature; index: number }) {
  return (
    <Reveal
      as="li"
      delay={(index % 3) * 0.08}
      className={cn("min-h-[220px]", feature.className)}
    >
      <TiltCard className="group frame-brutal relative flex h-full flex-col rounded-xl bg-panel p-5 transition-all duration-300 hover:shadow-brutal-lg">
        <div className="flex items-start justify-between">
          <div className="glass flex h-9 w-9 items-center justify-center rounded-lg">
            {feature.icon}
          </div>
          <span className="font-mono text-[10px] text-faint">{feature.hint}</span>
        </div>

        <h3 className="mt-4 text-[15px] font-medium tracking-tight text-zinc-100">
          {feature.title}
        </h3>
        <p className="mt-1.5 text-[13px] leading-relaxed text-dim">{feature.desc}</p>

        <div className="mt-auto pt-5">
          <div className="rounded-lg border border-white/[0.06] bg-black/25 p-3 opacity-90 transition-all duration-500 group-hover:border-white/15 group-hover:bg-black/40">
            {feature.visual}
          </div>
        </div>
      </TiltCard>
    </Reveal>
  )
}

export function Features() {
  return (
    <section id="features" className="relative scroll-mt-24 py-24">
      <div className="container">
        <SectionHeading
          eyebrow="01 · capabilities"
          title={
            <>
              Eight subsystems.
              <span className="text-gradient"> One latency budget.</span>
            </>
          }
          description="Everything you need to make your API fast, authenticated, and observable — no duct tape between services."
        />

        <ul className="mt-14 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-6">
          {FEATURES.map((f, i) => (
            <FeatureCard key={f.title} feature={f} index={i} />
          ))}
        </ul>
      </div>
    </section>
  )
}
