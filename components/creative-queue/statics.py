"""statics.py — the hand-offs waiting for a maker on the content-queue page: editor's statics, QB-9 (editor statics), and
creator's videos, QB-11 (creator view). Read from Drive directly (Shared Assets/runs/handoffs/<role>/<brand>/<key>/),
never from owner's runs/queue/index.json, which reaches main about once a day (email_lead, 2026-10-29).

  statics.py list [--role graphic-designer | video-editor] [--out <repo>/runs/creative-queue/<statics | videos>]
  statics.py done <key> [--role …] --by <person> [--out …] [--no-commit]
  statics.py refresh [--role …] [--out …]    the full Drive walk, kept as the last good list (list starts it)

The role (ROLES) sets the Drive folder, the cache folder, what counts as work back in returned/ (pictures for a
graphic designer, any file for a video editor), whether there is an approved picture, the review lane and the refusal.
--role defaults to graphic-designer, so QB-9's commands and output are unchanged.

`list` answers at once from the last good list (<out>/last.json, Done read from disk now) and, when that list is
older than STALE_S or there is none, starts one `refresh` in the background; `refreshing` is true while it runs
(2026-11-02: a cold Drive walk took 137 s). `refresh` is the walk itself, printing nothing; it keeps its result as
last.json, an error apart in refresh-error.json (shown as `refresh_error`, or `error` with no list yet). Both print or
keep {"read_at", "rows", "incomplete", "error"}, and write only under --out: each hand-off's
approved picture (<brand>/<key>/approved.png, gitignored media) and cache.json (gitignored), so a folder costs three
Drive listings and the brief and picture are fetched again only when their Drive file id changes or a day has passed.
A row is one COMPLETE hand-off — BRIEF.md, RUN.md and run.json at its top and a refs/ folder (components/briefs/
HANDOFF-QUEUE.md's four parts): its brand, key, title (the brief's `# BRIEF · … · <title>` heading, else its first
`# ` heading that is not "DOCUMENT …" — a video brief has no BRIEF line — else the key),
Drive folder link, how many files and pictures are in returned/, the approved picture (00-approved/*-approved.png, not
-clean; matched by suffix because older keys name it differently), `done` once editor has pressed Done, and `moment`
(2026-11-03): the campaign the brief names most often among the brand's dated moments (brands/<brand>/strategy/
moments.json, read only), at least MOMENT_MIN times, else null; read from the cached brief whenever `list` answers. An incomplete
hand-off is never a row; it is listed under `incomplete` with what it lacks. Neither a row nor incomplete (2026-11-25):
a brief the owner has not approved (components/briefs/approved.py), unless finished work is already back, and an idea
with no brief number. For the video editor only, a folder with
a handoff.md and no BRIEF.md (owner's own form, 2026-11-03) is complete: its handoff.md stands for the brief and the
row says `form: "handoff.md"` (else "four parts"). No key or no Drive: rows [], and `error`
says why (exit 0, so the page can say it).

`done` is editor's "Done: send to email_lead". Refused (exit 2, nothing written) when the hand-off is not there or not
complete, or returned/ holds no work (no picture for statics; nothing at all for video; a missing returned/ folder
counts as empty and is never created). Otherwise it writes <brand>/<key>/done.json and files ONE review request to
email_lead (components/review file_request, lane static-done or video-done, the returned/ folder as the Drive asset), commits both by path
and pushes. Only email_lead is told; she passes it to owner. A second Done says it was already sent and files nothing.
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
BRANDPATH = HERE.parent / "brandpath"
if str(BRANDPATH) not in sys.path:
    sys.path.append(str(BRANDPATH))
from brandpath import brand_root  # noqa: E402  builder card rule 3: brand folders through brandpath

HANDOFFS = ["runs", "handoffs"]                       # Shared Assets/runs/handoffs/<role>/, the hand-off roots
PARTS = HANDOFFS + ["graphic-designer"]
OUT = REPO / "runs" / "creative-queue" / "statics"
NEEDS_FILES = ("BRIEF.md", "RUN.md", "run.json")
NEEDS_FOLDERS = ("refs",)
PICTURE = re.compile(r"\.(png|jpe?g|webp|gif|tiff?|psd|heic)$", re.I)
VIDEO = re.compile(r"\.(mp4|mov|m4v|webm|mkv|avi)$", re.I)   # a finished cut; a README or a note in returned/ is not
SET_ASIDE = re.compile(r"^(superseded|old|archive)", re.I)  # a returned/ subfolder of cuts put aside, not the delivery
IDEA = re.compile(r"_idea-\d+$", re.I)           # a folder named by its production id: the register has not numbered it
VERSION = re.compile(r"^v\d+$")                 # a hand-off's version folders, v1/ ... v5/ (the brief's variations)
TITLE = re.compile(r"^# BRIEF · (.+)$", re.M)
HEADING = re.compile(r"^# (?!DOCUMENT\b)(.+)$", re.M)
FRESH_S = 24 * 3600                                   # a cached brief or picture is fetched again after a day
REVIEWER = "email_lead"                                    # only email_lead is told (email_lead, 2026-10-29)
LANE = "static-done"
DRIVE_FOLDER = "https://drive.google.com/drive/folders/%s"
MOMENT_MIN = 3        # a brief names its campaign at least this often (2026-11-03: the 44 Black Friday briefs name it
                      #   11 to 14 times, the two that are not Black Friday never)
DATED = ("holiday", "window", "date")                 # a moment with a date is a campaign; `any` and `live` are not
ROLES = {
    "graphic-designer": {"out": "statics", "work": PICTURE, "picture": True, "lane": LANE, "type": "image", "card": "QB-9 (editor statics)",
                         "what": "statics", "empty": "Not sent: returned/ has no pictures yet. "
                                                    "Put your finished pictures there first."},
    # also: the production stage is creator's too (components/stage-handoff/roles.json: video-producer held by creator and
    # owner). owner hands some videos out there (0334 "The Inch", 2026-11-19, START.md form), and the queue saw only
    # his register's stale "brief to approve" for it (email_lead, 2026-11-19).
    "video-editor": {"out": "videos", "work": VIDEO, "picture": False, "lane": "video-done", "type": "video", "card": "QB-11 (creator view)",
                     "also": ("video-producer",),
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


NO_DRIVE = "this computer can't reach Drive yet (no Drive key or Drive package here); email_lead or designer can set it up"


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


def moments_of(brand):
    """The brand's dated moment keys, from brands/<brand>/strategy/moments.json (read only): every entry with a `key`
    and an `anchor` naming a holiday, a window or a date. [] when the brand keeps no such file."""
    try:
        doc = json.loads((brand_root(brand) / "strategy" / "moments.json").read_text())
    except (OSError, ValueError):
        return []
    keys = []

    def walk(x):
        if isinstance(x, dict):
            a = x.get("anchor")
            if isinstance(x.get("key"), str) and isinstance(a, dict):
                if any(k in a for k in DATED) and x["key"] not in keys:
                    keys.append(x["key"])
                return
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(doc)
    return keys


def moment_of(text, keys):
    """The campaign a brief is for: the moment key its text names most often ("black-friday", "Black Friday" or
    "black friday" alike), at least MOMENT_MIN times; else None. Ties go to the earlier key."""
    low, best, most = (text or "").lower(), None, MOMENT_MIN - 1
    for k in keys:
        pat = r"\b" + "[- ]".join(re.escape(w) for w in k.lower().split("-")) + r"\b"
        n = len(re.findall(pat, low))
        if n > most:
            best, most = k, n
    return best


def _moment(home, brand, memo):
    """moment_of the hand-off's cached BRIEF.md, the brand's keys read once per call (memo)."""
    if brand not in memo:
        memo[brand] = moments_of(brand)
    try:
        return moment_of((Path(home) / "BRIEF.md").read_text(errors="replace"), memo[brand])
    except OSError:
        return None


def brand_of(key):
    """The key's brand, the part before its first "_" (brand_a_flex-face-brush_brief-0296 → brand_a)."""
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
    # A video hand-off packed by hand with one handoff.md (owner's own form, as for brand_b Body Scrub 0324 and 0325 on
    # 2026-11-03: "Each folder has the brief, edit notes, voice, music, the swipe and a Higgsfield prompt per scene. Open
    # handoff.md first") is complete for the video editor: creator works from it. Its handoff.md stands for the brief.
    # Statics keep the four parts (email_lead, 2026-11-11: make creator's page match what he is really doing).
    own = next((f for f in top if (f.get("name") or "").lower() == "handoff.md"), None) if role == "video-editor" else None
    form = "four parts"
    if missing and own is not None and "BRIEF.md" not in names:
        missing, form = [], "handoff.md"
    if missing and role == "video-editor" and "START.md" in names and "BRIEF.md" in names:   # a production packet:
        missing, form = [], "START.md"                                                       # BRIEF.md + START.md
    writing = None   # a writing continuation (email_lead, 2026-11-19: owner's six Grandma Yai jobs for creator): no brief yet,
    if missing and role == "video-editor" and "START.md" in names and "HANDOFF.json" in names:   # its START.md and
        hj = next(f for f in top if f["name"] == "HANDOFF.json")                                  # HANDOFF.json say so
        hcache = _read(Path(out) / brand / key / "cache.json") or {}
        if _fetch(drive, hcache, "handoff", hj, Path(out) / brand / key / "HANDOFF.json", clock):
            hd = _read(Path(out) / brand / key / "HANDOFF.json") or {}
            if isinstance(hd, dict) and hd.get("packet_kind") == "writing-continuation":
                stops = [x for x in hd.get("stopped") or [] if isinstance(x, dict)]
                writing = {"title": hd.get("title"), "stage": hd.get("stage"),
                           "held": any(str(x.get("status")).lower() == "held" for x in stops),
                           "at": ", ".join(str(x.get("stage")) for x in stops if x.get("stage")) or None}
                missing, form = [], "writing"
            (Path(out) / brand / key).mkdir(parents=True, exist_ok=True)
            (Path(out) / brand / key / "cache.json").write_text(json.dumps(hcache, indent=1, sort_keys=True) + "\n")
    if missing:
        return None, {"key": key, "brand": brand, "missing": missing}
    home = Path(out) / brand / key
    cache = _read(home / "cache.json") or {}
    back = _returned(drive, subs.get("returned"))
    title = key
    brief = own if form == "handoff.md" else next(f for f in top if f["name"] == ("START.md" if form == "writing" else "BRIEF.md"))   # cached as BRIEF.md either way
    if _fetch(drive, cache, "brief", brief, home / "BRIEF.md", clock):
        title = title_of((home / "BRIEF.md").read_text(errors="replace"), key)
    if writing and writing.get("title"):
        title = writing["title"]
    if form == "handoff.md" and title == key:    # owner's handoff.md is headed by the key; the name is in briefs/<brief>/brief.md
        title = _named(drive, cache, subs, (home / "BRIEF.md"), home, key, clock)
    picture, R = None, role_of(role)
    appr = approved_of(drive.files(subs["00-approved"])) if R["picture"] and "00-approved" in subs else None
    if R["picture"] and not appr and "refs" in subs:   # with no 00-approved/, the preview is the plate packed in refs/ (email_lead,
        refs = [f for f in drive.files(subs["refs"])    # 2026-11-19: "por qué en el static no se ve la imagencita"): the approved
                if re.search(r"\.(png|jpe?g|webp)$", f.get("name") or "", re.I) and "clean" not in (f.get("name") or "").lower()]
        for word in ("approved", "final", "original", "print", "source"):  # plate (a revision), else the final, else the picked original or its source (dec26)
            appr = next((f for f in refs if word in (f.get("name") or "").lower()), None)
            if appr:
                break
    if appr and _fetch(drive, cache, "picture", appr, home / "approved.png", clock):
        picture = (home / "approved.png").relative_to(REPO).as_posix() if _inside(home, REPO) else str(home / "approved.png")
    made = None        # when and by whom the hand-off was made, for the card's history (email_lead, 2026-11-19): HANDOFF.json's
    hjf = next((f for f in top if f.get("name") == "HANDOFF.json"), None)   # "made" and "from.by", else run.json's below
    if hjf and _fetch(drive, cache, "handoff", hjf, home / "HANDOFF.json", clock):
        hd = _read(home / "HANDOFF.json") or {}
        if isinstance(hd, dict) and hd.get("made"):
            made = {"at": hd.get("made"), "by": (hd.get("from") or {}).get("by") if isinstance(hd.get("from"), dict) else None}
    revision = None    # a hand-off that came back for revision says so in its run.json (state "revision", email_lead 2026-11-19)
    rj = next((f for f in top if f.get("name") == "run.json"), None)
    if rj and _fetch(drive, cache, "run", rj, home / "run.json", clock):
        run = _read(home / "run.json") or {}
        if isinstance(run, dict) and not made and (run.get("made") or run.get("created")):
            made = {"at": run.get("made") or run.get("created"), "by": None}
        if isinstance(run, dict) and str(run.get("state") or "").lower() == "revision":
            revision = {"round": run.get("round") or run.get("revision_round"),
                        "why": run.get("what_must_be_fixed") or run.get("next_action") or run.get("title")}
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
        # When each piece of work in returned/ last changed (Drive's modifiedTime), oldest first: a redo is finished by
        # work newer than the moment it was put back on the list, whoever made it (email_lead, 2026-11-06: "que se muevan solos")
        "returned_work_at": sorted(f["modifiedTime"] for f in back if f.get("modifiedTime")
                                   and (R["work"] is None or R["work"].search(f.get("name") or ""))),
        # How many versions the brief asks for: the board counts a static finished when returned/ holds at least
        # this much work, Done or not (owner, 2026-11-04: work in returned/ is the signal; email_lead, 2026-11-04).
        "versions": sum(1 for n in subs if VERSION.match(n)),
        "picture": picture,
        "done": done if isinstance(done, dict) else None,
        "moment": _moment(home, brand, {}),
        "form": form,
        "handed": _handed(home / "BRIEF.md") if form == "handoff.md" else None,
        "revision": revision,
        "writing": writing,
        "made": made,
    }, None


