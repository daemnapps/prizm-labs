#!/usr/bin/env python3
"""library.py — a brand's footage library, sorted into one vocabulary.

Reads the asset index's records for a brand (runs/asset-index/<brand>/*/ clip.json + breakdown.json),
the check pass's answers (runs/asset-index/<brand>/library/check/results.jsonl) and the proof index's
tagged before-and-after pictures (runs/asset-index/<brand>/proof/), and gives every scene the
vocabulary's descriptors: doctrine beat, product, setting, shot, tier (A direct b-roll / B montage or
proof / P presenter), polish, text marks (captions are marked, never rejected), handles, the Drive's
filed creator gender / ethnicity / age, people on screen, and source. Then answers a storyboard blank.

    python3 library.py build --brand <brand> [--sheet]
    python3 library.py query --brand <brand> '{"beat":"mechanism","product":"<id>","min_tier":"A"}'

Library for callers: use_brand(brand) -> rows; query(rows, blank); enrich(hits, brand) adds the
descriptors to asset-index search hits (the video footage step calls it).

Brand-agnostic: the shared words are vocabulary.json beside this file; the brand's words (products,
cleared handles, exclusions) are runs/asset-index/<brand>/library/brand-vocabulary.json.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUNS = Path(os.environ.get("ASSET_INDEX_RUNS") or (REPO / "runs" / "asset-index"))
BASE = json.loads((HERE / "vocabulary.json").read_text())
D: dict = {}
BRAND: dict = {}
EXACT = set()
_cache: dict = {}
TIER_RANK = {"A": 3, "P": 2, "B": 2}
BEAT_ORDER = ["presenter", "proof", "mechanism", "routine", "product", "problem", "transformation",
              "failed-solutions", "identification", "presence"]
REPOST = re.compile(r"snaptik|ssstik|tikmate|saveinsta|savefrom|ttsave|^ig[_-]reel|instagram|rpreplay|videoplayback", re.I)
PROBLEMS = ["acne", "razor bumps", "ingrown", "dark marks", "dark spots", "hyperpigmentation", "wrinkles", "fine lines",
            "texture", "oily", "dry skin", "redness", "scars", "blackheads", "pores", "breakouts", "beard"]


def libdir(brand: str) -> Path:
    return RUNS / brand / "library"


BRANDS = Path(os.environ.get("ASSET_INDEX_BRANDS") or (REPO / "brands"))
CREATOR_ROOT = ["content-creators"]       # the brand's creator filing folder; brands/<brand>/footage-library.json creator_root


def brand_config(brand: str) -> dict:
    """The brand's footage-library settings, brands/<brand>/footage-library.json (shape in brands/_TEMPLATE); {} when none."""
    try:
        return json.loads((BRANDS / brand / "footage-library.json").read_text())
    except (OSError, ValueError):
        return {}


def use_brand(brand: str) -> dict:
    """Load the shared vocabulary with the brand's words merged in; returns the merged descriptors."""
    global D, BRAND, EXACT
    import copy
    CREATOR_ROOT[0] = brand_config(brand).get("creator_root") or "content-creators"
    f = libdir(brand) / "brand-vocabulary.json"
    BRAND = json.loads(f.read_text()) if f.is_file() else {"products": {}, "partners": {"values": []}}
    d = copy.deepcopy(BASE["descriptors"])
    prods = BRAND.get("products") or {}
    d["product"]["values"] = prods
    d["partners"] = BRAND.get("partners") or {"values": []}
    d["text_marks"]["brand_handles"] = BRAND.get("brand_handles") or []
    words = sorted({w for ws in prods.values() for w in ws})
    def fill(o):
        if isinstance(o, list):
            out = []
            for x in o:
                out += words if x == "{brand_device}" else [fill(x)]
            return out
        if isinstance(o, dict):
            return {k: fill(v) for k, v in o.items()}
        return o
    d = fill(d)
    pb = d["beat"]["values"]["product"]["all_any"][1]
    d["beat"]["values"]["product"]["all_any"][1] = pb + [w for w in words if w not in pb]
    D = d
    EXACT = set()
    _cache.clear()
    return D


def _pat(kw: str) -> re.Pattern:
    kw = kw.lower()
    tail = r"\b" if kw in EXACT else ""
    return re.compile(r"\b" + re.escape(kw).replace(r"\ ", r"\s+") + tail)



def has(text: str, words) -> bool:
    for w in words:
        p = _cache.get(w) or _cache.setdefault(w, _pat(w))
        if p.search(text):
            return True
    return False


def beats_of(text: str, talking: bool, spoken: str) -> list[str]:
    out = []
    if talking and spoken.strip():
        out.append("presenter")
    for b, v in D["beat"]["values"].items():
        if b == "presenter":
            continue
        if "or_any" in v and has(text, v["or_any"]):
            out.append(b)
            continue
        ok = True
        if "any" in v:
            ok = has(text, v["any"])
        if ok and "all_any" in v:
            ok = all(has(text, grp) for grp in v["all_any"])
        if ok and "none" in v:
            ok = not has(text, v["none"])
        if ok:
            out.append(b)
    out.sort(key=lambda b: BEAT_ORDER.index(b))
    return out or [D["beat"]["unmatched"]]


