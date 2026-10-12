#!/usr/bin/env python3
"""work_queue.py — one shared list of every ad on the video line, and who is working it.

Two (or more) computers run the song-ad / video line side by side: the owner's Mac and a
second video editor's own Mac (the owner, 2026-10-10: "I'm about to have a second video
editor pump stuff too so he'll have another computer"). Each machine sees its OWN runs
under runs/; neither sees the other's until it is pushed. This tool is the seam:

    python3 tools/video-production/machine/work_queue.py list [--brand B] [--all] [--json]
    python3 tools/video-production/machine/work_queue.py claim <brief> [--take-over]
    python3 tools/video-production/machine/work_queue.py progress <brief> [--stage S]
    python3 tools/video-production/machine/work_queue.py sync           # progress for every ad this machine holds
    python3 tools/video-production/machine/work_queue.py release <brief>
    python3 tools/video-production/machine/work_queue.py page           # the status page (HTML) for the owner

WHAT AN AD IS. One brief id (brief-0037). Its stage is the first of
song · b-roll · cut · hooks · card · done that is not finished yet, read from:
  - runs/video-production/<brand>/<label>/run.json (the song, the clips),
  - runs/video-edit/<brand>/<label>/ and its deliverable/versions-index.json (the cut, the hooks),
  - the Drive card folders, Shared Assets/meta/<brand>/<1-check|2-approved|3-live|sent-back>/video/*/card.json.
A format with no song skips the song stage. An ad another machine made, which this
machine has no run for, still shows: from its card on Drive and from the claim record.

WHO IS ON IT. Claims are records on the records plane, kind `video-queue`
(platform/data/kinds/video-queue.json), one append-only file per act under
platform/data/records/video-queue/, named <UTC>--<person>--<brief>.json — the same
shape and the same naming as every other record there. Current state is FOLDED, never
stored: the latest claim not followed by a release is the owner; the owner's latest
record is its last progress.

HOW BOTH MACHINES SEE THE SAME CLAIMS. A claim counts only once it is on origin/main.
The record is committed straight onto origin/main with git plumbing — a temporary
index, commit-tree on the fetched tip, push — so the working tree and the shared
index of a busy checkout are never touched, and other sessions' uncommitted work is
never staged. Git's own fast-forward check is the lock: if the other machine pushed
first, the push is refused, this tool fetches, re-reads the claims, and either
re-decides (refusing if the ad is now taken) or retries. Offline means NOT claimed:
nothing is written and it says so.

A STALE CLAIM is one whose owner filed nothing (claim or progress) for --stale-hours
(default 6, or VIDEO_QUEUE_STALE_HOURS). It can be taken over with --take-over; the
new claim names the claim it replaced.

WHO THIS MACHINE IS: VIDEO_QUEUE_MACHINE, else the host name. WHO IS AT IT:
VIDEO_QUEUE_PERSON, else the part of `git config user.email` before the @, else the
login name. No key is read; nothing is sent anywhere but this repo's own origin.
Output (the page) goes to runs/video-queue/_system/. Python 3.9.
"""
import argparse
import datetime as dt
import getpass
import html
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGES = ["song", "b-roll", "cut", "hooks", "card", "done"]
KIND = "video-queue"
RECORDS_REL = "platform/data/records/video-queue"
VIA = "video-queue/1"
CARD_STATES = ["1-check", "2-approved", "3-live", "sent-back"]
STALE_HOURS = 6.0
SLUG = re.compile(r"[^a-z0-9._-]+")


# ------------------------------------------------------------------ paths ---

def repo_root(start=None):
    """The workspace: AI_WORKSPACE when it holds brands/, else the first folder upward
    with components/ and brands/ (run-kit paths.repo(), same rule)."""
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    here = Path(start or __file__).resolve()
    for d in [here] + list(here.parents):
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise SystemExit("work_queue: no workspace found upward of %s" % here)