def _returned(drive, rid, depth=0):
    """Every file under returned/, its subfolders included, save a folder set aside (superseded/, old/, archive/).
    creator returns brand_a 0274 as returned/control/ and returned/v1-meme-wall/ …, brand_b 0324 and 0325 as
    returned/control/ and returned/variations/ (Drive, 2026-11-12): a top-level-only read saw none of it."""
    if not rid:
        return []
    found = list(drive.files(rid))
    if depth < 3:
        for sub in drive.subfolders(rid):
            if not SET_ASIDE.match(sub.get("name") or ""):
                found += _returned(drive, sub["id"], depth + 1)
    return found


BRIEF_FILE = re.compile(r"briefs/(brief-\d+)/brief\.md")
HANDED = re.compile(r"hand-off · [^·\n]+ · (\d{4}-\d{2}-\d{2})")


def _handed(path):
    """The day a handoff.md says it was handed over ("Video editor hand-off · brand_b · 2026-11-02 · handoff/1"), or None:
    work in returned/ from before it is not the editor's (brand_b 0325 held one file from the day before it reached creator)."""
    try:
        m = HANDED.search(Path(path).read_text(errors="replace"))
        return m.group(1) if m else None
    except OSError:
        return None


def _named(drive, cache, subs, handoff, home, key, clock):
    """The brief's own name for a handoff.md hand-off: the brief file it names (briefs/brief-NNNN/brief.md), fetched
    once like the brief; the key when there is none."""
    try:
        m = BRIEF_FILE.search(handoff.read_text(errors="replace"))
        if not m or "briefs" not in subs:
            return key
        sub = next((f["id"] for f in drive.subfolders(subs["briefs"]) if f["name"] == m.group(1)), None)
        f = next((x for x in drive.files(sub) if x["name"] == "brief.md"), None) if sub else None
        if f and _fetch(drive, cache, "named", f, home / "brief-named.md", clock):
            return title_of((home / "brief-named.md").read_text(errors="replace"), key)
    except Exception:  # noqa: BLE001  a name is a nicety: never fail the listing for it
        pass
    return key


