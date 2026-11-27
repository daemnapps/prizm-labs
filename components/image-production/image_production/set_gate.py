"""THE 3D SET GATE: every picture is made from a filed 3D set print, or it is not made (2026-11-10).

The owner's picture process (this folder's CLAUDE.md, "Every picture: a 3D set, printed"): the scene is built in 3D Jutsu at
true size, rendered, printed with `scene_builder_3d_generate_angles` (the casting sheet, or the cast board for several
people: `cast_board.py`, as the one reference), filed with `picture_sets.py put --note "kept: ..."`, and the picture is made
from that print. No exceptions (ruled 10 Nov 2026: anything an image is generated for goes through the process,
people or no people, cast sheets too). The process is the check.

Where it stops a picture, before anything is sent:
  - the engine (`engine_gate`): the request names `set`; its kept print is the base; no other base, no `region` patch, no
    picture we made as a reference. A cover (purposes.json `job: "cover"`) is the one other base: the frame of its own
    video is the composition and the kept print rides beside it (`cover_frame`); the set is required all the same;
  - the plain picture (`plain_gate`): IMAGE 1 is a kept print (or a byte copy of one);
  - the video line's still doors and any caller of the doors (`door_gate`): the first reference is a kept print, or the
    call names the kept print it started from (`from_print`, checked);
  - the picture doors themselves (`provider_gate`, in providers.generate / generate_ladder / edit_in_region): a call that
    no gate above cleared (`cleared()`) must start from a kept print too, so a new caller cannot slip past.

ROLLBACK, per lane or all of it (models.json `gate.set_required`, or on one machine the environment):
  "on": false                         everything back to how it was before
  "lanes": {"email": false, ...}      one lane back: statics, email, video, cast, direct, sessions
  PICTURE_GATE_OFF=all | email,video  the same, on this machine only (tests use it for code that is not about the gate)

THE EDIT LANE (2026-11-10): the 3D rule is for new production. Changing a picture that is already approved or live (take one
thing out, fix one part) is an edit, not a new picture, and is made as a masked edit on that picture: the model paints only
inside `region`, and every pixel outside it is the original's (providers.edit_in_region). The base is the set's kept print, or
an approved original filed into the set with `picture_sets.py put <brand> <set> --original F --note "approved: <where it is
live>"`. An edit of an original with no `region` (a whole-picture redraw) is refused. ROLLBACK: models.json
`gate.set_required.edits.on: false` refuses every masked edit again, as before; PICTURE_GATE_OFF=edits does the same on one
machine.
"""
import contextvars
import hashlib
import json
import os
from pathlib import Path

from . import paths as P, route as R

PROCESS = ("the 3D process: build the scene in 3D Jutsu at true size, render it, print it with "
           "scene_builder_3d_generate_angles using the casting sheet (or for several people the cast board, "
           "image-production cast_board.py) as the reference, file it with picture_sets.py put <brand> <set> --print "
           "<file> --note \"kept: ...\", then make the picture from that print (the 3d-print skill does all of it)")
LANES = ("statics", "email", "video", "cast", "direct", "sessions")


class SetRefused(ValueError):
    """A picture without a filed 3D set print: nothing was sent and nothing was spent."""


def config(t=None):
    return ((t or R.table()).get("gate") or {}).get("set_required") or {}


def lane_on(lane, t=None):
    """Whether the gate holds for this lane: the master switch, the lane's switch, and this machine's PICTURE_GATE_OFF."""
    off = {x.strip() for x in os.environ.get("PICTURE_GATE_OFF", "").split(",") if x.strip()}
    if "all" in off or lane in off:
        return False
    cfg = config(t)
    return bool(cfg.get("on")) and (cfg.get("lanes") or {}).get(lane, True) is not False


_CLEARED = contextvars.ContextVar("picture_gate_cleared", default=False)


class cleared:
    """`with cleared():` around the door calls a gate above has already decided on (passed, or its lane rolled back)."""
    def __enter__(self):
        self._tok = _CLEARED.set(True)
        return self

    def __exit__(self, *a):
        _CLEARED.reset(self._tok)
        return False


def _drive_roots():
    return list(Path.home().glob("Library/CloudStorage/*/Shared drives/Shared Assets"))


def homes(brand, name):
    """Every place this set may live: the workspace (set.json in git) and the Drive twin (the pictures)."""
    rel = Path("runs") / "image-production" / brand / "sets" / name
    out = [P.repo() / rel] + [r / rel for r in _drive_roots()]
    return [d for d in out if d.is_dir()]


def record(brand, name):
    for d in homes(brand, name):
        f = d / "set.json"
        if f.is_file():
            try:
                return json.loads(f.read_text())
            except ValueError:
                return {}
    return {}


