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
    return (_jsx("div", { className: "min-h-screen bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center", children: _jsx("div", { className: "w-full max-w-md", children: _jsxs("div", { className: "card", children: [_jsx("h1", { className: "text-3xl font-bold text-center mb-8 text-gray-800", children: "API Optimizer" }), error && _jsx("div", { className: "bg-red-100 text-red-700 p-3 rounded mb-4", children: error }), _jsxs("form", { onSubmit: handleSubmit, children: [_jsxs("div", { className: "mb-4", children: [_jsx("label", { className: "block text-gray-700 font-semibold mb-2", children: "Username" }), _jsx("input", { type: "text", value: formData.username, onChange: (e) => setFormData({ ...formData, username: e.target.value }), className: "w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500", required: true })] }), _jsxs("div", { className: "mb-6", children: [_jsx("label", { className: "block text-gray-700 font-semibold mb-2", children: "Password" }), _jsx("input", { type: "password", value: formData.password, onChange: (e) => setFormData({ ...formData, password: e.target.value }), className: "w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500", required: true })] }), _jsx("button", { type: "submit", disabled: loading, className: "w-full btn-primary disabled:opacity-50", children: loading ? 'Logging in...' : 'Login' })] }), _jsxs("p", { className: "text-center text-gray-600 mt-4", children: ["Don't have an account?", ' ', _jsx("a", { href: "/register", className: "text-blue-600 hover:underline", children: "Register" })] }), _jsxs("div", { className: "mt-6 p-3 bg-blue-50 rounded text-sm text-gray-700", children: [_jsx("p", { className: "font-semibold mb-2", children: "Demo Credentials:" }), _jsx("p", { children: "Username: demo_user" }), _jsx("p", { children: "Password: DemoPassword123!" })] })] }) }) }));
};
