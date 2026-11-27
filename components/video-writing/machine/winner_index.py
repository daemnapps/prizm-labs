#!/usr/bin/env python3
"""Winner index: one record per banked winner of a brand, and the trait sheet every swipe is matched on.

    python3 winner_index.py build --brand brand_a      writes runs/winners/<brand>/winner-index.json and .md
    python3 winner_index.py show  <run>               the trait sheet of one teardown run (winner or swipe)

A record is read from files that already exist, with no model call and no spend:
  traits   the run's teardown: 0-triage (runtime, sound, style, format, one line), 1c-doctrine (framework, sections
           in order, awareness in and out, sophistication, mass desire), transcript (words, speakers)
  proof    the brand's winner registry (purchases, cost per sale, return, months it ran, what it argues, hook,
           offer) and the bank (`runs/winners/<brand>/bank.json`: spend, purchases, first and last month)
  post     the original post date (post-talk.json)
A brand with no registry still gets proof: the bank row of the audit video the run tore down (`run.json` `video`
`.../<since>_<until>/videos/NN-<name>.mp4`, from the audit's `videos` step, is the row whose `source.teardown` is `.../teardowns/NN-<name>/...`).
A winner whose teardown has no 1c read takes awareness from the registry's teardown notes; a creator copy
(`<run>-creator`) or a second run of the same post is folded under its parent and carries the parent's proof.

The trait sheet is the one shape `winner_match.py` compares; a swipe's sheet is built the same way, so the swipe
and the winner are always read from their own teardowns on the same terms.
"""
import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get("DAEMN_WORKSPACE") or HERE.parents[2])
RUNS = Path(os.environ.get("VIDEO_STUDIO_WRITING") or WS / "runs" / "video-teardown" / "_work")

LADDER = ["unaware", "problem-aware", "solution-aware", "product-aware", "most-aware"]

# format families: two formats in one family carry the same kind of scene
FAMILIES = {
    "hook-then-pitch": r"dramatic-continuation",
    "scene": r"micro-drama|skit|sketch|drama|street-interview|multi-speaker|confrontation|dialogue|stitch",
    "presenter": r"single-presenter|founder|vsl|talking|presenter|confessional|podcast",
    "demo": r"demonstration|unboxing|product-focus|hands-and-voiceover|routine",
    "montage": r"montage|compilation",
}

TONES = {
    "funny": r"\b(absurd|wry|dry humou?r|self-deprecating|deadpan|comedy|comedic|meme|parody|gag)",
    "drama": r"(micro-drama|drama|tense|serious|suspense|cinematic-narrative|prestige)",
    "educational": r"(explain|educat|teach|lesson|how-to|tutorial|clinical|lecture|whiteboard)",
    "testimonial": r"(testimonial|confessional|review|before-and-after|glow-up)",
    "story": r"(storyteller|story|parable|founder)",
    "hype": r"(hype|staccato|lip-sync|urgent)",
    "demo": r"(demonstration|hands-and-voiceover|unboxing|product-focus|montage of)",
}


def _read(p):
    try:
        return Path(p).read_text()
    except OSError:
        return ""


def _json(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _secs(txt):
    m = re.search(r"(\d+):(\d{2})(?::(\d{2}))?", txt or "")
    if not m:
        return None
    a, b, c = m.groups()
    return int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)


def mmss(s):
    return "%d:%02d" % divmod(int(s), 60) if s else "?"


def _field(text, key):
    m = re.search(r"^" + key + r":\s*(.+)$", text, re.M)
    return m[1].strip() if m else ""


def _bold(text, key):
    """A `**KEY:** value` line of a 1c read, the value up to the line's end."""
    m = re.search(r"^\*\*" + key + r":\*\*\s*(.*)$", text, re.M)
    return m[1].strip() if m else ""


def awareness_word(text):
    t = (text or "").lower().replace("`", "")
    for w in LADDER:
        if t.startswith(w) or t.startswith(w.replace("-aware", " aware")):
            return w
    hits = [w for w in LADDER if w in t]
    return hits[0] if hits else ""


def sophistication_word(text):
    t = (text or "").lower()
    for w in ("a mechanism", "the claim enlarged", "the plain claim", "identification only", "a new mechanism"):
        if t.startswith(w):
            return w.replace("a ", "", 1) if w.startswith("a ") else w
    return t.split(".")[0][:30] if t else ""


