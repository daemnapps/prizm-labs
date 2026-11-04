"""statics.py — the hand-offs waiting for a maker on the content-queue page: the team's statics, QB-9 (the team statics), and
the team's videos, QB-11 (the team view). Read from Drive directly (Shared Assets/runs/handoffs/<role>/<brand>/<key>/),
never from the owner's runs/queue/index.json, which reaches main about once a day (the team, 2026-10-29).

  statics.py list [--role graphic-designer | video-editor] [--out <repo>/runs/creative-queue/<statics | videos>]
  statics.py done <key> [--role …] --by <person> [--out …] [--no-commit]

The role (ROLES) sets the Drive folder, the cache folder, what counts as work back in returned/ (pictures for a
graphic designer, any file for a video editor), whether there is an approved picture, the review lane and the refusal.
--role defaults to graphic-designer, so QB-9's commands and output are unchanged.

`list` prints {"read_at", "rows", "incomplete", "error"} and writes only its own cache under --out: each hand-off's
approved picture (<brand>/<key>/approved.png, gitignored media) and cache.json (gitignored), so a folder costs three
Drive listings and the brief and picture are fetched again only when their Drive file id changes or a day has passed.
A row is one COMPLETE hand-off — BRIEF.md, RUN.md and run.json at its top and a refs/ folder (components/briefs/
HANDOFF-QUEUE.md's four parts): its brand, key, title (the brief's `# BRIEF · … · <title>` heading, else its first
`# ` heading that is not "DOCUMENT …" — a video brief has no BRIEF line — else the key),
Drive folder link, how many files and pictures are in returned/, the approved picture (00-approved/*-approved.png, not
-clean; matched by suffix because older keys name it differently) and `done` once the team has pressed Done. An incomplete
hand-off is never a row; it is listed under `incomplete` with what it lacks. No key or no Drive: rows [], and `error`
says why (exit 0, so the page can say it).

`done` is the team's "Done: send to the team". Refused (exit 2, nothing written) when the hand-off is not there or not
complete, or returned/ holds no work (no picture for statics; nothing at all for video; a missing returned/ folder
counts as empty and is never created). Otherwise it writes <brand>/<key>/done.json and files ONE review request to
the team (components/review file_request, lane static-done or video-done, the returned/ folder as the Drive asset), commits both by path
and pushes. Only the team is told; she passes it to the owner. A second Done says it was already sent and files nothing.
Nothing on Drive is ever written, moved or deleted. Exit 0 ok, 2 refused, 1 any other error.
"""
import argparse
import json
import re
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
import qcore  # noqa: E402  the same component: its commit by path

HANDOFFS = ["runs", "handoffs"]                       # Shared Assets/runs/handoffs/<role>/, the hand-off roots
PARTS = HANDOFFS + ["graphic-designer"]
OUT = REPO / "runs" / "creative-queue" / "statics"
NEEDS_FILES = ("BRIEF.md", "RUN.md", "run.json")
NEEDS_FOLDERS = ("refs",)
PICTURE = re.compile(r"\.(png|jpe?g|webp|gif|tiff?|psd|heic)$", re.I)
TITLE = re.compile(r"^# BRIEF · (.+)$", re.M)
HEADING = re.compile(r"^# (?!DOCUMENT\b)(.+)$", re.M)
FRESH_S = 24 * 3600                                   # a cached brief or picture is fetched again after a day
REVIEWER = "pm"                                    # only the team is told (the team, 2026-10-29)
LANE = "static-done"
DRIVE_FOLDER = "https://drive.google.com/drive/folders/%s"
ROLES = {
    "graphic-designer": {"out": "statics", "work": PICTURE, "picture": True, "lane": LANE, "type": "image", "card": "QB-9 (the team statics)",
                         "what": "statics", "empty": "Not sent: returned/ has no pictures yet. "
                                                    "Put your finished pictures there first."},
    "video-editor": {"out": "videos", "work": None, "picture": False, "lane": "video-done", "type": "video", "card": "QB-11 (the team view)",
                     "what": "video", "empty": "Not sent: returned/ is empty. Put your finished cut there first."},
}


def role_of(role):
    if role not in ROLES:
        raise ValueError("no role %r: %s" % (role, " | ".join(sorted(ROLES))))
    return ROLES[role]


def out_of(role):
    return REPO / "runs" / "creative-queue" / role_of(role)["out"]


class Refused(Exception):
    """Done will not run; the message says why. Nothing was written."""


NO_DRIVE = "this computer can't reach Drive yet (no Drive key or Drive package here); the team or the team can set it up"


class NoDrive(Exception):
    """gdrive-creator stopped before any read: no key, or no Google package (it exits; the page needs words)."""


