
const API_URL = import.meta.env.VITE_API_URL

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  const data: unknown = await response.json().catch(() => null)

  if (!response.ok) {
    let detail: unknown = null

    if (
      typeof data === 'object' &&
      data !== null &&
      'detail' in data
    ) {
      detail = data.detail
    }

    let message = `Error HTTP: ${response.status}`

    if (typeof detail === 'string') {
      message = detail
    } else if (Array.isArray(detail)) {
      message = detail
        .map(item => {
          if (
            typeof item === 'object' &&
            item !== null &&
            'msg' in item
          ) {
            return String(item.msg)
          }

          return 'Error de validación'
        })
        .join('. ')
    }

    throw new Error(message)
  }

  return data as T
}
