#!/usr/bin/python3
"""Story presets — the layer between a format and the writing (2026-11-21).

A format says how a piece is made (names.json: production format, script format, style). A story preset is one
fully timed story inside a format: its beats at % marks, where the product enters and how it shows, the cast roles,
the tone and sound, the captions and the length. The writing chain fills a preset with the brand's own research
(avatar profile, culture map, verbatim language, objection bank, offer bank), the creative-controls dials and the
house rules; the preset itself is brand-free.

The first shelf is the 47 Higgsfield Drama Ads cards, captured word for word under
components/workflow-teardown/sources/higgsfield/drama-ads/catalog/. The capture is data (workspace rule 8); each
entry here is our structured version of one card, status draft.

    python3 components/creative-controls/story_presets.py list [--format <script format>] [--hf-style <family>]
    python3 components/creative-controls/story_presets.py show <id>
    python3 components/creative-controls/story_presets.py pick --format <script format> [--awareness <level>]
        [--length short|long] [--used <id,id>]
    python3 components/creative-controls/story_presets.py build [--check]   # re-read the captures, keep curated fields

Public surface (other components use only these): load, get, ids, pick, block, check_lines, check_brief.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[1]
MANIFEST = HERE / "story_presets.json"
CATALOG = WS / "components/workflow-teardown/sources/higgsfield/drama-ads/catalog"
CATALOG_REL = "components/workflow-teardown/sources/higgsfield/drama-ads/catalog"
NAMES = WS / "components/video-production/formats/names.json"
ELEMENT_STYLES = WS / "components/elements/library/style.video.json"   # the element bank's video looks (wider)
# a look's words -> an element-bank style id that already makes it
ELEMENT_ALIAS = {"clay": "claymation", "claymation": "claymation", "claymotion": "claymation", "crochet": "crochet",
                 "needle-felted": "needle-felt", "felt": "needle-felt", "ink": "ink-wash", "ink-gold": "ink-wash",
                 "hand-drawn-ink": "ink-wash", "pixel-art": "pixel-16bit", "pixel-night": "pixel-16bit",
                 "paper-diorama": "miniature-diorama", "paper-collage": "paper-cutout", "3d-papercraft": "paper-cutout",
                 "toy-planet": "miniature-diorama", "brick-toy": "brick-figure", "knit-sky": "crochet",
                 "cutaway-lab": "cutaway-3d", "fairy-tale": "storybook-watercolour", "fairy-tale-myth": "storybook-watercolour", "hand-drawn": "ink-wash", "pastel-clay": "claymation", "dusk-anime": "anime", "voxel-city": "brick-figure", "cube-planet": "miniature-diorama",
                 "watercolor-chronicle": "storybook-watercolour", "wash-atlas": "storybook-watercolour",
                 "noir_3d": "neon-noir", "fluffy-toy": "plush-mascot", "whiteboard-doodle": "whiteboard-sketch",
                 "feature-3d": "family-3d", "feature3d": "family-3d", "anime": "anime", "phone": "phone-ugc",
                 "live-action": "hypermotion-cinematic", "realism_cinematic": "hypermotion-cinematic",
                 "doll-3d": "art-toy", "low-poly": "low-poly", "classic_2d": "cel-1950s", "rubber-hose": "cel-1950s"}

# Higgsfield's nine style families -> the family id we file them under
HF_FAMILY = {"Micro drama": "micro-drama", "Cartoon story": "cartoon", "Claymation story": "claymation",
             "Cinematic story": "cinematic", "Inside the body": "inside-the-body", "Talking object": "talking-object",
             "Doll story": "doll", "Crochet story": "crochet", "Singing ads": "singing"}

# Fields a person sets and a rebuild keeps (the rest is re-read from the capture every build).
CURATED = ("status", "state", "arc", "arc_why", "notes")   # devices are read from the card by code

# First-build picks: the creative-controls arc each card runs closest to. A session's pick, for the curator to
# correct on the manifest (state "arc-picked-by-session"); a rebuild never overwrites a curated arc.
SEED_ARC = {
    "caught-stealing": "micro-drama", "endurance": "micro-drama", "fake-unmasked": "micro-drama",
    "falsely-accused": "micro-drama", "family-sabotage": "micro-drama", "inheritance-cheat": "micro-drama",
    "nerves": "micro-drama", "off-the-team": "micro-drama", "promotion-stolen": "micro-drama",
    "public-failure": "micro-drama", "revenge": "micro-drama", "secret-ally": "micro-drama",
    "stranger-s-gift": "micro-drama", "toast-of-the-night": "micro-drama", "trap-backfires": "micro-drama",
    "underdog": "micro-drama", "winning-the-room": "micro-drama", "stolen-at-the-final": "micro-drama",
    "frizzilla": "micro-drama", "smile-june": "micro-drama", "top-shelf": "micro-drama", "last-laugh": "micro-drama",
    "verdicam": "micro-drama",
    "second-chance": "person-in-a-hole", "last-goodbye": "person-in-a-hole", "lost-and-found": "person-in-a-hole",
    "failed-remedies": "person-in-a-hole", "hired-help": "person-in-a-hole", "last-bar": "person-in-a-hole",
    "cringe-rerun": "person-in-a-hole",
    "shrink-the-creature": "escalation-ladder", "ice-paws": "escalation-ladder", "monster-within": "escalation-ladder",
    "mock-tragedy": "escalation-ladder", "bear-proof": "escalation-ladder",
    "lasagna-heist": "mystery-box", "me-or-the-cat": "mystery-box", "stakeout-romance": "mystery-box",
    "snob-s-secret": "unreliable-narrator", "fluff-lift": "heros-journey", "third-row-mix-up": "two-sides",
    "inside-confession": "epiphany-bridge", "ruined-sheep": "oedipus", "stay-frost": "cinderella",
}

# Story devices read from a card's words (code, not judgement): (device id, pattern in the structure/cast text).
DEVICE_WORDS = (
    ("the-mentor", r"\bmentor\b"), ("the-villain", r"\b(rival|villain|bully|snob|cheat|culprit|thief)\b"),
    ("the-witness", r"\b(witness|barometer|the one kept away)\b"),
    ("ticking-clock", r"\b(deadline|exact hour|at an hour|countdown|tomorrow|next day)\b"),
    ("setup-payoff", r"\b(planted|clue|callback|returns?)\b"), ("reversal", r"\b(revers|turned|turns the|flips?)\b"),
    ("all-is-lost", r"\b(breakdown|rock bottom|lowest|all is lost)\b"), ("false-victory", r"\bremedies fail|fails?\b"),
("the-confession", r"\bconfess"), ("the-tag", r"\bpops? up behind\b"),
    ("identity-mirror", r"\bbuyers' (usual )?age\b"), ("the-specific-detail", r"\bnumbered\b"),
)

# Our nine questions on any drama-shaped script (from the drama-ads script review; our wording, our order).
CHECKS = [
    {"id": "hook-3s", "ask": "Does the first frame show the conflict between two characters, readable in 3 seconds "
                             "with no context (no scenery first, no document or screen to read)?"},
    {"id": "obvious-5s", "ask": "Does a stranger know the kind of situation in 5 seconds and, within 10, who each "
                                "character is to the others, in the plain words of their world?"},
    {"id": "on-screen", "ask": "Is every conflict shown on screen, with at most one world rule the viewer must learn?"},
    {"id": "exposition", "ask": "Does no line carry more than two facts, no villain confess for the viewer, and no "
                                "character explain their own feelings?"},
    {"id": "agency", "ask": "Does every turn in the hero's favour, the product's arrival included, come from a "
                            "deliberate act (theirs or the mentor's), and was everything the ending turns on planted "
                            "before it?"},
    {"id": "mute", "ask": "Do the turn and the ending read with the sound off and no readable text?"},
    {"id": "ending", "ask": "Does the piece end on a concrete, visible action that answers the hook?"},
    {"id": "physics", "ask": "Can every action happen by the world's own physics and be shown by the video model: at "
                             "most two bodily contacts and one change of state per 30 seconds, each across a cut?"},
    {"id": "clean", "ask": "No brand but ours, no real people or known characters, nothing sexualised, everyone "
                           "clothed, a child only in an everyday scene?"},
]


# ------------------------------------------------------------------ reading the manifest

def load():
    return json.loads(MANIFEST.read_text())


def ids():
    return [p["id"] for p in load()["presets"]]


def get(pid):
    for p in load()["presets"]:
        if p["id"] == pid:
            return p
    raise KeyError("no story preset %r — known: %s" % (pid, ", ".join(ids())))


def _length_name(seconds):
    return "long" if seconds and seconds > 120 else "short"


def pick(script_format=None, awareness=None, length=None, used=(), hf_style=None):
    """The presets that fit, best first, each with why: [(preset, reason)].
    Fits: the script format (a names.json script format id) or the Higgsfield family; then, ranked: not used yet for
    this avatar, the arc listed for the awareness level, the length asked for, shorter first (paid ads run short).
    Deprecated presets and the singing cards (they run on the song line, not the drama writing) never come back."""
    arcs = {}
    try:
        arcs = {a["id"]: a for a in json.loads((HERE / "controls.json").read_text()).get("arcs") or []}
    except (OSError, ValueError):
        pass
    out = []
    for p in load()["presets"]:
        if p.get("status") == "deprecated" or p["hf_style"] == "singing":
            continue
        if script_format and p["format"].get("script_format") != script_format:
            continue
        if hf_style and p["hf_style"] != hf_style:
            continue
        why, score = [], 0
        if p["id"] in set(used):
            score -= 100
            why.append("already written for this avatar")
        fit = awareness and awareness in (arcs.get(p.get("arc") or "", {}).get("best_for") or [])
        if fit:
            score += 10
            why.append("its arc (%s) is listed for %s" % (p.get("arc"), awareness))
        if length and p["length"] == length:
            score += 5
            why.append("runs %s" % length)
        score -= (p.get("seconds") or 0) / 60.0
        out.append((score, p, why))
    out.sort(key=lambda x: -x[0])
    return [(p, "; ".join(why) or "fits the format") for _s, p, why in out]


# ------------------------------------------------------------------ what a writing pass is handed

def _clock(pct, seconds):
    s = round(seconds * pct / 100.0)
    return "%d:%02d" % (s // 60, s % 60)


def block(p, seconds=None):
    """The preset as the writer reads it: the shape to fill, at its own length (or `seconds`), every slot to be
    filled from the brand's research already in the prompt, and our nine checks. Brand-free by construction."""
    secs = seconds or p.get("seconds") or 45
    beats = "\n".join("| %d–%d%% | %s–%s | %s |" % (b["from_pct"], b["to_pct"], _clock(b["from_pct"], secs),
                                                     _clock(b["to_pct"], secs), b["beat"]) for b in p["beats"]) \
        or "| — | — | (this card has no timed beats: its shape is the song line's) |"
    pe = p.get("product") or {}
    f = p.get("format") or {}
    lines = [
        "## THE STORY PRESET — `%s` (%s), read this before anything else" % (p["id"], p["name"]), "",
        "This piece is written in the story preset below. Its SHAPE is fixed: the beats at their marks, where the "
        "product enters and how it shows, the cast roles, the tone and sound, the captions and the length. EVERYTHING "
        "INSIDE the shape is ours and comes from this prompt's own inputs, never from the preset: the hero, the "
        "problem, the creature or rival, the places, the props, the jokes and every line come from the avatar file, "
        "the culture map, the customer's verbatim words, the objection bank and the offer bank; the product's name, "
        "claims and last line come from the product file and offer bank only; the dials and the house rules hold as "
        "they are. Where this pass's own instructions point at the swipe's beats, use the preset's beats instead and "
        "say so in one line. The preset names no brand and no product; if a detail is missing from our research, "
        "say what is missing rather than inventing a claim.", "",
        "**Logline (the card's, as the shape):** %s" % p.get("logline", ""), "",
        "**Format:** script format `%s` · production format `%s` · look `%s`%s · playbook `%s` · %s, %ss (%s)" % (
            f.get("script_format"), f.get("production_format"),
            f.get("style") or f.get("element_style") or "none on our lists",
            " (from the element bank; not yet on the locked names list)" if not f.get("style") and f.get("element_style")
            else (" (gap: %s)" % f["style_gap"] if f.get("style_gap") and not f.get("style") else ""),
            f.get("playbook"), p["hf_style"], secs, _length_name(secs)),
        "Where the preset says \"the user\" (the user's line, their tagline, their offer), read OUR brand: its line "
        "and offer come from the offer bank and product file, never invented.",
        "**Arc:** `%s`%s" % (p.get("arc"), (" · devices: " + ", ".join("`%s`" % x for x in p.get("devices") or []))
                             if p.get("devices") else ""), "",
        "### Beats, at their marks", "", "| Share | Time | What happens |", "|---|---|---|", beats, "",
        "### The product in the piece", "",
        "Enters at %s%% (%s). %s" % (pe.get("enters_pct", "—"),
                                     _clock(pe["enters_pct"], secs) if pe.get("enters_pct") is not None else "—",
                                     pe.get("how", "")), "",
        "### Cast roles", "", p.get("cast", ""), "",
        "### Tone, sound and look", "", p.get("tone", ""), "",
        "### Captions", "", p.get("captions") or "as the format's caption look says", "",
        "### Details we fill (from our research, never the first stock choice)", "", p.get("invent", ""), "",
        "### Our nine checks — answer each yes in one line at the end of this pass's output, or fix it first", "",
    ]
    lines += ["%d. **%s** — %s" % (i + 1, c["id"], c["ask"]) for i, c in enumerate(CHECKS)]
    lines += ["", "## END OF THE STORY PRESET", "", ""]
    return "\n".join(lines)


