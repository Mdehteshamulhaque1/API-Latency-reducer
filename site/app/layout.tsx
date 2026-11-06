import type { Metadata } from "next"
import { GeistSans } from "geist/font/sans"
import { JetBrains_Mono } from "next/font/google"

import { Grain } from "@/components/backgrounds"
import { ScrollProgress } from "@/components/scroll-progress"
import "./globals.css"

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
})

export const metadata: Metadata = {
  title: "API Optimizer — cache, throttle & monitor your API",
  description:
    "A FastAPI gateway with Redis response caching, token-bucket rate limiting, JWT auth, and live performance analytics.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={[GeistSans.variable, mono.variable].join(" ")}>
      <body>
        <Grain />
        <ScrollProgress />
        {children}
      </body>
    </html>
  )
}
