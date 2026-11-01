# The Four Stations — the map (step a, 2026-09-28; updated 2026-09-30)

Mirror of **The Four Stations** artifact ((team page)), tab *a · The map*.
Builds on the proposal in `notes/four-stations-damon.md`. Mapped from the prompts the machine actually loads (highest `-vN-` per folder), not from `prompts/README.md`.

| Station | Takes | Gives | Home |
|---|---|---|---|
| 1 Teardown | a swipe video | the Teardown Record — no brand in it | `tools/video-teardown/` |
| 2 Writing | the Teardown Record + a route the owner picked + a brand | the stamped Brief, one per route | `tools/copywriter/` (with routes) |
| 3 Production | the stamped Brief | clips, voice, `EDITOR-PACK.md` | `tools/video-production/` |
| 4 Editing | the production run | the finished ad, cutdowns, covers | `the team notes/video-edit/` |

Three chains, same stations: **New video** (a swipe; full teardown) · **Variation video** (our proven ad; every awareness level) · **Framework** (no swipe; 2f compose stands in for T4 and reads the brand by design).

## 1 · Teardown
| New | Was | Step | Prompt running |
|---|---|---|---|
| T0 | 0 | Triage — kind of source, sound form | triage v2 |
| T1 | new | Audio teardown — every word, who said it, voice cards → Sound Sheet (in the chain since 25 Sep) | words v1 · voice card v1 |
| T2 | 1 + deep passes | Teardown record — cast/places/props, shot table; people, visuals, music, transcript-check passes | teardown v14 |
| T3 | 1c | Doctrine read — framework, awareness in/out, desire, techniques; banked | doctrine v3 |
| T4 | 2 | Replication spec — elements E1…, load-bearing L1…, swappable | replication v4 |

## 2 · Writing
| New | Was | Step | Prompt running |
|---|---|---|---|
| W0 | new | Route — creator brief · AI production brief · founder · social copy; a model may only suggest | — |
| W1 | 1b | Audience — which of OUR avatars; may suggest a route, can no longer switch it (route lock, 30 Sep) | audience v10 |
| W2 | 3 | Rewrite — substitution, structure locked; the only step whose text changes by route | injection v15 |
| W3 | 4a | Reading | read v4 |
| W4 | 4b | Hooks — format with blanks, control + 5 | hooks v17 |
| W5 | 4c | Placement | placement v13 |
| W6 | 4d | Expansion | expansion v15 |
| W7 | 4e | Close — the ask is the click | close v8 |
| W8 | 4f | Audit — reports only | audit v5 |
| W9 | 4g | Spice — spoken script for the mouth | spice v5 |
| W10 | 5 · 5m · 5n | Brief + swipe match + manifest | creator v26 · AI v18 · hook asset v2 |
| W11 | 7b | Her page — creator only | concept v6 |
| W12 | 8 | Creator profile — creator's own posts only | profile v2 |

## 3 · Production
Takes the stamped brief (swipe match PASSED, manifest COMPLETE, the owner's read APPROVED). Runs: production gate → banks → voice → audio/song gates → platform plan → preflight → stills → motion → director → line check → coverage → editor pack. Frames (old 6) move in here.

## 4 · Editing
Takes the production run. Runs: gather → cut → gate → STOP timeline → STOP captions → export → checks → file → learn → render (one per hook, 15/30/60, covers).

## Which route runs which writing steps (today)
| Step | Creator | AI | Founder | Social copy |
|---|---|---|---|---|
| W1 | ● | ● | ● | ● (decided at triage) |
| W2 | ● "film this" | ● cut / generate / composite | ● as creator, no fallbacks | ● no structure lock |
| W3–W8 | ● | ● | ● | ● older copies, no format lock |
| W9 | runs, never read | ● feeds the voice | runs, never read | render pass instead |
| W10 | creator v26 | AI v18 | borrows creator v26 | brief for the media buyer |
| W11 | ● | — | ● | — |
| W12 | her own posts only | — | — | — |

## W3–W9 route by route
**Today none of these seven prompts changes with the route** — only W2 and W10 do. Proposed per-route writing (the owner's to decide, nothing built):

| Step | Creator | AI | Founder | Social copy |
|---|---|---|---|---|
| W3 Reading | same | same | same | reads the first line of text |
| W4 Hooks | blanks in words she'd say; first frame she can shoot | first frame from a banked person and place | first person as the maker | first line of primary text + headline |
| W5 Placement | she holds and uses it | banked product shot, label readable | from the maker's hands | where the product is first named |
| W6 Expansion | lines she can say without reading | every line maps to a makeable scene | proof from the maker's world | length by format |
| W7 Close | she says the click ask | voice + end card | guarantee as a personal promise | headline + button |
| W8 Audit | +1: nothing she can't film or buy | +1: no "film this", every person banked | +1: nothing untrue for the founder | copy gate |
| W9 Spice | delivery notes in her voiceprint, or skip | as today (the voice field) | the founder's voiceprint | the render pass |

## Found
- The route drifts: no route = creator; W1 switches it mid-run (`run.py` ~1813–1818, ~1979–1993, re-plan ~2163).
- W3–W9 identical across routes.
- Spice runs on creator/founder and nothing reads it.
- Founder has no brief; borrows the creator brief.
- W3's default named a Brand A product/objection file — FIXED 2026-09-30, now `brands/<brand>/…`.
- Teardown brand-free — FIXED 2026-09-30: element lists reach stages 0/1/1c/2 with record-keeping fields stripped (`run.py` `brand_free_list`); doctrine read v4 pastes each list once. Test: `machine/test_brand_free_teardown.py`.
- `machine/line.py` (11 Sep) split teardown/creator/AI but put audience inside teardown.
- No automatic hand-off between stations; editing reads production's raw run, not the editor pack; the Sound Sheet reaches editing only via the brief.
- Frames run for creator only; in Production they'd reach AI briefs too.
- The copywriter's hooks/expansion/close are older copies (no doctrine, format lock or spice).

## the owner's calls — settled 2026-09-30
- W0 is the **route** (*lane* stays ad/organic).
- **The copywriter writes video briefs too**, not only social copy — proven side by side first.
- **Spice stays on creator and founder**, as delivery notes she reads.
- **No more frames.** A brief carries the brief and the swipe file link, nothing else.
- **The writing process is the same for every route.** The per-route drafts on W3–W9 are dropped; only the rewrite (W2) and the brief (W10) differ by route.

## Next steps (2026-09-30)
1. Frames out of the run; the brief carries the swipe file link.
2. Spice becomes delivery notes in the creator and founder brief.
3. Social copy + one video brief through the copywriter, side by side with today's chain.
4. My Feeds' tear-down button asks the route before writing (until then: tears down, waits).
5. File moves in a quiet window the owner picks.
