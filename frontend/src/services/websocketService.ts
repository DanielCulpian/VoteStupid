const API_URL = import.meta.env.VITE_API_URL

const WS_URL = API_URL.replace(/^http/, 'ws')

export function connectToPoll(
  pollId: string,
  onResultsUpdated: (results: unknown) => void,
  onPollStatusUpdated?: (isActive: boolean) => void,
): WebSocket {
  const socket = new WebSocket(
    `${WS_URL}/api/polls/${pollId}/ws`,
  )

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

  socket.addEventListener('error', error => {
    console.error('Error en la conexión WebSocket:', error)
  })

  return socket
}