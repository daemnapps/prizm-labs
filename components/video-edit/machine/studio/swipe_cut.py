"""Swipe cut: each scene's take cut to the swipe's own shot lengths, through the Video Studio. No per-ad cut script.

  python3 swipe_cut.py <production>                 saves a new take of every scene the picks name (Studio API)
  python3 swipe_cut.py <production> --run [S2 S3]   also runs them through the Studio (POST .../run)
  python3 swipe_cut.py <production> --dry-run       prints the takes, saves nothing

Reads two things in briefs/<production>/:
  shot-list.json  from swipe_shots.py: one row per swipe shot each scene copies, with its `share` of the scene
  picks.json      the person's picks: which clip plays each shot (the creative choice is data, not code)
     {"shots":   {"<shot id>": {"source": "<key>", "in": 4.0, "note": "what it shows"}},
                                                                      every shot is moving footage: a still picture is refused
      "sources": {"<key>": "<file path>"},                         new files; keys already on a take need no line
      "cards":   {"<scene>": {"on": "<shot id>"} | {"off": "why"}}, the scene's card rides on that shot only, or is dropped
      "people":  {"demographic": "white", "library": "<footage index library.json>",
                  "cast": {"<ROLE>": "<the creator's folder name>"}},
                                                                      everyone on screen from one creator pool; others refused.
                                                                      A story (a song ad, or any brief with cast) names its
                                                                      cast: a shot whose pick carries "role" plays only that
                                                                      creator's footage, so one lead runs the whole story
      "add":     {"<scene>": [{"after": "<shot id> or null", "id": "<id>", "share": 0.3, "source": ..., "in": ...,
                                "note": "...", "why": "the owner's call, in his words"}]}}
     "add" is only for shots the owner asked for beyond the swipe; their share comes out of the scene's other shots
     in proportion, so the swipe's rhythm holds across the rest.
Each scene keeps its current take's read (voice.read) and cards (hyperframes.card, layer cards); only the pictures
change. Every picture step is placed by `weight` = its share, so the Studio splits the scene's read in the swipe's
proportions: the swipe's quick bursts and held shots survive at any read length. No minimum length is coded.
THE EDITING RULES are the chain's, called from here, never copied (owner ruling 2026-11-16, V57 (swipe is the backbone)): how long a shot plays
and where in its clip it starts (components/video-edit/machine/shot_timing.py), and the frame look on every shot
(components/video-production/machine/frame_look.py). This file only finds the Studio's files and the index's cuts.
MOMENTS FIRST (owner, 17 Nov: editing is a lookup on the asset index): both rules answer from the index's moments
(components/asset-index/library/moments.py, measured and judged once per clip) and read a clip live only when it has
no moments yet. A production can switch this off with shot_fill.moments: false in its brief.json.
Brand-agnostic.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")  # the Studio's production side (settings, takes, voices) until each seam is cut
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))  # this folder first, then the Studio it serves
import settings as ST  # noqa: E402
# the cut's own ffmpeg calls are tiny reads (a few seconds of a clip, four frames): they skip the machine's ffmpeg queue,
# which long jobs elsewhere can hold for minutes (17 Nov: a 3 s read waited 5 minutes); renders still queue
os.environ.setdefault("DAEMN_FFMPEG_DIRECT", "1")
TIMING = ST.chain("video-edit", "shot_timing")      # how long a shot plays, where it starts, the swap
LOOKS = ST.chain("video-production", "frame_look")  # every shot looked at, frame by frame

STUDIO = os.environ.get("VIDEO_STUDIO_URL", "http://127.0.0.1:8922")


def api(path, body=None):
    req = urllib.request.Request(STUDIO + path, data=json.dumps(body or {}).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read())


def source_entry(path):
    if isinstance(path, dict):
        return path
    p = Path(path)
    return {"file": p.name, "drive_location": str(p), "library": None, "creator": None}


STILL = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".tif", ".tiff")


def refuse_still(sid, p, src):
    """No still picture plays as b-roll: every shot is real moving footage."""
    f = str((src or {}).get("drive_location") or (src or {}).get("file") or "") if isinstance(src, dict) else str(src or "")
    if p.get("photo") or f.lower().endswith(STILL):
        raise SystemExit("%s: a still picture is not b-roll. Pick real video footage for this shot." % sid)


def people_check(picks, scenes):
    """Everyone on screen comes from one creator pool (picks["people"]). A pick the footage index files under another
    demographic is refused; one the index does not know is listed to check by eye. Generated (G-) and composite (C-)
    sources are checked when they are made."""
    want = (picks.get("people") or {}).get("demographic")
    lib = (picks.get("people") or {}).get("library")
    if not want or not lib or not Path(lib).exists():
        return
    d = json.load(open(lib))
    if isinstance(d, dict):                       # a split library: library.json lists its parts beside it
        d = [x for part in d.get("parts") or [] for x in json.load(open(Path(lib).parent / part))]
    eth = {}
    for x in d:
        if x.get("file") and x.get("creator_ethnicity") not in (None, "not filed", "unknown-ethnicity"):
            eth[x["file"]] = x["creator_ethnicity"]
            if x.get("label"):                    # the clip's name on the shared drive, as picks name it
                eth[Path(x["label"]).name] = x["creator_ethnicity"]
    bad, unknown = [], []
    for rows in scenes.values():
        for r in rows:
            p = {**r, **(picks["shots"].get(r["id"]) or {})}
            key = p.get("source") or ""
            path = (picks.get("sources") or {}).get(key)
            if not isinstance(path, str) or key.startswith(("G-", "C-")):
                continue
            e = eth.get(Path(path).name)
            if e is None:
                unknown.append(r["id"])
            elif e != want:
                bad.append("%s (%s)" % (r["id"], e))
    if unknown:
        print("people: the index has no demographic for %s; check by eye" % ", ".join(unknown))
    if bad:
        raise SystemExit("people: outside the %s creator pool: %s. Re-pick from that pool." % (want, ", ".join(bad)))


def cast_check(picks, scenes, brief, sung=False):
    """One story, one cast (owner, 20 Nov 2026, on a real-footage song ad cut from random people: "so bad"). A story
    (a song ad, or a brief that names cast) must name its cast in picks["people"]["cast"] as role -> creator folder;
    every shot whose pick carries "role" must play that creator's footage, and every role named must be on screen."""
    cast = (picks.get("people") or {}).get("cast") or {}
    story = sung or bool(brief.get("cast") or brief.get("cast_roles"))
    if story and not cast:
        raise SystemExit("cast: this ad tells a story; name its cast in picks.people.cast (role -> creator folder) and "
                         "give each shot of a cast member its role. One lead through the story, never a montage of "
                         "strangers. If the footage has no one person who can carry it, say so instead of cutting.")
    if not cast:
        return
    srcs = picks.get("sources") or {}
    bad, seen = [], set()
    for rows in scenes.values():
        for r in rows:
            p = {**r, **(picks["shots"].get(r["id"]) or {})}
            role = p.get("role")
            if not role or role == "EXTRA" or p.get("join"):   # an extra is anyone; a joined beat has no clip
                continue
            if role not in cast:
                bad.append("%s (role %s is not in the cast)" % (r["id"], role))
                continue
            path = srcs.get(p.get("source") or "")
            if (p.get("source") or "").startswith(("G-", "C-")):   # made from the cast member's sheet: checked when made
                seen.add(role)
                continue
            if not isinstance(path, str) or cast[role].lower() not in path.lower():
                bad.append("%s (%s is not %s's footage)" % (r["id"], role, cast[role]))
            else:
                seen.add(role)
    missing = [k for k in cast if k not in seen]
    if bad or missing:
        raise SystemExit("cast: " + "; ".join(bad + ["%s never on screen" % k for k in missing]))


