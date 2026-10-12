"""THE STORYBOARD — the ad as the edit will hold it, layer by layer (2026-10-01).

the owner: "we don't need to go frame by frame and each scene is more a section of a
bigger video so we need to establish the sections and just design the start
frame and end frame to establish that scene then the moments in between need to
be described" — and — "there are layers to this entire experience … frame control
and layering the timeline so we need to think about this at this stage so when we
actually process it's all the right stuff and editing becomes actually easy."

Built BEFORE anything is generated, from four things already on file:

    the brief         every scene, line, person, look, place, prop, card
    the swipe record  its sections (the teardown's timed shot table: roll, sound,
                      layers), its verbatim transcript with times
    the frame map     every cut and every moment of the swipe (framemap.py)
    the voices        the real length of every line we recorded

and writes, in the production run:

    storyboard.json   SECTIONS — the brief's scenes grouped into the swipe's own
                      sections (one continuous setup each): the swipe span they
                      copy, the shots and cuts inside it, how the picture is made
                      (lip-sync / motion transfer / plate / packshot edit / from
                      the brief), a start frame and an end frame, the moments in
                      between (the swipe's, retimed to our voice), where lips must
                      match our words, and every element the section needs.
                      LAYERS — voice, picture, text, room sound, music, sound
                      effects, frame control — each item placed on the timeline.
                      CHECK — what would make the edit fail, found now.
    STORYBOARD.md     the same, to read.

Brand-agnostic: everything comes from the run's own files.

    python3 storyboard_plan.py <production run> --teardown <teardown run>
"""
import argparse, difflib, json, re, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]

MAKERS = {
    "A": ("lip-sync", "start + end frame, made with its own voice line so the lips match; the moments in between from the swipe"),
    "B-over": ("motion transfer", "the swipe's own clip drives the movement, rebuilt with our people, look and place from the locked elements and our start frame"),
    "C": ("plate", "one plain background; the words are the text layer, never drawn into the picture"),
    "E": ("packshot edit", "the brand's real product photo; the words are the text layer"),
    None: ("from the brief", "no swipe moment to copy (a section we added): start + end frame and the brief's beats"),
}


# ---------------------------------------------------------------- inputs

def brief_doc(path):
    """The brief's block: the last ```json block of a brief.md, or a plan.json as it is."""
    body = Path(path).read_text()
    if str(path).endswith(".json"):
        return json.loads(body)
    return json.loads(re.findall(r"```json\s*\n(.*?)\n```", body, re.S)[-1])


def secs(ts):
    m, s = ts.strip().split(":")
    return int(m) * 60 + float(s)


def swipe_sections(teardown_text):
    """The teardown's timed shot table → [{start, end, roll, section, on_screen, sound, layers, visuals}]."""
    rows = []
    for line in teardown_text.splitlines():
        m = re.match(r"^\|\s*(\d+:\d{2}(?:\.\d+)?)\s*-\s*(\d+:\d{2}(?:\.\d+)?)\s*\|(.*)\|\s*$", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(3).split("|")]
        cells += [""] * (7 - len(cells))
        roll = cells[0].split("·")[0].strip()
        rows.append({"start": secs(m.group(1)), "end": secs(m.group(2)), "roll": roll,
                     "section": cells[1], "visuals": cells[2], "on_screen": cells[3],
                     "transcript": cells[4], "sound": cells[5], "layers": cells[6]})
    for i, r in enumerate(rows, 1):
        r["id"] = f"W{i:02d}"
    return rows


def sound_part(sound, key):
    m = re.search(rf"{key}:\s*([^/]+)", sound or "")
    v = m.group(1).strip() if m else ""
    return "" if v.lower() in ("none", "n/a", "") else v


def voice_seconds(run, sid):
    if run is None:
        return None
    f = Path(run) / "vo" / f"{sid}.mp3"
    if not f.exists():
        return None
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 2)
    except ValueError:
        return None


# ---------------------------------------------------------------- alignment

def _words(t):
    return re.sub(r"[^a-z' ]", " ", (t or "").lower()).split()


def align(scenes, lines, lead):
    """Our spoken scenes ↔ the swipe's transcript lines, in order (the structure
    lock keeps the order). Score: shared words + the same kind of speaker (the
    lead vs anyone else). A scene we added aligns to nothing; returns {scene id: T}."""
    S = [s for s in scenes if (s.get("voice") or "").strip()]
    n, m = len(S), len(lines)

    def score(s, t):
        a, b = _words(s.get("voice")), _words(t.get("text"))
        sim = difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0
        same = (s.get("speaker") == lead) == (t.get("lead"))
        return sim + (0.35 if same else -0.5)

    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    P = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        P[i][0] = "up"
    for j in range(1, m + 1):
        P[0][j] = "left"
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            opts = [(D[i - 1][j - 1] + score(S[i - 1], lines[j - 1]), "diag"),
                    (D[i - 1][j], "up"), (D[i][j - 1], "left")]
            D[i][j], P[i][j] = max(opts, key=lambda x: x[0])
    out, i, j = {}, n, m
    while i > 0 and j > 0:
        p = P[i][j]
        if p == "diag":
            if score(S[i - 1], lines[j - 1]) > 0.2:
                out[S[i - 1]["id"]] = lines[j - 1]
            i, j = i - 1, j - 1
        elif p == "up":
            i -= 1
        else:
            j -= 1
    return out


def shot_type(k):
    """What a swipe shot is, from its frame-map answer — never from a name."""
    if k.get("_type"):
        return k["_type"]
    m = k.get("map") or {}
    who = " ".join(m.get("who") or []).lower()
    held = str((m.get("camera") or {}).get("held") or "").lower()
    height = str((m.get("camera") or {}).get("height") or "").lower()
    if not who.strip() or "graphic" in held:
        return "graphic"
    if not re.search(r"\bface\b|\bhead\b", who) and ("hand" in who or height == "above"):
        return "insert"
    if "arm's length" in held or "arm’s length" in held:
        return "handheld selfie"
    return "set-up shot"


def overlays(k, transcript):
    """On-screen words in a shot that are NOT the captions of what is being said."""
    said = set(w for t in transcript for w in _words(t.get("text")))
    out = []
    for o in (k.get("map") or {}).get("on_screen") or []:
        w = _words(o.get("text"))
        if not w:
            continue
        if "bottom" in str(o.get("where") or "").lower() and sum(1 for x in w if x in said) / len(w) >= 0.4:
            continue                                       # a caption
        out.append({"text": re.sub(r"\s+", " ", str(o.get("text"))).strip(), "where": o.get("where"), "look": o.get("look")})
    return out


def place_shots(shots_, rows):
    """Every swipe shot → the record's section row it belongs to. The record's
    times are rounded to the second; the cuts are exact, so a graphic goes to
    the nearest graphic row and anything filmed to the filmed row it mostly sits in."""
    out = {}
    for k in shots_:
        # a shot that mostly sits inside a graphic row of the record and carries
        # words on screen is that graphic, even with faces in it (an endcard of faces)
        for r in rows:
            if r["roll"] in ("C", "E"):
                ov = min(k["end"], r["end"] + 0.6) - max(k["start"], r["start"] - 0.6)
                if ov >= 0.5 * (k["end"] - k["start"]) and len((k.get("map") or {}).get("on_screen") or []) >= 2 \
                        and shot_type(k) != "graphic" and any(len(_words(o.get("text"))) <= 8 and "bottom" not in str(o.get("where")).lower()
                                                              for o in (k.get("map") or {}).get("on_screen") or []):
                    k["_type"] = "graphic"
    for k in shots_:
        t = shot_type(k)
        mid = (k["start"] + k["end"]) / 2
        pool = [r for r in rows if (r["roll"] in ("C", "E")) == (t == "graphic")] or rows
        inside = [r for r in pool if r["start"] - 0.6 <= mid < r["end"] + 0.6]
        out[k["id"]] = (min(inside or pool, key=lambda r: min(abs(mid - r["start"]), abs(mid - r["end"])) if not (r["start"] <= mid < r["end"]) else -1))
    return out


def _setup(scene):
    """A scene's camera set-up, in words that change only when the set-up does."""
    cam = str((scene.get("first_frame") or {}).get("camera") or "").lower()
    if not cam or cam.strip() in ("same", "held"):
        return "same"
    for k in ("mirror", "selfie", "arm's length", "set still", "propped", "from where the mirror", "top-down", "over the shoulder"):
        if k in cam:
            return k
    return cam[:40]


CLIP_MAX = 15.0       # the clip door: 4–15 s (model-inputs.json); the alternate door takes up to 30 s
ALT_MAX = 30.0


