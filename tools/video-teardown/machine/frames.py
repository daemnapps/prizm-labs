#!/usr/bin/env python3
"""Stage 6 — a generated frame on every scene. No gaps.

    python3 frames.py --brief <brief.md> --video <source.mp4> --out <dir>

Damon's rule (2026-08-21): every scene gets a picture. The shared runner drops
frames when the generated person does not match the seed still, or when it
judges a scene unusable — this one does not. It generates for every scene, and
if generation fails outright it falls back to the still cut from the video so
the scene still has something to look at.

The seed still keeps the place and the light consistent between scenes.
"""

import argparse, base64, json, os, re, subprocess, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keys

# Best model, always (Damon, 2026-08-25). The 08-21 note below it chose the
# cheapest tier because these were reference frames a creator glanced at.
# They are becoming ad assets, so the job changed and the choice with it —
# image generation is cheap next to video, so there is no reason to run
# anything but the best. Override per run with --image-model.
#   gemini-3-pro-image        Nano Banana Pro   best, slowest, sometimes busy
#   gemini-3.1-flash-image    Nano Banana 2     very good, fast
#   gemini-3.1-flash-lite-image                 the old default
# Pro is the default (Damon, 2026-08-25, revised same day). Flash held the
# default for one afternoon because Pro's 250/day cap used to kill a whole run
# the moment it was spent — topping up does not move it, it is a daily quota,
# not credit. The per-frame fallback below now catches that case and finishes
# the run on Flash, so the reason is gone and the frames were visibly cheaper
# for it. At ~29 frames a video the cap is roughly eight videos a day; past
# that the run finishes on Flash and says how many frames it had to hand over.
MODEL = os.environ.get("FRAMES_MODEL", "gemini-3-pro-image")

# Whatever MODEL is, this is the other one to try before giving up on a frame.
FALLBACK = ("gemini-3.1-flash-image"
            if MODEL != "gemini-3.1-flash-image" else "gemini-3-pro-image")

# Vertical, to match the ads these frames are shot for. 2K is the useful
# ceiling for a reference frame; Pro will go to 4K if ever needed.
ASPECT = "9:16"
SIZE = "2K"
WORKERS = 6   # concurrent frames; higher starts drawing rate limits
BASE = "https://generativelanguage.googleapis.com"

# Stated on every generation. Clothing and the product's real look are the two
# things that go wrong when left to the model's imagination.
# Rewritten 2026-08-25 in positive framing. Google's guidance for this model
# is explicit — "describe what you want, not what you don't want" — and the
# old version was almost entirely negations ("no smoothing, no beautifying,
# no captions"), which names the thing and puts it in front of the model.
# It says nothing about WHERE. It used to: "available light from the windows
# already in the room", "walls ... are plain and unmarked" — an interior
# hardcoded into the one instruction appended to every frame. On a shoot that
# happens entirely on a beach that put her in a bedroom (Damon, 2026-08-26).
# The scene names the place; this only says how the picture is taken.
GUARD = (
    # POSITIVE FRAMING, and it applies to the camera too. The old text said
    # "a phone photograph, handheld at chest height, the way someone filming
    # themselves would hold it" and got a hand holding a phone drawn into the
    # shot, caption rendered on its little screen (Damon, 2026-08-26). Adding
    # "no phone, no camera, no hand" made it worse for the reason already
    # written above: naming a thing puts it in front of the model. So neither
    # word appears here at all. This describes the LOOK — off-centre framing,
    # available light, real skin, flat colour — and nothing else.
    "A candid vertical snapshot, framed slightly off-centre and a little "
    "imperfectly, the way an unposed picture of a real moment comes out. "
    "Lit only by the light already falling on the scene described above, "
    "wherever that scene takes place, with no added lamps and no studio "
    "lighting. Real skin, with visible pores, fine lines and uneven tone. "
    "Flat, unretouched, ungraded colour. Clothing and background surfaces "
    "are plain and unmarked, and the image is one continuous moment in a "
    "single frame. "
    # The product legitimately has a label; everything else must not. Saying
    # "no lettering anywhere" while the product line says "gold-cream
    # lettering" is a contradiction, and the model resolves it by inventing
    # mirrored nonsense text on the tube — seen 2026-08-25.
    "Aside from the product's own label and any caption named above, no other "
    "lettering appears anywhere in the frame, and what does appear is legible "
    "and the right way round. "
)

# Captioned formats are the norm in this feed, and the caption is part of what
# the frame IS — the source's opening is a keyed talking head with the line
# burned across it. Until v18 the brief dropped the caption and every
# generated frame came back clean, so a creator could not see the format.
CAPTION_DIRECTION = (
    "Burned into the picture as a caption, styled exactly this way — {style} "
    "— and reading: {text} Reproduce that wording exactly, spelled as "
    "written, in that one style, and put no other words anywhere in the "
    "frame. Every frame in this set uses the identical caption treatment. "
)

# Used only when the teardown did not record the source's overlay style.
CAPTION_STYLE_DEFAULT = "white sans-serif, bottom-centre, no box behind it"

# The scene text is written TO the person filming — "turn your forearms toward
# the window". Handed to an image model that is an instruction with no subject
# in it, so it invented a person every time and the frames matched nothing.
#
# The subject stays a neutral noun phrase. It used to be "she", which made every
# generated frame female whatever the run was about — a brand assumption in code
# (rule 4). Who the person is comes from the face anchor, which is an actual
# photograph; the words do not need to guess it.
SUBJECT = "the person"
SUBJECT_C = SUBJECT[0].upper() + SUBJECT[1:]
POSS = "their"

# The cast block arrives as ONE line, so an outfit's text must stop at the
# next "Outfit X" rather than at a newline — otherwise the first match eats
# the whole menu and nothing can be subtracted (caught 2026-09-02).
OUTFIT_LINE = re.compile(
    r"\*{0,2}Outfit\s+([A-Z])\*{0,2}\s*(?:\(([^)]*)\))?\s*:?\*{0,2}\s*"
    r"(.*?)(?=\*{0,2}Outfit\s+[A-Z]|$)", re.I | re.S)


def one_outfit(block, sc):
    """A cast block lists every outfit a character wears across the piece.
    Pasting all of them hands the model a menu and it blends them — that is
    how the mistress's denim jacket landed on the lead (2026-09-02). Keep
    only the outfit whose scene range covers this scene; if none can be
    matched, keep none and let the scene's own Wearing line rule."""
    found = OUTFIT_LINE.findall(block)
    if len(found) <= 1:
        return block
    n = None
    m = re.search(r"(\d+)", str(sc.get("n") or sc.get("key") or ""))
    if m:
        n = int(m.group(1))
    keep = None
    for letter, scope, text in found:
        if n is not None and scope:
            rng = re.findall(r"(\d+)", scope)
            if len(rng) >= 2 and int(rng[0]) <= n <= int(rng[-1]):
                keep = (letter, scope, text); break
            if len(rng) == 1 and int(rng[0]) == n:
                keep = (letter, scope, text); break
    # strip every outfit line out, then put back at most the one that applies
    out = OUTFIT_LINE.sub("", block)
    out = " ".join(out.split())
    if keep:
        out += f" Wearing: {keep[2].strip()}"
    return out


