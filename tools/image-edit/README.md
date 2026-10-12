# image-edit

## How to use it → (team dashboard)

Turns a reference picture and ONE change — free words, a named fix, or a
variation row — into the edited picture, judged against the reference, filed
as a new version. No fresh generation, no rewritten words, no touching the
original.

    python3 edit.py <picture> --brand <brand> --change "<one thing>" --dry-run   # check, spend nothing
    python3 edit.py <picture> --brand <brand> --change "<one thing>"             # one delta, one judged version
    python3 edit.py <picture> --brand <brand> --fix <row> ...                     # a fix's arguments and every flag: python3 edit.py --help
    python3 vary.py <baseline> --brand <brand> --v <row:args> [--v <row:args> ...]
    python3 sequence.py <slide-one draft> --brand <brand> --deltas <brief>       # slides two onward, as edits off slide one

Every edit carries a keep/change split (`splits.json`): what is load-bearing
and never moves, and what the one change is allowed to touch. Two judges run
on every result: image-production's own (is this a good picture) and this
component's two-picture judge (the reference beside the result — CHANGE
PRESENT, NOTHING ELSE MOVED). A result that moved anything else is held under
`rejected/`, never delivered.

The two libraries designers run from — `library/fixes-vN-damon.json` (logo,
product, layout, background, remove) and `library/variations-vN-damon.json`
(headline, angle, person, product, colour, background, reframe) — are printed
verbatim by `edit.py --fixes` and `vary.py --library`.

Rules, files and what is not settled yet: CLAUDE.md. The page: context/artifacts.md.

Output: `runs/image-edit/<brand>/<label>/` — `edit.json` or `variations.json`,
the result as a new version beside the original, `rejected/*-why.md`.
