// src/api/signing.js

import api from './axios';

export const getSigningLink = (token) => api.get(`/signing/${token}/`);
export const submitSignature = (token, signatureData) => api.post(`/signing/${token}/submit/`, {signature_data: signatureData});