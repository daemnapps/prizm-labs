# Icon / game-art set

**Higgsfield first:** character-sheet / style sheet → batch generate → Ideogram Vector (SVG) or Recraft styles; autosprite when the icons animate.

| Stage | Skills | Output |
|---|---|---|
| 1. References | his or the client's refs; game-icons.net, Kenney, Streamline/Icons8 (plugins) | Reference board → **he picks** |
| 2. Style sheet | Higgsfield `generate_image` — one sheet: palette, outline weight, lighting, perspective | Sheet → **he picks** |
| 3. Full set | Higgsfield batch on the sheet, one icon per prompt, same seed/style ref | Grid |
| 4. Clean | `remove_background`, `upscale_image`; SVG trace where a vector is needed | Transparent PNG + SVG |
| 5. Deliver | icon grid page + zip | Page + files |
