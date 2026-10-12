#!/usr/bin/env python3
"""cutsheet.py — the cut sheet: the one file that IS the edit, and the gate it
has to pass before anything renders.

The model (or the auto cut) decides; this file checks; compose.py executes.
Nothing else knows what is in the video.

    python3 machine/cutsheet.py check <cutsheet.json>

Shape (every time is seconds on the FINAL timeline unless it says source):

    meta      brand, label, format, style_id, width, height, fps
    controls  the dials this edit ran under (defaults.json + the run's overrides)
    voice     {src, start, volume_db} | null     a voiceover piece only. A TALKING clip carries its
                                                 own sound (talks: true, volume_db set) — never both
    voice_cuts [{id, src, start, duration, source_start, volume_db}]   a B-roll scene's slice of the voice read, cut at its pauses
    music     {src, start, volume_db} | null
    sfx       [{id, src, at, volume_db, for}]    `for` = the clip or word it belongs to
    picture   [{id, roll: "a"|"b", src, start, duration, source_start, scene, why,
                volume_db|null, still: bool}]    a-roll below, b-roll covers it
    captions  {look, words: [{text, start, end}], fixes: [{from, to}]}
    overlays  [{id, kind: "hook"|"label"|"end-card", text, start, duration, y_pct}]

Every element (tools/video-production/ELEMENTS.md, added 2026-09-23 by assemble.py):

    picture[i].kind   talking · broll · card · screen · split · greenscreen · endcard, with its data:
                      card {lines, plan_lines, lands_on, lands_at}   screen {surface, lines, plan_lines, lands_on}
                      split {left, right, layout, labels}            greenscreen {background, layout}
                      endcard {offer_lines, plan_offer_lines, cta, guarantee}
                      and section (the doctrine's id) · priority · opens · claims
    layers    {lower_thirds [{scene, name, title, start, duration, zone}],
               annotations [{scene, kind, target, at_words, place, start, duration, follow?}],
                  target "face"|"subject" (or {follow: "face"}) follows the person: follow {by, keys [{t, x_pct, y_pct}]}
               platform_ui [{scene, kind, style, text, handle, start, duration, zone}],
               icons [{scene, icon, zone, at_words, size, text, value, start, duration}],
               transitions [{after_scene, kind}], disclaimers [{claim, text, start, duration, zone}]}
              every zone is an id in looks/placement.json; fonts are ids in looks/fonts.json;
              placement [{layer, id, asked, zone, why}] · face_blind [scene] — what placement.py did
    pauses    [{clip, length, action: cut|kept, at | start/end, source}]   every mid-clip pause the trim cut or kept (live timeline)
    captions.words[i].heard   what the transcriber wrote where the script's spelling is shown instead (spelling.py)
    warnings(sheet)  what renders but not as asked (a font or icon not fetched, a face-blind scene)
    music     + tempo_bpm, source_start, duck {under_db, gap_db, points}
    room_tone [{id, src, start, duration, volume_db}]
    hooks [{id, text, opener_scene}] · versions {hooks, cutdowns, ratios: ["9x16"], cover}
    grade · mix {lufs, true_peak_db} · name {...naming fields} · compliance · unmade · elements

No brand name lives in this file.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent


def load(name: str) -> dict:
    return json.loads((TOOL / name).read_text())


def probe_seconds(path: Path) -> float | None:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, check=True).stdout.strip()
        return float(out)
    except Exception:
        return None


def end_of(sheet: dict) -> float:
    ends = [c["start"] + c["duration"] for c in sheet.get("picture", [])]
    return round(max(ends), 3) if ends else 0.0


def check(sheet: dict, root: Path, probe=probe_seconds) -> list[str]:
    """Every reason this sheet may not render. Empty list = green."""
    red: list[str] = []
    meta = sheet.get("meta") or {}
    for f in ("brand", "label", "width", "height", "fps"):
        if not meta.get(f):
            red.append(f"meta.{f} is missing")

    looks = {r["id"] for r in load("looks/bank.json")["looks"]}
    transitions = {r["id"] for r in load("looks/transitions.json")["transitions"]}
    controls = sheet.get("controls") or {}
    t = (controls.get("transition") or {}).get("value", "cut")
    if t not in transitions:
        red.append(f"controls.transition `{t}` is not a transition — known: {', '.join(sorted(transitions))}")

    picture = sheet.get("picture") or []
    if not picture:
        red.append("picture is empty — there is no video")
    ids = set()
    for i, c in enumerate(picture):
        at = f"picture[{i}] ({c.get('id', '?')})"
        if c.get("id") in ids:
            red.append(f"{at}: id used twice")
        ids.add(c.get("id"))
        if c.get("roll") not in ("a", "b"):
            red.append(f"{at}: roll must be 'a' or 'b'")
        if not c.get("why"):
            red.append(f"{at}: no `why` — every cut says what it is for")
        src = root / str(c.get("src", ""))
        if not src.is_file():
            red.append(f"{at}: file not found — {c.get('src')}")
            continue
        if c.get("duration", 0) <= 0:
            red.append(f"{at}: duration must be above zero")
        if not c.get("still"):
            have = probe(src)
            need = c.get("source_start", 0) + c.get("duration", 0)
            if have is not None and need > have + 0.05:
                red.append(f"{at}: trim runs past the source ({need:.2f}s asked, {have:.2f}s there)")

    # no hole in the picture: a-roll + b-roll together cover 0 → end
    end = end_of(sheet)
    spans = sorted((c["start"], c["start"] + c["duration"]) for c in picture if c.get("duration", 0) > 0)
    cursor = 0.0
    for s, e in spans:
        if s > cursor + 0.04:
            red.append(f"picture has a hole from {cursor:.2f}s to {s:.2f}s — nothing is on screen")
        cursor = max(cursor, e)
    a_spans = sorted((x["start"], x["start"] + x["duration"]) for x in picture if x.get("roll") == "a")
    for c in picture:
        if c.get("roll") == "b":
            at, stop = c["start"], c["start"] + c["duration"]
            under = a_spans + sorted((v["start"], v["start"] + v["duration"]) for v in sheet.get("voice_cuts") or [])
            for s0, e0 in sorted(under):  # a-roll (or the voice it covers) may be several cuts back to back
                if s0 <= at + 0.04 and e0 > at:
                    at = e0
            if at < stop - 0.04:
                red.append(f"picture ({c.get('id')}): b-roll has nothing under it from {at:.2f}s — if it carries the moment alone, label it 'a'")

    voice = sheet.get("voice")
    talking = [x for x in picture if x.get("talks")]
    for x in talking:
        if x.get("volume_db") is None:
            red.append(f"picture ({x.get('id')}): a talking clip is muted — it must carry its own sound, or the lips will not match")
    vcuts = sheet.get("voice_cuts") or []
    for i, v in enumerate(vcuts):
        if not (root / str(v.get("src", ""))).is_file():
            red.append(f"voice_cuts[{i}]: file not found — {v.get('src')}")
        for x in talking:
            if v["start"] < x["start"] + x["duration"] - 0.04 and x["start"] < v["start"] + v["duration"] - 0.04:
                red.append(f"two voices at {max(v['start'], x['start']):.2f}s: voice cut {v.get('id')} runs while {x.get('id')} is talking")
    if voice and talking:
        red.append("two voices: a separate voice track AND talking clips with their own sound — a talking clip's own sound is the voice")
    if not voice and not talking and not vcuts:
        red.append("no voice: neither a voice track nor a talking clip")
    if voice:
        if not (root / str(voice.get("src", ""))).is_file():
            red.append("voice: the approved voice track is missing")
        else:
            have = probe(root / voice["src"])
            if voice.get("duration"):
                have = min(have or voice["duration"], voice["duration"])
            if have is not None and voice.get("start", 0) + have > end + 0.5:
                red.append(f"voice runs {voice.get('start', 0) + have - end:.2f}s past the last picture")
    music = sheet.get("music")
    if music:
        if not (root / str(music.get("src", ""))).is_file():
            red.append(f"music: file not found — {music.get('src')}")
        if music.get("volume_db", -18) > (voice or {}).get("volume_db", 0) - 10:
            red.append("music is less than 10 dB under the voice — it will fight the words")
    for i, s in enumerate(sheet.get("sfx") or []):
        if not (root / str(s.get("src", ""))).is_file():
            red.append(f"sfx[{i}]: file not found — {s.get('src')}")
        if not s.get("for"):
            red.append(f"sfx[{i}]: no `for` — a sound belongs to a clip or a word")

    caps = sheet.get("captions") or {}
    if (controls.get("captions") or {}).get("value", "on") == "on":
        look = caps.get("look")
        if not (isinstance(look, str) and look in looks) and not (isinstance(look, dict) and look.get("id") == "match-swipe"):
            red.append(f"captions.look `{look}` is not a caption look — known: {', '.join(sorted(looks))}, or a match-swipe look")
        elif isinstance(look, dict):
            red += look_red(look, "captions.look (match-swipe)")
        for sc, z in (caps.get("zones") or {}).items():
            if z.get("zone") not in zone_ids():
                red.append(f"captions.zones[{sc}]: zone `{z.get('zone')}` is not a zone — known: {', '.join(zone_ids())}")
        words = caps.get("words") or []
        if not words:
            red.append("captions are on but there are no timed words")
        last = -1.0
        for i, w in enumerate(words):
            if w["end"] <= w["start"]:
                red.append(f"captions.words[{i}] `{w['text']}`: ends before it starts")
            if w["start"] < last - 0.02:
                red.append(f"captions.words[{i}] `{w['text']}`: out of order")
            if w["end"] > end + 0.05:
                red.append(f"captions.words[{i}] `{w['text']}`: lands after the video ends")
            last = w["start"]

    safe = controls.get("safe_zone") or {}
    for i, o in enumerate(sheet.get("overlays") or []):
        if not o.get("text") and o.get("kind") != "end-card":
            red.append(f"overlays[{i}]: no text")
        y = o.get("y_pct")
        if o.get("zone"):
            if o["zone"] not in zone_ids():
                red.append(f"overlays[{i}]: zone `{o['zone']}` is not a zone — known: {', '.join(zone_ids())}")
        elif y is not None and (y < safe.get("top_pct", 12) or y > 100 - safe.get("bottom_pct", 25)):
            red.append(f"overlays[{i}]: sits at {y}% — inside the part of the frame the app's buttons cover")
        if o.get("start", 0) + o.get("duration", 0) > end + 0.05:
            red.append(f"overlays[{i}]: runs past the end")
    red += check_elements(sheet, root, probe, end)
    red += settings_red()
    return red


KINDS = ("talking", "broll", "card", "screen", "split", "greenscreen", "endcard")
SURFACES = ("review", "comment", "dm", "site", "order", "search")
LAYOUTS = {"split": ("side", "top-bottom", "wipe"), "greenscreen": ("cutout", "pip")}
ANNOTATIONS = ("arrow", "circle", "underline", "highlight")
UI = load("looks/platform_ui.json")
UI_STYLES = {x["id"]: x for x in UI["styles"]}
PLATFORM_UI = tuple(UI["kinds"])  # comment_reply · ig_comment · youtube_comment · x_post · imessage · whatsapp · dm_generic · stitch · duet · search · likes · views · review


def zone_ids() -> list[str]:
    return [z["id"] for z in load("looks/placement.json")["zones"]]


def font_ids() -> list[str]:
    return [f["id"] for f in load("looks/fonts.json")["fonts"]]


def look_red(look: dict, at: str) -> list[str]:
    red = []
    if look.get("font") not in font_ids():
        red.append(f"{at}: font `{look.get('font')}` is not in looks/fonts.json — a look names a font id, never a CSS stack")
    if look.get("zone") and look["zone"] not in zone_ids():
        red.append(f"{at}: zone `{look['zone']}` is not a zone — known: {', '.join(zone_ids())}")
    return red


def settings_red() -> list[str]:
    """The settings themselves: every font and zone they name exists, and every zone
    clears the platforms' buttons and sits in the 4:5 content band."""
    import placement as P
    red, F, Z = [], set(font_ids()), set(zone_ids())
    box = P.safe_box(None)
    for z in load("looks/placement.json")["zones"]:
        if not P.zone_clear(z, box):
            red.append(f"looks/placement.json `{z['id']}`: crosses the platforms' buttons or leaves the 4:5 content band (safe box {box})")
    for r in load("looks/bank.json")["looks"]:
        red += look_red(r, f"looks/bank.json `{r['id']}`")
    for k, v in load("looks/layers.json").items():
        if isinstance(v, dict):
            if v.get("font") and v["font"] not in F:
                red.append(f"looks/layers.json {k}.font `{v['font']}` is not in looks/fonts.json")
            if v.get("zone") and v["zone"] not in Z:
                red.append(f"looks/layers.json {k}.zone `{v['zone']}` is not a zone")
    ui = load("looks/platform_ui.json")
    ids = {s["id"]: s for s in ui["styles"]}
    for kind, row in ui["kinds"].items():
        if (ids.get(row["default"]) or {}).get("kind") != kind:
            red.append(f"looks/platform_ui.json kind `{kind}`: default style `{row['default']}` is not a `{kind}` style")
    for s_ in ui["styles"]:
        if s_["draw"].get("font") not in F:
            red.append(f"looks/platform_ui.json `{s_['id']}`: font `{s_['draw'].get('font')}` is not in looks/fonts.json")
        if s_.get("zone") not in Z:
            red.append(f"looks/platform_ui.json `{s_['id']}`: zone `{s_.get('zone')}` is not a zone")
    return red


