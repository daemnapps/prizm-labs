"""Put a picture a person made outside Claude (Higgsfield, a camera, a designer's file) into a designed email.

the team's own-picture step (the team's lab, 2026-10-21). email-production's `sync.py` can only remake or edit a picture
with AI; this places a file the team brings, in place of one picture of the email, and rebuilds the email.

    own_picture.py list  <run>                                   every picture of the email, with its code (P1, P2, …)
    own_picture.py place <run> <P-code> <file> --alt "<words>"   put the file in that picture's place, rebuild
    own_picture.py newest <run> [--role graphic-designer]       show the newest file in the email's returned/ folder (moves nothing)
    own_picture.py newest <run> <P-code> --alt "<words>" --made-with "<tool>"
                                                                 "use my newest", LD-90 (the team takes newest): that file is
                                                                 MOVED into the run's Drive media, then placed as above

<run>   an email label (oct-20, brand-b-oct-20) or a run folder path; --brand picks the brand (default:
        the one brand folder holding that label).
<P-code> P2, or "2", or an S address S6.1 (part 6 as the emails page shows it, its first picture; both count
        from 1, so S6.1 is section 5, picture 0 of design/email.json; "nov-02 · S6.1" works too). S6 alone
        is enough when part 6 holds one picture. P numbers count every picture of the email in order, top to
        bottom, the same order adapter/sync.py lists them; a P code wins over an S address.
<file>  a local file path, or a Google Drive link or file id (read with the person's own GDRIVE_SA_KEY).

What place does, in order: reads the picture (HEIC, PNG, WEBP, JPG: saved as JPEG); copies it to the run's
media/ folder (gitignored) and mirrors it to the Drive at Shared Assets/runs/email-production/<brand>/<label>/media/
(the place a `run:` picture is read back from on another machine); replaces the picture in design/email.json,
keeping the old one in the picture's `history`; rebuilds and checks the email with email-production's own
design/build.py and design/check.py; prints where the rebuilt email is.

What newest does (LD-90 (the team takes newest), the words the team says are the team's: "<id> P<n>: use my newest"): lists
the email's own handoff folder for the asker's role, Shared Assets/runs/handoffs/<role>/<brand>/<email label>/returned/
(role from tools/image-edit delivery.json `roles`; never a person's folder, the owner 2026-10-27), and its direct
subfolders by API, takes the newest picture by its Drive
modified time, MOVES it (LD-89 (tracked Drive moves)'s move(), which writes a drive-move record) to the run's
Shared Assets/runs/email-production/<brand>/<label>/media/, reads it back by id and places it as above. The picture
then holds both refs, `original` and `email_copy` ({drive_id, label}), and `made_with` (required: Higgsfield,
Photoshop, a real photo…); one model-outcome record is written (try_picture.py's kind, door "own"). After a take the
file is gone from the returned/ folder: that is how she sees it moved. Undo is the picture's `history`: every place appends,
and putting an earlier picture back is a place too, so nothing is rewritten.

A place from the command line (place_own) also writes one model-outcome record, and a picture read from a link (a
Higgsfield result) keeps `made_from` {link, id}, --source-id being the tool's own id for it (the team, 2026-10-23).

Nothing here talks to Klaviyo, deletes anything, or commits. The alt text is required and must describe the NEW
picture: an alt still holding a "to make" prompt is refused.
"""
import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(d for d in HERE.parents if (d / "components" / "run-kit").is_dir()) / "components" / "run-kit"))
from run_kit import paths  # noqa: E402

REPO = paths.repo(HERE)
EM = REPO / "tools" / "email-production"
RUNS = REPO / "runs" / "email-production"
BAD_ALT = re.compile(r"to make|after your ok|change:|^\s*$", re.I)
REAL_PHOTO = re.compile(r"^\s*(?:an?\s+)?(?:real\s+)?(?:photo|photograph|camera)\s*$", re.I)
MADE_WITH_Q = "what made it — Higgsfield, Photoshop, a real photo…?"


