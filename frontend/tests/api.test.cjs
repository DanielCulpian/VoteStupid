const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadService } = require('./helpers/loadService.cjs')

// Build a mock HTTP response using the API's JSON format.
function jsonResponse(status, data) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
}

// Verify that successful responses preserve data and private request headers.
test('devuelve los datos y conserva las cabeceras de administración', async () => {
  let received
  const { apiRequest } = loadService('api.ts', {
    // Capture request arguments without making a network connection.
    fetch: async (url, options) => {
      received = { url, options }
      return jsonResponse(200, { id: 'poll-1' })
    },
  })
  const data = await apiRequest('/api/admin/polls/poll-1', {
    headers: new Headers({ 'X-Admin-Token': 'token-de-prueba' }),
  })
  assert.equal(data.id, 'poll-1')
  assert.equal(received.options.headers.get('X-Admin-Token'), 'token-de-prueba')
  assert.equal(received.options.headers.get('Content-Type'), 'application/json')
  assert.equal(received.options.headers.get('X-Requested-With'), 'VoteStupid')
  assert.equal(received.options.credentials, 'include')
  assert.equal(received.url, 'http://127.0.0.1:8000/api/admin/polls/poll-1')
  assert.ok(received.options.signal instanceof AbortSignal)
})

// Verify that network failures show a Spanish explanation and allow retrying.
test('traduce un fallo de conexión con el backend', async () => {
  const { apiRequest } = loadService('api.ts', {
    // Simulate fetch rejecting when the server is unavailable.
    fetch: async () => { throw new TypeError('Failed to fetch') },
  })
  await assert.rejects(apiRequest('/api/polls/poll-1'), /No se puede conectar con el servidor/)
})

// Check link, permission, and server error messages without exposing internal details.
test('presenta errores HTTP comprensibles y conserva el código de estado', async () => {
  for (const [status, detail, expected] of [
    [404, 'Not Found', /No se ha encontrado la votación/],
    [403, 'Forbidden', /No tienes autorización/],
    [500, 'password=secreto interno', /servidor no puede completar/],
    [429, 'Too Many Requests', /demasiadas peticiones/],
    [409, 'La votación está cerrada.', /La votación está cerrada/],
  ]) {
    const { apiRequest, ApiError } = loadService('api.ts', {
      // Return the HTTP status for each error scenario.
      fetch: async () => jsonResponse(status, { detail }),
    })
    await assert.rejects(apiRequest('/api/polls/poll-1'), error => {
      // Verify the error type, status, and message received by the view.
      assert.ok(error instanceof ApiError)
      assert.equal(error.status, status)
      assert.match(error.message, expected)
      assert.doesNotMatch(error.message, /password|secreto interno/)
      return true
    })
  }
})

// Verify that validation errors identify a link or field without technical wording.
test('traduce los errores de validación de FastAPI', async () => {
  for (const [loc, expected] of [
    [['path', 'poll_id'], /enlace de la votación no es válido/],
    [['body', 'title'], /Revisa el título/],
    [['body', 'selected_option_ids'], /Revisa las opciones de tu voto/],
    [['header', 'X-Admin-Token'], /Falta el acceso de administración/],
    [['body', 'campo_desconocido'], /Revisa los datos del formulario/],
  ]) {
    const { apiRequest } = loadService('api.ts', {
      // Simulate structured details from a failed validation.
      fetch: async () => jsonResponse(422, { detail: [{ loc, msg: 'Input should be valid' }] }),
    })
    await assert.rejects(apiRequest('/api/polls/incorrecto'), expected)
  }
})

// Verify that an unreadable response is not treated as a successful operation.
test('rechaza una respuesta correcta que no contiene JSON válido', async () => {
  const { apiRequest } = loadService('api.ts', {
    // Simulate a proxy returning HTML instead of poll data.
    fetch: async () => new Response('<html>Error</html>', { status: 200 }),
  })
  await assert.rejects(apiRequest('/api/polls/poll-1'), /respuesta inesperada/)
})

// Verify that the timeout covers both connection establishment and body reading.
test('limita la espera a 15 segundos sin necesitar una espera real', async () => {
  for (const duringBody of [false, true]) {
    const controller = new AbortController()
    let timeoutDuration
    let notifyPending
    // Allow cancelling the signal while the simulated operation is pending.
    const pendingStarted = new Promise(resolve => { notifyPending = resolve })
    const { apiRequest } = loadService('api.ts', {
      AbortSignal: {
        // Provide a signal that the test can cancel immediately.
        timeout: milliseconds => {
          timeoutDuration = milliseconds
          return controller.signal
        },
      },
      // Simulate an operation that remains pending until its timeout signal expires.
      fetch: async () => {
        const pending = () => new Promise((resolve, reject) => {
          // Interrupt the pending operation when its allowed time expires.
          controller.signal.addEventListener('abort', () => reject(controller.signal.reason), { once: true })
          notifyPending()
        })
        if (duringBody) return { ok: true, status: 200, json: pending }
        return pending()
      },
    })
    const request = apiRequest('/api/polls/poll-1')
    const rejected = assert.rejects(request, /servidor está tardando demasiado/)
    await pendingStarted
    controller.abort(new DOMException('Timeout', 'TimeoutError'))
    await rejected
    assert.equal(timeoutDuration, 15000)
  }
})