def clips_of(g):
    """A section as the clips that make it: scenes packed in order up to the
    door's 15 s; a single line past 15 s goes to the alternate door (up to 30 s)
    or is split at a beat. A section with a person in it: EVERY clip starts from
    the section's approved picture — never from a clip's last frame (the owner,
    2026-10-03, providers.json ruling_2026_10_03_no_handoffs: 17 of 17 clips from
    the approved picture held the face, 10 of 10 handed-on clips drifted). Only a
    section with nobody in it chains from the real last frame of the one before."""
    out, cur, t = [], [], 0.0
    for sid in g["scenes"]:
        sec = (g.get("voice") or {}).get(sid) or 0.0
        if cur and t + sec > CLIP_MAX:
            out.append({"scenes": cur, "seconds": round(t, 2)}); cur, t = [], 0.0
        cur.append(sid); t += sec + (0.15 if cur[:-1] else 0)
    if cur:
        out.append({"scenes": cur, "seconds": round(t, 2)})
    for c in out:
        if c["seconds"] > CLIP_MAX:
            c["door"] = ("the alternate clip door (up to 30 s)" if c["seconds"] <= ALT_MAX
                         else "split at a beat")
    people = has_people(g)
    for i, c in enumerate(out):
        c["starts_from"] = ("the section's start picture" if i == 0 or people
                            else "the real last frame of the clip before")
    return out


def frame_chain(g) -> str:
    """How a section's clip starts, for the frame-control layer. No hand-offs for people
    (the owner, 2026-10-03): a section with a person starts from its own approved picture; only a
    section with nobody in it may start from the real last frame of the section before; a card or
    plate is a hard cut."""
    if g.get("roll") not in ("A", "B-over"):
        return "hard cut"
    if has_people(g):
        return "start from its approved picture — never the section before's last frame"
    return "start from the real last frame of the section before"


def has_people(g) -> bool:
    """A person of ours is on screen in this section (its elements name one)."""
    return any(str(e).startswith("person · ") for e in g.get("elements") or [])


def cites_of(scene):
    """The swipe shots a scene says it copies — "K02–K04: …" at the head of its source."""
    ks = []
    for a, b in re.findall(r"\bK(\d+)(?:\s*[–-]\s*K?(\d+))?", str(scene.get("source") or "")):
        ks += [f"K{i:02d}" for i in range(int(a), int(b or a) + 1)]
    return ks


_VOICE = {}


def voice_for(run, sid, text, near=""):
    """(seconds, how) for a line. The recording is found by its WORDS, not its
    scene number — a brief renumbered after its voices were made still finds
    them; a line split from a recorded one is estimated from its share of words."""
    if run is None:
        return None, None
    run = Path(run)
    if run not in _VOICE:
        lines = json.loads((run / "lines.json").read_text()) if (run / "lines.json").exists() else {}
        _VOICE[run] = {k: (" ".join(_words(v)), voice_seconds(run, k)) for k, v in lines.items()}
    idx = _VOICE[run]
    w = " ".join(_words(text))
    if not w:
        return None, None
    if sid in idx and idx[sid][0] == w and idx[sid][1]:
        return idx[sid][1], "recorded"
    for k, (t, sec) in idx.items():
        if t == w and sec:
            return sec, f"recorded as {k}"
    cands = [(k, t, sec) for k, (t, sec) in idx.items() if sec and f" {w} " in f" {t} "]
    if cands:
        nb = set(_words(near))
        # a split line came from the recording that also holds its neighbour's words
        k, t, sec = max(cands, key=lambda c: (len(nb & set(c[1].split())), -len(c[1])))
        return round(sec * len(w.split()) / max(1, len(t.split())), 2), f"estimated from {k} (a part of it)"
    return None, None


def row_at(rows, t):
    for r in rows:
        if r["start"] <= t < r["end"]:
            return r
    for r in rows:
        if r["start"] - 0.3 <= t < r["end"] + 0.3:
            return r
    return None


# ---------------------------------------------------------------- the plan

