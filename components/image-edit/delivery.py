#!/usr/bin/env python3
"""delivery — check for new deliveries from the roles that finish ads outside the chain, match each file to its
brief, bring it into the repo at the same path, and put it on the Meta approval page with one press.

    delivery.py --brand <b>                         what is new from every role since the last check; brings it in
    delivery.py --brand <b> --role <role>           one role only (a key under `roles` in delivery.json)
    delivery.py --brand <b> --dry-run               the same list, nothing downloaded or written
    delivery.py --brand <b> --send <role/brief key> that delivery onto one card in the Meta approval page's To check
                                                    (components/meta-upload to_check.py)

owner, 2026-10-27 (Tella): *"check for [the graphic designer's] recent delivery"*; *"for [the video editor] as well on
the video side, everything needs to run through the same process"*; then *"make this name agnostic. and the name of the folders need to be the
same for both repo and drive ... briefs should come from final stages of the chains, not some random set up."*

ONE PROCESS, NAMED BY ROLE. `delivery.json` `roles` says what each role delivers (`pictures` / `videos`) and which card
lane it takes; who fills a role today is the one place a person is named (`filled_by`). A brief's hand-off folder is
`runs/handoffs/<role>/<brand>/<brief key>/` in the repo and the same path under `Shared Assets/` on the Drive
(`Shared Assets/runs/handoffs/…`, since 2026-10-28; it was `Shared Assets/handoffs/…`): the packages put the brief there (image-edit handoff.py, video-edit editor_handoff.py) and the
person saves the finished files into its `returned/`. email_lead confirms the folders; until she does `state` says so and
every check says so.

Where it looks, in order (2026-10-28): the repo's own `runs/handoffs/<role>/<brand>/<brief key>/returned/` first (an agent's or another machine's
return already here, recorded with no Drive id), then the Drive's `Shared Assets/runs/handoffs/…/returned/`, then the
LEGACY places last (`legacy_folders` in delivery.json, the old `Shared Assets/handoffs/…`) so nothing in flight is lost;
one Drive id is read once, wherever it is listed. Every check that writes rebuilds `runs/handoffs/INDEX.md`
(handoff_index.py).

Only files inside a `returned/` are read; the package around it is never touched. The brief key in the folder name
decides the brief (the register's key, components/image-teardown briefs.json through tools/briefs.py; a folder named
only with a brief ID or an old code like `P167` is looked up by it). A file of the role's kind is brought by its Drive
id to the same path in the repo (`runs/handoffs/<role>/<brand>/<brief key>/returned/…`, media git-ignored), and the
brief's `delivery.json` beside `returned/` records it (repo-relative paths and {drive_id, label} only). A folder whose
name is not a brief of this brand is listed as NOT A BRIEF and left alone. The role's ledger
`runs/handoffs/<role>/<brand>/deliveries.json` holds every Drive id already brought in, so "new" means not seen before.

Drive is KEYS ONLY (GDRIVE_SA_KEY) through components/gdrive-creator, never a mount. Nothing on the Drive is deleted,
moved, renamed or written: the hand-off folders are only listed and read. Nothing is sent to anyone: `--send` files a
card for owner's approval and nothing goes live until he presses Approve on the approval page.
"""
import argparse
import hashlib
import math
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
from image_edit import paths as P  # noqa: E402

SETTING = HERE / "delivery.json"
KINDS = {"pictures": (".png", ".jpg", ".jpeg", ".webp"), "videos": (".mp4", ".mov", ".m4v")}
RECEIPTS = (".record.json", ".receipt.json", ".link.txt")   # Higgsfield's record or the maker's receipt beside a returned file (reference_check.py reads it)
TAG = re.compile(r"(?<![a-z0-9])(?:brief[\s_-]?(\d{3,4})|p(\d{3}))(?![0-9])", re.I)   # brief-0325, or the old P167


class Refused(Exception):
    pass


# ---------------------------------------------------------------- the setting, the register, the Drive
def setting(path=None):
    d = json.loads(Path(path or SETTING).read_text())
    for need in ("roles", "folder", "drive_root", "repo_root", "returned"):
        if not d.get(need):
            raise Refused(f"delivery.json has no {need}")
    for rid, r in d["roles"].items():
        for need in ("delivers", "lane"):
            if not r.get(need):
                raise Refused(f"delivery.json: {rid} has no {need}")
        if r["delivers"] not in KINDS:
            raise Refused(f"delivery.json: {rid} delivers {r['delivers']!r}; one of {', '.join(KINDS)}")
    return d


