#!/usr/bin/env python3
"""The video-editor hand-off: one production's brief and the clips it still needs, packed for the video maker's Claude.

    python3 components/video-edit/maker/maker_pack.py <production, e.g. idea-21> [--productions <dir>] [--no-drive]

The chain's own builder of the hand-off from video-production into video-edit (moved out of the Video Studio
2026-11-17: the chains run on their own; the Studio only calls this and shows it). A production is a folder
<productions>/<production>/ holding brief.json (order, picks, style, lane) and scenes/<scene>/<pick>.json (each
scene's steps and the files it made). <productions> is --productions, else VIDEO_PRODUCTIONS, else VIDEO_STUDIO_DATA/
briefs, else runs/video-studio/briefs in this workspace.

Rule (owner, 16 Nov 2026): at this point it is a brief; it just needs the clips the maker produces, and the maker's
Claude takes over from the folder. The Studio makes every scene it can (our footage cut, the narration read); a
scene that waits on an AI shot (gen.shot / gen.take) goes to the maker. No brief number is needed: the folder is named
by the production until the finished ad is filed and numbered.

Writes runs/handoffs/video-editor/<brand>/<brand>_<product>_<production>/ in the workspace, the same path below
Shared Assets/ on the Drive (copied, never deleted):
  TIMELINE.html   the ad on its clock: picture, words, on-screen and voice tracks; tap a block for its clip
  BRIEF.md        what the ad is, every scene in order, what is made, what each clip needs (the exact recipe)
  clips.json      the same clip list for an agent
  made/           the scenes already made, in order
  voice/          the narration reads each scene plays
  refs/<clip>/    the swipe frames each clip copies (first / mid / last)
  returned/       the finished clips come back here, named <clip id>.mp4, then the cut <key>-control.mp4
Spends nothing.
"""
import json
import re
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ST = None  # set by _settings() below, from this folder by file (never a same-named module elsewhere)

AI_TOOLS = {"gen.shot", "gen.take"}


def _here(name):
    """A module of this folder, loaded by its file under its own name, so a caller's module of the same name (the
    Studio has its own maker_* files) is never picked up instead."""
    import importlib.util
    key_ = "video_edit_maker_" + name
    if key_ not in sys.modules:
        spec = importlib.util.spec_from_file_location(key_, str(HERE / (name + ".py")))
        m = importlib.util.module_from_spec(spec)
        sys.modules[key_] = m
        spec.loader.exec_module(m)
    return sys.modules[key_]


ST = _here("maker_settings")


def _load(p):
    return json.loads(Path(p).read_text())


def _ws():
    return Path(ST.WRITING).resolve().parents[2]


def _link_share(dest, svc, E):
    """The hand-off folder open to anyone with the link, its returned/ taking uploads (owner, 2026-11-27: every hand-off
    Drive folder shared by link so editors scale): the one sharing rule, image-edit's handoff.link_share. Best effort: a
    share that fails is recorded, never stops the hand-off."""
    try:
        ie = str(_ws() / "components" / "image-edit")
        if ie not in sys.path:
            sys.path.append(ie)
        from image_edit import handoff as IH  # noqa: E402
        return IH.link_share(dest, svc, E)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200]}


def _drive_root():
    try:
        import importlib.util as iu
        sp = iu.spec_from_file_location("mp_drive_index", str(ST.part("brandpath") / "drive_index.py"))
        di = iu.module_from_spec(sp)
        sp.loader.exec_module(di)
        return di.mount()
    except Exception:  # noqa: BLE001 — no Drive here: the folder stays in the workspace and says so
        return None


UNNUMBERED = re.compile(r"_idea-\d+$", re.I)      # named by the production id: no brief number yet (2026-11-25)


def _key(brief, brand, n, rj=None):
    prod = (rj or {}).get("product") or (brief.get("shot_fill") or {}).get("product") or ""   # the run's name first, as the Studio
    try:
        sys.path.insert(0, str(_ws() / "components" / "naming"))
        import names as NM
        prod = NM.product_id(brand, prod) or prod
    except Exception:  # noqa: BLE001
        pass
    prod = "".join(c if c.isalnum() else "-" for c in str(prod).lower()).strip("-") or "ad"
    # a brief, named by its brief number (owner, 16 Nov 2026: "it should be a brief"); the production id only when
    # the register has not numbered it yet
    num = (rj or {}).get("brief") or (re.search(r"brief-\d+", str(brief.get("brief_key") or "")) or [None])[0]
    return "%s_%s_%s" % (brand, prod, num or n)     # the brief number the register or the production carries


def _dur(p):
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def _span(src):
    """'0:29.4 - 0:31.0 · S · …' -> 1.6 seconds, or None."""
    import re
    m = re.match(r"\s*(\d+):(\d+(?:\.\d+)?)\s*-\s*(\d+):(\d+(?:\.\d+)?)", src or "")
    if not m:
        return None
    a, b = int(m[1]) * 60 + float(m[2]), int(m[3]) * 60 + float(m[4])
    return b - a if b > a else None


def _route(src):
    """The swipe's roll letter for the scene: S a screen, X a split, C a card, else a shot."""
    import re
    m = re.search(r"·\s*([A-Z])\s*·", src or "")
    return {"S": "screen", "X": "split", "C": "card"}.get(m[1] if m else "", "shot")


def _clip_tool(step, workflow, scene):
    """A screen/card with no generated plate is assembled in the edit, as the run sheet declares."""
    kind = str(scene.get("kind") or "").lower()
    if not kind:
        kind = {"S": "screen", "C": "card"}.get(workflow.get("roll"), _route(scene.get("source")))
    if kind not in ("screen", "card", "endcard"):
        return step["tool"]
    plate = ((scene.get(kind) or {}).get("plate") or scene.get("first_frame")
             or (step.get("inputs") or {}).get("picture") or (step.get("params") or {}).get("picture"))
    if plate or workflow.get("pictures") or str(step.get("prompt") or "").strip():
        return step["tool"]
    return "edit"


LANES = {"ai": "AI (every shot made)", "mix": "AI + Real (our footage where it truly shows the shot, AI for the rest)",
         "real": "Real (our own footage on every shot)"}


def _chain(component, name):
    """A chain module by its file (`components/<component>/machine/<name>.py` in this workspace), under its own name."""
    import importlib.util
    key_ = "maker_chain_%s_%s" % (component.replace("-", "_"), name)
    if key_ not in sys.modules:
        f = _ws() / "components" / component / "machine" / (name + ".py")
        if not f.is_file():                       # a production kept elsewhere: the workspace this builder sits in
            f = HERE.parents[2] / "components" / component / "machine" / (name + ".py")
        spec = importlib.util.spec_from_file_location(key_, str(f))
        m = importlib.util.module_from_spec(spec)
        sys.modules[key_] = m
        try:
            spec.loader.exec_module(m)
        except BaseException:
            sys.modules.pop(key_, None)
            raise
    return sys.modules[key_]


def made_as(brief):
    """How this production is made, from the chain's one rule (video-production machine/lane.py): {"lane", "why", "by",
    "label"}. The lane recorded on the production, else the one answer for an older production; never a lane assumed
    here (the logic layer, 2026-11-18: this builder read "ai" where the Studio's own tools read "real")."""
    try:
        LN = _chain("video-production", "lane")
        got = LN.of(brief)
        return dict(got, label=LN.label(got["lane"]))
    except Exception:  # noqa: BLE001 — the rule could not be read: what the production itself says, said as such
        lane = (brief or {}).get("lane") or "real"
        return {"lane": lane, "why": (brief or {}).get("lane_why") or "as recorded on the production",
                "by": (brief or {}).get("lane_by") or "the production", "label": LANES.get(lane, lane)}


def passed_clips(footage):
    """Every clip the footage decision passed for this ad (storyboard-footage.json rows whose plan is cut):
    {(file label, clip id)}. A row that carries text marks other than clean never counts (no captioned clips)."""
    out = set()
    for v in (footage or {}).values():
        c = (v or {}).get("clip") if isinstance(v, dict) else None
        if not isinstance(c, dict) or (v or {}).get("plan") != "cut":
            continue
        marks = c.get("text_marks") if "text_marks" in c else c.get("marks")
        if marks is not None and list(marks) != ["clean"]:
            continue
        out.add((c.get("shared_path"), c.get("clip_id")))
    return out


def ours_passed(wf, passed):
    """The scene's own-footage steps, when every one of them is cut from a clip the footage decision passed:
    [{"step", "file", "clip_id", "in", "out", "creator"}], else None. A scene cut from our closest clips in an earlier
    Real pass (clips the decision did not pass) is None: it still goes to the maker."""
    trims = [st for st in wf.get("steps") or [] if st.get("tool") == "ffmpeg.trim"]
    if not trims or not passed:
        return None
    files = {x for x, _ in passed if x}
    ids = {y for _, y in passed if y}
    rows = []
    for st in trims:
        src = (wf.get("sources") or {}).get(st.get("id")) or {}
        if src.get("generated"):
            return None                         # a made take laid as a trim is not our footage
        if not ((src.get("drive_location") and src["drive_location"] in files) or
                (src.get("clip_id") and src["clip_id"] in ids)):
            return None
        rows.append({"step": st.get("id"), "file": src.get("drive_location"), "clip_id": src.get("clip_id"),
                     "in": (st.get("inputs") or {}).get("in"), "out": (st.get("inputs") or {}).get("out"),
                     "creator": src.get("creator")})
    return rows


def lay_ours(rows, dst):
    """A passed scene the Studio has not cut yet, cut here from its source so it still reaches the editor as a file:
    one own-footage step, read through gdrive-creator and trimmed picture only (video-production owned_clips, the
    chain's own door). -> None when laid, else why not (said on the scene's row; the build never stops on it)."""
    if len(rows) != 1:
        return "the scene is %d clips of ours joined on its voice: cut it in the Studio first" % len(rows)
    r = rows[0]
    try:
        OC = _chain("video-production", "owned_clips")
        OC.cut(OC.readable(str(r["file"])), float(r["in"] or 0), float(r["out"] or 0), Path(dst))
        return None if Path(dst).is_file() and Path(dst).stat().st_size else "the cut wrote no file"
    except Exception as e:  # noqa: BLE001
        return "our clip could not be read or cut (%s: %s)" % (type(e).__name__, str(e)[:160])


def _brief_doc(W):
    """The writing run's production brief as data (its scene block), {} when it cannot be read."""
    try:
        text = (W / "stages" / "5-brief.md").read_text()
    except OSError:
        return {}
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and "scenes" in d:
            return d
    return {}


def _idea_of(W, piece):
    """The one idea the ad turns on: the brief's own `piece.idea` when writing carries it, else the controlling idea as
    the idea pass wrote it (its first paragraph). "" when neither is there."""
    if isinstance(piece.get("idea"), str) and piece["idea"].strip():
        return piece["idea"].strip()
    try:
        text = (W / "stages" / "4i-controlling-idea.md").read_text()
    except OSError:
        return ""
    m = re.search(r"#+\s*THE CONTROLLING IDEA\s*\n+(.+?)(?:\n\s*\n|\n#|$)", text, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def _trail(key, W, rj, brief, brand, run):
    """Every row of the decision trail this ad has, oldest first, each once: the brief's joined trail (run-kit
    `trail.for_brief`), the writing run's own rows, the production's (the Studio's brief.json and the production run)."""
    rows = []
    try:
        rk = str(_ws() / "components" / "run-kit")
        if rk not in sys.path:
            sys.path.append(rk)
        from run_kit import trail as T
        rows += [r for r in (T.for_brief(key) or []) if isinstance(r, dict)]
    except Exception:  # noqa: BLE001 — no trail module or no join yet: the rows found on the runs themselves
        T = None
    piece_trail = ((_brief_doc(W).get("piece") or {}).get("trail")) if W else None
    own = [rj.get("trail"), piece_trail if isinstance(piece_trail, list) else None, (brief or {}).get("trail")]
    try:
        own.append(_load(_ws() / "runs" / "video-production" / brand / str(run) / "run.json").get("trail"))
    except (OSError, ValueError):
        pass
    for src in own:
        rows += [r for r in src or [] if isinstance(r, dict)]
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: str(r.get("at") or "")):
        k = (r.get("stage"), r.get("decision"), json.dumps(r.get("choice"), sort_keys=True, default=str), r.get("why"))
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out, T


