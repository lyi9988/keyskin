#!/usr/bin/env python3
"""Apply original pearl-glass artwork to a BDS without changing its behavior.

These colors describe exported skin artwork, not the KeySkin editor UI. All
layouts, atlas slicing, icons, text, style IDs, audio and animation stay intact.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from base_validation import parse
from bds_visual import read_bds, image_bytes


SCALE = 3
ALLOWED_ENTRIES = {'res/panel.png', 'res/keys.png', 'res/default.css'}
COLOR_FIELDS = {'NM_COLOR', 'HL_COLOR'}
INK = '3B3A53'
PRESSED_INK = '464968'
TOOLBAR = 'EDF1F9'


def blend(a, b, amount):
    return tuple(a[i] * (1 - amount) + b[i] * amount for i in range(len(a)))


def gaussian(x, y, cx, cy, rx, ry):
    return math.exp(-(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2) * 1.6)


def glass_panel():
    """Large, unfocused color fields: lilac left, icy blue right, pearl above."""
    image = Image.new('RGB', (1080, 624))
    pixels = image.load()
    for y in range(image.height):
        t = y / (image.height - 1)
        # The first row matches the native toolbar's flat backing exactly.
        emergence = 1 - math.exp(-y / 105)
        for x in range(image.width):
            color = blend((237, 241, 249), (216, 224, 243), t)
            fields = [
                ((227, 202, 242), 0.86 * gaussian(x, y, 90, 505, 470, 410)),
                ((187, 224, 244), 0.88 * gaussian(x, y, 1080, 300, 650, 520)),
                ((204, 205, 242), 0.52 * gaussian(x, y, 530, 720, 420, 430)),
                ((253, 248, 255), 0.70 * gaussian(x, y, 340, 90, 520, 285)),
            ]
            for tint, amount in fields:
                color = blend(color, tint, amount * emergence)
            # A broad, softly refracted sweep, without any discernible artwork.
            sweep = math.exp(-((y - (180 + x * 0.25)) / 145) ** 2)
            color = blend(color, (248, 252, 255), 0.11 * sweep * emergence)
            pixels[x, y] = tuple(round(v) for v in color)
    return image


def rounded_mask(size, bounds, radius, width=None):
    image = Image.new('L', size)
    draw = ImageDraw.Draw(image)
    box = tuple(round(v * SCALE) for v in bounds)
    if width is None:
        draw.rounded_rectangle(box, radius * SCALE, fill=255)
    else:
        draw.rounded_rectangle(box, radius * SCALE, outline=255,
                               width=max(1, round(width * SCALE)))
    return image


def clipped_layer(layer, mask):
    layer.putalpha(ImageChops.multiply(layer.getchannel('A'), mask))
    return layer


def glass_keycap(kind, pressed=False):
    """One nine-slice-compatible RGBA key, with restrained physical highlights."""
    size = (128 * SCALE, 128 * SCALE)
    image = Image.new('RGBA', size)
    shift = 1 if pressed else 0
    box = (6, 5 + shift, 122, 118 + shift)
    mask = rounded_mask(size, box, 21)
    shadow = Image.new('RGBA', size, (74, 76, 127, 0))
    shadow_alpha = rounded_mask(size, (7, 9 + shift, 121, 122 + shift), 21)
    shadow.putalpha(shadow_alpha.point(lambda a: a * (17 if pressed else 32) // 255))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(2.4 * SCALE)))

    # Pearl keys transmit the panel; functional keys carry slightly more blue.
    # The accent is deliberately darker so the inherited white return icon
    # remains legible. No proprietary glyphs or images are generated here.
    palettes = {
        ('pearl', False): ((255, 255, 255, 185), (225, 238, 255, 104)),
        ('pearl', True): ((232, 242, 255, 194), (190, 214, 248, 164)),
        ('function', False): ((243, 246, 255, 128), (187, 207, 241, 135)),
        ('function', True): ((224, 236, 255, 182), (169, 192, 235, 175)),
        ('accent', False): ((111, 120, 184, 247), (102, 101, 167, 252)),
        ('accent', True): ((96, 108, 172, 251), (86, 87, 151, 255)),
    }
    top, bottom = palettes[(kind, pressed)]
    fill = Image.new('RGBA', size)
    pixels = fill.load()
    for y in range(size[1]):
        t = max(0, min(1, (y / SCALE - box[1]) / (box[3] - box[1])))
        for x in range(size[0]):
            color = blend(top, bottom, t)
            sheen = gaussian(x / SCALE, y / SCALE, 24, 15 + shift, 89, 54)
            color = blend(color, (255, 255, 255, color[3]),
                          sheen * (0.065 if kind == 'accent' else 0.20))
            pixels[x, y] = tuple(round(v) for v in color)
    image.alpha_composite(clipped_layer(fill, mask))

    # The rim varies smoothly from bright pearl to a subtle cool reflection.
    # Each of its 9-slice corners is retained by the unchanged 32px insets.
    rim_mask = rounded_mask(size, box, 21, 1)
    rim = Image.new('RGBA', size)
    draw = ImageDraw.Draw(rim)
    for y in range(size[1]):
        t = max(0, min(1, (y / SCALE - box[1]) / (box[3] - box[1])))
        alpha = (215 - 120 * t) * (0.56 if pressed else 1)
        if kind == 'accent':
            alpha *= 0.56
        draw.line((0, y, size[0], y), fill=(255, 255, 255, round(alpha)))
    image.alpha_composite(clipped_layer(rim, rim_mask))

    # A very fine inner glass edge; no heavy inset bevel or opaque gloss band.
    inner = Image.new('RGBA', size, (255, 255, 255, 23 if pressed else 34))
    inset = (7.4, 6.4 + shift, 120.6, 116.6 + shift)
    image.alpha_composite(clipped_layer(inner, rounded_mask(size, inset, 19.6, 0.55)))
    return image.resize((128, 128), Image.Resampling.LANCZOS)


def glass_atlas():
    image = Image.new('RGBA', (768, 128))
    for index, kind in enumerate(('pearl', 'function', 'accent')):
        for pressed in (False, True):
            image.alpha_composite(glass_keycap(kind, pressed),
                                  ((index * 2 + int(pressed)) * 128, 0))
    return image


def recolor_css(data):
    """Replace only existing color values; retain exact other bytes and order."""
    section = None
    changed = []
    result = []
    for line in data.decode('utf-8-sig').splitlines(keepends=True):
        match = re.fullmatch(r'\[([^\]]+)\]\s*', line)
        if match:
            section = match[1]
        match = re.fullmatch(r'(NM_COLOR|HL_COLOR)=([^\r\n]+)(\r?\n|$)', line)
        if match:
            field, old, newline = match.groups()
            if section == 'STYLE213':
                color = TOOLBAR
            elif section == 'STYLE214':
                color = '4B4D69' if field == 'NM_COLOR' else INK
            else:
                color = INK if field == 'NM_COLOR' else PRESSED_INK
            if old != color:
                changed.append({'section': section, 'field': field,
                                'before': old, 'after': color})
            line = f'{field}={color}{newline}'
        result.append(line)
    encoded = ''.join(result).encode('utf-8')
    if data.startswith(b'\xef\xbb\xbf'):
        encoded = b'\xef\xbb\xbf' + encoded
    return encoded, changed


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_preservation(before, after):
    if list(before) != list(after):
        raise ValueError('Entry names or order changed')
    changed = {name for name in before if before[name] != after[name]}
    if changed != ALLOWED_ENTRIES:
        raise ValueError(f'Unexpected changed entries: {changed}')
    old_css, new_css = parse(before['res/default.css']), parse(after['res/default.css'])
    if old_css.keys() != new_css.keys():
        raise ValueError('Style IDs changed')
    for section, old_style in old_css.items():
        new_style = new_css[section]
        if old_style.keys() != new_style.keys():
            raise ValueError(f'Style fields changed: {section}')
        for field, value in old_style.items():
            if field not in COLOR_FIELDS and new_style[field] != value:
                raise ValueError(f'Non-color style changed: {section}.{field}')
    for name in ALLOWED_ENTRIES - {'res/default.css'}:
        with Image.open(io.BytesIO(before[name])) as old:
            with Image.open(io.BytesIO(after[name])) as new:
                new.load()
                if old.size != new.size:
                    raise ValueError(f'Image dimensions changed: {name}')
    # Resource references and every tile are checked without requiring a
    # particular animation schema, since the motion pass runs independently.
    for style in new_css.values():
        for field in ('NM_IMG', 'HL_IMG'):
            if field in style:
                resource, tile = style[field].split(',')
                if f'res/{resource}.png' not in after:
                    raise ValueError(f'Missing image: {resource}')
                tiles = parse(after[f'res/{resource}.til'])
                if f'IMG{tile}' not in tiles:
                    raise ValueError(f'Missing image tile: {resource},{tile}')
    for name, data in after.items():
        if not name.endswith('.til'):
            continue
        with Image.open(io.BytesIO(after[name[:-4] + '.png'])) as image:
            for section, values in parse(data).items():
                if not section.startswith('IMG'):
                    continue
                x, y, w, h = map(int, values['SOURCE_RECT'].split(','))
                if not (0 <= x < x + w <= image.width and 0 <= y < y + h <= image.height):
                    raise ValueError(f'Out-of-bounds atlas tile: {name} {section}')
    return {
        'same_archive_entry_order': True,
        'all_layouts_byte_identical': True,
        'all_actions_and_clear_f40_preserved': True,
        'style_ids_labels_sizes_and_bindings_preserved': True,
        'all_atlas_geometry_byte_identical': True,
        'icons_audio_animations_and_metadata_byte_identical': True,
        'only_three_declared_entries_changed': True,
        'image_dimensions_and_references_valid': True,
    }


def contrast_ratio(a, b):
    def luminance(rgb):
        values = [v / 255 for v in rgb]
        values = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                  for v in values]
        return sum(v * weight for v, weight in zip(values, (0.2126, 0.7152, 0.0722)))
    x, y = sorted((luminance(a), luminance(b)))
    return (y + 0.05) / (x + 0.05)


def contrast_samples(panel, atlas):
    """Conservative interior samples, not a claim of device accessibility QA."""
    backgrounds = [panel.getpixel((x, y)) for x in range(0, panel.width, 18)
                   for y in range(0, panel.height, 12)]
    ink_colors = [(59, 58, 83), (70, 73, 104), (75, 77, 105), (62, 50, 91)]
    ratios = {}
    for index, name in enumerate(('pearl', 'pearl_pressed', 'function',
                                  'function_pressed', 'accent', 'accent_pressed')):
        candidates = []
        inks = [(255, 255, 255)] if index >= 4 else ink_colors
        for y in (30, 48, 64, 80, 96):
            for x in (32, 64, 96):
                rgba = atlas.getpixel((index * 128 + x, y))
                for background in backgrounds:
                    composite = blend(background, rgba[:3], rgba[3] / 255)
                    candidates.extend(contrast_ratio(ink, composite) for ink in inks)
        ratios[name] = round(min(candidates), 2)
    if any(ratio < (3 if name.startswith('accent') else 4.5)
           for name, ratio in ratios.items()):
        raise ValueError(f'Interior label/icon contrast is too low: {ratios}')
    return ratios


def build(base, output):
    if output.exists():
        raise ValueError('Output directory exists; use a fresh destination')
    entries, before, comment = read_bds(base)
    after = dict(before)
    panel, atlas = glass_panel(), glass_atlas()
    after['res/panel.png'], after['res/keys.png'] = image_bytes(panel), image_bytes(atlas)
    after['res/default.css'], colors = recolor_css(before['res/default.css'])
    checks = validate_preservation(before, after)
    ratios = contrast_samples(panel, atlas)
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='.glass-visuals-', dir=output.parent))
    try:
        result = work / 'glass-visuals.bds'
        with ZipFile(result, 'w') as archive:
            archive.comment = comment
            for entry in entries:
                archive.writestr(entry, after[entry.filename])
        _, reopened, _ = read_bds(result)
        validate_preservation(before, reopened)
        with ZipFile(result) as archive:
            if archive.testzip() is not None:
                raise ValueError('Archive integrity check failed')
        panel.save(work / 'panel.png')
        atlas.save(work / 'keys.png')
        report = {
            'name': 'Pearl Glass visual pass',
            'input_sha256': digest(base.read_bytes()),
            'output_sha256': digest(result.read_bytes()),
            'changed_entries': sorted(ALLOWED_ENTRIES),
            'color_changes': colors,
            'unchanged_entry_count': len(before) - len(ALLOWED_ENTRIES),
            'unchanged_entry_sha256': {name: digest(data) for name, data in before.items()
                                       if name not in ALLOWED_ENTRIES},
            'checks': checks,
            'minimum_sampled_interior_contrast': ratios,
            'provenance': 'Original procedural gradients and rounded geometry only; no downloaded artwork, proprietary assets or fonts.',
            'limitations': [
                'Visual pass only; existing star effect is intentionally retained for the separate motion pass.',
                'Frosted appearance is painted RGBA, not live backdrop blur or optical refraction.',
                'Native toolbar behavior is client-controlled and unchanged.',
                'Not verified on an Android device or Baidu IME.',
                'Contrast measurements sample asset interiors over the panel, not device-rendered glyphs.',
            ],
        }
        (work / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        work.rename(output)
        return report
    finally:
        if work.exists():
            shutil.rmtree(work)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = build(args.base, args.output)
    print(json.dumps({key: result[key] for key in
                      ('changed_entries', 'unchanged_entry_count', 'checks',
                       'minimum_sampled_interior_contrast', 'output_sha256')}, indent=2))
