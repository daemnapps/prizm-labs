# image-production — one image engine, every workflow

**image-production** — takes **a picture REQUEST** (brand, purpose, direction,
out), makes **the pictures, judged, filed and mirrored to Drive**. Does not
**write the words, lay out the asset, or decide what to make**. Triggered by
`import image_production` (a library) or
`python3 tools/image-production/make.py --brand <b> --purpose <p> --direction "…" --out <dir>`.

**Owner:** the owner (engine and definitions both).

**Not the only still door:** video-production keeps a second still family on purpose — `tools/video-production/machine/direct_openai.py`, declared in its CLAUDE.md's public surface (2026-10-08, A-rule-second-still-family option (b), B4a (decide-now cards) card 11: the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:52:41Z; the owner told after).

the owner, 2026-09-21: *"We have the image production workflow. Now, obviously,
that is for static ads, but what we need to do is create a component for just
image production that works regardless of whatever workflow it's in. That way,
we go through the same models, the same prompting structures, and the same
context structures to develop these images out for any of the assets that we
create."*

**This is an EXTRACTION, not an invention.** Every part already worked
somewhere: the judge, the gates, the brand facts and the slot discipline come
from `tools/image-production/static` (the static-ad tool); the OpenAI door and the
"make the offer picture FROM the real product photo" rule come from
`components/email-production/simple_email.py`. Each module's docstring names
what it was lifted from and what it changed.

**Who calls the engine** is whatever imports it (`git grep -n "image_production" -- components`);
this file does not keep that list. Callers move across one at a time, side by
side, with a proof each time — a working chain is never rewired on assumption.

---

## Two halves, one component (2026-09-22)

the owner: *"image-production should move entirely to components now — make sure we
have the full thing there because there's awkwardness with a half-built
folder."* There were two: this engine, and the static-ad tool in `the team notes/`.
The tool is now `static/` inside this folder, so there is one home and no twin.

