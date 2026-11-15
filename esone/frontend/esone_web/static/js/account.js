import { API_BASE_URL, ApiError, AUTH_EVENT, apiChangePassword, apiHealth, apiMe, authGetAccessToken, authGetClaims, authGetRefreshClaims, authLogin, authRefresh, authStoreTokens, } from "./api.js";
import { clearAlert, el, formatCountdown, formatDate, formatIsoDate, qs, setPending, setupPasswordToggles, showAlert, } from "./dom.js";
const PASSWORD_MIN = 8;
const ROLE_TONE = { admin: "pill-ink", operator: "pill-saffron", viewer: "pill-brand" };
const ui = {
    skeleton: qs("#console-skeleton"),
    console: qs("#console"),
    notice: qs("#console-notice"),
    statSub: qs("#stat-sub"),
    statRole: qs("#stat-role"),
    accessCard: qs("#stat-access-card"),
    statAccess: qs("#stat-access"),
    statAccessHint: qs("#stat-access-hint"),
    statRefresh: qs("#stat-refresh"),
    statRefreshHint: qs("#stat-refresh-hint"),
    claims: qs("#claims"),
    rolePill: qs("#role-pill"),
    typeBadge: qs("#type-badge"),
    activeBadge: qs("#active-badge"),
    expiredAlert: qs("#expired-alert"),
    healthBody: qs("#health-body"),
    healthMeta: qs("#health-meta"),
    reloadHealth: qs("#reload-health"),
    profileBody: qs("#profile-body"),
    rotate: qs("#rotate-btn"),
    passwordForm: qs("#password-form"),
    passwordAlert: qs("#password-alert"),
    passwordSubmit: qs("#password-submit"),
    current: qs("#current-password"),
    next: qs("#new-password"),
    confirm: qs("#confirm-password"),
};
let claims = null;
let refreshClaims = null;
let profile = null;
function renderClaims() {
    if (!claims)
        return;
    ui.statSub.textContent = claims.sub ?? "n/a";
    ui.statRole.textContent = claims.role ?? "n/a";
    ui.claims.innerHTML = "";
    const rows = [
        ["sub", claims.sub ?? "null"],
        ["role", claims.role ?? "null"],
        ["type", claims.type ?? "null"],
        ["exp", claims.exp ? String(claims.exp) : "null"],
    ];
    ui.claims.appendChild(el("span", "claims-brace", "{"));
    for (const [key, value] of rows) {
        const shown = key === "exp" ? value : `"${value}"`;
        ui.claims.appendChild(el("div", "claims-row", undefined, [el("span", "claims-key", `"${key}":`), el("span", "claims-value", `${shown},`)]));
    }
    ui.claims.appendChild(el("span", "claims-brace", "}"));
    if (claims.role) {
        ui.rolePill.textContent = claims.role;
        ui.rolePill.className = `pill ${ROLE_TONE[claims.role] ?? "pill-neutral"}`;
        ui.rolePill.hidden = false;
    }
    else {
        ui.rolePill.hidden = true;
    }
    ui.typeBadge.textContent = `type: ${claims.type ?? "unknown"}`;
    tick();
}
function tick() {
    if (!claims)
        return;
    const now = Math.floor(Date.now() / 1000);
    const remaining = claims.exp ? claims.exp - now : 0;
    const expired = Boolean(claims.exp) && remaining <= 0;
    ui.statAccess.textContent = formatCountdown(remaining);
    ui.statAccess.classList.toggle("is-danger", expired);
    ui.accessCard.dataset.tone = expired ? "danger" : remaining < 120 ? "saffron" : "brand";
    ui.statAccessHint.textContent = formatDate(claims.exp);
    if (refreshClaims) {
        const refreshRemaining = refreshClaims.exp ? refreshClaims.exp - now : 0;
        ui.statRefresh.textContent = formatCountdown(refreshRemaining);
        ui.statRefreshHint.textContent = formatDate(refreshClaims.exp);
    }
    else {
        ui.statRefresh.textContent = "n/a";
        ui.statRefreshHint.textContent = "no refresh token";
    }
    ui.activeBadge.textContent = expired ? "expired" : "active";
    ui.activeBadge.className = `badge ${expired ? "badge-danger" : "badge-live"}`;
    ui.expiredAlert.hidden = !expired;
}
function healthBadge(value) {
    const ok = value === "healthy" || value === "ok";
    const badge = el("span", `badge ${ok ? "badge-live" : "badge-accent"}`);
    badge.appendChild(el("span", `dot ${ok ? "dot-brand dot-pulse" : "dot-saffron"}`));
    badge.appendChild(document.createTextNode(value ?? "unknown"));
    return badge;
}
function renderHealth(health, error) {
    ui.healthBody.innerHTML = "";
    if (error) {
        showAlert(ui.healthBody, "destructive", error);
    }
    else if (!health) {
        for (let i = 0; i < 3; i += 1)
            ui.healthBody.appendChild(el("div", "skeleton skeleton-row"));
    }
    else {
        const list = el("ul", "rows");
        const rows = [
            ["API", health.status],
            ["Database", health.database],
        ];
        for (const [label, value] of rows) {
            const row = el("li", "row");
            row.appendChild(el("span", "row-label", label));
            row.appendChild(healthBadge(value));
            list.appendChild(row);
        }
        ui.healthBody.appendChild(list);
    }
    ui.healthMeta.textContent = `${health?.version ? `version ${health.version} | ` : ""}${API_BASE_URL}`;
}
async function loadHealth() {
    renderHealth(null, null);
    try {
        renderHealth(await apiHealth(), null);
    }
    catch (err) {
        renderHealth(null, err instanceof ApiError ? err.message : "Backend unreachable");
    }
}
function renderProfile(error) {
    ui.profileBody.innerHTML = "";
    if (error) {
        showAlert(ui.profileBody, "destructive", error);
        return;
    }
    if (!profile) {
        for (let i = 0; i < 3; i += 1)
            ui.profileBody.appendChild(el("div", "skeleton skeleton-row"));
        return;
    }
    const list = el("ul", "rows");
    const rows = [
        ["Username", profile.username],
        ["Email", profile.email],
        ["Member since", formatIsoDate(profile.created_at, { dateStyle: "long" })],
    ];
    for (const [label, value] of rows) {
        const row = el("li", "row");
        row.appendChild(el("span", "row-label", label));
        row.appendChild(el("span", "row-value", value));
        list.appendChild(row);
    }
    ui.profileBody.appendChild(list);
}
async function loadProfile() {
    profile = null;
    renderProfile(null);
    try {
        profile = await apiMe();
        renderProfile(null);
    }
    catch (err) {
        renderProfile(err instanceof ApiError ? err.message : "Backend unreachable");
    }
}
ui.rotate.addEventListener("click", async () => {
    ui.rotate.disabled = true;
    ui.rotate.dataset.pending = "true";
    clearAlert(ui.notice);
    try {
        await authRefresh();
        showAlert(ui.notice, "success", "Token pair rotated. New expiry applied.");
    }
    catch (err) {
        showAlert(ui.notice, "destructive", err instanceof ApiError ? err.message : "Refresh failed. Sign in again.");
    }
    finally {
        ui.rotate.disabled = false;
        ui.rotate.dataset.pending = "false";
    }
});
ui.reloadHealth.addEventListener("click", () => void loadHealth());
function updatePasswordButton() {
    const pending = ui.passwordForm.dataset.pending === "true";
    ui.passwordSubmit.disabled = pending || !ui.current.value || !ui.next.value || !ui.confirm.value;
}
for (const input of [ui.current, ui.next, ui.confirm])
    input.addEventListener("input", updatePasswordButton);
