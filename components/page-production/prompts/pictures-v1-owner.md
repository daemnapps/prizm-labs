# PAGE PRODUCTION — WHICH FILED 3D PRINT CARRIES EACH PICTURE (v1)

Every picture on our pages comes from image production's 3D process: a scene built in 3D at true sizes, printed into
a photo, filed as a set. Nothing is generated outside it. Below are the page's picture slots (what each must show)
and every 3D print the brand has filed and kept.

For each slot, pick the ONE filed print that already shows what the slot needs — the same kind of subject, doing the
same thing, close enough that a reader would take it as that picture — or say none fits. Rules:

- A print that carries words, signs, badges or a sale on it fits only a slot about that exact thing. A page picture
  carries no words, so prefer prints without signage.
- A print made for a seasonal sale (holiday, Black Friday) fits only if the slot is about the same moment.
- People: the slot's person must match the print's person in kind (age, look). Never stretch.
- The same print may serve two slots only if both slots ask for the same picture.
- When none fits, write `none` and say in `print_brief` exactly what the 3D set must hold for this slot: the place,
  the props at real size, the person (from our cast if one fits), the product and its pose, the camera and the light.

Return ONE json block and nothing else:

```json
{"slots": [{"slot": "s3-p1", "set": "set name | none", "why": "one line", "print_brief": "only when none"}]}
```

## The page's picture slots
```json
{slots}
```

## The brand's filed, kept 3D prints
```json
{sets}
```
