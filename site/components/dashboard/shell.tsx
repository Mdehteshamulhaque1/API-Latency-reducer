"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import {
  Activity,
  BookOpen,
  Bot,
  Coins,
  Database,
  Gauge,
  LayoutDashboard,
  LineChart,
  LogOut,
  Menu,
  MessageSquare,
  ShieldAlert,
  SlidersHorizontal,
  Timer,
  Users,
  Wallet,
  X,
} from "lucide-react"

import { ServiceSwitch } from "@/components/dashboard/service-switch"
import { UserSwitch, ViewAsBanner } from "@/components/dashboard/user-switch"
import { Logo } from "@/components/logo"
import { Pill, type PillTone } from "@/components/ui/pill"
import { apiHealth, authLogout, type HealthResponse } from "@/lib/api"
import { useAuth, usePolling } from "@/lib/use-auth"
import { MonitoredServiceProvider, useMonitoredService } from "@/lib/use-service"
import { ViewAsProvider, useViewAs } from "@/lib/use-view-as"
import { cn } from "@/lib/utils"

interface NavItem {
  href: string
  label: string
  icon: typeof LayoutDashboard
  group: string
  /** Label while a monitored service is selected; `null` hides the page (gateway-only configuration). */
  monitored?: string | null
  /** Shown only to admins (the API refuses everyone else). */
  adminOnly?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard, group: "Gateway" },
  { href: "/dashboard/analytics", label: "Analytics", icon: LineChart, group: "Gateway" },
  { href: "/dashboard/users", label: "Users", icon: Users, group: "Gateway", adminOnly: true },
  { href: "/dashboard/cache", label: "Cache", icon: Database, group: "Gateway", monitored: "Answer cache" },
  { href: "/dashboard/rate-limits", label: "Rate limits", icon: Timer, group: "Gateway" },
  { href: "/dashboard/rules", label: "Cache rules", icon: SlidersHorizontal, group: "Gateway", monitored: null },
  { href: "/status", label: "System status", icon: Activity, group: "Gateway", monitored: "Gateway status" },
  { href: "/dashboard/gateway", label: "LLM gateway", icon: Gauge, group: "AI", monitored: "Chat traffic" },
  { href: "/dashboard/assistant", label: "Assistant", icon: Bot, group: "AI" },
  { href: "/dashboard/knowledge-base", label: "Knowledge base", icon: BookOpen, group: "AI", monitored: null },
  { href: "/dashboard/ai-usage", label: "AI usage", icon: Coins, group: "AI" },
  { href: "/dashboard/pricing", label: "Pricing", icon: Wallet, group: "AI" },
  { href: "/dashboard/security", label: "Guardrails", icon: ShieldAlert, group: "AI" },
]

const NAV_GROUPS = ["Gateway", "AI"] as const

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  operator: "Operator",
  viewer: "Viewer",
  guest: "Guest",
}

const ROLE_HINT: Record<string, string> = {
  admin: "Full access",
  operator: "Can edit rules and cache",
  viewer: "Read only",
  guest: "Read only",
}

function isActive(pathname: string, href: string): boolean {
  if (href === "/dashboard") return pathname === "/dashboard"
  return pathname === href || pathname.startsWith(`${href}/`)
}

function HealthPill({ health, error }: { health: HealthResponse | null; error: string | null }) {
  const tone: PillTone = error ? "red" : health?.status === "healthy" ? "emerald" : health ? "amber" : "zinc"
  const label = error ? "API offline" : health?.status ?? "checking"
  return (
    <Link href="/status" className="hidden sm:inline-flex" aria-label="System status">
      <Pill tone={tone} dot>
        {label}
      </Pill>
    </Link>
  )
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <MonitoredServiceProvider>
      <ViewAsProvider>
        <ShellFrame>{children}</ShellFrame>
      </ViewAsProvider>
    </MonitoredServiceProvider>
  )
}