setupPasswordToggles(ui.passwordForm);
updatePasswordButton();
ui.passwordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearAlert(ui.passwordAlert);
    if (ui.next.value.length < PASSWORD_MIN) {
        showAlert(ui.passwordAlert, "destructive", `New password must have at least ${PASSWORD_MIN} characters.`);
        return;
    }
    if (ui.next.value !== ui.confirm.value) {
        showAlert(ui.passwordAlert, "destructive", "New passwords do not match.");
        return;
    }
    const newPassword = ui.next.value;
    setPending(ui.passwordForm, true);
    try {
        await apiChangePassword(ui.current.value, newPassword);
        if (profile?.username) {
            authStoreTokens(await authLogin(profile.username, newPassword));
        }
        ui.current.value = "";
        ui.next.value = "";
        ui.confirm.value = "";
        showAlert(ui.passwordAlert, "success", "Password changed. Other sessions have been signed out.");
    }
    catch (err) {
        showAlert(ui.passwordAlert, "destructive", err instanceof ApiError ? err.message : "Could not reach the authentication server.");
    }
    finally {
        setPending(ui.passwordForm, false);
        updatePasswordButton();
    }
});
function sync() {
    if (!authGetAccessToken()) {
        window.location.replace("/login?next=/account");
        return;
    }
    claims = authGetClaims();
    refreshClaims = authGetRefreshClaims();
    renderClaims();
    ui.skeleton.hidden = true;
    ui.console.hidden = false;
    void loadHealth();
    void loadProfile();
}
sync();
window.setInterval(tick, 1000);
window.addEventListener(AUTH_EVENT, sync);
window.addEventListener("storage", sync);
