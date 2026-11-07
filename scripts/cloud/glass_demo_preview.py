"""Combine real editor renders; label animation compositing as illustration."""
import argparse,io,zipfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from base_validation import parse


def build(package,render,bar,out):
    out.mkdir(parents=True,exist_ok=False)
    top=Image.open(bar).convert('RGBA');font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',20)
    for layout,label in [('py_9','九键'),('py_26','26键')]:
        panel=Image.open(render/f'light-{layout}.png').convert('RGBA')
        still=Image.new('RGBA',(panel.width,panel.height+top.height+55),'#edf0f7');still.alpha_composite(top,(0,55));still.alpha_composite(panel,(0,55+top.height))
        ImageDraw.Draw(still).text((16,14),f'流光玻璃15 · {label}编辑器绘制预览',font=font,fill='#35425b');still.convert('RGB').save(out/f'glass-{layout}.png')
    z=zipfile.ZipFile(package);gif=Image.open(io.BytesIO(z.read('res/glass-ripple.gif')))
    layout=parse(z.read('port/py_26.ini'));key=next(v for k,v in layout.items() if k.startswith('KEY') and v.get('CENTER')=='g')
    x,y,w,h=map(int,key['VIEW_RECT'].split(','));background=Image.open(out/'glass-py_26.png').convert('RGBA');frames=[]
    for i in range(gif.n_frames):
        gif.seek(i);frame=background.copy();d=ImageDraw.Draw(frame);d.rectangle((0,0,frame.width,54),fill='#edf0f7');d.text((16,14),'淡波纹动态示意 · 非手机实录，实际触发待验证',font=font,fill='#35425b');effect=gif.convert('RGBA');frame.alpha_composite(effect,(round(x+w/2-effect.width/2),round(y+h/2-effect.height/2)+55+top.height));frames.append(frame.convert('RGB'))
    frames[0].save(out/'glass-ripple-demo.gif',save_all=True,append_images=frames[1:],duration=30,loop=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('render',type=Path);p.add_argument('bar',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.package,a.render,a.bar,a.output)
