const assert = require('node:assert/strict')
const { test } = require('node:test')
const { loadService } = require('./helpers/loadService.cjs')

// Execute real guards with a controlled router and cookie validation.
function routing() {
  let guard, expired, authenticated = false
  const replacements = []
  let routes
  const router = {
    currentRoute: { value: { path: '/admin', meta: { private: true } } },
    beforeEach(callback) { guard = callback },
    replace(target) { replacements.push(target); return Promise.resolve() },
  }
  loadService('../router/index.ts', {
    window: { addEventListener(_, callback) { expired = callback } },
    // Stub visual components while preserving the router's authorization logic.
    require: name => name === 'vue-router' ? {
      createWebHistory: () => ({}),
      createRouter: config => { routes = config.routes; return router },
    } : name.includes('authService') ? {
      getSession: async () => { if (!authenticated) throw new Error('Caducada'); return { authenticated: true } },
    } : { default: {} },
  })
  return { router, routes, guard: to => guard(to), expire: () => expired(), replacements, authenticate: () => { authenticated = true } }
}

// Verify that private entries require a session while the home page remains public.
test('protege panel, creación y administración individual sin bloquear visitantes', async () => {
  const context = routing()
  for (const path of ['/admin', '/admin/crear', '/admin/:id']) {
    const route = context.routes.find(r => r.path === path)
    assert.equal(route.meta.private, true)
    const redirect = await context.guard({ ...route, path })
    assert.equal(redirect.path, '/acceso')
    assert.equal(redirect.query.redirect, path)
  }
  const home = context.routes.find(r => r.path === '/')
  assert.equal(await context.guard(home), true)
  assert.equal(context.routes.find(r => r.path === '/crear').redirect, '/admin/crear')
})

// Recover old polls with a valid cookie without retaining secret links.
test('permite entrar en todas las rutas privadas con una sesión válida', async () => {
  const context = routing(); context.authenticate()
  assert.equal(await context.guard({ path: '/admin/old-poll', meta: { private: true } }), true)
})

// Remove sensitive fragments from login redirects.
test('no incorpora tokens de enlaces antiguos a la URL de inicio de sesión', async () => {
  const context = routing()
  const redirect = await context.guard({ path: '/admin/poll', fullPath: '/admin/poll#token=secret', meta: { private: true } })
  assert.doesNotMatch(JSON.stringify(redirect), /secret|token/)
})

// React to revoked sessions while leaving public routes accessible.
test('redirige al caducar la sesión solo cuando la vista actual es privada', () => {
  const context = routing(); context.expire()
  assert.equal(context.replacements[0].path, '/acceso')
  context.router.currentRoute.value = { path: '/', meta: {} }
  context.expire()
  assert.equal(context.replacements.length, 1)
})
