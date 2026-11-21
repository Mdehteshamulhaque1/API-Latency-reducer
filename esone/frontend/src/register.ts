import { ApiError, authRegister, authStoreTokens } from "./api.js"
import { clearAlert, qs, qsa, setPending, setupPasswordToggles, showAlert, slowNotice } from "./dom.js"

/* Mirrors backend/esone_api/schemas.py: username 3-100 chars, password 8-100 chars. */
const USERNAME_MIN = 3
const PASSWORD_MIN = 8
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const STRENGTH_LABELS = ["Too short", "Weak", "Fair", "Good", "Strong"]
const STRENGTH_CLASSES = ["", "is-danger", "is-saffron", "is-brand-soft", "is-brand"]

function passwordScore(value: string): number {
  let score = 0
  if (value.length >= PASSWORD_MIN) score += 1
  if (value.length >= 12) score += 1
  if (/[A-Z]/.test(value) && /[a-z]/.test(value)) score += 1
  if (/\d/.test(value) || /[^A-Za-z0-9]/.test(value)) score += 1
  return score
}

const form = qs<HTMLFormElement>("#register-form")
const alertHost = qs("#form-alert")
const notice = slowNotice(qs("#slow-notice"))

const username = qs<HTMLInputElement>("#username", form)
const email = qs<HTMLInputElement>("#email", form)
const password = qs<HTMLInputElement>("#password", form)
const confirm = qs<HTMLInputElement>("#confirm", form)
const strengthBars = qsa("#strength .strength-bar", form)
const strengthLabel = qs("#strength-label", form)
const checks = {
  username: qs("[data-check='username']", form),
  email: qs("[data-check='email']", form),
  password: qs("[data-check='password']", form),
  match: qs("[data-check='match']", form),
}

setupPasswordToggles(form)

function evaluate(): boolean {
  const results = {
    username: username.value.trim().length >= USERNAME_MIN,
    email: EMAIL_RE.test(email.value.trim()),
    password: password.value.length >= PASSWORD_MIN,
    match: password.value.length > 0 && password.value === confirm.value,
  }
  for (const [key, ok] of Object.entries(results) as Array<[keyof typeof results, boolean]>) {
    checks[key].classList.toggle("is-ok", ok)
  }

  const score = passwordScore(password.value)
  strengthBars.forEach((bar, index) => {
    bar.className = "strength-bar"
    if (score >= index + 1) bar.classList.add(STRENGTH_CLASSES[score] ?? "")
  })
  strengthLabel.textContent = password.value ? (STRENGTH_LABELS[score] ?? "") : ""

  return Object.values(results).every(Boolean)
}

for (const input of [username, email, password, confirm]) input.addEventListener("input", evaluate)
evaluate()

form.addEventListener("submit", async (event) => {
  event.preventDefault()
  clearAlert(alertHost)
  if (!evaluate()) {
    showAlert(alertHost, "destructive", "Complete the checklist below before continuing.")
    return
  }

  setPending(form, true)
  notice.start()
  try {
    const tokens = await authRegister(username.value.trim(), email.value.trim(), password.value)
    authStoreTokens(tokens)
    window.location.assign("/chat")
  } catch (err) {
    showAlert(
      alertHost,
      "destructive",
      err instanceof ApiError ? err.message : "Could not reach the authentication server.",
    )
    setPending(form, false)
    notice.stop()
  }
})
