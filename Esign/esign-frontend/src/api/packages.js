// src/api/packages.js

import api from './axios';

export const createPackage    = (data) => api.post('/packages/create/', data);
export const listPackages     = (page = 1) => api.get(`/packages/?page=${page}`);
export const getDashboardStats= () => api.get('/packages/stats/');
export const getPackage       = (id) => api.get(`/packages/${id}/`);
export const sendPackage      = (id) => api.post(`/packages/${id}/send/`);
export const cancelPackage    = (id) => api.post(`/packages/${id}/cancel/`);
export const resendPackage    = (id) => api.post(`/packages/${id}/resend/`);

// Signature Fields
export const getSignatureFields    = (id) => api.get(`/packages/${id}/fields/`);
export const createSignatureField  = (id, data) => api.post(`/packages/${id}/fields/`, data);
export const deleteSignatureField  = (id, fieldId) => api.delete(`/packages/${id}/fields/${fieldId}/`);

export const getAuditTrail    = (id) => api.get(`/audit/packages/${id}/`);

// Audit export — returns a raw Response so caller can create a blob download
export const downloadAuditCSV  = (id) =>
  api.get(`/audit/packages/${id}/export/csv/`,  { responseType: 'blob' });
export const downloadAuditJSON = (id) =>
  api.get(`/audit/packages/${id}/export/json/`, { responseType: 'blob' });

// Webhook CRUD
export const listWebhooks   = () => api.get('/webhooks/');
export const createWebhook  = (data) => api.post('/webhooks/', data);
export const updateWebhook  = (id, data) => api.patch(`/webhooks/${id}/`, data);
export const deleteWebhook  = (id) => api.delete(`/webhooks/${id}/`);
export const getWebhookDeliveries = (id) => api.get(`/webhooks/${id}/deliveries/`);
