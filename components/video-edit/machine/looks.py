#!/usr/bin/env python3
"""looks.py — the one place the edit reads its looks and levels from (video system sync 2026-10-21, E6 + E27).

    caption(id)            a caption look row from looks/bank.json — the ONE caption-look registry
    pick_caption(fmt, app) the look a piece starts on: by its format, else by the app it pretends to be made in,
                           else the default (bank.json `pick`) — V13: "It can never look like it's being edited off
                           of the phone"; bottom is the default, edits-glow aims at the neck
    text_look(kind, id)    a headline / option card / end-card / badge look from looks/edit-looks.json `text`
    sound()                the ONE loudness table (defaults.json `sound`) both renderers read — V14, C10
    pace(fmt)              how the cut breathes, per format (defaults.json `pace`: a set value, then `by_format`, then
                           the default) — V15, E20; pace_call / caption_call give the same answers with their reasons
    moves(fmt)             the camera moves the edit may add, per format (defaults.json `moves`) — V15, E17/E18/E21
    app_for(vm)            the app every road picks captions by: app_of, else the lane (paid → meta) — E36
    app_of(vm)             the app a production run's piece pretends to be made in — its own fields, else the brief's
                           App line, else the swipe's own link (tiktok.com / instagram.com) — V13, verify 10-21 row 9
    placement_of(vm)       paid or organic, and surfaces(placement) the feeds whose safe box the words and the
                           product keep inside: paid adds Meta's Reels-ads zone — V16/V1, verify 10-21 row 20

Until 2026-10-21 there were two caption registries with two defaults (edit-looks.json `captions` for the edit-map
line, bank.json for the cut sheet) and two loudness tables (edit-looks.json `mix` vs defaults.json `sound`). Both are
folded in here; edit-looks.json keeps only id stubs under `captions` for readers that list them.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent


def _read(p: Path) -> dict:
    return json.loads(p.read_text())


def bank() -> dict:
    return _read(TOOL / "looks" / "bank.json")


def defaults() -> dict:
    return _read(HERE / "defaults.json")


def caption(look_id: str | None) -> dict | None:
    """The caption look row by id, or None when the bank has no such row."""
    return next((r for r in bank()["looks"] if r["id"] == look_id), None)


def pick_caption(fmt: str | None = None, app: str | None = None) -> str:
    """The caption look a piece of this format (and app) starts on. A run's own controls.json still wins (run.py)."""
    p = bank().get("pick") or {}
    by_f, by_a = p.get("by_format") or {}, p.get("by_app") or {}
    if fmt and fmt in by_f and not str(fmt).startswith("_"):
        row = by_f[fmt]                      # a plain look id, or {"look", "why", "from"}
        got = row.get("look") if isinstance(row, dict) else row
        if got:
            return got
    for a in ([app] if isinstance(app, str) else list(app or [])):
        key = str(a or "").lower()
        for k, v in by_a.items():
            if k in key:
                return v
    return p.get("default") or "ig-fb-native"


# THE CAPTIONS FOLLOW THE SWIPE (2026-10-28): the
# scene breakdown reads the swipe's own captions in words (scene-breakdown.json `captions`); the nearest bank look wins.
def swipe_captions(vm) -> list:
    """Every caption line the scene breakdown read off the swipe, in scene order ([] when it was not read)."""
    f = Path(vm) / "scene-breakdown.json"
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        return []
    return [str(x) for k in sorted(d) for x in ((d[k] or {}).get("captions") or [])]


