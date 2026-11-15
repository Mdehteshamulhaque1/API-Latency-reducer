/* Small DOM helpers shared by the page scripts. No framework. */

export function qs<T extends Element = HTMLElement>(selector: string, root: ParentNode = document): T {
  const el = root.querySelector<T>(selector)
  if (!el) throw new Error(`Missing element: ${selector}`)
  return el
}

export function qsa<T extends Element = HTMLElement>(selector: string, root: ParentNode = document): T[] {
  return Array.from(root.querySelectorAll<T>(selector))
}

export type AlertKind = "default" | "destructive" | "success"

const ICON_ATTRS = 'class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"'

const ALERT_ICONS: Record<AlertKind, string> = {
  default: `<svg ${ICON_ATTRS}><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`,
  destructive: `<svg ${ICON_ATTRS}><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>`,
  success: `<svg ${ICON_ATTRS}><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>`,
}

/** Replace the contents of `host` with one alert box. */
export function showAlert(host: HTMLElement, kind: AlertKind, text: string): void {
  host.innerHTML = ""
  const box = document.createElement("div")
  box.className = `alert alert-${kind}`
  box.setAttribute("role", "alert")
  box.innerHTML = ALERT_ICONS[kind]
  const body = document.createElement("div")
  body.textContent = text
  box.appendChild(body)
  host.appendChild(box)
  host.hidden = false
}

export function clearAlert(host: HTMLElement): void {
  host.innerHTML = ""
  host.hidden = true
}

/** Disable every control in a form while a request is pending. Buttons swap to their pending label via CSS. */
export function setPending(form: HTMLFormElement, pending: boolean): void {
  form.dataset.pending = pending ? "true" : "false"
  for (const el of qsa<HTMLInputElement | HTMLButtonElement | HTMLSelectElement>("input, button, select", form)) {
    el.disabled = pending
  }
}

/** After a few seconds of a pending request, reveal a "server may be waking up" note. */
export function slowNotice(el: HTMLElement, delayMs = 4000): { start(): void; stop(): void } {
  let timer: number | null = null
  const stop = () => {
    if (timer !== null) window.clearTimeout(timer)
    timer = null
    el.hidden = true
  }
  const start = () => {
    stop()
    timer = window.setTimeout(() => {
      el.hidden = false
    }, delayMs)
  }
  return { start, stop }
}

/** Wire every [data-password-toggle] button to the input next to it. */
export function setupPasswordToggles(root: ParentNode = document): void {
  for (const btn of qsa<HTMLButtonElement>("[data-password-toggle]", root)) {
    btn.addEventListener("click", () => {
      const input = btn.parentElement?.querySelector<HTMLInputElement>("input")
      if (!input) return
      const show = input.type === "password"
      input.type = show ? "text" : "password"
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password")
      btn.classList.toggle("is-visible", show)
    })
  }
}

export function formatCountdown(seconds: number): string {
  if (seconds <= 0) return "expired"
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const mm = String(m).padStart(2, "0")
  const ss = String(s).padStart(2, "0")
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

export function formatDate(exp: number | null): string {
  if (!exp) return "unknown"
  return new Date(exp * 1000).toLocaleString()
}

export function formatIsoDate(iso: string, opts?: Intl.DateTimeFormatOptions): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(undefined, opts)
}

/** Only allow same-origin relative paths as a post-login destination. */
export function safeNext(value: string | null): string {
  if (!value || !/^\/(?![/\\])/.test(value)) return "/account"
  return value
}

/** Build an element with optional class list, text and children. */
export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = "",
  text?: string,
  children: Node[] = [],
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  for (const child of children) node.appendChild(child)
  return node
}