| | |
|---|---|
| **the engine** — this folder's top level | one picture REQUEST in, judged pictures out; the 9:16 finish; the model route. A LIBRARY any workflow calls. Tests: `tests/` |
| **`static/`** — the static-ad tool | the chain that turns a designer work order into a batch: `templates/` (the only place layout numbers live), `style-packs.json`, `format-bank.json`, the plate/judge/compose tools, the queue, `run.py` and `batch.py`. Tests: `static/tests/` |
| **`static/runs-history/`** | the eighteen run folders the tool made before output moved to `runs/image-production/`. Kept, not tidied — they are the record of how the templates were arrived at. **FROZEN, read-only history: nothing writes here and reviews do not re-flag it; the same holds for `static/retired/`** (image-production#13, triage page 9, decision log 2026-10-07 — not moved, because history moved under `runs/` would file as new per-run records under PLANE-19 (runs filer)) |

`static/tools/pad.py` delegates to the engine's `finish_9x16`, so both halves
make the same 9:16 asset. The static tool's own tests were ERRORING before the
move (its fixture wrote `products/offer-bank.md` before creating `products/`,
missed when the offer bank moved under products) — fixed on arrival, because a
component with a broken suite is exactly the half-built thing this move was
meant to end.

**A LIBRARY — the public surface** (the developer, 2026-10-07, triage action 6 (declare public surfaces), provisionally on the owner's behalf — he sees it in the decision log and may strike any line; consumers pinned 2026-10-08, SI-120 (library clauses drafted)). Callers APPEND this folder to `sys.path` and `import image_production`; they may use only these names:
1. **Top level:** `make(req, library=, transport=, judge_caller=, mirror=)` → the judged pictures (`{model, prompt, …}`); `finish(content, out, …)` → the 9:16 asset; `purposes()` → the purpose map; `dry_run(req)` → `(ok, resolved)`. Commands: `make.py --brand --purpose --direction --out` (or `--request <json>`), `make.py purposes`, `finish.py`.
2. **`route`:** `table()` → the model table; `pick(req, ctx)` → a model entry; `key_name(entry)` → the key's NAME; `key_value(name)` → its value; `judge_entry()` → the judge's entry; `aspects()` → the allowed aspects.
3. **`providers`:** `generate(entry, prompt, references, out, aspect, transport=, key=)` → the files written; `http_transport(method, url, headers, body)` → `(status, headers, raw)`, the one HTTP door callers pass on as `transport=`; `OUT_W`, `OUT_H` (1080 × 1920).
4. **`judge`:** `seen(img, tests, entry, caller=)` → the verdict, `google_caller(...)`; **`prompting`:** `latest(stage)` → the newest prompt, `body(path)` → its text; **`assets`:** `described(brand)`, `pick(brand, direction, product=, …)` → reference pictures; **`context`:** `build(req, library=)` → the request's context, `fetched(brand, key, url)` → `(path|None, why)` — a brand's declared remote photo, fetched once into the cache; **`filing`:** `mirror(files, brand, label, tool=)`; **`paths`:** `brand(brand)` → the brand's path map.
5. **`static/`, read by path:** `style-packs.json`, `letterform-bank.json`, `tools/prompt.py render --slots <json>` (a command), `tools/product_geometry.describe|sentence`, `tools/paths.brand(brand)`; and `queue/review.json` + `queue/headline-audit.json` only until the static queue moves out (C1 (static queue out)), when its readers move with it.
6. **The fetch seam is PUBLIC now** (SI-101 (public fetch seam), video-production#3 (private image-production call), 2026-10-08): `context.fetched(brand, key, url)`, listed under `context` above; video-production `brandfiles.py` calls it by that name. `context._fetched` stays as an alias to the same function — a seam renamed keeps its old name until its callers move.
7. **`_purpose` is a DECLARED field of `context.build`'s request** (image-edit#13 (declare _purpose), ruled in B8 (seven B3 calls), 2026-10-08): `context.build(req)` reads `req["_purpose"]`, the purpose row `engine.resolve` puts there; a caller that builds a context directly (image-edit) passes `"_purpose": purposes()[<purpose>]` itself.
Everything else is internal and may change without notice. There is no `python -m image_production` (no `__main__.py`).

## The request contract

One shape, whatever the caller is. **A field nothing on this list names is
REFUSED, not ignored** — a silently dropped field is a caller that thinks it
asked for something.

| Field | | What |
|---|---|---|
| `brand` | **required** | a folder under `brands/`. Never a default — defaulting meant every other brand's picture got the first brand's packshot |
| `purpose` | **required** | a row in `purposes.json`: `email-hero` · `email-offer` · `ad` · `page-section` · `video-still` · `product-shot`. An unknown one is refused naming the real ones |
| `direction` | **required** | the words describing the picture. The one thing this component cannot read from anywhere else |
| `out` | **required** | where the caller wants the files. This component never picks a folder on a caller's behalf |
| `aspect` | optional | `9:16` `4:5` `1:1` `3:2` `16:9` `3:4`. Default: the purpose's |
| `count` | optional | 1–12. Default 1 |
| `product` | optional | a product the brand declares. Its photo and its facts come from the brand |
| `style` | optional | an id on the element library's `style/image` list |
| `format` | optional | … `format/image` |
| `template` | optional | … `template/image` |
| `from_image` | optional | **makes it an edit of that picture** rather than a fresh render |
| `references` | optional | extra reference pictures, paths on this machine |
| `people` | optional | true / false. Required when the purpose says `"maybe"` — see below |
| `label` | optional | the run label; it is the Drive folder's name |
| `model` | optional | force one model. It still has to be a declared row |
| `checks` | optional | extra judge tests for this picture |
| `rules` | optional | extra standing rules for this picture |
| `region` | optional | `(l, t, r, b)` in percent. With `from_image`, the model may paint ONLY inside that rectangle; everything else is the original, pixel for pixel |
| `assets` | optional | attach the brand's matched assets as references. Default **yes** for a render, **no** for an edit — the reference IS the picture (found live 2026-09-22: three matched packshots rode along on a headline swap and the model painted hands in) |

**Back:** `{out, brand, purpose, prompt, prompt_skeleton, model, model_why,
pictures[], delivered[], held[], drive, check}`.

**`people` is declared, never guessed.** The model route splits on whether a
photoreal person is in frame. The static-ad tool never had this problem — its
signal (`cast`) was always declared, and "nothing is inferred from the prompt
text". Here the direction is free words, so reading a person out of them is a
guess. A purpose whose `people` is `"maybe"` has not decided, and the inputs
gate refuses until the caller says. This was found on this component's first
real dry run: "a man in his forties at a bathroom sink" routed silently to the
object model.

## The four questions

- **Engine + owner:** `image_production/` (`paths` every path, found by walking
  up · `context` the one context builder · `prompting` the one prompt skeleton
  · `route` the one model route · `providers` the two doors · `judge` the
  verdict · `brand_facts` the brand's product truth · `gates` the three gates ·
  `filing` where pictures go · `dryrun` the free dry run · `engine` the request
  and `make`), plus `make.py`, the thin CLI. **the owner.**
- **Definitions + curator:** `purposes.json` (what a picture is FOR),
  `models.json` (the route table and the two doors), `prompts/*-vN-damon.md`
  (the skeleton, the standing rules, the judge). **the owner** holds the approval
  gate; every row carries a `status`. The element library is NOT here — it is
  `components/elements`' and is asked, never copied; four of its source lists
  live in `static/` (`format-bank.json`, `style-packs.json`, `templates/*.json`,
  `letterform-bank.json`, per `static/CLAUDE.md`). The model registry is
  NOT here — `components/models` is the developer's and is read, never edited.
- **The plane it emits:** **none of its own — it files the CALLER's request.**
  Text lands in the caller's `out` (`prompt-as-sent.txt`, `elements.json`,
  `check.json`, `run.json`, `rejected/*-why.md`); pictures land in `out` and
  are mirrored to `Team Drive/runs/image-production/<brand>/<label>/` on
  Drive, the path `components/run-kit/run_kit/filing.py` builds. Media is never
  git (workspace rule 3).
- **Manifest per entry:** `run.json` — the request, the resolved context, the
  model and why, every picture with its verdict, what is held and why, the
  Drive copies, and `state` (`filed` or `held`).

## Gates

Three of the five shared gates (`components/quality-checks`, via `hold()` → a
gate-keyed `check.json` in `out`). `--gates warn` records the same verdict and
carries on.

- **inputs** — before any model runs. The brand is real · a direction was given
  · the purpose and the frame are on their lists · `out` was named · `people`
  is declared when the purpose says `"maybe"` · the product is one the brand
  declares, and its photograph is a file ON THIS MACHINE when the purpose is
  made from it (a remote url is a declaration the model never sees — nothing
  here downloads).
- **elements** — before any model runs. Every `style`, `format` and `template`
  named is a real, DEFINED row in the element library. An unknown id is refused
  naming the real ids; a row whose `what` starts `[TO DEFINE` is refused as
  named but not defined yet. Recorded in `elements.json`.
- **media** — after the judge. A picture the judge failed is HELD from delivery
  and never reaches `out`, named with the judge's reason. **The gate does not
  judge** — the verdicts are `judge.py`'s. Survivors still ship; holding one
  picture never holds its siblings. A hold is a work item, not a verdict: fix
  the prompt, never the picture.

## Keys

Read **by name**, never by path: the process environment first, then the macOS
Keychain via `daemn_keys.key("<NAME>")` (service `daemn-<NAME>`, account
`damon`). Never out of a file in the repo or the home folder, never printed,
never logged, never written into a run record.

| Key | Spent by |
|---|---|
| `OPENAI_API_KEY` | `gpt-image-person`, `gpt-image-edit` — **every picture and every edit** |
| `GEMINI_API_KEY` | the judge (and `gemini-image-object`, the alternate, if it is ever forced) |

## The free dry run

`--dry-run` on every path. It resolves and prints the context, the prompt
EXACTLY as it would be sent, the model and why, whether each key is on this
machine, what the judge would ask, what the gates would say, and where the
files would land — in `out` and on Drive. **It starts no model, judges
nothing, writes no file and touches nothing on Drive.** Exit 1 when anything
required is missing.

## Rules this component holds itself to

1. **No brand, product, person or model name in code or in a prompt.** A test
   enforces it against the real `brands/` tree.
2. **Refused, never guessed.** An unknown element, purpose, model or aspect
   stops the work and names the real ones.
3. **Nothing is ever deleted on the Drive mount.** A file is copied in or
   replaced in place — `rm -rf` on a Drive folder kills every link already
   handed out.
4. **Filing never stops a delivery.** A mirror that cannot be written prints
   SKIP and the reason; the pictures are already in `out`.
5. **`sys.path.append`, never insert at 0** — a folder at position 0 shadows
   the stdlib.
6. **A changed prompt is a NEW file** `-v<N+1>-damon.md` beside the old one;
   highest number wins, numerically. Never edited in place.

**Every asset is 9:16; only the content is 4:5 — by geometry** (the owner,
2026-09-22, then "make this"): a safe-zone purpose (`ad`, `video-still`)
asked for 9:16 generates its CONTENT at 4:5 (`_gen_aspect`), the judge sees
that content, and a passing picture is FINISHED (`providers.finish_9x16`):
the content is placed in the middle of a tall canvas, a mask exposes only the
strips above and below, the edit door paints the backdrop continuing into
them, and the original content is pasted back over the answer at the exact
box — so it cannot have moved, the zone holds without asking, and the scene
continues instead of a flat band. Delivered at 1080x1920; the 4:5 content is
kept (`content` on the picture row, `content_box` on `finish`). Thirteen live
rolls the same day had shown that ASKING a model to hold a 4:5 layout in a
9:16 frame fails on both doors. A finish that cannot run HOLDS the picture —
a 4:5 never ships as if it were 9:16. `finish.py <picture> --out <file>` and
`image_production.finish()` do it for any step that already has its content
(the Brief Board's drafts ship an `asset-9x16.png` beside `draft.png`; the
static tool's `pad.py` now delegates here — the solid ink band is retired).
**Any ratio in, and always** (the owner, 2026-09-29: "any asset in any aspect
ratio → a 9:16 asset out … it needs to be done anyway"): `finish.py` takes a
picture or a folder of ANY shape and fits the WHOLE picture inside the 4:5
zone (`providers.zone_box`, `fit="whole"`) — a 1:1 or 16:9 spans the width,
a 2:3 is zone-tall with the sides painted too (`OUTPAINT_PROMPT_ALL_SIDES`),
a 9:16 is left alone; output in a `9x16/` folder beside, `resize.json` the
record. And a safe-zone purpose now leaves at 9:16 whatever frame was asked —
the content is made at the asked frame and finished. Front door: the
`resize-9x16` skill; the Higgsfield-side copy is `tools/image-edit/skills/resize-9x16.md`.
The zone judge test (`judge.SAFE_ZONE`) remains only for a native 9:16 that
leaves unfinished. Known polish: a faint tone step can show where a strip
meets the content.

**ONE DOOR FOR PICTURES** (the owner, 2026-09-22: *"everything image needs to just
be gpt now, literally that's it — it's going to make all of our work easier"*).
The person/object split of 09-14 is RETIRED: every picture, with a person in
it or not, fresh or an edit, routes to **GPT Image 2.5** — one look across a
batch, one set of quirks, one prompt style. `gemini-image-object` stays
declared as an ALTERNATE (forceable with `model`, never routed to) — in models.json `status: approved`, `routed: false` (rule 6, triage page 15, 2026-10-07) — because run
records name it and because it is the only door here that makes 9:16 natively
— and it takes no mask, so it can never serve a region edit or the 9:16
finish. GPT Image makes no 9:16 of its own, which costs nothing: the content
is made at 4:5 and finished to 9:16 by the masked outpaint, which is the
standing frame rule anyway. **`people` is no longer refused when undeclared** —
it stopped changing the model, so it is a NOTE (it still decides whether the
brand's cast rides along as a reference).

**`region` makes an edit a masked one** (2026-09-22): `(l, t, r, b)` in
percent with `from_image` routes generation through `providers.edit_in_region`
— the picture is the canvas, a mask exposes that rectangle alone, the model
paints only there, and the original is pasted back outside it. Recorded per
picture as `region_px`. Found because a model handed a whole ad and told to
change one line redrew the product's own label on every roll.

**Edits keep the reference's composition** (2026-09-22): a `from_image`
request gets no COMPOSITION FOR CROPPING clause — that clause tells the model
how to compose a scene, and an edit has its composition already. **A frame the
vendor cannot make is cropped back** (`providers.conform`): a backstop for a door
that hands back a frame other than the one asked for; the centre crop takes
the extra canvas back before the judge. Recorded
per picture as `conformed`. A side crop (9:16 asked of a 2:3 door) can clip
content — route 9:16 work to a door that makes it. Both found on `tools/image-edit`'s first live
run.

Tests: `python3 tools/image-production/tests/test_image_production.py` (its
run prints the count) — stdlib `unittest`, stubbed provider and stubbed judge, temp dirs
only. No network, no model, no real key, nothing written outside `tempfile`.

## Two things that are open, not settled (stated 2026-09-23)

- **The Drive carve-out (O9).** `static/tools/paths.py:74` discovers
  `Team Drive/the team notes` on the mounted Drive — deliberately discovered and
  never typed, but still the lab path and still the mount. The standing ruling
  is fileId through the API. The static tool's media did not move when the code
  did; migrating it is a card. The main engine already mirrors to
  `Team Drive/runs/image-production/`, the standard.
- **A records adapter (O12): none yet.** The convention allows "an adapter or
  'none yet' stated"; this states it. One shared kind behind one adapter is
  50–100 lines per component; a kind of its own is 450–650 plus a manifest plus
  worker wiring, which is why none has been built yet.