def check_lines():
    return ["%s: %s" % (c["id"], c["ask"]) for c in CHECKS]


# ------------------------------------------------------------------ the mechanical half of the check, on a brief

def check_brief(brief, p):
    """Code checks on a written brief's scene block (dict with `scenes`) against its preset. Returns notes (str):
    never a hold — only money and law hold a script (video-writing holds.py). Empty list = nothing to say."""
    notes = []
    scenes = (brief or {}).get("scenes") or []
    if not scenes:
        return ["story preset %s: the brief has no scene block to check" % p["id"]]
    secs = (brief.get("piece") or {}).get("seconds") or p.get("seconds") or 0

    def start(s):
        for k in ("start", "t_start", "from"):
            if isinstance(s.get(k), (int, float)):
                return float(s[k])
        return None

    def words(s):
        return " ".join(str(s.get(k) or "") for k in ("happens", "words", "voice", "lyrics", "action", "beats")).lower()

    first = scenes[0]
    if start(first) not in (None, 0.0):
        notes.append("hook-3s: the first scene starts at %ss, not 0" % start(first))
    vo = str(first.get("voice") or first.get("words") or "")
    if len(vo.split()) > 12:
        notes.append("hook-3s: the first scene opens on %d spoken words; the conflict should land before talk"
                     % len(vo.split()))
    pe = (p.get("product") or {}).get("enters_pct")
    prod = [i for i, s in enumerate(scenes) if "product" in words(s) or s.get("product")]
    if pe is not None and prod and secs:
        at = start(scenes[prod[0]])
        if at is not None and abs(at / secs * 100 - pe) > 15:
            notes.append("product entry: first product scene at %d%%, the preset says %d%%" % (at / secs * 100, pe))
    elif pe is not None and not prod:
        notes.append("product entry: no scene shows the product; the preset brings it in at %d%%" % pe)
    last = scenes[-1]
    if not any(last.get(k) for k in ("action", "happens", "beats")):
        notes.append("ending: the last scene names no visible action")
    return notes


