# tools/video-teardown — the teardown machine

**video-teardown** — takes **a video ad**, makes **its element labels and a
brief to remake it**. Does not **produce the video**. Triggered by
`python3 machine/run.py <video> --brand <brand>` (add `--dry-run` to check the
whole plan and spend nothing).

the owner's teardown chain: a swiped video goes in, a shot-ready creator brief
comes out. **Graduated from `the team notes/` 2026-08-25 (the developer ruling); homed at `tools/video-teardown/` same day under the three-station design** — the first lab graduation after PM, run deliberately as the worked example of the
process. `README.md` is the doctrine: it is the owner's, written in his voice,
and his corrections outrank anything a session writes here.

**A LIBRARY — the public surface** (the developer, 2026-10-07, triage action 6 (declare public surfaces), provisionally on the owner's behalf — he sees it in the decision log and may strike any line; this clause replaces TI-1 (adapter card) as the contract callers rely on). Callers put `machine/` on the path or load one file by path, and may use only these names:
1. **Commands:** `machine/run.py <video> --brand <b> [--route --label --creator --product --for-avatar --from --to --only --stages]` (mini: `--source`) — a working run in `machine/runs/<slug>/`, filed to the two shelves below; `machine/swipe_match.py <run> [--approve-structure … | --damon-read]`; `machine/compose.py plan`.
2. **Production's gates** (pure reads of a brief's text): `swipe_match.stamp_of(text)` → `PASSED|HELD|STALE|None`; `swipe_match.read_of(text)` → `APPROVED|STALE|None`; `swipe_match.brief_hash(text)` → the 16-hex fingerprint; `manifest.status_of(text)` → `COMPLETE|MISSING|STALE|None`; `manifest.check(run_dir, brand, brief_name)` re-checks and rewrites the block; `spoken_check.check_lines([(id, text)])` → `[{id, text, found}]`; `cast_match.check(run_dir)` (findings at `[1]`), `cast_match.readable_mismatches(body, doc, brand)` and `cast_match.scene_mismatches(doc, brand)` → `[{n, element, why}]`; `cast_match.repair(run_dir)`.
3. **Helpers:** `deepen.ask(media, prompt)` → the model's text; `transcript.scribe_only(media)` → `{words: […]}`; `culture.pull(dir, url, runner=)` → `(path|None, why)`; `md.render(markdown)` → HTML; `chain.drive_root()` → the Team Drive `Path` (raises `MountError`); `chain.stages(brand, asset_type, route, lane)` → the stage list, with `chain.route_for`, `chain.PROMPT_HOMES`, `chain.GEMINI_MODEL`, `chain.CLAUDE_MODEL`; `tools/gemini_breakdown.key()`, `.req(url, …)` → parsed reply, `.BASE`; `tools/storage.drive_root()` → `Path|None`.
4. **Read by path:** `machine/runs/<slug>/` (`run.json`, `stages/1-teardown.md`), `records/creators/<handle>/`, `machine/chain_config.json`, and `prompts/` + `README.md` read or copied whole — a reader that pins one prompt version by file name carries its own risk.
5. **SEAM, not public:** `run._clean_env()` (ad-variations `proven_to_format.py`). A seam renamed keeps its old name as an alias until its callers move. `keys.py` is NOT on this surface: four callers import it for keys read by path, a wall; they move with the keys work (video-production#1 (keys by path)).
Everything else in `machine/` and `tools/` is internal and may change without notice. The tests in `new-workflow-design/builds/vt-multiuser/` and `teardown-integration/` test internals on purpose and are not callers.

## Rules for working here

1. **the owner owns this folder and this folder is primary.** He works here the
   way he always has — sentences into a Claude session, the session runs the
   CLI (`machine/run.py`), the board is the view. Preserving that experience
   is a ruled design constraint, not a preference.
2. **His notes are his.** `notes/`, TODOs, and wants-next files are the owner's
   own roadmap — never a work queue for anyone else. Work reaches the team
   only when he flags it explicitly (process being designed in PM).
3. **Sessions other than the owner's touch this folder only for**: the
   runs→records adapter surface, path/key graduation mechanics, or a change
   the owner asked for — and anything ambiguous stops and asks him.
4. **Agnostic on every axis — brand, product, avatar — in the prompts AND
   in the code (the owner, 2026-08-25; product + avatar made explicit
   2026-08-30).** Workspace rule 7 applies here with teeth, because this
   machine is meant to run on any piece of content for any brand we own.
   Rework an *example* freely — an example is illustrative and always was,
   and a prompt should say so at the top, before its first example, not
   only in a footnote. But **nothing that gets filled in at run time may
   name a brand, a product, a category or an avatar.** That detail arrives
   only through variables resolved from `brands/<brand>/`. The same test
   applies to code: a word list, a regex, a path or a default that only
   makes sense for one brand is a bug, not a shortcut. If a rule cannot be
   written without naming the brand, it belongs in that brand's folder,
   not in this machine.
5. Media and run outputs live on the team Drive, never in git (workspace
   rule 3). Keys live in `~/.daemn/keys.env` on the owner's machine today;
   company-account keys land in the ruled key home when that migration runs.
6. The retired shared chain (`new-workflow-design/builds/video-teardown/`)
   is history, not a reference — this machine replaced it entirely
   (decision log 2026-08-25).

## Gates

One check reports without stopping a run (the elements validation); the rest STOP it.

1. **The audit (stage 4e on the config, shown as 4f on the board).** Eleven
   checks of the finished script against the source. **Since 2026-09-30 a
   verdict other than SHIP holds the chain** (`AUDIT-HOLD.md`) — but what the
   swipe itself does is only ever a NOTE, never a FAIL (audit v8: "If the swipe
   has it, that's what we do"); each failed check
   is A<n>, passed only by a fix and re-run or `--approve-structure A5`. the owner:
   "do whatever is necessary to fix this problem" — a scene staging a result
   the product does not deliver had been reported by three passes and fixed by
   none.
2. **The elements validation** (`machine/elements_check.py`, 2026-09-20).
   After stage 1c files `doctrine.json`, every label in it — framework,
   awareness entry and exit, sophistication, sections, techniques, the
   delivery dials — is looked up in the shared element library
   (`components/elements/`) and written to `elements.json` beside it. A value
   the library does not hold is **recorded as unknown, never dropped and never
   nudged onto the nearest row**: it is the evidence that the library is
   missing a row. It costs nothing (two JSON reads) and never fails a run.
   The framework bank re-checks every banked run on refresh.
   Off: `VT_NO_ELEMENTS_CHECK=1`.
3. **The structure lock** (stage 3, 2026-09-24 — the one gate that STOPS the
   chain). the owner: "literally this cannot happen again UNLESS I DISCRETELY SAY
   SO. THE WHOLE POINT IS TO TAKE A SWIPE AND ADAPT, not ruin it." The
   rewrite (v12) keeps every place, role, speaker and beat of the swipe; a
   brand's position files shape the words only. Any ELEMENT LEDGER row it
   marks Adapted or Dropped, and any STRUCTURE QUESTIONS FOR DAMON it raises,
   hold stage 3 (`status: held`, `STRUCTURE-CHECK.md` in the run) and nothing
   after it runs. Only the owner's numbers release it:
   `run.py <video> --approve-structure 2,Q1` (or `all`) re-checks the SAME
   rewrite — never re-writes it — and the prompt is told which changes he
   approved. There is no off switch. Test: `machine/test_structure_lock.py`.
4. **The swipe match** (stage 5, 2026-09-24 — STOPS the chain, and production
   refuses what it did not pass). the owner, before batching many videos for many
   brands: "make sure this never happens again, literally." The rewrite's
   own ledger is not trusted: `machine/swipe_match.py` has a judge (prompt
   `prompts/stage-5m-swipe-match/`, the strongest Gemini we hold) compare the
   FINISHED brief with the swipe's teardown shot by shot — place, people,
   camera, who speaks, order, added or dropped scenes — quoting the brief's
   own words, plus a machine check that a selfie shot stays a selfie. Every
   change is numbered M1, M2…; any not approved (`--approve-structure M2` or
   `all`) holds stage 5 and writes `SWIPE-MATCH.md`. The brief's first line
   carries the stamp; video-production's `run.py start` refuses a brief
   without `swipe-match: PASSED`, or one edited after its check (binding the
   cast is not an edit). `--composed` there is only for a brief made with no
   swipe. Findings are kept per brief, so an approval never renumbers them.
   Test: `machine/test_swipe_match.py`.
5. **The manifest** (stage 5, right after the swipe match, 2026-09-24). the owner:
   "a manifest at the end of every brief to make sure teardown record, and
   final brief has the core elements that literally make this ad work before
   we can go into ai production — i do not have time to babysit this anymore."
   `machine/manifest.py` writes a block onto the END of the brief: every
   ELEMENT (E1…) and LOAD-BEARING item (L1…) of the replication spec pointed at
   the scene that carries it (a judge, prompt `prompts/stage-5n-manifest/`,
   quoting the brief), the swipe-match stamp, every person/look/voice/place/
   product/prop banked or to make, and every $ figure found in `brands/<brand>/`
   or flagged. Last line `MANIFEST: COMPLETE` or `MISSING — …`, tied to the
   brief's fingerprint. A missing core element or unsourced price holds stage
   5; elements still to make do not (that is a fresh brief's normal state).
   video-production re-checks it before spending and refuses anything but
   COMPLETE. A missing core element passes only on `--approve-structure E6`.

6. **Every line of the swipe** (stages 1 and 3, 2026-09-24). The teardown
   model was asked for the transcript "word for word" and wrote 9 fragments
   for 26 spoken lines ("…" for the rest, two lines in the wrong mouth), and
   every later stage lost the swipe's back-and-forth. Now `machine/transcript.py`
   runs right after stage 1: the audio is transcribed (ElevenLabs speech-to-text,
   speakers separated), one numbered line per speaker turn (T1…), appended to
   the teardown record as `### VERBATIM TRANSCRIPT` and kept as
   `transcript.json`. The spec (v4) lists a real exchange as an element; the
   injection (v13) carries one row per T-number; the stage-3 gate holds any
   missing number as a Dropped change.

7. **The hook is a format** (stage 4b, 2026-09-25 — STOPS the chain). the owner:
   "we're building out a format … all we want to do is adjust its variables …
   we just inject words from our language bank." Then: "this is literally
   perfect. This is how we get this done." Hooks prompt v16 prints the source's
   opening line, card and first frame with named `[BLANKS]`; every blank is a
   named ELEMENT with what it must hold, in element names only
   (`[PLACE] holds [EXPERT]`). The control fills the blanks with the swap;
   each variation keeps every fixed word and fills the blanks from the
   avatar's own words; `[RESEARCH: …]` blanks are researched with a receipt.
   `machine/hook_format.py` checks, with no model: the format's words are the
   source's own (line and card), no blank swallowed a shared word (repaired
   mechanically when it did), every version keeps every fixed word, every
   blank has an ELEMENTS line. A break holds 4b (`HOOK-FORMAT.md`);
   `--approve-structure H3` passes one. Creativity is the spice's job, not
   the hooks'. Test: `machine/test_hook_format.py`.

8. **The route lock** (every writing stage, 2026-09-30 — STOPS the chain at
   the end of the teardown). the owner's four stations (2026-09-25): tearing a
   swipe down is one job and writing our version is another, and writing
   starts only on a route a person picked — creator, ai or founder
   (`--route`). There is no default any more, and 1b's ROUTE RECOMMENDED is
   printed as a suggestion and never switches the run ("it kept going and
   wrote for the wrong thing"). With no route, stages 0, 1, 1k, 1c and 2 run,
   every other stage waits, `run.json` carries `waiting_for: route`, and the
   run is filed like any teardown. A run already written on a route before
   the lock keeps it. Map and hand-offs: `notes/four-stations-map-damon.md`,
   `notes/four-stations-contracts-damon.md`. Test: `machine/test_route_lock.py`.

9. **No more frames** (2026-09-30, the owner: "no more frames, only the brief and
   swipe file link"). Stage 6 never runs, on any route. Every brief opens with
   `**Swipe file:** <link>` (creator brief v28, AI brief v19, her page v7), and
   the creator and founder brief end each concept with HOW TO SAY IT — the
   spice sheet turned into notes she reads. Test: `machine/test_route_lock.py`.

10. **Every person is the swipe's person, and the brief says so** (stage 5,
   2026-10-01 — STOPS the chain). the owner: "why did you make doctor 3 a woman
   if you knew it was a man?" then "did the brief follow the element?"
   `machine/cast_match.py` pairs each brief person with the swipe person they
   stand in for and compares gender (P-), then reads every word of the brief
   about that person — the readable cast block (R-) and every scene direction
   (D-, their own hands, clothes and look) — against their banked element.
   Any finding holds stage 5; `cast_match.repair()` fixes the words from the
   element. Production's element check (3.1) runs the same reading.
   Test: `machine/test_cast_match.py`. Then, on an AI brief, **production's own
   brief contract** (video-production `model_inputs.brief_violations`) — anything
   production would refuse holds the brief here, not at the spend (2026-10-01).

11. **The swipe, shot by shot** (stage 1 + stage 5, 2026-10-01 — STOPS the
   chain at 5). the owner: "map out every single frame so when we describe what
   happens in our version it's as close as possible to the swipe." After the
   transcript, `machine/framemap.py` finds every cut in the pixels and has the
   strongest Gemini watch each shot at 8 fps (prompt
   `prompts/stage-1f-frame-map/`): who is in frame, start and end frame, camera,
   every moment with its time and body geometry, words on screen, sound, edit,
   and the capture (resolution, fps, bitrate). `framemap/FRAME-MAP.md` feeds
   the brief as `{frame_map}`. At stage 5 the brief is held on any swipe insert
   it has no scene for, any on-screen word it drops, or an arm entering from
   another edge (video-production `storyboard_plan.swipe_carry`, F<n>;
   `--approve-structure F3` passes one). Tests: `machine/test_framemap.py`,
   video-production `machine/test_storyboard_plan.py`.

12. **The swipe's style and format** (stage 0, 2026-10-09). the owner, after a
   3D-animated swipe came back as a photoreal cast (and the doll ads before
   it): "we need to also know the actual creative style and format that it's
   in … it needs to be picked up so we're not wasting time on credits." Triage
   v3 names both as element-library ids (`{styles}`, `{formats}`, the
   brand-free lists) or `new:<name>`; `run.py` writes `style_id` and
   `format_id` onto `run.json`, which the shelves copy into the repo with
   every swipe. Production's element makers put that style at the top of
   every prompt in place of photoreal and refuse a style the bank does not
   hold (video-production `make_character.style_lock`). Tests:
   `machine/test_swipe_style.py`, video-production
   `machine/test_swipe_style_lock.py`. Chain doc: video-production
   `THE-CHAIN.md`, "The swipe's style is read at 1".

Also at the end of every run (2026-09-20): the run's words are **copied** to
the repo's one home for run records, on two shelves with one slug
(2026-09-30, the owner: "naming needs to be lined up cleanly across all the
tools"): `runs/video-teardown/<brand>/<slug>/` holds what was read off the
swipe (stages 0, 1, 1k, 1c, 2, the transcript, the Sound Sheet, `doctrine.json`,
`elements.json`, `post-talk.json`) and `runs/video-writing/<brand>/<slug>/` holds everything
written for the brand (1b, 3, 4a–4g, 5, 7, 7b, 8, RULINGS, swipe match,
manifest, `deliverable/` — the brief production takes). `run.json` sits on
both. `machine/file_run.py`; text only, nothing over 1 MB. Test:
`machine/test_shelves.py`. Every filing also rebuilds the brief index,
`runs/video-writing/INDEX.md` + `index.json` (`machine/brief_index.py`, test
`machine/test_brief_index.py`) — one row per brief, joined to its production
runs by their `brief_from` and to edits by the kit's `from_run`.
`machine/runs/<slug>/` is still the working folder and nothing moved.
Off: `VT_NO_REPO_FILING=1`.
