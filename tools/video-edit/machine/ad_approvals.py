#!/usr/bin/env python3
"""ad_approvals.py — the ONE reader of the Ad Runs OKs, and the one place an OK is given from
(AR-1 (shared ad approvals), reworked by AR-1b (approvals as verdicts)).

Two OKs per ad (the owner, 15 Oct): "production" (start making it, the spend) and "final" (the finished ad —
releases hook versions + thumbnails).

AN OK IS A REVIEW VERDICT (AR-1b (approvals as verdicts), the dashboard route): the latest `approve` verdict on
the review request, lane `ad-runs`, whose asset names the ad and the step (`asset_for` is that shape, written
once, so the request the board opens and the verdict a person gives meet). Every door files on that request —
the dashboard's Ad Runs page (`POST /api/review`), a person's own Claude (lab/damon/ad-runs/approve.py, git
route) and the owner's board button — and every reader reads it here. Records are read through
components/review/review_request.py (`read_records`, `fold`, `list_open`); this file never folds a request.

    load(repo, include_remote=True) -> {id: {step: record}}   record = {id, step, approved_by, at, note, item}
    request_for(repo, ad, step) -> the open request on the ad + step, folded; None when none is open
    give(repo, ad, step, person, note="", commit=True) -> file_record's receipt     the approve verdict, git route
    may_approve(repo, email, step) -> (ok, why)              team/ad-approvers.json, read on every call
    person_of(email) -> the person id a verdict names, or ""

`load` reads the legacy runs/ad-runs/approvals.jsonl (the owner's seed, read as is, never written; a record with no
step is a final OK) and the review records — this clone's working tree and, with `include_remote`, origin/main's
as of the caller's last `git fetch` (git ls-tree + cat-file, never a pull), so a runner sees a verdict given
elsewhere without pulling into its working clone. A component: line.py imports it, lab may; it imports nothing
from lab.
"""
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

REPO = Path(__file__).resolve().parents[3]
LEGACY = "runs/ad-runs/approvals.jsonl"
APPROVERS = "team/ad-approvers.json"
REMOTE = "origin/main"
STEPS = ("production", "final")
ID_RE = re.compile(r"[\w.-]{3,96}")
LANE = "ad-runs"                                        # an open label (platform/data/kinds/review.json, lane note)
PAGE = "https://dashboard.company.com/ad-runs"  # AR-3 (ad runs page)'s address; the ref names ad + step on it


