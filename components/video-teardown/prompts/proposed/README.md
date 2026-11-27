# proposed/ — prompts written for the owner to read; only switched-on stages run

**Switched on (2026-11-07, the owner's pick):** `stage3` (injection v10), `stage4i` (idea v2), `stage4v2a` (hooks v9).
Every other stage here is off and its live prompt runs. Research (`stage1r`) stays off because only the mechanism
stage, also off, reads it.

**2026-11-09:** the live brief writer is now `stage5-ai-brief-v13-the owner` (v12 + A SCENE IS ONE MOMENT, in `video-writing/prompts/v2/`). The proposed `stage5-ai-brief-v13-owner.md` here carries that rule word for word and goes live, if picked, as v14.

Nothing in this folder runs on its own. The chain picks the highest-numbered prompt in a
stage's own folder (`machine/chain.py`, `PROMPT_HOMES`) and the writing line names its
prompts by hand (`video-writing/machine/writing_v2.py`, `PASSES`); this folder is neither,
so a file here can never become live by accident.

## The switch (2026-11-07)

Each file below has one switch in `components/video-writing/machine/proposed-switches.json`
(the map from stage to file is `chain.py` `PROPOSED_FILES`). Every switch is `false`: with
all of them off the run plan is byte-for-byte the live one
(`video-writing/tests/test_proposed_switch.py` proves it). A switch is set to `true` only for
a stage the owner picked on the bake-off pick page; that stage alone then reads its file
here. `VW_PROPOSED=stage4g,stage5` turns stages on for one shell, for a test run, without
touching the file.

To make a picked file permanent later: move it into the folder named in the last column,
point `PASSES` (or the stage folder) at it, move the old version to that folder's
`archive/`, and set the switch back to `false`.

| File | Stage (switch) | What it changes | Where it goes when picked |
|---|---|---|---|
| `stage1b-audience-v14-owner.md` | `stage1b` swap | v13 plus 4c · AUDIENCE LANE: one of 40 audience lanes with its core emotion, five `AUDIENCE LANE` labels added at the end of the answer | `video-writing/prompts/stage-1b-audience/`, v13 to its `archive/` |
| `stage1r-research-v1-owner.md` | `stage1r` add, after 1b | New stage: one research page per brief: buyer, pains, desires, doubts with bank row ids, proof ranked 1–5, competitor grid, what is not on file | a new `video-teardown/prompts/stage-1r-research/` home |
| `stage1m-mechanism-v1-owner.md` | `stage1m` add, after 1r | New stage: up to 7 named reasons the product clears skin, scored new / specific / believable, features on a separate supporting line; proposals only, the ruled mechanism is printed beside them unchanged | a new `video-teardown/prompts/stage-1m-mechanism/` home |
| `stage3-injection-v10-owner.md` | `stage3` swap | v9 plus STRIP THE SHELL: the swipe's surface phrases are replaced, its structure kept; check 6 · SHELL | `video-writing/prompts/v2/` |
| `stage4i-idea-v2-owner.md` | `stage4i` swap | v1 plus the emotion contract, the promise in one sentence, the strategy brief and five angles, written before the controlling idea; reads the audience lane (`{audience_read}` = `@stage1b`) when the audience switch printed one | `video-writing/prompts/v2/` |
| `stage4v2a-readhooks-v9-owner.md` | `stage4v2a` swap | v8 plus the menu: three ways in, six opening types with dead openings banned, a ten-line hook battery; ENTRY/TYPE/TRIGGER tags | `video-writing/prompts/v2/` |
| `stage4v2b-build-v10-owner.md` | `stage4v2b` swap | v9 plus THE STORY BUILD: beat map, cause chain, story engine, scene turns, gears, proof hold, rhythm, opponent, inner voice, evidence, offer type, what is owed, cliff end | `video-writing/prompts/v2/` |
| `stage4v2b-patch-v2-owner.md` | `stage4v2b-patch` swap | v1 plus THE CUT ORDER: over-length scripts give time back in one fixed order; payoff set-up, payoff, verdict and ask are never cut | `video-writing/prompts/v2/` |
| `stage4e-audit-v12-owner.md` | `stage4e` swap | v11 plus five copy gates and a 0–100 copy score, reported only; the verdict and re-run words are unchanged | `video-writing/prompts/v2/` only. **Not** `video-writing/prompts/stage-4-loop/4f-audit/`: an older file of the same name (a different text, the v1 audit line) lives there |
| `stage4g-spice-v10-owner.md` | `stage4g` swap | v9 plus THE LINE DOCTOR: each spoken paragraph drafted, reviewed on seven line checks with P0–P2 cards, fixed in a separate pass | `video-writing/prompts/v2/` only. **Not** `stage-4-loop/4g-spice/`: an older file of the same name (the v1 spice line) lives there |
| `stage4r-ruler-v1-owner.md` | `stage4h` add, after 4g | New pass: our script measured with the ruler the teardown used on the swipe, one row per gap; report only. Its pass key is `stage4h` because `stage4r` is the old Reading step. It reads `{full_script}` = `@stage4d`, the script the audit reads, after its patches | `video-writing/prompts/v2/` |
| `stage5-ai-brief-v13-owner.md` | `stage5` swap | v12 plus seen, acted, timed, gated: feelings as what the camera sees, a five-step reaction, a line-time budget, a show-now-or-hold-back list | `video-writing/prompts/v2/` |
| `format-call-guidance-v1-owner.md` | none (not a prompt; shown nowhere yet) | The short guidance for the person deciding on a format the lists do not know: decide by the structure, and one line each on when to choose Same as X, Its own format, Not a format (held for review, 2026-11-18) | the text shown at the format call, once reviewed |
| `narrator-montage-timing-owner.md` | none (not a prompt) | Time budget per part for the narrator-montage format: hook about 30%, body about 55%, proof about 5%, offer and ask about 10%; a part that needs more takes it from another part inside the planned runtime, and seconds the runtime can't give are flagged for the owner, never run long | the table in `video-production/formats/narrator-montage/FORMAT.md` |

`stage1c-doctrine-v3-owner.md` went live on 2026-09-20 on the owner's word. It now sits in `stage-1c-doctrine/`, and v2 is in that folder's `archive/`.