def warnings(sheet: dict) -> list[str]:
    """What renders, but not as asked: a font or icon not fetched yet (drawn in its
    stand-in), a scene whose text is placed without knowing where the face is, and
    every layer the edit moved off a face (with why)."""
    import fonts as FT
    import icons as IC
    out, used = [], set()
    look = (sheet.get("captions") or {}).get("look")
    if isinstance(look, str):
        look = next((r for r in load("looks/bank.json")["looks"] if r["id"] == look), {})
    if (look or {}).get("font"):
        used.add(look["font"])
    ST = load("looks/layers.json")
    used |= {v["font"] for v in ST.values() if isinstance(v, dict) and v.get("font")}
    used |= {ST.get("font"), ST.get("font_heavy")} - {None}
    styles = {s_["id"]: s_ for s_ in load("looks/platform_ui.json")["styles"]}
    for r in (sheet.get("layers") or {}).get("platform_ui") or []:
        if r.get("style") in styles:
            used.add(styles[r["style"]]["draw"]["font"])
    for f in sorted(x for x in used if x in font_ids()):
        _, w = FT.resolve(f)
        if w:
            out.append(w)
    for r in (sheet.get("layers") or {}).get("icons") or []:
        if IC.status(r.get("icon")) == "missing":
            out.append(f"icon `{r.get('icon')}` is not fetched yet — drawn as the plain character until `python3 machine/icons.py install {r.get('icon')}` is run (not the same on every machine)")
    for c in sheet.get("picture") or []:  # a cut-out scene with no cut-out made: the presenter shows whole, box and all
        if c.get("kind") == "greenscreen" and (c.get("greenscreen") or {}).get("layout") == "cutout" and not (c.get("cutout") or {}).get("webm"):
            out.append(f"{c['id']}: the presenter is not cut out yet (no helpers venv, or a dry run) — she shows whole, background and all, over the plate")
    for r in (sheet.get("layers") or {}).get("annotations") or []:
        f = r.get("follow") or {}
        if f and not f.get("by"):
            out.append(f"annotation {r.get('id')} ({r.get('kind')}) should follow the {r.get('target')} but nothing tracks the person there — drawn fixed at `{f.get('fell_back_to')}`")
    for n in (sheet.get("captions") or {}).get("spelling") or []:
        out.append(f"captions: {n}")
    for sc in sheet.get("face_blind") or []:
        out.append(f"placement is face-blind for {sc} — production has not marked where the person is (subject_box), so text may sit on the face")
    for m in sheet.get("placement") or []:
        out.append(f"moved: {m['layer']} {m.get('id') or ''} — {m['why']}")
    return out