def role(rid, cfg=None):
    cfg = cfg or setting()
    if rid not in cfg["roles"]:
        raise Refused(f"no role {rid!r} in delivery.json; there is {', '.join(cfg['roles'])}")
    r = cfg["roles"][rid]
    return {"id": rid, **r, "state": r.get("state") or cfg.get("state"), "note": r.get("note") or cfg.get("note") or "",
            "words": rid.replace("-", " ")}


def _rel_folder(rid, brand, cfg):
    return cfg["folder"].replace("{role}", rid).replace("{brand}", brand).strip("/")


def place(rid, brand, cfg=None):
    """(the "Shared Assets/…" folder that holds this role's hand-offs for this brand, whether email_lead confirmed it). A
    brief's own folder is <that>/<brief key>/, and the finished files go in its returned/ (`returned_folder`)."""
    cfg = cfg or setting()
    r = role(rid, cfg)
    return f"{cfg['drive_root']}/{_drive_folder(rid, brand, cfg)}", r["state"] == "confirmed"


def _drive_folder(rid, brand, cfg):
    """The Drive copy is the repo path itself, runs/ included (2026-10-28):
    `drive_folder` when the setting names one, else <repo_root>/<folder>."""
    f = cfg.get("drive_folder") or f"{cfg['repo_root']}/{cfg['folder']}"
    return f.replace("{role}", rid).replace("{brand}", brand).strip("/")


def legacy_places(rid, brand, cfg=None):
    """The old Drive places for this role's returns, read LAST so nothing in flight is lost: `legacy_folders` in the
    setting, else the pre-2026-10-28 `Shared Assets/handoffs/<role>/<brand>`."""
    cfg = cfg or setting()
    olds = cfg.get("legacy_folders", ["handoffs/{role}/{brand}"])
    labels = [f"{cfg['drive_root']}/" + f.replace("{role}", rid).replace("{brand}", brand).strip("/") for f in olds]
    return [x for x in labels if x != place(rid, brand, cfg)[0]]


def returned_folder(rid, brand, key, cfg=None):
    """The Drive label where the finished files for one brief go."""
    cfg = cfg or setting()
    return f"{place(rid, brand, cfg)[0]}/{key}/{cfg['returned']}"


def repo_folder(rid, brand, cfg=None):
    """The same folder in the repo: the same words after the root."""
    cfg = cfg or setting()
    return P.repo() / cfg["repo_root"] / _rel_folder(rid, brand, cfg)


def folder_parts(label, cfg=None):
    cfg = cfg or setting()
    parts = [p for p in label.split("/") if p]
    if parts and parts[0] == cfg["drive_root"]:
        parts = parts[1:]
    return parts


_B = None


def briefs():
    """components/image-teardown tools/briefs.py, loaded by path under its own name (the register's one reader)."""
    global _B
    if _B is None:
        f = P.sibling("image-teardown", "tools", "briefs.py")
        spec = importlib.util.spec_from_file_location("it_briefs_register", f)
        _B = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_B)
    return _B


def _gdrive():
    folder = str(P.sibling("gdrive-creator"))
    if folder not in sys.path:
        sys.path.append(folder)
    from gdrive_creator import engine, reach
    return engine, reach


