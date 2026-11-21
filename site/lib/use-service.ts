"use client"

import * as React from "react"

import { apiAnalyticsServices, type MonitoredService } from "@/lib/api"

const STORAGE_KEY = "apiopt.monitored-service"
const SELF_LABEL = "This gateway"

/** Display name for a service in switches and copy. */
export function serviceLabel(service: MonitoredService | string | null | undefined): string {
  if (!service) return SELF_LABEL
  const entry = typeof service === "string" ? null : service
  const name = typeof service === "string" ? service : service.service
  if (entry?.is_self) return SELF_LABEL
  return name.charAt(0).toUpperCase() + name.slice(1)
}

function readStored(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function writeStored(value: string | null) {
  try {
    if (value) localStorage.setItem(STORAGE_KEY, value)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* private mode or blocked storage: selection just does not persist */
  }
}

export interface MonitoredServiceState {
  /** Services with rows in the last 24h, this gateway first. */
  services: MonitoredService[]
  /** Selected service name, or null for this gateway's own requests. */
  service: string | null
  /** The selected entry, when it exists in `services`. */
  selected: MonitoredService | null
  /** True while a monitored service (not this gateway) is selected. */
  monitoring: boolean
  /** Human label for the selection ("Esone" or "This gateway"). */
  label: string
  setService: (service: string | null) => void
  loading: boolean
}

/**
 * Which application the dashboard is analysing. Lists the services that
 * shipped request rows (GET /api/v1/analytics/services) and remembers the
 * choice in localStorage. With no stored choice, the first monitored
 * application (for example Esone) is selected, so the dashboard shows the
 * monitored API rather than the gateway's own traffic by default.
 */
function useMonitoredServiceState(enabled = true): MonitoredServiceState {
  const [services, setServices] = React.useState<MonitoredService[]>([])
  const [service, setServiceState] = React.useState<string | null>(null)
  const [loading, setLoading] = React.useState(true)
  const decided = React.useRef(false)

  React.useEffect(() => {
    if (!enabled) return
    let cancelled = false
    apiAnalyticsServices(24)
      .then((list) => {
        if (cancelled) return
        setServices(list)
        if (decided.current) return
        decided.current = true
        const stored = readStored()
        if (stored === "") {
          setServiceState(null)
        } else if (stored && list.some((item) => item.service === stored && !item.is_self)) {
          setServiceState(stored)
        } else {
          const monitored = list.find((item) => !item.is_self)
          setServiceState(monitored ? monitored.service : null)
        }
      })
      .catch(() => {
        if (!cancelled) setServices([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [enabled])

  const setService = React.useCallback((next: string | null) => {
    decided.current = true
    setServiceState(next)
    // An empty string records an explicit choice of the gateway itself.
    writeStored(next ?? "")
  }, [])

  const selected = React.useMemo(
    () => (service ? services.find((item) => item.service === service) ?? null : null),
    [service, services],
  )

  return {
    services,
    service,
    selected,
    monitoring: service !== null,
    label: serviceLabel(selected ?? service),
    setService,
    loading,
  }
}

const MonitoredServiceContext = React.createContext<MonitoredServiceState | null>(null)

/** Provides one shared selection to every dashboard page (mounted by the shell). */
export function MonitoredServiceProvider({ children }: { children: React.ReactNode }) {
  const state = useMonitoredServiceState()
  return React.createElement(MonitoredServiceContext.Provider, { value: state }, children)
}

/** The shared selection; falls back to a local instance outside the provider. */
export function useMonitoredService(): MonitoredServiceState {
  const shared = React.useContext(MonitoredServiceContext)
  const local = useMonitoredServiceState(shared === null)
  return shared ?? local
}
