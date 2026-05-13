import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import { rulesService } from '@/services/api-services';
import { Plus, Edit2, Trash2, Check, X } from 'lucide-react';
export const RulesPage = () => {
    const queryClient = useQueryClient();
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [formData, setFormData] = useState({
        endpoint_pattern: '',
        ttl: 3600,
        enabled: true,
        cache_by_user: false,
        cache_by_query_params: false,
        cache_by_headers: false,
        max_cache_size: 1000,
        priority: 0,
        description: '',
    });
    const { data: rules, isLoading } = useQuery('cacheRules', () => rulesService.listRules());
    const createMutation = useMutation((data) => rulesService.createRule(data), {
        onSuccess: () => {
            queryClient.invalidateQueries('cacheRules');
            resetForm();
        },
    });
    const updateMutation = useMutation((data) => rulesService.updateRule(editingId, data), {
        onSuccess: () => {
            queryClient.invalidateQueries('cacheRules');
            resetForm();
        },
    });
    const deleteMutation = useMutation((id) => rulesService.deleteRule(id), {
        onSuccess: () => {
            queryClient.invalidateQueries('cacheRules');
        },
    });
    const resetForm = () => {
        setFormData({
            endpoint_pattern: '',
            ttl: 3600,
            enabled: true,
            cache_by_user: false,
            cache_by_query_params: false,
            cache_by_headers: false,
            max_cache_size: 1000,
            priority: 0,
            description: '',
        });
        setShowForm(false);
        setEditingId(null);
    };
    const handleSubmit = (e) => {
        e.preventDefault();
        if (editingId) {
            updateMutation.mutate(formData);
        }
        else {
            createMutation.mutate(formData);
        }
    };
    if (isLoading) {
        return _jsx("div", { className: "flex h-96 items-center justify-center text-slate-500", children: "Loading..." });
    }
    return (_jsxs("div", { className: "space-y-6", children: [_jsxs("div", { className: "flex justify-between items-center", children: [_jsxs("div", { children: [_jsx("h1", { className: "text-3xl font-black tracking-tight text-slate-900", children: "Cache Rules" }), _jsx("p", { className: "mt-1 text-sm text-slate-500", children: "Configure policies with a LinkedIn-clean, Instagram-accented look." })] }), _jsxs("button", { onClick: () => setShowForm(true), className: "btn-primary flex items-center gap-2", children: [_jsx(Plus, { className: "w-5 h-5" }), "New Rule"] })] }), showForm && (_jsxs("div", { className: "card", children: [_jsx("h2", { className: "text-xl font-bold mb-4 text-slate-900", children: editingId ? 'Edit Rule' : 'Create New Rule' }), _jsxs("form", { onSubmit: handleSubmit, className: "space-y-4", children: [_jsxs("div", { className: "grid grid-cols-1 md:grid-cols-2 gap-4", children: [_jsxs("div", { children: [_jsx("label", { className: "block text-sm font-semibold text-slate-700 mb-1", children: "Endpoint Pattern" }), _jsx("input", { type: "text", value: formData.endpoint_pattern, onChange: (e) => setFormData({ ...formData, endpoint_pattern: e.target.value }), placeholder: "/api/users/*", className: "w-full rounded-2xl border border-sky-100 bg-white/90 px-3 py-2.5 text-slate-900 focus:outline-none focus:ring-4 focus:ring-sky-500/15", required: true })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-sm font-semibold text-slate-700 mb-1", children: "TTL (seconds)" }), _jsx("input", { type: "number", value: formData.ttl, onChange: (e) => setFormData({ ...formData, ttl: parseInt(e.target.value) }), className: "w-full rounded-2xl border border-sky-100 bg-white/90 px-3 py-2.5 text-slate-900 focus:outline-none focus:ring-4 focus:ring-sky-500/15", required: true })] })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-sm font-semibold text-slate-700 mb-2", children: "Description" }), _jsx("textarea", { value: formData.description, onChange: (e) => setFormData({ ...formData, description: e.target.value }), className: "w-full rounded-2xl border border-sky-100 bg-white/90 px-3 py-2.5 text-slate-900 focus:outline-none focus:ring-4 focus:ring-sky-500/15", rows: 3 })] }), _jsx("div", { className: "grid grid-cols-2 md:grid-cols-4 gap-4", children: [
                                    { key: 'enabled', label: 'Enabled' },
                                    { key: 'cache_by_user', label: 'Cache by User' },
                                    { key: 'cache_by_query_params', label: 'Cache by Query Params' },
                                    { key: 'cache_by_headers', label: 'Cache by Headers' },
                                ].map(({ key, label }) => (_jsxs("label", { className: "flex items-center space-x-2", children: [_jsx("input", { type: "checkbox", checked: formData[key], onChange: (e) => setFormData({ ...formData, [key]: e.target.checked }), className: "rounded border-sky-300 text-sky-600 focus:ring-sky-500" }), _jsx("span", { className: "text-sm text-slate-700", children: label })] }, key))) }), _jsxs("div", { className: "flex gap-2", children: [_jsx("button", { type: "submit", className: "btn-primary", children: editingId ? 'Update Rule' : 'Create Rule' }), _jsx("button", { type: "button", onClick: resetForm, className: "btn-secondary", children: "Cancel" })] })] })] })), _jsx("div", { className: "card overflow-x-auto", children: rules && rules.length > 0 ? (_jsxs("table", { className: "w-full text-sm", children: [_jsx("thead", { className: "bg-sky-50/80", children: _jsxs("tr", { children: [_jsx("th", { className: "px-4 py-2 text-left font-semibold text-slate-700", children: "Endpoint" }), _jsx("th", { className: "px-4 py-2 text-center font-semibold text-slate-700", children: "TTL" }), _jsx("th", { className: "px-4 py-2 text-center font-semibold text-slate-700", children: "Enabled" }), _jsx("th", { className: "px-4 py-2 text-center font-semibold text-slate-700", children: "Options" }), _jsx("th", { className: "px-4 py-2 text-center font-semibold text-slate-700", children: "Actions" })] }) }), _jsx("tbody", { children: rules.map((rule) => (_jsxs("tr", { className: "border-b border-sky-50 hover:bg-sky-50/60 transition-colors", children: [_jsx("td", { className: "px-4 py-2 font-mono text-sky-700 text-xs", children: rule.endpoint_pattern }), _jsxs("td", { className: "px-4 py-2 text-center", children: [rule.ttl, "s"] }), _jsx("td", { className: "px-4 py-2 text-center", children: rule.enabled ? (_jsx(Check, { className: "w-5 h-5 text-emerald-600 mx-auto" })) : (_jsx(X, { className: "w-5 h-5 text-rose-600 mx-auto" })) }), _jsx("td", { className: "px-4 py-2 text-center", children: _jsxs("div", { className: "flex gap-1 justify-center flex-wrap", children: [rule.cache_by_user && _jsx("span", { className: "badge badge-success text-xs", children: "User" }), rule.cache_by_query_params && _jsx("span", { className: "badge badge-success text-xs", children: "Params" }), rule.cache_by_headers && _jsx("span", { className: "badge badge-success text-xs", children: "Headers" })] }) }), _jsxs("td", { className: "px-4 py-2 text-center flex gap-2 justify-center", children: [_jsx("button", { onClick: () => {
                                                    setFormData(rule);
                                                    setEditingId(rule.id);
                                                    setShowForm(true);
                                                }, className: "rounded-full p-2 hover:bg-sky-100 transition-colors", children: _jsx(Edit2, { className: "w-4 h-4 text-sky-600" }) }), _jsx("button", { onClick: () => deleteMutation.mutate(rule.id), className: "rounded-full p-2 hover:bg-rose-100 transition-colors", children: _jsx(Trash2, { className: "w-4 h-4 text-rose-600" }) })] })] }, rule.id))) })] })) : (_jsx("div", { className: "text-center text-slate-500 py-8", children: "No cache rules created yet" })) })] }));
};
