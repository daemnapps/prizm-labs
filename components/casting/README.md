# casting — who plays this role?

## How to use it → (team dashboard)

One engine, one question. Every tool that needs a person in a picture or a
video asks it the same way, instead of each one casting its own way or not at
all.

    import casting
    casting.cast(brand="…", role="a barber who explains the routine")

    → the person already banked for that role, with the evidence
    → or the gap, and the nine steps that close it

**Read `CLAUDE.md` first** — it is the contract, not a summary of it.

---

## The two rules everything here exists to hold

**Identity comes from an IMAGE, never from a paragraph.** A character written
as prose is a different person every roll. The first real step is finding a
frame, not writing a description. What carries from that frame is the WORLD —
the room, the light, the framing, the wardrobe category. What must never carry
is the PERSON. Baseline, not likeness.

**A role the bank covers never gets a new face.** A second face for a role
that already has one breaks the first across everything already shipped. So
the question is asked before anything is built, and a build for a covered role
is held.

## How to use it

### Who plays this role?

    python3 components/casting/cast.py who --brand <brand> --role "barber"

Free, always. It prints the bank it read, the person it found and why, what
that person can front today and what is still missing before they can front
the rest — and, when nobody covers the role, the nearest people, the open
items already on record, and what to do next.

Add `--json` for the same answer as data.

### What could be the baseline?

    python3 components/casting/cast.py find --brand <brand> --like "barber, apron"

Free. Searches the owned footage by WHAT IS IN each clip — not what the file
is called — and returns the frames beside each match, plus anything on the
brand's own reference shelves.

### Build the person the bank is missing

    python3 components/casting/cast.py build --brand <brand> --role "barber" \
        --id <id> --kind authority --noun man \
        --who "…" --wardrobe "…" --world "…" \
        [--detail "hands and forearms"] [--baseline <frame.jpg>] --dry-run

**Always dry-run first.** It spends nothing, writes nothing, and prints the
prompts exactly as they would be sent. Drop `--dry-run` to run it.

## What comes back

| Where | What |
|---|---|
| `runs/casting/<brand>/<label>/` | the prompts as sent, the judge's verdicts, `check.json`, `run.json` |
| `…/register/` | the proposed registry row and what to do with it |
| `…/bible/character.md` | the draft production bible, for a person to finish |
| `…/held/` | any sheet the judge failed, with the reason |
| `brands/<brand>/ai-cast/<id>/` | `master-sheet.png` and `boards/` — the pictures |
| `Team Drive/brands/<brand>/ai-cast/<id>/` | the Drive mirror |

## When to stop and ask

- **The bank already covers the role.** That is an answer, not an obstacle.
  Cast that person; if they are genuinely wrong for this, that is a
  conversation about the bank, not a second face.
- **Nothing in the footage matches.** A baseline is a real frame, and picking
  it the way a person would — the right register, the right room, a clear look
  at the archetype — is a person's job. The search ranks; it does not choose.
- **A sheet was held.** A hold is a prompt to fix, not a picture to patch.
- **The character is filed but not registered.** That is by design: this
  component proposes a row and a person writes it. Until then the character
  exists and is not castable from the bank.
- **No Element and no voice element.** Both need the upload widget, which is a
  person at a machine. Until they exist the character runs on the image chain,
  which takes image urls, and NOT on the Cinema line, which takes element ids.
  Every run says so out loud rather than implying otherwise.

## What it will not do

- **Invent a character from prose.** Identity comes from a frame.
- **Produce a likeness.** The baseline may be a real face; the output is a
  different person, the prompt says so, and the judge is asked it.
- **Coin a name.** The id, the name and the role are the caller's.
- **Write into a brand's registry.** It proposes; a person registers.
- **Rebuild the readable cast sheet.** That sheet is rendered from the records
  by the tool that owns that job, and is never edited by hand.
- **Delete anything on the Drive mount.** Supersede instead.

## Where every part came from

| Part | Lifted from |
|---|---|
| the nine steps, the three prompts, the fal door, "a DIFFERENT person" | `the team notes/avatar-builder/` (`README.md`, `build.py`, `find.py`) |
| the registry shape, and "never invent a person for a role the bank covers" | `the team notes/casting/` (`README.md`, `build_cast.py`) |
| the footage search | `tools/image-production/image_production/assets.py` — **imported, not rewritten** |
| the judge's eyes and its prompt | `tools/image-production/image_production/judge.py` — the questions here are this component's own |
| the gates and the dry-run report | `tools/image-production/image_production/{gates,dryrun}.py`, `components/quality-checks` |
| the path walking, the prompt versioning, the run path | `tools/image-production/image_production/paths.py`, `components/run-kit/run_kit/{prompts,filing}.py` |

`the team notes/avatar-builder` and `the team notes/casting` are untouched and still
work exactly as before. They get retired later, side by side, once this is
proven.

## Tests

    python3 components/casting/tests/test_casting.py

51 tests, stdlib `unittest`, on `/usr/bin/python3`. No network, no model, no
model call, no real key, and nothing written outside a temporary directory.