def products_of(text: str) -> list[str]:
    out = [p for p, words in D["product"]["values"].items() if has(text, words)]
    if len(out) > 1:
        out = [p for p in out if not p.startswith("other-")]
    return out


def pick(text: str, table: dict, unmatched: str) -> str:
    for k, words in table.items():
        if has(text, words):
            return k
    return unmatched


def person_of(subject) -> str:
    s = str(subject or "").lower()
    if not s or s in ("null", "none"):
        return "none"
    man = bool(re.search(r"\b(man|men|male|guy|boy|he)\b", s))
    woman = bool(re.search(r"\b(woman|women|female|girl|she)\b", s))
    if man and woman or re.search(r"\b(two|three|group|several|people|friends)\b", s):
        return "group"
    if man:
        return "man"
    if woman:
        return "woman"
    if re.search(r"\bhands?\b|\barm\b|\bfingers?\b", s):
        return "hands"
    return "man" if "person" in s else "none"


def source_of(label: str, filename: str) -> str:
    p = label.split("/")[3:] if label else []
    top = p[0] if p else ""
    if top == CREATOR_ROOT[0]:
        return "creator-repost" if REPOST.search(filename or "") else "creator-raw"
    if top == "archive" and len(p) > 1 and p[1] == "creators-curated":
        return "curated-ugc"
    if top == "intake" and len(p) > 1 and p[1] == "organic":
        return "brand-post"
    if top == "ai-elements" or (top == "archive" and len(p) > 2 and p[1].startswith("ai-")):
        return "ai"
    if (top == "intake" and len(p) > 2 and p[1] == "ads") or top == "briefs":
        return "ad"
    if top == "brand-assets":
        return "brand-footage"
    if (top == "intake" and len(p) > 1 and p[1] in ("references", "before-after")) or top == "archive":
        return "reference"
    if top in ("operations", "core-avatars", "brand-identity"):
        return "internal"
    return "other"


def used_in(label: str) -> dict | None:
    """The ad a file was made for, by its Drive filing: intake/ads/<product>/<project>/… (an ad project and the
    b-roll gathered for it) or briefs/delivered/<brief>/… (an ad delivered from a brief). None otherwise."""
    p = label.split("/")[3:] if label else []
    if len(p) > 3 and p[0] == "intake" and p[1] == "ads":
        name = p[3] if len(p) > 4 else p[2]
        return {"kind": "ad project", "name": name, "product_folder": p[2], "folder": "/".join(p[:4] if len(p) > 4 else p[:3])}
    if len(p) > 2 and p[0] == "intake" and p[1] == "ads":
        return {"kind": "ad project", "name": p[2], "product_folder": p[2], "folder": "/".join(p[:3])}
    if len(p) > 3 and p[0] == "briefs":
        m = re.search(r"brief-(\d+)", p[2])
        return {"kind": "delivered brief", "name": f"brief {m.group(1)}" if m else p[2], "folder": "/".join(p[:3])}
    return None


def filed_of(label: str) -> dict:
    """The Shared Drive's own people filing (content-creators/<gender>/<ethnic-appearance>/<age-band>/<person>/)."""
    p = label.split("/")
    if len(p) > 8 and p[3] == CREATOR_ROOT[0]:
        return {"creator_gender": p[4], "creator_ethnicity": p[5], "creator_age": p[6]}
    return {"creator_gender": "not filed", "creator_ethnicity": "not filed", "creator_age": "not filed"}


def age_of(subject) -> str:
    s = str(subject or "").lower()
    if re.search(r"\bteens?\b", s):
        return "teen"
    if re.search(r"\b(40s|50s|60s|mid-40s|late 50s|middle[- ]aged|older|elderly|mature|senior)\b", s):
        return "40+"
    if re.search(r"\b(30s|early 30s|mid-30s|late 30s)\b", s):
        return "30s"
    if re.search(r"\b(20s|early 20s|mid-20s|late 20s|young adult|young|25-3\d|2\d-\d\d)\b", s):
        return "20s"
    if re.search(r"\badult\b", s):
        return "adult (age not stated)"
    return "unknown"


def marks_of(txt, qn: str, creator: str) -> tuple[list, int]:
    T = D["text_marks"]
    out, words = [], 0
    if txt:
        t = str(txt)
        words = len(re.findall(r"\w+", t))
        if "@" in t:
            out.append("handle")
        if has(t.lower(), T["offer_words"]):
            out.append("offer-text")
        if not out:
            out.append("caption")
    if has(qn, ["username", "handle", "@"]):
        out.append("handle")
    if has(qn, ["tiktok ui", "ui overlay", "ui and", "status bar", "screen recording", "app ui", "instagram ui", "reels ui", "control center"]):
        out.append("app-screen")
    elif has(qn, ["tiktok", "watermark"]):
        out.append("handle")
    if has(qn, ["capcut", "logo at end", "outro", "videoleap", "inshot"]):
        out.append("editor-logo")
    partner = next((x for x in D["partners"]["values"] if x["creator_folder"] == creator and x.get("match") != "handle"), None)
    if partner:
        out = [m for m in out if m != "handle"] + ["partner-handle"]
    out = list(dict.fromkeys(out)) or ["clean"]
    return out, words


