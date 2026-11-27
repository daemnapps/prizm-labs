# image-production — one image engine, every workflow

**image-production** — takes **a picture REQUEST** (brand, purpose, direction,
out), makes **the pictures, judged, filed and mirrored to Drive**. Does not
**write the words, lay out the asset, or decide what to make**. Triggered by
`import image_production` (a library) or
`python3 components/image-production/make.py --brand <b> --purpose <p> --direction "…" --out <dir>`.

**Owner:** the owner (engine and definitions both).

**One picture process, no exceptions (2026-10-31).** A session never makes a picture by a direct model call, a script of its own or the raw Higgsfield command line. Every picture, cast sheet, room print and video start picture goes through image production and the board; where the board has no door, the door is built first. The older direct doors below stay only for the machine steps that already call them, never for a session's own use. A scratch ad with no swipe uses each scene's `reference` frame in its plan as IMAGE 1.

**Not the only still door:** video-production keeps a second still family on purpose — `components/video-production/machine/direct_openai.py`, declared in its CLAUDE.md's public surface (2026-10-08, A-rule-second-still-family option (b), B4a (decide-now cards) card 11: the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:52:41Z; the owner told after).

the owner, 2026-09-21: *"We have the image production workflow. Now, obviously,
that is for static ads, but what we need to do is create a component for just
image production that works regardless of whatever workflow it's in. That way,
we go through the same models, the same prompting structures, and the same
context structures to develop these images out for any of the assets that we
create."*

**This is an EXTRACTION, not an invention.** Every part already worked
somewhere: the judge, the gates, the brand facts and the slot discipline come
from `components/image-production/static` (the static-ad tool); the OpenAI door and the
"make the offer picture FROM the real product photo" rule come from
`components/email-production/simple_email.py`. Each module's docstring names
what it was lifted from and what it changed.

**Who calls the engine** is whatever imports it (`git grep -n "image_production" -- components`);
this file does not keep that list. Callers move across one at a time, side by
side, with a proof each time — a working chain is never rewired on assumption.

---

## Every picture: a 3D set, printed, then the words (the owner, 2026-10-28 — never skipped)

the owner, on the first ad made this way: *"this is perfect execution. This is our workflow for creating images over and over
and over again. We never skip this process."* Sizes, depth, contact and light come from pixels, never from words
(`research/diffusion-fundamentals.md`, rule 1; none of our image models takes a depth map, so the 3D render is the lock).

