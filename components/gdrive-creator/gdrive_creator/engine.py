#!/usr/bin/env python3
"""Direct Drive API — put a document on the team Drive and hand back its link.

Until 2026-08-26 the video chain stopped one step short: it laid the document
out and handed back a file, and a session had to create the Doc by hand. Miss
that step and a run ends with nothing anyone can open, which is exactly what
happened that day. This closes it — a chain makes its own Doc, every run.

ONE HOME (GC-1 (gdrive creator), 2026-09-02). This engine used to live inside
`tools/video-teardown/machine/drive.py` — component internals nothing
else may depend on (components rule 2) — and the copy lab reached in through a
`sys.path.insert` into that machine's folder, which would have broken on any
vt-internal refactor. Both callers are now thin, so the pipe has one home:
`tools/video-teardown/machine/drive.py` is a same-command shim over this
file, and `tools/copywriter/machine/gdoc_out.py` imports this component directly.

LAYOUT IS NOT PIPE (the ruled design line). What a document LOOKS like is
per-machine and stays there — the video machine's `gdoc.py` did not move and
will not. What moved is the plumbing: auth, find, update-in-place, upload,
folder make-if-missing, sharing, and reading a folder's Drive id off the
mount.

DOCS-ONLY, deliberately (batch 23, on record). Exactly two constants make this
a Docs pipe — `DOC_MIME` in `find` and the same mime in `upload_doc`; the
other ~90% is target-agnostic. A Sheets path mints on the first real sheet
deliverable, not before. NARROWED TWICE SINCE, both times on a real
deliverable rather than a guess: `upload_file` (2026-09-09) carries arbitrary
bytes, and `mirror_tree` / `get_media` (2026-09-17) carry whole folders and
read them back. The two Doc constants have not moved, and `upload_doc` is
never reimplemented on top of `upload_file` — HTML-to-Doc conversion is a
different act from a byte upload, and collapsing them would lose it.

Auth is the service account in `GDRIVE_SA_KEY`, read from the ENVIRONMENT at
call time (components rule 8), never at import time. The value may be the JSON
itself, base64 of it, or a path to a file holding it; all three are accepted
so nobody has to remember which was used. A host with a credential vault of
its own hands it in as a FALLBACK — `configure(key_lookup=...)` — and the
environment still wins.

Shared drives need supportsAllDrives on every call — without it the API
pretends the parent folder does not exist and the error says nothing useful.
Every query here is PARENT-SCOPED (`'<id>' in parents`), which those two flags
are enough for; a drive-wide search by name is the case that also needs
`corpora="drive"` and `driveId` together, and this module never makes one.

Reads no credential and imports no network module at import time: the Google
client libraries are imported inside the functions that need them, which is
also what lets a caller drive this whole module with a fake `svc`.

IT READS AS WELL AS WRITES, since 2026-09-17 (WM-73). A machine's inputs
resolve through the API by fileId — `get_media` — and never through the Drive
for Desktop mount. The mount was proved unreliable for machines on 2026-09-16
by a live A/B: the same assets stayed unreadable through four client-side
interventions (never-materialized items, `links=65535`, `size=2097120`, each
with a working control), while ONE API read by the same service account
returned the file whole and intact. `folder_id` is the only thing left here
that touches the mount, and the mount stays for PEOPLE.

A MISSING PACKAGE IS A FAILURE, NEVER A SKIP. Those same lazy imports are what
made an absent `google-api-python-client` on `/usr/bin/python3` look like a
skipped Doc stage rather than a broken one. Every one of them now goes through
`_google`, which exits NAMING the package and the interpreter that lacks it.
"""
import base64, importlib, io, json, mimetypes, os, sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive"]
DOC_MIME = "application/vnd.google-apps.document"
DRIVE_XATTR = "com.google.drivefs.item-id#S"
FOLDER_MIME = "application/vnd.google-apps.folder"
OCTET = "application/octet-stream"

