import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { unzipSync,strFromU8 } from 'fflate'
import { IniDocument } from '../../src/ini.ts'
import { parseLegacyAnimationFile } from '../../src/legacy-animation.ts'
import { readAnimationBinding } from '../../src/legacy-animation-binding.ts'
const [base,target]=process.argv.slice(2).map(p=>unzipSync(readFileSync(p)))
const doc=p=>IniDocument.parse(strFromU8(target[p]))
const styles=doc('res/default.css'), anim=doc('res/anim.ini')
assert.equal(parseLegacyAnimationFile(strFromU8(target['res/anim.ini'])).entries.length,3)
assert.equal(anim.get('ANIM3','CATEGORY'),'2')
assert.equal(anim.get('ANIM3','ANIM_PATH'),'star-pop.gif')
assert.equal(strFromU8(target['res/star-pop.gif'].subarray(0,6)),'GIF89a')
let n=0
for(const path of Object.keys(base)){
 if(!/^(port|land)\/.*\.ini$/.test(path))continue
 assert.deepEqual(target[path],base[path],path)
 const layout=doc(path)
 for(const section of layout.sections().filter(s=>/^KEY\d+$/.test(s)&&layout.get(s,'CENTER')!=='F55')){
  assert.equal(readAnimationBinding(layout,styles,{section,field:'ANIM_STYLE'},'PRESS_ANIM').animation,'3'); n++
 }
}
assert.equal(n,580)
console.log(`PASS: ${n} native press bindings resolve to packaged GIF; all layout bytes preserved`)
