#!/usr/bin/env node
/**
 * Frontend dev runner.
 * Frees port 5173, then starts the Vue dev server.
 * The API runs separately — see sgummalla79/pragna-api.
 */

const { spawn, spawnSync } = require('child_process')
const path = require('path')

const ROOT   = path.resolve(__dirname, '..')
const IS_WIN = process.platform === 'win32'

function killPort(port) {
  if (IS_WIN) {
    spawnSync('powershell', [
      '-Command',
      `Get-NetTCPConnection -LocalPort ${port} -ErrorAction SilentlyContinue` +
      ` | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }`,
    ], { stdio: 'ignore' })
  } else {
    spawnSync('sh', ['-c', `lsof -ti:${port} | xargs kill -9 2>/dev/null; true`], { stdio: 'ignore' })
  }
}

function spawnLabeled(label, color, cmd, args, opts = {}) {
  const c = { green: '\x1b[32m', reset: '\x1b[0m', bold: '\x1b[1m' }
  const prefix = `${c.bold}${c[color]}[${label}]${c.reset} `
  const child = spawn(cmd, args, { ...opts, stdio: ['ignore', 'pipe', 'pipe'], cwd: ROOT })
  child.stdout.on('data', d => process.stdout.write(d.toString().replace(/^(?=.)/gm, prefix)))
  child.stderr.on('data', d => process.stderr.write(d.toString().replace(/^(?=.)/gm, prefix)))
  return child
}

console.log('\n── Freeing port 5173 ───────────────────────────────────────────')
killPort(5173)
console.log('  ✔  Port 5173 cleared')
console.log(`  ✔  Platform: ${IS_WIN ? 'Windows' : 'macOS/Linux'}`)
console.log('  ℹ  API (port 8000) runs separately — start it from pragna-api repo')
console.log('───────────────────────────────────────────────────────────────\n')

const frontend = IS_WIN
  ? spawnLabeled('frontend', 'green', 'cmd', ['/C', 'cd frontend && npm install --silent && npm run dev'])
  : spawnLabeled('frontend', 'green', 'sh', ['-c', 'cd frontend && npm install --silent && npm run dev'])

process.on('SIGINT',  () => { frontend.kill('SIGTERM'); killPort(5173); process.exit(0) })
process.on('SIGTERM', () => { frontend.kill('SIGTERM'); killPort(5173); process.exit(0) })

frontend.on('exit', code => {
  killPort(5173)
  process.exit(code ?? 1)
})