function ShellFrame({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const auth = useAuth()
  const monitored = useMonitoredService()
  const viewAs = useViewAs()
  const [menuOpen, setMenuOpen] = React.useState(false)

  const healthLoader = React.useCallback(() => apiHealth(), [])
  const health = usePolling(healthLoader, 30_000)

  React.useEffect(() => {
    if (auth.ready && !auth.token) router.replace("/login")
  }, [auth.ready, auth.token, router])

  React.useEffect(() => {
    const onLoginNeeded = () => {
      authLogout()
      window.dispatchEvent(new Event("auth-status-changed"))
      router.replace("/login")
    }
    window.addEventListener("login-needed", onLoginNeeded)
    return () => window.removeEventListener("login-needed", onLoginNeeded)
  }, [router])

  React.useEffect(() => {
    setMenuOpen(false)
  }, [pathname])

  function handleLogout() {
    authLogout()
    window.dispatchEvent(new Event("auth-status-changed"))
    router.replace("/login")
  }

  if (!auth.ready || !auth.token || !viewAs.ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-frost">
        <p className="text-sm text-graphite">Checking your session</p>
      </div>
    )
  }

  const role = auth.role
  // While a monitored service is selected the nav describes that service:
  // gateway-only configuration pages are hidden and some labels change.
  const navItems = NAV_ITEMS.filter(
    (item) => !(monitored.monitoring && item.monitored === null) && (!item.adminOnly || auth.isAdmin),
  )
  const navLabel = (item: NavItem) => (monitored.monitoring && item.monitored) || item.label
  const current = navItems.find((item) => isActive(pathname, item.href))
  const groupLabel = (group: string) => (monitored.monitoring && group === "Gateway" ? monitored.label : group)

  const navLink = (item: NavItem) => {
    const active = isActive(pathname, item.href)
    return (
      <Link
        key={item.href}
        href={item.href}
        aria-current={active ? "page" : undefined}
        className={cn(
          "flex items-center gap-2.5 border-l-2 py-1.5 pl-3 pr-2 text-sm transition-colors",
          active ? "border-ink text-ink" : "border-transparent text-graphite hover:border-rule-strong hover:text-ink",
        )}
      >
        <item.icon className={cn("h-4 w-4", active ? "text-ink" : "text-faint")} />
        {navLabel(item)}
      </Link>
    )
  }

  return (
    <div className="min-h-screen bg-frost text-ink">
      <div className="lg:grid lg:grid-cols-[232px_1fr]">
        <aside className="sticky top-0 hidden h-screen flex-col border-r border-rule bg-paper px-4 py-5 lg:flex">
          <Link href="/" aria-label="API Optimizer home" className="px-2">
            <Logo />
          </Link>

          <nav className="mt-8 flex flex-1 flex-col overflow-y-auto">
            {NAV_GROUPS.map((group, index) => (
              <div key={group} className={cn(index > 0 && "mt-6")}>
                <p className="mb-1.5 px-3 text-[12px] text-faint">{groupLabel(group)}</p>
                <div className="flex flex-col">{navItems.filter((item) => item.group === group).map(navLink)}</div>
              </div>
            ))}
          </nav>

          <div className="mt-4 border-t border-rule pt-4">
            <p className="text-sm text-ink">{role ? ROLE_LABELS[role] ?? role : "Viewer"}</p>
            <p className="text-[12px] text-graphite">{role ? ROLE_HINT[role] ?? "Read only" : "Read only"}</p>
            <button
              type="button"
              onClick={handleLogout}
              className="mt-3 inline-flex items-center gap-2 text-[13px] text-graphite transition-colors hover:text-ink"
            >
              <LogOut className="h-3.5 w-3.5" />
              Log out
            </button>
          </div>
        </aside>

        <div className="flex min-h-screen flex-col">
          <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-rule bg-paper px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setMenuOpen((open) => !open)}
                aria-label={menuOpen ? "Close navigation" : "Open navigation"}
                aria-expanded={menuOpen}
                className="flex h-9 w-9 items-center justify-center rounded border border-rule text-ink lg:hidden"
              >
                {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
              </button>
              <Link href="/" className="lg:hidden" aria-label="API Optimizer home">
                <Logo />
              </Link>
              <p className="hidden text-sm text-graphite lg:block">
                {current ? groupLabel(current.group) : "Console"}
                <span className="mx-2 text-rule-strong">/</span>
                <span className="text-ink">{current ? navLabel(current) : "Console"}</span>
              </p>
            </div>

            <div className="flex items-center gap-2">
              <UserSwitch className="hidden sm:block" />
              <ServiceSwitch state={monitored} />
              <HealthPill health={health.data} error={health.error} />
              {role && (
                <Pill tone="zinc" className="hidden sm:inline-flex">
                  {ROLE_LABELS[role] ?? role}
                </Pill>
              )}
              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-2 rounded border border-rule px-3 py-1.5 text-[13px] text-graphite transition-colors hover:border-ink hover:text-ink lg:hidden"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Log out</span>
              </button>
            </div>
          </header>

          {menuOpen && (
            <nav className="border-b border-rule bg-paper px-4 py-3 lg:hidden">
              <UserSwitch align="left" className="mb-3 sm:hidden" />
              <div className="flex flex-col">{navItems.map(navLink)}</div>
            </nav>
          )}

          <ViewAsBanner state={viewAs} />

          <main className="flex-1 px-4 py-6 sm:px-6 sm:py-8">
            {/* Keyed on the viewed user: switching remounts the page so every panel refetches in the new scope. */}
            <div key={viewAs.user?.key ?? "all-users"} className="mx-auto w-full max-w-6xl">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
