const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require('typescript')
const { parse, compileScript } = require('@vue/compiler-sfc')
const vue = require('vue')

// Execute real view logic with controlled services without mounting a mock interface.
function loadView(filename, services = {}, globals = {}) {
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
    setTimeout,
    clearTimeout,
    // Resolve Vue and explicit test services without external requests.
    require: name => {
      if (name === 'vue') return {
        ...vue,
        // Exercise mounting and unmounting explicitly in each test.
        onMounted(callback) { globals.captureMount?.(callback) },
        // Avoid registering a real lifecycle when only testing view logic.
        onUnmounted(callback) { globals.captureUnmount?.(callback) },
      }
      if (name === 'vue-router') return {
        // Provide the poll identifier for the test scenario.
        useRoute: () => ({ params: { id: 'poll-1' } }),
      }
      if (name.endsWith('.vue')) return { default: {} }
      if (name in services) return services[name]
      throw new Error(`Servicio no configurado en la prueba: ${name}`)
    },
    localStorage: {
      // Retrieve the selections stored by the view during the test.
      getItem: key => storage.get(key) ?? null,
      // Store selections without using the user's browser storage.
      setItem: (key, value) => storage.set(key, value),
    },
    sessionStorage: {
      // Provide the private token for the administrative test scenario.
      getItem: key => storage.get(key) ?? null,
      // Retain the scenario token when the view reads it from the link.
      setItem: (key, value) => storage.set(key, value),
    },
    window: {
      location: { origin: 'http://localhost:5173', hash: '', pathname: '/admin/poll-1', search: '' },
      // Replace history updates to avoid navigating away from the test.
      history: { replaceState() {} },
    },
    URLSearchParams,
    Error,
    document: {
      body: {},
      activeElement: null,
      // Test logic without real elements; focus tests may override this stub.
      getElementById: () => null,
    },
    ...globals,
  }, { filename })
  // Collect script setup references and actions to verify their behavior.
  return exports.default.setup(globals.props ?? {}, { expose() {} })
}

// Create a controlled promise to simulate a slow request.
function deferred() {
  let resolve
  let reject
  const promise = new Promise((success, failure) => { resolve = success; reject = failure })
  return { promise, resolve, reject }
}

module.exports = { loadView, deferred }
