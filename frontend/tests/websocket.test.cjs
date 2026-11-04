const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadService } = require('./helpers/loadService.cjs')

// Simula el ciclo de vida del WebSocket sin abrir conexiones ni depender del backend.
class FakeWebSocket extends EventTarget {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 3
  readyState = FakeWebSocket.CONNECTING

  // Conserva la URL de la suscripción para verificar la votación de destino.
  constructor(url) {
    super()
    this.url = url
  }

  // Abre la conexión simulada y notifica a los oyentes registrados por el servicio.
  open() {
    this.readyState = FakeWebSocket.OPEN
    this.dispatchEvent(new Event('open'))
  }

  // Cierra la conexión simulada y permite comprobar el aviso de desconexión.
  close() {
    this.readyState = FakeWebSocket.CLOSED
    this.dispatchEvent(new Event('close'))
  }
}

// Crea el servicio con temporizadores controlados y captura los estados que verá la interfaz.
function setup() {
  const timers = new Map()
  const states = []
  const results = []
  const statuses = []
  const { connectToPoll } = loadService('websocketService.ts', {
    WebSocket: FakeWebSocket,
    // Registra el temporizador sin retrasar la ejecución de la prueba.
    setTimeout: (callback, milliseconds) => {
      timers.set(1, { callback, milliseconds })
      return 1
    },
    // Retira el temporizador cuando la conexión se abre, se cierra o falla.
    clearTimeout: id => timers.delete(id),
    console: { error() {} }, // Silencia los errores esperados de estos escenarios simulados.
  })
  // Recoge los resultados, estados de votación y estados de conexión emitidos por el servicio.
  const socket = connectToPoll('poll-1', value => results.push(value), value => statuses.push(value), value => states.push(value))
  return { socket, states, results, statuses, timers }
}

// Comprueba el estado visible al conectar y al perder una conexión que ya estaba abierta.
test('notifica la conexión y su pérdida y libera el tiempo límite', () => {
  const { socket, states, timers } = setup()
  assert.deepEqual(states, ['connecting'])
  assert.equal(socket.url, 'ws://127.0.0.1:8000/api/polls/poll-1/ws')
  socket.open()
  assert.equal(timers.size, 0)
  socket.close()
  assert.deepEqual(states, ['connecting', 'connected', 'disconnected'])
})

// Comprueba que un error de transporte se comunica aunque todavía no haya llegado el cierre.
test('notifica los errores del WebSocket', () => {
  const { socket, states, timers } = setup()
  socket.dispatchEvent(new Event('error'))
  assert.equal(states.at(-1), 'disconnected')
  assert.equal(timers.size, 0)
})

// Comprueba que una conexión que nunca se abre deja de mostrar el indicador de carga.
test('cierra una conexión que no responde en 12 segundos', () => {
  const { socket, states, timers } = setup()
  const timeout = timers.get(1)
  assert.equal(timeout.milliseconds, 12000)
  timeout.callback()
  assert.equal(socket.readyState, FakeWebSocket.CLOSED)
  assert.equal(states.at(-1), 'disconnected')
  assert.equal(timers.size, 0)
})

// Comprueba que los avisos de conexión no alteran la recepción de resultados ni de estado.
test('sigue entregando resultados y cambios de estado e ignora mensajes ilegibles', () => {
  const { socket, results, statuses } = setup()
  socket.open()
  socket.dispatchEvent(new MessageEvent('message', { data: JSON.stringify({ type: 'results_updated', results: { total_votes: 2 } }) }))
  socket.dispatchEvent(new MessageEvent('message', { data: JSON.stringify({ type: 'poll_status_updated', is_active: false }) }))
  socket.dispatchEvent(new MessageEvent('message', { data: 'JSON inválido' }))
  socket.dispatchEvent(new MessageEvent('message', { data: JSON.stringify({ type: 'poll_status_updated', is_active: 'no' }) }))
  assert.equal(results.length, 1)
  assert.equal(results[0].total_votes, 2)
  assert.deepEqual(statuses, [false])
})
