#!/usr/bin/env node
/**
 * Pre-flight checks for the backend.
 * Exits with code 1 (blocking the dev server from starting) if anything is wrong.
 */

const fs   = require('fs')
const path = require('path')
const { execSync } = require('child_process')

const ROOT    = path.resolve(__dirname, '..')
const BACKEND = path.join(ROOT, 'backend')

let ok = true

function pass(msg) { console.log(`  ✔  ${msg}`) }
function fail(msg) { console.error(`  ✘  ${msg}`); ok = false }
function info(msg) { console.log(`  ℹ  ${msg}`) }

console.log('\n── Backend pre-flight ─────────────────────────────────────────')

// ── 1. Python available ──────────────────────────────────────────────────────
try {
  const ver = execSync('python --version 2>&1', { encoding: 'utf8' }).trim()
  pass(`Python found: ${ver}`)
} catch {
  fail('Python not found. Install Python 3.11+ and ensure it is on PATH.')
}

// ── 2. Virtual environment ───────────────────────────────────────────────────
const venvPy = path.join(BACKEND, '.venv', 'Scripts', 'python.exe')
const venvPyUnix = path.join(BACKEND, '.venv', 'bin', 'python')
const venvExists = fs.existsSync(venvPy) || fs.existsSync(venvPyUnix)
if (venvExists) {
  pass('.venv exists')
} else {
  info('.venv not found — it will be created automatically by dev:backend:win/mac')
}

// ── 3. requirements.txt present ─────────────────────────────────────────────
const req = path.join(BACKEND, 'requirements.txt')
if (fs.existsSync(req)) {
  pass('requirements.txt found')
} else {
  fail(`requirements.txt missing at ${req}`)
}

// ── 4. .env file ────────────────────────────────────────────────────────────
const envFile = path.join(BACKEND, '.env')
if (!fs.existsSync(envFile)) {
  fail(`.env not found at ${envFile}\n     Copy backend/.env.example to backend/.env and fill in the values.`)
} else {
  pass('.env file found')

  const envContent = fs.readFileSync(envFile, 'utf8')
  const envVars = {}
  for (const line of envContent.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    const key = trimmed.slice(0, eq).trim()
    const val = trimmed.slice(eq + 1).trim()
    envVars[key] = val
  }

  // ── 5. SETTINGS_SECRET present and valid Fernet key ─────────────────────
  const secret = envVars['SETTINGS_SECRET'] || ''
  if (!secret) {
    fail('SETTINGS_SECRET is not set in backend/.env\n' +
         '     Generate one with:\n' +
         '     python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
  } else {
    try {
      const decoded = Buffer.from(secret, 'base64')
      if (decoded.length !== 32) throw new Error('wrong length')
      pass('SETTINGS_SECRET is a valid Fernet key')
    } catch {
      fail('SETTINGS_SECRET is set but is NOT a valid Fernet key (must be 32 url-safe base64 bytes).\n' +
           '     Generate a valid key with:\n' +
           '     python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
    }
  }

  // ── 6. DB config ────────────────────────────────────────────────────────
  const dbUrl = envVars['DATABASE_URL'] || ''
  const isPostgres = dbUrl.startsWith('postgresql://') || dbUrl.startsWith('postgres://')
  if (isPostgres) {
    pass(`DATABASE_URL set → PostgreSQL`)
  } else {
    const sqlitePath = envVars['SQLITE_PATH'] || 'data/agent.db'
    pass(`DATABASE_URL not set → SQLite at ${sqlitePath}`)
  }

  // ── 7. Port 8000 free ───────────────────────────────────────────────────
  const { createServer } = require('net')
  const probe = createServer()
  probe.once('error', () => {
    fail('Port 8000 is already in use. Run "npm run stop:backend:win" or "npm run stop:backend:mac" first.')
    probe.close()
  })
  probe.once('listening', () => {
    pass('Port 8000 is free')
    probe.close()
  })
  probe.listen(8000, '127.0.0.1')

  setTimeout(() => {
    console.log('───────────────────────────────────────────────────────────────')
    if (!ok) {
      console.error('\n  Backend pre-flight FAILED. Fix the issues above and retry.\n')
      process.exit(1)
    }
    console.log('\n  Backend pre-flight passed.\n')
  }, 200)

  return
}

console.log('───────────────────────────────────────────────────────────────')
if (!ok) {
  console.error('\n  Backend pre-flight FAILED. Fix the issues above and retry.\n')
  process.exit(1)
}
console.log('\n  Backend pre-flight passed.\n')
