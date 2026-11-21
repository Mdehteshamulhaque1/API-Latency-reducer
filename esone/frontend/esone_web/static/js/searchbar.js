import { qs } from "./dom.js";
export function wireSearchBar() {
    const form = qs("#search-form");
    const input = qs("#search-input");
    const clear = qs("#search-clear");
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const q = input.value.trim();
        if (q.length < 3) {
            input.focus();
            return;
        }
        window.location.assign(`/chat?q=${encodeURIComponent(q)}`);
    });
    input.addEventListener("input", () => {
        clear.hidden = input.value.length === 0;
    });
    clear.addEventListener("click", () => {
        input.value = "";
        clear.hidden = true;
        input.focus();
    });
}
