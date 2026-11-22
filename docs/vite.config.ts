import { defineConfig } from 'vite'
import { readFileSync } from 'node:fs'
import { execSync } from 'node:child_process'
import { dockit } from '@dreamlake/dockit/vite'

/** The version chip tracks the Python package this site documents. */
const pyproject = readFileSync(new URL('../pyproject.toml', import.meta.url), 'utf-8')
const APP_VERSION = pyproject.match(/^version = "(.*)"$/m)?.[1] ?? '0.0.0'

const GIT_HASH = (() => {
  try {
    return execSync('git rev-parse --short=6 HEAD', { encoding: 'utf-8' }).trim()
  } catch {
    return 'dev'
  }
})()

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(APP_VERSION),
    __GIT_HASH__: JSON.stringify(GIT_HASH),
  },
  // Spread: `vike prerender` only detects Vike's plugin at the top level.
  plugins: [...dockit()],
  server: { port: 3027 },
})