def from_swipe(lines) -> str | None:
    """The bank look nearest the swipe's captions as the breakdown words them, or None when they say nothing to match."""
    import re
    t = " ".join(str(x) for x in lines or []).lower()
    if not t.strip():
        return None
    want = {}
    if re.search(r"\bno (?:outline or )?(?:box|plate|background)\b|no outline or box|without a box", t):
        want["plate"] = False
    elif re.search(r"\b(box|plate|background|sticker)\b", t):
        want["plate"] = True
    if re.search(r"\bno (?:outline|stroke|edge)\b|no outline or box", t):
        want["stroke"] = False
    elif re.search(r"\b(outline|stroke|black edge|edged)\b", t):
        want["stroke"] = True
    if re.search(r"\b(middle|centre|center|chest)\b", t):
        want["zone"] = "center"
    elif re.search(r"\b(bottom|low|lower third|lower)\b", t):
        want["zone"] = "caption-band"
    if re.search(r"\b(all caps|capitals|upper ?case)\b", t):
        want["upper"] = True
    elif re.search(r"\b(sentence case|lower ?case)\b", t):
        want["upper"] = False
    n = re.search(r"(\d+)\s*(?:to|-|–)\s*(\d+)\s*words?|(\d+)\s*words?", t)
    if n:
        want["words"] = int(n.group(2) or n.group(3))
    if not want:
        return None

    def score(l):
        s = 0
        if "plate" in want:
            s += 3 if bool(l.get("plate")) == want["plate"] else -3
        if "stroke" in want:
            s += 2 if bool(l.get("stroke_px")) == want["stroke"] else -2
        if "zone" in want:
            s += 3 if l.get("zone") == want["zone"] else -1
        if "upper" in want:
            s += 1 if (l.get("case") == "upper") == want["upper"] else -1
        if "words" in want:
            s -= abs(int(l.get("max_words") or 3) - want["words"]) * 0.5
        return s
    return max(bank()["looks"], key=score)["id"]


def headline_distinct(lines) -> bool:
    """Does the swipe show its opening words in a headline look of their own (a title, a banner, static top text)?
    When it does not, the opening is set in the caption look like every other line (2026-10-28)."""
    import re
    return bool(re.search(r"\b(headline|title|banner|static (?:top )?text|top text|text at the top)\b",
                          " ".join(str(x) for x in lines or []), re.I))


def text_look(kind: str, look_id: str | None = None) -> dict:
    """A headline / option card / end-card words look (edit-looks.json `text`), the ad's own id first."""
    L = _read(TOOL / "looks" / "edit-looks.json")
    return L["text"].get(look_id or "") or L["text"][L["defaults"][kind]]


def sound() -> dict:
    """The one loudness table: voice, music under the voice and in the pauses, effects, room tone, the master."""
    d = defaults()
    s = dict(d["sound"])
    s.setdefault("lufs", (d.get("mix") or {}).get("lufs", -14))
    s.setdefault("true_peak_db", (d.get("mix") or {}).get("true_peak_db", -1))
    return s


def _by_format(table: dict, fmt: str | None):
    """A format's own row of a `by_format` table: the option name, whether the row is a plain name or {"use", "why",
    "from"}. (name | None, the row's reason | None)."""
    row = (table or {}).get(fmt or "")
    if isinstance(row, dict):
        return row.get("use") or row.get("look"), row.get("why")
    return (row or None), None


def pace(fmt: str | None = None, controls: dict | None = None) -> dict:
    """{name, breath_s, max_pause | None, by, why}: the breath laid between two lines, and the longest silence left
    INSIDE a take (None = a take is never cut inside — V15 "cuts between shots, never mid-breath").

    THE ORDER (fixed 2026-11-18, the logic layer): a `value` SET (here or in a run's controls.json) wins for every
    take; else the format's own (`by_format`); else `default`. That is what the dial's own `what` always said; the code
    read format, then default, then value, so a set value was never reached and a format out-ranked the run. `by` and
    `why` say which rung answered, so the next stage reads a reason and not only a name."""
    p = (controls or {}).get("pace") or defaults()["pace"]
    f_name, f_why = _by_format(p.get("by_format"), fmt)
    if p.get("value"):
        name, by, why = p["value"], "the run", "set for this run (its controls), for every take"
    elif f_name:
        name, by, why = f_name, "the format", f_why or f"the {fmt} format's own pace"
    else:
        name, by, why = p.get("default"), "the default", "no pace is set for this format: the default for every format"
    opt = dict(p["options"][name])
    opt.setdefault("breath_s", 0.15)
    opt.setdefault("max_pause", None)
    return {"name": name, **opt, "by": by, "why": why}