def drive_root(repo):
    """Shared Assets on this machine's Drive, through brandpath's one helper; None if not mounted.
    VIDEO_QUEUE_DRIVE names it outright (tests, or a mount the helper cannot see)."""
    env = os.environ.get("VIDEO_QUEUE_DRIVE")
    if env:
        p = Path(env)
        return p if p.is_dir() else None
    bp = repo / "components" / "brandpath"
    if str(bp) not in sys.path:
        sys.path.append(str(bp))
    try:
        import drive_index
        return drive_index.mount()
    except Exception:
        return None


def slug(s):
    return SLUG.sub("-", (s or "").strip().lower()).strip("-") or "unknown"


def machine_name():
    return slug(os.environ.get("VIDEO_QUEUE_MACHINE") or socket.gethostname().split(".")[0])


def person_name(repo=None):
    p = os.environ.get("VIDEO_QUEUE_PERSON")
    if not p:
        try:
            email = subprocess.run(["git", "config", "user.email"], cwd=str(repo or HERE),
                                   capture_output=True, text=True, timeout=10).stdout.strip()
            p = email.split("@")[0] if email else ""
        except Exception:
            p = ""
    return slug(p or getpass.getuser())


def now_utc():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------ the scan ---

def _load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _versions(vi):
    """versions-index.json in either shape → (list of {id, card}, top-level card path or '')."""
    if isinstance(vi, dict):
        rows = vi.get("versions") or []
        top = vi.get("card") or ""
    elif isinstance(vi, list):
        rows, top = vi, ""
    else:
        return [], ""
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append({"id": r.get("version_id") or r.get("version") or "",
                        "card": r.get("card_path") or r.get("card") or ""})
    return out, top


def drive_cards(drive):
    """brief id → {state, folder} for every video card on Drive (latest state wins in CARD_STATES order)."""
    cards = {}
    if drive is None:
        return cards
    meta = Path(drive) / "meta"
    try:
        brands = sorted(p for p in meta.iterdir() if p.is_dir())
    except OSError:
        return cards
    for b in brands:
        for state in CARD_STATES:
            d = b / state / "video"
            try:
                folders = sorted(p for p in d.iterdir() if p.is_dir())
            except OSError:
                continue
            for f in folders:
                # the folder name carries the brief (brand_product_brief-NNNN_batch-…); card.json is read only
                # when it does not — a Drive-for-desktop read of every card.json costs about a minute
                m = re.search(r"(brief-\d+)", f.name)
                brief = m.group(1) if m else (_load(f / "card.json") or {}).get("brief_id")
                if not brief:
                    continue
                prev = cards.get(brief)
                # an approved/live card outranks a 1-check one; sent-back outranks 1-check only
                rank = {"1-check": 1, "sent-back": 2, "2-approved": 3, "3-live": 4}[state]
                if prev is None or rank >= prev["rank"]:
                    cards[brief] = {"state": state, "folder": "meta/%s/%s/video/%s" % (b.name, state, f.name),
                                    "brand": b.name, "rank": rank}
    return cards


def _has(d, suffix):
    try:
        return d.is_dir() and any(p.suffix == suffix for p in d.iterdir())
    except OSError:
        return False


def run_stage(prod_dir, run, edit_dir, card, drive_run=None):
    """The ad's stage from one production run, its edit run, its Drive card and the run's Drive
    mirror (Shared Assets/runs/video-production/<brand>/<label>/ — media never sits in git, so on a
    machine that did not make the song, the mirror is where it shows). Returns (stage, why).
    The furthest proof wins: a filed card means every stage before it is done."""
    if card and card["state"] in ("2-approved", "3-live", "1-check"):
        return "done", "card on Drive in %s" % card["state"]
    if card and card["state"] == "sent-back":
        return "card", "card sent back — fix and re-file"
    vi = _load(edit_dir / "deliverable" / "versions-index.json") if edit_dir else None
    versions, top_card = _versions(vi)
    if top_card or any(v["card"] for v in versions):
        return "done", "card filed (versions-index)"
    if versions and any(v["id"] and v["id"] != "control" for v in versions):
        return "card", "hook versions made; card not filed"
    if versions:
        return "hooks", "control cut made; no hook versions"
    if edit_dir and edit_dir.is_dir():
        return "cut", "edit run open; no deliverable yet"
    if run.get("format") == "song-ad":
        song_done = (bool(run.get("song_file_drive")) or (prod_dir / "song" / "song.mp3").is_file()
                     or (drive_run is not None and _has(drive_run / "song", ".mp3")))
        if not song_done:
            return "song", "no song yet"
    if run.get("finished") or run.get("clips_in_cut"):
        return "cut", "clips finished; no edit run yet"
    has_clips = _has(prod_dir / "clips", ".mp4") or (drive_run is not None and _has(drive_run / "clips", ".mp4"))
    return "b-roll", ("clips in progress" if has_clips else "no clips yet")