CREATORS_DIR = re.compile(r"^(?:\d+\.\s*)?creators$", re.I)
# Social downloads carry the poster's handle in the file name: IG_reel_<h>_<date>, IG-story-<h>-<stamp>, <h>_<date>_<time>.
HANDLE_IN_NAME = [
    re.compile(r"^(?:IG|TT|FB)[_-](?:reel|post|story|video|carousel)[_-](.+?)[_-](?:\d{4}-\d{2}-\d{2}|\d{8}T\d{6})", re.I),
    re.compile(r"^(.+?)_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$"),
]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def _person_folder(path: str) -> str | None:
    """The person folder under a store's own '<n>. Creators/' folder: '1. Founder - Jo Bloggs' -> 'jo', 'Sam' -> 'sam'."""
    p = [x for x in str(path or "").split(" @ ")[0].split("/") if x]
    for i, seg in enumerate(p[:-2]):
        if CREATORS_DIR.match(seg.strip()):
            name = re.sub(r"^\d+\.\s*", "", p[i + 1]).strip()
            name = name.split(" - ", 1)[1] if " - " in name else name
            return _slug(name.split()[0]) if name.split() else None
    return None


def handle_of_file(filename: str) -> str | None:
    stem = Path(str(filename or "").split(" @ ")[0]).stem
    for pat in HANDLE_IN_NAME:
        m = pat.match(stem)
        if m and _slug(m.group(1)):
            return m.group(1)
    return None


def creator_of(label: str, clip: dict | None = None) -> str:
    """The person a clip belongs to: the Drive's content-creators/<gender>/<look>/<age>/<person>/ filing; else the
    person folder under a '<n>. Creators/' folder in the record's own path; else the handle in a social download's
    file name, mapped to its creator folder when the brand's partners table names one. Otherwise the top two
    folders (a bucket such as intake/organic), so an unknown person is never guessed."""
    p = label.split("/")
    if len(p) > 8 and p[3] == CREATOR_ROOT[0]:
        return p[7]
    for path in [(clip or {}).get(k) for k in ("shade_path", "path")] + [label]:
        who = _person_folder(path)
        if who:
            return who
    h = handle_of_file(label.split("/")[-1])
    if h:
        key = re.sub(r"[^a-z0-9]", "", h.lower())
        for x in (D.get("partners") or {}).get("values") or []:
            folder = x.get("creator_folder") or ""
            if "/" not in folder and re.sub(r"[^a-z0-9]", "", str(x.get("handle")).lower()) == key:
                return folder
        return _slug(h)
    return "/".join(p[3:5]) if len(p) > 4 else "?"


def excluded(text: str) -> bool:
    words = (BRAND.get("exclude_words") or {}).get("values") or []
    t = str(text or "").lower()
    return any(w in t for w in words)


def records(brand: str):
    seen_md5 = set()
    for base in sorted(p for p in (RUNS / brand).iterdir() if p.is_dir() and p.name not in ("library", "proof")):
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if not (d / "breakdown.json").is_file():
                continue
            try:
                clip = json.loads((d / "clip.json").read_text())
                bd = json.loads((d / "breakdown.json").read_text())
            except (OSError, ValueError):
                continue
            if isinstance(bd, list):
                bd = bd[0]
            if not (clip.get("meta") or {}).get("duration_s") or not bd.get("scenes"):
                continue
            if excluded(clip.get("label")):
                continue
            m = clip.get("md5")
            if m and m in seen_md5:
                continue
            seen_md5.add(m)
            yield base.name, d, clip, bd


CHECK_MARK = {"caption": "caption", "offer": "offer-text", "handle": "handle", "app-screen": "app-screen",
              "editor-logo": "editor-logo"}
PRODUCTY = ("mechanism", "routine", "product", "proof", "transformation")


def check_files(d: Path) -> list:
    """The check pass's answer files in order: results.jsonl, then results-02.jsonl, results-03.jsonl, …
    (a new one starts when the last would pass PART_BYTES, for the 10 MB repo rule)."""
    return sorted(Path(d).glob("results*.jsonl"), key=lambda p: (p.stem != "results", p.stem))


def check_lines(d: Path) -> list:
    """Every line of every check answer file, in order."""
    return [line for f in check_files(d) for line in f.read_text().splitlines()]


def check_append_file(d: Path, more: int = 0) -> Path:
    """The answer file the next `more` bytes go into: the last one, or a new part when it would pass PART_BYTES."""
    fs = check_files(d)
    last = fs[-1] if fs else Path(d) / "results.jsonl"
    if last.is_file() and last.stat().st_size + more > PART_BYTES:
        return Path(d) / f"results-{len(fs) + 1:02d}.jsonl"
    return last


