const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadService } = require('./helpers/loadService.cjs')

// Ejecuta el servicio real con peticiones observables sin acceso al servidor.
function setup() {
  const calls = []
  const service = loadService('catalogService.ts', {
    URLSearchParams,
    // Conserva la consulta enviada para comprobar todos los filtros combinables.
    require: () => ({ apiRequest: async url => { calls.push(url); return { items: [], total: 0 } } }),
  })
  return { service, calls }
}

// Comprueba que no se pierde ningún filtro ni se mezcla la ruta pública con la privada.
test('combina estados, tipos y paginación en el catálogo público y privado', async () => {
  const { service, calls } = setup()
  for (const state of ['all', 'active', 'inactive']) {
    for (const type of ['', 'single_choice', 'multiple_choice', 'ranking']) {
      await service.getCatalog(state, type, 24)
      const url = new URL(calls.at(-1), 'http://localhost')
      assert.equal(url.pathname, '/api/polls')
      assert.equal(url.searchParams.get('state'), state)
      assert.equal(url.searchParams.get('poll_type') ?? '', type)
      assert.equal(url.searchParams.get('offset'), '24')
    }
  }
  await service.getCatalog('all', '', 0, true)
  assert.match(calls.at(-1), /^\/api\/admin\/polls\?/)
})

// Verifica que una fecha cumplida y un cierre manual deshabilitan la participación en tarjetas.
test('calcula la disponibilidad incluyendo los cierres programados', () => {
  const { service } = setup()
  assert.equal(service.isOpen({ is_active: true, closes_at: null }, 1000), true)
  assert.equal(service.isOpen({ is_active: false, closes_at: null }, 1000), false)
  assert.equal(service.isOpen({ is_active: true, closes_at: new Date(999).toISOString() }, 1000), false)
  assert.equal(service.isOpen({ is_active: true, closes_at: new Date(1001).toISOString() }, 1000), true)
})

// Mantiene denominaciones comprensibles y coherentes para los tres tipos existentes.
test('presenta los tres tipos sin nombres técnicos internos', () => {
  const { service } = setup()
  assert.equal(service.typeLabel('single_choice'), 'Elección única')
  assert.equal(service.typeLabel('multiple_choice'), 'Elección múltiple')
  assert.equal(service.typeLabel('ranking'), 'Ranking')
})