def build(run, teardown_run, brief_path=None):
    if run is not None:
        bp = Path(brief_path) if brief_path else song_brief(Path(run))
        if bp is not None and bp.exists():
            sdoc = brief_doc(bp)
            if is_song(sdoc, Path(run)):
                return build_song(Path(run), teardown_run, bp, sdoc)
    try:
        _man = json.loads((Path(run) / "elements.json").read_text())
        product_scenes = {sid for it in _man.get("items") or [] if it.get("kind") == "product" for sid in it.get("scenes") or []}
    except (OSError, ValueError, TypeError):
        product_scenes = set()
    run, tdir = (Path(run) if run else None), Path(teardown_run)
    brief_path = Path(brief_path) if brief_path else run / "brief.md"
    doc = brief_doc(brief_path)
    tear = (tdir / "stages" / "1-teardown.md").read_text()
    rows = swipe_sections(tear)
    tr = json.loads((tdir / "transcript.json").read_text())
    fm_p = tdir / "framemap" / "framemap.json"
    fm = json.loads(fm_p.read_text()) if fm_p.exists() else None
    scenes = doc.get("scenes") or []
    lead = next((c["id"] for c in doc.get("cast") or []), None)
    lead_speaker = tr[0]["speaker"] if tr else None          # the swipe opens on its lead
    lines = [{**t, "lead": t["speaker"] == lead_speaker} for t in tr]
    matched = align(scenes, lines, lead)

    # cards: the roll sheet names the swipe time of each card row
    card_t = {}
    for r in doc.get("roll_sheet") or []:
        m = re.match(r"\s*(\d+:\d{2})", r.get("row") or "")
        if m and r.get("scene"):
            card_t[r["scene"]] = secs(m.group(1))

    # each scene → the swipe section row it copies
    shot_row = place_shots(fm["shots"], rows) if fm else {}
    used_graphics = set()
    placed, prev = [], None
    kmap = {k["id"]: k for k in (fm or {}).get("shots") or []}
    by_cites = fm is not None and any(cites_of(x) for x in scenes)
    for s in scenes:
        t = matched.get(s["id"])
        if by_cites:
            # the brief says which shots each scene copies — placement is exact
            ks = [k for k in cites_of(s) if k in kmap]
            row = shot_row.get(ks[0]) if ks else None
            if row is not None:
                placed.append({"scene": s, "row": row, "line": t, "added": False, "cites": ks})
            else:
                prev_row = placed[-1]["row"] if placed and placed[-1]["scene"].get("setting_id") == s.get("setting_id") else None
                placed.append({"scene": s, "row": prev_row, "line": t, "added": True, "cites": []})
            prev = placed[-1]
            continue
        when = t["start"] if t else card_t.get(s["id"])
        graphic = s.get("kind") in ("card", "endcard")
        row = None
        if when is not None and fm:
            if graphic:
                gs = [k for k in fm["shots"] if shot_type(k) == "graphic" and k["id"] not in used_graphics] \
                     or [k for k in fm["shots"] if shot_type(k) == "graphic"]
                k = min(gs, key=lambda k: abs(k["start"] - when)) if gs else None
                if k:
                    used_graphics.add(k["id"]); row = shot_row[k["id"]]
            else:
                filmed = [k for k in fm["shots"] if shot_type(k) != "graphic"]
                k = next((k for k in filmed if k["start"] - 0.05 <= when < k["end"]), None) \
                    or next((k for k in filmed if k["start"] >= when), None)
                row = shot_row[k["id"]] if k else None
        elif when is not None:
            row = row_at(rows, when)
        if row is not None and (row["roll"] in ("C", "E")) != graphic:
            row = None          # a filmed line never takes a graphic's row, and a card never takes a filmed one
        if row is None and prev and prev["row"] is not None and prev["scene"].get("setting_id") == s.get("setting_id") \
                and s.get("kind") not in ("card", "endcard"):
            row, added = prev["row"], True        # an added line inside the same setup rides on it
        else:
            added = row is None
        placed.append({"scene": s, "row": row, "line": t, "added": added})
        prev = placed[-1]

    # group consecutive scenes on the same swipe row (or the same added setting)
    groups = []
    for p in placed:
        key = (p["row"]["id"] if p["row"] else "+") + f"|{p['scene'].get('setting_id') or p['scene'].get('kind')}"
        if p["scene"].get("kind") in ("card", "endcard"):
            key += f"|{p['scene']['id']}"     # every card is its own section
        if p["added"]:
            key += "|added"                   # lines the swipe never had are made from the brief, never by stretching a copied clip
            # a new camera set-up is a new section (2026-10-02, QC C3: a close
            # insert of the tube hid inside the talking close)
            cam = _setup(p["scene"])
            if groups and groups[-1]["key"].startswith(key):
                if cam == "same" or groups[-1].get("cam") in (None, cam):
                    key = groups[-1]["key"]            # the same set-up carries on
                else:
                    key += f"|{p['scene']['id']}"
        if groups and groups[-1]["key"] == key:
            groups[-1]["items"].append(p)
        else:
            groups.append({"key": key, "items": [p]})
        if p["added"]:
            c = _setup(p["scene"])
            if c != "same":
                groups[-1]["cam"] = c

    groups_on_row = {}
    for g in groups:
        r = g["items"][0]["row"]
        if r is not None and not g["items"][0]["added"]:
            groups_on_row.setdefault(r["id"], []).append(g)
    # every filmed swipe shot → the group whose spoken lines cover most of it;
    # a shot no line covers (a silent insert) → the nearest group on its row
    owner = {}
    if by_cites:
        taken = set()
        for g in groups:
            for p in g["items"]:
                graphic = p["scene"].get("kind") in ("card", "endcard")
                for kid in p.get("cites") or []:
                    if graphic or kid not in taken:      # a graphic shot may carry a card and the endcard both
                        taken.add(kid)
                        if kmap[kid] not in owner.get(id(g), []):
                            owner.setdefault(id(g), []).append(kmap[kid])
    elif fm:
        for k in fm["shots"]:
            best, bv = None, 0.0
            for g in groups:
                for p in g["items"]:
                    t = p["line"]
                    if t and not p["added"]:
                        ov = min(k["end"], t["end"]) - max(k["start"], t["start"])
                        if ov > bv and (shot_type(k) == "graphic") == (p["scene"].get("kind") in ("card", "endcard")):
                            best, bv = g, ov
            if best is None and shot_type(k) != "graphic":
                r = shot_row.get(k["id"])
                cands = [g for g in groups if g["items"][0]["row"] is r and not g["items"][0]["added"]]
                def dist(g):
                    ts = [p["line"] for p in g["items"] if p["line"]]
                    if not ts:
                        return 1e9
                    a, b = min(t["start"] for t in ts), max(t["end"] for t in ts)
                    return 0 if a <= k["start"] <= b else min(abs(k["start"] - b), abs(k["end"] - a))
                best = min(cands, key=dist) if cands else None
            if best is not None:
                owner.setdefault(id(best), []).append(k)
    sections, clock = [], 0.0
    for gi, g in enumerate(groups, 1):
        items = g["items"]
        row = items[0]["row"]
        sc = [p["scene"] for p in items]
        roll = row["roll"] if row else None
        if roll not in MAKERS:
            roll = "A" if any(x.get("to_camera") for x in sc) else "B-over"
        copied = row is not None and not items[0]["added"]
        if sc[0].get("kind") == "card":
            roll = "C"
        elif sc[0].get("kind") == "endcard":
            roll = "E"
        maker, how = MAKERS[roll if (copied or roll in ("C", "E")) else None]
        if not copied and roll not in ("C", "E"):
            talkers = [x["id"] for x in sc if (x.get("voice") or "").strip() and (x.get("to_camera") or x.get("speaker") == lead)
                       and not re.search(r"'s hands?\b", str(x.get("who") or ""))]   # a voice over hands has no lips
            roll = "A" if any(x.get("to_camera") for x in sc) else "B-over"
            if talkers:
                maker = "lip-sync (from the brief)"
                how = (f"no swipe moment to copy: start + end frame and the brief's beats; "
                       f"{', '.join(talkers)} speak on camera, so it is made with their voice lines")
        vo, vo_how = {}, {}
        for x in sc:
            if (x.get("voice") or "").strip():
                i = next(n for n, y in enumerate(scenes) if y["id"] == x["id"])
                near = " ".join((scenes[j].get("voice") or "") for j in (i - 1, i + 1) if 0 <= j < len(scenes))
                vo[x["id"]], vo_how[x["id"]] = voice_for(run, x["id"], x["voice"], near)
        ours = round(sum(v for v in vo.values() if v) + 0.15 * max(0, len(vo) - 1), 2)
        if not vo:
            ours = round(max(1.0, (row["end"] - row["start"]) if row else 2.0), 2)
        span = None
        if row and copied:
            lt = [p["line"] for p in items if p["line"]]
            # the swipe span is the stretch of the row these lines actually cover
            # (a row can be split by lines we added in between)
            a = min(t["start"] for t in lt) if lt else row["start"]
            b = max(t["end"] for t in lt) if lt else row["end"]
            first_in_row = all(not (q["row"] is row and q["line"] and q["line"]["start"] < a) for q in placed)
            last_in_row = all(not (q["row"] is row and q["line"] and q["line"]["end"] > b) for q in placed)
            span = (row["start"] if first_in_row else a, row["end"] if last_in_row else b)
        shots = []
        if fm and row and copied:
            graphic = sc[0].get("kind") in ("card", "endcard")
            shots = (sorted(owner.get(id(g), []), key=lambda k: k["start"]) if by_cites else
                     [k for k in fm["shots"] if shot_row.get(k["id"]) is row and shot_type(k) == "graphic"][:1]
                     if graphic else sorted(owner.get(id(g), []), key=lambda k: k["start"]))
            if shots:
                span = (shots[0]["start"], shots[-1]["end"])
        if span and span[1] <= span[0] + 0.05:
            # A SPAN THAT RUNS BACKWARDS IS NO SWIPE MOMENT (2026-10-08, the athlete G03: [86.48, 46.7] — lines matched out
            # of order in the swipe). Copying "the swipe's movement" from it left the section with no picture; it is
            # staged from the brief like any section the swipe has no moment for.
            span, shots, copied = None, [], False
            talkers = [x["id"] for x in sc if (x.get("voice") or "").strip() and (x.get("to_camera") or x.get("speaker") == lead)
                       and not re.search(r"'s hands?\b", str(x.get("who") or ""))]
            roll = "A" if any(x.get("to_camera") for x in sc) else "B-over"
            maker, how = MAKERS[None]
            if talkers:
                maker = "lip-sync (from the brief)"
                how = (f"no swipe moment to copy (its matched span ran backwards): start + end frame and the brief's "
                       f"beats; {', '.join(talkers)} speak on camera, so it is made with their voice lines")
        scale = (ours / (span[1] - span[0])) if span and span[1] > span[0] else 1.0
        moments = []
        for k in shots:
            for mo in ((k.get("map") or {}).get("moments") or []):
                try:
                    at = k["start"] + float(mo.get("t") or 0)
                except (TypeError, ValueError):
                    continue
                if span[0] - 0.05 <= at <= span[1] + 0.05:
                    moments.append({"swipe_t": round(at, 2), "t": round((at - span[0]) * scale, 2),
                                    "shot": k["id"], "who": mo.get("who"), "does": mo.get("does"), "face": mo.get("face")})
        cuts = [round((k["start"] - span[0]) * scale, 2) for k in shots[1:] if k["start"] > span[0] + 0.1] if span else []
        lips = []
        for p in items:
            x = p["scene"]
            same = _words(x.get("voice")) == _words((p["line"] or {}).get("text"))
            hands_only = bool(re.search(r"'s hands?\b", str(x.get("who") or "")))
            if (x.get("voice") or "").strip() and (x.get("to_camera") or x.get("speaker") == lead) \
                    and maker == "motion transfer" and not same and not hands_only:
                lips.append({"scene": x["id"], "ours": x["voice"], "swipe": (p["line"] or {}).get("text"),
                             "note": "a visible mouth inside a copied clip: the swipe's mouth says the swipe's words — "
                                     "lip-sync this moment to our line"})
        first, last = sc[0].get("first_frame") or {}, sc[-1].get("last_frame") or {}
        elements = elements_of(sc)
        sections.append({
            "id": f"G{gi:02d}", "scenes": [x["id"] for x in sc], "setting": sc[0].get("setting_id") or sc[0].get("kind"),
            "roll": roll, "maker": maker, "how": how, "added": bool(items[0]["added"] and not row),
            "swipe": {"row": row["id"] if row else None, "span": span, "section": row["section"] if row else None,
                      "visuals": row["visuals"] if row else None,
                      "shots": [{"id": k["id"], "type": shot_type(k), "start": k["start"], "end": k["end"],
                                 "at": round((k["start"] - span[0]) * scale, 2) if span else None,
                                 "first": k.get("stills", {}).get("first"), "last": k.get("stills", {}).get("last"),
                                 "clip": k.get("clip"), "frame": (k.get("map") or {}).get("start_frame"),
                                 "camera": (k.get("map") or {}).get("camera"),
                                 "overlays": overlays(k, tr)} for k in shots]},
            "seconds": ours, "starts": round(clock, 2), "scale_vs_swipe": round(scale, 2) if span else None,
            "voice": vo, "voice_from": vo_how,
            "start_frame": {"from_scene": sc[0]["id"], **{k: first.get(k) for k in ("subject", "composition", "viewpoint", "location", "camera", "lighting") if first.get(k)},
                            "swipe_ref": shots[0]["stills"]["first"] if shots else None,
                            "swipe": ((shots[0].get("map") or {}).get("start_frame") if shots else None)},
            "end_frame": {"from_scene": sc[-1]["id"], "change": last.get("change"), "camera": last.get("camera"),
                          "swipe_ref": shots[-1]["stills"]["last"] if shots else None,
                          "swipe": ((shots[-1].get("map") or {}).get("end_frame") if shots else None)},
            "moments": moments,
            "beats": [{"scene": x["id"], "do": b.get("do"), "over": b.get("over")} for x in sc for b in (x.get("beats") or [])],
            "cuts": cuts, "lips": lips, "elements": elements,
            "frames": frames_for(maker, shots, sc, product_scenes),
        })
        sections[-1]["clips"] = clips_of(sections[-1]) if maker not in ("plate", "packshot edit", "endcard plate") else []
        # a section whose every swipe shot is a clip the swipe already used is
        # made once and reused — no new picture, no new clip (framemap repeats)
        same = [k.get("same_as") for k in shots]
        # an endcard whose plate is our people is made from their pictures
        if sc[0].get("kind") == "endcard":
            plate = str((sc[0].get("endcard") or {}).get("plate") or "")
            named = [c["id"] for c in doc.get("cast") or [] if re.search(rf"\b{re.escape(c['id'])}\b", plate)]
            if named:
                import importlib.util as _u
                _sp = _u.spec_from_file_location("vm_element_refs", HERE / "element_refs.py")
                _er = _u.module_from_spec(_sp); _sp.loader.exec_module(_er)
                _ep = _er._load("element_paths")
                brand = (doc.get("piece") or {}).get("brand")
                bank = {c["id"]: c.get("bank_id") for c in doc.get("cast") or []}
                refs = [str(m) for m in (_er.person_master(_ep.casting_home(brand, bank[n])) for n in named) if m]
                sections[-1]["maker"] = "endcard plate"
                sections[-1]["frames"] = [{"what": "endcard plate", "from": sc[0]["id"], "people": named,
                                           "plate": plate, "refs": refs}]
        # each picture names the brief scene it is made from
        for f in sections[-1]["frames"]:
            if f.get("copies") and not f.get("from"):
                f["from"] = next((x["id"] for x in sc if f["copies"] in cites_of(x)), sc[0]["id"])
        if shots and all(same):
            first = next((x for x in sections[:-1] if any(k["id"] in same for k in x["swipe"]["shots"])), None)
            if first:
                sections[-1]["frames"] = []
                sections[-1]["reuses"] = first["id"]
        clock += ours

    layers = layer_plan(doc, sections, rows, tear)
    # who in the swipe is who in ours: the lead is the swipe's first speaker's
    # person; in each section the one other cast member stands in for the swipe's other person
    swipe_people = (fm or {}).get("people") or []
    lead_sw = swipe_people[0] if swipe_people else None
    others = {}
    for g in sections:
        ours = sorted({e.split(" · ")[1] for e in g["elements"] if e.startswith("person · ")} - {lead})
        if len(ours) == 1:
            others[g["id"]] = {n: ours[0] for n in swipe_people[1:]}
    people_map = {"lead": [lead, lead_sw], "others": others}
    people_lines = {c["id"]: c.get("identity_block") or "" for c in doc.get("cast") or []}
    cap = (fm or {}).get("capture") or {}
    layers["capture"] = {**cap, "style": (doc.get("piece") or {}).get("style"),
                         "rule": "pictures are prompted with the brief's own capture sentence and every clip is finished "
                                 "locally to the swipe's resolution, frame rate and bitrate, with its softness and sensor "
                                 "noise — never cleaner than the swipe"}
    looks = []
    for g in sections:
        for e in g["elements"]:
            if e.startswith("person · ") and e.count(" · ") == 2:
                _, who, look = e.split(" · ")
                if not looks or (who, look) not in [(w, l) for w, l, _ in looks if w == who][-1:]:
                    looks.append((who, look, g["id"]))
    layers["outfits"] = [{"who": w, "look": l, "from": gid} for w, l, gid in looks]
    check = check_plan(doc, sections, layers, fm, tr)
    notes = [f"{g['id']} runs {g['scale_vs_swipe']}× the swipe's time for the same movement — "
             f"the copied clip is retimed (frame control: slow dips, never freezes) or the swipe's own pauses are used"
             for g in sections if g["maker"] == "motion transfer" and g["scale_vs_swipe"] and g["scale_vs_swipe"] > 1.35]
    plan = {"brief": str(brief_path), "teardown": str(tdir), "frame_map": bool(fm),
            "seconds": round(clock, 2), "swipe_seconds": fm["seconds"] if fm else None,
            "sections": sections, "layers": layers, "check": check, "notes": notes,
            "people_map": people_map, "people_lines": people_lines, "style": (doc.get("piece") or {}).get("style")}
    if run is not None:
        (run / "storyboard.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
        (run / "STORYBOARD.md").write_text(markdown(plan))
        # THE BUDGET (2026-10-02): every storyboard comes with what it will
        # likely cost — budget.py writes <run>/BUDGET.md; a budget that cannot
        # be worked out is said, and never stops the storyboard
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("vm_sb_budget", HERE / "budget.py")
            bm = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bm)
            print(bm.write(run, plan)["line"])
        except Exception as e:  # noqa: BLE001 — the storyboard stands without it
            print(f"budget: not worked out — {e}")
    return plan