class Drive:
    """The two Drive calls this needs, through gdrive-creator by key: list and read. Tests hand in their own."""

    def __init__(self):
        self.E, self.R = _gdrive()
        if not self.E.has_key():
            raise Refused("the Drive key (GDRIVE_SA_KEY) is not on this machine, so the hand-off folders cannot be read")
        self.svc = self.E.service()

    def list(self, label, returned="returned"):
        """[("<brief key>/returned/<file>", drive id)] for every brief folder under the label: only the returned/
        folders are walked, never the packages around them, in batched questions (40 folders a question), so a role
        with a hundred hand-offs costs a handful of calls. None when the label is not there. Names only."""
        fid = self.E.folder_by_path(label, svc=self.svc)
        if not fid:
            return None
        briefs = {f["id"]: f["name"] for f in self._children([fid], folders=True)}
        todo = {f["id"]: briefs[f["parent"]] + "/" + returned
                for f in self._children(list(briefs), folders=True, name=returned)}
        out = []
        while todo:
            for f in self._children(list(todo), folders=False):
                out.append((f"{todo[f['parent']]}/{f['name']}", f["id"]))
            todo = {f["id"]: f"{todo[f['parent']]}/{f['name']}" for f in self._children(list(todo), folders=True)}
        return sorted(out)

    def _children(self, parents, folders, name=None):
        """Every child of these folders, through the svc seam (gdrive-creator's contract), 40 parents a question:
        [{id, name, parent}]. folders=True: folders only (named `name` if given); False: files only."""
        out, mime = [], self.E.FOLDER_MIME
        for i in range(0, len(parents), 40):
            chunk = parents[i:i + 40]
            q = "(" + " or ".join(f"'{p}' in parents" for p in chunk) + ") and trashed = false and mimeType "
            q += f"= '{mime}'" if folders else f"!= '{mime}'"
            if name:
                q += f" and name = '{self.E.esc(name)}'"
            token = None
            while True:
                # corpora=allDrives: without it an OR over several parents silently returns nothing from a shared
                # drive (2026-10-28: 18 returned files in Shared Assets listed as 0 when two hand-offs were asked at once)
                kw = dict(q=q, fields="nextPageToken, files(id,name,parents)", pageSize=1000, supportsAllDrives=True,
                          includeItemsFromAllDrives=True, corpora="allDrives")
                if token:
                    kw["pageToken"] = token
                r = self.svc.files().list(**kw).execute()
                for f in r.get("files") or []:
                    parent = next((x for x in f.get("parents") or [] if x in chunk), None)
                    if parent:
                        out.append({"id": f["id"], "name": f["name"], "parent": parent})
                token = r.get("nextPageToken")
                if not token:
                    break
        return out

    def get(self, drive_id, dest):
        return self.E.get_media(drive_id, str(dest), svc=self.svc)


# ---------------------------------------------------------------- matching
def tags_in(text):
    return sorted({f"brief-{int(m.group(1) or m.group(2)):04d}" for m in TAG.finditer(text or "")})


def brief_tag(name):
    """The one brief ID a folder name carries: (id, None) or (None, why)."""
    t = tags_in(name)
    if len(t) > 1:
        return None, f"two brief IDs in one name ({', '.join(t)})"
    return (t[0], None) if t else (None, "no brief ID in the folder's name")


def lookup(reg, brand, bid, name):
    """Which brief this ID names, given the folder name: ("ok", key, record) for a brief of this brand, or
    ("bad", None, why). One number can name briefs of two brands or two products (numbers count per brand AND
    product): the brand or product in the name decides."""
    low = name.lower()
    cands = [(k, r) for k, r in dict.items(reg["briefs"]) if isinstance(r, dict) and r.get("brief") == bid]
    for field in ("brand", "product"):
        if len(cands) > 1:
            named = [c for c in cands if c[1].get(field) and (str(c[1][field]).lower() in low or
                     (field == "product" and _same_product(str(c[1][field]).lower(), low, brand)))]
            cands = named or cands
    mine = [c for c in cands if c[1].get("brand") == brand]
    if not cands:
        return "bad", None, f"{bid} is not a brief in the register"
    if not mine:
        return "bad", None, f"{bid} is another brand's brief ({cands[0][1].get('brand')}), in the {brand} folder"
    if len(mine) > 1:
        prods = sorted({c[1].get("product") or "no product" for c in mine})
        return "bad", None, f"{bid} is used by more than one {brand} product ({', '.join(prods)}); use the brief key"
    return ("ok",) + mine[0]


def _same_product(product, low, brand):
    """The folder's product word and the register's are one product when one starts the other (the catalog name and
    the old handle: flex-face-brush / flex), so a folder matches its brief by brief NUMBER plus brand in either
    spelling (2026-10-28)."""
    m = re.match(re.escape(brand.lower()) + r"[_-](.+?)[_-]brief", low)
    word = m.group(1) if m else ""
    return bool(word) and (product.startswith(word + "-") or word.startswith(product + "-") or word == product)


def brief_of(reg, brand, name):
    """The brief a hand-off folder is for: its name is the register key (brand_product_brief-NNNN), else a brief ID
    or an old code in it. ("ok", key, record) or ("bad", None, why)."""
    rec = dict.get(reg["briefs"], name) or dict.get(reg["briefs"], name.lower())
    if isinstance(rec, dict):
        if rec.get("brand") != brand:
            return "bad", None, f"{name} is another brand's brief ({rec.get('brand')}), in the {brand} folder"
        return "ok", name.lower() if name.lower() in reg["briefs"] else name, rec
    bid, why = brief_tag(name)
    return ("bad", None, why) if not bid else lookup(reg, brand, bid, name)


