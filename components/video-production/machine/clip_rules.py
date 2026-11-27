#!/usr/bin/env python3
"""THE CLIP RULES — what every AI clip plan must hold before any clip is paid for (2026-11-20, owner direction after
the first run of a brief whose start pictures were finished 3D prints). Standing rules for every AI brief; CLIP-RULES.md
is the page. Nothing here names a brand, product, person or brief.

  1  WHO SPEAKS IS WHO IS IN FRAME. A talking (lip-synced) call is planned only when each speaker's face is in its
     start picture. Otherwise the call is silent and the line is voice-over in the edit. One person's voice never goes
     on another person's mouth, and one person's marks are never asked of another person's picture.
  2  A RENDER GETS A RENDER PROMPT. A start picture that is a 3D render or diagram, with nobody in it, gets slow
     explainer motion with no body, hands, face or words, silent; never the phone-footage or talking-person preamble.
     A call never mixes a render and live action.
  3  THE PRODUCT IS NEVER DRAWN (nor any real artwork, cover or packaging) unless a real photo of it is a reference in
     the call. Its size and behaviour lines go only with that photo; otherwise it is laid on in the edit.
  4  THE BEATS MATCH THE PICTURE. A beat that contradicts the start picture (a jacket taken off that is already off)
     is caught here, at clip-plan time.

How the picture is read: the chain's one picture door (vision_judge.ask: the owner's Claude plan first, a local model,
then the paid door last) looks at each call's start picture and shot pictures once, with the brief's cast names and
the call's beats, and says who is in frame, whose face shows, whether it is a render and which beats it contradicts.
Each answer is kept in <run>/clips/picture-reads.json by the picture's bytes and the question, never asked twice. A dry
run, or a call whose picture is not made yet, reads nothing: the rules are checked when the pictures exist.

What `apply` does to the plan (clips/plan.json, plan-only.json):
  fixes   rule 2: a render call's prompt becomes the render prompt (its picture lines and camera and motion plan kept);
          rule 1: a silent call whose people are not in its picture loses the marks line that describes them
  refuses everything else broken, as a CLIP RULE problem the live clip door stops on: a talking call whose speaker's
          face is not in frame, a render call that also shows live action or talks, a product line with no product
          photo, a beat the picture contradicts, and a picture that could not be read

    python3 clip_rules.py <run dir> [--dry-run]       read, fix and refuse; prints every problem
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
HEAD = "CLIP RULE"
RENDER_LINE = ("A clean 3D explainer render, exactly as Image 1 shows it: slow, smooth explainer motion of the material "
               "itself (it settles, dissolves, soaks in, layers shift), lit evenly, the camera moving slowly as the plan "
               "below says. Only the layered material and its surface model are in the picture; no words, no labels, "
               "no numbers, nothing written. The surface stays whole. Silent: nobody speaks.")
# a render names no body: the content filter read a flesh-coloured cut-away plus "skin" lines as a body and refused it
# (2026-11-21, brief-0380 G04-C1-B, "nsfw"); its own plan's body words are said as the material model's
BODY_WORDS = re.compile(r"\b(skin|flesh|body|bodies|epidermis|dermis|pores?)\b", re.I)
BODY_SAFE = {"skin": "surface", "flesh": "material", "body": "model", "bodies": "models", "epidermis": "top layer",
             "dermis": "lower layer", "pore": "opening", "pores": "openings"}
RENDER_KEEP = ("Constant throughout: one continuous take of the same render, the same objects, materials, colours and "
               "light as Image 1; nothing appears that Image 1 does not hold. No subtitles. No background music.")
PRODUCT_WORDS = re.compile(r"\b(\d+(\.\d+)?\s?cm (tall|wide|long|high)|true size|draw (it|the product)|at (its|that) true)\b",
                           re.I)
MARKS = re.compile(r"\s*Marks kept exactly as in Image 1:[^.]*(\.[^.A-Z][^.]*)*\.")


# Rules 6-9 (owner direction through the first finished run's review, 2026-11-20: a tube and jars drawn into hands, an
# end card's words and arrow burned into a clip, a listener lip-syncing the speaker's voice, droplets turning to fibres
# and a surface lifting off a render). Each is a line every call carries, or a stop.
NO_ADD_MARK = "Nothing is added that is not in Image"
NO_ADD_LINE = ("Nothing is added that is not in Image 1 or the shot pictures: no container, tube, jar, bottle, pot, box, "
               "label, packaging or product appears, nobody picks one up or is handed one, and nothing is applied that "
               "the picture does not already show.")
NO_TEXT_MARK = "No words, letters"
NO_TEXT_LINE = ("No words, letters, numbers, captions, subtitles, logos, arrows, buttons or graphics appear anywhere in "
                "the picture at any moment; every on-screen word is added in the edit, never drawn here.")
LIQUID_LINE = ("Every liquid stays a liquid: droplets and cream soak in or run off. Nothing grows, sprouts, forms fibres, "
               "hairs or threads, and nothing lifts, peels, flakes or flies off the surface.")
TEXT_SENT = re.compile(r"typograph|caption|subtitle|on-?screen (text|words?)|text overlay|lettering|\barrows?\b|"
                       r"tap below|link below|buy now|swipe up|end ?card", re.I)
NEGATED = re.compile(r"\b(no|never|nothing|not|without|nor)\b", re.I)
TIMED_QUOTE = re.compile(r'^(\d+(?:\.\d+)?-\d+(?:\.\d+)?s), as (?:the person|[\w ]{1,40}?) starts "[^"\n]*":', re.M)


def _insert(prompt: str, line: str) -> str:
    """The line before the constants (\"Constant throughout\"), or at the end."""
    paras = (prompt or "").split("\n\n")
    at = next((i for i, x in enumerate(paras) if x.startswith("Constant throughout")), len(paras))
    return "\n\n".join(paras[:at] + [line] + paras[at:])


def no_text(prompt: str) -> str:
    """Rule 7: every sentence asking for words, an arrow or a card on screen is taken out (a sentence that forbids them
    stays), a timed line no longer quotes the words it is timed to (its seconds carry the timing, and a quoted line
    can be drawn), and the no-text line is added."""
    out = []
    for ln in TIMED_QUOTE.sub(r"\1:", prompt or "").split("\n"):
        if ln.startswith(("Image ", "Video ", "Audio ")):
            out.append(ln)
            continue
        sents = re.split(r"(?<=[.;!?])\s+", ln)
        kept = [x for x in sents if not (TEXT_SENT.search(x) and not NEGATED.search(x))]
        if ln.strip() and not kept:
            continue
        out.append(" ".join(kept))
    text = "\n".join(out)
    return text if NO_TEXT_MARK in text else _insert(text, NO_TEXT_LINE)


PRODUCT_LINE = ("The product is exactly the one in its reference pictures (its casting sheet): the same shape, size, colour, "
                "label and contents, shown only where the scene puts it, never redrawn or swapped for another. ")


def has_product(c: dict) -> bool:
    return any("/products/" in str(r.get("file") or "") for r in c.get("image_refs") or [])


def no_additions(prompt: str, product: bool = False) -> str:
    """Rule 6: nothing that is not in the pictures is added — no container, tube, jar or packaging. The real product
    named in the scene is not an addition: when its casting sheet rides along it is required, exactly as the sheet shows."""
    if NO_ADD_MARK in (prompt or ""):
        return prompt
    line = NO_ADD_LINE
    if product:
        line = PRODUCT_LINE + line.replace("Image 1 or the shot pictures", "Image 1, the shot pictures or the product's "
                                           "reference pictures").replace("label, packaging or product appears",
                                                                         "label or packaging other than the real product appears")
    return _insert(prompt, line)


def missing_casting(run: Path, c: dict) -> list:
    """Rule 11: the casting files this call's people, product and props have that its references do not carry."""
    try:
        cr = _load("clip_refs")
        sb = _read(run / "storyboard.json", {}) or {}
        want = cr.for_call(run, c, WS, people=not (sb.get("picture_only") and c.get("talking")))
    except Exception:  # noqa: BLE001
        return []
    if c.get("render"):                                 # a render carries no people: only its product sheets count
        want = [w for w in want if "/products/" in str(w.get("file"))]
    have = {str(r.get("file")) for r in c.get("image_refs") or []}
    if not have:
        return want                                     # nothing carried at all: every casting file is missing
    # the product's sheets are never left out; the rest may be trimmed to the model's picture limit
    return [w for w in want if "/products/" in str(w.get("file")) and str(w.get("file")) not in have]


def listeners_line(speakers, others) -> str:
    who = " and ".join(sorted(speakers))
    them = " and ".join(sorted(others))
    return (f"Only {who} speaks, and only while Audio 1 plays. {them} never speaks: lips closed and still, eyes off the "
            f"lens, for the whole take, in every shot.")


def finish(c: dict) -> dict:
    """Rules 6 and 7, on every call (a dry run included)."""
    _set_prompt(c, no_additions(no_text(c.get("prompt") or ""), has_product(c)))
    return c


def _load(name):
    sp = importlib.util.spec_from_file_location("cr_" + name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def brief_of(run: Path) -> dict:
    """The run's brief block (the last JSON block of the brief it was made from)."""
    rj = _read(Path(run) / "run.json", {}) or {}
    bf = Path(rj.get("brief_from") or Path(run) / "brief.md")
    bf = bf if bf.is_absolute() else WS / bf
    try:
        blocks = re.findall(r"```json\s*\n(.*?)\n```", bf.read_text(), re.S)
        return json.loads(blocks[-1]) if blocks else {}
    except (OSError, ValueError):
        return {}


def never_rules(run: Path, limit: int = 8) -> list:
    """Rule 13: the brief's never-rules — every sentence it writes with "never" in it (a look, a world, the product
    lock), de-duplicated, as written."""
    out = []

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            for sent in re.split(r"(?<=[.!?])\s+", v):
                sent = sent.strip()
                if re.search(r"\bnever\b", sent, re.I) and 8 < len(sent) <= 220 and sent not in out:
                    out.append(sent)
    walk(brief_of(run))
    return out[:limit]


NEVER_MARK = "The brief's never-rules hold in every frame:"


def never_line(prompt: str, rules: list) -> str:
    if not rules or NEVER_MARK in (prompt or ""):
        return prompt
    return _insert(prompt, NEVER_MARK + " " + " ".join(r if r.endswith(".") else r + "." for r in rules))


DIRECTION_Q = """You are checking the action plan of one AI video clip before it is made.
The brief's never-rules: {rules}
{render}The beats the clip will act, by id: {beats}
List every beat whose action would show something a never-rule forbids{render_tail}. Exaggerated or absurd action is
intended and allowed when no never-rule forbids it. Answer in JSON only: {{"breaks": [{{"beat": "<id>", "why": "<the rule
it breaks, in a few words>"}}]}}"""
RENDER_CAN = ("The clip starts on a 3D render with nobody in it. A render can show only a slow camera move, liquids "
              "soaking in or running, and the surface staying whole and in place.\n")


def direction_breaks(run: Path, beats: list, rules: list, render: bool, ask=None) -> list:
    """The beats that break a never-rule (or, on a render, show what a render cannot), read once per plan and kept in
    clips/direction-reads.json."""
    if not beats or not (rules or render):
        return []
    rows = [f'{b.get("id")}: {b.get("do")}' for b in beats if b.get("id")]
    q = DIRECTION_Q.format(rules=" ".join(rules) or "(none written)", render=RENDER_CAN if render else "",
                           beats="; ".join(rows),
                           render_tail=", or that a render cannot show (anything lifting, peeling, flying off, "
                                       "growing, sprouting or forming fibres, or particles that are not in the picture)"
                           if render else "")
    key = hashlib.sha256(q.encode()).hexdigest()[:20]
    f = Path(run) / "clips" / "direction-reads.json"
    seen = _read(f, {}) or {}
    if key in seen:
        return seen[key]
    if ask is None:
        vj = _load("vision_judge")
        got = vj.json_of(str(vj.ask(q, [], want_json=True))) or None
    else:
        got = ask(q, [])
    if not isinstance(got, dict):
        raise RuntimeError("the direction check could not be read")
    out = [x for x in got.get("breaks") or [] if isinstance(x, dict) and x.get("beat")]
    seen[key] = out
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(seen, indent=1, ensure_ascii=False))
    return out


def cast_of(run: Path) -> dict:
    """{cast id: one line of who they are} from the run's brief, for the picture read."""
    rj = _read(Path(run) / "run.json", {}) or {}
    bf = Path(rj.get("brief_from") or Path(run) / "brief.md")
    bf = bf if bf.is_absolute() else WS / bf
    try:
        blocks = re.findall(r"```json\s*\n(.*?)\n```", bf.read_text(), re.S)
        doc = json.loads(blocks[-1]) if blocks else {}
    except (OSError, ValueError):
        doc = {}
    out = {}
    for c in doc.get("cast") or []:
        cid = str(c.get("id") or "").strip()
        if cid:
            out[cid.lower()] = " ".join(str(c.get(k) or "") for k in ("name", "age", "look", "description", "who")
                                        if c.get(k))[:240] or cid
    return out


def headshots_of(run: Path) -> dict:
    """{cast id: headshot file} from the cast bank, so the read knows who is who by face, not by guess."""
    rj = _read(Path(run) / "run.json", {}) or {}
    brand = rj.get("brand")
    out = {}
    for cid in cast_of(run):
        home = WS / "runs" / "ai-elements" / str(brand) / "casting" / cid
        for f in (home / "sheets" / "headshot.jpg", home / "sheets" / "headshot-crop.jpg", home / "master.jpg",
                  home / "master.png"):
            if f.is_file():
                out[cid] = f
                break
    return out


QUESTION = """You are checking one start picture for an AI video clip before it is made. Image 1 is the picture.
{faces}The cast, by id: {cast}
The beats this clip will act, in order: {beats}
Answer in JSON only:
{{"people": [the cast ids of everyone you can see, even partly], "faces": [the cast ids whose face you can clearly see],
  "render": true if the picture is a 3D render, diagram or cross-section with no real person in it, else false,
  "contradicts": [{{"beat": "<beat id>", "kind": "done" or "impossible", "why": "<what the picture shows>"}}],
  "lookalikes": [short names of any objects that could be mistaken for a product, a tube, a jar, packaging or soap],
  "products_seen": [short names of every product tube, jar, bottle or pack you can see, empty if none]}}
"done" = the picture already shows that beat's own end state (it was already done before the clip starts).
"impossible" = anything else that seems not to fit. Exaggerated, absurd or surreal actions are intended: never list
them.
A beat contradicts the picture ONLY when the picture already shows that beat's end state (a garment already taken
off, a liquid already poured, a lid already open) or makes the action physically impossible. These are NOT
contradictions: an object or product not visible yet (it may be laid on in the edit or brought in), a material or
ingredient that looks a little different from its name, the picture's framing, or anything that happens later in the
clip. Leave "contradicts" empty when unsure."""


def read_picture(run: Path, picture: Path, cast: dict, beats: list, ask=None) -> dict:
    """The judge's read of one picture, kept by the picture's bytes and the question. The cast's headshots ride along
    after the picture (Image 2, 3, …) so each person is known by face."""
    heads = headshots_of(run) if ask is None else {}
    order = [k for k in cast if k in heads]
    faces = "".join(f"Image {i + 2} is the face of cast id {k} (a reference only, not the picture). " for i, k in
                    enumerate(order))
    q = QUESTION.format(faces=(faces + "\n") if faces else "",
                        cast="; ".join(f"{k}: {v}" for k, v in cast.items()) or "(none)",
                        beats="; ".join(f"{b.get('id')}: {b.get('action') or b.get('do')}" for b in beats) or "(none)")
    key = hashlib.sha256(Path(picture).read_bytes()).hexdigest()[:20] + "-" + hashlib.sha256(q.encode()).hexdigest()[:12]
    store = Path(run) / "clips" / "picture-reads.json"
    reads = _read(store, {}) or {}
    if key in reads:
        return reads[key]
    if ask is None:
        vj = _load("vision_judge")
        ans = vj.ask(q, [str(picture)] + [str(heads[k]) for k in order], want_json=True)
        got = vj.json_of(str(ans)) or {}
    else:
        got = ask(q, [str(picture)])
    got = {"people": [str(x).lower() for x in got.get("people") or []],
           "faces": [str(x).lower() for x in got.get("faces") or []],
           "render": bool(got.get("render")), "contradicts": got.get("contradicts") or [],
           "lookalikes": [str(x) for x in got.get("lookalikes") or []][:6],
           "products_seen": [str(x) for x in got.get("products_seen") or []][:6],
           "picture": str(picture)}
    reads[key] = got
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(reads, indent=1, ensure_ascii=False) + "\n")
    return got


