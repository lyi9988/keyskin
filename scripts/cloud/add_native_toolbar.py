"""Add the Android native idle toolbar without touching keyboard input layouts."""
import argparse, io, json, zipfile, hashlib
from pathlib import Path
from PIL import Image,ImageDraw
from original_base import ini
from base_validation import parse
from mist_lilac import icons,png


def build(base,out):
    out.mkdir(parents=True,exist_ok=False)
    z=zipfile.ZipFile(base); original={n:z.read(n) for n in z.namelist()};files=dict(original)
    css=parse(files['res/default.css']); first=max(int(s[5:]) for s in css if s.startswith('STYLE'))+1
    art,tiles,ids=icons()
    for i,name in enumerate(['Menu','Hide','More']):
        css[f'STYLE{first+i}']={'NM_IMG':f'icons,{ids[name]}','HL_IMG':f'icons,{ids[name]}'}
    css[f'STYLE{first+3}']={'NM_COLOR':'EDE7F5','HL_COLOR':'EDE7F5'}
    css['GLOBAL']['STYLE_NUM']=first+4;files['res/default.css']=ini(css)
    # Native bitmap indexes, not action codes; missing indexes fall back to client assets.
    atlas=Image.new('RGBA',(64*7,64)); mapping=[(26,'Emoji'),(27,'Keyboard'),(29,'Mic'),(31,'Search'),(25,'Edit'),(50,'Clipboard'),(67,'Hide')]
    til={'GLOBAL':{'USE_ALPHA':1,'TILE_NUM':68}}
    for x,(index,name) in enumerate(mapping):
        if name in ids:
            sx=(ids[name]-1)*64; tile=art.crop((sx,0,sx+64,64))
        else:
            tile=Image.new('RGBA',(64,64));d=ImageDraw.Draw(tile);c='#3e325b'
            if name=='Keyboard':
                d.rounded_rectangle((9,17,55,48),5,outline=c,width=3)
                for y in [25,33]:
                    for xx in [18,27,36,45]:d.rectangle((xx,y,xx+2,y+2),fill=c)
                d.line((23,41,42,41),fill=c,width=3)
            elif name=='Mic':
                d.rounded_rectangle((25,10,39,38),7,outline=c,width=3);d.arc((18,22,46,47),0,180,fill=c,width=3);d.line((32,47,32,54),fill=c,width=3)
            elif name=='Search':
                d.ellipse((13,12,41,40),outline=c,width=3);d.line((38,38,52,52),fill=c,width=4)
            elif name=='Edit':
                d.line((17,46,44,19,49,24,22,51,16,52,17,46),fill=c,width=3)
        atlas.alpha_composite(tile,(x*64,0));til[f'IMG{index}']={'SOURCE_RECT':f'{x*64},0,64,64'}
    files['res/logo/pop_menu_icons.png']=png(atlas);files['res/logo/pop_menu_icons.til']=ini(til)
    for orient in ['port','land']:
        gp=f'{orient}/gen.ini';gen=parse(files[gp]);w,h=map(int,gen['CAND']['VIEW_RECT'].split(',')[2:]);side=round(w/7)
        gen['LOGO']={'LAYOUT_NAME':'logo'};files[gp]=ini(gen)
        files[f'{orient}/logo.ini']=ini({'GLOBAL':{'ICON_NUM':1,'VERSION':1},'PANEL':{'BACK_STYLE':first+3,'ICON_INDEX':1},'ICON1':{'FORE_STYLE':4,'TEXT_STYLE':4}})
        cand=parse(files[f'{orient}/cand.cnd']);cand={s:v for s,v in cand.items() if not s.startswith('ICON')}
        cand['CAND'].update(ICON_NUM=4,PADDING=f'12,0,{side},0',BACK_STYLE=first+3)
        cand['TAB'].update(PADDING=f'12,0,{side},0',BACK_STYLE=first+3)
        for i,(action,persist,x,width,fore) in enumerate([('F31',1,0,side,first),('F14',1,side,w-2*side,None),('F8',1,w-side,side,first+1),('F9',2,w-side,side,first+2)],1):
            cand[f'ICON{i}']={'SIZE':f'{width},{h}','POS':f'{x},0','ANCHOR_TYPE':1,'KEY':action,'PERSIST':persist}
            if action=='F14':cand[f'ICON{i}'].update(ANCHOR_TYPE=5,POS=f'{-width//2},{-h//2}')
            elif action in ('F8','F9'):cand[f'ICON{i}'].update(ANCHOR_TYPE=3,POS=f'{-width},0')
            if fore is not None:cand[f'ICON{i}']['FORE_STYLE']=fore
        files[f'{orient}/cand.cnd']=ini(cand)
    files['Info.txt']=files['Info.txt'].replace('雾紫星星12'.encode(),'雾紫星星13'.encode())
    allowed={'Info.txt','res/default.css','port/gen.ini','land/gen.ini','port/cand.cnd','land/cand.cnd'}
    for n,b in original.items():
        if n not in allowed:assert files[n]==b,n
    target=out/'mist-star-toolbar-13.bds'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in files.items():
            info=zipfile.ZipInfo(n,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
    report={'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'input_layouts_byte_identical':True,'idle':['F31 menu','F14 native functions','F8 hide'],'composing':['F9 expand candidates'],'native_function_order':'controlled by Baidu client, not forced by skin','device_toolbar_verified':False}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.base,a.output)
