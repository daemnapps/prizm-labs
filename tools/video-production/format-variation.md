# FORMAT VARIATION PLAYBOOK
## Re-styling an Approved Micro-Drama into a New Visual Format (e.g., 1950s Disney Cel)
*Worked example: "Steam and Proof" (a brand) — live-action → 1950s hand-drawn cel animation*

---

## 1. THE PRINCIPLE (read this first)

A format variation is **NOT a new film**. It is the SAME film with a new visual
rendering. Everything the audience hears and understands stays identical; only how it
looks changes.

**One sentence: the screenplay, blocking, dialogue, mechanics, product truth, and edit
are frozen; the character designs, world design, and motion language are swapped.**

If you find yourself rewriting shots, changing blocking, or re-planning the film — stop.
You are doing a remake, not a variation. That mistake produced the "slop" run.

---

## 2. WHAT TRANSFERS 1:1 (never touch)

| Element | Why it's frozen |
|---|---|
| **Screenplay / dialogue** (verbatim) | The audience's emotional story. Every line approved in the Director's Cut stays byte-identical. |
| **Blocking mechanics** | Door ledger (who enters when), position ledger (who is where per clip), screen order, camera axis rule. Same room geometry = same blocking. |
| **Tube / product mechanics** | Squeeze → set tube down → rub → rinse → fade; one handoff; label legibility. |
| **Offer rules** | No profanity; offer never claims product made in Thailand; recipe-origin line allowed only in story beats. |
| **Wardrobe locks** | The locked outfit per character persists (robe / tank / blouse-skirt / teal-bun-no-hat) — restyled, never redesigned. |
| **Duration / aspect / resolution** | Same clip durations, 9:16, 1080p, hard cuts. |
| **Editing workflow** | The edit decision list, J-cuts, trim rules, QC gate — all transfer unchanged. |

---

## 3. WHAT CHANGES (the swap)

1. **Style formula** — one canonical string describing the target look (e.g., the
   1950s cel formula). Byte-identical across every asset and every clip prompt.
2. **Character designs** — the REAL cast is converted into the new style, keeping
   recognizable identity (same person, drawn differently).
3. **World design** — the location plate is converted to the style (painted matte,
   ink lines, etc.), preserving exact spatial layout so blocking still matches.
4. **Prop designs** — the REAL product (tube + paste) converted to the style, label
   kept legible, product identity preserved.
5. **Motion language** — the animation's movement rules (cel = on-twos, squash-and-
   stretch; 3D = different timing). This is a separate axis from the visual style.

---

## 4. THE PIPELINE (proven order)

```
STEP 0 — STYLE CHOICE GATE (user picks the target style; one question, no debate)
STEP 1 — STYLE FORMULA (enhancer writes the canonical string; user approves verbatim)
STEP 2 — CHARACTER CONVERSION (the subtle step — see §5)
STEP 3 — LOCATION CONVERSION (from the APPROVED plate, not a fresh render)
STEP 4 — PROP CONVERSION (from the REAL product photos, not an invented version)
STEP 5 — CLIP REGENERATION (see §6 — the step where slop happened)
STEP 6 — ASSEMBLY + QC (same edit workflow, same gates)
```

### STEP 2 — Character conversion (identity-preserving restyle)

- Source = the REFINED identity baselines (the real cast photos / trained Souls),
  NEVER a fresh text-described character.
