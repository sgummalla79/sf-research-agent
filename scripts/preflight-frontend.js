#!/usr/bin/env node
/**
 * Pre-flight checks for the frontend.
 * Exits with code 1 (blocking the dev server from starting) if anything is wrong.
 */

const fs   = require('fs')
const path = require('path')
const { createServer } = require('net')

const ROOT     = path.resolve(__dirname, '..')
const FRONTEND = path.join(ROOT, 'frontend')

let ok = true

function pass(msg) { console.log(`  ✔  ${msg}`) }
function fail(msg) { console.error(`  ✘  ${msg}`); ok = false }

console.log('\n── Frontend pre-flight ────────────────────────────────────────')

// ── 1. frontend/package.json present ────────────────────────────────────────
const pkgJson = path.join(FRONTEND, 'package.json')
if (fs.existsSync(pkgJson)) {
  pass('frontend/package.json found')
} else {
  fail(`frontend/package.json missing at ${pkgJson}`)
}

// ── 2. node_modules installed ───────────────────────────────────────────────
const nodeModules = path.join(FRONTEND, 'node_modules')
if (fs.existsSync(nodeModules)) {
  pass('frontend/node_modules present')
} else {
  fail('frontend/node_modules not found. Run "npm run dev:frontend:win" or "npm run dev:frontend:mac" — it installs automatically.')
}

// ── 3. vite.config.js present ───────────────────────────────────────────────
const viteCfg = path.join(FRONTEND, 'vite.config.js')
if (fs.existsSync(viteCfg)) {
  pass('vite.config.js found')
} else {
  fail(`vite.config.js missing at ${viteCfg}`)
}

console.log('───────────────────────────────────────────────────────────────')
if (!ok) {
  console.error('\n  Frontend pre-flight FAILED. Fix the issues above and retry.\n')
  process.exit(1)
}
console.log('\n  Frontend pre-flight passed.\n')
