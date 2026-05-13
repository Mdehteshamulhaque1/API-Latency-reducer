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
    return (_jsx("nav", { className: "bg-white shadow-md", children: _jsx("div", { className: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8", children: _jsxs("div", { className: "flex justify-between items-center h-16", children: [_jsxs(Link, { to: "/dashboard", className: "flex items-center space-x-2", children: [_jsx(Shield, { className: "w-8 h-8 text-blue-600" }), _jsx("span", { className: "text-xl font-bold text-gray-800", children: "API Optimizer" })] }), _jsxs("div", { className: "flex items-center space-x-8", children: [_jsxs(Link, { to: "/dashboard", className: "flex items-center space-x-1 text-gray-700 hover:text-blue-600", children: [_jsx(BarChart3, { className: "w-5 h-5" }), _jsx("span", { children: "Dashboard" })] }), _jsxs(Link, { to: "/rules", className: "flex items-center space-x-1 text-gray-700 hover:text-blue-600", children: [_jsx(Settings, { className: "w-5 h-5" }), _jsx("span", { children: "Cache Rules" })] }), _jsxs("div", { className: "flex items-center space-x-4 pl-8 border-l", children: [_jsx("span", { className: "text-gray-700", children: user?.username }), _jsxs("button", { onClick: handleLogout, className: "flex items-center space-x-1 text-red-600 hover:text-red-700", children: [_jsx(LogOut, { className: "w-5 h-5" }), _jsx("span", { children: "Logout" })] })] })] })] }) }) }));
};