def cutting_words(fmt: str | None) -> dict:
    """How this format is cut and what its sound does, in the craft doctrine's own words (components/video-doctrine
    frameworks.json `shapes`, read at run time and never restated here). {} for a format the doctrine has no row for."""
    try:
        d = _read(TOOL.parent / "video-doctrine" / "frameworks.json")
    except (OSError, ValueError):
        return {}
    row = next((r for r in ((d.get("shapes") or {}).get("rows") or []) if r.get("format") == fmt), None)
    return {k: row[k] for k in ("cutting", "sound") if row and row.get(k)} if row else {}


def pace_call(fmt: str | None = None, controls: dict | None = None) -> dict:
    """The pace a piece of this format is cut at, with its reason and the doctrine's cutting words, for a hand-off or
    the trail: {"name", "what", "breath_s", "max_pause", "by", "why", "cutting"?, "sound"?}."""
    got = pace(fmt, controls)
    out = {k: got.get(k) for k in ("name", "what", "breath_s", "max_pause", "by", "why")}
    out.update(cutting_words(fmt))
    return out


def caption_call(fmt: str | None = None, app: str | None = None, asked: str | None = None) -> dict:
    """The caption look a piece starts on, with its reason, for a hand-off or the trail: {"look", "name", "by", "why",
    "asked"?}. The same answer as `pick_caption` (format, then the app the piece pretends to be made in, then the
    default); a look the brief asks for in words is carried beside it as a note, never applied here."""
    p = bank().get("pick") or {}
    look = pick_caption(fmt, app)
    f_name, f_why = _by_format(p.get("by_format"), fmt)
    apps = [str(a or "").lower() for a in ([app] if isinstance(app, str) else list(app or []))]
    if f_name and f_name == look:
        by, why = "the format", f_why or f"the {fmt} format has a look of its own"
    elif any(k in a for a in apps for k in (p.get("by_app") or {})):
        by, why = "the app", f"the piece is made to look native to {next(a for a in apps if a)}"
    else:
        by, why = "the default", "no look of its own for this format and no app named: the default"
    row = caption(look) or {}
    out = {"look": look, "name": row.get("name") or look, "by": by, "why": why}
    if asked and str(asked).strip():
        out["asked"] = str(asked).strip()
    return out


def moves(fmt: str | None = None) -> dict:
    """The camera moves the edit may add for this format: {push_stills, punch, punch_scale, image_drift}. Off by
    default — a punch-in happens only where the swipe itself pushes in (V15: "no unneeded zoom-ins or punch-ins")."""
    m = defaults().get("moves") or {}
    base = dict(m.get("default") or {})
    base.update((m.get("by_format") or {}).get(fmt or "") or {})
    base.setdefault("push_stills", False)
    base.setdefault("punch", "swipe")
    base.setdefault("punch_scale", 1.07)
    base.setdefault("image_drift", 1.03)
    return base


# ---------------------------------------------------------------- the app and the placement of a production run
APP_KEYS = ("app", "platform", "made_in", "made_on", "surface")
URL_KEYS = ("post_url", "origin_url", "source_url", "url", "swipe_url", "link")


def _json(p: Path) -> dict:
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


def _app_word(v) -> str | None:
    for a in ([v] if isinstance(v, str) else list(v or []) if isinstance(v, (list, tuple)) else []):
        a = str(a or "").strip().lower()
        if not a:
            continue
        for host, name in (("tiktok", "tiktok"), ("instagram", "instagram"), ("facebook", "facebook"), ("fb.", "facebook"),
                           ("meta", "meta"), ("youtube", "youtube"), ("reels", "instagram")):
            if host in a:
                return name
    return None


