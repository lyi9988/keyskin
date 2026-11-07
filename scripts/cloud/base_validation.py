"""Structural checks for our generated base, deliberately not an IME emulator."""
import configparser
from pathlib import PurePosixPath
import re
import struct


def parse(data):
    config = configparser.ConfigParser(interpolation=None, strict=True)
    config.optionxform = str
    config.read_string(data.decode('utf-8-sig'))
    return {name: dict(config[name]) for name in config.sections()}


def rect(value):
    result = tuple(map(int, value.split(',')))
    if len(result) != 4:
        raise ValueError('Rectangle must have four coordinates')
    return result


def overlap(a, b):
    x, y, w, h = a
    X, Y, W, H = b
    return min(x + w, X + W) > max(x, X) and min(y + h, Y + H) > max(y, Y)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_files(files):
    require('Info.txt' in files and b'SupportPlatform=A\r\n' in files['Info.txt'], 'Android metadata missing')
    require('res/default.css' in files, 'Stylesheet missing')
    require(all(name.endswith(('.ini', '.css', '.cnd', '.pop', '.txt', '.til')) or name == 'res/panel.png' for name in files), 'Unexpected binary or asset')
    require(all(b'\n' not in data.replace(b'\r\n', b'') for name, data in files.items() if not name.endswith('.png')), 'Text must use CRLF')
    configs = {path: parse(data) for path, data in files.items() if path != 'Info.txt' and not path.endswith('.png')}
    require('res/panel.png' in files and 'res/panel.til' in files, 'Background asset missing')
    require(files['res/panel.png'][:8] == b'\x89PNG\r\n\x1a\n', 'Invalid PNG signature')
    require(struct.unpack('>II', files['res/panel.png'][16:24]) == (1080, 624), 'PNG size mismatch')
    require(configs['res/panel.til']['IMG1']['SOURCE_RECT'] == '0,0,1080,624', 'TIL source rectangle mismatch')
    styles = configs['res/default.css']
    require(styles['STYLE1'].get('NM_IMG') == 'panel,1', 'Background image reference missing')
    ids = {int(name[5:]) for name in styles if re.fullmatch(r'STYLE\d+', name)}
    require(int(styles['GLOBAL']['STYLE_NUM']) > max(ids), 'STYLE_NUM too small')
    for section, values in styles.items():
        for field in ('NM_IMG', 'HL_IMG'):
            if field in values:
                image, tile = values[field].split(',')
                require(f'res/{image}.png' in files and f'res/{image}.til' in configs, f'{section} missing image or TIL')
                require(f'IMG{tile}' in configs[f'res/{image}.til'], f'{section} missing image tile')
    layout_count = key_count = 0
    action_fields = {'CENTER', 'LEFT', 'RIGHT', 'UP', 'DOWN', 'HOLD', 'KEY'}
    for path, config in configs.items():
        if path.endswith('.css'):
            continue
        parent = str(PurePosixPath(path).parent)
        icons = {name for name in config if re.fullmatch(r'ICON\d+', name)}
        for section, values in config.items():
            if 'ICON_NUM' in values:
                require(int(values['ICON_NUM']) == len(icons), f'{path} ICON_NUM mismatch')
            for field in ('BACK_ICON', 'ARROW_ICON'):
                if field in values:
                    require('ICON' + values[field] in icons, f'{path} missing popup icon')
        for section, values in config.items():
            for field, value in values.items():
                if field.endswith('STYLE') and value.isdecimal():
                    require(int(value) in ids, f'{path} {section} unresolved style {value}')
                if field in ('LAYOUT_NAME', 'SYM_LAYOUT'):
                    require(any(f'{parent}/{value}{ext}' in files for ext in ('.ini', '.cnd', '.pop')),
                            f'{path} missing layout {value}')
                if field in action_fields and value.startswith('Z+'):
                    require(f'{parent}/{value[2:]}.ini' in files, f'{path} missing custom page {value}')
        keys = [name for name in config if re.fullmatch(r'KEY\d+', name)]
        if 'KEY_NUM' in config.get('PANEL', {}):
            require(int(config['PANEL']['KEY_NUM']) == len(keys), f'{path} KEY_NUM mismatch')
        if not keys:
            continue
        layout_count += 1
        key_count += len(keys)
        require(keys == [f'KEY{i}' for i in range(1, len(keys) + 1)], f'{path} key numbering gap')
        require(int(config['PANEL']['KEY_NUM']) == len(keys), f'{path} KEY_NUM mismatch')
        w, h = map(int, config['PANEL']['SIZE'].split(','))
        areas = []
        for key in keys:
            area = rect(config[key]['VIEW_RECT'])
            x, y, width, height = area
            require(x >= 0 and y >= 0 and width > 0 and height > 0 and x + width <= w and y + height <= h,
                    f'{path} {key} outside panel')
            require(not any(overlap(area, other) for other in areas), f'{path} overlapping keys')
            areas.append(area)
        if 'LIST' in config:
            listing = config['LIST']
            require(listing.get('LIST_ORDER') == '0', f'{path} only vertical LIST_ORDER supported by this base')
            require(all(field in listing for field in ['POS', 'CELL_SIZE', 'LIST_NUM', 'LIST_ORDER']), f'{path} incomplete LIST')
            x, y = map(int, listing['POS'].split(','))
            width, height = map(int, listing['CELL_SIZE'].split(','))
            height *= int(listing['LIST_NUM'])
            require(x >= 0 and y >= 0 and width > 0 and height > 0 and x + width <= w and y + height <= h,
                    f'{path} LIST outside panel')
            require(not any(overlap((x, y, width, height), other) for other in areas), f'{path} LIST overlaps key')
        basename = PurePosixPath(path).name
        if basename in ('py_9.ini', 'def_9.ini', 'en_9.ini', 'en_9s.ini'):
            require(config['PANEL']['NO_BLUR'] == '0', f'{path} nine-key fuzzy flag wrong')
            require('LIST' in config, f'{path} native nine-key LIST missing')
            for n, group in enumerate(["'", 'abc', 'def', 'ghi', 'jkl', 'mno', 'pqrs', 'tuv', 'wxyz'], 1):
                key = config[f'KEY{n}']
                require(key.get('SHOW') == str(n), f'{path} KEY{n} engine SHOW missing or wrong')
                require(key.get('UP') == str(n), f'{path} KEY{n} digit gesture wrong')
                if n > 1:
                    require(key.get('CENTER') == group[1] and key.get('LEFT') == group[0] and key.get('RIGHT') == group[2],
                            f'{path} KEY{n} group action mapping wrong')
                    require(key.get('DOWN') == (group[3] if len(group) == 4 else None), f'{path} KEY{n} fourth letter wrong')
        if basename in ('py_26.ini', 'def_26.ini', 'en_26.ini', 'en_26s.ini'):
            require(''.join(config[f'KEY{i}']['CENTER'] for i in range(1, 27)) == 'qwertyuiopasdfghjklzxcvbnm',
                    f'{path} qwerty actions wrong')
            require(config['PANEL']['NO_BLUR'] == '1', f'{path} qwerty precise flag wrong')
        actions = {config[key].get('CENTER') for key in keys}
        if basename.startswith(('py_', 'def_', 'en_')):
            language = 'F15' if basename.startswith('en_') else 'F16'
            require({language, 'F1', 'F6', 'F36', 'F38', 'F39'} <= actions, f'{path} required shortcuts missing')
    for orient in ('port', 'land'):
        required = {'gen.ini', 'py_9.ini', 'en_9.ini', 'en_9s.ini', 'py_26.ini', 'en_26.ini', 'en_26s.ini',
                    'num_9.ini', 'num_26.ini', 'symbol.ini', 'sel_ch.ini', 'sel_en.ini', 'tools.ini', 'hint.pop', 'cand.cnd'}
        require(all(f'{orient}/{name}' in files for name in required), f'{orient} required panel missing')
        require(configs[f'{orient}/gen.ini']['CAND']['TYPE'] == '4', f'{orient} candidate type wrong')
    return {'layouts': layout_count, 'keys': key_count, 'entries': len(files),
            'all_references_resolve': True, 'all_key_rectangles_valid_and_nonoverlapping': True,
            'native_lists_complete_and_nonoverlapping': True, 'nine_key_engine_show_codes': True,
            'nine_key_fuzzy_flags_and_letter_slots': True, 'qwerty_and_language_switches': True,
            'all_assets_generated_without_donor': True}