def find_run(arg, brand=None):
    p = Path(arg).expanduser()
    if (p / "design" / "email.json").is_file():
        return p.resolve()
    label = arg.strip()
    hits = []
    for b in ([brand] if brand else sorted(x.name for x in RUNS.iterdir() if x.is_dir())):
        for name in (label, "%s-%s" % (b, label)):
            if (RUNS / b / name / "design" / "email.json").is_file():
                hits.append(RUNS / b / name)
    if len(hits) != 1:
        raise SystemExit("no single email called %r (%s); give the brand with --brand or the run folder"
                         % (arg, ", ".join(str(h.relative_to(REPO)) for h in hits) or "none found"))
    return hits[0]


def slots(spec):
    """Every picture slot of the email, top to bottom: (P number, section index, index in section, the dict).
    Same test and walk order as adapter/sync.py pictures(), so P numbers match the page."""
    out = []
    for i, sec in enumerate(spec["sections"]):
        found = []

        def walk(x):
            if isinstance(x, dict):
                if "alt" in x and ("photo" in x or "proof" in x or "source" in x or "todo" in x):
                    found.append(x)
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(sec)
        for j, d in enumerate(found):
            out.append((len(out) + 1, i, j, d))
    return out


def pick(spec, code):
    """A picture by its P code (P2, 2, "oct-20 · P2") or its S address S<part>.<picture>, both counted from 1
    the way the emails page shows them (S2.1 = section 1, picture 0 of design/email.json). PF-11 (part codes S)."""
    c = code.strip().lower().replace(" ", "")
    m = re.fullmatch(r"p?(\d+)", c) or re.fullmatch(r"(?:.*·|[\w-]*)p(\d+)", c)
    every = slots(spec)
    if m:
        for n, i, j, d in every:
            if n == int(m.group(1)):
                return n, i, j, d
        raise SystemExit("no picture %r in this email; `own_picture.py list` shows them" % code)
    tok = re.split(r"[\s·]+", code.strip().lower())[-1]
    s = re.fullmatch(r"s(?:ection)?(\d+)(?:[.,/](?:picture)?(\d+))?", tok)
    if not s:
        raise SystemExit("no picture %r in this email; `own_picture.py list` shows them" % code)
    part, k = int(s.group(1)), (None if s.group(2) is None else int(s.group(2)))
    if part == 0 or k == 0:
        raise SystemExit("S codes count from 1, as the emails page shows them: the first part is S1, its first picture "
                         "S1.1. The old 0-based %s is retired; section %d, picture %d of design/email.json is S%d.%d"
                         % (tok, part, k or 0, part + 1, (k or 0) + 1))
    if part > len(spec["sections"]):
        raise SystemExit("no part S%d in this email (it has %d parts, S1 to S%d)"
                         % (part, len(spec["sections"]), len(spec["sections"])))
    here = [x for x in every if x[1] == part - 1]
    if not here:
        raise SystemExit("no picture in part S%d (%s); `own_picture.py list` shows the pictures"
                         % (part, sec_kind(spec, part - 1)))
    if k is None and len(here) == 1:
        return here[0]
    if k is not None and k <= len(here):
        return here[k - 1]
    raise SystemExit("part S%d holds %d picture%s: %s; say which one"
                     % (part, len(here), "" if len(here) == 1 else "s",
                        ", ".join("P%d (S%d.%d)" % (n, part, j + 1) for n, i, j, d in here)))


def drive_id(src):
    m = re.search(r"/d/([\w-]{20,})", src) or re.search(r"[?&]id=([\w-]{20,})", src)
    if m:
        return m.group(1)
    return src if re.fullmatch(r"[\w-]{25,}", src) and not Path(src).exists() else None


def _drive():
    sys.path.append(str(REPO / "components" / "gdrive-creator"))
    from gdrive_creator import engine, reach
    return engine, reach


MAX_LINK_BYTES = 60 * 1024 * 1024


