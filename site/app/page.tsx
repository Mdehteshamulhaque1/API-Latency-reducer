import { Navbar } from "@/components/navbar"
import { Hero } from "@/components/hero"
import { StatsStrip } from "@/components/stats-strip"
import { TechStack } from "@/components/tech-stack"
import { Features } from "@/components/features"
import { ArchitectureDiagram } from "@/components/architecture-diagram"
import { HowItWorks } from "@/components/how-it-works"
import { DashboardPreview } from "@/components/dashboard-preview"
import { MetricsBento } from "@/components/metrics-bento"
import { Roadmap } from "@/components/roadmap"
import { Footer } from "@/components/footer"

export default function Home() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <StatsStrip />
        <TechStack />
        <Features />
        <ArchitectureDiagram />
        <HowItWorks />
        <DashboardPreview />
        <MetricsBento />
        <Roadmap />
      </main>
      <Footer />
    </>
  )
}
