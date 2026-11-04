const API_URL = import.meta.env.VITE_API_URL

const WS_URL = API_URL.replace(/^http/, 'ws')

// Abre un WebSocket y notifica las actualizaciones de resultados y estado de la votación.
export function connectToPoll(
  pollId: string,
  onResultsUpdated: (results: unknown) => void,
  onPollStatusUpdated?: (isActive: boolean) => void,
): WebSocket {
  const socket = new WebSocket(
    `${WS_URL}/api/polls/${pollId}/ws`,
  )

  // Valida cada mensaje recibido y lo entrega al callback de resultados o de estado.
  socket.addEventListener('message', event => {
    try {
      const message: unknown = JSON.parse(event.data)

      if (
        typeof message === 'object' &&
        message !== null &&
        'type' in message &&
        message.type === 'results_updated' &&
        'results' in message
      ) {
        onResultsUpdated(message.results)
      }
      if (
        typeof message === 'object' &&
        message !== null &&
        'type' in message &&
        message.type === 'poll_status_updated' &&
        'is_active' in message &&
        typeof message.is_active === 'boolean'
      ) {
        onPollStatusUpdated?.(message.is_active)
      }
    } catch (error) {
      console.error('Error procesando mensaje WebSocket:', error)
    }
  })

  // Registra los fallos de conexión WebSocket para facilitar su diagnóstico.
  socket.addEventListener('error', error => {
    console.error('Error en la conexión WebSocket:', error)
  })

  return socket
}