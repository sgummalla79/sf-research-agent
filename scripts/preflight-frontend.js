#!/usr/bin/env node
/**
 * Pre-flight checks before starting the dev server.
 * Exits with code 1 if anything is wrong.
 */

const fs   = require('fs')
const path = require('path')

const ROOT = path.resolve(__dirname, '..')

let ok = true

function pass(msg) { console.log(`  ✔  ${msg}`) }
function fail(msg) { console.error(`  ✘  ${msg}`); ok = false }

console.log('\n── Pre-flight ─────────────────────────────────────────────────')

// 1. package.json present
if (fs.existsSync(path.join(ROOT, 'package.json'))) {
  pass('package.json found')
} else {
  fail(`package.json missing at ${ROOT}`)
}

// 2. node_modules installed
if (fs.existsSync(path.join(ROOT, 'node_modules'))) {
  pass('node_modules present')
} else {
  fail('node_modules not found — run npm install')
}

// 3. vite.config.js present
if (fs.existsSync(path.join(ROOT, 'vite.config.js'))) {
  pass('vite.config.js found')
} else {
  fail(`vite.config.js missing at ${ROOT}`)
}

console.log('───────────────────────────────────────────────────────────────')
if (!ok) {
  console.error('\n  Pre-flight FAILED. Fix the issues above and retry.\n')
  process.exit(1)
}
console.log('\n  Pre-flight passed.\n')
