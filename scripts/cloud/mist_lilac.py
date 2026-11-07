#!/usr/bin/env python3
"""Compile original Mist Lilac artwork and keycap atlases over the original base."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from PIL import Image, ImageDraw, ImageFilter
from original_base import Base, ini
from base_validation import parse, validate_files

S = 3


def png(image):
    out = io.BytesIO()
    image.save(out, format='PNG')
    return out.getvalue()


def panel():
    image = Image.new('RGB', (1080, 624))
    pixels = image.load()
    for y in range(624):
        for x in range(1080):
            t = y / 623
            warm = math.exp(-((x - 120) ** 2 + (y + 80) ** 2) / 280000)
            cool = math.exp(-((x - 1000) ** 2 + (y - 620) ** 2) / 160000)
            pixels[x, y] = (round(226 - 23 * t + 20 * warm - 4 * cool),
                            round(222 - 15 * t + 16 * warm + 5 * cool),
                            round(243 - 12 * t + 9 * warm + 10 * cool))
    return image


def keycap(fill, pressed=False):
    image = Image.new('RGBA', (128 * S, 128 * S))
    shadow = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(shadow)
    shift = 3 if pressed else 0
    draw.rounded_rectangle((6*S, (9+shift)*S, 122*S, (122+shift)*S), 19*S,
                           fill=(83, 68, 120, 22 if pressed else 52))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(2*S)))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((6*S, (5+shift)*S, 122*S, (118+shift)*S), 19*S,
                           fill=fill, outline=(255, 255, 255, 190 if not pressed else 65), width=S)
    return image.resize((128, 128), Image.Resampling.LANCZOS)


def icons():
    names = ['Del', 'Enter', 'Shift', 'CAPS', 'Emoji', 'Menu', 'More', 'Back',
             'Left', 'Right', 'Copy', 'Paste', 'All', 'Undo', 'Clipboard', 'Hide']
    atlas = Image.new('RGBA', (64 * len(names), 64))
    for index, name in enumerate(names):
        image = Image.new('RGBA', (64*S, 64*S))
        d = ImageDraw.Draw(image)
        color = (255, 255, 255, 255) if name == 'Enter' else (62, 50, 91, 255)
        def line(points, width=3):
            d.line([(round(x*S), round(y*S)) for x,y in points], fill=color, width=round(width*S), joint='curve')
        def box(bounds, radius=4):
            d.rounded_rectangle(tuple(round(v*S) for v in bounds), radius*S, outline=color, width=3*S)
        if name == 'Del':
            line([(26,17),(53,17),(53,47),(26,47),(11,32),(26,17)])
            line([(33,25),(44,39)]); line([(44,25),(33,39)])
        elif name == 'Enter':
            line([(49,18),(49,33),(17,33)]); line([(27,23),(16,33),(27,43)])
        elif name in ('Shift','CAPS'):
            line([(14,31),(32,14),(50,31),(40,31),(40,47),(24,47),(24,31),(14,31)])
            if name == 'CAPS': line([(24,54),(40,54)])
        elif name == 'Emoji':
            d.ellipse((12*S,12*S,52*S,52*S),outline=color,width=3*S)
            d.ellipse((22*S,24*S,26*S,28*S),fill=color);d.ellipse((38*S,24*S,42*S,28*S),fill=color)
            d.arc((22*S,29*S,42*S,43*S),0,180,fill=color,width=3*S)
        elif name == 'Menu':
            for x in (17,32,47):d.ellipse(((x-3)*S,29*S,(x+3)*S,35*S),fill=color)
        elif name in ('More','Hide'):
            line([(18,25),(32,39),(46,25)])
            if name == 'Hide':line([(18,47),(46,47)])
        elif name in ('Back','Left'):
            line([(38,17),(23,32),(38,47)])
            if name == 'Back':line([(23,32),(52,32)])
        elif name == 'Right':line([(25,17),(40,32),(25,47)])
        elif name == 'Copy':box((24,23,50,51));line([(40,16),(15,16),(15,42)])
        elif name in ('Paste','Clipboard'):
            box((17,17,47,53));box((24,11,40,22),3);line([(25,32),(39,32)],2);line([(25,40),(39,40)],2)
        elif name == 'All':
            for points in [[(23,14),(14,14),(14,23)],[(41,14),(50,14),(50,23)],[(14,41),(14,50),(23,50)],[(41,50),(50,50),(50,41)]]:line(points)
            line([(25,32),(39,32)])
        elif name == 'Undo':
            d.arc((16*S,19*S,51*S,51*S),180,490,fill=color,width=3*S)
            line([(12,15),(16,35),(31,28)])
        atlas.alpha_composite(image.resize((64,64),Image.Resampling.LANCZOS),(64*index,0))
    tiles={'GLOBAL':{'USE_ALPHA':1,'TILE_NUM':len(names)}}
    tiles.update({f'IMG{i+1}':{'SOURCE_RECT':f'{i*64},0,64,64'} for i in range(len(names))})
    return atlas,tiles,{name:i+1 for i,name in enumerate(names)}


def themed_files():
    files = Base().generate()
    validate_files(files)
    original = dict(files)
    files['res/panel.png'] = png(panel())
    atlas = Image.new('RGBA',(768,128))
    colors = [(255,254,255,248),(226,215,249,255),(220,212,239,250),
              (196,181,225,255),(142,118,200,255),(112,87,173,255)]
    for i,color in enumerate(colors):atlas.alpha_composite(keycap(color,i%2==1),(i*128,0))
    tiles={'GLOBAL':{'USE_ALPHA':1,'TILE_NUM':6}}
    for i in range(6):tiles[f'IMG{i+1}']={'SOURCE_RECT':f'{i*128},0,128,128','INNER_RECT':f'{i*128+32},32,64,64','SCALE':'1,1,1,1,1'}
    files['res/keys.png'],files['res/keys.til']=png(atlas),ini(tiles)
    icon_image,icon_tiles,icon_ids=icons()
    files['res/icons.png'],files['res/icons.til']=png(icon_image),ini(icon_tiles)
    styles=parse(files['res/default.css'])
    accent=max(int(name[5:]) for name in styles if re.fullmatch(r'STYLE\d+',name))+1
    styles['GLOBAL']['STYLE_NUM']=str(accent+1)
    for style,tile in [('STYLE2',1),('STYLE3',3),(f'STYLE{accent}',5)]:
        styles[style]={'NM_IMG':f'keys,{tile}','HL_IMG':f'keys,{tile+1}'}
    replacements={'EN':'英','CN':'中','SYM':'符','Space':'空格','Predict':'联想','Prev':'上页','Next':'下页'}
    for name,style in styles.items():
        if not name.startswith('STYLE'):continue
        if 'SHOW' in style:
            label=style['SHOW']
            if label in icon_ids:
                styles[name]={'NM_IMG':f'icons,{icon_ids[label]}','HL_IMG':f'icons,{icon_ids[label]}'}
                continue
            style['SHOW']=replacements.get(label,label)
            style['FONT_SIZE']='40' if len(style['SHOW'])<=3 else '32'
        if 'NM_COLOR' in style:style['NM_COLOR']='3E325B'
        if 'HL_COLOR' in style:style['HL_COLOR']='67508F'
    files['res/default.css']=ini(styles)
    changed_layouts=[]
    for path,data in list(files.items()):
        if not re.fullmatch(r'(port|land)/[^/]+\.ini',path):continue
        config=parse(data)
        if 'LIST' in config:config['LIST']['BACK_STYLE']='0'
        for section,key in config.items():
            if not re.fullmatch(r'KEY\d+',section):continue
            if key.get('CENTER')=='F39':key['BACK_STYLE']=str(accent)
            elif key.get('CENTER')=='F38':key['BACK_STYLE']='2'
        files[path]=ini(config);changed_layouts.append(path)
        before=parse(original[path])
        for section,values in before.items():
            assert {k:v for k,v in config[section].items() if k!='BACK_STYLE'} == {k:v for k,v in values.items() if k!='BACK_STYLE'},(path,section)
    files['Info.txt']=files['Info.txt'].replace(b'Name=KeySkin Original Base Prototype 09','Name=雾紫轻触10'.encode()).replace(b'VersionCode=9',b'VersionCode=10')
    # Verify every PNG/TIL/style reference and slice geometry in the actual package.
    for path,data in files.items():
        if not path.endswith('.til'):continue
        til=parse(data);image=Image.open(io.BytesIO(files[path[:-4]+'.png']))
        slices=[s for s in til if re.fullmatch(r'IMG\d+',s)]
        assert len(slices)==int(til['GLOBAL']['TILE_NUM'])
        for section in slices:
            x,y,w,h=map(int,til[section]['SOURCE_RECT'].split(','));assert x>=0 and y>=0 and x+w<=image.width and y+h<=image.height
            if 'INNER_RECT' in til[section]:
                a,b,c,d=map(int,til[section]['INNER_RECT'].split(','));assert x<=a<a+c<=x+w and y<=b<b+d<=y+h
    for style in styles.values():
        for field in ('NM_IMG','HL_IMG'):
            if field in style:
                resource,tile=style[field].split(',');assert f'res/{resource}.png' in files
                assert f'IMG{tile}' in parse(files[f'res/{resource}.til'])
    return files,{'theme':'雾紫轻触10','source':'All bitmap artwork compiled from original geometry and palette; no donor assets or embedded fonts.',
                  'image_files':3,'keycap_slices':6,'icon_slices':len(icon_ids),'layout_actions_preserved':True,
                  'device_verified':False,'changed_layout_count':len(changed_layouts)}


def build(output):
    if output.exists():raise ValueError('Output directory already exists')
    files,report=themed_files()
    output.parent.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='.mist-lilac-',dir=output.parent))
    try:
        target=work/'themed-base.bds'
        with ZipFile(target,'w',ZIP_DEFLATED) as z:
            for name,data in files.items():
                entry=ZipInfo(name,(2026,1,1,0,0,0));entry.compress_type=ZIP_DEFLATED;z.writestr(entry,data)
        with ZipFile(target) as z:assert z.testzip() is None
        report['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        (work/'artwork-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        work.rename(output)
        return report
    finally:
        if work.exists():shutil.rmtree(work)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.output),ensure_ascii=False,indent=2))
