import { ApiError, apiChatbot } from "./api.js";
import { el, qs } from "./dom.js";
const STORE_KEY = "esone.chatbot";
const MAX_STORED = 30;
const HISTORY_SENT = 6;
const REQUEST_TIMEOUT_MS = 70000;
const SLOW_NOTICE_MS = 8000;
const GREETING = "Hi! I can tell you about the API Optimizer project: what it does, how caching and rate limits work, the dashboard, the tech stack and who built it. What would you like to know?";
const root = document.querySelector("#chatbot");
function loadTurns() {
    try {
        const raw = sessionStorage.getItem(STORE_KEY);
        const parsed = raw ? JSON.parse(raw) : [];
        if (!Array.isArray(parsed))
            return [];
        return parsed.filter((t) => !!t &&
            typeof t === "object" &&
            (t.role === "user" || t.role === "assistant") &&
            typeof t.content === "string");
    }
    catch {
        return [];
    }
}
function saveTurns(turns) {
    try {
        sessionStorage.setItem(STORE_KEY, JSON.stringify(turns.slice(-MAX_STORED)));
    }
    catch {
    }
}
if (root) {
    const toggle = qs("#chatbot-toggle", root);
    const panel = qs("#chatbot-panel", root);
    const close = qs("#chatbot-close", root);
    const reset = qs("#chatbot-reset", root);
    const log = qs("#chatbot-log", root);
    const form = qs("#chatbot-form", root);
    const input = qs("#chatbot-input", root);
    const send = qs("#chatbot-send", root);
    const suggestions = qs("#chatbot-suggestions", root);
    let turns = loadTurns();
    let busy = false;
    const bubble = (role, text) => {
        const node = el("div", `chatbot-msg chatbot-msg-${role}`, text);
        log.appendChild(node);
        log.scrollTop = log.scrollHeight;
        return node;
    };
    const render = () => {
        log.replaceChildren();
        bubble("assistant", GREETING);
        for (const turn of turns)
            bubble(turn.role, turn.content);
        suggestions.hidden = turns.length > 0;
    };
    const setOpen = (open) => {
        panel.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
        root.classList.toggle("is-open", open);
        if (open) {
            render();
            window.setTimeout(() => input.focus(), 50);
        }
    };
    const ask = async (question) => {
        const message = question.trim();
        if (!message || busy)
            return;
        busy = true;
        send.disabled = true;
        suggestions.hidden = true;
        const history = turns.slice(-HISTORY_SENT);
        turns = [...turns, { role: "user", content: message }];
        saveTurns(turns);
        bubble("user", message);
        input.value = "";
        const typing = bubble("assistant", "Thinking…");
        typing.classList.add("chatbot-typing");
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
        const slow = window.setTimeout(() => {
            typing.textContent = "Waking up the server, this can take up to a minute…";
        }, SLOW_NOTICE_MS);
        try {
            const reply = await apiChatbot(message, history, controller.signal);
            typing.remove();
            turns = [...turns, { role: "assistant", content: reply.answer }];
            saveTurns(turns);
            bubble("assistant", reply.answer);
        }
        catch (err) {
            typing.remove();
            const text = err instanceof ApiError
                ? err.message
                : controller.signal.aborted
                    ? "The server took too long to answer. Please send your question again."
                    : "Could not reach the server. It may be waking up; please try again in a moment.";
            bubble("error", text);
        }
        finally {
            window.clearTimeout(timeout);
            window.clearTimeout(slow);
            busy = false;
            send.disabled = false;
            input.focus();
        }
    };
    toggle.addEventListener("click", () => setOpen(panel.hidden));
    close.addEventListener("click", () => setOpen(false));
    reset.addEventListener("click", () => {
        turns = [];
        saveTurns(turns);
        render();
        input.focus();
    });
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        void ask(input.value);
    });
    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void ask(input.value);
        }
    });
    suggestions.addEventListener("click", (event) => {
        const target = event.target;
        if (target instanceof HTMLButtonElement && target.dataset.question)
            void ask(target.dataset.question);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !panel.hidden)
            setOpen(false);
    });
}