# ------------------------------------------------------------------ building the manifest from the captures

def _card(f):
    m = re.search(r"```json\n(.*?)\n```", f.read_text(), re.S)
    return json.loads(m.group(1))


def _sections(prompt):
    return {k.strip(): " ".join(v.split()) for k, v in re.findall(r"^## (.+?)\n(.*?)(?=^## |\Z)", prompt, re.M | re.S)}


def _beats(structure):
    """'0-7%: text. 7-20%: text.' -> [{from_pct, to_pct, beat}]"""
    marks = list(re.finditer(r"(\d+)\s*-\s*(\d+)%:\s*", structure))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(structure)
        text = structure[m.end():end].strip()
        text = re.sub(r"\s*These shares hold at any length\.?$", "", text)
        out.append({"from_pct": int(m.group(1)), "to_pct": int(m.group(2)), "beat": text})
    if out and out[-1]["to_pct"] < 100:     # a card that stops short leaves the end card unwritten: say so
        out.append({"from_pct": out[-1]["to_pct"], "to_pct": 100,
                    "beat": "(unwritten on the card) the end card: the product and our line from the offer bank."})
    return out


def _captions(settings):
    s = settings.lower()
    if "no captions" in s or "captions off" in s:
        return "none"
    m = re.search(r"(caption[^.]*\.)", settings, re.I)
    return m.group(1) if m else None


