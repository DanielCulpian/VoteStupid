import { apiRequest } from './api'

// Comprueba la cookie en el servidor sin almacenar sesiones en JavaScript.
export function getSession() {
  return apiRequest<{ authenticated: boolean; expires_at: string }>('/api/admin/auth/session')
}

// Envía la contraseña únicamente al endpoint privado y deja que el navegador reciba la cookie.
export function login(password: string) {
  return apiRequest('/api/admin/auth/login', { method: 'POST', body: JSON.stringify({ password }) })
}

// Revoca la sesión del servidor y su cookie.
export function logout() {
  return apiRequest('/api/admin/auth/session', { method: 'DELETE' })
}
