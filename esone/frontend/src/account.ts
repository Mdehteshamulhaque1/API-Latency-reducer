/* Your account: profile, password change and sign-out. Token internals are
 * not shown here; the app refreshes sessions silently in the background. */
import {
  ApiError,
  AUTH_EVENT,
  apiChangePassword,
  apiChatStats,
  apiMe,
  authGetAccessToken,
  authLogin,
  authStoreTokens,
  type UserProfile,
} from "./api.js"
import { clearAlert, el, formatIsoDate, qs, setPending, setupPasswordToggles, showAlert } from "./dom.js"
import { wireSearchBar } from "./searchbar.js"

const PASSWORD_MIN = 8
const ui = {
  skeleton: qs("#console-skeleton"),
  console: qs("#console"),
  notice: qs("#console-notice"),
  statUsername: qs("#stat-username"),
  statEmail: qs("#stat-email"),
  statSince: qs("#stat-since"),
  profileBody: qs("#profile-body"),
  passwordForm: qs<HTMLFormElement>("#password-form"),
  passwordAlert: qs("#password-alert"),
  passwordSubmit: qs<HTMLButtonElement>("#password-submit"),
  current: qs<HTMLInputElement>("#current-password"),
  next: qs<HTMLInputElement>("#new-password"),
  confirm: qs<HTMLInputElement>("#confirm-password"),
}

let profile: UserProfile | null = null

// ----- profile -----

function renderProfile(error: string | null): void {
  ui.profileBody.innerHTML = ""
  if (error) {
    showAlert(ui.profileBody, "destructive", error)
    return
  }
  if (!profile) {
    for (let i = 0; i < 3; i += 1) ui.profileBody.appendChild(el("div", "skeleton skeleton-row"))
    return
  }
  ui.statUsername.textContent = profile.username
  ui.statEmail.textContent = profile.email
  ui.statSince.textContent = formatIsoDate(profile.created_at, { dateStyle: "medium" })

  const list = el("ul", "rows")
  const rows: Array<[string, string]> = [
    ["Username", profile.username],
    ["Email", profile.email],
    ["Role", profile.role],
    ["Status", profile.is_active ? "active" : "disabled"],
    ["Member since", formatIsoDate(profile.created_at, { dateStyle: "long" })],
  ]
  for (const [label, value] of rows) {
    const row = el("li", "row")
    row.appendChild(el("span", "row-label", label))
    row.appendChild(el("span", "row-value", value))
    list.appendChild(row)
  }
  ui.profileBody.appendChild(list)
}

// ----- usage -----

async function loadUsage(): Promise<void> {
  const host = qs("#billing-rows")
  host.innerHTML = ""
  const row = (label: string, value: string) => {
    const li = el("li", "row")
    li.appendChild(el("span", "row-label", label))
    li.appendChild(el("span", "row-value mono", value))
    host.appendChild(li)
  }
  try {
    const stats = await apiChatStats(24 * 365)
    row("Searches", stats.total_queries.toLocaleString())
    row("Instant answers", stats.cache_hits.toLocaleString())
    row("Freshly researched", stats.misses.toLocaleString())
  } catch (err) {
    row("Usage", err instanceof ApiError ? err.message : "Could not load your usage")
  }
}

async function loadProfile(): Promise<void> {
  profile = null
  renderProfile(null)
  try {
    profile = await apiMe()
    renderProfile(null)
  } catch (err) {
    renderProfile(err instanceof ApiError ? err.message : "Could not load your profile")
  } finally {
    ui.skeleton.hidden = true
    ui.console.hidden = false
  }
}

// ----- password -----

function updatePasswordButton(): void {
  const pending = ui.passwordForm.dataset.pending === "true"
  ui.passwordSubmit.disabled = pending || !ui.current.value || !ui.next.value || !ui.confirm.value
}
for (const input of [ui.current, ui.next, ui.confirm]) input.addEventListener("input", updatePasswordButton)
setupPasswordToggles(ui.passwordForm)
updatePasswordButton()

ui.passwordForm.addEventListener("submit", async (event) => {
  event.preventDefault()
  clearAlert(ui.passwordAlert)
  if (ui.next.value.length < PASSWORD_MIN) {
    showAlert(ui.passwordAlert, "destructive", `New password must have at least ${PASSWORD_MIN} characters.`)
    return
  }
  if (ui.next.value !== ui.confirm.value) {
    showAlert(ui.passwordAlert, "destructive", "New passwords do not match.")
    return
  }

  const newPassword = ui.next.value
  setPending(ui.passwordForm, true)
  try {
    await apiChangePassword(ui.current.value, newPassword)
    if (profile?.username) {
      // Other sessions were signed out; sign this one in again so it continues.
      authStoreTokens(await authLogin(profile.username, newPassword))
    }
    ui.current.value = ""
    ui.next.value = ""
    ui.confirm.value = ""
    showAlert(ui.passwordAlert, "success", "Password changed. Other devices have been signed out.")
  } catch (err) {
    showAlert(ui.passwordAlert, "destructive", err instanceof ApiError ? err.message : "Could not reach the server.")
  } finally {
    setPending(ui.passwordForm, false)
    updatePasswordButton()
  }
})

// ----- boot -----

function sync(): void {
  if (!authGetAccessToken()) {
    // Signed out here or in another tab. Leave the page.
    window.location.replace("/login?next=/account")
    return
  }
  void loadProfile()
  void loadUsage()
}

sync()
window.addEventListener(AUTH_EVENT, sync)
window.addEventListener("storage", sync)
wireSearchBar()