def _format(family, settings):
    s = settings.lower()
    talk = "dialogue" in s and "storytime" not in s
    fmt = {"script_format": "micro-drama", "production_format": "multi-speaker-scene",
           "style": None, "style_gap": None, "playbook": "multi-speaker-scene", "hook_format": None}
    if family == "singing":
        fmt.update(script_format=None, production_format="song-ad", playbook="song-ad", style=None,
                   style_gap="the card's own look (a song card names none)")
        return fmt
    if not talk:
        fmt.update(script_format="personal-story", production_format="narrator-montage", playbook="narrator-montage")
    if family in ("micro-drama", "cinematic"):
        fmt["style_gap"] = "live-action film (cinematic, locked-off, graded)"
    elif family in ("cartoon", "talking-object") or "feature-3d" in s:
        fmt["style"] = "family-3d"
    if family == "talking-object":
        fmt["playbook"] = "talking-object"
    if family == "doll":
        fmt.update(style_gap="doll-world 3D", playbook="short-movie" if talk else fmt["playbook"])
    if family == "claymation":
        fmt.update(style=None, style_gap="claymation (stop-motion puppets)")
    if family == "crochet":
        fmt.update(style=None, style_gap="needle-felted / crochet")
    if family == "inside-the-body":
        fmt.update(hook_format="3d-body-animation", style="family-3d")
    look = {"micro-drama": "live-action", "cinematic": "live-action", "cartoon": "feature-3d",
            "talking-object": "feature-3d", "claymation": "claymation", "crochet": "needle-felted",
            "doll": "doll-3d", "inside-the-body": "cutaway-lab"}.get(family)
    fmt["element_style"] = ELEMENT_ALIAS.get(look)        # the element bank's look that makes it (scratch --style)
    named = {"micro-drama": "cinematic-live", "cinematic": "cinematic-live", "claymation": "claymation",
             "crochet": "needle-felt", "doll": "art-toy"}.get(family)   # looks on the names list (owner, 2026-11-21)
    if not fmt["style"] and named in _names()["style"]:
        fmt.update(style=named, style_gap=None)
    return fmt


