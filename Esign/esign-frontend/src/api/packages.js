// src/api/packages.js

import api from './axios';

export const createPackage = (data) => api.post('/packages/create/', data);
export const listPackages = (page = 1) => api.get(`/packages/?page=${page}`);
export const getPackage = (id) => api.get(`/packages/${id}/`);
export const sendPackage = (id) => api.post(`/packages/${id}/send/`);
export const getAuditTrail = (id) => api.get(`/audit/packages/${id}/`);
