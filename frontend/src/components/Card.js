import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export const Card = ({ title, children, className = '' }) => {
    return (_jsxs("div", { className: `card ${className}`, children: [title && _jsx("h2", { className: "text-lg font-bold mb-4", children: title }), children] }));
};
