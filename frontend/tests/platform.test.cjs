const assert = require('node:assert/strict')
const { test } = require('node:test')
const vue = require('vue')
const { loadView, deferred } = require('./helpers/loadView.cjs')

const poll = { id: 'poll-1', title: 'Prueba', is_active: true, closes_at: null, poll_type: 'single_choice', created_at: '2026-01-01T00:00:00Z' }

// Retira el fragmento secreto conservando el estado que necesita Vue Router para navegar.
test('retira el token de la dirección sin borrar el historial del router', async () => {
  const routerState = { position: 2, back: '/admin', current: '/admin/poll-1' }
  let replaced
  const view = loadView('AdminView.vue', {
    '../services/adminService': { getAdminPoll: async () => ({ ...poll }) },
    '../services/resultsService': { getPollResults: async () => ({}) },
    '../services/websocketService': { connectToPoll: () => ({ close() {} }) },
  }, {
    window: {
      location: { hash: '#token=legacy-test-token', pathname: '/admin/poll-1', search: '' },
      history: { state: routerState, replaceState: (...args) => { replaced = args } },
    },
  })
  await view.loadAdminPanel()
  assert.equal(replaced[0], routerState)
  assert.equal(replaced[2], '/admin/poll-1')
})

for (const filename of ['PollView.vue', 'AdminView.vue']) {
  // Comprueba el cierre por fecha y la cancelación del temporizador al abandonar la vista.
  test(`${filename}: cierra al vencer el plazo y cancela las esperas al salir`, async () => {
    let unmount, callback, cleared = 0
    const view = loadView(filename, {
      '../services/pollService': {},
      '../services/voteService': {},
      '../services/adminService': {},
      '../services/resultsService': {},
      '../services/websocketService': {},
    }, {
      captureUnmount: handler => { unmount = handler },
      setTimeout: handler => { callback = handler; return 1 },
      clearTimeout: () => { cleared++ },
    })
    view.poll.value = { ...poll, closes_at: new Date(Date.now() + 60000).toISOString() }
    await vue.nextTick()
    assert.equal(typeof callback, 'function')
    assert.equal(view.poll.value.is_active, true)
    view.poll.value.closes_at = new Date(Date.now() - 1000).toISOString()
    callback()
    assert.equal(view.poll.value.is_active, false)
    await vue.nextTick()
    const before = cleared
    unmount()
    assert.ok(cleared > before)
  })
}

// Ejecuta el catálogo real con reloj, ciclo de vida y transporte controlados.
function catalog(getCatalog = async () => ({ items: [poll], total: 1 })) {
  let mount, unmount, callbacks, closed = 0, nextTimer = 0
  const timers = new Map()
  const view = loadView('../components/PollCatalog.vue', {
    '../services/catalogService': { getCatalog },
    '../services/websocketService': {
      // Captura suscripciones para comprobar cancelación y recuperación sin conexiones reales.
      connectToPoll: (...args) => { callbacks = args; return { close() { closed++ } } },
    },
  }, {
    captureMount: callback => { mount = callback },
    captureUnmount: callback => { unmount = callback },
    setTimeout: (callback, ms) => { const id = ++nextTimer; timers.set(id, { callback, ms }); return id },
    clearTimeout: id => timers.delete(id),
  })
  return { view, mount: () => mount(), unmount: () => unmount(), callbacks: () => callbacks, timers, closed: () => closed }
}

// Comprueba que una respuesta antigua no sustituye los resultados de filtros nuevos.
test('el catálogo descarta respuestas tardías de filtros anteriores', async () => {
  const slow = deferred()
  let calls = 0
  const c = catalog(() => ++calls === 1 ? slow.promise : Promise.resolve({ items: [{ ...poll, id: 'new' }], total: 1 }))
  const old = c.view.load()
  await c.view.load()
  slow.resolve({ items: [poll], total: 1 }); await old
  assert.equal(c.view.items.value[0].id, 'new')
  c.unmount()
})

