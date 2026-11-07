// Original deterministic effect parameters + synthesized audio; no donor assets.
// Uses KeySkin's AGPL archive/sound/animation implementation, preserving its license.
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { unzipSync, zipSync, strToU8, strFromU8 } from 'fflate'
import { IniDocument } from '../../src/ini.ts'
import { adaptPackageSounds, soundAsWav, soundFilenameForKey } from '../../src/sounds.ts'
import { decodeWav } from '../../src/wav.ts'
import { parseLegacyAnimationFile } from '../../src/legacy-animation.ts'
import { readAnimationBinding } from '../../src/legacy-animation-binding.ts'

export function validatePreset(preset) {
  assert.deepEqual(Object.keys(preset).sort(), ['press_scale_percent', 'press_duration_ms', 'release_duration_ms', 'sound_peak_limit', 'sound_duration_ms', 'frequencies_hz'].sort(), 'Unknown or missing preset field')
  for (const [key, low, high] of [['press_scale_percent', 90, 100], ['press_duration_ms', 20, 180], ['release_duration_ms', 20, 180], ['sound_peak_limit', 0, .15], ['sound_duration_ms', 20, 100]]) {
    assert.ok(Number.isFinite(preset[key]) && preset[key] >= low && preset[key] <= high, `${key} outside budget`)
  }
  assert.deepEqual(Object.keys(preset.frequencies_hz).sort(), ['delete', 'space', 'tap'])
  for (const value of Object.values(preset.frequencies_hz)) assert.ok(Number.isFinite(value) && value >= 200 && value <= 2400, 'Pitch outside budget')
}

function synthesizeWav(frequency, preset) {
  const rate = 22050, frames = Math.round(rate * preset.sound_duration_ms / 1000)
  const bytes = Buffer.alloc(44 + frames * 2)
  bytes.write('RIFF', 0); bytes.writeUInt32LE(bytes.length - 8, 4); bytes.write('WAVEfmt ', 8)
  bytes.writeUInt32LE(16, 16); bytes.writeUInt16LE(1, 20); bytes.writeUInt16LE(1, 22)
  bytes.writeUInt32LE(rate, 24); bytes.writeUInt32LE(rate * 2, 28); bytes.writeUInt16LE(2, 32)
  bytes.writeUInt16LE(16, 34); bytes.write('data', 36); bytes.writeUInt32LE(frames * 2, 40)
  for (let i = 0; i < frames; i++) {
    const t = i / rate, phase = i / (frames - 1)
    const envelope = Math.sin(Math.PI * phase) ** 2 * Math.exp(-3 * phase)
    const wave = (Math.sin(2 * Math.PI * frequency * t) + .3 * Math.sin(2 * Math.PI * frequency * 2.1 * t)) / 1.3
    bytes.writeInt16LE(Math.round(preset.sound_peak_limit * envelope * wave * 32767), 44 + i * 2)
  }
  return new Uint8Array(bytes)
}

const hash = bytes => createHash('sha256').update(bytes).digest('hex')
const writeIni = doc => strToU8(doc.toString().replace(/\r?\n/g, '\r\n'))
const fields = data => IniDocument.parse(strFromU8(data)).entries().map(({ section, key, value }) => ({ section, key, value }))

