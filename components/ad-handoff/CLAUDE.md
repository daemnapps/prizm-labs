# ad-handoff — one ad drop, verified, handed to a person

**ad-handoff** — takes **a finished ad drop** (pictures, copy, names) and
**either hands over one link or refuses and says what is missing**. Does not
**make pictures, write copy, or name anything**. Triggered by
`python3 components/ad-handoff/handoff.py --brand <brand> --drop <drop> --for <email>`.

**Owner:** the owner. **Group:** delivery.

## Why it exists

the owner, 2026-09-24, after a handoff reached the person without the pictures:
*"stop these types of issues from happening. Make sure these things are
clean, consolidated, and systemized so that when I just do ad handoffs,
everything is ready to go. There should be no question. You're wasting my
time."*

A drop passes through four machines before it reaches anyone — `image-edit`
makes the pictures, `copywriter` writes the copy, `naming` names them,
Drive carries them. Each one is fine on its own and nobody owned the seam.
Every defect that has cost him time lived in that seam, and none of them
were visible from inside the folder.

**This is the gate on the seam.** It builds nothing. It refuses.

## The seven checks, and the day each one bit

| # | Check | What went wrong |
|---|---|---|
| 1 | the handoff document carries its own Drive link | the page said "everything is in this one folder" and never said which folder; it travelled on its own and the pictures were unreachable (2026-09-24) |
| 2 | every picture is on **Drive** with bytes, counted through the API | Drive for Desktop went offline mid-copy and the server got filenames with no bytes (2026-09-07). The local mount lies; the API does not |
| 3 | every ad folder holds at least one picture | a brief whose rolls all failed shipped an empty folder |
| 4 | every ad has copy, and no copy row names an ad that is not there | the pictures and the copy were built against two different labels and nobody noticed until the counts were compared |
| 5 | every ad name parses to the naming convention | a name that does not parse cannot join Meta spend back to the creative, which is the whole point of the name |
| 6 | every funnel link answers 200 | two of three destinations sat on a branch that was never deployed; the ads would have run to a 404 (2026-09-24) |
| 7 | the person it is for can open the folder | the one thing that cannot be checked from inside the folder |

**A failing check refuses the handoff and names what is missing. No link is
printed.** A link to an incomplete handoff costs more time than no link.

## The four questions

- **Engine + owner:** `handoff.py`, the owner.
- **Definitions + curator:** the seven checks, in this file and in the
  module docstring. A new check is a new row here with the failure that
  earned it — never a precaution somebody imagined.
- **The plane it emits:** one verdict record per hand-off,
  `runs/ad-handoff/<brand>/<drop>/run.json` (`tool`, `brand`, `drop`,
  `state` ready|refused, `check_only`, `at` UTC, `drop_dir`, `link` or null)
  + `check.json` (`held`, `problems`), rewritten on every READY or REFUSED —
  the runs filer (PLANE-19 (runs filer)) files it from there (SI-103 (handoff
  verdict record), 2026-10-08). It reads the drop at
  `runs/image-teardown/<brand>/<drop>/deliverable/` on both planes (legacy
  drops at `runs/image-edit/<brand>/<drop>/deliverable/`; SI-48 (teardown
  drops home), 2026-10-08), and writes
  into the drop at most one thing: the folder's own address into its
  `HANDOFF.md`. A record that cannot be written is one line on stderr; the
  verdict, its exit code and its printed link do not change.
- **Manifest per entry:** none — the drop's own `copy.csv`, `drop.csv` and
  per-ad `manifest.json` are the record. This adds no fourth list.

**Public names** (the developer, 2026-10-07, triage action 6 (declare public surfaces), provisionally on the owner's behalf — he sees it in the decision log and may strike any line). Besides the command and its exit code, a caller that loads `handoff.py` may use only these, all pure reads of a drop folder:
1. `ad_folders(d)` → the drop's ad folders, sorted, hidden ones skipped.
2. `copy_rows(d)` → the rows of `copy.csv` as dicts (`[]` if absent).
3. `links(d)` → `{name: url}` — the funnel links the ads point at, from `links.json`, else from the table in the drop's `HANDOFF.md`, else `{}`.
4. `resolves(url, timeout=20)` → `(HTTP status, reason)`; `0` when unreachable.
5. `take_back.py`, loaded by path: `take_back(role, brand, name, staging, ledger)` → the returned/ index (and writes returned/index.json, the manifest's `returned` block and one `returned` ledger row); `Refused` (`.reasons`) (SI-143 (take-back home), 2026-10-08).
Everything else, the seven checks included, is internal and may change without notice. Callers: email-production klaviyo_upload.py, meta-upload upload.py, video-edit handoff_run.py, and the lab hand-off tool.

## What a drop must hold

```
runs/image-teardown/<brand>/<drop>/deliverable/   (legacy: runs/image-edit/…)
    HANDOFF.md            the page for the person — carries this folder's own link
    copy.csv              one row per ad: ad_name, primary_text, lane, …
    drop.csv              one row per picture
    links.json            optional — {"Offer page": "https://…"}; else read off HANDOFF.md
    <ad name>/            one folder per ad, the folder name IS the ad name
        <ad name>-a01.png
        manifest.json
```

## Rules that bite here

- **Verify against Drive, never the mount.** A file that exists locally may
  be a filename with no bytes on the server.
- **Brand-agnostic** (workspace rule 7): the brand arrives as `--brand`, and
  the Shared Assets path is the only thing assumed.
- **It refuses; it does not fix.** A missing picture is the picture machine's
  problem, a dead link is the funnel's. This says which, and stops.
- Tests: `python3 components/ad-handoff/tests/test_ad_handoff.py` — offline,
  no network, no Drive.
