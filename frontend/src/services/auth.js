import apiClient from './api';
export const authService = {
    register: async (data) => {
        const response = await apiClient.post('/api/v1/auth/register', data);
        return response.data;
    },
    login: async (credentials) => {
        const response = await apiClient.post('/api/v1/auth/login', credentials);
        return response.data;
    },
    refresh: async (refreshToken) => {
        const response = await apiClient.post('/api/v1/auth/refresh', {
            refresh_token: refreshToken,
        });
        return response.data;
    },
};
