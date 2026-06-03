// src/api/axios.js

import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true, // IMPORTANT: Send cookies with every request
});

// Helper function to get cookie value by name
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Request interceptor
api.interceptors.request.use((config) => {
  // Attach CSRF token if it exists (Django sets this if CSRF_COOKIE_HTTPONLY=False)
  const csrfToken = getCookie('csrftoken');
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

// Response interceptor — handle expired tokens
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and we haven't already retried, and the error isn't from the refresh endpoint itself
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes('/users/token/refresh') &&
      !originalRequest.url.includes('/users/login')
    ) {
      originalRequest._retry = true;

      try {
        // Try to refresh the token via the cookie-based endpoint
        await axios.post(
          `${import.meta.env.VITE_API_URL}/users/token/refresh/`,
          {},
          { withCredentials: true }
        );

        // If successful, the backend has set a new access_token cookie.
        // Retry the original request.
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh token also expired or invalid — force logout
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;