def _inside(p, root):
    try:
        Path(p).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def approved(role):
    """The briefs this role may read: the ones the owner approved (components/briefs/approved.py, 2026-11-25)."""
    p = str(REPO / "components" / "briefs")
    if p not in sys.path:
        sys.path.append(p)
    import approved as A
    return A.readable(role, REPO)


def listing(drive, out=OUT, clock=time.time, role="graphic-designer"):
    parts = HANDOFFS + [role]
    R = role_of(role)
    root = drive.folder(parts)
    if not root:
        return {"read_at": _now(), "rows": [], "incomplete": [], "error": "no Shared Assets/%s on Drive" % "/".join(parts)}
    rows, incomplete, seen, ok = [], [], set(), approved(role)
    for folder, stage in [(root, role)] + [(drive.folder(HANDOFFS + [a]), a) for a in R.get("also") or ()]:
        if not folder:
            continue
        for b in drive.subfolders(folder):
            for k in drive.subfolders(b["id"]):
                if k["name"] in seen:          # the role's own folder first: one hand-off a key
                    continue
                seen.add(k["name"])
                if IDEA.search(k["name"]):     # no brief number yet: an idea, never a maker's work (2026-11-25)
                    continue
                row, gap = read_one(drive, b["name"], k["name"], k["id"], out, clock, role)
                if k["name"] not in ok and not (row or {}).get("returned_work"):
                    continue                   # not approved by the owner: not a maker's to read. What came back stays.
                if stage != role:              # the production folder: only a complete packet (BRIEF.md + START.md, or
                    if not row:                #   the role's own parts); its writing continuations are not videos yet
                        continue
                    row["stage_role"] = stage
                (rows if row else incomplete).append(row or gap)
    return {"read_at": _now(), "rows": rows, "incomplete": incomplete, "error": None}


