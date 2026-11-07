import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {unzipSync,strFromU8} from 'fflate'
import {IniDocument} from '../../src/ini.ts'
import {parseLegacyAnimationFile} from '../../src/legacy-animation.ts'
import {iniPreviewClip} from '../../src/animation-preview-model.ts'
import {previewItems,keyAnimationStyles} from '../../src/preview-items.ts'
const [base,after]=process.argv.slice(2).map(p=>unzipSync(readFileSync(p)))
const parse=b=>IniDocument.parse(strFromU8(b));const styles=parse(after['res/default.css']),anim=parse(after['res/anim.ini'])
assert.equal(parseLegacyAnimationFile(strFromU8(after['res/anim.ini'])).entries.length,7)
assert.equal(iniPreviewClip(anim,'ANIM4').tracks.length,2);assert.equal(iniPreviewClip(anim,'ANIM7').tracks.length,2)
assert.equal(iniPreviewClip(anim,'ANIM3').images[0].file,'glass-ripple.gif')
assert.equal(strFromU8(after['res/glass-ripple.gif'].subarray(0,6)),'GIF89a')
let count=0
for(const [name,data] of Object.entries(base)){
 if(/\.(cnd|pop)$/.test(name) || /^res\/original-.*\.ogg$/.test(name))assert.deepEqual(after[name],data,name)
 if(!/^(port|land)\/[^/]+\.ini$/.test(name))continue
 const old=parse(data),next=parse(after[name])
 assert.deepEqual(next.entries().filter(e=>e.key!=='PRESS_STYLE'),old.entries(),name)
 for(const key of previewItems(next))if(key.animStyle==='206'){
  assert.ok(key.pressStyle);assert.ok(keyAnimationStyles(key).includes(key.pressStyle));assert.equal(styles.get('STYLE'+key.pressStyle,'PRESS_ANIM'),'3');count++
 }
}
assert.equal(count,580)
console.log('PASS: 580 ripple slots, native transform graphs, unchanged typing/clear/toolbar configuration and original sounds')
