"""Add a visible preedit-only clear key in the nine-key panel's unused bottom-left cell."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
from base_validation import parse,overlap
from original_base import ini


def build(base,out):
    out.mkdir(parents=True,exist_ok=False)
    z=zipfile.ZipFile(base);before={n:z.read(n) for n in z.namelist()};files=dict(before)
    css=parse(files['res/default.css']);sid=max(int(n[5:]) for n in css if re.fullmatch('STYLE[0-9]+',n))+1
    css[f'STYLE{sid}']={'SHOW':'清空','FONT_SIZE':38,'NM_COLOR':'67508F','HL_COLOR':'3E325B'}
    css['GLOBAL']['STYLE_NUM']=sid+1;files['res/default.css']=ini(css)
    changed=[]
    for name,data in before.items():
        if not re.fullmatch(r'(port|land)/py_9.ini',name):continue
        doc=parse(data);w,h=map(int,doc['PANEL']['SIZE'].split(','));rect=[8,round(h*3/4)+8,round(w/5)-16,h-round(h*3/4)-16]
        for section,key in doc.items():
            if re.fullmatch('KEY[0-9]+',section):assert not overlap(rect,tuple(map(int,key['VIEW_RECT'].split(',')))),section
        listing=doc['LIST'];x,y=map(int,listing['POS'].split(','));cw,ch=map(int,listing['CELL_SIZE'].split(','));assert not overlap(rect,(x,y,cw,ch*int(listing['LIST_NUM'])))
        n=int(doc['PANEL']['KEY_NUM'])+1;doc['PANEL']['KEY_NUM']=str(n)
        doc[f'KEY{n}']={'BACK_STYLE':'3','FORE_STYLE':str(sid),'VIEW_RECT':','.join(map(str,rect)),'CENTER':'F40','SOUND_STYLE':doc['KEY11']['SOUND_STYLE']}
        # Deliberately no star animation on cancellation; no change to existing keys.
        old=parse(data)
        for section,values in old.items():
            if section!='PANEL':assert doc[section]==values
        files[name]=ini(doc);changed.append(name)
    assert len(changed)==2
    files['Info.txt']=files['Info.txt'].replace('雾紫星星13'.encode(),'雾紫星星14'.encode())
    for name,data in before.items():
        if name not in changed+['Info.txt','res/default.css']:assert files[name]==data
    target=out/'mist-star-clear-14.bds'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():
            i=zipfile.ZipInfo(name,(2026,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,data)
    report={'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'changed_layouts':changed,'action':'F40 clear input code; not F48 clear field','position':'bottom-left unused cell below punctuation list','existing_keys_unchanged':True,'device_clear_verified':False}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.base,a.output)
