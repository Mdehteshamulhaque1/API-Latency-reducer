import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store';
import { LogOut, BarChart3, Settings, Shield } from 'lucide-react';
export const Navigation = () => {
    const navigate = useNavigate();
    const { logout, user } = useAuthStore();
    const handleLogout = () => {
        logout();
        navigate('/login');
    };
    return (_jsx("nav", { className: "glass-panel sticky top-0 z-30 border-x-0 border-t-0 rounded-none", children: _jsx("div", { className: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8", children: _jsxs("div", { className: "flex justify-between items-center h-16", children: [_jsxs(Link, { to: "/dashboard", className: "flex items-center space-x-2", children: [_jsx("span", { className: "flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-[rgb(10,102,194)] via-sky-500 to-pink-500 shadow-lg shadow-sky-500/25", children: _jsx(Shield, { className: "w-5 h-5 text-white" }) }), _jsx("span", { className: "text-xl font-extrabold tracking-tight text-slate-900", children: "API Optimizer" })] }), _jsxs("div", { className: "flex items-center space-x-8", children: [_jsxs(Link, { to: "/dashboard", className: "flex items-center space-x-1 text-slate-600 hover:text-[rgb(10,102,194)] transition-colors", children: [_jsx(BarChart3, { className: "w-5 h-5" }), _jsx("span", { children: "Dashboard" })] }), _jsxs(Link, { to: "/rules", className: "flex items-center space-x-1 text-slate-600 hover:text-pink-600 transition-colors", children: [_jsx(Settings, { className: "w-5 h-5" }), _jsx("span", { children: "Cache Rules" })] }), _jsxs("div", { className: "flex items-center space-x-4 pl-8 border-l border-sky-100", children: [_jsx("span", { className: "rounded-full bg-sky-50 px-3 py-1 text-sm font-semibold text-slate-700 ring-1 ring-sky-100", children: user?.username }), _jsxs("button", { onClick: handleLogout, className: "flex items-center space-x-1 rounded-full px-3 py-2 text-pink-600 hover:bg-pink-50 hover:text-pink-700 transition-colors", children: [_jsx(LogOut, { className: "w-5 h-5" }), _jsx("span", { children: "Logout" })] })] })] })] }) }) }));
};
