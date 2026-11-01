# The angle — set once on the brief, read everywhere after

the owner, 2026-10-12: *"The angle should be derived from the brief itself through analyzing
what the brief actually even is. That's it. The angle should be in the notes of the brief."*
And: *"Let's keep this organized, streamlined, and straightforward."*

**One field. One writer. Every stage reads it.**

```
 swipe ─► teardown ─► brief written ─► BRIEF REGISTERED ─► production ─► edit ─► copy ─► card ─► ad set ─► Meta report
                                            │
                                   ANGLE SET HERE, ONCE
                              (read off the brief by a model,
                               picked from the brand's signed bank)
                                            │
                       stored on the brief record ── every stage to the right reads it
```

## Where it is set

At the first point the brief exists and its content is settled: **when the brief gets its
number** (`tools/image-teardown/tools/briefs.py` `open_brief` — every lane: image, carousel, video
teardown, video production, email, page, and every caller, the chain's own numbering included; until
2026-10-27 only the `open` command did it, so picture briefs numbered by the chain never got an angle).
Right after the number, `components/naming/angle_pick.py` reads the brief and names ONE angle.

| | |
|---|---|
| Reads | the brief file itself (`brief_file` on the register, else the run's brief) + its header facts |
| Picks from | the brand's ACTIVE angles in `brands/<brand>/strategy/angles.json`, less rows marked `misfiled` (formats, not claims) — every one open to every avatar (the owner, 28 Oct 2026: "angles are just ways to start the conversation and each conversation varies by language of the avatar but the approach is the same") — then to the angles whose ad set is already running (`components/meta-upload/ad_sets.py`; the owner, 2026-10-27: "most new ads will go into existing ad sets unless a new angle or avatar is clearly defined"). An avatar with none running keeps the whole bank |
| Prompt | `components/naming/prompts/angle-pick-v1.md` (brand-agnostic, invented-example guard at the top) |
| Model | the registry's `sonnet` entry (`components/models/models.json`) |
| Refuses | an id not in the bank (nothing is coined); a quote that is not in the brief |
| Nothing fits | `no-fit` — recorded with no angle; the card's ad-set check then fails and says so |
| Already declared | an image brief whose stage 6 declares a signed angle with a running ad set keeps it (either spelling, `grandmasrecipe` = `grandmas-recipe`) — no model call |
| Switch | `NAMING_ANGLE_PICK=off` skips it at registration |
| By hand | `angle_pick.py --brand <b> --brief <id> --write` (or `--missing --write`) |

## Where it is kept — the notes of the brief

`brands/` is read-only to machines, so:

1. **The brief record** — the register entry (`tools/image-teardown/briefs.json`):
   `angle`, `angle_why` (one line, quoting the brief), `angle_state` (picked · declared · no-fit),
   `angle_by` (tool, prompt, model, time). **This is the one home.**
2. **A Notes line in the brief file itself**: `- Angle: \`<id>\` — <why> — "<quote>"`.
3. The prompt and the answer, to read and tighten: `runs/naming/<brand>/angle-<brief>/`.
4. A proposal for the `brands/<brand>/briefs/briefs.json` header, for a person to commit:
   `runs/brands-proposals/<brand>/<date>-brief-angles/briefs/brief-angles.json`.
   A header angle a person writes there wins over the register's.

## Who reads it — all through `names.brief_record` / `names.brief_angle`

| Stage | What it uses the angle for | Before 2026-10-12 |
|---|---|---|
| copywriter `brief_words.py` | one copy set per product + angle | brands header only |
| meta-upload `card_words.py` | the approved copy set for the angle | brands header only |
| video-edit `deliver.py` | the angle on the staged card | header, else the edit run's own record (a second source) |
| video-edit `line.py` | files the card | passed `--angle` by hand — **removed**, the filer reads the brief |
| meta-upload `to_check.py` | the card's angle → ad set `adset_<brand>_<avatar>_<angle>` | header, or `--angle` typed by whoever filed |
| meta-upload `to_check.py --angle` | only for an ad whose brief has no angle; **a different angle from the brief's is refused** | always won |
| naming `delivery_rule.py` | READY-TO-LAUNCH grouped by ad set | brands header only |
| meta-upload `business.py` | spend / CPA per angle | header, else register (already right) |

## What changed (2026-10-12)

- NEW `components/naming/angle_pick.py` + `prompts/angle-pick-v1.md` + `test_angle_pick.py`.
- `names.py`: `brief_record()` (register under header — the one brief record) and
  `brief_angle()`; `brief_header()` falls back to the register's angle when the header has none.
- The readers above switched to it; the hand-typed `--angle` paths removed or refused on disagreement.
- Applied to <brand> brief-0035..0041 and <brand> brief-0308..0311; the cards in 1-check refiled.