CUTDOWNS = (15, 30, 60)
RATIOS = ("9x16",)  # 9:16 only — the owner, 2026-09-23: "I do not want 4:5 or 1:1 videos at all"


def doctrine_sections() -> list[str]:
    """The section ids, read from the marketing doctrine every machine binds —
    never a list kept here."""
    for p in [TOOL, *TOOL.parents]:
        f = p / "components" / "marketing-doctrine" / "frameworks.json"
        if f.exists():
            d = json.loads(f.read_text())
            return [r["id"] for r in d.get("sections") or [] if isinstance(r, dict) and r.get("id")]
    return []


def check_elements(sheet: dict, root: Path, probe, end: float) -> list[str]:
    """The gate for every element the edit assembles. Red names the field."""
    red: list[str] = []
    controls = sheet.get("controls") or {}
    safe = controls.get("safe_zone") or {}
    top, bottom = safe.get("top_pct", 12), 100 - safe.get("bottom_pct", 25)
    elements = bool(sheet.get("elements"))
    picture = sheet.get("picture") or []
    scenes = []
    for c in picture:
        if (c.get("scene") or c["id"]) not in scenes:
            scenes.append(c.get("scene") or c["id"])
    order = sorted(scenes, key=lambda sc: min(x["start"] for x in picture if (x.get("scene") or x["id"]) == sc))

    for u in sheet.get("unmade") or []:
        red.append(f"unmade: {u} — production makes it (or pulls it from its bank); the edit only assembles")

    # every part of the edit names the doctrine section it is — the swap unit for variations
    if elements:
        ids = doctrine_sections()
        for c in picture:
            sec = c.get("section")
            if not sec:
                red.append(f"picture ({c.get('id')}): no section — every part of the edit names the doctrine section it represents")
            elif ids and sec not in ids:
                red.append(f"picture ({c.get('id')}): section `{sec}` is not a doctrine section — known: {', '.join(ids)}")

    for c in picture:
        at = f"picture ({c.get('id')})"
        k = c.get("kind")
        if k is None:
            continue
        if k not in KINDS:
            red.append(f"{at}: kind `{k}` is not a scene kind — known: {', '.join(KINDS)}")
            continue
        d = c.get(k) if k not in ("talking", "broll") else {}
        if k not in ("talking", "broll") and not isinstance(d, dict):
            red.append(f"{at}: a {k} scene with no `{k}` data")
            continue
        if k in ("card", "screen"):
            lines = d.get("lines") or []
            if not lines or not all(str(x).strip() for x in lines):
                red.append(f"{at}: {k}.lines is empty — the words are the plan's, and there are none")
            if "plan_lines" not in d:
                red.append(f"{at}: {k}.plan_lines is missing — nothing to hold the set words to")
            elif list(lines) != list(d["plan_lines"]):
                red.append(f"{at}: {k}.lines do not match the plan word for word — set {lines!r}, the plan says {d['plan_lines']!r}")
            if d.get("lands_on_unheard"):
                red.append(f"{at}: {k} lands on `{d.get('lands_on')}` but those words are never said")
        if k == "screen" and d.get("surface") not in SURFACES:
            red.append(f"{at}: screen.surface `{d.get('surface')}` is not a surface — known: {', '.join(SURFACES)}")
        if k in LAYOUTS and d.get("layout") not in LAYOUTS[k]:
            red.append(f"{at}: {k}.layout `{d.get('layout')}` is not a layout — known: {', '.join(LAYOUTS[k])}")
        if k == "split":
            for side in ("left", "right"):
                if not d.get(side) or not (root / str(d[side])).is_file():
                    red.append(f"{at}: split.{side} not found — {d.get(side)}")
            labels = d.get("labels") or []
            if len(labels) > 2 or not all(isinstance(x, str) and x.strip() for x in labels):
                red.append(f"{at}: split.labels must be up to two words-on-a-side, got {labels!r}")
        if k == "greenscreen":
            if not d.get("background") or not (root / str(d["background"])).is_file():
                red.append(f"{at}: greenscreen.background not found — {d.get('background')}")
            if not c.get("talks"):
                red.append(f"{at}: a greenscreen scene is the presenter talking — this clip does not talk")
        if k == "endcard":
            offer = d.get("offer_lines") or []
            if not offer:
                red.append(f"{at}: endcard.offer_lines is empty — the words come from the offer bank only")
            elif "plan_offer_lines" in d and list(offer) != list(d["plan_offer_lines"]):
                red.append(f"{at}: endcard.offer_lines do not match the plan word for word")
            if not str(d.get("cta") or "").strip():
                red.append(f"{at}: endcard.cta is missing")
            if not str(d.get("guarantee") or "").strip():
                red.append(f"{at}: endcard.guarantee is missing — write \"none\" in the plan when the offer has none")

    L = sheet.get("layers") or {}

    def timed(row: dict, at: str) -> None:
        if row.get("start") is None or row.get("duration") is None:
            red.append(f"{at}: never placed on the clock — its scene `{row.get('scene')}` is not in the cut")
            return
        if row["start"] < -0.01 or row["start"] + row["duration"] > end + 0.05:
            red.append(f"{at}: runs outside the video ({row['start']:.2f}s + {row['duration']:.2f}s, the video is {end:.2f}s)")
        if row["duration"] <= 0:
            red.append(f"{at}: duration must be above zero")

    def safe_y(row: dict, at: str) -> None:
        y = row.get("y_pct")
        if y is not None and (y < top or y > bottom):
            red.append(f"{at}: sits at {y}% — inside the part of the frame the app's buttons cover")

    Z = zone_ids()

    def zoned(row: dict, at: str) -> None:
        """A text layer names a zone (looks/placement.json); a legacy row with only a y_pct is held to the safe box."""
        if row.get("zone") is not None:
            if row["zone"] not in Z:
                red.append(f"{at}: zone `{row['zone']}` is not a zone — known: {', '.join(Z)}")
        else:
            safe_y(row, at)

    for i, r in enumerate(L.get("lower_thirds") or []):
        at = f"layers.lower_thirds[{i}]"
        if not str(r.get("name") or "").strip():
            red.append(f"{at}: no name")
        timed(r, at); zoned(r, at)
    for i, r in enumerate(L.get("annotations") or []):
        at = f"layers.annotations[{i}]"
        if r.get("kind") not in ANNOTATIONS:
            red.append(f"{at}: kind `{r.get('kind')}` — known: {', '.join(ANNOTATIONS)}")
        if not r.get("place"):
            red.append(f"{at}: target `{r.get('target')}` is not a place on the frame — name an anchor (looks/layers.json) or {{x_pct, y_pct}}")
        if r.get("at_words") and r.get("start") is None and r.get("scene") in scenes:
            red.append(f"{at}: at_words `{r['at_words']}` are never said in {r.get('scene')}")
        else:
            timed(r, at)
        if r.get("place"):
            safe_y(r["place"], at)
    for i, r in enumerate(L.get("platform_ui") or []):
        at = f"layers.platform_ui[{i}]"
        k = r.get("kind")
        if k not in PLATFORM_UI:
            red.append(f"{at}: kind `{k}` — known: {', '.join(PLATFORM_UI)}")
        else:
            for need in UI["kinds"][k]["needs"]:
                if not str(r.get(need) or "").strip():
                    red.append(f"{at}: a {k} with no {need}")
            st = r.get("style")
            if st is not None and st not in UI_STYLES:
                red.append(f"{at}: style `{st}` is not a platform-UI style — known for {k}: {', '.join(i for i, x in UI_STYLES.items() if x['kind'] == k)}")
            elif st is not None and UI_STYLES[st]["kind"] != k:
                red.append(f"{at}: style `{st}` draws a {UI_STYLES[st]['kind']}, not a {k}")
        timed(r, at); zoned(r, at)
    T = {r["id"]: r for r in load("looks/transitions.json")["transitions"]}
    known_t = {i for i, r in T.items() if r.get("drawn") and r.get("type", "transition") == "transition"}
    for i, r in enumerate(L.get("transitions") or []):
        at = f"layers.transitions[{i}]"
        if r.get("kind") in T and r["kind"] not in known_t:
            red.append(f"{at}: kind `{r['kind']}` is in the catalogue but " + ("is a move inside one shot, not a hand-off" if T[r["kind"]].get("type") == "move" else f"not installed — registry {T[r['kind']].get('registry')}") + f"; drawn today: {', '.join(sorted(known_t))}")
        elif r.get("kind") not in known_t:
            red.append(f"{at}: kind `{r.get('kind')}` is not a transition — known: {', '.join(sorted(known_t))}")
        if r.get("after_scene") not in order:
            red.append(f"{at}: after_scene `{r.get('after_scene')}` is not in the cut")
        elif r.get("after_scene") == order[-1]:
            red.append(f"{at}: after_scene `{r.get('after_scene')}` is the last scene — there is nothing to hand off to")
        gl = (T.get(r.get("kind")) or {}).get("glsl")
        if gl and not (TOOL / gl).is_file():
            red.append(f"{at}: kind `{r['kind']}` is a GL transition and its shader {gl} is missing")
    import registry as RG  # a HyperFrames registry block named by id: only once installed (machine/registry.py install <id>)
    for i, r in enumerate(L.get("registry") or []):
        at = f"layers.registry[{i}]"
        why = RG.gate(str(r.get("id")))
        if why:
            red.append(f"{at}: {why}")
        elif (RG.row(r["id"]) or {}).get("category") != "block":
            red.append(f"{at}: `{r['id']}` is a component — components are pasted into a page, the edit wires blocks only")
        timed(r, at)
    comp = sheet.get("compliance") or {}
    if comp.get("claims") and not comp.get("file"):
        red.append(f"disclaimers: the piece makes {len(comp['claims'])} claim(s) ({', '.join(comp['claims'])}) and brands/{(sheet.get('meta') or {}).get('brand')}/compliance.json does not exist — the brand's disclaimers are written there, not here")
    elif comp.get("unfilled"):
        red.append(f"disclaimers: no disclaimer in compliance.json for claim(s) {', '.join(comp['unfilled'])}")
    for i, r in enumerate(L.get("disclaimers") or []):
        at = f"layers.disclaimers[{i}]"
        if not str(r.get("text") or "").strip():
            red.append(f"{at}: no text")
        timed(r, at); zoned(r, at)
    ICONS = {r["id"]: r for r in load("looks/icons.json")["icons"]}
    sizes = load("looks/icons.json")["sizes"]
    for i, r in enumerate(L.get("icons") or []):
        at = f"layers.icons[{i}]"
        ic = ICONS.get(r.get("icon"))
        if not ic:
            red.append(f"{at}: icon `{r.get('icon')}` is not in looks/icons.json — known: {', '.join(sorted(ICONS))}")
        else:
            if ic.get("takes_text") and not str(r.get("text") or "").strip():
                red.append(f"{at}: a {ic['id']} carries words — `text` is empty")
            if ic.get("takes_value") and not isinstance(r.get("value"), (int, float)):
                red.append(f"{at}: a {ic['id']} needs a number in `value`")
        if r.get("size") not in sizes and not isinstance(r.get("size"), (int, float)):
            red.append(f"{at}: size `{r.get('size')}` — known: {', '.join(sizes)} or a pixel number")
        if r.get("at_words") and r.get("start") is None and r.get("scene") in scenes:
            red.append(f"{at}: at_words `{r['at_words']}` are never said in {r.get('scene')}")
        else:
            timed(r, at)
        zoned(r, at)

    ids = [h.get("id") for h in sheet.get("hooks") or []]
    if len(ids) != len(set(ids)):
        red.append("hooks: an id is used twice")
    for i, h in enumerate(sheet.get("hooks") or []):
        if not str(h.get("text") or "").strip():
            red.append(f"hooks[{i}]: no text")
        if h.get("opener_scene") and h["opener_scene"] not in scenes:
            red.append(f"hooks[{i}]: opener_scene `{h['opener_scene']}` is not in the cut")
    if elements:
        for o in sheet.get("overlays") or []:
            if o.get("kind") == "hook" and o.get("start", 0) > 0.04:
                red.append(f"overlays ({o.get('id')}): the opening hook starts at {o['start']:.2f}s — it is on screen from frame one")

    music = sheet.get("music")
    if music and elements:
        if not music.get("tempo_bpm"):
            red.append("music: no tempo_bpm on its bank row — the music is cut to the beat, so the row must carry it")
        if (music.get("duck") or {}).get("under_db", 0) < 18:
            red.append(f"music: ducked {(music.get('duck') or {}).get('under_db')} dB under the voice — the rule is 18")
        have = probe(root / str(music.get("src", ""))) if (root / str(music.get("src", ""))).is_file() else None
        if have is not None and music.get("source_start", 0) + (music.get("duration") or end) > have + 0.05:
            red.append(f"music: the track is {have:.2f}s and the piece needs {music.get('source_start', 0) + (music.get('duration') or end):.2f}s of it")
    for i, x in enumerate(sheet.get("sfx") or []):
        if x.get("at") is None:
            red.append(f"sfx[{i}] ({x.get('cue') or x.get('id')}): never lands — `{x.get('at_words') or x.get('scene')}` is not in the cut")
        elif not (0 <= x["at"] <= end + 0.05):
            red.append(f"sfx[{i}]: lands at {x['at']:.2f}s, outside the video")
    need = sheet.get("room_tone_needed") or {}
    if elements and (need.get("joins") or need.get("spans")) and not sheet.get("room_tone"):
        red.append(f"room tone: {need.get('joins', 0)} trimmed join(s) and {need.get('spans', 0)} silent span(s) and no room-tone bed — the SFX bank's room-tone rows")
    for i, r in enumerate(sheet.get("room_tone") or []):
        if not (root / str(r.get("src", ""))).is_file():
            red.append(f"room_tone[{i}]: file not found — {r.get('src')}")

    v = sheet.get("versions") or {}
    for n in v.get("cutdowns") or []:
        if n not in CUTDOWNS:
            red.append(f"versions.cutdowns: {n} — known: 15, 30, 60")
    for r in v.get("ratios") or []:
        if r not in RATIOS:
            red.append(f"versions.ratios: {r} — 9:16 only (the owner, 2026-09-23: no 4:5 or 1:1 videos at all)")
    grades = {r["id"] for r in load("looks/grades.json")["grades"]}
    if sheet.get("grade") is not None and sheet["grade"] not in grades:
        red.append(f"grade `{sheet['grade']}` is not a grade — known: {', '.join(sorted(grades))}")
    return red


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 2 or argv[0] != "check":
        print(__doc__)
        return 2
    p = Path(argv[1]).resolve()
    red = check(json.loads(p.read_text()), p.parent)
    for r in red:
        print("RED  ", r)
    for w in warnings(json.loads(p.read_text())):
        print("WARN ", w)
    print("GREEN — the sheet may render" if not red else f"{len(red)} to fix — nothing renders red")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
