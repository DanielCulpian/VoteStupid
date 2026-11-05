const API_URL = import.meta.env.VITE_API_URL || window.location.origin
const WS_URL = API_URL.replace(/^http/, 'ws')

export type RealtimeConnectionState = 'connecting' | 'connected' | 'disconnected'
export interface PollConnection { close: () => void }

// Maintain one connection and recover missed data before confirming reconnection.
export function connectToPoll(
  pollId: string,
  onResultsUpdated: (results: unknown) => void,
  onPollStatusUpdated?: (isActive: boolean) => void,
  onConnectionStateChanged?: (state: RealtimeConnectionState) => void,
  onSynchronize?: (isCurrent: () => boolean) => Promise<void>,
): PollConnection {
  let socket: WebSocket | null = null
  let stopped = false
  let attempts = 0
  let retry: ReturnType<typeof setTimeout> | undefined
  let timeout: ReturnType<typeof setTimeout> | undefined

  // Schedule one retry with progressive delays capped at thirty seconds.
  function scheduleRetry() {
    if (stopped || retry !== undefined) return
    onConnectionStateChanged?.('disconnected')
    retry = setTimeout(() => {
      retry = undefined
      open()
    }, Math.min(1000 * 2 ** Math.min(attempts++, 5), 30000))
  }

  // Open the transport and discard events from replaced or cancelled connections.
  function open() {
    if (stopped) return
    let current: WebSocket
    try {
      current = new WebSocket(`${WS_URL}/api/polls/${pollId}/ws`)
    } catch {
      scheduleRetry()
      return
    }
    socket = current
    let synchronized = false
    const pending: MessageEvent[] = []

    // Close the failed attempt and clear its timer before retrying.
    function fail() {
      if (stopped || socket !== current) return
      socket = null
      clearTimeout(timeout)
      current.close()
      scheduleRetry()
    }

    timeout = setTimeout(fail, 12000)
    // Fetch a snapshot, then apply events received while the request was pending.
    current.addEventListener('open', async () => {
      if (stopped || socket !== current) return
      try {
        await onSynchronize?.(() => !stopped && socket === current)
        if (stopped || socket !== current) return
        synchronized = true
        pending.forEach(deliver)
        pending.length = 0
        clearTimeout(timeout)
        attempts = 0
        onConnectionStateChanged?.('connected')
      } catch {
        fail()
      }
    })
    current.addEventListener('close', fail)
    current.addEventListener('error', fail)
    // Retain concurrent events so an HTTP response cannot overwrite newer changes.
    current.addEventListener('message', event => {
      if (stopped || socket !== current) return
      if (!synchronized) pending.push(event)
      else deliver(event)
    })

    // Validate messages while preserving the two existing public event types.
    function deliver(event: MessageEvent) {
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
    }
  }

  onConnectionStateChanged?.('connecting')
  open()
  return {
    // Permanently stop the transport and all retries when leaving the page.
    close() {
      stopped = true
      clearTimeout(retry)
      clearTimeout(timeout)
      const current = socket
      socket = null
      current?.close()
    },
  }
}
