"use client"

import Link from "next/link"
import { motion, useReducedMotion } from "framer-motion"

import { Button } from "@/components/ui/button"

/* Measured on 20 Nov 2026: three questions through POST /api/v1/answers on a
 * local stack, each asked twice. Medians of the fresh answer (Gemini) and the
 * repeat served from the shared answer cache. */
const UPSTREAM_MS = 9695
const CACHED_MS = 959

export function Hero() {
  const reduce = useReducedMotion()
  const cachedShare = CACHED_MS / UPSTREAM_MS

  return (
    <section className="border-b border-rule bg-paper">
      <div className="container grid gap-12 py-16 lg:grid-cols-[1.1fr_1fr] lg:items-center lg:gap-16 lg:py-24">
        <div>
          <p className="mono-label">Admin console</p>
          <h1 className="mt-3 max-w-[16ch] text-[clamp(2.3rem,5.4vw,4rem)] font-semibold leading-[1.04] tracking-[-0.025em] text-ink">
            Run the API Optimizer gateway from one place.
          </h1>
          <p className="mt-6 max-w-[54ch] text-[17px] leading-relaxed text-graphite">
            Watch traffic and latency, decide what gets cached, set rate limits, follow AI usage and each
            user&apos;s charges, and review guardrail events, for the gateway and for the services it monitors.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button asChild variant="primary" size="lg">
              <Link href="/login">Sign in to the console</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/status">Check system status</Link>
            </Button>
          </div>
          <p className="mt-6 text-[13px] text-faint">
            For administrators, operators and viewers of this deployment. Access is by account; see{" "}
            <a href="#access" className="underline underline-offset-4 hover:text-ink">
              who can do what
            </a>
            .
          </p>
        </div>

        {/* The one moving thing on the page: the cached bar settles once. */}
        <figure className="housing" aria-label="Latency comparison for one endpoint">
          <div className="px-5 py-4">
            <p className="text-sm font-medium text-ink">What the shared answer cache saves</p>
            <p className="text-[12px] text-graphite">Median of three questions, measured 20 Nov 2026</p>
          </div>

          <div className="space-y-5 px-5 py-5">
            <LatencyBar label="Fresh answer from the model" ms={UPSTREAM_MS} share={1} color="bg-signal" reduce={reduce} delay={0} />
            <LatencyBar
              label="Asked again, shared cache hit"
              ms={CACHED_MS}
              share={cachedShare}
              color="bg-relay"
              reduce={reduce}
              delay={0.35}
            />
          </div>

          <figcaption className="flex items-center justify-between px-5 py-3 text-[12px] text-graphite">
            <span>Scale shared, 0 to {UPSTREAM_MS.toLocaleString("en-US")} ms</span>
            <span className="font-mono">
              {Math.round((1 - cachedShare) * 100)}% less time
            </span>
          </figcaption>
        </figure>
      </div>
    </section>
  )
}

function LatencyBar({
  label,
  ms,
  share,
  color,
  reduce,
  delay,
}: {
  label: string
  ms: number
  share: number
  color: string
  reduce: boolean | null
  delay: number
}) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-4">
        <span className="text-sm text-ink">{label}</span>
        <span className="font-mono text-sm text-ink">{ms.toLocaleString("en-US")} ms</span>
      </div>
      <div className="h-6 w-full border border-rule bg-frost">
        <motion.div
          className={`h-full ${color}`}
          initial={reduce ? { width: `${share * 100}%` } : { width: "100%" }}
          animate={{ width: `${share * 100}%` }}
          transition={{ duration: 1.1, delay, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
    </div>
  )
}