# The pip package behind each import, so a failure names the thing to install
# rather than the thing that failed. `google-auth` arrives as a dependency of
# `google-api-python-client`; both are in this component's requirements.txt.
GOOGLE_PACKAGE = "google-api-python-client"
PACKAGES = {"googleapiclient": GOOGLE_PACKAGE, "google": "google-auth"}
REQUIREMENTS = "components/gdrive-creator/requirements.txt"

# Media types the stdlib's table has been unreliable about across our two rails
# — 3.9 on `/usr/bin/python3` and 3.14 — because `mimetypes` on a Mac leans on
# `/etc/apache2/mime.types`, which a server may not have at all. A BACKSTOP,
# never an override: `mimetypes.guess_type` wins whenever it answers, so a host
# that knows better is never second-guessed.
EXTRA_TYPES = {".md": "text/markdown", ".markdown": "text/markdown",
               ".json": "application/json", ".jsonl": "application/x-ndjson",
               ".webp": "image/webp", ".webm": "video/webm",
               ".heic": "image/heic", ".avif": "image/avif",
               ".yaml": "application/yaml", ".yml": "application/yaml"}

# The host seams. Private on purpose: a machine installs its own habits here,
# and no caller reaches through this module to get at them.
_KEY_LOOKUP = None
_MOUNT_LOOKUP = None


def configure(key_lookup=None, mount_lookup=None):
    """Install a host machine's credential vault and/or Drive mount.

    Both are FALLBACKS, never overrides: the environment wins on the key, and
    an explicit `parent_id` wins on the mount. A host that sets neither loses
    nothing — it just needs `GDRIVE_SA_KEY` in the environment and passes its
    own folder ids in.

    key_lookup(name)   consulted when `GDRIVE_SA_KEY` is not in the
                       environment. The video machine passes `keys.get`, which
                       reads through components/keys/loader.py
    mount_lookup()     returns the filesystem path, on the Drive mount, under
                       which `creator_share` hangs its `creators/` tree.
                       The video machine passes `chain.runs_mirror()`
    """
    global _KEY_LOOKUP, _MOUNT_LOOKUP
    if key_lookup is not None:
        _KEY_LOOKUP = key_lookup
    if mount_lookup is not None:
        _MOUNT_LOOKUP = mount_lookup


def sa_key(name="GDRIVE_SA_KEY"):
    """Env first (components rule 8); the host's vault only after."""
    v = os.environ.get(name)
    if v:
        return v
    if _KEY_LOOKUP is not None:
        return _KEY_LOOKUP(name)
    raise SystemExit(
        "No %s yet — put the service-account key in the environment (the "
        "JSON, base64 of it, or a path to it), or give this engine your "
        "machine's vault with configure(key_lookup=...)." % name)


def _google(dotted):
    """A Google client module, or a failure that NAMES the missing package.

    THE POINT IS THAT IT IS NOT SILENT (found 2026-09-16 by the drive-pipe
    stream). `/usr/bin/python3` — the interpreter BOTH worker plists invoke —
    had no `google-api-python-client` at all. Because these imports are lazy,
    the ImportError surfaced three frames down inside a stage wrapped in a
    broad `except`, so an affected run reported a SKIPPED Doc stage and nobody
    could tell a missing package from a missing permission. Every previously
    skipped Doc stage on the mini may have been this.

    SystemExit rather than ImportError on purpose: it is not an `Exception`,
    so a caller's broad `except Exception` cannot swallow it back into a skip
    — the same reason `sa_key` exits.
    """
    try:
        return importlib.import_module(dotted)
    except ImportError as e:
        top = dotted.split(".")[0]
        raise SystemExit(
            "gdrive-creator could not import %s (%s). THE PACKAGE IS MISSING "
            "— install %s for THIS interpreter, %s. It is not a permission "
            "problem and it is not a stage to skip:\n"
            "    %s -m pip install --user -r %s"
            % (dotted, e, PACKAGES.get(top, GOOGLE_PACKAGE), sys.executable,
               sys.executable, REQUIREMENTS))


