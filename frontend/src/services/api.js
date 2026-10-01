import axios from 'axios';
import { API_BASE } from './config';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getToken = () => localStorage.getItem('token');

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Clears the saved login and sends the user to the login page (session expired / revoked)
export const forceLogout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = '/login';
};

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // A 401 on a logged-in request means the session expired. A 401 from /auth/*
    // (e.g. wrong password on login) must NOT reload the page, or the error message is lost.
    const isAuthRequest = error.config?.url?.startsWith('/auth/');
    if (error.response?.status === 401 && !isAuthRequest) {
      forceLogout();
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (userData) => api.post('/auth/login', userData),
  requestSignupOtp: (email) => api.post('/auth/request-signup-otp', { email }),
  completeSignup: (data) => api.post('/auth/complete-signup', data),
  updateProfile: (fullName) => api.patch('/auth/me', { full_name: fullName }),
};

// Public chat for visitors without an account; nothing is saved on the server
export const guestAPI = {
  chat: (question, history) => api.post('/guest/chat', { question, history }),
};

// Admins only: keep the chatbot in sync with apsit.edu.in
export const adminAPI = {
  startWebsiteSync: () => api.post('/admin/website-sync'),
  websiteSyncStatus: () => api.get('/admin/website-sync'),
  syncOnePage: (url) => api.post('/admin/website-sync/page', { url }),
};

const pdfForm = (file) => {
  const form = new FormData();
  form.append('file', file);
  return form;
};
const multipart = { headers: { 'Content-Type': 'multipart/form-data' } };

export const chatSessionAPI = {
  getSessions: () => api.get('/chat-sessions'),
  getSession: (sessionId) => api.get(`/chat-sessions/${sessionId}`),
  updateSessionTitle: (sessionId, title) => api.put(`/chat-sessions/${sessionId}/title`, { title }),
  deleteSession: (sessionId) => api.delete(`/chat-sessions/${sessionId}`),
  // PDFs: a new chat about a PDF, or attach / replace / remove the PDF of an existing chat
  startWithPdf: (file) => api.post('/chat-sessions/document', pdfForm(file), multipart),
  uploadPdf: (sessionId, file) => api.put(`/chat-sessions/${sessionId}/document`, pdfForm(file), multipart),
  removePdf: (sessionId) => api.delete(`/chat-sessions/${sessionId}/document`),
};

export default api;