def from_link(url, tmp, opener=None):
    """A picture's https link (a Higgsfield result, as its connector lists it, or any public file link) downloaded to
    tmp. Higgsfield (the team, 2026-10-22, the team's ask): the team's Claude reads her newest generation's link through the
    Higgsfield connector and places it with no download or drag. Refuses a non-https link, a page that is not a
    picture, and anything over 60 MB; never sends anything, only reads the one link."""
    import urllib.request
    if not url.lower().startswith("https://"):
        raise SystemExit("only an https link can be read: %s" % url[:120])
    req = urllib.request.Request(url, headers={"User-Agent": "upright-email-adapter/1"})
    try:
        r = (opener or urllib.request.urlopen)(req, timeout=60)
    except Exception as e:  # noqa: BLE001 — said, never hidden
        raise SystemExit("couldn't read the link (%s): %s. If it needs a login, download the picture and drag it in"
                         % (str(e)[:120], url[:120]))
    kind = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if kind and not kind.startswith("image/") and kind != "application/octet-stream":
        raise SystemExit("that link is a %s, not a picture: %s (a picture link usually ends in .png, .jpg or .webp)"
                         % (kind, url[:120]))
    data = r.read(MAX_LINK_BYTES + 1)
    if len(data) > MAX_LINK_BYTES:
        raise SystemExit("that picture is over 60 MB: %s" % url[:120])
    ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/heic": ".heic"}.get(kind) \
        or (Path(url.split("?", 1)[0]).suffix.lower() if Path(url.split("?", 1)[0]).suffix else ".img")
    out = Path(tmp) / ("link" + ext)
    out.write_bytes(data)
    return out


def fetch(src, tmp):
    """The file as a local path: a path on this machine, a Drive file read by id with the person's key, or a picture's
    https link (from_link)."""
    if src.lower().startswith("https://") and "drive.google.com" not in src.lower() \
            and "docs.google.com" not in src.lower():
        return from_link(src, tmp)
    fid = drive_id(src)
    if fid:
        engine, _ = _drive()
        return Path(engine.get_media(fid, str(Path(tmp) / ("drive-" + fid))))
    p = Path(src).expanduser()
    if not p.is_file():
        raise SystemExit("can't find the file %s" % src)
    return p


def as_jpeg(src, dest):
    """The picture saved as a JPEG at most 2400 px wide; HEIC goes through macOS's own sips first."""
    from PIL import Image
    try:
        im = Image.open(src)
        im.load()
    except Exception:  # noqa: BLE001 — PIL can't read HEIC; sips can
        conv = Path(tempfile.mkdtemp()) / "conv.jpg"
        r = subprocess.run(["sips", "-s", "format", "jpeg", str(src), "--out", str(conv)], capture_output=True)
        if r.returncode or not conv.is_file():
            raise SystemExit("%s isn't a picture I can read" % src)
        im = Image.open(conv)
    im = im.convert("RGB")
    if im.width > 2400:
        im = im.resize((2400, round(im.height * 2400 / im.width)), Image.LANCZOS)
    im.save(dest, quality=90, optimize=True, progressive=True)
    return im.size


def rebuild(run):
    """email-production's own build and check, run as their commands (the same pair sync.py's rebuild runs)."""
    out = []
    for step in ("design/build.py", "design/check.py"):
        p = subprocess.run([sys.executable, step, str(run)], cwd=EM, capture_output=True, text=True)
        out.append({"step": step, "ok": p.returncode == 0, "said": (p.stdout + p.stderr).strip()[-600:]})
        if p.returncode:
            break
    return out