LAST, LOCK, FAILED = "last.json", "refresh.json", "refresh-error.json"   # per machine, gitignored
STALE_S = 300                                         # a last good list older than this starts one refresh behind it
LOCK_S = 15 * 60                                      # a refresh that has not finished in this long is taken as dead


def _write(path, doc):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True))
    tmp.replace(path)                                 # a reader never sees half a file


def _spawn(out, role):
    """One `statics.py refresh` in the background, detached from the page server's request."""
    import subprocess
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "refresh", "--role", role, "--out", str(out)],
                     cwd=str(REPO), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def quick(out=OUT, role="graphic-designer", clock=time.time, spawn=None):
    """The list at once (2026-11-02: a cold Drive walk took 137 s and editor read a missing Done as "already finished"):
    the last good list with each Done read from disk now, `refreshing` while a refresh runs behind it. A list older
    than STALE_S, or none yet, starts ONE refresh (`spawn`); with none yet the rows are [] and `refreshing` says the
    Done buttons are coming. A failed refresh never replaces the last good list: it shows as `refresh_error`, or as
    `error` when there is no list yet."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    last, failed, lock = _read(out / LAST), _read(out / FAILED), _read(out / LOCK)
    now = clock()
    running = bool(lock) and now - lock.get("at", 0) < LOCK_S
    newest = max((last or {}).get("_at", 0), (failed or {}).get("_at", 0))
    if not running and now - newest >= STALE_S:
        _write(out / LOCK, {"at": now})
        (spawn or _spawn)(out, role)
        running = True
    if last:
        doc = {k: v for k, v in last.items() if k != "_at"}
        memo = {}
        for r in doc.get("rows") or []:
            d = _read(out / r["brand"] / r["key"] / "done.json")
            r["done"] = d if isinstance(d, dict) else None
            r["moment"] = _moment(out / r["brand"] / r["key"], r["brand"], memo)   # from the brief on disk, now
        if failed and failed.get("_at", 0) >= last.get("_at", 0):   # kept after it, even in the same second
            doc["refresh_error"] = failed.get("error")
    elif failed:
        doc = {"read_at": failed.get("read_at"), "rows": [], "incomplete": [], "error": failed.get("error")}
    else:
        doc = {"read_at": None, "rows": [], "incomplete": [], "error": None}
    doc["refreshing"] = running
    return doc


def refresh(drive, out=OUT, role="graphic-designer", clock=time.time):
    """The full Drive walk (listing), kept as the last good list; an error is kept apart and never replaces it."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        doc = listing(drive, out, clock, role)
        _write(out / (FAILED if doc.get("error") else LAST), dict(doc, _at=clock()))
        return doc
    finally:
        try:
            (out / LOCK).unlink()                     # its own lock file, written by quick()
        except OSError:
            pass