def as_picture(shot, subject=SUBJECT):
    S = subject[0].upper() + subject[1:]
    out = shot
    for a, b in (
        ("You are", f"{S} is"), ("you are", f"{subject} is"),
        ("You're", f"{S} is"), ("you're", f"{subject} is"),
        ("You have", f"{S} has"), ("you have", f"{subject} has"),
        (" your ", f" {POSS} "), ("Your ", f"{POSS.capitalize()} "),
        (" you ", f" {subject} "), ("You ", f"{S} "),
        ("Hold ", f"{S} holds "), ("Turn ", f"{S} turns "),
        ("Run ", f"{S} runs "), ("Keep ", f"{S} keeps "),
        ("Look ", f"{S} looks "), ("Pick ", f"{S} picks "),
        ("Squeeze ", f"{S} squeezes "), ("Rub ", f"{S} rubs "),
        ("Don't ", f"{S} does not "), ("Show ", f"{S} shows "),
    ):
        out = out.replace(a, b)
    return out


# Stops at the next bold marker: the brief often puts the text-card note on the
# same line, and it was ending up inside the wardrobe — so the prompt said "no
# on-screen text" and then described the text card.
WARDROBE = re.compile(r"\*\*Wearing:?\*\*\s*(.+?)(?=\*\*|\n|$)", re.I)

# Stage 5 v17 adds a Hear: line to every scene. It is direction for the
# person filming, not something in the picture — left in, the generator
# tries to draw the sound ("nothing but the room" became empty rooms).
SOUND = re.compile(r"\*\*Hear:?\*\*\s*(.+?)(?=\*\*|\n|$)", re.I)

# v18 renamed the unit from Scene to Frame — every cut is now its own entry.
# Both spellings are accepted so briefs written before that still parse.
# Openings are units too (brief v22). They are the shots being tested and
# the hardest for a maker to picture from words, since they are all the
# same moment shot differently — exactly what an image carries and a
# paragraph does not.
SCENE = re.compile(r"\*\*(?:Frame|Scene|Opening) (\d+)\s*·\s*([^*]+?)\*\*")

# The caption burned into the picture. The teardown always captured it in its
# On-Screen Text column; until v18 the brief dropped it, so every generated
# frame came back clean when the source format was captioned throughout.
# v19 adds a Source: line naming the shot each frame replaces. It is an
# audit reference for humans, not part of the picture — left in, the model
# tries to draw the competitor's shot description as well as ours.
SOURCESHOT = re.compile(r"\*\*Source:?\*\*\s*(.+?)(?=\*\*|\n|$)", re.I)

ONSCREEN = re.compile(r"\*\*On[- ]screen(?: text)?:?\*\*\s*(.+?)(?=\*\*|\n|$)", re.I)

# The Film line is written for the person filming, so it says where to PUT the
# camera — "Phone on the sand, tilted slightly up, lens twelve inches off the
# ground". Handed to an image model that is a description of things to draw,
# and it drew them: a phone lying in the sand with the shot on its screen
# (2026-08-26). The rig is not in the picture. These clauses go.
RIG = re.compile(
    r"(?:^|(?<=[.;]))\s*(?:the\s+)?"
    r"(?:phone|camera|lens|tripod)\b[^.;]*[.;]?", re.I)


def drop_rig(text):
    """Take the camera setup out of a shot description, keep the picture."""
    out = RIG.sub(" ", text or "")
    return re.sub(r"\s{2,}", " ", out).strip()


def say(m):
    print(m, flush=True)


def parse_cast(md):
    """The brief's locked THE CAST blocks — every character written once,
    to be reproduced identically wherever they appear. The brief's own shape
    says the scenes station pastes these into every generation; until
    2026-08-31 nothing did, so a supporting character was re-imagined per
    frame and drifted (the strawberry-legs run's helper). {NAME: block}."""
    cast = {}
    for section in re.findall(r"## THE CAST\n(.*?)(?=\n## )", md, re.S):
        for chunk in re.split(r"\n(?=\*\*[A-Z][A-Z .'’-]*\*\*)", section):
            h = re.match(r"\*\*([A-Z][A-Z .'’-]*)\*\*", chunk)
            if h:
                # voice is for the voice station; an image prompt carrying it
                # is noise at best, drawn-on sound at worst
                blk = re.sub(r"\*\*Voice:\*\*.*?(?=\n\*\*|\n\n|\Z)", "",
                             chunk, flags=re.S)
                cast[h.group(1).strip()] = " ".join(
                    blk.replace("**", "").split())
    return cast


def parse(md):
    """Every scene AND every opening, keyed by concept and number.

    Concepts each restart at 1, so the number alone would collapse them — and
    openings restart at 1 independently of scenes, so they carry their own
    letter. Openings are units in their own right (brief v22): they are the
    shots being tested, and the hardest thing to picture from words alone."""
    out, concept, ci = [], "", 0
    for block in re.split(r"\n(?=\*\*(?:Frame|Scene|Opening) \d+|# )", md):
        h = re.match(r"# (.+)", block)
        if h and not re.match(r"\*\*(?:Frame|Scene|Opening) ", block):
            concept, ci = h.group(1).strip(), ci + 1
        m = SCENE.match(block)
        if not m:
            continue
        is_opening = block.lstrip().startswith("**Opening")
        wear = WARDROBE.search(block)
        cap = ONSCREEN.search(block)
        # the scene text is everything before the quote and the picture slot
        body = re.sub(r"^\*\*(?:Frame|Scene|Opening)[^\n]*\n", "", block)
        body = re.split(r"\n!\[(?:Frame|Scene|Opening)", body)[0]
        shot = " ".join(l.strip() for l in body.split("\n")
                        if l.strip() and not l.strip().startswith(">"))
        shot = re.sub(r"\*\*On screen\*\*\s*—\s*", "", shot)
        shot = re.sub(r"\*\*(How|She says)\*\*\s*—?\s*", "", shot).strip()
        # seed from where this scene sits in the source, for consistent light
        start = m.group(2).strip().split("–")[0].split("-")[0].strip()
        shot = WARDROBE.sub("", shot).strip()
        shot = SOUND.sub("", shot).strip()
        shot = ONSCREEN.sub("", shot).strip()
        shot = SOURCESHOT.sub("", shot).strip()
        out.append(dict(
            key=f"c{max(ci,1)}{'o' if is_opening else 's'}{int(m.group(1)):02d}",
            concept=concept, n=int(m.group(1)), span=m.group(2).strip(),
            on_screen=shot, wearing=wear.group(1).strip() if wear else "",
            caption=(cap.group(1).strip().strip('"') if cap else ""),
            seed_at=start if re.match(r"\d+:\d{2}$", start) else "0:00"))
    return out


