const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadView } = require('./helpers/loadView.cjs')

// Proporciona los servicios de la vista pública sin realizar peticiones ni abrir conexiones.
function pollServices() {
  return {
    '../services/pollService': {},
    '../services/voteService': {},
    '../services/resultsService': {},
    '../services/websocketService': {},
  }
}

// Comprueba que un error del formulario señala el campo y permite corregirlo con el teclado.
test('sitúa el foco en el primer campo inválido y conserva su explicación', async () => {
  const focused = []
  const view = loadView('CreatePollView.vue', { '../services/pollService': {} }, {
    document: {
      // Registra el campo que recibirá el foco tras la validación.
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

// Comprueba que añadir o eliminar opciones conserva un punto de continuación para el teclado.
test('mantiene el foco en una opción existente al añadir y eliminar filas', async () => {
  const focused = []
  const view = loadView('CreatePollView.vue', { '../services/pollService': {} }, {
    document: {
      // Captura el identificador de la opción que recibe el foco.
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

// Comprueba que mover una opción al extremo mantiene el foco en una acción que sigue habilitada.
test('anuncia la posición del ranking y evita perder el foco en un botón desactivado', async () => {
  const focused = []
  const view = loadView('PollView.vue', pollServices(), {
    document: {
      // Simula que subir deja de estar disponible cuando la opción llega al primer puesto.
      getElementById: id => ({
        disabled: id.endsWith('-up'),
        // Registra el control disponible al que se devuelve el foco.
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
