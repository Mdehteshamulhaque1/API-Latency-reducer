export function qs(selector, root = document) {
    const el = root.querySelector(selector);
    if (!el)
        throw new Error(`Missing element: ${selector}`);
    return el;
}
export function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
}
const ICON_ATTRS = 'class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';
const ALERT_ICONS = {
    default: `<svg ${ICON_ATTRS}><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`,
    destructive: `<svg ${ICON_ATTRS}><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>`,
    success: `<svg ${ICON_ATTRS}><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>`,
};
export function showAlert(host, kind, text) {
    host.innerHTML = "";
    const box = document.createElement("div");
    box.className = `alert alert-${kind}`;
    box.setAttribute("role", "alert");
    box.innerHTML = ALERT_ICONS[kind];
    const body = document.createElement("div");
    body.textContent = text;
    box.appendChild(body);
    host.appendChild(box);
    host.hidden = false;
}
export function clearAlert(host) {
    host.innerHTML = "";
    host.hidden = true;
}
export function setPending(form, pending) {
    form.dataset.pending = pending ? "true" : "false";
    for (const el of qsa("input, button, select", form)) {
        el.disabled = pending;
    }
}
export function slowNotice(el, delayMs = 4000) {
    let timer = null;
    const stop = () => {
        if (timer !== null)
            window.clearTimeout(timer);
        timer = null;
        el.hidden = true;
    };
    const start = () => {
        stop();
        timer = window.setTimeout(() => {
            el.hidden = false;
        }, delayMs);
    };
    return { start, stop };
}
export function setupPasswordToggles(root = document) {
    for (const btn of qsa("[data-password-toggle]", root)) {
        btn.addEventListener("click", () => {
            const input = btn.parentElement?.querySelector("input");
            if (!input)
                return;
            const show = input.type === "password";
            input.type = show ? "text" : "password";
            btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
            btn.classList.toggle("is-visible", show);
        });
    }
}
export function formatIsoDate(iso, opts) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime()))
        return iso;
    const wantsTime = Boolean(opts && ("timeStyle" in opts || "hour" in opts || "minute" in opts));
    return wantsTime ? d.toLocaleString(undefined, opts) : d.toLocaleDateString(undefined, opts);
}
export function safeNext(value) {
    if (!value || !/^\/(?![/\\])/.test(value))
        return "/chat";
    return value;
}
export function el(tag, className = "", text, children = []) {
    const node = document.createElement(tag);
    if (className)
        node.className = className;
    if (text !== undefined)
        node.textContent = text;
    for (const child of children)
        node.appendChild(child);
    return node;
}