def sections(doc):
    m = re.search(r"\*\*SECTIONS CARRIED:\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)", doc, re.S)
    found = re.findall(r"([a-z][a-z-]+)\s+\d+:\d", m[1]) if m else []
    out = []
    for s in found:                       # consecutive repeats collapse; order is what is carried
        if not out or out[-1] != s:
            out.append(s)
    return out


def family(fmt):
    for f, rx in FAMILIES.items():
        if re.search(rx, fmt or "", re.I):
            return f
    return ""


def hook_kind(line):
    t = (line or "").lower()
    if not t:
        return ""
    if re.search(r"\bpov\b", t):
        return "pov"
    if re.search(r"sorry|apologi|hardest|confess|lied|accountab", t):
        return "confession"
    if re.search(r"\$\d|sale|free|% off|deal|for \$", t):
        return "offer"
    if re.search(r"reply|comment", t):
        return "comment reply"
    if "?" in t[:160]:
        return "question"
    return "statement"


def _first_line(run_dir):
    tr = _json(run_dir / "transcript.json", []) or []
    for t in tr:
        if isinstance(t, dict) and str(t.get("text", "")).strip():
            return re.sub(r"\[[^\]]*\]", "", str(t["text"])).strip()
    txt = _read(run_dir / "stages" / "1-transcript.md")
    for ln in txt.splitlines():
        ln = re.sub(r"\*\*[^*]*\*\*|\[[^\]]*\]|^\s*[-*]\s*|\d+:\d+(\.\d+)?", "", ln).strip(" :|-")
        if len(ln.split()) >= 3:
            return ln
    return ""


def traits(run):
    """The trait sheet of one teardown run, from its files only. None when it has no triage."""
    d = RUNS / run
    tri = _read(d / "stages" / "0-triage.md")
    if not tri:
        return None
    rec = _json(d / "run.json", {}) or {}
    doc = _read(d / "stages" / "1c-doctrine.md")
    dj = _json(d / "doctrine.json", {}) or {}          # older runs kept the read as json
    fmt_line = _field(tri, "FORMAT")
    fmt_id = rec.get("format_id") or fmt_line.split(" — ")[0].strip()
    fmt_id = fmt_id.replace("new:", "")
    style = (rec.get("style_id") or _field(tri, "STYLE").split(" — ")[0]).replace("new:", "").strip(" —-")
    runtime = _secs(_field(tri, "RUNTIME"))
    tr = _json(d / "transcript.json", []) or []
    words = sum(len(re.sub(r"\[[^\]]*\]", " ", str(t.get("text", ""))).split()) for t in tr if isinstance(t, dict))
    if not tr:
        words = len(re.sub(r"\[[^\]]*\]|\*\*[^*]*\*\*", " ", _read(d / "stages" / "1-transcript.md")).split())
    speakers = {t.get("speaker") for t in tr if isinstance(t, dict) and t.get("speaker")}
    dl = dj.get("delivery") if isinstance(dj.get("delivery"), dict) else {}
    tone_text = " ".join(str(x) for x in (fmt_line, style, dl.get("delivery_style"), dl.get("humor"),
                                          _field(tri, "ONE LINE")) if x)
    tones = sorted(t for t, rx in TONES.items() if re.search(rx, tone_text, re.I))
    fam = family(fmt_id) or family(fmt_line)
    multi = fam == "scene" or len(speakers) > 1
    aw = dj.get("awareness") if isinstance(dj.get("awareness"), dict) else {}
    framework = _bold(doc, "CROSSWALK ROW") or ""
    if framework.lower().startswith("none"):
        framework = ""
    first = _first_line(d)
    return {
        "run": run, "brand": rec.get("brand"),
        "runtime": runtime, "words": words, "pace": round(words / runtime, 2) if runtime and words >= 3 else None,
        "sound": (_field(tri, "SOUND FORM").split() or [""])[0].upper(),
        "style": style, "format": fmt_id, "format_line": fmt_line, "family": fam,
        "cast": "several people in a scene" if multi else "one person",
        "tones": tones,
        "framework": framework.split(" (")[0].strip() if framework else "",
        "framework_full": framework,
        "sections": sections(doc) or [str(s) for s in (dj.get("sections_carried") or [])],
        "aware_in": awareness_word(_bold(doc, "AWARENESS ENTRY") or aw.get("entry")),
        "aware_out": awareness_word(_bold(doc, "AWARENESS EXIT") or aw.get("exit")),
        "sophistication": sophistication_word(_bold(doc, "SOPHISTICATION SIGNATURE")),
        "mass_desire": _bold(doc, "MASS DESIRE").split(". In the source")[0][:160],
        "first_line": first[:160], "hook": hook_kind(first),
        "one_line": _field(tri, "ONE LINE"),
        "has_read": bool(doc or dj),
        "post_url": rec.get("post_url"),
        "posted": _post_date(d),
    }


