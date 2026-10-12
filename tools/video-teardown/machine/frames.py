#!/usr/bin/env python3
"""Stage 6 — a generated frame on every scene. No gaps.

    python3 frames.py --brief <brief.md> --video <source.mp4> --out <dir>

the owner's rule (2026-08-21): every scene gets a picture. The shared runner drops
frames when the generated person does not match the seed still, or when it
judges a scene unusable — this one does not. It generates for every scene, and
if generation fails outright it falls back to the still cut from the video so
the scene still has something to look at.

The seed still keeps the place and the light consistent between scenes.
"""

import argparse, base64, json, os, re, subprocess, sys, tempfile, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keys

# ONE DOOR, GPT IMAGE (the owner, 2026-09-22: "brief frames need to run on gpt,
# not nano banana"). This file names no model: it asks the one route table,
# `tools/image-production/models.json`, which is where every picture in
# the business is routed — stills, statics, email, pages and now these frames.
# Today that resolves to GPT Image 2.5 on OpenAI's own door.
#
# The seed still, the face anchor and the product photographs all go IN as
# references, which is the edit-first operation (2026-09-02, proven head to
# head) done in that model's own door. Because GPT Image takes one prompt and
# a LIST of pictures, the sentence that used to sit beside each reference is
# written into the prompt as a numbered legend — see `legend()`.
#
# Gone the same day: fal (nano-banana/edit, flux-lora trained identities, the
# packshot composite), ruled out 2026-09-11, restated 09-13 and again here.
#
# The history below is kept because it is why the frames look the way they do.
# Best model, always (the owner, 2026-08-25). The 08-21 note below it chose the
# cheapest tier because these were reference frames a creator glanced at.
# They are becoming ad assets, so the job changed and the choice with it —
# image generation is cheap next to video, so there is no reason to run
# anything but the best. Override per run with --image-model.
# Every frame records WHICH model drew it, in the manifest (2026-09-22, after
# the owner asked the question off a brief page and nothing on the page answered
# it). The run page reads that record; runs before this date carry none.
#   gemini-3-pro-image        Nano Banana Pro   best, slowest, sometimes busy
#   gemini-3.1-flash-image    Nano Banana 2     very good, fast
#   gemini-3.1-flash-lite-image                 the old default
# Pro is the default (the owner, 2026-08-25, revised same day). Flash held the
# default for one afternoon because Pro's 250/day cap used to kill a whole run
# the moment it was spent — topping up does not move it, it is a daily quota,
# not credit. The per-frame fallback below now catches that case and finishes
# the run on Flash, so the reason is gone and the frames were visibly cheaper
# for it. At ~29 frames a video the cap is roughly eight videos a day; past
# that the run finishes on Flash and says how many frames it had to hand over.
# Kept for the manifest and the run page: what a frame SAYS drew it. The real
# id comes back from the engine; this is the row name asked for.
MODEL = os.environ.get("FRAMES_MODEL", "gpt-image-person")

# There is no second door any more — one model, one look (the whole point of
# the route table). FALLBACK stays equal to MODEL so the "try the other one"
# branches below are inert rather than removed, and a future second row is one
# line away.
FALLBACK = MODEL

