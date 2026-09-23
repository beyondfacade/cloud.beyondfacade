# Metabole landing artwork

Original offline Blender artwork created for the Seoul commercial atlas landing.
The ceramic city, Han River, bridges, neighborhood shops, trees and observation
tower are a conceptual illustration. They are not geographic boundaries, actual
store locations, observed building heights, or visualized statistics.

## Reproduce

Run from the repository root with Blender 5.x and Python with Pillow installed:

```bash
blender --background --factory-startup --threads 8 --python frontend/art/landing/build_scene.py
python3 frontend/art/landing/prepare_assets.py
```

The script writes editable, compressed `seoul-atlas.blend` and
`location-pin.blend` here. Original transparent PNG renders are written to
`/tmp/metabole-landing-renders`; set `METABOLE_RENDER_DIR` to use another output
directory. `METABOLE_SAMPLES` controls offline Cycles quality (default 96).
`METABOLE_RENDER_PERCENT` may be used for previews; restore 100 before converting
the assets, since the converter checks the agreed image dimensions.

Published assets:

| File | Dimensions | Use |
|---|---|---|
| `public/landing/seoul-diorama.webp` | 1600×1400 | Main transparent city illustration |
| `public/landing/location-pin.webp` | 256×320 | Separate decorative floating pin |

All meshes, materials and lighting are created by `build_scene.py`. There are no
downloaded textures or third-party models. The `.blend` files stay outside
`public/` and are not downloaded by visitors. The browser only displays WebP
images and CSS animations; it does not run a 3D renderer. Text, navigation and
feature labels remain HTML and work independently of the artwork. Mobile and
reduced-motion layouts use the still composition.
