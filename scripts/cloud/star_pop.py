"""Original smiling-star frame clip layered on the tested v10 input configuration.
No donor artwork. GIF preview is an illustration, not an Android recording.
"""
import argparse, io, json, math, hashlib, zipfile
from pathlib import Path
from PIL import Image, ImageDraw


def frames(size=1, count=12):
    result = []
    for i in range(count):
        phase = i * 12 / count
        im = Image.new('RGBA', (96, 112))
        d = ImageDraw.Draw(im)
        scale = min(1, (phase + 1) / 3) * (1 if phase < 9 else (12-phase)/3)
        cx, cy = 48, 65 - phase * 3
        points=[]
        for k in range(10):
            a=-math.pi/2+k*math.pi/5
            r=(31 if k%2==0 else 17)*scale
            points.append((cx+math.cos(a)*r, cy+math.sin(a)*r))
        d.polygon(points, fill='#ffe582' if size != 1 else '#d4bbff', outline='#7245ae' if size != 1 else '#8263b6', width=2)
        if scale > .6:
            for x in (cx-8,cx+8): d.ellipse((x-2,cy-4,x+2,cy+1), fill='#493563')
            d.arc((cx-6,cy-1,cx+6,cy+8),0,180,fill='#493563',width=2)
            for x in (cx-15,cx+12): d.ellipse((x,cy+2,x+5,cy+5),fill='#fa9fb9')
        for x,y in [(17,29),(78,48)]:
            r=3 if i%3 else 5
            d.line((x-r,y,x+r,y),fill='#af8bdf',width=2)
            d.line((x,y-r,x,y+r),fill='#af8bdf',width=2)
        # Fixed transparent index: GIF disposal clears the previous moving frame.
        if size != 1:
            im = im.resize((round(96*size), round(112*size)), Image.Resampling.NEAREST)
        p=im.convert('RGB').quantize(colors=255)
        mask=im.getchannel('A').point(lambda a: 255 if a==0 else 0)
        p.paste(255,mask=mask); p.info['transparency']=255
        result.append(p)
    return result


def build(base, output, prominent=False):
    output.mkdir(parents=True,exist_ok=False)
    original=zipfile.ZipFile(base)
    data={n:original.read(n) for n in original.namelist()}
    assert 'res/star-pop.gif' not in data
    css=data['res/default.css'].decode()
    assert css.count('PRESS_ANIM=1\r\n')==1
    data['res/default.css']=css.replace('PRESS_ANIM=1\r\n','PRESS_ANIM=3\r\n').encode()
    anim=data['res/anim.ini'].decode()
    assert 'ANIM_NUM=2' in anim
    anim=anim.replace('ANIM_NUM=2','ANIM_NUM=3')
    anim+='\r\n[ANIM3]\r\nCATEGORY=2\r\nANIM_PATH=star-pop.gif\r\nDURATION=480\r\nDELAY=0\r\nREPEAT_CNT=1\r\nREPEAT_MODE=0\r\nREMOVE=1\r\n'
    if prominent: anim=anim.replace('DURATION=480','DURATION=720')
    data['res/anim.ini']=anim.encode()
    f=frames(1.75 if prominent else 1, 18 if prominent else 12); buf=io.BytesIO()
    f[0].save(buf,format='GIF',save_all=True,append_images=f[1:],duration=40,disposal=2,transparency=255,optimize=False)
    data['res/star-pop.gif']=buf.getvalue()
    data['Info.txt']=data['Info.txt'].replace('雾紫轻触10'.encode(),('雾紫星星12' if prominent else '雾紫星星11').encode())
    target=output/('mist-star-12.bds' if prominent else 'mist-star-11.bds')
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in data.items():
            zi=zipfile.ZipInfo(n,(2026,1,1,0,0,0)); zi.compress_type=zipfile.ZIP_DEFLATED; z.writestr(zi,b)
    # Strict byte identity for ALL layout/action files, sound and prior art resources.
    allowed={'Info.txt','res/default.css','res/anim.ini'}
    for n in original.namelist():
        if n not in allowed: assert data[n]==original.read(n),n
    gif=Image.open(io.BytesIO(data['res/star-pop.gif']))
    assert gif.n_frames==(18 if prominent else 12)
    assert sum((gif.seek(i) or gif.info['duration']) for i in range(gif.n_frames))==(720 if prominent else 480)
    (output/'star-pop.gif').write_bytes(data['res/star-pop.gif'])
    report={'base_sha256':hashlib.sha256(Path(base).read_bytes()).hexdigest(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'frames':gif.n_frames,'duration_ms':720 if prominent else 480,'input_files_byte_identical':True,'press_chain':'existing ANIM_STYLE -> PRESS_ANIM=3 -> original GIF; release scale remains','device_effect_verified':False,'limitations':['Native GIF positioning and clipping unverified','Rapid typing and release interruption unverified','Preview illustration is not native runtime evidence']}
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('base',type=Path); p.add_argument('output',type=Path)
    p.add_argument('--prominent',action='store_true')
    a=p.parse_args(); build(a.base,a.output,a.prominent)
