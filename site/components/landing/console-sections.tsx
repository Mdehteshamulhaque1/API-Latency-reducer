import {
  Activity,
  BookOpen,
  Bot,
  Coins,
  Database,
  Gauge,
  LayoutDashboard,
  LineChart,
  ShieldAlert,
  SlidersHorizontal,
  Timer,
  Wallet,
} from "lucide-react"

/* The console's sidebar, in its order (components/dashboard/shell.tsx). */
const SECTIONS = [
  { icon: LayoutDashboard, name: "Overview", detail: "Requests, latency, error rate and service health for the last 24 hours." },
  { icon: LineChart, name: "Analytics", detail: "p50, p95 and p99 latency, slowest endpoints, traffic split and a searchable request log." },
  { icon: Database, name: "Cache", detail: "Redis hit rate, cached entries and invalidation, plus the shared AI answer cache and its costs." },
  { icon: SlidersHorizontal, name: "Cache rules", detail: "Choose which endpoints are cached, for how long, and what the cache key varies by." },
  { icon: Timer, name: "Rate limits", detail: "The limit for each tier, your own bucket, and every request rejected with HTTP 429." },
  { icon: Gauge, name: "LLM gateway", detail: "Chat traffic, cache hit rate, latency over time and a before-and-after benchmark." },
  { icon: Bot, name: "Assistant", detail: "Ask questions about your traffic; answers cite the measured facts they use." },
  { icon: BookOpen, name: "Knowledge base", detail: "Upload PDF, text or Markdown documents and test grounded answers against them." },
  { icon: Coins, name: "AI usage", detail: "Model calls, tokens, latency and estimated provider cost, by model and by call." },
  { icon: Wallet, name: "Pricing", detail: "Model price tables and every user's billable tokens and charges." },
  { icon: ShieldAlert, name: "Guardrails", detail: "Blocked prompt injections, masked personal data, and a dry-run checker." },
  { icon: Activity, name: "System status", detail: "Live checks of the API, database and Redis. Open to anyone, no sign-in needed." },
]

export function ConsoleSections() {
  return (
    <section id="sections" className="border-b border-rule">
      <div className="container py-16 lg:py-20">
        <div className="max-w-2xl">
          <h2 className="text-[clamp(1.8rem,3.5vw,2.6rem)] font-semibold leading-tight tracking-[-0.02em] text-ink">
            What you manage in the console
          </h2>
          <p className="mt-4 text-[16px] leading-relaxed text-graphite">
            Every view reads live data from the gateway. Switch between the gateway itself and the services it
            monitors from the selector at the top of the console.
          </p>
        </div>

        <ul className="mt-12 grid border-t border-rule sm:grid-cols-2 sm:gap-x-12 lg:grid-cols-3">
          {SECTIONS.map((section) => (
            <li key={section.name} className="flex gap-3 border-b border-rule py-5">
              <section.icon className="mt-0.5 h-4 w-4 shrink-0 text-graphite" aria-hidden />
              <div>
                <p className="text-[15px] font-medium text-ink">{section.name}</p>
                <p className="mt-1 text-[14px] leading-relaxed text-graphite">{section.detail}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
