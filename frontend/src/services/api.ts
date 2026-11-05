const API_URL = import.meta.env.VITE_API_URL ?? ''
const REQUEST_TIMEOUT_MS = 15000

// Conserva el código HTTP para distinguir errores de acceso, validación y servidor.
export class ApiError extends Error {
  status: number

  // Asocia un mensaje comprensible al estado devuelto por la API.
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// Traduce los errores de validación de FastAPI sin mostrar mensajes técnicos.
function validationMessage(detail: unknown): string {
  if (Array.isArray(detail)) {
    const fields: Record<string, string> = {
      title: 'el título',
      option_texts: 'las opciones de respuesta',
      poll_type: 'el tipo de votación',
      max_selections: 'el máximo de opciones seleccionables',
      closes_at: 'la fecha de cierre y su zona horaria',
      selected_option_ids: 'las opciones de tu voto',
    }

    for (const item of detail) {
      if (typeof item !== 'object' || item === null || !Array.isArray(item.loc)) continue
      if (item.loc[0] === 'path') {
        return 'El enlace de la votación no es válido. Comprueba que lo has copiado completo.'
      }
      const field = String(item.loc[1])
      if (field === 'X-Admin-Token') {
        return 'Falta el acceso de administración. Abre el enlace privado completo de esta votación.'
      }
      if (fields[field]) return `Revisa ${fields[field]} e inténtalo de nuevo.`
    }
  }

  return 'Revisa los datos del formulario e inténtalo de nuevo.'
}

// Elige un mensaje útil sin exponer detalles internos de los errores del servidor.
function responseMessage(status: number, data: unknown): string {
  const detail = typeof data === 'object' && data !== null && 'detail' in data
    ? data.detail
    : null

  if (status >= 500) return 'El servidor no puede completar la operación ahora. Inténtalo de nuevo en unos instantes.'
  if (status === 404) {
    if (typeof detail === 'string' && detail.includes('todavía no ha votado')) return detail
    return 'No se ha encontrado la votación. Comprueba el enlace o pide uno nuevo a quien la creó.'
  }
  if (status === 401) return 'Tu sesión no está disponible o ha caducado. Inicia sesión para continuar.'
  if (status === 403) return 'No tienes autorización para realizar esta operación. Vuelve a acceder a la zona privada.'
  if (status === 422) return validationMessage(detail)
  if (status === 429) return 'Se han enviado demasiadas peticiones. Espera unos instantes antes de volver a intentarlo.'
  if (typeof detail === 'string' && detail.trim()) return detail
  return 'No se ha podido completar la operación. Vuelve a intentarlo.'
}

// Envía una petición con tiempo límite y transforma los fallos en mensajes comprensibles.
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  const headers = new Headers(options.headers)
  headers.set('X-Requested-With', 'VoteStupid')
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')

  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      credentials: 'include',
      headers,
      signal: options.signal ? AbortSignal.any([options.signal, timeout]) : timeout,
    })
    const data: unknown = await response.json().catch(error => {
      // Propaga las cancelaciones para conservar el mensaje de tiempo de espera.
      if (timeout.aborted || options.signal?.aborted) throw error
      return null
    })

    if (!response.ok) {
      if (response.status === 401 && endpoint !== '/api/admin/auth/login' && typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
        window.dispatchEvent(new Event('admin-session-expired'))
      }
      const message = endpoint === '/api/admin/auth/login' && response.status === 401
        ? 'La contraseña no es correcta. Vuelve a intentarlo.'
        : endpoint === '/api/admin/auth/login' && response.status === 503
          ? 'El acceso privado no está configurado. Contacta con el administrador.'
          : responseMessage(response.status, data)
      throw new ApiError(message, response.status)
    }
    if (data === null) throw new ApiError('El servidor ha devuelto una respuesta inesperada. Vuelve a intentarlo.', response.status)
    return data as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (timeout.aborted) {
      throw new Error('El servidor está tardando demasiado. Comprueba si la operación se ha completado antes de repetirla.')
    }
    if (options.signal?.aborted) throw new Error('La petición se ha cancelado. Puedes volver a intentarlo.')
    throw new Error('No se puede conectar con el servidor. Comprueba tu conexión y vuelve a intentarlo.')
  }
}