def _creds():
    service_account = _google("google.oauth2.service_account")
    raw = sa_key()

    info = None
    # a path to the json
    p = Path(raw).expanduser()
    if len(raw) < 500 and p.is_file():
        info = json.loads(p.read_text())
    if info is None:
        try:
            info = json.loads(raw)
        except json.JSONDecodeError:
            try:
                info = json.loads(base64.b64decode(raw))
            except Exception:
                raise SystemExit(
                    "GDRIVE_SA_KEY is not a service-account key I can read — "
                    "it should be the JSON, base64 of the JSON, or a path to it.")
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def service():
    # The package check comes FIRST, before the credential: a machine missing
    # both should hear about the one a `pip install` fixes, not be sent looking
    # for a key it already has.
    build = _google("googleapiclient.discovery").build
    return build("drive", "v3", credentials=_creds(), cache_discovery=False)


def esc(s):
    """Drive query strings are single-quoted, so an apostrophe in a name closes
    the string and the API rejects the whole query. A brief titled
    "Everything I don't do anymore" never got a Doc (2026-08-29), and
    apostrophes are ordinary in a title written from someone's speech."""
    return (s or "").replace("\\", "\\\\").replace("'", "\\'")


def find(svc, name, parent):
    """An existing Doc of this name in this folder, so a re-run updates rather
    than littering the folder with copies."""
    q = (f"name = '{esc(name)}'  and '{parent}' in parents and trashed = false "
         f"and mimeType = '{DOC_MIME}'")
    r = svc.files().list(q=q, fields="files(id,webViewLink)", pageSize=1,
                         supportsAllDrives=True,
                         includeItemsFromAllDrives=True).execute()
    f = r.get("files") or []
    return f[0] if f else None


def _folder_by_name(svc, name, parent_id):
    """The by-name search — one query, and it can LIE. See `_folder_listed`."""
    q = (f"name = '{esc(name)}' and '{parent_id}' in parents and trashed = false "
         f"and mimeType = '{FOLDER_MIME}'")
    r = svc.files().list(q=q, fields="files(id)", pageSize=1,
                         supportsAllDrives=True,
                         includeItemsFromAllDrives=True).execute()
    got = r.get("files") or []
    return got[0]["id"] if got else None


def _folder_listed(svc, name, parent_id):
    """The same folder found by LISTING the parent and matching the name here
    — the second look, and the one that stops a duplicate.

    NOT A WORRY, AN OBSERVATION (2026-09-17). For several seconds after
    `Team Drive/runs/` was created, a by-name search returned EMPTY while a
    parent listing already showed it: Drive's search index lags its own
    writes. A create-if-missing that trusts ONE search mints a second `runs/`,
    and two roots is not a problem anyone notices until the run's files are
    split across both of them."""
    q = (f"'{parent_id}' in parents and trashed = false "
         f"and mimeType = '{FOLDER_MIME}'")
    token = None
    while True:
        kw = dict(q=q, fields="nextPageToken, files(id,name)", pageSize=100,
                  supportsAllDrives=True, includeItemsFromAllDrives=True)
        if token:
            kw["pageToken"] = token
        r = svc.files().list(**kw).execute()
        for f in r.get("files") or []:
            if f.get("name") == name:
                return f["id"]
        token = r.get("nextPageToken")
        if not token:
            return None


def folder(name, parent_id, svc=None):
    """A Drive folder by name under a parent, made if it is not there.

    The Docs live in one folder per creator so the owner can hand that folder to
    his content manager and she can pass it straight to the creator — the
    working files stay behind in the run folders where they belong
    (2026-08-28).

    TWO LOOKS BEFORE A CREATE, never one (2026-09-17, WM-73): the name search,
    then a parent-scoped listing, and only then a create. Resolve by id where
    an id is known and you skip this entirely — which is why `mirror_tree`
    takes its root as an id and never makes it."""
    svc = svc or service()
    got = _folder_by_name(svc, name, parent_id)
    if got:
        return got
    got = _folder_listed(svc, name, parent_id)
    if got:
        return got
    f = svc.files().create(
        body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
        fields="id", supportsAllDrives=True).execute()
    return f["id"]