def edits_on(t=None):
    """Whether the edit lane is open: models.json `gate.set_required.edits.on`, and not PICTURE_GATE_OFF=edits."""
    off = {x.strip() for x in os.environ.get("PICTURE_GATE_OFF", "").split(",") if x.strip()}
    return "edits" not in off and bool((config(t).get("edits") or {}).get("on"))


def originals(brand, name):
    """The set's approved originals (an approved or live picture filed with --original, its note starting "approved"),
    as files on this machine."""
    out = []
    for row in record(brand, name).get("originals") or []:
        if not str(row.get("note", "")).startswith("approved"):
            continue
        for d in homes(brand, name):
            if (d / row["file"]).is_file():
                out.append(d / row["file"])
                break
    return out


def edit_base(brand, name, picture):
    """The picture an edit may start from: the set's kept print or one of its approved originals (byte for byte), else None."""
    want = sha(picture)
    if not want:
        return None
    for f in [kept_print(brand, name)] + originals(brand, name):
        if f is not None and sha(f) == want:
            return Path(picture)
    return None


def kept_print(brand, name):
    """The set's newest kept print (a print whose note starts "kept"), as a file on this machine, or None."""
    r = record(brand, name)
    kept = [p for p in r.get("prints") or [] if str(p.get("note", "")).startswith("kept")]
    for p in reversed(kept):
        for d in homes(brand, name):
            if (d / p["file"]).is_file():
                return d / p["file"]
    return None


def set_name(ref):
    """A set named as its name, its folder, its set.json or one of its prints -> the set's name."""
    s = str(ref or "").strip()
    if not s:
        return ""
    p = Path(s)
    if p.name == "set.json" or p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        return p.parent.name
    return p.name


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest() if f and Path(f).is_file() else None


def is_kept_print(brand, picture):
    """True when `picture` is a kept print of one of the brand's filed sets (the file itself, or a byte-for-byte copy)."""
    if not picture or not Path(picture).is_file():
        return False
    p = Path(picture)
    if (p.parent / "set.json").is_file():                        # the file in its own set folder
        kp = kept_print(brand, p.parent.name)
        if kp is not None and sha(kp) == sha(p):
            return True
    want = sha(p)
    names = set()
    for root in [P.repo()] + _drive_roots():
        base = root / "runs" / "image-production" / brand / "sets"
        if base.is_dir():
            names |= {d.name for d in base.iterdir() if d.is_dir()}
    for n in sorted(names):
        r = record(brand, n)
        for row in r.get("prints") or []:
            if not str(row.get("note", "")).startswith("kept"):
                continue
            for d in homes(brand, n):
                if (d / row["file"]).is_file() and sha(d / row["file"]) == want:
                    return True
    return False


def _ours(pic):
    return Path(str(pic)).with_suffix(".recipe.json").is_file()


def _brands():
    out = set()
    for root in [P.repo()] + _drive_roots():
        base = root / "runs" / "image-production"
        if base.is_dir():
            out |= {d.name for d in base.iterdir() if (d / "sets").is_dir()}
    return sorted(out)


def is_hand_off_print(picture):
    """True when `picture` is a 3D print a maker made from a brief's hand-off step and saved with briefs make.py (its
    <file>.made.json says job 3d-print and matches its bytes): the maker's tools take it like a filed kept print."""
    p = Path(str(picture or ""))
    side = p.parent / (p.name + ".made.json")
    if not p.is_file() or not side.is_file():
        return False
    try:
        rec = json.loads(side.read_text())
    except ValueError:
        return False
    return rec.get("route") == "hand-off" and rec.get("job") == "3d-print" and rec.get("sha256") == sha(p)


def set_of_print(picture):
    """(brand, set name) of the filed set whose kept print `picture` is (the file or a byte copy), or None."""
    if not picture or not Path(str(picture)).is_file():
        return None
    p, want = Path(str(picture)), sha(picture)
    for brand in _brands():
        if (p.parent / "set.json").is_file() and is_kept_print(brand, p):
            return brand, p.parent.name
        for root in [P.repo()] + _drive_roots():
            base = root / "runs" / "image-production" / brand / "sets"
            for d in sorted(base.iterdir()) if base.is_dir() else []:
                r = record(brand, d.name)
                for row in r.get("prints") or []:
                    if str(row.get("note", "")).startswith("kept") and (d / row["file"]).is_file() \
                            and sha(d / row["file"]) == want:
                        return brand, d.name
    return None