def _review_request():
    """components/review/review_request.py, loaded by path — the small loader its CLAUDE.md asks callers to keep."""
    mod = sys.modules.get("review_request")
    if mod is None:
        path = Path(__file__).resolve().parents[2] / "review" / "review_request.py"
        spec = importlib.util.spec_from_file_location("review_request", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["review_request"] = mod
    return mod


RR = _review_request()
Refused = RR.Refused


def _check(ad, step):
    if not ID_RE.fullmatch(str(ad or "")):
        raise ValueError("bad ad id: %r" % (ad,))
    if step not in STEPS:
        raise ValueError("step must be production or final, not %r" % (step,))


def asset_for(ad, step):
    """The asset of an ad's request at one step — the one shape the board files and `names` reads back."""
    _check(ad, step)
    return {"warehouse": "url", "ref": PAGE + "?" + urlencode([("ad", ad), ("step", step)]),
            "title": "%s — %s OK" % (ad, step)}


def names(asset):
    """(ad, step) a request's asset names, else None."""
    if not isinstance(asset, dict):
        return None
    q = parse_qs(urlparse(str(asset.get("ref") or "")).query)
    ad, step = (q.get("ad") or [""])[0], (q.get("step") or [""])[0]
    return (ad, step) if ID_RE.fullmatch(ad) and step in STEPS else None


def _git(repo, *args, data=None):
    return subprocess.run(["git", *args], cwd=str(repo), input=data, capture_output=True, timeout=60)


def _remote_records(repo, ref):
    """ref's review records (origin/main as of the last fetch), read by read_records over a scratch copy; [] when
    there is no such ref (no remote, never fetched)."""
    rel = RR.RECORDS_REL
    try:
        ls = _git(repo, "ls-tree", "-z", ref, "--", rel + "/")
    except Exception:
        return []
    if ls.returncode != 0:
        return []
    blobs = []
    for entry in ls.stdout.decode("utf-8", "replace").split("\0"):
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob" and path.endswith(".json") and "/" not in path[len(rel) + 1:]:
            blobs.append((path.rsplit("/", 1)[-1], parts[2]))
    if not blobs:
        return []
    # every blob in one call: cat-file --batch frames each one with its size
    cat = _git(repo, "cat-file", "--batch", data="".join(sha + "\n" for _, sha in blobs).encode())
    buf, pos = cat.stdout, 0
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / rel
        d.mkdir(parents=True)
        for name, _ in blobs:
            nl = buf.find(b"\n", pos)
            head = buf[pos:nl].split()
            if nl < 0 or len(head) != 3:
                break
            size = int(head[2])
            (d / name).write_bytes(buf[nl + 1:nl + 1 + size])
            pos = nl + 1 + size + 1
        return RR.read_records(root=tmp)


def records(repo=None, include_remote=True, ref=REMOTE):
    """Every review record this clone can see — origin's and its own working tree's, one copy of each."""
    repo = Path(repo or REPO)
    seen = {}
    for rec in (_remote_records(repo, ref) if include_remote else []) + RR.read_records(root=repo):
        try:
            key = RR.filename(rec)
        except Exception:
            key = json.dumps(rec, sort_keys=True)
        seen[key] = rec
    return [seen[k] for k in sorted(seen)]


def _put(out, rec):
    try:
        out.setdefault(rec["id"], {})[rec.get("step") or "final"] = rec
    except Exception:
        pass


def oks(recs):
    """One OK per lane-`ad-runs` request (open or closed) that names an ad + step and carries an approve verdict:
    the latest approve among the fold's latest verdict per reviewer. Oldest OK first."""
    by_item = {}
    for r in recs:
        if isinstance(r, dict) and r.get("item"):
            by_item.setdefault(r["item"], []).append(r)
    found = []
    for item, rs in by_item.items():
        st = RR.fold(rs)
        req = st["request"]
        named = names(req.get("asset")) if req and req.get("lane") == LANE else None
        if not named:
            continue
        approves = [v for v in st["verdicts"].values() if (v.get("verdict") or {}).get("verdict") == "approve"]
        if not approves:
            continue
        v = max(approves, key=lambda r: str(r.get("created") or ""))
        found.append({"id": named[0], "step": named[1], "approved_by": v.get("reviewer"), "at": v.get("created"),
                      "note": str((v.get("verdict") or {}).get("note") or ""), "item": item})
    return sorted(found, key=lambda r: (str(r["at"] or ""), r["id"], r["step"]))


def load(repo=None, include_remote=True, ref=REMOTE):
    """{id: {step: record}} — the legacy jsonl first (its own order, a later line wins), then every verdict OK,
    origin's and this clone's together, oldest first (a runner meets them in the order they were given)."""
    repo = Path(repo or REPO)
    out = {}
    legacy = repo / LEGACY
    if legacy.is_file():
        for line in legacy.read_text().splitlines():
            try:
                _put(out, json.loads(line))
            except Exception:
                pass
    for rec in oks(records(repo, include_remote, ref)):
        _put(out, rec)
    return out


def request_for(repo, ad, step, include_remote=True, ref=REMOTE):
    """The OPEN lane-`ad-runs` request naming this ad + step, folded (the oldest, should there be two); None when
    none is open. The board opens one when the ad is waiting (AR-2 (ad board snapshot))."""
    for st in RR.list_open(records=records(repo, include_remote, ref), lane=LANE):
        if names(st["request"].get("asset")) == (ad, step):
            return st
    return None


def give(repo, ad, step, person, note="", commit=True, request=None):
    """File the approve verdict on the ad's open request through review_request.file_record — the GIT route
    whatever the environment holds, committing that one record path when `commit`. Raises LookupError when no
    request is open, Refused when the record is refused (a person who is not a person id, say)."""
    _check(ad, step)
    st = request or request_for(repo, ad, step)
    if st is None:
        raise LookupError("no open %s review request names %s at the %s step — the board opens one when the ad "
                          "is waiting (AR-2 (ad board snapshot))" % (LANE, ad, step))
    verdict = {"event": "verdict", "verdict": "approve"}
    if str(note or "").strip():
        verdict["note"] = str(note)[:500]
    return RR.file_record(st["item"], verdict, person, root=Path(repo or REPO), env={}, commit=commit)


def person_of(email, repo=None):
    """The person id a verdict names: whoever team/people/<id>/identity.json lists `email` under, in `repo`
    (default REPO) — run_kit.people, never the email's local part (LD-77 (one person resolver)); "" when
    unmapped or not a person id — never guessed onto a record."""
    kit = str(Path(__file__).resolve().parents[2] / "run-kit")
    if kit not in sys.path:
        sys.path.append(kit)
    from run_kit import people
    who = people.try_person_of(Path(repo or REPO), str(email or ""))
    try:
        return RR.people([who], "reviewer")[0] if who else ""
    except Refused:
        return ""


def may_approve(repo, email, step):
    """(True, "") when email is on the step's list in team/ad-approvers.json ("*" = anyone), else (False, why)."""
    f = Path(repo or REPO) / APPROVERS
    try:
        lists = json.loads(f.read_text())
    except Exception as e:
        return False, "cannot read %s (%s)" % (APPROVERS, e.__class__.__name__)
    who = lists.get(step) if isinstance(lists, dict) else None
    if not isinstance(who, list):
        return False, "%s has no list for the %s step" % (APPROVERS, step)
    email = str(email or "").strip().lower()
    if not email:
        return False, "no git user.email set in this clone — an OK names who gave it"
    if "*" in who or email in {str(w).strip().lower() for w in who}:
        return True, ""
    return False, "%s is not on the %s list in %s" % (email, step, APPROVERS)
