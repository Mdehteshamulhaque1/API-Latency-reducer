/* Search results: the question lives in the URL (?q=), the answer sits on
 * top and the sources read like search results. Earlier searches of the
 * signed-in user are listed on the side and can be re-run with one click. */
import {
  ApiError,
  AUTH_EVENT,
  apiAsk,
  apiChatHistory,
  apiChatHistoryClear,
  authGetAccessToken,
  type AnswerResponse,
  type ChatHistoryItem,
} from "./api.js"
import { clearAlert, el, formatIsoDate, qs, showAlert } from "./dom.js"

const RECENT_LIMIT = 12

const ui = {
  form: qs<HTMLFormElement>("#search-form"),
  input: qs<HTMLInputElement>("#search-input"),
  clearInput: qs<HTMLButtonElement>("#search-clear"),
  submit: qs<HTMLButtonElement>("#search-submit"),
  alert: qs("#search-alert"),
  status: qs("#result-status"),
  pending: qs("#result-pending"),
  pendingText: qs("#result-pending-text"),
  answer: qs("#result-answer"),
  meta: qs("#result-meta"),
  text: qs("#result-text"),
  tags: qs("#result-tags"),
  empty: qs("#result-empty"),
  recentList: qs("#recent-list"),
  recentEmpty: qs("#recent-empty"),
  clearHistory: qs<HTMLButtonElement>("#clear-btn"),
}

let searching = false
let recent: ChatHistoryItem[] = []

