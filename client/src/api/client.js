import axios from 'axios';
import { auth } from '../config/firebase';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

apiClient.interceptors.request.use(async (config) => {
    try {
        const user = auth.currentUser;
        if (user) {
            const token = await user.getIdToken();
            config.headers.Authorization = `Bearer ${token}`;
        } else {
            console.warn('No authenticated user found for API request');
        }
    } catch (error) {
        console.error('Error getting auth token:', error);
    }
    return config;
});

export const authAPI = {
    verifyToken: async (idToken) => {
        const response = await apiClient.post('/auth/verify', { idToken });
        return response.data;
    },
    getCurrentUser: async () => {
        const response = await apiClient.get('/auth/me');
        return response.data;
    },
};

export const assessmentAPI = {
    submit: async (assessmentData) => {
        const response = await apiClient.post('/assessment/submit', assessmentData);
        return response.data;
    },
    getById: async (id) => {
        const response = await apiClient.get(`/assessment/${id}`);
        return response.data;
    },
    getUserHistory: async () => {
        const response = await apiClient.get('/assessment/user/history');
        return response.data;
    },
};

export const planAPI = {
    getById: async (planId) => {
        const response = await apiClient.get(`/plan/${planId}`);
        return response.data;
    },
    save: async (assessmentId, plan) => {
        const response = await apiClient.post('/plan/save', { assessmentId, plan });
        return response.data;
    },
    getUserHistory: async () => {
        const response = await apiClient.get('/plan/user/history');
        return response.data;
    },
    update: async (planId, plan) => {
        const response = await apiClient.put(`/plan/${planId}`, { plan });
        return response.data;
    },
};

export const ragAPI = {
    query: async (subject, query, top_k = 10) => {
        const response = await apiClient.post('/rag/query', { subject, query, top_k });
        return response.data;
    },
    ingest: async (urls) => {
        const response = await apiClient.post('/rag/ingest', { urls });
        return response.data;
    },
    getJobStatus: async (jobId) => {
        const response = await apiClient.get(`/rag/jobs/${jobId}`);
        return response.data;
    },
    getDocuments: async () => {
        const response = await apiClient.get('/rag/documents');
        return response.data;
    },
    health: async () => {
        const response = await apiClient.get('/rag/health');
        return response.data;
    },
    getStats: async () => {
        const response = await apiClient.get('/rag/stats');
        return response.data;
    },
};

export default apiClient;
