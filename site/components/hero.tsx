"use client"

import { motion, type Variants } from "framer-motion"
import { ArrowDown, ArrowUpRight } from "lucide-react"

import { Aurora, GridBackdrop } from "@/components/backgrounds"
import { LivePanel } from "@/components/live-panel"
import { Button } from "@/components/ui/button"
import { EASE } from "@/components/motion/reveal"
import { cn } from "@/lib/utils"

const container: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.09, delayChildren: 0.15 } },
}

const word: Variants = {
  hidden: { opacity: 0, y: 34, filter: "blur(6px)" },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.75, ease: EASE },
  },
}

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: EASE },
  },
}

/** One headline phrase: mixed weight (heavy/light) with optional accent gradient. */
function Phrase({
  heavy,
  light,
  accent = false,
}: {
  heavy: string
  light: string
  accent?: boolean
}) {
  return (
    <span className="block">
      <motion.span
        variants={word}
        className="mr-[0.18em] inline-block font-extrabold tracking-[-0.04em] text-zinc-50"
      >
        {heavy}
      </motion.span>
      <motion.span
        variants={word}
        className={cn(
          "inline-block font-normal tracking-[-0.04em]",
          accent ? "text-gradient font-medium" : "text-zinc-400",
        )}
      >
        {light}
      </motion.span>
    </span>
  )
}

export function Hero() {
  return (
    <section id="top" className="relative overflow-hidden pb-24 pt-36 sm:pt-44">
      <Aurora />
      <GridBackdrop className="opacity-60" />

      <div className="container relative">
        <div className="grid items-center gap-16 lg:grid-cols-[1.1fr_0.9fr] lg:gap-10">
          {/* left — copy */}
          <motion.div
            variants={container}
            initial="hidden"
            animate="visible"
            className="text-center lg:text-left"
          >
            <motion.div variants={fadeUp} className="flex justify-center lg:justify-start">
              <span className="sticker gap-2.5 bg-surface">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                </span>
                [live] · 99.9% uptime
              </span>
            </motion.div>

            <motion.h1 className="mt-6 max-w-2xl text-[clamp(2.8rem,7vw,6rem)] font-medium leading-[0.95] tracking-[-0.03em] text-zinc-50">
              <Phrase heavy="Cut" light="latency." accent />
              <Phrase heavy="Ship" light="faster." accent />
            </motion.h1>

            <motion.p
              variants={fadeUp}
              className="mx-auto mt-6 max-w-md text-pretty text-[15px] leading-relaxed text-dim lg:mx-0"
            >
              A drop-in FastAPI gateway that caches, throttles, and monitors every
              request — so your users feel nothing but speed.
            </motion.p>

            <motion.div
              variants={fadeUp}
              className="mt-9 flex flex-wrap items-center justify-center gap-3 lg:justify-start"
            >
              <Button asChild variant="primary" size="lg">
                <a href="/dashboard">
                  Launch the dashboard
                  <ArrowUpRight className="h-4 w-4" />
                </a>
              </Button>
              <Button asChild variant="outline" size="lg">
                <a href="#how">
                  See how it works
                  <ArrowDown className="h-4 w-4" />
                </a>
              </Button>
            </motion.div>

            <motion.div
              variants={fadeUp}
              className="mt-8 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 font-mono text-[10px] uppercase tracking-[0.14em] text-faint lg:justify-start"
            >
              <span>no infra changes</span>
              <span className="text-zinc-600">/</span>
              <span>redis-backed</span>
              <span className="text-zinc-600">/</span>
              <span>prometheus-ready</span>
            </motion.div>
          </motion.div>

          {/* right — live metrics panel */}
          <div className="mx-auto w-full max-w-md lg:max-w-none">
            <LivePanel />
          </div>
        </div>
      </div>
    </section>
  )
}
