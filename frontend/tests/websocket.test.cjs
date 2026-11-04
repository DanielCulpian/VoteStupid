const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadService } = require('./helpers/loadService.cjs')

// Simula el transporte con eventos independientes de la red.
class FakeWebSocket extends EventTarget {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 3
  static instances = []
  readyState = 0
  // Registra cada transporte para detectar conexiones duplicadas.
  constructor(url) { super(); this.url = url; FakeWebSocket.instances.push(this) }
  // Abre el transporte y permite sincronizar la vista.
  open() { this.readyState = 1; this.dispatchEvent(new Event('open')) }
  // Simula el cierre del servidor o del usuario.
  close() { this.readyState = 3; this.dispatchEvent(new Event('close')) }
  // Entrega un evento de resultados o estado.
  message(value) { this.dispatchEvent(new MessageEvent('message', { data: JSON.stringify(value) })) }
}

// Proporciona un reloj controlado y captura los eventos de la interfaz.
function setup(synchronize) {
  FakeWebSocket.instances = []
  const timers = new Map(), states = [], results = [], statuses = []
  let sequence = 0
  const { connectToPoll } = loadService('websocketService.ts', {
    WebSocket: FakeWebSocket,
    // Registra esperas sin consumir tiempo real.
    setTimeout(callback, milliseconds) { const id = ++sequence; timers.set(id, { callback, milliseconds }); return id },
    // Cancela las esperas del intento anterior.
    clearTimeout(id) { timers.delete(id) },
    console: { error() {} },
  })
  const connection = connectToPoll('poll-1', v => results.push(v), v => statuses.push(v), v => states.push(v), synchronize)
  // Ejecuta una espera concreta y la retira como haria el navegador.
  function tick(milliseconds) {
    const entry = [...timers].find(([, timer]) => timer.milliseconds === milliseconds)
    assert.ok(entry, `No existe espera de ${milliseconds}`)
    timers.delete(entry[0]); entry[1].callback()
  }
  return { connection, timers, states, results, statuses, tick, sockets: FakeWebSocket.instances }
}

// Permite finalizar las promesas de apertura sin esperas reales.
async function flush() { await Promise.resolve(); await Promise.resolve() }

// Verifica el retroceso progresivo y que error y cierre no dupliquen reintentos.
test('reintenta con esperas progresivas limitadas y un solo transporte', async () => {
  const s = setup()
  for (const delay of [1000, 2000, 4000, 8000, 16000, 30000, 30000]) {
    const current = s.sockets.at(-1)
    current.dispatchEvent(new Event('error')); current.close()
    assert.equal(s.timers.size, 1)
    s.tick(delay)
    assert.equal(s.sockets.filter(socket => socket.readyState !== 3).length, 1)
  }
  s.sockets.at(-1).open(); await flush()
  assert.equal(s.states.at(-1), 'connected')
  s.sockets.at(-1).close(); s.tick(1000)
  s.connection.close()
  assert.equal(s.timers.size, 0)
})

// Comprueba el limite de apertura y la cancelacion definitiva al abandonar la vista.
test('cancela conexion pendiente, reintentos y eventos tardios al salir', async () => {
  const s = setup()
  s.tick(12000)
  assert.equal(s.states.at(-1), 'disconnected')
  s.connection.close()
  assert.equal(s.timers.size, 0)
  s.sockets[0].open(); s.sockets[0].message({ type: 'poll_status_updated', is_active: false })
  await flush()
  assert.equal(s.statuses.length, 0)
  assert.equal(s.states.at(-1), 'disconnected')
})

// Conserva eventos recibidos durante la consulta y recupera la instantanea antes de ocultar el aviso.
test('sincroniza cada apertura y entrega resultados y estado acumulados', async () => {
  let resolve, calls = 0
  const s = setup(() => { calls++; return new Promise(done => { resolve = done }) })
  const first = s.sockets[0]
  first.open()
  first.message({ type: 'results_updated', results: { total_votes: 2 } })
  first.message({ type: 'poll_status_updated', is_active: false })
  assert.equal(s.results.length, 0)
  resolve(); await flush()
  assert.equal(s.results[0].total_votes, 2)
  assert.deepEqual(s.statuses, [false])
  assert.equal(s.states.at(-1), 'connected')
  first.close(); s.tick(1000); s.sockets[1].open()
  assert.equal(calls, 2)
  resolve(); await flush()
  first.message({ type: 'poll_status_updated', is_active: true })
  assert.deepEqual(s.statuses, [false])
  s.connection.close()
})

// Reintenta si HTTP falla aunque el socket se haya abierto y descarta consultas caducadas.
test('no confirma conexiones sin sincronizar y caduca las consultas lentas', async () => {
  let valid, resolve
  const s = setup(isCurrent => { valid = isCurrent; return new Promise(done => { resolve = done }) })
  s.sockets[0].open(); assert.equal(valid(), true)
  s.tick(12000); assert.equal(valid(), false)
  resolve(); await flush()
  assert.equal(s.states.at(-1), 'disconnected')
  s.connection.close()
  const failed = setup(async () => { throw new Error('Backend caido') })
  failed.sockets[0].open(); await flush()
  assert.equal(failed.states.at(-1), 'disconnected')
  assert.equal(failed.timers.size, 1)
  failed.connection.close()
})

// Ignora mensajes corruptos y mantiene los eventos existentes tras recuperarse.
test('ignora mensajes invalidos sin interrumpir el directo', async () => {
  const s = setup(); s.sockets[0].open(); await flush()
  s.sockets[0].dispatchEvent(new MessageEvent('message', { data: 'invalid' }))
  s.sockets[0].message({ type: 'poll_status_updated', is_active: 'no' })
  s.sockets[0].message({ type: 'poll_status_updated', is_active: true })
  assert.deepEqual(s.statuses, [true]); s.connection.close()
})
