// Integration with KeySkin's real archive/layout/router modules, not Android IME.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { SkinArchive } from '../../src/skin.ts'
import { IniDocument } from '../../src/ini.ts'
import { resolvePanelConfig } from '../../src/keyboard.ts'
import { listCellRect } from '../../src/layout.ts'
import { previewPageTransition } from '../../src/actions.ts'

const root = fileURLToPath(new URL('../../', import.meta.url))
const temp = mkdtempSync(join(tmpdir(), 'keyskin-original-'))
try {
  execFileSync('python', ['scripts/cloud/original_base.py', '--output', join(temp, 'out')], { cwd: root })
  const bytes = readFileSync(join(temp, 'out/original-base-prototype-09.bds'))
  const archive = await SkinArchive.openAsync(bytes, 'bds')
  assert.equal(archive.format, 'bds')
  const styles = IniDocument.parse(archive.getText('light/skin/res/default.css'))
  let layouts = 0
  for (const orient of ['port', 'land']) {
    const prefix = `light/skin/${orient}/`
    const gen = IniDocument.parse(archive.getText(prefix + 'gen.ini'))
    const names = archive.names().filter(n => n.startsWith(prefix) && n.endsWith('.ini')).map(n => n.slice(prefix.length))
    for (const name of names.filter(n => n !== 'gen.ini')) {
      const doc = IniDocument.parse(archive.getText(prefix + name))
      const config = resolvePanelConfig(doc, gen, styles)
      assert.equal(config.width, orient === 'port' ? 1080 : 1920)
      assert.equal(config.height, orient === 'port' ? 624 : 480)
      if (['py_9.ini', 'def_9.ini', 'en_9.ini', 'en_9s.ini'].includes(name)) {
        assert.ok(listCellRect(doc, 'LIST'))
        assert.equal(doc.get('KEY2', 'SHOW'), '2')
        assert.equal(doc.get('KEY2', 'CENTER'), 'b')
      }
      layouts++
    }
    for (const base of ['py_9.ini', 'py_26.ini']) {
      const suffix = base.includes('26') ? '26' : '9'
      for (const [action, expected] of [['F16', `en_${suffix}.ini`], ['F6', `num_${suffix}.ini`], ['F1', 'symbol.ini'], ['Z+tools', 'tools.ini']]) {
        const transition = previewPageTransition(action, base, base, names)
        assert.equal(transition.target, expected)
        assert.equal(previewPageTransition('F4', expected, transition.returnName, names).target, base)
      }
    }
  }
  const reopened = await SkinArchive.openAsync(archive.toBytes('bds'), 'bds')
  for (const name of archive.names()) assert.deepEqual(reopened.getBytes(name), archive.getBytes(name), name)
  console.log(JSON.stringify({ passed: true, layouts, checks: ['KeySkin archive import/export', 'panel sizing', 'LIST geometry', 'preview page routing'], androidIMEVerified: false }, null, 2))
} finally {
  rmSync(temp, { recursive: true, force: true })
}
