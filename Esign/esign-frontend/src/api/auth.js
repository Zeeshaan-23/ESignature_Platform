// src/api/auth.js

import api from './axios';

export const loginUser = (email, password) =>
  api.post('/users/login/', { email, password });

export const registerUser = (email, firstName, lastName, password) =>
  api.post('/users/register/', {
    email,
    first_name: firstName,
    last_name: lastName,
    password,
    role: 'SENDER',
  });

export const getMe = () => api.get('/users/me/');

export const logoutUser = () => api.post('/users/logout/');

export const forgotPassword = (email) =>
  api.post('/users/password-reset/', { email });

export const resetPassword = (uid, token, new_password) =>
  api.post('/users/password-reset/confirm/', { uid, token, new_password });