def duration(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def seconds(ts):
    """'1:15' -> 75.0"""
    parts = str(ts).split(":")
    try:
        return sum(float(p) * 60 ** i for i, p in enumerate(reversed(parts)))
    except ValueError:
        return 0.0


def still(video, ts, dest, length=None):
    """A frame from the video at `ts`, or from the last moment there is one.

    An organic source is a hook — nine seconds standing in front of a
    forty-eight second ad — so most of the shot list sits PAST the end of the
    video. Asking ffmpeg for 0:26 of a 0:07 clip returns nothing, which left
    those frames with no seed, and with no seed there was nothing to fall back
    to when generation missed. They came out empty (2026-08-26). Clamping
    keeps every frame anchored to her real footage: the light, the place and
    the person are still hers even where the timestamp has run out.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    at = ts
    if length and seconds(ts) >= length:
        at = f"{max(length - 0.35, 0):.2f}"
    subprocess.run(["ffmpeg", "-y", "-ss", at, "-i", str(video), "-frames:v", "1",
                    "-vf", "scale=768:-1", str(dest)], capture_output=True)
    return dest if dest.exists() else None


def img_part(f):
    mime = "image/jpeg" if f.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return {"inline_data": {"mime_type": mime,
                            "data": base64.b64encode(f.read_bytes()).decode()}}


class OutOfCredit(Exception):
    """The key is out. Retrying cannot fix it, so the run stops and says so."""


# Generic packaging and container words — brand-agnostic (workspace rule 7),
# so this reads the same on a scrub, a supplement or a razor.
PRODUCT_WORDS = re.compile(
    r"\b(tube|bottle|jar|pot|tub|sachet|packet|pump|dropper|"
    r"canister|tin|box|package|parcel|carton|product|label|cap|"
    r"scrub|cream|serum|lotion|balm|gel|oil|powder|capsule|tablet)\b", re.I)


def scene_has_product(scene_text, product_look=""):
    """Does this scene actually put the product on camera?

    Until 2026-08-25 the product description — and then its photographs —
    went onto EVERY scene. So the opening of a five-minute ad, which in the
    source is a woman talking over a green-screen plate with no product
    anywhere for the first seventy-five seconds, came back as a product
    demo. The model was doing as it was told; it was told wrong.
    """
    if PRODUCT_WORDS.search(scene_text or ""):
        return True
    # Anything the brand itself calls the product by name, taken from its own
    # description rather than hard-coded here.
    # Only distinctive words count. The scan used to take any capitalised
    # word of four letters or more out of the product description, so "BODY"
    # — from a product whose name contains it — matched a direction reading
    # "the whole body in frame" and hung a tube in a shot that had none
    # (2026-08-26). Six characters is the line: brand and ingredient names
    # clear it, the generic words in a product name do not. A length test,
    # never a word list, so it stays brand-agnostic.
    for word in re.findall(r"\b[A-Z][A-Za-z]{5,}\b", product_look or ""):
        if re.search(rf"\b{re.escape(word)}\b", scene_text or "", re.I):
            return True
    return False


# What carries over from the still, and what does not. The old instruction
# was "Use this image for the setting, framing and light." — it never said
# what to IGNORE, so the still's wardrobe walked into every generation and
# on 2026-08-20 produced seven frames of a real person in swimwear.
SEED_RELATIONSHIP = (
    "This photograph is the reference. Keep from it: the person's face and "
    "build, the place it was taken and everything in it, the surfaces, and "
    "the direction the light comes from. "
    "Everything else comes from the written scene below — above all the "
    "clothing, which the words alone decide. Where the photograph and the "
    "words disagree, the words win."
)

# When a face anchor is supplied, two references are describing the same
# person and the seed still is the weaker of the two — often it shows no face
# at all (a creator lying down in sunglasses), and asking it for one is how
# 2026-08-20 rebuilt a stranger at a bathroom counter. So the jobs split: the
# still owns the place, the anchor owns the person.
SEED_RELATIONSHIP_WITH_FACE = (
    "This photograph is the location reference, and it is where this scene "
    "happens. Keep from it: the place and everything in it — indoors or "
    "outdoors, whichever it shows — the surfaces, the framing of the shot, "
    "and the direction the light comes from. The person is described by the "
    "portrait reference instead. "
    "Everything else comes from the written scene below — above all the "
    "clothing, which the words alone decide. Where the photograph and the "
    "words disagree, the words win."
)

# The creator's likeness. Cut only from her own published video (see the
# likeness README beside the anchors) — she is under contract, the mock-up is
# of her, and a stock face would make the brief a picture of somebody else.
# Pro takes up to 5 character-consistency references; one good one is enough.
FACE_RELATIONSHIP = (
    "This portrait is the person who appears in every frame. Their face, "
    "their hair, their colouring, their build and their apparent age come "
    "from this photograph and stay the same in every scene — the same "
    "recognisable person throughout. Their expression, their pose, their "
    "clothing and their surroundings come from the written scene below."
)


# A written description of packaging — however exact — is still something the
# model has to imagine. The config's product_look runs to 90 words and it
# still produced a tube reading "DAILY RESTORE MOISTURISER" on 2026-08-25.
# The brand keeps real product photography; this hands it over directly.
# Pro accepts 6 object references, so there is room.
PRODUCT_RELATIONSHIP = (
    "This photograph shows the real product. Reproduce it exactly as it "
    "appears here — the same shape, the same colour and finish, the same "
    "label, the same wording, the same logo. Match every part of it to this "
    "photograph including the cap or closure, which is whatever colour the "
    "photograph shows and not a metallic unless it is metallic here. Do not "
    "restyle it, do not redesign the label, do not recolour any part of it, "
    "and do not write different words on it. Only its position and the light "
    "falling on it may change to suit the scene. "
    # The 2026-08-31 run invented a cream label panel on a tube whose real
    # artwork prints directly on the packaging — treatment is part of the
    # label, not a styling choice the model gets to make.
    "The artwork sits on the packaging exactly the way the photograph shows "
    "it — printed directly on the surface if that is what the photograph "
    "shows, with the same placement and proportions. Never move the design "
    "onto a panel, plate or sticker the photograph does not show. "
    # Label fidelity dies at small sizes: a background tube on 2026-08-31
    # came back reading a misspelling of the brand. At any size where the
    # label's words cannot be reproduced exactly, the honest render is an
    # unreadable one — angle or blur, never invented letters.
    "When the product sits small in the frame or in the background, either "
    "keep its label exactly right or show the product angled away or softly "
    "out of focus so no words are readable — a small label never carries "
    "approximated or re-spelled text. "
    # The label's Thai line came back as Latin gibberish ("Warhngn") on
    # 2026-08-31 — the model transliterates what it cannot draw.
    "Any line of the label written in a non-Latin script is copied "
    "stroke-for-stroke from the photograph or left out entirely — never "
    "replaced with invented Latin lettering."
)


QC_MODEL = os.environ.get("FRAMES_QC_MODEL", "gemini-3.5-flash")


def qc_frame(k, png, named, cast_blocks, packshots, caption):
    """THE QC LOOP's inspector (Damon's ruling 2026-08-31: every frame is
    QC'd in loop, and controlled if variated). One generated frame is held
    against ground truth — the real packshot for the product, the locked
    cast blocks for every character the scene names, the caption for
    lettering. Returns [] on a clean frame, else the exact deviations for
    the re-roll to correct."""
    parts = [{"inline_data": {"mime_type": "image/png",
                              "data": base64.b64encode(png).decode()}},
             {"text": "THE FRAME TO INSPECT is the image above."}]
    for p in list(packshots)[:1]:
        parts.append(img_part(Path(p)))
        parts.append({"text": "THE REAL PRODUCT photograph — ground truth "
                              "for the packaging."})
    rules = ["You are a strict QC inspector for ad reference frames. Check "
             "THE FRAME against every rule below and report violations."]
    if packshots:
        rules.append(
            "PRODUCT: if the product appears, its packaging must match THE "
            "REAL PRODUCT photograph — same shape, same colours, same label "
            "wording, and the artwork printed the same way on the same "
            "surface (a panel, plate or sticker the photograph does not "
            "show is a violation). One exception: a non-Latin script line "
            "may be absent — absent is allowed, garbled is a violation. "
            "A small or background product must be "
            "either exactly right or unreadable — approximated, garbled or "
            "invented lettering is a violation.")
    for n in named:
        rules.append(f"CHARACTER — {n} must match this description exactly "
                     f"(age, skin, hair, build, wardrobe): {cast_blocks[n]}")
    if caption:
        rules.append(f'CAPTION: the burned-in caption must read exactly: '
                     f'"{caption}" — correctly spelled, and no other text '
                     "appears anywhere except the product's own label.")
    else:
        rules.append("TEXT: no caption is expected; any lettering other "
                     "than the product's own label is a violation.")
    rules.append(
        'Answer ONLY with JSON: {"pass": true} or {"pass": false, '
        '"problems": ["<one specific, visible, correctable deviation>", '
        '...]}. Report only real violations of the rules above — style or '
        "taste is never a violation.")
    parts.append({"text": "\n\n".join(rules)})
    req = urllib.request.Request(
        f"{BASE}/v1beta/models/{QC_MODEL}:generateContent?key={k}",
        data=json.dumps({"contents": [{"parts": parts}]}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
        text = d["candidates"][0]["content"]["parts"][0]["text"]
        m = re.search(r"\{.*\}", text, re.S)
        v = json.loads(m.group(0)) if m else {}
        if v.get("pass"):
            return []
        return [str(p)[:300]
                for p in (v.get("problems") or ["failed inspection"])][:6]
    except Exception as e:
        # An unreachable inspector must never kill a run — but it must NEVER
        # look like a pass either. A silent [] here once waved a known-bad
        # frame through while the model id 404'd (2026-08-31). None means
        # "not inspected", and the run reports it loudly.
        return None if not str(e) else None


# ------------------------------------------------------- trained identities
# A LoRA is an identity TRAINED IN, not a reference photo shown and hoped
# over. Proven 2026-08-31/09-01: a character holds across every scene with
# no reference image at all; a product holds colour/shape/logo but wobbles
# on micro-text at hero size, which is why a label-forward frame still
# composites the real packshot. Identities are recorded as lora.json beside
# the character/creator/product in the brand folder (train_identity.py).
FAL_TXT2IMG = "https://queue.fal.run/fal-ai/flux-lora"
FAL_IMG2IMG = "https://queue.fal.run/fal-ai/flux-lora/image-to-image"


class NoIdentity(RuntimeError):
    pass


def fal_call(key, url, payload, tries=3):
    for attempt in range(tries):
        try:
            r = urllib.request.Request(
                url, data=json.dumps(payload).encode(),
                headers={"Authorization": f"Key {key}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(r, timeout=300) as resp:
                job = json.loads(resp.read() or b"{}")
            while True:
                s = urllib.request.Request(
                    job["status_url"] + "?logs=0",
                    headers={"Authorization": f"Key {key}"})
                with urllib.request.urlopen(s, timeout=120) as resp:
                    st = json.loads(resp.read() or b"{}")
                if st.get("status") in ("COMPLETED", "FAILED", "ERROR"):
                    break
                time.sleep(4)
            if st.get("status") != "COMPLETED":
                raise RuntimeError(st.get("status"))
            g = urllib.request.Request(
                job["response_url"], headers={"Authorization": f"Key {key}"})
            with urllib.request.urlopen(g, timeout=120) as resp:
                out = json.loads(resp.read() or b"{}")
            with urllib.request.urlopen(out["images"][0]["url"],
                                        timeout=120) as im:
                return im.read()
        except Exception:
            if attempt == tries - 1:
                return None
            time.sleep(3 * (attempt + 1))
    return None


def generate_trained(key, prompt, loras, seed=None, strength=0.72):
    """Generate with trained identities. With a seed still, this is
    image-to-image so the source's framing and place carry over; without
    one it is straight text-to-image."""
    payload = {"prompt": prompt,
               "loras": [{"path": u, "scale": s} for u, s in loras],
               "image_size": {"width": 768, "height": 1344},
               "num_inference_steps": 32, "guidance_scale": 3.5,
               "enable_safety_checker": False}
    if seed and Path(seed).exists():
        payload["image_url"] = data_uri(Path(seed))
        payload["strength"] = strength
        return fal_call(key, FAL_IMG2IMG, payload)
    return fal_call(key, FAL_TXT2IMG, payload)


def data_uri(p):
    import base64 as _b64
    kind = "jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "png"
    return f"data:image/{kind};base64," + \
        _b64.b64encode(p.read_bytes()).decode()


def composite_product(key, frame_png, packshot, note=""):
    """Paste the REAL product into a generated frame — the label is never
    drawn, it is the actual artwork. Nano Banana's editing role, on fal."""
    payload = {
        "prompt": ("Replace the product in this photograph with the exact "
                   "product shown in the second image. Keep the scene, the "
                   "hand, the pose, the lighting and the framing identical — "
                   "change only the product, and reproduce its packaging, "
                   "colour, logo and label wording exactly as the second "
                   "image shows. " + note),
        "image_urls": [data_uri_bytes(frame_png), data_uri(Path(packshot))],
        "num_images": 1}
    return fal_call(key, "https://queue.fal.run/fal-ai/nano-banana/edit",
                    payload)


def data_uri_bytes(b, kind="png"):
    import base64 as _b64
    return f"data:image/{kind};base64," + _b64.b64encode(b).decode()


NANO_EDIT = "https://queue.fal.run/fal-ai/nano-banana/edit"


def edit_frame(key, seed, instruction, products=()):
    """EDIT-FIRST (Damon's ruling 2026-09-02, proven side by side).

    The seed still already contains the framing, the blocking, the room,
    the light and the lens. Generating from scratch throws all of that
    away and rebuilds it from a paragraph — which is why the prompt kept
    growing (4,262 characters on one frame) and kept drifting: every rule
    was compensating for information we had and discarded.

    This is what "recreate this image with these words" actually is: the
    picture is the canvas, and the words describe only the CHANGE. Head
    to head on the same scene, a 451-character edit beat a 4,262-character
    generation on wardrobe, composition and — for the first time — a
    legible caption.

    An edit inherits the source's LOOK, which is the point when we are
    reprinting an ad's structure. Where a different aesthetic is wanted,
    that is the variation chain's style lock, not this stage's job.
    """
    if not (seed and Path(seed).exists()):
        return None
    urls = [data_uri(Path(seed))]
    for q in list(products)[:2]:
        if q and Path(q).exists():
            urls.append(data_uri(Path(q)))
    return fal_call(key, NANO_EDIT,
                    {"prompt": instruction, "image_urls": urls,
                     "num_images": 1})


# Markup the brief writes for a human reader. It is direction ABOUT the
# picture, not content IN it, and an edit instruction carrying it asks the
# model to draw the word "Film:".
MARKUP = re.compile(r"\*\*(?:Film|Say|Hear|Wearing|Text|Overlay)s?:?\*\*\s*", re.I)


def edit_instruction(sc, who_line, wearing, caption, has_product,
                     product_look, lead_in_frame=True):
    """The DELTA, and nothing else. Everything the seed already shows —
    the room, the framing, the light, the blocking — is named as kept, not
    described.

    Three defects fixed 2026-09-02, found by reading the machine's own
    instruction beside a hand-written one that worked:

      * IT DRESSED THE WRONG PERSON. The lead's identity and wardrobe were
        applied to every frame regardless of who is actually on screen —
        so a shot that is the lead's POV OF SOMEONE ELSE told the model to
        make that someone else look like the lead. `lead_in_frame` gates it.
      * IT LEAKED MARKUP. "**Film:**" reached the model as content.
      * IT TRUNCATED MID-WORD, ending an instruction on "Shallow focus hol".
        Cut on a sentence, or do not cut.

    Order matters too: the CHANGE leads and the caption sits close behind
    it. Burying the caption under a long "who" clause is how it went
    missing on frames the hand test rendered perfectly.
    """
    bits = ["Keep this exact shot — same framing, same place, same lighting, "
            "same composition and camera position. Change only what follows. "]
    if lead_in_frame:
        if who_line:
            bits.append(f"The person is {who_line.rstrip('. ')}. ")
        if wearing:
            bits.append(f"They are wearing {wearing.rstrip('. ')}. ")
    action = MARKUP.sub("", drop_rig(sc.get("on_screen") or ""))
    action = " ".join(action.split())
    if len(action) > 300:
        cut = action[:300].rsplit(". ", 1)[0]
        action = (cut + ".") if len(cut) > 80 else action[:300].rsplit(" ", 1)[0]
    if action:
        bits.append(f"What is happening: {action} ")
    if has_product and product_look:
        bits.append("The product in frame is exactly the one in the second "
                    "image — same packaging, colour, logo and label wording. ")
    if caption:
        bits.append(f'Burned into the bottom of the picture, white sans-serif, '
                    f'reading exactly: "{caption}". That wording, spelled as '
                    "written, and no other lettering anywhere in the frame. ")
    else:
        bits.append("No lettering anywhere except the product's own label. ")
    return "".join(bits)


def generate(k, seed, prompt, tries=4, model=None, products=(), face=None,
             why=None):
    """`why` is an optional dict this fills in with the model's finishReason,
    so a caller can tell "the reference photo was declined" apart from "the
    call came back empty" — they need different answers and used to get the
    same one."""
    parts = []
    # The person first: whoever is named first is the one the model holds on
    # to when a later reference disagrees, and who she is matters more than
    # which room she is standing in.
    if face and Path(face).exists():
        parts.append(img_part(Path(face)))
        parts.append({"text": FACE_RELATIONSHIP})
    if seed and seed.exists():
        parts.append(img_part(seed))
        seed_text = SEED_RELATIONSHIP_WITH_FACE if face else SEED_RELATIONSHIP
        # The still is cut from SOMEBODY ELSE'S ad, so their product is often
        # sitting in it — and "keep everything in it" was carrying that tub
        # into our frame, where it blended with our product references
        # (found 2026-08-31 on the strawberry-legs run). When our product is
        # in the scene, the still's product is explicitly not.
        if products:
            seed_text += (
                " Any words or captions burned into this location photograph are "
                "not part of the scene either — the only caption is the one "
                "named below, if any. One exception: any product, container, tube, jar or "
                "packaging visible in this location photograph is NOT part "
                "of the scene — ignore it completely. The only product that "
                "may appear is the one in the product reference photographs.")
        parts.append({"text": seed_text})
    for p in products:
        if p and Path(p).exists():
            parts.append(img_part(Path(p)))
            parts.append({"text": PRODUCT_RELATIONSHIP})
    parts.append({"text": prompt})
    body = {
        "contents": [{"parts": parts}],
        # Without this the model picks a shape per call — runs on 2026-08-21
        # came back as a mix of 768x1365 and square 1024x1024. These are
        # reference frames for vertical ads; a square one misleads the maker.
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": ASPECT, "imageSize": SIZE},
        },
    }
    req = urllib.request.Request(
        f"{BASE}/v1beta/models/{model or MODEL}:generateContent?key={k}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            for c in d.get("candidates", []):
                if why is not None and c.get("finishReason"):
                    why["reason"] = c["finishReason"]
                for p in c.get("content", {}).get("parts", []):
                    inl = p.get("inlineData") or p.get("inline_data")
                    if inl and inl.get("data"):
                        return base64.b64decode(inl["data"])
            return None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                body = e.read()[:300].decode("utf8", "replace")
                raise OutOfCredit(body)
            if attempt == tries - 1:
                say(f"      generation failed: {str(e)[:90]}")
                return None
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            if attempt == tries - 1:
                say(f"      generation failed: {str(e)[:90]}")
                return None
            time.sleep(5 * (attempt + 1))
    return None


def run(brief_path, video, out_dir, product_look="", subject="", products=(),
        face=None,
        caption_style="", identities=(), limit=0):
    k = keys.get("GEMINI_API_KEY")
    # identities: [(lora_url, scale, kind)] — the run's trained assets.
    # When any are present the frames are generated WITH THE IDENTITY
    # TRAINED IN rather than a reference photo shown alongside; that is the
    # whole point of training them (Damon, 2026-09-01).
    fal_key = keys.get("FAL_KEY")
    trained = [(u, s) for u, s, _ in identities] if (identities and fal_key) else []
    # A person LoRA means the lead is already in the weights — so the written
    # identity must NOT also go in (Damon, 2026-09-02: subtraction).
    face_is_trained = any(k in ("character", "creator") for _, _, k in identities) \
        if trained else False
    id_triggers = " ".join(t for _, _, t in identities) if trained else ""
    if identities and not fal_key:
        say("      trained identities present but NO FAL_KEY — falling back "
            "to reference-photo generation")
    md = Path(brief_path).read_text()
    scenes = parse(md)
    cast_blocks = parse_cast(md)
    if cast_blocks:
        say(f"  locked cast: {', '.join(cast_blocks)} — pasted into every "
            "frame that names them")
    if not scenes:
        sys.exit("no scenes found in that brief")
    if limit:
        scenes = scenes[:limit]
        say(f"  limit: first {len(scenes)} scene(s) only")

    frames = Path(out_dir); frames.mkdir(parents=True, exist_ok=True)
    seeds = frames / "seeds"; seeds.mkdir(exist_ok=True)
    say(f"  {len(scenes)} scenes — generating one frame for each")

    # Scenes are independent, so they run side by side. One at a time was ~90
    # seconds a frame — forty minutes for a single video, which does not scale
    # to the volume this is for.
    broke = threading.Event()
    lock = threading.Lock()
    state = dict(made=0, fell_back=0, misses=0, credit_error=None,
                 used_fallback_model=0)

    vid_len = duration(video)

    def one(sc):
        if broke.is_set():
            return None
        seed = still(video, sc["seed_at"], seeds / f"{sc['key']}.jpg", vid_len)
        # Order follows Google's own formula for this model — subject, action
        # and location first, materials next, style last. It used to open on
        # the style block, which front-loaded the look and left the actual
        # scene trailing at the end of a long paragraph.
        # The scene is written TO the maker ("turn your forearms to the
        # window"). Find-and-replacing the pronouns left the verbs
        # unconjugated — "She open a box and lift out the tube" — so every
        # prompt reached the model in broken English. This model reads
        # natural language, so telling it what it is looking at beats
        # rewriting the sentence badly.
        bits = [
            "Photograph this moment. The description is written as directions "
            "to the person being photographed; show them doing it. — ",
            f"{drop_rig(sc['on_screen'])} ",
        ]
        # SUBTRACTION, NOT MORE RULES (Damon, 2026-09-02). Every safeguard
        # below was sensible alone and collectively made the prompt argue
        # with itself: one frame carried TWO different women (a trained
        # identity's description AND the brief's character), FIVE outfits,
        # and a second character's wardrobe — so the model blended them and
        # put the mistress's denim jacket on the lead. 4,262 characters of
        # contradiction. A prompt that contradicts itself cannot be fixed
        # by adding a rule; the fix is to send less.
        #
        # 1. ONE identity per frame. A trained identity IS the person —
        #    describing a different one beside it is the contradiction.
        # ONE short line naming who this is, for the edit path. A trained
        # identity supplies the person itself, so the words only need to
        # name them when nothing is trained.
        lead_nm = next(iter(cast_blocks), None)
        who_line = ""
        if not face_is_trained:
            if subject:
                who_line = subject
            elif lead_nm and lead_nm in cast_blocks:
                first = re.split(r"(?<=[.!?])\s", cast_blocks[lead_nm])
                who_line = " ".join(first[:2])[:240]
        # (frame_face is decided further down, after `named` exists — this
        # only needs to know whether the identity is trained)
        if subject and not face_is_trained:
            bits.append(f"The person is {subject} ")
        # 2. Only the characters this scene actually names, and when a
        #    trained identity carries the lead, only the OTHERS need
        #    describing — the lead is already in the weights.
        named = [n for n in cast_blocks
                 if re.search(rf"\b{re.escape(n)}\b", sc["on_screen"], re.I)]
        if face_is_trained and named:
            lead_name = next(iter(cast_blocks), None)
            named = [n for n in named if n != lead_name]
        if named:
            bits.append(
                "The people in this picture, each exactly as written here — "
                "the same recognisable person in every frame they appear: ")
            for n in named:
                # 3. Only THIS scene's wardrobe. The block lists every
                #    outfit a character wears across the piece; pasting all
                #    of them hands the model a menu to blend.
                bits.append(one_outfit(cast_blocks[n], sc) + " ")
        if sc.get("wearing"):
            bits.append(f"{SUBJECT_C} is fully dressed in {sc['wearing']}. "
                        "Exactly this, whatever the reference photograph shows. ")
        # Only scenes that actually show the product get told about it, and
        # only those get the reference photographs. Everywhere else the
        # product is simply absent — which is what the source does for its
        # whole first act.
        shows_product = scene_has_product(sc["on_screen"], product_look)
        if product_look and shows_product:
            bits.append(f"The product is {product_look}. ")
        scene_products = products if shows_product else ()
        cap = (sc.get("caption") or "").strip()
        # A caption still carrying an unfilled marker is not text — rendering
        # it burns "[SLOT: time interval]" across the picture, which is what
        # happened on 2026-08-25. Leave the frame clean; the brief already
        # lists the gap at the top for whoever fills it.
        if re.search(r"\[\s*(SLOT|TBC|TODO|PLACEHOLDER)\b", cap, re.I):
            cap = ""
        if cap and cap.lower() not in ("nothing", "none", "n/a", "-"):
            bits.append(CAPTION_DIRECTION.format(
                style=(caption_style or CAPTION_STYLE_DEFAULT), text=f'"{cap}"'))
        bits.append(GUARD)
        prompt = "".join(bits)
        # The portrait anchor is THE LEAD's identity. On a frame that names
        # other cast but not the lead, sending it anyway bleeds the lead into
        # them — 2026-08-31, the lead's silver hair landed on a supporting
        # character the brief wrote as dark-haired. The lead is the first
        # character in the brief's locked cast.
        lead = next(iter(cast_blocks), None)
        frame_face = face
        if face and cast_blocks and named and lead not in named:
            frame_face = None
        (frames / "prompts").mkdir(exist_ok=True)
        (frames / "prompts" / f"{sc['key']}.txt").write_text(prompt)
        try:
            # An empty response is transient — the same prompt that returned
            # nothing generates fine seconds later. Give it real attempts before
            # falling back to a still.
            why = {}
            data = None
            # EDIT-FIRST. The seed still is the canvas; the words are the
            # delta. This is the operation that actually works (2026-09-02,
            # proven head to head) and it runs before anything rebuilds the
            # scene from a paragraph.
            if seed and Path(seed).exists() and fal_key:
                # A name in the scene does NOT mean the person is in the
                # picture. "Michelle's point of view down the aisle" puts
                # her BEHIND the camera — dressing her there told the model
                # to make the woman she is looking at into her (2026-09-02).
                txt = sc.get("on_screen") or ""
                lead_here = True
                if lead_nm:
                    named_here = bool(re.search(rf"\b{re.escape(lead_nm)}\b",
                                                txt, re.I))
                    behind_camera = bool(re.search(
                        rf"(?:{re.escape(lead_nm)}\'?s?\s+(?:point of view|POV|"
                        rf"eyeline)|from\s+{re.escape(lead_nm)}\'?s?\s+"
                        rf"(?:point of view|POV|side)|over\s+"
                        rf"{re.escape(lead_nm)}\'?s?\s+shoulder)", txt, re.I))
                    # named elsewhere in the line as well? then she is both
                    # behind the camera and in it only if named again after
                    other = re.sub(
                        rf"{re.escape(lead_nm)}\'?s?\s+(?:point of view|POV|"
                        rf"eyeline)", "", txt, flags=re.I)
                    still_named = bool(re.search(rf"\b{re.escape(lead_nm)}\b",
                                                 other, re.I))
                    lead_here = named_here and not (behind_camera and not still_named)
                instr = edit_instruction(
                    sc, who_line, sc.get("wearing") or "", cap,
                    shows_product, product_look, lead_in_frame=lead_here)
                (frames / "prompts" / f"{sc['key']}.edit.txt").write_text(instr)
                data = edit_frame(fal_key, seed, instr, scene_products)
                if data:
                    with lock:
                        state["from_edit"] = state.get("from_edit", 0) + 1
            if data is None and trained:
                # The identity leads the prompt: the trigger words are what
                # the trained weights answer to.
                data = generate_trained(
                    fal_key, f"{id_triggers}. {prompt}", trained, seed=seed)
                if data:
                    with lock:
                        state["from_identity"] = \
                            state.get("from_identity", 0) + 1
            if data is None:
                data = generate(k, seed, prompt, products=scene_products,
                                face=frame_face, why=why)
            # A reference photo can be declined — most often a real person in
            # swimwear, which is most of an organic beach post. Retrying the
            # same call cannot pass and a still is not a generated frame, so
            # this asks for the written scene on its own. It is a different
            # request, not the same one pushed harder, and what comes back is
            # NOT her likeness — the manifest says so, and so does the board.
            if not data and why.get("reason") == "IMAGE_SAFETY":
                data = generate(k, None, prompt, tries=2)
                if data:
                    with lock:
                        state["from_description"] = \
                            state.get("from_description", 0) + 1
            for attempt in range(3):
                if data:
                    break
                time.sleep(3 * (attempt + 1))
                data = generate(k, seed, prompt, tries=2, products=scene_products,
                                face=frame_face)
            # Pro is capacity-constrained and answers "high demand" in bursts.
            # A whole run failing because the best model was busy is worse
            # than the second-best model drawing this one frame.
            if not data and MODEL != FALLBACK:
                data = generate(k, seed, prompt, tries=2, model=FALLBACK,
                                products=scene_products, face=frame_face)
                if data:
                    # Its own counter: "fell_back" already means "gave up on
                    # generating and used a still from the video". Reusing it
                    # would report a second-best model as a missing frame.
                    with lock:
                        state["used_fallback_model"] = \
                            state.get("used_fallback_model", 0) + 1
            if not data:
                data = generate(k, seed, f"{GUARD}A photograph showing: "
                                         f"{as_picture(sc['on_screen'])[:600]}", tries=2,
                                face=frame_face)
        except OutOfCredit as e:
            # A 429 is either a daily quota (resets, another model still has
            # room) or a genuinely empty key (nothing will work). Try the other
            # model before killing the run — this is exactly the case the
            # fallback exists for, and raising past it wasted a whole run.
            data = None
            if MODEL != FALLBACK:
                try:
                    data = generate(k, seed, prompt, tries=2, model=FALLBACK,
                                    products=scene_products)
                except OutOfCredit:
                    data = None
            if data:
                with lock:
                    state["used_fallback_model"] = \
                        state.get("used_fallback_model", 0) + 1
            else:
                with lock:
                    state["credit_error"] = str(e)[:600]
                broke.set()
                return None

        # THE QC LOOP: inspect the frame against ground truth the moment it
        # exists; a frame that varies is re-rolled with the deviation named,
        # up to twice. A frame still flagged after that ships FLAGGED — the
        # manifest and the log both say so, so slop never passes silently.
        qc_problems = []
        if data:
            for qc_round in range(3):
                qc_problems = qc_frame(k, data, named, cast_blocks,
                                       scene_products, cap)
                if qc_problems is None:          # inspector unreachable
                    qc_problems = []
                    with lock:
                        state["qc_unavailable"] = \
                            state.get("qc_unavailable", 0) + 1
                    break
                if not qc_problems or qc_round == 2:
                    break
                with lock:
                    state["qc_rerolls"] = state.get("qc_rerolls", 0) + 1
                fix = (" The previous attempt failed inspection. Correct "
                       "every one of these exactly, changing nothing else: "
                       + "; ".join(qc_problems))
                # A LABEL failure is never fixed by drawing it again — no
                # generator holds small type across re-rolls (26 re-rolls,
                # 2026-08-31). Composite the real packshot in instead: the
                # artwork stops being generated at all.
                label_bad = any(
                    re.search(r"label|wording|text|logo|packaging|brand",
                              p, re.I) for p in qc_problems)
                redo = None
                if label_bad and fal_key and scene_products:
                    redo = composite_product(fal_key, data,
                                             list(scene_products)[0])
                    if redo:
                        with lock:
                            state["composited"] = \
                                state.get("composited", 0) + 1
                if not redo and trained:
                    redo = generate_trained(
                        fal_key, f"{id_triggers}. {prompt}{fix}", trained,
                        seed=seed)
                if not redo:
                    redo = generate(k, seed, prompt + fix, tries=2,
                                    products=scene_products, face=frame_face)
                if not redo:
                    break
                data = redo

        dest, kind = frames / f"{sc['key']}.png", "generated"
        if qc_problems:
            kind = "generated · QC FLAGGED: " + "; ".join(qc_problems)[:220]
            with lock:
                state["qc_flagged"] = state.get("qc_flagged", 0) + 1
        if data:
            dest.write_bytes(data)
            with lock:
                state["made"] += 1
                state["misses"] = 0
        elif seed:
            dest = frames / f"{sc['key']}.jpg"
            dest.write_bytes(seed.read_bytes())
            # Only after real retries. Says what it is: the still cut from the
            # source at this scene's timestamp, because generation kept coming
            # back empty.
            kind = "still from the source — generation kept returning nothing"
            with lock:
                state["fell_back"] += 1
                state["misses"] += 1
                if state["misses"] >= 3:
                    broke.set()
        else:
            dest, kind = None, "none"
        say(f"    {sc['key']}  {kind}")
        return dict(key=sc["key"], concept=sc["concept"], scene=sc["n"],
                    span=sc["span"], seeded_from=sc["seed_at"],
                    output=dest.name if dest else None, kind=kind,
                    qc=qc_problems)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        manifest = [m for m in pool.map(one, scenes) if m]

    if state["credit_error"]:
        err = state["credit_error"]
        daily = "per_day" in err or "per_model_per_day" in err
        why = ("every image model has hit its DAILY REQUEST CAP. This is not "
               "credit — topping up will not move it. It resets on its own; "
               "the error below says when."
               if daily else
               "the Gemini key is out of credit. Top up at "
               "https://ai.studio/projects.")
        sys.exit(f"STOPPING — {why} Nothing was faked as a fallback.\n"
                 f"Both {MODEL} and {FALLBACK} were tried.\n"
                 "Re-run stage 6 with: --from 6\n\n" + err)
    if broke.is_set() and state["misses"] >= 3:
        sys.exit("STOPPING — three scenes came back with no image. Something is "
                 "wrong upstream; the rest would only produce more stills.")
    # NO FRAME LEAVES THIS STAGE EMPTY (Damon, 2026-08-26: "NO BRIEF SHOULD BE
    # EMPTY"). Everything above tries to make the right picture; this makes
    # sure there is A picture. In order of preference: the still cut for this
    # scene, then the nearest earlier scene's image, then the poster. Each one
    # is real footage from this very video, and the manifest records exactly
    # which so nobody mistakes a stand-in for a generated frame.
    rescued = 0
    last_good = None
    for sc in scenes:
        entry = next((m for m in manifest if m.get("key") == sc["key"]), None)
        have = next((frames / f"{sc['key']}{e}" for e in (".png", ".jpg", ".jpeg")
                     if (frames / f"{sc['key']}{e}").exists()), None)
        if have:
            last_good = have
            continue
        src = seeds / f"{sc['key']}.jpg"
        pick = src if src.exists() else last_good
        if pick is None:
            poster = Path(video).parent / "poster.jpg"
            pick = poster if poster.exists() else None
        if pick is None:
            continue
        dest = frames / f"{sc['key']}.jpg"
        dest.write_bytes(Path(pick).read_bytes())
        rescued += 1
        note = ("still from the source" if pick == src
                else "the nearest frame we do have — this scene runs past the "
                     "end of the source video")
        if entry is not None:
            entry["file"], entry["kind"] = dest.name, note
        else:
            manifest.append(dict(key=sc["key"], n=sc["n"], span=sc["span"],
                                 file=dest.name, kind=note))
    if rescued:
        say(f"  {rescued} frame(s) filled from the source so none went out empty")

    made, fell_back = state["made"], state["fell_back"]
    (frames / "manifest.json").write_text(json.dumps(manifest, indent=2))
    if state.get("from_description"):
        say(f"  {state['from_description']} frame(s) drawn from the written "
            f"scene because a reference photograph was declined — those are "
            f"not her likeness")
    if state.get("used_fallback_model"):
        say(f"  {state['used_fallback_model']} frame(s) drawn by {FALLBACK} "
            f"because {MODEL} was busy or capped")
    say(f"  {made} generated, {fell_back} fell back to a still, "
        f"{len(scenes)} scenes covered")
    if state.get("from_edit"):
        say(f"  {state['from_edit']} frame(s) made by EDITING the source still "
            "— the picture carried the framing, the words carried the change")
    if state.get("qc_rerolls") or state.get("qc_flagged"):
        say(f"  QC loop: {state.get('qc_rerolls', 0)} re-roll(s) forced, "
            f"{state.get('qc_flagged', 0)} frame(s) still flagged — flagged "
            "frames are named above and in the manifest")
    elif state.get("qc_unavailable"):
        say(f"  QC loop: INSPECTOR UNREACHABLE on {state['qc_unavailable']} "
            "frame(s) — those frames are UNINSPECTED, not passed")
    else:
        say("  QC loop: every frame passed inspection first time")
    if state.get("from_identity"):
        say(f"  trained identities: {state['from_identity']} frame(s) "
            "generated with the identity trained in")
    if state.get("composited"):
        say(f"  product composite: {state['composited']} frame(s) had the "
            "real packshot pasted in after a label failure")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--product-look", default="")
    ap.add_argument("--caption-style", default="",
                    help="how the source styles its burned-in captions, from "
                         "the teardown record")
    ap.add_argument("--face", default="",
                    help="the creator's likeness anchor — one frame from her own "
                         "published video, so the mock-up is of her and not a "
                         "stranger who happens to match the description.")
    ap.add_argument("--product-image", action="append", default=[],
                    help="real product photography, passed to the image model "
                         "as a reference. Repeatable.")
    ap.add_argument("--subject", default="",
                    help="who is on camera — age, hair, build. Without it the "
                         "model invents a different woman for every scene.")
    ap.add_argument("--limit", type=int, default=0,
                    help="only the first N scenes — for calibrating a "
                         "template cheaply before committing to a full set")
    ap.add_argument("--identity", action="append", default=[],
                    help="a trained identity for this run, as "
                         "<lora_url>|<scale>|<trigger> (from the asset's "
                         "lora.json). Repeatable — a character and a product "
                         "can both be trained in. With any identity present "
                         "the frames are generated WITH IT TRAINED IN "
                         "instead of a reference photo shown alongside.")
    a = ap.parse_args()
    ids = []
    for spec in a.identity:
        bits = spec.split("|")
        if len(bits) == 3:
            ids.append((bits[0], float(bits[1]), bits[2]))
    run(Path(a.brief), Path(a.video), Path(a.out), a.product_look, a.subject,
        products=a.product_image, caption_style=a.caption_style,
        face=(Path(a.face) if a.face else None), identities=ids,
        limit=a.limit)


if __name__ == "__main__":
    main()
