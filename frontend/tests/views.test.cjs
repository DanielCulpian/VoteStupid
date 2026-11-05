const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadView, deferred } = require('./helpers/loadView.cjs')

const poll = {
  id: 'poll-1', title: 'Votación de prueba', description: null,
  poll_type: 'single_choice', is_active: true, max_selections: null,
  options: [{ id: 'a', text: 'Opción A' }, { id: 'b', text: 'Opción B' }],
}

// Verify that slow requests block duplicate submissions and form option changes.
test('bloquea la creación duplicada mientras la petición está pendiente', async () => {
  const request = deferred()
  let calls = 0
  const view = loadView('CreatePollView.vue', {
    '../services/pollService': {
      // Keep creation pending to verify that controls remain disabled.
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

// Verify that validation and network failures preserve form data and allow retries.
test('recupera el formulario tras datos inválidos y tras una creación fallida', async () => {
  let calls = 0
  const view = loadView('CreatePollView.vue', {
    '../services/pollService': {
      // Simulate an initial server failure followed by recovery.
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

// Verify submission locking and that results failures do not invalidate a saved vote.
test('registra y actualiza el voto sin envíos duplicados ni confirmaciones contradictorias', async () => {
  const request = deferred()
  let casts = 0
  let updates = 0
  let failResults = false
  const view = loadView('PollView.vue', {
    '../services/pollService': {
      // Return an open poll with two options for interaction.
      getPoll: async () => ({ ...poll }),
    },
    '../services/voteService': {
      // Keep submission pending to attempt another vote before completion.
      castVote: () => { casts++; return request.promise },
      // Record updates after the first confirmed vote.
      updateVote: async () => { updates++ },
    },
    '../services/resultsService': {
      // Isolate results errors from vote confirmation.
      getPollResults: async () => {
        if (failResults) throw new Error('No se pueden cargar los resultados.')
        return { total_votes: 0, results: [] }
      },
    },
    '../services/websocketService': {
      // Prevent external connections when testing submission logic only.
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

// Verify that administrative errors leave the panel usable and do not duplicate retries.
test('conserva la administración y permite cerrar y reabrir tras un fallo', async () => {
  const closeRequest = deferred()
  let closes = 0
  const view = loadView('AdminView.vue', {
    '../services/adminService': {
      // Provide a poll whose private access has already been validated.
      getAdminPoll: async () => ({ ...poll }),
      // Simulate a failed first closure and allow a later successful attempt.
      closePoll: () => {
        closes++
        return closes === 1 ? closeRequest.promise : Promise.resolve({ ...poll, is_active: false })
      },
      // Return the open state that confirms reopening.
      reopenPoll: async () => ({ ...poll, is_active: true }),
    },
    '../services/resultsService': {
      // Simulate an independent error that must not prevent poll administration.
      getPollResults: async () => { throw new Error('No se pueden cargar los resultados.') },
    },
    '../services/websocketService': {
      // Isolate administrative operation tests from WebSocket transport.
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

// Check both views with changes made during disconnection and cleanup on navigation.
for (const filename of ['PollView.vue', 'AdminView.vue']) {
  test(`${filename}: recupera resultados y estado sin perder selecciones y cancela al salir`, async () => {
    let callbacks, unmount, closed = 0
    let current = { ...poll }, total = 0
    const view = loadView(filename, {
      '../services/pollService': {
        // Return the current state, which may have changed during disconnection.
        getPoll: async () => ({ ...current }),
      },
      '../services/adminService': {
        // Simulate revalidating the session's administration token.
        getAdminPoll: async () => ({ ...current }),
      },
      '../services/voteService': {},
      '../services/resultsService': {
        // Return votes submitted by another client during disconnection.
        getPollResults: async () => ({ total_votes: total, results: [] }),
      },
      '../services/websocketService': {
        // Capture events to exercise the view's real synchronization logic.
        connectToPoll: (...args) => { callbacks = args; return { close() { closed++ } } },
      },
    }, {
      // Retain Vue's cleanup callback to simulate leaving the page.
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
