function resolveBaseUrl(raw) {
    const value = (raw ?? "").trim().replace(/\/+$/, "");
    if (!value)
        return "http://localhost:8000";
    return /^https?:\/\//i.test(value) ? value : `https://${value}`;
}
const META = document.querySelector('meta[name="esone-api-url"]');
export const API_BASE_URL = resolveBaseUrl(META?.content);
export class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}
async function readErrorMessage(res) {
    try {
        const data = await res.json();
        if (data && typeof data === "object" && "detail" in data) {
            const detail = data.detail;
            if (typeof detail === "string")
                return detail;
            if (Array.isArray(detail)) {
                const parts = detail.map((item) => {
                    if (item && typeof item === "object" && "msg" in item) {
                        return String(item.msg);
                    }
                    return typeof item === "string" ? item : "Invalid value";
                });
                if (parts.length > 0)
                    return parts.join(", ");
            }
        }
    }
    catch {
    }
    if (res.status === 401)
        return "Invalid username or password";
    if (res.status === 403)
        return "You do not have permission to do that";
    if (res.status === 429)
        return "Too many requests. Please try again shortly";
    return `Request failed (${res.status})`;
}
async function request(path, init = {}) {
    const url = new URL(path, API_BASE_URL);
    const headers = {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
    };
    return fetch(url.toString(), { ...init, headers });
}
function authHeaders() {
    const access = localStorage.getItem("access_token");
    return access ? { Authorization: `Bearer ${access}` } : {};
}
export const AUTH_EVENT = "auth-status-changed";
function notifyAuthChanged() {
    window.dispatchEvent(new Event(AUTH_EVENT));
}
function clearTokens() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    notifyAuthChanged();
}
let refreshInFlight = null;
function refreshTokens() {
    if (refreshInFlight)
        return refreshInFlight;
    refreshInFlight = (async () => {
        const refresh = localStorage.getItem("refresh_token");
        if (!refresh) {
            clearTokens();
            return false;
        }
        try {
            const res = await request("/api/v1/auth/refresh", {
                method: "POST",
                body: JSON.stringify({ refresh_token: refresh }),
            });
            if (!res.ok) {
                clearTokens();
                return false;
            }
            const data = (await res.json());
            localStorage.setItem("access_token", data.access_token);
            if (data.refresh_token)
                localStorage.setItem("refresh_token", data.refresh_token);
            notifyAuthChanged();
            return true;
        }
        catch {
            return false;
        }
        finally {
            refreshInFlight = null;
        }
    })();
    return refreshInFlight;
}
export async function requestWithRefresh(path, init = {}) {
    const res = await request(path, init);
    if (res.status !== 401)
        return res;
    if (!(await refreshTokens()))
        return null;
    return request(path, { ...init, headers: { ...(init.headers ?? {}), ...authHeaders() } });
}
export async function authLogin(username, password) {
    const res = await request("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
    });
    if (!res.ok)
        throw new ApiError(await readErrorMessage(res), res.status);
    return res.json();
}
export async function authRegister(username, email, password) {
    const res = await request("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
    });
    if (!res.ok)
        throw new ApiError(await readErrorMessage(res), res.status);
    return authLogin(username, password);
}
export async function authRefresh() {
    const ok = await refreshTokens();
    const access = ok ? authGetAccessToken() : null;
    if (!access)
        throw new ApiError("Session expired. Please sign in again", 401);
    return { access_token: access };
}
export function authLogout() {
    const refresh = localStorage.getItem("refresh_token");
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    notifyAuthChanged();
    if (refresh) {
        void request("/api/v1/auth/logout", {
            method: "POST",
            body: JSON.stringify({ refresh_token: refresh }),
        }).catch(() => undefined);
    }
}
export function authStoreTokens(tokens) {
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    notifyAuthChanged();
}
export function authGetAccessToken() {
    return localStorage.getItem("access_token");
}
function decodeTokenPayload(token) {
    try {
        const segment = token.split(".")[1];
        if (!segment)
            return null;
        const base64 = segment.replace(/-/g, "+").replace(/_/g, "/");
        const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
        const json = decodeURIComponent(Array.from(atob(padded))
            .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
            .join(""));
        const payload = JSON.parse(json);
        return payload && typeof payload === "object" ? payload : null;
    }
    catch {
        return null;
    }
}
function toClaims(payload) {
    const str = (v) => (typeof v === "string" ? v : null);
    const exp = payload.exp;
    return {
        sub: str(payload.sub),
        role: str(payload.role),
        type: str(payload.type),
        exp: typeof exp === "number" ? exp : null,
    };
}
export function authGetClaims() {
    const token = authGetAccessToken();
    if (!token)
        return null;
    const payload = decodeTokenPayload(token);
    return payload ? toClaims(payload) : null;
}
export function authGetRefreshClaims() {
    const token = localStorage.getItem("refresh_token");
    if (!token)
        return null;
    const payload = decodeTokenPayload(token);
    return payload ? toClaims(payload) : null;
}
export function authGetRole() {
    const token = authGetAccessToken();
    if (!token)
        return null;
    const role = decodeTokenPayload(token)?.role;
    return typeof role === "string" ? role : null;
}
async function authed(path, init = {}) {
    const res = await requestWithRefresh(path, {
        ...init,
        headers: { ...(init.headers ?? {}), ...authHeaders() },
    });
    if (!res)
        throw new ApiError("Session expired. Please sign in again", 401);
    if (!res.ok)
        throw new ApiError(await readErrorMessage(res), res.status);
    return res;
}
export async function apiMe() {
    const res = await authed("/api/v1/users/me", { method: "GET" });
    return res.json();
}
export async function apiChangePassword(currentPassword, newPassword) {
    await authed("/api/v1/users/me/password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
}
export async function apiAdminUsers(limit = 50, offset = 0) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    const res = await authed(`/api/v1/admin/users?${params.toString()}`, { method: "GET" });
    return res.json();
}
export async function apiAdminUpdateUser(id, patch) {
    const res = await authed(`/api/v1/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
    return res.json();
}
export async function apiHealth() {
    const res = await request("/api/v1/health", { method: "GET" });
    if (!res.ok)
        throw new ApiError(await readErrorMessage(res), res.status);
    return res.json();
}
