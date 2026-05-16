#!/usr/bin/env node
/**
 * Cross-platform dev runner (Mac + Windows).
 * 1. Frees ports 8000 and 5173.
 * 2. Starts the backend (platform-appropriate venv path).
 * 3. Polls GET /health until the backend is ready.
 * 4. Only then starts the frontend — no ECONNREFUSED on first load.
 * 5. CTRL+C kills both processes and frees both ports.
 */

const { spawn, spawnSync } = require('child_process')
const http  = require('http')
const path  = require('path')

const ROOT    = path.resolve(__dirname, '..')
const IS_WIN  = process.platform === 'win32'

// ── helpers ──────────────────────────────────────────────────────────────────

function killPort(port) {
  if (IS_WIN) {
    spawnSync('powershell', [
      '-Command',
      `Get-NetTCPConnection -LocalPort ${port} -ErrorAction SilentlyContinue` +
      ` | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }`,
    ], { stdio: 'ignore' })
  } else {
    // lsof may find nothing — that's fine; suppress errors
    spawnSync('sh', ['-c', `lsof -ti:${port} | xargs kill -9 2>/dev/null; true`], { stdio: 'ignore' })
  }
}

function spawnLabeled(label, color, cmd, args, opts = {}) {
  const c = { blue: '\x1b[34m', green: '\x1b[32m', reset: '\x1b[0m', bold: '\x1b[1m' }
  const prefix = `${c.bold}${c[color]}[${label}]${c.reset} `
  const child = spawn(cmd, args, { ...opts, stdio: ['ignore', 'pipe', 'pipe'], cwd: ROOT })
  child.stdout.on('data', d => process.stdout.write(d.toString().replace(/^(?=.)/gm, prefix)))
  child.stderr.on('data', d => process.stderr.write(d.toString().replace(/^(?=.)/gm, prefix)))
  return child
}

function waitForBackend(url, intervalMs, timeoutMs) {
  return new Promise((resolve, reject) => {
    const start   = Date.now()
    const attempt = () => {
      http.get(url, res => {
        if (res.statusCode === 200) return resolve()
        retry()
      }).on('error', retry)
    }
    const retry = () => {
      if (Date.now() - start > timeoutMs)
        return reject(new Error(`Backend did not become ready within ${timeoutMs / 1000}s`))
      setTimeout(attempt, intervalMs)
    }
    attempt()
  })
}

// ── main ─────────────────────────────────────────────────────────────────────

console.log('\n── Freeing ports ───────────────────────────────────────────────')
killPort(8000)
killPort(5173)
console.log('  ✔  Ports 8000 and 5173 cleared')
console.log(`  ✔  Platform: ${IS_WIN ? 'Windows' : 'macOS/Linux'}`)
console.log('───────────────────────────────────────────────────────────────\n')

const processes = []

function killAll() {
  for (const p of processes) {
    try { process.kill(-p.pid, 'SIGTERM') } catch { /* ignore */ }
    try { p.kill('SIGTERM') } catch { /* ignore */ }
  }
  killPort(8000)
  killPort(5173)
}

process.on('SIGINT',  () => { killAll(); process.exit(0) })
process.on('SIGTERM', () => { killAll(); process.exit(0) })

// ── 1. Start backend ─────────────────────────────────────────────────────────

// PYTHONUNBUFFERED=1 ensures Python never buffers stdout/stderr in pipe mode
const backendEnv = { ...process.env, PYTHONUNBUFFERED: '1' }

let backend
if (IS_WIN) {
  backend = spawnLabeled('backend', 'blue', 'cmd', [
    '/C',
    'cd backend && ' +
    '(if not exist .venv python -m venv .venv) && ' +
    '.venv\\Scripts\\pip install -r requirements.txt -q --disable-pip-version-check && ' +
    '.venv\\Scripts\\uvicorn api.app:app --reload --port 8000',
  ], { env: backendEnv })
} else {
  backend = spawnLabeled('backend', 'blue', 'sh', [
    '-c',
    'cd backend && ' +
    '([ -d .venv ] || python3 -m venv .venv) && ' +
    '.venv/bin/pip install -r requirements.txt -q --disable-pip-version-check && ' +
    '.venv/bin/uvicorn api.app:app --reload --port 8000',
  ], { env: backendEnv })
}
processes.push(backend)

backend.on('exit', code => {
  console.error(`\n[backend] exited with code ${code}`)
  killAll()
  process.exit(code ?? 1)
})

// ── 2. Wait for /health, then start frontend ─────────────────────────────────

console.log('[runner] Waiting for backend to be ready...')
waitForBackend('http://localhost:8000/health', 1000, 120000)
  .then(() => {
    console.log('[runner] Backend is ready — starting frontend\n')

    let frontend
    if (IS_WIN) {
      frontend = spawnLabeled('frontend', 'green', 'cmd', [
        '/C',
        'cd frontend && npm install --silent && npm run dev',
      ])
    } else {
      frontend = spawnLabeled('frontend', 'green', 'sh', [
        '-c',
        'cd frontend && npm install --silent && npm run dev',
      ])
    }
    processes.push(frontend)

    frontend.on('exit', code => {
      console.error(`\n[frontend] exited with code ${code}`)
      killAll()
      process.exit(code ?? 1)
    })
  })
  .catch(err => {
    console.error(`\n[runner] ${err.message}`)
    killAll()
    process.exit(1)
  })
