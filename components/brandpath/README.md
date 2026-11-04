# brandpath — one door into a brand's folders

## How to use it → https://dashboard.the company.com/atlas#c-components-brandpath

Every tool that reads `brands/<brand>/…` goes through this module, so the
brand folders can be renamed to the v6 plan (Brand Folder Map) without a
single tool breaking. Nothing here creates, moves or deletes anything.

## Use

```python
import sys; sys.path.insert(0, str(WS / "components/brandpath"))
from brandpath import brand_path, brand_file, brand_paths

brand_path(brand, "ai-elements/characters", "casting")    # today: brands/<brand>/ai-cast/casting
brand_path(brand, "ai-elements", "index.json")            # today: brands/<brand>/elements/index.json
brand_file(brand, "brand-identity", "identity-anchors.md") # today: brands/<brand>/identity-anchors.md
brand_path(brand, "strategy", "moments.json")              # today: brands/<brand>/calendar/moments.json
brand_paths("intake", "ads")                               # every brand's existing-content/ads that exists
brand_path(brand, "intake", "ads", root=drive_root / "brands")   # same map on the Drive mirror
```

`brand_path(brand, key, *rest, root=None)` — the first EXISTING path among
the new name, then each of today's places, in the order the map gives. When
none exists it returns the path a tool would have built today (under the
first of those places whose folder is on disk), else the new-name path — so
writers file where they file today, and move with the folder.

`root` is a different folder-of-brands (the Drive mirror). The map is still
read from the repo's brand folder.

## The map

`brands/<brand>/FOLDERS.json`: new name → list of today's places, first
existing wins. A key may name a sub-folder of the plan
(`ai-elements/characters`) when today's folder maps one level down. Missing file → the defaults in `brandpath.DEFAULTS`, which are
the v6 plan verbatim. A place may be a file (`identity-anchors.md`): it
answers only when that exact file is asked for.

| new name | old places |
|---|---|
| brand-identity | identity/, identity-anchors.md, story.md, story.html, position.md, compliance.json |
| brand-identity/voice | voice/ |
| ai-elements | elements/, element-facts.json |
| ai-elements/characters | ai-cast/, elements/character/ |
| ai-elements/environments · props | elements/environment/, set/ · elements/prop/ |
| intake · intake/research | existing-content/ · research/ |
| strategy | calendar/, strategy/ |
| content-creators · content-creators/clipping | creators/, channels/creators/ · channels/clipping/ |
| email-sms | email/ |
| ads/hooks · ads/copy | hook-ledger.md · copy/ |
| web/funnels | funnels/ |
| customer-experience | customer-service-documentation/, customer/ |
| operations · operations/data-notes | operations/, operations.md, commerce/ · data-notes/ |
| meta/persona-pages | persona-pages/ |
| context | context/, data-sources.md, tracker.json, market.md |
| archive/retired-2026-09-30 (+ /dropbox-migration) | assets.json, product-details.md (+ dropbox-migration/) |
| competitors | competitive/, qc-dictionary.json |
| core-avatars · products · offers · variables · briefs · archive · meta | unchanged |
| brand-assets · learnings · ads · web | new, nothing maps yet |

## Switch-over

1. **Alias (done, wave A).** Tools call `brand_path`; old folders answer.
2. **Move (done, wave C).** `git mv` to the new names; the old places stay in
   `FOLDERS.json` as aliases, so a today-style path (`calendar/moments.json`,
   `channels/creators/contact.md`) still resolves through `resolve_rel`. One
   file was renamed in the move because its name clashed in the target
   folder: `calendar/README.md` -> `strategy/calendar-README.md`. `calendar/`
   went flat into `strategy/` (the alias layer's shape), not into
   `strategy/calendar/`. `qc-dictionary.json` did not move (its reader is in
   `components/qc-checks`, not this component's to edit).
2b. **Move, part two (done 2026-09-30).** The rest of both brand folders to
   v6: `email/` → `email-sms/`, `funnels/` → `web/funnels/`, the hook ledger
   → `ads/hooks/`, story · position · compliance · `voice/` → `brand-identity/`,
   element facts → `ai-elements/`, `customer/` + customer-service docs →
   `customer-experience/`, and the rest — one line each in
   `lab/owner/brand-folder-map/REPO-MOVE-2026-09-30.md`. Every old place is an
   alias in `FOLDERS.json` (and `DEFAULTS`). Held in place because a reader
   outside this component names them literally: `qc-dictionary.json`,
   `channels/own-accounts.json`, `brand-identity/identity-anchors.md`.
3. **Retire.** Old places are dropped from `FOLDERS.json` once a rescan shows
   zero readers of the old names.

## Tests

    python3 -m unittest discover components/brandpath/tests

## The alias proof

    python3 components/brandpath/check_alias.py            # differences only
    python3 components/brandpath/check_alias.py --verbose  # every reader path

For every reader that goes through brandpath, the path it used to build
(today's literal folder names) beside the brandpath answer, on every real
brand folder. Exit 1 on any difference. Run it after touching the map or a
reader.

    python3 components/brandpath/check_alias.py --before origin/wave-a/code

With `--before REF` (the move-time proof, wave C): the old paths and their
content are read from the git tree at REF, and a row passes only when the
brandpath answer holds the same bytes today. A second section walks every
file each brand had at REF through `resolve_rel` and checks it is found, with
the same content, at its new place. Since the move, this is the form to run.