# ---------------------------------------------------------------- the check
def _read(p, default):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _write(p, d):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    tmp.replace(p)


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(P.repo().resolve()))
    except ValueError:
        return str(p)


def check(brand, rid=None, dry_run=False, drive=None, reg=None, cfg=None):
    """Every role's new deliveries (or one role's), matched to briefs; brought in unless dry_run.
    Returns {"brand", "checked", "dry_run", "roles": [check_role(...) for each]}."""
    cfg = cfg or setting()
    ids = [rid] if rid else list(cfg["roles"])
    drive = drive or Drive()
    reg = reg or briefs().load()
    res = {"brand": brand, "checked": time.strftime("%Y-%m-%dT%H:%M"), "dry_run": bool(dry_run),
           "roles": [check_role(brand, role(i, cfg), dry_run, drive, reg, cfg) for i in ids]}
    if not dry_run:                                   # the front door, runs/handoffs/INDEX.md, after every check
        res["index"] = index_refresh(drive=isinstance(drive, Drive))
    return res


def index_refresh(drive=False):
    """runs/handoffs/INDEX.md + START-HERE.md rebuilt (handoff_index.py), on the Drive too when the real Drive was read
    (2026-10-28). Never stops the check."""
    import handoff_index as HI
    return HI.quiet_refresh(repo=P.repo(), drive=drive)


def check_role(brand, r, dry_run, drive, reg, cfg):
    """One role's hand-off folders for the brand: {"role", "words", "filled_by", "delivers", "lane", "folder",
    "confirmed", "note", "found", "new": [{brief, key, product, label, count, files}], "untagged": [{file, why, new}],
    "other", "already"}."""
    label, confirmed = place(r["id"], brand, cfg)
    at = time.strftime("%Y-%m-%dT%H:%M")
    out = {"role": r["id"], "words": r["words"], "filled_by": r.get("filled_by"), "delivers": r["delivers"],
           "lane": r["lane"], "folder": label, "confirmed": confirmed, "note": r["note"], "found": True, "new": [],
           "untagged": [], "other": [], "already": 0, "dry_run": bool(dry_run)}
    home = repo_folder(r["id"], brand, cfg)
    ledger = home / "deliveries.json"
    led = _read(ledger, {"brought": {}, "untagged": {}})
    groups = {}
    receipts = {}
    for rel in _repo_returns(home, r, cfg):                      # the repo's own returned/ first
        state, key, rec = brief_of(reg, brand, rel.split("/")[0])
        if state == "ok":
            groups.setdefault(rel.split("/")[0], (key, rec, []))[2].append((rel, None, None))
    listing, seen, found = [], set(), False
    for lab in [label] + legacy_places(r["id"], brand, cfg):   # then the Drive, the legacy places last
        got = drive.list(lab, cfg["returned"])
        found = found or got is not None
        for rel, fid in got or []:
            if fid not in seen:
                seen.add(fid)
                listing.append((rel, fid, lab))
        if got and lab != label:
            out.setdefault("legacy", []).append(lab)
    if not found and not groups:
        out["found"] = False
        return out
    for rel, fid, lab in listing:
        parts = rel.split("/")
        if len(parts) < 3 or parts[1] != cfg["returned"]:
            continue                                              # the package itself, never the delivery
        if rel.lower().endswith(RECEIPTS) or parts[-1] == "return-manifest.json":                        # a receipt rides along; never a delivery itself
            manifest = parts[-1] == "return-manifest.json"
            fresh = fid not in (led.get("manifests") or {}) if manifest else not home.joinpath(*parts).is_file()
            if fresh and brief_of(reg, brand, parts[0])[0] == "ok":
                receipts.setdefault(parts[0], []).append((rel, fid))
            continue
        if Path(rel).suffix.lower() not in KINDS[r["delivers"]]:
            out["other"].append(rel)
            continue
        if fid in led["brought"] or _taken_back(home, parts, cfg):
            out["already"] += 1
            continue
        state, key, rec = brief_of(reg, brand, parts[0])
        if state != "ok":
            out["untagged"].append({"file": rel, "why": rec, "new": fid not in led["untagged"]})
            led["untagged"].setdefault(fid, {"file": rel, "first_seen": at})
            continue
        led["untagged"].pop(fid, None)
        groups.setdefault(parts[0], (key, rec, []))[2].append((rel, fid, lab))
    for folder, (key, rec, files) in groups.items():
        row = {"brief": rec.get("brief") or key, "key": key, "product": rec.get("product"), "avatar": rec.get("avatar"),
               "label": f"{r['id']}/{folder}", "count": len(files), "files": [x for x, _, _ in files]}
        if not dry_run:
            row.update(_bring(brand, r, folder, key, rec, files, label, home, drive, led, at, cfg))
        out["new"].append(row)
    if not dry_run:
        _write(ledger, led)
        for folder, got in receipts.items():                      # receipts in beside their files
            for rel, fid in got:
                dest = home / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                drive.get(fid, dest)
                if Path(rel).name == "return-manifest.json":
                    led.setdefault("manifests", {})[fid] = {"file": rel, "brought": at}
        _write(ledger, led)
        for folder in sorted(set(groups) | set(receipts)):        # then the proof, per brief folder
            said = reference_check(home / folder)
            row = next((x for x in out["new"] if x["label"] == f"{r['id']}/{folder}"), None)
            if row is not None:
                row["reference_check"] = said
            else:
                out.setdefault("rechecked", []).append({"label": f"{r['id']}/{folder}", "reference_check": said})
    return out


