# 流光玻璃15

An original iOS-inspired visual treatment, not an Apple skin or proprietary asset reuse. The base is v14: Chinese nine-key clear button, native Android toolbar, input mappings and original sounds are retained.

```
python scripts/cloud/glass_visuals.py artifacts/star14/mist-star-clear-14.bds artifacts/glass-visuals
python scripts/cloud/glass_effects.py artifacts/glass-visuals/glass-visuals.bds artifacts/glass15
node scripts/cloud/check-glass.mjs artifacts/glass-visuals/glass-visuals.bds artifacts/glass15/glass-ripple-15.bds
node scripts/cloud/render-demo.mjs artifacts/glass15/glass-ripple-15.bds artifacts/glass15/keyboard
KEYSKIN_CAND=1 node scripts/cloud/render-demo.mjs artifacts/glass15/glass-ripple-15.bds artifacts/glass15/toolbar
python scripts/cloud/glass_demo_preview.py artifacts/glass15/glass-ripple-15.bds artifacts/glass15/keyboard artifacts/glass15/toolbar/light-cand.png artifacts/glass15/delivery-preview
```

## Effects

- Original 14-frame ripple GIF, 420ms, two pale rings with a slight drift. It replaces the star asset.
- Existing ANIM_STYLE selects a parallel 98% scale + 2px downward translation; release returns over 150ms.
- Separate PRESS_STYLE triggers the ripple, using the native additive press-effect slot instead of placing a GIF inside a transform group. See src/preview-items.ts and tests/preview-surface-height.test.mjs.
- The new preedit clear button remains free of decorative effects. Its F40 and delete sound are preserved.
- Original three Ogg sounds are byte-identical.

## Verification boundaries

The glass is a rendered translucent/frosted visual treatment, not live OS backdrop blur. Existing input fields and actions are compared semantically; only PRESS_STYLE is added. Transform graphs, frame path and 580 press bindings are checked using KeySkin models. Still images use the actual editor renderer. The GIF demonstration composites the packaged frames on an editor render and is explicitly labeled as an illustration; it does not verify native animation timing or placement.

The user reported v11 star visibility and v13 toolbar presence, but that is not verification of this new ripple slot, transform combination, repeated pressing, cancellation or native clipping. Actual Android rendering and effects need a phone check. F14 shortcut contents/order remain controlled by Baidu client settings. No dark-mode/tablet/handwriting support is newly claimed.
