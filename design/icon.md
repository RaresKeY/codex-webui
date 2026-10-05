# Application icon

The primary application icon is `icon.png`: a warm ivory coding chat bubble on a charcoal rounded tile, with transparency outside the tile. The previous icon is preserved as `icon-v1.png`.

`frontend/public/favicon-v2.png` contains the same 1254×1254 RGBA PNG. The document's favicon link and sidebar brand consume that asset. The versioned URL avoids stale browser caching. The original `frontend/public/favicon.png` remains as an unused legacy asset.

## Generation

Generated with the built-in `image_gen` tool, with transparent background enabled; no CLI fallback was used. The selected output is copied into the project without pixel edits.

Final prompt:

```text
Use case: logo-brand
Asset type: a square raster application icon for Codex WebUI 2, also readable as a browser favicon.
Primary request: create one distinctive, clean coding-chat icon that suits a quiet charcoal ChatGPT-like interface.
Subject: one bold ivory chat-bubble glyph incorporating a pair of simple code chevrons as its central cutout; unify the bubble and coding symbol into one balanced mark.
Style/medium: polished minimal flat app-icon artwork, crisp silhouette, broad strokes and generous negative space.
Composition/framing: centered inside an opaque charcoal rounded-square tile with even padding; genuinely transparent canvas outside the rounded tile. Square image, front view.
Color palette: the existing interface's neutral charcoal and warm off-white, with restrained tonal depth.
Constraints: one icon only; remain recognizable at 16 and 32 pixels; no text, letters, numbers, gradients with bright colors, tiny details, external branding, watermark, mockup, or presentation grid.
```

## Gaps

- No optimized small bitmap derivatives; the browser downsamples the original PNG.