def ingest_filming(folder, brand=None, dry_run=False):
    """Validate an explicit filming return and expose the existing video-edit kit seam.

    No Drive, generation or send. Identical validated manifests/media do not rewrite the kit.
    A changed accepted take requires a new manifest hash; stale evidence never passes.
    """
    folder = Path(folder).resolve()
    sheet = _read(folder / "run.json", {})
    if not isinstance(sheet, dict):
        raise Refused("filming assignment must be a JSON object")
    if sheet.get("packet_kind") != "filming-assignment" or sheet.get("production_route") not in ("creator", "founder"):
        raise Refused("this is not a creator/founder filming assignment")
    if brand and sheet.get("brand") != brand:
        raise Refused("filming assignment brand does not match --brand")
    if not sheet.get("execution_ready"):
        raise Refused("filming assignment is draft: " + "; ".join(sheet.get("gaps") or []))
    manifest = _read(folder / "returned/return-manifest.json", {})
    if not isinstance(manifest, dict) or not isinstance(manifest.get("takes"), list):
        raise Refused("filming return must be an object with a takes list")
    if manifest.get("schema") != "filming-return/v1" or manifest.get("brief_key") != sheet.get("brief_key") or manifest.get("production_route") != sheet.get("production_route"):
        raise Refused("return manifest schema, brief_key and production_route must match the assignment")
    expected = {(t["asset_id"], n): t for t in sheet["takes"] for n in range(1, t["expected_takes"] + 1)}
    seen, chosen, clips, evidence = set(), set(), [], []
    for take in manifest.get("takes") or []:
        if not isinstance(take, dict):
            raise Refused("each filming take must be a JSON object")
        key = (take.get("asset_id"), take.get("take"))
        if type(key[1]) is not int or key not in expected or key in seen:
            raise Refused("unknown or duplicate asset/take in return manifest: " + str(key))
        seen.add(key)
        name = take.get("file")
        if not isinstance(name, str) or Path(name).is_absolute():
            raise Refused("take file must be relative to returned/")
        src = (folder / "returned" / name).resolve()
        if (folder / "returned").resolve() not in src.parents or src.suffix.lower() not in KINDS["videos"] or not src.is_file():
            raise Refused("take file must exist inside returned/: " + str(name))
        content_hash = hashlib.sha256()
        with src.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                content_hash.update(chunk)
        digest = content_hash.hexdigest()
        if take.get("sha256") != digest:
            raise Refused("take SHA-256 does not match: " + name)
        evidence.append({"file": name, "sha256": digest})
        if take.get("accepted") is not True:
            continue
        if not str(take.get("reviewer") or "").strip() or take.get("roll") not in ("a", "b") or type(take.get("talks")) is not bool:
            raise Refused("accepted take needs reviewer, roll a/b and talks true/false: " + name)
        if take["talks"] and take["roll"] != "a":
            raise Refused("talking footage must carry A-roll sound: " + name)
        words = take.get("words") or []
        if not isinstance(words, list):
            raise Refused("timed transcript words must be a list: " + name)
        if take["talks"] and not words:
            raise Refused("accepted talking take needs timed transcript words: " + name)
        last = 0.0
        for w in words:
            try:
                start, end = float(w["start"]), float(w["end"])
                valid = math.isfinite(start) and math.isfinite(end) and start >= last and end > start and isinstance(w["text"], str) and bool(w["text"].strip())
            except (KeyError, TypeError, ValueError):
                valid = False
            if not valid:
                raise Refused("invalid timed transcript words: " + name)
            last = end
        chosen.add(key[0])
        clip = {"id": f"{key[0]}_take-{key[1]:02d}", "src": "returned/" + name,
                "scene": expected[key]["scene"], "roll": take["roll"], "talks": take["talks"],
                "approved": True, "words": words, "acceptance": {"reviewer": take["reviewer"], "sha256": digest}}
        if take.get("covers") is not None:
            clip["covers"] = take["covers"]
        clips.append(clip)
    if seen != set(expected):
        raise Refused("return manifest is missing expected raw takes: " + str(sorted(set(expected) - seen)))
    if chosen != {t["asset_id"] for t in sheet["takes"]}:
        raise Refused("each assigned asset needs at least one explicitly accepted take")
    if not any(c["roll"] == "a" and c["talks"] for c in clips):
        raise Refused("filming return has no talking A-roll; an approved sound/word-led kit is still required before edit")
    # Build timestamps and copied-folder metadata are not changes to the assignment.
    assignment = {k: sheet.get(k) for k in ("brief_key", "production_route", "takes", "execution_ready")}
    assignment["brief_sha256"] = hashlib.sha256((folder / "BRIEF.md").read_bytes()).hexdigest() if (folder / "BRIEF.md").is_file() else None
    fingerprint = hashlib.sha256(json.dumps({"manifest": manifest, "media": evidence, "assignment": assignment}, sort_keys=True).encode()).hexdigest()
    kit = {"brief_key": sheet["brief_key"], "brand": sheet["brand"], "production_route": sheet["production_route"],
           "clips": clips, "voice": None, "filming_return": {"schema": "filming-return/v1", "sha256": fingerprint}}
    old = _read(folder / "edit-kit.json", {})
    unchanged = old == kit
    result = {"state": "ready", "brief_key": sheet["brief_key"], "production_route": sheet["production_route"],
              "kit": "edit-kit.json", "clips": len(clips), "unchanged": unchanged, "dry_run": bool(dry_run),
              "next": "python3 components/video-edit/machine/run.py start <this-folder> --brand " + sheet["brand"] + " --label " + sheet["brief_key"] + " --dry-run"}
    if not dry_run and not unchanged:
        _write(folder / "edit-kit.json", kit)
        _write(folder / "filming-intake.json", {**result, "manifest_sha256": fingerprint})
    return result


