#!/usr/bin/env python3
"""A prompt is assembled from named slots, never written as prose.

    prompt.py render --slots slots.json                 the prompt string
    prompt.py diff   --a a.json --b b.json              what actually moved
    prompt.py packs                                     the registers available

Damon, 2026-09-14: *"whenever we do regenerations and similar work, things
don't stay in place… what I need is consistency."*

**Why things move.** A prompt written as prose has no parts. Re-rolling it
rewrites the whole paragraph, so the man's age drifts, the light changes, a
lens appears, and nothing in the system can tell you which of those you meant
to change. The prompt is the unit, so the prompt is what varies.

**So the prompt stops being the unit.** The slots are. A prompt is rendered
from them in a fixed order, which means a regeneration can differ only where
a slot differs — and `diff` proves it, naming every slot that moved. Change
the wardrobe and the wardrobe is the only thing in the diff.

**Where the slots came from.** The shot-list order this lane already used —
subject, action, environment, composition, camera, light, grade, style,
texture — plus the two things the AvatarHype 6C skill has that we did not
write down: a references slot, and positive realism anchors rather than only
a ban list. Its six map onto these thirteen:

    C1 Character  -> references + subject + wardrobe
    C2 Camera     -> composition + shot      (split on purpose, see below)
    C3 Clothing   -> wardrobe
    C4 Context    -> setting
    C5 Light      -> light + grade
    C6 Anchors    -> texture + anchors + negatives

**C2 is split, and that is the one place we refuse to follow it.** 6C writes
the camera into the prompt — "iPhone photo", "harsh iPhone flash". A model
has no concept of a camera it looks *through*; everything named is an object
it can place *in* frame, and "shot on a phone on a tripod" once put a phone
on a tripod in the middle of a barbershop ad. So `composition` says what
occupies the frame and `shot` says height, angle, distance and depth — the
result, never the equipment. `GENERATION-METHOD.md`, principle 5.

**A pack carries the register.** 6C is written for one look, phone-flash UGC.
The slots that describe how a frame is rendered — shot, light, grade, style,
texture, negatives — come from a style pack, so the same subject renders as
candid UGC or flat vector by changing one word. That is the adaptation.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PACKS = HERE.parent / "style-packs.json"

# The order is the contract. Anything rendered in a different order is a
# different prompt even when every value matches.
ORDER = [
    ("references",  "The material, by id. An Element for the cast and an Element for the product. "
                    "Never a description of a face or a device that has an id — a paragraph cannot "
                    "carry a material, and a described device is a device the model invents."),
    ("subject",     "Who or what is in frame, beyond the references. Condition, build, state."),
    ("action",      "What is happening. Hands, gesture, what is being held and how."),
    ("wardrobe",    "Clothing and accessories, named as items. `null` when nobody is in frame."),
    ("setting",     "Where it happens, and what is behind them."),
    ("composition", "What occupies what, the crop, what sits at each edge."),
    ("shot",        "Height, angle, distance, depth. The result, never the equipment."),
    ("light",       "Direction, quality, and what it is there to reveal."),
    ("grade",       "Palette, contrast, black level."),
    ("style",       "The rendering register."),
    ("texture",     "Surface truth — what must stay visible."),
    ("fidelity",    "The source's own capture quality, measured in stage 1 and "
                    "carried here so the draft matches the swipe instead of "
                    "improving on it. A phone photo of a 60-year-old woman that "
                    "comes back looking like a campaign is a different ad."),
    ("copy",        "The words the ad says, verbatim, and where each line sits. "
                    "A draft carries them so the idea can be judged; the shipping "
                    "ad composites them at full precision instead."),
    ("anchors",     "Positive constraints that hold realism, not bans."),
    ("negatives",   "The ban list. Pack defaults plus anything this ad adds."),
]
KEYS = [k for k, _ in ORDER]
FROM_PACK = ("shot", "light", "grade", "style", "texture", "negatives")

# Damon, 2026-09-14: *"I want them to be 9:16, not 4x5 — the 4x5 is just for
# the contents (subject, captions) to fit in there, but the full images should
# always be 9x16 so we can hit all placement."*
#
# Emitted automatically whenever a slot file asks for 9:16, so a prompt cannot
# request the tall canvas without also saying which part of it survives the
# feed crop. SAFE-ZONE.md's clause, structural rather than remembered.
SAFE = (
    "COMPOSITION FOR CROPPING: this frame is 9:16 and will be cropped to a "
    "centred 4:5 window in feed, so the top 15% and the bottom 15% get cut "
    "off. Compose the whole picture for the tall frame — it must read "
    "complete at 9:16, with real scene continuing top and bottom, never "
    "empty space and never a band. But every part that carries meaning — the "
    "subject's face, the eye line, the hands, the body part the proof is on, "
    "the product, and any words — sits inside the centred 4:5 window, "
    "comfortably clear of the top and bottom edges. Treat the outer 15% top "
    "and bottom as bleed: more of the same scene, nothing that must be seen.")


def packs():
    return json.loads(PACKS.read_text())["packs"]


def result_budget():
    """The credibility budget, for an ad whose frame shows an after state.

    Orthogonal to the packs — a pack says how a frame is rendered, this says
    what a frame may CLAIM. Set `"result": true` on the slot file and the
    anchors and bans below join that ad's own. `judge.py` reads the same
    entry, so a picture is never asked for one thing and judged against
    another (Damon, 2026-09-14).
    """
    return json.loads(PACKS.read_text()).get("_result_budget", {})


def baseline(slots, path=None):
    """The batch's one cast and one product, read from a file above the slots.

    A slot file names no person. `cast` and `product` in `references` are
    written as `@cast` and `@product` and resolved here, so swapping the man
    for a whole batch is one line in one file — and every other slot is
    provably untouched (Damon, 2026-09-14: "just change the person").
    """
    f = Path(path or slots.get("baseline") or "")
    if not f.is_file():
        return {}
    b = json.loads(f.read_text())
    cast = b.get("cast") or {}
    prod = b.get("product_ref") or {}
    return {"@cast": cast.get("element"), "@product": prod.get("element"),
            "_cast": cast, "_baseline": b}


def resolve(slots, base=None):
    """Slot values, with the pack filling everything the ad does not override."""
    out, p = {}, {}
    base = base if base is not None else baseline(slots)
    name = slots.get("pack")
    if name:
        p = packs().get(name) or sys.exit(
            f"no style pack {name!r} — have: {', '.join(packs())}")
    for k in KEYS:
        v = slots.get(k)
        if k == "references" and isinstance(v, list):
            v = [base.get(r, r) for r in v]
            missing = [r for r in v if isinstance(r, str) and r.startswith("@")]
            if missing:
                sys.exit(f"{', '.join(missing)} not in the baseline — a slot file "
                         f"names no person, so the baseline must supply one")
            v = [r for r in v if r]
        if v in (None, "") and k in FROM_PACK:
            v = p.get(k)
        if k == "anchors" and slots.get("result"):
            # A result frame carries the credibility budget as positive
            # anchors. Without them the judge fails plates the generator was
            # never told to avoid, which is just a slower way to burn money.
            v = ", ".join(x for x in (v, result_budget().get("anchors")) if x) or None
        if k == "negatives":
            pv = p.get(k) or ""
            if pv and slots.get("copy"):
                # A pack bans text because a plate carries none. A draft
                # carries the ad's words, so those bans would fight the copy
                # slot — p008's pack said "no labels, no callout boxes" while
                # its copy asked for eight of them (2026-09-14).
                pv = ", ".join(x for x in pv.split(", ") if not any(
                    w in x for w in ("text", "lettering", "typography", "words",
                                     "label", "UI", "callout")))
            rb = result_budget().get("negatives") if slots.get("result") else None
            v = ", ".join(x for x in (pv, slots.get(k), rb) if x) or None
        out[k] = v
    return out


def render(slots, base=None):
    base = base if base is not None else baseline(slots)
    v = resolve(slots, base)
    if not v.get("references"):
        print("! no references — if this ad shows a person or the product, "
              "their Element ids belong here", file=sys.stderr)
    parts = []
    for k in KEYS:
        val = v.get(k)
        if not val:
            continue
        if k == "references":
            parts.append(" ".join(f"<<<{r}>>>" for r in val)
                         if isinstance(val, list) else str(val))
            c = base.get("_cast") or {}
            if c and base.get("@cast") in (val if isinstance(val, list) else [val]):
                # His own roster lines, verbatim. The Element carries the face;
                # these carry build, hair and the problem, which the Element
                # does not — and they are the same words every time.
                parts.append(", ".join(x for x in
                    (c.get("reads"), c.get("build"), c.get("hair")) if x))
        elif k == "copy":
            parts.append(str(val) + ". Spell every word exactly as written")
        elif k == "negatives":
            parts.append("NEGATIVE: " + str(val))
        else:
            parts.append(str(val))
    body = " ".join(s.rstrip(" .") + "." for s in parts)
    if slots.get("ratio"):
        body += f" {slots['ratio']}."
        if str(slots["ratio"]).strip() == "9:16":
            body += " " + SAFE
    return body


def diff(a, b):
    ra, rb = resolve(a), resolve(b)
    moved = [(k, ra.get(k), rb.get(k)) for k in KEYS if ra.get(k) != rb.get(k)]
    if a.get("pack") != b.get("pack"):
        moved.insert(0, ("pack", a.get("pack"), b.get("pack")))
    return moved


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render"); r.add_argument("--slots", required=True)
    r.add_argument("--baseline"); r.add_argument("--cast",
        help="override the baseline's cast element for this render only")
    d = sub.add_parser("diff"); d.add_argument("--a", required=True); d.add_argument("--b", required=True)
    sub.add_parser("packs")
    a = ap.parse_args()
    if a.cmd == "packs":
        for k, v in packs().items():
            print(f"  {k:<17} {v['name']:<18} {v['what']}")
    elif a.cmd == "render":
        s = json.loads(Path(a.slots).read_text())
        b = baseline(s, a.baseline)
        if a.cast:
            # A roster id, not an element id. Swapping the man has to swap his
            # own lines too — build, hair, skin — or the new man is rendered
            # under the old one's description (2026-09-14).
            bl = b.get("_baseline", {})
            import paths as _P       # the workspace is found, never counted
            rf = (_P.BRANDS
                  / bl.get("brand", "") / "core-avatars/casting")
            ros, ids = rf / "roster.json", rf / "identities.json"
            man = None
            if ros.is_file():
                def walk(o):
                    if isinstance(o, dict):
                        if o.get("id") == a.cast: return o
                        for v in o.values():
                            g = walk(v)
                            if g: return g
                    if isinstance(o, list):
                        for v in o:
                            g = walk(v)
                            if g: return g
                man = walk(json.loads(ros.read_text()))
            if not man:
                sys.exit(f"no roster man {a.cast!r} for {bl.get('brand')}")
            el = json.loads(ids.read_text())["people"][a.cast]["element_id"]
            if man.get("lane") != bl.get("lane"):
                sys.exit(f"{a.cast} is {man.get('lane')}, this batch is "
                         f"{bl.get('lane')} — lanes never blend")
            b = dict(b, **{"@cast": el, "_cast": man})
        print(render(s, b))
    else:
        m = diff(json.loads(Path(a.a).read_text()), json.loads(Path(a.b).read_text()))
        if not m:
            print("identical — nothing moved")
        for k, x, y in m:
            print(f"  {k}\n    was: {x}\n    now: {y}")