def checks() -> dict:
    """The check pass's answers (check/results*.jsonl), by clip id. Empty before the pass runs."""
    out = {}
    for line in check_lines(libdir(BRANDNAME[0]) / "check"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        a = d.get("answer")
        if isinstance(a, dict):
            out[d["clip"]] = a
    return out


def _norm_handle(h: str) -> str:
    return re.sub(r"[^a-z0-9_.]", "", str(h).lower())


BRANDNAME = [""]
SNAP_S = 1.0      # a scene edge moves to a real shot change only when one sits within this many seconds


def snap(t0: float, t1: float, cuts) -> tuple[float, float, str]:
    """The editor's in and out: each labelled edge moved to the nearest real shot change within SNAP_S
    (cuts.py), else kept. -> (in, out, 'shot change' | 'label' | 'in on a cut' | 'out on a cut')."""
    if not cuts:
        return round(t0, 2), round(t1, 2), "label"
    def near(t):
        c = min(cuts, key=lambda x: abs(x - t))
        return (c, True) if abs(c - t) <= SNAP_S else (t, False)
    ci, a = near(t0) if t0 > 0 else (t0, False)
    co, b = near(t1)
    if co - ci < 0.3:
        return round(t0, 2), round(t1, 2), "label"
    how = "shot change" if a and b else ("in on a cut" if a else ("out on a cut" if b else "label"))
    return round(ci, 2), round(co, 2), how


def build(brand: str) -> tuple[list, dict]:
    BRANDNAME[0] = brand
    use_brand(brand)
    tq = D["tier"]["quality_flags"]
    pol = D["polish"]["values"]
    partner_h = {_norm_handle(x["handle"]) for x in D["partners"]["values"]}
    brand_h = {_norm_handle(x) for x in D["text_marks"].get("brand_handles", [])}
    CK = checks()
    try:
        CUTS = json.loads((libdir(brand) / "cuts.json").read_text())
    except (OSError, ValueError):
        CUTS = {}
    rows = []
    for col, d, clip, bd in records(brand):
        meta = clip["meta"]
        w, h = meta.get("width") or 0, meta.get("height") or 0
        short = min(w, h)
        label = clip.get("label") or ""
        fn = clip.get("filename") or label.split("/")[-1]
        qn = " | ".join(bd.get("quality_notes") or []).lower()
        qual = has(qn, tq)
        talking = bool(bd.get("talking_head"))
        clip_products = products_of(" ".join(bd.get("products_visible") or []).lower())
        setting_text = str(bd.get("setting") or "").lower()
        frames = clip.get("frames") or []
        ck = CK.get(d.name) or {}
        ck_scenes = {int(x.get("n") or 0): x for x in (ck.get("scenes") or []) if isinstance(x, dict)}
        polish = ck.get("polish") if ck.get("polish") in pol else ("unchecked" if not ck else "unclear")
        handles = [str(x) for x in (ck.get("handles") or [])]
        plat = [str(x) for x in (ck.get("platform_marks") or [])]
        ck_quality = [str(x) for x in (ck.get("quality") or [])]
        ck_people = [p for p in (ck.get("people") or []) if isinstance(p, dict)]
        ck_products = [p for p in (ck.get("products") or []) if p in D["product"]["values"]]
        creator = creator_of(label, clip)
        for i, sc in enumerate(bd["scenes"], 1):
            t0 = float(sc.get("t_start") or 0)
            t1 = float(sc.get("t_end") or t0)
            vis = str(sc.get("visuals") or "")
            spoken = str(sc.get("spoken") or "")
            txt = sc.get("on_screen_text")
            low = vis.lower()
            rule_beats = beats_of(low, talking, spoken)
            cs = ck_scenes.get(i) or {}
            cb = cs.get("beat") if cs.get("beat") in D["beat"]["values"] else None
            beats = list(dict.fromkeys(([cb] if cb else []) + [b for b in rule_beats if b != "other" or not cb]))
            if talking and spoken.strip() and "presenter" not in beats:
                beats.append("presenter")
            prods = products_of(low)
            if beats[0] in PRODUCTY:
                prods = list(dict.fromkeys(prods + (ck_products if ck else clip_products)))
            marks, twords = marks_of(txt, qn, creator)
            if cs:
                marks = [m for m in marks if m != "clean"] + [CHECK_MARK[t] for t in (cs.get("text") or []) if t in CHECK_MARK]
                if cs.get("words") and not twords:
                    twords = len(re.findall(r"\w+", str(cs["words"])))
            if ck:
                if plat:
                    marks.append("platform-mark")
                hn = {_norm_handle(x) for x in handles}
                if "handle" in marks or hn:
                    if hn and hn <= (partner_h | brand_h):
                        marks = [m for m in marks if m != "handle"]
                        marks += ["partner-handle"] if hn & partner_h else []
                        marks += ["brand-handle"] if hn & brand_h else []
                    elif hn:
                        marks.append("handle")
            if any(x["creator_folder"] == creator and x.get("match") != "handle" for x in D["partners"]["values"]):
                marks = [m for m in marks if m != "handle"] + ["partner-handle"]
            marks = list(dict.fromkeys(m for m in marks if m != "clean")) or ["clean"]
            why = []
            if beats[0] == "presenter":
                tier = "P"; why.append("talking to camera")
            else:
                if ck:
                    if polish not in ("studio-staged", "hucg"):
                        why.append(polish)
                    if short < 720:
                        why.append("under 720 px")
                    why += ck_quality
                else:
                    if short < 1080:
                        why.append("under 1080 px")
                    if qual:
                        why.append("quality note")
                if t1 - t0 < 2:
                    why.append("under 2 s")
                tier = "B" if why else "A"
            mid = (t0 + t1) / 2
            fr = min(frames, key=lambda f: abs(float(f.get("at_s") or 0) - mid)) if frames else None
            ci, co, how = snap(t0, t1, CUTS.get(d.name))
            if ck_people:
                gs = {p.get("gender") for p in ck_people} - {"unclear", None}
                osg = "group" if len(ck_people) > 1 else (next(iter(gs)) if gs else "unclear")
                osa = sorted({p.get("age") for p in ck_people} - {None}) or ["unclear"]
            else:
                osg, osa = person_of(bd.get("subject")), [age_of(bd.get("subject"))]
            rows.append({
                "clip": d.name, "collection": col, "scene": i, "in": round(t0, 2), "out": round(t1, 2),
                "cut_in": ci, "cut_out": co, "cut_source": how,
                "seconds": round(t1 - t0, 2), "beat": beats[0], "beats": beats, "beat_rule": rule_beats[0],
                "products": prods,
                "setting": pick(low + " " + setting_text, D["setting"]["values"], D["setting"]["unmatched"]),
                "person": person_of(bd.get("subject")),
                "shot": pick(" ".join(bd.get("shot") or []).lower(), D["shot"]["values"], "medium"),
                "vertical": h > w, "width": w, "height": h,
                "tier": tier, "why": why, "polish": polish, "checked": bool(ck),
                "text_marks": marks, "text_words": twords, "text_size": cs.get("text_size") or ("none" if marks == ["clean"] else "unknown"),
                "handles": handles, "on_screen_text": txt or cs.get("words"), "shows": vis, "says": spoken,
                **filed_of(label), "on_screen_gender": osg, "on_screen_age": ", ".join(osa),
                "source": source_of(label, fn), "used_in": used_in(label), "creator": creator, "file": fn, "label": label,
                "frame": f"{d.parent.name}/{d.name}/{fr['file']}" if fr else None,
            })
    rows += proof_rows(brand)
    cov = coverage(rows)
    return rows, cov


def proof_rows(brand: str) -> list:
    """The proof index's before-and-after PICTURES (proof/proof.json + tags.json from tag.py), as library rows:
    beat proof, one row per picture. Videos filed with them are already footage records."""
    pdir = RUNS / brand / "proof"
    try:
        items = json.loads((pdir / "proof.json").read_text())["items"]
    except (OSError, ValueError, KeyError):
        return []
    try:
        tags = json.loads((pdir / "tags.json").read_text())
    except (OSError, ValueError):
        tags = {}
    out = []
    for it in items:
        if it.get("kind") != "before-after" or it.get("media") != "image" or excluded(it.get("rel")):
            continue
        t = tags.get(it["id"]) or {}
        one = str(t.get("one_line") or "")
        prob = it.get("problem") or next((p for p in PROBLEMS if p in one.lower()), None)
        baked = str(t.get("baked_text") or "unknown").lower()
        marks = ["clean"] if baked in ("none", "") else (["caption"] if baked != "unknown" else ["clean"])
        q = t.get("quality")
        tier = "A" if isinstance(q, (int, float)) and q >= 4 else "B"
        ppl = str(t.get("people") or "")
        g = "man" if re.search(r"\bman\b|\bmen\b|male", ppl) else ("woman" if re.search(r"woman|female", ppl) else "unclear")
        age = "20s" if re.search(r"18-29|20s", ppl) else ("30s" if re.search(r"30-|30s", ppl) else ("40+" if re.search(r"4\d|5\d|6\d|40\+", ppl) else "unclear"))
        out.append({
            "clip": it.get("drive_id") or it["id"], "collection": "proof", "scene": 1, "in": None, "out": None,
            "seconds": 0, "beat": "proof", "beats": ["proof"], "beat_rule": "proof", "kind": "picture",
            "products": [p for p in (t.get("products") or []) if p in D["product"]["values"]],
            "setting": pick(str(t.get("setting") or "").lower(), D["setting"]["values"], D["setting"]["unmatched"]),
            "person": g, "shot": "close-up", "vertical": (it.get("h") or 0) > (it.get("w") or 0),
            "width": it.get("w") or 0, "height": it.get("h") or 0,
            "tier": tier, "why": [] if tier == "A" else [f"picture quality {q}"], "polish": "photo", "checked": bool(t),
            "text_marks": marks, "text_words": 0, "text_size": baked if baked in ("small", "medium", "large") else "none",
            "handles": [it["handle"]] if it.get("handle") else [], "on_screen_text": None,
            "shows": one or it.get("rel", "").split("/")[-1], "says": "",
            "problem": prob, "stage": it.get("stage"), "layout": it.get("layout"), "skin_tone_tag": t.get("skin_tone"),
            "creator_gender": "not filed", "creator_ethnicity": "not filed", "creator_age": "not filed",
            "on_screen_gender": g, "on_screen_age": age,
            "source": "proof", "creator": it.get("person") or "?", "file": it.get("rel", "").split("/")[-1],
            "label": "Shared Assets/brands/%s/%s" % (brand, it.get("rel", "")), "drive_url": it.get("drive_url"),
            "frame": f"proof/{it['thumb']}" if it.get("thumb") else None,
        })
    return out


def coverage(rows) -> dict:
    beats = [b for b in D["beat"]["values"]] + [D["beat"]["unmatched"]]
    prods = list(D["product"]["values"]) + ["none"]
    grid = {b: {p: {"A": 0, "B": 0, "P": 0, "marked": 0, "clean_seconds": 0.0} for p in prods} for b in beats}
    for r in rows:
        for p in (r["products"] or ["none"]):
            c = grid[r["beat"]][p]
            c[r["tier"]] += 1
            if r["text_marks"] != ["clean"]:
                c["marked"] += 1
            elif r["tier"] in ("A", "B"):
                c["clean_seconds"] = round(c["clean_seconds"] + r["seconds"], 1)
    tiers = collections.Counter(r["tier"] for r in rows)
    pictures = sum(1 for r in rows if r.get("kind") == "picture")
    marks = collections.Counter(m for r in rows for m in r["text_marks"])
    people = {k: dict(collections.Counter(r[k] for r in rows)) for k in
              ("creator_gender", "creator_ethnicity", "creator_age", "on_screen_gender", "on_screen_age")}
    clips_people = {}
    for k in ("creator_gender", "creator_ethnicity", "creator_age"):
        seen = {}
        for r in rows:
            seen[r["clip"]] = r[k]
        clips_people[k] = dict(collections.Counter(seen.values()))
    combo = collections.Counter()
    for r in rows:
        if r["creator_gender"] != "not filed":
            combo[f'{r["creator_gender"]} / {r["creator_ethnicity"]} / {r["creator_age"]}'] += 1
    polish = {}
    for r in rows:
        polish[r["clip"]] = r["polish"]
    hcount = collections.Counter(h for c in {r["clip"]: tuple(r["handles"]) for r in rows}.values() for h in c)
    return {"scenes": len(rows) - pictures, "clips": len({r["clip"] for r in rows if r.get("kind") != "picture"}), "tiers": dict(tiers),
            "checked_clips": len({r["clip"] for r in rows if r["checked"] and r.get("kind") != "picture"}),
            "proof_pictures": pictures,
            "proof_problems": dict(collections.Counter(r.get("problem") or "not named" for r in rows if r.get("kind") == "picture")),
            "polish_clips": dict(collections.Counter(polish.values())), "handles": dict(hcount.most_common()),
            "handles_distinct": len({_norm_handle(h) for h in hcount} - {""}),
            "text_marks": dict(marks), "people_scenes": people, "people_clips": clips_people,
            "filed_combos": dict(combo.most_common()),
            "by_beat": dict(collections.Counter(r["beat"] for r in rows)),
            "by_source": dict(collections.Counter(r["source"] for r in rows)),
            "grid": grid}


def query(rows, blank: dict, n: int = 6) -> dict:
    """A storyboard blank in, two bands out (doctrine §10), plus what was dropped and why."""
    floor = TIER_RANK.get(blank.get("min_tier", "B"), 2)
    want_p = blank.get("product")
    dropped = collections.Counter()
    cand = []
    for r in rows:
        if blank.get("beat") and blank["beat"] not in r["beats"]:
            dropped["other beat"] += 1; continue
        if blank.get("stream") == "human-only" and r["source"] == "ai":
            dropped["AI footage (human-only stream)"] += 1; continue
        if blank.get("source") and r["source"] != blank["source"]:
            dropped["other source"] += 1; continue
        if want_p and want_p not in r["products"]:
            dropped["other product"] += 1; continue
        if blank.get("min_tier") == "A" and r["tier"] != "A":
            dropped["below tier A"] += 1; continue
        tx = blank.get("text", "any")
        if tx == "clean" and r["text_marks"] != ["clean"]:
            dropped["text-marked (asked for clean)"] += 1; continue
        if isinstance(tx, list) and not set(r["text_marks"]) <= set(tx + ["clean"]):
            dropped["text mark not allowed"] += 1; continue
        if any(blank.get(k) and r[k] != blank[k] for k in ("creator_gender", "creator_ethnicity", "creator_age")):
            dropped["other filed person"] += 1; continue
        if blank.get("beat") != "presenter" and r["tier"] == "P":
            dropped["talking to camera"] += 1; continue
        for k in ("setting", "person", "shot"):
            if blank.get(k) and r[k] != blank[k]:
                dropped["other " + k] += 1; break
        else:
            words = [w for w in re.findall(r"[a-z]+", str(blank.get("action_words") or "").lower()) if len(w) > 2]
            hit = sum(1 for w in words if w in r["shows"].lower())
            score = (8 if r["beat"] == blank.get("beat") else 0) + TIER_RANK[r["tier"]] * 10 + min(r["seconds"], 6) + min(r["width"], r["height"]) / 1080 + hit * 3 \
                + (2 if r["vertical"] else 0) + (1 if r["text_marks"] == ["clean"] else 0)
            cand.append((score, r))
    cand.sort(key=lambda x: (-x[0], x[1]["clip"], x[1]["scene"]))
    ranked, used = [], set()
    for s, r in cand:
        if r["clip"] in used:
            continue
        ranked.append(r); used.add(r["clip"])
        if len(ranked) == n:
            break
    seen_c = {r["creator"] for r in ranked}
    seen_s = {r["setting"] for r in ranked}
    different = []
    for s, r in sorted(cand, key=lambda x: (x[1]["creator"] in seen_c, x[1]["setting"] in seen_s, -x[0])):
        if r["clip"] in used:
            continue
        different.append(r); used.add(r["clip"]); seen_c.add(r["creator"])
        if len(different) == n:
            break
    if ranked:
        fill = "owned cut"
    else:
        ref = [r for r in rows if (not want_p or want_p in r["products"]) and r["tier"] in ("A", "B")
               and r["shot"] == "close-up" and r["text_marks"] == ["clean"]]
        fill = ("AI with real reference (%d clean close-up frames of the product)" % len(ref)) if ref else \
            "[UNFILLED: %s]" % json.dumps(blank)
    return {"blank": blank, "candidates": len(cand), "fill": fill, "ranked": ranked, "different": different,
            "dropped": dict(dropped)}


FRAMES = Path.home() / "Library" / "Caches" / "asset-library-frames"   # scene frames cut from local proxies; a cache, never committed


def _abs(r) -> Path | None:
    return (RUNS / BRANDNAME[0] / r["frame"]) if r.get("frame") else None


def scene_frame(r) -> str | None:
    """The scene's own middle frame, cut from the record's local proxy (free, ffmpeg); else the nearest saved frame."""
    import subprocess
    fa = _abs(r)
    proxy = fa.parent / "proxy.mp4" if fa else None
    FRAMES.mkdir(parents=True, exist_ok=True)
    out = FRAMES / f"{r['clip']}_{r['scene']}.jpg"
    if out.is_file():
        return str(out)
    if proxy and proxy.is_file():
        at = (r["in"] + r["out"]) / 2
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(at), "-i", str(proxy), "-frames:v", "1",
                        "-vf", "scale=-2:360", str(out)], capture_output=True)
        if out.is_file() and out.stat().st_size > 0:
            return str(out)
    return str(fa) if fa and fa.is_file() else None


