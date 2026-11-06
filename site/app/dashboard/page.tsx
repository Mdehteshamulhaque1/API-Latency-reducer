import type { Metadata } from "next"

import { Navbar } from "@/components/navbar"
import { DashboardPreview } from "@/components/dashboard-preview"
import { Footer } from "@/components/footer"

export const metadata: Metadata = {
  title: "Dashboard — API Optimizer",
  description:
    "A working management UI for API Optimizer — auth, monitoring, and cache rules in one panel.",
}

export default function DashboardPage() {
  return (
    <>
      <Navbar />
      <main>
        <div className="pt-16">
          <DashboardPreview
            eyebrow="the dashboard"
            title={
              <>
                Your control panel,
                <span className="text-gradient"> live.</span>
              </>
            }
            description="Auth, monitoring, and cache rules ship with a working management UI — no external admin tool required."
          />
        </div>
      </main>
      <Footer />
    </>
  )
}
