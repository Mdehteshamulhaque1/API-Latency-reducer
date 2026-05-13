import { jsx as _jsx } from "react/jsx-runtime";
export const Skeleton = ({ className = 'h-12 w-full', count = 1 }) => {
    return (_jsx("div", { className: "space-y-2", children: Array.from({ length: count }).map((_, i) => (_jsx("div", { className: `${className} bg-slate-200 animate-pulse rounded` }, i))) }));
};