- Process: take each real photo → stylize into the target style via the style
  formula + identity-preservation language ("same face, same hair, same features;
  only rendering changes").
- **Failure mode observed:** generating a new "raw base" from a text description
  produced characters that were NOT the approved people. The user's correction was
  absolute: "use the baselines we already spent time to refine and build."
- Same rule for location (convert the approved bathroom plate, not a new room) and
  props (convert the real product tube, not an invented bottle).

### STEP 3 — Location conversion
- Take the approved location plate from the original film → stylize with the formula.
- **Preserve spatial layout exactly** (sink, mirror, shower curtain, door positions)
  so the blocking ledger still holds.

### STEP 4 — Prop conversion
- Take the REAL product photo → stylize. Label stays legible and ungarbled.
- **Failure mode observed:** a text-generated "bottle" replaced the real product
  tube — user: "why would you use a bottle that is not the <brand> bottle."

---

## 5. STEP 5 — CLIP REGENERATION (the exact procedure, including the fix)

### THE ONE TRUE WAY (what works)

1. Take the FINAL APPROVED live-action clip prompts (the ones the user approved —
   every word, every camera move, every mechanic).
2. **Swap ONLY the reference media** in the `medias` array:
   - live-action character photos → styled character designs
   - live-action bathroom plate → styled location plate
   - live-action product photo → styled product design
3. **Add a STYLE LOCK block at the very top of each prompt** (see §6).
4. **REMOVE all photoreal descriptors** from the prompt text (see §7).
5. Submit, poll, assemble — same as the original run.

### THE FAILURE MODE (what caused the "slop" run — do not repeat)

Running the variation through a DIFFERENT production pipeline (e.g., a new animation
workflow with its own shot planner) **re-planned the film**: new shot structure, new
framing, paraphrased dialogue, different pacing. The result looked like a different
film — "slop". The user's correction: "you did not run it based on what we had before
with a simple character style swap, that was literally the only change that needed to
happen."

**Rule: the variation reuses the original prompts verbatim. No re-planning, no
re-structuring, no paraphrase.**

---

## 6. THE STYLE LOCK BLOCK (mandatory, every clip prompt)

Paste at the top of every clip prompt, before anything else:

```
STYLE LOCK (absolute — overrides everything below): <style formula>
@Image2/@Image3/... are the characters in this style: clean tapered ink outlines,
flat three-value cel shading, crisp shadow shapes, warm nostalgic palette,
occasional line-boil, hand-drawn cel characters, ON-TWOS stepped motion with
squash-and-stretch, painted matte background. NO photographic detail, NO skin pores,
NO photoreal skin texture, NO realistic shading, NO photorealism, NO depth-of-field,
NO live-action look. The characters are flat hand-drawn cartoon cels, NOT real people.
```

**Why:** the reference images alone do not lock the style — the prompt text's other
descriptors fight them. Without the lock, some clips resolve back toward photoreal
(the user's exact complaint: "Susan still looks like a real person in some clips, you
didn't lock it in").

---

## 7. REMOVE THESE PHOTOREAL DESCRIPTORS (they sabotage the cel lock)

When converting a live-action film into an animation format, strip or replace:

| Photoreal language (remove) | Cel replacement (use) |
|---|---|
| Camera/sensor/lens (ARRI Alexa, Cooke, Sony DVCAM, 50mm f/2.8) | "hand-drawn cel camera, locked-off" |
| "warm peachy skin tones, lifted blacks, highlight bloom" | "flat cel shading, crisp shadow shapes" |
| "pore-level skin detail", "wet eye catchlights", "natural skin texture" | "flat cel shading, ink outlines, no skin texture" |
| "photorealistic", "realistic shading", "film grain", "bokeh" | "hand-drawn, flat, painted matte" |
| "smooth gradients", "volumetric light" | "flat colors, hard shadow shapes" |

Rule of thumb: if the descriptor would apply to a live-action film, it fights the
animation style. Replace it with the style formula's vocabulary.

---

## 8. QC GATE FOR VARIATIONS (run before delivery)

1. **Style consistency** — every clip reads as the same style (check each clip
   against the formula, not just one).
2. **Identity hold** — each character is recognizable as the same person across all
   clips (compare to the approved real photos).
3. **No photoreal leakage** — scan for any clip where skin/hair/lighting reads real.
4. **Dialogue verbatim** — every line matches the approved screenplay; no paraphrase.
5. **Mechanics held** — door ledger, no double entry, no one scrubs the husband in
   clip 4, one handoff, no Thailand in the offer.
6. **Product integrity** — tube label legible, paste dark brown grainy.
7. **Blocking continuity** — screen order and camera side consistent per clip.

---

## 9. SCALING ACROSS FORMATS (the template)

For any new target style (3D Pixar, anime, stop-motion, noir, retro-comic, etc.):

1. Run STEP 0 (style gate) → STEP 1 (style formula).
2. Convert baselines FROM THE REFINED SOURCES (characters from real photos, location
   from the approved plate, product from real photos).
3. Reuse the original clip prompts verbatim with only media swapped + style lock
   added + photoreal descriptors removed.
4. Keep the same edit workflow and QC gate.

**The three documents that make this repeatable:**
- **Director's Cut** — the frozen screenplay, ledgers, per-clip mechanics (the "what").
- **Prompt Structure Guide** — the 11-section prompt skeleton and constants (the "how").
- **Format Variation Playbook** (this document) — how to swap formats cleanly (the "swap").

*End of playbook.*