def one_clip_once(made, picks):
    """EACH SOURCE CLIP ONCE PER AD (owner, 21 Nov 2026: "you're literally just repeating the same clips over and over
    again"): one stretch of any one clip file in the whole ad, not one stretch per time range. A second use of a file is
    refused and named, unless its pick carries "keep" (the owner's own call). -> the refusals, in words."""
    seen, out = {}, []
    for sid, rows, wf in made:
        srcs = wf.get("sources") or {}
        for st in list(wf.get("steps") or []):
            if st.get("tool") != "ffmpeg.trim":
                continue
            key = str((st.get("inputs") or {}).get("source") or "").replace("slot:", "")
            if key.startswith(("G-", "C-")):
                continue
            s = srcs.get(key) or {}
            f = _sk(s.get("drive_location") or s.get("file") or key) if isinstance(s, dict) else _sk(s or key)
            shot = (st.get("note") or "").split(" · ")[0]
            if (picks["shots"].get(shot) or {}).get("keep"):
                continue
            if f in seen:
                ours = any(r.get("status") == "ours" for r in rows)
                trims = [x for x in wf["steps"] if x.get("tool") == "ffmpeg.trim"]
                if ours and len(trims) > 1:      # our script's beat: it joins its neighbour (small miss, 20 Nov)
                    i = trims.index(st)
                    nb = trims[i - 1] if i > 0 else trims[i + 1]
                    nb.setdefault("params", {})["weight"] = round(float(nb["params"].get("weight") or 0)
                                                                  + float((st.get("params") or {}).get("weight") or 0), 4)
                    wf["steps"].remove(st)
                    _JOINED.append("%s %s joined its neighbour: the same clip as %s" % (sid, shot, seen[f]))
                    continue
                out.append("%s %s: the same clip as %s (%s)" % (sid, shot, seen[f], Path(str(f)).name))
            else:
                seen[f] = shot
    return out