DRIVE_ID = re.compile(r"[0-9A-Za-z_-]{25,44}")


def drive_link(r) -> str | None:
    """The scene's file on Google Drive: the row's drive_url, else its clip id, which is the Drive file id."""
    if r.get("drive_url"):
        return r["drive_url"]
    return f"https://drive.google.com/file/d/{r['clip']}/view" if DRIVE_ID.fullmatch(str(r.get("clip") or "")) else None


def source_file(r, mount: Path | None = None) -> Path | None:
    """The scene's original file on the Drive folder synced to this machine (Drive for desktop), or None.
    A row's label is its path under the Shared drives ("Shared Assets/brands/<brand>/..."); mount is the
    synced "Shared Assets" folder, found by components/brandpath/drive_index.mount() when not given.
    Reading here costs no Drive API download quota; with None, fetch by the Drive file id instead."""
    if mount is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("drive_index", REPO / "components" / "brandpath" / "drive_index.py")
        di = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(di)
        mount = di.mount()
    label = r.get("label") or ""
    if not mount or not label.startswith(Path(mount).name + "/"):
        return None
    f = Path(mount).parent / label
    return f if f.is_file() else None


MARK_COLOUR = {"clean": (120, 200, 140), "partner-handle": (120, 170, 240), "caption": (240, 200, 90),
               "handle": (240, 150, 90), "offer-text": (240, 110, 110), "app-screen": (240, 110, 110),
               "editor-logo": (240, 150, 90)}


