const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadService } = require('./helpers/loadService.cjs')
const { loadView } = require('./helpers/loadView.cjs')

const firstPoll = {
  id: '11111111-1111-4111-8111-111111111111', title: 'Primera votación',
  poll_type: 'single_choice', created_at: '2026-01-01T10:00:00Z',
  is_active: true, closes_at: null, options: [], description: null,
}
const secondPoll = { ...firstPoll, id: '22222222-2222-4222-8222-222222222222', title: 'Segunda votación', poll_type: 'multiple_choice', created_at: '2026-02-01T10:00:00Z' }
const thirdPoll = { ...firstPoll, id: '33333333-3333-4333-8333-333333333333', title: 'Tercera votación', poll_type: 'ranking', created_at: '2026-03-01T10:00:00Z' }
const token = 'token-privado-solo-para-la-prueba'
const origin = 'http://localhost:5173'

// Proporciona un almacenamiento de navegador controlado con una sesión independiente del histórico persistente.
function setup(stored = new Map(), session = new Map()) {
  const localStorage = {
    // Lee únicamente los datos locales del escenario de prueba.
    getItem: key => stored.get(key) ?? null,
    // Conserva el histórico para simular otra ejecución de la aplicación.
    setItem: (key, value) => stored.set(key, value),
  }
  const sessionStorage = {
    // Recupera credenciales temporales de la pestaña de prueba.
    getItem: key => session.get(key) ?? null,
    // Guarda el token solo en la sesión simulada.
    setItem: (key, value) => session.set(key, value),
  }
  const globals = { localStorage, sessionStorage, URL, URLSearchParams }
  return { stored, session, globals, service: loadService('historyService.ts', globals) }
}

// Distingue el caso de una votación inexistente de los fallos temporales del servidor.
class TestApiError extends Error {
  // Asocia el estado HTTP que interpretará la vista del histórico.
  constructor(message, status) { super(message); this.status = status }
}

// Construye la vista con el servicio real de almacenamiento y respuestas HTTP controladas.
function historyView(context, getPoll, getAdminPoll = async () => firstPoll) {
  return loadView('LegacyHistoryView.vue', {
    '../services/historyService': context.service,
    '../services/pollService': { getPoll },
    '../services/adminService': { getAdminPoll },
    '../services/api': { ApiError: TestApiError },
  }, context.globals)
}

// Comprueba que los tres tipos se ordenan por fecha y que el cierre actualiza sin eliminar ni duplicar.
test('recuerda varias votaciones y conserva las cerradas sin duplicarlas', () => {
  const { service } = setup()
  for (const poll of [secondPoll, firstPoll, thirdPoll]) service.rememberPoll(poll)
  service.rememberPoll({ ...firstPoll, is_active: false })
  const rows = service.getPollHistory()
  assert.equal(rows.length, 3)
  assert.deepEqual(Array.from(rows, row => row.id), [thirdPoll.id, secondPoll.id, firstPoll.id])
  assert.equal(rows[2].is_active, false)
})

// Comprueba que incluso una respuesta con campos adicionales no persiste secretos ni enlaces privados.
test('guarda exclusivamente metadatos públicos y nunca tokens', () => {
  const { service, stored } = setup()
  service.rememberPoll({ ...firstPoll, admin_token: token, admin_token_hash: 'hash-secreto', admin_url: `${origin}/admin/${firstPoll.id}#token=${token}`, voter_token_hash: 'otro-secreto' })
  const raw = [...stored.values()].join('')
  assert.doesNotMatch(raw, /token|hash-secreto|otro-secreto|admin_url/)
  assert.deepEqual(Object.keys(service.getPollHistory()[0]).sort(), ['closes_at', 'created_at', 'id', 'is_active', 'poll_type', 'title'])
})

// Comprueba que otra ejecución conserva el histórico sin recuperar las credenciales de una sesión anterior.
test('recupera la lista tras reiniciar la aplicación pero no conserva el acceso privado', () => {
  const context = setup()
  context.service.rememberPoll(firstPoll)
  context.session.set(`votestupid:admin-token:${firstPoll.id}`, token)
  assert.equal(context.service.hasSessionAdminAccess(firstPoll.id), true)
  const restarted = setup(context.stored)
  assert.equal(restarted.service.getPollHistory()[0].id, firstPoll.id)
  assert.equal(restarted.service.hasSessionAdminAccess(firstPoll.id), false)
  assert.equal(setup().service.getPollHistory().length, 0)
})