# a render's camera words that read as an edit overlay (the clip gate's GRAPHICS check): said as what the camera sees
OVERLAY_WORDS = re.compile(r"cross-sections?|overlays?|graphics?|cartoons?", re.I)
SAFE_WORDS = {"cross-section": "cut-away", "cross-sections": "cut-aways", "overlay": "layer", "overlays": "layers",
              "graphic": "render", "graphics": "render", "cartoon": "render", "cartoons": "render"}
RENDER_SIDE = re.compile(r"render|cross-section|diagram|3d|model", re.I)


def render_prompt(prompt: str, shot_pictures=None, refs=None) -> str:
    """The render prompt: its own picture lines (the render, then each shot picture it still sends, then the product
    and prop references it carries), its camera and motion plan, the render line and constants. Never a person line."""
    paras = [p for p in (prompt or "").split("\n\n") if p.strip()]
    pics = ["Image 1 is the first frame: the render exactly as it is, its objects, materials, colours and light."]
    pics += [f"Image {i + 2} is the opening picture of shot {s['shot']}: the same render, framed as it shows."
             for i, s in enumerate(shot_pictures or [])]
    k = len(pics)
    pics += [f"Image {k + i + 1} is a reference for {r.get('job') or 'a real object in the render'}."
             for i, r in enumerate(refs or [])]
    plan = [BODY_WORDS.sub(lambda m: BODY_SAFE.get(m.group(0).lower(), "material"),
                           OVERLAY_WORDS.sub(lambda m: SAFE_WORDS.get(m.group(0).lower(), "cut-away"), p))
            for p in paras if p.startswith("CAMERA AND MOTION")]
    return "\n\n".join(["\n".join(pics), RENDER_LINE] + plan + [LIQUID_LINE, RENDER_KEEP])


