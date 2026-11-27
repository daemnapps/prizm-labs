# brandpath — one door into a brand's folders

**brandpath** — takes a brand and a folder's NEW name (the v6 folder plan) and
says where that content sits on disk today, so the brand folders can be renamed
without a tool breaking. Also finds a product picture on the Shared Assets Drive
by its Drive id (`drive_index.py`). Never creates, moves or deletes anything —
it only says where. Triggered by importing it (`import brandpath`,
`from brandpath import brand_path`).

**Owner:** the owner (engine), matching his authorship — named provisionally in B1
(owner names), then REGISTERED as a library to keep: the developer 2026-10-08, B4a
(decide-now cards) card 1, A-register-brandpath. The map's data lives in each
brand's own `brands/<brand>/FOLDERS.json` (a person's commit); the defaults are
`DEFAULTS` in `brandpath.py`.

**Runs by:** none — a library; it runs inside its callers.

**Records (O12 (records adapter)):** none: no runs by design.

**LIBRARY (public surface, registered 2026-10-08 — read from what callers
import at HEAD, `git grep -n "import brandpath\|from brandpath\|import drive_index"`):**
`brandpath.py` — `brand_path`, `brand_file`, `brand_paths`, `resolve_rel`,
`rel`, `brands_dir`, `brand_root`, `repo`; `drive_index.py` — `mount`, `local`,
`rows`, `accounts`. Everything else, and every name starting with `_`, is
internal. `folders` is read by one lab script (the owner's `prizm-labs`), not a
component — it stays callable but is not promised.

`check_alias.py` is a PROOF TOOL, not part of the library: it deliberately
imports its readers' own path modules (image-production, casting,
image-teardown, video-production) and reads video-teardown's
`chain_config.json`, to compare their old paths with brandpath's answers. A
failed import is reported, never fatal. It is run by hand after the map
changes; nothing may import it.

**How it behaves:** the module docstrings are the spec —
`brandpath.py` (lookup order, the FOLDERS.json map, the defaults) and
`drive_index.py` (repo copy first, then the mount, then the Drive id through
gdrive-creator `engine.get_media`, O9 (Drive by fileId)). The README shows
calls; `check_alias.py --help` compares old paths with brandpath's answers on
the real brand folders.

**The four questions:** engine + owner — `brandpath.py`, `drive_index.py`,
the owner · definitions — `brands/<brand>/FOLDERS.json`, else `DEFAULTS` · plane —
none · manifest — `FOLDERS.json`'s shape, as `brandpath.folders()` reads it.

Tests: `python3 tests/test_brandpath.py` · `python3 tests/test_drive_index_reach.py`.
