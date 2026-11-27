---
name: casting
description: Find who plays a role — a brand and a role go in; the person already banked for it comes out (with the evidence), or the gap and the nine steps that close it. Use whenever someone says "who plays the barber for <brand>", "who do we have for <brand> as <role>", "do we already have someone for this role at <brand>", "is there a person banked for <brand>", "who fronts the script for <brand>", "who do we have for this avatar at <brand>", "find a baseline frame for <role> at <brand>", "we have no one for this role at <brand>, what do we need", or "show me the cast for <brand>".
---

# Casting

> **Activates component:** `components/casting` — `cast.py`, which answers "who plays this role?" from the brand's banked cast (`who`, `avatar`, `find`) and, for a gap, plans or runs the nine-step build (`build`).

External dependencies: `components/casting/` (the engine; `CLAUDE.md` is the contract, `README.md` the how-to, `prompts/*-vN-owner.md` the master, anchor, detail-board and standing-rule prompts), `brands/<brand>/` (the cast records and the pictures — read; only the finished pictures are ever written there), `components/image-production/` (the owned-footage search and the judge it borrows), `components/elements/` (the `style` and `format` lists, asked never copied), `components/marketing-chain-checks/` (the gates), `components/keys/loader.py` (the key loader, used only by the paid steps).

## Who plays this role (free, always)

```
python3 components/casting/cast.py who --brand <brand> --role "<the role, in words>"
python3 components/casting/cast.py who --brand <brand> --role "<role>" --json
python3 components/casting/cast.py avatar --brand <brand>                 # lists the core avatars the cast serves
python3 components/casting/cast.py avatar --brand <brand> --name <avatar> # who do we have for this avatar
python3 components/casting/cast.py find --brand <brand> --like "<words that describe the role>" [--collection <collection>] [--top N]
```

- `who`, `avatar` and `find` generate nothing, judge nothing, write nothing and spend nothing.
- `who` prints the bank it read, the person it found and why, what that person can front today, and what is still missing. When nobody covers the role it prints the gap, the nearest people, the open items on record, and what to do next.
- `find` searches the owned footage by what is in each clip, not by file name, and returns baseline candidates.
- `--brand` and `--role` are both required and never defaulted.

## Every new master: de-slop, then video element

A master from `build` is not castable in video until the `cast-deslop` skill has run both steps on it: real skin and hair texture references, then the three-model video element the owner picks. Never put a raw master into a scene.

## When the answer is a gap: plan the build, free first

```
python3 components/casting/cast.py build --brand <brand> --role "<role>" --id <id> --kind authority|roster --noun <noun> --who "<who>" --wardrobe "<wardrobe>" --world "<room, framing, light>" [--detail "<continuity board>"] [--baseline <frame on this machine>] --dry-run
python3 components/casting/cast.py --dry-run          # prints the nine steps and the request contract, nothing else
```

- Always `--dry-run` first. It starts no model, writes no file, touches nothing on Drive; it prints the prompts exactly as they would be sent, the baseline it would pick and why, whether the door and the key are on this machine, and what the gates would say. Exit 1 means something required is missing or a gate would hold.
- `id`, `kind`, `who`, `wardrobe`, `world` and `noun` are required and come from a person. Never choose them for the person. Also accepted: `--like`, `--collection`, `--style`, `--format`, `--out`, `--label`, `--name`, `--lane`, `--fronts`, `--problem`, `--reads`, `--hair`, `--setting`, `--register`, `--note`, `--check`, `--rule`, `--gates hold|warn`, `--no-mirror`.
- **Dropping `--dry-run` spends money** (the master, anchor and detail steps are paid picture generations) and writes pictures into the brand. Stop and get an explicit yes from the person, in chat, first. This skill's job is the lookup and the plan.
- This cannot be done from one command: finding a person is one command, but closing a gap is a person's decisions (id, kind, who, wardrobe, world, noun, baseline) followed by a dry run, a yes, and then a person registering the proposed row by hand.

## What it reads

- The brand's cast records, read only. The registry is looked up in `brands/<brand>/core-avatars/casting/` then `brands/<brand>/ai-cast/casting/`, and for a brand whose records sit in the character folder, `brands/<brand>/ai-elements/characters/casting/` (`authority.json`, `roster.json`). A brand with neither is answered from its `ai-cast/<id>/character.md` bibles. Finding two registries for one brand is reported as a problem.
- `brands/<brand>/casting/cards-v6.json` where it exists (each character's `casting-sheet: yes|no`).
- The owned footage, through image-production's asset reader (for `find` and the baseline).
- Keys by name only, through `components/keys/loader.py` (`~/.upright-keys.env`); never printed, never asked for in chat.

## The rules it enforces — do not work around any of them

1. **A role the bank covers never gets a new face.** `who` answers with the banked person, and `build` is held at the inputs gate when the bank already covers the role, naming who and where the record is. If the banked person seems wrong, that is a conversation about the bank, not a second face.
2. **Identity comes from an image, never a paragraph.** A build with no baseline frame is refused. The baseline carries the world (room, framing, light, wardrobe category), never the person: the output is a DIFFERENT person.
3. **Only current characters are cast.** A character without a casting sheet is not current and is not used in new work; a card saying `not current` is the answer "nobody current plays this role yet — build the sheet".
4. **It never coins a name.** The id, the character's name and the role are the caller's. A name not given is a field left out, never a guess.
5. **It never registers anyone.** Words (the proposed row, the bible) go into the run folder for a person to move. `brands/` registries are read-only to it.
6. **Refused, never guessed.** An unknown style/format id, an undeclared `kind`, a missing `noun` stops the work and names what to do instead.
7. **A judge-failed sheet is held**, never filed into the brand's cast folder; the reason is written to `held/`. Fix the prompt, never patch the picture.
8. **Nothing is ever deleted on the Drive mount**; a rebuild gets a new id.
9. **Remote baselines are refused**: the baseline must be a file on this machine.

## What comes back, and where it lands

- `who`, `avatar`, `find`: printed in the session only; nothing is filed.
- `build --dry-run`: printed only; nothing is filed.
- A real `build` (only after an explicit yes):
  - `runs/casting/<brand>/<label>/` holds `<step>--prompt-as-sent.txt`, `elements.json`, `check.json`, `run.json` (ends `state: filed` or `held`), `held/<step>-why.md`, `register/proposed-row.json`, `register/REGISTER.md`, `bible/character.md`.
  - `brands/<brand>/ai-cast/<id>/` holds `master-sheet.png` and `boards/` (the pictures, never committed to git).
  - Mirrored to `Shared Assets/brands/<brand>/ai-cast/<id>/` on the Drive (skipped with a printed reason if the mount is not found; `--no-mirror` skips it on purpose).
- Tell the person plainly: the character exists once built but is not castable from the bank until a person registers the proposed row from `register/REGISTER.md`.

Report: the banked person and why, or "nobody current plays this" with the missing items and the next step; for a plan, the dry-run's baseline pick and any gate that would hold.

Reply with the result and the folder it landed in (repo path or Drive folder name).