export async function compileEffects(baseBytes, preset) {
  validatePreset(preset)
  const original = unzipSync(baseBytes), files = new Map(Object.entries(original))
  assert.ok(original['res/default.css'] && original['port/py_9.ini'], 'Expected original Android base')
  assert.ok(!Object.keys(original).some(path => path.endsWith('/anim.ini')), 'Effects compiler requires a fresh base without animation files')
  assert.ok(!Object.entries(original).some(([path, data]) => path.endsWith('.ini') && /^(?:ANIM_STYLE|BACK_ANIM_STYLE|FORE_ANIM_STYLE|SOUND_STYLE)=/m.test(strFromU8(data))), 'Effects compiler requires a fresh base without existing effect bindings')
  const styles = IniDocument.parse(strFromU8(original['res/default.css']))
  const first = Math.max(...styles.sections().filter(s => /^STYLE\d+$/.test(s)).map(s => Number(s.slice(5)))) + 1
  const animationStyle = first, soundStyles = { tap: first + 1, space: first + 2, delete: first + 3 }
  styles.appendSection(`STYLE${animationStyle}`, [{ key: 'PRESS_ANIM', value: '1' }, { key: 'RELEASE_ANIM', value: '2' }])
  const masters = {}
  for (const [name, id] of Object.entries(soundStyles)) {
    styles.appendSection(`STYLE${id}`, [{ key: 'PRESS_SOUND_PATH', value: `original-${name}.wav` }])
    masters[name] = synthesizeWav(preset.frequencies_hz[name], preset)
    files.set(`res/original-${name}.wav`, masters[name])
  }
  styles.set('GLOBAL', 'STYLE_NUM', String(first + 4))
  files.set('res/default.css', writeIni(styles))
  const animation = IniDocument.parse('[GLOBAL]\r\nANIM_NUM=2\r\n')
  for (const [id, from, to, duration, remove] of [
    [1, 100, preset.press_scale_percent, preset.press_duration_ms, 0],
    [2, preset.press_scale_percent, 100, preset.release_duration_ms, 1],
  ]) {
    animation.appendSection(`ANIM${id}`, Object.entries({ CATEGORY: 0, TYPE: 4, FROM: `${from},${from}`, TO: `${to},${to}`, PIVOT: '50,50', DURATION: duration, DELAY: 0, INTPOL: 2, REPEAT_CNT: 1, REPEAT_MODE: 0, REMOVE: remove }).map(([key, value]) => ({ key, value: String(value) })))
  }
  files.set('res/anim.ini', writeIni(animation))
  let boundKeys = 0
  for (const [path, bytes] of [...files]) {
    if (!/^(port|land)\/[^/]+\.ini$/.test(path)) continue
    const layout = IniDocument.parse(strFromU8(bytes))
    for (const section of layout.sections().filter(s => /^KEY\d+$/.test(s))) {
      const action = layout.get(section, 'CENTER')
      if (action === 'F55') continue // Native candidate grid is not a decorative key.
      layout.set(section, 'ANIM_STYLE', String(animationStyle))
      layout.set(section, 'SOUND_STYLE', String(soundStyles[action === 'F36' ? 'delete' : action === 'F38' ? 'space' : 'tap']))
      boundKeys++
    }
    files.set(path, writeIni(layout))
  }
  files.set('Info.txt', strToU8(strFromU8(original['Info.txt']).replace('Prototype 09', 'Full Prototype 09') + 'Abilities=Sound,Animation\r\n'))
  const transcoding = await adaptPackageSounds(files, 'bds')
  assert.deepEqual(transcoding.warnings, [], 'Audio transcode warnings')
  assert.equal(transcoding.converted, 3)
  const finalStyles = IniDocument.parse(strFromU8(files.get('res/default.css')))
  const audio = {}
  for (const name of Object.keys(soundStyles)) {
    const encoded = files.get(`res/original-${name}.ogg`)
    assert.equal(strFromU8(encoded.subarray(0, 4)), 'OggS')
    const decoded = decodeWav(await soundAsWav(encoded))
    const peak = Math.max(...decoded.channelData[0].map(Math.abs))
    assert.ok(decoded.samplesDecoded > 0 && decoded.samplesDecoded / decoded.sampleRate < .15)
    assert.ok(peak <= .16, 'Decoded audio exceeds conservative peak budget')
    audio[name] = { filename: `original-${name}.ogg`, sha256: hash(encoded), duration_ms: decoded.samplesDecoded / decoded.sampleRate * 1000, decoded_peak: peak }
  }
  for (const [path, bytes] of Object.entries(original)) {
    if (/^(port|land)\/[^/]+\.ini$/.test(path)) {
      const after = fields(files.get(path)).filter(e => !['ANIM_STYLE', 'SOUND_STYLE'].includes(e.key))
      assert.deepEqual(after, fields(bytes), `Input/geometry changed in ${path}`)
      const layout = IniDocument.parse(strFromU8(files.get(path)))
      for (const section of layout.sections().filter(s => /^KEY\d+$/.test(s) && layout.get(s, 'CENTER') !== 'F55')) {
        assert.equal(readAnimationBinding(layout, finalStyles, { section, field: 'ANIM_STYLE' }, 'PRESS_ANIM').animation, '1')
        assert.equal(readAnimationBinding(layout, finalStyles, { section, field: 'ANIM_STYLE' }, 'RELEASE_ANIM').animation, '2')
        const sound = soundFilenameForKey(layout, section, finalStyles)
        assert.ok(sound?.endsWith('.ogg') && files.has('res/' + sound), 'Sound binding missing')
      }
    } else if (!['Info.txt', 'res/default.css'].includes(path)) assert.deepEqual(files.get(path), bytes, path)
  }
  // Existing visual styles are unchanged; NM/HL colors remain distinct for both key kinds.
  assert.deepEqual(fields(files.get('res/default.css')).filter(e => !/^STYLE\d+$/.test(e.section) || Number(e.section.slice(5)) < first).filter(e => e.key !== 'STYLE_NUM'), fields(original['res/default.css']).filter(e => e.key !== 'STYLE_NUM'))
  for (const id of [2, 3]) assert.notEqual(finalStyles.get(`STYLE${id}`, 'NM_COLOR'), finalStyles.get(`STYLE${id}`, 'HL_COLOR'))
  const animations = parseLegacyAnimationFile(strFromU8(files.get('res/anim.ini')))
  assert.equal(animations.entries.length, 2)
  assert.ok(animations.entries.every(e => e.kind === 'basic' && e.type === 4))
  const packed = Object.fromEntries([...files].map(([name, data]) => [name, [data, { mtime: new Date('2026-01-01T00:00:00Z') }]]))
  const bytes = zipSync(packed, { level: 9 })
  const roundTrip = unzipSync(bytes)
  for (const [name, data] of files) assert.deepEqual(roundTrip[name], data, name)
  return { bytes, masters, report: { status: 'FULL_EFFECTS_PROTOTYPE_DEVICE_NOT_TESTED', sha256: hash(bytes), base_sha256: hash(baseBytes), node_version: process.version,
    resource_sha256: Object.fromEntries([...files].map(([name, data]) => [name, hash(data)])), bound_keys: boundKeys,
    animation_count: 2, audio, preset,
    checks: ['Original input actions, SHOW, LIST and geometry preserved', 'Normal/pressed colors distinct', 'Press/release animation chains resolve', 'Three original synthesized sounds encode/decode as Ogg Vorbis', 'All per-key sound paths resolve', 'ZIP round-trip'],
    not_verified: ['Actual Android typing', 'Native press/release timing and interruption', 'IME sound switch and volume behavior', 'Actual native visual rendering'],
    unsupported: ['Particle and GIF compilation', 'Arbitrary animation graphs', 'Per-key custom image atlases', 'Custom sound import UI'] } }
}
