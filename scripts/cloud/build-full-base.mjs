import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { compileEffects } from './base_effects.mjs'
const root = fileURLToPath(new URL('../../', import.meta.url))
const args = process.argv.slice(2)
let output = resolve('artifacts/original-full-09'), presetFile = join(root, 'scripts/cloud/presets/soft-tap.json')
for (let i = 0; i < args.length; i += 2) {
  if (!args[i + 1] || !['--output', '--preset'].includes(args[i])) throw new Error('Use --output DIR and/or --preset JSON')
  if (args[i] === '--output') output = resolve(args[i + 1]); else presetFile = resolve(args[i + 1])
}
if (existsSync(output)) throw new Error('Output directory exists; choose a new directory')
mkdirSync(dirname(output), { recursive: true })
const work = mkdtempSync(join(dirname(output), '.full-base-'))
try {
  execFileSync('python', ['scripts/cloud/original_base.py', '--output', join(work, 'base')], { cwd: root })
  const preset = JSON.parse(readFileSync(presetFile, 'utf8'))
  const result = await compileEffects(readFileSync(join(work, 'base/original-base-prototype-09.bds')), preset)
  writeFileSync(join(work, 'original-full-prototype-09.bds'), result.bytes)
  writeFileSync(join(work, 'validation.json'), JSON.stringify(result.report, null, 2) + '\n')
  writeFileSync(join(work, 'preset.json'), JSON.stringify(preset, null, 2) + '\n')
  mkdirSync(join(work, 'original-sound-masters'))
  for (const [name, data] of Object.entries(result.masters)) writeFileSync(join(work, 'original-sound-masters', name + '.wav'), data)
  renameSync(work, output)
  console.log(JSON.stringify({ output, ...result.report }, null, 2))
} finally {
  if (existsSync(work)) rmSync(work, { recursive: true, force: true })
}