def reference_check(folder):
    """reference_check.py on one hand-off folder after its files came in: the verdict line, or why it did not run.
    Never stops the bring-in."""
    if _read(Path(folder) / "run.json", {}).get("packet_kind") == "filming-assignment":
        try:
            result = ingest_filming(folder)
            return "filming return: edit kit ready" + (" (unchanged)" if result["unchanged"] else "")
        except Refused as e:
            return "filming return blocked: " + str(e)
    try:
        import reference_check as RC
        return RC.summary(RC.check(folder))
    except Exception as e:                                        # noqa: BLE001 — the bring-in is already done
        return f"not run: {type(e).__name__}: {str(e)[:160]}"


def _repo_returns(home, r, cfg):
    """"<brief key>/returned/<file>" for every file of the role's kind already in the repo's own returned/ that the
    brief's delivery.json does not record and the hand-off road's returned/index.json did not take back: a return that
    reached the repo first (2026-10-28)."""
    out = []
    for back in sorted(home.glob(f"*/{cfg['returned']}")) if home.is_dir() else []:
        known = {Path(f.get("file") or "").name for f in (_read(back.parent / "delivery.json", {}) or {}).get("files", [])}
        known |= {f.get("file") for f in _read(back / "index.json", {}).get("files") or [] if isinstance(f, dict)}
        for f in sorted(back.rglob("*")):
            if f.is_file() and f.suffix.lower() in KINDS[r["delivers"]] and f.name not in known:
                out.append(f.relative_to(home).as_posix())
    return out


def _repo_returns(home, r, cfg):
    """"<brief key>/returned/<file>" for every file of the role's kind already in the repo's own returned/ that the
    brief's delivery.json does not record and the hand-off road's returned/index.json did not take back: a return that
    reached the repo first (2026-10-28)."""
    out = []
    for back in sorted(home.glob(f"*/{cfg['returned']}")) if home.is_dir() else []:
        known = {Path(f.get("file") or "").name for f in (_read(back.parent / "delivery.json", {}) or {}).get("files", [])}
        known |= {f.get("file") for f in _read(back / "index.json", {}).get("files") or [] if isinstance(f, dict)}
        for f in sorted(back.rglob("*")):
            if f.is_file() and f.suffix.lower() in KINDS[r["delivers"]] and f.name not in known:
                out.append(f.relative_to(home).as_posix())
    return out


