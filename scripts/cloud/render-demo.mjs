/** Actual KeySkin Preview/AtlasResolver rendered on Node Skia Canvas, not Android IME.
 * Setup: npm ci (uses the pinned @napi-rs/canvas development dependency)
 * Usage: node scripts/cloud/render-demo.mjs input.bds output-directory
 * KEYSKIN_CANVAS_MODULE can point to another installed @napi-rs/canvas directory.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, join } from 'node:path'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { SkinArchive } from '../../src/skin.ts'
import { IniDocument } from '../../src/ini.ts'
import { AtlasResolver } from '../../src/atlas.ts'
import { Preview } from '../../src/preview.ts'
import { resolvePanelConfig } from '../../src/keyboard.ts'
// Isolate each still frame so no canvas or resource cache is shared across outputs.
if (!process.env.KEYSKIN_RENDER_CHILD) {
  const target = resolve(process.argv[3] || join(resolve(process.argv[2] || 'artifacts/mist-lilac/mist-lilac.bds'), '..', 'keyskin-preview'))
  if (existsSync(target)) throw new Error(`Output directory already exists: ${target}; choose a fresh directory`)
  const reports = []
  for (const layout of ['py_26', 'py_9']) for (const pressed of ['false', 'true']) {
    const stdout = execFileSync(process.execPath, [fileURLToPath(import.meta.url), ...process.argv.slice(2)], {
      env: { ...process.env, KEYSKIN_RENDER_CHILD: '1', KEYSKIN_LAYOUT: layout, KEYSKIN_PRESSED: pressed }, encoding: 'utf8',
    })
    reports.push(JSON.parse(stdout))
  }
  const report = { ...reports[0], decodedImages: reports.reduce((n, r) => n + r.decodedImages, 0), images: reports.flatMap(r => r.images) }
  const output = resolve(process.argv[3] || join(resolve(process.argv[2] || 'artifacts/mist-lilac/mist-lilac.bds'), '..', 'keyskin-preview'))
  writeFileSync(join(output, 'render-report.json'), JSON.stringify(report, null, 2))
  console.log(JSON.stringify(report, null, 2))
  process.exit(0)
}
const require = createRequire(import.meta.url)
const { createCanvas, loadImage, GlobalFonts } = require(process.env.KEYSKIN_CANVAS_MODULE || '@napi-rs/canvas')
const warnings = []
const fontPath = process.env.KEYSKIN_CJK_FONT || '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if (!existsSync(fontPath) || !GlobalFonts.registerFromPath(fontPath, 'system-ui')) warnings.push(`CJK font unavailable: ${fontPath}; Chinese text may be missing`)
function canvas(width = 1, height = 1) {
  const c = createCanvas(width, height)
  // Snapshot reusable staging canvases to preserve immediate-mode drawImage semantics.
  const ctx = c.getContext('2d')
  const drawImage = ctx.drawImage.bind(ctx)
  const snapshots = []
  ctx.drawImage = (source, ...args) => {
    if (source.getContext) {
      const snapshot = createCanvas(source.width, source.height)
      snapshot.getContext('2d').putImageData(source.getContext('2d').getImageData(0, 0, source.width, source.height), 0, 0)
      snapshots.push(snapshot)
      source = snapshot
    }
    const result = drawImage(source, ...args)
    ctx.getImageData(0, 0, c.width, c.height)
    return result
  }
  c.dataset = {}; c.style = {}; c.addEventListener = () => {}
  c.getBoundingClientRect = () => ({ width: c.width, height: c.height, left: 0, top: 0 })
  return c
}
globalThis.window = globalThis
globalThis.devicePixelRatio = 1
globalThis.requestAnimationFrame = () => 0
globalThis.cancelAnimationFrame = () => {}
globalThis.ResizeObserver = class { observe() {} disconnect() {} }
globalThis.document = { createElement: (tag) => { if(tag !== 'canvas') throw new Error(`Unexpected DOM ${tag}`); return canvas() }, fonts: { add() {} } }
globalThis.FontFace = class { constructor(family, data) { this.family = family; this.data = data } async load() { if (!GlobalFonts.register(Buffer.from(this.data), this.family)) throw new Error('Font registration failed'); return this } }
let decodedImages = 0
globalThis.createImageBitmap = async (blob) => { const image = await loadImage(Buffer.from(await blob.arrayBuffer())); decodedImages++; return image }
class OfflinePreview extends Preview { draw() {} }
const input = resolve(process.argv[2] || 'artifacts/mist-lilac/mist-lilac.bds')
const output = resolve(process.argv[3] || join(input, '..', 'keyskin-preview'))
mkdirSync(output, { recursive: true })
const bytes = readFileSync(input)
const archive = await SkinArchive.openAsync(bytes, 'bds')
const reports = []
for (const theme of ['light', 'dark']) {
  const prefix = `${theme}/skin/port/`
  if (!archive.getBytes(prefix + 'gen.ini')) continue
  const doc = (path) => IniDocument.parse(archive.getText(path))
  const gen = doc(prefix + 'gen.ini')
  const styles = doc(`${theme}/skin/res/default.css`)
  for (const layout of ['py_26', 'py_9']) {
    if (process.env.KEYSKIN_LAYOUT && process.env.KEYSKIN_LAYOUT !== layout) continue
    const ini = doc(prefix + layout + '.ini')
    const config = resolvePanelConfig(ini, gen, styles)
    const c = canvas(config.width, config.height)
    const preview = new OfflinePreview(c, () => {}, () => {})
    preview.mode = 'preview'
    preview.theme = theme
    preview.resolver = new AtlasResolver(archive, theme, 'port')
    preview.setDefaults(gen)
    preview.setPanel(config.styleID, config.width, config.height)
    preview.setDocument(ini)
    preview.setOffsets(gen)
    for (const pressed of [false, true]) {
      if (process.env.KEYSKIN_PRESSED && process.env.KEYSKIN_PRESSED !== String(pressed)) continue
      const key = preview.keys.find(k => k.center.toLowerCase() === 'a') || preview.keys.find(k => /^KEY\d+$/.test(k.section))
      preview.active = pressed && key ? { key, direction: 'center' } : undefined
      await preview.render()
      if (preview.lastDrawnID !== preview.drawID) throw new Error('Renderer did not complete')
      const name = `${theme}-${layout}${pressed ? '-pressed' : ''}.png`
      writeFileSync(join(output, name), c.toBuffer('image/png'), { flag: 'wx' })
      reports.push({ file: name, width: c.width, height: c.height, keys: preview.keys.length, pressedKey: pressed ? key?.section : null })
    }
  }
}
const report = { source: input, sha256: createHash('sha256').update(bytes).digest('hex'), renderer: 'Unmodified KeySkin Preview.render / paintPreview + AtlasResolver, @napi-rs/canvas Node adapter', androidIMEVerified: false, browserScreenshot: false, decodedImages, warnings, limitations: ['Node Skia canvas rasterization and installed font fallback can differ from WebKit/Android', 'Pressed state uses actual highlight styles; static image does not verify touch handling or animation playback'], images: reports }
console.log(JSON.stringify(report, null, 2))
