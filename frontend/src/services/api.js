import axios from 'axios';
import { useAuthStore } from '../store';
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});
// Add auth token to requests
apiClient.interceptors.request.use((config) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});
// Handle token refresh
apiClient.interceptors.response.use((response) => response, async (error) => {
    if (error.response?.status === 401) {
        useAuthStore.getState().logout();
        window.location.href = '/login';
    }
    return Promise.reject(error);
});
export default apiClient;
