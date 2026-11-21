import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Sign in — API Optimizer",
  description: "Sign in to the API Optimizer gateway console",
}

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
