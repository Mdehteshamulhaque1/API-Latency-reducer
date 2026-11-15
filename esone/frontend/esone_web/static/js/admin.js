import { ApiError, AUTH_EVENT, apiAdminUpdateUser, apiAdminUsers, authGetAccessToken, authGetClaims, } from "./api.js";
import { clearAlert, el, formatIsoDate, qs, showAlert } from "./dom.js";
const ROLES = ["viewer", "operator", "admin"];
const ROLE_TONE = { admin: "pill-ink", operator: "pill-saffron", viewer: "pill-brand" };
const ui = {
    notAdmin: qs("#not-admin"),
    panel: qs("#admin-panel"),
    actions: qs("#admin-actions"),
    error: qs("#admin-error"),
    notice: qs("#admin-notice"),
    total: qs("#users-total"),
    body: qs("#users-body"),
    reload: qs("#reload-btn"),
};
let selfId = null;
let users = null;
let total = 0;
let busyId = null;
function renderSkeleton() {
    ui.body.innerHTML = "";
    const wrap = el("div", "stack-sm pad");
    for (let i = 0; i < 3; i += 1)
        wrap.appendChild(el("div", "skeleton skeleton-row-lg"));
    ui.body.appendChild(wrap);
}
function renderUsers() {
    ui.total.textContent = users ? `${total} total` : "";
    if (!users) {
        renderSkeleton();
        return;
    }
    ui.body.innerHTML = "";
    if (users.length === 0) {
        ui.body.appendChild(el("p", "empty", "No users found."));
        return;
    }
    const table = el("table", "table");
    const thead = el("thead");
    const headRow = el("tr");
    for (const label of ["User", "Role", "Status", "Joined", "Actions"]) {
        const th = el("th", label === "Actions" ? "text-right" : "", label);
        headRow.appendChild(th);
    }
    thead.appendChild(headRow);
    table.appendChild(thead);
    const tbody = el("tbody");
    for (const user of users)
        tbody.appendChild(renderRow(user));
    table.appendChild(tbody);
    const scroller = el("div", "table-scroll", undefined, [table]);
    ui.body.appendChild(scroller);
}
function renderRow(user) {
    const self = user.id === selfId;
    const busy = busyId === user.id;
    const row = el("tr");
    const who = el("td");
    const name = el("p", "table-primary", user.username);
    if (self)
        name.appendChild(el("span", "table-you", "(you)"));
    who.appendChild(name);
    who.appendChild(el("p", "table-secondary", user.email));
    row.appendChild(who);
    const roleCell = el("td");
    const select = el("select", `pill pill-select ${ROLE_TONE[user.role] ?? "pill-neutral"}`);
    select.setAttribute("aria-label", `Role for ${user.username}`);
    for (const role of ROLES) {
        const option = el("option", "", role);
        option.value = role;
        option.selected = role === user.role;
        select.appendChild(option);
    }
    select.disabled = self || busy;
    select.addEventListener("change", () => void patch(user, { role: select.value }));
    roleCell.appendChild(select);
    row.appendChild(roleCell);
    const statusCell = el("td");
    statusCell.appendChild(el("span", `badge ${user.is_active ? "badge-live" : "badge-danger"}`, user.is_active ? "active" : "disabled"));
    row.appendChild(statusCell);
    row.appendChild(el("td", "text-muted", formatIsoDate(user.created_at)));
    const actionCell = el("td", "text-right");
    const button = el("button", `btn btn-sm ${user.is_active ? "btn-outline" : "btn-subtle"}`);
    button.type = "button";
    button.disabled = self || busy;
    if (busy)
        button.appendChild(el("span", "spinner"));
    button.appendChild(document.createTextNode(user.is_active ? "Deactivate" : "Reactivate"));
    button.addEventListener("click", () => void patch(user, { is_active: !user.is_active }));
    actionCell.appendChild(button);
    row.appendChild(actionCell);
    return row;
}
async function load() {
    clearAlert(ui.error);
    users = null;
    renderUsers();
    try {
        const list = await apiAdminUsers(200, 0);
        users = list.items;
        total = list.total;
    }
    catch (err) {
        users = [];
        showAlert(ui.error, "destructive", err instanceof ApiError ? err.message : "Could not reach the authentication server.");
    }
    renderUsers();
}
async function patch(user, body) {
    busyId = user.id;
    clearAlert(ui.notice);
    clearAlert(ui.error);
    renderUsers();
    try {
        const updated = await apiAdminUpdateUser(user.id, body);
        users = users ? users.map((u) => (u.id === updated.id ? updated : u)) : users;
        showAlert(ui.notice, "success", `Updated ${updated.username}.`);
    }
    catch (err) {
        showAlert(ui.error, "destructive", err instanceof ApiError ? err.message : "Could not reach the authentication server.");
    }
    finally {
        busyId = null;
        renderUsers();
    }
}
ui.reload.addEventListener("click", () => void load());
let wasAdmin = null;
function sync() {
    if (!authGetAccessToken()) {
        window.location.replace("/login?next=/admin");
        return;
    }
    const claims = authGetClaims();
    selfId = claims?.sub ? Number(claims.sub) : null;
    const admin = claims?.role === "admin";
    ui.notAdmin.hidden = admin;
    ui.panel.hidden = !admin;
    ui.actions.hidden = !admin;
    if (admin && wasAdmin !== true)
        void load();
    wasAdmin = admin;
}
sync();
window.addEventListener(AUTH_EVENT, sync);
window.addEventListener("storage", sync);