def share(file_id, role="reader", svc=None):
    """Anyone with the link. `reader` for briefs, `writer` for deliverables so
    a creator can drop her finished videos in without an account or an invite
    (the owner, 2026-08-28).

    BEST EFFORT, ALWAYS. The Workspace refuses anyone/writer, and letting that
    403 escape took down the whole document stage: CRE-02 and CRC-01 finished
    with no Doc at all on 2026-08-29 because a permission could not be set on
    a folder. A brief that exists but is not shared is a small problem; a
    brief that was never created is the whole job."""
    svc = svc or service()
    try:
        return _share(file_id, role, svc)
    except Exception:
        return False


def _share(file_id, role, svc):
    have = svc.permissions().list(fileId=file_id, supportsAllDrives=True,
                                  fields="permissions(id,type,role)").execute()
    for p in have.get("permissions", []):
        if p["type"] == "anyone":
            if p["role"] == role:
                return False
            svc.permissions().update(fileId=file_id, permissionId=p["id"],
                                     body={"role": role},
                                     supportsAllDrives=True).execute()
            return True
    svc.permissions().create(fileId=file_id,
                             body={"type": "anyone", "role": role},
                             supportsAllDrives=True).execute()
    return True


def creator_share(handle, svc=None, parent_id=None, brand=""):
    """The one folder a chain sends: BRIEFS to read, DELIVERABLES to write.

    Creators sit under their brand — creators/<brand>/<handle>/ — since
    2026-09-18 (the owner: "why do you have a <brand> creator in that folder?").
    A caller that names no brand gets the old flat shape, so nothing that
    never passed one changes.

    `parent_id` is the Drive folder the `creators/` tree hangs under. Given, it
    wins; omitted, the host's mount seam answers (`configure(mount_lookup=...)`
    — the video machine's runs mirror). Neither → None, which is what a caller
    with no Drive of its own gets, and what this returned before the move when
    the mount could not be read."""
    svc = svc or service()
    if not handle:
        return None
    # Make the folder through the API rather than waiting for a folder to
    # appear on the mount. Runs moved under work/ on 2026-08-28, so nothing
    # creates creators/<handle>/ as a side effect any more — and without it
    # this returned None and the Docs quietly went into the working folder
    # instead of BRIEFS (2026-08-29).
    runs_root = parent_id or (folder_id(_MOUNT_LOOKUP())
                              if _MOUNT_LOOKUP is not None else "")
    if not runs_root:
        return None
    creators = folder("creators", runs_root, svc)
    if brand:
        creators = folder(brand, creators, svc)
    root = folder(handle, creators, svc)
    briefs = folder("BRIEFS", root, svc)
    drops = folder("DELIVERABLES", root, svc)
    share(root, "reader", svc)      # each of these is best-effort — see share()
    share(briefs, "reader", svc)
    share(drops, "writer", svc)
    return {"folder": root, "briefs": briefs, "deliverables": drops,
            "link": f"https://drive.google.com/drive/folders/{root}"}


def upload_doc(html_path, name, parent_id, svc=None):
    """HTML in, a real Google Doc out. Returns its link.

    Same name in the same folder = the same Doc, updated in place — so the
    link the reader already has keeps working after a re-run instead of going
    stale beside a second copy."""
    MediaIoBaseUpload = _google("googleapiclient.http").MediaIoBaseUpload

    svc = svc or service()
    data = Path(html_path).read_bytes()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype="text/html",
                              resumable=False)

    existing = find(svc, name, parent_id)
    if existing:
        f = svc.files().update(fileId=existing["id"], media_body=media,
                               fields="id,webViewLink",
                               supportsAllDrives=True).execute()
        return f["webViewLink"], False
    f = svc.files().create(
        body={"name": name, "mimeType": DOC_MIME, "parents": [parent_id]},
        media_body=media, fields="id,webViewLink",
        supportsAllDrives=True).execute()
    return f["webViewLink"], True


