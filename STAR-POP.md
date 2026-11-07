# 雾紫星星11: native frame-animation test

This test is based on v10, which the user reports can type normally. It is not a claim of Android animation validation.

```
npm ci
npm run skin:mist -- --output artifacts/mist-lilac
python scripts/cloud/star_pop.py artifacts/mist-lilac/mist-lilac.bds artifacts/star11
node scripts/cloud/check-star-pop.mjs artifacts/mist-lilac/mist-lilac.bds artifacts/star11/mist-star-11.bds
```

The script draws an original smiling star from geometric primitives into a transparent 12-frame GIF (480 ms). It changes the existing shared PRESS_ANIM from scale animation 1 to frame animation 3. The existing release scale, pressed keycap artwork and sounds remain. All 30 portrait/landscape layout files, actions, SHOW/LIST configuration, artwork and sounds are byte-identical to the input. The checker resolves all 580 press bindings to the packaged GIF.

Implementation evidence: `src/legacy-animation.ts` recognizes CATEGORY=2 and ANIM_PATH; `src/legacy-animation-binding.ts` resolves the existing key → style → PRESS_ANIM chain. GIF intrinsic frame timing is independently decoded and checked. No speculative mixed GIF/scale composite or positioning fields are emitted.

Limitations: the precise native GIF anchor, clipping, quick press/release interruption and simultaneous presses are unverified. The KEY press scale is intentionally replaced by the GIF, not combined with it. The stock keyboard preview does not render this GIF path; any composited image/GIF is explicitly an effect illustration, not native runtime proof. Native import and actual animation need a phone test; keep v10 available for rollback. No typing regression is claimed solely from static checks.