// Comprueba que un histórico corrupto se comunica sin sobrescribir datos que podrían recuperarse.
test('no sobrescribe un histórico corrupto y descarta identificadores manipulados', () => {
  const context = setup(new Map([['votestupid:created-polls:v1', '{JSON incorrecto']]))
  assert.throws(() => context.service.getPollHistory(), /No se puede leer el histórico/)
  assert.throws(() => context.service.rememberPoll(firstPoll), /No se puede leer el histórico/)
  assert.equal(context.stored.get('votestupid:created-polls:v1'), '{JSON incorrecto')
  context.stored.set('votestupid:created-polls:v1', JSON.stringify([{ ...firstPoll, admin_token: token }, { ...secondPoll, id: '../admin' }]))
  const entries = context.service.getPollHistory()
  assert.equal(entries.length, 1)
  assert.equal('admin_token' in entries[0], false)
})

// Comprueba que los enlaces privados se interpretan localmente y no aceptan otros dominios o tokens en consultas.
test('acepta solo enlaces privados completos de esta aplicación', () => {
  const { service } = setup()
  const parsed = service.parsePrivatePollLink(`${origin}/admin/${firstPoll.id}#token=abc%2B123`, origin)
  assert.equal(parsed.id, firstPoll.id)
  assert.equal(parsed.token, 'abc+123')
  for (const invalid of [
    `${origin}/votacion/${firstPoll.id}`,
    `${origin}/admin/${firstPoll.id}?token=${token}`,
    `https://otro-sitio.example/admin/${firstPoll.id}#token=${token}`,
    `${origin}/admin/incorrecto#token=${token}`,
  ]) assert.throws(() => service.parsePrivatePollLink(invalid, origin), /enlace privado completo/)
})

// Comprueba que las restricciones del navegador no producen errores técnicos ni aparentan guardar el histórico.
test('comunica los fallos de almacenamiento y no presupone acceso administrativo', () => {
  const service = loadService('historyService.ts', {
    localStorage: {
      // Simula que el navegador permite leer pero ya no tiene espacio para escribir.
      getItem: () => null,
      // Rechaza la escritura para comprobar el aviso al organizador.
      setItem: () => { throw new Error('QuotaExceededError') },
    },
    sessionStorage: {
      // Simula una sesión cuyo almacenamiento está bloqueado.
      getItem: () => { throw new Error('SecurityError') },
    },
  })
  assert.throws(() => service.rememberPoll(firstPoll), /No se ha podido guardar el histórico/)
  assert.equal(service.hasSessionAdminAccess(firstPoll.id), false)
})

// Comprueba que el histórico actualiza el estado sin perder entradas cuando una votación deja de estar disponible.
test('actualiza las entradas conocidas y conserva las que no se pueden consultar', async () => {
  const context = setup()
  for (const poll of [firstPoll, secondPoll, thirdPoll]) context.service.rememberPoll(poll)
  context.session.set(`votestupid:admin-token:${firstPoll.id}`, token)
  const requested = []
  const view = historyView(context, async id => {
    // Responde solo a identificadores que ya estaban guardados en el navegador.
    requested.push(id)
    if (id === secondPoll.id) throw new TestApiError('No existe.', 404)
    if (id === thirdPoll.id) throw new Error('Sin conexión.')
    return { ...firstPoll, is_active: false }
  })
  await view.loadHistory()
  assert.equal(requested.length, 3)
  assert.equal(view.rows.value.length, 3)
  assert.equal(view.rows.value.find(row => row.poll.id === firstPoll.id).poll.is_active, false)
  assert.equal(view.rows.value.find(row => row.poll.id === firstPoll.id).canAdminister, true)
  assert.equal(view.rows.value.find(row => row.poll.id === secondPoll.id).availability, 'missing')
  assert.equal(view.rows.value.find(row => row.poll.id === thirdPoll.id).availability, 'unavailable')
  assert.match(view.refreshWarning.value, /últimos datos guardados/)
  assert.equal(view.isLoading.value, false)
})

