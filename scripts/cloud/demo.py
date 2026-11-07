"""Create an original procedural PNG, then apply it to the bundled BDS for local QA."""
import argparse
import json
from pathlib import Path
from PIL import Image
from bds_visual import build

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/cloud-demo')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
# Original test art, not copied from another skin or an artist's image.
image = Image.new('RGB', (480, 312))
for y in range(image.height):
    for x in range(image.width):
        t = (x + y) / (image.width + image.height - 2)
        image.putpixel((x, y), (int(235 - 35 * t), int(245 - 17 * t), int(252 - 7 * t)))
image.save(args.output / 'original-background.png')
plan = args.output / 'plan.json'
plan.write_text(json.dumps({'replacements': [
    {'target': 'res/back1.png', 'image': 'original-background.png', 'fit': 'cover'}
]}, indent=2))
report = build(ROOT / 'public/default-template.bds', plan, args.output / 'result')
print(json.dumps({'output': str(args.output / 'result'), 'checks': report['checks']}, indent=2))
