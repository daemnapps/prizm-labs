"""The teardown corpus: every finished video-teardown run for a brand, with its
post metrics, read into one record per run.

Reads only the video-teardown CONTRACT — the filed run folder
`runs/video-teardown/<brand>/<slug>/` (run.json, doctrine.json,
transcript.json, sound-sheet.json, stages/*.md) — and any swipe manifest that
names the run in its `teardown_run` column. Nothing here names a brand: the
brand is a folder name the caller passes.

Every `rule:` extractor in definitions/variables.json lives here. A rule that
cannot find its field returns None — recorded as "not in the record", never
guessed.
"""
import json
import re
import statistics
from pathlib import Path

ROLLS = ("A", "B-over", "B-vo", "B-silent", "C", "S", "X", "G", "E")


# ------------------------------------------------------------------ helpers
def ts(s):
    """'0:14.5' or '1:02' → seconds."""
    m = re.match(r"\s*(\d+):(\d+(?:\.\d+)?)", s or "")
    return int(m.group(1)) * 60 + float(m.group(2)) if m else None


def kv(text, key):
    m = re.search(rf"^\s*(?:[*-]\s+)?(?:\*\*)?`?{re.escape(key)}`?:(?:\*\*)?\s*(.+)$", text or "", re.M)
    return m.group(1).strip().strip("`") if m else None


def read(p):
    p = Path(p)
    return p.read_text(errors="replace") if p.is_file() else ""


def load_json(p, default=None):
    p = Path(p)
    try:
        return json.loads(p.read_text()) if p.is_file() else default
    except ValueError:
        return default


