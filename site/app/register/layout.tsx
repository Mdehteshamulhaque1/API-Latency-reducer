import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Create account — API Optimizer",
  description: "Create an API Optimizer account",
}

export default function RegisterLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