def thinking(key, W, rj, brief, brand, run):
    """What the editor needs to know about WHY the ad is built this way, carried with the clips (the logic layer,
    2026-11-18: the idea, the angle, the openings and the reasons were written upstream and read by nothing here):
    angle, concept and idea from the brief; the openings; the caption look and the pace the format picks, with who
    picked them; how the ad is made; and the decision trail."""
    doc = _brief_doc(W)
    piece = doc.get("piece") or {}
    fmt = piece.get("format") or rj.get("format_id") or rj.get("format")
    out = {"angle": piece.get("angle") or rj.get("angle") or None,
           "concept": piece.get("concept") or rj.get("concept") or None,
           "idea": _idea_of(W, piece) or None,
           "avatar": piece.get("avatar") or (rj.get("audience") or {}).get("_avatar"),
           "awareness": piece.get("awareness") or (rj.get("market_state") or {}).get("awareness"),
           "format": fmt,
           "hooks": [{"id": h.get("id"), "text": h.get("text"), "take": h.get("take"), "opens": h.get("opener_scene")}
                     for h in doc.get("hooks") or [] if isinstance(h, dict) and h.get("text")],
           "made_as": made_as(brief)}
    try:
        LK = _chain("video-edit", "looks")
        app = piece.get("app") or rj.get("app")
        asked = ((doc.get("layers") or {}).get("captions") or {}).get("look")
        out["caption_look"] = LK.caption_call(fmt, app, asked)
        out["pace"] = LK.pace_call(fmt)
    except Exception as e:  # noqa: BLE001 — said, never a gap that looks like a choice
        out["caption_look"] = out["pace"] = None
        out["settings_note"] = "the caption look and the pace could not be read: %s" % str(e)[:160]
    rows, T = _trail(key, W, rj, brief, brand, run)
    out["trail"] = rows
    try:
        out["trail_text"] = T.block(rows) if T else None
    except Exception:  # noqa: BLE001
        out["trail_text"] = None
    return out


def thinking_md(th):
    """The same, as a section an editor reads: short lines, every reason beside its choice."""
    cell = lambda x: str(x).replace("\n", " ").strip()  # noqa: E731
    L = ["## Why this ad is built this way", ""]
    for label, k in (("Idea", "idea"), ("Angle", "angle"), ("Concept", "concept"), ("Who it is for", "avatar"),
                     ("What they already know", "awareness"), ("Format", "format")):
        if th.get(k):
            L.append("- **%s:** %s" % (label, cell(th[k])))
    m = th.get("made_as") or {}
    if m.get("lane"):
        L.append("- **How it is made:** %s. Why: %s (%s)" % (m.get("label") or m["lane"], cell(m.get("why") or ""), m.get("by") or ""))
    c = th.get("caption_look") or {}
    if c.get("look"):
        L.append("- **Caption look:** %s. Why: %s" % (c.get("name") or c["look"], cell(c.get("why") or "")))
    pc = th.get("pace") or {}
    if pc.get("name"):
        L.append("- **Pace:** %s%s. Why: %s" % (pc["name"], (" (" + cell(pc["what"]) + ")") if pc.get("what") else "", cell(pc.get("why") or "")))
    if th.get("settings_note"):
        L.append("- " + th["settings_note"])
    if th.get("hooks"):
        L += ["", "### The openings", "", "Each is its own way into the same ad; the first is the control.", ""]
        for h in th["hooks"]:
            L.append("- **%s:** %s%s" % (cell(h.get("id") or "opening"), cell(h.get("text") or ""),
                                         (" · " + cell(h["take"])) if h.get("take") else ""))
    L += ["", "### How we got here", ""]
    if th.get("trail_text") and th["trail_text"].strip() and th["trail_text"].strip() != "NONE":
        L += [th["trail_text"].strip()]
    elif th.get("trail"):
        L += ["- %s · %s: %s. Why: %s (%s)" % (r.get("stage"), r.get("decision"), cell(r.get("choice")), cell(r.get("why") or ""),
                                              r.get("by") or "") for r in th["trail"]]
    else:
        L += ["No decision trail is on file for this brief yet."]
    return "\n".join(L) + "\n"


THINKING_MARK = "<!-- thinking: written by the hand-off builder -->"


def _into_brief(out, th):
    """The thinking into the pack's BRIEF.md (the run sheet's own file, written just before): once, at its end."""
    f = out / "BRIEF.md"
    if not f.is_file():
        return
    text = f.read_text()
    if THINKING_MARK in text:
        text = text[:text.index(THINKING_MARK)].rstrip() + "\n"
    f.write_text(text.rstrip() + "\n\n" + THINKING_MARK + "\n" + thinking_md(th))


def _style_words(style):
    """The ad's own look in words: the style bank's rule and swatch, never a default."""
    sid = style.get("id")
    if not sid or sid in ("photoreal", "phone-ugc"):
        return " (phone-grade UGC look, real skin, no cinematic grade)"
    look = style.get("look") or {}
    return " (every picture and clip in this style%s; never photoreal)" % (
        ": " + look.get("use") if look.get("use") else "")


def _once(text):
    """A recipe with a sentence said twice in a row said once (17 Nov: 'ear pressed to the marble…' twice)."""
    out = []
    key = lambda x: re.sub(r"[^a-z0-9 ]", "", x.lower()).strip()  # noqa: E731
    for part in re.split(r"(?<=[.!?])\s+", text or ""):
        k = key(part)
        if k and not (out and k in key(out[-1])):         # a sentence already said in the one before it
            out.append(part)
    return " ".join(out)


def _song(W, brand, run, out):
    """A sung ad's song, carried into the hand-off: song.mp3, timing.json, LISTEN.md in song/, and each scene's lyric
    lines with its time on the song (matched line by line to the song's own timing). None when the ad is not sung."""
    try:
        text = (W / "stages" / "5-brief.md").read_text()
    except OSError:
        return None
    doc = {}
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and "scenes" in d:
            doc = d
            break
    home = _ws() / "runs" / "video-production" / brand / str(run) / "song"
    if not doc.get("song") or not (home / "song.mp3").exists():
        return None
    (out / "song").mkdir(exist_ok=True)
    for name in ("song.mp3", "timing.json", "LISTEN.md", "song.json", "ear-check.json"):   # the gate's own record too
        if (home / name).exists():
            shutil.copy2(home / name, out / "song" / name)
    try:
        lines = _load(home / "timing.json").get("lines") or []
    except (OSError, ValueError):
        lines = []
    norm = lambda x: re.sub(r"[^a-z0-9 ]", "", str(x).lower()).strip()  # noqa: E731
    used, scenes = set(), {}
    for sc in doc.get("scenes") or []:
        parts = [sc] + [j for j in sc.get("joined_scenes") or [] if isinstance(j, dict)]
        lyr = []
        for p in parts:
            v = p.get("lyrics") or []
            lyr += [v] if isinstance(v, str) else [x if isinstance(x, str) else (x.get("line") or x.get("say") or "") for x in v]
        lyr = [x for x in dict.fromkeys(lyr) if x]
        at = []
        for ly in lyr:
            k = next((n for n, ln in enumerate(lines) if n not in used and norm(ln.get("line")) == norm(ly)), None)
            if k is not None:
                used.add(k)
                if lines[k].get("start") is not None and lines[k].get("end") is not None:   # a line heard, with its time
                    at.append(lines[k])
        scenes[sc.get("id")] = {"lyrics": lyr, "start": min((a["start"] for a in at), default=None),
                                "end": max((a["end"] for a in at), default=None)}
    return {"file": "song/song.mp3", "scenes": scenes, "brief_scenes": doc.get("scenes") or [],
            "make_list": (doc.get("piece") or {}).get("make_list") or [],
            "captions": ((doc.get("edit") or {}).get("captions") or ""), "seconds": _dur(home / "song.mp3")}


COLOUR_WORDS = {"white", "cream", "rust", "stone", "floral", "striped", "black", "blue", "green", "grey", "gray", "pink",
                "brown", "navy", "beige", "ivory", "plaid", "light", "dark"}     # a look's colour words: an envelope can be cream
def _song_ad_rules(ws):
    """The song-ad format's own finishing rules (its playbook json): hooks, versions, loudness, end card."""
    try:
        return json.loads((ws / "components" / "video-production" / "formats" / "playbooks" / "song-ad.json").read_text())["stages"]
    except (OSError, ValueError, KeyError):
        return {}


HOOK_SFX_TAGS = {"hit", "impact", "reveal", "stop", "interrupt", "transition"}


def _hook_sfx(ws, out):
    """The bank sound effects a hook can take (the song-ad playbook: "a lyric line as text + one bank SFX"), carried into
    sfx/ so the maker never hunts for the bank: every made row of components/video-production/banks/sfx/index.json
    tagged for a hit or a transition, copied from the Drive. -> [file names]."""
    try:
        idx = json.loads((ws / "components" / "video-production" / "banks" / "sfx" / "index.json").read_text())
    except (OSError, ValueError):
        return []
    rows = idx.get("rows") if isinstance(idx, dict) and isinstance(idx.get("rows"), list) else \
        next((v for v in (idx.values() if isinstance(idx, dict) else []) if isinstance(v, list)), idx if isinstance(idx, list) else [])
    root = _drive_root()
    got = []
    for r in rows:
        f = str(r.get("file") or "")
        if r.get("status") != "made" or not f.startswith("Shared Assets/") or not HOOK_SFX_TAGS & set(r.get("tags") or []):
            continue
        src = Path(root) / f[len("Shared Assets/"):] if root else None
        if src and src.is_file():
            (out / "sfx").mkdir(exist_ok=True)
            shutil.copy2(src, out / "sfx" / src.name)
            got.append(src.name)
    return got


def _caption_rules(ws, brand, fmt, out):
    """The caption look the edit chain picks for this format (video-edit looks/bank.json `pick`) and the brand's own
    caption font (looks/fonts.json, role caption), its files copied into fonts/. -> (look dict, font dict, [files])."""
    look, font, files = {}, {}, []
    try:
        bank = json.loads((ws / "components" / "video-edit" / "looks" / "bank.json").read_text())
        lid = (bank.get("pick") or {}).get("by_format", {}).get(fmt) or (bank.get("pick") or {}).get("default")
        looks = bank.get("looks") or {}
        look = looks.get(lid) if isinstance(looks, dict) else next((x for x in looks if x.get("id") == lid), {})
        fonts = json.loads((ws / "components" / "video-edit" / "looks" / "fonts.json").read_text())
        fl = fonts.get("fonts") if isinstance(fonts, dict) else fonts
        font = next((x for x in fl or [] if x.get("role") == "caption" and str(x.get("id", "")).startswith(brand + "-")), {})
        root = _drive_root()
        src = str(font.get("source") or "")
        if root and src.startswith("Shared Assets/"):
            d = Path(root) / src[len("Shared Assets/"):]
            if d.is_dir():
                (out / "fonts").mkdir(exist_ok=True)
                for f in sorted(d.iterdir()):
                    if f.suffix.lower() in (".woff", ".woff2", ".otf", ".ttf", ".css"):
                        shutil.copy2(f, out / "fonts" / f.name)
                        files.append("fonts/" + f.name)
    except (OSError, ValueError):
        pass
    return look or {}, font, files


CLEARS_SCENE = re.compile(r"for \w+ in list\(bpy\.data\.objects\)\s*:\s*\n?\s*bpy\.data\.objects\.remove")


