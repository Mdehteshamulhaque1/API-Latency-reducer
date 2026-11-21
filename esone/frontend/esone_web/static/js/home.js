import { qs, qsa } from "./dom.js";
const form = qs("#search-form");
const input = qs("#search-input");
const clear = qs("#search-clear");
const lucky = qs("#search-lucky");
const chips = qsa("#search-chips .chip");
function go(question) {
    const q = question.trim();
    if (q.length < 3) {
        input.focus();
        return;
    }
    window.location.assign(`/chat?q=${encodeURIComponent(q)}`);
}
form.addEventListener("submit", (event) => {
    event.preventDefault();
    go(input.value);
});
input.addEventListener("input", () => {
    clear.hidden = input.value.length === 0;
});
clear.addEventListener("click", () => {
    input.value = "";
    clear.hidden = true;
    input.focus();
});
for (const chip of chips)
    chip.addEventListener("click", () => go(chip.dataset.question ?? ""));
lucky.addEventListener("click", () => {
    const pick = chips[Math.floor(Math.random() * chips.length)];
    if (pick)
        go(pick.dataset.question ?? "");
});
input.focus();
