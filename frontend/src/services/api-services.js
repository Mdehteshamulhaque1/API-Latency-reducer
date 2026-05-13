import apiClient from './api';
export const analyticsService = {
    getSummary: async (hours = 24) => {
        const response = await apiClient.get('/api/v1/analytics/summary', {
            params: { hours },
        });
        return response.data;
    },
    getEndpointLogs: async (endpoint, limit = 100, hours = 24) => {
        const response = await apiClient.get('/api/v1/analytics/endpoints', {
            params: { endpoint_pattern: endpoint, limit, hours },
        });
        return response.data;
    },
    getBenchmarkReport: async (hours = 24) => {
        const response = await apiClient.get('/api/v1/analytics/benchmark', {
            params: { hours },
        });
        return response.data;
    },
    runBenchmarkReport: async (hours = 24) => {
        const response = await apiClient.post('/api/v1/analytics/benchmark/run', undefined, {
            params: { hours },
        });
        return response.data;
    },
    getOptimizationSuggestions: async (hours = 24) => {
        const response = await apiClient.get('/api/v1/analytics/suggestions', {
            params: { hours },
        });
        return response.data;
    },
};
export const rulesService = {
    listRules: async (skip = 0, limit = 100) => {
        const response = await apiClient.get('/api/v1/rules', {
            params: { skip, limit },
        });
        return response.data;
    },
    getRule: async (id) => {
        const response = await apiClient.get(`/api/v1/rules/${id}`);
        return response.data;
    },
    createRule: async (data) => {
        const response = await apiClient.post('/api/v1/rules', data);
        return response.data;
    },
    updateRule: async (id, data) => {
        const response = await apiClient.put(`/api/v1/rules/${id}`, data);
        return response.data;
    },
    deleteRule: async (id) => {
        await apiClient.delete(`/api/v1/rules/${id}`);
    },
};