def update_doc(file_id, html_path, name=None, svc=None):
    """HTML in, the Doc with THIS id rewritten. Returns (webViewLink, trashed).

    The by-id twin of `upload_doc`'s by-name update, for a caller that already
    holds the link it handed out: a re-run that renamed its title would
    otherwise find nothing by the new name and make a second Doc beside the
    first. `name` given = the title is rewritten too.

    TRASHED IS RETURNED, NOT DECIDED. A Doc a person trashed comes back from
    `update` with `trashed` set; whether to leave it there and say so is the
    caller's call (the video machine does, 2026-09-05)."""
    MediaIoBaseUpload = _google("googleapiclient.http").MediaIoBaseUpload

    svc = svc or service()
    media = MediaIoBaseUpload(io.BytesIO(Path(html_path).read_bytes()),
                              mimetype="text/html", resumable=False)
    kw = dict(fileId=file_id, media_body=media,
              fields="id,webViewLink,trashed", supportsAllDrives=True)
    if name is not None:
        kw["body"] = {"name": name}
    f = svc.files().update(**kw).execute()
    return f["webViewLink"], bool(f.get("trashed"))


def shared_drive_id(name, svc=None):
    """The id of the shared drive called exactly `name`, or None.

    A shared drive is not a folder — no parent to scope a query to — so this
    lists the drives this account can reach and matches the name here, whole
    and case-sensitive. None when absent: what to say about a missing drive
    is the caller's, because only the caller knows what it was trying to do."""
    svc = svc or service()
    token = None
    while True:
        kw = dict(fields="nextPageToken, drives(id,name)", pageSize=100)
        if token:
            kw["pageToken"] = token
        r = svc.drives().list(**kw).execute()
        for d in r.get("drives") or []:
            if d.get("name") == name:
                return d["id"]
        token = r.get("nextPageToken")
        if not token:
            return None


def find_file(svc, name, parent, mime=None):
    """An existing file of this name in this folder, any mime unless given —
    the non-Doc twin of `find`, so an upload of the same name updates rather
    than littering the folder with copies."""
    q = (f"name = '{esc(name)}' and '{parent}' in parents and trashed = false")
    if mime:
        q += f" and mimeType = '{mime}'"
    r = svc.files().list(q=q, fields="files(id,size,webViewLink)", pageSize=1,
                         supportsAllDrives=True,
                         includeItemsFromAllDrives=True).execute()
    f = r.get("files") or []
    return f[0] if f else None


def upload_file(path, name, parent_id, mime="application/octet-stream",
                svc=None):
    """Bytes in, a Drive file out, uploaded straight through the API. Returns
    (file_id, created?).

    The first non-Doc deliverable, minted 2026-09-09 (GC-1's condition:
    "on the FIRST real deliverable"). The trigger was the mount: on 09-07
    Drive for Desktop went offline mid-upload and left zero-byte placeholders
    on the server while reporting done locally. Ads delivered through the
    mount were invisible to the person they were for. This path never touches
    the mount — the bytes go to the server and the server's answer is the only
    answer.

    Same name in the same folder = the same file, updated in place, so a link
    already handed out keeps working after a re-run. Resumable upload because
    ad renders run 3–8 MB and a shared-drive PUT can stall.

    IT DETECTS THE MEDIA TYPE (the developer, 2026-09-17, verbatim "detect media type").
    Precedence: the caller's `mime` when it passes one, then
    `mimetypes.guess_type`, then `EXTRA_TYPES`, and `OCTET` only as the last
    fallback. WHY IT IS NOT TIDINESS: `mirror_tree` uploads whole folders, so
    an octet-stream default would land every image, PDF and video on Drive as
    an unpreviewable binary blob — and the deliverable a person opens is the
    entire point of a mirror. The signature is unchanged, so passing `mime`
    explicitly still wins."""
    MediaFileUpload = _google("googleapiclient.http").MediaFileUpload

    if not mime or mime == OCTET:
        mime = (mimetypes.guess_type(str(path))[0]
                or EXTRA_TYPES.get(Path(path).suffix.lower(), OCTET))
    svc = svc or service()
    media = MediaFileUpload(str(path), mimetype=mime, resumable=True)
    existing = find_file(svc, name, parent_id)
    if existing:
        f = svc.files().update(fileId=existing["id"], media_body=media,
                               fields="id", supportsAllDrives=True).execute()
        return f["id"], False
    f = svc.files().create(
        body={"name": name, "parents": [parent_id]},
        media_body=media, fields="id", supportsAllDrives=True).execute()
    return f["id"], True


