# fixtures — what `test_preflight.py` runs against

Invented UUIDs, no brand, no product, no person. Not a `runs/` folder on
purpose: `**/runs/` is gitignored and these must be committed.

| file | what it is |
|---|---|
| `bank.json` | a one-row format bank (`fixture-format`) so tests never depend on the real `formats/bank.json` |
| `sample-run/` | `run.json` (format `fixture-format`), `frames.json` (one verified frame `…a1`, one not `…a2`), `lines.json` (L1–L3) |
| `unknown-format-run/` | a run whose `format` is not in any bank — trips rule 9 |
| `batch-bad.json` | seven items that trip rules 1, 2, 3, 4, 5, 6, 8 and the rule-7 duplicate claim |
| `batch-bad-format.json` | one clean item, checked against `unknown-format-run/` for rule 9 |
| `batch-good.json` | three items on the Higgsfield family (element in prompt · references + product media · motion on the verified frame) — green there, rule 8 on fal |
| `batch-good-fal.json` | the same three shots on the fal family — green there, rule 8 on Higgsfield |
| `cinema-payloads.json` | the bare-list shape `prompt.py payloads` prints, elements in the prompts, `characters` set — green |
| `batch-negation.json` | a still whose prompt forbids subtitles, captions, title cards — must PASS rule 3 |
| `brief-frames.md` | the SCENE SHAPE brief — two scenes, each a paragraph with a first frame, beats and a last frame; the first scene's beat spans are the ones from the scene run by hand on 2026-09-18. Exercised by `test_frames.py` |
| `vo-timing.json` | the timing sheet that brief is planned against — the shape `voice.py` writes to `<run>/vo/timing.json` (8.92 s of voice, four sentence windows), with invented ids |
| `run-plan.json` | `run.py`'s own fixture — brand `_fixture`, format `fixture-format`, invented uuids, two scenes + one cutaway; exercised by `test_run.py`, not `test_preflight.py` |
| `element-library/` | a test-only copy of the element library's shape (`format.video`, `style.video`, four `delivery.*` lists) with invented rows — one defined, one named-only (`[TO DEFINE`), one deprecated. `test_rollout.py` points preflight at it with `--library` |
| `plan-library-good.json` · `plan-library-bad.json` | a brief's json block as rule 13 reads it — delivery dials and a `style_id` that are all on the fixture lists, and one with three that are not |
| `cast-workspace/` | two invented brands, each with its own `core-avatars/casting/roster.json` — shows `promptify.py`'s cast lookup follows the run's brand |

Running `check` on any of these by hand needs the fixture bank:

    python3 machine/preflight.py check machine/fixtures/batch-good.json \
        --run machine/fixtures/sample-run --provider higgsfield-ui \
        --bank machine/fixtures/bank.json

The real bank refuses `fixture-format` by design. Tests copy `sample-run/`
to a temp folder before writing anything, so a green check by hand is the
only thing that leaves a `batches/` folder here — delete it.