def posed_people(brand, name):
    """The cast members a set's print was made with as posed 3D figures: its cast board's members, its record's
    `picture_from` elements and any `people_posed` the record names (lower-case element ids)."""
    out = set()
    r = record(brand, name)
    out |= {str(x).lower() for x in r.get("people_posed") or []}
    out |= {str(x.get("element")).lower() for x in r.get("picture_from") or [] if isinstance(x, dict) and x.get("element")}
    for d in homes(brand, name):
        f = d / "cast-board.json"
        if f.is_file():
            try:
                b = json.loads(f.read_text())
            except ValueError:
                continue
            out |= {str(m.get("element")).lower() for m in b.get("members") or [] if m.get("element")}
            out |= {str(x).lower() for x in b.get("order") or []}
    # a styled variant on the board (best-man/styles/family-3d) poses that same person: its base id counts too
    return out | {x.split("/")[0] for x in out}


def people_gate(picture, people, door="this door", what="this picture"):
    """PEOPLE ARE POSED IN 3D (owner, 21 Nov 2026: "We use this 3D process to not have these problems happen"): a
    picture whose request names its people (cast element ids) is made only from a kept print whose set posed those
    people as 3D figures (printed with the cast board: picture_sets.py put --cast-board). A room-only print passes
    GATE-4 but leaves who stands where, hands and reflections to the picture model; it is refused here and the print
    is queued for the 3d-print skill. `people` that is not a list of ids (None, False, a flag) asks nothing."""
    want = [str(x).lower() for x in people or [] if isinstance(x, str) and x.strip()] \
        if isinstance(people, (list, tuple, set)) else []
    if not want:
        return
    got = set_of_print(picture)
    posed = posed_people(*got) if got else set()
    missing = [x for x in want if x not in posed]
    if not missing:
        return
    brand, name = got if got else ("", None)
    tail = queue_refusal(brand, f"{what}: the set with {', '.join(missing)} posed as 3D figures", name=name,
                         cast=missing, source=door) if brand else ""
    raise SetRefused(f"{door} refuses {what}: its kept print ({Path(str(picture)).name}) does not have "
                     f"{', '.join(missing)} posed in the 3D set (its cast board names {sorted(posed) or 'nobody'}). "
                     f"People are built in the 3D scene as posed figures and printed with the cast board, never "
                     f"painted onto a room print. Nothing was sent and nothing was spent.{tail}")


def is_any_kept_print(picture):
    """True when `picture` is a kept print (or its copy) of any brand's filed set, or a hand-off 3D print: the machine
    doors know no brand."""
    return is_hand_off_print(picture) or any(is_kept_print(b, picture) for b in _brands())




def lane_of_purpose(purpose):
    return "video" if purpose == "video-still" else "email" if str(purpose or "").startswith("email") else "statics"


def cover_frame(req, purpose_row=None, t=None):
    """The frame of the version's own video a cover is composed from (`cover.frame`), when the purpose runs the cover job
    (purposes.json `job: "cover"`) and its source-frame switch is on (models.json `gate.cover.source_frame`); else None."""
    if (purpose_row or {}).get("job") != "cover":
        return None
    from . import covers
    if not covers.on("source_frame", t):
        return None
    f = (req.get("cover") or {}).get("frame") if isinstance(req.get("cover"), dict) else None
    return Path(str(f)).expanduser() if f else None