def plan(n):
    bd = ST.BRIEFS / n
    sl = json.load(open(bd / "shot-list.json"))
    picks = json.load(open(bd / "picks.json"))
    brief = json.load(open(bd / "brief.json"))
    scenes = {}
    for r in sl["shots"]:
        scenes.setdefault(r["scene"], []).append(dict(r))
    for sid, adds in (picks.get("add") or {}).items():
        rows = scenes.setdefault(sid, [])
        took = sum(a["share"] for a in adds)
        if rows and took >= 0.9:          # added shots never leave the scene's own shots a negative or vanishing share
            adds = [{**a, "share": a["share"] * 0.75 / took} for a in adds]
            took = 0.75
        for r in rows:
            r["share"] = r["share"] * (1 - took)
        for a in adds:
            at = next((i + 1 for i, r in enumerate(rows) if r["id"] == a.get("after")), 0 if a.get("after") is None else len(rows))
            rows.insert(at, {**a, "scene": sid, "copies": "", "status": "owner added: " + a.get("why", "")})
    out = {}
    for sid, rows in scenes.items():
        if not all(r["id"] in picks["shots"] or r.get("source") for r in rows):
            continue                          # a scene is cut only when every one of its shots has a pick
        out[sid] = rows
    return brief, picks, out


def _song_cut(n):
    try:
        return json.load(open(ST.BRIEFS / n / "song-cut.json"))
    except (OSError, ValueError):
        return {}


# NEVER SHIPPED (owner, 20 Nov 2026, on a real-footage cut: "so bad"): a shot whose frames fail and no clip of the
# pool passes is not kept with a note; the cut is refused and names the shots to re-pick. These always refuse; a
# sung footage ad also refuses a clip that does not show its line.
# A pick the owner asked for by name carries "keep": "<his words>" and stays, its reason on the shot.
HARD = ("letterboxed", "other_brand", "blur_or_transition", "dead")
_REFUSED = []
_JOINED = []
_USED = set()         # every clip file the cut has placed in this ad (a clip file plays once per ad)
_PLAYED = {}          # every clip section the cut has placed in this ad, across scenes (the edit check's no_repeat)


