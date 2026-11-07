#!/usr/bin/env python3
"""Headless, image-only BDS editing. Never changes layout, styles or actions."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

from PIL import Image, ImageDraw, ImageOps

MAX_BYTES = 128 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_bds(path):
    if path.suffix.lower() != '.bds':
        raise ValueError('Only ordinary ZIP-based .bds templates are supported')
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Template exceeds 128 MiB')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)) or len(names) > 10000:
            raise ValueError('Duplicate entries or too many files')
        if sum(entry.file_size for entry in entries) > MAX_BYTES:
            raise ValueError('Uncompressed template exceeds 128 MiB')
        for entry in entries:
            path_name = PurePosixPath(entry.filename)
            if (path_name.is_absolute() or '..' in path_name.parts or
                    '\\' in entry.filename or ':' in entry.filename or
                    entry.flag_bits & 1):
                raise ValueError('Unsafe path or encrypted entry: ' + entry.filename)
        if not any(n.lower().endswith('info.txt') for n in names):
            raise ValueError('Missing BDS Info.txt')
        if not any(n.endswith('/gen.ini') for n in names):
            raise ValueError('Missing BDS layout gen.ini')
        return entries, {n: archive.read(n) for n in names}, archive.comment


def png(data):
    with Image.open(io.BytesIO(data)) as image:
        if image.format != 'PNG':
            raise ValueError('Replacement targets and sources must be PNG')
        image.load()
        return image.convert('RGBA')


def image_bytes(image):
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    return stream.getvalue()


def inspect(path):
    _, data, _ = read_bds(path)
    return {'template_sha256': digest(path.read_bytes()), 'images': [
        {'target': name, 'size': list(png(value).size)}
        for name, value in data.items() if name.lower().endswith('.png')]}


def build(template, plan_file, output):
    if output.exists():
        raise ValueError('Output directory already exists; choose a new directory')
    entries, before, comment = read_bds(template)
    plan = json.loads(plan_file.read_text())
    if not isinstance(plan, dict) or set(plan) != {'replacements'}:
        raise ValueError('Plan must contain only replacements')
    replacements = plan['replacements']
    if not isinstance(replacements, list) or not 1 <= len(replacements) <= 64:
        raise ValueError('Between 1 and 64 image replacements are required')
    after, changes, pairs = dict(before), [], []
    for replacement in replacements:
        if (not isinstance(replacement, dict) or
                set(replacement) - {'target', 'image', 'fit'} or
                not {'target', 'image'} <= set(replacement)):
            raise ValueError('Replacement accepts target, image and optional fit')
        target = replacement['target']
        if not isinstance(target, str) or target not in before or not target.lower().endswith('.png'):
            raise ValueError('Target must be an existing PNG resource')
        if any(item['target'] == target for item in changes):
            raise ValueError('Duplicate replacement target: ' + target)
        source_path = plan_file.parent / replacement['image']
        if source_path.stat().st_size > MAX_BYTES:
            raise ValueError('Source image exceeds 128 MiB')
        original, source = png(before[target]), png(source_path.read_bytes())
        fit = replacement.get('fit', 'exact')
        if fit == 'cover':
            source = ImageOps.fit(source, original.size, method=Image.Resampling.LANCZOS)
        elif fit != 'exact':
            raise ValueError('fit must be exact or cover')
        if source.size != original.size:
            raise ValueError('Image dimensions differ; prepare the atlas at original size or use cover for backgrounds')
        after[target] = image_bytes(source)
        if after[target] == before[target]:
            raise ValueError('Replacement has identical encoded bytes: ' + target)
        changes.append({'target': target, 'size': list(source.size), 'fit': fit,
                        'before_sha256': digest(before[target]),
                        'after_sha256': digest(after[target])})
        pairs.append((target, original, source))
    changed = {item['target'] for item in changes}
    unchanged = {name: digest(value) for name, value in before.items() if name not in changed}
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='.bds-build-', dir=output.parent))
    try:
        result = work / 'skin.bds'
        with zipfile.ZipFile(result, 'w') as archive:
            archive.comment = comment
            for entry in entries:
                archive.writestr(entry, after[entry.filename])
        _, reopened, _ = read_bds(result)
        if list(reopened) != list(before):
            raise ValueError('Archive entry list or order changed')
        if any(digest(reopened[name]) != sha for name, sha in unchanged.items()):
            raise ValueError('A protected entry changed')
        if any(png(reopened[c['target']]).size != tuple(c['size']) for c in changes):
            raise ValueError('Image geometry changed')
        sheet = Image.new('RGB', (800, 270 * len(pairs)), '#e6e6e6')
        draw = ImageDraw.Draw(sheet)
        for index, (target, original, source) in enumerate(pairs):
            for column, picture in enumerate((original, source)):
                picture = ImageOps.contain(picture, (380, 230))
                x, y = column * 400 + 10, index * 270 + 30
                sheet.paste(picture, (x, y), picture)
                draw.text((x, index * 270 + 8), ('Before: ' if column == 0 else 'After: ') + target, fill='black')
        sheet.save(work / 'assets-before-after.png')
        report = {
            'template_sha256': digest(template.read_bytes()),
            'output_sha256': digest(result.read_bytes()),
            'changed_images': changes, 'unchanged_entry_count': len(unchanged),
            'unchanged_entry_sha256': unchanged,
            'checks': {'zip_reopened': True, 'same_entry_order': True,
                       'all_non_image_data_byte_identical': True,
                       'unchanged_images_byte_identical': True,
                       'replacement_dimensions_preserved': True},
            'limitations': ['Not tested on an Android device or Baidu IME.',
                           'Preview is an asset contact sheet, not a keyboard render.',
                           'Layout, key actions, metadata, CSS and TIL slices are unchanged.',
                           'PNG replacement does not guarantee legibility, contrast or visual suitability.',
                           'Template and input image reuse rights must be checked separately.']}
        (work / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        work.rename(output)
        return report
    finally:
        if work.exists():
            shutil.rmtree(work)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    listing = sub.add_parser('inspect')
    listing.add_argument('--template', required=True, type=Path)
    generating = sub.add_parser('build')
    generating.add_argument('--template', required=True, type=Path)
    generating.add_argument('--plan', required=True, type=Path)
    generating.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'inspect':
            print(json.dumps(inspect(args.template), indent=2))
        else:
            report = build(args.template, args.plan, args.output)
            print(json.dumps({'output': str(args.output), 'checks': report['checks']}, indent=2))
    except (ValueError, OSError, zipfile.BadZipFile, KeyError, TypeError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