def open_drive():
    """Drive(), with gdrive-creator's SystemExit (no key, no package) turned into NoDrive carrying its own words."""
    try:
        return Drive()
    except SystemExit as e:
        raise NoDrive(str(e.code if e.code is not None else e))


class Drive(object):
    """The four reads statics needs, through gdrive-creator's public surface (engine + reach)."""

    def __init__(self):
        home = REPO / "components" / "gdrive-creator"
        if str(home) not in sys.path:
            sys.path.append(str(home))
        # Google's libraries warn on every import under Python 3.9; the kit shows a command's LAST line, which must be
        # statics' own answer, not that warning
        warnings.simplefilter("ignore", FutureWarning)
        from gdrive_creator import engine, reach
        self.E, self.R = engine, reach
        self.svc = engine.service()

    def folder(self, parts):
        return self.E.folder_by_path("/".join([self.R.SHARED_DRIVE] + list(parts)), svc=self.svc)

    def subfolders(self, fid):
        return self.R.subfolders(fid, svc=self.svc)

    def files(self, fid):
        return sorted(self.E.list_files(fid, svc=self.svc), key=lambda f: f.get("name") or "")

    def get(self, file_id, dest):
        return self.E.get_media(file_id, str(dest), svc=self.svc)


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def approved_of(files):
    """The approved picture among 00-approved/'s files: *-approved.png (never -approved-clean), else None."""
    for f in files:
        if (f.get("name") or "").lower().endswith("-approved.png"):
            return f
    return None


def title_of(text, key):
    m = TITLE.search(text or "")
    if m:
        return m.group(1).split(" · ")[-1].strip()
    h = HEADING.search(text or "")
    return h.group(1).strip() if h else key


def brand_of(key):
    """The key's brand, the part before its first "_" (brand_a_nova-face-brush_brief-0296 → brand-a)."""
    return key.split("_", 1)[0]


def _fetch(drive, cache, slot, f, dest, clock):
    """Fetch file f to dest unless the cache already holds it by the same Drive id within a day; True when on disk."""
    seen = cache.get(slot) or {}
    if dest.is_file() and seen.get("id") == f["id"] and clock() - seen.get("at", 0) < FRESH_S:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        drive.get(f["id"], dest)
    except Exception:  # noqa: BLE001 — a picture that did not come is a placeholder, never a failed list
        return dest.is_file()
    cache[slot] = {"id": f["id"], "at": clock()}
    return dest.is_file()


def read_one(drive, brand, key, fid, out, clock=time.time, role="graphic-designer"):
    """(row, None) for a complete hand-off, (None, {"key", "brand", "missing"}) for an incomplete one."""
    top = drive.files(fid)
    subs = {s["name"]: s["id"] for s in drive.subfolders(fid)}
    names = {f["name"] for f in top}
    missing = [n for n in NEEDS_FILES if n not in names] + [n + "/" for n in NEEDS_FOLDERS if n not in subs]
    if missing:
        return None, {"key": key, "brand": brand, "missing": missing}
    home = Path(out) / brand / key
    cache = _read(home / "cache.json") or {}
    back = drive.files(subs["returned"]) if "returned" in subs else []
    title = key
    brief = next(f for f in top if f["name"] == "BRIEF.md")
    if _fetch(drive, cache, "brief", brief, home / "BRIEF.md", clock):
        title = title_of((home / "BRIEF.md").read_text(errors="replace"), key)
    picture, R = None, role_of(role)
    appr = approved_of(drive.files(subs["00-approved"])) if R["picture"] and "00-approved" in subs else None
    if appr and _fetch(drive, cache, "picture", appr, home / "approved.png", clock):
        picture = (home / "approved.png").relative_to(REPO).as_posix() if _inside(home, REPO) else str(home / "approved.png")
    if cache:
        home.mkdir(parents=True, exist_ok=True)
        (home / "cache.json").write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n")
    done = _read(home / "done.json")
    return {
        "key": key, "brand": brand, "title": title,
        "drive_id": fid, "drive_url": DRIVE_FOLDER % fid,
        "returned_files": len(back), "returned_pictures": sum(1 for f in back if PICTURE.search(f.get("name") or "")),
        "returned_work": sum(1 for f in back if R["work"] is None or R["work"].search(f.get("name") or "")),
        "returned_id": subs.get("returned"),
        "picture": picture,
        "done": done if isinstance(done, dict) else None,
    }, None


def _inside(p, root):
    try:
        Path(p).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def listing(drive, out=OUT, clock=time.time, role="graphic-designer"):
    parts = HANDOFFS + [role]
    role_of(role)
    root = drive.folder(parts)
    if not root:
        return {"read_at": _now(), "rows": [], "incomplete": [], "error": "no Shared Assets/%s on Drive" % "/".join(parts)}
    rows, incomplete = [], []
    for b in drive.subfolders(root):
        for k in drive.subfolders(b["id"]):
            row, gap = read_one(drive, b["name"], k["name"], k["id"], out, clock, role)
            (rows if row else incomplete).append(row or gap)
    return {"read_at": _now(), "rows": rows, "incomplete": incomplete, "error": None}