def _product(prod_text, beats):
    m = re.search(r"(\d+)%", prod_text)      # the card's first mark is where the product enters
    pct = int(m.group(1)) if m else None
    if pct is None:
        hit = next((b for b in beats if re.search(r"\bproduct\b", b["beat"], re.I)), None)
        pct = hit["from_pct"] if hit else None
    return {"enters_pct": pct, "how": prod_text}


def _devices(text):
    return [d for d, pat in DEVICE_WORDS if re.search(pat, text, re.I)]


def _entry(f, card):
    pid = f.stem
    family = HF_FAMILY.get(card["style"]["title"], card["style"]["title"].lower())
    prompt = card.get("prompt") or ""
    sec = _sections(prompt)
    seconds = (card.get("settings") or {}).get("duration_seconds")
    src = "%s/%s" % (CATALOG_REL, f.name)
    if not prompt.startswith("/drama-ads"):
        return {"id": pid, "name": card["title"], "status": "draft", "state": "song-line-card",
                "hf_style": family, "format": _format(family, ""), "seconds": seconds, "length": "short",
                "logline": "A singing ad on the card's song; the card is an example of the result, never a source.",
                "beats": [], "product": {"enters_pct": None, "how": "as the song line places it"},
                "cast": "", "tone": "", "captions": None, "invent": "", "arc": None, "devices": [],
                "runs_on": "components/workflow-teardown/recipes/singing-ads.md", "source": src}
    beats = _beats(sec.get("Structure", ""))
    logline = prompt.split("\n", 2)[1].strip()
    if not logline.endswith("."):
        logline = " ".join(prompt.split("\n\n")[0].split()[1:])
    invent = sec.get("Details you invent", "")
    m = re.search(r"invent the details that fill the parts above: ([^.]*)\.", invent)
    return {
        "id": pid, "name": card["title"], "status": "draft", "state": "arc-picked-by-session",
        "hf_style": family, "format": _format(family, sec.get("Settings", "")),
        "seconds": seconds, "length": _length_name(seconds), "logline": logline,
        "beats": beats, "product": _product(sec.get("The product in the film", ""), beats),
        "cast": sec.get("Cast", ""), "tone": sec.get("Tone, sound and look", ""),
        "captions": _captions(sec.get("Settings", "")),
        "invent": (m.group(1) if m else "names, places, props, looks, lines and jokes")
        + " — each from the product, its buyers, where it is used and what goes wrong without it",
        "arc": SEED_ARC.get(pid), "devices": _devices(sec.get("Structure", "") + " " + sec.get("Cast", "")),
        "runs_on": "components/workflow-teardown/recipes/drama-ads.md", "source": src,
    }


# ------------------------------------------------------------------ the other shelves: everything else they make
# Beyond the drama cards: the 80 slash recipes (one picture or one clip each), every format their workflows make,
# every named look, and the live galleries not yet captured. Each row says what OURS is for it, or that we have none
# (the gap). Ours is a names.json id, never a coined name (a gap is a gap until the owner names it).

HF = WS / "components/workflow-teardown/sources/higgsfield"
HF_REL = "components/workflow-teardown/sources/higgsfield"

