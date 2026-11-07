import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { compileEffects } from './base_effects.mjs'
const root = fileURLToPath(new URL('../../', import.meta.url))
const args = process.argv.slice(2)
if (args.length && (args.length !== 2 || args[0] !== '--output')) throw new Error('Use --output DIR')
const output = resolve(args[1] ?? 'artifacts/mist-lilac')
if (existsSync(output)) throw new Error('Output already exists')
mkdirSync(dirname(output), { recursive: true })
const work = mkdtempSync(join(dirname(output), '.mist-demo-'))
try {
  execFileSync('python', ['scripts/cloud/mist_lilac.py', '--output', join(work, 'artwork')], { cwd: root })
  const preset = JSON.parse(readFileSync(join(root, 'scripts/cloud/presets/soft-tap.json'), 'utf8'))
  const result = await compileEffects(readFileSync(join(work, 'artwork/themed-base.bds')), preset)
  writeFileSync(join(work, 'mist-lilac.bds'), result.bytes)
  writeFileSync(join(work, 'validation.json'), JSON.stringify({ theme: '雾紫轻触10', ...result.report }, null, 2) + '\n')
  renameSync(work, output)
  console.log(JSON.stringify({ output, sha256: result.report.sha256, bound_keys: result.report.bound_keys, device_verified: false }))
} finally {
  if (existsSync(work)) rmSync(work, { recursive: true, force: true })
}
