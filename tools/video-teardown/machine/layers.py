"""Teardown v2 (2026-10-18): the four layers, the owner's worked examples, and the
real cost of every stage.

Only the v2 chain uses this file (VT_CHAIN=v2, or run.py --v2). v1 never
imports it, so nothing the owner runs today changes.

The four layers every swipe gets at triage (structure confirmed at 1c):
  format     who carries it + the script shape   (elements format.video.json)
  style      what every picture looks like       (elements style.video.json)
  structure  the beat-by-beat build              (elements structure.video.json)
  made       how our version gets made: from-scratch / cast-swap / real-footage
Test between style and format: swap it and the script, cast and beats stay →
style; the script or who carries it changes → format.

Choices are only the rows the owner has NOT parked: what the Outlier Lists tab
shows (rows with swipes or ads, plus runs/video-teardown/unparked.json). His
hand tags (runs/video-teardown/layer-edits.json) always outrank triage. A value
not on the list comes back "new:<name>" and the run stops before writing until
his call lands in runs/video-teardown/format-calls.json (Outlier → Create →
Swipes).
"""
import json
import os
import re
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
LIB = WS / "components" / "elements" / "library"
TEARDOWN_RUNS = WS / "runs" / "video-teardown"
LISTS_URL = os.environ.get("VT_LISTS_URL", "http://127.0.0.1:8880/api/lists")

ELEMENTS = ("format", "style", "structure")
MADE = [
    ("from-scratch", "every picture and voice is generated new — nothing filmed is reused (animation, stylised looks, or a cast we make)"),
    ("cast-swap", "the swipe's own footage is kept — motion, timing, camera — and our character and product are swapped into it"),
    ("real-footage", "real filmed footage carries it — a creator films it, or our own archive / product B-roll is cut to it"),
]

# Price per million tokens, input / output (thinking is billed as output).
# Gemini returns its token counts; the dollars are these list prices.
PRICES = {
    "gemini-3.1-pro": (2.00, 12.00),
    "gemini-3-pro": (2.00, 12.00),
    "gemini-3.5-flash": (0.50, 3.00),
    "gemini-3-flash": (0.50, 3.00),
}


def _read(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


# ── the lists ────────────────────────────────────────────────────────────────

def _bank(el):
    return [r for r in _read(LIB / f"{el}.video.json", {}).get("rows", [])
            if r.get("status") != "deprecated"]


_ACTIVE = {}
LISTS_FILE = "lists.json"     # under TEARDOWN_RUNS: the last answer Outlier gave, committed for machines without it


class ListsMissing(RuntimeError):
    """No Outlier and no committed lists file: the run refuses rather than offer parked rows."""


def _snapshot(got):
    """Write Outlier's live lists (ids and plain names only) to runs/video-teardown/lists.json when they changed,
    so a machine with no Outlier (the mini) reads the same lists (blocker 6, 2026-10-21). Never raises."""
    try:
        keep = {el: [{k: x.get(k) for k in ("id", "name", "swipes", "ads") if k in x} for x in (got.get(el) or [])]
                for el in ELEMENTS}
        for el in ELEMENTS:
            keep[el + "_parked"] = list(got.get(el + "_parked") or [])
        f = TEARDOWN_RUNS / LISTS_FILE
        old = _read(f, {})
        if {k: v for k, v in old.items() if k != "_taken"} == keep:
            return
        keep["_taken"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "from": LISTS_URL}
        tmp = f.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(keep, indent=1, ensure_ascii=False) + "\n")
        tmp.replace(f)
    except Exception:
        pass


def active(el):
    """(rows, where) — the rows of this element the owner has not parked.

    The Outlier Lists tab is the one place that decides parked (rows with
    swipes or ads, plus unparked.json); it is read, never re-derived, and each
    answer is kept in runs/video-teardown/lists.json. When the page is not up
    (the mini), that file is read and `where` names it and when it was taken.
    With neither, the run REFUSES (ListsMissing) — never the whole library,
    parked rows included (blocker 6, 2026-10-21)."""
    if el in _ACTIVE:
        return _ACTIVE[el]
    bank = {r["id"]: r for r in _bank(el)}
    ids, where = None, "Outlier Lists tab"
    try:
        with urllib.request.urlopen(LISTS_URL, timeout=60) as r:
            got = json.loads(r.read() or b"{}")
        ids = [x["id"] for x in got.get(el) or []]
        _snapshot(got)
    except Exception as e:
        f = TEARDOWN_RUNS / LISTS_FILE
        snap = _read(f, None)
        if not isinstance(snap, dict) or not isinstance(snap.get(el), list):
            raise ListsMissing(
                f"the {el} list cannot be read: Outlier is not reachable ({type(e).__name__}) and there is no "
                f"runs/video-teardown/{LISTS_FILE} — run a teardown once where Outlier is up (the owner's Mac) and "
                f"commit that file; the whole library, parked rows included, is never offered")
        ids = [x["id"] for x in snap[el] if isinstance(x, dict) and x.get("id")]
        taken = (snap.get("_taken") or {}).get("at") or "an unknown time"
        where = f"runs/video-teardown/{LISTS_FILE}, Outlier's answer taken {taken} (Outlier not reachable: {type(e).__name__})"
    for extra in (_read(TEARDOWN_RUNS / "unparked.json", {}).get(el) or []):
        if extra not in ids:
            ids.append(extra)
    rows = [bank[i] for i in ids if i in bank]
    _ACTIVE[el] = (rows, where)
    return _ACTIVE[el]


