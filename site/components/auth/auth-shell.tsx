"use client"

import * as React from "react"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"

import { Logo } from "@/components/logo"

const FACTS = [
  { term: "Monitor", detail: "Traffic, latency percentiles, errors and rate-limit rejections." },
  { term: "Control", detail: "Cache rules, cache invalidation and the knowledge base." },
  { term: "Account for", detail: "AI usage, provider cost and every user's charges." },
]

interface AuthShellProps {
  /** Kept for compatibility; no longer rendered. */
  eyebrow?: string
  title: string
  subtitle: string
  children: React.ReactNode
  footer: React.ReactNode
}

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <main className="min-h-screen bg-frost">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-8 lg:grid lg:grid-cols-[1fr_420px] lg:items-center lg:gap-20 lg:py-12">
        <section className="hidden lg:block">
          <Link href="/" className="inline-flex">
            <Logo />
          </Link>
          <h2 className="mt-16 max-w-md text-[40px] font-semibold leading-[1.05] tracking-[-0.02em] text-ink">
            API Optimizer admin console.
          </h2>
          <dl className="mt-12 max-w-md divide-y divide-rule border-y border-rule">
            {FACTS.map((fact) => (
              <div key={fact.term} className="grid grid-cols-[120px_1fr] gap-4 py-3">
                <dt className="text-sm font-medium text-ink">{fact.term}</dt>
                <dd className="text-sm text-graphite">{fact.detail}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="flex flex-1 flex-col justify-center">
          <div className="mb-8 lg:hidden">
            <Link href="/" aria-label="API Optimizer home" className="inline-flex">
              <Logo />
            </Link>
          </div>

          <div className="rounded border border-rule bg-paper p-6 sm:p-8">
            <h1 className="text-2xl font-semibold tracking-[-0.01em] text-ink">{title}</h1>
            <p className="mt-2 text-sm leading-relaxed text-graphite">{subtitle}</p>
            <div className="mt-7">{children}</div>
            <div className="mt-6 border-t border-rule pt-5 text-sm text-graphite">{footer}</div>
          </div>

          <Link
            href="/"
            className="mt-6 inline-flex items-center gap-2 text-[13px] text-graphite transition-colors hover:text-ink"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to the site
          </Link>
        </section>
      </div>
    </main>
  )
}
