import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle } from 'lucide-react';
export const Toast = ({ message, type, onClose }) => {
    const typeClasses = {
        success: 'bg-green-50 text-green-800 border-green-200',
        error: 'bg-red-50 text-red-800 border-red-200',
        warning: 'bg-yellow-50 text-yellow-800 border-yellow-200',
        info: 'bg-blue-50 text-blue-800 border-blue-200',
    };
    const icons = {
        success: _jsx(CheckCircle2, { className: "w-5 h-5" }),
        error: _jsx(AlertCircle, { className: "w-5 h-5" }),
        warning: _jsx(AlertTriangle, { className: "w-5 h-5" }),
        info: _jsx(Info, { className: "w-5 h-5" }),
    };
    React.useEffect(() => {
        if (onClose) {
            const timer = setTimeout(onClose, 5000);
            return () => clearTimeout(timer);
        }
    }, [onClose]);
    return (_jsxs("div", { className: `border rounded-lg p-4 flex items-center space-x-3 ${typeClasses[type]}`, children: [icons[type], _jsx("span", { children: message })] }));
};
