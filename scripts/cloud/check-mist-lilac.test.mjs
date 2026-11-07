import assert from 'node:assert/strict'
import test, { after } from 'node:test'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { unzipSync, strFromU8 } from 'fflate'
import { SkinArchive } from '../../src/skin.ts'
import { IniDocument } from '../../src/ini.ts'
const root=fileURLToPath(new URL('../../',import.meta.url))
const temp=mkdtempSync(join(tmpdir(),'mist-lilac-'))
after(()=>rmSync(temp,{recursive:true,force:true}))
execFileSync('node',['scripts/cloud/build-mist-lilac.mjs','--output',join(temp,'out')],{cwd:root})
const bytes=readFileSync(join(temp,'out/mist-lilac.bds'))
const files=unzipSync(bytes)
test('actual demo packages artwork, pressed states, motion and three Ogg sounds',async()=>{
  assert.equal(Object.keys(files).filter(n=>n.endsWith('.png')).length,3)
  assert.equal(Object.keys(files).filter(n=>n.endsWith('.ogg')).length,3)
  assert.match(strFromU8(files['Info.txt']),/Name=雾紫轻触10/)
  assert.match(strFromU8(files['res/anim.ini']),/ANIM_NUM=2/)
  const styles=IniDocument.parse(strFromU8(files['res/default.css']))
  assert.equal(styles.get('STYLE2','NM_IMG'),'keys,1')
  assert.equal(styles.get('STYLE2','HL_IMG'),'keys,2')
  const archive=await SkinArchive.openAsync(bytes,'bds')
  assert.ok(archive.getBytes('light/skin/res/icons.png'))
  const layout=IniDocument.parse(archive.getText('light/skin/port/py_9.ini'))
  assert.equal(layout.get('KEY2','SHOW'),'2');assert.equal(layout.get('KEY2','CENTER'),'b')
  assert.ok(layout.get('KEY2','ANIM_STYLE'));assert.ok(layout.get('KEY2','SOUND_STYLE'))
})
test('build refuses to overwrite an earlier demo',()=>{
  assert.throws(()=>execFileSync('node',['scripts/cloud/build-mist-lilac.mjs','--output',join(temp,'out')],{cwd:root,stdio:'pipe'}))
})
test('real KeySkin renderer outputs repeatable normal and pressed panel previews',()=>{
  const a=join(temp,'preview-a'),b=join(temp,'preview-b')
  for(const output of [a,b]) execFileSync('node',['scripts/cloud/render-demo.mjs',join(temp,'out/mist-lilac.bds'),output],{cwd:root})
  const report=JSON.parse(readFileSync(join(a,'render-report.json'),'utf8'))
  assert.equal(report.images.length,4)
  assert.equal(report.androidIMEVerified,false)
  for(const image of report.images){
    assert.equal(image.width,1080);assert.equal(image.height,624)
    assert.deepEqual(readFileSync(join(a,image.file)),readFileSync(join(b,image.file)))
  }
  for(const layout of ['py_26','py_9']) assert.notDeepEqual(readFileSync(join(a,`light-${layout}.png`)),readFileSync(join(a,`light-${layout}-pressed.png`)))
})