def elements_of(sc):
    """Every element a section's scenes need: person · look, place, prop, the real packshot."""
    return sorted({f"person · {k} · {v}" for x in sc for k, v in (x.get("looks") or {}).items()}
                  | {f"place · {x.get('setting_id')}" for x in sc if x.get("setting_id")}
                  | {f"prop · {pr if isinstance(pr, str) else pr.get('id') or pr.get('name')}"
                     for x in sc for pr in (x.get("props") or [])}
                  | ({"product · real packshot"} if any("packshot" in json.dumps(x.get("first_frame") or {}).lower()
                                                        or x.get("kind") == "endcard" for x in sc) else set()))


# ---------------------------------------------------------------- a song ad (2026-10-10)
#
# A song ad has no voice lines: the song is the voice, so its sections are clocked
# from the song's own lyric times (SONG-CHAIN.md step 8: song/timing.json, else the
# song transcript's word times). One scene = one sung line = one section = one silent
# clip of the scene's picture (the first song ad, 10 Oct,
# ran on a hand-written storyboard of exactly this shape). A scene with no line of
# its own (an intro, an instrumental) shares the time before the next sung line.

SONG_HOW = "song ad: one silent clip animating the scene's picture under its sung line"
SONG_MATCH = 0.75          # a heard line is a scene's line at this word match or better (providers.json gates.song_lines)


def song_brief(run):
    """The brief a run's storyboard is built from: brief.md, else plan.json."""
    for name in ("brief.md", "plan.json"):
        if (run / name).exists():
            return run / name
    return None


def is_song(doc, run=None) -> bool:
    """A sung piece: its scenes carry `lyrics` and nobody has a voice line, and the
    song is on file (its timing, or its transcript)."""
    scenes = doc.get("scenes") or []
    if any((s.get("voice") or "").strip() for s in scenes):
        return False
    if not any(s.get("lyrics") for s in scenes):
        return False
    if run is None:
        return bool(doc.get("song"))
    return song_timing_file(run, doc) is not None or (run / "song" / "transcript.json").exists()


def song_timing_file(run, doc):
    rel = (doc.get("song") or {}).get("timing") or "song/timing.json"
    f = Path(run) / rel
    return f if f.exists() else None


def _match(a, b) -> float:
    a, b = _words(a), _words(b)
    return difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def heard_lines(run, doc):
    """[{line, start, end}] in the order the song sings them. From song/timing.json
    (SONG-CHAIN.md step 8); without it, from the song transcript's word times,
    each of the brief's sung lines found in order."""
    tf = song_timing_file(run, doc)
    if tf is not None:
        t = json.loads(tf.read_text())
        return [{"line": l.get("line"), "start": l.get("start"), "end": l.get("end")} for l in t.get("lines") or []]
    tr = json.loads((Path(run) / "song" / "transcript.json").read_text())
    words = [w for w in tr.get("words") or [] if w.get("type", "word") == "word"]
    heard = [(_words(w.get("text"))[:1] or [""])[0] for w in words]
    # the scenes' own lines, in play order — a section line no scene sits on (an intro
    # hook sung over the open) would otherwise swallow the first scene's words
    lines = [l for s in doc.get("scenes") or [] for l in s.get("lyrics") or []]
    out, pos = [], 0
    for line in lines:
        want = _words(line)
        sm = difflib.SequenceMatcher(None, heard[pos:], want, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size]
        if not want or not blocks or sum(b.size for b in blocks) / len(want) < SONG_MATCH:
            out.append({"line": line, "start": None, "end": None})
            continue
        i0, i1 = pos + blocks[0].a, pos + blocks[-1].a + blocks[-1].size - 1
        out.append({"line": line, "start": float(words[i0]["start"]), "end": float(words[i1]["end"])})
        pos = i1 + 1
    return out


def song_seconds(run, doc, heard):
    """The song's full length: the transcript's audio length, else the file's, else its last heard word."""
    tf = Path(run) / "song" / "transcript.json"
    if tf.exists():
        try:
            d = float(json.loads(tf.read_text()).get("audio_duration_secs") or 0)
            if d:
                return round(d, 2)
        except (ValueError, TypeError):
            pass
    f = Path(run) / ((doc.get("song") or {}).get("file") or "song/song.mp3")
    if f.exists():
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                           capture_output=True, text=True)
        try:
            return round(float(r.stdout.strip()), 2)
        except ValueError:
            pass
    ends = [h["end"] for h in heard if h.get("end") is not None]
    return round(max(ends), 2) if ends else 0.0