def _jutsu(out, ws, brand, places, product_ids, key=None, people=()):
    """The 3D builds this ad's start pictures are printed from, carried so the maker rebuilds them in their own
    Higgsfield account (3D Jutsu cannot share a project between accounts; components/3d-recipes is the standard):
    every recipe whose source project made one of this ad's set prints (sets/<print>/set.json), and the product's own
    builds. Writes 3d/<recipe>/ and 3d/JUTSU.md. -> {place: room id or None}, [recipe rows], {"project": name}.

    One project per SOURCE project (18 Nov cold run, notes 13 and 19): the recipes that came out of one project (the
    ad's cast stage and its rooms) are rebuilt into ONE project, `<key> sets`, the name the run sheet prints in, so a
    person and the product can be put into a room. A recipe that clears the scene first (a product build) keeps a
    project of its own and is a reference for the product's shape only."""
    rec_dir = ws / "components" / "3d-recipes"
    try:
        reg = json.loads((rec_dir / "recipes.json").read_text())
    except (OSError, ValueError):
        return {}, [], {}
    reg = reg if isinstance(reg, list) else list((reg.get("recipes") or reg).values()) if isinstance(reg, dict) else []
    slug = lambda x: re.sub(r"[^a-z0-9]+", "-", str(x).lower()).strip("-")  # noqa: E731
    projects = set()
    for pl in places:
        try:
            el = json.loads((ws / "runs" / "ai-elements" / brand / "sets" / slug(pl) / "element.json").read_text())
            sj = json.loads((ws / "runs" / "image-production" / brand / "sets" / el["print"] / "set.json").read_text())
            projects.add((sj.get("project") or {}).get("id"))
        except (OSError, ValueError, KeyError):
            continue
    keep = [r for r in reg if r.get("source_project") in projects
            or any(str(r.get("recipe", "")).startswith("%s-%s" % (brand, slug(pid))) for pid in product_ids)]
    # a product with a numbered master build (`-v2-product-master`) is that build alone: its older casting-sheet build is
    # superseded and was built to another size (cold run 18 Nov: 14.3 cm against the master's 15.2 cm)
    for pid in product_ids:
        pre = "%s-%s" % (brand, slug(pid))
        mine = [r for r in keep if str(r.get("recipe", "")).startswith(pre)]
        masters = sorted([r for r in mine if re.search(r"-v(\d+)-product-master$", str(r.get("recipe")))],
                         key=lambda r: int(re.search(r"-v(\d+)-", r["recipe"]).group(1)))
        if masters:
            keep = [r for r in keep if r not in mine or r is masters[-1]]
    if not keep:
        return {}, [], {}
    (out / "3d").mkdir(exist_ok=True)
    rows, code, own = [], "", {}
    for r in keep:
        src = rec_dir / r["recipe"]
        if src.is_dir():
            shutil.copytree(src, out / "3d" / r["recipe"], dirs_exist_ok=True)
            text = "".join(f.read_text() for f in sorted(src.glob("step-*.py")))
            own[r["recipe"]] = bool(CLEARS_SCENE.search(text))
            if not own[r["recipe"]]:
                code += text
            rows.append(r)
    sets_rows = [r for r in rows if not own[r["recipe"]]]
    prod_rows = [r for r in rows if own[r["recipe"]]]
    sources = list(dict.fromkeys(r.get("source_project") for r in sets_rows))
    name = "%s sets" % key if key else "this ad's sets"
    groups = [(name if len(sources) == 1 else "%s · %d" % (name, i + 1), [r for r in sets_rows if r.get("source_project") == sp])
              for i, sp in enumerate(sources)]
    rooms = {pl: (slug(pl) if re.search(r'"%s"\s*:' % re.escape(slug(pl)), code) else None) for pl in places}
    all_rooms = re.findall(r'^\s*"([a-z0-9-]+)"\s*:\s*dict\(', code, flags=re.M)
    spare = [x for x in all_rooms if x not in set(rooms.values())]
    has_cast = "CAM_cast_" in code
    has_tube = "PS_tube" in code
    size = None
    for pid in product_ids:
        try:
            kit = json.loads((ws / "runs" / "ai-elements" / brand / "products" / str(pid) / "kit.json").read_text())
            size = kit.get("size_cm")
        except (OSError, ValueError):
            pass
    L = ["# Build the 3D sets first (3D Jutsu)", "",
         "Every start picture in this ad is a **3D print**: a set built in Higgsfield 3D Jutsu, rendered, then printed with "
         "the people's sheets. A Jutsu project cannot be shared between accounts, so each build comes with its recipe: "
         "code that rebuilds it the same in any account. Building and rendering are free; only a print costs credits "
         "(about 2.5 each). The builds render nothing when they finish: the first thing to look at is the first start "
         "picture's render.", "", "## 1. Rebuild the builds in your account (once)", "",
         "| Project (find it by this exact name, else create it) | Recipes run into it, in this order | Steps | What it is for |",
         "|---|---|---|---|"]
    for pname, grp in groups:
        L.append("| %s | %s | %s | the rooms, the people as plain figures and the product at its size: every start "
                 "picture is set up and rendered here |" % (pname, " then ".join("`3d/%s/`" % r["recipe"] for r in grp),
                                                           " + ".join(str(len(r.get("steps") or [])) for r in grp)))
    for r in prod_rows:
        L.append("| %s | `3d/%s/` | %d | the product's exact shape, for reference only: it starts by clearing its scene, "
                 "so it never shares a project. Not needed to make a start picture |" % (
                     r.get("name"), r["recipe"], len(r.get("steps") or [])))
    L += ["", "For each project: `scene_builder_3d_list_projects`; if a project with that exact name is there, use it. If "
          "not, `scene_builder_3d_create_project` with that name, then run its recipes in the order given, each "
          "`step-NN.py` in order with `scene_builder_3d_run_python`, the code unchanged, the revision from the last step (0 "
          "to begin), scene sequence 0; wait for `succeeded` before the next. A step that fails: stop and report it. "
          "Never retype a step. A project of the same name from an earlier ad is another ad's: leave it.", ""]
    if people:
        L.append("People in this ad: %s. Each is a plain grey figure at their true build in the sets project (`CS_<name>_*`, "
                 "for example `CS_%s_torso`)%s; any other figure there belongs to an earlier draft: leave it out." % (
                     ", ".join(people), str(people[0]).lower(), ", with a camera `CAM_cast_<name>`" if has_cast else ""))
    if has_tube:
        h = size.get("height") if isinstance(size, dict) else None
        w = size.get("width") if isinstance(size, dict) else None
        L.append("The product: the tube in the sets project (`PS_tube_*`) is the size every start picture uses%s." % (
            (" (the product's true size is %s cm tall x %s cm wide, from its casting sheet)" % (h, w)) if h and w else
            "; the product kit gives no true size yet, so the sets project's tube is the size to use"))
    if spare:
        L.append("The rooms build also holds %s: not used in this ad." % ", ".join("`%s`" % x for x in spare))
    L += ["", "## 2. Each start picture", "",
          "1. In the sets project, set the clip's room camera (`CAM_loc_<room>`, named on each clip in CLIPS.md) as the "
          "scene camera.",
          "2. Copy each person the clip's first shot names (their `CS_<name>_*` pieces) into the room, where that shot puts "
          "them; copy the product (`PS_tube_*`) in when the shot holds it. Move copies, never resize them.",
          "3. Render inside a scene edit: 608 x 1080, EEVEE, 8 samples (the size every recipe sets), published with "
          "`artifacts.file`. Every print needs its own fresh render.",
          "4. Print with `scene_builder_3d_generate_angles`: the render, ONE reference picture, `refs/<clip>/print-board.png` "
          "(the clip's cast sheets, its set and the product on one board, made for you), and the start picture's words "
          "from RUN.md (the step named `start picture for <clip>`), 9:16 at 2k.",
          "5. Look at the print against the sheets: face, outfit, the product's shape and label, true size. Wrong: fix the set "
          "or the words and print again; never patch a print. Three wrong prints: stop and report what keeps going wrong.",
          "", "## Rooms in this ad", "", "| Place | Room camera | Set picture (the look to match) |", "|---|---|---|"]
    for pl in places:
        rid = rooms.get(pl)
        sp = out / "refs" / "elements" / slug(pl)
        pics = sorted(f.name for f in sp.glob("*.png")) if sp.is_dir() else []
        L.append("| %s | %s | %s |" % (pl, ("`CAM_loc_%s`" % rid) if rid else
                                       "not in the build: block it at true size in the sets project first",
                                       ", ".join("`refs/elements/%s/%s`" % (slug(pl), f) for f in pics) or
                                       "`refs/elements/%s/`" % slug(pl)))
    (out / "3d" / "JUTSU.md").write_text("\n".join(L) + "\n")
    return rooms, rows, {"project": groups[0][0] if groups else None}


def _print_board(out, c):
    """One reference picture for a clip's 3D print (3d/JUTSU.md: the print takes ONE reference): the clip's cast
    sheets, its set and the product, side by side on one board, `refs/<clip>/print-board.png`. Never the swipe's
    frame or the look swatch (those shape the blockout and the words, not the print). None when nothing to board or
    no Pillow."""
    files = [out / r for r in c.get("refs") or [] if not Path(r).name.startswith(("swipe-", "the-ad-s-look", "ours-"))
             and Path(r).suffix.lower() in (".png", ".jpg", ".jpeg") and Path(r).name != "print-board.png"]
    files = [f for f in files if f.is_file()]
    if not files:
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    H, pad = 900, 24
    ims = []
    for f in files:
        try:
            im = Image.open(f).convert("RGB")
        except OSError:
            continue
        ims.append(im.resize((max(1, int(im.width * H / im.height)), H)))
    if not ims:
        return None
    rows, row, w = [], [], 0
    for im in ims:                              # rows no wider than ~3 sheets
        if row and w + im.width > 3 * H:
            rows.append(row)
            row, w = [], 0
        row.append(im)
        w += im.width + pad
    rows.append(row)
    W = max(sum(i.width for i in r) + pad * (len(r) + 1) for r in rows)
    board = Image.new("RGB", (W, len(rows) * (H + pad) + pad), "white")
    y = pad
    for r in rows:
        x = pad
        for im in r:
            board.paste(im, (x, y))
            x += im.width + pad
        y += H + pad
    dst = out / "refs" / c["id"] / "print-board.png"
    board.save(dst, optimize=True)
    return "refs/%s/print-board.png" % c["id"]


def _first_shot_words(c):
    """The start picture's words: the clip's first shot, without its time or its lyric, then who wears what and the
    look, so the print shows the moment the clip starts on (CLIPS.md's recipe, never a second draft)."""
    lines = (c.get("recipe") or "").split("\n")
    first = next((x.strip() for x in lines if re.match(r"\s*1\. ", x)), "")
    first = re.sub(r"^1\.\s*", "", first)
    bits = [b for b in first.split(" · ") if not re.match(r"^[\d.]+–[\d.]+ s$", b) and not b.startswith("under “")
            and not b.startswith("camera:")]
    out = ["The first moment of the clip, in %s: %s." % (c.get("where") or "the room", " · ".join(bits))]
    out += [x.strip() for x in lines if x.startswith("Wardrobe:")]
    look = next((x for x in lines if x.startswith("Look:")), "")
    if look:
        out.append(look)
    return "\n".join(out)


CLIP_MAX_S = 15.0      # the longest clip one generation makes (the take chain splits a long scene into parts of 15 s or less)


def _sung_parts(song, order):
    """A sung production's clips, set-up by set-up (song-ad V35: one place and camera set-up per clip, the lyric beats
    played inside it). The production joins neighbouring brief scenes (scene_shots.join_sections keeps the first id),
    so production scene S8 is brief S8 up to the next production id. Its shots, in order, are cut into a new part when
    the written scene or the place changes, or the part would pass CLIP_MAX_S, so every clip sits inside one written
    scene and matches that scene's step on the run sheet. Each shot keeps its lyric, its time on the song (a line the
    gate did not hear keeps the window the brief gives it), who, what they do, face and gestures.
    -> {production scene: [{"where", "start", "end", "shots": [...]}]}, empty when the brief has no timed shots."""
    briefs = (song or {}).get("brief_scenes") or []
    ids = [b.get("id") for b in briefs]
    marks = [ids.index(s) for s in order if s in ids]
    if not marks or marks[0] != 0:
        return {}
    out = {}
    for k, s in enumerate([s for s in order if s in ids]):
        a = marks[k]
        b = marks[k + 1] if k + 1 < len(marks) else len(briefs)
        shots = []
        for bs in briefs[a:b]:
            for sh in bs.get("shots") or []:
                if sh.get("start") is None or sh.get("end") is None:
                    continue
                shots.append(dict(sh, scene=bs.get("id"), to_camera=bs.get("to_camera"),
                                  where=sh.get("where") or bs.get("setting_id") or ""))
        parts = []
        for sh in shots:
            p = parts[-1] if parts else None
            if p and p["where"] == sh["where"] and p["scene"] == sh["scene"] and sh["end"] - p["start"] <= CLIP_MAX_S:
                p["shots"].append(sh)
                p["end"] = sh["end"]
            else:
                parts.append({"where": sh["where"], "scene": sh["scene"], "start": sh["start"], "end": sh["end"], "shots": [sh]})
        if parts:
            out[s] = parts
    return out


