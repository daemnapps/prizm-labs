# profiles — the one door to a person, and the standard a profile is built and checked against

**profiles** — takes **a brand and a profile name (`<avatar>[_<sub>][_<demographic>]`)**, gives **the profile as one object with the same shape every time (card, slots, doubts, awareness, stage, state), a check against the standard, an audit of every profile of a brand, and a list of tools that still take a person around the door**. Does not **build a profile (creative-strategist's `who.py` does), name one (naming does), spend, or write `brands/`**.

**Owner:** the owner · **Station:** `components/` — made 2026-11-27 when profiles replaced avatar and sub-avatar as how tools name a person.

Runs by: person — a person asks for a profile to be built or checked; the mini does not.

| New-resident question | Answer |
|---|---|
| Engine + owner | `profiles.py` (`load`, `check`, `audit`, `doors`); the standard is `SPEC.md` |
| Definitions + curator | `SPEC.md` (the parts every profile has); names live in `components/naming/PEOPLE.md`; the owner signs names |
| Plane | reads `brands/<brand>/core-avatars/` and `runs/creative-strategist/<brand>/{profiles,who}/`; `doors --save` writes `runs/profiles/_system/doors.json` |
| Manifest | none |
| Runs by | person |

## The rules

1. One door. A tool takes a person with `--profile` (through `naming/profile_arg.expand` or `profiles.load`), never `--avatar` / `--sub`, and never reads a `core-avatars/` folder to find one.
2. One standard. `profiles.check` fails structure (no card, no slots, wrong name, uncited line, missing doubt kind, awareness or stage) and only notes lower levels. Nothing is filled by guess.
3. A profile is built by `who.py` and filed by the owner's yes; this component reads, never writes a profile.
4. Brand-agnostic: no brand, product or person named in code, docs or tests (a test checks it). A brand's names live in `brands/<brand>/core-avatars/people.json`, its thresholds in `criteria.json`; see `CREATE.md`, "Any brand".

## Commands

    python3 profiles.py audit --brand <b>                    every profile against the standard (exit 1 on a fail)
    python3 profiles.py check --brand <b> --profile <name>   fails and notes for one
    python3 profiles.py show  --brand <b> --profile <name>   the profile as one object
    python3 profiles.py gate  --brand <b> --profile <name>   evidence and distinctness against its siblings (CREATE.md)
    python3 profiles.py init  --brand <b>                    the new-brand checklist (what stands between each profile and ads)
    python3 profiles.py doors [--save]                       tools still around the door
    python3 profiles.py pick  --brand <b> --avatar <a> [--product <p>] [--seed <s>]   the profile a send or ad speaks to when a plan names only the avatar

`pick` is how planned work reaches a person: email-production (`brief.chain_argv`) and the promo pack call it when the
calendar names only an avatar. It takes a profile with a filed card that passes `check` and that the product fits
(`who.fits`), the same one for the same seed, spread across the avatar's profiles as the seed changes. None: the run
speaks to the whole avatar.

Skill: `avatar-profile` (create, check, audit, file). Tests: `tests/test_profiles.py`.
