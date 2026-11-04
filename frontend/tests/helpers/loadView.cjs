const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require('typescript')
const { parse, compileScript } = require('@vue/compiler-sfc')
const vue = require('vue')

// Ejecuta la lógica real de una vista con servicios controlados, sin montar una interfaz ficticia.
function loadView(filename, services = {}) {
  const source = fs.readFileSync(path.join(__dirname, '../../src/views', filename), 'utf8')
  const { descriptor } = parse(source)
  const compiled = compileScript(descriptor, { id: filename })
  const { outputText } = ts.transpileModule(compiled.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  })
  const storage = new Map([['votestupid:admin-token:poll-1', 'token-de-prueba']])
  const exports = {}
  vm.runInNewContext(outputText, {
    exports,
    // Resuelve Vue y los servicios explícitos de la prueba sin peticiones externas.
    require: name => {
      if (name === 'vue') return {
        ...vue,
        // El montaje y desmontaje se ejercitan explícitamente desde cada prueba.
        onMounted() {},
        // Evita registrar un ciclo de vida real cuando solo se prueba la lógica.
        onUnmounted() {},
      }
      if (name === 'vue-router') return {
        // Proporciona el identificador de la votación del escenario de prueba.
        useRoute: () => ({ params: { id: 'poll-1' } }),
      }
      if (name.endsWith('.vue')) return { default: {} }
      if (name in services) return services[name]
      throw new Error(`Servicio no configurado en la prueba: ${name}`)
    },
    localStorage: {
      // Recupera las selecciones guardadas por la vista durante la prueba.
      getItem: key => storage.get(key) ?? null,
      // Guarda las selecciones sin utilizar el almacenamiento del navegador del usuario.
      setItem: (key, value) => storage.set(key, value),
    },
    sessionStorage: {
      // Proporciona el token privado del escenario de administración.
      getItem: key => storage.get(key) ?? null,
      // Conserva el token del escenario cuando la vista lo recupera del enlace.
      setItem: (key, value) => storage.set(key, value),
    },
    window: {
      location: { origin: 'http://localhost:5173', hash: '', pathname: '/admin/poll-1', search: '' },
      // Sustituye la modificación del historial para no navegar fuera de la prueba.
      history: { replaceState() {} },
    },
    URLSearchParams,
    Error,
  }, { filename })
  // Recoge las referencias y acciones expuestas por script setup para comprobar su comportamiento.
  return exports.default.setup({}, { expose() {} })
}

// Crea una promesa cuyo resultado controla la prueba para simular una petición lenta.
function deferred() {
  let resolve
  let reject
  const promise = new Promise((success, failure) => { resolve = success; reject = failure })
  return { promise, resolve, reject }
}

module.exports = { loadView, deferred }
