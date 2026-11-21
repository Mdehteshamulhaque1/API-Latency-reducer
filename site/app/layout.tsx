import type { Metadata } from "next"
import { Bricolage_Grotesque, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google"

import "./globals.css"

const display = Bricolage_Grotesque({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
  display: "swap",
})

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-sans",
  display: "swap",
})

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
})

export const metadata: Metadata = {
  title: "API Optimizer: cache, throttle and measure your API",
  description:
    "A FastAPI gateway with Redis response caching, token-bucket rate limiting, JWT auth, and live latency analytics.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={[display.variable, sans.variable, mono.variable].join(" ")}>
      <body>{children}</body>
    </html>
  )
}
