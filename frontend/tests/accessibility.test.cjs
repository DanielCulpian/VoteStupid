const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadView } = require('./helpers/loadView.cjs')

// Provide public view services without requests or external connections.
function pollServices() {
  return {
    '../services/pollService': {},
    '../services/voteService': {},
    '../services/resultsService': {},
    '../services/websocketService': {},
  }
}

// Verify that form errors identify the field and allow keyboard correction.
test('sitúa el foco en el primer campo inválido y conserva su explicación', async () => {
  const focused = []
  const view = loadView('CreatePollView.vue', { '../services/pollService': {} }, {
    document: {
      // Record the field that receives focus after validation.
      getElementById: id => ({ focus: () => focused.push(id) }),
    },
  })
  view.title.value = '   '
  await view.submitPoll()
  assert.equal(view.invalidField.value, 'title')
  assert.match(view.errorMessage.value, /título no puede estar vacío/)
  assert.equal(focused.at(-1), 'title')
  view.title.value = 'Título válido'
  view.options.value = ['A', '   ']
  await view.submitPoll()
  assert.equal(view.invalidField.value, 'option-1')
  assert.equal(focused.at(-1), 'option-1')
})

// Verify that adding or removing options preserves a keyboard navigation target.
test('mantiene el foco en una opción existente al añadir y eliminar filas', async () => {
  const focused = []
  const view = loadView('CreatePollView.vue', { '../services/pollService': {} }, {
    document: {
      // Capture the identifier of the option receiving focus.
      getElementById: id => ({ focus: () => focused.push(id) }),
    },
  })
  await view.addOption()
  assert.equal(view.options.value.length, 3)
  assert.equal(focused.at(-1), 'option-2')
  assert.match(view.formAnnouncement.value, /Opción 3 añadida/)
  await view.removeOption(2)
  assert.equal(view.options.value.length, 2)
  assert.equal(focused.at(-1), 'option-1')
  assert.match(view.formAnnouncement.value, /Quedan 2 opciones/)
})

// Verify that moving an option to an edge keeps focus on an enabled action.
test('anuncia la posición del ranking y evita perder el foco en un botón desactivado', async () => {
  const focused = []
  const view = loadView('PollView.vue', pollServices(), {
    document: {
      // Simulate the up control becoming unavailable when the option reaches first place.
      getElementById: id => ({
        disabled: id.endsWith('-up'),
        // Record the available control that receives focus.
        focus: () => focused.push(id),
      }),
    },
  })
  view.poll.value = {
    is_active: true,
    options: [{ id: 'a', text: 'Opción A' }, { id: 'b', text: 'Opción B' }, { id: 'c', text: 'Opción C' }],
  }
  view.rankingOptionIds.value = ['a', 'b', 'c']
  await view.moveRanking(1, -1)
  assert.deepEqual(Array.from(view.rankingOptionIds.value), ['b', 'a', 'c'])
  assert.equal(view.rankingAnnouncement.value, 'Opción B. Posición 1 de 3.')
  assert.equal(focused.at(-1), 'ranking-b-down')
  view.poll.value.is_active = false
  await view.moveRanking(0, 1)
  assert.equal(focused.length, 1)
  assert.deepEqual(Array.from(view.rankingOptionIds.value), ['b', 'a', 'c'])
})
