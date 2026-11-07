import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {unzipSync,strFromU8} from 'fflate'
import {IniDocument} from '../../src/ini.ts'
import {dynamicToolbarRect,persistVisible} from '../../src/preview-items.ts'
const [before,after]=process.argv.slice(2).map(p=>unzipSync(readFileSync(p)))
for(const [name,bytes] of Object.entries(before)) if(/^(port|land)\/(?!gen\.ini)[^/]+\.ini$/.test(name))assert.deepEqual(after[name],bytes,name)
for(const orient of ['port','land']){
 const doc=p=>IniDocument.parse(strFromU8(after[`${orient}/${p}`]))
 const gen=doc('gen.ini'),cand=doc('cand.cnd'),logo=doc('logo.ini');const [,,w,h]=gen.get('CAND','VIEW_RECT').split(',').map(Number)
 assert.equal(gen.get('LOGO','LAYOUT_NAME'),'logo');assert.equal(logo.get('GLOBAL','VERSION'),'1')
 const visible=composing=>cand.sections().filter(s=>/^ICON\d+$/.test(s)&&persistVisible(cand.get(s,'PERSIST'),composing)).map(s=>cand.get(s,'KEY'))
 assert.deepEqual(visible(false),['F31','F14','F8']);assert.deepEqual(visible(true),['F9'])
 const r=dynamicToolbarRect(cand,w,h);assert.ok(r.x>=0&&r.x+r.width<=w&&r.y===0&&r.height===h)
 const side=Math.round(w/7);assert.equal(r.x,side);assert.equal(cand.get('CAND','PADDING'),`12,0,${side},0`)
}
const til=IniDocument.parse(strFromU8(after['res/logo/pop_menu_icons.til']))
assert.equal(til.get('GLOBAL','TILE_NUM'),'68')
for(const id of [26,27,29,31,25,50,67])assert.ok(til.get(`IMG${id}`,'SOURCE_RECT'))
console.log('PASS: input files unchanged; native F14 geometry, idle/composing visibility and atlas references checked')
