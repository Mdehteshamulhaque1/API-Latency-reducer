import type { Metadata } from "next"

import { DashboardShell } from "@/components/dashboard/shell"

export const metadata: Metadata = {
  title: "Dashboard — API Optimizer",
  description: "View analytics, rules, and system health for the API Optimizer LLM gateway",
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <DashboardShell>{children}</DashboardShell>
}
