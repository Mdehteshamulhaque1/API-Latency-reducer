import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authService } from '@/services/auth';
export const RegisterPage = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match');
            return;
        }
        setLoading(true);
        try {
            await authService.register({
                username: formData.username,
                email: formData.email,
                password: formData.password,
            });
            navigate('/login?registered=true');
        }
        catch (err) {
            setError(err.response?.data?.detail || 'Registration failed');
        }
        finally {
            setLoading(false);
        }
    };
    return (_jsxs("div", { className: "surface-shell flex min-h-screen items-center justify-center px-4 py-10", children: [_jsx("div", { className: "absolute inset-x-0 top-10 flex justify-center", children: _jsx("div", { className: "h-44 w-44 rounded-full bg-pink-400/20 blur-3xl" }) }), _jsx("div", { className: "relative w-full max-w-md", children: _jsxs("div", { className: "card", children: [_jsx("h1", { className: "mb-2 text-center text-3xl font-black tracking-tight text-slate-900", children: "Create Account" }), _jsx("p", { className: "mb-8 text-center text-sm text-slate-500", children: "Join the dashboard with a polished social-inspired theme." }), error && _jsx("div", { className: "mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700", children: error }), _jsxs("form", { onSubmit: handleSubmit, children: [_jsxs("div", { className: "mb-4", children: [_jsx("label", { className: "mb-2 block font-semibold text-slate-700", children: "Username" }), _jsx("input", { type: "text", value: formData.username, onChange: (e) => setFormData({ ...formData, username: e.target.value }), className: "w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15", minLength: 3, required: true })] }), _jsxs("div", { className: "mb-4", children: [_jsx("label", { className: "mb-2 block font-semibold text-slate-700", children: "Email" }), _jsx("input", { type: "email", value: formData.email, onChange: (e) => setFormData({ ...formData, email: e.target.value }), className: "w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15", required: true })] }), _jsxs("div", { className: "mb-4", children: [_jsx("label", { className: "mb-2 block font-semibold text-slate-700", children: "Password" }), _jsx("input", { type: "password", value: formData.password, onChange: (e) => setFormData({ ...formData, password: e.target.value }), className: "w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15", minLength: 8, required: true })] }), _jsxs("div", { className: "mb-6", children: [_jsx("label", { className: "mb-2 block font-semibold text-slate-700", children: "Confirm Password" }), _jsx("input", { type: "password", value: formData.confirmPassword, onChange: (e) => setFormData({ ...formData, confirmPassword: e.target.value }), className: "w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15", minLength: 8, required: true })] }), _jsx("button", { type: "submit", disabled: loading, className: "w-full btn-primary disabled:opacity-50", children: loading ? 'Creating account...' : 'Register' })] }), _jsxs("p", { className: "mt-4 text-center text-slate-500", children: ["Already have an account?", ' ', _jsx(Link, { to: "/login", className: "font-semibold text-sky-700 hover:text-pink-600 hover:underline", children: "Login" })] })] }) })] }));
};
