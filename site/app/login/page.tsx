"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Loader2 } from "lucide-react"

import { AuthShell } from "@/components/auth/auth-shell"
import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PasswordInput } from "@/components/ui/password-input"
import { authGetAccessToken, authLogin, authStoreTokens } from "@/lib/api"

/** Only allow same-origin, path-style redirects after login. */
function safeNext(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/dashboard"
  return value
}

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const next = safeNext(searchParams.get("next"))

  const [username, setUsername] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [submitting, setSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (authGetAccessToken()) router.replace(next)
  }, [router, next])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return
    setError(null)
    setSubmitting(true)
    try {
      const tokens = await authLogin(username.trim(), password)
      authStoreTokens(tokens)
      window.dispatchEvent(new Event("auth-status-changed"))
      router.replace(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed")
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      {error && <Alert variant="destructive">{error}</Alert>}

      <div className="space-y-2">
        <Label htmlFor="username">Username</Label>
        <Input
          id="username"
          name="username"
          autoComplete="username"
          autoFocus
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          placeholder="your-username"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <PasswordInput
          id="password"
          name="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Your password"
        />
      </div>

      <Button
        type="submit"
        variant="primary"
        size="lg"
        className="w-full"
        disabled={submitting || username.trim().length === 0 || password.length === 0}
      >
        {submitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Signing in…
          </>
        ) : (
          <>
            Sign in
          </>
        )}
      </Button>

      <p className="text-center text-[12px] leading-relaxed text-graphite">
        You stay signed in on this browser until you sign out.
      </p>
    </form>
  )
}

export default function LoginPage() {
  return (
    <AuthShell
      title="Sign in"
      subtitle="Use your console account. Admins have full access, operators can change cache rules and documents, viewers can look but not change."
      footer={
        <span>
          No account yet?{" "}
          <Link href="/register" className="text-ink underline underline-offset-4">
            Create a viewer account
          </Link>
        </span>
      }
    >
      <React.Suspense fallback={<div className="h-[232px]" />}>
        <LoginForm />
      </React.Suspense>
    </AuthShell>
  )
}
