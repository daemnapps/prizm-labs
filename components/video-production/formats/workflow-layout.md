# What you can print (2026-11-27)

Page: https://claude.ai/artifact/Q9ZuJXKocp7vHybu5Xd6yX (source `workflow-layout.html` beside this file).

## Live lines (proven end to end)

| Line | Makes | Playbook |
|---|---|---|
| Micro drama | characters act and talk on screen in one story | `playbooks/micro-drama.json` |
| Song ad | a story told as a song, every line a shot | `playbooks/song-ad.json` |

Everything else is parked.

## Parked (kept, out of the owner's view)

Every other family carries `state: parked 2026-11-27: <what it is>; not proven end to end …. Was: <old state>`.
Status words and files are unchanged because team tools and tests still read them, and every parked format still
resolves (`workflow.py show <format>`). Parked: ad-series, fooh-stunt, freestyle-battle, multi-speaker-scene,
narrator-montage, remedy, short-movie, single-presenter, sports-interview, talking-object, vfx-stunt-hook,
vo-explainer. Formats with no family of their own run on the shared chain and count as parked too. ad-series and
narrator-montage were parked in their homes (`formats/<id>/format.json`) and written out by `formats/sync.py`.

- `playbook.parked(pb)`: a `state` starting with "parked".
- `workflow_catalog.line_of(fid)` / `inventory()`: each row carries `line` live|parked, live first.
- `workflow.py list`: the live lines, then one line `parked: N formats …`; `list --parked` shows every row.
- `components/WORKFLOWS.md`: the two live rows first in the named-workflow table, then one "Parked · video formats" row.
- Tests: `machine/test_parked_lines.py`.

## Retired earlier the same day (variant `status: deprecated`, never resolves)

micro-drama in short-movie, single-presenter and remedy in multi-speaker-scene (shadowed copies); meme in
sports-interview (gave meme runs press-conference settings); vo-montage in multi-speaker-scene (narrator-montage);
character-song in vfx-stunt-hook (song-ad). Guard and tests: `machine/test_retired_variants.py`.
