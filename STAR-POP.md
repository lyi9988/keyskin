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

## Prominent star + native toolbar (v13)

```
python scripts/cloud/star_pop.py artifacts/mist-lilac/mist-lilac.bds artifacts/star12 --prominent
python scripts/cloud/add_native_toolbar.py artifacts/star12/mist-star-12.bds artifacts/star13
node scripts/cloud/check-toolbar.mjs artifacts/star12/mist-star-12.bds artifacts/star13/mist-star-toolbar-13.bds
KEYSKIN_CAND=1 node scripts/cloud/render-demo.mjs artifacts/star13/mist-star-toolbar-13.bds artifacts/star13/toolbar-preview
```

The original star becomes 1.75× larger, yellow with a purple outline, and lasts 720 ms. The user reported seeing the v11 effect; v13 visibility and repeated typing are not yet device-verified.

The native candidate toolbar adds F31 menu, F14 client-managed functions and F8 hide for the idle state (PERSIST=1), switching to candidate expansion F9 while composing (PERSIST=2). Candidate padding reserves the expansion button. The package includes original bitmap-index artwork for emoji, keyboard, microphone, search, editing, clipboard and hide, plus logo.ini VERSION=1. The actual functions, number and order in F14 are controlled by the user's Baidu settings; the preview shows the available atlas icons and does not guarantee all will be pinned on the phone. Keyboard layouts and actions remain byte-identical. gen.ini gains only LOGO, not different candidate geometry. The reader checks F14 geometry, visibility switching and required icon indexes against the upstream native model.