def scan(repo, drive=None, include_all=False):
    """Every ad this machine can see → {key: ad}. key = brief id, or <brand>--<label> with --all."""
    repo = Path(repo)
    cards = drive_cards(drive)
    ads = {}
    prod = repo / "runs" / "video-production"
    edit = repo / "runs" / "video-edit"
    edit_by_brief = {}
    for vi_path in sorted(edit.glob("*/*/deliverable/versions-index.json")):
        vi = _load(vi_path)
        brief = vi.get("brief") if isinstance(vi, dict) else None
        if brief:
            edit_by_brief.setdefault(brief, vi_path.parents[1])
    for run_path in sorted(prod.glob("*/*/run.json")):
        brand, label = run_path.parts[-3], run_path.parts[-2]
        if brand.startswith("_") or label.startswith("_"):
            continue
        run = _load(run_path)
        if not isinstance(run, dict):
            continue
        brief = run.get("brief_id") or (run.get("brief") if str(run.get("brief", "")).startswith("brief-") else None)
        if not brief and not include_all:
            continue
        key = brief or "%s--%s" % (brand, label)
        edit_dir = edit / brand / label
        if not edit_dir.is_dir():
            edit_dir = edit_by_brief.get(brief) if brief else None
        drive_run = (Path(drive) / "runs" / "video-production" / brand / label) if drive else None
        stage, why = run_stage(run_path.parent, run, edit_dir, cards.get(brief) if brief else None, drive_run)
        opened = run.get("opened") or ""
        try:
            mtime = run_path.stat().st_mtime
        except OSError:
            mtime = 0
        entry = {"brief": brief, "brand": brand, "label": label, "format": run.get("format"),
                 "stage": stage, "why": why, "opened": opened, "mtime": mtime,
                 "run": "runs/video-production/%s/%s" % (brand, label),
                 "edit": ("runs/video-edit/%s/%s" % (edit_dir.parts[-2], edit_dir.parts[-1])) if edit_dir and edit_dir.is_dir() else None,
                 "card": (cards.get(brief) or {}).get("folder") if brief else None,
                 "seen_here": True, "runs": [label]}
        prev = ads.get(key)
        if prev is None:
            ads[key] = entry
        else:
            prev["runs"].append(label)
            # the most advanced run represents the ad; a tie goes to the newest
            if (STAGES.index(stage), mtime) > (STAGES.index(prev["stage"]), prev["mtime"]):
                entry["runs"] = prev["runs"]
                ads[key] = entry
    for brief, c in cards.items():           # made on another machine: known only from its card
        if brief not in ads:
            stage = "card" if c["state"] == "sent-back" else "done"
            ads[brief] = {"brief": brief, "brand": c["brand"], "label": c["folder"].rsplit("/", 1)[-1],
                          "format": None, "stage": stage, "why": "card on Drive in %s (no run on this machine)" % c["state"],
                          "opened": "", "mtime": 0, "run": None, "edit": None, "card": c["folder"],
                          "seen_here": False, "runs": []}
    return ads


# --------------------------------------------------------------- records ---

def make_record(event, item, machine, person, stage=None, brand=None, label=None, takeover_of=None, note=""):
    v = {"event": event, "machine": machine, "person": person,
         "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")}   # orders two acts in one second
    if stage:
        v["stage"] = stage
    if brand:
        v["brand"] = brand
    if label:
        v["label"] = label
    if takeover_of:
        v["takeover_of"] = takeover_of
    return {"schema": 1, "kind": KIND, "reviewer": person, "item": item, "verdict": v,
            "notes": note, "created": iso(now_utc()), "via": VIA}


