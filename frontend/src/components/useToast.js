import { jsx as _jsx } from "react/jsx-runtime";
import { useState } from 'react';
import { Toast } from './Toast';
export const useToast = () => {
    const [toasts, setToasts] = useState([]);
    const addToast = (message, type = 'info') => {
        const id = Math.random().toString(36).substr(2, 9);
        setToasts((prev) => [...prev, { id, message, type }]);
    };
    const removeToast = (id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    };
    const ToastContainer = () => (_jsx("div", { className: "fixed top-4 right-4 space-y-2 z-50", children: toasts.map((toast) => (_jsx(Toast, { message: toast.message, type: toast.type, onClose: () => removeToast(toast.id) }, toast.id))) }));
    return { addToast, removeToast, ToastContainer };
};