def mirror_tree(local_dir, parent_id, svc=None):
    """A local folder recreated on Drive under `parent_id`, file for file.
    Returns `{relative posix path: Drive file id}` — one entry per FILE.

    That map is the deliverable as much as the upload is: a run's record can
    then list every mirrored file WITH its id, which is what workspace rule 3
    asks for — ids and names on the records plane, never the bytes.

    `parent_id` IS NEVER CREATED HERE. It is resolved by the caller and passed
    in, which is how `Team Drive/runs/` (created 2026-09-17, an id that is
    already known) is FOUND rather than minted a second time, and why no
    folder id and no brand name appears anywhere in this file. The phase-1
    destination shape is `Team Drive/runs/<machine>/<brand>/<run-label>/`,
    mirroring `runs/<machine>/<brand>/<run-label>/` by name, and a caller
    reaches it by naming its own segments:

        runs = <the id of Team Drive/runs, from the caller's config>
        dest = folder(run_label,
                      folder(brand, folder(machine, runs, svc), svc), svc)
        ids = mirror_tree(local_run_dir, dest, svc)

    Sub-folders are made through `folder()`, so the index-lag race is handled
    there, once, for every caller. Files go through `upload_file`, so a mirror
    inherits its resumable upload, its update-in-place and its media-type
    detection rather than growing a second uploader beside it."""
    svc = svc or service()
    root = Path(local_dir)
    if not root.is_dir():
        raise SystemExit("mirror_tree: %s is not a directory — nothing to "
                         "mirror, and an empty run is worth saying out loud."
                         % root)
    made = {".": parent_id}     # relative posix path -> the Drive folder's id
    ids = {}
    # sorted() over rglob puts a folder before everything inside it, so every
    # parent id is already known by the time its children are reached.
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        under = made[rel.parent.as_posix()]
        if p.is_dir():
            made[rel.as_posix()] = folder(p.name, under, svc)
        elif p.is_file():
            ids[rel.as_posix()], _ = upload_file(p, p.name, under, svc=svc)
    return ids


def get_media(file_id, dest_path, svc=None):
    """A Drive file's BYTES, by its id, written to a local path. Returns the
    path it wrote.

    THE MACHINE'S READ PATH, and what it does NOT do is the point: it resolves
    BY fileId and never touches the Drive mount. `folder_id` reads the mount
    and using it here would reintroduce the exact dependency the 2026-09-17
    ruling removes — machine inputs through the API, the mount kept for
    people. `supportsAllDrives=True` or a shared-drive id 404s."""
    MediaIoBaseDownload = _google("googleapiclient.http").MediaIoBaseDownload

    svc = svc or service()
    dest = Path(dest_path)
    if str(dest.parent) not in ("", "."):
        dest.parent.mkdir(parents=True, exist_ok=True)
    req = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
    with open(str(dest), "wb") as fh:
        dl = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
    return str(dest)


def folder_id(path):
    """The Drive id of a folder on the mount, straight off the filesystem —
    the same trick gdoc.py uses for the frames. No search, no guessing.

    THE ONE THING HERE THAT NEEDS THE MOUNT, and since 2026-09-17 nothing on a
    machine's READ path may call it: `get_media` resolves by fileId precisely
    so a run stops depending on Drive for Desktop having materialized a file.
    This stays for the human-side callers that already hold a mount path."""
    import subprocess
    r = subprocess.run(["xattr", "-p", DRIVE_XATTR, str(path)],
                       capture_output=True, text=True)
    v = r.stdout.strip()
    return v if r.returncode == 0 and len(v) > 10 else ""


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Make the brief a Google Doc.")
    ap.add_argument("html")
    ap.add_argument("--name", required=True)
    ap.add_argument("--parent", required=True, help="Drive folder id")
    a = ap.parse_args()
    url, made = upload_doc(a.html, a.name, a.parent)
    print(f"  {'created' if made else 'updated'}: {url}")


if __name__ == "__main__":
    main()
