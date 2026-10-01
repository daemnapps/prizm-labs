#!/usr/bin/env python3
"""The work queue — one active list per brand, for every role, written where
the team already looks: the brand's `briefs/` folder on Google Drive.

    python3 queue.py build --brand <brand>            # rebuild one brand's queue
    python3 queue.py build --all                      # every brand with a briefs folder
    python3 queue.py set   --brand <brand> <brief> bounty="$150" due=2026-09-30 note="face product first" who=Sam
    python3 queue.py show  --brand <brand>            # print it
    python3 queue.py ship  <run-folder> --brand <brand>   # one finished video run → a package on Drive
    python3 queue.py ship  --auto                     # every finished video run, and every image /
                                                      # carousel brief ready to make → Drive

No project-management layer (Damon, 2 Oct 2026): the folders move the work and
this tool only reads them and writes the table. Nobody types a state.

ROWS, ONE PER BRIEF PER ROLE (the `For` column):

    Video editor      a package in briefs/ai-video-production/ (shipped from a finished video run)
    Graphic designer  a package in briefs/image/  (shipped from an image brief marked approved
                      in the private workspace's brief register = ready to make)
    Carousel          a package in briefs/carousel/ (an AI sequence brief marked approved)
    Creator           a creator hand-off folder, Shared Assets/handoffs/creator/<brand>/<folder>/
                      (written by the hand-off tool; the row points at the folder)
    (designer and editor hand-off folders under handoffs/graphic-designer|video-editor/ show too)

STATES, READ FROM FOLDERS AND CARDS, IN ORDER:

    Open        the package (or hand-off folder) is there
    Claimed     a file `<brief> — <name>` is in briefs/claims/  (a creator hand-off: marked sent)
    Delivered   files are in briefs/delivered/<folder>/  (a hand-off: in its returned/)
    In check    its card is in Shared Assets/meta/<brand>/1-check/<lane>/
    Approved    … in 2-approved/
    Live        … in 3-live/  (the count of Meta ad ids on the card is shown)
    Sent back   … in sent-back/ — the row reopens for the same person with Damon's note

BRIEF NUMBERS: a row shows `<product> brief-NNNN` (numbers count per brand and
product) with its old code beside it (a brand code like AB-01, a run name, or pNNN). The numbers are not
in this public repo — they are looked up at run time in the private workspace
(`AI_WORKSPACE`, default ~/Projects/ai-workspace): its naming tool
(components/naming/names.py), the brand's briefs.json, the brief register. A
brief with no number says "no number yet" and is listed under the table.

RENAMED DELIVERIES: the hourly delivery rule renames a delivered folder to its
short unit name (`<brand>_<product>_brief-NNNN_<batch>`) and keeps the old name
in naming.json (`folder_was`). A delivery is matched to its package by brief
number (naming.json `brief`, the unit name, the brand's aliases) or, failing
that, by its name (`AB-02 The Hen's Coat` is `ab-02-hens-coat`).

Hand-set fields — bounty, due, note, who — live in `queue.json` beside the
table and survive every rebuild. Brand-agnostic: the brand is an argument,
the Drive account is an environment variable (`DRIVE_ACCOUNT`).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE_EXT = {".zip"}
PACKAGE_SUFFIXES = ("-premiere-handoff", "-editor-handoff", "-designer-handoff", "-handoff", "-pack")
TYPE_BY_FOLDER = {"ai-video-production": "video", "video": "video",
                  "image": "image", "image-production": "image", "images": "image", "static": "image",
                  "carousel": "carousel", "carousels": "carousel"}
FOR = {"video": "Video editor", "image": "Graphic designer", "carousel": "Carousel", "creator": "Creator"}
LANE_TYPE = {"video": "video", "image": "image", "carousel": "carousel", "creator": "creator"}
HANDOFF_ROLES = {"creator": "creator", "graphic-designer": "image", "video-editor": "video"}
CARD_STATES = {"1-check": "In check", "2-approved": "Approved", "3-live": "Live", "sent-back": "Sent back"}
# what needs someone first: a send-back, then the open work, then what waits on others
ORDER = ["Sent back", "Open", "Claimed", "Delivered", "In check", "Approved", "Live"]
CARD_PRIORITY = ["Sent back", "In check", "Approved", "Live"]
MEDIA = {".mp4", ".mov", ".m4v", ".png", ".jpg", ".jpeg", ".webp", ".heic", ".gif", ".wav", ".mp3", ".m4a"}
NOT_WORK = ("control", "reference", "swipe", "candidate")
STOP = {"the", "a", "an", "of", "and", "v1", "v2", "v3", "final"}


# ---------------------------------------------------------------- the Drive --
def drive_root() -> Path:
    cs = Path.home() / "Library/CloudStorage"
    acct = os.environ.get("DRIVE_ACCOUNT")
    if acct:
        return cs / f"GoogleDrive-{acct}"
    return next(iter(sorted(cs.glob("GoogleDrive-*"))), cs / "GoogleDrive")


def shared_assets() -> Path:
    return Path(os.environ.get("SHARED_ASSETS") or drive_root() / "Shared drives/Shared Assets")


def brands_root() -> Path:
    return shared_assets() / "brands"


def meta_root() -> Path:
    return Path(os.environ.get("META_CARDS_ROOT") or shared_assets() / "meta")


def handoffs_root() -> Path:
    return shared_assets() / "handoffs"


def briefs_folder(brand: str) -> Path | None:
    """`brands/<brand>/briefs`, or wherever a `briefs` folder has drifted to
    under that brand — reported, so the drift is visible, never silent."""
    base = brands_root() / brand
    direct = base / "briefs"
    if direct.is_dir():
        return direct
    for depth in ("*/briefs", "*/*/briefs"):
        for cand in sorted(base.glob(depth)):
            if cand.is_dir():
                print(f"note: {brand}'s briefs folder is at {cand.relative_to(base)} — "
                      f"not at briefs/ — move it back when convenient", file=sys.stderr)
                return cand
    return None


def drive_link(p: Path | None) -> str | None:
    """The Google Drive web link for a file or folder on the mount, read off
    the id Drive for desktop keeps on it. None off the mount."""
    if not p or not Path(p).exists():
        return None
    try:
        out = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", str(p)],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    i = out.stdout.strip()
    if out.returncode or not re.match(r"^[A-Za-z0-9_-]{10,}$", i):
        return None
    return f"https://drive.google.com/drive/folders/{i}" if Path(p).is_dir() else f"https://drive.google.com/file/d/{i}/view"


def link(label: str, p: Path | None, rel: Path | None = None) -> str:
    u = drive_link(p)
    if u:
        return f"[{label}]({u})"
    if p and rel:
        try:
            return f"{label} `{Path(p).relative_to(rel)}`"
        except ValueError:
            pass
    return label


def is_work(f: Path) -> bool:
    return f.is_file() and f.suffix.lower() in MEDIA and not any(w in f.name.lower() for w in NOT_WORK)


def work_files(folder: Path) -> list[Path]:
    return sorted(f for f in folder.rglob("*") if is_work(f) and not any(p.startswith(".") for p in f.parts))


# ------------------------------------------------------------ brief numbers --
def norm(s: str) -> str:
    """A name as words: lowercase, apostrophes dropped, everything else a hyphen."""
    s = re.sub(r"['’]", "", str(s or "").lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def strip_pkg(name: str) -> str:
    n = re.sub(r"\.(zip|md|json)$", "", name, flags=re.I)
    for s in PACKAGE_SUFFIXES:
        if n.lower().endswith(s):
            n = n[: -len(s)]
    return n


def code_of(name: str) -> str | None:
    """The code at the front of a name — `ab-02` of `AB-02 The Hen's Coat`,
    `kq07` of `kq07-premiere-handoff` — when there is one (it carries a digit)."""
    t = norm(strip_pkg(name)).split("-")
    if t and re.search(r"\d", t[0]):
        return t[0]
    if len(t) > 1 and re.search(r"\d", t[1]):
        return f"{t[0]}-{t[1]}"
    return None


def loose_match(a: str, b: str) -> bool:
    """Two names of the same brief without a number to go by: the same code
    at the front, or the same words (small words dropped), or one the start
    of the other."""
    ca, cb = code_of(a), code_of(b)
    if ca and cb:
        return ca == cb
    wa = [w for w in norm(strip_pkg(a)).split("-") if w and w not in STOP]
    wb = [w for w in norm(strip_pkg(b)).split("-") if w and w not in STOP]
    if not wa or not wb:
        return False
    sa, sb = "-".join(wa), "-".join(wb)
    return sa == sb or sa.startswith(sb + "-") or sb.startswith(sa + "-")


WORKSPACE = Path(os.environ.get("AI_WORKSPACE", Path.home() / "Projects/ai-workspace"))


class Briefs:
    """Brief numbers, looked up in the private workspace's naming tool. With
    no workspace on this computer every lookup is None and rows fall back to
    their names — the queue still builds."""

    def __init__(self, ws: Path | None = None):
        self.ws = Path(ws or WORKSPACE)
        self.N = None
        f = self.ws / "components/naming/names.py"
        if f.is_file():
            try:
                sys.path.insert(0, str(f.parent))
                spec = importlib.util.spec_from_file_location("ws_names", f)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                self.N = mod
            except Exception as e:  # a broken naming tool must not stop the queue
                print(f"note: brief numbers unavailable — {e}", file=sys.stderr)
        self._reg = {}

    def register(self, brand):
        if brand not in self._reg:
            try:
                self._reg[brand] = self.N.register_rows(brand) if self.N else []
            except Exception:
                self._reg[brand] = []
        return self._reg[brand]

    def by_run(self, brand, name):
        """A register brief whose run folder is this name (or starts with it)."""
        n = norm(strip_pkg(name))
        for r in self.register(brand):
            if r.get("_table") != "briefs" or not r.get("run"):
                continue
            base = norm(Path(str(r["run"])).name)
            if n and (base == n or base.startswith(n + "-") or n.startswith(base + "-")):
                return r
        return None

    def _finish(self, brand, cand, name, reg=None):
        N = self.N
        num = cand.get("brief")
        reg = reg or cand.get("register")
        if not num and not reg:
            reg = self.by_run(brand, name)
        if not num and reg:
            num = reg.get("brief") or N.brief_id(reg.get("key"))
        product = cand.get("product") or (N.slug(reg.get("product")) if reg and reg.get("product") else None)
        old = []
        hdr = cand.get("header") or {}
        alias = next((a for a in hdr.get("aliases") or [] if a != a.lower()), None)
        c = code_of(name)
        if alias:
            old.append(alias)
        elif c and not re.match(r"^(p\d{3}|brief-\d{4})$", c):
            old.append(c)
        elif not c and name and not N.parse_short(name) and not re.search(r"brief-\d{4}|\bp\d{3}\b", norm(name)):
            old.append(norm(strip_pkg(name)))
        if reg and re.match(r"^p\d{3}$", str(reg.get("key") or "")):
            old.append(reg["key"])
        elif num and not cand.get("per_product") and not reg:
            old.append(N.brief_code(num))
        return {"product": product, "brief": num, "old": list(dict.fromkeys(o for o in old if o)),
                "key": (product or "", num) if num else None}

    def identify(self, brand, *names, product=None):
        """{product, brief, old, key} for the first name that resolves, else None."""
        if not self.N:
            return None
        for name in names:
            if not name:
                continue
            try:
                hit = self._one(brand, str(name), product)
            except Exception:
                hit = None
            if hit and hit.get("brief"):
                return hit
        return None

    def _one(self, brand, name, product=None):
        N = self.N
        stem = strip_pkg(Path(name).name)
        d = N.parse_short(stem)
        if d and d.get("brief") not in (None, "none"):
            return self._pick(brand, d["brief"], d["product"], stem)
        low = norm(stem)
        t = low.split("-")
        tries = [stem.lower(), low] + ["-".join(t[:k]) for k in range(1, min(3, len(t)) + 1)] \
            + ["".join(t[:k]) for k in range(2, min(3, len(t)) + 1)]
        m = re.search(r"brief-?0*(\d{1,4})", low) or re.search(r"(?:^|-)p0*(\d{2,4})(?:-|$)", low)
        if m:
            tries.insert(0, f"brief-{int(m.group(1)):04d}")
        for q in dict.fromkeys(x for x in tries if x):
            hit = self._pick(brand, q, product, stem)
            if hit:
                return hit
        reg = self.by_run(brand, stem)
        if reg:
            return self._finish(brand, {"brief": None, "product": None}, stem, reg)
        return None

    def _pick(self, brand, q, product, name):
        N = self.N
        c = N.brief_candidates(brand, q, product)
        if len(c) > 1:
            # a product named in the name picks between briefs that share the number
            low = norm(name)
            c = [x for x in c if x.get("product") and x["product"] in low] or c
        if len(c) != 1:
            return None
        return self._finish(brand, c[0], name)


# ------------------------------------------------------------- the folders --
def brief_name(p: Path) -> str:
    return strip_pkg(p.name) if (p.suffix.lower() in PACKAGE_EXT or p.is_dir()) else p.name


def packages(folder: Path) -> list[dict]:
    """Every brief package under the briefs folder: a zip, or a folder holding
    a handoff. `claims/`, `delivered/` and dotfiles are not packages."""
    out = []
    for sub in sorted(folder.iterdir()):
        if sub.name.startswith(".") or sub.name in ("claims", "delivered") or sub.name.startswith("QUEUE"):
            continue
        if sub.is_file() and sub.suffix.lower() in PACKAGE_EXT:
            out.append({"brief": brief_name(sub), "type": "video", "package": sub.name, "path": sub,
                        "mtime": sub.stat().st_mtime})
        elif sub.is_dir():
            kind = TYPE_BY_FOLDER.get(sub.name.lower())
            kids = [k for k in sorted(sub.iterdir()) if not k.name.startswith(".")]
            if kind:
                for k in kids:
                    if k.is_file() and k.suffix.lower() in PACKAGE_EXT or k.is_dir():
                        out.append({"brief": brief_name(k), "type": kind, "package": f"{sub.name}/{k.name}",
                                    "path": k, "mtime": k.stat().st_mtime})
            elif any(k.name.lower().endswith(("-handoff.md", "editor-pack.md", "brief.md")) for k in kids):
                out.append({"brief": brief_name(sub), "type": "video", "package": sub.name + "/", "path": sub,
                            "mtime": sub.stat().st_mtime})
    return out


def claims(folder: Path) -> dict[str, str]:
    d = folder / "claims"
    out = {}
    if d.is_dir():
        for f in d.iterdir():
            m = re.match(r"^(.*?)\s+[—–-]\s+(.+?)(\.\w+)?$", f.name)
            if m:
                out[m.group(1).strip()] = m.group(2).strip()
    return out


def deliveries(folder: Path) -> list[dict]:
    """Every folder in briefs/delivered/ that holds files, with every name it
    has had: its own, naming.json `folder_was`, and the brief naming.json names."""
    d = folder / "delivered"
    out = []
    if not d.is_dir():
        return out
    for sub in sorted(d.iterdir()):
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        files = [f for f in sorted(sub.iterdir()) if not f.name.startswith(".")]
        if not files:
            continue
        nj = {}
        if (sub / "naming.json").is_file():
            try:
                nj = json.loads((sub / "naming.json").read_text())
            except json.JSONDecodeError:
                nj = {}
        out.append({"folder": sub, "name": sub.name, "was": nj.get("folder_was"), "brief": nj.get("brief"),
                    "unit": nj.get("unit"), "work": work_files(sub), "files": [f.name for f in files]})
    return out


def _who(x) -> str:
    if isinstance(x, dict):
        return x.get("name") or x.get("handle") or x.get("id") or ""
    return str(x or "")


def cards(brand: str) -> list[dict]:
    """Every approval card of the brand: meta/<brand>/<state>/<lane>/<ad>/card.json."""
    out = []
    base = meta_root() / brand
    for state, label in CARD_STATES.items():
        for lane_dir in sorted((base / state).glob("*")) if (base / state).is_dir() else []:
            if not lane_dir.is_dir():
                continue
            for ad in sorted(lane_dir.iterdir()):
                f = ad / "card.json"
                if not f.is_file():
                    continue
                try:
                    c = json.loads(f.read_text())
                except json.JSONDecodeError:
                    continue
                out.append({"state": label, "lane": lane_dir.name, "folder": ad, "card": c,
                            "ad": c.get("ad_name") or ad.name,
                            "note": (c.get("approval") or {}).get("note") or "",
                            "ad_ids": sum(1 for m in c.get("meta") or [] if m.get("ad_id")),
                            "run": (c.get("made_by") or {}).get("run") or "",
                            "creator": _who((c.get("made_by") or {}).get("creator"))})
    return out


def handoffs(brand: str) -> list[dict]:
    """Role hand-off folders for this brand: one entry per brief in each."""
    out = []
    for role, kind in HANDOFF_ROLES.items():
        base = handoffs_root() / role / brand
        if not base.is_dir():
            continue
        for folder in sorted(p for p in base.iterdir() if (p / "manifest.json").is_file()):
            try:
                m = json.loads((folder / "manifest.json").read_text())
            except json.JSONDecodeError:
                continue
            who = m.get("creator") or {}
            sent = bool(who.get("sent") or m.get("sent"))
            back = work_files(folder / "returned") if (folder / "returned").is_dir() else []
            for b in m.get("briefs") or []:
                bid = b.get("id") or b.get("old_code")
                if not bid:
                    continue
                out.append({"type": kind, "folder": folder, "brief": bid, "old": b.get("old_code"),
                            "sent": sent, "who": who.get("name") or who.get("handle") or "",
                            "returned": back, "mtime": (folder / "manifest.json").stat().st_mtime})
    return out


def load_meta(folder: Path) -> dict:
    p = folder / "queue.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except json.JSONDecodeError:
        print(f"queue.json unreadable at {p} — starting from empty, the old one is kept as queue.json.bad",
              file=sys.stderr)
        p.rename(p.with_suffix(".json.bad"))
        return {}


# --------------------------------------------------------------- the build --
def _label(ident, fallback):
    if ident and ident.get("brief"):
        return f"{ident['product'] or 'no product'} {ident['brief']}"
    return "no number yet"


def build(brand: str, write: bool = True, briefs: Briefs | None = None) -> list[dict]:
    folder = briefs_folder(brand)
    if not folder:
        print(f"{brand}: no briefs folder under {brands_root() / brand}", file=sys.stderr)
        return []
    B = briefs or Briefs()
    meta = load_meta(folder)
    hand = meta.get("briefs", {})
    cl = claims(folder)
    dl = deliveries(folder)
    cds = cards(brand)
    rows = []

    def new_row(name, kind, ident, package, path, mtime, hkey):
        h = hand.get(hkey, {})
        return {"name": name, "type": kind, "for": FOR[kind], "ident": ident, "key": (ident or {}).get("key"),
                "label": _label(ident, name), "old": (ident or {}).get("old") or [name],
                "package": package, "package_path": path, "mtime": mtime, "hkey": hkey,
                "who": h.get("who", ""), "bounty": h.get("bounty", ""), "due": h.get("due", ""),
                "note": h.get("note", ""), "paid": bool(h.get("paid")),
                "claimed": False, "delivered": [], "returned": [], "cards": []}

    for pk in sorted(packages(folder), key=lambda r: -r["mtime"]):
        ident = B.identify(brand, pk["brief"], pk["path"].name)
        r = new_row(pk["brief"], pk["type"], ident, pk["package"], pk["path"], pk["mtime"], pk["brief"])
        if not ident:
            r["old"] = [code_of(pk["brief"]) or pk["brief"]]
        rows.append(r)
    for ho in handoffs(brand):
        ident = B.identify(brand, ho["brief"], ho["old"])
        hkey = f"{ho['folder'].name}/{ho['brief']}"
        r = new_row(ho["brief"], ho["type"], ident, f"{ho['folder'].parent.parent.name}/{brand}/{ho['folder'].name}/",
                    ho["folder"], ho["mtime"], hkey)
        r["handoff"] = True
        r["claimed"] = ho["sent"]
        r["who"] = r["who"] or ho["who"]
        r["returned"] = ho["returned"]
        rows.append(r)

    def same(r, key, names):
        if key and r["key"]:
            return key == r["key"]
        return any(n and loose_match(r["name"], n) for n in names)

    # claims: `<brief> — <name>`, the brief in any spelling
    for text, who in cl.items():
        ident = B.identify(brand, text)
        for r in rows:
            if not r.get("handoff") and same(r, (ident or {}).get("key"), [text]):
                r["claimed"], r["who"] = True, who

    # deliveries: matched by number, else by any name the folder has had
    loose_dl = []
    for d in dl:
        prod = (B.N.parse_short(d["unit"] or d["name"]) or {}).get("product") if B.N else None
        ident = B.identify(brand, d["brief"], d["unit"], d["name"], d["was"], product=prod)
        d["key"] = (ident or {}).get("key")
        d["ident"] = ident
        hit = [r for r in rows if not r.get("handoff") and same(r, d["key"], [d["name"], d["was"]])]
        for r in hit[:1]:
            r["delivered"].append(d)
        if not hit:
            loose_dl.append(d)

    # cards: matched by number, else through the delivery folder they came from
    loose_cards = []
    for c in cds:
        ident = B.identify(brand, c["ad"], c["card"].get("brief_id"), product=c["card"].get("product"))
        key = (ident or {}).get("key")
        run = Path(c["run"]).name if c["run"] else ""
        want = LANE_TYPE.get(c["lane"], "video")
        cand = [r for r in rows if (key and r["key"] == key)
                or any(d["name"] in (run, c["ad"]) for d in r["delivered"])]
        cand.sort(key=lambda r: (r["type"] != want, bool(r.get("handoff")) != (want == "creator")))
        if cand:
            cand[0]["cards"].append(c)
        else:
            c["ident"] = ident
            loose_cards.append(c)

    # work that reached a delivery folder or a card with no package here: its own row
    for d in loose_dl:
        r = new_row(d["was"] or d["name"], "video" if any(f.suffix.lower() in (".mp4", ".mov", ".m4v") for f in d["work"]) else "image",
                    d["ident"], "", None, d["folder"].stat().st_mtime, d["name"])
        r["delivered"].append(d)
        rows.append(r)
    for c in loose_cards:
        k = (c.get("ident") or {}).get("key")
        r = next((x for x in rows if x["package"] == "" and k and x["key"] == k), None)
        if not r:
            kind = LANE_TYPE.get(c["lane"], "video")
            r = new_row(c["ad"], kind, c.get("ident"), "", None, c["folder"].stat().st_mtime, c["ad"])
            r["who"] = r["who"] or (c["creator"] or "")
            rows.append(r)
        r["cards"].append(c)

    for r in rows:
        r["status"] = state(r)
        r["status_text"] = r["status"]
        if r["status"] == "Sent back":
            notes = [c["note"] for c in r["cards"] if c["state"] == "Sent back" and c["note"]]
            r["status_text"] = "Sent back — " + (" / ".join(notes) if notes else "no note")
    rows.sort(key=lambda r: (ORDER.index(r["status"]), -r["mtime"]))

    if write:
        (folder / "QUEUE.md").write_text(render(brand, rows, folder))
        meta.setdefault("briefs", {})
        for r in rows:
            if r["package"]:
                meta["briefs"].setdefault(r["hkey"], {})
        meta["built"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        (folder / "queue.json").write_text(json.dumps(meta, indent=2))
        # keep the folders the skills write into, so the first claim never fails on a missing folder
        (folder / "claims").mkdir(exist_ok=True)
        (folder / "delivered").mkdir(exist_ok=True)
    return rows


def state(r: dict) -> str:
    if r["cards"]:
        return min((c["state"] for c in r["cards"]), key=CARD_PRIORITY.index)
    if any(d["work"] or d["files"] for d in r["delivered"]) or r["returned"]:
        return "Delivered"
    if r["claimed"]:
        return "Claimed"
    return "Open"


def _cell(s: str) -> str:
    return str(s or "").replace("|", "/").replace("\n", " ")


def render(brand: str, rows: list[dict], folder: Path) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sa = shared_assets()
    L = [f"# Work queue — {brand}", "",
         f"Built {now} from the folders. Rebuilt every hour. Nobody edits this table by hand.", "",
         "States: **Open** (package here) · **Claimed** (`claims/<brief> — <name>`) · **Delivered** "
         "(files in `delivered/`) · **In check** · **Approved** · **Live** (Damon's approval page and Meta) · "
         "**Sent back** (back to the same person, with Damon's note).", "",
         "| # | Brief | Old code | For | State | Who | Package | Delivered | Check / live | Bounty | Due | Note |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        pkg = link("hand-off folder" if r.get("handoff") else "package", r["package_path"], folder) if r["package"] else "—"
        dl = []
        for d in r["delivered"]:
            n = len(d["work"]) or len(d["files"])
            dl.append(link(f"{n} file{'s' if n != 1 else ''}", d["folder"], folder))
        if r["returned"]:
            dl.append(link(f"{len(r['returned'])} back", r["package_path"] / "returned" if r["package_path"] else None))
        if not dl:
            for c in r["cards"]:
                p = Path(c["run"]) if c["run"] else None
                n = len(c["card"].get("media") or [])
                dl.append(link(f"{n} file{'s' if n != 1 else ''}", p if p and p.exists() else None))
        chk = []
        for c in r["cards"]:
            t = c["state"] + (f" · {c['ad_ids']} Meta ad id{'s' if c['ad_ids'] != 1 else ''}" if c["state"] == "Live" else "")
            chk.append(link(t, c["folder"], sa))
        note = r["note"] + (" · paid" if r["paid"] else "")
        L.append(f"| {i} | {r['label']} | {_cell(' · '.join(r['old']))} | {r['for']} | **{_cell(r['status_text'])}** | "
                 f"{_cell(r['who']) or '—'} | {pkg} | {', '.join(dl) or '—'} | {', '.join(chk) or '—'} | "
                 f"{_cell(r['bounty']) or '—'} | {_cell(r['due']) or '—'} | {_cell(note)} |")
    if not rows:
        L.append("| — | nothing waiting | | | | | | | | | | |")
    nonum = [r for r in rows if not r["key"]]
    if nonum:
        L += ["", "## No number yet", ""]
        L += [f"- {r['for']}: `{r['name']}`" for r in nonum]
    L += ["", "## How to take one", "",
          "- **Video editor or graphic designer:** in Higgsfield, say **\"pull briefs for "
          f"{brand}\"**. It shows the rows that are yours (video rows for editors, image and carousel rows "
          "for designers), claims one and lays it out.",
          "- **Finished?** Say **\"deliver\"**. Your files go into `delivered/` here under the brief's name. "
          "You never name a file.",
          "- **Creator:** your folder comes from the creator manager. Put your footage in its `returned/` folder.",
          "- **Sent back?** The note is in the row. It comes back to the same person — fix it and say "
          "**\"deliver\"** again.", "",
          f"Folder: `Shared Assets/{folder.relative_to(sa) if folder.is_relative_to(sa) else folder}`", ""]
    return "\n".join(L)


# --------------------------------------------------------------- shipping --
PACK_FILES = ("EDITOR-PACK.md", "editor-pack.md")


def finished_runs() -> list[tuple[str, Path]]:
    """(brand, run folder) for every run in the private workspace whose pack
    passed its gates. The pack file exists only when `run.py pack` cleared
    every gate, so its presence is the whole test."""
    out = []
    for machine in sorted((WORKSPACE / "runs").glob("*")):
        if not machine.is_dir():
            continue
        for brand in sorted(machine.iterdir()):
            if not brand.is_dir() or brand.name.startswith((".", "_")):
                continue
            for run in sorted(brand.iterdir()):
                if run.is_dir() and any((run / "deliverable" / f).exists() for f in PACK_FILES):
                    out.append((brand.name, run))
    return out


def _already(folder: Path, name: str) -> bool:
    have = {r["brief"] for r in packages(folder)}
    # a hand-shipped zip is often the run's short name ("tide" for
    # "tide-song-…"); either one being a prefix of the other is the same brief
    return any(name == e or name.startswith(e + "-") or e.startswith(name + "-") for e in have)


def ship(run: Path, brand: str, dry: bool = False) -> Path | None:
    """Zip a finished run's deliverable and put it in the brand's briefs folder
    on Drive. Never twice: a brief already on the queue under the same name is
    left alone, so a re-run never duplicates a row or overwrites what an
    editor has claimed."""
    import shutil, tempfile
    folder = briefs_folder(brand)
    if not folder:
        print(f"{brand}: no briefs folder on Drive — make brands/{brand}/briefs first", file=sys.stderr)
        return None
    name = run.name
    if _already(folder, name):
        return None
    dest_dir = folder / "ai-video-production"
    dest = dest_dir / f"{name}-editor-handoff.zip"
    if dry:
        print(f"would ship {brand}/{name} → {dest.relative_to(folder)}")
        return dest
    src = run / "deliverable"
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / name
        shutil.copytree(src, base / name)
        for extra in run.glob("*-handoff.md"):
            shutil.copy2(extra, base / name / extra.name)
        for extra in run.glob("*brief*.md"):
            shutil.copy2(extra, base / name / extra.name)
        z = shutil.make_archive(str(Path(td) / name), "zip", base)
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(z, dest)
    print(f"shipped {brand}/{name} → Shared Assets/brands/{brand}/{dest.relative_to(folder)}")
    return dest


def register_file() -> Path | None:
    for f in (WORKSPACE / "components/image-teardown/briefs.json", WORKSPACE / "lab/damon/image-teardown/briefs.json"):
        if f.is_file():
            return f
    return None


def ready_design_briefs() -> list[dict]:
    """Image and carousel briefs ready to make: register rows marked approved
    (for-review → approved → in-production). Video, email, page and creator
    lanes are not designer work and are left out."""
    f = register_file()
    if not f:
        return []
    try:
        reg = json.loads(f.read_text()).get("briefs", {})
    except json.JSONDecodeError:
        return []
    out = []
    for key, r in sorted(reg.items()):
        if not isinstance(r, dict) or r.get("status") != "approved" or not r.get("brand"):
            continue
        typ, lane = str(r.get("type") or ""), r.get("lane")
        if typ.startswith("sequence"):
            kind = "carousel"
        elif lane in (None, "image-teardown", "image-production") and (not typ or typ.startswith("image")):
            kind = "image"
        else:
            continue
        out.append({**r, "key": key, "kind": kind, "root": f.parent})
    return out


def ship_design(rec: dict, dry: bool = False) -> Path | None:
    """One image or carousel brief → `briefs/image/<brief>.zip` (or carousel/):
    its register record, its worksheet and prompts, its brief page, and the
    run's written stages. Never twice."""
    import shutil, tempfile
    brand = rec["brand"]
    folder = briefs_folder(brand)
    if not folder:
        return None
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"{rec['key']}-{rec['run']}" if rec.get("run") else rec["key"])
    if _already(folder, name) or _already(folder, rec["key"]):
        return None
    dest_dir = folder / rec["kind"]
    dest = dest_dir / f"{name}.zip"
    if dry:
        print(f"would ship {brand}/{rec['key']} → {dest.relative_to(folder)}")
        return dest
    root = rec["root"]
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / name / name
        base.mkdir(parents=True)
        (base / "brief.json").write_text(json.dumps({k: v for k, v in rec.items() if k not in ("root",)},
                                                    indent=1, ensure_ascii=False, default=str))
        ws = root / str(rec.get("worksheet") or "")
        if rec.get("worksheet") and ws.is_dir():
            shutil.copytree(ws, base / "worksheet")
        page = root / "briefs" / f"{rec['key']}.html"
        if page.is_file():
            shutil.copy2(page, base / "brief.html")
        if rec.get("run"):
            for runs in (WORKSPACE / "runs/image-teardown" / brand, root / "runs"):
                rd = runs / rec["run"]
                if rd.is_dir():
                    (base / "run").mkdir(exist_ok=True)
                    for f in sorted(rd.iterdir()):
                        if f.is_file() and f.suffix.lower() in (".md", ".json"):
                            shutil.copy2(f, base / "run" / f.name)
                    if (rd / "deliverable").is_dir():
                        shutil.copytree(rd / "deliverable", base / "run" / "deliverable")
                    break
        z = shutil.make_archive(str(Path(td) / name), "zip", Path(td) / name)
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(z, dest)
    print(f"shipped {brand}/{rec['key']} → Shared Assets/brands/{brand}/{dest.relative_to(folder)}")
    return dest