def engine_gate(req, purpose_row=None, t=None):
    """The engine's stop. Returns the kept print (the base the picture is made from), or None when the lane is rolled back.

    A COVER (2026-11-12) is composed from a frame of its own video: the frame is its base and the kept print rides beside
    it as the second picture, deciding the people and the room. The filed set and its kept print are still required, so
    no people picture is made without one. What the frame itself may be is the cover job's check (covers.py)."""
    if not lane_on(lane_of_purpose(req.get("purpose")), t):
        return None
    what = f"this {req.get('purpose')} picture"
    name = set_name(req.get("set"))
    if not name:
        raise SetRefused(f"components/image-production refuses {what}: it names no filed 3D set (`set`). Every picture "
                         f"goes through {PROCESS}. Nothing was sent and nothing was spent.")
    fi = req.get("from_image")
    if req.get("region") and fi and edits_on(t):                 # THE EDIT LANE: a masked edit of an approved picture
        base = edit_base(req["brand"], name, fi)
        if base is not None:
            return base
        raise SetRefused(f"components/image-production refuses {what}: an edit starts from set `{name}`'s kept print or an "
                         f"approved original filed into it (picture_sets.py put {req['brand']} {name} --original <file> "
                         f"--note \"approved: ...\"), not from {fi}. Nothing was sent and nothing was spent.")
    if fi and not req.get("region") and edits_on(t) and any(sha(o) == sha(fi) for o in originals(req["brand"], name)):
        raise SetRefused(f"components/image-production refuses {what}: an edit of an approved original is a masked edit "
                         f"(`region`, the part to change); a whole-picture redraw would repaint the product. Nothing was "
                         f"sent and nothing was spent.")
    pr = kept_print(req["brand"], name)
    if pr is None:
        raise SetRefused(f"components/image-production refuses {what}: set `{name}` has no kept print on this machine "
                         f"(runs/image-production/{req['brand']}/sets/{name}/set.json, a print whose note starts "
                         f"\"kept\"). Finish {PROCESS}. Nothing was sent and nothing was spent.")
    if req.get("region"):
        raise SetRefused(f"components/image-production refuses {what}: a masked patch (`region`). A wrong part is a new "
                         f"print of set `{name}`, never a patch (one picture process, no rounds); the edit lane takes a "
                         f"masked edit of the kept print or an approved original (`from_image` and `region`) when "
                         f"gate.set_required.edits is on. Nothing was sent and nothing was spent.")
    if cover_frame(req, purpose_row, t) is not None:
        if fi and sha(fi) != sha(pr):
            raise SetRefused(f"components/image-production refuses {what}: a cover takes no `from_image` ({fi}). Its base "
                             f"is the frame of its own video (`cover.frame`), with set `{name}`'s kept print beside it. "
                             f"Nothing was sent and nothing was spent.")
    elif fi and sha(fi) != sha(pr):
        raise SetRefused(f"components/image-production refuses {what}: it is made from {fi}, not from set `{name}`'s "
                         f"kept print ({pr.name}). A picture starts from its print, never from another picture. "
                         f"Nothing was sent and nothing was spent.")
    made = [str(x) for x in req.get("references") or [] if _ours(x)]
    if made:
        raise SetRefused(f"components/image-production refuses {what}: a picture we made is a reference "
                         f"({', '.join(made)}). No AI picture is a reference. Nothing was sent and nothing was spent.")
    return pr


def plain_gate(brand, references, kind="picture", people=None, people_lines=(), ref_says=None, t=None, lane="statics"):
    """The plain picture's stop: IMAGE 1 is a kept print (or a byte copy of one). The board makes no call at all when the
    run has a kept print, so a picture reaching here without one is the bypass. `people` is no longer an exception."""
    if not lane_on(lane, t):
        return
    first = list(references or [])[:1]
    if first and is_kept_print(brand, first[0]):
        return
    raise SetRefused(f"components/image-production refuses this {kind}: IMAGE 1 is not a filed 3D set's kept print "
                     f"({first[0] if first else 'no reference'}). Every picture goes through {PROCESS}. Nothing was "
                     f"sent and nothing was spent.")


def door_gate(references, people=None, cast_sheet=False, door="this door", t=None, from_print=None, lane=None):
    """A picture door called directly (the video line's still doors, the draft rolls, casting, the Studio's motion first
    frame): the first reference is a kept print, or the call names the kept print it started from (`from_print`, the
    board's L-40 realism pass), which is checked. A cast sheet is no exception: its lane is "cast"."""
    lane = lane or ("cast" if cast_sheet else "video")
    if not lane_on(lane, t):
        return
    if from_print and is_any_kept_print(from_print):
        people_gate(from_print, people, door)
        return
    first = list(references or [])[:1]
    if first and is_any_kept_print(first[0]):
        people_gate(first[0], people, door)
        return
    raise SetRefused(f"{door} refuses this picture: its first picture is not a filed 3D set's kept print "
                     f"({first[0] if first else 'no picture'}). Every picture, cast sheets included, goes through "
                     f"{PROCESS}. File it with picture_sets.py request <brand> \"<what>\" for the 3d-print skill. "
                     f"Nothing was sent and nothing was spent.")


def provider_gate(references, t=None):
    """The last stop, inside the picture doors: a call no gate above cleared must start from a kept print (lane "direct")."""
    if _CLEARED.get():
        return
    door_gate(references, door="image-production picture door", t=t, lane="direct")


SKILL = "the 3d-print skill (.claude/skills/3d-print/SKILL.md) builds, prints and files it, then runs this step again"


def queue_refusal(brand, what, name=None, products=(), cast=(), words=(), resume=None, source=None, **extra):
    """File a refused picture into the 3D print queue (set_queue.py); returns the sentence a refusal ends with. Never
    raises: a queue that cannot be written still leaves the refusal, named."""
    try:
        from . import set_queue
        f = set_queue.file(brand, what, name=name, products=products, cast=cast, words=words, resume=resume,
                           source=source, **extra)
        return f" Queued for the 3D print as {f.stem} ({P.rel(f)}): {SKILL}."
    except Exception as ex:                                  # noqa: BLE001
        return f" (Not queued: {type(ex).__name__}: {str(ex)[:120]}. File it with picture_sets.py request.)"

