# brandpath — one door into a brand's folders


Every tool that reads `brands/<brand>/…` goes through this module, so the
brand folders can be renamed to the v6 plan without a
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

## Tests

    python3 -m unittest discover components/brandpath/tests