def done(drive, key, by, out=OUT, commit=True, file_request=None, commit_paths=None, now=None, role="graphic-designer"):
    """editor's Done. Returns the line to show; Refused before anything is written."""
    brand = brand_of(key)
    home = Path(out) / brand / key
    was = _read(home / "done.json")
    if isinstance(was, dict):
        return "Already sent to email_lead %s (%d files back then)." % (was.get("at"), was.get("returned_files") or 0)
    R = role_of(role)
    fid = drive.folder(HANDOFFS + [role, brand, key])
    if not fid:
        raise Refused("Not sent: no hand-off %s on Drive." % key)
    row, gap = read_one(drive, brand, key, fid, out, role=role)
    if gap:
        raise Refused("Not sent: the hand-off is incomplete (missing %s). owner packs it again." % ", ".join(gap["missing"]))
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
            "Why you: you pass finished %s to owner." % R["what"],
            "What ends your part: you send it on to owner."]),
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
    return "Sent to email_lead: %s, %d files back." % (row["title"], row["returned_files"])


def main(argv=None, drive=None):
    ap = argparse.ArgumentParser(prog="statics.py", description="editor's statics, read from Drive.")
    sub = ap.add_subparsers(dest="cmd")
    a_list = sub.add_parser("list")
    a_list.add_argument("--out")
    a_list.add_argument("--role", default="graphic-designer", choices=sorted(ROLES))
    a_ref = sub.add_parser("refresh")
    a_ref.add_argument("--out")
    a_ref.add_argument("--role", default="graphic-designer", choices=sorted(ROLES))
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
        print(json.dumps(quick(out, role=a.role), ensure_ascii=False, sort_keys=True))
        return 0
    if a.cmd == "refresh":
        try:
            drive = drive or open_drive()
        except (NoDrive, Exception) as e:  # noqa: BLE001
            out.mkdir(parents=True, exist_ok=True)
            _write(out / FAILED, {"read_at": _now(), "error": NO_DRIVE, "detail": str(e)[:400], "_at": time.time()})
            try:
                (out / LOCK).unlink()
            except OSError:
                pass
            return 1
        refresh(drive, out, role=a.role)
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
