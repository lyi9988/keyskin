import assert from 'node:assert/strict'
import test, { after } from 'node:test'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { unzipSync, strFromU8 } from 'fflate'
import { compileEffects, validatePreset } from './base_effects.mjs'
import { IniDocument } from '../../src/ini.ts'
import { parseLegacyAnimation, legacyAnimationScale } from '../../src/preview-animation.ts'
import { SkinArchive } from '../../src/skin.ts'

const root = fileURLToPath(new URL('../../', import.meta.url))
const temp = mkdtempSync(join(tmpdir(), 'keyskin-effects-'))
after(() => rmSync(temp, { recursive: true, force: true }))
execFileSync('python', ['scripts/cloud/original_base.py', '--output', join(temp, 'base')], { cwd: root })
const bytes = readFileSync(join(temp, 'base/original-base-prototype-09.bds'))
const preset = JSON.parse(readFileSync(join(root, 'scripts/cloud/presets/soft-tap.json'), 'utf8'))
const result = await compileEffects(bytes, preset)
const files = unzipSync(result.bytes)

test('original full prototype compiles real sounds and animation bindings', () => {
  assert.equal(result.report.bound_keys, 580)
  assert.equal(result.report.animation_count, 2)
  for (const sound of Object.values(result.report.audio)) {
    assert.ok(sound.duration_ms >= 50 && sound.duration_ms < 100)
    assert.ok(sound.decoded_peak > 0 && sound.decoded_peak < .16)
    assert.equal(strFromU8(files['res/' + sound.filename].subarray(0, 4)), 'OggS')
  }
})

test('model sampling shrinks then restores, without claiming native playback', () => {
  const styles = IniDocument.parse(strFromU8(files['res/default.css']))
  const animation = IniDocument.parse(strFromU8(files['res/anim.ini']))
  const style = styles.sections().find(s => styles.get(s, 'PRESS_ANIM') === '1')
  const id = style.slice(5)
  const down = parseLegacyAnimation(styles, animation)
  assert.deepEqual(legacyAnimationScale(down, id, 0), [1, 1])
  const middle = legacyAnimationScale(down, id, 35)
  assert.ok(middle[0] < 1 && middle[0] > .96)
  assert.deepEqual(legacyAnimationScale(down, id, 70), [.96, .96])
  styles.set(style, 'PRESS_ANIM', '2') // Same model, sampling the separately bound release definition.
  const up = parseLegacyAnimation(styles, animation)
  assert.deepEqual(legacyAnimationScale(up, id, 0), [.96, .96])
  assert.deepEqual(legacyAnimationScale(up, id, 100), [1, 1])
  assert.equal(animation.get('ANIM2', 'REMOVE'), '1')
})

test('full package opens through KeySkin archive parser', async () => {
  const archive = await SkinArchive.openAsync(result.bytes, 'bds')
  assert.equal(archive.format, 'bds')
  assert.ok(archive.getText('light/skin/res/anim.ini').includes('ANIM_NUM=2'))
  assert.ok(archive.getBytes('light/skin/res/original-tap.ogg'))
})

test('loud, long, invalid and extra preset settings are rejected', () => {
  for (const override of [{ sound_peak_limit: .8 }, { sound_duration_ms: 5000 }, { press_duration_ms: Infinity }, { press_scale_percent: -1 }, { unknown: true }]) {
    assert.throws(() => validatePreset({ ...preset, ...override }))
  }
  assert.throws(() => validatePreset({ ...preset, frequencies_hz: { ...preset.frequencies_hz, tap: 30000 } }))
})

test('source WAV synthesis is reproducible', async () => {
  const again = await compileEffects(bytes, preset)
  assert.deepEqual(again.masters, result.masters)
})

test('later PNG replacement preserves sound, animation and actions byte for byte', () => {
  const full = join(temp, 'full.bds'), image = join(temp, 'blue.png'), plan = join(temp, 'plan.json')
  writeFileSync(full, result.bytes)
  execFileSync('python', ['-c', 'from PIL import Image; import sys; Image.new("RGB",(1080,624),"skyblue").save(sys.argv[1])', image])
  writeFileSync(plan, JSON.stringify({ replacements: [{ target: 'res/panel.png', image: 'blue.png' }] }))
  execFileSync('python', ['scripts/cloud/bds_visual.py', 'build', '--template', full, '--plan', plan, '--output', join(temp, 'recolored')], { cwd: root })
  const after = unzipSync(readFileSync(join(temp, 'recolored/skin.bds')))
  for (const [name, data] of Object.entries(files)) if (name !== 'res/panel.png') assert.deepEqual(after[name], data, name)
  assert.notDeepEqual(after['res/panel.png'], files['res/panel.png'])
})

test('already compiled effects package is explicitly rejected', async () => {
  await assert.rejects(compileEffects(result.bytes, preset), /fresh base/)
})
