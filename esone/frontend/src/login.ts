import { ApiError, authLogin, authStoreTokens } from "./api.js"
import { clearAlert, qs, safeNext, setPending, setupPasswordToggles, showAlert, slowNotice } from "./dom.js"

const form = qs<HTMLFormElement>("#login-form")
const alertHost = qs("#form-alert")
const notice = slowNotice(qs("#slow-notice"))
const next = safeNext(new URLSearchParams(window.location.search).get("next"))

setupPasswordToggles(form)

form.addEventListener("submit", async (event) => {
  event.preventDefault()
  clearAlert(alertHost)

  const username = qs<HTMLInputElement>("#username", form).value.trim()
  const password = qs<HTMLInputElement>("#password", form).value
  if (!username || !password) {
    showAlert(alertHost, "destructive", "Enter your username and password.")
    return
  }

  setPending(form, true)
  notice.start()
  try {
    const tokens = await authLogin(username, password)
    authStoreTokens(tokens)
    window.location.assign(next)
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