def _shot_line(sh):
    """One shot of a sung clip, written out whole: its time on the song, the line it plays under, who does what."""
    bits = ["%.1f–%.1f s" % (sh["start"], sh["end"]), "under “%s”" % " / ".join(sh.get("lyrics") or []) if sh.get("lyrics") else ""]
    act = " ".join(x for x in [sh.get("who") or "", sh.get("action") or ""] if x and x != "(none)")
    if act:
        bits.append(act)
    if sh.get("face"):
        bits.append("face: " + sh["face"])
    if sh.get("gestures"):
        bits.append("gestures: " + "; ".join(sh["gestures"]))
    if sh.get("camera_move"):
        bits.append("camera: " + sh["camera_move"])
    if sh.get("timed") == "window":
        bits.append("(the song gate did not hear this line; its time is the gap it sits in)")
    return " · ".join(b for b in bits if b)


def _ret(asset_of, scene, cid):
    """One name per clip: the door's step asset for the scene (`<key>_asset-NN.mp4`); a scene the brief shoots as several
    shots gets `-shotN` on the same name (the door makes it as one clip; made apart, they are named so)."""
    a = asset_of.get(scene)
    if not a:                                    # no door step (a screen recording, a split): still the brief key first
        return "returned/%s_%s.mp4" % (asset_of.get("_key") or "clip", scene)
    return "returned/" + a                       # the door makes the scene as one clip; its shots are in that clip's prompt


def _voice_into_sheet(out, RS):
    """The narration is already read (voice/ in this hand-off): the run sheet's 'not read yet' audio inputs become those
    files, so the editor's door attaches them (17 Nov walkthrough, N5)."""
    f = out / "run.json"
    s = json.loads(f.read_text())
    reads = {re.sub(r"^\d+-", "", v.stem): v for v in (out / "voice").glob("*.mp3")}
    hit = False
    for stp in s.get("steps") or []:
        for r in stp.get("references") or []:
            m = re.match(r"(S\w+)\.mp3 \(not read yet", str(r.get("file") or ""))
            if r.get("kind") == "audio" and m and m.group(1) in reads:
                name = "voice/" + reads[m.group(1)].name    # every reference carries all three places (runsheet.pack)
                r.update({"local": name, "file": name, "exists": True,
                          "drive": "Shared Assets/" + (out / name).resolve().relative_to(_ws().resolve()).as_posix()})
                hit = True
    try:
        secs = {}
        doc = json.loads((out / "clips.json").read_text())
        for sc in doc["scenes"]:
            secs[sc["scene"]] = sc.get("secs")
        for c in doc["clips"]:                   # a sung clip's length is its written scene's step's length
            if c.get("brief_scene"):
                secs[c["brief_scene"]] = round(sum(x["secs"] for x in doc["clips"] if x.get("brief_scene") == c["brief_scene"]), 2)
        import math
        for stp in s.get("steps") or []:
            m = re.search(r"clip for (S\w+)", stp.get("what") or "")
            if stp.get("medium") == "video" and m and secs.get(m.group(1)) and not (stp.get("settings") or {}).get("duration"):
                stp.setdefault("settings", {})["duration"] = max(4, min(15, int(math.ceil(secs[m.group(1)]))))
                hit = True
    except (OSError, ValueError, KeyError):
        pass
    if hit:
        f.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n")
        (out / "RUN.md").write_text(RS.render_md(s))


def _clips_into_sheet(out, RS):
    """One list of clips (18 Nov cold run, notes 6, 7, 13, 15, 20): the run sheet is drafted from the brief's scenes, one
    start picture and one clip per scene, while CLIPS.md makes a sung scene as one clip per place (S13 as S13.1-2, S13.3
    and S13.4) with its own recipe. Here the sheet's steps are rebuilt from clips.json, so RUN.md, run.json, CLIPS.md and
    the return names all name the same clips: per clip, a start picture step (the 3D print, its ONE reference the
    clip's print board, its words the clip's first shot) and a clip step (its prompt the clip's recipe, word for word,
    its length the clip's own). Explicit scene mappings cover sung and ordinary clips; older unmapped packs stay unchanged."""
    import copy
    import math
    f = out / "run.json"
    try:
        s = json.loads(f.read_text())
        doc = json.loads((out / "clips.json").read_text())
    except (OSError, ValueError):
        return False
    mapped = [c for c in doc.get("clips") or [] if c.get("brief_scene")]
    sung = [c for c in mapped if c.get("tool") != "edit"]
    edit_only = {c["brief_scene"] for c in mapped if c.get("tool") == "edit"} - {c["brief_scene"] for c in sung}
    if not mapped:
        return False
    steps = s.get("steps") or []
    pic, vid = {}, {}
    for st in steps:
        m = re.search(r"(start picture|clip) for (S[\w.]+)", st.get("what") or "")
        if m:
            (pic if m.group(1) == "start picture" else vid)[m.group(2)] = st
    h = s.get("handoff") or {}
    folder, drive = h.get("folder") or "", h.get("drive") or ""
    jutsu = (out / "3d" / "JUTSU.md").read_text() if (out / "3d" / "JUTSU.md").exists() else ""
    m = re.search(r"^\| ([^|]+?) \| `3d/[^|]*\| [^|]*\| the rooms", jutsu, flags=re.M)
    project = m.group(1).strip() if m else None
    new, moved, done = [], {}, set()
    for st in steps:
        m = re.search(r"(start picture|clip) for (S[\w.]+)", st.get("what") or "")
        scene = m.group(2) if m else None
        mine = [c for c in sung if c["brief_scene"] == scene] if scene else []
        if scene in edit_only:
            moved.setdefault(st["n"], [])
            continue
        if not mine or scene not in pic or scene not in vid:
            new.append(st)
            moved.setdefault(st["n"], []).append(st)
            continue
        if scene in done:
            continue
        done.add(scene)
        p0, v0 = pic[scene], vid[scene]
        vstem = Path(v0["asset"]).stem
        for c in mine:
            ret = Path(c["return"]).name
            tail = Path(ret).stem[len(vstem):] if Path(ret).stem.startswith(vstem) else "-" + c["id"].replace(".", "-")
            p = copy.deepcopy(p0)
            p.update({"asset": Path(p0["asset"]).stem + tail + Path(p0["asset"]).suffix,
                      "what": "start picture for %s" % c["id"], "prompt": c.get("start_words") or p0.get("prompt"),
                      "prompt_source": "the clip's first shot, from its recipe in CLIPS.md", "draft": False})
            if "who" not in c and not c.get("start_words"):
                p.update(draft=p0.get("draft", True), prompt_source="the brief's start-picture draft; finish it for this shot")
            board = c.get("print_board")
            if board:
                p["references"] = [{"n": 1, "kind": "image", "role": "the print board: %s's people, set and product on "
                                    "one picture" % c["id"], "file": "%s/%s" % (folder, board), "local": board,
                                    "drive": "%s/%s" % (drive, board), "exists": True, "element": None}]
                p.setdefault("print", {})["reference"] = [board]
            if p.get("job") == "3d-print" and jutsu:
                p["print"]["project"] = project
                p["print"]["how"] = [
                    "Follow `3d/JUTSU.md` (section 1 once for the ad, then section 2 for this picture), in the project "
                    "`{project}`.",
                    "Room camera: %s. Place %s where the first shot puts them%s; move copies, never resize them." % (
                        ("`CAM_loc_%s`" % c["room"]) if c.get("room") else "block %s at true size first" % c.get("where"),
                        ", ".join(c.get("who") or []) or "nobody",
                        " and the product (`PS_tube_*`)" if re.search(r"\btube|scrub|product\b", c.get("recipe") or "", re.I) else ""),
                    "Render it fresh: 608 x 1080, EEVEE, 8 samples, published with `artifacts.file`.",
                    "Upload the print board today (`media_upload`, PUT the bytes, `media_confirm`).",
                    "Print it: `scene_builder_3d_generate_angles` with the render's operationId and artifactId, the words "
                    "below word for word, referenceMediaId = the board's upload, 9:16, 2k, a new requestId; then "
                    "`scene_builder_3d_get_generation` until it has succeeded.",
                    "Look at it against the sheets on the board: face, outfit, the product's shape and label, true size. "
                    "Wrong: fix the set or the words and print again, never patch the print.",
                    "Right: save the `scene_builder_3d_get_generation` reply unchanged to a file and run `python3 "
                    "components/briefs/make.py save %s <STEP> --record <that file>`: it is named, put in `returned/` "
                    "and checked." % (s.get("brief_key") or "<brief>")]
            v = copy.deepcopy(v0)
            body = "\n".join(x for x in (c.get("recipe") or "").split("\n") if "no line sung here" not in x)
            v.update({"asset": ret, "what": re.sub(r"for S[\w.]+", "for " + c["id"], v0.get("what") or "clip"),
                      "prompt": "Image 1 is the first frame: keep this exact person, clothing, props, room and light.\n" + body,
                      "prompt_source": "the clip's recipe in CLIPS.md, word for word", "draft": False})
            if not body.strip():
                v.update(prompt=v0.get("prompt") or "", draft=True,
                         prompt_source="brief draft: write this clip's missing recipe before generation")
            v.setdefault("settings", {})["duration"] = max(4, min(15, int(math.ceil(c.get("secs") or 4))))
            who = {str(w).upper() for w in c.get("who") or []}
            if "who" in c and v.get("cast") is not None:  # sung clips explicitly name their cast
                v["cast"] = [x for x in v["cast"] if str(x.get("who") or "").upper() in who]
            for r in v.get("references") or []:
                if r.get("media_role") == "start_image" or r.get("role") == "the start picture":
                    r["file"] = "%s (not made yet: the step before makes it)" % p["asset"]
            new += [p, v]
            moved.setdefault(p0["n"], []).append(p)
            moved.setdefault(v0["n"], []).append(v)
    for i, st in enumerate(new, 1):
        st["n"] = i
        how = (st.get("print") or {}).get("how")
        if how:
            st["print"]["how"] = [x.replace("<STEP>", str(i)) for x in how]
    for r in new:                                # "the step before makes it" made exact
        for ref in r.get("references") or []:
            if "(not made yet: the step before makes it)" in str(ref.get("file")):
                ref["file"] = ref["file"].replace("the step before", "step %d" % (r["n"] - 1))
    rebuilt = {id(st) for sts in moved.values() for st in sts if st.get("prompt_source", "").startswith("the clip")}
    of = {}                                      # each rebuilt step -> its clip
    for c in sung:
        for st in new:
            if re.search(r"for %s(\s|$)" % re.escape(c["id"]), st.get("what") or ""):
                of[id(st)] = c
    for e in s.get("elements") or []:            # each element's steps, renumbered, and only where its clip has it
        cov = []
        for x in e.get("covers") or []:
            mm = re.match(r"step (\d+)(.*)", x)
            if not (mm and int(mm.group(1)) in moved):
                cov.append(x)
                continue
            for st in moved[int(mm.group(1))]:
                c = of.get(id(st)) if id(st) in rebuilt else None
                if c is not None and "who" in c and e.get("kind") == "cast" and str(e.get("name") or "").upper() not in \
                        {str(w).upper() for w in c.get("who") or []}:
                    continue
                cov.append("step %d%s" % (st["n"], "" if c is not None and st.get("medium") == "image" else mm.group(2))
                           + (" (on its print board)" if c is not None and st.get("medium") == "image" else ""))
        e["covers"] = list(dict.fromkeys(cov))
    s["steps"] = new
    s["gaps"] = [re.sub(r"\s*Drafted prompts are the brief's own words; tighten them against BRIEF\.md as you go\.", "", g)
                 for g in s.get("gaps") or [] if "every prompt here is a DRAFT" not in g] + [
        "CLIPS.md and this sheet name the same %d clips. Written recipes are copied word for word; a missing "
        "recipe keeps the brief draft and must be completed before generation." % len(sung)]
    h["per_clip"] = True
    boards = [c["print_board"] for c in sung if c.get("print_board")]
    have = {x.get("local") for x in h.get("refs") or []}
    h.setdefault("refs", []).extend({"name": Path(b).name, "local": b, "file": "%s/%s" % (folder, b),
                                     "drive": "%s/%s" % (drive, b), "source": b} for b in boards if b not in have)
    s["handoff"] = h
    f.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n")
    (out / "RUN.md").write_text(RS.render_md(s))
    return True