def _rows_sheet(bands: list, out: Path, per: int = 6, S: int = 160):
    """bands: [(title, [scene rows])]. Each thumbnail is the scene's own frame with its tier and text marks under it."""
    from PIL import Image, ImageDraw
    H = S + 40
    im = Image.new("RGB", (per * (S + 4) + 4, len(bands) * H + 4), (18, 18, 18))
    dr = ImageDraw.Draw(im)
    for bi, (title, rs) in enumerate(bands):
        y = bi * H + 2
        dr.text((6, y + 3), title, fill=(255, 255, 255))
        for j, r in enumerate(rs[:per]):
            x = 4 + j * (S + 4)
            f = scene_frame(r)
            if f:
                t = Image.open(f).convert("RGB")
                t.thumbnail((S, S - 4))
                im.paste(t, (x, y + 18))
            m = r["text_marks"]
            dr.text((x + 2, y + S + 16), f"{r['tier']} · {', '.join(m)}"[:30],
                    fill=MARK_COLOUR.get(m[-1] if m != ["clean"] else "clean", (220, 220, 220)))
    im.save(out, quality=64, optimize=True)


def sheet(rows, out: Path, per: int = 6):
    beats = [b for b in BEAT_ORDER if b != "presenter"]
    bands = []
    for b in beats:
        best = [r for r in query(rows, {"beat": b, "min_tier": "A", "stream": "human-only"}, per * 3)["ranked"]
                if r["beat"] == b][:per]
        bands.append((f"{b}  (tier A, human footage, one per clip; under each: tier · text marks)", best))
    _rows_sheet(bands, out, per)