1. **Build the swipe's scene in Higgsfield 3D Jutsu** (the session's scene_builder_3d tools): the product's own true-size
   build (its kit's `model/sheet/jutsu/angles.json` names the project), props at real sizes, the swipe's camera and light.
   A product shown at rest takes one of its kit's `behaviour.rests` (a brush that rolls sits in its cradle).
2. **Render inside a scene edit**, then **print** it with `scene_builder_3d_generate_angles` (9:16, 1.5k since 2026-11-25; a store picture 2k), the product's casting
   sheet as the reference and **nothing else for the product** (ruled 2026-11-23: product casting sheets only;
   the kit's rest pictures were old 2024 CGI and carried a misspelled towel mark, plants and a cradle into every print,
   so `set_queue.plan` no longer puts them on the board and `assets` never pulls a `cgi/` folder), uploaded fresh (an upload older than a day fails the print with no reason). Words of the print:
   `picture_sets.py print-words <brand> <run>` (keep structure, change materials), which carries the brief's concept and picture dials (`creative`) into the print; build the set from those lines too. The swipe's moment props become ours (stage 3 v11).
   **A product picture follows its brand's picture standard** (2026-11-07): `brands/<brand>/brand-identity/product-pictures.json`
   (readable copy `.md`) sets ground, framing, light, label and bundle rules per kind (Brand B: `shop-card`, `gallery`,
   `offer-icon`). `print-words … --kind <kind> [--bundle]` carries them into the print; `picture_standard.py check <brand>
   <kind> <picture>` measures the print (square, ground, fill) before it is filed.
   **Any account:** a build missing from your Higgsfield account is rebuilt from `components/3d-recipes/`. Every kept set
   saves its build steps there too (the README says how), or nobody else can run it.
   **Real skin, every time (2026-11-26):** a set that shows a person or bare skin prints with the skin bank
   (`image_production/skin_bank.py`, rows in `runs/ai-elements/_texture-refs/index.json`: a real customer crop + a macro
   shot) on its reference board and files with `--skin`; `put` refuses it otherwise, and the board's finish pass
   (`model-inputs/preview.py` `finish_people`) re-textures the skin from the same bank. **A product is always its own
   true 3D build** in its own project; `put` refuses a hand-made stand-in or a product with no build.
3. **File it**: `picture_sets.py put` into `runs/image-production/<brand>/sets/<set>/`, `set.json` naming the run and the
   kept print (`note` starting "kept").
4. **The board makes the picture from it** (model-inputs `preview.set_print`): the print is the plate, nothing is generated,
   the words go on top in the swipe's zones inside the safe zone. A product picture made with no set is flagged
   "no 3D set". Cost: the set and its renders are free; a print is 1.25 credits at 1.5k (2.5 for a store picture at 2k; a board picture is 2.25).

**Every picture comes from a filed 3D set print, no exceptions (RULE GATE-4, 2026-11-10).** On 10 Nov a video start picture
with six cast members went through the edit route (an AI picture as `from_image`, then two masked face patches) and nothing
stopped it. The ruling the same day: every generated picture goes through this process, people or no people, cast
sheets too. It is slower per picture and better and cheaper overall, and the process is the check. `image_production/set_gate.py` stops
a picture before anything is sent, dry runs included:
- **Engine** (`make.py --set`, `IP.make`, and so image-edit, the email picture tries, the Video Studio's still door): every
  purpose names `set`, a filed set with a kept print, which becomes `from_image`. Refused: no set, no kept print, any other
  base, a `region` patch, a picture we made as a reference.
- **Plain** (`plain.make`, so the board's fallback, the Picture Bench, image-teardown pictures and slides): IMAGE 1 is a kept
  print or a byte copy. The board makes no call when the run has a kept print: the print is the picture. The owner's skin
  realism pass on it (model-inputs lesson L-40) names that print (`from_print`), which is checked.
- **Email** (`email-production/design/picture_chain.py`): every picture takes the set route; with no kept print it is held
  with its set request (`media/sets/<label>.json`) and the email still builds.
- **Doors called directly** (`video-production/machine/direct_openai.generate`, `direct_google.edit_image`, so every
  machine step; image-teardown `gpt_drafts`; `casting/casting/generate.py`; the Studio's `motion_program.first_frame`):
  the first reference is a kept print, or the named `from_print`. **Cast sheets:** `make_character.py` puts the person's
  set print first (spec `"set"`, or per sheet `"sets"`: the 3D figure posed for that sheet, printed with the real person's
  frames as the reference).
- **The picture doors themselves** (`providers.generate`, `generate_ladder`, `edit_in_region`): a call that no gate above
  cleared (`set_gate.cleared()`) must start from a kept print too, so a new caller cannot slip past.
- **Several people in one print:** the reference is the **cast board**: `cast_board.py build <brand> <out.png>
  <element>[:<look>] ...` in standing order, each member's headshot and look sheet, sha256 per file; file the print with
  `picture_sets.py put <brand> <set> --print F --note "kept: ..." --cast-board <board.json>` (set.json gets `picture_from`,
  the Studio's old-element list; `picture_sets.py picture-from` reads it).
- **A refusal is never the end: the 3D print queue.** Every refusal that knows its brand files a request
  (`image_production/set_queue.py`, `runs/image-production/<brand>/set-requests/<id>.json`, with the step to run again);
  email set requests join it too, and a cast sheet with no set files one for that sheet. The **`3d-print` skill**
  (`.claude/skills/3d-print/SKILL.md`) clears it: `picture_sets.py queue`, `plan <brand> <id>` (worlds, true-size builds,
  casting sheets, cast board, print words, the commands), build and print in Jutsu, `put`, `done` (prints the step to run
  again), then that step. A dry run files nothing. By hand: `picture_sets.py request <brand> "<what>"`.
- **Sessions:** `.claude/hooks/people-picture-guard.py` (this workspace, and the owner's user-level hook on his Mac) blocks
  Higgsfield's picture tools typed by hand, the Higgsfield command line's picture jobs and raw OpenAI images calls.
- **Retired:** static `make_variations.py`, the mini worker's `generate-image` action and its `higgsfield.py` /
  `bakeoff.py` spikes, `sequence.py stills`, `master.py`, lab `hook-library/shots.py`, `pages/machine/pictures.py`, lab
  `gpt_drafts.py`; lab `hf_client.py run` needs `--no-people`.
- **ROLLBACK** (`models.json` `gate.set_required`): `"on": false` puts everything back as it was; one lane set to `false`
  puts that lane back alone: `statics`, `email`, `video`, `cast`, `direct`, `sessions`. `PICTURE_GATE_OFF=all` or a comma
  list does the same on one machine. The rollback register is `team/rollbacks.md`.
**The edit lane (2026-11-10) — SWITCHED OFF the same day by the owner: a change to an approved picture is a 3D rebuild too (a little more work, far fewer problems). Kept built behind `edits.on`; what it does when on:**
Changing one thing on a picture that is already approved or live (take an item out, fix one part) is a masked edit on that
picture: `from_image` is the set's kept print or an **approved original** filed into the set
(`picture_sets.py put <brand> <set> --original F --note "approved: <where it is live>"`), `region` is the box to change,
the model paints only there (`providers.edit_in_region`) and every pixel outside it is the original's. An original with no
`region` (a whole-picture redraw) is refused, and so is any picture not filed into the set. ROLLBACK: `models.json`
`gate.set_required.edits.on: false` (or `PICTURE_GATE_OFF=edits` on one machine) refuses every masked edit again; row in
`team/rollbacks.md`.
Tests: `tests/test_set_gate.py`. Other suites that make a no-print picture to test something else set
`PICTURE_GATE_OFF=all` at their top.

5. **A variation is the set changed** (2026-10-30): image-edit's `vary_recipe` reads `picture_sets.py` by path (`kept`,
   `change_request`, `kept_change`, `put_change`) and turns a picture row into a set request. The print files as its own set
   `<set>--<variation>`, which never names the run in `runs`, so the run's own print stays its picture. One print per picture
   row, 1.25 credits; words-only rows are free.

6. **The words on a prop travel on their own** (2026-10-30): `picture_sets.signage_for` reads them from THE SET block of the
   brief (`props[].signage`, stage 6 v12), else the run's swap rows or stage 3's art direction. `print-words <brand> <run>`
   gives a first print's words with them in, `put --run` records them in `set.json`, a variation's request carries them, and
   `signage <brand>` fills sets made before this. Nobody types them, and the print's no-writing line lets them through.

## Covers: one job, one cover per version of a video ad (2026-11-12)

A cover (thumbnail) is purpose `cover` (purposes.json `job: "cover"`), made by `image_production/covers.py`. Never purpose `ad`.

- **One ad, every version, one call:** `make.py covers --job <job.json>` (or `IP.covers.make_ad(job)`). The job:
  `{brand, ad, out, set, product?, product_place?, people?, references?, type?, versions: [{version, headline, frame,
  video, t, swipe, direction?, set?, product?, product_place?, people?, references?}]}`. A version's own field wins over the
  job's; `"product": false` on a version leaves the product off that cover. `--only <version>` makes one again in the
  ad's filed type. `--dry-run` spends and writes nothing.
- **One version, one request:** `purpose: "cover"` with `cover: {version, headline, frame, video, t, swipe, ad,
  type?}`, `set`, `out`. `count` is 1. `cover` on any other purpose is refused. The video edit line calls this
  (`components/video-edit/machine/line.py` `cover_cmd`): `make.py --purpose cover --brand --version --frame --video
  --frame-at --ad --swipe --headline --out [--product] [--set]`; it exits 1 when the cover it delivered is not `ok`, so
  the line stops and files nothing. With no `type`, the request takes its ad's type from
  `cover-type.json` beside its `out` folder (the file `covers --job` writes); the ad's first cover fits the default to
  its headline and files it there. A later headline that does not fit that type is refused: make the ad's versions
  together with `covers --job`. No `ad` and no `type` is refused.
- **The direction** is the caller's: the moment, the concept taken from the swipe, the one thing pushed. It never
  carries the words. A request that brings none gets the job's standing direction (`prompts/cover-direction-v1.md`:
  the frame's moment, the headline shown literally, one thing pushed, and the swipe's `move` from the cover swipe
  index); the record says so (`cover.direction_from`). With no direction, a swipe with no rated `move` in the index
  (`runs/asset-index/swipes/covers/covers.json`) is refused. A placeholder swipe id (`none`, `TBD`, `x`, `?`, under
  three letters or digits) is refused always.
- **The frame is the composition.** `cover.frame`, a frame of that version's own video (`video`, at `t` seconds), is IMAGE 1. The filed 3D set is
  still required (GATE-4): its kept print rides beside the frame as IMAGE 2 and decides the people and the room.
  Refused: no set, no kept print, any `from_image`, the set print as the frame, two versions of one job from the same
  frame; a `video` that is not a real video (a picture file, or no video stream with a duration by ffprobe, or `t`
  past its end); a frame that is not the picture at `t` of `video` or of its clean twin (`<name>.clean.<ext>`), checked
  with ffmpeg (other picture shape, or more than 8% apart small and grey); a frame we made: a `.recipe.json` or
  `.cover.json` beside it, inside a `generated/` folder, its bytes in the tool's ledger (made or made-from), or in a
  run record, `covers.json` or `.cover.json` beside it or one folder up; or a re-saved, re-encoded or regraded copy of
  a cover or its plate, told by its look (`covers.look`: 27x48 grey cells, under 15% apart, and nearer the made picture
  than both its own source frame and the real frames of `video` at `t`, grabbed with ffmpeg; the cover's record and
  ledger line carry `looks`). A frame with too little detail to tell
  by look is judged by its bytes. The record keeps the video's full path and
  its sha256 (`source_frame.video_sha256`).
- **The product comes from its 3D kit**, rendered and placed by the tool, when the request names `product`, set or no
  set. A product with no 3D kit is refused. A cover that names no product is told to show none.
- **The words are set by the tool, inside the job.** The picture model paints none (the prompt keeps the band clear of
  faces). `words.set_headline` sets the version's headline before the picture is delivered: exact characters, one
  type record for every version of the ad (`covers.ad_type`: same face, weight, size and band; default
  `cover-type.json`; with no band given, the first of its `bands` where no headline lands on its version's product).
  A headline and a product that would still land on each other are refused. Nothing is added after the tool delivers. A face the machine lacks, a character the face cannot
  draw, or a headline that does not fit is refused before anything is spent.
- **The record:** `run.json` `cover`, the picture's `.recipe.json` and `<picture>.cover.json` carry the version, the
  ad, the swipe id, the source frame (`source_frame`: `file`, `video`, `t`, `sha256`), the set and its print, the type,
  the plate and the delivered file's sha256; where `provenance.py` is present the cover also gets its line in the
  tool's ledger. The approval filer's cover rule and made-by-tool gate (`components/meta-upload`) read these. The ad's
  folder holds `covers.json` (every version, `ok` and `problems`) and `cover-type.json`. File only a cover whose row
  says `ok`, from its own run folder.
- **Faces:** the tool reads the faces and lips on the plate (before the words hide anything) with the local reader
  (`image_production/face_read.py`: macOS Vision through `components/video-edit/machine/vision/scene.swift`, the edit
  line's own). A headline on a face is a problem; a cover whose faces were not read (no reader on the machine, or it
  stopped) is not `ok`, in `covers.json` and in its own `.cover.json`. `make_ad(job, faces=<callable>)` replaces the
  reader. Faces against the cast sheets stay an eye check.
- **ROLLBACK** (`models.json` `gate.cover`; `IMAGE_COVER_OFF=all` or a comma list on one machine; row in
  `team/rollbacks.md`): `on: false` refuses purpose `cover`; `source_frame: false` makes the kept print the base again;
  `product_with_set: false` stops the 3D product when a set is named; `words_step: false` hands the words back to the
  picture model. Row COVER-CHECKS: `own_video: false`, `frame_not_made: false`, `one_type: false`, `faces: false`,
  `swipe_concept: false`, `video_stream: false`, `made_look: false`, `unfit_exit: false` each put that check back as it was (models.json `gate.cover._what` says what each does).
- Tests: `tests/test_covers.py`.

## Two halves, one component (2026-09-22)

the owner: *"image-production should move entirely to components now — make sure we
have the full thing there because there's awkwardness with a half-built
folder."* There were two: this engine, and the static-ad tool in `lab/the owner/`.
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
1. **Top level:** `make(req, library=, transport=, judge_caller=, mirror=)` → the judged pictures (`{model, prompt, …}`); `purposes()` → the purpose map; `dry_run(req)` → `(ok, resolved)`. Commands: `make.py --brand --purpose --direction --out` (or `--request <json>`), `make.py purposes`.
2. **`route`:** `table()` → the model table; `pick(req, ctx)` → a model entry; `key_name(entry)` → the key's NAME; `key_value(name)` → its value; `judge_entry()` → the judge's entry; `aspects()` → the allowed aspects.
3. **`providers`:** `generate(entry, prompt, references, out, aspect, transport=, key=)` → the files written; `http_transport(method, url, headers, body)` → `(status, headers, raw)`, the one HTTP door callers pass on as `transport=`; `OUT_W`, `OUT_H` (1080 × 1920).
4. **`judge`:** `seen(img, tests, entry, caller=)` → the verdict, `google_caller(...)`; **`prompting`:** `latest(stage)` → the newest prompt, `body(path)` → its text; **`assets`:** `described(brand)`, `pick(brand, direction, product=, …)` → reference pictures; **`context`:** `build(req, library=)` → the request's context, `fetched(brand, key, url)` → `(path|None, why)` — a brand's declared remote photo, fetched once into the cache; **`filing`:** `mirror(files, brand, label, tool=)`; **`paths`:** `brand(brand)` → the brand's path map.
5. **`static/`, read by path:** `style-packs.json`, `letterform-bank.json`, `tools/prompt.py render --slots <json>` (a command), `tools/product_geometry.describe|sentence`, `tools/paths.brand(brand)`; and `queue/review.json` + `queue/headline-audit.json` only until the static queue moves out (C1 (static queue out)), when its readers move with it.
6. **The fetch seam is PUBLIC now** (SI-101 (public fetch seam), video-production#3 (private image-production call), 2026-10-08): `context.fetched(brand, key, url)`, listed under `context` above; video-production `brandfiles.py` calls it by that name. `context._fetched` stays as an alias to the same function — a seam renamed keeps its old name until its callers move.
7. **`_purpose` is a DECLARED field of `context.build`'s request** (image-edit#13 (declare _purpose), ruled in B8 (seven B3 calls), 2026-10-08): `context.build(req)` reads `req["_purpose"]`, the purpose row `engine.resolve` puts there; a caller that builds a context directly (image-edit) passes `"_purpose": purposes()[<purpose>]` itself.
8. **`product3d` — the product from its 3D model** (2026-10-14, the owner: "use the 3d models moving forward for product"; image-teardown's draft step is its second caller): `find_kit(brand, product)`, `declaration(kit)`, `kit_facts(kit)`, `pose_for(decl, hands=)`, `shows_hands(text)`, `not_covered(decl, text)`, `zone_from_text(text)`, `size_words(facts)`, `render_product(kit, pose, camera, out_png, size_px=)` → the render record, `locate(scene, what, size, ask, count=)` → spots + the scene's px-per-cm off a reference of known size, `place_located(scene, rec, out, loc, i=, zone=)`, `place_product(scene, rec, out, box= | anchor= + px_per_cm=)`, `silhouette_iou(kit, angles)`, `judge_ask(entry)`. Request fields `product_3d` / `product_place` (engine docstring). Prompts: `product-space`, `product-locate`. The cradle a resting product sits in is a STAND-IN built from the product's own back half until a real cradle model exists.
9. **`brandmark` — the real logo** (2026-10-14, the owner: an ad that shows the brand as a mark shows the REAL logo; the image model never draws it): `space_rule(brand)` → the picture-prompt rule, `wordmark(brand, tone)` → the kit's wordmark file (`light` for a dark ground), `locate(picture, brand, ask, swipe=)`, `put(picture, out, brand, box)`, `apply(picture, out, brand, ask, swipe=)`; and `context.logo_files(brand)` → every logo file in the brand's kit (repo + Drive). Prompts: `brand-mark-space`, `brand-mark-locate`.
10. **`plain` — the plain picture** (2026-10-25, the owner on the carousels made this way: "literally 1000000x better than any flex implementation we had in the past ... not just statics but also video scenes as well"): `make(brand, text, out, references=, products=, aspect=, product_refs=, product_lines=)` → `{file, refs, prompt, model, products}`; `product(brand, slug)` → `(name, refs, line)`; `on_black(content, out)` → the 9:16 with the 4:5 on black. ONE call: the caller's reference as IMAGE 1, each product's real pictures and line from its kit (`kit.json` `in_use`: `refs`, `line`; else its real front photo), the caller's own lines. No house prompt, no judge hold, no paste. Callers: image-teardown `tools/slides.py`, `tools/pictures.py`.
11. **`covers` — the cover job** (2026-11-12): `make_ad(job, only=, dry_run=, faces=, mirror=, mode=)` → `{ok, brand, ad, out, type, covers[], failed[], problems[], record}`; `ad_type(headlines, given=)` → the ad's one type record; `type_of(given=)`; `check_ad(rows, faces=)`; `problems(cover)`; `CoverRefused`. **`words`:** `set_headline(picture, text, type, out=, plate=)`, `fit(headlines, type)`, `layout(text, type)`, `check_type(type)`, `face_file(face)`. Command: `make.py covers --job <job.json> [--only <version>] [--dry-run]`.
Everything else is internal and may change without notice. There is no `python -m image_production` (no `__main__.py`).

## The request contract

One shape, whatever the caller is. **A field nothing on this list names is
REFUSED, not ignored** — a silently dropped field is a caller that thinks it
asked for something.

| Field | | What |
|---|---|---|
| `brand` | **required** | a folder under `brands/`. Never a default — defaulting meant every other brand's picture got the first brand's packshot |
| `purpose` | **required** | a row in `purposes.json`: `email-hero` · `email-offer` · `ad` · `page-section` · `video-still` · `product-shot` · `cover`. An unknown one is refused naming the real ones |
| `direction` | **required** | the words describing the picture. The one thing this component cannot read from anywhere else (a cover that brings none gets the cover job's standing direction) |
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
| `set` | **required while GATE-4 is on** | the filed 3D set the picture is made from (name, folder or print): its kept print is the base |
| `region` | optional | `(l, t, r, b)` in percent. With `from_image`, the model may paint ONLY inside that rectangle; everything else is the original, pixel for pixel |
| `cover` | **required for purpose `cover`**, refused for any other | `{version, headline, frame, swipe, video?, t?, ad?, type?}`: see "Covers" above |
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
  `models.json` (the route table and the two doors), `prompts/*-vN-owner.md`
  (the skeleton, the standing rules, the judge). **the owner** holds the approval
  gate; every row carries a `status`. The element library is NOT here — it is
  `components/elements`' and is asked, never copied; four of its source lists
  live in `static/` (`format-bank.json`, `style-packs.json`, `templates/*.json`,
  `letterform-bank.json`, per `static/CLAUDE.md`). The model registry is
  NOT here — `components/models` is the developer's and is read, never edited.
- **The plane it emits:** **none of its own — it files the CALLER's request.**
  Text lands in the caller's `out` (`prompt-as-sent.txt`, `elements.json`,
  `check.json`, `run.json`, `rejected/*-why.md`); pictures land in `out` and
  are mirrored to `Shared Assets/runs/image-production/<brand>/<label>/` on
  Drive, the path `components/run-kit/run_kit/filing.py` builds. Media is never
  git (workspace rule 3).
- **Manifest per entry:** `run.json` — the request, the resolved context, the
  model and why, every picture with its verdict, what is held and why, the
  Drive copies, and `state` (`filed` or `held`).

## Gates

Three of the five shared gates (`components/marketing-chain-checks`, via `hold()` → a
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

Read **by name**, never by path: the process environment first, then the
one key file `~/.upright-keys.env` (add `NAME=value` there), through
`components/keys/loader.py`. Never out of a file in the repo or the home folder, never printed,
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
6. **A changed prompt is a NEW file** `-v<N+1>-owner.md` beside the old one;
   highest number wins, numerically. Never edited in place.
7. **A creator's footage is a reference only when her rights allow the picture's
   use** (the email lead, 2026-11-10). `assets.pick` and `assets.nearest` drop every
   creator asset whose verdict from asset-index's `machine/rights.py` is not
   `allowed` for the use (`assets.use_of`: email purposes "email",
   `page-section` "website", the rest "ads"); each one dropped is named in the
   asset note. A creator with no row is left out, never assumed cleared.
   Whether "reference for AI" is its own use in the register is open (asked of
   the owner, 2026-11-10). Tests: `tests/test_reference_rights.py`.

**Every photo and video asset (not email) is 9:16, made 9:16 from the start, safe zone assumed** (the owner, 2026-10-26: "when
we do it 9:16 from the jump and assume safe zones it's easier to crop ... 4:5 then adding space comes out like shit
and inconsistent"). A safe-zone purpose (`ad`, `video-still`) asks the model for 9:16 (1152x2048) with the centre 4:5
as the safe zone in the prompt (`prompting.SAFE`; `plain.FRAME`), the judge measures the zone (`judge.SAFE_ZONE`), and
the picture is delivered at 1080x1920. **Removed on the same day, all of it:** the 4:5 content + masked outpaint finish
(`finish_9x16`, `outpaint_canvas`, `zone_box`, `content_4x5`, the outpaint prompts), `finish.py` and the `resize-9x16`
skills, `IP.finish`, the `pad` route in the designer work order, and the grid-on-black placement. An edit of a picture
is made at 9:16 like everything else.

**ONE DOOR FOR PICTURES** (the owner, 2026-09-22: *"everything image needs to just
be gpt now, literally that's it — it's going to make all of our work easier"*).
The person/object split of 09-14 is RETIRED: every picture, with a person in
it or not, fresh or an edit, routes to **GPT Image 2.5** — one look across a
batch, one set of quirks, one prompt style. `gemini-image-object` stays
declared as an ALTERNATE (forceable with `model`, never routed to) — in models.json `status: approved`, `routed: false` (rule 6, triage page 15, 2026-10-07) — because run
records name it and because it is the only door here that makes 9:16 natively
— and it takes no mask, so it can never serve a region edit or the 9:16
finish. Every picture is made at 9:16 from the start, centre 4:5 as the safe zone (the 2026-10-26 rule above; the
4:5-then-outpaint finish was removed that day). **`people` is no longer refused when undeclared** —
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
content — route 9:16 work to a door that makes it. Both found on `components/image-edit`'s first live
run.

Tests: `python3 components/image-production/tests/test_image_production.py` (its
run prints the count) — stdlib `unittest`, stubbed provider and stubbed judge, temp dirs
only. No network, no model, no real key, nothing written outside `tempfile`.

## Two things that are open, not settled (stated 2026-09-23)

- **The Drive carve-out (O9).** `static/tools/paths.py:74` discovers
  `Shared Assets/lab/the owner` on the mounted Drive — deliberately discovered and
  never typed, but still the lab path and still the mount. The standing ruling
  is fileId through the API. The static tool's media did not move when the code
  did; migrating it is a card. The main engine already mirrors to
  `Shared Assets/runs/image-production/`, the standard.
- **A records adapter (O12): none yet.** The convention allows "an adapter or
  'none yet' stated"; this states it. One shared kind behind one adapter is
  50–100 lines per component; a kind of its own is 450–650 plus a manifest plus
  worker wiring, which is why none has been built yet.
