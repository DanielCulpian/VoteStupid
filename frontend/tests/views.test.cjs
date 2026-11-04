const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadView, deferred } = require('./helpers/loadView.cjs')

const poll = {
  id: 'poll-1', title: 'Votación de prueba', description: null,
  poll_type: 'single_choice', is_active: true, max_selections: null,
  options: [{ id: 'a', text: 'Opción A' }, { id: 'b', text: 'Opción B' }],
}

// Comprueba que una petición lenta no admite otro envío ni cambios en las opciones del formulario.
test('bloquea la creación duplicada mientras la petición está pendiente', async () => {
  const request = deferred()
  let calls = 0
  const view = loadView('CreatePollView.vue', {
    '../services/pollService': {
      // Mantiene la creación pendiente para comprobar el bloqueo de los controles.
      createPoll: () => { calls++; return request.promise },
    },
  })
  view.title.value = 'Título válido'
  view.options.value = ['A', 'B']
  const first = view.submitPoll()
  assert.equal(view.isSubmitting.value, true)
  await view.submitPoll()
  view.addOption()
  view.removeOption(0)
  assert.equal(calls, 1)
  assert.equal(view.options.value.length, 2)
  request.resolve({ ...poll, admin_token: 'token-de-prueba' })
  await first
  assert.equal(view.isSubmitting.value, false)
  assert.equal(view.createdPoll.value.id, poll.id)
})

// Comprueba que la validación y un fallo de red conservan los datos y permiten corregir o reintentar.
test('recupera el formulario tras datos inválidos y tras una creación fallida', async () => {
  let calls = 0
  const view = loadView('CreatePollView.vue', {
    '../services/pollService': {
      // Simula una caída inicial y la recuperación posterior del servidor.
      createPoll: async () => {
        calls++
        if (calls === 1) throw new Error('No se puede conectar con el servidor.')
        return { ...poll, admin_token: 'token-de-prueba' }
      },
    },
  })
  view.title.value = '   '
  view.options.value = ['A', 'B']
  await view.submitPoll()
  assert.equal(calls, 0)
  assert.match(view.errorMessage.value, /título no puede estar vacío/)
  view.title.value = 'Título corregido'
  await view.submitPoll()
  assert.equal(view.isSubmitting.value, false)
  assert.equal(view.title.value, 'Título corregido')
  assert.match(view.errorMessage.value, /conectar con el servidor/)
  await view.submitPoll()
  assert.equal(calls, 2)
  assert.equal(view.errorMessage.value, '')
  assert.equal(view.createdPoll.value.id, poll.id)
})

// Comprueba el bloqueo durante el envío y que un fallo al cargar resultados no invalida el voto guardado.
test('registra y actualiza el voto sin envíos duplicados ni confirmaciones contradictorias', async () => {
  const request = deferred()
  let casts = 0
  let updates = 0
  let failResults = false
  const view = loadView('PollView.vue', {
    '../services/pollService': {
      // Devuelve una votación abierta con dos opciones para la interacción.
      getPoll: async () => ({ ...poll }),
    },
    '../services/voteService': {
      // Conserva el envío pendiente para intentar votar de nuevo antes de finalizar.
      castVote: () => { casts++; return request.promise },
      // Registra las actualizaciones posteriores al primer voto confirmado.
      updateVote: async () => { updates++ },
    },
    '../services/resultsService': {
      // Permite aislar los errores de resultados de la confirmación del voto.
      getPollResults: async () => {
        if (failResults) throw new Error('No se pueden cargar los resultados.')
        return { total_votes: 0, results: [] }
      },
    },
    '../services/websocketService': {
      // Evita conexiones externas al probar únicamente la lógica de envío.
      connectToPoll: () => ({ close() {} }),
    },
  })
  await view.loadPoll()
  view.selectedOptionIds.value = ['a']
  const first = view.submitVote()
  await view.submitVote()
  view.toggleOption('b')
  assert.equal(casts, 1)
  assert.deepEqual(Array.from(view.selectedOptionIds.value), ['a'])
  failResults = true
  request.resolve({})
  await first
  assert.equal(view.isSubmitting.value, false)
  assert.equal(view.hasVoted.value, true)
  assert.match(view.successMessage.value, /registrado correctamente/)
  assert.equal(view.errorMessage.value, '')
  assert.match(view.resultsError.value, /cargar los resultados/)
  view.toggleOption('b')
  await view.submitVote()
  assert.equal(updates, 1)
  assert.match(view.successMessage.value, /actualizado/)
})