def record_filename(rec, exists=None):
    """<UTC>--<person>--<brief>--<event>.json; a second act in the same second gets -2, -3 …
    so a progress never overwrites the claim it follows."""
    t = parse_iso(rec["created"]) or now_utc()
    base = "%s--%s--%s--%s" % (t.strftime("%Y%m%dT%H%M%SZ"), rec["reviewer"], slug(rec["item"]),
                               rec["verdict"].get("event", "act"))
    name, n = base + ".json", 1
    while exists is not None and exists(name):
        n += 1
        name = "%s-%d.json" % (base, n)
    return name


def fold(records):
    """records (any order) → {item: state}. state = {owner: {machine, person, at} | None,
    last_at, stage, history_len}. Latest claim not followed by a release is the owner."""
    by = {}
    def order(r):
        v = r.get("verdict") if isinstance(r.get("verdict"), dict) else {}
        return (r.get("created") or "", v.get("at") or "", r.get("_name") or "")
    for r in sorted(records, key=order):
        if r.get("kind") != KIND or not isinstance(r.get("verdict"), dict):
            continue
        item, v = r.get("item"), r["verdict"]
        s = by.setdefault(item, {"owner": None, "last_at": None, "stage": None, "history": 0})
        s["history"] += 1
        ev, at = v.get("event"), r.get("created")
        if ev == "claim":
            s["owner"] = {"machine": v.get("machine"), "person": v.get("person"), "at": at}
            s["last_at"] = at
        elif ev == "release":
            if s["owner"] and s["owner"]["machine"] == v.get("machine"):
                s["owner"] = None
            elif v.get("forced"):
                s["owner"] = None
            s["last_at"] = at
        elif ev == "progress":
            if s["owner"] and s["owner"]["machine"] == v.get("machine"):
                s["last_at"] = at
        if v.get("stage") and ev in ("claim", "progress"):
            s["stage"] = v["stage"]
    return by


def is_stale(state, hours, now=None):
    if not state or not state.get("owner"):
        return False
    last = parse_iso(state.get("last_at") or state["owner"].get("at"))
    if last is None:
        return True
    return ((now or now_utc()) - last).total_seconds() > hours * 3600


class Refused(Exception):
    pass


# ----------------------------------------------------------------- stores ---

class DirStore:
    """Records in a plain folder. The test seam, and a fallback for a folder both machines share."""

    def __init__(self, path):
        self.path = Path(path)

    def records(self):
        out = []
        try:
            files = sorted(self.path.glob("*.json"))
        except OSError:
            files = []
        for f in files:
            r = _load(f)
            if isinstance(r, dict):
                r["_name"] = f.name
                out.append(r)
        return out

    def publish(self, rec, recheck):
        recheck(fold(self.records()))
        self.path.mkdir(parents=True, exist_ok=True)
        p = self.path / record_filename(rec, lambda n: (self.path / n).exists())
        tmp = p.parent / (p.name + ".tmp")
        tmp.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(p))
        return str(p)


