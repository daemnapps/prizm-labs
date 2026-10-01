# run.py — the one runner

**How a scene is generated, step by step, is `../SCENE-GENERATION.md` — the
method page. This page is the runner that executes it.**

A brief or a plan goes in. The gates run. Every station is made directly
on our own keys — voice, cast, stills, edits, song, the talking beat and
silent motion (the one hand, 2026-09-18) — into `<run>/media/` with
`direct.json` as the manifest. A house (fal, Higgsfield) is used only when
`--provider` forces one; then the editor gets a submit sheet and hands
results back. Every job lands in the ledger. The run lives at `runs/video-machine/<brand>/<label>/`, per the
repo-root `runs/README.md`.

    python3 machine/run.py start  <brief.md | plan.json> --brand B --format F \
                                   --label L [--provider P] [--yes] [--dry-run] \
                                   [--bank <path>] [--runs-root <path>] [--cast-root <path>]
    python3 machine/run.py record <run-dir> --direct                 # the machine's own clips
    python3 machine/run.py record <run-dir> --results <results.json> # a forced house's results
    python3 machine/run.py pack   <run-dir> [--dry-run]

Exit 0 done · 1 declined at the confirm gate · 2 a gate failed, nothing
submitted · 3 bad input.

## `start`

1. Opens `runs/video-machine/<brand>/<label>/`, writes `run.json`
   (`machine`, `brand`, `label`, `format`, `source_brief`, `provider`,
   `opened`) — a key already there is never overwritten, so a second
   `start` on the same run cannot quietly change its history.
2. Copies the input in: a `.md` file lands at `brief.md` and is turned into
   a plan with `plan_from_brief.py`'s own parsing (the two header dialects,
   the field regexes); a `.json` file is treated as an already-built plan
   and copied straight to `plan.json`.
3. Writes `lines.json` — every scene's PARAGRAPH, keyed by scene id. In the
   scene shape a scene speaks a paragraph, not a line, and that paragraph
   is one chunk of the piece's one continuous read.
4. **Voice — before anything else generates, and as ONE track**
   (2026-09-17, 2026-09-18). If any scene carries words, `machine/voice.py`
   runs now: one custom ElevenLabs voice per character, bound in
   `brands/<brand>/ai-cast/<name>/voice.json` (`voice_id`), on the direct
   ElevenLabs account.
   **On the scene shape it is one continuous read.** One request per scene
   paragraph, each carrying `previous_request_ids` from the responses
   before it, so the read never restarts; the chunks concatenate into
   `<run>/vo/track.mp3`, `<run>/vo/timing.json` says where every scene and
   every sentence sits on that one timeline, and `<run>/vo/<scene>.mp3` is
   the slice the talking door dubs. Those timings are what the clip prompts'
   beats are timed against — nothing in a run chooses a number.
   **On the old shape it is still one call per line**, into
   `<run>/voice/<line id>.mp3` (`--per-line` forces that path anywhere) — never
   through a provider's own wrapped endpoint, because fal's ElevenLabs
   endpoints see library voices only and cannot reach an account-private
   voice id. A character with only a fal library preset name (no
   `voice_id`), or no `voice.json` at all, is a hard stop — `--dry-run`
   included, because nothing here should plan around a voice that cannot
   actually speak. A plan with no line to speak skips this step cleanly.