// Comprueba que un error administrativo deja el panel disponible y que los reintentos no se duplican.
test('conserva la administración y permite cerrar y reabrir tras un fallo', async () => {
  const closeRequest = deferred()
  let closes = 0
  const view = loadView('AdminView.vue', {
    '../services/adminService': {
      // Proporciona una votación cuyo acceso privado ya ha sido validado.
      getAdminPoll: async () => ({ ...poll }),
      // Simula un primer cierre fallido y permite otro cierre posterior.
      closePoll: () => {
        closes++
        return closes === 1 ? closeRequest.promise : Promise.resolve({ ...poll, is_active: false })
      },
      // Devuelve el estado abierto que confirma la reapertura.
      reopenPoll: async () => ({ ...poll, is_active: true }),
    },
    '../services/resultsService': {
      // Simula un error independiente que no debe impedir administrar la votación.
      getPollResults: async () => { throw new Error('No se pueden cargar los resultados.') },
    },
    '../services/websocketService': {
      // Aísla la prueba de operaciones administrativas del transporte WebSocket.
      connectToPoll: () => ({ close() {} }),
    },
  })
  await view.loadAdminPanel()
  assert.equal(view.poll.value.id, poll.id)
  assert.equal(view.errorMessage.value, '')
  assert.match(view.resultsError.value, /cargar los resultados/)
  const first = view.updatePollStatus()
  await view.updatePollStatus()
  assert.equal(closes, 1)
  closeRequest.reject(new Error('No se puede conectar con el servidor.'))
  await first
  assert.equal(view.isUpdating.value, false)
  assert.equal(view.poll.value.is_active, true)
  assert.match(view.errorMessage.value, /conectar con el servidor/)
  await view.updatePollStatus()
  assert.equal(view.poll.value.is_active, false)
  assert.match(view.successMessage.value, /se ha cerrado/)
  assert.equal(view.errorMessage.value, '')
  await view.updatePollStatus()
  assert.equal(view.poll.value.is_active, true)
  assert.match(view.successMessage.value, /se ha reabierto/)
})

// Comprueba ambas vistas con datos cambiados durante el corte y limpieza al navegar.
for (const filename of ['PollView.vue', 'AdminView.vue']) {
  test(`${filename}: recupera resultados y estado sin perder selecciones y cancela al salir`, async () => {
    let callbacks, unmount, closed = 0
    let current = { ...poll }, total = 0
    const view = loadView(filename, {
      '../services/pollService': {
        // Devuelve el estado actual que pudo cambiar durante la desconexion.
        getPoll: async () => ({ ...current }),
      },
      '../services/adminService': {
        // Simula la revalidacion del token administrativo de la sesion.
        getAdminPoll: async () => ({ ...current }),
      },
      '../services/voteService': {},
      '../services/resultsService': {
        // Devuelve los votos emitidos por otro cliente durante el corte.
        getPollResults: async () => ({ total_votes: total, results: [] }),
      },
      '../services/websocketService': {
        // Captura los eventos para ejercitar la sincronizacion real de la vista.
        connectToPoll: (...args) => { callbacks = args; return { close() { closed++ } } },
      },
    }, {
      // Conserva la limpieza registrada por Vue para simular el cambio de pagina.
      captureUnmount: callback => { unmount = callback },
    })
    await (filename === 'PollView.vue' ? view.loadPoll() : view.loadAdminPanel())
    if (view.selectedOptionIds) view.selectedOptionIds.value = ['b']
    callbacks[3]('disconnected')
    current = { ...poll, is_active: false }; total = 3
    await callbacks[4](() => true)
    callbacks[3]('connected')
    assert.equal(view.poll.value.is_active, false)
    assert.equal(view.results.value.total_votes, 3)
    if (view.selectedOptionIds) assert.deepEqual(Array.from(view.selectedOptionIds.value), ['b'])
    current = { ...poll, is_active: true }; total = 4
    await callbacks[4](() => false)
    assert.equal(view.poll.value.is_active, false)
    await callbacks[4](() => true)
    assert.equal(view.poll.value.is_active, true)
    assert.equal(view.results.value.total_votes, 4)
    unmount()
    assert.equal(closed, 1)
    total = 99
    await callbacks[4](() => true)
    callbacks[1]({ total_votes: 99 })
    callbacks[2](false)
    assert.equal(view.results.value.total_votes, 4)
    assert.equal(view.poll.value.is_active, true)
  })
}
