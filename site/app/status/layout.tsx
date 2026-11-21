import type { Metadata } from "next"

import { DashboardShell } from "@/components/dashboard/shell"

export const metadata: Metadata = {
  title: "System Status — API Optimizer",
  description: "View system health, database and Redis status for the API Optimizer LLM gateway",
}

export default function StatusLayout({ children }: { children: React.ReactNode }) {
  return <DashboardShell>{children}</DashboardShell>
}