def _front_page(out, key, doc, song, sheet_steps):
    """handoff.md, the folder's first page (START-HERE.md says read it first; 18 Nov cold run, notes 2 and 24): what the
    ad is, what to read in what order, what every file and folder is for, and the order of work with its counts."""
    clips = [c for c in doc["clips"] if c.get("tool") != "edit"]
    edit = [c for c in doc["clips"] if c.get("tool") == "edit"]
    pics = [s for s in sheet_steps or [] if s.get("job") == "3d-print"]
    vids = [s for s in sheet_steps or [] if s.get("medium") == "video"]
    secs = sum((s.get("settings") or {}).get("duration") or 0 for s in vids)
    has = lambda p: (out / p).exists()  # noqa: E731
    L = ["# %s · %s" % (doc.get("title") or key, key), "",
         "**What it is:** %s ad, %s. %d clip%s to make%s, then the cut%s." % (
             "a sung" if song else "a narrated", doc.get("brand"), len(clips), "" if len(clips) == 1 else "s",
             (" and %d made in the edit (%s)" % (len(edit), ", ".join(c["id"] for c in edit))) if edit else "",
             " and its hook versions" if doc.get("hooks") is not None else ""), "",
         "## Read in this order", "",
         "1. **handoff.md**, this page.",
         "2. **CLIPS.md**: the one list of clips. Each clip's recipe, its files, its start picture and its return name.",
         "3. **ELEMENTS.md**: the people, places, product and look, already made. Use their files as they are."]
    drafts = [c["id"] for c in clips if not str(c.get("recipe") or "").strip()]
    if drafts:
        L += ["", "**Before generation:** finish the missing recipe for " + ", ".join(drafts) +
              " from BRIEF.md and its supplied swipe references. RUN.md keeps these as brief drafts; the maker owns this writing step.", ""]
    n = 4
    if has("3d/JUTSU.md"):
        L.append("%d. **3d/JUTSU.md**: rebuild the 3D sets in your own Higgsfield account (free), then how each start "
                 "picture is set up and printed." % n)
        n += 1
    if has("song/LISTEN.md"):
        L.append("%d. **song/LISTEN.md**: the lines to listen for before you cut. Where it says the owner kept a take, "
                 "that outranks a FAIL in `song/song.json` (the machine gate's own record)." % n)
        n += 1
    L += ["%d. **RUN.md** (and `run.json`, the same for a machine): the same clips as CLIPS.md, as tool calls, with the "
          "step numbers, settings, file names and every prompt word for word." % n, "",
          "## What else is here", ""]
    rows = [("swipe/", "the swipe video this ad remakes (`swipe.mp4`) and where it came from: watch it first"),
            ("BRIEF.md", "the brief as written, with its run sheet's sources"),
            ("brief/", "the written brief; its product, props and camera notes rule every clip"),
            ("refs/<clip>/", "each clip's own files; `print-board.png` is its start picture's one print reference"),
            ("refs/elements/", "every element's files, the same as in ELEMENTS.md"),
            ("3d/", "the recipes that rebuild the sets (3d/JUTSU.md says how)"),
            ("song/", "the song, its timing and the song gate's record"),
            ("voice/", "the narration reads"),
            ("made/", "scenes already made"),
            ("fonts/", "the caption font"),
            ("sfx/", "the bank sound effects for the hook versions"),
            ("TIMELINE.html", "the ad on its clock; open it in a browser and tap a block for its clip"),
            ("hyperframes/", "the cut as a HyperFrames project, a placeholder in each clip's place: replace each with "
                             "your clip under the same name"),
            ("edit/", "the same cut as a Premiere timeline (`.premiere.xml`) with its placeholders"),
            ("returned/", "where every finished clip, the cut and the hook versions go, named as CLIPS.md says")]
    for name, what in rows:
        if has(name.split("<")[0].rstrip("/")) or name == "returned/":
            L.append("- `%s`: %s" % (name, what))
    L += ["", "## The order of work", ""]
    k = 1
    if has("3d/JUTSU.md"):
        L.append("%d. The 3D builds (free, once): 3d/JUTSU.md section 1." % k)
        k += 1
    if pics:
        L.append("%d. The %d start pictures, each a 3D print (2.5 credits each, %.1f in all). Check each against its "
                 "sheets before any clip is made." % (k, len(pics), 2.5 * len(pics)))
        k += 1
    if vids:
        L.append("%d. The %d clips, %d seconds in all on %s. Quote the cost first with `estimate_video_cost` (free) and "
                 "tell the person what it will spend before the first one." % (
                     k, len(vids), secs, ", ".join(sorted({s.get("model_name") or "" for s in vids} - {""}))))
        k += 1
    L += ["%d. The cut: `python3 components/video-edit/machine/run.py handoff <this folder>` (or by hand, from the "
          "timeline in `hyperframes/` or `edit/`): every clip on its time, %s, the captions as CLIPS.md says." % (
              k, "the song under the whole cut" if song else "the reads on their scenes"),
          "%d. The versions CLIPS.md names, each into `returned/`." % (k + 1),
          "%d. Run the editor queue's `sync` after each stage; the finished ad lands as a card in "
          "`Shared Assets/meta/%s/1-check/video/` for approval. Nothing goes live from here." % (k + 2, doc.get("brand")), ""]
    (out / "handoff.md").write_text("\n".join(L) + "\n")


def _brief_and_elements(out, W, key, brand, frames, production=None, order=(), extra=None, clips=None):
    ME = _here("maker_elements")                 # the brief and what to build first, with its real files (16 Nov)
    return ME.build(out, W, key, brand, _ws(), production=production, order=order, briefs=ST.BRIEFS, extra=extra,
                    clips=clips)