# their format -> (kind, our production format, our script format, our style, our recipe or tool, note)
THEIR_FORMATS = [
    # id, name, from, what, kind, production_format, script_format, ours_tool
    ("drama-ads", "Drama ads (47 story cards)", "drama-ads", "a timed story ad, 9 looks", "story",
     "multi-speaker-scene", "micro-drama", "story presets (this file) + recipes/drama-ads"),
    ("short-drama", "Short drama series", "commands/short-drama.md", "an episodic vertical drama series, 15 looks",
     "story", "multi-speaker-scene", "micro-drama", None),
    ("singing-ads", "Singing ads", "commands/singing-ads.md", "the product's own song, sung over scenes", "story",
     "song-ad", None, "recipes/singing-ads + video-production song line"),
    ("music-cards", "Music cards", "music-cards", "a 20-120 s cartoon with an original song about one person",
     "story", "song-ad", None, None),
    ("what-if-shorts", "What-if shorts", "commands/content-factory.md", "a 'what would happen if' scenario short, "
     "30 looks", "story", "narrator-montage", None, None),
    ("faceless-video", "Faceless channel video", "faceless-video", "a narrated explainer/story channel video, 21 "
     "house looks", "story", "narrator-montage", "tips-then-pitch", "video-production narrator-montage"),
    ("shorts", "Shorts Studio reels", "commands/shorts.md", "a presenter reel from a topic or script, live preset "
     "gallery", "story", "single-presenter", None, None),
    ("manga", "Manga / comics", "commands/manga.md", "black-and-white or colour manga and comic pages", "story",
     None, None, None),
    ("ugc-review", "UGC review", "ugc-video/references/formats/review.md", "one creator demonstrates or tells a "
     "story; product optional", "ugc", "single-presenter", "personal-story", "video-production single-presenter"),
    ("ugc-product", "UGC product voiceover", "ugc-video/references/formats/product.md", "product is the hero, "
     "off-screen voice", "ugc", "narrator-montage", "demonstration", "video-production narrator-montage"),
    ("ugc-unboxing", "UGC unboxing", "ugc-video/references/formats/unboxing.md", "a creator opens the pack and "
     "reacts", "ugc", "single-presenter", None, None),
    ("ugc-try-on", "UGC try-on", "ugc-video/references/formats/try-on.md", "a creator wears it, shows fit and "
     "texture", "ugc", "single-presenter", "demonstration", None),
    ("ugc-tutorial", "UGC tutorial", "ugc-video/references/formats/tutorial.md", "step-by-step use with Step N "
     "labels", "ugc", "single-presenter", "demonstration", "video-production single-presenter"),
    ("ugc-website", "UGC website", "ugc-video/references/formats/website.md", "a presenter over a captured site or "
     "app", "ugc", "single-presenter", None, None),
    ("ad-multiplier", "Ad multiplier", "ad-multiplier", "one 4-30 s ad remade with new people, product, market",
     "variation", None, None, "components/ad-variations (plans only, makes nothing)"),
    ("katana", "Katana remix", "katana", "a reference video remixed onto your subject", "variation", None, None,
     None),
    ("genjutsu", "Genjutsu motion and styles", "commands/genjutsu.md", "motion transfer or object replacement on a "
     "driving video; 20 restyle looks", "variation", None, None, "components/motion (motion transfer, our own)"),
    ("angles", "Angles", "angles-hf", "a one-camera take re-shot as a multi-camera edit", "edit", None, None, None),
    ("creator-dub", "Creator dub", "creator-dub", "a creator's video dubbed with lip sync", "edit", None, None,
     None),
    ("reel-effects", "Reel effects", "reel-effects", "text-behind, grade wipe and fixed effects on a talking head",
     "edit", None, None, "components/video-edit (captions, looks)"),
    ("grade", "Colour grades (34)", "grade-hf", "34 colour grades as a video edit", "edit", None, None, None),
    ("lighting", "Lighting looks (62)", "lighting-hf", "62 relighting looks as a video edit", "edit", None, None,
     None),
    ("layer-reveal", "Layer reveal", "layer-reveal-hf", "a hero painted into a scene, layers fade in under a "
     "loading bar", "hook", None, None, None),
    ("monsters", "Monsters", "monsters", "photoreal creatures from a grey sculpt and real materials", "asset", None,
     None, "components/objects + 3d"),
    ("character-sheet", "Character sheet", "character-sheet", "a reusable cast reference: face, outfit, 3-panel "
     "sheet", "asset", None, None, "components/casting"),
    ("product-photoshoot", "Product photoshoot", "product-photoshoot", "packshots, lifestyle, hero banners, pins",
     "still", None, None, "components/image-production"),
    ("ads-studio", "Ads Studio statics", "ads-studio", "static ads with copy and pictures from a brand or product",
     "still", None, None, "components/image-teardown + image-writing + image-production"),
    ("thumbnail", "Thumbnails", "thumbnail-generation", "video covers and thumbnails", "still", None, None, None),
    ("video-montage", "Video montage", "video-montage", "clips assembled, soundtrack, burned captions", "edit",
     None, None, "components/video-edit"),
    ("video-editing", "Higgsedit", "video-editing", "cuts, trims, motion graphics on supplied footage", "edit", None,
     None, "components/video-edit (HyperFrames)"),
    ("enhance", "Enhance video", "higgsfield-enhance-video", "upscale or enhance a video to 1080p", "edit", None,
     None, "components/local-studio (upscale)"),
    ("photo-to-3d", "Photo to 3D model", "photo-to-3d-model", "one photo to a textured GLB", "asset", None, None,
     "components/3d"),
    ("brand-assets", "Brand asset creation", "brand-asset-creation", "logos, kits, mockups, packaging", "still",
     None, None, None),
    ("narration", "Narration", "narration", "timed voice takes fitted to video windows", "edit", None, None,
     "components/audio-teardown + voice door"),
]

