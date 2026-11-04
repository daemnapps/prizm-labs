# components/gdrive-creator — the Drive pipe, as a component

**Name RULED by the team 2026-09-02** (via ◆ PLAN batch 23) — deliberately
format-agnostic after the docs-vs-sheets answer. **Engine owner: the team** (since 2026-10-23;
the team, relayed verbatim by ◆ PLAN [19616d], received 2026-10-23T04:03:10Z: "move owner of gdrive creator to the team"; was the owner, build folder's declaration, `new-workflow-design/builds/drive-pipe/`).
the owner's callers keep working: the video-teardown shim, copywriter gdoc_out and every other importer.
Extracted under GC-1 (gdrive creator) from `tools/video-teardown/machine/drive.py`, the
third run of the IDT-1 (identity extraction) / LL-1 (language layer) / BH-1 (brand home locator) extraction pattern.

## Definition

**gdrive-creator** — takes a local file, folder or rendered HTML plus a Drive parent folder id (or a mount path to read an id off), with the service-account key found by name through `configure()` / `GDRIVE_SA_KEY`; makes the Drive objects asked for — a folder if missing, a Google Doc, an uploaded or updated file, a mirrored tree, a link share — and returns their ids, or a file read back by id to a local path. Does not lay out documents (that is each caller's own, e.g. the video machine's `gdoc.py`), choose where anything goes, delete on Drive, or keep a plane of its own (the CALLER delivers and records). Triggered by importing `gdrive_creator.engine` (`folder`, `upload_doc`, `upload_file`, `mirror_tree`, `get_media`, `find_file`, `folder_by_path`, `list_files`, `share`, `folder_id`), or `gdrive_creator.reach` — the one Drive reach every reader and mirror uses (`route`, `get`, `put`, `put_ids`, `drive_json`, `kind`, `fetch_folder`, `readable`, `subfolders` (QB-9 (the team statics)); LD-14 (shared Drive reach), LD-64 (records Drive ids)) — or by `python3 components/gdrive-creator/make_doc.py <html> --name <name> --parent <folder id>`.

What it is: the plumbing between a machine and the team Drive — authenticate,
find, update in place, upload a Doc or any file, **mirror a whole folder**,
**read a file back by its id**, make a folder if it is missing, share by link,
and read a folder's Drive id off the mount. What it is not: a layout, a chain,
or anybody's document.

**LAYOUT IS NOT PIPE — the ruled design line.** `gdoc.py` is the video
machine's own layout and stays there. Only the pipe moved.

**Why it exists as one home.** It lived inside
`tools/video-teardown/machine/` — component internals nothing else may
depend on (components rule 2) — and `lab/damon/copy/machine/gdoc_out.py` (now
`tools/copywriter/machine/gdoc_out.py`, moved 2026-09-19) reached in through a `sys.path.insert` into that machine's folder, plus an
`import chain as C` behind it. Any refactor inside the video machine broke the
copy lab silently, and the copy-machine rebuild was about to live exactly
there. Fragility was the driver, not tidiness.

**The one for its side — not the only Drive client** (D1-A, decision log
2026-10-07 TRIAGE PAGE 8, the team). Component code reaches Drive through this
engine. The mini worker's own stdlib client
(`platform/workers/mini-worker/teardown_adapter.py`, used by `review_folder.py`)
stays for worker-internal reads. Merging the two is clean-up-phase work. For
this phase, O9 (Drive by fileId) reads: a job nobody is watching reaches Drive
through this engine by file id; a person's own run may use their mount, found
through the one shared helper `components/brandpath/drive_index.py` mount().
That helper's `local()` and `product_pictures()` read the file on the mount
when it is there; otherwise they fetch it by the row's `drive_id` through this
engine's `get_media` into a cache folder (a temp dir by default)
(SI-41 (Drive picture reach)).

**Both machines keep working, and that was the hard constraint of the move.**
`tools/video-teardown/machine/drive.py` is now a thin shim over this
engine: same command, same flags, same public names, same key vault, same
Drive mount. Nothing was asked of the owner and nothing changed on his side. On
the copy-lab side `gdoc_out.py` imports this component directly and takes its
destination folder from `--folder`; that file is the ONE lab touch GC-1 (gdrive creator) was
permitted, pre-flagged on I-82 (the owner copy package).

## New-resident checklist (components/CLAUDE.md, ruled 2026-09-01)

| question | answer |
|---|---|
| **engine + owner** | this folder's `gdrive_creator/` — **the team** (since 2026-10-23; was the owner) |
| **definitions + curator** | **none.** This is the inverse of `models/`: that component is definitions with no engine, this is an **engine with no definitions**. There is no curated content to execute — a folder id, a name and an HTML file all arrive from the caller at call time |
| **the plane it emits** | **none — the CALLER delivers.** A call returns a link (and whether it created or updated); nothing here writes a record, and `--out` would be meaningless. What lands on the plane is the calling chain's business |
| **what the manifest declares per entry** | **n/a** — no manifest, because there are no entries |

Runs by: both — a library; the mini runs it inside its callers (teardown-chain, lab-run) and people run it inside theirs (gdrive-creator#12).

## Contract (components/CLAUDE.md rule 2)

Three surfaces are dependable and they are the only three: **the Python API**,
**`configure()`**, and **the `svc` seam**. Nothing outside this folder may
depend on anything else here.

### 1. The API

```python
from gdrive_creator import engine
engine.service()                                   # -> an authenticated Drive v3 client
engine.upload_doc(html_path, name, parent_id, svc=None)   # -> (webViewLink, created?)
engine.upload_file(path, name, parent_id, mime="application/octet-stream", svc=None)
                                                   # -> (file_id, created?). DETECTS the type
engine.mirror_tree(local_dir, parent_id, svc=None) # -> {relative posix path: file id}, one per FILE
engine.get_media(file_id, dest_path, svc=None)     # -> the path written. BY ID, never the mount
engine.media_request(file_id)                      # -> (url, auth header) for a RANGED read (ffmpeg -headers … -ss … -i url): only the bytes it needs
engine.find(svc, name, parent)                     # -> {id, webViewLink} or None
engine.find_file(svc, name, parent, mime=None)     # -> {id, size, webViewLink} or None
engine.folder_by_path(label, svc=None)             # -> the id a "Shared Assets/a/b/c" label names, or None. READ-ONLY (LD-11 (stills by Drive API))
engine.list_files(folder_id, svc=None)             # -> [{id, name, mimeType}], non-folder, non-trashed, every page
engine.folder(name, parent_id, svc=None)           # -> folder id, made if missing (TWO looks)
engine.share(file_id, role="reader", svc=None)     # -> bool. BEST EFFORT, ALWAYS
engine.creator_share(handle, svc=None, parent_id=None, brand='')    # -> {folder, briefs, deliverables, link}; under creators/<brand>/<handle>/ when brand is given (gdrive-creator#9)
engine.folder_id(path)                             # -> the mount's Drive id, or "". NOT on a read path
engine.esc(s)                                      # -> a name safe inside a Drive query
engine.sa_key(name="GDRIVE_SA_KEY")                # -> the raw key, env first
engine.main()                                      # the CLI, also `make_doc.py`

engine.OCTET          # "application/octet-stream" — the LAST fallback, never the default answer
engine.EXTRA_TYPES    # the media types the stdlib misses on a bare rail. A backstop, not an override
engine.GOOGLE_PACKAGE # "google-api-python-client" — the name a missing-package failure says out loud
```

**`reach` — one Drive reach for every caller** (LD-14 (shared Drive reach),
2026-10-18). Extracted from the two copies that carried it — tools/image-production/image_production/drive_reach.py
and tools/email-production/drive_reach.py, now thin shims over it, every
public name kept (O1 (third copy extracts), the LL-1 (language layer) precedent).
Why: Full Disk Access is not applied to the mini's launchd jobs, so a mini
reader cannot list the mount; `readable()` is its one-call fallback to the API.

```python
from gdrive_creator import reach
reach.route()                                  # -> "api" (GDRIVE_SA_KEY present, even with a mount) | "mount" | NoDrive
                                               #    present = engine.has_key(): the environment, a configured key_lookup, else the
                                               #    one key loader (a person's this repo's .env counts; LD-47 (Drive sweep) step 1.6, 2026-10-20).
                                               #    Tests that mean "no key" set KEYS_NO_FALLBACK=1 as well as clearing the variable
reach.get(parts, name, dest_dir, svc=None)     # -> Shared Assets/<parts>/<name> as a local file (the mount file itself, or read by id), or None
reach.put(files, parts, svc=None)              # -> (how, placed, note). Folders made if missing, same name = updated in place; "none" + a SKIP note with no route
reach.fetch_folder(parts, dest_dir, recursive=False, max_bytes=reach.MAX_BYTES, svc=None)
                                               # -> dest_dir holding that Drive folder's files, by id (API only), or None. Subfolders made,
                                               #    filled only if recursive; stops once max_bytes is reached (2 GiB default) and says so on stderr
reach.readable(path, svc=None, recursive=False, max_bytes=reach.MAX_BYTES)
                                               # -> a path that reads: with GDRIVE_SA_KEY set (route() "api") ALWAYS an API copy, the mount
                                               #    never read (LD-47 (Drive sweep) step 1.5, 2026-10-20); with no key a mount path or
                                               #    "Shared Assets/…" label is itself when it lists/opens,
                                               #    else an API copy in this process's cache (reach.cache_root(), under tempfile.gettempdir());
                                               #    a path not under Shared Assets comes back unchanged
reach.mount()                                  # -> components/brandpath drive_index.mount(), or None
reach.folder_id(parts, svc, make=False, root=None)   # -> the id of Shared Assets/<parts>; make=True makes missing steps
reach.shared_assets_id(svc)                    # -> the Shared Assets drive id, or None
reach.subfolders(folder_id, svc=None)         # -> [{id, name}] child folders, name order, one listing, READ-ONLY (QB-9 (the team statics))
reach.NoDrive, reach.KEY_ENV, reach.NO_DRIVE, reach.SHARED_DRIVE, reach.MAX_BYTES
```

**`shared` — a Shared Assets folder as a local folder, API first** (the owner, 20 Oct 2026: the Drive "is connected
directly via API, which our tools need to default to"). With `GDRIVE_SA_KEY` a folder is a local copy under
`cache_home()` (`DRIVE_CACHE`, else `<tmp>/upright-drive`), kept in step through Drive's change feed (a full listing
once, then only what changed); a changed file goes back with `save()` / `save_tree()` (reach.put: same name =
updated in place). Without the key, or with `DRIVE_ROUTE=mount`, it is the Drive folder itself. Nothing on the Drive
is deleted, moved or renamed; a file the Drive no longer has leaves THE LOCAL COPY only.

```python
from gdrive_creator import shared as SH
SH.route()                       # "api" | "mount"
SH.folder(rel, want=None, ttl=60)   # -> local Path of Shared Assets/<rel> (want(rel, size) picks which files come down)
SH.ensure(rel)                   # -> one folder kept in step, or one file fetched; for big pools
SH.save(path) / SH.save_tree(dir)   # -> a changed local file (or folder) back to the Drive
SH.cache_home(), SH.is_copy(path)
```
Callers today: the card store (`meta-upload/shared_drive.py` → cards, to_check, learnings; the Meta approve page
pins `CARDS_ROUTE=mount`), Outlier's hand-offs and image drafts, video-edit `handoff_run` + `kit_from_run` banks,
video-teardown `chain.drive_root` / `mirror_to_drive`, the swipe pools (`swipe-paid/swipe_home.py`), the
acquisition board's cards. Test: `python3 components/gdrive-creator/tests/test_shared.py`.

Every call also takes `find_mount=` / `find_engine=` (zero-argument finders): a
shim passes its own, which is how each keeps its own behaviour. **Nothing in
`reach` deletes, moves or renames on Drive, mount or API** — `test_reach.py`
asserts it on the calls and on the source. Test:
`python3 components/gdrive-creator/tests/test_reach.py` (offline, fake `svc`).

**`move` — a tracked move, the one place a parent changes** (LD-89 (tracked Drive moves),
2026-10-23; the team ~04:25Z: "since the move is by machine anwayys, it should be fully tracked").
`from gdrive_creator.move import move, MoveRefused`; `move(file_id, to_parts, by, why, svc=None,
find_engine=None, record_root=None)` → `{drive_id, name, from, to, record}`: one `files().update`
(addParents/removeParents, `supportsAllDrives=True`), the Drive id kept, nothing copied; target
folders made under Shared Assets. `MoveRefused` (nothing changed) for a file the key cannot see, a
file with more than one parent, a file not on Shared Assets, a target that is not folder names under
it, or the file already there. **Every move writes ONE record** —
`platform/data/records/drive-move/<UTC stamp>--<by>--<drive_id>.json`, kind
`platform/data/kinds/drive-move.json` — the one plane this component writes; read it to answer
"where did my X go". Moving needs a key with Content manager (`fileOrganizer`) on Shared Assets;
below it the update fails and no record is written. **No delete, trash or rename stays a wall**, and
`reach` and both `drive_reach.py` shims still never move — `test_reach.py` asserts both on the
source. Test: `python3 components/gdrive-creator/tests/test_move.py` (offline, fake `svc`).

**`mirror_tree` never creates its own root.** `parent_id` is resolved by the
caller and passed in — that is how `Shared Assets/runs/` (id already known,
created 2026-09-17) is FOUND rather than minted twice, and why no folder id
and no brand name appears in the engine. The phase-1 destination shape is
`Shared Assets/runs/<machine>/<brand>/<run-label>/`, mirroring
`runs/<machine>/<brand>/<run-label>/` by name (the team, 2026-09-17); a caller
names its own segments:

```python
runs = ...                      # the id of Shared Assets/runs, from the caller's config
dest = engine.folder(run_label,
                     engine.folder(brand,
                                   engine.folder(machine, runs, svc), svc), svc)
ids = engine.mirror_tree(local_run_dir, dest, svc)   # {"brief.md": "1ab…", "shots/01.png": "1cd…"}
```

The returned map is the deliverable as much as the upload is: a run's record
lists every mirrored file WITH its id, which is workspace rule 3 kept — **ids
and names on the records plane, never the bytes**.

`svc` given = that client is used and nothing authenticates. `svc=None` = one
is built from the credential. **That parameter is the fake seam**: every call
path in this module can be driven end to end with a stand-in object, which is
how the declared test exercises the whole pipe with no network.

### 2. `configure()` — the host seams

```python
configure(key_lookup=None, mount_lookup=None)
```

Both are **fallbacks, never overrides**: the environment wins on the key, an
explicit `parent_id` wins on the mount. A host with neither loses nothing — it
needs `GDRIVE_SA_KEY` in the environment and passes its own folder ids in,
which is exactly what the copywriter now does.

| seam | consulted when | video-teardown's shim passes |
|---|---|---|
| `key_lookup(name)` | `GDRIVE_SA_KEY` is not in the environment | `keys.get` — the host's key lookup (the one key loader) |
| `mount_lookup()` | `creator_share` was given no `parent_id` | `chain.runs_mirror()` — his Drive mount |

The seams exist so this engine imports **nothing** from
`tools/video-teardown/` (rule 2 both ways): `keys.py` and `chain.py` are
that machine's internals and stay there.

### 3. The CLI

```
python3 components/gdrive-creator/make_doc.py <html> --name "<title>" --parent <folder-id>
```

Same three arguments the pre-move file's `main()` always had; the shim's
`main` **is this function object**, not a copy.

## Rules

- **DOCS-ONLY, and it is two constants** (batch 23, on record): `DOC_MIME` in
  `find` and the same mime in `upload_doc`. The other ~90% of this file is
  target-agnostic. **A Sheets path mints on the first real sheet deliverable**,
  not before — do not generalise it speculatively. **NARROWED 2026-09-09 and
  again 2026-09-17, both on a real deliverable rather than a guess:** the two
  Doc constants still stand exactly where they were, but the pipe is no longer
  Docs-only — `upload_file` carries arbitrary bytes (GC-1 (gdrive creator)'s "on the FIRST real
  deliverable" condition, met by the ad renders) and `mirror_tree` /
  `get_media` carry whole folders and read them back. **`upload_doc` is never
  reimplemented on top of `upload_file`** — HTML-to-Doc conversion is a
  different act from a byte upload, and collapsing them would lose it.
- **A MISSING PACKAGE IS A FAILURE, NEVER A SKIP** (2026-09-17, WM-73
  (drive mirror)). Every Google-client import goes through `_google`, which
  raises `SystemExit` NAMING the package and the interpreter that lacks it.
  `SystemExit` is deliberate: it is not an `Exception`, so a caller's broad
  `except Exception` cannot swallow it back into a skipped stage — the same
  reasoning `sa_key` already used. The dependency is declared in
  `requirements.txt` beside this file and rowed in
  `platform/workers/README.md` under `mini-worker`.
- **Machine reads resolve BY fileId, never through the mount** (the team ruling,
  2026-09-17). `get_media` takes an id; `folder_id` is the only thing here
  that touches Drive for Desktop and is for human-side callers that already
  hold a mount path. Evidence, not preference: a live A/B on 2026-09-16 left
  the same assets unreadable through four client-side interventions
  (never-materialized items, `links=65535`, `size=2097120`, each with a
  working control) while ONE API read by this service account returned the
  file whole and intact.
- **Every query is parent-scoped**, which `supportsAllDrives` +
  `includeItemsFromAllDrives` is enough for. A drive-wide search by name is
  the case that also needs `corpora="drive"` and `driveId` **together** — this
  module never makes one, and a future caller that does needs all three.
- **Credentials from the environment** (rule 8): `GDRIVE_SA_KEY`, read at CALL
  time, never at import time. Three forms are accepted — the JSON, base64 of
  it, or a path to a file holding it — so nobody has to remember which was
  used. Importing this module reads no credential and imports no network
  module; the declared test asserts it in a fresh interpreter rather than
  promising it.
- **Machine-agnostic** (rule 8): no machine's paths, no machine's vault, no
  assumption that a Drive is mounted at all. `folder_id()` reads an extended
  attribute if one is there and returns `""` if it is not — which is a fact
  about the filesystem, not a dependency on a host.
- **Brand-agnostic** (workspace rule 7): no brand, product, creator or
  category name appears here or in a default. A handle is a lookup key that
  arrives at run time.
- **The Google client libraries are imported inside the functions that use
  them.** That is what makes an import free, a fake `svc` sufficient, and a
  `--help` runnable on a machine that has never installed them.
- **Stdlib only at module level** — `base64`, `importlib`, `io`, `json`,
  `mimetypes`, `os`, `pathlib`, `sys`. (`importlib` and `mimetypes` joined
  2026-09-17: the lazy imports go through `importlib.import_module` so a
  missing package can be named, and media-type detection needs `mimetypes`.
  Both are stdlib, neither can open a connection, and the declared test
  asserts the whole list rather than a rule of thumb.)

## The six scars this code exists to hold (never refactor them away)

1. **`supportsAllDrives=True` on every call.** Without it a shared drive's API
   pretends the parent folder does not exist, and the error says nothing
   useful.
2. **`esc()` on every name in a query** (2026-08-29). Drive queries are
   single-quoted, so an apostrophe closes the string and the API rejects the
   whole query — a brief titled *"Everything I don't do anymore"* never got a
   Doc. Apostrophes are ordinary in a title written from someone's speech.
3. **`share()` is best-effort, always** (2026-08-29). The Workspace refuses
   `anyone/writer`; letting that 403 escape took down the whole document
   stage, and JEN-02 and PAM-01 finished with no Doc at all. A brief that
   exists but is not shared is a small problem; a brief that was never created
   is the whole job.
4. **`creator_share()` makes its folders through the API, not off the mount**
   (2026-08-29). Runs moved under `work/` on 2026-08-28, so nothing creates
   `creators/<handle>/` as a side effect any more; the mount-only version
   returned `None` and the Docs went quietly into the working folder instead
   of BRIEFS.

5. **`folder()` takes TWO looks before it creates** (2026-09-17, observed
   live, not a worry). For several seconds after `Shared Assets/runs/` was
   created, a by-name search returned EMPTY while a parent listing already
   showed it — **Drive's search index lags its own writes**. A create-if-missing
   that trusts one search mints a duplicate, and two `runs/` roots is not a
   problem anyone notices until a run's files are split across both. So: name
   search, then a parent-scoped listing, and only then a create. Resolving by
   a known id skips the question entirely, which is why `mirror_tree` takes
   its root as an id.
6. **The bytes never come through the mount** (2026-09-07 and 2026-09-16, two
   separate failures pointing the same way). Drive for Desktop went offline
   mid-upload and left ZERO-BYTE placeholders on the server while reporting
   success locally — that is why `upload_file` exists at all; and
   never-materialized items made assets unreadable to a machine through four
   client-side interventions — that is why `get_media` exists. Both go
   straight to the server, and the server's answer is the only answer.

Two more the code carries without a scar of their own: **update-in-place**
(same name + same folder = the same Doc, so a link already handed out keeps
working after a re-run) and the **2026-08-26 origin** — before this pipe, a
session had to create the Doc by hand, and a run whose session forgot ended
with nothing anyone could open.

## Provenance

Evidence base: artifact **3748baf6** ("The Drive Plumbing") — caller map,
scars, before/after. **URL recorded as provenance only, never hotlinked**
(b76787dc precedent). Its two diagrams and four scars are ruled INTO the
atlas node's pane-2 detail; the atlas node itself lands with the component
and is the lead's to place (`components/atlas/` was outside GC-1 (gdrive creator)'s write
scope). The scar list above is this folder's copy of that content.

## The declared test

`python3 new-workflow-design/builds/drive-pipe/test_gdrive_creator.py`
— no pytest, no network, no dependencies, green on **both rails** (3.9
`/usr/bin/python3` and 3.14), so no 3.10+ syntax anywhere in this component.

It proves the move rather than describing it: the shim exposes **every public
name the pre-move file exposed** (pinned list, cross-checked against
`git show HEAD` when git is available) and its `upload_doc`, `folder`,
`share`, `main` … **are the engine's own objects**, not copies; a full pipe
transcript — find, upload create, upload update, folder make-if-missing,
share in all three permission states, `creator_share`, `esc` — is
**byte-identical** driven through the shim and through the component entry
point against a fake `svc`, with **no `GDRIVE_SA_KEY` and an empty `HOME`**;
importing either module in a fresh interpreter reads no credential and pulls
in no network module; the copywriter's `gdoc_out.py` no longer names the video
machine's folder and requires `--folder`; and a sentinel fingerprint over
`lab/` and `tools/video-teardown/` (minus the two files this card owns)
is byte-unchanged across the whole run.

**WM-73 (drive mirror) added a fifth section, and its five claims each get
their own assertion** — offline, against an injected service, no network and
no credential: `mirror_tree` recreates a two-level fixture and returns one id
per file, with the nested files under the nested folder's id; `get_media`
writes exactly the bytes the injected service returned and passes
`supportsAllDrives=True`; **a name search that answers EMPTY once and then
non-empty produces ONE folder and not two** (scar 5, driven by a fake whose
index lags on demand); a `.png`, a `.md` and a `.json` each send the right
media type while an explicit `mime` from the caller still wins; and a missing
`google-api-python-client` is reported BY NAME from all four entry points
instead of being skipped.

## Kill-condition (ruled, carried from the card)

**the owner calls gdoc delivery a dying habit** — delivery moving to the records
plane — and this component folds back into its callers: pin the import with a
one-line fragility comment and let it die with the habit. Callers: at 6edbff9c96 (gdrive-creator#8) eight components import it
(video-teardown through its shim, copywriter `gdoc_out.py`, image-teardown deliver/pack,
ad-handoff, image-production static finish/drive_reconcile, ad-variations, brandpath
`drive_index`, email-production) plus `lab/damon/clipping`; count with
`git grep -l -E "gdrive_creator|gdrive-creator" -- 'components/*.py' 'lab/damon/*.py'`, not this line
(N12 (docs point, not restate)). Byte uploads and mirrors run through it too, so the
gdoc-only trigger is the owner's to re-confirm. **Fewer than 2 callers and it folds**, the same floor LL-1 (language layer) set.
