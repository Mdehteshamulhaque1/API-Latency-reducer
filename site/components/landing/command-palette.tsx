"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  CornerDownLeft,
  Gauge,
  Search,
  Settings2,
  Zap,
} from "lucide-react"

import { EASE } from "@/components/motion/reveal"
import { cn } from "@/lib/utils"

type Item = {
  id: string
  label: string
  hint: string
  group: string
  icon: React.ReactNode
  href: string
}

const GROUPS: { name: string; items: Item[] }[] = [
  {
    name: "Navigate",
    items: [
      { id: "nav-dashboard", label: "Launch dashboard", hint: "/dashboard", group: "Navigate", icon: <Gauge className="h-3.5 w-3.5 text-accent-cyan" />, href: "/dashboard" },
      { id: "nav-features", label: "Features", hint: "#features", group: "Navigate", icon: <Zap className="h-3.5 w-3.5 text-amber-300" />, href: "#features" },
      { id: "nav-architecture", label: "Architecture", hint: "#architecture", group: "Navigate", icon: <Settings2 className="h-3.5 w-3.5 text-violet-300" />, href: "#architecture" },
      { id: "nav-how", label: "How it works", hint: "#how", group: "Navigate", icon: <ArrowRight className="h-3.5 w-3.5 text-emerald-300" />, href: "#how" },
      { id: "nav-metrics", label: "Live metrics", hint: "#metrics", group: "Navigate", icon: <BarChart3 className="h-3.5 w-3.5 text-accent-cyan" />, href: "#metrics" },
      { id: "nav-roadmap", label: "Roadmap", hint: "#roadmap", group: "Navigate", icon: <BookOpen className="h-3.5 w-3.5 text-orange-300" />, href: "#roadmap" },
    ],
  },
  {
    name: "Docs & API",
    items: [
      { id: "docs-api", label: "API reference", hint: "/docs/api", group: "Docs & API", icon: <BookOpen className="h-3.5 w-3.5 text-violet-300" />, href: "#dashboard" },
      { id: "docs-cache", label: "Cache rules reference", hint: "/docs/cache", group: "Docs & API", icon: <Zap className="h-3.5 w-3.5 text-amber-300" />, href: "#dashboard" },
    ],
  },
]

const ALL_ITEMS = GROUPS.flatMap((g) => g.items)

export function openCommandPalette() {
  window.dispatchEvent(new Event("open-command-palette"))
}

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const reduce = useReducedMotion()

  const items = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return ALL_ITEMS
    return ALL_ITEMS.filter(
      (i) =>
        i.label.toLowerCase().includes(q) ||
        i.hint.toLowerCase().includes(q) ||
        i.group.toLowerCase().includes(q),
    )
  }, [query])

  useEffect(() => setActiveIdx(0), [query])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setOpen((v) => !v)
      }
      if (e.key === "Escape") setOpen(false)
    }
    function onOpen() {
      setOpen(true)
    }
    window.addEventListener("keydown", onKey)
    window.addEventListener("open-command-palette", onOpen)
    return () => {
      window.removeEventListener("keydown", onKey)
      window.removeEventListener("open-command-palette", onOpen)
    }
  }, [])

  useEffect(() => {
    if (open) {
      setQuery("")
      const t = setTimeout(() => inputRef.current?.focus(), 50)
      return () => clearTimeout(t)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowDown") {
        e.preventDefault()
        setActiveIdx((i) => (i + 1) % items.length)
      } else if (e.key === "ArrowUp") {
        e.preventDefault()
        setActiveIdx((i) => (i - 1 + items.length) % items.length)
      } else if (e.key === "Enter" && items[activeIdx]) {
        e.preventDefault()
        go(items[activeIdx])
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, items, activeIdx])

  function go(item: Item) {
    setOpen(false)
    setQuery("")
    if (item.href.startsWith("#")) {
      const el = document.querySelector(item.href)
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" })
        return
      }
    }
    window.location.href = item.href
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            initial={reduce ? false : { opacity: 0, y: -16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduce ? undefined : { opacity: 0, y: -12, scale: 0.98 }}
            transition={{ duration: 0.25, ease: EASE }}
            className="fixed left-1/2 top-[18%] z-[90] w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2"
          >
            <div className="frame-brutal overflow-hidden rounded-xl bg-panel shadow-panel">
              {/* input row */}
              <div className="flex items-center gap-3 border-b border-white/[0.07] px-4 py-3.5">
                <Search className="h-4 w-4 shrink-0 text-zinc-500" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search commands, sections, endpoints…"
                  className="w-full bg-transparent font-mono text-[13px] text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
                />
                <kbd className="hidden shrink-0 items-center gap-0.5 rounded border border-white/10 bg-white/[0.04] px-1.5 py-0.5 font-mono text-[9px] text-zinc-500 sm:flex">
                  esc
                </kbd>
              </div>

              {/* results */}
              <div className="max-h-[50vh] overflow-y-auto p-2">
                {items.length === 0 && (
                  <div className="px-3 py-8 text-center font-mono text-[11px] text-zinc-600">
                    no results for &quot;{query}&quot;
                  </div>
                )}

                {GROUPS.map((group) => {
                  const groupItems = items.filter((i) => i.group === group.name)
                  if (groupItems.length === 0) return null
                  return (
                    <div key={group.name} className="mb-1">
                      <div className="px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.18em] text-faint">
                        {group.name}
                      </div>
                      {groupItems.map((item) => {
                        const idx = items.indexOf(item)
                        const active = idx === activeIdx
                        return (
                          <button
                            key={item.id}
                            type="button"
                            onMouseEnter={() => setActiveIdx(idx)}
                            onClick={() => go(item)}
                            className={cn(
                              "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left transition-colors",
                              active ? "bg-white/[0.07]" : "bg-transparent",
                            )}
                          >
                            <span className="shrink-0">{item.icon}</span>
                            <span
                              className={cn(
                                "flex-1 font-mono text-[12px]",
                                active ? "text-white" : "text-zinc-300",
                              )}
                            >
                              {item.label}
                            </span>
                            <span className="shrink-0 font-mono text-[9px] text-zinc-600">
                              {item.hint}
                            </span>
                            <CornerDownLeft
                              className={cn(
                                "h-3 w-3 shrink-0 text-accent-cyan transition-opacity",
                                active ? "opacity-100" : "opacity-0",
                              )}
                            />
                          </button>
                        )
                      })}
                    </div>
                  )
                })}
              </div>

              {/* footer hints */}
              <div className="flex items-center justify-between border-t border-white/[0.07] px-4 py-2 font-mono text-[9px] text-zinc-600">
                <span className="flex items-center gap-1.5">
                  <kbd className="rounded border border-white/10 bg-white/[0.04] px-1 py-0.5">↑</kbd>
                  <kbd className="rounded border border-white/10 bg-white/[0.04] px-1 py-0.5">↓</kbd>
                  to navigate
                </span>
                <span className="flex items-center gap-1.5">
                  <kbd className="rounded border border-white/10 bg-white/[0.04] px-1 py-0.5">↵</kbd>
                  to open
                </span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