def blanks_sheet(results: list, titles: list, rows, out: Path):
    """One band per blank: 3 ranked + 3 different; a blank with no owned cut shows its clean reference frames."""
    bands = []
    for t, r in zip(titles, results):
        rs = r["ranked"] + r["different"]
        if not rs:
            want = r["blank"].get("product")
            seen, rs = set(), []
            for x in rows:
                if (not want or want in x["products"]) and x["tier"] in ("A", "B") and x["shot"] == "close-up" \
                        and x["text_marks"] == ["clean"] and x["clip"] not in seen:
                    seen.add(x["clip"]); rs.append(x)
            t += "  ->  no owned cut; clean reference frames for AI"
        bands.append((t, rs))
    _rows_sheet(bands, out)


_ROWS: dict = {}


PART_BYTES = 9_000_000   # one file stays under the repo's 10 MB rule


def write_rows(out: Path, rows: list) -> list:
    """Write the library: one library.json while it fits under PART_BYTES; past that, the rows go into
    library-01.json, library-02.json, … and library.json names the parts (written last, so a reader never sees a
    half-written set). Parts left from an older, longer build are removed. Returns the files written."""
    one = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    text = one(rows)
    names = []
    if len(text.encode()) > PART_BYTES:
        parts, cur, size = [], [], 2
        for r in rows:
            n = len(one(r).encode()) + 1
            if cur and size + n > PART_BYTES:
                parts.append(cur)
                cur, size = [], 2
            cur.append(r)
            size += n
        parts.append(cur)
        for i, part in enumerate(parts, 1):
            names.append(f"library-{i:02d}.json")
            (out / names[-1]).write_text(one(part) + "\n")
        text = json.dumps({"schema": "asset-library-parts/v1", "rows": len(rows), "parts": names,
                           "what": "The library's rows, split across these files (in order) to keep each under 10 MB. "
                                   "Read them with library.read_rows."}, indent=1)
    (out / "library.json").write_text(text + "\n")
    for old in out.glob("library-[0-9]*.json"):
        if old.name not in names:
            old.unlink()
    return ["library.json"] + names