// Comprueba que un navegador nuevo no solicita un listado global ni ve votaciones de otros perfiles.
test('un histórico vacío no consulta ni enumera votaciones del servidor', async () => {
  let calls = 0
  const view = historyView(setup(), async () => { calls++ })
  await view.loadHistory()
  assert.equal(calls, 0)
  assert.equal(view.rows.value.length, 0)
})

// Comprueba la autenticación del enlace antes de guardar el acceso temporal y limpiar el campo sensible.
test('recupera una votación antigua después de validar su token con el backend', async () => {
  const context = setup()
  const view = historyView(context, async () => firstPoll, async (id, receivedToken) => {
    // Verifica la credencial que se enviaría al endpoint de administración existente.
    assert.equal(id, firstPoll.id)
    assert.equal(receivedToken, token)
    return { ...firstPoll, admin_token: token }
  })
  view.privateLink.value = `${origin}/admin/${firstPoll.id}#token=${token}`
  await view.recoverPoll()
  assert.equal(view.rows.value.length, 1)
  assert.equal(view.rows.value[0].canAdminister, true)
  assert.equal(context.session.get(`votestupid:admin-token:${firstPoll.id}`), token)
  assert.equal(view.privateLink.value, '')
  assert.equal(view.importError.value, '')
  assert.match(view.importSuccess.value, /Votación recuperada/)
  assert.doesNotMatch([...context.stored.values()].join(''), /token|admin_token/)
})

// Comprueba que un token rechazado no introduce entradas ni habilita acciones administrativas.
test('rechaza la recuperación no autorizada sin guardar el token', async () => {
  const context = setup()
  let calls = 0
  const view = historyView(context, async () => firstPoll, async () => {
    // Simula el rechazo del token por parte del backend.
    calls++
    throw new TestApiError('El acceso de administración no es válido.', 403)
  })
  view.privateLink.value = `${origin}/admin/${firstPoll.id}#token=incorrecto`
  await view.recoverPoll()
  assert.equal(calls, 1)
  assert.equal(context.service.getPollHistory().length, 0)
  assert.equal(context.session.size, 0)
  assert.match(view.importError.value, /no es válido/)
  assert.equal(view.isImporting.value, false)
})

// Comprueba que la creación incorpora la votación al histórico y separa el token de los datos persistentes.
test('registra automáticamente las nuevas votaciones sin guardar el token permanentemente', async () => {
  const context = setup()
  const view = loadView('CreatePollView.vue', {
    '../services/pollService': {
      // Devuelve los metadatos reales que recibe el formulario tras crear una votación.
      createPoll: async () => ({ ...firstPoll, admin_token: token }),
    },
    '../services/historyService': context.service,
  }, context.globals)
  view.title.value = firstPoll.title
  view.options.value = ['A', 'B']
  await view.submitPoll()
  assert.equal(context.service.getPollHistory()[0].id, firstPoll.id)
  assert.equal(context.session.get(`votestupid:admin-token:${firstPoll.id}`), undefined)
  assert.equal(view.historyWarning.value, '')
  assert.doesNotMatch([...context.stored.values()].join(''), /token/)
})

// Comprueba que un fallo del histórico no invalida una votación que el backend ya ha creado.
test('conserva la confirmación y los enlaces cuando no se puede recordar la votación', async () => {
  const view = loadView('CreatePollView.vue', {
    '../services/pollService': {
      // Simula una creación correcta en el servidor.
      createPoll: async () => ({ ...firstPoll, admin_token: token }),
    },
    '../services/historyService': {
      // Simula un almacenamiento local bloqueado tras la creación.
      rememberPoll: () => { throw new Error('No se ha podido guardar el histórico.') },
    },
  })
  view.title.value = firstPoll.title
  view.options.value = ['A', 'B']
  await view.submitPoll()
  assert.equal(view.createdPoll.value.id, firstPoll.id)
  assert.equal(view.errorMessage.value, '')
  assert.match(view.historyWarning.value, /guardar el histórico/)
  assert.doesNotMatch(view.adminUrl.value, /#token=/)
})