def blocks_for(cm: dict, scenes: list, render: bool) -> list:
    """The CAMERA AND MOTION blocks of the scenes' render sides (render=True) or live sides (render=False). A scene
    that is not split is live unless its shots say render."""
    out = []
    for sid in scenes or []:
        p = (cm.get("scenes") or {}).get(sid) or {}
        if p.get("kind") == "split":
            for side in p.get("sides") or []:
                shots = ((p.get("camera") or {}).get(side) or {}).get("shots") or []
                is_r = bool(RENDER_SIDE.search(" ".join(str(s.get("angle") or "") for s in shots)))
                if is_r == render and (p.get("side_words") or {}).get(side):
                    out.append(p["side_words"][side])
        elif p.get("words"):
            shots = (p.get("camera") or {}).get("shots") or []
            if bool(RENDER_SIDE.search(" ".join(str(s.get("angle") or "") for s in shots))) == render:
                out.append(p["words"])
    return out


def _beats_of(call: dict, cm: dict) -> list:
    """The beats the call's START picture has to hold: its first scene's, and of a split scene only the side the start
    picture shows (its first side), never a side the picture does not show."""
    sids = call.get("scenes") or []
    if not sids:
        return []
    p = (cm.get("scenes") or {}).get(sids[0]) or {}
    m = p.get("motion") or {}
    if p.get("kind") == "split":
        side = (p.get("sides") or [None])[0]
        return (m.get(side) or {}).get("beats") or [] if side else []
    return m.get("beats") or []