# Vertical, to match the ads these frames are shot for. 2K is the useful
# ceiling for a reference frame; Pro will go to 4K if ever needed.
ASPECT = "9:16"
SIZE = "2K"
# GPT Image counts INPUT IMAGES per minute (limit 5 on this account) and every
# frame attaches at least the seed still, so six at once fails five of them.
# The gate below paces the calls; the workers just queue behind it.
WORKERS = 3   # concurrent frames
IMAGES_PER_MIN = int(os.environ.get("FRAMES_IMAGES_PER_MIN", "5"))
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
# happens entirely on a beach that put her in a bedroom (the owner, 2026-08-26).
# The scene names the place; this only says how the picture is taken.
GUARD = (
    # POSITIVE FRAMING, and it applies to the camera too. The old text said
    # "a phone photograph, handheld at chest height, the way someone filming
    # themselves would hold it" and got a hand holding a phone drawn into the
    # shot, caption rendered on its little screen (the owner, 2026-08-26). Adding
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


class Pace:
    """Lets at most N image calls start in any 60 seconds. A 429 for going too
    fast is not a failure to report — it is a queue to join (learned live
    2026-09-22: six workers, limit five, nine frames in and the run stopped)."""

    def __init__(self, per_min):
        self.per_min, self.at, self.lock = per_min, [], threading.Lock()

    def wait(self):
        while True:
            with self.lock:
                now = time.time()
                self.at = [t for t in self.at if now - t < 60]
                if len(self.at) < self.per_min:
                    self.at.append(now)
                    return
                sleep = 60 - (now - self.at[0]) + 0.5
            time.sleep(max(sleep, 0.5))


PACE = Pace(IMAGES_PER_MIN)


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
    """THE QC LOOP's inspector (the owner's ruling 2026-08-31: every frame is
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


def engine():
    """The shared image engine. Imported at CALL time so this module still
    imports on a machine that has not got it."""
    import chain as _C                                   # noqa: PLC0415
    root = _C.workspace() / "tools" / "image-production"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from image_production import providers, route          # noqa: PLC0415
    return providers, route


def legend(seed, products, face):
    """GPT Image takes ONE prompt and a LIST of pictures — there is no slot to
    hang a sentence on each reference the way Gemini's parts had. So the
    relationships that used to sit beside each image are written into the
    prompt as a numbered legend, in the exact order the images are attached.
    The words themselves are unchanged; only where they sit moved."""
    bits, n = [], 0
    if face:
        n += 1
        bits.append(f"IMAGE {n} — {FACE_RELATIONSHIP}")
    if seed:
        n += 1
        bits.append(f"IMAGE {n} — "
                    + (SEED_RELATIONSHIP_WITH_FACE if face else SEED_RELATIONSHIP))
    for _ in products:
        n += 1
        bits.append(f"IMAGE {n} — {PRODUCT_RELATIONSHIP}")
    if not bits:
        return ""
    return ("The attached photographs are references, in this order:\n\n"
            + "\n\n".join(bits) + "\n\n")


def generate(k, seed, prompt, tries=4, model=None, products=(), face=None,
             why=None):
    """One frame, on GPT Image (the owner, 2026-09-22: "brief frames need to run on
    gpt, not nano banana"). Returns the PNG bytes, or None.

    The model is not named here — it comes from the one route table in
    `tools/image-production/models.json`, the same door every other
    picture in the business goes through. `why` is filled with what came back
    when a call fails, so a caller can tell a refused reference apart from an
    empty answer, which is what the Gemini `finishReason` used to give.
    """
    providers, route = engine()
    # `k` is the QC inspector's Gemini key, which every call site already had
    # to hand — it is NOT this door's. The image key is resolved from the
    # route's own entry, by name, so the two can never be crossed.
    del k
    refs = [str(p) for p in
            ([face] if face and Path(face).exists() else [])
            + ([seed] if seed and Path(seed).exists() else [])
            + [q for q in products if q and Path(q).exists()]]
    # An edit when there is a picture to work from — that is the route's own
    # rule, and the edits endpoint is the only one that holds a reference.
    req = {"from_image": refs[0] if refs else None, "people": True}
    if model:
        req["model"] = model
    _, entry, _ = route.pick(req, {"purpose": {"id": "video-frame", "people": True}})
    key = route.key_value(route.key_name(entry))
    if not key:
        say(f"      no {route.key_name(entry)} on this machine")
        return None
    full = legend(seed if seed and Path(seed).exists() else None,
                  [q for q in products if q and Path(q).exists()],
                  face if face and Path(face).exists() else None) + prompt
    tmp = Path(tempfile.mkdtemp(prefix="frame-")) / "frame.png"
    for attempt in range(tries):
        try:
            PACE.wait()
            providers.generate(entry, full, refs, tmp, ASPECT, key=key)
            return tmp.read_bytes()
        except Exception as e:                              # noqa: BLE001
            msg = str(e)
            if why is not None:
                why["reason"] = ("IMAGE_SAFETY"
                                 if re.search(r"safety|moderation|rejected", msg, re.I)
                                 else "ERROR")
                why["said"] = msg[:300]
            # 429 is two different things. "Rate limit ... try again in 12s"
            # is a queue and clears by waiting; an exhausted balance or quota
            # never clears, and only that one stops the run.
            spent = re.search(r"insufficient_quota|billing|exceeded your current quota"
                              r"|out of credit", msg, re.I)
            if spent:
                raise OutOfCredit(msg[:300])
            if re.search(r"\b429\b|rate.?limit", msg, re.I):
                m = re.search(r"try again in ([\d.]+)s", msg)
                nap = min(float(m.group(1)) + 2 if m else 20 * (attempt + 1), 90)
                say(f"      the door is pacing us — waiting {nap:.0f}s")
                time.sleep(nap)
                continue
            if attempt == tries - 1:
                say(f"      generation failed: {msg[:90]}")
                return None
            time.sleep(5 * (attempt + 1))
    return None



def run(brief_path, video, out_dir, product_look="", subject="", products=(),
        face=None,
        caption_style="", identities=(), limit=0):
    k = keys.get("GEMINI_API_KEY")
    # Trained identities (LoRAs) ran on fal and fal is not a path any more
    # (the owner, 2026-09-11, restated 2026-09-13 and again 2026-09-22). The
    # parameter stays because run.py passes it; an identity now enters the
    # picture as a reference photo, which is what every other lane does.
    face_is_trained = False
    if identities:
        say("      trained identities were a fal path and fal is gone — "
            "these frames use the reference photo instead")
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
        # SUBTRACTION, NOT MORE RULES (the owner, 2026-09-02). Every safeguard
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
            # Which model actually drew this frame — the manifest records it, so
            # nobody has to ask again (the owner, 2026-09-22: "what model is used").
            drew = None
            # EDIT-FIRST is still the operation (2026-09-02, proven head to
            # head): the seed still is the canvas and the words are only the
            # delta. It used to run through fal's nano-banana/edit; since fal
            # was cut (2026-09-22) the same job is done by `generate` below,
            # which hands the model the seed still as an image part with
            # SEED_RELATIONSHIP — an edit, in Gemini's own door.
            if data is None:
                data = generate(k, seed, prompt, products=scene_products,
                                face=frame_face, why=why)
                if data:
                    drew = MODEL
            # A reference photo can be declined — most often a real person in
            # swimwear, which is most of an organic beach post. Retrying the
            # same call cannot pass and a still is not a generated frame, so
            # this asks for the written scene on its own. It is a different
            # request, not the same one pushed harder, and what comes back is
            # NOT her likeness — the manifest says so, and so does the board.
            if not data and why.get("reason") == "IMAGE_SAFETY":
                data = generate(k, None, prompt, tries=2)
                if data:
                    drew = MODEL
                    with lock:
                        state["from_description"] = \
                            state.get("from_description", 0) + 1
            for attempt in range(3):
                if data:
                    break
                time.sleep(3 * (attempt + 1))
                data = generate(k, seed, prompt, tries=2, products=scene_products,
                                face=frame_face)
                if data:
                    drew = MODEL
            # Pro is capacity-constrained and answers "high demand" in bursts.
            # A whole run failing because the best model was busy is worse
            # than the second-best model drawing this one frame.
            if not data and MODEL != FALLBACK:
                data = generate(k, seed, prompt, tries=2, model=FALLBACK,
                                products=scene_products, face=frame_face)
                if data:
                    drew = FALLBACK
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
                    if data:
                        drew = FALLBACK
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
                # 2026-08-31). The packshot used to be composited in on fal;
                # with fal gone the real product goes to the model as a
                # reference image (PRODUCT_RELATIONSHIP) and a label that
                # still fails is flagged for the maker rather than faked.
                redo = None
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
                    model=drew, qc=qc_problems)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        manifest = [m for m in pool.map(one, scenes) if m]

    if state["credit_error"]:
        err = state["credit_error"]
        daily = "per_day" in err or "per_model_per_day" in err
        why = ("every image model has hit its DAILY REQUEST CAP. This is not "
               "credit — topping up will not move it. It resets on its own; "
               "the error below says when."
               if daily else
               "the image account is out of credit — top it up on the "
               "provider the route table names "
               "(tools/image-production/models.json).")
        sys.exit(f"STOPPING — {why} Nothing was faked as a fallback.\n"
                 f"The door was {MODEL}.\n"
                 "Re-run stage 6 with: --from 6\n\n" + err)
    if broke.is_set() and state["misses"] >= 3:
        sys.exit("STOPPING — three scenes came back with no image. Something is "
                 "wrong upstream; the rest would only produce more stills.")
    # NO FRAME LEAVES THIS STAGE EMPTY (the owner, 2026-08-26: "NO BRIEF SHOULD BE
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
    if state.get("qc_rerolls") or state.get("qc_flagged"):
        say(f"  QC loop: {state.get('qc_rerolls', 0)} re-roll(s) forced, "
            f"{state.get('qc_flagged', 0)} frame(s) still flagged — flagged "
            "frames are named above and in the manifest")
    elif state.get("qc_unavailable"):
        say(f"  QC loop: INSPECTOR UNREACHABLE on {state['qc_unavailable']} "
            "frame(s) — those frames are UNINSPECTED, not passed")
    else:
        say("  QC loop: every frame passed inspection first time")
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