def place(run, code, src, alt, by, made_with, ratio, focus, drive, *, original=None, made_from=None):
    """`original` (take_newest): the {drive_id, label} of the file the email copy was made from; stored with the email
    copy's own {drive_id, label} as `email_copy`. `made_from` (place_own): where a picture read from a link came from
    — {link, id?} — so it can be traced back to its generation in the tool that made it."""
    if BAD_ALT.search(alt or ""):
        raise SystemExit("the alt text must describe the new picture in plain words (not a 'to make' prompt)")
    f = run / "design" / "email.json"
    spec = json.loads(f.read_text())
    n, i, j, p = pick(spec, code)
    old = {k: v for k, v in p.items() if k != "history"}
    # design/check.py counts every "todo" key in the spec as an unfilled slot, history included
    was = {("was_todo" if k == "todo" else k): v for k, v in old.items()}
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = "own-p%d-%s.jpg" % (n, stamp)
    media = run / "media"
    media.mkdir(exist_ok=True)
    k = 2
    while (media / name).exists():                  # a second place in the same second never overwrites the first,
        name, k = "own-p%d-%s-%d.jpg" % (n, stamp, k), k + 1     # which its history still points at
    with tempfile.TemporaryDirectory() as tmp:
        w, h = as_jpeg(fetch(src, tmp), media / name)
    put = {"how": "skipped (--no-drive)", "files": []}
    if drive:
        _, reach = _drive()
        put = reach.put_ids([str(media / name)], ["runs", "email-production", spec["brand"], run.name, "media"])
        if not put.get("files"):
            raise SystemExit("the picture didn't reach the Drive (%s); nothing in the email changed. "
                             "The file is at %s" % (put.get("note"), media / name))
    keep_ratio = ratio == "slot" and "photo" in old and old.get("ratio")
    new = {"photo": "run:media/" + name, "ratio": old["ratio"] if keep_ratio else round(w / h, 4),
           "focus": focus or old.get("focus") or [0.5, 0.5], "alt": alt.strip(),
           "source": "made" if made_with and not REAL_PHOTO.search(made_with) else "photo",
           "by": by, "placed_at": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    if made_with:
        new["made_with"] = made_with
    if made_from:
        new["made_from"] = made_from
    if put.get("files") and put["files"][0].get("id"):
        new["drive_id"] = put["files"][0]["id"]
    if original:
        new["original"] = {"drive_id": original["drive_id"], "label": original["label"]}
        if new.get("drive_id"):
            new["email_copy"] = {"drive_id": new["drive_id"], "label": "%s/%s" % (put.get("folder") or "Shared Assets/"
                                 + "/".join(["runs", "email-production", spec["brand"], run.name, "media"]), name)}
    new["history"] = (p.get("history") or []) + [{"was": was, "replaced_by": by, "at": new["placed_at"]}]
    p.clear()
    p.update(new)
    f.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    sys.path.insert(0, str(HERE))
    import prepare
    steps = prepare.keep_card(run, lambda: rebuild(run))   # a rebuild drops the parts marked right; keep them
    if all(x["ok"] for x in steps):
        prepare.stamp(run)
    return {"picture": "P%d" % n, "section": i, "index": j, "file": str(media / name), "drive": put.get("placed") or put["how"],
            "drive_note": put.get("note"), "was": old.get("photo") or old.get("proof") or ("to make: " + old["todo"] if "todo" in old else old.get("stage")),
            "old_alt": old.get("alt"), "new_alt": new["alt"], "rebuilt": steps,
            "see": str(run / "klaviyo" / "email.html")}


# --------------------------------------------------------------- "use my newest", LD-90 (the team takes newest)

def _drive_lister(svc=None):
    """lister(parts) -> the children of Shared Assets/<parts> as [{id, name, modified, folder}], or None when the
    folder is not there: by API with the person's key (gdrive-creator's service and folder_by_path), every page,
    parent-scoped, supportsAllDrives. Reads only."""
    engine, reach = _drive()
    held = []

    def lister(parts):
        if not held:
            held.append(svc or engine.service())
        s = held[0]
        fid = engine.folder_by_path("/".join([reach.SHARED_DRIVE] + list(parts)), svc=s)
        if not fid:
            return None
        rows, token = [], None
        while True:
            kw = dict(q="'%s' in parents and trashed = false" % fid, pageSize=100,
                      fields="nextPageToken, files(id,name,mimeType,modifiedTime)",
                      supportsAllDrives=True, includeItemsFromAllDrives=True)
            if token:
                kw["pageToken"] = token
            r = s.files().list(**kw).execute()
            rows += [{"id": f.get("id"), "name": f.get("name"), "modified": f.get("modifiedTime"),
                      "folder": f.get("mimeType") == engine.FOLDER_MIME} for f in r.get("files") or []]
            token = r.get("nextPageToken")
            if not token:
                return rows
    return lister


def newest(brand_folder_parts, svc=None, lister=None):
    """The newest picture in Shared Assets/<brand_folder_parts>/ and its direct subfolders (one level: brief or
    project folders), by Drive modified time: {"id", "name", "modified", "folder": its "Shared Assets/…" label}, or
    None (no such folder, or no picture in it). Only pictures count (gdrive-creator's reach.kind): a note or a layered
    file beside them is never taken."""
    _, reach = _drive()
    ls = lister or _drive_lister(svc)
    parts = list(brand_folder_parts)
    top = ls(parts)
    if top is None:
        return None
    rows = [dict(r, where=parts) for r in top if not r.get("folder")]
    for sub in sorted((r for r in top if r.get("folder")), key=lambda r: r.get("name") or ""):
        rows += [dict(r, where=parts + [sub["name"]]) for r in ls(parts + [sub["name"]]) or [] if not r.get("folder")]
    rows = [r for r in rows if r.get("name") and not r["name"].startswith(".") and reach.kind(r["name"]) == "image"]
    if not rows:
        return None
    hit = max(rows, key=lambda r: (r.get("modified") or "", r["name"]))
    return {"id": hit["id"], "name": hit["name"], "modified": hit.get("modified"),
            "folder": "/".join([reach.SHARED_DRIVE] + hit["where"])}


def _fetch_id(svc=None):
    """fetcher(file_id, tmp) -> the file read back BY ID into tmp (gdrive-creator's get_media), never the mount."""
    def get(fid, tmp):
        engine, _ = _drive()
        return Path(engine.get_media(fid, str(Path(tmp) / ("drive-" + fid)), svc=svc))
    return get


def _outcome(person, run, p_code, made_with, purpose, brand, root=None):
    """One model-outcome record for an own picture, in try_picture.outcome's shape (LD-83 (picture try first)'s kind):
    item <run>-<P>-own-<UTC stamp>, door "own", never judged, picked. Returns its path."""
    sys.path.insert(0, str(HERE))
    import try_picture as TP
    who = str(person or "unknown").lower()
    now = dt.datetime.now(dt.timezone.utc)
    item = "%s-%s-own-%s" % (run.name, p_code, now.strftime("%Y%m%dT%H%M%SZ"))
    verdict = {"model": "real photo" if REAL_PHOTO.search(made_with) else made_with, "door": "own",
               "purpose": purpose, "brand": brand, "judge": "not judged", "picked": True, "tries_before_pick": None,
               "cost": "not on record"}
    out = Path(root or TP.OUTCOME_ROOT) / "platform" / "data" / "records" / TP.OUTCOME_KIND
    out.mkdir(parents=True, exist_ok=True)
    stem = "%s--%s--%s" % (now.strftime("%Y%m%dT%H%M%SZ"), who, item)
    f, k = out / (stem + ".json"), 2
    while f.exists():                                           # one record per event, never over an earlier one
        f, k = out / ("%s-%d.json" % (stem, k)), k + 1
    f.write_text(json.dumps({"schema": 1, "kind": TP.OUTCOME_KIND, "reviewer": who, "item": item, "verdict": verdict,
                             "created": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
                             "via": "email-production/own_picture"}, indent=1, ensure_ascii=False) + "\n")
    return f


def _purpose(run, before):
    """The purpose the picture's own record names (try_picture's picture_record, design/), for the outcome record."""
    sys.path.insert(0, str(HERE))
    import try_picture as TP
    try:
        return (TP.PR.read(run, before.get("record")) or {}).get("purpose")
    except (OSError, ValueError):
        return None


def is_link(src):
    """A picture's https link that is not a Google Drive link (a Higgsfield result)."""
    s = str(src).lower()
    return s.startswith("https://") and "drive.google.com" not in s and "docs.google.com" not in s


def place_own(run, code, src, alt, by, made_with, ratio, focus, drive, source_id=None, outcome_root=None):
    """`place` for a picture a person brings (a file, a Drive link, a Higgsfield link), with the two things the team
    Drive flow asks of every picture (the team, 2026-10-23: the system knows where each one came from): a picture read
    from a link keeps `made_from` {link, id} — the id is the tool's own (a Higgsfield generation id) — and one
    model-outcome record is written, the same as "use my newest". Returns place()'s dict + {"outcome": record path}."""
    run = Path(run)
    spec = json.loads((run / "design" / "email.json").read_text())
    n, _, _, before = pick(spec, code)
    purpose = _purpose(run, before)
    made_from = None
    if is_link(src):
        made_from = {"link": src}
        if source_id:
            made_from["id"] = str(source_id)
    res = place(run, code, src, alt, by, made_with, ratio, focus, drive, made_from=made_from)
    rec = _outcome(by, run, "P%d" % n, (made_with or "").strip() or "real photo", purpose, spec["brand"],
                   outcome_root)
    return dict(res, outcome=str(rec))


ROLE = "graphic-designer"     # who makes an email's own pictures, by role, never by name (the owner, 2026-10-27)
ROLES = REPO / "tools" / "image-edit" / "delivery.json"      # who fills each role: the one setting


def role_of(by):
    """The role the asker fills (delivery.json `roles`, `filled_by`), else the graphic designer."""
    try:
        roles = json.loads(ROLES.read_text()).get("roles") or {}
    except (OSError, ValueError):
        return ROLE
    who = str(by or "").strip().lower()
    return next((r for r, v in roles.items() if who in (r, str((v or {}).get("filled_by") or "").lower())), ROLE)


def returned_parts(brand, label, role=ROLE):
    """Where a person puts the pictures they made for one email: its handoff folder's returned/, the one shape every
    handoff has, the same words in the repo and on the Drive (the owner, 2026-10-27: "the name of the folders need to be the
    same for both repo and drive"; "standardization is the default")."""
    # under runs/ like every hand-off since 2026-10-28 ()
    return ["runs", "handoffs", role, brand, label, "returned"]


def take_newest(run, code, alt, by, made_with, role=None, svc=None, mover=None, lister=None, fetcher=None,
                drive=True, outcome_root=None):
    """"<id> P<n>: use my newest": the newest picture in the email's returned/ folder for the asker's role
    (handoffs/<role>/<brand>/<email label>/returned/) is MOVED (LD-89 (tracked Drive moves)) into
    the run's Drive media, read back by id and placed (place: the 2400 px JPEG, the old picture kept in history); the
    picture holds both refs and made_with; one model-outcome record. Every refusal comes before the move. Returns
    place()'s dict + {"moved": the move's result, "original": {drive_id, label}, "outcome": record path, "newest"}."""
    run = Path(run)
    made_with = (made_with or "").strip()
    if not made_with:
        raise SystemExit(MADE_WITH_Q)
    if BAD_ALT.search(alt or ""):
        raise SystemExit("the alt text must describe the new picture in plain words (not a 'to make' prompt)")
    spec = json.loads((run / "design" / "email.json").read_text())
    n, _, _, before = pick(spec, code)
    p_code = "P%d" % n
    purpose = _purpose(run, before)
    where = returned_parts(spec["brand"], run.name, role or role_of(by))
    hit = newest(where, svc=svc, lister=lister)
    if hit is None:
        raise SystemExit("no picture in Shared Assets/%s/ (or one folder down) to use: put it there first, or drag it "
                         "in here" % "/".join(where))
    refused, kw = Exception, {}                                  # a stand-in mover: any refusal it raises
    if mover is None:
        _drive()
        from gdrive_creator.move import move as mover, MoveRefused as refused
        kw = {"svc": svc} if svc is not None else {}
    try:
        moved = mover(hit["id"], ["runs", "email-production", spec["brand"], run.name, "media"], by,
                      why="%s %s: use my newest" % (run.name, p_code), **kw)
    except refused as e:
        raise SystemExit("%s was not moved (%s); nothing changed, it is still in %s/" % (hit["name"], e, hit["folder"]))
    original = {"drive_id": moved["drive_id"], "label": "%s/%s" % (moved["to"], moved.get("name") or hit["name"])}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            local = (fetcher or _fetch_id(svc))(moved["drive_id"], tmp)
            res = place(run, code, str(local), alt, by, made_with, "own", None, drive, original=original)
    except SystemExit as e:
        raise SystemExit("%s — %s was moved to %s/ (record %s); the email is unchanged"
                         % (e, hit["name"], moved["to"], moved.get("record")))
    rec = _outcome(by, run, p_code, made_with, purpose, spec["brand"], outcome_root)
    return dict(res, moved=moved, original=original, outcome=str(rec), newest=hit)


def moved_line(r):
    """The reply's proof it moved (the team, ~04:30Z: gone from her folder, and where it went)."""
    m = r["moved"]
    return "%s moved from %s to %s (record %s)" % (m.get("name") or r["newest"]["name"], m.get("from"), m.get("to"),
                                                   m.get("record"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("list")
    a.add_argument("run")
    a.add_argument("--brand")
    b = sub.add_parser("place")
    b.add_argument("run")
    b.add_argument("code")
    b.add_argument("file", help="a file on this Mac, a Google Drive link or id, or a picture's https link (a Higgsfield result)")
    b.add_argument("--alt", required=True, help="what the NEW picture shows, for people who can't see it")
    b.add_argument("--brand")
    b.add_argument("--by", default=ROLE)
    b.add_argument("--made-with", default="", help="the tool that made it (Higgsfield); leave out for a real photo")
    b.add_argument("--source-id", help="the tool's own id for the picture (a Higgsfield generation id), kept with its link")
    b.add_argument("--ratio", choices=("own", "slot"), default="own",
                   help="own: the picture's own shape (default); slot: crop to the shape the old photo had")
    b.add_argument("--focus", help="x,y between 0 and 1: the point a crop keeps (default the middle)")
    b.add_argument("--no-drive", action="store_true", help="tests on a copy only: skip the Drive mirror")
    b.add_argument("--commit", action="store_true", help="commit and push the changed email (ask.py's share)")
    c = sub.add_parser("newest", help="the newest picture in the email's returned/ folder: shown, or with a P-code taken")
    c.add_argument("run")
    c.add_argument("code", nargs="?")
    c.add_argument("--alt", default="", help="what the NEW picture shows, for people who can't see it")
    c.add_argument("--made-with", default="", help="what made it: Higgsfield, Photoshop, a real photo… (required)")
    c.add_argument("--role", default=None, help="whose returned/ folder, by role (default: the asker's role, else %s)" % ROLE)
    c.add_argument("--brand")
    c.add_argument("--by", default=ROLE)
    c.add_argument("--commit", action="store_true", help="commit and push the changed email and its records")
    x = ap.parse_args()
    run = find_run(x.run, x.brand)
    if x.cmd == "newest" and not x.code:
        spec = json.loads((run / "design" / "email.json").read_text())
        where = returned_parts(spec["brand"], run.name, x.role or role_of(x.by))
        print(json.dumps({"folder": "Shared Assets/%s/" % "/".join(where), "newest": newest(where)}, indent=1,
                         ensure_ascii=False))
        return
    if x.cmd == "newest":
        r = take_newest(run, x.code, x.alt, x.by, x.made_with, role=x.role)
        r["said"] = moved_line(r)
        if x.commit and all(s["ok"] for s in r["rebuilt"]):
            sys.path.insert(0, str(HERE))
            import ask
            rel = str(run.relative_to(REPO))
            recs = [str(Path(p).resolve().relative_to(REPO)) for p in (r["outcome"], r["moved"].get("record")) if p]
            r["git"] = ask.share([rel] + recs, "%s's newest: %s %s" % (x.by, rel.split("/")[-1], r["picture"]))
        print(json.dumps(r, indent=1, ensure_ascii=False))
        if not all(s["ok"] for s in r["rebuilt"]):
            sys.exit(1)
        return
    if x.cmd == "list":
        spec = json.loads((run / "design" / "email.json").read_text())
        short = re.sub(r"^%s-" % re.escape(spec.get("brand", "")), "", run.name)
        rows = [{"code": "%s · P%d" % (short, n), "s": "%s · S%d.%d" % (short, i + 1, j + 1), "section": i, "index": j,
                 "kind": sec_kind(spec, i),
                 "now": "to make" if "todo" in d else d.get("source"), "alt": d.get("alt")} for n, i, j, d in slots(spec)]
        print(json.dumps({"run": str(run), "pictures": rows}, indent=1, ensure_ascii=False))
        return
    focus = [float(v) for v in x.focus.split(",")] if x.focus else None
    r = place_own(run, x.code, x.file, x.alt, x.by, x.made_with, x.ratio, focus, not x.no_drive, x.source_id)
    if x.commit and all(s["ok"] for s in r["rebuilt"]):
        sys.path.insert(0, str(HERE))
        import ask
        rel = str(run.relative_to(REPO))
        recs = [str(Path(r["outcome"]).resolve().relative_to(REPO))]
        r["git"] = ask.share([rel] + recs, "%s's own picture: %s %s" % (x.by, rel.split("/")[-1], r["picture"]))
    print(json.dumps(r, indent=1, ensure_ascii=False))
    if not all(s["ok"] for s in r["rebuilt"]):
        sys.exit(1)


def sec_kind(spec, i):
    return spec["sections"][i]["s"]


if __name__ == "__main__":
    main()
