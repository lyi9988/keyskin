"""Original subtle ripple frames + native micro-press; preserves typing and sounds."""
import argparse,io,json,math,re,zipfile,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
from base_validation import parse
from original_base import ini


def ripple_frames():
    result=[]
    for i in range(14):
        p=i/13;im=Image.new('RGBA',(160,144));d=ImageDraw.Draw(im)
        cx=80+2*math.sin(p*2*math.pi);cy=72+math.sin(p*math.pi)
        for delay in (0,.25):
            q=(p-delay)/(1-delay)
            if not 0<=q<=1:continue
            rx=12+60*q;ry=10+48*q
            # Pale but visibly blue on white; no broad opaque overlay over glyphs.
            col='#bdd3ec' if q<.65 else '#d5e2f1'
            if q<.94:d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),outline=col,width=2 if q<.7 else 1)
            if q<.75:d.arc((cx-rx+3,cy-ry+3,cx+rx-3,cy+ry-3),190,290,fill='#ffffff',width=2)
        frame=im.convert('RGB').quantize(colors=255);mask=im.getchannel('A').point(lambda a:255 if a==0 else 0);frame.paste(255,mask=mask);frame.info['transparency']=255;result.append(frame)
    return result


def build(base,out):
    out.mkdir(parents=True,exist_ok=False);z=zipfile.ZipFile(base);original={n:z.read(n) for n in z.namelist()};files=dict(original)
    styles=parse(files['res/default.css']);sid=max(int(n[5:]) for n in styles if re.fullmatch(r'STYLE\d+',n))+1
    # Separate native press-effect slot avoids unsupported GIF-inside-transform groups.
    styles[f'STYLE{sid}']={'PRESS_ANIM':3};styles['STYLE206']['PRESS_ANIM']='4';styles['STYLE206']['RELEASE_ANIM']='7';styles['GLOBAL']['STYLE_NUM']=sid+1
    files['res/default.css']=ini(styles)
    animations={'GLOBAL':{'ANIM_NUM':7}}
    def base(kind,**v):return {'CATEGORY':0,'TYPE':kind,'DURATION':90,'DELAY':0,'INTPOL':2,'REPEAT_CNT':1,'REPEAT_MODE':0,'REMOVE':0,**v}
    animations['ANIM1']=base(4,FROM='100,100',TO='98,98',PIVOT='50,50')
    animations['ANIM2']=base(4,FROM='98,98',TO='100,100',PIVOT='50,50',DURATION=150,REMOVE=1)
    animations['ANIM3']={'CATEGORY':2,'ANIM_PATH':'glass-ripple.gif','DURATION':420,'REPEAT_CNT':1,'REMOVE':1}
    animations['ANIM4']={'CATEGORY':1,'BUILD_NUM':2,'BUILD_LIST':'1,5','BUILD_METHOD':0,'REPEAT_CNT':1,'REMOVE':0}
    animations['ANIM5']=base(2,FROM_PX='0,0',TO_PX='0,2')
    animations['ANIM6']=base(2,FROM_PX='0,2',TO_PX='0,0',DURATION=150,REMOVE=1)
    animations['ANIM7']={'CATEGORY':1,'BUILD_NUM':2,'BUILD_LIST':'2,6','BUILD_METHOD':0,'REPEAT_CNT':1,'REMOVE':1}
    files['res/anim.ini']=ini(animations)
    frames=ripple_frames();buf=io.BytesIO();frames[0].save(buf,format='GIF',save_all=True,append_images=frames[1:],duration=30,disposal=2,transparency=255,optimize=False)
    gif=Image.open(io.BytesIO(buf.getvalue()));assert gif.n_frames==14
    assert sum((gif.seek(i) or gif.info['duration']) for i in range(gif.n_frames))==420
    files['res/glass-ripple.gif']=buf.getvalue();files.pop('res/star-pop.gif',None)
    changed=[];count=0
    for name,data in original.items():
        if not re.fullmatch(r'(port|land)/[^/]+\.ini',name):continue
        layout=parse(data);found=False
        for section,key in layout.items():
            if re.fullmatch(r'KEY\d+',section) and key.get('ANIM_STYLE')=='206':key['PRESS_STYLE']=str(sid);count+=1;found=True
        if found:
            for section,key in parse(data).items():assert {k:v for k,v in layout[section].items() if k!='PRESS_STYLE'}==key
            files[name]=ini(layout);changed.append(name)
    assert count==580
    files['Info.txt']=files['Info.txt'].replace('雾紫星星14'.encode(),'流光玻璃15'.encode())
    for name,data in original.items():
        if name not in changed+['Info.txt','res/default.css','res/anim.ini','res/star-pop.gif']:assert files[name]==data,name
    target=out/'glass-ripple-15.bds'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():
            info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
    (out/'ripple.gif').write_bytes(buf.getvalue())
    report={'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bound_keys':count,'ripple_duration_ms':420,'micro_press':'98 percent scale and 2px downward movement; 150ms release','input_actions_unchanged':True,'sounds_unchanged':True,'device_effect_verified':False}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.base,a.output)