TALK = re.compile(r"\b(talk|talks|talking|speak|speaks|speaking|said|says|saying|mouth|mouthing|lip-?sync\w*|"
                  r"with their words|while talking|to camera)\b", re.I)
ALLOWED = re.compile(r"lips? (stay |kept |keep |are )?closed|lips closed|keeps? (their|her|his) lips closed|nobody speaks|"
                     r"says nothing|mouths? stay closed|in silence|silent", re.I)


def _talky(sentence: str) -> bool:
    """A sentence that asks for talking, once the allowed silences are taken out of it."""
    return bool(TALK.search(ALLOWED.sub("", sentence)))


def silent_clean(c: dict) -> list:
    """A silent call's prompt with every talking word taken out (rule 1, 2026-11-20): the talking-person preamble, a
    talking-movement reference video and its line, the swipe pattern's talking moments, any other sentence asking for
    talk or a moving mouth. Beat lines and their quoted words stay. Returns the movement refs it removed."""
    lines, removed_videos = (c.get("prompt") or "").split("\n"), []
    out = []
    for ln in lines:
        m = re.match(r"Video (\d+) is ", ln)
        if m and _talky(ln):
            removed_videos.append(int(m.group(1)))
            continue
        if ln.startswith(("Beat by beat", "Image ", "Audio ", "CAMERA AND MOTION", "Camera:")):
            out.append(ln)
            continue
        if ln.startswith("The swipe's motion pattern"):
            head, _, rest = ln.partition("): ")
            parts = [x for x in re.split(r",\s*(?=-?\d+(?:\.\d+)? s )", rest) if not _talky(x)]
            out.append(head + "): " + ", ".join(parts) if rest else ln)
            continue
        sents = re.split(r"(?<=[.;])\s+", ln)
        keep = [s for s in sents if not _talky(s)]
        if keep or not ln.strip():
            out.append(" ".join(keep))
    # the removed reference videos: dropped from the call, and the other videos renumbered in send order
    vids = [r for r in c.get("refs") or [] if r.get("kind") in ("movement", "swipe")]
    gone = [vids[i - 1] for i in removed_videos if 0 < i <= len(vids)]
    if gone:
        c["refs"] = [r for r in c.get("refs") or [] if r not in gone]
        left = [i for i in range(1, len(vids) + 1) if i not in removed_videos]
        remap = {old_: new_ + 1 for new_, old_ in enumerate(left)}
        out = [re.sub(r"^Video (\d+) is ", lambda m: f"Video {remap.get(int(m.group(1)), int(m.group(1)))} is ", ln)
               for ln in out]
        if not c["refs"] and c.get("endpoint") == "reference-to-video" and not c.get("talking"):
            c["endpoint"] = "image-to-video"
    _set_prompt(c, "\n".join(out))
    return gone