def _taken_back(home, parts, cfg):
    """Already in: the file is at the same path in the repo, or the hand-off road's own take-back recorded it in
    returned/index.json (an agent that worked a hand-off puts its result there itself; the check never brings it twice)."""
    if (home.joinpath(*parts)).is_file():
        return True
    idx = _read(home / parts[0] / cfg["returned"] / "index.json", {})
    return parts[-1] in {f.get("file") for f in idx.get("files") or [] if isinstance(f, dict)}


def _bring(brand, r, folder, key, rec, files, label, home, drive, led, at, cfg):
    """Read each file by id to the same path in the repo; record it beside returned/."""
    d = home / folder
    recf = d / "delivery.json"
    rd = _read(recf, None) or {"what": f"what the {r['words']} delivered for one brief, into its returned/",
                               "role": r["id"], "delivers": r["delivers"], "lane": r["lane"],
                               "brief": rec.get("brief") or key, "key": key, "brand": brand,
                               "product": rec.get("product"), "avatar": rec.get("avatar"), "run": rec.get("run"),
                               "state": "delivered", "files": []}
    taken = {f["file"]: f["drive_id"] for f in rd["files"]}
    for rel, fid, lab in files:
        if fid is None:                                                   # already in the repo: recorded, not read
            rd["files"] = [f for f in rd["files"] if f["file"] != _rel(home / rel)] + [{
                "name": Path(rel).name, "file": _rel(home / rel), "drive_id": None, "label": _rel(home / rel),
                "brought": at}]
            continue
        dest = home / rel
        n = 2
        while _rel(dest) in taken and taken[_rel(dest)] != fid:             # Drive allows two files of one name
            dest = home / str(Path(rel).with_name(f"{Path(rel).stem}-{n}{Path(rel).suffix}"))
            n += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        drive.get(fid, dest)
        taken[_rel(dest)] = fid
        rd["files"] = [f for f in rd["files"] if f["drive_id"] != fid] + [{
            "name": dest.name, "file": _rel(dest), "drive_id": fid, "label": f"{lab or label}/{rel}", "brought": at}]
        led["brought"][fid] = {"brief": rd["brief"], "key": key, "file": rel, "brought": at}
    rd["updated"] = at
    _write(recf, rd)
    return {"folder": _rel(d / cfg["returned"]), "brought": len(files), "total": len(rd["files"])}


def delivered(brand, cfg=None):
    """Every brief with a delivery brought in for this brand, every role, newest first: what the board lists."""
    cfg = cfg or setting()
    rows = []
    for rid in cfg["roles"]:
        home = repo_folder(rid, brand, cfg)
        for f in home.glob("*/delivery.json") if home.is_dir() else []:
            r = _read(f, None)
            if not r:
                continue
            rows.append({"role": rid, "delivers": r.get("delivers"), "brief": r.get("brief"), "key": r.get("key"),
                         "product": r.get("product"), "label": f"{rid}/{f.parent.name}",
                         "files": [str(P.repo() / x["file"]) for x in r.get("files", [])], "card": r.get("card"),
                         "updated": r.get("updated")})
    return sorted(rows, key=lambda x: x.get("updated") or "", reverse=True)