def take_for(n, sid, rows, picks, brief, all_sources):
    sd = ST.BRIEFS / n / "scenes" / sid
    base = json.load(open(sd / (brief["picks"][sid] + ".json")))
    keep = [s for s in base["steps"] if s["tool"] in ("voice.read",) or s["tool"].endswith(".card") or s.get("id", "").startswith("card")]
    steps = [s for s in keep if s["tool"] == "voice.read"]
    # a scene with no read (an end card) has no length to share out: each shot runs the swipe shot's own seconds
    unread = not steps
    sources = dict(base.get("sources") or {})
    used_paths = _USED                # ONE USE PER CLIP (owner, 21 Nov): a swap never takes a clip the ad already plays
    sections = _PLAYED                # path -> (in, out) already played anywhere in the ad: no clip moment twice
    carry_w = [0.0]                   # the time of a joined opening beat, handed to the next shot
    first_out = [None]
    carry_need = [0.0]                # the seconds of a joined opening beat, handed to the next shot
    for i, r in enumerate(rows, 1):
        p = {**r, **(picks["shots"].get(r["id"]) or {})}
        if p.get("join"):
            # ONE USE PER CLIP (owner, 21 Nov): a beat with no unused clip of the cast plays on as the shot before it
            # (its seconds go to that shot); the first beat of a scene hands its seconds to the next shot
            slot_ = ((_song_cut(n).get("scenes") or {}).get(sid) or {}).get("seconds")
            extra = float(slot_) * (r["share"] / max(sum(x["share"] for x in rows), 1e-6)) if slot_ \
                else float(r.get("seconds") or 0)
            prev = next((x for x in reversed(steps) if x["tool"] == "ffmpeg.trim"), None)
            if prev:
                prev["params"]["weight"] = round(float(prev["params"].get("weight") or 0) + r["share"], 4)
                if unread:
                    prev["inputs"]["out"] = round(float(prev["inputs"]["out"]) + extra, 3)
            else:
                carry_w[0] += r["share"]
                carry_need[0] += extra
            _JOINED.append("%s %s plays on as the shot before it (no unused clip of the cast)" % (sid, r["id"]))
            continue
        key = p["source"]
        if key not in sources:
            path = (picks.get("sources") or {}).get(key)
            sources[key] = source_entry(path) if path else all_sources[key]
        refuse_still(r["id"], p, sources.get(key))
        prm = {"weight": round(r["share"] + carry_w[0], 4)}
        carry_w[0] = 0.0
        prm.update(p.get("params") or {})
        what = "%s · copies %s (swipe %s s) · %s" % (r["id"], r.get("copies") or "—", r.get("swipe_seconds") or "—", p.get("note", ""))
        own = round(min(float(r.get("swipe_seconds") or 2.0), MAX_SHOT), 3)   # its action, never a held pause
        # the seconds this shot plays: its own swipe seconds, or its share of the scene's read
        import video_studio as VS  # noqa: E402 - the Studio's own probe, as the cards below use it
        if unread and r.get("seconds"):       # a sung scene: the shot list carries its seconds on the song's clock
            own = round(float(r["seconds"]), 3)
        need = own if unread else round(r["share"] * (VS.probe_dur(str(ST.BRIEFS / n / steps[0]["inputs"]["file"]))
                                                     if steps and steps[0].get("inputs", {}).get("file") else own / max(r["share"], 0.01)), 3)
        # A SUNG AD (owner, 20 Nov): each scene fills its own slot on the song (song-cut.json), so the cut runs the
        # whole song; its shots share that slot as they share a read
        slot = ((_song_cut(n).get("scenes") or {}).get(sid) or {}).get("seconds")
        if slot:
            need = round(float(slot) * (r["share"] / max(sum(x["share"] for x in rows), 1e-6)), 3)
        if carry_need[0]:
            need, carry_need[0] = round(need + carry_need[0], 3), 0.0
        src = sources.get(key) or {}
        cfg = dict(brief.get("shot_fill") or {}, footage=True)   # our own footage: captions are marked, not refused
        brand_ = cfg.get("brand") or ""
        # a footage ad told by its words is judged on what its pick shows for the line (the picker's note, by the
        # lyric), not on the shot list's directions for a generated picture
        shows = ((p.get("note") if cfg.get("shows_required") else None) or r.get("shows") or p.get("note") or "")
        sung = _sung_line(n, brief, r, rows)
        if sung:                              # a real-footage song ad is graded on the line sung over the shot
            shows = sung + ((" (%s)" % p.get("role")) if p.get("role") else "")
        pk = product_need(cfg, shows)          # a shot about the product needs that product in use (moments first)
        path0 = src.get("drive_location") or src.get("file")
        at = busiest_in(brand_, path0, p["in"], need, product=pk, avoid=sections.get(_sk(path0), ()))
        fits = lambda path_, s_, need_: busiest_in(brand_, path_, s_, need_, product=pk,  # noqa: E731
                                                   avoid=sections.get(_sk(path_), ()))
        if at is None:                            # this clip cannot run unbroken for the shot: the next-best clip that can
            got = TIMING.swap_for_fit(cast_alternates(n, r["id"], p, picks), need, fits, used_paths)
            if got:
                alt, at2 = got
                key = "L-" + __import__("hashlib").md5(alt["path"].encode()).hexdigest()[:8]
                sources[key] = source_entry(alt["path"])
                at, what = at2, what + " · swapped: the first pick has cuts inside this shot; " + (alt.get("shows") or "")[:60]
        p["in"] = at if at is not None else p["in"]
        # FRAME BY FRAME (owner, 16 Nov): the frames this shot will play are looked at; a miss takes the next-best clip
        # whose frames pass; the first pick stays when none does, with the reason on the shot
        src_now = (sources.get(key) or {}).get("drive_location") or (sources.get(key) or {}).get("file")
        ok, said = frame_look(n, src_now, p["in"], need, shows, cfg)
        if not ok:
            got = LOOKS.swap_for_look(cast_alternates(n, r["id"], p, picks), need, shows, fits,
                                      lambda path_, s_, need_, shows_: frame_look(n, path_, s_, need_, shows_, cfg), used_paths)
            if got:
                alt, at2, _ = got
                key = "L-" + __import__("hashlib").md5(alt["path"].encode()).hexdigest()[:8]
                sources[key] = source_entry(alt["path"])
                p["in"], ok, said = at2, True, "clean after a swap (first pick: %s)" % said
        if not ok and not p.get("keep") and (any(k in said for k in HARD) or (cfg.get("shows_required") and "shows_it" in said)):
            # A SMALL MISS GETS THE SMALL FIX (owner, 20 Nov 2026): on a shot list built from our script, a beat whose
            # clip fails and has no passing swap joins the shot beside it (its time goes to that shot) and the cut
            # goes on; it is listed in _JOINED. Swipe-copied shot lists keep refusing as before.
            if r.get("status") == "ours" and len(rows) > 1:
                if first_out[0] is None:          # kept aside: a scene whose every beat fails still shows its first clip
                    first_out[0] = (r, p, key, prm)
                prev = next((x for x in reversed(steps) if x["tool"] == "ffmpeg.trim"), None)
                if prev:
                    prev["params"]["weight"] = round(float(prev["params"].get("weight") or 0) + prm["weight"], 4)
                else:
                    carry_w[0] += prm["weight"]
                _JOINED.append("%s %s joined its neighbour: %s" % (sid, r["id"], said[:120]))
                continue
            if r.get("status") == "ours":          # a scene of one beat: its clip stays, the reason on the shot
                _JOINED.append("%s %s kept (one beat, no neighbour): %s" % (sid, r["id"], said[:120]))
                said = "kept, " + said
            else:
                _REFUSED.append("%s %s: %s" % (sid, r["id"], said[:160]))
        what = what + " · frames: " + said
        # THE SHOT ENDS INSIDE ITS CLIP (2026-11-20, a sung ad's 5 s generated clips ran 0.1-0.3 s past their end and
        # froze): the start moves back so the whole shot plays from real frames, with a frame to spare
        try:
            clip_len = VS.probe_dur(str(src_now)) if src_now and os.path.isfile(str(src_now)) else None
        except Exception:  # noqa: BLE001 - an unreadable clip keeps its start
            clip_len = None
        # what it really plays: its share of the scene's whole read (the read runs past a sung slot), with any joined time
        vf = steps[0].get("inputs", {}).get("file") if steps and steps[0].get("tool") == "voice.read" else None
        read_s = (VS.probe_dur(str(ST.BRIEFS / n / vf)) + float((steps[0].get("params") or {}).get("tail", 0.2))) \
            if vf and (ST.BRIEFS / n / vf).is_file() else None
        plays = (read_s * float(prm.get("weight") or r["share"]) / max(sum(x["share"] for x in rows), 1e-6)) if read_s \
            else need * float(prm.get("weight") or r["share"]) / max(float(r["share"]), 1e-6)
        if clip_len and float(p["in"]) + plays > clip_len - 0.08:
            p["in"] = round(max(0.0, clip_len - plays - 0.08), 3)
            what += " · start moved back to end inside the clip"
        used_paths.add((sources.get(key) or {}).get("drive_location") or key)
        used_paths.add(_sk((sources.get(key) or {}).get("drive_location") or key))   # the same clip by either path
        sections.setdefault(_sk(src_now), []).append((float(p["in"]), float(p["in"]) + need))
        prm["sound"] = "mute"
        if key.startswith("G-"):
            prm["look"] = "phone"
        steps.append({"id": "cut-%d" % i, "tool": "ffmpeg.trim", "model": None, "prompt": None, "seed": None,
                      "inputs": {"source": "slot:" + key, "in": p["in"], "out": round(p["in"] + (need if unread else 8), 3)},
                      "params": prm, "note": what})
    if first_out[0] and not any(x["tool"] == "ffmpeg.trim" for x in steps):
        r0, p0, k0, prm0 = first_out[0]
        prm0 = dict(prm0, weight=1.0)
        steps.append({"id": "cut-1", "tool": "ffmpeg.trim", "model": None, "prompt": None, "seed": None,
                      "inputs": {"source": "slot:" + k0, "in": p0["in"], "out": round(float(p0["in"]) + 8, 3)},
                      "params": prm0, "note": "%s · kept: every beat of the scene failed its look; its first clip stays" % r0["id"]})
        _JOINED.append("%s %s kept (every beat failed; first clip stays)" % (sid, r0["id"]))
    cards = [dict(s) for s in keep if s["tool"] != "voice.read"]
    if "off" in ((picks.get("cards") or {}).get(sid) or {}):
        cards = []                       # the swipe carries no designed card on this scene: its captions carry the words
    on = ((picks.get("cards") or {}).get(sid) or {}).get("on")
    if on and cards:                     # the card rides on one shot (the shot the swipe shows its graphic over)
        v = steps[0]
        import video_studio as VS
        total = VS.probe_dur(str(ST.BRIEFS / n / v["inputs"]["file"])) + float(v["params"].get("tail", 0.2))
        start = sum(r["share"] for r in rows[:next(i for i, r in enumerate(rows) if r["id"] == on)])
        share = next(r["share"] for r in rows if r["id"] == on)
        for c in cards:
            prm = {k: v for k, v in c["params"].items() if k not in ("from_word", "to_word")}
            c["params"] = dict(prm, **{"in": round(start * total, 3), "out": round((start + share) * total, 3)})
    steps += cards
    # a scene carries only the clips it plays (20 Nov: stale entries from earlier picks made the Studio fetch files it
    # could not open and failed the whole scene)
    refs = json.dumps([st.get("inputs") for st in steps])
    sources = {k: v for k, v in sources.items() if ("slot:" + k) in refs or ('"%s"' % k) in refs}
    return dict(base, steps=steps, sources=sources,
                cut="Swipe cut (swipe_cut.py): every shot at its swipe shot's share of the scene; picks from picks.json")