def aliases(el):
    return {a: r["id"] for r in _bank(el) for a in (r.get("aliases") or [])}


def compact(rows, beats=True):
    """id · plain name · what it is (· beats) — one block per row, no JSON."""
    out = []
    for r in rows:
        line = f"- `{r['id']}` — {r.get('name') or r['id']}: {(r.get('what') or '').strip()}"
        b = (r.get("extra") or {}).get("beats") if beats else None
        if b:
            line += "\n  beats: " + " → ".join(str(x) for x in b)
        out.append(line)
    return "\n".join(out)


def made_list():
    return "\n".join(f"- `{k}` — {v}" for k, v in MADE)


# ── the owner's worked examples ──────────────────────────────────────────────────

def _record_dir(record):
    for base in (TEARDOWN_RUNS / "_work", *[p for p in TEARDOWN_RUNS.iterdir() if p.is_dir() and not p.name.startswith("_")]):
        d = base / record
        if (d / "stages" / "0-triage.md").is_file():
            return d
    return None


def signature(record):
    """What the swipe is, in its own triage's words: category + one line."""
    d = _record_dir(record)
    if not d:
        return None
    t = (d / "stages" / "0-triage.md").read_text()
    get = lambda k: (re.search(rf"^{k}:\s*(.+)$", t, re.M) or [None, ""])[1].strip()
    sig = " · ".join(x for x in (get("CATEGORY"), get("ONE LINE")) if x)
    return sig[:400] or None


def teaching_block(skip_key=None):
    """Per element and row, the swipes the owner placed there by hand, described.

    skip_key: this swipe's own key, left out so a re-run is not shown its own answer."""
    te = _read(TEARDOWN_RUNS / "teaching-examples.json", {})
    out = []
    for el in ELEMENTS + ("made",):
        rows = te.get(el) or {}
        if not rows:
            continue
        out.append(f"#### {el.upper()}")
        for rid, xs in rows.items():
            sigs = [signature(x["record"]) for x in xs if x.get("key") != skip_key]
            sigs = [s for s in sigs if s]
            if sigs:
                out.append(f"`{rid}` — the owner put these here:")
                out.extend(f"  - {s}" for s in sigs[:5])
    return "\n".join(out) or "(no hand-sorted examples yet)"


# ── this swipe ───────────────────────────────────────────────────────────────

def swipe_key(video):
    """The Outlier key of a swipe: ig:<code> for a saved Instagram post."""
    p = Path(video or "")
    if p.parent.parent.name == "swipe-videos":
        return "ig:" + p.parent.name
    return None


def hand_tags(key):
    if not key:
        return {}
    ed = _read(TEARDOWN_RUNS / "layer-edits.json", {})
    for k, v in ed.items():
        if k.lower() == key.lower():
            return dict(v)
    return {}


LINE = {el: re.compile(rf"^[ \t]*\**{el}\**[ \t]*:[ \t]*\**[ \t]*`?([a-z0-9][a-z0-9:_-]*)`?", re.I | re.M)
        for el in ("FORMAT", "STYLE", "STRUCTURE", "MADE")}


def parse(text):
    out = {}
    for el, rx in LINE.items():
        for m in rx.finditer(text or ""):
            v = m.group(1).strip().lower().rstrip(":")
            if v and v not in ("format", "style", "structure", "made", "new"):
                out[el.lower()] = v
                break
    return out