# ---------------------------------------------------------------- onto the Meta approval page
def send(brand, which, run=None, drive=None, cfg=None):
    """One card in the Meta approval page's To check holding this delivery's files, through components/meta-upload
    to_check.py (the one writer of cards), in the role's lane. `which` is the delivery's label (<role>/<brief key>)
    or its brief. A second send updates that card while it is still in To check."""
    cfg = cfg or setting()
    rows = [x for x in delivered(brand, cfg) if which in (x["label"], x["brief"], x["key"])]
    if not rows:
        raise Refused(f"no delivery brought in for {which} yet; check for new deliveries first")
    if len(rows) > 1:
        raise Refused(f"{which} has more than one delivery ({', '.join(x['label'] for x in rows)}); say which")
    row = rows[0]
    d = repo_folder(row["role"], brand, cfg) / row["label"].split("/", 1)[1]
    r = _read(d / "delivery.json", {})
    if _read(d / "run.json", {}).get("packet_kind") == "filming-assignment":
        raise Refused("raw filming takes are not finished ads; ingest-filming then video-edit before Meta delivery")
    contract_file = d / "DELIVERY-REQUIREMENTS.json"
    if row["role"] in ("video-editor", "graphic-designer"):
        import importlib.util
        spec = importlib.util.spec_from_file_location("briefs_delivery_submit", P.sibling("briefs", "delivery_contract.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plan = module.submit(d)
        return {"state": "1-check", "said": plan["state"], "name": plan["card"]["ad_name"], "revision_id": plan["card"].get("delivery", {}).get("revision_id")}
    media = []
    for f in r.get("files", []):
        p = P.repo() / f["file"]
        if not p.is_file() and not f.get("drive_id"):          # a repo-only return not on this machine
            continue
        if not p.is_file():                                    # another machine brought it in: read it back by id
            p.parent.mkdir(parents=True, exist_ok=True)
            (drive or Drive()).get(f["drive_id"], p)
        media.append(str(p))
    if not media:
        raise Refused(f"{which} has no delivered files on file")
    batch = (r.get("card") or {}).get("batch") or "batch-" + time.strftime("%Y-%m-%d") + "-a"
    cmd = [str(P.sibling("meta-upload", "to_check.py")), "--brand", brand, "--lane", r.get("lane") or "image",
           "--product", r.get("product") or "", "--brief", r.get("brief") or which, "--batch", batch,
           "--media"] + media + ["--tool", row["role"], "--run", _rel(d), "--replace"]
    if r.get("avatar"):
        cmd += ["--avatar", r["avatar"]]
    log = (run or _sh)(cmd)
    said = next((l for l in log.splitlines() if l.startswith(("REFUSED", "filed", "replaced", "skipped"))), "")
    if not said.startswith(("filed", "replaced")):
        raise Refused(said or ("the card filer said nothing it did: " + log[-300:]))
    card = {"state": "1-check", "said": said.split()[0], "name": said.split()[-1].split("/")[-1], "batch": batch,
            "at": time.strftime("%Y-%m-%dT%H:%M"), "files": len(media)}
    r["card"] = card
    r["state"] = "on-the-approval-page"
    _write(d / "delivery.json", r)
    return card


def _sh(cmd, timeout=3600):
    p = subprocess.run([sys.executable] + cmd, cwd=str(P.repo()), capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise Refused(((p.stderr or "") + (p.stdout or "")).strip()[-600:] or "the card filer stopped")
    return p.stdout


# ---------------------------------------------------------------- the words a person reads
def say(res):
    lines = []
    for o in res["roles"]:
        who = f"the {o['words']}" + (f" ({o['filled_by']} today)" if o.get("filled_by") else "")
        lines.append(f"{who}, {o['delivers']}:")
        if not o["confirmed"]:
            lines.append(f"  folder {o['folder']}/<brief key>/returned (not confirmed yet: {o['note']})")
        if not o["found"]:
            lines.append(f"  no hand-off folder on the Drive yet ({o['folder']}).")
            continue
        if not o["new"] and not o["untagged"]:
            lines.append("  nothing new since the last check.")
        for n in o["new"]:
            where = f" -> {n['folder']}" if n.get("folder") else ""
            lines.append(f"  {n['brief']} ({n.get('product') or 'no product'}): {n['count']} new{where}")
            if n.get("reference_check"):
                lines.append(f"    reference check: {n['reference_check']} (REFERENCE-CHECK.md beside returned/)")
        for x in o.get("rechecked") or []:
            lines.append(f"  {x['label']}: new receipts; reference check: {x['reference_check']}")
        for u in o["untagged"]:
            lines.append(f"  NOT A BRIEF: {u['file']} ({u['why']})")
        for lab in o.get("legacy") or []:
            lines.append(f"  still found work in the OLD place {lab}: read it, but returns go in {o['folder']}/<brief key>/returned")
    if res["dry_run"]:
        lines.append("Dry run: nothing downloaded or written.")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--role")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--send", metavar="ROLE/BRIEF_KEY")
    ap.add_argument("--ingest-filming", metavar="FOLDER", help="validate local creator/founder takes and write edit-kit.json; no Drive")
    a = ap.parse_args(argv)
    try:
        if a.ingest_filming:
            print(json.dumps(ingest_filming(a.ingest_filming, a.brand, a.dry_run), indent=2))
        elif a.send:
            c = send(a.brand, a.send)
            print(f"{c['said']}: {c['files']} files on the Meta approval page, in To check ({c['name']})")
        else:
            print(say(check(a.brand, a.role, dry_run=a.dry_run)))
    except Refused as e:
        print(f"REFUSED: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