# their look -> our names.json style id when one is close enough to stand in, else None (a gap)
LOOK_OURS = {"feature-3d": "family-3d", "feature3d": "family-3d", "classic_3d": "family-3d", "colorful-3d":
             "family-3d", "studio-3d": "family-3d", "anime": "anime", "low-poly": "low-poly",
             "lowpoly-skyline": "low-poly", "frost-lowpoly": "low-poly", "canyon-crowd": "low-poly",
             "phone": "phone-ugc", "classic_2d": "cel-1950s", "rubber-hose": "cel-1950s",
             "stickman-cartoon": "stick-explainer", "whiteboard-doodle": "stick-explainer",
             # added to the names list on the owner's word, 2026-11-21
             "live-action": "cinematic-live", "realism_cinematic": "cinematic-live", "claymation": "claymation",
             "clay": "claymation", "claymotion": "claymation", "pastel-clay": "claymation", "doll-3d": "art-toy"}


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _json_block(f):
    return json.loads(re.search(r"```json\n(.*?)\n```", f.read_text(), re.S).group(1))


def _shots():
    cat = _json_block(HF / "_catalog-presets.md")["presets"]
    out = []
    for r in cat:
        f = HF / "presets" / ("%s.md" % r["id"])
        params = {}
        if f.is_file():
            m = re.search(r"## Generation parameters\s*```json\n(.*?)\n```", f.read_text(), re.S)
            params = json.loads(m.group(1)) if m else {}
        d = r.get("description") or ""
        person = re.search(r"\b(person|portrait|human|recognizable|transformation|werewolf|zombie|vampire|"
                           r"spellcaster|pumpkin)\b", d, re.I)
        family = "still" if r["output_type"] == "image" else ("person-effect" if person else "product-motion")
        out.append({"id": r["id"], "name": r["title"], "status": "draft", "output": r["output_type"],
                    "family": family, "what": d, "model": params.get("model"),
                    "settings": {k: v for k, v in params.items() if k != "model"},
                    "ours": {"still": "components/image-production", "product-motion": "video-production clip door",
                             "person-effect": None}[family],
                    "brief_use": {"still": "a static ad or an end card", "product-motion": "a product shot inside "
                                  "a video brief (pack shot, demo insert, end card)", "person-effect": "a hook "
                                  "(hook format vfx-stunt-hook)"}[family],
                    "source": "%s/presets/%s.md" % (HF_REL, r["id"])})
    return out


def _formats(names):
    out = []
    for fid, name, frm, what, kind, prod, script, tool in THEIR_FORMATS:
        src = HF / frm
        out.append({"id": fid, "name": name, "status": "draft", "kind": kind, "what": what,
                    "ours": {"production_format": prod if prod in names["production_format"] else None,
                             "script_format": script if script in names["script_format"] else None,
                             "tool": tool},
                    "state": "covered" if (prod or tool) else "gap",
                    "source": "%s/%s" % (HF_REL, frm) if src.exists() else None})
    return out


def _looks(names):
    rows = []
    try:
        elements = {r["id"] for r in json.loads(ELEMENT_STYLES.read_text())["rows"]}
    except (OSError, ValueError, KeyError):
        elements = set()

    def add(lid, name, frm, what=""):
        ours = LOOK_OURS.get(lid)
        el = ELEMENT_ALIAS.get(lid) or ELEMENT_ALIAS.get(_slug(name)) or (_slug(name) if _slug(name) in elements else None)
        if any(r["id"] == "%s:%s" % (frm.split("/")[0], lid) for r in rows):
            return                                  # a look named twice in its source is one look
        rows.append({"id": "%s:%s" % (frm.split("/")[0], lid), "name": name, "status": "draft", "from": frm,
                     "what": what, "ours": ours if ours in names["style"] else None,
                     "element_style": el if el in elements else None,
                     "state": "covered" if ours in names["style"] else
                     ("element-only" if el in elements else "gap")})
    for f in sorted((HF / "drama-ads/scripts/styles").glob("*.md")):
        add(f.stem, f.stem.replace("-", " ").capitalize(), "drama-ads/scripts/styles")
    t = (HF / "commands/short-drama-references-styles.md").read_text()
    for lid, name in re.findall(r"^### `([^`]+)` (.+)$", t, re.M):
        add(lid, name.strip(), "short-drama/looks")
    t = (HF / "commands/music-cards-references-styles.md").read_text()
    for lid, name in re.findall(r"^## `([^`]+)`: (.+)$", t, re.M):
        add(lid, name.strip(), "music-cards/looks")
    t = (HF / "commands/content-factory.md").read_text()
    for lid, name, what in re.findall(r'^- `([^`]+)` "([^"]+)": "([^"]+)"', t, re.M):
        add(lid, name, "what-if/looks", what)
    t = (HF / "faceless-video/references/preset-catalog.md").read_text()
    for name in re.findall(r"^\s+- ([^—\n]+?) — `[0-9a-f-]{36}`", t, re.M):
        add(_slug(name.split("(")[0]), name.strip(), "faceless/looks")
    return rows