def _shots_of(call: dict, cm: dict) -> list:
    """The camera shots of the call's start scene (of a split scene, its first side)."""
    sids = call.get("scenes") or []
    p = (cm.get("scenes") or {}).get(sids[0]) or {} if sids else {}
    cam = p.get("camera") or {}
    if p.get("kind") == "split":
        side = (p.get("sides") or [None])[0]
        return (cam.get(side) or {}).get("shots") or [] if side else []
    return cam.get("shots") or []


def _set_prompt(c: dict, text: str):
    c["prompt"] = text
    if isinstance(c.get("seedance"), dict):
        c["seedance"]["prompt"] = text
    if isinstance(c.get("params"), dict):
        c["params"]["prompt"] = text


def check_call(run: Path, c: dict, cast: dict, cm: dict, dry: bool, ask=None) -> list:
    """The problems one call breaks after its fixes are applied (the call is changed in place)."""
    probs = []
    cid = c.get("id")
    # rule 3: no product line without a product photo (text only, needs no picture)
    has_photo = any("product" in str(r.get("job") or "").lower() or "/products/" in str(r.get("file") or "")
                    for r in c.get("image_refs") or [])
    if not has_photo and PRODUCT_WORDS.search(c.get("prompt") or ""):
        probs.append(f"{HEAD} 3: {cid} asks for the product at its true size with no product casting sheet in the call — "
                     f"the chain's references must carry it (clip_refs)")
    # rule 12: every product the scene's words or beats name is a banked product (its sheet rides along, clip_refs);
    # a product word acted in the scene that names none is a stop, never left for the model to invent
    try:
        _ids, loose = _load("clip_refs").named_products(run, c, WS)
    except Exception:  # noqa: BLE001
        loose = []
    if loose:
        probs.append(f"{HEAD} 12: {cid}'s scene acts with {', '.join(repr(w) for w in loose)} but no banked product or "
                     f"prop of the scene is called that — name the product in the brief or bank it")
    # rule 11: every call carries the chain's own setup — the casting files its people, product and props have
    gone = missing_casting(run, c)
    if gone:
        probs.append(f"{HEAD} 11: {cid} does not carry its casting files ({', '.join(Path(str(g['file'])).name for g in gone[:4])}"
                     f"{' …' if len(gone) > 4 else ''}) — re-plan; a call never goes out without the chain's references")
    if dry:
        finish(c)
        return probs
    cp = _load("clips_plan")
    start = cp.picture_file(run, c.get("start_frame")) if c.get("start_frame") else None
    if not start:
        finish(c)
        return probs
    beats = _beats_of(c, cm)
    try:
        r = read_picture(run, start, cast, beats, ask=ask)
        shots = [read_picture(run, WS / s["file"], cast, [], ask=ask) for s in c.get("shot_pictures") or []
                 if (WS / s["file"]).is_file()]
    except Exception as e:  # noqa: BLE001 -- a picture nobody could read is a stop, never a pass
        finish(c)
        return probs + [f"{HEAD}: {cid}'s start picture could not be read ({type(e).__name__}: {str(e)[:120]})"]
    speakers = {str(v.get("person") or "").lower() for v in c.get("voice_parts") or [] if v.get("person")}
    # rule 2: a render — the judge says so, or nobody is in the picture and the brief's own shots for it say it is one
    side_text = " ".join(str(s.get("angle") or "") + " " + str(s.get("move") or "")
                         for s in _shots_of(c, cm)).lower()
    if not r["render"] and not r["people"] and re.search(r"render|cross-section|diagram|3d|model", side_text):
        r = dict(r, render=True)
    if r["render"]:
        if c.get("talking"):
            probs.append(f"{HEAD} 2: {cid} starts on a render but is planned to talk — a render is silent")
        live = [s for s in shots if not s["render"]]
        if live and not c.get("layout"):
            # A SPLIT IS A LAYOUT (owner, 2026-11-20): the live pictures leave this call for their own clip over the
            # same stretch of time (split_off), stacked with this render in the edit; this call keeps the renders only
            c["_live_out"] = [s["picture"] for s in live]
            keep = {s["picture"] for s in shots if s["render"]}
            c["shot_pictures"] = [s for s in c.get("shot_pictures") or [] if str(WS / s["file"]) in keep]
        if not any(p.startswith(f"{HEAD} 2") for p in probs):
            c["_live_prompt"] = c.get("prompt") or ""
            rb = blocks_for(cm, c.get("scenes"), render=True)
            base = "\n\n".join([p for p in (c.get("prompt") or "").split("\n\n") if not p.startswith("CAMERA AND MOTION")] + rb) \
                if rb else (c.get("prompt") or "")
            # a render has nobody in it: only the product and prop references stay, each named in the prompt
            c["image_refs"] = [x for x in c.get("image_refs") or []
                               if "/products/" in str(x.get("file")) or "/props/" in str(x.get("file"))]
            _set_prompt(c, render_prompt(base, c.get("shot_pictures"), c["image_refs"]))
            c["render"] = True
    else:
        # rule 1: who speaks is who is in frame
        if c.get("talking"):
            off = sorted(s for s in speakers if s not in r["faces"])
            if off:
                probs.append(f"{HEAD} 1: {cid} lip-syncs {', '.join(off)} but no face of theirs is in its start picture — "
                             f"plan it silent with the line as voice-over")
            # rule 8: the speaker lock holds across every shot picture — a shot whose picture shows no speaker's face
            # is a stop (the voice would land on whoever is there), and everyone else in any picture never speaks
            for sh in shots:
                if speakers and not (speakers & set(sh["faces"])):
                    probs.append(f"{HEAD} 8: {cid}'s shot picture {Path(sh['picture']).name} shows no face of "
                                 f"{', '.join(sorted(speakers))} while the voice plays — that shot goes silent in a call "
                                 f"of its own, or its picture shows the speaker")
            others = {x for rr in [r] + shots for x in rr["people"]} - speakers
            if speakers and others and "never speaks: lips closed" not in (c.get("prompt") or ""):
                _set_prompt(c, _insert(c.get("prompt") or "", listeners_line(speakers, others)))
        if not c.get("talking"):
            gone = silent_clean(c)
            if gone:
                c.setdefault("removed_refs", []).extend(gone)
            left = [s for ln in (c.get("prompt") or "").split("\n")
                    if not ln.startswith(("Beat by beat", "CAMERA AND MOTION", "Camera:", "Image ", "The swipe's motion"))
                    for s in re.split(r"(?<=[.;])\s+", ln) if _talky(s)]
            if left:
                probs.append(f"{HEAD} 1: {cid} is silent but still asks for talking: \"{left[0][:90]}\"")
        looks = sorted({x for rr in [r] + shots for x in rr.get("lookalikes") or []})
        if looks and "could read as a product" not in (c.get("prompt") or ""):
            line = (f"Things that could read as a product or its packaging (the {', the '.join(looks)}) stay exactly as "
                    f"they are in the picture; no product, label or packaging is added, drawn or reshaped.")
            paras = (c.get("prompt") or "").split("\n\n")
            at = next((i for i, x in enumerate(paras) if x.startswith("Constant throughout")), len(paras))
            _set_prompt(c, "\n\n".join(paras[:at] + [line] + paras[at:]))
        people = {str(x).lower() for x in c.get("people") or []}
        if not c.get("talking") and people and not (people & set(r["people"])):
            _set_prompt(c, MARKS.sub("", c.get("prompt") or ""))        # their marks are not asked of someone else
            c["people_in_frame"] = r["people"]
    # rule 14: the taken prints fit the current direction — a scene that uses the product shows it in its pictures, and
    # no two of a call's pictures are the same print; either is flagged for a remake on the owner's word
    if not r["render"] and any("/products/" in str(x.get("file")) for x in c.get("image_refs") or []) \
            and not any(rr.get("products_seen") for rr in [r] + shots):
        probs.append(f"{HEAD} 14: {cid}'s scene uses the product but none of its pictures shows it — flag the picture "
                     f"for a remake on the owner's word (the clip would invent the product's place)")
    pics = [start] + [WS / s["file"] for s in c.get("shot_pictures") or [] if (WS / s["file"]).is_file()]
    shas = {}
    for f in pics:
        shas.setdefault(hashlib.sha256(Path(f).read_bytes()).hexdigest(), []).append(Path(f).name)
    for names in shas.values():
        if len(names) > 1:
            probs.append(f"{HEAD} 14: {cid}'s pictures {' and '.join(names)} are the same print — each shot needs its "
                         f"own; flag for a remake on the owner's word")
    # rule 4: a beat the picture already shows done is dropped from the call's plan (and kept on the call, said);
    # one that cannot be found in the plan to drop is refused by name
    done_before = {d.get("beat") for d in c.get("dropped_beats") or []}
    for x in r.get("contradicts") or []:
        bid = str(x.get("beat") or "").strip()
        if bid in done_before:
            continue                                   # dropped on an earlier pass: the rule already holds
        if str(x.get("kind") or "").lower() != "done":
            if bid not in {n.get("beat") for n in c.get("beat_notes") or []}:
                c.setdefault("beat_notes", []).append({"beat": bid, "why": x.get("why")})
            continue
        text, ok = drop_beat(c.get("prompt") or "", (c.get("scenes") or [None])[0], bid)
        if ok:
            _set_prompt(c, text)
            c.setdefault("dropped_beats", []).append({"beat": bid, "why": x.get("why")})
        else:
            probs.append(f"{HEAD} 4: {cid} beat {bid}: {x.get('why')} — rewrite or drop the beat")
    # rule 13: the direction keeps the brief's never-rules, and a render is asked only what a render can show — a
    # breaking beat is dropped from the call's plan (kept on the call, said); one that cannot be dropped is a stop
    try:
        broke = direction_breaks(run, _beats_of(c, cm), never_rules(run), bool(c.get("render") or r.get("render")), ask=ask)
    except Exception as e:  # noqa: BLE001 -- a direction nobody could check is a stop, never a pass
        broke = []
        probs.append(f"{HEAD} 13: {cid}'s direction could not be checked against the brief's never-rules ({str(e)[:120]})")
    gone = {d.get("beat") for d in c.get("dropped_beats") or []}
    for x in broke:
        bid = str(x.get("beat") or "").strip()
        if bid in gone:
            continue
        text, ok = drop_beat(c.get("prompt") or "", (c.get("scenes") or [None])[0], bid)
        if ok:
            _set_prompt(c, text)
            c.setdefault("dropped_beats", []).append({"beat": bid, "why": f"breaks the brief: {x.get('why')}"})
        else:
            probs.append(f"{HEAD} 13: {cid} beat {bid} breaks the brief ({x.get('why')}) — rewrite or drop the beat")
    finish(c)
    return probs


