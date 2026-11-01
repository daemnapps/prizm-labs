"""Compose a picture request from a character's elements — pick at will.

A character's folder holds `elements.json`: the SLOTS (outfit, headwear,
eyewear, jewelry, hands, expression, place, prop) and, for each, the named
OPTIONS a script may pick. `compose()` takes the picks a script names and
returns the one prompt and the reference pictures to send to the edit door.

THE BASELINE IS LAYERED, NOT THE MASTER (the owner, 2026-10-27): headshot, then look,
then details, then expression, with the picked place and props laid on top. The
master is never a reference here. `layers` in the answer names which layer each
reference is.

THE RULE the casting component turns on stays: identity comes from the
character's IMAGE, never from prose. So the first reference is always the
core head shot (clean face, nothing on it) and the prompt says the face is
that face. The elements only say what is ADDED to it.

This module makes no model call, reads no key and writes nothing. It refuses
an unknown slot or option by name rather than guessing; a slot not picked is
left OUT of the prompt (nothing is invented). Python 3.9-safe, stdlib only.
No brand, person or model is named here.
"""
import json
from pathlib import Path

HEADSHOT = "sheets/headshot.jpg"
DETAILS = "sheets/details.jpg"
EXPRESSIONS = "sheets/angles-expressions.jpg"
SKIN = "sheets/skin-closeup.jpg"     # pores, peach fuzz, real eyes (2026-10-28)
FILE = "elements.json"


class PickError(ValueError):
    pass


def load(folder):
    folder = Path(folder)
    data = json.loads((folder / FILE).read_text())
    if "slots" not in data or "identity" not in data:
        raise PickError("%s needs `identity` and `slots`" % (folder / FILE))
    return data


def choices(folder):
    """{slot: [option, ...]} — what a script may pick."""
    return {s: sorted(o) for s, o in load(folder)["slots"].items()}


def compose(folder, picks, scene="", aspect="9:16"):
    """picks: {slot: option}. Returns {prompt, references, aspect, picked}.
    `references` are paths relative to the character's folder."""
    folder = Path(folder)
    data = load(folder)
    slots = data["slots"]
    parts, picked = [], {}
    for slot, option in picks.items():
        if slot not in slots:
            raise PickError("no slot %r (slots: %s)" % (slot, ", ".join(sorted(slots))))
        if option not in slots[slot]:
            raise PickError("slot %r has no option %r (options: %s)"
                            % (slot, option, ", ".join(sorted(slots[slot]))))
        entry = slots[slot][option]
        picked[slot] = option
        parts.append("%s: %s" % (slot, entry["words"]))
    layers = [("headshot", HEADSHOT)]
    look = [r for r in slots.get("outfit", {}).get(picked.get("outfit"), {}).get("references", [])]
    layers += [("look", r) for r in look]
    det = slots.get("outfit", {}).get(picked.get("outfit"), {}).get("details") or data.get("details") or DETAILS
    exp = slots.get("expression", {}).get(picked.get("expression"), {}).get("references", [None])[0] \
        or data.get("expressions") or EXPRESSIONS
    if (folder / det).is_file():
        layers.append(("details", det))
    if (folder / exp).is_file():
        layers.append(("expression", exp))
    if (folder / SKIN).is_file():
        layers.append(("skin", SKIN))
    for slot, option in picked.items():
        if slot in ("outfit", "expression"):
            continue
        for ref in slots[slot][option].get("references", []):
            layers.append((slot, ref))
    refs = []
    for _, r in layers:
        if r not in refs:
            refs.append(r)
    prompt = (
        "The face in the FIRST reference picture (the head shot) is this person's face: same bone structure, skin, age and "
        "features, nothing about the face changes. The next references give the look, the details and the expression. " + data["identity"] + " "
        + ("Dress and set this person with exactly this, and nothing else added: " + "; ".join(parts) + ". "
           if parts else "")
        + (("Scene: " + scene + " ") if scene else "")
        + ("Unretouched skin with pores, photorealistic." if "skin" in picked
           else "Unretouched skin with pores and age spots, photorealistic.")
        + " No text, no logos, no watermark. Single image."
    )
    return {"prompt": prompt, "references": refs, "layers": layers, "aspect": aspect, "picked": picked}


def main(argv=None):
    import sys
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0] in ("-h", "--help"):
        print("usage: python3 -m casting.compose <character-folder> [slot=option ...] [--scene TEXT]\n"
              "       with no picks it lists every slot and option")
        return 0
    folder, scene, picks = a[0], "", {}
    rest = a[1:]
    while rest:
        t = rest.pop(0)
        if t == "--scene":
            scene = rest.pop(0)
        elif "=" in t:
            k, v = t.split("=", 1)
            picks[k] = v
    if not picks:
        print(json.dumps(choices(folder), indent=1))
        return 0
    print(json.dumps(compose(folder, picks, scene), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
