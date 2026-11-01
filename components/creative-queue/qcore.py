"""The queue core, QB-1 (queue core): machine OBSERVATIONS + per-person DECISION logs -> one index.json.

Three file shapes under a ROOT (default <repo>/runs/queue-shadow until QB-4 (joint queue test) passes):
  observations/<source>.json             {"schema": 1, "source", "as_of": "<UTC …Z>", "entries": {"<id>": {...}}}
                                         one writer per file; `observed_stage` and `execution` are reserved
  decisions/<person>/<YYYY-MM-DD>.jsonl  one {"schema": 1, "id", "op", "field", "value", "by", "made"} a line,
                                         append-only, one log per person per UTC day (git union-merges them)
  index.json                             {"schema": 1, "built", "sources": {src: {"as_of", "age_s"}}, "entries": [...]}

`reduce` is a pure function of the first two; the index is a projection, rebuilt, never hand-edited.
Stdlib only, Python 3.9.6. Nothing here imports lab code: the shapes were read from lab/damon/suite/queue_store.py.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402

SETTABLE = ("who", "priority", "due", "title_set", "note", "requested_stage")
DUE = re.compile(r"^\d{4}-\d{2}-\d{2}$")         # QB-6 (content queue page): `due` is YYYY-MM-DD, or "" to clear
OPS = ("set", "add", "remove", "restore", "approve")
EXECUTION = ("pending", "running", "done", "failed", "needs-reconfirm")
# keys the reducer owns: an observation carrying one of these never shows through
DERIVED = ("id", "removed", "approved", "decided_by", "stage_differs", "observed_in")
SWITCH = ("components", "creative-queue", "live-switch.json")
REFUSED = ("REFUSED: the live queue is off (components/creative-queue/live-switch.json) — "
           "build-only until QB-4 (joint queue test)")
NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
ZFMT = "%Y-%m-%dT%H:%M:%SZ"
UTC = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?Z$")


class Refused(Exception):
    """A root the switches do not allow."""


def _order():
    """The stage order: the naming standard's one list, components/naming/stages.json `stages[].id` (the same list
    as naming/stages.py ORDER; QB-5 (production contract) retired this folder's copy). Read once at import, so
    `reduce` stays pure."""
    try:
        stages = json.loads((HERE.parent / "naming" / "stages.json").read_text())["stages"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    if not isinstance(stages, list):
        return []
    return [s["id"] for s in stages if isinstance(s, dict) and isinstance(s.get("id"), str)]


ORDER = _order()


# --------------------------------------------------------------- roots and the live guard

def _repo(repo=None):
    return Path(repo) if repo else paths.repo()


def shadow_root(repo=None):
    return _repo(repo) / "runs" / "queue-shadow"


def live_root(repo=None):
    return _repo(repo) / "runs" / "queue"


def live_state(repo=None):
    """"on" only when live-switch.json says exactly {"live": "on"}; a missing file, bad JSON or any other value is off."""
    try:
        v = json.loads(_repo(repo).joinpath(*SWITCH).read_text()).get("live")
    except (OSError, ValueError, AttributeError):
        return "off"
    return "on" if v == "on" else "off"


def check_root(root, repo=None):
    """The root, resolved; Refused when it is the live queue (or inside it) and the live switch is not on."""
    r = Path(root).expanduser().resolve()
    live = live_root(repo).resolve()
    if (r == live or live in r.parents) and live_state(repo) != "on":
        raise Refused(REFUSED)
    return r


# --------------------------------------------------------------- time, as text

def utc_now():
    return datetime.now(timezone.utc).strftime(ZFMT)


def _utc(s):
    """A UTC "…Z" string as a datetime, or None. Fractional seconds allowed. Parsed by hand, not strptime,
    so `reduce` never pulls in a module or a locale on its first call."""
    m = UTC.match(s) if isinstance(s, str) else None
    if not m:
        return None
    y, mo, d, h, mi, sec, frac = m.groups()
    try:
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(sec),
                        int((frac or "0")[:6].ljust(6, "0")), tzinfo=timezone.utc)
    except ValueError:
        return None


def _need_utc(s, what):
    if _utc(s) is None:
        raise ValueError("%s must be a UTC time like 2026-10-22T02:24:18Z, got %r" % (what, s))
    return s


def due_ok(v):
    """True for "" (clears it) or a real calendar day written exactly YYYY-MM-DD."""
    if v == "":
        return True
    if not isinstance(v, str) or not DUE.match(v):
        return False
    try:
        datetime(int(v[:4]), int(v[5:7]), int(v[8:10]))
    except ValueError:
        return False
    return True


def _name(s, what):
    if not isinstance(s, str) or not NAME.match(s):
        raise ValueError("%s must be lower-case letters, digits, '.', '_' or '-', got %r" % (what, s))
    return s


# --------------------------------------------------------------- reading

def load(root):
    """(observations keyed by source, decisions in (file path, line) order)."""
    root = Path(root)
    observations = {}
    for f in sorted((root / "observations").glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except ValueError as e:
            raise ValueError("%s is not JSON: %s" % (f, e))
        if not isinstance(d, dict) or not isinstance(d.get("entries"), dict):
            raise ValueError("%s has no entries object" % f)
        observations[f.stem] = d
    decisions = []
    for f in sorted((root / "decisions").glob("**/*.jsonl")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError as e:
                raise ValueError("%s line %d is not JSON: %s" % (f, n, e))
            if not isinstance(rec, dict):
                raise ValueError("%s line %d is not an object" % (f, n))
            decisions.append(rec)
    return observations, decisions


# --------------------------------------------------------------- the reducer (PURE)

def _rank(stage):
    return (ORDER.index(stage), "") if stage in ORDER else (-1, str(stage))


def _winner(cands):
    """The decision that wins: any non-legacy beats every legacy one; inside a group the latest `made` wins,
    ties by `by`, then load order. Legacy `made` is naive text, compared only with other legacy text."""
    real = [c for c in cands if not c[1].get("legacy")]
    if real:
        epoch = datetime.min.replace(tzinfo=timezone.utc)
        return max(real, key=lambda c: (_utc(c[1].get("made")) or epoch, str(c[1].get("by") or ""), c[0]))
    return max(cands, key=lambda c: (str(c[1].get("made") or ""), str(c[1].get("by") or ""), c[0]))


def _stamp(rec):
    return {"by": rec.get("by"), "made": rec.get("made")}


def reduce(observations, decisions, now):
    """The index: a pure function of the observations, the decisions and `now` (a UTC "…Z" string).
    No file, clock or environment is touched here."""
    now_dt = _utc(now)
    sources = {}
    for src in sorted(observations):
        as_of = observations[src].get("as_of")
        t = _utc(as_of)
        sources[src] = {"as_of": as_of, "age_s": int((now_dt - t).total_seconds()) if t and now_dt else None}
    # freshest source first, so a field two machines both report shows the newer report; ties by source name
    fresh = sorted(observations, key=lambda s: (sources[s]["as_of"] or "", s), reverse=True)

    by_id = {}
    for seq, rec in enumerate(decisions):
        if isinstance(rec, dict) and isinstance(rec.get("id"), str) and rec.get("op") in OPS:
            by_id.setdefault(rec["id"], []).append((seq, rec))

    ids = {i for o in observations.values() for i in (o.get("entries") or {})}
    ids |= {i for i, recs in by_id.items() if any(r["op"] == "add" for _, r in recs)}

    entries = []
    for eid in sorted(ids):
        recs = by_id.get(eid, [])
        seen = [s for s in fresh if eid in (observations[s].get("entries") or {})]
        e, decided_by = {}, {}
        adds = [c for c in recs if c[1]["op"] == "add"]
        if adds:
            w = _winner(adds)[1]
            seed = w.get("value") if isinstance(w.get("value"), dict) else {}
            for k, v in seed.items():
                if k not in DERIVED and k not in ("observed_stage", "execution"):
                    e[k] = v
                    decided_by[k] = _stamp(w)
        observed = {}
        for s in reversed(seen):                         # oldest first, the freshest lands last
            observed.update(observations[s]["entries"][eid] or {})
        for k, v in observed.items():
            if k in DERIVED or k in ("observed_stage", "execution"):
                continue
            e[k] = v
            decided_by.pop(k, None)                      # a machine's report replaces the person's seed
        e["id"] = eid
        e["observed_in"] = seen
        stages = [observations[s]["entries"][eid].get("observed_stage") for s in seen]
        stages = [x for x in stages if x not in (None, "")]
        if stages:
            e["observed_stage"] = max(stages, key=_rank)
        for f in SETTABLE:
            cands = [c for c in recs if c[1]["op"] == "set" and c[1].get("field") == f]
            if cands:
                w = _winner(cands)[1]
                e[f] = w.get("value")
                decided_by[f] = _stamp(w)
        rr = [c for c in recs if c[1]["op"] in ("remove", "restore")]
        e["removed"] = False
        if rr:
            w = _winner(rr)[1]
            e["removed"] = w["op"] == "remove"
            decided_by["removed"] = _stamp(w)
        ap = [c for c in recs if c[1]["op"] == "approve"]
        if ap:
            w = _winner(ap)[1]
            e["approved"] = _stamp(w)
            decided_by["approved"] = _stamp(w)
        receipt = next((observations[s]["entries"][eid].get("execution") for s in seen
                        if observations[s]["entries"][eid].get("execution")), None)
        if receipt:
            e["execution"] = receipt
        elif ap:
            e["execution"] = "pending"
        req, obs = e.get("requested_stage"), e.get("observed_stage")
        e["stage_differs"] = bool(req) and bool(obs) and req != obs
        e["decided_by"] = decided_by
        entries.append(e)
    return {"schema": 1, "built": now, "sources": sources, "entries": entries}


# --------------------------------------------------------------- writing

def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)
    return path


def write_observation(root, source, entries, now=None):
    """observations/<source>.json, written only when the entries changed; None when unchanged."""
    _name(source, "source")
    if not isinstance(entries, dict):
        raise ValueError("entries must be an object keyed by id")
    for eid, fields in entries.items():
        if not isinstance(fields, dict):
            raise ValueError("entry %s must be an object" % eid)
        x = fields.get("execution")
        if x is not None and x not in EXECUTION:
            raise ValueError("entry %s: execution must be one of %s, got %r" % (eid, ", ".join(EXECUTION), x))
    path = Path(root) / "observations" / (source + ".json")
    try:
        old = json.loads(path.read_text()).get("entries")
    except (OSError, ValueError, AttributeError):
        old = None
    if old == json.loads(json.dumps(entries)):
        return None
    as_of = _need_utc(now, "now") if now else utc_now()
    return _write(path, _dump({"schema": 1, "source": source, "as_of": as_of, "entries": entries}))


def append_decision(root, person, rec, now=None):
    """One line on decisions/<person>/<UTC day>.jsonl; fills schema / by / made; ValueError names the problem."""
    _name(person, "person")
    if not isinstance(rec, dict):
        raise ValueError("a decision must be an object")
    rec = dict(rec)
    now = _need_utc(now, "now") if now else utc_now()
    rec.setdefault("schema", 1)
    rec.setdefault("by", person)
    rec.setdefault("made", now)
    rec.setdefault("field", None)
    rec.setdefault("value", None)
    if rec["by"] != person:
        raise ValueError("by %r does not match the log's person %r: a person writes only their own log" % (rec["by"], person))
    if not isinstance(rec.get("id"), str) or not rec["id"].strip():
        raise ValueError("a decision needs an id")
    if rec.get("op") not in OPS:
        raise ValueError("op must be one of %s, got %r" % (", ".join(OPS), rec.get("op")))
    if rec["op"] == "set":
        if rec["field"] not in SETTABLE:
            raise ValueError("field must be one of %s, got %r" % (", ".join(SETTABLE), rec["field"]))
        if rec["field"] == "requested_stage" and ORDER and rec["value"] not in ORDER:
            raise ValueError("requested_stage must be one of %s, got %r" % (", ".join(ORDER), rec["value"]))
        if rec["field"] == "due" and not due_ok(rec["value"]):
            raise ValueError("due must be a date like 2026-10-27, or \"\" to clear, got %r" % (rec["value"],))
    elif rec["field"] is not None:
        raise ValueError("op %s takes no field, got %r" % (rec["op"], rec["field"]))
    if rec["op"] == "add" and not isinstance(rec["value"], dict):
        raise ValueError("op add needs a value object (title, brand, type)")
    if rec.get("legacy"):
        raise ValueError("legacy lines are written by import-legacy only")
    _need_utc(rec["made"], "made")
    path = Path(root) / "decisions" / person / (now[:10] + ".jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def write_index(root, index):
    return _write(Path(root) / "index.json", _dump(index))


# --------------------------------------------------------------- committing (by path, never the whole index)

def commit_paths(paths, message, repo, run=subprocess.run):
    """git add / commit by path / push; a rejected push pulls (--no-rebase) and pushes again, 3 pushes at most.
    Returns the commit sha; RuntimeError names the step that failed."""
    repo = Path(repo)
    rel = []
    for p in paths:
        p = Path(p)
        try:
            rel.append(str(p.resolve().relative_to(repo.resolve())))
        except ValueError:
            rel.append(str(p))

    def git(step, *args):
        r = run(["git", *args], cwd=str(repo), capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return r, step

    def need(r_step):
        r, step = r_step
        if r.returncode != 0:
            raise RuntimeError("%s failed: %s" % (step, (r.stderr or r.stdout or "").strip()))
        return r

    need(git("git add", "add", "--", *rel))
    need(git("git commit", "commit", "-m", message, "--", *rel))
    for attempt in range(3):
        r, _ = git("git push", "push")
        if r.returncode == 0:
            break
        if attempt == 2:
            raise RuntimeError("git push failed after 3 tries: %s" % (r.stderr or r.stdout or "").strip())
        need(git("git pull --no-rebase", "pull", "--no-rebase"))
    return need(git("git rev-parse HEAD", "rev-parse", "HEAD")).stdout.strip()
