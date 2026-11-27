"""ran — what ran, one line per Claude call (part 5 of the Creative Workflow Standard, "record what ran").

WHERE IT RECORDS (moved down into the credential door, developer 2026-11-26: "Yes, move it down"). Every call that
goes through run_kit/claude_door.run writes one JSON line, so a chain is recorded without changing its code:
the shared caller (`model.call`), and every chain that calls the door directly. A call that runs its own
`claude -p` past the door is not recorded until it moves onto the door. `model.call` with a runner of its own
(tests, email's lean calls) writes the line itself, because the door never sees that call.

    the run folder known  →  <run folder>/what-ran.jsonl   (model.call's run_dir=, every stage.Chain step)
    otherwise             →  runs/what-ran/<person>/<YYYY-MM-DD>.jsonl, with the script that made the call

A line holds: when, the step, the model asked for, the effort, which door answered (a Claude login, the company
key, Codex, the session hand), the prompt's fingerprint and file name (never its text), seconds, how it ended,
characters out, the calling script, who ran it (person id, never an email), and tier/why when the caller knew.

THE SWITCH IS OFF. While RECORD is False nothing here writes anything and every caller behaves exactly as
before. No environment knob, the same as EFFORT in claude_flags.py (developer, 2026-10-21: "Don't add more
variables"): switch it in a commit, so every machine records the same way. Turning it off again, if developer is
offline: the prompt in 1.8.1 of the Creative Workflow Standard page. owner owns run-kit; he is told there.

Never raises. Stdlib only, Python 3.9, no relative imports: claude_door loads this file by path, and both
loads share ONE instance through sys.modules["run_kit.ran"], so the switch and the per-call context agree.
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

RECORD = False                 # the switch; see the docstring before turning it on
FILE = "what-ran.jsonl"
HERE = Path(__file__).resolve()
LOG_ROOT = None                # the daily log's root; None = <repo>/runs/what-ran (tests point it at a temp folder)
_lock = threading.Lock()
_ctx = threading.local()       # what model.call knows about the call in flight on this thread
_who = {}


def on():
    return bool(RECORD)


def fingerprint(text):
    """The first 12 hex of the prompt's sha256: the same shape as email's prompt_sha256_12."""
    return hashlib.sha256((text or "").encode("utf-8", "replace")).hexdigest()[:12]


def repo():
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    for d in HERE.parents:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    return None


def _rel(p):
    """A path as the record stores it: repo-relative, or None (builder card rule 4: no machine paths)."""
    try:
        r = repo()
        return str(Path(p).resolve().relative_to(r)) if r else None
    except (ValueError, OSError, TypeError):
        return None


def who():
    """The person id the repo's git email resolves to (team/people/<id>/identity.json), or ""."""
    r = repo()
    key = str(r)
    if key in _who:
        return _who[key]
    pid = ""
    try:
        email = subprocess.run(["git", "config", "user.email"], cwd=str(r), capture_output=True, text=True,
                               timeout=10).stdout.strip().casefold()
        for ident in sorted((r / "team" / "people").glob("*/identity.json")) if email else []:
            try:
                txt = ident.read_text(encoding="utf-8").casefold()
            except OSError:
                continue
            if f'"{email}"' in txt:
                pid = ident.parent.name
                break
    except Exception:
        pid = ""
    _who[key] = pid
    return pid


def caller():
    """The script outside run-kit that made this call, repo-relative."""
    try:
        f = sys._getframe(1)
        kit = HERE.parent
        while f is not None:
            p = Path(f.f_code.co_filename)
            if p.suffix == ".py" and kit not in p.resolve().parents and p.name != "lean_call.py":
                return _rel(p) or p.name
            f = f.f_back
    except Exception:
        pass
    return None


# --- the context model.call hands down to the door -------------------------------------------------------------

def set_context(**fields):
    _ctx.fields = {k: v for k, v in fields.items() if v is not None}
    _ctx.wrote = 0


def clear_context():
    _ctx.fields = {}
    _ctx.wrote = 0


def context():
    return dict(getattr(_ctx, "fields", {}) or {})


def wrote():
    """How many lines the door wrote for the call in flight (model.call writes its own when the door wrote none)."""
    return getattr(_ctx, "wrote", 0)


# --- writing ---------------------------------------------------------------------------------------------------

def _daily(person):
    root = Path(LOG_ROOT) if LOG_ROOT else ((repo() / "runs" / "what-ran") if repo() else None)
    if root is None:
        return None
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return root / (person or "unknown") / f"{day}.jsonl"


def note(run_dir=None, **fields):
    """Append one line: into <run_dir>/what-ran.jsonl, else the daily log. No-op while off; never raises.
    Returns the row written, or None."""
    if not on():
        return None
    try:
        ctx = context()
        run_dir = run_dir or ctx.pop("run_dir", None)
        ctx.pop("run_dir", None)
        row = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               **ctx, **{k: v for k, v in fields.items() if v is not None}}
        row.setdefault("ran_by", who())
        if run_dir:
            dest = Path(run_dir) / FILE
        else:
            dest = _daily(row["ran_by"])
            if dest is None:
                return None
        line = json.dumps(row, ensure_ascii=False) + "\n"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            with open(dest, "a", encoding="utf-8") as f:
                f.write(line)
        _ctx.wrote = getattr(_ctx, "wrote", 0) + 1
        return row
    except Exception:
        return None


def rows(path):
    """Every row of a what-ran file, or of <run folder>/what-ran.jsonl; lines that are not JSON are skipped."""
    p = Path(path)
    p = p / FILE if p.is_dir() else p
    out = []
    if not p.is_file():
        return out
    for ln in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out
