#!/usr/bin/env python3
"""Generate an original, minimal Baidu Android base from code, without a donor BDS.

This is a format prototype, not a verified IME implementation. Composition and
candidate behavior belong to Baidu's native engine and require device testing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import shutil
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from base_validation import validate_files
from base_assets import background_png, WIDTH, HEIGHT

GROUPS = {2: 'abc', 3: 'def', 4: 'ghi', 5: 'jkl', 6: 'mno',
          7: 'pqrs', 8: 'tuv', 9: 'wxyz'}
ORIENTATIONS = {'port': (1080, 624), 'land': (1920, 480)}
FUNCTIONS = {'symbols': 'F1', 'return': 'F4', 'numbers': 'F6', 'emoji': 'F7',
             'hide': 'F8', 'more_candidates': 'F9', 'shift': 'F10', 'caps': 'F11',
             'chinese': 'F15', 'english': 'F16', 'previous': 'F22', 'next': 'F23',
             'prediction': 'F25', 'menu': 'F31', 'delete': 'F36', 'space': 'F38',
             'enter': 'F39', 'clear_preedit': 'F40', 'copy': 'F45', 'paste': 'F46',
             'select_all': 'F47', 'left': 'F51', 'right': 'F52',
             'candidate_area': 'F55', 'undo': 'F67', 'clipboard': 'F76'}


def ini(sections):
    """Fresh deterministic UTF-8/CRLF; no template text is loaded or copied."""
    return ('\r\n\r\n'.join('[' + name + ']\r\n' + '\r\n'.join(
        str(key) + '=' + str(value) for key, value in values.items())
        for name, values in sections.items()) + '\r\n').encode('utf-8')


class Base:
    def __init__(self):
        self.files = {}
        self.labels = {}

    def label(self, text):
        if text not in self.labels:
            self.labels[text] = 100 + len(self.labels)
        return self.labels[text]

    def key(self, label, action, rect, function=False, **events):
        return {'BACK_STYLE': 3 if function else 2,
                'FORE_STYLE': self.label(label),
                'VIEW_RECT': ','.join(map(str, rect)), 'CENTER': action, **events}

    def grid_key(self, label, action, w, h, col, row, width=1, columns=5,
                 function=False, **events):
        # Own proportional geometry; leaves 8px of space on each edge.
        x0, x1 = round(w * col / columns), round(w * (col + width) / columns)
        y0, y1 = round(h * row / 4), round(h * (row + 1) / 4)
        return self.key(label, action, (x0 + 8, y0 + 8, x1 - x0 - 16, y1 - y0 - 16),
                        function, **events)

    def native_list(self, w, h, english=False, symbols=False):
        result = {'BACK_STYLE': 1, 'CELL_STYLE': 3, 'FORE_STYLE': 4,
                  'POS': '8,8', 'CELL_SIZE': f'{round(w / 5) - 16},{(round(h * 3 / 4) - 16) // 5}',
                  'PADDING': '4,2,4,2', 'LIST_NUM': 5, 'LIST_ORDER': 0}
        if not symbols:
            chars = ', . ? ! ~' if english else '， 。 ？ ！ ～'
            result.update(TYPE=0, NAMES=chars, VALUES=chars)
        return result

    def layout(self, keys, w, h, blur=False, english=False, listing=None, more=None):
        sections = {'INPUT': {}, 'CAND': {},
                    'HINT': {'LAYOUT_NAME': 'hint', 'TYPE': 0},
                    'MORE': more or {'LAYOUT_NAME': 'sel_en' if english else 'sel_ch',
                                     'GRID': '5,2' if english else '4,4'},
                    'PANEL': {'SIZE': f'{w},{h}', 'KEY_NUM': len(keys),
                              'NO_BLUR': 0 if blur else 1, 'BACK_STYLE': 1}}
        if listing is not None:
            sections['LIST'] = listing
        sections.update({f'KEY{i}': key for i, key in enumerate(keys, 1)})
        return ini(sections)

    def nine(self, w, h, english=False, upper=False):
        keys = [self.grid_key('1', '…' if english else "'", w, h, 1, 0,
                              UP='1', HOLD='1', SHOW='1')]
        for number, group in GROUPS.items():
            letters = group  # IME caps state handles casing; action slots remain lowercase.
            events = {'LEFT': letters[0], 'RIGHT': letters[2], 'UP': str(number), 'SHOW': str(number)}
            if len(group) == 4:
                events['DOWN'] = letters[3]
            keys.append(self.grid_key(letters.upper(), letters[1], w, h,
                                      (number - 1) % 3 + 1, (number - 1) // 3, **events))
        keys.extend([
            self.grid_key('Space', 'F38', w, h, 2, 3, UP='0', HOLD='Z+tools'),
            self.grid_key('Del', 'F36', w, h, 4, 0, function=True, LEFT='F40'),
            self.grid_key('Enter', 'F39', w, h, 4, 1, function=True),
            self.grid_key(('CAPS' if upper else 'Shift') if english else 'Emoji',
                          ('F11' if upper else 'F10') if english else 'F7', w, h, 4, 2, function=True),
            self.grid_key('123', 'F6', w, h, 4, 3, function=True),
        ])
        if english:
            keys.extend([self.grid_key('SYM', 'F1', w, h, 3, 3, function=True),
                         self.grid_key('CN', 'F15', w, h, 1, 3, width=.5, function=True),
                         self.grid_key('Predict', 'F25', w, h, 1.5, 3, width=.5, function=True)])
        else:
            keys.extend([self.grid_key('EN', 'F16', w, h, 1, 3, function=True),
                         self.grid_key('SYM', 'F1', w, h, 3, 3, function=True)])
        return self.layout(keys, w, h, blur=True, english=english,
                           listing=self.native_list(w, h, english))

    def qwerty(self, w, h, english=False, upper=False):
        keys = []
        for row, (letters, start) in enumerate([('qwertyuiop', 0), ('asdfghjkl', .5), ('zxcvbnm', 1.5)]):
            for col, letter in enumerate(letters):
                value = letter.upper() if upper else letter
                extra = {'UP': str((col + 1) % 10)} if row == 0 else {}
                keys.append(self.grid_key(value, letter, w, h, start + col, row, columns=10, **extra))
        keys.extend([
            self.grid_key(('CAPS' if upper else 'Shift') if english else "'",
                          ('F11' if upper else 'F10') if english else "'", w, h, 0, 2, width=1.5, columns=10, function=True),
            self.grid_key('Del', 'F36', w, h, 8.5, 2, width=1.5, columns=10, function=True, LEFT='F40'),
        ])
        bottom = [('123', 'F6', 1.2), ('CN' if english else 'EN', 'F15' if english else 'F16', 1.2),
                  ('SYM', 'F1', 1.1), ('Space', 'F38', 3),
                  (',' if english else '，', ',' if english else '，', 1),
                  ('.' if english else '。', '.' if english else '。', 1), ('Enter', 'F39', 1.5)]
        x = 0
        for label, action, span in bottom:
            extra = {'HOLD': 'Z+tools'} if action == 'F38' else {'HOLD': 'F7'} if action == 'F1' else {}
            keys.append(self.grid_key(label, action, w, h, x, 3, width=span, columns=10, function=True, **extra))
            x += span
        return self.layout(keys, w, h, english=english)

    def numeric(self, w, h):
        keys = [self.grid_key(str(n), str(n), w, h, (n - 1) % 3 + 1, (n - 1) // 3) for n in range(1, 10)]
        keys.append(self.grid_key('0', '0', w, h, 2, 3))
        for row, char in enumerate(['@', '%', '/', '+']):
            keys.append(self.grid_key(char, char, w, h, 0, row))
        keys.extend([self.grid_key('-', '-', w, h, 1, 3), self.grid_key('.', '.', w, h, 3, 3)])
        for row, (label, action) in enumerate([('Del', 'F36'), ('Enter', 'F39'), ('Space', 'F38'), ('Back', 'F4')]):
            keys.append(self.grid_key(label, action, w, h, 4, row, function=True))
        return self.layout(keys, w, h)

    def selector(self, w, h, english=False):
        keys = [self.key('', 'F55', (round(w / 5) + 8, 8, round(w * 4 / 5) - 16, round(h * 3 / 4) - 16))]
        for i, (label, action) in enumerate([('Back', 'F4'), ('Prev', 'F22'), ('Next', 'F23'), ('Del', 'F36')]):
            keys.append(self.grid_key(label, action, w, h, i, 3, columns=4, function=True))
        return self.layout(keys, w, h, english=english, listing=self.native_list(w, h, symbols=True), more={'GRID': '5,2' if english else '4,4'})

    def tools(self, w, h):
        rows = [[('Copy', 'F45'), ('Paste', 'F46'), ('All', 'F47')],
                [('Left', 'F51'), ('Right', 'F52'), ('Undo', 'F67')],
                [('Clipboard', 'F76'), ('Menu', 'F31'), ('Hide', 'F8')],
                [('Back', 'F4'), ('Space', 'F38'), ('Enter', 'F39')]]
        keys = [self.grid_key(label, action, w, h, col, row, columns=3, function=True)
                for row, items in enumerate(rows) for col, (label, action) in enumerate(items)]
        return self.layout(keys, w, h)

    def common(self, w, h):
        ch = 104 if w == 1080 else 88
        gen = {'PANEL': {'SIZE': f'{w},{h}', 'BACK_STYLE': 1},
               'INPUT': {'BACK_STYLE': 1, 'FORE_STYLE': 4},
               'CAND': {'LAYOUT_NAME': 'cand', 'TYPE': 4, 'VIEW_RECT': f'0,0,{w},{ch}'},
               'HINT': {'LAYOUT_NAME': 'hint', 'TYPE': 0},
               'MORE': {'LAYOUT_NAME': 'sel_ch', 'SYM_LAYOUT': 'symbol', 'GRID': '4,4', 'CELL_STYLE': 2, 'FORE_STYLE': 4},
               'LIST': {'BACK_STYLE': 1, 'CELL_STYLE': 3, 'FORE_STYLE': 4, 'PADDING': '4,2,4,2'}}
        cand = {'TAB': {'BACK_STYLE': 1, 'CELL_STYLE': 2, 'FORE_STYLE': 4, 'CELL_W': 60,
                        'FIRST_GAP': 12, 'PADDING': '100,0,100,0'},
                'CAND': {'BACK_STYLE': 1, 'CELL_STYLE': 2, 'FORE_STYLE': 4, 'CELL_W': 60,
                         'FIRST_GAP': 12, 'PADDING': '100,0,100,0', 'ICON_NUM': 2},
                'SWITCH': {'NML_BACK_STYLE': 2, 'SEL_BACK_STYLE': 3, 'NML_FONT_STYLE': 4, 'SEL_FONT_STYLE': 5, 'PADDING': 0},
                'ICON1': {'BACK_STYLE': 3, 'FORE_STYLE': self.label('Menu'), 'SIZE': f'88,{ch - 16}',
                          'ANCHOR_TYPE': 4, 'POS': f'8,{-ch // 2 + 8}', 'KEY': 'F31', 'PERSIST': 1},
                'ICON2': {'BACK_STYLE': 3, 'FORE_STYLE': self.label('More'), 'SIZE': f'88,{ch - 16}',
                          'ANCHOR_TYPE': 6, 'POS': f'-96,{-ch // 2 + 8}', 'KEY': 'F9', 'PERSIST': 2}}
        hint = {'GLOBAL': {'ICON_NUM': 1}, 'HINT': {'BACK_ICON': 1},
                'BAR': {'BACK_ICON': 1, 'ARROW_ICON': 1},
                'ICON1': {'BACK_STYLE': 3, 'FORE_STYLE': 4, 'SIZE': '150,160', 'POS': '0,-20', 'PADDING': '8,8,8,8'}}
        return {'gen.ini': ini(gen), 'cand.cnd': ini(cand), 'hint.pop': ini(hint)}

    def generate(self):
        for orient, (w, h) in ORIENTATIONS.items():
            layouts = self.common(w, h)
            for name in ['py_9', 'def_9', 'en_9', 'en_9s']:
                layouts[name + '.ini'] = self.nine(w, h, name.startswith('en'), name.endswith('s'))
            for name in ['py_26', 'def_26', 'en_26', 'en_26s']:
                layouts[name + '.ini'] = self.qwerty(w, h, name.startswith('en'), name.endswith('s'))
            for name in ['num_9', 'num_26', 'num_26_1']:
                layouts[name + '.ini'] = self.numeric(w, h)
            for name in ['symbol', 'sel_ch', 'sel_en']:
                layouts[name + '.ini'] = self.selector(w, h, name == 'sel_en')
            layouts['tools.ini'] = self.tools(w, h)
            self.files.update({orient + '/' + name: value for name, value in layouts.items()})
        styles = {'GLOBAL': {'STYLE_NUM': max(self.labels.values()) + 1},
                  'STYLE0': {}, 'STYLE1': {'NM_IMG': 'panel,1'},
                  'STYLE2': {'NM_COLOR': 'FFFFFF', 'HL_COLOR': 'D7E5E1'},
                  'STYLE3': {'NM_COLOR': 'E0E9E3', 'HL_COLOR': 'BCCFC3'},
                  'STYLE4': {'FONT_SIZE': 42, 'NM_COLOR': '243F38', 'HL_COLOR': '3D6A59'},
                  'STYLE5': {'FONT_SIZE': 42, 'NM_COLOR': '3D6A59', 'HL_COLOR': '243F38'}}
        for label, number in self.labels.items():
            styles['STYLE' + str(number)] = {'SHOW': label, 'FONT_SIZE': 32 if len(label) > 4 else 42,
                                             'NM_COLOR': '243F38', 'HL_COLOR': '243F38'}
        self.files['res/default.css'] = ini(styles)
        self.files['res/panel.png'] = background_png()
        self.files['res/panel.til'] = ini({'GLOBAL': {'USE_ALPHA': 0, 'TILE_NUM': 1},
            'IMG1': {'SOURCE_RECT': f'0,0,{WIDTH},{HEIGHT}',
                     'INNER_RECT': f'1,1,{WIDTH - 2},{HEIGHT - 2}', 'SCALE': '1,1,1,1,1'}})
        self.files['Info.txt'] = ('Name=KeySkin Original Base Prototype 09\r\nAuthor=KeySkin Workflow\r\n'
                                  'Style=default\r\nSupportPlatform=A\r\nSkinFlags=1\r\nSkinType=1\r\nVersionCode=9\r\n').encode()
        return self.files


def write_base(output):
    if output.exists():
        raise ValueError('Output directory already exists')
    files = Base().generate()
    validation = validate_files(files)
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='.original-base-', dir=output.parent))
    try:
        target = work / 'original-base-prototype-09.bds'
        with ZipFile(target, 'w', compression=ZIP_DEFLATED) as archive:
            for name, data in files.items():
                entry = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                entry.compress_type = ZIP_DEFLATED
                archive.writestr(entry, data)
        with ZipFile(target) as archive:
            if archive.testzip() is not None:
                raise ValueError('ZIP CRC failed')
            if {name: archive.read(name) for name in archive.namelist()} != files:
                raise ValueError('ZIP round-trip mismatch')
        report = {'artifact': target.name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                  'provenance': 'All entries generated by original_base.py/base_assets.py; no source BDS, images or fonts read.',
                  'checks': validation, 'function_codes': FUNCTIONS,
                  'status': 'STRUCTURAL_PROTOTYPE_DEVICE_NOT_TESTED',
                  'not_verified': ['Android import and activation', 'Nine-key fuzzy composition and candidate selection',
                                   'English prediction and caps state', 'Clipboard, popup and page navigation behavior',
                                   'Native rendering and font scaling'],
                  'unsupported': ['Dark mode', 'Handwriting', 'Stroke input', 'Tablet-specific panels'],
                  'prior_failure': 'Prototype 06 middle-letter-only report has no confirmed root cause. This is not a claimed fix.'}
        (work / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        work.rename(output)
        return report
    finally:
        if work.exists():
            shutil.rmtree(work)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('artifacts/original-base-09'))
    args = parser.parse_args()
    try:
        print(json.dumps(write_base(args.output), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f'Error: {error}\n')
