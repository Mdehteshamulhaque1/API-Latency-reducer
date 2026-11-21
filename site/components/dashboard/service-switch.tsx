"use client"

import * as React from "react"

import { Pill } from "@/components/ui/pill"
import { Segmented, type SegmentedOption } from "@/components/ui/segmented"
import { serviceLabel, type MonitoredServiceState } from "@/lib/use-service"

const SELF = "__self__"

/**
 * Picks which application the analytics pages analyse: a monitored service
 * (its rows arrive through POST /api/v1/ingest/requests) or this gateway's
 * own requests. Rendered only when at least one monitored service exists.
 */
export function ServiceSwitch({ state, className }: { state: MonitoredServiceState; className?: string }) {
  const monitored = state.services.filter((item) => !item.is_self)
  if (monitored.length === 0) return null

  const options: SegmentedOption<string>[] = [
    ...monitored.map((item) => ({ value: item.service, label: serviceLabel(item) })),
    { value: SELF, label: serviceLabel(null) },
  ]
  return (
    <Segmented
      value={state.service ?? SELF}
      onChange={(value) => state.setService(value === SELF ? null : value)}
      options={options}
      ariaLabel="Monitored service"
      className={className}
    />
  )
}

/** Small "in" / "out" marker for a request-log row. */
export function DirectionPill({ direction }: { direction: "inbound" | "outbound" | string }) {
  const outbound = direction === "outbound"
  return (
    <Pill tone={outbound ? "amber" : "zinc"} title={outbound ? "Call the service made" : "Request the service served"}>
      {outbound ? "out" : "in"}
    </Pill>
  )
}