_CUTS = {}
MAX_SHOT = TIMING.MAX_SHOT     # the chain's: a shot no line is read over plays its action and no more (2.5 s)
END_CARD = TIMING.END_CARD     # the chain's: the end card, held long enough to read the card on it (3 s)


def _file(path):
    """The clip's file on this machine (the Studio's own resolver), or None when it is not here."""
    try:
        import video_studio as VS
        return VS.resolve({"drive_location": str(path)})
    except Exception:  # noqa: BLE001
        return None


def motion(path, start, length, fps=10):
    """How much moves in each frame of the clip (the chain's shot_timing.motion). [] when the clip cannot be read here."""
    return TIMING.motion(_file(path), start, length, fps)


_SUNG = {}


def _sung_line(n, brief, r, rows):
    """The line sung over a shot of a real-footage song ad (the song's own timing at the shot's middle), or None for
    any other ad. A real clip cannot show an animated brief's shot text; it can show what the line says (owner,
    20 Nov 2026: real footage is graded on our words)."""
    if (brief.get("lane") or "") not in ("real", "mix"):
        return None
    if n not in _SUNG:
        lines = []
        try:
            import video_studio as VS
            _sb, run = VS.song_of(n)
            if run and (Path(run) / "song" / "timing.json").is_file():
                lines = [x for x in json.load(open(Path(run) / "song" / "timing.json")).get("lines") or []
                         if x.get("start") is not None]
        except Exception:  # noqa: BLE001 - no song here: graded on the shot text as before
            lines = []
        _SUNG[n] = lines
    lines = _SUNG[n]
    if not lines:
        return None
    at = r.get("at")
    if at is None:                            # an added shot: the time of the row it follows
        prev = next((x for x in rows if x.get("id") == r.get("after")), None)
        at = (prev or {}).get("at")
    if at is None:
        return None
    mid = float(at) + float(r.get("seconds") or 1.0) / 2
    hit = min(lines, key=lambda x: 0 if x["start"] <= mid <= x["end"] else min(abs(mid - x["start"]), abs(mid - x["end"])))
    return hit.get("line")