def done(drive, key, by, out=OUT, commit=True, file_request=None, commit_paths=None, now=None, role="graphic-designer"):
    """the team's Done. Returns the line to show; Refused before anything is written."""
    brand = brand_of(key)
    home = Path(out) / brand / key
    was = _read(home / "done.json")
    if isinstance(was, dict):
        return "Already sent to the team %s (%d files back then)." % (was.get("at"), was.get("returned_files") or 0)
    R = role_of(role)
    fid = drive.folder(HANDOFFS + [role, brand, key])
    if not fid:
        raise Refused("Not sent: no hand-off %s on Drive." % key)
    row, gap = read_one(drive, brand, key, fid, out, role=role)
    if gap:
        raise Refused("Not sent: the hand-off is incomplete (missing %s). the owner packs it again." % ", ".join(gap["missing"]))
    if not row["returned_work"]:
        raise Refused(R["empty"])
    at = now or _now()
    who = by[:1].upper() + by[1:]
    if file_request is None:
        sys.path.append(str(REPO / "components" / "review"))
        from review_request import file_request
    got = file_request(
        asset={"warehouse": "drive", "ref": row["returned_id"],
               "title": "%s is done with %s: %s (%d files back)" % (who, key, row["title"], row["returned_files"])},
        type=R["type"], reviewers=[REVIEWER], lane=R["lane"], requested_by=by.lower(),
        notes="\n".join([
            "What this is: %s finished the %s for brief %s, %s (%s)." % (who, R["what"], key, row["title"], brand),
            "What came back: %d files, %d of them pictures, in returned/: %s" % (
                row["returned_files"], row["returned_pictures"], row["drive_url"]),
            "Why you: you pass finished %s to the owner." % R["what"],
            "What ends your part: you send it on to the owner."]),
        root=str(REPO), commit=False)
    rec = {"schema": 1, "key": key, "brand": brand, "role": role, "title": row["title"], "by": who, "at": at,
           "returned_files": row["returned_files"], "returned_pictures": row["returned_pictures"],
           "drive_url": row["drive_url"], "review": {"item": got.get("item"), "route": got.get("route"),
                                                       "path": got.get("path")}}
    home.mkdir(parents=True, exist_ok=True)
    (home / "done.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    if commit:
        paths = [home / "done.json"] + ([Path(got["path"])] if got.get("route") == "git" and got.get("path") else [])
        (commit_paths or qcore.commit_paths)(
            paths, "%s: %s done by %s, %d files back (%s)" % (R["out"], key, who, row["returned_files"], R["card"]), REPO)
    return "Sent to the team: %s, %d files back." % (row["title"], row["returned_files"])


def main(argv=None, drive=None):
    ap = argparse.ArgumentParser(prog="statics.py", description="the team's statics, read from Drive.")
    sub = ap.add_subparsers(dest="cmd")
    a_list = sub.add_parser("list")
    a_list.add_argument("--out")
    a_list.add_argument("--role", default="graphic-designer", choices=sorted(ROLES))
    a_done = sub.add_parser("done")
    a_done.add_argument("key")
    a_done.add_argument("--by", required=True)
    a_done.add_argument("--role", default="graphic-designer", choices=sorted(ROLES))
    a_done.add_argument("--out")
    a_done.add_argument("--no-commit", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 1
    out = Path(a.out) if getattr(a, "out", None) else out_of(getattr(a, "role", None) or "graphic-designer")
    if a.cmd == "list":
        try:
            drive = drive or open_drive()
        except (NoDrive, Exception) as e:  # noqa: BLE001 — no key, no package: the page says why in plain words
            print(json.dumps({"read_at": _now(), "rows": [], "incomplete": [], "error": NO_DRIVE,
                              "detail": str(e)[:400]}))
            return 0
        print(json.dumps(listing(drive, out, role=a.role), ensure_ascii=False, sort_keys=True))
        return 0
    if a.cmd == "done":
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*_[A-Za-z0-9._-]+", a.key) or ".." in a.key:
            print("Not sent: %r is not a hand-off key." % a.key, file=sys.stderr)
            return 2
        try:
            try:
                drive = drive or open_drive()
            except NoDrive as e:
                print("(%s)" % str(e)[:200])          # the detail first: the kit shows the LAST line
                print("Not sent: %s." % NO_DRIVE)
                return 1
            print(done(drive, a.key, a.by, out, commit=not a.no_commit, role=a.role))
            return 0
        except Refused as e:
            print(str(e))
            return 2
        except Exception as e:  # noqa: BLE001
            print("error: %s" % e, file=sys.stderr)
            return 1
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
