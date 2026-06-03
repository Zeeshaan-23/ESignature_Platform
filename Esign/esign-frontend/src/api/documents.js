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