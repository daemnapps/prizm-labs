"""THE EDIT STAGE'S READS (2026-11-13): every body shot against its own line, and every edit note the brief carries.

Why: an ad cut showed hands washing under a line about brushing instead of hands, and dropped notes the brief already
carried; the edit has to follow the brief's own notes on every run.

  line_check   each shot-list row the narrator speaks over: two frames of the rendered cut in that row's slot, and the
               words that play under it (voice/continuous/<scene>.words.json, else the row's phrase), asked through
               the team's vision_judge door: does the shot show what the line says, or what its sentence is about?
               A shot unrelated to its words or showing their opposite holds the production and names the shot and
               the line; a shot nobody could read holds too. Answers are kept in
               edit/line-check.json and reused until the cut or the line changes.
  brief_notes  the writing run's brief (stages/5-brief.md: B-ROLL, CARDS, END CARD, LAYERS AND SOUND) and brief.json
               "edit_notes": every note is one row. What the stage can read off the production is checked there (the
               card's words in the card layer, the captions look, the bed made from the swipe and its effects by
               name, the shot's line check); the rest needs a record in brief.json "edit" under the note's id
               ({"landed": "<where>"} or {"reason": "<why not>"}). A note with neither holds.

Both run inside the Video Studio's edit_stage.run, behind edit-stage.json (`line_check`, `brief_notes`). The rules live
here, in the chain (owner ruling 2026-11-16, V57 (swipe is the backbone)), so every editing path reads the same ones: the Studio's
edit_notes.py is this module.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(p, d=None):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def _norm(s):
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", str(s or "").lower().replace("’", "'"))).strip()


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")[:24]


# ---------------------------------------------------------------- the slots: each row's seconds in the cut
def slots(rows, layout):
    """[{row, scene, a, b, rel_a, rel_b}] for every shot-list row of a scene in the layout (seconds in the cut, and
    in its scene)."""
    out = []
    for sc in (layout or {}).get("scenes") or []:
        mine = [r for r in rows if r.get("scene") == sc["scene"]]
        dur = float(sc["end"]) - float(sc["start"])
        tot = sum(float(r.get("share") or 0) for r in mine) or 1.0
        at = 0.0
        for r in mine:
            span = float(r.get("share") or 0) / tot * dur
            out.append({"row": r, "scene": sc["scene"], "rel_a": at, "rel_b": at + span,
                        "a": float(sc["start"]) + at, "b": float(sc["start"]) + at + span})
            at += span
    return out


def _inside(slot, w):
    return slot["rel_a"] <= (float(w["start"]) + float(w["end"])) / 2 < slot["rel_b"]


def line_of(slot, words):
    """The words heard in a slot: words.json words whose middle falls inside it, else the row's phrase."""
    got = [w["w"] for w in (words or {}).get("words") or [] if _inside(slot, w)]
    return " ".join(got).strip() or str(slot["row"].get("phrase") or "").strip()


def sentence_of(slot, words):
    """The whole sentence(s) the slot's words belong to (a shot under "It has ten" is judged against "It has ten sonic
    vibrations you can choose from…"), else the row's phrase."""
    ws = (words or {}).get("words") or []
    sents, cur = [], []
    for w in ws:
        cur.append(w)
        if re.search(r"[.?!]$", w["w"]):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    got = [" ".join(x["w"] for x in s) for s in sents if any(_inside(slot, x) for x in s)]
    return " ".join(got).strip() or str(slot["row"].get("phrase") or "").strip()


ASK = """Two frames from one shot of a short video ad (the same shot, early and late). The narrator's sentence is:
"{sentence}"
Over this exact shot he says: "{line}"

How does the picture stand to those words, read inside their sentence? Pick one:
  "shows"        it shows the action, product, person or moment the words name (the product under a line about its
                 features; a couple close together under a line about her being close).
  "related"      it shows what the sentence is about, if not the exact words at this point (a man touching the bumps
                 on his jaw under "she can still feel those bumps"; a couple close under a line that promises she'll
                 stay close).
  "unrelated"    it has nothing to do with the sentence (a man talking with no product while the words describe the
                 product; a different product than the one named).
  "contradicts"  it shows the opposite of the words (hands washing while the words say "I stopped using my hands, I
                 brush it now").
Captions burned into the frames are not what the shot shows: judge the picture.
Answer only JSON: {{"fit": "shows" | "related" | "unrelated" | "contradicts", "sees": "what the frames show, one
short sentence", "missing": "what the words need that the frames lack, or empty"}}"""
PASS = ("shows", "related")


