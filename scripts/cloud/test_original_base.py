import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from original_base import Base, ini, write_base
from base_validation import parse, validate_files

ROOT = Path(__file__).resolve().parents[2]


class OriginalBaseTests(unittest.TestCase):
    def setUp(self):
        self.files = Base().generate()

    def mutate(self, path, edit):
        files = copy.copy(self.files)
        config = parse(files[path])
        edit(config)
        files[path] = ini(config)
        return files

    def test_from_scratch_without_reading_any_input_file(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('Must not read a donor')):
            self.assertEqual(Base().generate(), self.files)
        self.assertEqual(validate_files(self.files)['layouts'], 30)
        self.assertEqual([p for p in self.files if p.endswith('.png')], ['res/panel.png'])
        self.assertTrue(all(not p.endswith(('.ttf', '.otf')) for p in self.files))

    def test_nine_key_semantics_match_reference_in_both_orientations(self):
        # Reference is a read-only test oracle, not a generator dependency or asset source.
        fields = ('CENTER', 'LEFT', 'RIGHT', 'UP', 'DOWN', 'SHOW')
        with ZipFile(ROOT / 'public/default-template.bds') as reference:
            for orient in ('port', 'land'):
                for name in ('py_9', 'def_9', 'en_9', 'en_9s'):
                    path = f'{orient}/{name}.ini'
                    actual, expected = parse(self.files[path]), parse(reference.read(path))
                    self.assertEqual(actual['PANEL']['NO_BLUR'], expected['PANEL']['NO_BLUR'], path)
                    for n in range(2, 10):
                        for field in fields:
                            self.assertEqual(actual[f'KEY{n}'].get(field), expected[f'KEY{n}'].get(field), (path, n, field))

    def test_missing_engine_show_is_rejected_even_if_center_slots_match(self):
        def remove(c):
            del c['KEY2']['SHOW']
        with self.assertRaisesRegex(ValueError, 'engine SHOW'):
            validate_files(self.mutate('port/py_9.ini', remove))

    def test_wrong_fuzzy_flag_rejected(self):
        with self.assertRaisesRegex(ValueError, 'fuzzy flag'):
            validate_files(self.mutate('port/py_9.ini', lambda c: c['PANEL'].update(NO_BLUR='1')))

    def test_missing_native_selector_rejected(self):
        with self.assertRaisesRegex(ValueError, 'LIST missing'):
            validate_files(self.mutate('port/py_9.ini', lambda c: c.pop('LIST')))

    def test_incomplete_native_selector_rejected(self):
        with self.assertRaisesRegex(ValueError, 'incomplete LIST'):
            validate_files(self.mutate('port/py_9.ini', lambda c: c['LIST'].pop('CELL_SIZE')))

    def test_list_key_overlap_rejected(self):
        with self.assertRaisesRegex(ValueError, 'LIST overlaps'):
            validate_files(self.mutate('port/py_9.ini', lambda c: c['LIST'].update(POS='300,8')))

    def test_wrong_group_center_rejected(self):
        with self.assertRaisesRegex(ValueError, 'group action'):
            validate_files(self.mutate('port/py_9.ini', lambda c: c['KEY2'].update(CENTER='a')))

    def test_wrong_language_return_rejected(self):
        def change(c):
            for section in c.values():
                if section.get('CENTER') == 'F15':
                    section['CENTER'] = 'F16'
        with self.assertRaisesRegex(ValueError, 'shortcuts'):
            validate_files(self.mutate('port/en_26.ini', change))

    def test_missing_custom_page_rejected(self):
        del self.files['port/tools.ini']
        with self.assertRaisesRegex(ValueError, 'custom page'):
            validate_files(self.files)

    def test_missing_candidate_page_rejected(self):
        del self.files['port/cand.cnd']
        with self.assertRaisesRegex(ValueError, 'missing layout'):
            validate_files(self.files)

    def test_missing_style_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unresolved style'):
            validate_files(self.mutate('port/py_26.ini', lambda c: c['KEY1'].update(FORE_STYLE='9999')))

    def test_overlapping_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'overlapping keys'):
            validate_files(self.mutate('port/py_26.ini', lambda c: c['KEY2'].update(VIEW_RECT=c['KEY1']['VIEW_RECT'])))

    def test_key_count_rejected(self):
        with self.assertRaisesRegex(ValueError, 'KEY_NUM'):
            validate_files(self.mutate('port/py_9.ini', lambda c: c['PANEL'].update(KEY_NUM='99')))

    def test_all_keys_removed_rejected(self):
        def remove(c):
            for name in list(c):
                if name.startswith('KEY'):
                    del c[name]
        with self.assertRaisesRegex(ValueError, 'KEY_NUM'):
            validate_files(self.mutate('port/py_9.ini', remove))

    def test_horizontal_list_rejected(self):
        with self.assertRaisesRegex(ValueError, 'LIST_ORDER'):
            validate_files(self.mutate('port/py_9.ini', lambda c: c['LIST'].update(LIST_ORDER='1')))

    def test_missing_popup_icon_rejected(self):
        with self.assertRaisesRegex(ValueError, 'popup icon'):
            validate_files(self.mutate('port/hint.pop', lambda c: c['HINT'].update(BACK_ICON='999')))

    def test_icon_count_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ICON_NUM'):
            validate_files(self.mutate('port/cand.cnd', lambda c: c['CAND'].update(ICON_NUM='1')))

    def test_missing_image_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing image'):
            validate_files(self.mutate('res/default.css', lambda c: c['STYLE2'].update(NM_IMG='absent,1')))

    def test_missing_tile_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing image tile'):
            validate_files(self.mutate('res/default.css', lambda c: c['STYLE2'].update(NM_IMG='panel,99')))

    def test_english_selector_grid_matches_input(self):
        for orient in ('port', 'land'):
            self.assertEqual(parse(self.files[f'{orient}/sel_en.ini'])['MORE']['GRID'], '5,2')
            self.assertEqual(parse(self.files[f'{orient}/en_9.ini'])['MORE']['GRID'], '5,2')

    def test_output_is_deterministic_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a, b = write_base(root / 'a'), write_base(root / 'b')
            self.assertEqual(a['sha256'], b['sha256'])
            self.assertEqual(a['status'], 'STRUCTURAL_PROTOTYPE_DEVICE_NOT_TESTED')
            with ZipFile(root / 'a/original-base-prototype-09.bds') as z:
                self.assertIsNone(z.testzip())
                self.assertEqual({n: z.read(n) for n in z.namelist()}, self.files)
            with self.assertRaises(ValueError):
                write_base(root / 'a')


if __name__ == '__main__':
    unittest.main()
