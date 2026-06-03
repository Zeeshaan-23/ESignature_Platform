// src/api/documents.js

import api from './axios';

export const uploadDocument = (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/documents/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  });
};

export const listDocuments = () => api.get('/documents/');
export const verifyDocumentHash = (id) => api.get(`/documents/${id}/verify/`);

// Templates
export const listTemplates = () => api.get('/documents/templates/');
export const createTemplate = (data) => api.post('/documents/templates/', data);
export const useTemplate = (id) => api.post(`/documents/templates/${id}/use/`);