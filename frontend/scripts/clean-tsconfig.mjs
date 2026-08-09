import fs from 'node:fs'
import path from 'node:path'

const tsconfigPath = path.resolve('.nuxt/tsconfig.json')
if (fs.existsSync(tsconfigPath)) {
  try {
    const raw = fs.readFileSync(tsconfigPath, 'utf8')
    const json = JSON.parse(raw)
    if (json.vueCompilerOptions?.plugins) {
      json.vueCompilerOptions.plugins = json.vueCompilerOptions.plugins.filter(
        (p) => !p.includes('vue-router'),
      )
      fs.writeFileSync(tsconfigPath, JSON.stringify(json, null, 2))
    }
  } catch {
    // Ignore parse errors if file is being generated
  }
}
