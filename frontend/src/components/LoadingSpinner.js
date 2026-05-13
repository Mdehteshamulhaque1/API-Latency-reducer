import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Loader } from 'lucide-react';
export const LoadingSpinner = ({ message, size = 'md' }) => {
    const sizeClasses = {
        sm: 'w-4 h-4',
        md: 'w-8 h-8',
        lg: 'w-12 h-12',
    };
    return (_jsxs("div", { className: "flex flex-col items-center justify-center space-y-3", children: [_jsx(Loader, { className: `${sizeClasses[size]} animate-spin text-sky-600` }), message && _jsx("p", { className: "text-slate-600", children: message })] }));
};
