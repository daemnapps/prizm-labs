"""Frame pairs: the start and end frame of one video scene are made from ONE shared sheet.

the owner, 2026-10-26: "a different end frame makes the video bad". So the end frame is the start frame's sheet with only the
declared delta changed; the locked variables (person, wardrobe, product, place and light, photo style, colours, shape,
camera) must be the same in both, or the pair is refused by name before anything is made. The sheet and these two
functions live in components/model-inputs (`make_frame_pair`, `validate_pair`) when they exist; until then the rule below is
the rule, over the sheet's own variable ids (components/model-inputs/picture-sheet.json).

Both frames are made through plain.make with their own recipes; the end frame takes the start frame as IMAGE 1 (so the start
frame must be approved first when the approved-bases gate is on). The run record gets which pictures became which scene's
first and last frame.
"""
import json
import time
from pathlib import Path

from . import approval, plain


class PairRefused(ValueError):
    """The two frames do not share their locked variables: nothing was made."""


LOCKED_FALLBACK = ("brand", "product", "avatar", "people_mode", "people_who", "people_age", "people_look", "person", "wardrobe",
                   "product_kit", "product_sides", "product_size", "place", "light", "place_light", "photo_style",
                   "colours", "shape", "safe_zone", "camera")


def locked():
    IR = plain._rules()
    return tuple(getattr(IR, "LOCKED", None) or LOCKED_FALLBACK)


def make_frame_pair_sheet(sheet, delta):
    """The end frame's sheet: the start sheet with ONLY the delta changed. A delta that touches a locked variable is refused."""
    fn = getattr(plain._rules(), "make_frame_pair", None)
    if fn:
        return fn(sheet, delta)
    bad = sorted(k for k in (delta or {}) if k in locked())
    if bad:
        raise PairRefused("the end frame may not change " + ", ".join(bad) + ": they are locked so the two frames are one scene.")
    if not delta:
        raise PairRefused("the end frame needs a declared delta: what changes between the first and last frame.")
    return {**sheet, **delta}


def validate_pair(a, b):
    """Problems with a pair of sheets, [] when every locked variable is the same."""
    fn = getattr(plain._rules(), "validate_pair", None)
    if fn:
        got = fn(a, b)
        return [] if got in (None, True, [], ()) else [str(x) for x in (got if isinstance(got, (list, tuple)) else [got])]
    return [f"{k} differs between the first and last frame ({a.get(k)!r} vs {b.get(k)!r}) and is locked"
            for k in locked() if k in a or k in b if a.get(k) != b.get(k)]


def record_scene_frames(run_dir, scene_id, first, last, delta=None, t=None):
    """Which approved pictures became which scene's first and last frame, in `<run_dir>/frames.json`. With the approved-bases
    gate on, a frame without an approved record is refused here too."""
    approval.check_bases([first, last], t)
    f = Path(run_dir) / "frames.json"
    doc = json.loads(f.read_text()) if f.is_file() else {}
    doc[str(scene_id)] = {
        "first": {"file": str(first), "approved": bool((approval.read(first) or {}).get("approved")),
                  "below_criteria": approval.flag_of(first)},
        "last": {"file": str(last), "approved": bool((approval.read(last) or {}).get("approved")),
                 "below_criteria": approval.flag_of(last)},
        "delta": delta, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    Path(run_dir).mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    return doc[str(scene_id)]


def make_pair(brand, sheet, delta, texts, out_dir, scene_id, run_dir=None, references=(), **kw):
    """Make a scene's first and last frame from one shared sheet. `texts` = (first picture text, last picture text).
    Returns {"first": record, "last": record, "delta", "end_sheet", "frames": the run-record entry}."""
    end_sheet = make_frame_pair_sheet(sheet, delta)
    bad = validate_pair(sheet, end_sheet)
    if bad:
        raise PairRefused("the two frames are not one scene: " + "; ".join(bad) + ". Nothing was made.")
    out_dir = Path(out_dir)
    first_file, last_file = out_dir / f"{scene_id}-first.png", out_dir / f"{scene_id}-last.png"
    first = plain.make(brand, texts[0], first_file, references=references, recipe=sheet, **kw)
    last = plain.make(brand, texts[1], last_file, references=[first_file, *references], recipe=end_sheet, **kw)
    frames = record_scene_frames(run_dir, scene_id, first_file, last_file, delta) if run_dir else None
    return {"first": first, "last": last, "delta": delta, "end_sheet": end_sheet, "frames": frames}
