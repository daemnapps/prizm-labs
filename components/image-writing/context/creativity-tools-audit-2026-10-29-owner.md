# Creativity tools vs the new picture chain — audit, 2026-10-29

Since 2026-10-28 every picture ad is **a 3D set at true sizes → printed into a photo with the product's casting sheet →
the words set on top** (components/image-production CLAUDE.md), and stage 3 v13 opens with **THE CONCEPT** (a
culture-map concept × the moment dresses the swipe; the headline is the concept talking with one spice device). This
page lists each creativity tool, what it still assumed about the old way, what changed, and the new file.

| Tool | What was outdated (the old way) | What changed (what the new way allows) | New file / version |
|---|---|---|---|
| **Headlines** (stage 4b) | Never read THE CONCEPT; image concepts written "for a generator from the sentence alone"; the control's picture was "the source's own photograph"; "her" for the avatar (wrong on a men's brand) | Every headline is the concept talking, one named spice device, never a calendar; the moment's name on a prop belongs to the set, never the headline; image concepts are a change to the 3D set (object, real size in cm, place, material); rung test adds "Plays the concept?"; neutral pronouns | `image-writing/prompts/stage4b-image-hook-v8-owner.md` |
| **Variations** (stage 5) | "Change the approved picture" as a flat edit; light and size as effects; no concept; "what she holds / wears" | Each change written as a set change (object, cm, place, material) so it can be re-printed; all five stay inside the approved concept; a concept prop or the moment's palette counts as a visible change; the sign on a prop never changes; record keys unchanged | `image-writing/prompts/stage4e-image-variations-v9-owner.md` |
| **The brief** (stage 6) | Product "composited from the brand's own photograph"; "the words ARE drawn by the model now" (2026-09-25); camera, light, sizes carried by words; keep-clear zones as "clean background only"; brand palette only; no concept | Product = its own true-size build, printed; words set on top by the board inside the safe zone; camera/sizes/depth/light built in the set, words carry only material and mood; new **THE SET** json block in Document Two (concept, moment palette, camera, light as facts, surfaces, props at cm with signage, product, keep-clear, print line); keep-clear = no prop crosses; moment palette allowed; concept slug in the ad name. Layout block stays first; every other block's shape unchanged | `image-writing/prompts/stage6-image-brief-v12-owner.md` |
| **Brief template** | Section 3 "background, person, product, light" in a few loose lines | Section 3 opens with Concept and Moment palette, then The set (props at cm, the moment's name on its prop), The person, The product (true-size build), Camera and light as facts, How it is made. Same box, same nine sections | `image-writing/templates/brief-standard-static-v3-owner.md` |
| **Culture read** (step 1k, image + video) | Read jokes and references only; nothing named the swipe's moment props or words printed on objects, so stage 3 had to find them itself | Two new lines: **MOMENT MARKERS** (props/colours that mark the post's season, with size, place, printed words) and **WORDS IN THE WORLD** (signs, flags, packages, kept apart from overlay words) | `culture/prompts/stage1k-culture-v5-owner.md` |
| **Creative controls** (dials) | `rhyme` asked for the product "at the ball's size" (breaks true size); `scale_distortion` risk/picture line assumed words could hold a size; `density` "subject on nothing"; no dial for theming | `rhyme`: frame size comes from where the product sits in the set, never from scaling it; `scale_distortion`: built in the set on props, product stays true size; `density`: a set always has a surface; `realism`: the print makes it real. **New dial `dressing`** (0 as swiped → 4 the world built; default 3, native posts 1). New techniques **in-world-signage**, **moment-dressing**, **true-scale-set**; new bar move **moment-world-dressed**; new rule **dressing-keeps-the-layout** | `creative-controls/controls.json` (all new entries `draft`), re-rendered `slices/controls.md` |
| **Glossary** | No names for the set-and-print way | New domain "Set and production design": previs/blockout, set dressing, production design, hero prop, diegetic text (in-world signage), moment marketing, colour script, motivated light (marked "from memory, check before quoting") | `creative-controls/glossary.json`, re-rendered `GLOSSARY.md` |
| **Picture dials** | Every dial said as words to the picture model, light as "hard light", sizes as "too big"; density 0 "plain background" | Each picture dial now says where it is made (`built_in`: set / print / cast) and, for set dials, what to build per level (key light angle and hardness, prop count, camera distance, a prop's modelled size); new `dressing` dial; the word lines stay for a picture made without a set | `model-inputs/picture-dials.json` |
| **Spice** (language layer `spice` stage) | Nothing: it is a bank of the avatar's words, not picture-making | No change. Headlines and variations now name the spice device they use | none |
| **Writers' Room** | Not in this workspace (it lives in the owner's own repo), so not audited here | none | none |

## Found, not changed (outside this task)

- **The print's own words** (`image-production/picture_sets.py` `print_prompt`) end with "No writing anywhere except the
  product's own label", which forbids the moment's name on a prop that stage 3 v11/v13 and this update ask for. It
  needs an exception for the set's signage.
- **The variations machine** (`image-edit` `vary_recipe`) still makes the five as flat edits of the approved picture;
  the rows are now written so they could be built into the set and re-printed.
- **Picture dials' `set` lines are not read by any code yet**: the set is built in the session today. They are the
  instruction sheet for whoever builds it, and for a future set builder.
- **Stage 3 v13** (not touched, per the order) still carries old lines in rule 2 ("the real product photo, placed") and
  section 3 (light and lens as art direction), and "her" for the avatar.

Every changed prompt is on the Image Lane Prompt Library, old next to new:
https://claude.ai/artifact/DtGTnxEuUb9qyuzPdz9eYg
