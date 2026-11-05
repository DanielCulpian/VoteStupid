import { apiRequest } from './api'

// Check the cookie on the server without storing sessions in JavaScript.
export function getSession() {
  return apiRequest<{ authenticated: boolean; expires_at: string }>('/api/admin/auth/session')
}

// Send the password only to the private endpoint and let the browser receive the cookie.
export function login(password: string) {
  return apiRequest('/api/admin/auth/login', { method: 'POST', body: JSON.stringify({ password }) })
}

// Revoke the server session and its cookie.
export function logout() {
  return apiRequest('/api/admin/auth/session', { method: 'DELETE' })
}
