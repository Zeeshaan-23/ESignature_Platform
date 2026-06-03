// src/api/signing.js

import api from './axios';

export const getSigningLink = (token) => api.get(`/signing/${token}/`);
export const submitSignature = (token, signatureData) => api.post(`/signing/${token}/submit/`, {signature_data: signatureData});
export const declineSignature = (token, reason) => api.post(`/signing/${token}/decline/`, { reason });
export const returnPackage = (token, reason) => api.post(`/signing/${token}/return/`, { reason });
export const delegateSignature = (token, delegate_name, delegate_email) => api.post(`/signing/${token}/delegate/`, { delegate_name, delegate_email });