# THE CORE MESSAGE (2026-11-25). Every teardown since 5 Oct ends with section 6, THE CORE MESSAGE, and the spec with what
# is load-bearing and swappable; the doctrine read names the desire. The index carries all three for every winner, as
# written, so an analysis, a brief and a writing pass read one message and nobody re-sorts scripts by hand.
CORE_FIELDS = (("core", "Core message"), ("beliefs", "Beliefs under it"), ("delivery", "Delivery"), ("angle", "Angle, not message"))


def message(run):
    """The winner's message off its own run: {core, beliefs[], delivery, angle[], load_bearing[], swappable[], desire,
    enters, leaves}. A part the run does not hold is empty, never filled from anywhere else."""
    d = RUNS / run / "stages"
    out = {"core": "", "beliefs": [], "delivery": "", "angle": [], "load_bearing": [], "swappable": [],
           "desire": "", "enters": "", "leaves": ""}
    t = _read(d / "1-teardown.md")
    i = t.find("Core message")
    if i >= 0:
        s = re.sub(r"[*`]", "", re.split(r"\n### |\n---|\n> ", t[i:])[0])
        alt = "|".join(re.escape(n) for _, n in CORE_FIELDS)
        for k, n in CORE_FIELDS:
            m = re.search(re.escape(n) + r"\s*:(.*?)(?=\n\s*[-•]?\s*(?:" + alt + r")\s*:|\Z)", s, re.S)
            rows = [x for x in (re.sub(r"^[\s\-•]+", "", l).strip() for l in (m.group(1) if m else "").split("\n")) if x]
            out[k] = rows if isinstance(out[k], list) else " ".join(rows)
    sp = _read(d / "2-spec.md")
    for k, pat in (("load_bearing", r"6\. LOAD-BEARING(.*?)(?=7\. SWAPPABLE|\Z)"), ("swappable", r"7\. SWAPPABLE(.*)\Z")):
        m = re.search(pat, sp, re.S)
        # an item is a bullet or a numbered line: specs are written both ways
        out[k] = [re.sub(r"[*`]", "", re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", l)).strip() for l in (m.group(1) if m else "").split("\n")
                  if re.match(r"^\s*(?:[-*]|\d+[.)])\s+", l)]
    doc = _read(d / "1c-doctrine.md")
    for k, n in (("desire", "MASS DESIRE"), ("enters", "AWARENESS ENTRY"), ("leaves", "AWARENESS EXIT")):
        m = re.search(r"^[*\s]*" + n + r":[*\s]*(.+)$", doc, re.M)
        out[k] = m.group(1).strip() if m else ""
    return out


def message_text(run):
    """The message as a writing pass reads it; '' when the run's teardown wrote none."""
    m = message(run)
    if not m["core"]:
        return ""
    o = ["CORE MESSAGE (its own teardown): " + m["core"], "", "BELIEFS IT LANDS, with the line that carries each (the job, "
         "never a line to repeat):"] + ["- " + x for x in m["beliefs"]]
    o += ["", "DESIRE: " + (m["desire"] or "not named"), "DELIVERY: " + m["delivery"]]
    if m["load_bearing"]:
        o += ["", "LOAD-BEARING in this winner (its spec). Carry what serves the message; its look and format belong to the "
              "winner, and the swipe's own form stays:"] + ["- " + x for x in m["load_bearing"]]
    if m["angle"]:
        o += ["", "ANGLE, NOT MESSAGE (free to change):"] + ["- " + x for x in m["angle"]]
    return "\n".join(o)


def _post_date(d):
    p = (_json(d / "post-talk.json", {}) or {}).get("posted") or \
        ((_json(d / "post" / "post.info.json", {}) or {}).get("upload_date"))
    if p and re.fullmatch(r"\d{8}", str(p)):
        return f"{p[:4]}-{p[4:6]}-{p[6:]}"
    return None


# ---------------------------------------------------------------------------------------------------- the bank

def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _registry(brand):
    """The brand's winner registry rows, found through the bank's own pointer to it."""
    bank = _json(WS / "runs" / "winners" / brand / "bank.json", {}) or {}
    paths = {str((r.get("source") or {}).get("registry") or "").split("#")[0] for r in bank.get("rows") or []}
    rows = []
    for p in sorted(x for x in paths if x):
        rows += (_json(WS / p, {}) or {}).get("rows") or []
    return rows, bank.get("rows") or [], sorted(x for x in paths if x)


def _video_key(run):
    """The audit video a run tore down, as its `NN-<name>` stem; '' when the run came from anywhere else."""
    v = str((_json(RUNS / run / "run.json", {}) or {}).get("video") or "")
    p = Path(v)
    window = re.fullmatch(r"\d{4}-\d\d-\d\d_\d{4}-\d\d-\d\d", p.parent.parent.name or "")
    return p.stem if p.parent.name == "videos" and window else ""     # <...>/<since>_<until>/videos/NN-<name>.mp4


def bank_by_teardown(bank_rows):
    """Bank rows by the `NN-<name>` folder of their audit teardown (`source.teardown`)."""
    out = {}
    for b in bank_rows:
        t = str((b.get("source") or {}).get("teardown") or "")
        m = re.search(r"/teardowns/([^/]+)/", t)
        if m:
            out.setdefault(m[1], b)
    return out


def _core_named(run):
    """A run named for a Core winner: `core<N>-NN-...` or `<brand>-core<N>-NN...`."""
    return bool(re.match(r"(?:[a-z]+-)?core\d+-\d+", run))


def banked_runs(brand):
    """Every teardown run of the brand whose name carries `winner` or `core` (switched runs left out), plus the
    brand default and any listed in brands/<brand>/winners.json."""
    out = []
    dflt = (_json(WS / "brands" / brand / "winner.json", {}) or {}).get("winner")
    listed = _json(WS / "brands" / brand / "winners.json", []) or []
    for x in [dflt] + [(x.get("winner") if isinstance(x, dict) else x) for x in listed]:
        if x and x not in out:
            out.append(x)
    for d in sorted(RUNS.iterdir()) if RUNS.is_dir() else []:
        if d.name in out or "--w-" in d.name or not re.search(r"winner|core", d.name):
            continue
        if (_json(d / "run.json", {}) or {}).get("brand") == brand and (d / "stages" / "0-triage.md").is_file():
            out.append(d.name)
    return out


def _primary(r):
    """Which of two runs of one ad is the original: a Core-named run, then a finished teardown, then the shorter name."""
    return (not _core_named(r), not (RUNS / r / "stages" / "2-spec.md").is_file(), len(r), r)


def _parent(run, runs, url_of, video_of=None):
    """The run a copy is folded under: `<x>-creator` -> `<x>`; a second run of the same post or the same audit video
    -> the original (`_primary`)."""
    if run.endswith("-creator") and run[: -len("-creator")] in runs:
        return run[: -len("-creator")]
    video_of = video_of or {}
    same = [r for r in runs if r != run and not r.endswith("-creator") and
            ((url_of.get(run) and url_of.get(r) == url_of.get(run)) or
             (video_of.get(run) and video_of.get(r) == video_of.get(run)))]
    if same:
        first = min(same + [run], key=_primary)
        if first != run:
            return first
    return None


def _month_gap(a, b):
    """Whole months from month a (YYYY-MM) to month b."""
    try:
        ya, ma = map(int, a[:7].split("-"))
        yb, mb = map(int, b[:7].split("-"))
        return (yb - ya) * 12 + (mb - ma)
    except (ValueError, AttributeError):
        return None


def _clip(s, n=220):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def build(brand):
    reg, bank_rows, reg_paths = _registry(brand)
    bank_by_reg = {str((b.get("source") or {}).get("registry") or "").split("#")[-1]: b for b in bank_rows}
    bank_by_name = {}
    for b in bank_rows:
        bank_by_name.setdefault(_norm(b.get("name")), b)
    reg_by_run, reg_by_url = {}, {}
    for r in reg:
        m = re.search(r"_work/([^/`\s]+)", str(r.get("run") or ""))
        if m:
            reg_by_run[m[1]] = r
        if r.get("watch"):
            reg_by_url[r["watch"]] = r
    snapshot = (_json(WS / reg_paths[0], {}) or {}).get("snapshot") if reg_paths else None
    snapshot = snapshot or date.today().isoformat()

    runs = banked_runs(brand)
    sheets = {r: traits(r) for r in runs}
    runs = [r for r in runs if sheets[r]]
    url_of = {r: sheets[r].get("post_url") for r in runs}
    video_of = {r: _video_key(r) for r in runs}
    by_teardown = bank_by_teardown(bank_rows)
    records = []
    for run in runs:
        t = sheets[run]
        parent = _parent(run, runs, url_of, video_of)
        key = parent or run
        rg = reg_by_run.get(key) or reg_by_run.get(run) or reg_by_url.get(url_of.get(key) or "") or {}
        bk = (bank_by_reg.get(rg.get("id", "")) or bank_by_name.get(_norm(rg.get("name")))) if rg else None
        # no registry row, or one whose bank row is not pointed at: the bank row of the audit video this run
        # (or its original) tore down
        bk = bk or by_teardown.get(video_of.get(key) or "") or by_teardown.get(video_of.get(run) or "")
        snap = ((bk or {}).get("snapshots") or [{}])[0]
        ran = rg.get("ran") or ""
        first, last = (snap.get("first"), snap.get("last")) if snap.get("last") else \
            (tuple((ran.split(" to ") + [None, None])[:2]) if ran else (None, None))
        # a winner without its own 1c read borrows the parent's or copy's read, else the registry's notes
        if not t["has_read"]:
            twin = next((sheets[o] for o in runs if o != run and sheets[o]["has_read"] and
                         (o == f"{run}-creator" or _parent(o, runs, url_of) == run)), None)
            if twin:
                for k in ("framework", "framework_full", "sections", "aware_in", "aware_out", "sophistication",
                          "mass_desire"):
                    t[k] = twin[k]
                t["read_from"] = twin["run"]
            elif rg.get("awareness"):
                a = re.split(r"→|->", str(rg["awareness"]).split(".")[0])
                t["aware_in"] = awareness_word(a[0])
                t["aware_out"] = awareness_word(a[1]) if len(a) > 1 else ""
                t["read_from"] = "registry"
        gap = _month_gap(last, snapshot) if last else None
        proof = {
            "purchases": snap.get("purchases") or rg.get("purchases"),
            "spend": round(snap["spend"]) if snap.get("spend") else None,
            "cpa": snap.get("cpa") or rg.get("cpa_usd"),
            "roas": snap.get("roas") or rg.get("roas"),
            "core_rank": rg.get("rank"),
            "first_ran": first, "last_ran": last,
            "months_since_last_ran": gap,
            "live": "ran this month" if gap == 0 else (f"last ran {last}" if last else "no run dates on record"),
            "source": "bank" if snap.get("purchases") else ("registry" if rg else None),
        }
        name = label(run)
        if bk and not rg and bk.get("name"):          # no registry: the owner reads the ad's own name
            m = re.match(r"(?:[a-z]+-)?core\d*-(\d+)", run)
            name = (f"Winner #{int(m[1])} · " if m else "Winner · ") + str(bk["name"]).lower()
        records.append({
            "run": run, "label": name, "copy_of": parent, "bank_id": (bk or {}).get("id"),
            "sells": _clip(rg.get("offer") or "", 200) or None,
            "message": rg.get("message"),
            "argument": _clip(rg.get("core_message") or t["one_line"], 260),
            "hook_words": _clip(rg.get("hook") or t["first_line"], 200),
            "on_screen": rg.get("on_screen"),
            "posted": t["posted"], "watch": rg.get("watch") or t.get("post_url"),
            "traits": t, "proof": proof, "message_read": message(run),
            "registry_id": rg.get("id"),
        })
    for r in records:
        r["teardown"] = completeness(r["run"], r["traits"])
    # every proven VIDEO ad on the list is a winner, torn down or not: one with no teardown is listed so the gap shows
    have = {r.get("registry_id") for r in records if r.get("registry_id")}
    images = []
    for rg in reg:
        if rg.get("id") in have:
            continue
        if str(rg.get("format") or "").lower() != "video":
            images.append(rg.get("id"))
            continue
        bk = bank_by_reg.get(rg.get("id", "")) or bank_by_name.get(_norm(rg.get("name")))
        snap = ((bk or {}).get("snapshots") or [{}])[0]
        ran = (rg.get("ran") or "").split(" to ") + [None, None]
        first, last = (snap.get("first"), snap.get("last")) if snap.get("last") else (ran[0], ran[1])
        records.append({
            "run": None, "label": f"Winner #{rg.get('rank')} · {(rg.get('name') or rg.get('message') or '').lower()}",
            "copy_of": None, "sells": _clip(rg.get("offer") or "", 200) or None, "message": rg.get("message"),
            "argument": _clip(rg.get("core_message") or "", 260) or None, "hook_words": _clip(rg.get("hook") or "", 200) or None,
            "on_screen": rg.get("on_screen"), "posted": None, "watch": rg.get("watch"), "traits": None, "message_read": None,
            "proof": {"purchases": snap.get("purchases") or rg.get("purchases"),
                      "spend": round(snap["spend"]) if snap.get("spend") else None,
                      "cpa": snap.get("cpa") or rg.get("cpa_usd"), "roas": snap.get("roas") or rg.get("roas"),
                      "core_rank": rg.get("rank"), "first_ran": first, "last_ran": last,
                      "months_since_last_ran": _month_gap(last, snapshot) if last else None,
                      "source": "bank" if snap.get("purchases") else "registry"},
            "registry_id": rg.get("id"),
            "teardown": {"complete": False, "missing": [n for n, _ in PARTS], "note": "no teardown yet"}})
    for r in records:
        r["retire"] = retire_call(r, records)
    out = {"brand": brand, "built": date.today().isoformat(), "snapshot": snapshot, "sources": reg_paths +
           [f"runs/winners/{brand}/bank.json", "runs/video-teardown/_work/<run>/stages"], "count": len(records),
           "rule": RETIRE_RULE, "parts": [n for n, _ in PARTS], "image_winners": images, "winners": records}
    d = WS / "runs" / "winners" / brand
    d.mkdir(parents=True, exist_ok=True)
    (d / "winner-index.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    (d / "winner-index.md").write_text(markdown(out))
    return out


# what every winner's teardown holds, so every winner is indexed the same way (the order the teardown writes them)
PARTS = [("triage", "stages/0-triage.md"), ("teardown", "stages/1-teardown.md"), ("transcript", "stages/1-transcript.md"),
         ("culture", "stages/1k-culture.md"), ("persuasion read", "stages/1c-doctrine.md"), ("spec", "stages/2-spec.md")]


def completeness(run, t):
    """Which parts of the standard teardown a winner has. A read borrowed from a copy of the same ad still counts as
    missing on this run (the match uses the borrowed one meanwhile)."""
    d = RUNS / run
    missing = [n for n, f in PARTS if not (d / f).is_file()]
    if not message(run)["core"]:
        missing.append("core message")
    out = {"complete": not missing, "missing": missing}
    if t and t.get("read_from"):
        out["note"] = "read borrowed from " + t["read_from"]
    return out


RETIRE_RULE = ("fold: a copy of another winner, removed from the bank (its proof counts once, on the original). "
               "retire: not a winner, no sales on record. watch: lost money over its life (return under 1.0x), "
               "still matched. keep: everything else. Age retires nothing.")


def retire_call(r, records):
    p = r["proof"]
    if not r["run"]:
        return {"call": "needs teardown", "why": f"{p.get('purchases')} sales, never torn down: it cannot be matched"}
    if r["copy_of"]:
        return {"call": "fold", "why": f"copy of {label(r['copy_of'])}: same ad, its proof counts once"}
    if not p.get("purchases"):
        return {"call": "retire", "why": "not a winner: no sales on record for this ad"}
    if p.get("roas") is not None and p["roas"] < 1.0:
        return {"call": "watch", "why": f"lost money over its life: {p['roas']}x return, ${p['cpa']:.0f} a sale"}
    return {"call": "keep", "why": f"{p['purchases']} sales at ${p['cpa']:.0f}, last ran {p['last_ran']}"}


def label(run):
    """What the owner reads: "Winner #29 · cf mexico 1". The run folders keep their names (core<N>-NN-…, <brand>-core<N>-NN-…)."""
    m = re.match(r"(?:[a-z]+-)?core\d*-(\d+)-(.+)", run)
    if m:
        return f"Winner #{int(m[1])} · {m[2].replace('-', ' ')}"
    m = re.match(r"(?:[a-z]+-)?core\d*-(.+)", run)
    if m:
        return f"Winner · {m[1].replace('-', ' ')}"
    return run.replace("-", " ")


def markdown(idx):
    L = [f"# {idx['brand'].upper()} winner index ({idx['built']})", "",
         f"{idx['count']} banked winners. Proof snapshot {idx['snapshot']}. Built from the teardowns, the registry "
         f"and the bank; no model call.", "", f"Retire rule: {idx['rule']}", "",
         "| winner | call | sales | $/sale | return | last ran | posted | format | awareness | framework | length | teardown |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in idx["winners"]:
        t, p = r["traits"] or {}, r["proof"]
        L.append(f"| {r['label']} | {r['retire']['call']} | {p.get('purchases') or '–'} | "
                 f"{('$%.0f' % p['cpa']) if p.get('cpa') else '–'} | {p.get('roas') or '–'} | {p.get('last_ran') or '–'} | "
                 f"{r['posted'] or '–'} | {t.get('format') or '–'} | {t.get('aware_in') or '?'} → {t.get('aware_out') or '?'} | "
                 f"{t.get('framework') or '–'} | {mmss(t.get('runtime'))} | {'✓' if r['teardown']['complete'] else 'missing ' + ', '.join(r['teardown']['missing'])} |")
    L += ["", "## Each winner", ""]
    for r in idx["winners"]:
        t, p = r["traits"], r["proof"]
        if not t:
            L += [f"### {r['label']}", "", f"- call: **{r['retire']['call']}** — {r['retire']['why']}",
                  f"- argues: {r['argument'] or '–'}", f"- watch: {r['watch'] or '–'}", ""]
            continue
        L += [f"### {r['label']}", "",
              f"- call: **{r['retire']['call']}** — {r['retire']['why']}",
              f"- sells: {r['sells'] or '–'}", f"- argues: {r['argument'] or '–'}",
              f"- hook: {r['hook_words'] or '–'} ({t['hook'] or '?'})",
              f"- shape: {t['format']} · {t['cast']} · {mmss(t['runtime'])} · {t['pace'] or '?'} words/s · "
              f"{', '.join(t['tones']) or '–'}",
              f"- sections: {' → '.join(t['sections']) or '–'}",
              f"- awareness: {t['aware_in'] or '?'} → {t['aware_out'] or '?'} · sophistication: "
              f"{t['sophistication'] or '?'}" + (f" (read from {t['read_from']})" if t.get("read_from") else ""),
              f"- proof: {p.get('purchases') or '–'} sales · ${p.get('spend') or '–'} spent · "
              f"{('$%.0f' % p['cpa']) if p.get('cpa') else '–'} a sale · {p.get('roas') or '–'}x · ran "
              f"{p.get('first_ran') or '?'} to {p.get('last_ran') or '?'} · posted {r['posted'] or '–'}",
              f"- run: `runs/video-teardown/_work/{r['run']}`", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--brand", required=True)
    s = sub.add_parser("show"); s.add_argument("run")
    a = ap.parse_args()
    if a.cmd == "build":
        idx = build(a.brand)
        calls = {}
        for r in idx["winners"]:
            calls[r["retire"]["call"]] = calls.get(r["retire"]["call"], 0) + 1
        print(f"{idx['count']} winners indexed · " + " · ".join(f"{k} {v}" for k, v in sorted(calls.items())))
        print(f"runs/winners/{a.brand}/winner-index.json")
        return 0
    print(json.dumps(traits(a.run), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
