"use client"

import { Sparkles } from "lucide-react"

import { Reveal } from "@/components/motion/reveal"
import { SectionHeading } from "@/components/section-heading"

const ITEMS = [
  { label: "Prometheus metrics", tag: "scrape /metrics" },
  { label: "Grafana dashboards", tag: "prebuilt panels" },
  { label: "OpenTelemetry traces", tag: "otlp · trace-id" },
  { label: "Kubernetes autoscaling", tag: "hpa · 50% util" },
  { label: "Redis Cluster", tag: "no single point" },
  { label: "AI cache suggestions", tag: "rules · auto TTL" },
]

export function Roadmap() {
  return (
    <section id="roadmap" className="relative scroll-mt-24 py-24">
      <div className="container">
        <SectionHeading
          eyebrow="06 · roadmap"
          title={
            <>
              Where this is
              <span className="text-gradient"> heading next.</span>
            </>
          }
          description="The core is done. These are the batteries that keep getting added — scroll the shelf."
        />

        <Reveal delay={0.1}>
          <div className="mt-10 flex gap-3 overflow-x-auto pb-4 mask-fade-x [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {ITEMS.map((item, i) => (
              <div
                key={item.label}
                className="group flex shrink-0 snap-start flex-col gap-2 rounded-xl border-2 border-dashed border-white/15 bg-white/[0.015] px-5 py-4 opacity-80 transition-all duration-300 hover:border-accent-cyan/40 hover:bg-white/[0.03] hover:opacity-100"
              >
                <div className="flex items-center justify-between gap-6">
                  <span className="flex items-center gap-2 font-mono text-[13px] text-zinc-300 transition-colors group-hover:text-white">
                    <span className="font-mono text-[10px] text-zinc-600">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    {item.label}
                  </span>
                  <span className="rounded border border-dashed border-white/20 px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-[0.18em] text-zinc-500">
                    soon
                  </span>
                </div>
                <span className="font-mono text-[10px] text-faint">{item.tag}</span>
              </div>
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.15}>
          <div className="mt-6 flex items-center justify-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-accent-cyan" />
            <span className="font-mono text-[11px] text-faint">
              suggestions welcome — the shelf is never full
            </span>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
