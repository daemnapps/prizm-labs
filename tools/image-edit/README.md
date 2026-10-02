# Image edit

A finished picture and **one change** in; the same picture with that one
thing changed out — judged against the original and filed as a new version.
The change can be your own words, a named fix (wrong logo, wrong product,
move one thing, swap the background, remove one thing) or a variation off a
baseline (new headline, new angle, another person, another product, another
colour, another background, another frame). No fresh generation, no
rewritten words, and the original is never touched.

The editor never types a command: they say "swap the logo on this", "make
three variations of this draft", "make slides two to five off slide one",
and the agent runs these. No brand lives here: a brand arrives only through
the brand folder.

## The one rule, and the second one

    generate from a description        4,262 chars   wrong wardrobe, blended faces
    edit, but still describing it      766-1,133     composition better, caption wrong
    EDIT, DELTA ONLY                     204-386     scene held, wardrobe right, legible

1. **The instruction carries the change and nothing else.** The picture
   carries the composition. An instruction that describes what the picture
   already shows tells the model to rebuild it. A change past 400 characters
   has started describing the scene and is refused before anything is spent.
2. **One change per edit** (two at a push). Five changes in one sentence come
   back wrong and nothing says which one did it. Counted, and refused.

Every picture has a **keep/change split** — what never moves and what may
(`splits.json`, one row per kind: `picture`, `slide`, `frame-A/B/C`).

## How it runs

Higgsfield's image models are reached by the agent, not by a script, so an
edit is two halves with the agent in the middle — the same shape as image
production's plates:

| Step | Who | What happens |
|---|---|---|
| 1 · prepare | `edit.py` / `vary.py` / `sequence.py` | The change is checked against both rules, the brand's logo or product photo is found if the fix needs it, and `job.json` is written: the instruction exactly as it is sent, the model, the frame, the reference pictures in order, and the judge's prompt. Nothing is spent. |
| 2 · make | the agent, on Higgsfield | `generate_image` with the job's model and settings, the reference picture first in `image_references`, then each file in order. A 4:5 reference is edited at 4:5 and then finished to 9:16 with [`skills/resize-9x16.md`](skills/resize-9x16.md). The results go in `results.json`: `{slug: picture}`. |
| 3 · bring back | `edit.py --ingest` | Both pictures — the original beside the result — go to the two-picture judge. A pass is filed as `<name>--<fix or edit>-v<N>.png`; anything that moved something else is held under `rejected/` with the reason. |

The model is the one the editing skills name — **GPT Image 2.5**
(`gpt_image_2_5`, variant `sunburst`, high quality, 2k). Before a run the
agent looks for a newer version of that same model and uses it; never a
different maker on its own. `--model` changes it for one edit.

## The commands

| Step | Command |
|---|---|
| One change, your words | `edit.py <picture> --brand <brand> --change "the tube is in her left hand"` |
| A named fix | `edit.py <picture> --brand <brand> --fix logo` · `--fix product --product <slug>` · `--fix layout --arg element="the badge" --arg where="top right"` |
| Only one part may change | add `--region 4,10,96,34` (left, top, right, bottom, in percent) |
| Variations off a baseline | `vary.py <baseline> --brand <brand> --v headline:headline="Your new headline" --v colour:from_colour=teal,to_colour=gold` |
| Slides two onward, off slide one | `sequence.py <slide-one> --brand <brand> --deltas <06-brief.md or deltas.json>` |
| Check first, spend nothing | add `--dry-run` to any of them |
| Bring the pictures back | `edit.py --ingest <run folder> --results results.json` (one edit, a variation set or a sequence) |
| Read the libraries | `edit.py --fixes` · `vary.py --library` |

`results.json` takes, per job: a path; a list of paths (several rolls); or
`{"content": "<the edit at 4:5>", "file": "<the finished 9:16>", "judge": {…}}`.

Everything lands in `runs/image-edit/<brand>/<label>/`: `edit.json` (what was
asked, the instruction, the count, the verdicts, the versions), `job.json`,
the delivered versions, and `rejected/*-why.md`. A variation set or a
sequence adds `variations.json` / `sequence.json` and one folder per row.

## The two libraries — the prompts designers run from

| File | Rows | What a row is |
|---|---|---|
| [`library/fixes-v2-damon.json`](library/fixes-v2-damon.json) | logo · product · layout · background · remove (· text, parked) | a spot fix on a finished picture: one change with `{slots}`, the keeps it adds, what it needs, which brand file rides along (the logo, the product photo), and the test the judge adds |
| [`library/variations-v1-damon.json`](library/variations-v1-damon.json) | headline · angle · person · product · colour · background · reframe | a variation off a baseline, the same shape. Image teardown's variation stage writes its list against these ids |

Every row carries `status` (draft / approved / parked / deprecated). A
changed row is a **new file** `-v<N+1>-damon.json` beside the old one; the
highest number wins. A missing slot is refused by name. A parked row is not
run: **`text` is parked** — four live attempts at re-lettering one line
redrew the product's label, re-composed the frame, or painted the band black.
Wrong words are changed in the brief's type layer and recomposed
(`tools/image-production/tools/compose.py`), which is exact and free.

## The judge

[`prompts/compare-judge-v1-damon.md`](prompts/compare-judge-v1-damon.md) —
two pictures, the original beside the result, the change that was asked for,
and two standing tests: **CHANGE PRESENT** and **NOTHING ELSE MOVED** — plus
the fix's or variation's own test (a sequence adds: same person, product,
palette and framing as slide one).

It runs on Gemini with the key image production's own judge reads
(`GEMINI_API_KEY`). With no key, the agent can answer the same prompt — it
is written, filled in, into `job.json` as `judge_prompt` — and return its
reply as `judge` in `results.json`. **The judge not running is a hold, never
a pass.**

## `region` — the only thing that makes "nothing else moved" a fact

With `--region`, everything outside the rectangle is put back from the
original, pixel for pixel, when the result comes in — whatever the model did
there. Measured on one line of type, 22 Sep: with no region the product's own
label redrew itself every roll; with the paste-back alone the label held, but
the model had re-composed the frame and the band carried a shifted copy of
the headline — which the judge holds. The region fixes what is outside the
box; the judge still checks what is inside it.

## The editing skills

[`skills/`](skills/) — the same one-change edits as skills an editor pastes
into Higgsfield once and then calls by name: **resize to 9:16**, **logo
swap**, **avatar swap**, **element swap**. Each names its model and checks
for a newer version of it before every run.

## Rules it holds itself to

1. **The original is never written to.** A result is a new version, counted
   up per picture under the brand's run folder.
2. **No brand, product, person or model in the code, prompts or libraries.**
   A test reads the `brands/` tree and checks.
3. **Refused, never guessed.** An unknown fix, variation, kind, brand or slot
   stops the work and names the real ones.
4. **Keys by name, never by value.** This tool reads one key — the judge's —
   through image production's own reader.
5. **The band is measured on the change.** The keep list is capped separately
   (700 characters for the whole instruction): a longer keep list is a
   tighter edit, not a looser one.
6. **A logo or product is never drawn from memory.** The fix attaches the
   brand's own file, or is refused.

Tests: `python3 tools/image-edit/tests/test_image_edit.py` — stdlib
`unittest`, temp folders only, Higgsfield and the judge stood in for. No
network, no key.