def block(text, start, stops):
    """The text between a bold section header and the next of `stops`."""
    hdr = lambda w: rf"^(?:\*\*{re.escape(w)}:?\*\*|#+\s*{re.escape(w)}:?)\s*$"
    m = re.search(hdr(start), text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    ends = [re.search(hdr(s), rest, re.M) for s in stops]
    ends = [e.start() for e in ends if e]
    ends.append(rest.find("\n| Timestamp"))
    ends = [e for e in ends if e >= 0]
    return rest[: min(ends)] if ends else rest


def shot_rows(teardown):
    """The shot table as dicts. Tolerant of 8-column tables and stray pipes."""
    rows = []
    for line in teardown.splitlines():
        if not re.match(r"^\|\s*\d+:\d", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        span = cells[0].split("-")
        a, b = ts(span[0]), ts(span[1]) if len(span) > 1 else None
        roll = re.split(r"[\s·]", cells[1].replace("`", "").strip())[0] if cells[1] else ""
        rows.append({"start": a, "end": b, "roll": roll, "section": cells[2].lower(), "visuals": cells[3],
                     "ost": cells[4], "words": cells[5], "sound": cells[6] if len(cells) > 6 else "",
                     "layers": cells[7] if len(cells) > 7 else ""})
    return rows


def none_like(s):
    s = (s or "").strip().lower().strip("[]()*_ ")
    return s in ("", "none", "-", "—", "n/a", "no", "nothing", "none.") or s.startswith("none ")


# ------------------------------------------------------------------ the run
class Run:
    def __init__(self, folder, metrics=None):
        self.dir = Path(folder)
        self.slug = self.dir.name
        self.metrics = metrics or {}
        self.runjson = load_json(self.dir / "run.json", {}) or {}
        self.triage = read(self.dir / "stages/0-triage.md")
        self.teardown = read(self.dir / "stages/1-teardown.md")
        # who OUR version speaks to is a writing decision, filed on the
        # writing shelf beside this one since 2026-09-30 (runs/video-writing/)
        wdir = self.dir.parents[1].parent / "video-writing" / self.dir.parent.name / self.dir.name
        self.audience = (read(wdir / "stages/1b-audience.md")
                         or read(self.dir / "stages/1b-audience.md")).strip("` \n")
        self.spec = read(self.dir / "stages/2-spec.md")
        self.doctrine_md = read(self.dir / "stages/1c-doctrine.md")
        self.doctrine = load_json(self.dir / "doctrine.json", {}) or {}
        self.transcript = load_json(self.dir / "transcript.json", []) or []
        self.sound = load_json(self.dir / "sound-sheet.json", {}) or {}
        self.rows = shot_rows(self.teardown)

    @property
    def complete(self):
        return bool(self.triage and self.teardown and self.doctrine and self.audience and self.spec)

    @property
    def views(self):
        return float(self.metrics.get("views") or 0)

    @property
    def saves(self):
        return float(self.metrics.get("saves") or 0)

    @property
    def likes(self):
        return float(self.metrics.get("likes") or 0)

    def runtime(self):
        if self.metrics.get("duration_s"):
            return float(self.metrics["duration_s"])
        r = ts(kv(self.triage, "RUNTIME") or "")
        if r:
            return r
        ends = [x["end"] for x in self.rows if x["end"]]
        return max(ends) if ends else None

    def sections(self):
        return [s.get("id") for s in self.doctrine.get("sections_carried") or [] if s.get("id")]

    def lead_voice(self):
        cards = self.sound.get("voice_cards") or []
        if not cards:
            return {}
        return max(cards, key=lambda c: (c.get("measured") or {}).get("talk_share_percent") or 0)

    def cast_names(self):
        b = block(self.teardown, "CAST", ["PLACES", "PROPS"])
        hits = re.findall(r"^(?:\*\*([^*\n]+)\*\*|#{3,}\s*(.+))\s*$", b, re.M)
        return [a or c for a, c in hits]

    def places(self):
        b = block(self.teardown, "PLACES", ["PROPS"])
        found = re.findall(r"\*\*What(?: it is)?:\*\*\s*(.+)$", b, re.M)
        if not found:  # a places block with no 'What it is' lines: fall back to the card names
            found = [a or c for a, c in re.findall(r"^(?:\*\*([^*\n]+)\*\*|#{3,}\s*(.+))\s*$", b, re.M)]
        return found

    def props(self):
        b = block(self.teardown, "PROPS", ["ZZZ"])
        return re.findall(r"^\s*[*-]\s+\*\*([^*:]+):?\*\*", b, re.M)

    def layer_sheet(self):
        m = re.search(r"Layer sheet\**:?\**\s*\n(.*?)(?:\n\s*\**\s*\**Sound sheet|\Z)", self.teardown, re.S)
        return m.group(1) if m else ""

    def techniques(self, section_ids):
        out = []
        for t in self.doctrine.get("techniques") or []:
            if t.get("section") in section_ids and t.get("technique"):
                out.append(f"{t['technique']} · {t.get('sub_method') or '—'}")
        return sorted(set(out))


# ------------------------------------------------------------------ rule extractors
SETTING_WORDS = [
    ("bathroom", r"bathroom|shower|\bsink\b|mirror|vanity"), ("bedroom", r"bedroom|\bbed\b"),
    ("living room", r"living room|couch|sofa|lounge"), ("kitchen", r"kitchen"), ("car", r"\bcar\b|vehicle|driver"),
    ("store / retail", r"store|aisle|shop|retail|pharmacy|mall"), ("gym", r"\bgym\b|fitness"),
    ("outdoors", r"outdoor|street|park|yard|beach|sidewalk|parking"), ("studio / plain wall", r"studio|plain wall|backdrop|digital background|green ?screen"),
    ("barbershop / salon", r"barber|salon"), ("office / desk", r"office|desk|workspace|warehouse|factory"),
    ("screen / app", r"screen recording|app interface|phone screen|dashboard")]


def _band(x, bins, unit=""):
    if x is None:
        return None
    for lo, hi in zip(bins, bins[1:]):
        if lo <= x < hi:
            return f"{lo:g}–{hi:g}{unit}" if hi < 99 else f"{lo:g}{unit}+"
    return None


def rule(name, r):
    f = RULES.get(name)
    return f(r) if f else None


def _first_roll(r):
    return r.rows[0]["roll"] if r.rows else None


def _first_words(r):
    return r.transcript[0].get("start") if r.transcript else None


def _hook_line(r):
    return r.transcript[0].get("text") if r.transcript else None


def _hook_platform(r):
    kinds = set()
    for x in r.rows:
        if x["start"] is not None and x["start"] < 3.0:
            for k in re.findall(r"platform:\s*([a-z_ -]+?)[:\"/·]", x["layers"] + " :", re.I):
                if not none_like(k):
                    kinds.add(k.strip().replace("_", "-").lower())
            if x["roll"] == "G":
                kinds.add("picture-in-picture")
    return " + ".join(sorted(kinds)) if kinds else "none"


def _hook_text(r):
    t = kv(r.layer_sheet(), "Hook text")
    if t is None:
        return None
    if none_like(t):
        return "none"
    return re.split(r"\s*[|·]?\s*look:", t)[0].strip()


def _platform_any(r):
    sheet = r.layer_sheet()
    kinds = set(k.strip().lower().replace("_", "-") for k in re.findall(r"·\s*platform\s*·\s*([A-Za-z_ -]+?)\s*·", sheet))
    for x in r.rows:
        for k in re.findall(r"platform:\s*([a-z_ -]+?)[:\"/·]", x["layers"] + " :", re.I):
            if not none_like(k):
                kinds.add(k.strip().replace("_", "-").lower())
    return " + ".join(sorted(kinds)) if kinds else "none"


def _platform_text(r):
    for x in r.rows:
        m = re.search(r"platform:\s*[a-z_ -]+?:?\s*\"([^\"]+)\"", x["layers"], re.I)
        if m:
            return m.group(1).strip()
    m = re.search(r"·\s*platform\s*·[^\"]*\"([^\"]+)\"", r.layer_sheet())
    return m.group(1).strip() if m else "none"


def _lane(r):
    v = (kv(r.triage, "LANE") or "").upper()
    return v or None


def _framework(r):
    row = r.doctrine.get("crosswalk_row")
    return re.sub(r"\s*\(.*", "", row) if row else "no crosswalk row (own shape)"


def _section_order(r):
    s = r.sections()
    out = []
    for x in s:
        if not out or out[-1] != x:
            out.append(x)
    return " → ".join(out) if out else None


def _problem_placement(r):
    s = r.sections()
    if "problem" not in s:
        return "no problem section"
    if "call-to-action" not in s:
        return "problem, no ask"
    return "problem before first ask" if s.index("problem") < s.index("call-to-action") else "problem after first ask"


def _aud(key):
    return lambda r: (kv(r.audience, key) or None)


def _topics(r):
    t = kv(r.audience, "TOPICS")
    return [x.strip() for x in t.split(",") if x.strip()] if t else []


def _settings(r):
    out = set()
    for p in r.places():
        hit = [name for name, rx in SETTING_WORDS if re.search(rx, p, re.I)]
        out.update(hit or ["other"])
    return sorted(out)


def _camera(r):
    cams = [re.search(r"Camera:\s*([^·]+)", x["visuals"]) for x in r.rows]
    return [c.group(1).lower() for c in cams if c]


def _camera_grade(r):
    c = _camera(r)
    if not c:
        return None
    phone = sum("phone" in x for x in c) / len(c)
    return "phone-grade" if phone >= 0.6 else "mixed" if phone > 0 else "not phone-grade"


def _camera_mode(r):
    c = _camera(r)
    if not c:
        return None
    counts = {"selfie / front camera": sum(("selfie" in x or "front" in x) for x in c),
              "propped / static": sum(("propped" in x or "tripod" in x) and "selfie" not in x for x in c),
              "rear camera / handheld": sum(("rear" in x) for x in c)}
    best = max(counts, key=counts.get)
    return best if counts[best] / len(c) >= 0.5 else "mixed"


def _ai(r):
    a = kv(r.triage, "AI ASSESSMENT") or ""
    m = re.search(r"(LIKELY HUMAN|LIKELY AI|MIXED|UNCLEAR|AI[- ]GENERATED)", a.upper())
    return m.group(1) if m else (a[:40] or None)


def _archetype(label):
    def f(r):
        m = re.search(rf"\*\*{label}:\*\*\s*(.+)$", r.teardown, re.M)
        if not m:
            return None
        v = m.group(1).strip().strip('"“”')
        return re.split(r"[.—]\s|\s—|\"\s", v)[0].strip(' "“”')[:80]
    return f


def _music_line(r):
    m = re.search(r"^(?:\*\*)?Music:(?:\*\*)?\s*(?:Music:\s*)?(.+)$", r.teardown, re.M)
    return m.group(1).strip() if m else None


def _music_bed(r):
    v = _music_line(r)
    if v is None:
        return None
    return "none" if none_like(v) else "music bed"


def _music_source(r):
    m = re.search(r"Music, described:\*\*\s*(.+)$", r.teardown, re.M)
    d = m.group(1) if m else ""
    if not d or none_like(d):
        return "none described"
    if re.search(r"not a known recording|original|unreleased", d, re.I):
        return "original / unidentified"
    if re.search(r"IDENTIFIED|AudD:\s*[^()]*\b(by|—)\b", d):
        return "known recording"
    return "described, not identified"


def _voice(key, measured=False):
    def f(r):
        c = r.lead_voice()
        return ((c.get("measured") or {}).get(key) if measured else c.get(key)) or None
    return f


def _length_band(r):
    x = r.runtime()
    if x is None:
        return None
    return "≤15 s" if x <= 15 else "16–24 s" if x <= 24 else "25–45 s" if x <= 45 else "46 s +"


def _avg_shot(r):
    d = [x["end"] - x["start"] for x in r.rows if x["start"] is not None and x["end"] is not None and x["end"] > x["start"]]
    return round(statistics.mean(d), 2) if d else None


def _roll_secs(r):
    out = {}
    for x in r.rows:
        if x["start"] is None or x["end"] is None:
            continue
        out[x["roll"]] = out.get(x["roll"], 0) + max(0, x["end"] - x["start"])
    return out


def _dominant_roll(r):
    s = _roll_secs(r)
    return max(s, key=s.get) if s else None


def _transitions(r):
    n = 0
    for x in r.rows:
        m = re.search(r"transition out:\s*([^/|·]+)", x["layers"], re.I)
        if m and not none_like(m.group(1)) and "cut" not in m.group(1).lower():
            n += 1
    return n


def _sfx(r):
    for x in r.rows:
        m = re.search(r"effects:\s*([^/|]+)", x["sound"], re.I)
        if m and not none_like(m.group(1)):
            return "effects present"
    return "none"


def _captions(r):
    c = kv(r.layer_sheet(), "Captions")
    if c is None:
        return None
    return "none" if none_like(c) else "running captions"


def _ost_share(r):
    if not r.rows:
        return None
    return round(100 * sum(not none_like(x["ost"]) for x in r.rows) / len(r.rows))


def _ask_position(r):
    rt = r.runtime()
    for s in r.doctrine.get("sections_carried") or []:
        if s.get("id") == "call-to-action":
            a = ts((s.get("span") or "").split("-")[0])
            if a is None or not rt:
                return None
            pos = a / rt
            return "ask in last 15%" if pos >= .85 else "ask mid-to-late" if pos >= .5 else "ask early"
    return "no spoken ask"


def _mass_desire(r):
    return (r.doctrine.get("mass_desire") or {}).get("words")


RULES = {
    "first_roll": _first_roll, "first_words_at": _first_words, "hook_line": _hook_line,
    "hook_platform": _hook_platform, "hook_text": _hook_text,
    "hook_techniques": lambda r: r.techniques({r.sections()[0]} if r.sections() else set()),
    "platform_text": _platform_text, "lane": _lane, "framework": _framework, "section_order": _section_order,
    "aw_entry": lambda r: (r.doctrine.get("awareness") or {}).get("entry"),
    "aw_exit": lambda r: (r.doctrine.get("awareness") or {}).get("exit"),
    "soph": lambda r: r.doctrine.get("sophistication_signature"),
    "format": lambda r: r.doctrine.get("format"),
    "section_count": lambda r: len(r.sections()) or None,
    "problem_placement": _problem_placement, "mass_desire": _mass_desire,
    "avatar": _aud("AVATAR"), "funnel": _aud("FUNNEL"), "story": _aud("STORY"), "topics": _topics,
    "route": _aud("ROUTE RECOMMENDED"), "aud_awareness": _aud("AWARENESS"), "lead_desire": _aud("LEAD DESIRE"),
    "has_transformation": lambda r: "transformation beat" if "transformation" in r.sections() else "none",
    "cast_count": lambda r: len(r.cast_names()) or None,
    "voices": lambda r: r.sound.get("voices"),
    "lead_gender": _voice("gender_presentation"), "lead_age": _voice("age_band"),
    "read_style": _voice("read_style"), "accent": _voice("accent"),
    "char_archetype": _archetype("Character archetype"),
    "settings": _settings, "place_count": lambda r: len(r.places()) or None,
    "camera_grade": _camera_grade, "camera_mode": _camera_mode, "ai_assessment": _ai,
    "aesthetic": _archetype("Aesthetic archetype"), "props_count": lambda r: len(r.props()) or None,
    "sound_form": lambda r: (kv(r.triage, "SOUND FORM") or "").upper() or None,
    "music_bed": _music_bed, "music_source": _music_source,
    "talk_share": _voice("talk_share_percent", True), "wpm": _voice("words_per_minute", True),
    "delivery_voice": _voice("delivery_style"),
    "humor": lambda r: (r.doctrine.get("delivery") or {}).get("humor"),
    "register": lambda r: (r.doctrine.get("delivery") or {}).get("register"),
    "pacing": lambda r: (r.doctrine.get("delivery") or {}).get("pacing"),
    "lines": lambda r: len(r.transcript) if r.transcript else None, "sfx": _sfx,
    "runtime": lambda r: r.runtime(), "length_band": _length_band,
    "shot_count": lambda r: len(r.rows) or None, "avg_shot": _avg_shot,
    "silent_broll": lambda r: round(_roll_secs(r).get("B-silent", 0), 1) if r.rows else None,
    "dominant_roll": _dominant_roll, "transitions": _transitions,
    "mood": lambda r: r.doctrine.get("mood"),
    "captions": _captions, "ost_share": _ost_share, "platform_any": _platform_any,
    "post_caption": lambda r: r.metrics.get("caption") or None,
    "has_cta": lambda r: "spoken ask" if "call-to-action" in r.sections() else "no spoken ask",
    "ask_position": _ask_position,
    "close_techniques": lambda r: r.techniques({"call-to-action"}),
}


# ------------------------------------------------------------------ the corpus
def metrics_index(repo, brand):
    """Every manifest row that names a teardown run, keyed by that run's folder name."""
    out = {}
    for mf in sorted((Path(repo) / "runs").glob(f"swipe-*/{brand}/*/manifest.json")):
        data = load_json(mf, {}) or {}
        for row in data.get("rows") or []:
            tr = row.get("teardown_run")
            if tr:
                out[Path(tr).name] = {**row, "_manifest": str(mf.relative_to(repo))}
    return out


def load(repo, brand, with_metrics_only=True):
    base = Path(repo) / "runs" / "video-teardown" / brand
    mx = metrics_index(repo, brand)
    runs = []
    for d in sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []:
        m = mx.get(d.name)
        if with_metrics_only and not m:
            continue
        r = Run(d, m)
        if r.complete:
            runs.append(r)
    return runs


def find_run(repo, brand, ref):
    """A run folder from a path, a slug, or a post id."""
    p = Path(ref)
    if p.is_dir():
        return p.resolve()
    base = Path(repo) / "runs" / "video-teardown" / brand
    for cand in (base / ref, base / f"{brand}-{ref}"):
        if cand.is_dir():
            return cand
    hits = [d for d in base.iterdir() if d.is_dir() and ref in d.name] if base.is_dir() else []
    if len(hits) == 1:
        return hits[0]
    raise FileNotFoundError(f"no teardown run for {ref!r} under {base}")
