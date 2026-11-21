import Link from "next/link"

import { Logo } from "@/components/logo"
import { API_BASE_URL } from "@/lib/api"

export function Footer() {
  return (
    <footer className="bg-frost">
      <div className="container flex flex-col gap-6 py-10 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Logo />
          <p className="mt-3 max-w-xs text-[13px] leading-relaxed text-graphite">
            Admin console for the API Optimizer gateway: caching, rate limits, latency, AI usage and billing.
          </p>
        </div>
        <nav className="flex gap-10 text-[13px]">
          <div className="flex flex-col gap-2">
            <Link href="/login" className="text-ink hover:underline">
              Sign in
            </Link>
            <Link href="/status" className="text-ink hover:underline">
              System status
            </Link>
            <a href={`${API_BASE_URL}/metrics`} className="text-ink hover:underline">
              Prometheus metrics
            </a>
          </div>
          <div className="flex flex-col gap-2 text-graphite">
            <a href="#sections">Console sections</a>
            <a href="#access">Access and roles</a>
          </div>
        </nav>
      </div>
      <div className="border-t border-rule">
        <div className="container py-4 text-[12px] text-faint">Latency figures above: median of three questions measured on a local stack on 20 Nov 2026. The console shows your live traffic.</div>
      </div>
    </footer>
  )
}