class GitStore:
    """Records on origin/<branch> under RECORDS_REL. Reads the fetched tip (plus any local files);
    publishes by commit-tree + push, never touching the working tree or the shared index."""

    def __init__(self, repo, remote="origin", branch="main", tries=5):
        self.repo, self.remote, self.branch, self.tries = Path(repo), remote, branch, tries
        self.ref = "refs/remotes/%s/%s" % (remote, branch)
        self.fetched = None

    def git(self, *args, **kw):
        env = kw.pop("env", None)
        inp = kw.pop("input", None)
        p = subprocess.run(["git"] + list(args), cwd=str(self.repo), capture_output=True, text=True,
                           input=inp, env=env, timeout=kw.pop("timeout", 120))
        return p

    def fetch(self):
        p = self.git("fetch", "--quiet", self.remote, "+refs/heads/%s:%s" % (self.branch, self.ref), timeout=90)
        self.fetched = (p.returncode == 0)
        return self.fetched

    def _tip(self):
        p = self.git("rev-parse", "--verify", "--quiet", self.ref)
        return p.stdout.strip() if p.returncode == 0 else None

    def _remote_records(self):
        tip = self._tip()
        if not tip:
            return []
        p = self.git("ls-tree", "-r", "--name-only", tip, "--", RECORDS_REL)
        names = [n for n in p.stdout.split("\n") if n.endswith(".json")]
        if not names:
            return []
        q = subprocess.run(["git", "cat-file", "--batch"], cwd=str(self.repo), capture_output=True, timeout=120,
                           input="".join("%s:%s\n" % (tip, n) for n in names).encode("utf-8"))
        out, data, i = [], q.stdout, 0       # bytes: a blob's size is in bytes, not characters
        for n in names:            # parse "<sha> blob <size>\n<content>\n" records in order
            j = data.find(b"\n", i)
            if j < 0:
                break
            head = data[i:j].split()
            if len(head) < 3 or head[1] != b"blob":
                i = j + 1
                continue
            size = int(head[2])
            body = data[j + 1:j + 1 + size]
            i = j + 1 + size + 1
            try:
                r = json.loads(body.decode("utf-8"))
            except ValueError:
                continue
            if isinstance(r, dict):
                r["_name"] = n.rsplit("/", 1)[-1]
                out.append(r)
        return out

    def records(self, fetch=True):
        if fetch:
            self.fetch()
        seen, out = set(), []
        for r in self._remote_records() + DirStore(self.repo / RECORDS_REL).records():
            if r["_name"] in seen:
                continue
            seen.add(r["_name"])
            out.append(r)
        return out

    def publish(self, rec, recheck):
        """Commit ONE record onto the remote tip and push. recheck(folded) raises Refused when
        the claims on the fresh tip no longer allow the act. Returns the record's repo path."""
        last = ""
        for _ in range(self.tries):
            if not self.fetch():
                raise Refused("could not reach %s — NOT claimed, nothing written. Try again when online." % self.remote)
            recheck(fold(self.records(fetch=False)))
            tip = self._tip()
            if not tip:
                raise Refused("%s/%s does not exist — nothing written" % (self.remote, self.branch))
            name = record_filename(rec, lambda n: self.git("cat-file", "-e", "%s:%s/%s" % (tip, RECORDS_REL, n)).returncode == 0)
            rel = "%s/%s" % (RECORDS_REL, name)
            body = json.dumps(rec, indent=2, ensure_ascii=False) + "\n"
            with tempfile.TemporaryDirectory(prefix="video-queue-") as td:
                env = dict(os.environ, GIT_INDEX_FILE=str(Path(td) / "index"))
                if self.git("read-tree", tip, env=env).returncode != 0:
                    raise Refused("git read-tree failed — nothing written")
                blob = self.git("hash-object", "-w", "--stdin", input=body).stdout.strip()
                if self.git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, rel), env=env).returncode != 0:
                    raise Refused("git update-index failed — nothing written")
                tree = self.git("write-tree", env=env).stdout.strip()
            v = rec["verdict"]
            msg = "video-queue: %s %s by %s on %s" % (v["event"], rec["item"], v["person"], v["machine"])
            commit = self.git("commit-tree", tree, "-p", tip, "-m", msg).stdout.strip()
            if not commit:
                raise Refused("git commit-tree failed — nothing written")
            push = self.git("push", "--quiet", self.remote, "%s:refs/heads/%s" % (commit, self.branch), timeout=120)
            if push.returncode == 0:
                self.git("update-ref", self.ref, commit)
                return rel
            last = (push.stderr or "").strip().splitlines()[-1:] or [""]
            last = last[0]
        raise Refused("the push kept being refused (%s) — NOT done, nothing written" % last)


def default_store(repo):
    d = os.environ.get("VIDEO_QUEUE_STORE")
    return DirStore(d) if d else GitStore(repo)


# ------------------------------------------------------------------ acts ---

