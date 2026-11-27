"""THE THREE NAMES every swipe, winner and brief carries (owner, 2026-11-19): script format (what it says),
production format (how it's made) and style (what it looks like), each a locked name from
components/video-production/formats/names.json, or a DEFINE the owner rules.

Triage v5 writes them as three lines:
    SCRIPT FORMAT: remedy — <why>
    PRODUCTION FORMAT: single-presenter — <why>
    STYLE: phone-ugc — <why>
or, when nothing on the list fits:
    SCRIPT FORMAT: DEFINE: <its own name> — <its own words>

A DEFINE is carried as `new:<name>` (the teardown's existing convention), waits in `names_pending` as
`<kind>:new:<name>`, and is released by the owner's call in runs/video-teardown/format-calls.json, read through
layers.call_for (fold into a locked name / own / drop). A triage written before v5 has no such lines: its names are
read by rule from what it did write (sound form, format, style), the same rules the backfill uses.

Library only. Writes nothing but the run state handed to it, and runs/video-teardown/names-backfill.json when asked.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
NAMES_FILE = WS / "components" / "video-production" / "formats" / "names.json"
TEARDOWN_RUNS = WS / "runs" / "video-teardown"
BACKFILL = TEARDOWN_RUNS / "names-backfill.json"

KINDS = ("script_format", "production_format", "style")          # every ad carries these three
OPTIONAL = ("hook_format", "headline_format")                     # what you see first / the words first, when there are
ALL = KINDS + OPTIONAL
LINE_WORD = {"script_format": "SCRIPT FORMAT", "production_format": "PRODUCTION FORMAT", "style": "STYLE",
             "hook_format": "HOOK FORMAT", "headline_format": "HEADLINE FORMAT"}
TITLE = {"script_format": "Script format", "production_format": "Production format", "style": "Style",
         "hook_format": "Hook format", "headline_format": "Headline format", "length": "Length"}
LONG_OVER_S = 120                                                  # Long = over 2 minutes (a VSL is Long, owner 2026-11-19)


def locked():
    """{kind: {id: {name, what}}} from names.json — the only names there are."""
    d = json.loads(NAMES_FILE.read_text(encoding="utf-8"))
    return {k: {n["id"]: n for n in d[k]["names"]} for k in ALL if k in d}


def name_of(kind, nid):
    if not nid:
        return None
    if str(nid).startswith("new:"):
        return "DEFINE: " + nid[4:]
    return (locked()[kind].get(nid) or {}).get("name") or nid


def render():
    """The three lists for the triage prompt: id, name, what it is."""
    out = []
    every = json.loads(NAMES_FILE.read_text(encoding="utf-8"))
    for k in ALL:
        if k not in every:
            continue
        d = every[k]
        out.append("%s — %s:" % (LINE_WORD[k], d["means"]))
        for n in d["names"]:
            out.append("- `%s` — %s%s" % (n["id"], n["name"], (": " + n["what"]) if n.get("what") else ""))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:60] or "unnamed"


DEFINE = re.compile(r"^([ \t]*\**(?:SCRIPT FORMAT|PRODUCTION FORMAT|HOOK FORMAT|HEADLINE FORMAT|STYLE|FORMAT)\**[ \t]*:[ \t]*\**[ \t]*)DEFINE[ \t]*:[ \t]*`?([^`—–\n]+?)`?[ \t]*(—|–|$)",
                    re.I | re.M)


def normalize(text):
    """`STYLE: DEFINE: Glass toy — …` -> `STYLE: new:glass-toy — …`, so every existing reader of the lines (and the
    owner's call path) treats a DEFINE exactly like the `new:<name>` it always meant."""
    return DEFINE.sub(lambda m: "%snew:%s %s" % (m.group(1), _slug(m.group(2)), m.group(3)), text or "")


def _line(text, word):
    m = re.search(r"^[ \t]*\**%s\**[ \t]*:[ \t]*\**[ \t]*`?([a-z0-9][a-z0-9:_-]*)`?(.*)$" % word, text or "", re.I | re.M)
    if not m:
        return None, ""
    why = re.sub(r"^[\s`*]*(?:—|–|-|·|:)?\s*", "", m.group(2)).strip().strip("*").strip()
    return m.group(1).strip().lower(), why[:600]


def read(text):
    """{kind: (id or 'new:<name>' or None, why)} off triage v5's three lines. Absent lines are absent."""
    t = normalize(text)
    out = {}
    for k in ALL:
        v, why = _line(t, LINE_WORD[k])
        if k in OPTIONAL and v == "none":
            out[k] = (None, why or "no scroll stopper: the opening is the body starting")
        elif v and v not in ("define", "new", "none"):
            out[k] = (v, why)
    return out


# ── the rules for a triage written before v5 (also the backfill) ─────────────

_PF_IDS = ("single-presenter", "song-ad", "narrator-montage", "multi-speaker-scene", "short-movie", "text-thread")


def _voices(run):
    try:
        return int(json.loads((Path(run) / "sound-sheet.json").read_text(encoding="utf-8")).get("voices") or 0)
    except (OSError, ValueError, TypeError):
        return 0


def production_by_rule(sound, fmt_id, words, voices):
    s, w = (sound or "").upper(), ((fmt_id or "") + " " + (words or "")).lower()
    if fmt_id in _PF_IDS:
        return fmt_id, "the triage named it"
    if re.search(r"text messages?|chat screen|messaging app|screen recording of a (private )?chat|text thread", w):
        return "text-thread", "told in messages on a phone screen"
    if s.startswith(("SUNG", "RAPPED")):
        return "song-ad", "sound form %s" % s.split()[0].lower()
    if s.startswith("MUSIC ONLY"):
        return "short-movie", "music only, no words"
    if re.search(r"voice-?over|narrat|off-camera|off-screen voice|unseen narrator|nobody speak|no on-camera", w):
        return "narrator-montage", "one voice over shots"
    if voices >= 2 or re.search(r"\b(two|three|four)\b[^.]{0,40}\b(people|presenters|characters|speakers)\b|interview|skit|duet|stitch|conversation", w):
        return "multi-speaker-scene", ("%d voices" % voices) if voices >= 2 else "people talking to each other"
    if s.startswith("SPOKEN"):
        return "single-presenter", "one voice, on camera"
    return None, "no sound form read"


def runtime_s(text, run=None):
    """Seconds the swipe runs: the sound sheet's own measure, else the triage's RUNTIME line (mm:ss)."""
    if run:
        try:
            v = float(json.loads((Path(run) / "sound-sheet.json").read_text(encoding="utf-8")).get("seconds") or 0)
            if v:
                return v
        except (OSError, ValueError, TypeError):
            pass
    m = re.search(r"^RUNTIME:\s*(?:(\d+):)?(\d+):(\d+)", text or "", re.M)
    if m:
        return int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    return None


def length(text, run=None):
    """('short' | 'long', why) from the runtime, or None when no runtime is on file."""
    s = runtime_s(text, run)
    if not s:
        return None
    return ("long" if s > LONG_OVER_S else "short"), "runs %d s (Long is over %d s)" % (s, LONG_OVER_S)


def by_rule(text, run=None):
    """What a pre-v5 triage says, put into the three names. A value the locked list does not hold comes back as
    `new:<what the triage called it>` with the triage's own words, never a guess."""
    t = normalize(text)
    lk = locked()
    fmt, fwhy = _line(t, "FORMAT")
    sty, swhy = _line(t, "STYLE")
    fmt = (fmt[4:] if fmt and fmt.startswith("new:") and fmt[4:] in lk["script_format"] else fmt)
    sty = (sty[4:] if sty and sty.startswith("new:") and sty[4:] in lk["style"] else sty)
    sound = (re.search(r"^SOUND FORM:\s*(.+)$", t, re.M) or [None, ""])[1]
    one = (re.search(r"^ONE LINE:\s*(.+)$", t, re.M) or [None, ""])[1]
    out = {}
    if fmt in lk.get("hook_format", {}):
        # a scroll stopper the triage filed as its format: the hook is named, the body's script format is not
        out["hook_format"] = (fmt, "the triage named it: " + fwhy)
        fmt = None
    pf, pwhy = production_by_rule(sound, fmt, fwhy + " " + one, _voices(run) if run else 0)
    out["production_format"] = (pf, "by rule: " + pwhy) if pf else ("new:unread", "no sound form or format in the triage")
    if fmt in lk["script_format"]:
        out["script_format"] = (fmt, "the triage named it: " + fwhy)
    elif fmt and fmt not in _PF_IDS:
        out["script_format"] = ("new:" + fmt.replace("new:", ""), fwhy or one)
    else:
        out["script_format"] = ("new:unnamed", one or fwhy or "the triage named no script format")
    sty = sty or "phone-ugc"
    out["style"] = (sty, swhy or "no style named: phone-camera UGC") if sty in lk["style"] else \
        ("new:" + sty.replace("new:", ""), swhy)
    return out


# ── onto a run ───────────────────────────────────────────────────────────────

def _calls():
    try:
        return json.loads((TEARDOWN_RUNS / "format-calls.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def call_for(kind, nid, calls=None):
    """The owner's call on a DEFINE, through the teardown's one call reader."""
    import layers as L
    return L.call_for(nid, el=kind, calls=_calls() if calls is None else calls)


def settle(st, text, trail_add=None, run=None):
    """Put the three names on the run: st['names'] {kind: id}, st['names_why'], st['names_pending'] (DEFINEs with no
    call yet). Triage v5's lines win; a triage without them is read by rule and says so. Each name goes on the trail
    with its reason (stage teardown)."""
    got = read(text)
    how = "the triage"
    if len(got) < len(KINDS):
        rule = by_rule(text, run)
        for k in KINDS:
            if k not in got:
                got[k] = rule[k]
        how = "the triage (names read by rule where it wrote none)"
    names = {k: got[k][0] for k in KINDS}
    for k in OPTIONAL:
        if k in got:
            names[k] = got[k][0]
    ln = length(text, run)
    if ln:
        names["length"] = ln[0]
        got["length"] = ln
    st["names"] = names
    st["names_why"] = {k: got[k][1] for k in names if k in got and got[k][1]}
    calls = _calls()
    st["names_pending"] = ["%s:%s" % (k, v) for k, v in names.items()
                           if str(v).startswith("new:") and not call_for(k, v, calls)]
    if trail_add:
        for k in [k for k in ALL if k in names]:
            trail_add(st, "0", "The swipe's " + TITLE[k].lower(), name_of(k, names[k]), st["names_why"].get(k), how)
    return names


def apply_calls(st):
    """The owner's calls on DEFINEs, applied: fold -> the locked name; drop -> none; own -> kept (approved)."""
    names = dict(st.get("names") or {})
    calls = _calls()
    for k, v in list(names.items()):
        if str(v).startswith("new:"):
            c = call_for(k, v, calls)
            if c and c.get("decision") == "fold" and c.get("into"):
                names[k] = c["into"]
            elif c and c.get("decision") == "drop":
                names[k] = None
    st["names"] = names
    st["names_pending"] = [p for p in (st.get("names_pending") or [])
                           if not call_for(p.split(":", 1)[0], p.split(":", 1)[1], calls)]
    return st


def missing(st):
    """What stops a brief: each name that is neither locked nor called by the owner. [] = the brief may be written."""
    lk, calls, out = locked(), _calls(), []
    names = st.get("names") or backfilled(st) or {}
    for k in KINDS:
        v = names.get(k)
        if v and v in lk[k]:
            continue
        if v and str(v).startswith("new:") and call_for(k, v, calls) and call_for(k, v, calls).get("decision") == "own":
            continue
        out.append("%s %s" % (TITLE[k].lower(), "DEFINE " + v[4:] + " (waiting for the owner's call)"
                              if v and str(v).startswith("new:") else "not named"))
    return out


def backfilled(st):
    """The backfill's names for a run torn down before v5, by its slug; None when it has none."""
    try:
        rows = json.loads(BACKFILL.read_text(encoding="utf-8")).get("runs") or {}
    except (OSError, ValueError):
        return None
    key = "%s/%s" % (st.get("brand") or "", st.get("slug") or st.get("label") or "")
    r = rows.get(key) or rows.get(st.get("slug") or "")
    return dict(r["names"]) if r else None


def backfill(reads=None):
    """Every teardown run with a triage and no names, read by rule, recorded as data in names-backfill.json. Old run
    folders are not touched. `reads`: {"<brand>/<slug>": {"script_format": <locked id>, "why"}} — a script format
    read off the triage's own words where the rule finds none (taken only when it is a locked id)."""
    reads = reads or {}
    rows = {}
    for tri in sorted(TEARDOWN_RUNS.glob("*/*/stages/0-triage.md")):
        run = tri.parent.parent
        if run.parent.name.startswith("_"):
            continue
        try:
            st = json.loads((run / "run.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            st = {}
        if isinstance(st.get("names"), dict) and all(st["names"].get(k) for k in KINDS):
            continue
        got = by_rule(tri.read_text(encoding="utf-8", errors="replace"), run)
        key = "%s/%s" % (run.parent.name, run.name)
        r = reads.get(key) or {}
        if got["script_format"][0] in ("new:unnamed",) and r.get("script_format") in locked()["script_format"]:
            got["script_format"] = (r["script_format"], "read from the triage's words: " + (r.get("why") or ""))
        ln = length(tri.read_text(encoding="utf-8", errors="replace"), run)
        if ln:
            got["length"] = ln
        rows[key] = {"names": {k: got[k][0] for k in ALL + ("length",) if k in got},
                     "why": {k: got[k][1] for k in ALL + ("length",) if k in got}}
    import datetime
    BACKFILL.write_text(json.dumps({
        "_what": "The three video names (components/video-production/formats/names.json) for teardown runs read before "
                 "triage v5, by rule from what their triage wrote. new:<name> = a DEFINE waiting for the owner's call. "
                 "Written by video_names.backfill(); run folders are not touched.",
        "as_of": datetime.date.today().isoformat(), "runs": rows}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return rows


def defines(rows=None):
    """Every DEFINE waiting, grouped: {(kind, name): [run keys]} — one owner card per group."""
    if rows is None:
        try:
            rows = json.loads(BACKFILL.read_text(encoding="utf-8")).get("runs") or {}
        except (OSError, ValueError):
            rows = {}
    calls, out = _calls(), {}
    for key, r in rows.items():
        for k, v in (r.get("names") or {}).items():
            if v in ("new:unnamed", "new:unread"):
                continue                  # never read, not a new name: a v5 re-read names it, the owner is not asked
            if v and str(v).startswith("new:") and not call_for(k, v, calls):
                out.setdefault((k, v[4:]), []).append(key)
    return out
