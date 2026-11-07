import io
import unittest
from PIL import Image
from original_base import Base
from mist_lilac import themed_files
from base_validation import parse


class MistLilacTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files,cls.report=themed_files()
        cls.base=Base().generate()

    def test_all_input_semantics_preserved(self):
        for path,data in self.base.items():
            if not path.endswith('.ini'):continue
            before,after=parse(data),parse(self.files[path])
            self.assertEqual(list(before),list(after))
            for section in before:
                self.assertEqual({k:v for k,v in before[section].items() if k!='BACK_STYLE'},
                                 {k:v for k,v in after[section].items() if k!='BACK_STYLE'},(path,section))

    def test_three_original_png_resources(self):
        self.assertEqual(sorted(p for p in self.files if p.endswith('.png')),
                         ['res/icons.png','res/keys.png','res/panel.png'])
        for name in ['panel','keys','icons']:
            image=Image.open(io.BytesIO(self.files[f'res/{name}.png']));image.load()
            self.assertGreater(image.width,0)
        self.assertEqual(self.report['keycap_slices'],6)
        self.assertEqual(self.report['icon_slices'],16)

    def test_normal_and_pressed_cap_pixels_differ(self):
        atlas=Image.open(io.BytesIO(self.files['res/keys.png']))
        for start in [0,256,512]:
            normal=atlas.crop((start,0,start+128,128)).tobytes()
            pressed=atlas.crop((start+128,0,start+256,128)).tobytes()
            self.assertNotEqual(normal,pressed)
        self.assertEqual(atlas.getpixel((0,0))[3],0)
        self.assertGreater(atlas.getpixel((64,64))[3],240)

    def test_no_duplicate_text_over_icon(self):
        styles=parse(self.files['res/default.css'])
        icons=[v for v in styles.values() if v.get('NM_IMG','').startswith('icons,')]
        self.assertEqual(len(icons),16)
        self.assertTrue(all('SHOW' not in v for v in icons))

    def test_native_nine_selector_background_transparent(self):
        for orient in ['port','land']:
            self.assertEqual(parse(self.files[f'{orient}/py_9.ini'])['LIST']['BACK_STYLE'],'0')
            self.assertEqual(parse(self.files[f'{orient}/py_9.ini'])['KEY2']['SHOW'],'2')

    def test_typographic_contrast(self):
        def luminance(rgb):
            cs=[v/255 for v in rgb]
            linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in cs]
            return sum(a*b for a,b in zip(linear,[.2126,.7152,.0722]))
        foreground=luminance((62,50,91))
        for fill in [(255,254,255),(220,212,239)]:
            self.assertGreater((luminance(fill)+.05)/(foreground+.05),4.5)


if __name__=='__main__':unittest.main()
