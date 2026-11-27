# Creator brief: talking points, shots and don'ts

A brief for a real creator, booked through Trybe, filming on their own phone. It gives the argument as talking points in the creator's own words, the shots to film and the don'ts. It is not a script: the live creator brief (`components/video-writing/prompts/stage-5-brief/creator-lane/stage5-creator-brief-v28-owner.md`) stays live; this is a new style beside it.

Status: draft. Not in `../briefs.json` and not read by any chain yet; registering and the bake-off against the live style are the wave-2 integrate step.

| File | Holds |
|---|---|
| `creator-brief-v1-owner.md` | the stage prompt: role, inputs, task, a real example, the output shape, the banned list |
| `build.py` | `inputs`: reads an accepted brief and the brand's files, writes the inputs packet and the filled prompt. `check`: tests a finished draft against the prompt's rules |
| `tests/test_build.py` | `/usr/bin/python3 components/briefs/creator-brief/tests/test_build.py` |

## Run it

```
python3 components/briefs/creator-brief/build.py inputs <5-brief.md> --brand <brand> --product <product> \
    --length 30 --format problem_solution --rows <bank row id>,<bank row id> --label <brief label> --out <dir>
python3 components/briefs/creator-brief/build.py check <dir>/creator-brief.draft.md --inputs <dir>/creator-brief.inputs.json
```

- `inputs` reads: the brief's fenced json block (`scenes`, `openings`, `piece`), `brands/<brand>/products/<product>.md` ("What it does", "What the live store says", and every quoted phrase the file calls wrong or invented), `brands/<brand>/offers/guarantees.json`, and the named language-bank rows.
- The stage model writes `creator-brief.draft.md` from `creator-brief.prompt.md`. `check` must pass before the draft is shown.
- `check` fails on: a missing DRAFT header, a missing or out-of-order section, not three hooks, a missing beat, fewer than four or more than six shots, eight words in a row copied from a brief paragraph (sourced quotes and lines on file excepted), a banned phrase outside Don't, a dollar amount not in the guarantee, a studio ask or a pushy close.

## The gate

Nothing is sent to a creator. A draft stays a draft until the owner sends it through Trybe; `inputs` writes `"sent": false` and the draft's first line says so. An ad built from the creator's returned video carries `trybe=<trybe_id>` in its link and at the end of its name.

## How a section of the brief becomes a beat

| Brief `section` | Beat |
|---|---|
| hook | Hook |
| problem, failed-solutions, agitation, enemy | Problem |
| product, solution, unique-mechanism, mechanism | Discovery |
| proof, demonstration, testimonial (and anything unlisted) | Experience |
| offer, guarantee, result | Result |
| call-to-action, cta | CTA |

A beat with no scene is listed under `gaps`; the writer takes it from the openings and the bank rows.

## Source

Beat structure, the four parts (pain as relatable, mechanism as a discovery, proof as experience, the ask as a tip) and the quality criteria are adapted from RMBC `skills/ugc-brief/SKILL.md` (coleschaffer/copywritingskills-rmbc, MIT, © 2026 Stefan Georgi).
