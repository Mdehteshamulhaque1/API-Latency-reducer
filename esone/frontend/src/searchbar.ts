/* The search bar on pages other than the results page: typing a question and
 * submitting opens /chat?q=… (the form also works without JavaScript). */
import { qs } from "./dom.js"

export function wireSearchBar(): void {
  const form = qs<HTMLFormElement>("#search-form")
  const input = qs<HTMLInputElement>("#search-input")
  const clear = qs<HTMLButtonElement>("#search-clear")
  form.addEventListener("submit", (event) => {
    event.preventDefault()
    const q = input.value.trim()
    if (q.length < 3) {
      input.focus()
      return
    }
    window.location.assign(`/chat?q=${encodeURIComponent(q)}`)
  })
  input.addEventListener("input", () => {
    clear.hidden = input.value.length === 0
  })
  clear.addEventListener("click", () => {
    input.value = ""
    clear.hidden = true
    input.focus()
  })
}
