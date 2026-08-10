"use client"

import { useEffect, useState } from "react"
import * as Tabs from "@radix-ui/react-tabs"
import { AnimatePresence, motion } from "framer-motion"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Command,
  Database,
  FileText,
  Gauge,
  Globe,
  ListTree,
  Lock,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  UserCog,
  Users,
  Workflow,
} from "lucide-react"

import { Reveal } from "@/components/motion/reveal"
import { SectionHeading } from "@/components/section-heading"
import { cn } from "@/lib/utils"

/* ---------- tiny mock primitives ---------- */

function MiniStat({
  label,
  value,
  delta,
  good,
}: {
  label: string
  value: string
  delta?: string
  good?: boolean
}) {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
      <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-faint">
        {label}
      </div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="font-mono text-lg font-semibold tabular-nums text-zinc-100">
          {value}
        </span>
        {delta && (
          <span
            className={cn(
              "font-mono text-[9px] tabular-nums",
              good ? "text-emerald-300" : "text-amber-300",
            )}
          >
            {delta}
          </span>
        )}
      </div>
    </div>
  )
}

function Switch({ on = true }: { on?: boolean }) {
  return (
    <span
      className={cn(
        "relative inline-flex h-4 w-7 shrink-0 items-center rounded-full transition-colors",
        on ? "bg-accent-indigo" : "bg-white/15",
      )}
    >
      <span
        className={cn(
          "ml-0.5 h-3 w-3 rounded-full bg-white transition-transform",
          on && "translate-x-3",
        )}
      />
    </span>
  )
}

function CodeChip({ children, tone = "zinc" }: { children: React.ReactNode; tone?: "zinc" | "cyan" | "violet" | "emerald" }) {
  return (
    <span
      className={cn(
        "rounded border px-1.5 py-0.5 font-mono text-[9px]",
        tone === "cyan" && "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
        tone === "violet" && "border-violet-400/20 bg-violet-400/10 text-violet-300",
        tone === "emerald" && "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
        tone === "zinc" && "border-white/10 bg-white/[0.03] text-zinc-400",
      )}
    >
      {children}
    </span>
  )
}

/* ---------- mock panels ---------- */

const AREA_DATA = [
  { t: "09:00", v: 820 },
  { t: "09:05", v: 1050 },
  { t: "09:10", v: 940 },
  { t: "09:15", v: 1320 },
  { t: "09:20", v: 1180 },
  { t: "09:25", v: 1560 },
  { t: "09:30", v: 1410 },
  { t: "09:35", v: 1890 },
  { t: "09:40", v: 1720 },
]

const BAR_DATA = [
  { r: "<50ms", v: 8200 },
  { r: "50-150", v: 3400 },
  { r: "150-300", v: 1100 },
  { r: ">300ms", v: 210 },
]

const ENDPOINTS = [
  { m: "GET", path: "/v1/products", hits: "4.2k", p95: "41ms" },
  { m: "GET", path: "/v1/checkout/status", hits: "3.1k", p95: "38ms" },
  { m: "POST", path: "/v1/checkout", hits: "1.8k", p95: "212ms" },
  { m: "GET", path: "/v1/orders", hits: "1.4k", p95: "66ms" },
]

