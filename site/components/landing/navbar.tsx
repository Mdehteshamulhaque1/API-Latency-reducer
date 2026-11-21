"use client"

import * as React from "react"
import Link from "next/link"
import { Menu, X } from "lucide-react"

import { Logo } from "@/components/logo"
import { Button } from "@/components/ui/button"

const LINKS = [
  { href: "#sections", label: "Console" },
  { href: "#access", label: "Access" },
  { href: "/status", label: "System status" },
]

export function Navbar() {
  const [open, setOpen] = React.useState(false)

  return (
    <header className="sticky top-0 z-40 border-b border-rule bg-paper">
      <div className="container flex h-14 items-center justify-between">
        <Link href="/" aria-label="API Optimizer home">
          <Logo />
        </Link>

        <nav className="hidden items-center gap-7 md:flex">
          {LINKS.map((link) => (
            <a key={link.href} href={link.href} className="text-sm text-graphite transition-colors hover:text-ink">
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <Button asChild variant="primary" size="sm">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>

        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          className="flex h-9 w-9 items-center justify-center rounded border border-rule text-ink md:hidden"
        >
          {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </button>
      </div>

      {open && (
        <nav className="border-t border-rule bg-paper px-6 py-4 md:hidden">
          <div className="flex flex-col gap-3">
            {LINKS.map((link) => (
              <a key={link.href} href={link.href} onClick={() => setOpen(false)} className="text-sm text-ink">
                {link.label}
              </a>
            ))}
            <div className="mt-2 flex gap-2 border-t border-rule pt-4">
              <Button asChild variant="primary" size="sm" className="w-full">
                <Link href="/login">Sign in</Link>
              </Button>
            </div>
          </div>
        </nav>
      )}
    </header>
  )
}
