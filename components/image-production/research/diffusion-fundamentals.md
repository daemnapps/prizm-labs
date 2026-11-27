# How picture models read a prompt, and what that means for our chain

Research, 2026-10-28. Companion to `movie-level-depth.md` (same folder). Written for every picture the line makes: static ads,
video start frames, product shots. Brand-agnostic.

**The finding that started it:** a scene built in 3D at true sizes and light, then printed into a real photo by an image model
with a product reference sheet, had no product slop, no size errors and no pasted-on look. The same scene described in words
did. The research below says why that is expected, not luck.

**The short answer:** a picture model is good at *what things look like* and bad at *where things are, how big they are and
where the light comes from*. Words carry appearance well and geometry badly. Pixels carry geometry well. So: geometry, size,
depth, contact and light go in as a picture (a 3D render, a print, a first frame); words carry identity, material, mood and
the one change; and anything that must be exact (words, a label) is laid on afterwards, never asked for.

Lines marked *(practice)* are our own synthesis from the sourced principles or from our own runs, not a quoted source.

---

## 1. Principles (plain English, each with its source)

1. **Words are read as a whole, not as instructions in order, and older encoders barely read past the start.** The CLIP
   text encoder that classic diffusion models use stops at 77 tokens and in practice uses fewer than 20 of them well; words
   late in a long prompt carry little weight. ([Long-CLIP, arXiv 2403.15378](https://arxiv.org/abs/2403.15378)). Newer
   diffusion transformers add a large language encoder (T5) next to CLIP, which mostly improves following long prompts and
   spelling ([SD3 paper, arXiv 2403.03206](https://arxiv.org/abs/2403.03206);
   [Stability summary](https://stability.ai/news/stable-diffusion-3-research-paper)). Language-model image makers (GPT
   Image, Gemini image) read long prompts far better, but language models still weigh the start and end of a long input
   more than the middle ([Lost in the Middle, arXiv 2307.03172](https://arxiv.org/abs/2307.03172)). **Rule: the things that
   must be right go first and are restated in one line at the end; decoration goes in the middle or nowhere.**

2. **Layout is decided in the first moments of making the picture, from the words' attention maps; later steps only add
   detail.** ([Prompt-to-Prompt, arXiv 2208.01626](https://arxiv.org/abs/2208.01626),
   [project page](https://prompt-to-prompt.github.io)). So a prompt that leaves the layout vague gets the model's average
   layout, usually centred and symmetric (Seedream sheet, `inputs/seedream-5-pro-edit.json`, from
   [fal's Seedream 5 Pro guide](https://fal.ai/learn/tools/how-to-use-seedream-5-0-pro-v2)). **Rule: give the layout as a
   picture (IMAGE 1) whenever position or size matters.**

3. **Models drop subjects and mix up which word belongs to which thing.** With several objects, one is often left out
   ("catastrophic neglect") and colours or materials land on the wrong object
   ([Attend-and-Excite, arXiv 2301.13826](https://arxiv.org/abs/2301.13826);
   [T2I-CompBench, arXiv 2307.06350](https://arxiv.org/abs/2307.06350)). **Rule: few objects per pass; each object named
   once, with its attributes right next to it.**

4. **Position, count and relative size are the weakest skills, and words do not fix them.** On GenEval, older open models
   score 0.07 to 0.15 on position and about 0.4 on counting ([SPRIGHT, arXiv 2404.01197](https://arxiv.org/abs/2404.01197)).
   A 2026 benchmark of relative object scale finds that current generators and editors "cannot reliably observe relative
   scale yet" ([GenScale, arXiv 2609.00525](https://arxiv.org/abs/2609.00525)); OpenAI lists the same weakness for its own
   model: it "may have difficulty placing elements precisely in structured or layout-sensitive compositions"
   ([OpenAI image generation guide](https://developers.openai.com/api/docs/guides/image-generation)). **Rule: "X is 12 cm
   tall" in a prompt is a hint, never a lock. True size comes from a 3D set, or from a reference photo that shows the
   thing at scale against a hand.**

5. **"No X" often makes X.** Negation is rare in training captions; the text side can understand "a room without a cat" and
   the image side still draws the cat
   ([Contrastive Prompts, arXiv 2402.13490](https://arxiv.org/abs/2402.13490);
   [negative-prompt timing, arXiv 2406.02965](https://arxiv.org/abs/2406.02965);
   [circuit-tracing, arXiv 2606.15796](https://arxiv.org/abs/2606.15796)). Seedance's guide also warns that long
   blacklists "compete with the scene" (`inputs/seedance-2.5.json`). **Rule: say the state you want ("matte skin with
   visible pores"), not the list of things you fear ("never waxy, plastic, glossy"). Keep negatives to one short
   exclusion line at the end: no extra text, no watermark, no logos.**

6. **A reference picture is read as appearance, not as measurements.** Image prompts enter the model through their own
   attention path beside the words, and by default they carry look, identity and style more than exact layout
   ([IP-Adapter, arXiv 2308.06721](https://arxiv.org/abs/2308.06721)). Edit models built on language models (GPT Image,
   Gemini) take many references and combine them by the roles the words give them
   ([OpenAI prompting guide](https://developers.openai.com/api/docs/guides/image-prompting);
   [Gemini image docs](https://ai.google.dev/gemini-api/docs/image-generation)). **Rule: every IMAGE n has one job and one
   "do not take" line; only one image may define the layout.**

7. **Starting from a picture trades faithfulness for realism.** Image-to-image adds noise to the start picture and redraws
   it: more noise, more realistic and less faithful; less noise, more faithful and closer to the start's flaws
   ([SDEdit, arXiv 2108.01073](https://arxiv.org/abs/2108.01073)). Edit models without a strength setting make that choice
   from the words, which is why "change only X, keep everything else" matters
   ([OpenAI prompting guide](https://developers.openai.com/api/docs/guides/image-prompting)). **Rule: the 3D render is the
   structure; the print's words tell the model how far it may redraw (materials and light: yes; layout and sizes: no).**

8. **Real control inputs lock structure in a way words cannot.** ControlNet feeds a depth, edge, segmentation or pose map
   into a frozen model through a trained copy of its encoder
   ([ControlNet, arXiv 2302.05543](https://arxiv.org/abs/2302.05543)); its strength and the share of steps it acts on
   (`controlnet_conditioning_scale`, `control_guidance_start/end`, 0.0 to 1.0 of the steps) set how hard it holds
   ([diffusers ControlNet docs](https://huggingface.co/docs/diffusers/api/pipelines/controlnet_flux)). Because layout is
   set early (principle 2), ending control early keeps the layout and frees the detail
   ([Flick – Blender for AI filmmaking](https://flick.art/blog/blender-ai-filmmaking), cited in `movie-level-depth.md`).
   **None of the four models behind our doors takes a depth map as a control channel** (section 2).

9. **Every edit pass drifts; exact pixels are composited, not prompted.** OpenAI: repeated edits drift; restate the
   constraints each pass; "if a region must stay pixel-identical, composite the approved edit into the original"; masks are
   "guidance" and "may not follow its exact shape"
   ([OpenAI prompting guide](https://developers.openai.com/api/docs/guides/image-prompting),
   [OpenAI image generation guide](https://developers.openai.com/api/docs/guides/image-generation)). **Rule: one change per
   pass, the full keep-list each time, and words, logos and labels laid on top afterwards.**

10. **Text inside a picture is copied as picture content.** A model draws what it reads, including names, dates and quotes in
    the prompt (our own avoid rule `author-quotes`, `inputs/gpt-image-2.5.json`) and lettering printed on a reference
    image *(practice)*. **Rule: no names, dates or quotes in a prompt; reference sheets carry no titles or captions the model
    could copy, or the role line says their writing is a note, never drawn.**

---

## 2. What each model we use does and does not take

| Model (our door) | What it is | Takes | Does NOT take | Prompt reading | Source |
|---|---|---|---|---|---|
| **GPT Image 2.5** (Higgsfield `gpt_image_2_5`; OpenAI direct last rung) | OpenAI's image model inside a language model; OpenAI describes its 4o-era image maker as "a native modality", reported autoregressive. Architecture of 2.5 not published. | Up to 16 images (OpenAI); a prompt up to 32,000 characters; a mask on the FIRST image (OpenAI door only), used as guidance | Depth, edge or pose maps as control; strength / denoise; `input_fidelity` on 2.x; mask on the Higgsfield door; exact WxH on Higgsfield | Long structured prompts work; labelled sections; numbered inputs with roles; result first | [OpenAI guide](https://developers.openai.com/api/docs/guides/image-generation), [prompting](https://developers.openai.com/api/docs/guides/image-prompting), [4o image generation](https://openai.com/index/introducing-4o-image-generation/), `inputs/gpt-image-2.5.json` |
| **Seedream 5 Pro** (Higgsfield `seedream_v5_pro`; ladder rung 2) | ByteDance diffusion transformer (DiT + high-compression VAE) with a vision-language model that expands the prompt | Up to 10 references on Higgsfield; ByteDance says the family reads "Canny, Depth, Mask, and other visual signals" and sketches natively, without ControlNet | A separate control channel or strength; more than 10 images (extras are cut) | Overloaded prompts drop instructions; refer by number; photographer's order (subject, camera, light, finish) | [Seedream 4.0 blog](https://seed.bytedance.com/en/blog/seedream-4-0-officially-released-beyond-drawing-into-imagination), [Seedream 4.0 report arXiv 2509.20427](https://arxiv.org/abs/2509.20427), `inputs/seedream-5-pro-edit.json` |
| **3D Jutsu "angles"** (`scene_builder_3d_generate_angles`) | The print step: Seedream 5 Pro pricing, run on a render from the 3D scene | ONE render (any PNG/JPEG the scene published, so a beauty, clay, or depth render) + ONE optional reference image; prompt up to 20,000 characters; 1k / 1.5k / 2k | A second reference; masks; strength | The render is the structure; the words say what to keep and what not to inherit ("its grey materials, proxy geometry or lighting") | Higgsfield tool schema (read 2026-10-28), [3D Jutsu blog](https://higgsfield.ai/blog/higgsfield-3d-jutsu) |
| **Nano Banana Pro** (Gemini 3 Pro Image; ladder rung 3) | Gemini's image model, thinking always on | Up to 14 images in total, of which up to 6 objects at "high-fidelity" and 3 style images; 1K / 2K / 4K (capital K) | Masks; depth maps; any control channel | Full sentences, not keywords; give each image a role; one change at a time | [Gemini image docs](https://ai.google.dev/gemini-api/docs/image-generation), [Google tips](https://blog.google/products/gemini/prompting-tips-nano-banana-pro/), `inputs/gemini-3-pro-image.json` |
| **Seedance 2.5** (video; start frames) | ByteDance video model | A first frame (locks the composition and aspect), a last frame, up to 30 images, up to 10 reference videos (camera move), audio | Depth maps; a still's words (spelling is unreliable) | Number every file with its job and what it must NOT pass on; a timeline; one dominant move per shot; "when a reference is accurate, say to use it; do not describe it again" | [BytePlus Seedance 2.5 guide](https://docs.byteplus.com/en/docs/modelark/seedance-2-5-prompt-guide), [Higgsfield Seedance 2.5 guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide), `inputs/seedance-2.5.json` |
| **FLUX.1 Depth / Canny** (not wired; fal, Replicate, BFL) | Black Forest Labs' structure-conditioned models | A depth map or edge map as a real control input, plus a prompt | Our cast and product references (one image path) | Short prompt; structure from the map | [FLUX.1 Tools coverage](https://www.maginative.com/article/black-forest-labs-introduces-flux-1-tools-for-ai-image-editing/) |

The Higgsfield image catalog search for "depth map / control / canny" (2026-10-28) returned no ControlNet-style model; only
Seedream 4.5 tagged "control". So for us, **the depth lock is the 3D render itself**, used as IMAGE 1 or as the print's input.

---

## 3. The rules, ranked by impact on accuracy

| # | Rule | Where it goes (file :: function) | What changes |
|---|---|---|---|
| 1 | **Geometry from pixels, never from words.** A picture goes through a 3D set and a print first when any of these hold: the product is in frame beside a hand, face or other object whose size it must match; two or more objects whose relative size matters; the product rests on or touches a surface (contact, shadow); a person is placed into a room that is not the swipe's own photo; the shot will become a clip with a camera move. (Principles 2, 4, 8) | `model-inputs/preview.py :: make_picture` (the `set_print` branch) and `image-production/picture_sets.py :: needs` | Today, no kept print means a silent fallback to words (`plain.generate`). Instead: when the swap list says product in frame or a person into a new room and `set_print` returns nothing, record a "needs a set" flag on the picture (amber, per PSH-8, outputs never stop) and show it on the board, so a set is built before the next take. |
| 2 | **One image owns the layout.** IMAGE 1 is the only structure source: the print when there is a set, else the swipe. Every other image is look-only and says so. (Principle 6) | `model-inputs/preview.py :: build_picture` (`refs[0]`), `image-production/image_production/plain.py :: plan` | When a set print exists and the picture is still generated (a cast member into the print), IMAGE 1 = the print; the swipe moves to a later slot as "its look, grain and colour only, not its layout or sizes" or is dropped. |
| 3 | **Front-load what must be right.** Order: INPUTS → THE PICTURE (result, subject, layout source) → THE PRODUCT lock → THE PEOPLE identity → THE FRAME → light facts → feeling, dials, techniques → RULES, ending with one line that restates the product and face locks. (Principles 1, 3) | `image-production/image_production/plain.py :: prompt` (the `secs` order) | Today the sheet sections (WHAT STAYS, THE FEELING, THE DIALS, TECHNIQUES) sit between THE PICTURE and THE PRODUCT, pushing the geometry lock into the middle. Move THE PRODUCT and THE PEOPLE up; add a one-line restatement at the end of RULES. |
| 4 | **Word every reference with a job and a "do not take".** `IMAGE n is <what>: take <X> from it; do not take <Y>.` (Principle 6; OpenAI, Gemini, Seedance guides) | `plain.py :: product` (`SHEET_SAYS`), `plain.py :: labels`, `preview.py :: build_picture` (`says[...]`) | `SHEET_SAYS` names what to copy but not what to leave: add "do not copy its layout, white background, labels of the sheet or its light". Cast sheet and skin lines already do this; give the same shape to product photos and library pieces. |
| 5 | **State the wanted state; one short exclusion line.** Turn "never X" lists into the positive (principle 5). Keep "no extra text, no watermark, no logos" as the only negatives. | `plain.py :: product` (`never_show` line), `preview.py :: build_picture` (the ONE PHOTOGRAPH and REAL PEOPLE `rules_lines`), `inputs/*.json` `avoid` | Rewrite "Never show X: ..." as "X is always <how it really is>"; "never smoothed, waxy, airbrushed, plastic" as "matte, unretouched skin with pores and fine lines". Add an avoid row `negation-stack` (warn when a prompt has more than ~5 "never/no" clauses) so the checker flags it. |
| 6 | **A length and load budget per model, and re-shape the prompt per rung.** GPT Image: long is fine, every line still competes. Seedream (and the Jutsu print): short; split work into passes (its sheet: "overloaded prompts drop instructions"). Nano Banana: full sentences, medium. Seedance: "the shortest prompt that fully says the shot". (Principle 1) | `inputs/<model>.json` (new `limits.budget_chars`), `model-inputs/input_rules.py :: check`, `image-production/image_production/providers.py :: generate_ladder` | Today every rung gets GPT's prompt unchanged ("same prompt, same references"). Add a per-rung shaping step (trim to the rung's budget, drop decoration sections first, keep locks) and a `check()` warning above the budget. Also cap references per rung by the rung's own limit with the layout image and product sheet kept first (Gemini: 6 high-fidelity object images). |
| 7 | **Size words are a check, never the lock.** Keep `size_cm` in the prompt as a hint; the lock is the set or an in-use photo at scale. (Principle 4) | `plain.py :: product` (the size line), `preview.py :: make_picture` | No wording change needed; the change is rule 1's flag, plus an output check later that measures product height against a hand or face on the finished picture. |
| 8 | **One change per edit pass, and restore what must not move.** The realism pass is a second full redraw of the finished picture; it can move the product, hands and light. (Principles 7, 9) | `model-inputs/preview.py :: finish_people` (`REALISM`) | Composite the realism result back only inside the person (a skin/person mask made locally), keeping the original pixels for product, hands and room; on the OpenAI door, send a mask on IMAGE 1. Also remove the quoted ruling (a name, a date and a quote) inside `REALISM`: it breaks our own `author-quotes` avoid rule. |
| 9 | **Word the print: keep structure, change materials.** Print prompt = "this render is the layout: keep the camera, every object's position and size, the light's direction and colour; make it a real photograph: real materials, texture, wear; the product is IMAGE 2's shape, label and finish; nothing of the render's grey materials, proxy shapes or flat light is kept." (Principle 7; Jutsu blog's "nothing else from the previz ... is inherited") | `image-production/picture_sets.py` (new `print_prompt(set)` builder; record the exact prompt in `set.json` beside each print) | Today the print prompt is written by hand in the session and not stored. Store it with each print so it shows on the board and can be tightened like any other prompt. |
| 10 | **Light as facts from the scene, not mood.** Direction, hardness, colour, what it falls on, where the shadow lands, focus falloff. (Principle 2; `movie-level-depth.md` §4D) | `preview.py :: build_picture` (`sw0.light` → "THE LIGHT ON THE PERSON") | Today only video start frames carry light facts. Read them from the set's record (`set.json` light) for every picture with a set. |
| 11 | **Exact things are laid on, not drawn.** Words, logos and labels go on top (`set_on_top`); a resting product may be the real cut-out. (Principle 9) | `preview.py :: make_picture`, `preview.py :: real_product` | Already the house way for words. When text must be drawn, add "exactly once" (marked "not in yet" in `gpt-image-2.5.json`). |
| 12 | **No writing in reference images.** A reference with a title or caption printed on it invites copied lettering. (Principle 10) | `video-production/machine/product_kit.py` (the sheet's title line), `plain.py :: product` (`SHEET_SAYS`) | Either render a sheet copy with no title for model input, or add "its printed title is a note, never drawn" to its role line. |

---

## 4. Control inputs we could add, and through which model

| Control | What it locks | Through | Status |
|---|---|---|---|
| **3D render as IMAGE 1** | Layout, camera, sizes, contact | GPT Image 2.5 (soft: a role, not a channel) | Live in the print path; extend per rule 2 |
| **3D render as the print's input** | Layout, sizes, light | Jutsu angles (Seedream 5 Pro) | Live (2026-10-28); store the prompt per rule 9 |
| **Depth or clay render as the print's input** | Depth and silhouettes without the grey look | Jutsu angles: the artifact can be any published render, and Seedream reads depth/edge signals natively (ByteDance) | Untested: one A/B, beauty render vs depth render, same prompt |
| **Depth render as an extra labelled IMAGE** ("depth and layout only, no colour or texture from it") | Depth ordering | GPT Image 2.5, Nano Banana Pro | Untested; soft guidance only |
| **True depth / edge control** with strength and end step | Layout held hard, detail free | FLUX.1 Depth / Canny (fal or BFL); not in the Higgsfield catalog | Would need a new door and a Model House row; cannot take our cast and product references, so only for empty plates |
| **Mask on IMAGE 1** | The only area an edit may change | GPT Image 2.5 on the OpenAI door (not Higgsfield) | Use for the realism pass (rule 8) |
| **First frame** | The whole composition of a clip | Seedance 2.5 | Live; the start frame should itself come from a set |
| **Clay video of the camera move** | Camera path and timing | Seedance 2.5 reference video ("for camera movement only") | In `movie-level-depth.md` §4B; not wired |

---

## 5. What never goes in a prompt

- A person's name, a date or a quote from our own rulings (drawn as picture content) — `author-quotes` avoid rule.
- A stack of "never / no / without" clauses (principle 5); one short exclusion line only.
- Exact sizes as the only size control (principle 4).
- Two images that both claim the layout (principle 6).
- A re-description of something a reference already shows accurately (Seedance guide; the words then compete with the picture).
- Studio, cinematic or "8k masterpiece" wording when a real photo is wanted (OpenAI prompting guide; `studio-wording` avoid rule).
- Mood words with no direction, colour or hardness for light (OpenAI prompting guide; Seedream sheet).

## Caveats

- OpenAI has not published GPT Image 2.5's architecture; what is said about language-model image makers comes from OpenAI's
  4o image announcement and third-party write-ups, which disagree on whether a diffusion decoder is involved.
- The "Seedream reads depth natively" claim is ByteDance's own, for Seedream 4.0; not yet confirmed for 5 Pro or through the
  Jutsu angles door.
- The 77-token / 20-token figures apply to CLIP-based models; the models we use run larger text encoders, so the
  front-loading rule rests on the weaker "start and end weigh more" effect, plus our own runs.
- GenScale and the circuit-tracing negation paper are 2026 preprints.