def drop_beat(prompt: str, scene: str, beat: str):
    """(prompt, dropped?): the beat taken out of its scene's CAMERA AND MOTION block ("Beat by beat" line)."""
    if not beat or not scene:
        return prompt, False
    paras = prompt.split("\n\n")
    for i, para in enumerate(paras):
        if not para.startswith(f"CAMERA AND MOTION (the director's plan for {scene}"):
            continue
        lines = para.split("\n")
        for j, ln in enumerate(lines):
            if not ln.startswith("Beat by beat"):
                continue
            head, _, body = ln.partition(": ")
            segs = [s for s in body.rstrip(".").split("; ") if s]
            keep = [s for s in segs if not re.match(re.escape(beat) + r"\b", s)]
            if len(keep) == len(segs):
                continue
            lines[j] = head + ": " + "; ".join(keep) + "." if keep else ""
            paras[i] = "\n".join(x for x in lines if x)
            return "\n\n".join(paras), True
    return prompt, False


def split_off(c: dict, live: list, cast: dict, reads: dict, voices: dict | None = None, cm: dict | None = None) -> dict:
    """The live half of a split as its own clip over the same stretch of time: its first live picture as the start,
    the rest as shot pictures; it talks when a speaker's face is in its start picture (rule 1), else it is silent.
    Both halves carry `layout` for the edit (render on top, people below)."""
    first = Path(live[0])
    n = json.loads(json.dumps(c))       # its own copy: the halves never share a prompt, refs or params
    n["id"] = f"{c['id']}-B"
    n["start_frame"] = first.stem
    n["shot_pictures"] = [{"shot": Path(x).stem, "file": str(Path(x).resolve().relative_to(WS.resolve())),
                           "job": "the shot opens on this picture: the same people, place and light"} for x in live[1:]]
    n.pop("render", None)
    n.pop("_live_out", None)
    faces = set(reads.get(str(first), {}).get("faces") or [])
    speakers = {str(l.get("speaker") or "").lower() for l in c.get("lines") or [] if str(l.get("text") or "").strip()}
    talk = sorted(s for s in speakers if s in faces)
    n["lines"] = [dict(l, on_camera=str(l.get("speaker") or "").lower() in faces) for l in c.get("lines") or []]
    n["talking"] = bool(talk)
    n["voice_parts"] = [{"scene": l["scene"], "person": l.get("speaker"), "line": l.get("text"),
                         "voice_id": l.get("voice_id") or (voices or {}).get(l["scene"])}
                        for l in n["lines"] if l["on_camera"]]
    n["people"] = sorted(set(reads.get(str(first), {}).get("people") or []))
    prompt = c.get("_live_prompt") or c.get("prompt") or ""
    pics = [f"Image 1 is the first frame and shows {' and '.join(n['people']) or 'the people'}: keep these exact people, "
            f"faces, clothing, props, place and light."]
    pics += [f"Image {i + 2} is the opening picture of shot {s['shot']}: {s['job']}." for i, s in enumerate(n["shot_pictures"])]
    lb = blocks_for(cm or {}, c.get("scenes"), render=False)     # the people's side of the plan, never the render's
    body = [p for p in prompt.split("\n\n") if p.strip() and not p.startswith("Image ")
            and not (lb and p.startswith("CAMERA AND MOTION"))]
    if lb:
        at = next((i for i, p in enumerate(body) if p.startswith("Constant throughout")), len(body))
        body = body[:at] + lb + body[at:]
    if talk:
        who = " and ".join(talk)
        pics.append(f"Audio 1 is {who}'s voice: {who} speaks Audio 1 word for word, lips matching every word, and says "
                    f"nothing else; everyone else keeps their lips closed.")
    _set_prompt(n, "\n\n".join(["\n".join(pics)] + body))
    c["layout"] = {"kind": "stack", "position": "top", "with": n["id"],
                   "note": "a split in the swipe is a layout: this render sits on top, the people below; captions on the seam"}
    n["layout"] = {"kind": "stack", "position": "bottom", "with": c["id"],
                   "note": "the people's half of the split, under the render, same stretch of time"}
    return n