def board(repo, store, drive=None, include_all=False, stale_hours=STALE_HOURS, records=None, now=None):
    """The merged list: every ad this machine sees, plus every claimed ad it does not."""
    ads = scan(repo, drive, include_all)
    states = fold(records if records is not None else store.records())
    rows = []
    for key in sorted(set(ads) | set(states)):
        ad = dict(ads.get(key) or {"brief": key, "brand": None, "label": None, "format": None, "stage": None,
                                   "why": "not on this machine yet", "run": None, "edit": None, "card": None,
                                   "seen_here": False, "runs": []})
        s = states.get(key) or {}
        reported = s.get("stage")
        if reported in STAGES and (ad["stage"] not in STAGES or STAGES.index(reported) > STAGES.index(ad["stage"])):
            ad["stage"], ad["why"] = reported, "reported by %s" % ((s.get("owner") or {}).get("machine") or "its last owner")
        ad["stage"] = ad["stage"] or "song"
        own = s.get("owner")
        ad["owner"] = own.get("machine") if own else None
        ad["person"] = own.get("person") if own else None
        ad["claimed_at"] = own.get("at") if own else None
        ad["last_progress"] = s.get("last_at") if own else None
        ad["stale"] = is_stale(s, stale_hours, now)
        rows.append(ad)
    return rows


def _decide_claim(item, me, take_over, stale_hours):
    def check(states):
        s = states.get(item) or {}
        own = s.get("owner")
        if not own:
            return None
        if own["machine"] == me:
            raise Refused("already yours (%s claimed it %s) — nothing written" % (me, own["at"]))
        if is_stale(s, stale_hours):
            if take_over:
                return {"machine": own["machine"], "person": own["person"], "last_at": s.get("last_at")}
            raise Refused("%s is held by %s (%s), but stale — nothing from them since %s. "
                          "Add --take-over to take it." % (item, own["machine"], own["person"], s.get("last_at")))
        raise Refused("%s is being worked on %s by %s (claimed %s, last progress %s). Pick another ad; "
                      "it can be taken over after %g hours with no progress." %
                      (item, own["machine"], own["person"], own["at"], s.get("last_at"), stale_hours))
    return check


def claim(repo, store, item, take_over=False, stale_hours=STALE_HOURS, drive=None, me=None, person=None):
    me, person = me or machine_name(), person or person_name(repo)
    ad = scan(repo, drive).get(item) or {}
    decide = _decide_claim(item, me, take_over, stale_hours)
    box = {}

    def recheck(states):
        box["takeover_of"] = decide(states)

    recheck(fold(store.records()))           # refuse early, before building anything
    rec = make_record("claim", item, me, person, stage=ad.get("stage"), brand=ad.get("brand"),
                      label=ad.get("label"), takeover_of=box.get("takeover_of"))

    def recheck_and_stamp(states):
        recheck(states)
        if box.get("takeover_of"):
            rec["verdict"]["takeover_of"] = box["takeover_of"]
        else:
            rec["verdict"].pop("takeover_of", None)

    return store.publish(rec, recheck_and_stamp), rec


def _owner_only(item, me, forced=False):
    def check(states):
        own = (states.get(item) or {}).get("owner")
        if not own:
            raise Refused("%s is not claimed by anyone — nothing written" % item)
        if own["machine"] != me and not forced:
            raise Refused("%s is held by %s (%s), not this machine (%s) — nothing written" %
                          (item, own["machine"], own["person"], me))
    return check


def progress(repo, store, item, stage=None, drive=None, me=None, person=None):
    me, person = me or machine_name(), person or person_name(repo)
    _owner_only(item, me)(fold(store.records()))      # not yours: say so before anything else
    ad = scan(repo, drive).get(item) or {}
    stage = stage or ad.get("stage")
    if stage not in STAGES:
        raise Refused("unknown stage %r — one of %s" % (stage, ", ".join(STAGES)))
    rec = make_record("progress", item, me, person, stage=stage, brand=ad.get("brand"), label=ad.get("label"))
    return store.publish(rec, _owner_only(item, me)), rec


def release(repo, store, item, force=False, me=None, person=None):
    me, person = me or machine_name(), person or person_name(repo)
    rec = make_record("release", item, me, person)
    if force:
        rec["verdict"]["forced"] = True
    return store.publish(rec, _owner_only(item, me, forced=force)), rec