def settle(st, read, key):
    """Merge triage's read with the owner's hand tags (his win) onto the run."""
    lay = dict(st.get("layers") or {})
    src = dict(lay.pop("_from", {}) or {})
    for el in ELEMENTS + ("made",):
        v = read.get(el)
        if v and el in ELEMENTS and not v.startswith("new:"):
            v = aliases(el).get(v, v)
            if v not in {r["id"] for r in active(el)[0]}:
                v = "new:" + v            # a parked or unknown id is not on the list
        if v:
            lay[el], src[el] = v, "triage"
    for el, v in hand_tags(key).items():
        if el in ELEMENTS:
            v = aliases(el).get(v, v)
        lay[el], src[el] = v, "owner"
    lay["_from"] = src
    st["layers"] = lay
    if lay.get("style"):
        st["style_id"] = lay["style"]
    if lay.get("format"):
        st["format_id"] = lay["format"]
    st["layers_pending"] = pending(lay, key)
    return lay


def call_for(name, key=None, el="format", calls=None):
    """the owner's call on a new layer name, or None. THE ONE READER (2026-10-19).

    Outlier's Swipes tab saves a call under the BARE name ("xyz", swipe_layers.save_call),
    while the readers looked it up as "format:new:xyz", "new:xyz" or "<key>|format" — so a call
    made on Outlier never released a held run. Every reader asks here, with any of those shapes."""
    calls = _read(TEARDOWN_RUNS / "format-calls.json", {}) if calls is None else calls
    n = str(name or "")
    if ":new:" in n:                      # "format:new:xyz"
        el, n = n.split(":", 1)[0], n.split(":", 1)[1]
    bare = n[4:] if n.startswith("new:") else n
    for k in (bare, "new:" + bare, f"{el}:new:{bare}", f"{key}|{el}" if key else None):
        if k and isinstance(calls.get(k), dict):
            return calls[k]
    return None


def pending(lay, key):
    """Every new:<name> still waiting for the owner's call on Outlier."""
    calls = _read(TEARDOWN_RUNS / "format-calls.json", {})
    out = []
    for el in ELEMENTS:
        v = lay.get(el) or ""
        if not v.startswith("new:"):
            continue
        if not call_for(v, key=key, el=el, calls=calls):
            out.append(f"{el}:{v}")
    return out


# ── 1k's view of the record ─────────────────────────────────────────────────

def record_brief(record):
    """The cast, places, props, core message and every spoken line — what the
    culture read needs beside the video it is watching. The shot table and the
    scene mechanics stay out: the model sees the video itself."""
    t = record or ""
    keep = []
    m = re.search(r"\*\*CAST\*\*.*?(?=^\|\s*Timestamp)", t, re.S | re.M)
    if m:
        keep.append(m.group(0).strip())
    m = re.search(r"\*\*6\. THE CORE MESSAGE\*\*.*?(?=^###|\Z)", t, re.S | re.M)
    if m:
        keep.append(m.group(0).strip())
    m = re.search(r"^### VERBATIM TRANSCRIPT.*?(?=^### (?!VERBATIM)|\Z)", t, re.S | re.M)
    if m:
        keep.append(m.group(0).strip())
    return "\n\n".join(keep) if keep else t


# ── cost and time ────────────────────────────────────────────────────────────

def log_path():
    return os.environ.get("VT_USAGE_LOG")


# The stage a paid call is filed under. Per THREAD since 2026-10-21 (video-system sync W31): two teardown
# stages may run side by side, and the shared VT_USAGE_STAGE env would file one's calls under the other.
import threading as _threading  # noqa: E402
USAGE = _threading.local()


def log(entry):
    p = log_path()
    if not p:
        return
    entry = dict(entry, stage=getattr(USAGE, "stage", None) or os.environ.get("VT_USAGE_STAGE", "?"), at=time.time())
    with open(p, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_gemini(url, reply):
    """One Gemini call: its model and token counts, priced."""
    if not log_path() or not isinstance(reply, dict):
        return
    u = reply.get("usageMetadata") or {}
    m = re.search(r"/models/([^:/?]+)", url or "")
    model = m.group(1) if m else "?"
    tin = u.get("promptTokenCount") or 0
    tout = (u.get("candidatesTokenCount") or 0) + (u.get("thoughtsTokenCount") or 0)
    pi, po = next((v for k, v in PRICES.items() if model.startswith(k)), (2.0, 12.0))
    if tin > 200_000 and "pro" in model:
        pi, po = pi * 2, po * 1.5
    log(dict(kind="gemini", model=model, tokens_in=tin, tokens_out=tout,
             cost_usd=round(tin / 1e6 * pi + tout / 1e6 * po, 5)))


def stage_cost(key, since=0):
    """(dollars, calls) logged for one stage since `since` (this pass only)."""
    p = log_path()
    if not p or not Path(p).is_file():
        return None, 0
    tot, n = 0.0, 0
    for line in Path(p).read_text().splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("stage") == key and (e.get("at") or 0) >= since:
            tot += e.get("cost_usd") or 0
            n += 1
    return round(tot, 4), n