def _swipe_run(vm: Path, run: dict) -> dict:
    """The teardown run the brief came from (run.json `brief_from` → …/_work/<slug>/stages/5-brief.md), else by label."""
    bf = str(run.get("brief_from") or "")
    cands = []
    if bf:
        b = Path(bf)
        cands += [b.parent.parent / "run.json", b.parent / "run.json"]
    if run.get("label"):
        cands.append(TOOL.parents[1] / "runs" / "video-teardown" / "_work" / str(run["label"]) / "run.json")
    for c in cands:
        d = _json(c)
        if d:
            return d
    return {}


def app_of(vm: Path, run: dict | None = None, plan: dict | None = None) -> str | None:
    """The app this piece pretends to be made in (tiktok · instagram · facebook · meta · youtube), or None: the run's or
    the brief's piece fields first, then an `App:` / `Platform:` line in the brief, then the host of the swipe's own link
    — the swipe is what the piece copies (V13: "It can never look like it's being edited off of the phone")."""
    import re
    vm = Path(vm)
    run = run if run is not None else _json(vm / "run.json")
    plan = plan if plan is not None else _json(vm / "plan.json")
    for src in (run, plan.get("piece") or {}, plan):
        for k in APP_KEYS:
            a = _app_word(src.get(k)) if isinstance(src, dict) else None
            if a:
                return a
    try:
        brief = (vm / "brief.md").read_text()
    except OSError:
        brief = ""
    m = re.search(r"^\W*(?:app|platform|made in)\W*:\W*(.+)$", brief, re.I | re.M)
    if m and _app_word(m.group(1)):
        return _app_word(m.group(1))
    sw = _swipe_run(vm, run)
    for k in URL_KEYS:
        a = _app_word(sw.get(k))
        if a:
            return a
    for v in (sw.get("source") or {}, sw.get("swipe") or {}):
        if isinstance(v, dict):
            for k in URL_KEYS + APP_KEYS:
                a = _app_word(v.get(k))
                if a:
                    return a
    return None


def app_for(vm: Path | None, run: dict | None = None, plan: dict | None = None) -> str | None:
    """The app every road picks the caption look by (E36, verify 2026-10-21): the piece's own app (app_of — its fields,
    the brief, the swipe's link); else from the lane the run already carries — paid runs on Meta; organic has no app
    of its own to name, so None and the look falls to the default (ig-fb-native)."""
    if vm is None:
        return None
    a = app_of(vm, run, plan)
    if a:
        return a
    return "meta" if placement_of(vm, run, plan) == "paid" else None


def placement_of(vm: Path, run: dict | None = None, plan: dict | None = None) -> str:
    """'paid' or 'organic'. A run or brief that says so wins (`placement` · `lane` · `paid`); otherwise a cut made on the
    edit-map line is a PAID Meta placement — the line files it as a Meta ad card (deliver.py → meta/<brand>/1-check)."""
    vm = Path(vm)
    run = run if run is not None else _json(vm / "run.json")
    plan = plan if plan is not None else _json(vm / "plan.json")
    for src in (run, plan.get("piece") or {}, plan):
        if not isinstance(src, dict):
            continue
        if isinstance(src.get("paid"), bool):
            return "paid" if src["paid"] else "organic"
        for k in ("placement", "lane", "distribution"):
            v = str(src.get(k) or "").lower()
            if "organic" in v:
                return "organic"
            if any(w in v for w in ("paid", "ads", "meta-ad", "spark")):
                return "paid"
    return "paid"


def surfaces(placement: str) -> list[str]:
    """The feeds whose safe box this piece keeps inside: the defaults (organic), and Meta's Reels-ads zone when paid
    (defaults.json `safe_zones.surfaces.meta-reels-ads`: top 14%, bottom 35% — the sponsored label, CTA and ad copy)."""
    d = defaults()
    names = list((d.get("platform_surfaces") or {}).get("value") or [])
    if placement == "paid":
        names += [n for n in ("meta-reels-ads",) if n not in names]
    return names
