"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Check, Loader2 } from "lucide-react"

import { AuthShell } from "@/components/auth/auth-shell"
import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PasswordInput } from "@/components/ui/password-input"
import { authGetAccessToken, authRegister, authStoreTokens } from "@/lib/api"
import { cn } from "@/lib/utils"

// Mirrors app/schemas/auth.py UserCreate constraints.
const USERNAME_MIN = 3
const USERNAME_MAX = 100
const PASSWORD_MIN = 8
const PASSWORD_MAX = 100
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function RegisterPage() {
  const router = useRouter()
  const [username, setUsername] = React.useState("")
  const [email, setEmail] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [confirm, setConfirm] = React.useState("")
  const [submitting, setSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [touched, setTouched] = React.useState(false)

  React.useEffect(() => {
    if (authGetAccessToken()) router.replace("/dashboard")
  }, [router])

  const checks = [
    {
      ok: username.trim().length >= USERNAME_MIN && username.trim().length <= USERNAME_MAX,
      label: `Username is ${USERNAME_MIN}–${USERNAME_MAX} characters`,
    },
    { ok: EMAIL_RE.test(email.trim()), label: "Email address looks valid" },
    {
      ok: password.length >= PASSWORD_MIN && password.length <= PASSWORD_MAX,
      label: `Password is at least ${PASSWORD_MIN} characters`,
    },
    { ok: confirm.length > 0 && confirm === password, label: "Passwords match" },
  ]
  const valid = checks.every((check) => check.ok)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setTouched(true)
    if (!valid || submitting) return
    setError(null)
    setSubmitting(true)
    try {
      const tokens = await authRegister(username.trim(), email.trim(), password)
      authStoreTokens(tokens)
      window.dispatchEvent(new Event("auth-status-changed"))
      router.replace("/dashboard")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed")
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Create a viewer account"
      subtitle="New accounts are read-only. Operator and admin roles are granted by the system administrator."
      footer={
        <span>
          Already have an account?{" "}
          <Link href="/login" className="text-ink underline underline-offset-4">
            Sign in
          </Link>
        </span>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        {error && <Alert variant="destructive">{error}</Alert>}

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              name="username"
              autoComplete="username"
              autoFocus
              required
              minLength={USERNAME_MIN}
              maxLength={USERNAME_MAX}
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="jane-doe"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="jane@example.com"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <PasswordInput
            id="password"
            name="password"
            autoComplete="new-password"
            required
            minLength={PASSWORD_MIN}
            maxLength={PASSWORD_MAX}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 8 characters"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirm">Confirm password</Label>
          <PasswordInput
            id="confirm"
            name="confirm"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            placeholder="Repeat your password"
          />
        </div>

        <ul className="grid gap-1.5 rounded border border-rule bg-frost p-3 sm:grid-cols-2">
          {checks.map((check) => (
            <li
              key={check.label}
              className={cn(
                "flex items-center gap-2 text-[12px]",
                check.ok ? "text-relay" : touched ? "text-warn" : "text-graphite",
              )}
            >
              <span
                className={cn(
                  "flex h-4 w-4 items-center justify-center rounded-full border",
                  check.ok ? "border-relay bg-relay text-paper" : "border-rule-strong",
                )}
              >
                {check.ok && <Check className="h-2.5 w-2.5" />}
              </span>
              {check.label}
            </li>
          ))}
        </ul>

        <Button type="submit" variant="primary" size="lg" className="w-full" disabled={submitting}>
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Creating account…
            </>
          ) : (
            <>
              Create account
            </>
          )}
        </Button>
      </form>
    </AuthShell>
  )
}