def song_clock(scenes, heard, total):
    """{scene id: (start, seconds, lyric, how)} on the song's clock. A scene starts on
    its first sung line, found in the song in order; a scene with no line of its own,
    or whose line was not heard, shares the time between its timed neighbours. Each
    scene lasts until the next one starts; the last runs to the end of the song."""
    anchor, pos = {}, 0
    for s in scenes:
        lyric = " ".join(s.get("lyrics") or []).strip()
        first = (s.get("lyrics") or [""])[0]
        if not lyric:
            continue
        for j in range(pos, len(heard)):
            if _match(first, heard[j].get("line")) >= SONG_MATCH:
                pos = j + 1
                if heard[j].get("start") is not None:
                    anchor[s["id"]] = float(heard[j]["start"])
                break
    ids = [s["id"] for s in scenes]
    starts, i = {}, 0
    while i < len(ids):
        if ids[i] in anchor:
            starts[ids[i]] = anchor[ids[i]]; i += 1; continue
        j = i
        while j < len(ids) and ids[j] not in anchor:
            j += 1
        a = starts[ids[i - 1]] if i else 0.0
        if i:                                        # the timed scene before keeps its own line's time
            prev_end = next((h["end"] for h in heard if h.get("start") == starts[ids[i - 1]]), None)
            a = max(a, prev_end or a)
        z = anchor[ids[j]] if j < len(ids) else total
        step = (z - a) / (j - i)
        for n, k in enumerate(range(i, j)):
            starts[ids[k]] = round(a + n * step, 2)
        i = j
    out = {}
    for n, sid in enumerate(ids):
        a = starts[sid]
        z = starts[ids[n + 1]] if n + 1 < len(ids) else total
        sc = scenes[n]
        how = ("on its sung line" if sid in anchor else
               "no sung line of its own — shares the time before the next" if not sc.get("lyrics") else
               "its line was not heard in the song — timed between its neighbours")
        out[sid] = (round(a, 2), round(max(0.0, z - a), 2), " ".join(sc.get("lyrics") or []).strip(), how)
    return out