def _frame(video, t, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t, "-i", str(video), "-frames:v", "1",
                    "-vf", "scale=360:-2,format=yuvj420p", str(out)], check=True)
    return out


def _vision():
    """The team's vision_judge door: video-production's, beside this component."""
    import importlib.util
    p = HERE.parents[1] / "video-production" / "machine" / "vision_judge.py"
    spec = importlib.util.spec_from_file_location("edit_notes_vj", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def line_check(B, cut, rows, layout, ask=None, frame=_frame):
    """One row per spoken shot: {"id": "line-<row>", "kind": "line", "ours", "what", "landed"|"open_why"}.
    ask(prompt, [images]) -> dict or None (default: the vision_judge door). Cached in edit/line-check.json."""
    B = Path(B)
    cache_f = B / "edit" / "line-check.json"
    cache = _load(cache_f, {}) or {}
    stamp = "%s:%d" % (Path(cut).name, int(Path(cut).stat().st_mtime)) if Path(cut).exists() else str(cut)
    vj = None
    out = []
    tmp = Path(tempfile.mkdtemp(prefix="line-check-"))
    for s in slots(rows, layout):
        words = _load(B / "voice" / "continuous" / ("%s.words.json" % s["scene"]), {})
        line = line_of(s, words)
        if not line or s["b"] - s["a"] < 0.2:
            continue
        rid = s["row"]["id"]
        key = hashlib.sha1(("%s|%s|%s|%s" % (rid, line, stamp, hashlib.sha1(ASK.encode()).hexdigest()[:6])).encode()).hexdigest()[:16]
        ans = cache.get(key)
        if ans is None:
            try:
                imgs = [frame(cut, s["a"] + (s["b"] - s["a"]) * f, tmp / ("%s-%d.jpg" % (rid, i)))
                        for i, f in enumerate((0.3, 0.7))]
                q = ASK.format(line=line, sentence=sentence_of(s, words))
                if ask:
                    ans = ask(q, imgs)
                else:
                    vj = vj or _vision()
                    a = vj.ask(q, imgs, want_json=True)
                    ans = vj.json_of(a)
                    if ans is not None:
                        ans["by"] = a.by()
            except Exception as e:  # noqa: BLE001 — an unread shot holds; it never takes the Studio down
                ans = {"error": str(e)[:200]}
            if ans and ans.get("fit") in PASS + ("unrelated", "contradicts"):
                cache[key] = ans
        r = {"id": "line-%s" % rid, "kind": "line", "swipe_at": 0.0, "ours": round(s["a"], 2), "line": line,
             "what": '%s %.2f-%.2f s under "%s"' % (rid, s["a"], s["b"], line[:120])}
        fit = (ans or {}).get("fit")
        if fit in PASS:
            r["landed"] = "the shot %s its line: %s" % ("shows" if fit == "shows" else "is about", (ans.get("sees") or "")[:160])
        elif fit in ("unrelated", "contradicts"):
            r["open_why"] = "%s %s its line: it shows %s; the line needs %s" % (
                rid, "contradicts" if fit == "contradicts" else "has nothing to do with",
                (ans.get("sees") or "?")[:140], (ans.get("missing") or "?")[:140])
        else:
            r["open_why"] = "%s could not be read against its line (%s)" % (rid, (ans or {}).get("error", "no answer"))
        out.append(r)
    (B / "edit").mkdir(exist_ok=True)
    cache_f.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    return out


# ---------------------------------------------------------------- the brief's edit notes
SECTIONS = (("B-ROLL", "broll"), ("CARDS", "card"), ("END CARD", "endcard"), ("LAYERS AND SOUND", "layer"))


def _tables(md):
    """{section key: [{header: cell}]} for the brief's edit sections, plus "card_words" (the end card's centred words)."""
    out, cur, head = {}, None, None
    extra = {}
    for ln in (md or "").splitlines():
        if ln.startswith("## "):
            t = ln[3:].strip().upper()
            cur = next((k for name, k in SECTIONS if t.startswith(name)), None)
            head = None
            continue
        if cur is None:
            continue
        m = re.match(r"\s*Card words[^:]*:\s*(.+)", ln, re.I)
        if m:
            extra["card_words"] = [w.strip() for w in m.group(1).split("/") if w.strip()]
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            continue
        if head is None:
            head = [c.lower() for c in cells]
            continue
        out.setdefault(cur, []).append(dict(zip(head, cells)))
    out.update(extra)
    return out


def _col(row, *names):
    for k, v in row.items():
        if any(n in k for n in names):
            return v
    return ""


def _card_text(B, scene):
    f = Path(B) / "scenes" / scene / "card" / "index.template.html"
    if not f.exists():
        return None
    return _norm(re.sub(r"<[^>]+>", " ", f.read_text()))


def _caption_misses(text, look):
    t, lk, miss = text.lower(), look or {}, []
    if not lk:
        return ["no caption look is set (brief.json captions.look)"]
    if "uppercase" in t or "upper case" in t:
        if str(lk.get("case", "")).lower() != "upper":
            miss.append("upper case")
    if "bold" in t and int(lk.get("weight") or 400) < 600:
        miss.append("bold")
    if "outline" in t and "no outline" not in t and not float(lk.get("stroke_px") or 0) > 0:
        miss.append("a black outline (stroke_px is 0)")
    if "white" in t and str(lk.get("color", "")).lower() not in ("#fff", "#ffffff", "white"):
        miss.append("white")
    m = re.search(r"(\d+)\s*[–-]\s*(\d+)\s*words", t)
    if m and int(lk.get("max_words") or 99) > int(m.group(2)):
        miss.append("%s-%s words at a time" % m.groups())
    if "no highlight" in t and lk.get("highlight") and str(lk["highlight"]).lower() != str(lk.get("color", "")).lower():
        miss.append("no highlight")
    return miss


def _sfx_names(text):
    return [n.strip().lower() for n in re.findall(r"([a-z][a-z \-]+?)\s*(?:\(|\bon\b)", text.lower())]


def brief_notes(md, brief, B, lines=(), bed=None, alias=None):
    """Every edit note in the brief as a row. lines: the line-check rows (for B-roll notes); bed: music/bed.json."""
    B, alias = Path(B), alias or {}
    tabs = _tables(md)
    notes = []

    def add(nid, kind, what, landed=None, auto_reason=None, open_why=None):
        notes.append({"id": nid, "kind": kind, "swipe_at": 0.0, "ours": None, "what": what[:200],
                      **({"landed": landed} if landed else {}), **({"auto_reason": auto_reason} if auto_reason else {}),
                      **({"open_why": open_why} if open_why else {})})

    line_rows = {r["id"][5:]: r for r in lines}
    for row in tabs.get("broll") or []:
        sc, says = _col(row, "scene"), _col(row, "plays over", "words")
        shows = _col(row, "shows")
        nid = "note-broll-%s" % _slug(sc)
        what = "%s shows %s%s" % (sc, shows, (" under %s" % says) if says else "")
        mine = [r for k, r in line_rows.items() if k.split(".")[0] == sc]
        if not mine and says.strip('" ') and "no words" not in says:       # the scene was folded: find its words
            want = _norm(says).split()

            def near(r):                     # the row's words are mostly the note's, or the note's mostly the row's
                got = _norm(r.get("line")).split()
                return len(got) >= 2 and (sum(x in set(want) for x in got) >= 0.75 * len(got) or
                                          sum(x in set(got) for x in want) >= 0.75 * len(want))
            mine = [r for r in lines if near(r)]
        if mine:
            bad = [r for r in mine if not r.get("landed")]
            if bad:
                add(nid, "note-broll", what, open_why="the line check holds %s" % ", ".join(r["id"][5:] for r in bad))
            else:
                add(nid, "note-broll", what, landed="the line check passed on %s" % ", ".join(r["id"][5:] for r in mine))
        else:
            add(nid, "note-broll", what)
    for kind, key in (("card", "card"), ("endcard", "endcard")):
        for row in tabs.get(key) or []:
            sc = _col(row, "scene")
            words = [w.strip() for w in _col(row, "the words", "words, exactly").split("/") if w.strip()]
            if kind == "endcard":
                words = tabs.get("card_words") or words
            nid = "note-%s-%s" % (kind, _slug(sc))
            what = "%s card words: %s" % (sc, " / ".join(words) or "(none)")
            text = _card_text(B, sc)
            if text is None:
                add(nid, "note-" + kind, what, open_why="%s has no card layer (scenes/%s/card)" % (sc, sc))
                continue
            gone = [w for w in words if _norm(w) and _norm(w) not in text]
            if gone:
                add(nid, "note-" + kind, what, open_why="the card on %s lacks: %s" % (sc, " / ".join(gone)))
            else:
                add(nid, "note-" + kind, what, landed="the card layer on %s carries the words" % sc)
    look = ((brief or {}).get("captions") or {}).get("look")
    effects = {alias.get(e.get("name", "").lower(), e.get("name", "").lower()) for e in (bed or {}).get("effects") or []}
    effects |= {re.sub(r"^sfx-|\.mp3$", "", Path(str(e.get("file") or "")).name).lower() for e in (bed or {}).get("effects") or []}
    for row in tabs.get("layer") or []:
        el, it = _col(row, "element"), _col(row, "what it is")
        nid = "note-layer-%s" % _slug(el)
        what = "%s: %s" % (el, it)
        e = el.lower()
        if e == "captions":
            miss = _caption_misses(it, look if isinstance(look, dict) else None)
            add(nid, "note-layer", what, open_why=("the captions look lacks " + ", ".join(miss)) if miss else None,
                landed=None if miss else "brief.json captions.look matches")
        elif e == "music":
            if (B / "song-cut.json").is_file():
                # a sung ad: the song IS the music, laid scene by scene on its own clock (the Studio's song cut) —
                # a bed remade from the swipe would play under it (20 Nov 2026: every song ad stopped here)
                add(nid, "note-layer", what, landed="the song is the music, laid on the song's own clock (song-cut.json)")
            elif (bed or {}).get("from_swipe"):
                drop = re.search(r"drops at (\d+(?:\.\d+)?)", it)
                if drop and not (bed or {}).get("dropout"):
                    add(nid, "note-layer", what, open_why="the bed has no drop-out (the note drops at %ss)" % drop.group(1))
                else:
                    add(nid, "note-layer", what, landed="the bed is made from the swipe's sound%s" % (
                        ", drop-out %.1f-%.1f s" % tuple(bed["dropout"]) if (bed or {}).get("dropout") else ""))
            else:
                add(nid, "note-layer", what, open_why="the bed is not made from the swipe's sound")
        elif e == "sfx":
            want = [alias.get(n, n) for n in _sfx_names(it)]
            gone = sorted({n for n in want if n not in effects})
            add(nid, "note-layer", what, open_why=("the bed has no %s" % ", ".join(gone)) if gone else None,
                landed=None if gone else "the bed carries %s" % ", ".join(sorted(set(want))))
        elif e in ("hook",) and it.strip().lower() in ("none", "—", "-", ""):
            add(nid, "note-layer", what, auto_reason="nothing to lay")
        elif e in ("sections", "framework", "opens"):
            add(nid, "note-layer", what, auto_reason="the script's order, carried by the shot list; no layer to lay")
        else:
            add(nid, "note-layer", what)
    for i, n in enumerate((brief or {}).get("edit_notes") or [], 1):
        add("note-brief-%d" % i, "note-brief", str(n.get("what") if isinstance(n, dict) else n))
    return notes


def resolve(rows, records):
    """Fold brief.json "edit" records into the rows; returns the ids still open. A record's reason answers a row the
    stage could not lay; a record never overrides a failed read with "landed" (fix the shot, or give the reason)."""
    open_ = []
    for r in rows:
        rec = (records or {}).get(r["id"]) or {}
        if not r.get("landed"):
            if rec.get("reason"):
                r["reason"] = rec["reason"]
            elif rec.get("landed") and not r.get("open_why"):
                r["landed"] = rec["landed"]
            elif r.get("auto_reason"):
                r["reason"] = r["auto_reason"]
        if not r.get("landed") and not r.get("reason"):
            open_.append(r["id"])
    return open_