def cmd_ship(a):
    if a.auto:
        n, touched = 0, set()
        for brand, run in finished_runs():
            if ship(run, brand, dry=a.dry_run):
                n += 1
                touched.add(brand)
        for rec in ready_design_briefs():
            if ship_design(rec, dry=a.dry_run):
                n += 1
                touched.add(rec["brand"])
        if n and not a.dry_run:
            for brand in touched:
                if briefs_folder(brand):
                    build(brand)
        print(f"auto-ship: {n} new package(s)")
        return
    run = Path(a.run).expanduser().resolve()
    if not any((run / "deliverable" / f).exists() for f in PACK_FILES):
        sys.exit(f"{run} has no deliverable/EDITOR-PACK.md — the pack has not cleared its gates, nothing ships")
    if ship(run, a.brand, dry=a.dry_run) and not a.dry_run:
        build(a.brand)


def cmd_set(a):
    folder = briefs_folder(a.brand)
    if not folder:
        sys.exit(f"{a.brand}: no briefs folder")
    meta = load_meta(folder)
    row = meta.setdefault("briefs", {}).setdefault(a.brief, {})
    for kv in a.fields:
        k, _, v = kv.partition("=")
        if k == "paid":
            row[k] = v.lower() in ("1", "true", "yes")
        else:
            row[k] = v
    (folder / "queue.json").write_text(json.dumps(meta, indent=2))
    build(a.brand)
    print(f"{a.brand}/{a.brief}: " + ", ".join(f"{k}={v}" for k, v in row.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--brand"); b.add_argument("--all", action="store_true")
    s = sub.add_parser("show"); s.add_argument("--brand", required=True)
    st = sub.add_parser("set"); st.add_argument("--brand", required=True); st.add_argument("brief"); st.add_argument("fields", nargs="+")
    sh = sub.add_parser("ship"); sh.add_argument("run", nargs="?"); sh.add_argument("--brand"); sh.add_argument("--auto", action="store_true"); sh.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.cmd == "set":
        return cmd_set(a)
    if a.cmd == "ship":
        if not a.auto and not (a.run and a.brand):
            sys.exit("ship <run-folder> --brand <brand>, or ship --auto")
        return cmd_ship(a)
    if a.cmd == "show":
        f = briefs_folder(a.brand)
        print((f / "QUEUE.md").read_text() if f and (f / "QUEUE.md").exists() else f"{a.brand}: no queue yet")
        return
    brands = [a.brand] if a.brand else [p.name for p in sorted(brands_root().iterdir())
                                        if p.is_dir() and not p.name.startswith(".") and briefs_folder(p.name)]
    if not brands:
        sys.exit("say --brand <brand> or --all")
    B = Briefs()
    for br in brands:
        rows = build(br, briefs=B)
        counts = {}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print(f"{br}: {len(rows)} row(s) — " + (", ".join(f"{k} {v}" for k, v in counts.items()) or "none"))


if __name__ == "__main__":
    main()