# The live galleries, counted read-only on 2026-11-21 (get_presets totals; nothing generated). Not yet captured
# item by item: the next capture pulls them through tools/harvest.py like the rest.
GALLERIES = [
    {"id": "marketing-studio", "name": "Marketing Studio templates", "count": 649, "state": "counted-not-captured",
     "what": "product shots, product shots with people, hypermotion, 2D motion, mixed media, SaaS motion, effects"},
    {"id": "viral", "name": "Viral Hub effects", "count": 87, "state": "counted-not-captured",
     "what": "chained effect presets (e.g. a fall with belongings floating, product close-ups mid-air)"},
    {"id": "soul", "name": "Soul image styles", "count": 33, "state": "counted-not-captured",
     "what": "curated photo styles for the Soul image model"},
    {"id": "genjutsu-styles", "name": "Genjutsu restyle looks", "count": 20, "state": "counted-not-captured",
     "what": "looks that redraw your own video, motion kept (knitted yarn, rounded toy CGI, felt puppet ...)"},
    {"id": "genjutsu-motion", "name": "Genjutsu motion presets", "count": None, "state": "counted-not-captured",
     "what": "driving videos for motion transfer and object replacement (paged past 1,000)"},
    {"id": "katana", "name": "Katana remix presets", "count": None, "state": "widget-only",
     "what": "community and Higgsfield remixes, personalised edits, style and motion transfer"},
    {"id": "shorts-studio", "name": "Shorts Studio presets", "count": None, "state": "widget-only",
     "what": "presenter reel styles"},
]


def _names():
    try:
        n = json.loads(NAMES.read_text())
        return {k: {x["id"] for x in n[k]["names"]} for k in ("production_format", "script_format", "style")}
    except (OSError, ValueError, KeyError):
        return {"production_format": set(), "script_format": set(), "style": set()}


def build(check=False):
    old = {}
    if MANIFEST.is_file():
        old = {p["id"]: p for p in load().get("presets") or []}
    presets = []
    for f in sorted(CATALOG.glob("*.md")):
        if f.name.startswith("_"):
            continue
        e = _entry(f, _card(f))
        for k in CURATED:
            if k in old.get(e["id"], {}):
                e[k] = old[e["id"]][k]
        presets.append(e)
    names = _names()
    doc = {
        "schema": "story-presets/v1",
        "what": "Story presets: one fully timed story inside a format, brand-free, filled by the writing chain with "
                "the brand's own research, dials and house rules. First shelf: the 47 Higgsfield Drama Ads cards, as "
                "our structured version (the capture stays data, workspace rule 8).",
        "status_values": ["draft", "approved", "deprecated"],
        "curated_fields": list(CURATED),
        "built_by": "components/creative-controls/story_presets.py build",
        "checks": CHECKS,
        "presets": presets,
        "shots": _shots(),
        "formats": _formats(names),
        "looks": _looks(names),
        "galleries": GALLERIES,
    }
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    if check:
        return MANIFEST.is_file() and MANIFEST.read_text() == text
    MANIFEST.write_text(text)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description="Story presets: list, show, pick, build.")
    sub = ap.add_subparsers(dest="cmd")
    ls = sub.add_parser("list")
    ls.add_argument("--format")
    ls.add_argument("--hf-style")
    sh = sub.add_parser("show")
    sh.add_argument("id")
    pk = sub.add_parser("pick")
    pk.add_argument("--format")
    pk.add_argument("--awareness")
    pk.add_argument("--length", choices=["short", "long"])
    pk.add_argument("--used", default="")
    b = sub.add_parser("build")
    b.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        ok = build(check=a.check)
        print("story presets: %s" % ("current" if ok and a.check else "written" if ok else "OUT OF DATE — run build"))
        return 0 if ok else 1
    if a.cmd == "show":
        print(block(get(a.id)))
        return 0
    if a.cmd == "pick":
        for p, why in pick(a.format, a.awareness, a.length, [x for x in a.used.split(",") if x])[:5]:
            print("%-22s %-16s %4ss  %s" % (p["id"], p["hf_style"], p["seconds"], why))
        return 0
    for p in load()["presets"]:
        if (a.cmd == "list" and a.format and p["format"].get("script_format") != a.format) or \
                (a.cmd == "list" and a.hf_style and p["hf_style"] != a.hf_style):
            continue
        print("%-22s %-8s %-16s %4ss  %-18s %s" % (p["id"], p["status"], p["hf_style"], p["seconds"], p.get("arc"),
                                                  p["name"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
