import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {unzipSync,strFromU8} from 'fflate'
import {IniDocument} from '../../src/ini.ts'
const [before,after]=process.argv.slice(2).map(p=>unzipSync(readFileSync(p)))
const parse=b=>IniDocument.parse(strFromU8(b))
let count=0
for(const [name,b]of Object.entries(before)){
 if(!/^(port|land)\/py_9.ini$/.test(name)){
  if(!['Info.txt','res/default.css'].includes(name))assert.deepEqual(after[name],b,name)
  continue
 }
 const old=parse(b),next=parse(after[name]);const n=Number(old.get('PANEL','KEY_NUM'))+1
 assert.equal(next.get('PANEL','KEY_NUM'),String(n));assert.equal(next.get(`KEY${n}`,'CENTER'),'F40')
 assert.equal(next.get(`KEY${n}`,'LEFT'),undefined);assert.equal(next.get(`KEY${n}`,'HOLD'),undefined)
 for(const section of old.sections())if(section!=='PANEL')assert.deepEqual(next.entries(section),old.entries(section),`${name}/${section}`)
 const style=parse(after['res/default.css']);assert.equal(style.get('STYLE'+next.get(`KEY${n}`,'FORE_STYLE'),'SHOW'),'清空');count++
}
assert.equal(count,2)
console.log('PASS: two nine-key panels gain only F40; all existing keys and other files preserved')
