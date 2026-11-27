# components/generative-model-house — what each model does

**generative-model-house** — answers **which model does which job** (pictures, image edits, clips, swipe-footage
swaps, voices, songs, sounds, word timings, judging, upscaling, 3D) for every tool that makes media. It does
not **make anything**: the tools call the models; this says which one.

the owner, 2026-10-20: *"any of these generative tools that we build should just reference model house. There's
no reason to write it into anything specific … Model house should be a component. That way we can adjust our
model house and keep that separate from the actual workflow and just reference it directly."*

Named the Generative Model House by the owner, 2026-10-20: other kinds of models, called by other tools, may join later; for now it holds the generative ones.

## The rule for every tool

- A tool never writes its own model choice. People read `MODEL-HOUSE.md`; code reads `models.json` through
  `model_house.py` (`MH.model("pictures.edit")`). An unknown job is refused by name.
- To add or change a model: change `models.json` and `MODEL-HOUSE.md` together, here, and every tool follows.
- Per-format model choices, once ruled, are recorded here too.
- Cost is never a reason to pick a model the house does not name for that job.

## The four new-resident questions

- **Engine + owner:** `model_house.py` (a reader; stdlib, no credential, writes nothing). Owner the owner.
- **Definitions + curator:** `models.json` + `MODEL-HOUSE.md`. Curators the owner and the developer, either one's approval counts (the developer, relayed verbatim by ◆ PLAN [60643d], ≤04:34:30Z 2026-10-22: "We can both curate all models").
- **Plane:** none for the manifest. `spend.py` (the spend meter and the guard the paid doors ask before they send, 2026-11-25;
  its limits in `spend_limits.json`) appends one line per paid call to `runs/generative-model-house/_system/spend/<YYYY-MM>.jsonl`.
- **Manifest per entry:** each job names its model id and the door (service) it runs on, with what it is
  good and bad at where that matters; `status` on the file (draft / approved / deprecated).
- **Runs by:** both (read by people's runs and the mini alike).

## Doors and keys

The model ids here are the makers' ids. Which service door carries each call, and its request shape, stay in
each tool's own door file (e.g. `components/video-production/machine/providers.json`) — the door file follows
this house, never the other way round.

## Tests

    /usr/bin/python3 -m unittest discover -s components/generative-model-house -p "test_*.py"