// Verifica filtros combinados y limpieza reactiva, también ante un fallo del servidor.
test('cambia y limpia filtros sin conservar tarjetas que no coinciden', async () => {
  const calls = []
  let fail = false
  const c = catalog(async (...args) => { calls.push(args); if (fail) throw new Error('Sin conexión'); return { items: [poll], total: 1 } })
  await c.view.load()
  fail = true
  c.view.state.value = 'inactive'; c.view.type.value = 'ranking'
  await vue.nextTick(); await Promise.resolve()
  assert.equal(c.view.items.value.length, 0)
  assert.deepEqual(calls.at(-1).slice(0, 2), ['inactive', 'ranking'])
  fail = false
  c.view.clearFilters(); await vue.nextTick(); await Promise.resolve()
  assert.equal(c.view.state.value, 'all'); assert.equal(c.view.type.value, '')
  c.unmount()
})

// Impide tarjetas repetidas si una votación cambia de posición entre páginas.
test('pagina sin duplicar tarjetas y conserva el total del servidor', async () => {
  const c = catalog(async (_, __, offset) => ({ items: offset ? [poll, { ...poll, id: 'second' }] : [poll], total: 2 }))
  await c.view.load(); await c.view.load(true)
  assert.deepEqual(Array.from(c.view.items.value, p => p.id), ['poll-1', 'second'])
  assert.equal(c.view.total.value, 2)
  c.unmount()
})

// Mantiene un único temporizador de actualización ante varios eventos del catálogo.
test('agrupa cambios de estado y cancela la conexión y esperas al salir', async () => {
  const c = catalog()
  c.mount(); await Promise.resolve()
  const callbacks = c.callbacks()
  assert.equal(callbacks[0], 'catalog')
  callbacks[2](false); callbacks[2](true)
  assert.equal(c.timers.size, 1)
  c.unmount()
  assert.equal(c.closed(), 1); assert.equal(c.timers.size, 0)
})

// Evita conexiones duplicadas cuando el usuario pulsa el reintento manual.
test('el reintento manual sustituye el transporte anterior', () => {
  const c = catalog()
  c.view.reconnect(); c.view.reconnect()
  assert.equal(c.closed(), 1)
  c.unmount(); assert.equal(c.closed(), 2)
})

// Evita que consultas de un transporte ya caducado actualicen las tarjetas.
test('descarta una sincronización invalidada y una respuesta posterior al desmontaje', async () => {
  const request = deferred()
  const c = catalog(() => request.promise)
  let valid = true
  const result = c.view.load(false, () => valid)
  valid = false
  request.resolve({ items: [poll], total: 1 }); await result
  assert.equal(c.view.items.value.length, 0)
  c.unmount(); await c.view.load()
  assert.equal(c.view.items.value.length, 0)
})

// El organizador ya no depende de almacenamiento local ni conserva tokens de creación.
test('crea enlaces sin secreto y no guarda tokens en el navegador', async () => {
  const view = loadView('CreatePollView.vue', {
    '../services/pollService': { createPoll: async () => ({ ...poll, admin_token: 'must-not-persist' }) },
  }, {
    localStorage: { setItem() { assert.fail('No debe escribir datos administrativos locales') } },
    sessionStorage: { setItem() { assert.fail('No debe guardar tokens individuales') } },
  })
  view.title.value = 'Prueba'; view.options.value = ['A', 'B']
  await view.submitPoll()
  assert.equal(view.createdPoll.value.id, 'poll-1')
  assert.equal('admin_token' in view.createdPoll.value, false)
  assert.doesNotMatch(view.adminUrl.value, /token|must-not-persist/)
})

// Mantiene la explicación de errores de consulta y permite recuperar la lista sin recargar.
test('recupera el catálogo después de un error y representa listas vacías', async () => {
  let fail = true
  const c = catalog(async () => { if (fail) throw new Error('Sin conexión'); return { items: [], total: 0 } })
  await assert.rejects(c.view.load(), /Sin conexión/)
  assert.equal(c.view.loading.value, false)
  assert.match(c.view.error.value, /Sin conexión/)
  fail = false; await c.view.load()
  assert.equal(c.view.error.value, ''); assert.equal(c.view.items.value.length, 0); assert.equal(c.view.total.value, 0)
  c.unmount()
})