5. **Turns the plan into batch items.**
   **The scene shape** (2026-09-18): each scene becomes **two still items
   and one clip item**, and nothing else.
   - `<scene>-F1` — the FIRST FRAME, a generation, its prompt assembled in
     the stills order the contract gives (subject · composition · action ·
     location · style · camera · lighting), carrying the scene's references
     in the order the door preserves detail in.
   - `<scene>-FLAST` — the LAST FRAME, an EDIT of the first, its prompt the
     delta plus the one line that says what may not change. **Always two
     references, the frame first and the cast sheet second.** Since the
     one-image-door ruling every edit runs on the same door with input
     fidelity high; the frame's own `Camera:` word (`same` · `push-in to
     <framing>` · `new angle to <framing>`) is still declared, because it
     is what the clip's camera phrase is built from. Every edit is then
     **colour-matched** to the frame it came from (`colour_match.py`)
     before anyone verifies it.
   - `<scene>` — ONE clip: `talking` where the scene is to camera, `motion`
     where it is not. **Its medias are exactly three, in this order** —
     `start_image` (the first frame), `end_image` (the last frame) and, to
     camera, `audio_references` (`vo/<scene>.mp3`, the scene's own slice of
     the one track). **Nothing else rides along**: the first frame already
     carries the identity, the wardrobe, the room and the light, so a cast
     sheet or a style frame attached beside it is a second opinion about
     the same face, and the gate refuses it. Its params are the mode, the
     duration (the slice, rounded up, floored at the door's minimum — the
     ceiling is never clamped, it is refused), the piece's aspect and
     resolution, and `generate_audio`. Its prompt is the maker's four
     blocks — asset line, ONE summary sentence from labelled slots, the
     timeline of beats with their spans from `vo/timing.json`, the
     consistency notes. No number is chosen here, and a block that cannot
     be built from a labelled field is a refusal by name, never a fragment.
   Every field is read from `machine/model-inputs.json` — the model input
   contract — so nothing is assembled from memory of what a door takes.
   **The old shape** turns every scene and cutaway into one protocol batch
   item, `kind: "motion"`, using `prompt.py`'s own `payload()` / `broll()` for the
   prompt text and duration — the same shapes the Cinema line's board
   sends. **The model prompt.py bakes in is dropped before the item is
   written.** `prompt.py` hardcodes Cinema Studio because it was built for
   one house; `run.py` has to run on any provider, so the item carries
   `kind: "motion"` and `platform.py` picks the model per provider from
   `providers.json`, the same way every other gate does.
   - `characters` — the cast's name, for scenes; for a cutaway, only if the
     cast's name shows up in its subject/action/place text.
   - `products` — element uuids in the prompt that
     `brands/<brand>/element-facts.json` marks `kind`./`role` `"product"`.
     A brand with no facts file has no products; it is never an error.
   - `lines` — `[scene id]` for a scene, `[]` for a cutaway. A scene whose
     line was just voiced gets that line's take attached as `medias:
     [{"role": "audio", "value": "voice/<line id>.mp3"}]` — a path,
     uploaded later; preflight's rule 4 (media UUID required) only checks
     role `start_image`, so a path here is never rejected.
6. Shows the platform's plan (station, model, rate, ceiling, cost) and
   confirms only where the provider's `confirm` is true — `--yes` bypasses,
   fal never asks.
7. Splits into the provider's `batch_max` and runs `preflight.check` on
   every chunk — **including the contract gate** (rule 12): every
   scene-shape item validated against `model-inputs.json`. A missing
   required field, a beat naming two actions, a beat naming none, a frame
   with no delta, an edit with one reference, a scene with anything other
   than its two frames, a to-camera scene with no audio slice, more beats
   than the maker's panel limit, a paragraph past the door's duration
   ceiling — each is RED with the field named. Any failure anywhere:
   nothing is written to `batches/` and nothing is submitted, exit 2.
8. **Makes everything, directly.** Every item whose station's door says
   `hand: machine` (all seven since 2026-09-18) runs on the machine hand,
   in order — a `-still` item before the motion item that uses it: cast /
   still → `direct_openai.py`; edit → `direct_google.py`; song →
   `direct_google.py`; a scene with a line → `omni.py talk` (the
   controlled-Omni recipe: line in the prompt → parity → speech-to-speech
   into the character's voice → remux → parity); a cutaway → `omni.py
   motion` (sound stripped). Results land in `media/` and `direct.json`;
   parity verdicts in `verdicts.json`. Then it stops: "machine hand made
   everything".
   **Only if a house was forced** (`--provider`) do motion and talking go
   to that house instead: which family it belongs to (`fal`, `higgsfield`,
   …) comes from `providers.json`, never from a name written in this
   file. A family with its own `providers_<family>.py` submits itself;
   one with none is, structurally, a hand-submitted house. On that hand-submitted
   path, `SUBMIT.md` gets its own **Voices** section — upload each
   `voice/*.mp3`, then use the returned media id as the `audio` media on
   the item(s) that carry it.

## Two hands (Damon's 2026-09-17 ruling — "we scale tomorrow")

**The machine hand runs directly, with nobody at a keyboard.** Cast, still
and edit are called on the direct OpenAI/Gemini APIs (`machine/direct_openai.py`,
`machine/direct_google.py`); the song, when the plan carries one, is Lyria
on the direct Gemini API too; voice was already direct (`voice.py`, step 4
above). **The editor hand** stays motion and talking, submitted to
Higgsfield (or fal) exactly as before. Which station is whose hand lives in
`providers.json`'s own `doors[...].hand` — never a kind name written here.

Inside `start`, right after the batches are preflighted and copied:

1. Every batch item whose station resolves to `hand: "machine"` — a scene or
   cutaway's own `generate` block (`{"kind": "still"|"edit"|"cast", "prompt":
   ..., "references": [...]}`) becomes such an item, id `<scene id>-still`,
   linked back to the scene via `for`; a plan's own `song` block
   (`{"prompt": ..., "clip": bool}`) becomes one more, id `SONG` — is run
   straight through `direct_openai.generate` (cast/still) or
   `direct_google.edit_image` / `direct_google.song` (edit / audio), never
   through whichever provider `--provider` named. An item with an empty
   `generate` (still the default `plan_from_brief.py` writes) makes nothing
   here — the scene animates from whatever medias it already carries.
2. Every file lands at `<run>/media/<item id>.<ext>`; every call is recorded
   in `<run>/direct.json` (`{item id: {file, model, request_id, at, ...}}`)
   and in `ledger.json` via `preflight.ledger`, at `0` seconds (these are
   per-job, not per-second, doors).
3. **These items never reach the editor.** `SUBMIT.md`'s own **Machine-made
   media** section lists every file `direct.json` made; each motion/talking
   item's own block gets a `start_image (upload first)` line naming the
   still made for it (via its `for` link) — the same pattern the **Voices**
   section already used for the ElevenLabs lines. On fal, machine-hand items
   are dropped from the batch fal actually submits, for the same reason.
4. `--dry-run` calls each direct client in its own dry-run mode: it prints
   the request (method, url, redacted headers, body) and writes no media,
   no `direct.json`. A missing key for a machine-hand station is a hard
   stop naming the key (`OPENAI_API_KEY` / `GEMINI_API_KEY`) — `--dry-run`
   included is exempt (a dry run never needs a real key), a real run is not.

`run.py` never names a model — `direct_openai.py` and `direct_google.py`
read `providers.json`'s own `direct.openai` / `direct.google` sections for
every URL, model id and param, the same rule every other module here follows.

## `record`

Takes the `results.json` an editor hands back after submitting a
`SUBMIT.md` sheet by hand — `[{"id","job","url","seconds","status"}]`. For
each row: resolves the model the same way `start` would have (from the
run's own batches and its recorded provider), writes the ledger row
(`nsfw` / `ip_detected` land billing-ambiguous automatically), and — if the
row carries a `url` — downloads it into `media/<id>.<ext>`, archiving
whatever was there before into `media/versions/` rather than overwriting it
(ported from `pull.py`). Merges every row into `results.json`, keyed by id.

**Line parity, automatic** (Damon, 2026-09-18: a talking clip from one door
lip-synced perfectly to the WRONG words). Right after a clip downloads
successfully, if its item carries `lines`, `record` transcribes it on the
direct ElevenLabs API (`machine/lineparity.py`, speech-to-text) and compares
the transcript to the line — PASS at ≥85% match (`providers.json`'s own
`gates.line_parity.threshold`), FLAG below it — and writes the verdict into
`verdicts.json[item]["parity"]` through `preflight.py`'s own verdict writer.
No `ELEVENLABS_API_KEY` reachable is a printed skip, never a failed record;
`--no-parity` skips the check outright.

## `pack`

1. `preflight.coverage` — every line claimed exactly once, and (per the
   two-layer verdict gate) every motion/revoice item carries both a
   `motion` and a `director` verdict on file. Any gap: exit 2, nothing
   packed.
2. Copies every `done` clip's media into `deliverable/`.
3. The naming gate — `deliver.py`'s own `read_brief()` plus `run.json`'s
   `brand`./`format`, handed to `components/naming/deliver.py`'s `deliver()`.
   A field it cannot find is never guessed: printed and exit 2.
4. Writes `deliverable/EDITOR-PACK.md` — WHAT THIS IS, THE CLIPS, LINE
   COVERAGE, POST, THE RECEIPT (from `ledger.json`, never memory), THE NAME
   — plus a VERDICTS section when `verdicts.json` exists.

## The fal / Higgsfield difference

**fal** has a real API and a key (env, the Keychain vault, or
`machine/.env`). `providers_fal.py` submits every item itself: submit,
poll, download, ledger — no person in the loop, no `--dry-run` needed
beyond printing what would be sent. It is a straight port of the retired
`sequence.py`'s HTTP mechanics behind two injectable seams,
`transport(method, url, body, headers)` and `download(url, dest)`, so
nothing here ever touches the network in a test.

**Higgsfield** has no API key on this machine — it is reached by hand,
through the MCP connector or the web app. `start` writes `SUBMIT.md`
instead: one block per item, every param, the prompt verbatim, and the
exact shape to hand back as `results.json`. `--dry-run` changes nothing on
this path — nothing here ever calls Higgsfield's network either way.

**A gap, narrowed, not fully closed.** A scene/cutaway only gets a still
made for it (see Two hands, above) when its own `generate` block names a
prompt — `plan_from_brief.py` still writes an empty one by default, so a
plan built straight from a brief still goes to a `"motion"` item with no
`start_image`, the same one-shot shape `prompt.py` was built for on Cinema
Studio (text + `generate_audio: true`). fal's motion station
(`providers.json` → `providers.fal.stations.motion`) is an image-to-video
model; a motion item built this way carries no `start_image`, so a real fal
submission may be refused by fal itself for the same reason. Preflight
doesn't catch this today because rule 6 (verified start frame) only
applies when a `start_image` is present. Teaching `plan_from_brief.py` (or
whatever composes a plan) to populate every scene's `generate` block is
real, future work, not something worth faking here.

## Fixtures

`machine/fixtures/run-plan.json` — brand `_fixture`, format
`fixture-format`, invented uuids, two scenes and one cutaway. Its cast is
named `Lead`, voiced from `machine/fixtures/cast-root/lead/voice.json` (a
fake `voice_id`, never a real ElevenLabs one) via `--cast-root`, so no test
ever reads `brands/`. Exercised by `test_run.py`, which also covers: a
Higgsfield `--dry-run` (submit sheet, no ledger, no voice files — voice
respects `--dry-run` too); a real Higgsfield start (both lines voiced, the
`SUBMIT.md` Voices section, the audio media on the talking item's batch
entry); a fal `--dry-run` (printed bodies, no ledger); a fal run against a
fake transport/download (media on disk, ledger rows, totals that match
`platform.estimate()`, both lines voiced); `record` with one `nsfw` row
landing ambiguous and separate from a `done` one; `pack` failing on an
uncovered line and succeeding once it, and the two verdicts, are on file;
and a grep guard that neither `run.py` nor `providers_fal.py` ever writes a
model slug from `providers.json` as a literal.

`machine/test_voice.py` covers `voice.py` on its own: every line generated
against a fake transport, the manifest written and matching what is on
disk, a character resolved from the plan's `cast.name` (slugified) or
overridden with `--character`, a clean no-op when `lines.json` has nothing
in it, and the refusal — hard stop even on `--dry-run` — when a
character's `voice.json` carries only a fal library preset name instead of
a bound `voice_id`.

`test_run.py`'s own `StartMachineHand` class exercises the two hands on a
second plan fixture (built in-test, not `fixtures/run-plan.json` — so none
of the counts the fal/Higgsfield tests above assert on are touched by it):
a scene with a `generate` block and a plan-level `song`, run against fake
`openai_transport`./`google_transport`, produces `media/A1-still.png`,
`media/SONG.wav` and `media/SONG-song-timings.txt`, a `direct.json` naming
both models, ledger rows for both, and a `SUBMIT.md` whose `A1` block
carries a `start_image (upload first)` line pointing at the still made for
it — while `A1-still` and `SONG` never appear as their own editor blocks.
A `--dry-run` on the same plan prints both direct requests and writes no
`media/` and no `direct.json`; a run with neither `OPENAI_API_KEY` nor the
Keychain vault reachable is a hard stop naming the key.

`machine/test_direct.py` covers `direct_openai.py` and `direct_google.py`
against fake transports on their own: an OpenAI edit sends every reference
in order under repeated `image[]` parts and decodes `b64_json` to the output
file; no references hits `images/generations` instead; a Gemini edit builds
one `inline_data` part per image plus the text prompt, the registry's
`imageConfig` and a `safetySettings` entry per category; a Lyria call writes
both the WAV and the timing-sheet text file and reports `timed` correctly
for text with and without an `[m:ss]`-style marker, and picks the `clip`
model when asked; every `--dry-run` writes nothing and needs no key; a
missing key on a real call is a hard stop naming it (`OPENAI_API_KEY` /
`GEMINI_API_KEY`).

`machine/test_lineparity.py` covers `lineparity.py` on its own: an exact
line transcribed back is PASS, different words are FLAG, punctuation/case
are ignored, the threshold is read from `providers.json`'s own `gates`
section, a dry run prints the request and needs no key, and a missing key
on a real call is a hard stop naming it. `test_run.py`'s own `RecordParity`
class exercises the automatic step inside `record`: a fake transcription
matching the line writes a PASS verdict and prints it, one that doesn't
writes FLAG, `--no-parity` skips the check entirely (no call, no verdict
file), and no `ELEVENLABS_API_KEY` reachable prints a skip note without
failing the record.

`machine/fixtures/brief-frames.md` + `machine/fixtures/vo-timing.json` +
`machine/fixtures/golden-timing.json` — the SCENE SHAPE fixture: two scenes
(one to camera, one silent), each a paragraph, a first frame, its beats and
a last frame. **Scene 1 is the golden scene** — the shape of the call that
worked live on 2026-09-18 evening (to camera, a push-in last frame, four
beats, 8.92 s of voice → a 9 s clip); `golden-timing.json` is that run's own
timing sheet with the account ids replaced by invented ones, and
`test_frames.py`'s `TheGoldenCall` holds the assembled call to it: the three
medias by role, the params, the four blocks in order, the timeline equal to
that sheet, and each of the four gate refusals by name.
`machine/test_frames.py` runs the whole shape against them: the piece
declaring aspect and resolution once; two stills a scene and nothing
between them; the first frame in the stills order; the last frame as a
delta with two references, the frame first; the face-rescale edit routed
to the fidelity door; one clip a scene carrying both frames, its prompt in
the maker's four blocks, its timeline timed off the track and its words
never written twice; every contract-gate defect refused by name; a green
batch through `preflight.check`; and the old timed shape still parsing and
still planning.

`machine/test_voice.py`'s `ContinuousTests` covers the one read: a
scene-shape run going continuous by itself, the request ids carried
forward (never more than the contract allows), timing cumulative on one
timeline with every sentence placed, the track and a slice per scene on
disk, the slices cut at the scene bounds, a dry run that writes nothing,
and `--per-line` still working.