def read_rows(f: Path) -> list:
    """The rows of a built library.json, joining its parts when the library is split (see write_rows)."""
    d = json.loads(Path(f).read_text())
    if isinstance(d, dict):
        return [r for n in d.get("parts") or [] for r in json.loads((Path(f).parent / n).read_text())]
    return d


def rows_of(brand: str) -> list:
    """The built library for a brand (runs/asset-index/<brand>/library/library.json), cached; [] when none."""
    if brand not in _ROWS:
        f = libdir(brand) / "library.json"
        try:
            _ROWS[brand] = read_rows(f)
        except (OSError, ValueError):
            _ROWS[brand] = []
        if _ROWS[brand]:
            BRANDNAME[0] = brand
            use_brand(brand)
    return _ROWS[brand]


A_NEAR = 0.75   # direct b-roll goes first only when its match is within a quarter of the best one


CARRY = ("tier", "why", "polish", "text_marks", "text_size", "handles", "beat", "creator_gender", "creator_ethnicity",
         "creator_age", "on_screen_gender", "on_screen_age", "source", "used_in")


def enrich(hits: list, brand: str) -> list:
    """asset-index search hits in, the same hits out with the library's descriptors on each (under `library`,
    plus tier / text_marks / polish at the top level), duplicates of one file removed (the best score kept),
    talking-to-camera scenes (tier P) left out of b-roll, and direct b-roll (tier A) first when its score is
    within A_NEAR of the best, then by score.
    A brand with no built library gets its hits back unchanged."""
    rows = rows_of(brand)
    if not rows or not hits:
        return hits
    by_label = collections.defaultdict(list)
    for r in rows:
        if r.get("kind") != "picture":
            by_label[r["label"]].append(r)
    best: dict = {}
    for h in hits:
        k = h.get("shared_path") or h.get("clip_id")
        if k not in best or h.get("score", 0) > best[k].get("score", 0):
            best[k] = h
    out = []
    for h in best.values():
        cand = by_label.get(h.get("shared_path") or "") or []
        if cand and h.get("in") is not None:
            a, b = float(h["in"]), float(h.get("out") or h["in"])
            r = max(cand, key=lambda x: (min(b, x["out"]) - max(a, x["in"]), -abs(x["in"] - a)))
        else:
            r = None
        h = dict(h)
        if r:
            h["library"] = {k: r.get(k) for k in CARRY}
            if r.get("cut_in") is not None:
                h["label_in"], h["label_out"] = h.get("in"), h.get("out")
                h["in"], h["out"], h["cut_source"] = r["cut_in"], r["cut_out"], r.get("cut_source")
            h["tier"], h["text_marks"], h["polish"] = r["tier"], r["text_marks"], r["polish"]
            if r["tier"] == "P":
                continue
        out.append(h)
    top = max((h.get("score", 0) for h in out), default=0)
    out.sort(key=lambda h: (-(h.get("tier") == "A" and h.get("score", 0) >= A_NEAR * top), -h.get("score", 0)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["build", "query"])
    ap.add_argument("blank", nargs="?", default="{}")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--sheet", default="", help="write the glance sheet (jpg) to this path")
    a = ap.parse_intermixed_args(argv)
    out = libdir(a.brand)
    if a.cmd == "build":
        rows, cov = build(a.brand)
        out.mkdir(parents=True, exist_ok=True)
        write_rows(out, rows)
        (out / "coverage.json").write_text(json.dumps(cov, indent=1, ensure_ascii=False) + "\n")
        if a.sheet:
            sheet(rows, Path(a.sheet))
        print(json.dumps({k: v for k, v in cov.items() if k not in ("grid", "handles", "filed_combos")}, indent=1))
    else:
        rows = rows_of(a.brand)
        res = query(rows, json.loads(a.blank))
        for band in ("ranked", "different"):
            res[band] = [{k: r.get(k) for k in ("clip", "file", "label", "creator", "in", "out", "tier", "polish", "text_marks",
                                                "beat", "products", "setting", "creator_gender", "creator_ethnicity",
                                                "creator_age", "on_screen_age", "shows")} for r in res[band]]
        print(json.dumps(res, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
