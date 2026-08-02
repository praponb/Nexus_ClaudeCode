#!/usr/bin/env node
/**
 * Vitest runner wrapper.
 * Some CI harnesses invoke `npm test -- --watchAll=false` (a Jest convention).
 * Vitest does not know that flag, so unknown watch-related flags are dropped
 * before delegating to `vitest run`.
 */
import { spawn } from 'node:child_process'

const passthrough = process.argv
  .slice(2)
  .filter((arg) => !arg.startsWith('--watchAll') && arg !== '--')

const child = spawn('vitest', ['run', ...passthrough], {
  stdio: 'inherit',
  shell: false,
  env: process.env,
})

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal)
    return
  }
  process.exit(code ?? 1)
})
