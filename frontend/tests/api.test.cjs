const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadService } = require('./helpers/loadService.cjs')

// Construye una respuesta HTTP simulada con el mismo formato JSON que la API.
function jsonResponse(status, data) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
}

// Comprueba que una respuesta correcta conserva los datos y las cabeceras privadas de la petición.
test('devuelve los datos y conserva las cabeceras de administración', async () => {
  let received
  const { apiRequest } = loadService('api.ts', {
    // Captura los argumentos enviados sin realizar ninguna conexión de red.
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
  assert.equal(received.url, 'http://127.0.0.1:8000/api/admin/polls/poll-1')
  assert.ok(received.options.signal instanceof AbortSignal)
})

// Comprueba que una caída de red muestra una explicación en español y permite reintentar.
test('traduce un fallo de conexión con el backend', async () => {
  const { apiRequest } = loadService('api.ts', {
    // Simula el rechazo de fetch cuando el servidor no está disponible.
    fetch: async () => { throw new TypeError('Failed to fetch') },
  })
  await assert.rejects(apiRequest('/api/polls/poll-1'), /No se puede conectar con el servidor/)
})

// Comprueba los mensajes de enlace, permisos y servidor sin exponer sus detalles internos.
test('presenta errores HTTP comprensibles y conserva el código de estado', async () => {
  for (const [status, detail, expected] of [
    [404, 'Not Found', /No se ha encontrado la votación/],
    [403, 'Forbidden', /acceso de administración no es válido/],
    [500, 'password=secreto interno', /servidor no puede completar/],
    [429, 'Too Many Requests', /demasiadas peticiones/],
    [409, 'La votación está cerrada.', /La votación está cerrada/],
  ]) {
    const { apiRequest, ApiError } = loadService('api.ts', {
      // Devuelve el estado HTTP correspondiente a cada escenario de error.
      fetch: async () => jsonResponse(status, { detail }),
    })
    await assert.rejects(apiRequest('/api/polls/poll-1'), error => {
      // Verifica el tipo del error, su estado y el mensaje que recibirá la vista.
      assert.ok(error instanceof ApiError)
      assert.equal(error.status, status)
      assert.match(error.message, expected)
      assert.doesNotMatch(error.message, /password|secreto interno/)
      return true
    })
  }
})

// Comprueba que los errores de validación señalan el enlace o el campo sin mostrar texto técnico.
test('traduce los errores de validación de FastAPI', async () => {
  for (const [loc, expected] of [
    [['path', 'poll_id'], /enlace de la votación no es válido/],
    [['body', 'title'], /Revisa el título/],
    [['body', 'selected_option_ids'], /Revisa las opciones de tu voto/],
    [['header', 'X-Admin-Token'], /Falta el acceso de administración/],
    [['body', 'campo_desconocido'], /Revisa los datos del formulario/],
  ]) {
    const { apiRequest } = loadService('api.ts', {
      // Simula los detalles estructurados de una validación fallida.
      fetch: async () => jsonResponse(422, { detail: [{ loc, msg: 'Input should be valid' }] }),
    })
    await assert.rejects(apiRequest('/api/polls/incorrecto'), expected)
  }
})

// Comprueba que una respuesta ilegible no se trata como una operación correcta.
test('rechaza una respuesta correcta que no contiene JSON válido', async () => {
  const { apiRequest } = loadService('api.ts', {
    // Simula un proxy que responde con HTML en lugar de los datos de la votación.
    fetch: async () => new Response('<html>Error</html>', { status: 200 }),
  })
  await assert.rejects(apiRequest('/api/polls/poll-1'), /respuesta inesperada/)
})

// Comprueba que el tiempo límite se aplica tanto a la conexión como a la lectura del cuerpo.
test('limita la espera a 15 segundos sin necesitar una espera real', async () => {
  for (const duringBody of [false, true]) {
    const controller = new AbortController()
    let timeoutDuration
    let notifyPending
    // Permite cancelar la señal cuando la operación simulada ya está esperando.
    const pendingStarted = new Promise(resolve => { notifyPending = resolve })
    const { apiRequest } = loadService('api.ts', {
      AbortSignal: {
        // Proporciona una señal que la prueba puede cancelar de forma inmediata.
        timeout: milliseconds => {
          timeoutDuration = milliseconds
          return controller.signal
        },
      },
      // Simula una operación que no finaliza hasta que vence su señal de tiempo límite.
      fetch: async () => {
        const pending = () => new Promise((resolve, reject) => {
          // Interrumpe la operación pendiente al agotarse el tiempo permitido.
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
