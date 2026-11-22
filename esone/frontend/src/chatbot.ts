/* Project chatbot: a floating "Ask about this project" panel on every page.
 *
 * Talks to POST /api/v1/chatbot (public, no account needed). The conversation
 * lives in sessionStorage so it survives page changes within the tab and is
 * forgotten when the tab closes. Messages are inserted as text, never HTML.
 */
import { ApiError, apiChatbot, type ChatbotTurn } from "./api.js"
import { el, qs } from "./dom.js"

const STORE_KEY = "esone.chatbot"
const MAX_STORED = 30
const HISTORY_SENT = 6
/** Give up on one message after this long, so a sleeping or redeploying server never freezes the widget. */
const REQUEST_TIMEOUT_MS = 70_000
const SLOW_NOTICE_MS = 8_000
const GREETING =
  "Hi! I can tell you about the API Optimizer project: what it does, how caching and rate limits work, the dashboard, the tech stack and who built it. What would you like to know?"

const root = document.querySelector<HTMLElement>("#chatbot")

function loadTurns(): ChatbotTurn[] {
  try {
    const raw = sessionStorage.getItem(STORE_KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    if (!Array.isArray(parsed)) return []
    return parsed.filter(
      (t): t is ChatbotTurn =>
        !!t &&
        typeof t === "object" &&
        ((t as ChatbotTurn).role === "user" || (t as ChatbotTurn).role === "assistant") &&
        typeof (t as ChatbotTurn).content === "string",
    )
  } catch {
    return []
  }
}

function saveTurns(turns: ChatbotTurn[]): void {
  try {
    sessionStorage.setItem(STORE_KEY, JSON.stringify(turns.slice(-MAX_STORED)))
  } catch {
    /* storage blocked: the conversation just does not survive a page change */
  }
}

if (root) {
  const toggle = qs<HTMLButtonElement>("#chatbot-toggle", root)
  const panel = qs<HTMLElement>("#chatbot-panel", root)
  const close = qs<HTMLButtonElement>("#chatbot-close", root)
  const reset = qs<HTMLButtonElement>("#chatbot-reset", root)
  const log = qs<HTMLElement>("#chatbot-log", root)
  const form = qs<HTMLFormElement>("#chatbot-form", root)
  const input = qs<HTMLTextAreaElement>("#chatbot-input", root)
  const send = qs<HTMLButtonElement>("#chatbot-send", root)
  const suggestions = qs<HTMLElement>("#chatbot-suggestions", root)

  let turns = loadTurns()
  let busy = false

  const bubble = (role: "user" | "assistant" | "error", text: string): HTMLElement => {
    const node = el("div", `chatbot-msg chatbot-msg-${role}`, text)
    log.appendChild(node)
    log.scrollTop = log.scrollHeight
    return node
  }

  const render = () => {
    log.replaceChildren()
    bubble("assistant", GREETING)
    for (const turn of turns) bubble(turn.role, turn.content)
    suggestions.hidden = turns.length > 0
  }

  const setOpen = (open: boolean) => {
    panel.hidden = !open
    toggle.setAttribute("aria-expanded", String(open))
    root.classList.toggle("is-open", open)
    if (open) {
      render()
      window.setTimeout(() => input.focus(), 50)
    }
  }

  const ask = async (question: string) => {
    const message = question.trim()
    if (!message || busy) return
    busy = true
    send.disabled = true
    suggestions.hidden = true
    const history = turns.slice(-HISTORY_SENT)
    turns = [...turns, { role: "user", content: message }]
    saveTurns(turns)
    bubble("user", message)
    input.value = ""
    const typing = bubble("assistant", "Thinking…")
    typing.classList.add("chatbot-typing")
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
    const slow = window.setTimeout(() => {
      typing.textContent = "Waking up the server, this can take up to a minute…"
    }, SLOW_NOTICE_MS)
    try {
      const reply = await apiChatbot(message, history, controller.signal)
      typing.remove()
      turns = [...turns, { role: "assistant", content: reply.answer }]
      saveTurns(turns)
      bubble("assistant", reply.answer)
    } catch (err) {
      typing.remove()
      const text =
        err instanceof ApiError
          ? err.message
          : controller.signal.aborted
            ? "The server took too long to answer. Please send your question again."
            : "Could not reach the server. It may be waking up; please try again in a moment."
      bubble("error", text)
    } finally {
      window.clearTimeout(timeout)
      window.clearTimeout(slow)
      busy = false
      send.disabled = false
      input.focus()
    }
  }

  toggle.addEventListener("click", () => setOpen(panel.hidden))
  close.addEventListener("click", () => setOpen(false))
  reset.addEventListener("click", () => {
    turns = []
    saveTurns(turns)
    render()
    input.focus()
  })
  form.addEventListener("submit", (event) => {
    event.preventDefault()
    void ask(input.value)
  })
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      void ask(input.value)
    }
  })
  suggestions.addEventListener("click", (event) => {
    const target = event.target
    if (target instanceof HTMLButtonElement && target.dataset.question) void ask(target.dataset.question)
  })
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) setOpen(false)
  })
}