def build_song(run, teardown_run, brief_path, doc):
    """The storyboard of a song ad: one section per scene, clocked from the song."""
    scenes = doc.get("scenes") or []
    heard = heard_lines(run, doc)
    total = song_seconds(run, doc, heard)
    clock = song_clock(scenes, heard, total)
    tdir = Path(teardown_run) if teardown_run else None
    fm_p = tdir / "framemap" / "framemap.json" if tdir else None
    fm = json.loads(fm_p.read_text()) if fm_p and fm_p.exists() else None
    kmap = {k["id"]: k for k in (fm or {}).get("shots") or []}
    cast = doc.get("cast") or []
    if isinstance(cast, dict):         # a plan.json carries the cast as {name: lead, names: [...]}
        cast = [{"id": x} for x in cast.get("names") or [cast.get("name")] if x]
    lead = next((c["id"] for c in cast), None)
    sections, of_scene = [], {}
    for n, sc in enumerate(scenes, 1):
        sid = sc["id"]
        a, sec, lyric, _how = clock[sid]
        gid = f"G{n:02d}"
        of_scene[sid] = gid
        ks = [kmap[k] for k in cites_of(sc) if k in kmap]
        first = (sc.get("frames") or [{}])[0] if sc.get("frames") else (sc.get("first_frame") or {})
        g = {"id": gid, "scenes": [sid], "setting": sc.get("setting_id") or sc.get("kind"),
             "roll": "B-over", "maker": "from the brief", "how": SONG_HOW, "added": False,
             "swipe": {"row": None, "span": None, "section": None, "visuals": None,
                       "shots": [{"id": k["id"], "type": shot_type(k), "start": k["start"], "end": k["end"], "at": 0.0,
                                  "first": (k.get("stills") or {}).get("first"), "last": (k.get("stills") or {}).get("last"),
                                  "clip": k.get("clip"), "frame": (k.get("map") or {}).get("start_frame"),
                                  "camera": (k.get("map") or {}).get("camera"), "overlays": []} for k in ks]},
             "seconds": sec, "starts": a, "scale_vs_swipe": None, "voice": {}, "voice_from": {},
             "lyric": lyric, "sung": _how,
             "start_frame": {"from_scene": sid, **{k: first.get(k) for k in ("subject", "composition", "viewpoint",
                                                                            "location", "camera", "lighting") if first.get(k)}},
             "end_frame": {}, "moments": [], "beats": [], "cuts": [], "lips": [],
             # a plan.json scene names its product and keeps its pictures under `frames`
             "elements": sorted(set(elements_of([sc])) | ({"product · real packshot"} if sc.get("product") or
                                "packshot" in json.dumps(sc.get("frames") or []).lower() else set())),
             "frames": [{"what": "start frame", "from": sid}],
             # every song-ad section is a clip — no stills, no holds (the owner, 2026-10-10)
             "clips": [{"scenes": [sid], "seconds": sec, "starts_from": "the section's start picture"}]}
        m = re.match(r"\s*reuse\s*:\s*(\S+)", str(sc.get("make") or ""))
        if m and m.group(1) in of_scene:
            # a repeated line (a chorus) plays the clip already made for it — made once
            g["frames"], g["reuses"] = [], of_scene[m.group(1)]
            g["clips"] = [{"scenes": [sid], "seconds": sec}]
        sections.append(g)
    layers = layer_plan(doc, sections, [], "")
    layers["song"] = (doc.get("song") or {}).get("file") or "song/song.mp3"
    layers["voice"] = []
    check = []
    for sid, (a, sec, lyric, how) in clock.items():
        if lyric and how != "on its sung line":
            check.append(f"{sid}: {how} (\"{lyric[:60]}\")")
        if sec <= 0:
            check.append(f"{sid} has no time on the song's clock")
    plan = {"brief": str(brief_path), "teardown": str(tdir) if tdir else None, "frame_map": bool(fm),
            "seconds": round(total, 2), "swipe_seconds": fm["seconds"] if fm else None,
            "sections": sections, "layers": layers, "check": check,
            "notes": [f"clocked from the song's lyric times ({'song/timing.json' if song_timing_file(run, doc) else 'the song transcript'}): "
                      f"each section starts on its sung line"],
            "people_map": {"lead": [lead, ((fm or {}).get("people") or [None])[0]], "others": {}},
            "people_lines": {c["id"]: c.get("identity_block") or "" for c in cast if c.get("identity_block")},
            "style": (doc.get("piece") or {}).get("style"), "song": True}
    (run / "storyboard.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    (run / "STORYBOARD.md").write_text(markdown(plan))
    return plan


SWIPE_FINDING = re.compile(r"the swipe (cuts to an insert|shows |has a )|the swipe's (\(K\d+\) )?from the")


def swipe_carry(brief_path, teardown_run):
    """What the brief drops or changes from the swipe's frame map — the inserts,
    the words on screen, the edge each arm enters from. Run at the brief stage
    (no voices needed), so a brief is held before production ever sees it.
    -> [{"n": "F1", "finding": …}]; [] when there is no frame map."""
    if not (Path(teardown_run) / "framemap" / "framemap.json").exists():
        return []
    blocks = re.findall(r"```json\s*\n(.*?)\n```", Path(brief_path).read_text(), re.S)
    if not blocks or '"scenes"' not in blocks[-1]:
        return []                                  # a written (creator / founder) brief has no shot list to hold
    plan = build(None, teardown_run, brief_path)
    found = [c for c in plan["check"] if SWIPE_FINDING.search(c)]
    return [{"n": f"F{i}", "finding": c} for i, c in enumerate(found, 1)]


POSTURES = ("walking", "walks", "standing", "stands", "lowering", "sitting down", "seated", "sits", "lying", "kneeling")


def setup_key(scene):
    """The camera set-up a scene's first frame describes: its shot size (the composition's first word) and the
    lead's posture (the first posture word in its subject)."""
    ff = scene.get("first_frame") or {}
    size = str(ff.get("composition") or "").split(",")[0].split(" ")[0].strip().lower()
    subj = str(ff.get("subject") or "").lower()
    posture = next((p for p in POSTURES if p in subj), "")
    posture = {"walks": "walking", "stands": "standing", "sits": "seated", "sitting down": "lowering"}.get(posture, posture)
    return (size, posture)


def frames_for(maker, shots, sc, product_scenes=()):
    """The pictures this section needs generated — and nothing more."""
    if maker == "plate":
        return [{"what": "card background", "from": sc[0]["id"]}]
    if maker == "packshot edit":
        return [{"what": "endcard on the real packshot", "from": sc[0]["id"]}]
    if maker == "motion transfer":
        # one reference still per kind of shot in the section: each kind is its
        # own camera set-up (the consult, her selfie, an insert) and the clips of
        # that kind are all driven from it
        out, seen = [], set()
        for k in shots:
            t = shot_type(k)
            if t not in seen:
                seen.add(t)
                out.append({"what": f"start frame · {t}", "copies": k["id"], "drives": [x["id"] for x in shots if shot_type(x) == t],
                            # the section's first kind is its scene's own first frame; any other kind
                            # (her selfie cutaway inside a consultation) is its own picture, written
                            # from that swipe shot with our people in it
                            "own": bool(out)})
        return out
    first, last = sc[0], sc[-1]
    if maker.startswith("lip-sync"):
        # a talking clip is its first picture + its voice — the door takes no end
        # picture (model-inputs.json: "A TALKING scene = image_references [the
        # first frame] + audio_references … NO end_image").
        # ONE PICTURE PER SET-UP, NOT PER SECTION (2026-10-08, the athlete): every clip starts from an approved
        # picture, so a section whose brief changes set-up inside it (he walks in wide, then sits for a medium
        # shot) needs a picture for each — with one, every clip of a 62 s section started from him walking
        # in, and he stood through half the ad. A new set-up is a new shot size or a new posture.
        # the product coming into the frame is a set-up too (2026-10-08, the athlete S7: he brings the device up but no
        # picture had it on the table, so Omni drew a hairbrush) — the element manifest says where it is
        key = lambda x: setup_key(x) + (x["id"] in product_scenes,)
        out, cur = [{"what": "start frame", "from": first["id"]}], key(first)
        for x in sc[1:]:
            k = key(x)
            if k != cur:
                out.append({"what": "set-up frame", "from": x["id"], "setup": True})
                cur = k
        return out
    same = (last is first or (
        str((first.get("first_frame") or {}).get("composition")) == str((last.get("first_frame") or {}).get("composition"))
        and set(first.get("looks") or {}) == set(last.get("looks") or {})))
    # an edit can move a hand, never re-frame a shot or bring a face in
    # (2026-10-02, QC B4): a section that ends on another framing or with other
    # people ends on its last scene's own picture
    # an end frame that EDITS the section's start frame carries that scene's id (S10-FLAST, an edit of S10-F1):
    # the model input contract holds an edit to the frame it edits, by name (2026-10-08, preflight rule 12
    # refused S11-FLAST whose first reference was S10-F1)
    return [{"what": "start frame", "from": first["id"]},
            ({"what": "end frame", "from": first["id"], "edit_of": first["id"], "ends": last["id"]} if same
             else {"what": "end frame (own picture)", "from": last["id"]})]


def own_picture(base, g, k, plan):
    """A picture for a kind of shot the brief has no first frame for (a cutaway
    inside a section): the swipe shot's own first frame, its people swapped for
    ours, in the section's place and look — refs inherited from the section's
    start frame, so the same people, looks and set travel with it."""
    names = plan.get("people_map") or {}
    lead_ours, lead_swipe = names.get("lead") or (None, None)
    text = str(k.get("frame") or "")
    if lead_swipe and lead_ours:
        text = re.sub(rf"\b{re.escape(lead_swipe)}\b", lead_ours, text)
    for sw, ours in (names.get("others") or {}).get(g["id"], {}).items():
        text = re.sub(rf"\b{re.escape(sw)}\b", ours, text)
    cam = k.get("camera") or {}
    camera = ", ".join(x for x in (cam.get("height"), cam.get("distance"), cam.get("held")) if x)
    style = plan.get("style") or ""
    ff = g.get("start_frame") or {}
    who_line = (plan.get("people_lines") or {}).get(lead_ours, "") if lead_ours else ""
    looks = "; ".join(e.split(" · ", 1)[1].replace(" · ", " in ") for e in g.get("elements") or [] if e.startswith("person · "))
    prompt = " ".join(x for x in (
        text, f"{lead_ours}: {who_line}." if who_line else "",
        f"Wearing: {looks}." if looks else "",
        f"Camera: {camera}." if camera else "",
        f"Place: {ff.get('location')}." if ff.get("location") else f"Place: {g['setting']}.",
        f"Light: {ff.get('lighting')}." if ff.get("lighting") else "",
        "The same people, looks and place as the section's other shots.", style,
        "No camera, no phone, no tripod, no filming equipment in frame unless held by the person filming herself. "
        "No words, letters or captions anywhere in the picture.") if x)
    # the outfit IN WORDS, carried from the section's start frame — a look's id
    # alone ("look-2-denim") put Nova in a T-shirt (2026-10-02, Section 7)
    worn = " ".join(x.strip() + "." for x in re.split(r"(?<=\.)\s+", (base.get("params") or {}).get("prompt", ""))
                    if " wears " in x).replace("..", ".")
    if worn:
        prompt = prompt.replace(f"Wearing: {looks}.", worn) if looks else prompt + " " + worn
    it = json.loads(json.dumps(base))
    it["id"] = f"{base['id'].split('-')[0]}-{re.sub(r'[^A-Z]', '', str(k.get('type', 'shot')).upper())[:8]}-{k.get('id')}"
    it["kind"] = "still"
    it.setdefault("params", {})["prompt"] = prompt
    it["medias"] = [m for m in it.get("medias") or [] if not re.match(r"^S\d+-F1$", str(m.get("value")))]
    # only the people in THIS swipe shot: with the section's doctor still in the
    # references the door added him to her selfie (2026-10-02, Section 7)
    others = [o for o in ((names.get("others") or {}).get(g["id"], {}) or {}).values() if o and o in text]
    if lead_ours and not others:
        slug = re.sub(r"[^a-z0-9]+", "-", lead_ours.lower()).strip("-")
        it["medias"] = [m for m in it["medias"] if not ("/casting/" in str(m.get("value")) and
                        str(m.get("value")).endswith("master.png") and f"/{slug}/" not in str(m.get("value")))]
    it["copies_swipe_shot"] = k.get("id")
    return it


def usable_frame(shots, k_id):
    """The shot's first frame — unless it is a transition (mostly black or blown
    out), then its middle, then its last. Section 11's guide was the black glitch
    that opens K23, and with nothing to copy the door invented a different woman
    (2026-10-02)."""
    from PIL import Image
    for name in ("first", "mid", "last"):
        f = shots / f"{k_id}-{name}.jpg"
        if not f.is_file():
            continue
        # judged on the middle band only: a card's letterbox bars are black but
        # its middle carries the receipt; a transition's middle is black too
        g = Image.open(f).convert("L").resize((64, 112)).crop((0, 39, 64, 73))
        px = list(g.tobytes())
        dead = sum(1 for v in px if v < 24 or v > 245) / len(px)
        if dead < 0.5:
            return f
    return None


def swipe_camera_ref(plan, k_id):
    """The swipe shot's usable frame, SHARP since 2026-10-08 (it was blurred — faces and captions unreadable,
    camera, framing and light kept), cached beside it as <K>-camera.jpg.
    THE RECIPE (the owner, 2026-10-02: "literally everything looks perfect now"):
    this swipe shot as the FIRST reference on the ruled still door (GPT Image
    2.5), the written framing dropped, everything else as bound."""
    td = plan.get("teardown")
    if not td:
        return None
    shots = (Path(__file__).resolve().parent / td / "framemap" / "shots").resolve()
    src = usable_frame(shots, k_id)
    if src is None:
        return None
    out = shots / f"{k_id}-camera.jpg"
    from PIL import Image, ImageFilter
    im = Image.open(src).convert("RGB")
    im.save(out, quality=92)   # SHARP (the owner, 2026-10-08: "I don't know why you would blur a frame")
    return str(out)


def with_swipe_camera(it, cam, k_id, composition=None):
    """The blurred swipe shot goes in FIRST (dropping the lowest reference past
    the door's five — props and outfit sheets go first, the outfit is said in
    words), the written framing comes out, and the rule says what to copy."""
    it = json.loads(json.dumps(it))
    refs = [m for m in it.get("medias") or [] if m.get("role") == "image_references"]
    rest = [m for m in it.get("medias") or [] if m.get("role") != "image_references"]
    if it.get("swipe_camera") == k_id and refs and refs[0].get("value") == cam:
        return it
    # element_refs may already carry this blurred shot as the composition
    # reference (2026-10-08): it moves to FIRST, never in twice
    refs = [m for m in refs if m.get("value") != cam]
    while len(refs) >= 5:
        refs.pop()
    refs.insert(0, {"role": "image_references", "value": cam})
    it["medias"] = refs + rest
    rule = _rule("swipe_camera")
    if rule and isinstance(it.get("params"), dict):
        pr = it["params"].get("prompt", "")
        if composition:
            c = " ".join(str(composition).split()).rstrip(".")
            pr = pr.replace(c + ".", "").replace(c, "")
        it["params"]["prompt"] = (" ".join(pr.split()) + " " + rule).strip()
    it["swipe_camera"] = k_id
    return it


def _rule(name) -> str:
    try:
        c = json.loads((Path(__file__).resolve().parent / "model-inputs.json").read_text())
        return ((c.get("frame_rules") or {}).get(name) or {}).get("says") or ""
    except (OSError, ValueError):
        return ""


def _endcard_rule() -> str:
    try:
        c = json.loads((Path(__file__).resolve().parent / "model-inputs.json").read_text())
        return ((c.get("frame_rules") or {}).get("endcard") or {}).get("says") or ""
    except (OSError, ValueError):
        return ""


def picture_jobs(plan, items):
    """The storyboard's pictures as production's own still/edit items — and only
    those. A start frame is its scene's first frame; a section's end frame is an
    edit of the SECTION's start frame (not of its own scene's), so a section is
    two pictures, never three; a card is its plate; the endcard its packshot.
    -> (kept items, problems)."""
    by_id = {str(i.get("id")): i for i in items}
    keep, problems = [], []
    for g in plan["sections"]:
        for f in g["frames"]:
            sid = f.get("from")
            w = f["what"]
            iid = (f"{sid}-PLATE" if w == "card background" else f"{sid}-PACKSHOT" if w.startswith("endcard")
                   else f"{sid}-FLAST" if w == "end frame" else f"{sid}-F1")
            if w == "endcard plate" and iid not in by_id:
                iid = next((k for k in by_id if k.startswith(f"{sid}-")), iid)
            it = by_id.get(iid)
            if it is None:
                problems.append(f"{section_no(g['id'])}: {w} — production has no item {iid}")
                continue
            it = json.loads(json.dumps(it))
            if f.get("own"):
                k = next((x for x in g["swipe"]["shots"] if x["id"] == f["copies"]), {})
                it = own_picture(it, g, k, plan)
            if w == "endcard plate":
                # the endcard the brief describes (its people), not the product photo
                it["kind"] = "still"
                it["id"] = f"{sid}-ENDCARD"
                it.setdefault("params", {})["prompt"] = " ".join(x for x in (
                    f.get("plate"), plan.get("style") or "",
                    # model-inputs.json frame_rules.endcard (the three-doctors run QC, 2026-10-02)
                    _endcard_rule() if len(f.get("refs") or []) > 1 else "",
                    "No words, letters, numbers or prices anywhere in the picture.") if x)
                it["medias"] = [{"role": "image_references", "value": r} for r in f.get("refs") or []]
                it.pop("packshot", None)
            # THE SWIPE SHOT IS A REFERENCE (the owner, 2026-10-02: "literally look like
            # the swipe … this is what makes it indistinguishable from AI"). Every
            # first frame that copies a swipe shot carries that shot, blurred so no
            # face or on-screen word can be lifted: camera, angle, framing and light
            # come from the picture, not from words. model-inputs.json frame_rules.swipe_camera
            if w != "end frame" and w != "endcard plate":
                k_id = f.get("copies") or ((g.get("start_frame") or {}).get("swipe_ref") or "").split("-")[0]
                cam = swipe_camera_ref(plan, k_id) if k_id else None
                if cam:
                    sf = g.get("start_frame") or {}
                    it = with_swipe_camera(it, cam, k_id, composition=None if (f.get("own") or f.get("setup")) else sf.get("composition"))
            it["section"] = section_no(g["id"])
            if f.get("edit_of") and f["edit_of"] != sid:
                for m in it.get("medias") or []:
                    if m.get("value") == f"{sid}-F1":
                        m["value"] = f"{f['edit_of']}-F1"
            keep.append(it)
    return keep, problems


def layer_plan(doc, sections, rows, tear):
    L = {"voice": [], "picture": [], "text": [], "room": [], "music": [], "sfx": [], "frame_control": [], "capture": {}, "outfits": []}
    rowmap = {r["id"]: r for r in rows}
    for g in sections:
        t = g["starts"]
        for sid, sec in g["voice"].items():
            L["voice"].append({"scene": sid, "at": round(t, 2), "seconds": sec, "file": f"vo/{sid}.mp3"})
            t += (sec or 0) + 0.15
        L["picture"].append({"section": g["id"], "at": g["starts"], "seconds": g["seconds"], "roll": g["roll"],
                             "maker": g["maker"], "covers": {"from": g["scenes"][0], "to": g["scenes"][-1]}})
        row = rowmap.get(g["swipe"]["row"]) if g["swipe"]["row"] else None
        room = sound_part(row["sound"], "room") if row else ""
        if room:
            L["room"].append({"section": g["id"], "at": g["starts"], "seconds": g["seconds"], "what": room})
        fx = sound_part(row["sound"], "effects") if row else ""
        if fx:
            L["sfx"].append({"section": g["id"], "at": g["starts"], "what": fx, "from": "the swipe's section " + row["id"]})
        for sid in g["scenes"]:
            sc = next(s for s in doc["scenes"] if s["id"] == sid)
            words = sc.get("on_screen") if isinstance(sc.get("on_screen"), str) else ""
            card = (sc.get("card") or {}).get("lines") or (sc.get("screen") or {}).get("lines") or []
            end = sc.get("endcard") or {}
            if card:
                L["text"].append({"section": g["id"], "scene": sid, "at": g["starts"], "kind": "card text", "words": card})
            elif end:
                L["text"].append({"section": g["id"], "scene": sid, "at": g["starts"], "kind": "endcard text",
                                  "words": [w for w in (end.get("offer_lines") or []) + [end.get("cta") or ""] if w]})
            elif words and words.lower() != "nothing":
                L["text"].append({"section": g["id"], "scene": sid, "at": g["starts"], "kind": "on screen", "words": [words]})
        fc = {"section": g["id"], "cuts_at": g["cuts"],
              "chain": frame_chain(g),
              # a push-in hides a jump cut; with no cut in the swipe there is nothing to hide (2026-10-08)
              "push_in": g["roll"] in ("B-over",) and g["seconds"] > 3 and bool(g["cuts"])}
        if row and row.get("layers"):
            tr = re.search(r"transition out:\s*([^/|]+)", row["layers"])
            fc["transition_out"] = (tr.group(1).strip() if tr else "none")
        L["frame_control"].append(fc)
    hook = (doc.get("layers") or {}).get("hook") or {}
    if hook.get("text"):
        L["text"].insert(0, {"section": sections[0]["id"], "at": 0.0, "kind": "hook headline",
                             "words": [w.strip() for w in hook["text"].split("/")], "look": hook.get("look"),
                             "rule": "on frame one, no fade, lives as long as the first clip"})
    cap = (doc.get("edit") or {}).get("captions")
    if cap:
        L["text"].append({"kind": "captions", "at": 0.0, "look": cap, "words": "every spoken line"})
    mus = (doc.get("edit") or {}).get("music") or ""
    if mus:
        L["music"].append({"at": 0.0, "what": mus, "bank": doc.get("music")})
    return L


def check_plan(doc, sections, layers, fm, tr=None):
    out = []
    seen = [sid for g in sections for sid in g["scenes"]]
    for s in doc.get("scenes") or []:
        if seen.count(s["id"]) != 1:
            out.append(f"{s['id']} sits in {seen.count(s['id'])} sections — every scene sits in exactly one")
    if not fm:
        out.append("no frame map of the swipe — the moments in between cannot be copied (framemap.py)")
    for g in sections:
        if g["maker"] == "motion transfer" and not g["swipe"]["shots"]:
            out.append(f"{g['id']} copies the swipe's movement but no swipe shot is mapped to it")
        for sid, sec in g["voice"].items():
            if not sec:
                out.append(f"{sid} has a line but no recorded voice — the section's length is unknown")
        for k in ("subject", "composition"):
            if g["maker"] not in ("plate", "packshot edit", "endcard plate") and g["roll"] in ("A", "B-over") and not g["start_frame"].get(k):
                out.append(f"{g['id']} start frame has no {k}")
    # which swipe shots each scene says it copies ("K02–K04: …" in its source)
    cites = {}
    for x in doc.get("scenes") or []:
        ks = []
        for a, b in re.findall(r"\bK(\d+)(?:\s*[–-]\s*K?(\d+))?", str(x.get("source") or "")):
            ks += [f"K{i:02d}" for i in range(int(a), int(b or a) + 1)]
        cites[x["id"]] = ks
    kmap = {k["id"]: k for k in (fm or {}).get("shots") or []}
    by_scene = {x["id"]: x for x in doc.get("scenes") or []}
    for g in sections:
        if g["maker"] in ("plate", "packshot edit"):
            continue
        pairs = []
        for sid in g["scenes"]:
            ks = [k for k in cites.get(sid, []) if k in kmap]
            if ks:      # a scene that names its shots is held to the first of them
                ff = by_scene[sid].get("first_frame") or {}
                pairs.append((sid, ks[0], " ".join(str(ff.get(k) or "") for k in ("subject", "composition", "viewpoint")),
                              (kmap[ks[0]].get("map") or {}).get("start_frame") or ""))
        if not pairs and g["start_frame"].get("swipe"):
            pairs.append((g["id"], (g["swipe"]["shots"] or [{}])[0].get("id"),
                          " ".join(str(g["start_frame"].get(k) or "") for k in ("subject", "composition", "viewpoint")),
                          g["start_frame"]["swipe"]))
        for who, kid, ours, sw in pairs:
            a, b = edges(ours), edges(sw)
            if a and b and not (a & b):
                out.append(f"{g['id']} {who}: our arms enter from the {', '.join(sorted(a))} edge, the swipe's ({kid}) from the "
                           f"{', '.join(sorted(b))} — copy the swipe's body geometry in the start frame")
    carried = set()
    for x in doc.get("scenes") or []:
        for a, b in re.findall(r"\bK(\d+)(?:\s*[–-]\s*K?(\d+))?", str(x.get("source") or "")):
            for i in range(int(a), int(b or a) + 1):
                carried.add(f"K{i:02d}")
    if fm and any(cites.values()):
        # a brief that names its shots must name every one of them
        allc = {k for ks in cites.values() for k in ks}
        for k in fm.get("shots") or []:
            if k["id"] in allc:
                continue
            kind = shot_type(k)
            what = "cuts to an insert" if kind == "insert" else f"has a {kind}"
            out.append(f"the swipe {what} at {k['start']:.1f} s ({k['id']}: {str((k.get('map') or {}).get('start_frame'))[:90]}) — "
                       f"no scene of the brief copies it; if the swipe has it, the brief carries it")
            for o in overlays(k, tr or []):
                out.append(f"the swipe shows \"{o['text']}\" on screen at {k['start']:.1f} s ({k['id']}, {o.get('where')}) — "
                           f"no text layer in the brief carries it")
    ours_text = " ".join(" ".join(t["words"]) if isinstance(t.get("words"), list) else str(t.get("words"))
                         for t in layers["text"]).lower()
    for g in sections:
        if g["maker"] in ("plate", "packshot edit"):
            continue
        for k in g["swipe"]["shots"]:
            if k["type"] == "insert" and k["id"] not in carried:
                out.append(f"{g['id']}: the swipe cuts to an insert at {k['start']:.1f} s ({k['id']}: {str(k.get('frame'))[:90]}) — "
                           f"the brief has no scene for it; if the swipe has it, the brief carries it")
            def _words_on(x):
                # words a scene puts on screen: its on-screen line, a card's lines, an endcard's lines
                w = [str(x.get("on_screen") or "")] + list((x.get("card") or {}).get("lines") or []) \
                    + list((x.get("screen") or {}).get("lines") or []) + list((x.get("endcard") or {}).get("offer_lines") or [])
                return [t for t in w if t.strip().lower() not in ("", "nothing", "none")]
            shown = [sid for sid, ks in cites.items() if k["id"] in ks and _words_on(by_scene[sid])]
            for o in k["overlays"]:
                if g is sections[0] and k is g["swipe"]["shots"][0]:
                    continue                      # the opening overlay is the hook layer
                if shown:
                    continue                      # a scene copying this shot puts its own words on screen — the format, our words
                if not any(w in ours_text for w in _words(o["text"]) if len(w) > 3):
                    out.append(f"{g['id']}: the swipe shows \"{o['text']}\" on screen at {k['start']:.1f} s ({k['id']}, {o.get('where')}) — "
                               f"no text layer in the brief carries it")
    texts = [w for t in layers["text"] if isinstance(t.get("words"), list) for w in t["words"] if len(w) > 6]
    for g in sections:
        frame = json.dumps(g["start_frame"]).lower() + json.dumps(g["end_frame"]).lower()
        for w in texts:
            if w.lower() in frame:
                out.append(f"{g['id']}: the words \"{w}\" are in a frame description — words are the text layer, never drawn into a picture")
    cast = {c["id"] for c in doc.get("cast") or []}
    used = {e.split(" · ")[1] for g in sections for e in g["elements"] if e.startswith("person")}
    for c in cast - used:
        out.append(f"{c} is in the cast but on no layer")
    worlds = {w["id"] for w in doc.get("world") or []}
    places = {g["setting"] for g in sections}
    for w in worlds - places:
        out.append(f"place {w} is in the brief but on no layer")
    return out


EDGE = re.compile(r"enter(?:s|ing)?\s+(?:the\s+frame\s+)?from\s+(?:the\s+)?((?:top|bottom|upper|lower)?[\s-]*(?:left|right|top|bottom)?)\s*(?:edge|side|corner)", re.I)


def edges(text):
    """Which frame edges limbs enter from, normalised: {'top right', 'right', …}."""
    out = set()
    for m in EDGE.finditer(text or ""):
        e = re.sub(r"\s+", " ", m.group(1).lower().replace("-", " ")).strip()
        e = e.replace("upper", "top").replace("lower", "bottom")
        if e:
            out.add(e)
    return out


PLAIN = {"lip-sync": "talking to camera, lip-synced to our voice",
         "lip-sync (from the brief)": "talking, lip-synced; not in the swipe, staged from the brief",
         "motion transfer": "the swipe's own movement, rebuilt with our people",
         "from the brief": "staged from the brief; not in the swipe",
         "plate": "price card", "packshot edit": "endcard on the real product photo",
         "endcard plate": "endcard: our people, the words laid on in the edit"}


def mmss(sec):
    if sec is not None and 0 < sec < 10:
        return f"0:0{sec:.1f}"          # a short line still shows its length, never 0:00
    sec = int(round(sec or 0))
    return f"{sec // 60}:{sec % 60:02d}"


def section_no(gid):
    """G03 is the machine's id; a reader sees Section 3 (the owner, 2026-10-02: one word, one meaning)."""
    return f"Section {int(str(gid)[1:])}"


def relabel(text):
    return re.sub(r"\bG0*([0-9]+)\b", lambda m: "Section " + m.group(1), str(text))


def markdown(p):
    """The storyboard to read, in the page's fixed words: swipe shot (cut to cut in
    the swipe) · scene (one row of the brief) · section (one continuous set-up,
    one clip to make) · picture (a still we generate) · lengths in m:ss."""
    secs_ = p["sections"]
    n = sum(len(g["frames"]) for g in secs_)
    L = [f"# Storyboard — {len(secs_)} sections · {n} pictures · {mmss(p['seconds'])}"
         + (f" (swipe {mmss(p['swipe_seconds'])})" if p.get("swipe_seconds") else ""), "",
         "Words: **swipe shot** = the swipe from one cut to the next · **scene** = one row of the brief "
         "(one line or one card) · **section** = scenes filmed as one continuous camera set-up, one clip to make · "
         "**picture** = a still we generate to start a section · lengths are m:ss.", "",
         "| Section | Where | Scenes | Copies swipe shots | Length | How it's made | Pictures | Clips |",
         "|---|---|---|---|---|---|---|---|"]
    for i, g in enumerate(secs_, 1):
        sc = g["scenes"][0] + (f"–{g['scenes'][-1]}" if len(g["scenes"]) > 1 else "")
        L.append(f"| {i} | {g['setting']} | {sc} | {', '.join(k['id'] for k in g['swipe']['shots']) or '—'} | "
                 f"{mmss(g['seconds'])} | {PLAIN.get(g['maker'], g['maker'])}"
                 + (f" — the same clip as {section_no(g['reuses'])}" if g.get("reuses") else "") + f" | {len(g['frames'])} | "
                 + (str(len(g.get("clips") or [])) + (" (one past 15 s)" if any(c.get("door") for c in g.get("clips") or []) else "")) + " |")
    for i, g in enumerate(secs_, 1):
        sp = g["swipe"]["span"]
        L += ["", f"## Section {i} · {g['setting']} · scenes {g['scenes'][0]}–{g['scenes'][-1]} · {PLAIN.get(g['maker'], g['maker'])}", "",
              f"Length {mmss(g['seconds'])}" + (f" · copies the swipe from {mmss(sp[0])} to {mmss(sp[1])}" if sp else " · not in the swipe")
              + f" · pictures: {'; '.join(f['what'] for f in g['frames'])}", "",
              f"**Start** ({g['start_frame']['from_scene']}): {g['start_frame'].get('subject','')}",
              f"**End** ({g['end_frame'].get('from_scene', '—')}): {g['end_frame'].get('change','')}",
              *([f"**Sung** ({g.get('sung')}): {g['lyric']}"] if g.get("lyric") or g.get("sung") else []),
              f"**Elements:** {'; '.join(g['elements'])}", ""]
        if g["moments"]:
            L += ["| our time | swipe time | who | does |", "|---|---|---|---|"]
            L += [f"| {m['t']} s | {m['swipe_t']} s | {m.get('who','')} | {str(m.get('does','')).replace('|','/')} |" for m in g["moments"]]
        for l in g["lips"]:
            L.append(f"- lips {l['scene']}: ours \"{l['ours']}\" vs swipe \"{l['swipe']}\"")
    L += ["", "## Where our version runs longer than the swipe's movement", ""] + ([f"- {relabel(c)}" for c in p.get("notes") or []] or ["- none"])
    L += ["", "## Check", ""] + ([f"- {relabel(c)}" for c in p["check"]] or ["- clean"])
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run")
    ap.add_argument("--teardown", help="the swipe's teardown run (needed unless the piece is a song ad)")
    ap.add_argument("--brief")
    a = ap.parse_args()
    _bp = Path(a.brief) if a.brief else song_brief(Path(a.run))
    if not a.teardown and not (_bp and _bp.exists() and is_song(brief_doc(_bp), Path(a.run))):
        ap.error("--teardown is required (only a song ad, clocked from its song, is built without one)")
    p = build(a.run, a.teardown, a.brief)
    print(f"{len(p['sections'])} sections · {sum(len(g['frames']) for g in p['sections'])} pictures · "
          f"{mmss(p['seconds'])} · check: {len(p['check'])} finding(s)")
    for c in p["check"]:
        print("  ", c)
