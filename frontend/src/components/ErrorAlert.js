import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { AlertCircle } from 'lucide-react';
export const ErrorAlert = ({ title, message, onDismiss, variant = 'error', }) => {
    const variantClasses = {
        error: 'bg-red-50 text-red-800 border-red-200',
        warning: 'bg-yellow-50 text-yellow-800 border-yellow-200',
        info: 'bg-blue-50 text-blue-800 border-blue-200',
    };
    return (_jsx("div", { className: `border rounded-lg p-4 ${variantClasses[variant]}`, children: _jsxs("div", { className: "flex items-start space-x-3", children: [_jsx(AlertCircle, { className: "w-5 h-5 flex-shrink-0 mt-0.5" }), _jsxs("div", { className: "flex-1", children: [title && _jsx("h3", { className: "font-semibold mb-1", children: title }), _jsx("p", { className: "text-sm", children: message })] }), onDismiss && (_jsx("button", { onClick: onDismiss, className: "text-gray-400 hover:text-gray-600", children: "\u2715" }))] }) }));
};
