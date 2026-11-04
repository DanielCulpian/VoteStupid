const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const ts = require('typescript')

// Carga el servicio real con una URL de prueba y dependencias controladas, sin navegador ni servidor.
function loadService(filename, globals = {}) {
  const source = fs.readFileSync(path.join(__dirname, '../../src/services', filename), 'utf8')
    .replaceAll('import.meta.env.VITE_API_URL', JSON.stringify('http://127.0.0.1:8000'))
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  })
  const exports = {}
  vm.runInNewContext(outputText, {
    exports, Headers, AbortSignal, Error, setTimeout, clearTimeout, console,
    ...globals,
  }, { filename })
  return exports
}

module.exports = { loadService }
