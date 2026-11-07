import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from PIL import Image
from bds_visual import build, inspect


def png_bytes(color, size=(24, 16)):
    data = io.BytesIO()
    Image.new('RGBA', size, color).save(data, format='PNG')
    return data.getvalue()


class VisualBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.template = self.root / 'original.bds'
        self.files = {'Info.txt': b'Name=Original\nSupportPlatform=A',
                      'port/gen.ini': b'[PANEL]\nSIZE=24,16\n',
                      'port/py_26.ini': b'[KEY1]\nVIEW_RECT=0,0,24,16\nCENTER=q\nUP=1\nHOLD=F7\n',
                      'res/back.til': b'[IMG1]\nSOURCE_RECT=0,0,24,16\n',
                      'res/default.css': b'[STYLE1]\nNM_IMG=back,1\n',
                      'res/back.png': png_bytes('blue'),
                      'res/fore.png': png_bytes('white')}
        self.write_template()
        (self.root / 'new.png').write_bytes(png_bytes('red'))
        self.plan = self.root / 'plan.json'
        self.replacements = [{'target': 'res/back.png', 'image': 'new.png'}]
        self.write_plan()

    def write_template(self):
        with ZipFile(self.template, 'w') as archive:
            archive.comment = b'original comment'
            for name, value in self.files.items():
                archive.writestr(name, value)

    def write_plan(self):
        self.plan.write_text(json.dumps({'replacements': self.replacements}))

    def run_build(self):
        return build(self.template, self.plan, self.root / 'out')

    def test_exact_replacement_preserves_every_other_byte_and_order(self):
        report = self.run_build()
        with ZipFile(self.root / 'out/skin.bds') as archive:
            self.assertEqual(archive.namelist(), list(self.files))
            self.assertEqual(archive.comment, b'original comment')
            for name, data in self.files.items():
                if name != 'res/back.png':
                    self.assertEqual(archive.read(name), data)
        self.assertEqual(report['unchanged_entry_count'], 6)
        self.assertTrue(all(report['checks'].values()))
        self.assertTrue((self.root / 'out/assets-before-after.png').exists())

    def test_inspect_dimensions(self):
        self.assertEqual(inspect(self.template)['images'][0]['size'], [24, 16])

    def test_wrong_size_fails_without_partial_output(self):
        (self.root / 'new.png').write_bytes(png_bytes('red', (8, 8)))
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            self.run_build()
        self.assertFalse((self.root / 'out').exists())

    def test_cover_is_explicit(self):
        (self.root / 'new.png').write_bytes(png_bytes('red', (8, 8)))
        self.replacements[0]['fit'] = 'cover'
        self.write_plan()
        self.assertEqual(self.run_build()['changed_images'][0]['size'], [24, 16])

    def test_config_cannot_be_replaced(self):
        self.replacements[0]['target'] = 'port/py_26.ini'
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'existing PNG'):
            self.run_build()

    def test_unknown_target_rejected(self):
        self.replacements[0]['target'] = 'res/missing.png'
        self.write_plan()
        with self.assertRaises(ValueError):
            self.run_build()

    def test_duplicate_replacement_rejected(self):
        self.replacements *= 2
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'Duplicate replacement'):
            self.run_build()

    def test_malformed_png_rejected(self):
        (self.root / 'new.png').write_bytes(b'not an image')
        with self.assertRaises(OSError):
            self.run_build()

    def test_unsafe_zip_path_rejected(self):
        self.files['../escape'] = b'test'
        self.write_template()
        with self.assertRaisesRegex(ValueError, 'Unsafe path'):
            self.run_build()

    def test_output_never_overwritten(self):
        self.run_build()
        before = (self.root / 'out/skin.bds').read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.run_build()
        self.assertEqual((self.root / 'out/skin.bds').read_bytes(), before)

    def test_unknown_fit_rejected(self):
        self.replacements[0]['fit'] = 'stretch'
        self.write_plan()
        with self.assertRaises(ValueError):
            self.run_build()

    def test_requires_layout(self):
        del self.files['port/gen.ini']
        self.write_template()
        with self.assertRaisesRegex(ValueError, 'layout'):
            self.run_build()


if __name__ == '__main__':
    unittest.main()