def cast_alternates(n, shot_id, pick, picks):
    """The next-best clips a shot may swap to. A cast shot (its pick names a role in picks.people.cast) swaps only to
    that creator's own footage: a swap to "the next-best clip" from anyone turned a one-lead story into a montage of
    strangers (owner, 20 Nov 2026). No clip of theirs fits: the pick stays as placed."""
    alts = alternates_of(n, shot_id)
    cast = (picks.get("people") or {}).get("cast") or {}
    role = (pick or {}).get("role")
    if role in cast:
        alts = [a for a in alts if str(cast[role]).lower() in str(a.get("path") or "").lower()]
    return alts


def alternates_of(n, shot_id):
    """The footage step's next-best clips for a shot (shot-fill.json `alternatives`, the chain's order)."""
    try:
        d = json.load(open(ST.BRIEFS / n / "shot-fill.json"))
    except (OSError, ValueError):
        return []
    rows = [r for r in d.get("shots") or [] if r.get("id") == shot_id]
    return [a for r in rows for a in r.get("alternatives") or [] if a.get("path")]


def _cuts_of(brand, path):
    """The shot changes inside one of our clips (asset-index library cuts.json, keyed by the clip's Drive id; the
    library's rows map a Shared Assets path to that id). [] when the clip or the list is unknown."""
    if brand not in _CUTS:
        lib = ST.part("asset-index") / "library"
        cuts, ids = {}, {}
        try:
            sys.path.insert(0, str(lib))
            import library as LB
            for r in LB.rows_of(brand):
                ids.setdefault(str(r.get("label") or ""), r.get("clip"))
            cuts = json.loads((Path(LB.libdir(brand)) / "cuts.json").read_text())
        except Exception:  # noqa: BLE001 - no cut list: every pick plays as it was placed
            pass
        _CUTS[brand] = (cuts, ids)
    cuts, ids = _CUTS[brand]
    s = str(path or "")
    label = "Shared Assets/" + s.split("Shared Assets/", 1)[1] if "Shared Assets/" in s else s
    return sorted(float(c) for c in cuts.get(ids.get(label) or "", []) or [])


def measured_cuts(path, start, length):
    """The shot changes actually in the clip between start and start+length (the chain's shot_timing.measured_cuts, on
    the clip pulled from Shared Assets). The index's cut list can miss cuts in a fast edit."""
    return TIMING.measured_cuts(_file(path), start, length)


LOOK_V = LOOKS.LOOK_V      # the chain's frame look: its words and version
LOOK = LOOKS.LOOK


def frame_look(n, path, start, need, shows, cfg):
    """Frame by frame, by default (owner, 16 Nov): the chain's frame look (frame_look.look) on the stretch a shot will
    play, cached in briefs/<production>/frame-look/cache.json. -> (clean, why).
    MOMENTS FIRST (17 Nov): a stretch the asset index's moments pass already judged answers from there (the chain's
    frame_look.looked), with no read of the clip and no ask; only a stretch with no moment is looked at live."""
    if moments_on(cfg):
        got = LOOKS.looked((cfg or {}).get("brand") or "", path, float(start), need, shows, cfg)
        if got is not None:
            return got
    # the frames come from a preview copy of just this stretch (excerpt), never the whole clip
    f, off = excerpt(path, float(start), need, (cfg or {}).get("brand") or "")
    return LOOKS.look("%s@%.2f" % (path, float(start)), float(start) - off, need, shows, cfg,
                      cache_file=ST.BRIEFS / n / "frame-look" / "cache.json", resolve=lambda p_: f)


_XC = Path.home() / ".upright" / "cache" / "excerpts"


