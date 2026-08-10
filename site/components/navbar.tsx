"use client"

import { useEffect, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { ArrowUpRight, Menu, Search, X } from "lucide-react"

import { CommandPalette, openCommandPalette } from "@/components/command-palette"
import { Logo } from "@/components/logo"
import { Button } from "@/components/ui/button"
import { EASE } from "@/components/motion/reveal"
import { cn } from "@/lib/utils"

const LINKS = [
  { href: "#features", label: "Features" },
  { href: "#architecture", label: "Architecture" },
  { href: "#how", label: "How it works" },
  { href: "#metrics", label: "Metrics" },
  { href: "#roadmap", label: "Roadmap" },
]

export function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState<string>("")

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  useEffect(() => {
    const sections = LINKS.map((l) => document.querySelector(l.href))
      .filter((el): el is Element => Boolean(el))
    const ids = LINKS.map((l) => l.href.slice(1))

    if (sections.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActive(`#${entry.target.id}`)
          }
        }
      },
      { rootMargin: "-35% 0px -55% 0px", threshold: 0 },
    )

    sections.forEach((s) => observer.observe(s))
    return () => observer.disconnect()
  }, [])

  function onNavClick() {
    setOpen(false)
  }

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-all duration-300",
        scrolled
          ? "border-b border-white/10 bg-ink/70 backdrop-blur-xl"
          : "border-b border-transparent bg-transparent",
      )}
    >
      <nav className="container flex h-16 items-center justify-between">
        <a href="#top" onClick={onNavClick} className="shrink-0">
          <Logo />
        </a>

        <ul className="hidden items-center gap-7 md:flex">
          {LINKS.map((link) => {
            const isActive = active === link.href
            return (
              <li key={link.href}>
                <a
                  href={link.href}
                  aria-current={isActive ? "true" : undefined}
                  className={cn(
                    "group relative font-mono text-[12px] uppercase tracking-[0.12em] transition-colors",
                    isActive ? "text-white" : "text-zinc-400 hover:text-white",
                  )}
                >
                  {link.label}
                  <span
                    className={cn(
                      "absolute -bottom-1.5 left-0 h-px bg-gradient-to-r from-accent-indigo to-accent-cyan transition-all duration-300",
                      isActive ? "w-full opacity-100" : "w-0 opacity-0 group-hover:w-full group-hover:opacity-60",
                    )}
                  />
                </a>
              </li>
            )
          })}
        </ul>

        <div className="hidden items-center gap-2 md:flex">
          <button
            onClick={openCommandPalette}
            className="group hidden items-center gap-2 rounded-md border border-white/10 px-3 py-1.5 font-mono text-[12px] text-zinc-400 transition-colors hover:border-white/25 hover:text-zinc-100 lg:flex"
            aria-label="Open command palette"
          >
            <Search className="h-3.5 w-3.5" />
            Search
            <kbd className="ml-1 rounded border border-white/10 bg-white/[0.04] px-1 py-px font-mono text-[9px] text-zinc-500">
              ⌘K
            </kbd>
          </button>
          <Button asChild variant="ghost" size="sm">
            <a href="/dashboard">Log in</a>
          </Button>
          <Button asChild variant="primary" size="sm">
            <a href="/dashboard">
              Get started
              <ArrowUpRight className="h-3.5 w-3.5" />
            </a>
          </Button>
        </div>

        <button
          className="rounded-md border border-white/10 p-2 text-zinc-300 md:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="overflow-hidden border-t border-white/10 bg-ink/95 backdrop-blur-xl md:hidden"
          >
            <ul className="container flex flex-col gap-1 py-4">
              {LINKS.map((link) => {
                const isActive = active === link.href
                return (
                  <li key={link.href}>
                    <a
                      href={link.href}
                      onClick={onNavClick}
                      aria-current={isActive ? "true" : undefined}
                      className={cn(
                        "block rounded-md px-3 py-2 font-mono text-[13px] uppercase tracking-[0.12em] transition-colors",
                        isActive
                          ? "bg-white/[0.06] text-white"
                          : "text-zinc-300 hover:bg-white/5 hover:text-white",
                      )}
                    >
                      {link.label}
                    </a>
                  </li>
                )
              })}
              <li className="mt-2 flex gap-2 border-t border-white/10 pt-3">
                <Button asChild variant="ghost" size="sm" className="flex-1">
                  <a href="/dashboard" onClick={onNavClick}>
                    Log in
                  </a>
                </Button>
                <Button asChild variant="primary" size="sm" className="flex-1">
                  <a href="/dashboard" onClick={onNavClick}>
                    Get started
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </a>
                </Button>
              </li>
            </ul>
          </motion.div>
        )}
      </AnimatePresence>

      <CommandPalette />
    </header>
  )
}
