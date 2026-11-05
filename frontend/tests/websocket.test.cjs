const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadService } = require('./helpers/loadService.cjs')

// Build the WebSocket URL from the public HTTPS origin when running behind Nginx.
test('usa el origen público y wss cuando no hay URL de API configurada', () => {
  let destination
  const { connectToPoll } = loadService('websocketService.ts', {
    window: { location: { origin: 'https://votes.example' } },
    WebSocket: class {
      // Capture the URL without opening a network connection.
      constructor(url) { destination = url }
      // Stub the transport to check only the generated URL.
      addEventListener() {}
      // Allow closing the attempt and cancelling its timer.
      close() {}
    },
  }, '')
  const connection = connectToPoll('poll-1', () => {})
  assert.equal(destination, 'wss://votes.example/api/polls/poll-1/ws')
  connection.close()
})

// Simulate transport events independently of the network.
class FakeWebSocket extends EventTarget {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSED = 3
  static instances = []
  readyState = 0
  // Record each transport to detect duplicate connections.
  constructor(url) { super(); this.url = url; FakeWebSocket.instances.push(this) }
  // Open the transport and allow view synchronization.
  open() { this.readyState = 1; this.dispatchEvent(new Event('open')) }
  // Simulate closure by the server or user.
  close() { this.readyState = 3; this.dispatchEvent(new Event('close')) }
  // Deliver a results or state event.
  message(value) { this.dispatchEvent(new MessageEvent('message', { data: JSON.stringify(value) })) }
}

// Provide a controlled clock and capture interface events.
function setup(synchronize) {
  FakeWebSocket.instances = []
  const timers = new Map(), states = [], results = [], statuses = []
  let sequence = 0
  const { connectToPoll } = loadService('websocketService.ts', {
    WebSocket: FakeWebSocket,
    // Record delays without consuming real time.
    setTimeout(callback, milliseconds) { const id = ++sequence; timers.set(id, { callback, milliseconds }); return id },
    // Cancel delays scheduled by the previous attempt.
    clearTimeout(id) { timers.delete(id) },
    console: { error() {} },
  })
  const connection = connectToPoll('poll-1', v => results.push(v), v => statuses.push(v), v => states.push(v), synchronize)
  // Run a specific timer and remove it as the browser would.
  function tick(milliseconds) {
    const entry = [...timers].find(([, timer]) => timer.milliseconds === milliseconds)
    assert.ok(entry, `No existe espera de ${milliseconds}`)
    timers.delete(entry[0]); entry[1].callback()
  }
  return { connection, timers, states, results, statuses, tick, sockets: FakeWebSocket.instances }
}

// Flush connection promises without real delays.
async function flush() { await Promise.resolve(); await Promise.resolve() }

// Verify progressive backoff and that error and close events do not duplicate retries.
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

// Check connection timeouts and permanent cancellation when leaving the view.
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

// Retain events received during loading and restore the snapshot before hiding the notice.
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

// Retry after HTTP failures even if the socket opened, and discard expired queries.
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

// Ignore malformed messages while preserving existing events after recovery.
test('ignora mensajes invalidos sin interrumpir el directo', async () => {
  const s = setup(); s.sockets[0].open(); await flush()
  s.sockets[0].dispatchEvent(new MessageEvent('message', { data: 'invalid' }))
  s.sockets[0].message({ type: 'poll_status_updated', is_active: 'no' })
  s.sockets[0].message({ type: 'poll_status_updated', is_active: true })
  assert.deepEqual(s.statuses, [true]); s.connection.close()
})