def excerpt(path, lo, span, brand=""):
    """(local file, offset): only the seconds lo..lo+span of one of our Shared Assets clips, read by range straight
    from the Drive by the key (gdrive-creator engine.media_request), never the whole file (owner, 17 Nov: "the
    downloading is happening on my computer too"). A small preview copy, kept, for measuring and looking only."""
    import hashlib, subprocess
    lo = max(0.0, float(lo))
    s = str(path or "")
    out = _XC / (hashlib.md5(("%s|%.2f|%.2f" % (s, lo, span)).encode()).hexdigest()[:16] + ".mp4")
    if out.is_file() and out.stat().st_size > 0:
        return str(out), lo
    local = s if (os.path.isabs(s) and os.path.isfile(s)) else None
    if not local and "Shared Assets/" in s:         # synced in a Google Drive folder on this Mac: read it here
        import glob as _g
        tail = "Shared Assets/" + s.split("Shared Assets/", 1)[1]
        local = next((os.path.join(r, tail) for r in _g.glob(os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/Shared drives"))
                      if os.path.isfile(os.path.join(r, tail))), None)
    if local:
        _XC.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "%.3f" % lo, "-t", "%.3f" % span, "-i", local, "-an",
                        "-vf", "scale=480:-2", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", str(out)], check=True, timeout=300)
        return str(out), lo
    try:
        import video_studio as VS
        if "Shared Assets/" not in s and brand:        # another footage root the brand lists: read by range there
            rg = VS._other_root(s, brand)
            if rg:
                _XC.mkdir(parents=True, exist_ok=True)
                subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *(["-headers", rg[1]] if rg[1] else []),
                                "-ss", "%.3f" % lo, "-t", "%.3f" % span, "-i", rg[0], "-an", "-vf", "scale=480:-2",
                                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", str(out)], check=True, timeout=180)
                return str(out), lo
        R = VS._drive_reach()
        label = "Shared Assets/" + s.split("Shared Assets/", 1)[1] if "Shared Assets/" in s else None
        full = R.cache_root().joinpath(*label.split("/")[1:]) if (R and label) else None
        if full is not None and full.is_file() and full.stat().st_size > 0:
            return str(full), 0.0                      # already here whole from an earlier run: use it
        from gdrive_creator import engine as E
        _cuts_of(brand, path) if brand else None             # loads the index's path -> Drive id map for the brand
        fid = (_CUTS.get(brand) or ({}, {}))[1].get(label) or R.drive_id(label)
        url, head = E.media_request(fid)
        _XC.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-headers", head, "-ss", "%.3f" % lo, "-t", "%.3f" % span,
                        "-i", url, "-an", "-vf", "scale=480:-2", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                        str(out)], check=True, timeout=180)
        return str(out), lo
    except Exception:  # noqa: BLE001 - no ranged read here: the whole clip, as before
        return _file(path), 0.0


def _sk(path):
    """One name for a clip whichever way it is written (a Drive-mount path or 'Shared Assets/...')."""
    s = str(path or "")
    return "Shared Assets/" + s.split("Shared Assets/", 1)[1] if "Shared Assets/" in s else s


_MOMENTS_OFF = []


def moments_on(cfg=None):
    """Moments first, unless a production's brief says shot_fill.moments: false (or VIDEO_STUDIO_MOMENTS=0)."""
    if os.environ.get("VIDEO_STUDIO_MOMENTS", "1") == "0" or _MOMENTS_OFF:
        return False
    return (cfg or {}).get("moments", True) is not False


def product_need(cfg, shows):
    """The brand's product key a shot about the product must show in use (moments first), else None."""
    if not moments_on(cfg) or not LOOKS.about_product(shows, cfg):
        return None
    MO = TIMING._moments()
    try:
        return MO.product_key((cfg or {}).get("product"), (cfg or {}).get("brand")) if MO else None
    except Exception:  # noqa: BLE001
        return None


_FAST_F = Path.home() / ".upright" / "cache" / "shot-starts.json"
try:
    _FAST = json.loads(_FAST_F.read_text())
except (OSError, ValueError):
    _FAST = {}


def _save_fast():
    try:
        _FAST_F.parent.mkdir(parents=True, exist_ok=True)
        _FAST_F.write_text(json.dumps(_FAST))
    except OSError:
        pass


def busiest_in(brand, path, start, need, before=1.0, after=5.0, fps=10, product=None, avoid=()):
    """The chain's start rule (shot_timing.busiest_in) on one of our clips: the index's cut list for it, plus the cuts
    measured in it and its motion jumps. None when no unbroken stretch is there: the caller swaps the clip.
    MOMENTS FIRST (17 Nov): a clip the asset index's moments pass has read starts on its clean moment (the chain's
    shot_timing.placed), with no read of the clip; only a clip with no moments yet is measured live."""
    if moments_on():
        known, at = TIMING.placed(brand, path, start, need, product, reach=max(before, after), avoid=avoid)
        if known:
            return at
    return _clear_of(_busiest_live(brand, path, start, need, before, after, fps), need, avoid, start, before, after)


