import { requestJson } from './client.js';

export function getAuthSession() {
  return requestJson('/api/v1/auth/me');
}

export function logout() {
  return requestJson('/api/v1/auth/logout', {
    method: 'POST',
  });
}

export function login({ login, password }) {
  return requestJson('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ login, password }),
  });
}