function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`
}

function pill(text: string, tone = "neutral"): HTMLElement {
  return el("span", `badge badge-${tone}`, text)
}

function currentQuery(): string {
  return (new URLSearchParams(window.location.search).get("q") ?? "").trim()
}

function setQuery(question: string): void {
  const url = new URL(window.location.href)
  url.searchParams.set("q", question)
  window.history.pushState({ q: question }, "", url)
}

// ----- rendering -----

function showAnswer(question: string, answer: AnswerResponse, roundTripMs: number): void {
  ui.empty.hidden = true
  ui.pending.hidden = true

  const how = answer.cached
    ? `Instant answer${answer.match_method === "exact" ? "" : `, matched a similar question (${Math.round((answer.similarity ?? 0) * 100)}%)`}`
    : answer.answered_by === "model"
      ? "Answered by Gemini from its own knowledge"
      : "Researched fresh"
  ui.status.textContent = `${how} · ${formatMs(answer.latency_ms)} on the server, ${formatMs(roundTripMs)} in total`
  ui.status.hidden = false

  // Citation markers such as "[1, 3]" refer to a source list that is no longer shown.
  ui.text.textContent = answer.answer.replace(/\s*\[\d+(?:\s*,\s*\d+)*\]/g, "")
  ui.meta.textContent = formatIsoDate(new Date().toISOString(), { dateStyle: "medium", timeStyle: "short" })
  ui.tags.innerHTML = ""
  if (!answer.cacheable) ui.tags.appendChild(pill("private: not saved for others"))
  ui.tags.hidden = ui.tags.childElementCount === 0
  ui.answer.hidden = false

  document.title = `${question} · Esone`
}

function showIdle(): void {
  ui.status.hidden = true
  ui.pending.hidden = true
  ui.answer.hidden = true
  ui.empty.hidden = false
  document.title = "Search · Esone"
}

function renderRecent(): void {
  ui.recentList.innerHTML = ""
  const items = recent.slice(0, RECENT_LIMIT)
  ui.recentEmpty.hidden = items.length > 0
  ui.clearHistory.disabled = searching || recent.length === 0
  for (const item of items) {
    const li = el("li", "recent-item")
    const btn = el("button", "recent-question", item.question)
    btn.type = "button"
    btn.addEventListener("click", () => {
      ui.input.value = item.question
      void search(item.question)
    })
    li.appendChild(btn)
    const meta = el("span", "recent-meta")
    meta.appendChild(el("span", "text-xs text-muted", formatIsoDate(item.created_at, { dateStyle: "short", timeStyle: "short" })))
    li.appendChild(meta)
    ui.recentList.appendChild(li)
  }
}

function setSearching(on: boolean): void {
  searching = on
  ui.form.dataset.pending = on ? "true" : "false"
  ui.submit.disabled = on
  ui.input.disabled = on
  ui.clearHistory.disabled = on || recent.length === 0
}

// ----- loading messages -----

/** Short, friendly status lines shown while an answer is being found. */
const LOADING_LINES: readonly string[] = [
  "Asking the librarian. She's very thorough.",
  "Checking whether someone already asked this…",
  "Flipping through a few million pages, politely.",
  "Consulting the encyclopedia. It insists on footnotes.",
  "Brewing a fresh answer. No shortcuts.",
  "Cross-checking facts so you don't have to.",
  "Reading so you can keep scrolling.",
  "Separating the facts from the fluff…",
  "Warming up the search engines. Literally several of them.",
  "Looking it up the old-fashioned way: carefully.",
  "Turning the question over to see the other side.",
  "Finding the shortest path to a good answer.",
  "Asking the internet nicely. It usually answers.",
  "Double-checking the dates. History is picky.",
  "Polishing the answer until it shines.",
  "Almost there. Good answers take a moment.",
  "Gathering sources worth trusting…",
  "Doing the homework, so you don't have to.",
]

let lastLine = -1

function nextLine(): string {
  let index = Math.floor(Math.random() * LOADING_LINES.length)
  if (index === lastLine) index = (index + 1) % LOADING_LINES.length
  lastLine = index
  return LOADING_LINES[index] ?? "Looking it up…"
}

/** Show a fresh line now and a different one every few seconds until stopped. */
function startLoadingMessages(): { stop(): void } {
  ui.pendingText.textContent = nextLine()
  const timer = window.setInterval(() => {
    ui.pendingText.textContent = nextLine()
  }, 2600)
  return { stop: () => window.clearInterval(timer) }
}

// ----- actions -----

async function search(question: string, pushUrl = true): Promise<void> {
  const q = question.trim()
  if (q.length < 3 || searching) return
  if (!authGetAccessToken()) {
    window.location.replace(`/login?next=${encodeURIComponent(`/chat?q=${encodeURIComponent(q)}`)}`)
    return
  }
  if (pushUrl && currentQuery() !== q) setQuery(q)
  clearAlert(ui.alert)
  setSearching(true)
  ui.empty.hidden = true
  ui.answer.hidden = true
  ui.status.hidden = true

  ui.pending.hidden = false
  const ticker = startLoadingMessages()
  const started = performance.now()
  try {
    const answer = await apiAsk(q)
    showAnswer(q, answer, performance.now() - started)
    recent = [
      {
        id: Date.now(),
        created_at: new Date().toISOString(),
        question: answer.question,
        answer: answer.answer,
        status: "ok",
        error_message: null,
        answered_by: answer.answered_by,
        cached: answer.cached,
        cache_type: answer.cached ? (answer.match_method === "exact" ? "exact" : "semantic") : "miss",
        match_method: answer.match_method,
        similarity: answer.similarity,
        compose_method: answer.compose_method,
        sources: answer.sources,
        sources_count: answer.sources.length,
        latency_ms: answer.latency_ms,
        cache_lookup_ms: answer.cache_lookup_ms,
        crawl_ms: answer.crawl_ms,
        llm_ms: answer.llm_ms,
        total_tokens: answer.total_tokens,
        estimated_cost_usd: answer.estimated_cost_usd,
        served_model: answer.served_model,
        correlation_id: null,
      },
      ...recent.filter((item) => item.question.toLowerCase() !== answer.question.toLowerCase()),
    ]
    renderRecent()
  } catch (err) {
    ui.pending.hidden = true
    ui.empty.hidden = false
    showAlert(ui.alert, "destructive", err instanceof ApiError ? err.message : "The search failed. Try again.")
  } finally {
    ticker.stop()
    setSearching(false)
    ui.input.focus()
  }
}

async function loadRecent(): Promise<void> {
  try {
    const history = await apiChatHistory(RECENT_LIMIT)
    recent = [...history.items].reverse() // newest first
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return
    recent = []
  }
  renderRecent()
}

ui.form.addEventListener("submit", (event) => {
  event.preventDefault()
  void search(ui.input.value)
})
ui.input.addEventListener("input", () => {
  ui.clearInput.hidden = ui.input.value.length === 0
})
ui.clearInput.addEventListener("click", () => {
  ui.input.value = ""
  ui.clearInput.hidden = true
  ui.input.focus()
})
ui.clearHistory.addEventListener("click", async () => {
  recent = []
  renderRecent()
  try {
    await apiChatHistoryClear()
  } catch (err) {
    showAlert(ui.alert, "destructive", err instanceof ApiError ? err.message : "Could not clear your searches")
  }
})
window.addEventListener("popstate", () => {
  const q = currentQuery()
  ui.input.value = q
  ui.clearInput.hidden = q.length === 0
  if (q) void search(q, false)
  else showIdle()
})

function guard(): void {
  if (!authGetAccessToken()) {
    const q = currentQuery()
    window.location.replace(`/login?next=${encodeURIComponent(q ? `/chat?q=${encodeURIComponent(q)}` : "/chat")}`)
  }
}
guard()
window.addEventListener(AUTH_EVENT, guard)
window.addEventListener("storage", guard)

const initial = currentQuery()
ui.input.value = initial
ui.clearInput.hidden = initial.length === 0
void loadRecent()
if (initial) void search(initial, false)
else {
  showIdle()
  ui.input.focus()
}