def _clear_of(at, need, avoid, start, before, after):
    """A live start that would replay a section another shot already plays moves just past that section (still inside
    the shot's reach); when no clear start is in reach, None: the caller swaps the clip (no clip moment twice)."""
    if at is None or not avoid:
        return at
    lo, hi = max(0.0, float(start or 0) - before), float(start or 0) + after
    for _ in range(len(avoid) + 1):
        hit = [b for a, b in avoid if min(at + need, b) - max(at, a) > 0.04]
        if not hit:
            return round(at, 3)
        at = max(hit) + 0.05
        if at > hi:
            break
    for a, b in sorted(avoid, reverse=True):      # or end just before the earliest clash, if that start is in reach
        cand = a - need - 0.05
        if lo <= cand and not [1 for x, y in avoid if min(cand + need, y) - max(cand, x) > 0.04]:
            return round(cand, 3)
    return None


def _busiest_live(brand, path, start, need, before, after, fps):
    # FAST (owner, 17 Nov: "editing should not take this long for basic stuff"): one motion read per window finds the
    # busy stretch AND the cuts (sudden jumps); no second re-encode pass. Each answer is kept, so a re-cut is instant.
    k = "%s|%.2f|%.2f|%.1f|%.1f" % (path, float(start or 0), need, before, after)
    if k in _FAST:
        return _FAST[k]
    lo = max(0.0, float(start or 0) - before)
    f, off = excerpt(path, lo, before + after + need, brand)
    known = [c - off for c in _cuts_of(brand, path)]
    at = TIMING.busiest_in(f, float(start or 0) - off, need, before, after, fps, known_cuts=known, reach_cuts=None,
                           read_cuts=lambda *a_: [])
    at = round(at + off, 3) if at is not None else None
    _FAST[k] = at
    _save_fast()
    return at


def one_shot_in(brand, path, start, need, reach=6.0):
    """The chain's unbroken-stretch rule (shot_timing.one_shot_in) on one of our clips: the start as placed when it
    already fits, else the nearest unbroken stretch long enough within `reach` seconds, else None (swap the clip)."""
    start = float(start or 0)
    cuts = sorted(set(_cuts_of(brand, path)) | set(round(c, 2) for c in measured_cuts(path, max(0.0, start - reach),
                                                                                       need + 2 * reach)))
    return TIMING.one_shot_in(start, need, cuts, reach)


def main(a):
    n = a[0]
    if not (ST.BRIEFS / n / "picks.json").is_file():
        # no footage picks (an AI-lane production: every scene holds the production chain's own cut, ai_shots.py):
        # nothing here to re-time to the swipe — the Studio's cut runs each scene as it is laid
        print("cut to the swipe: no footage picks — nothing to re-time; every scene is cut as it is laid")
        return
    brief, picks, scenes = plan(n)
    if (brief.get("shot_fill") or {}).get("moments") is False:
        _MOMENTS_OFF.append(1)
    people_check(picks, scenes)
    cast_check(picks, scenes, brief, (ST.BRIEFS / n / "song-cut.json").exists())
    all_sources = {}
    for sd in (ST.BRIEFS / n / "scenes").iterdir():
        for f in sd.glob("take-*.json"):
            all_sources.update(json.load(open(f)).get("sources") or {})
    only = [x for x in a[1:] if not x.startswith("--")]
    made = []
    for sid, rows in scenes.items():
        if only and sid not in only:
            continue
        made.append((sid, rows, take_for(n, sid, rows, picks, brief, all_sources)))
    if _JOINED:
        print("joined (no clip of ours shows the beat):\n  " + "\n  ".join(_JOINED))
    _REFUSED.extend(one_clip_once(made, picks))
    if _REFUSED and "--keep-failing" not in a:
        raise SystemExit("frames: %d shot(s) fail the frame look and no clip of the pool passes; re-pick them in "
                         "picks.json (nothing was saved):\n  " % len(_REFUSED) + "\n  ".join(_REFUSED))
    for sid, rows, wf in made:
        if "--dry-run" in a:
            print(sid, [(s["id"], s["params"].get("weight"), s["inputs"].get("source"), s["inputs"].get("in")) for s in wf["steps"] if s["tool"] != "voice.read"])
            continue
        take = api(f"/api/scene/{n}/{sid}/take", {})["take"]
        api(f"/api/scene/{n}/{sid}/pick", {"take": take})
        r = api(f"/api/scene/{n}/{sid}/save", wf)
        print(sid, r.get("pick"), r.get("status"), len(rows), "shots")
        if "--run" in a:
            r = api(f"/api/scene/{n}/{sid}/run", {})
            print(sid, "run:", ("ok %.3f s" % r["run"]["duration"]) if r.get("ok") else r)


if __name__ == "__main__":
    main(sys.argv[1:])