def build(n, drive=True):
    B = Path(ST.BRIEFS) / n
    brief = _load(B / "brief.json")
    run = brief["brief"]
    W = Path(ST.WRITING) / run
    rj = _load(W / "run.json") if (W / "run.json").exists() else {}
    brand = rj.get("brand") or run.split("-")[0]
    key = _key(brief, brand, n, rj)
    sheet, asset_of = None, {"_key": key}
    if "_brief-" in key:                        # the door's own step names are THE names (17 Nov: two naming systems)
        try:
            sys.path.insert(0, str(_ws() / "components" / "briefs"))
            import runsheet as RS
            sheet = RS.build(key, brand=brand)
            for stp in sheet["steps"]:
                m = re.search(r"clip for (S\w+)", stp.get("what") or "")
                if stp.get("medium") == "video" and m:
                    asset_of.setdefault(m.group(1), stp["asset"])
        except (Exception, SystemExit):  # noqa: BLE001 — named in the pack below when the run sheet cannot be written
            sheet = None
    out = _ws() / "runs" / "handoffs" / "video-editor" / brand / key
    for d in ("made", "voice", "refs", "returned"):
        (out / d).mkdir(parents=True, exist_ok=True)
    try:                                         # the swipe video travels with the brief (2026-11-19)
        import importlib.util as _iu
        _sp = _iu.spec_from_file_location("mp_runsheet", _ws() / "components" / "briefs" / "runsheet.py")
        _rs = _iu.module_from_spec(_sp); _sp.loader.exec_module(_rs)
        _rs.swipe_into(out, run, _ws())
    except Exception:  # noqa: BLE001 — the pack is still written; handoff_check names a missing swipe
        pass
    board = {}
    req = Path(ST.REPO if hasattr(ST, "REPO") else "") / "handoff-requests" / (brief.get("idea", n) + ".json")
    for cand in [req, Path(os.environ.get("VIDEO_STUDIO_BOARD_DATA", "")) / "handoff-requests" / (brief.get("idea", n) + ".json")]:
        if cand.is_file():
            board = {s["id"]: s for s in _load(cand).get("scenes") or []}
            break
    frames = W / "framemap" / "shots"
    if not frames.is_dir() and rj.get("forked_from"):          # a forked run (a sung remake) reads its swipe's frames
        frames = Path(ST.WRITING) / rj["forked_from"] / "framemap" / "shots"
    song = _song(W, brand, run, out)                            # a sung ad: the song, its timing, each scene's lyric lines
    parts = _sung_parts(song, brief["order"]) if song else {}   # a sung ad's clips, one per place and camera set-up
    try:                                        # the footage chain's own decisions per scene (storyboard-footage.json)
        footage = _load(W / "stages" / "storyboard-footage.json").get("scenes") or {}
    except (OSError, ValueError):
        footage = {}
    how = made_as(brief)                         # how the ad is made, from the chain's one rule
    lane = how["lane"]
    passed = passed_clips(footage)              # the clips the footage decision passed for this ad
    written = {s.get("id"): s for s in _brief_doc(W).get("scenes") or []}   # the written brief's own scenes
    scenes, clips, t = [], [], 0.0
    for i, s in enumerate(brief["order"], 1):
        pick = brief["picks"][s]
        wf = _load(B / "scenes" / s / (pick + ".json"))
        made = B / "scenes" / s / "out" / pick / (s + ".mp4")
        bs = board.get(s) or {}
        sl = (song or {}).get("scenes", {}).get(s) or {}
        row = {"n": i, "scene": s, "section": bs.get("section") or wf.get("title"),
               "words": " / ".join(sl.get("lyrics") or []) or wf.get("words") or "",
               "on_screen": bs.get("on_screen") or "", "swipe": bs.get("source") or "", "status": "made" if made.exists() else "needs clips"}
        for st in wf.get("steps") or []:
            if st["tool"] == "voice.read" and st["inputs"].get("file"):
                v = B / st["inputs"]["file"]
                if v.exists():
                    shutil.copy2(v, out / "voice" / ("%02d-%s.mp3" % (i, s)))
                    row["voice"] = "voice/%02d-%s.mp3" % (i, s)
        # a scene cut in the Real pass from our closest clips (not ones the footage check passed) is not "made" in the
        # AI / AI + Real lanes: it goes to the maker, our cut rides along as a reference only (16 Nov: the Real pass on
        # idea-21 carried burned-in captions, other products and a different man in every scene).
        # NARROWED 2026-11-18 (the logic layer): in the AI + Real lane a scene whose every own-footage step is cut from
        # a clip the footage decision PASSED is ours to keep. It used to be thrown back with the rest, so a scene given
        # to our footage never reached the editor as a file. The AI lane is unchanged: every shot is made.
        has_trim = any(st["tool"] == "ffmpeg.trim" for st in wf.get("steps") or [])
        ours = ours_passed(wf, passed) if (lane == "mix" and has_trim) else None
        stale = lane in ("ai", "mix") and has_trim and not ours
        to_make = any(st["tool"] in AI_TOOLS for st in wf.get("steps") or [])
        if ours and not made.exists() and not to_make:   # passed, not cut by the Studio yet: cut here so it arrives as a file
            dst = out / "made" / ("%02d-%s.mp4" % (i, s))
            why_not = lay_ours(ours, dst)
            if why_not is None:
                row["file"] = "made/%02d-%s.mp4" % (i, s)
                row["status"] = "made"
            else:
                row["status"] = "our footage: not cut yet"
                row["ours_note"] = why_not
        if ours:                                 # the source and times ride along either way, so nobody has to find them
            row["ours"] = ours
            row["why"] = ("our own footage: every clip of ours in this scene was passed by the footage decision"
                          + ("; its other shots are made" if to_make else ""))
        if made.exists() and not stale:
            shutil.copy2(made, out / "made" / ("%02d-%s.mp4" % (i, s)))
            row["file"] = "made/%02d-%s.mp4" % (i, s)
        elif stale:
            (out / "ours-reference").mkdir(exist_ok=True)
            if made.exists():
                shutil.copy2(made, out / "ours-reference" / ("%02d-%s.mp4" % (i, s)))
            cid = "%s-shot-1" % s
            ks = [x["k"] for x in bs.get("swipeShots") or [] if x.get("k")]
            refs = []
            (out / "refs" / cid).mkdir(parents=True, exist_ok=True)
            for k in ks:
                for part in ("first", "mid", "last"):
                    f = frames / ("%s-%s.jpg" % (k, part))
                    if f.exists():
                        shutil.copy2(f, out / "refs" / cid / f.name)
                        refs.append("refs/%s/%s" % (cid, f.name))
            # our own action, from the brief (2026-11-25: the swipe's action went in too, its person rolling another brand's
            # bottle on his scalp, and that is what came back); the swipe's shots ride along as framing and timing only
            recipe = bs.get("happens") or (written.get(s) or {}).get("happens") or ""
            clips.append({"id": cid, "scene": s, "tool": "gen.shot", "recipe": ("Remake the swipe moment with our person and our product: " + recipe) if recipe else "",
                          "copies": ks, "swipe": [{"k": x.get("k"), "seconds": x.get("len"), "does": x.get("does"), "text": x.get("text")} for x in bs.get("swipeShots") or []],
                          "named_refs": ["the ad's person (same as every other clip)"], "refs": refs,
                          "our_cut": ("ours-reference/%02d-%s.mp4" % (i, s)) if made.exists() else None,
                          "same_people_as": None, "continues": None, "lips": None, "return": _ret(asset_of, s, cid)})
            row["clips"] = [cid]
            row["status"] = "needs clips"
            row["why"] = ("made, not cut: our footage of this scene was not passed by the footage decision"
                          if lane == "mix" else "made: every shot of this ad is made (the AI lane)")
        elif s in parts and any(st["tool"] in AI_TOOLS for st in wf.get("steps") or []):
            # a sung scene: one clip per set-up, every shot written out with its time on the song (18 Nov, idea-12:
            # the one-beat take prompt and the first joined scene's time left 34 of 78 sung lines with no clip)
            row["clips"] = []
            try:
                look = _load(B / "scenes" / s / "take.json").get("look") or ""
            except (OSError, ValueError):
                look = ""
            many = len(parts[s]) > 1
            for k, p in enumerate(parts[s], 1):
                # named by scene and shot (owner, 18 Nov: "we operate on scenes and shots"): S11 for a whole scene,
                # S13.3 or S13.1-2 when a scene's shots sit in more than one place
                nums = [str(sh.get("id") or "").split(".")[-1] for sh in p["shots"]]
                whole = len([q for q in parts[s] if q["scene"] == p["scene"]]) == 1
                cid = p["scene"] if whole else "%s.%s" % (p["scene"], nums[0] if len(nums) == 1 else "%s-%s" % (nums[0], nums[-1]))
                who = list(dict.fromkeys(sh.get("who") for sh in p["shots"] if sh.get("who") and sh.get("who") != "(none)"))
                talks = any(sh.get("to_camera") for sh in p["shots"])
                recipe = "One continuous clip in %s, %d shot%s in order:\n%s%s" % (
                    p["where"] or "one place", len(p["shots"]), "s" if len(p["shots"]) > 1 else "",
                    "\n".join("  %d. %s" % (j, _shot_line(sh)) for j, sh in enumerate(p["shots"], 1)),
                    ("\nLook: " + look) if look else "")
                ret = _ret(asset_of, p["scene"] if p["scene"] in asset_of else s, cid)   # the scene's own run-sheet step
                if not whole:                    # its shots, on the scene's step name: -shot3, -shots1-2
                    ret = re.sub(r"(\.mp4)$", ("-shot%s" if len(nums) == 1 else "-shots%s") % cid.split(".", 1)[1] + "\\1", ret)
                clips.append({"id": cid, "scene": s, "tool": "gen.take", "recipe": recipe, "copies": [], "swipe": [],
                              "named_refs": [], "refs": [], "same_people_as": None,
                              "continues": None, "return": ret, "where": p["where"], "who": who, "brief_scene": p["scene"],
                              "props": list(dict.fromkeys(sh.get("prop") for sh in p["shots"] if sh.get("prop"))),
                              "song_at": [p["start"], p["end"]], "lyrics": [l for sh in p["shots"] for l in sh.get("lyrics") or []],
                              "lips": ("sung on camera: lips to song/song.mp3 %.1f–%.1f s" % (p["start"], p["end"])) if talks
                              else "none: a silent shot under the song; nobody sings on camera"})
                row["clips"].append(cid)
            row["sung_parts"] = True
        else:
            row["clips"] = []
            for st in wf.get("steps") or []:
                if st["tool"] not in AI_TOOLS:
                    continue
                cid = "%s-%s" % (s, st["id"])
                p = st.get("params") or {}
                ks = [k for k in str(p.get("copies") or "").replace(",", " ").split() if k.startswith("K")]
                if not ks:
                    ks = [x["k"] for x in bs.get("swipeShots") or [] if x.get("k")]
                refs = []
                (out / "refs" / cid).mkdir(parents=True, exist_ok=True)
                for k in ks:
                    for part in ("first", "mid", "last"):
                        f = frames / ("%s-%s.jpg" % (k, part))
                        if f.exists():
                            shutil.copy2(f, out / "refs" / cid / f.name)
                            refs.append("refs/%s/%s" % (cid, f.name))
                swipe = [{"k": x.get("k"), "seconds": x.get("len"), "does": x.get("does"), "text": x.get("text")}
                         for x in bs.get("swipeShots") or [] if not ks or x.get("k") in ks]
                ret = _ret(asset_of, s, cid)
                if sum(step["tool"] in AI_TOOLS for step in wf.get("steps") or []) > 1:
                    ret = str(Path(ret).with_name(Path(ret).stem + "-" + st["id"] + Path(ret).suffix))
                c = {"id": cid, "scene": s, "brief_scene": s, "tool": _clip_tool(st, wf, bs), "recipe": _once(st.get("prompt") or ""),
                     "copies": ks, "swipe": swipe, "named_refs": (st.get("inputs") or {}).get("refs") or [],
                     "refs": refs, "same_people_as": p.get("scene_master") and "%s-%s" % (s, p["scene_master"]),
                     "continues": p.get("continue_from") and "%s-%s" % (s, p["continue_from"]),
                     "lips": p.get("lips"), "return": ret}
                clips.append(c)
                row["clips"].append(cid)
        # its length falls out of what it holds (never a number): the swipe moment, the voice it plays, its caption lines
        vlen = _dur(out / row["voice"]) if row.get("voice") else None
        lines = len([x for x in (row["on_screen"] or "").split("\n") if x.strip()])
        row["secs"] = round(max(_span(row["swipe"]) or 0, vlen or 0, 1.2 * lines, 1.5), 2)
        if sl.get("start") is not None and sl.get("end"):       # sung: the scene's time on the song decides its length
            row["song_at"] = [sl["start"], sl["end"]]
            row["secs"] = round(sl["end"] - sl["start"], 2)
        if row.get("sung_parts"):               # its words are every line its clips play under
            mine = [c for c in clips if c["scene"] == s]
            row["words"] = " / ".join(l for c in mine for l in c["lyrics"])
            row["song_at"] = [mine[0]["song_at"][0], mine[-1]["song_at"][1]]
            row["secs"] = round(row["song_at"][1] - row["song_at"][0], 2)
        route = _route(row["swipe"])
        for c in clips:
            if c["scene"] != s:
                continue
            if row.get("sung_parts"):           # timed across the whole song below, once every clip is known
                c["route"] = route
                continue
            c["secs"] = round(row["secs"] / max(len(row.get("clips") or [1]), 1), 2)
            c["route"] = route
            w = written.get(s) or {}            # people who talk to each other in a scene still speak: only a shot with a read over it
            off = w.get("to_camera") is False and w.get("kind") in ("broll", "card", "split")
            if row.get("voice") and off:        # the brief says nobody talks to camera here: the read plays over it (2026-11-25,
                c["lips"] = "off: %s plays over it; nobody speaks on camera" % row["voice"]   # 0336's people were told to mouth the narrator)
            elif row.get("voice"):              # one answer on lip sync, the run sheet's: a scene with a read talks to it
                c["lips"] = "on: lips to %s" % row["voice"]
            elif row.get("song_at") and sl.get("lyrics"):   # sung: whoever sings on camera mouths their lines on the song
                c["lips"] = "sung: a person singing on camera mouths these lines on song/song.mp3 %.1f–%.1f s" % tuple(row["song_at"])
            near = ((footage.get(s) or {}).get("ref") or {}).get("frame")   # the chain's nearest clean clip of ours
            if near and Path(near).exists():
                (out / "refs" / c["id"]).mkdir(parents=True, exist_ok=True)
                shutil.copy2(near, out / "refs" / c["id"] / "ours-nearest.jpg")
                c["refs"].append("refs/%s/ours-nearest.jpg" % c["id"])
                c["named_refs"] = [r for r in c["named_refs"] if "owned" not in r.lower()] + [
                    "our nearest clip (ours-nearest.jpg): a reference for the action only, not a clip to cut"]
            if route == "screen":
                c["make"] = "SCREEN RECORDING, made in the edit: record our product page on a phone, the way the swipe scrolls its site"
            elif route == "split":
                c["make"] = "SPLIT SCREEN: two clips, top and bottom, as the swipe lays it out; make each half, stack them in the edit"
            elif c["tool"] == "edit":
                c["make"] = "CARD, made in the edit: build the scene from the brief and its on-screen words; no model call."
            elif not c["recipe"] and not c["swipe"] and not any((written.get(s) or {}).get(k) for k in ("happens", "first_frame", "split", "shots")):
                c["hold"] = "Nothing to make: no recipe and no swipe moment. Leave it out of the cut unless the brief says otherwise."
        if not row.get("sung_parts"):           # one clip per real moment: short shots and repeats are one take (2026-11-25)
            mine = [c for c in clips if c["scene"] == s]
            if mine:
                at = clips.index(mine[0])
                got = _here("clip_join").join(mine) if len(mine) > 1 else mine
                got = [x for c in got for x in _here("clip_join").split(c, row.get("words") if len(got) == 1 else "")]
                clips[:] = [c for c in clips[:at] if c["scene"] != s] + got + [c for c in clips[at:] if c["scene"] != s]
                row["clips"] = [c["id"] for c in got]
                for c in got:                   # its frames, where every reader looks for a clip's own
                    if c.get("joined") or c.get("part"):
                        (out / "refs" / c["id"]).mkdir(parents=True, exist_ok=True)
                        new = []
                        for r in c["refs"]:
                            f = out / r
                            if f.is_file() and not (out / "refs" / c["id"] / f.name).exists():
                                shutil.copy2(f, out / "refs" / c["id"] / f.name)
                            new.append("refs/%s/%s" % (c["id"], f.name))
                        c["refs"] = list(dict.fromkeys(new))
        scenes.append(row)
    extra = []
    sung = sorted([c for c in clips if c.get("song_at")], key=lambda c: c["song_at"][0])
    if sung:
        # on the song's clock end to end: each clip runs from its first line to the next clip's first line (the first
        # from 0 s, the last to the song's end), so no stretch of the song is left without a picture
        end = (song or {}).get("seconds") or sung[-1]["song_at"][1]
        for j, c in enumerate(sung):
            a = 0.0 if j == 0 else c["song_at"][0]
            last = c["song_at"][1]
            b = sung[j + 1]["song_at"][0] if j + 1 < len(sung) else min(end, last + 1.0)
            if b - last > 0.3:                  # a stretch with no line sung: the clip carries it, never a frozen frame
                c["recipe"] += ("\n  %.1f–%.1f s · no line sung here: keep the last shot moving into the next clip (slow it to "
                                "no less than 0.75x, then play it back in reverse; never a held frame)" % (last, b))
            c["song_at"] = [round(a, 2), round(b, 2)]
            c["secs"] = round(b - a, 2)
        for r in scenes:                         # each scene's time is its clips' time on the song
            mine = [c for c in sung if c["scene"] == r["scene"]]
            if mine:
                r["song_at"] = [mine[0]["song_at"][0], mine[-1]["song_at"][1]]
                r["secs"] = round(r["song_at"][1] - r["song_at"][0], 2)
        # each clip's own files: its people's sheets, ITS place's print (a banked set by its name when the scene's own
        # set is another place), the product when a shot handles it, the look
        try:
            els = _here("maker_elements")._from_scenes(n, brief["order"], ST.BRIEFS, W.parent)
        except Exception:  # noqa: BLE001
            els = {}
        by = {str(k).upper(): (k, e) for k, e in els.items()}
        sets = _ws() / "runs" / "ai-elements" / brand / "sets"
        prod_words = re.compile(r"\b(tube|tubes|scrub|label|product|%s)\b" % re.escape(brand), re.I)
        for c in sung:
            picks = []
            for w in c["who"]:
                if w.upper() not in by:
                    continue
                name, e = by[w.upper()]
                looks = sorted({str(f) for x in e["files"] for f in Path(x).parent.glob("look-*.jp*g")})
                rest = [f for f in e["files"] if "look-" not in Path(f).name][:2]          # the headshot, the sheet
                text = c["recipe"].split("\nLook:")[0].lower()      # the shots' own words, not the look line
                hit = [f for f in looks if any(re.search(r"\b%s\b" % re.escape(wd), text)       # the garment, never a colour
                                               for wd in re.sub(r"^look-\d+-", "", Path(f).stem).split("-")
                                               if len(wd) > 3 and wd not in COLOUR_WORDS)]
                if not hit:                      # no garment named in its shots: the look its scene's take sheet gives
                    try:
                        sheet_ = ((_load(B / "scenes" / c["scene"] / "take.json").get("cast") or {}).get(w) or {}).get("sheet")
                    except (OSError, ValueError):
                        sheet_ = None
                    hit = [f for f in looks if sheet_ and Path(f).name == Path(sheet_).name] or \
                          [f for f in e["files"] if "look-" in Path(f).name][:1]
                if hit and looks:
                    c["recipe"] += "\nWardrobe: %s in %s" % (w, re.sub(r"^look-\d+-", "", Path(hit[0]).stem).replace("-", " "))
                picks += [(name, f) for f in rest + hit[:1]]
            pl = (c.get("where") or "").upper()
            if pl in by:
                picks += [(by[pl][0], f) for f in by[pl][1]["files"][:1]]
            elif pl:
                f = sets / re.sub(r"[^a-z0-9]+", "-", pl.lower()).strip("-") / "picture.png"
                if f.is_file():
                    picks.append((c["where"], str(f)))
                    extra.append({"name": c["where"], "kind": "setting", "file": str(f), "scene": c["scene"]})
                else:
                    c["named_refs"].append("%s: no banked set; build it once in the ad's style (ELEMENTS.md)" % c["where"])
                    extra.append({"name": c["where"], "kind": "setting", "file": None, "scene": c["scene"]})
            if prod_words.search(c["recipe"]):
                picks += [(k, f) for k, e in els.items() if e["kind"] == "product" for f in e["files"][:1]]
                extra += [{"name": k, "kind": "product", "file": None, "scene": c["scene"]}
                          for k, e in els.items() if e["kind"] == "product"]
            picks += [(k, f) for k, e in els.items() if e["kind"] == "look" for f in e["files"][:1]]
            d = out / "refs" / c["id"]
            d.mkdir(parents=True, exist_ok=True)
            for name, f in picks:
                dst = d / ("%s-%s" % (re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")[:30], Path(f).name))
                shutil.copy2(f, dst)
                c["refs"].append("refs/%s/%s" % (c["id"], dst.name))
            c["named_refs"].append("these files are the people, the place, the product and the look in the ad's style: "
                                   "use them as they are")
        # the swipe's own frame for each shot (the brief's make_list: "edit of swipe K01"), for framing and look only
        made = {m.get("shot"): re.findall(r"\bK\d{2,3}\b", str(m.get("picture") or "")) for m in (song or {}).get("make_list") or []}
        for c in sung:
            ks = []
            for p in parts.get(c["scene"], []):
                if p["scene"] == c.get("brief_scene") and p["where"] == c.get("where"):
                    for sh in p["shots"]:
                        if c["song_at"][0] - 0.01 <= sh["start"] < c["song_at"][1]:
                            ks += made.get(sh.get("id"), [])
            ks = list(dict.fromkeys(ks))
            for k in ks:
                f = frames / ("%s-mid.jpg" % k)
                if f.is_file():
                    dst = out / "refs" / c["id"] / ("swipe-%s-mid.jpg" % k)
                    shutil.copy2(f, dst)
                    c["refs"].append("refs/%s/%s" % (c["id"], dst.name))
            if ks:
                c["swipe_frames"] = ks
                c["named_refs"].append("swipe-K… : the original ad's frame for these shots, for framing and look only "
                                       "(never its people, product or words)")
        places = list(dict.fromkeys(c.get("where") for c in sung if c.get("where")))
        people = list(dict.fromkeys(w for c in sung for w in c.get("who") or []))
        rooms, builds, jutsu = _jutsu(out, _ws(), brand, places, [k for k, e in els.items() if e["kind"] == "product"],
                                      key=key, people=people)
        for c in sung:
            board = _print_board(out, c)
            if board:
                c["print_board"] = board
            c["start_words"] = _first_shot_words(c)
            if builds:
                rid = rooms.get(c.get("where"))
                c["room"] = rid
                c["start_picture"] = ("a 3D print (3d/JUTSU.md) in the project `%s`: room camera `CAM_loc_%s`, the first "
                                      "shot's people and product placed, printed with `%s`" % (
                                          jutsu.get("project"), rid, board or "the clip's sheets")) if rid \
                    else "a 3D print (3d/JUTSU.md): block %s at true size first, then the first shot" % c.get("where")
        # the end card: the song's last seconds over the real product photo (song-ad: the only real product pixels)
        b = sung[-1]["song_at"][1]
        if end - b > 0.5:
            real = []
            for k, e in els.items():
                if e["kind"] == "product":
                    real += _here("maker_elements")._real_product_photos(_ws(), brand, k)
            cid = "END-card"
            d = out / "refs" / cid
            d.mkdir(parents=True, exist_ok=True)
            refs = []
            for f in real[:3]:
                shutil.copy2(f, d / f.name)
                refs.append("refs/%s/%s" % (cid, f.name))
            card = {"id": cid, "scene": "END", "tool": "edit", "recipe": "", "copies": [], "swipe": [], "refs": refs,
                    "named_refs": ["the real product photos: the only real product pixels in the ad"], "same_people_as": None,
                    "continues": None, "return": "returned/%s_end-card.mp4" % key, "song_at": [round(b, 2), round(end, 2)],
                    "secs": round(end - b, 2), "lips": "none", "route": "card",
                    "make": "END CARD, made in the edit, not an AI clip: a slow camera push on the real product photo, the "
                            "song's last seconds under it (%.1f–%.1f s)" % (b, end)}
            clips.append(card)
            scenes.append({"n": len(scenes) + 1, "scene": "END", "section": "end card", "words": "", "on_screen": "",
                           "swipe": "", "status": "needs clips", "clips": [cid], "song_at": card["song_at"], "secs": card["secs"]})
    # a clip with no swipe frame of its own (a script-backed scene, e.g. a sung remake) carries its scene's own files in
    # the ad's style: the people's sheets, the set's print, the product's picture, the look (17 Nov, idea-12)
    if any(not c["refs"] for c in clips):
        try:
            ME = _here("maker_elements")
            per = {}
            for name, e in ME._from_scenes(n, brief["order"], ST.BRIEFS, W.parent).items():
                for sid in e["scenes"]:
                    per.setdefault(sid, []).extend((name, f) for f in e["files"][:2])
            for c in clips:
                if c["refs"]:
                    continue
                d = out / "refs" / c["id"]
                d.mkdir(parents=True, exist_ok=True)
                for name, f in per.get(c["scene"], []):
                    dst = d / ("%s-%s" % (re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")[:30], Path(f).name))
                    shutil.copy2(f, dst)
                    c["refs"].append("refs/%s/%s" % (c["id"], dst.name))
                c["named_refs"] = [x for x in c["named_refs"] if not x.endswith(("cast sheet", "style frame"))] + \
                    ["the scene's own files above (cast sheets, set print, product, look): use them as they are"]
        except Exception:  # noqa: BLE001 — the clip keeps its words; ELEMENTS.md still carries every file
            pass
    # a scene with nothing to make (no recipe, no swipe moment) is left out of the cut, never handed to the maker as a
    # clip to make (17 Nov, hand-off checklist: 0333 S24a reached the editor as a blank clip)
    held = {c["id"] for c in clips if c.get("hold")}
    if held:
        clips = [c for c in clips if c["id"] not in held]
        for row in scenes:
            if row.get("clips"):
                row["clips"] = [x for x in row["clips"] if x not in held]
                if not row["clips"] and not row.get("file"):
                    row["status"] = "left out: nothing to make"
        for cid in held:
            d = out / "refs" / cid
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()                       # the empty folder this build just made for it
    style = brief.get("style") or {}
    rules = _song_ad_rules(_ws()) if song else {}
    sfx = _hook_sfx(_ws(), out) if rules.get("hooks") else []
    cap_look, cap_font, cap_files = _caption_rules(_ws(), brand, "song-ad" if song else (rj.get("format_id") or ""), out) \
        if song else ({}, {}, [])
    try:
        th = thinking(key, W, rj, brief, brand, run)
    except Exception as e:  # noqa: BLE001 — the pack still goes out; the gap is said in it
        th = {"made_as": how, "hooks": [], "trail": [], "settings_note": "the thinking could not be gathered: %s" % str(e)[:160]}
    doc = {"schema": "maker-pack/v1", "key": key, "production": n, "run": run, "title": brief.get("title"), "brand": brand,
           "lane": lane, "lane_why": how["why"], "lane_by": how["by"],
           "style": style.get("id"), "deliver": brief.get("deliver"), "scenes": scenes, "clips": clips,
           # the thinking travels with the clips: the idea, the angle, the openings, the caption look and the pace the
           # format picks, and the decision trail (2026-11-18)
           "thinking": {k: v for k, v in th.items() if k != "trail_text"}, "hooks": th.get("hooks") or [],
           "caption_look": th.get("caption_look"), "pace": th.get("pace"), "trail": th.get("trail") or [],
           "studio": "http://127.0.0.1:8922/?brief=" + n}
    (out / "clips.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    nmade = sum(1 for r in scenes if r.get("file"))
    L = ["# %s · %s" % (brief.get("title"), key), "",
         ("A brief that needs %d clips made%s. %s Make each clip below, put it in `returned/` named exactly as listed, then "
          "cut the ad: every scene in the order below, your clips where they go, %s, the on-screen words as captions. Name the "
          "cut `%s-control.mp4`, 1080 x 1920, also in `returned/`.") % (
             len([c for c in clips if c.get("tool") != "edit"]),
             "".join([(" (%d scenes already made, in `made/`)" % nmade) if nmade else "",
                      (", and %s made in the edit, not by a model" % ", ".join(c["id"] for c in clips if c.get("tool") == "edit"))
                      if any(c.get("tool") == "edit" for c in clips) else ""]),
             "The song is made (`song/`)." if song else "The narration is read (`voice/`).",
             "the song under the whole cut" if song else "the `voice/` reads on their scenes", key), "",
         "- Style: **%s**%s" % (style.get("id") or "photoreal", _style_words(style)),
         "- Lane: %s. Why: %s" % (how.get("label") or LANES.get(lane, lane), how["why"]),
         "- No words burned into any clip; captions and on-screen text go on in the edit.",
         "- Each person is built once (ELEMENTS.md) and is the same in every clip they are in.", ""] + ([
         "- **A sung ad.** The song is `song/song.mp3`; every scene's lyric lines and its time on the song are below and in "
         "`song/timing.json`. Cut every clip to its time on the song (each clip runs to the next one's start, so the "
         "song is covered end to end). %s Read `song/LISTEN.md` first: it names any line that may be sung unclearly; "
         "`song/song.json` is the song gate's own record." % (
             "Every shot is silent under the song: nobody sings on camera." if parts and not any(
                 c.get("lips", "").startswith("sung on camera") for c in clips)
             else "A person singing on camera lip-syncs to their lines."),
         "- **Clip model:** %s (RUN.md carries the call for every clip, its prompt the recipe below word for word). %s" % (
             ", ".join(sorted({st.get("model_name") or st.get("higgsfield_model") or "" for st in (sheet or {}).get("steps") or []
                               if st.get("medium") == "video"} - {""})) or "the house clip model (MODEL-HOUSE.md)",
             "Every clip here is silent under the song, so it is the house clip model: MODEL-HOUSE.md's MiniMax H3 row is "
             "for a clip where someone sings on camera, and this ad has none." if not any(
                 c.get("lips", "").startswith("sung on camera") for c in clips) else
             "A clip where someone sings on camera is MODEL-HOUSE.md's song-ad clip model (MiniMax H3 at 2K); every other "
             "clip stays on the house clip model."),
         "- **Captions:** the sung lines, each on its time in `song/timing.json`%s%s%s." % (
             (" · look `%s`: %s, %s px, %s px %s outline, shadow %s, up to %s words, in the caption band, never on a face"
              % (cap_look.get("id"), str(cap_look.get("what") or "").rstrip(". "), cap_look.get("size_px"), cap_look.get("stroke_px"),
                 cap_look.get("stroke"), cap_look.get("shadow"), cap_look.get("max_words"))) if cap_look else "",
             (" · font: %s (%s)" % (cap_font.get("name"), ", ".join("`%s`" % f for f in cap_files) or cap_font.get("source")))
             if cap_font else "",
             (" · the brief: " + song["captions"]) if (song or {}).get("captions") else ""),
         "- **Versions:** %s. %s" % (rules.get("edit", {}).get("versions") or "the control",
             ("Hooks: %s; %d of them, cut from the clips you made (never new clips). Name them `%s-hook-1.mp4` … in "
              "`returned/`.%s" % (rules["hooks"].get("shape"), rules["hooks"].get("count") or 0, key,
                                  (" The bank sound effects for them are in `sfx/` (%s), from the house SFX bank "
                                   "(`components/video-production/banks/sfx/index.json`)." % ", ".join(sfx)) if sfx else
                                  " The SFX bank is `components/video-production/banks/sfx/index.json`, its files under "
                                  "`Shared Assets/banks/sfx/`.")) if rules.get("hooks") else ""),
         "- **Finish:** %s · 1080 x 1920 (upscale any clip the model returns smaller) · %s." % (
             rules.get("edit", {}).get("loudness") or "-14 LUFS, true peak -1 dBTP",
             rules.get("edit", {}).get("garbled_background_text") or "blur garbled background text"),
         ("- **Build the 3D sets first:** `3d/JUTSU.md` rebuilds this ad's rooms, cast stage and product in your own "
          "Higgsfield account and makes every start picture a 3D print." if (out / "3d" / "JUTSU.md").exists() else ""),
         "- **One set of instructions:** RUN.md and run.json carry these same clips as tool calls, in the same order and "
         "under the same names, each prompt this file's recipe word for word; this file's rules win if anything ever "
         "reads differently.",
         "- **Product:** in every clip the product is the banked picture in the ad's style (ELEMENTS.md); the real "
         "product photo is used only on the end card (its own clip, `END-card`, after the last line).", ""] if song else []) + [
         "## The ad, scene by scene", "",
         "Each row is one part of the story; the clips it needs are named in the Clips column (clip names are the only "
         "S-numbers to go by: ELEMENTS.md, RUN.md and the return names use them too).", "",
         "| # | What it is | Clips | Words | On screen | Status |", "|---|---|---|---|---|---|"]
    cell = lambda x: (x or "–").replace("|", "/").replace("\n", " / ")  # noqa: E731 — one table row per scene
    for r in scenes:
        L.append("| %d | %s | %s | %s | %s | %s |" % (r["n"], r["section"] or "", ", ".join(r.get("clips") or []) or "–",
                                                     cell(r["words"]), cell(r["on_screen"]),
                                                     ("made · `%s`" % r["file"]) if r.get("file") else "to make" if r.get("clips")
                                                     else r.get("status") or "–"))
    L += ["", "## Clips to make", ""]
    for c in clips:
        L += ["### %s · %.2f s" % (c["id"], c.get("secs") or 0), ""]
        if c.get("hold"):
            L += ["**HOLD:** " + c["hold"], ""]
        if c.get("make"):
            L += ["**How:** " + c["make"], ""]
        if c["recipe"]:
            L += ["**Recipe (exact):** " + c["recipe"], ""]
        elif not c.get("make"):
            L += ["**No recipe written:** remake the swipe moment below with our product and our person, in the ad's style.", ""]
        for x in c["swipe"]:
            L.append("- Swipe %s (%.2f s): %s%s" % (x["k"], x["seconds"] or 0, x["does"] or "", (" · text: " + x["text"]) if x.get("text") else ""))
        if c.get("song_at"):
            L.append("- On the song: %.2f–%.2f s · %s" % (c["song_at"][0], c["song_at"][1], c.get("lips") or ""))
        if c.get("start_picture"):
            L.append("- Start picture: " + c["start_picture"])
        if c.get("start_words"):
            L.append("- Start picture words: " + c["start_words"].replace("\n", " · "))
        if c["refs"]:
            L.append(("- Swipe frames: " if c.get("copies") else "- Files: ") + ", ".join("`%s`" % r for r in c["refs"]))
        if c["named_refs"]:
            L.append("- Also use: " + ", ".join(c["named_refs"]))
        if c.get("our_cut"):
            L.append("- Our footage cut of this scene, for timing and framing only (do not use it: wrong person, burned-in words): `%s`" % c["our_cut"])
        if c["same_people_as"]:
            L.append("- Same people and place as `%s`" % c["same_people_as"])
        if c["continues"]:
            L.append("- Picks up where `%s` ends" % c["continues"])
        L += ["- Return: `%s`" % c["return"], ""]
    L += [thinking_md(th)]
    (out / "CLIPS.md").write_text("\n".join(L) + "\n")
    _brief_and_elements(out, W, key, brand, frames, production=n, order=brief["order"], extra=extra, clips=clips)
    # every clip carries every reference it needs and its one full prompt (VIDEO-RULINGS V59): once here for the clip
    # list, once more below when the run sheet's own steps are in the folder
    SP = _here("scene_packet")
    SP.apply(out, _ws())
    TL = _here("maker_timeline")                 # editors work on timelines, not instruction lists (owner, 16 Nov 2026)
    TL.build(out)
    EF = _here("maker_editfiles")                # every hand-off carries the editor's own working files (owner, 16 Nov)
    EF.build(out)
    if "_brief-" in key:                        # numbered: the standard run sheet (BRIEF.md, RUN.md, run.json, refs/) the
        try:                                    # maker's own tools read (components/briefs/runsheet.py, its public door)
            sys.path.insert(0, str(_ws() / "components" / "briefs"))
            import runsheet as RS
            RS.pack(sheet or RS.build(key, brand=brand), folder=out, role="video-editor")
            _voice_into_sheet(out, RS)
            _clips_into_sheet(out, RS)
            if SP.apply(out, _ws()):
                (out / "RUN.md").write_text(RS.render_md(json.loads((out / "run.json").read_text())))
            _into_brief(out, th)                # BRIEF.md says why the ad is built this way, not only what to make
            if (out / "RUN-SHEET-MISSING.txt").exists():
                (out / "RUN-SHEET-MISSING.txt").unlink()   # this build's own note from an earlier failed pack, now spent
        except (Exception, SystemExit) as e:  # noqa: BLE001 — said in the pack, never a silent gap
            (out / "RUN-SHEET-MISSING.txt").write_text("The standard run sheet could not be written: %s\n" % str(e)[:400])
    try:
        _front_page(out, key, doc, song, (json.loads((out / "run.json").read_text()).get("steps")
                                          if (out / "run.json").exists() else []))
    except Exception as e:  # noqa: BLE001 — a front page that cannot be written says why, in its place
        (out / "handoff.md").write_text("# %s\n\nThe front page could not be written: %s. Read CLIPS.md first.\n" % (key, str(e)[:300]))
    link, web, sharing = None, None, None
    if drive and UNNUMBERED.search(key):     # an idea is not the maker's yet: packed here, sent once the register numbers it
        drive = False
        (out / "DRIVE-NOTE.txt").write_text("Not sent: %s has no brief number yet. Number it, then build the pack "
                                            "again.\n" % key)
    if drive:
        # onto the Drive through gdrive-creator with the person's own key (builder card rule 4), the same path below
        # Shared Assets/; 17 Nov: the Mac's own Drive sync left a copied folder un-uploaded, so the editor never saw it
        parts = ["runs", "handoffs", "video-editor", brand, key]
        try:
            sys.path.insert(0, str(_ws() / "components" / "gdrive-creator"))
            from gdrive_creator import engine as E, reach
            import time
            for attempt in range(3):            # a write that times out is tried again before falling back (17 Nov)
                try:
                    svc = E.service()
                    dest = reach.folder_id(parts, svc, make=True, find_engine=lambda: E)
                    E.mirror_tree(str(out), dest, svc)
                    break
                except Exception:  # noqa: BLE001
                    if attempt == 2:
                        raise
                    time.sleep(10)
            web = "https://drive.google.com/drive/folders/" + dest
            link = "Shared Assets/" + "/".join(parts)
            sharing = _link_share(dest, svc, E)
            if (out / "DRIVE-NOTE.txt").exists():
                (out / "DRIVE-NOTE.txt").unlink()          # an earlier fallback's note, spent now the Drive tool wrote it
        except Exception as e:  # noqa: BLE001 — the mounted Drive copy is the fallback, said in the record
            m = _drive_root()
            if m:
                dst = Path(m) / "/".join(parts)
                shutil.copytree(out, dst, dirs_exist_ok=True)
                link = str(dst)
            (out / "DRIVE-NOTE.txt").write_text("Uploaded through the Mac's Drive copy, not the Drive tool: %s\n" % str(e)[:300])
    return {"key": key, "folder": str(out), "drive": link, "web": web, "sharing": sharing, "clips": len(clips),
            "made": sum(1 for r in scenes if r.get("file")), "scenes": len(scenes), "check": _check(out)}


def _check(out):
    """The hand-off checklist over the finished pack (components/video-edit/handoff_check.py, its public door): every
    line pass/fail, kept in the Studio's hand-off record so a gap is seen before anyone waits on the maker."""
    try:
        import subprocess
        r = subprocess.run([sys.executable, str(_ws() / "components" / "video-edit" / "handoff_check.py"), out.name, "--json"],
                           capture_output=True, text=True, timeout=180, env=dict(os.environ, VIDEO_STUDIO_DATA=str(Path(ST.BRIEFS).parent)))
        res = json.loads(r.stdout)[0]
        return {"passed": res["passed"], "total": res["total"],
                "fails": [c["group"] + " · " + c["check"] + (" — " + c["evidence"] if c["evidence"] else "")
                          for c in res["checks"] if not c["ok"]]}
    except Exception as e:  # noqa: BLE001 — a check that could not run says so; it never stops the hand-off
        return {"passed": None, "total": None, "fails": ["the checklist could not run: %s" % str(e)[:160]]}


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--productions" in a:
        ST.set_productions(a[a.index("--productions") + 1])
    print(json.dumps(build(a[0], drive="--no-drive" not in a), indent=1))