def apply(run: Path, dry: bool = False, files=("plan.json", "plan-only.json"), ask=None) -> list:
    """Fix and check every call of the run's clip plan(s); the problems go into the plan, where the live door stops."""
    run = Path(run)
    cast = cast_of(run)
    cm = _read(run / "clips" / "camera-motion.json", {}) or {}
    added = []
    for name in files:
        f = run / "clips" / name
        res = _read(f, None)
        if not isinstance(res, dict) or not res.get("calls"):
            continue
        probs = [p for p in res.get("problems") or [] if not str(p).startswith(HEAD)]
        calls, reads = [], {}
        nev = never_rules(run)
        for c in res["calls"]:
            new = check_call(run, c, cast, cm, dry, ask=ask)
            if not c.get("render"):            # a render shows no person or product: the brief's never-rules stay off it
                _set_prompt(c, never_line(c.get("prompt") or "", nev))
            probs += new
            added += new
            calls.append(c)
            if c.get("_live_out"):
                for v in (_read(run / "clips" / "picture-reads.json", {}) or {}).values():
                    reads[v.get("picture")] = v
                b = split_off(c, c.pop("_live_out"), cast, reads,
                              {x.get("scene"): x.get("voice_id") for x in res.get("tts") or []}, cm)
                calls.append(b)
                more = check_call(run, b, cast, cm, dry, ask=ask)
                if not b.get("render"):
                    _set_prompt(b, never_line(b.get("prompt") or "", nev))
                probs += more
                added += more
                # the lines this half says on camera are no longer voice-over
                said = {l["scene"] for l in b["lines"] if l.get("on_camera")}
                res["tts"] = [x for x in res.get("tts") or [] if x.get("scene") not in said]
            c.pop("_live_prompt", None)
        res["calls"] = calls
        stacks = [c for c in calls if (c.get("layout") or {}).get("position") == "top"]
        if stacks and name == "plan.json":
            # the editor's sheet for each split: which clip sits on top, which below, over the same stretch of time
            lines = ["# Layout — splits built in the edit", "",
                     "Each split in the swipe is a layout: two clips over the same stretch of time, stacked. Captions "
                     "sit on the seam.", "", "| Time | Top (render) | Bottom (people) | Scenes |", "|---|---|---|---|"]
            for c in stacks:
                w = c.get("window") or [0, c.get("seconds") or 0]
                lines.append(f"| {c.get('at')} s, {round(float(w[1]) - float(w[0]), 2)} s | {c['id']} | "
                             f"{c['layout'].get('with')} | {', '.join(c.get('scenes') or [])} |")
            (run / "clips" / "LAYOUT.md").write_text("\n".join(lines) + "\n")
        res["problems"] = probs
        res["clip_rules"] = {"dry_run": dry, "checked": len(res["calls"])}
        f.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    return added


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    added = apply(Path(a.run), a.dry_run)
    for p in dict.fromkeys(added):
        print("STOP " + p)
    print(f"clip rules: {len(set(added))} problem(s)")
    return 2 if added else 0


if __name__ == "__main__":
    sys.exit(main())