function LoginPanel() {
  return (
    <div className="grid gap-4 sm:grid-cols-[1.2fr_1fr]">
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] text-zinc-300">Sign in</span>
          <CodeChip tone="violet">access</CodeChip>
        </div>
        <div className="rounded-md border border-white/10 bg-black/40 px-3 py-2 font-mono text-[11px] text-zinc-500">
          dev@acme.io
        </div>
        <div className="rounded-md border border-white/10 bg-black/40 px-3 py-2 font-mono text-[11px] text-zinc-500">
          ••••••••••••
        </div>
        <div className="flex items-center justify-between rounded-md border border-accent-indigo/30 bg-accent-indigo/10 px-3 py-2 font-mono text-[11px]">
          <span className="text-zinc-200">Request access token</span>
          <span className="text-accent-cyan">POST /auth/login</span>
        </div>
        <div className="rounded-md border border-emerald-400/25 bg-emerald-400/[0.06] px-3 py-2 font-mono text-[10px] text-emerald-300">
          ✓ 200 · issued 30m access_token
        </div>
      </div>
      <div className="space-y-2">
        <div className="rounded-md border border-white/[0.06] bg-white/[0.02] p-3 font-mono text-[10px]">
          <div className="mb-1.5 text-faint">token.claims</div>
          <div className="space-y-1 text-zinc-400">
            <div>sub: &quot;user:12&quot;</div>
            <div>type: &quot;access&quot;</div>
            <div>roles: [&quot;admin&quot;]</div>
            <div>exp: 1735603200</div>
          </div>
        </div>
        <div className="rounded-md border border-white/[0.06] bg-white/[0.02] p-3 font-mono text-[10px]">
          <div className="mb-1.5 text-faint">flow</div>
          <div className="space-y-1 text-zinc-500">
            <div><CodeChip>Bearer</CodeChip> header → verify sig</div>
            <div><CodeChip tone="emerald">type ok</CodeChip> → attach user</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function DashboardPanel() {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MiniStat label="Requests" value="12.4k" delta="+18%" good />
        <MiniStat label="p95 latency" value="128ms" delta="-43%" good />
        <MiniStat label="Cache hits" value="72%" delta="+6%" good />
        <MiniStat label="Errors" value="0.3%" delta="−0.1%" good />
      </div>
      <div className="grid gap-3 lg:grid-cols-[1.6fr_1fr]">
        <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-mono text-[10px] text-faint">throughput · 60m</span>
            <CodeChip tone="cyan">live</CodeChip>
          </div>
          <div className="h-[150px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={AREA_DATA} margin={{ top: 4, right: 0, bottom: 0, left: -28 }}>
                <defs>
                  <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#818cf8" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="t" tick={{ fontSize: 9, fill: "#5D6270" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 9, fill: "#5D6270" }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: "#0c0c14", border: "1px solid rgba(255,255,255,0.1)", fontSize: 11 }}
                  labelStyle={{ color: "#a1a1aa" }}
                  itemStyle={{ color: "#818cf8" }}
                  cursor={{ stroke: "rgba(255,255,255,0.1)" }}
                />
                <Area type="monotone" dataKey="v" stroke="#22d3ee" strokeWidth={1.5} fill="url(#areaFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
          <div className="mb-2 font-mono text-[10px] text-faint">top endpoints</div>
          <div className="space-y-1.5">
            {ENDPOINTS.map((e) => (
              <div key={e.path} className="flex items-center justify-between gap-2 rounded-md border border-white/[0.05] bg-black/30 px-2 py-1.5">
                <div className="flex min-w-0 items-center gap-2">
                  <CodeChip tone={e.m === "GET" ? "cyan" : "violet"}>{e.m}</CodeChip>
                  <span className="truncate font-mono text-[10px] text-zinc-300">{e.path}</span>
                </div>
                <span className="shrink-0 font-mono text-[9px] tabular-nums text-faint">{e.p95}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function AnalyticsPanel() {
  return (
    <div className="grid gap-3 lg:grid-cols-[1.6fr_1fr]">
      <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="font-mono text-[10px] text-faint">latency distribution</span>
          <CodeChip tone="cyan">p99 310ms</CodeChip>
        </div>
        <div className="h-[160px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={BAR_DATA} margin={{ top: 4, right: 0, bottom: 0, left: -28 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="r" tick={{ fontSize: 9, fill: "#5D6270" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 9, fill: "#5D6270" }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "#0c0c14", border: "1px solid rgba(255,255,255,0.1)", fontSize: 11 }}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar dataKey="v" fill="#818cf8" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="space-y-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
        <div className="mb-1 font-mono text-[10px] text-faint">percentiles</div>
        {[
          { k: "p50", v: "41ms" },
          { k: "p90", v: "96ms" },
          { k: "p95", v: "128ms" },
          { k: "p99", v: "310ms" },
        ].map((p) => (
          <div key={p.k} className="flex items-center justify-between border-b border-white/[0.05] py-1.5 last:border-0">
            <span className="font-mono text-[11px] text-zinc-300">{p.k}</span>
            <span className="font-mono text-[11px] tabular-nums text-zinc-500">{p.v}</span>
          </div>
        ))}
        <div className="mt-2 flex items-center gap-1.5 rounded-md border border-amber-400/20 bg-amber-400/[0.05] px-2 py-1.5 font-mono text-[9px] text-amber-300/90">
          <AlertTriangle className="h-3 w-3 shrink-0 text-amber-300" />
          POST /v1/checkout at p95 212ms — below SLO
        </div>
      </div>
    </div>
  )
}

const RULES = [
  { key: "/v1/products*", ttl: "300s", mode: "public" },
  { key: "/v1/checkout*", ttl: "60s", mode: "user-keyed" },
  { key: "/v1/orders*", ttl: "600s", mode: "user-keyed" },
  { key: "/static/*", ttl: "86400s", mode: "public" },
]

function RulesPanel() {
  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-lg border border-white/[0.06] bg-white/[0.02]">
        <div className="grid grid-cols-[1.6fr_0.8fr_1fr_0.6fr] gap-2 border-b border-white/[0.06] px-3 py-2 font-mono text-[9px] uppercase tracking-wider text-faint">
          <span>rule pattern</span>
          <span>ttl</span>
          <span>keying</span>
          <span className="text-right">enabled</span>
        </div>
        {RULES.map((r) => (
          <div
            key={r.key}
            className="grid grid-cols-[1.6fr_0.8fr_1fr_0.6fr] items-center gap-2 border-b border-white/[0.05] px-3 py-2 last:border-0"
          >
            <code className="truncate font-mono text-[10px] text-zinc-300">{r.key}</code>
            <span className="font-mono text-[10px] text-zinc-500">{r.ttl}</span>
            <span className="font-mono text-[10px] text-zinc-500">{r.mode}</span>
            <div className="flex justify-end">
              <Switch />
            </div>
          </div>
        ))}
      </div>
      <div className="rounded-md border border-white/[0.06] bg-black/30 px-3 py-2 font-mono text-[10px] text-zinc-500">
        <span className="text-accent-cyan">POST /v1/rules</span> {"{ pattern, ttl, keying }"} → rule created · applied to next request
      </div>
    </div>
  )
}

const CACHE_ROUTES = [
  { path: "/static/*", hit: 99 },
  { path: "/v1/products*", hit: 94 },
  { path: "/v1/orders*", hit: 88 },
  { path: "/v1/checkout*", hit: 61 },
]

function CacheMetricsPanel() {
  return (
    <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr]">
      <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="font-mono text-[10px] text-faint">cache hit ratio · 24h</span>
          <CodeChip tone="emerald">72% · +6.4%</CodeChip>
        </div>
        <div className="flex h-2.5 w-full overflow-hidden rounded-full border border-white/[0.06] bg-black/40">
          <div className="h-full w-[72%] rounded-full bg-gradient-to-r from-accent-indigo to-accent-cyan" />
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2">
          {[
            { k: "keys stored", v: "48.2k" },
            { k: "evictions", v: "1.1k" },
            { k: "avg ttl", v: "412s" },
          ].map((m) => (
            <div key={m.k} className="rounded-md border border-white/[0.05] bg-black/30 px-2 py-1.5">
              <div className="font-mono text-[9px] uppercase tracking-wider text-faint">{m.k}</div>
              <div className="mt-0.5 font-mono text-[13px] font-semibold tabular-nums text-zinc-200">{m.v}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
        <div className="mb-2 font-mono text-[10px] text-faint">hit ratio by route</div>
        <div className="space-y-2.5">
          {CACHE_ROUTES.map((r) => (
            <div key={r.path}>
              <div className="mb-1 flex items-center justify-between font-mono text-[10px]">
                <span className="truncate text-zinc-300">{r.path}</span>
                <span className="tabular-nums text-accent-cyan">{r.hit}%</span>
              </div>
              <div className="h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent-indigo to-accent-cyan"
                  style={{ width: `${r.hit}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const DOC_ROWS = [
  { m: "GET", path: "/v1/rules", desc: "list cache rules", tone: "cyan" as const },
  { m: "POST", path: "/v1/rules", desc: "create rule", tone: "violet" as const },
  { m: "PATCH", path: "/v1/rules/:id", desc: "update rule", tone: "violet" as const },
  { m: "GET", path: "/v1/analytics", desc: "percentiles + hits", tone: "cyan" as const },
  { m: "GET", path: "/v1/status", desc: "health check", tone: "cyan" as const },
]

function DocsPanel() {
  return (
    <div className="space-y-2">
      {DOC_ROWS.map((d) => (
        <div key={d.path} className="flex items-center gap-3 rounded-md border border-white/[0.05] bg-white/[0.02] px-3 py-2">
          <CodeChip tone={d.tone as "cyan" | "violet"}>{d.m}</CodeChip>
          <code className="flex-1 truncate font-mono text-[10px] text-zinc-300">{d.path}</code>
          <span className="hidden font-mono text-[9px] text-faint sm:block">{d.desc}</span>
          <span className="font-mono text-[9px] text-zinc-600">→ /docs</span>
        </div>
      ))}
    </div>
  )
}

/* ---------- UX pattern demos ---------- */

function CommandPaletteDemo() {
  const rows = [
    { icon: <Gauge className="h-3 w-3 text-accent-cyan" />, label: "Launch dashboard", hint: "/dashboard" },
    { icon: <ListTree className="h-3 w-3 text-amber-300" />, label: "New cache rule", hint: "/v1/rules" },
    { icon: <BookOpen className="h-3 w-3 text-violet-300" />, label: "API reference", hint: "/docs/api" },
  ]
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-[10px] text-faint">command palette</span>
        <CodeChip tone="cyan">⌘K</CodeChip>
      </div>
      <div className="overflow-hidden rounded-lg border border-white/[0.08] bg-black/50">
        <div className="flex items-center gap-2 border-b border-white/[0.06] px-3 py-2">
          <Command className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
          <span className="font-mono text-[10px] text-zinc-500">jump to…</span>
          <kbd className="ml-auto rounded border border-white/10 bg-white/[0.04] px-1 py-px font-mono text-[8px] text-zinc-500">
            esc
          </kbd>
        </div>
        <div className="space-y-0.5 p-1.5">
          {rows.map((r, i) => (
            <div
              key={r.label}
              className={cn(
                "flex items-center gap-2 rounded px-2 py-1.5",
                i === 0 && "bg-white/[0.07]",
              )}
            >
              <span className="shrink-0">{r.icon}</span>
              <span className={cn("font-mono text-[10px]", i === 0 ? "text-white" : "text-zinc-400")}>
                {r.label}
              </span>
              <span className="ml-auto font-mono text-[8px] text-zinc-600">{r.hint}</span>
              {i === 0 && <ChevronRight className="h-3 w-3 text-accent-cyan" />}
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between border-t border-white/[0.06] px-3 py-1.5 font-mono text-[8px] text-zinc-600">
          <span>↑↓ navigate</span>
          <span>↵ open</span>
        </div>
      </div>
    </div>
  )
}

const ROLE_PERMS = {
  admin: [
    { k: "cache.rules.write", on: true },
    { k: "rate.limit.write", on: true },
    { k: "analytics.read", on: true },
    { k: "docs.view", on: true },
  ],
  developer: [
    { k: "cache.rules.write", on: false },
    { k: "rate.limit.write", on: false },
    { k: "analytics.read", on: true },
    { k: "docs.view", on: true },
  ],
}

function RoleToggleDemo() {
  const [role, setRole] = useState<"admin" | "developer">("admin")
  const perms = ROLE_PERMS[role]
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-[10px] text-faint">role-based ui</span>
        <span className="font-mono text-[9px] text-zinc-600">permissions</span>
      </div>
      <div className="flex items-center gap-1 rounded-md border border-white/[0.08] bg-black/40 p-1">
        {(["admin", "developer"] as const).map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => setRole(r)}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 rounded px-2 py-1.5 font-mono text-[10px] transition-colors",
              role === r ? "bg-accent-indigo/25 text-white" : "text-zinc-500 hover:text-zinc-300",
            )}
          >
            {r === "admin" ? (
              <UserCog className="h-3 w-3" />
            ) : (
              <Users className="h-3 w-3" />
            )}
            {r}
          </button>
        ))}
      </div>
      <div className="mt-2.5 space-y-1.5">
        {perms.map((p) => (
          <div key={p.k} className="flex items-center justify-between rounded-md border border-white/[0.05] bg-black/30 px-2 py-1.5">
            <code className="font-mono text-[10px] text-zinc-300">{p.k}</code>
            <Switch on={p.on} />
          </div>
        ))}
      </div>
      <div className="mt-2 font-mono text-[9px] text-faint">
        <span className={role === "admin" ? "text-accent-cyan" : "text-zinc-500"}>
          {role === "admin" ? "claims.roles → [admin]" : "claims.roles → [developer]"}
        </span>{" "}
        · UI hides write tools
      </div>
    </div>
  )
}

const ADVANCED_ROWS = [
  { key: "cache.ttl_override", desc: "override rule TTL per request", code: "Cache-Control: max-age=60" },
  { key: "cache.invalidate", desc: "purge keys on write", code: "DELETE /v1/cache/rules/:id" },
  { key: "webhook.retries", desc: "async retry backoff", code: "retry: 3 · backoff: exp" },
]

function DisclosureDemo() {
  const [openKey, setOpenKey] = useState<string | null>(null)
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-[10px] text-faint">progressive disclosure</span>
        <CodeChip tone="violet">advanced</CodeChip>
      </div>
      <div className="space-y-1.5">
        {ADVANCED_ROWS.map((row) => {
          const open = openKey === row.key
          return (
            <div key={row.key} className="overflow-hidden rounded-md border border-white/[0.05] bg-black/30">
              <button
                type="button"
                onClick={() => setOpenKey(open ? null : row.key)}
                className="flex w-full items-center gap-2 px-2.5 py-2 text-left"
              >
                <ChevronDown
                  className={cn(
                    "h-3 w-3 shrink-0 text-zinc-500 transition-transform",
                    open ? "rotate-0" : "-rotate-90",
                  )}
                />
                <span className="flex-1 truncate font-mono text-[10px] text-zinc-300">{row.key}</span>
                <span className="hidden truncate font-mono text-[9px] text-faint sm:block">{row.desc}</span>
              </button>
              <AnimatePresence initial={false}>
                {open && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                    className="overflow-hidden"
                  >
                    <div className="border-t border-white/[0.05] px-3 py-2">
                      <code className="font-mono text-[9px] text-accent-cyan">{row.code}</code>
                      <div className="mt-1 font-mono text-[9px] text-zinc-500">
                        applied to {row.key.replace(/[._]/g, " ")}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>
      <div className="mt-2 flex items-center gap-1.5 font-mono text-[9px] text-faint">
        <SlidersHorizontal className="h-3 w-3 text-zinc-600" />
        defaults hide the long tail of knobs
      </div>
    </div>
  )
}

const TABLE_ROWS = [
  { m: "GET", path: "/v1/products", req: "4.2k", p95: "41ms", err: "0.1%", spark: [3, 5, 4, 6, 8, 7, 9] },
  { m: "GET", path: "/v1/checkout/status", req: "3.1k", p95: "38ms", err: "0.0%", spark: [4, 3, 5, 4, 6, 5, 7] },
  { m: "POST", path: "/v1/checkout", req: "1.8k", p95: "212ms", err: "1.2%", spark: [2, 4, 3, 5, 4, 6, 5] },
  { m: "GET", path: "/v1/orders", req: "1.4k", p95: "66ms", err: "0.2%", spark: [5, 6, 5, 7, 6, 8, 7] },
  { m: "GET", path: "/v1/users/me", req: "3.6k", p95: "29ms", err: "0.0%", spark: [6, 5, 7, 6, 8, 7, 9] },
]

function DataTableDemo() {
  const [q, setQ] = useState("")
  const rows = TABLE_ROWS.filter(
    (r) => r.path.toLowerCase().includes(q.toLowerCase()) || r.m.toLowerCase().includes(q.toLowerCase()),
  )
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] text-faint">endpoints · data-dense</span>
        <div className="flex items-center gap-1.5 rounded-md border border-white/[0.08] bg-black/40 px-2 py-1">
          <Search className="h-3 w-3 text-zinc-500" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="filter…"
            className="w-20 bg-transparent font-mono text-[9px] text-zinc-300 placeholder:text-zinc-600 focus:outline-none"
          />
        </div>
      </div>
      <div className="max-h-[190px] overflow-auto rounded-md border border-white/[0.05]">
        <table className="w-full border-collapse font-mono">
          <thead className="sticky top-0 z-10">
            <tr className="bg-panel/95 backdrop-blur">
              {["method", "endpoint", "requests", "p95", "trend"].map((h) => (
                <th
                  key={h}
                  className={cn(
                    "border-b border-white/[0.06] px-2.5 py-1.5 text-left font-mono text-[8px] uppercase tracking-wider text-faint",
                    h === "requests" || h === "p95" ? "text-right" : "",
                  )}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.path} className="border-b border-white/[0.04] last:border-0 hover:bg-white/[0.03]">
                <td className="px-2.5 py-1.5">
                  <CodeChip tone={r.m === "GET" ? "cyan" : "violet"}>{r.m}</CodeChip>
                </td>
                <td className="px-2.5 py-1.5">
                  <span className="whitespace-nowrap text-[9px] text-zinc-300">{r.path}</span>
                </td>
                <td className="px-2.5 py-1.5 text-right text-[9px] tabular-nums text-zinc-400">{r.req}</td>
                <td className="px-2.5 py-1.5 text-right text-[9px] tabular-nums text-zinc-400">{r.p95}</td>
                <td className="px-2.5 py-1.5">
                  <svg viewBox="0 0 40 12" className="h-3 w-10">
                    {r.spark.map((v, i, arr) => {
                      const max = Math.max(...arr)
                      const x = (i / (arr.length - 1)) * 38 + 1
                      const y = 10 - (v / max) * 8
                      return <circle key={i} cx={x} cy={y} r="1.2" fill={r.err === "0.0%" ? "#34D399" : "#22D3EE"} />
                    })}
                  </svg>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-2.5 py-4 text-center text-[9px] text-zinc-600">
                  no endpoints match &quot;{q}&quot;
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-2 flex items-center gap-1.5 font-mono text-[9px] text-faint">
        <Workflow className="h-3 w-3 text-zinc-600" />
        sticky header · inline filter · right-aligned numbers
      </div>
    </div>
  )
}

/* ---------- skeleton ---------- */

function PanelSkeleton() {
  return (
    <div className="grid gap-3 lg:grid-cols-[1.6fr_1fr]">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="shimmer h-[52px] animate-pulse rounded-lg border border-white/[0.06] bg-white/[0.03]" />
          ))}
        </div>
        <div className="shimmer h-[150px] animate-pulse rounded-lg border border-white/[0.06] bg-white/[0.03]" />
        <div className="shimmer h-[72px] animate-pulse rounded-lg border border-white/[0.06] bg-white/[0.03]" />
      </div>
      <div className="shimmer h-[220px] animate-pulse rounded-lg border border-white/[0.06] bg-white/[0.03]" />
    </div>
  )
}

/* ---------- tabs ---------- */

const TABS = [
  { value: "login", label: "Login", icon: Lock },
  { value: "dashboard", label: "Dashboard", icon: Gauge },
  { value: "analytics", label: "Analytics", icon: BarChart3 },
  { value: "cache", label: "Cache Metrics", icon: Database },
  { value: "rules", label: "Cache Rules", icon: ListTree },
  { value: "patterns", label: "UX Patterns", icon: SlidersHorizontal },
  { value: "docs", label: "API Docs", icon: BookOpen },
] as const

const PANELS: Record<(typeof TABS)[number]["value"], React.ReactNode> = {
  login: <LoginPanel />,
  dashboard: <DashboardPanel />,
  analytics: <AnalyticsPanel />,
  cache: <CacheMetricsPanel />,
  rules: <RulesPanel />,
  patterns: (
    <div className="grid gap-3 sm:grid-cols-2">
      <CommandPaletteDemo />
      <RoleToggleDemo />
      <DisclosureDemo />
      <DataTableDemo />
    </div>
  ),
  docs: <DocsPanel />,
}

export function DashboardPreview({
  eyebrow = "04 · the dashboard",
  title = (
    <>
      Everything you need,
      <span className="text-gradient"> one panel away.</span>
    </>
  ),
  description = "Auth, monitoring, and cache rules ship with a working management UI — no external admin tool required.",
}: {
  eyebrow?: string
  title?: React.ReactNode
  description?: string
}) {
  const [active, setActive] = useState<(typeof TABS)[number]["value"]>("dashboard")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 700)
    return () => clearTimeout(t)
  }, [])

  function onTabChange(v: string) {
    setLoading(true)
    setActive(v as (typeof TABS)[number]["value"])
    setTimeout(() => setLoading(false), 450)
  }

  return (
    <section id="dashboard" className="relative scroll-mt-24 py-24">
      <div className="container">
        <SectionHeading
          eyebrow={eyebrow}
          title={title}
          description={description}
        />

        <Reveal delay={0.1}>
          <div className="relative mx-auto mt-14 max-w-4xl">
            <div className="pointer-events-none absolute -inset-8 rounded-[32px] bg-[radial-gradient(60%_60%_at_50%_50%,rgba(99,102,241,0.12),transparent_70%)]" />

            {/* browser chrome */}
            <div className="frame-brutal relative overflow-hidden rounded-xl bg-panel shadow-[0_24px_80px_-24px_rgba(0,0,0,0.8)]">
              <span className="sticker absolute -top-3.5 left-8 z-10 rotate-[-1deg] bg-panel">
                dashboard · live preview
              </span>
              <div className="flex items-center gap-3 border-b border-white/[0.06] bg-white/[0.02] px-4 py-2.5">
                <div className="flex gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
                  <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
                  <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
                </div>
                <div className="flex flex-1 items-center gap-2 rounded-md border border-white/[0.06] bg-black/40 px-3 py-1">
                  <Globe className="h-3 w-3 text-zinc-500" />
                  <span className="truncate font-mono text-[11px] text-zinc-500">
                    app.acme.dev/admin
                  </span>
                  <span className="ml-auto hidden items-center gap-1 font-mono text-[9px] text-emerald-300 sm:flex">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    live
                  </span>
                </div>
              </div>

              <Tabs.Root value={active} onValueChange={onTabChange} defaultValue="dashboard">
                <Tabs.List className="flex items-center gap-1 overflow-x-auto border-b border-white/[0.06] px-3 pt-2">
                  {TABS.map((t) => {
                    const Icon = t.icon
                    return (
                      <Tabs.Trigger
                        key={t.value}
                        value={t.value}
                        className="flex shrink-0 items-center gap-1.5 rounded-t-md border border-transparent border-b-white/[0.06] px-3 py-2 font-mono text-[11px] text-faint transition-colors data-[state=active]:border-white/10 data-[state=active]:bg-white/[0.04] data-[state=active]:text-zinc-100"
                      >
                        <Icon className="h-3 w-3" />
                        {t.label}
                      </Tabs.Trigger>
                    )
                  })}
                </Tabs.List>

                <div className="relative min-h-[340px] p-4 sm:p-5">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={loading ? `skeleton-${active}` : active}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.25, ease: "easeOut" }}
                    >
                      <Tabs.Content value="login" className="outline-none">
                        {loading ? <PanelSkeleton /> : PANELS.login}
                      </Tabs.Content>
                      <Tabs.Content value="dashboard" className="outline-none">
                        {loading ? <PanelSkeleton /> : PANELS.dashboard}
                      </Tabs.Content>
                      <Tabs.Content value="analytics" className="outline-none">
                        {loading ? <PanelSkeleton /> : PANELS.analytics}
                      </Tabs.Content>
                      <Tabs.Content value="cache" className="outline-none">
                        {loading ? <PanelSkeleton /> : PANELS.cache}
                      </Tabs.Content>
                      <Tabs.Content value="rules" className="outline-none">
                        {loading ? <PanelSkeleton /> : PANELS.rules}
                      </Tabs.Content>
                      <Tabs.Content value="patterns" className="outline-none">
                        {loading ? <PanelSkeleton /> : PANELS.patterns}
                      </Tabs.Content>
                      <Tabs.Content value="docs" className="outline-none">
                        {loading ? <PanelSkeleton /> : PANELS.docs}
                      </Tabs.Content>
                    </motion.div>
                  </AnimatePresence>
                </div>
              </Tabs.Root>

              {/* status bar */}
              <div className="flex items-center gap-4 border-t border-white/[0.06] bg-white/[0.02] px-4 py-2 font-mono text-[9px] text-faint">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="h-3 w-3 text-emerald-400" />
                  TLS · HTTP/2
                </span>
                <span className="flex items-center gap-1.5">
                  <Activity className="h-3 w-3 text-accent-cyan" />
                  99.9% uptime
                </span>
                <span className="ml-auto hidden items-center gap-1.5 sm:flex">
                  <FileText className="h-3 w-3" />
                  v1.4.0
                </span>
                <span className="flex items-center gap-1.5">
                  <Settings2 className="h-3 w-3" />
                  admin
                </span>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