def sync(repo, store, drive=None, me=None, person=None, stale_hours=STALE_HOURS):
    """A progress record for every ad this machine holds whose stage moved (or is going stale)."""
    me, person = me or machine_name(), person or person_name(repo)
    records = store.records()
    states = fold(records)
    ads = scan(repo, drive)
    done = []
    for item, s in sorted(states.items()):
        own = s.get("owner")
        if not own or own["machine"] != me:
            continue
        here = (ads.get(item) or {}).get("stage")
        half_stale = is_stale(s, stale_hours / 2.0)
        if here and (here != s.get("stage") or half_stale):
            path, _ = progress(repo, store, item, stage=here, drive=drive, me=me, person=person)
            done.append((item, here, path))
    return done


# ------------------------------------------------------------------- page ---

def _ago(s, now):
    t = parse_iso(s)
    if not t:
        return ""
    m = int((now - t).total_seconds() // 60)
    if m < 60:
        return "%dm ago" % max(m, 0)
    if m < 48 * 60:
        return "%dh ago" % (m // 60)
    return "%dd ago" % (m // 1440)


STAGE_WORDS = {"song": "Song", "b-roll": "B-roll", "cut": "Cut", "hooks": "Hooks", "card": "Card", "done": "Done"}


def page_html(rows, me, generated, stale_hours):
    now = parse_iso(generated) or now_utc()
    cols = []
    for st in STAGES:
        items = [r for r in rows if r["stage"] == st]
        cards = []
        for r in items:
            who = ""
            if r["owner"]:
                badge = '<span class="stale">stale</span>' if r["stale"] else ""
                who = '<div class="who"><b>%s</b> · %s · %s %s</div>' % (
                    html.escape(r["owner"]), html.escape(r["person"] or ""), _ago(r["claimed_at"], now), badge)
            else:
                who = '<div class="who free">open — nobody on it</div>' if st != "done" else ""
            cards.append('<div class="ad%s"><div class="top"><span class="brief">%s</span><span class="brand">%s</span></div>'
                         '<div class="label">%s</div>%s<div class="why">%s</div></div>' % (
                             " mine" if r["owner"] == me else "", html.escape(r["brief"] or ""), html.escape(r["brand"] or ""),
                             html.escape(r["label"] or ""), who, html.escape(r["why"] or "")))
        cols.append('<section><h2>%s <span>%d</span></h2>%s</section>' % (STAGE_WORDS[st], len(items), "".join(cards) or '<p class="none">—</p>'))
    working = sorted({r["owner"] for r in rows if r["owner"]})
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Video Work Queue</title><style>
:root{--bg:#fafafa;--card:#fff;--ink:#18181b;--mute:#71717a;--line:#e4e4e7;--accent:#2563eb;--warn:#b45309;--warnbg:#fef3c7}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#09090b;--card:#18181b;--ink:#fafafa;--mute:#a1a1aa;--line:#27272a;--accent:#60a5fa;--warn:#fbbf24;--warnbg:#422006}}
:root[data-theme="dark"]{--bg:#09090b;--card:#18181b;--ink:#fafafa;--mute:#a1a1aa;--line:#27272a;--accent:#60a5fa;--warn:#fbbf24;--warnbg:#422006}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:24px 16px}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 20px}
.cols{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px}
@media (max-width:900px){.cols{grid-template-columns:1fr}}
section h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute);margin:0 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}
section h2 span{float:right}
.ad{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;margin-bottom:8px}
.ad.mine{border-color:var(--accent)}.top{display:flex;justify-content:space-between;gap:8px}
.brief{font-weight:600}.brand{color:var(--mute);font-size:12px}.label{font-size:12px;color:var(--mute);word-break:break-word}
.who{margin-top:6px;font-size:12px}.who.free{color:var(--mute)}.why{margin-top:4px;font-size:12px;color:var(--mute)}
.stale{background:var(--warnbg);color:var(--warn);border-radius:4px;padding:0 5px;font-size:11px;margin-left:4px}
.none{color:var(--mute)}
</style></head><body>
<h1>Video Work Queue</h1>
<p class="sub">Every ad on the video line, which stage it is at, and which computer is on it. Made on <b>%s</b> at %s UTC.
Working now: %s. A claim with no progress for %g hours shows <span class="stale">stale</span> and can be taken over.</p>
<div class="cols">%s</div></body></html>
""" % (html.escape(me), html.escape(generated.replace("T", " ").rstrip("Z")),
       html.escape(", ".join(working) or "nobody"), stale_hours, "".join(cols))


def write_page(repo, rows, me, stale_hours, out=None):
    out = Path(out) if out else Path(repo) / "runs" / "video-queue" / "_system" / "status.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    gen = iso(now_utc())
    out.write_text(page_html(rows, me, gen, stale_hours), encoding="utf-8")
    (out.parent / "status.json").write_text(json.dumps({"generated": gen, "machine": me, "rows": rows}, indent=1,
                                                       ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return out


# -------------------------------------------------------------------- cli ---

def main(argv=None):
    ap = argparse.ArgumentParser(prog="work_queue.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--stale-hours", type=float, default=float(os.environ.get("VIDEO_QUEUE_STALE_HOURS") or STALE_HOURS))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list"); s.add_argument("--brand"); s.add_argument("--all", action="store_true"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("claim"); s.add_argument("brief"); s.add_argument("--take-over", action="store_true")
    s = sub.add_parser("progress"); s.add_argument("brief"); s.add_argument("--stage", choices=STAGES)
    s = sub.add_parser("release"); s.add_argument("brief"); s.add_argument("--force", action="store_true")
    sub.add_parser("sync")
    s = sub.add_parser("page"); s.add_argument("--out"); s.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    repo = repo_root()
    store = default_store(repo)
    drive = drive_root(repo)
    me = machine_name()
    try:
        if a.cmd in ("list", "page"):
            rows = board(repo, store, drive, getattr(a, "all", False), a.stale_hours)
            if a.cmd == "page":
                print(write_page(repo, rows, me, a.stale_hours, a.out))
                return 0
            if a.brand:
                rows = [r for r in rows if r["brand"] == a.brand]
            if a.json:
                print(json.dumps(rows, indent=1, default=str))
                return 0
            if isinstance(store, GitStore) and store.fetched is False:
                print("(could not reach origin — claims as of the last fetch)")
            if drive is None:
                print("(Drive not mounted — card stage read from this machine's runs only)")
            print("%-11s %-8s %-7s %-34s %-22s %s" % ("brief", "brand", "stage", "label", "owner", "claimed"))
            for r in rows:
                own = ("%s/%s" % (r["owner"], r["person"])) if r["owner"] else "-"
                print("%-11s %-8s %-7s %-34s %-22s %s%s" % (r["brief"] or "", r["brand"] or "", r["stage"],
                                                         (r["label"] or "")[:34], own[:22], r["claimed_at"] or "",
                                                         "  STALE" if r["stale"] else ""))
            return 0
        if a.cmd == "claim":
            path, rec = claim(repo, store, a.brief, a.take_over, a.stale_hours, drive)
            took = rec["verdict"].get("takeover_of")
            print("claimed %s for %s (%s)%s → %s" % (a.brief, rec["verdict"]["machine"], rec["verdict"]["person"],
                                                      (" — took over from %s" % took["machine"]) if took else "", path))
        elif a.cmd == "progress":
            path, rec = progress(repo, store, a.brief, a.stage, drive)
            print("%s at %s → %s" % (a.brief, rec["verdict"]["stage"], path))
        elif a.cmd == "release":
            path, rec = release(repo, store, a.brief, a.force)
            print("released %s → %s" % (a.brief, path))
        elif a.cmd == "sync":
            done = sync(repo, store, drive, stale_hours=a.stale_hours)
            for item, stage, path in done:
                print("%s at %s → %s" % (item, stage, path))
            if not done:
                print("nothing to report — no ad this machine holds has moved")
    except Refused as e:
        print("REFUSED — %s" % e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
