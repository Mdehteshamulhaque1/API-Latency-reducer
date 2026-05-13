import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '@/services/auth';
import { useAuthStore } from '@/store';
export const LoginPage = () => {
    const navigate = useNavigate();
    const login = useAuthStore((state) => state.login);
    const [formData, setFormData] = useState({ username: '', password: '' });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const response = await authService.login(formData);
            login(response.access_token, response.refresh_token, { username: formData.username });
            navigate('/dashboard');
        }
        catch (err) {
            setError(err.response?.data?.detail || 'Login failed');
        }
        finally {
            setLoading(false);
        }
    };
    return (_jsxs("div", { className: "surface-shell flex min-h-screen items-center justify-center px-4 py-10", children: [_jsx("div", { className: "absolute inset-x-0 top-10 flex justify-center", children: _jsx("div", { className: "h-44 w-44 rounded-full bg-sky-400/20 blur-3xl" }) }), _jsx("div", { className: "relative w-full max-w-md", children: _jsxs("div", { className: "card", children: [_jsxs("div", { className: "mb-8 text-center", children: [_jsx("div", { className: "mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-600 via-blue-600 to-pink-500 text-white shadow-lg shadow-sky-500/25", children: _jsx("span", { className: "text-xl font-black", children: "A" }) }), _jsx("h1", { className: "text-3xl font-black tracking-tight text-slate-900", children: "API Optimizer" }), _jsx("p", { className: "mt-2 text-sm text-slate-500", children: "LinkedIn clarity with Instagram energy" })] }), error && _jsx("div", { className: "mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700", children: error }), _jsxs("form", { onSubmit: handleSubmit, children: [_jsxs("div", { className: "mb-4", children: [_jsx("label", { className: "mb-2 block font-semibold text-slate-700", children: "Username" }), _jsx("input", { type: "text", value: formData.username, onChange: (e) => setFormData({ ...formData, username: e.target.value }), className: "w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15", required: true })] }), _jsxs("div", { className: "mb-6", children: [_jsx("label", { className: "mb-2 block font-semibold text-slate-700", children: "Password" }), _jsx("input", { type: "password", value: formData.password, onChange: (e) => setFormData({ ...formData, password: e.target.value }), className: "w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15", required: true })] }), _jsx("button", { type: "submit", disabled: loading, className: "w-full btn-primary disabled:opacity-50", children: loading ? 'Logging in...' : 'Login' })] }), _jsxs("p", { className: "mt-4 text-center text-slate-500", children: ["Don't have an account?", ' ', _jsx("a", { href: "/register", className: "font-semibold text-sky-700 hover:text-pink-600 hover:underline", children: "Register" })] }), _jsxs("div", { className: "mt-6 rounded-2xl border border-sky-100 bg-sky-50/80 p-4 text-sm text-slate-700", children: [_jsx("p", { className: "mb-2 font-semibold text-slate-900", children: "Demo Credentials:" }), _jsx("p", { children: "Username: demo_user" }), _jsx("p", { children: "Password: DemoPassword123!" })] })] }) })] }));
};
