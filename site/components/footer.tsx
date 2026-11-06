import { Zap } from "lucide-react"

const COLUMNS = [
  {
    title: "Product",
    links: ["Features", "Architecture", "Metrics", "Dashboard"],
  },
  {
    title: "Resources",
    links: ["Documentation", "API Reference", "GitHub", "Changelog"],
  },
  {
    title: "Legal",
    links: ["Privacy", "Terms", "Security", "License"],
  },
]

export function Footer() {
  return (
    <footer className="relative border-t border-white/[0.07] bg-black/30">
      <div className="container">
        <div className="grid gap-10 py-14 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div className="max-w-xs">
            <a href="#top" className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/[0.04]">
                <Zap className="h-4 w-4 text-accent-cyan" />
              </span>
              <span className="font-mono text-sm font-semibold text-zinc-100">
                API Optimizer
              </span>
            </a>
            <p className="mt-4 font-mono text-[11px] leading-relaxed text-faint">
              A FastAPI gateway that caches, throttles, and monitors — so your
              users feel nothing but speed.
            </p>
            <div className="mt-5 flex items-center gap-2 font-mono text-[10px] text-emerald-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              all systems operational
            </div>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h4 className="font-mono text-[10px] uppercase tracking-[0.18em] text-faint">
                {col.title}
              </h4>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((link) => (
                  <li key={link}>
                    <a
                      href="#top"
                      className="font-mono text-[12px] text-zinc-500 transition-colors hover:text-zinc-200"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="flex flex-col items-center justify-between gap-3 border-t border-white/[0.06] py-6 sm:flex-row">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-mono text-[10px] text-zinc-600">
              © 2026 API Optimizer
            </span>
            <span className="rounded border-2 border-zinc-100/20 px-2 py-1 font-mono text-[9px] uppercase tracking-[0.14em] text-zinc-400">
              built with fastapi + redis
            </span>
          </div>
          <span className="font-mono text-[10px] text-zinc-600">
            ship less, cache more
          </span>
        </div>
      </div>
    </footer>
  )
}
