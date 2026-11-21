/* Loaded on every page: navbar auth state, mobile menu, sign-out buttons and
 * scroll-triggered reveals. */
import { AUTH_EVENT, authGetAccessToken, authGetRole, authLogout } from "./api.js"
import { qsa } from "./dom.js"

/** Reflect the stored token on <body> so CSS can show the right navbar actions. */
function syncAuth(): void {
  const token = authGetAccessToken()
  const role = token ? authGetRole() : null
  document.body.dataset.auth = token ? "in" : "out"
  document.body.dataset.role = role ?? ""
  for (const node of qsa("[data-role-label]")) node.textContent = "My account"
  for (const node of qsa("[data-admin-only]")) node.hidden = role !== "admin"
}

function setupNavbar(): void {
  const nav = document.getElementById("navbar")
  if (!nav) return
  const onScroll = () => nav.classList.toggle("is-scrolled", window.scrollY > 8)
  onScroll()
  window.addEventListener("scroll", onScroll, { passive: true })

  const toggle = document.getElementById("menu-toggle")
  const menu = document.getElementById("mobile-menu")
  if (!toggle || !menu) return
  const setOpen = (open: boolean) => {
    menu.hidden = !open
    toggle.setAttribute("aria-expanded", String(open))
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu")
    toggle.classList.toggle("is-open", open)
  }
  toggle.addEventListener("click", () => setOpen(menu.hidden))
  for (const link of qsa("a", menu)) link.addEventListener("click", () => setOpen(false))
}

function setupLogout(): void {
  for (const btn of qsa("[data-action='logout']")) {
    btn.addEventListener("click", () => {
      authLogout()
      window.location.assign("/")
    })
  }
}

/** Fade-up elements marked data-reveal when they scroll into view. Honours reduced motion. */
function setupReveal(): void {
  const items = qsa("[data-reveal]")
  if (items.length === 0) return
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches
  if (reduce || !("IntersectionObserver" in window)) {
    for (const item of items) item.classList.add("is-visible")
    return
  }
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        entry.target.classList.add("is-visible")
        observer.unobserve(entry.target)
      }
    },
    { rootMargin: "0px 0px -80px 0px" },
  )
  for (const item of items) observer.observe(item)
}

document.documentElement.classList.add("js")
syncAuth()
setupNavbar()
setupLogout()
setupReveal()
window.addEventListener(AUTH_EVENT, syncAuth)
window.addEventListener("storage", syncAuth)
