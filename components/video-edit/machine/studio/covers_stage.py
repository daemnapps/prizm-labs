"""THE COVER STAGE (2026-11-12): once a production's versions are rendered, the Studio makes every version's cover
itself and hands them to the filer. Nobody presses anything and nobody is asked: where the rule settles a choice, the
stage makes it and writes down why, and the board shows it per version (Covers tab, GET /api/covers/<production>).

    python3 covers_stage.py run <production>                    the whole stage, now
    python3 covers_stage.py state <production>                  what it picked and why, per version (what the board reads)
    python3 covers_stage.py file-args <production> [--media <video> ...]
                                                                the filer's --thumbs and --cover-records, video for video

The steps (each one a step on the Next step screen, STEPS below):
  frames     one frame a second across each version's opener (`opener_seconds`); the strongest moment is the frame
             where a face fills the most of the picture (the closest reaction), and no two versions take the same
             moment (the cover rule's picture hash). It is saved as that cover's reference frame.
  concept    the swipe each cover follows: the ad's own (brief.json `covers.<version>.swipe`, `covers.swipes`), else the
             avatar's own Explore pull in the cover index (components/asset-index/swipes covers.py `find_covers`,
             scope `avatar` only), most liked first, a different one per version. Every swipe, the ad's own too, must
             be one of the avatar's own covers in the index with a rated move: that move is the concept the cover
             blends in. A version with none is held (`concept_required`).
  direction  the frame, the concept's move, the one thing pushed and the version's headline, in image production's
             standing cover direction (its prompts/cover-direction, latest version). The headline is the ad's own
             (`covers.<version>.headline`), else the first line of the version's opener that its siblings do not say,
             whole or cut at a first clause of at least three words; a line ends at . ? ! never at an abbreviation,
             an initial or an ellipsis inside it (`whole_sentences`). A version whose line has no whole clause of 3 to
             `headline_words` words, is one word, or opens a quote it does not close, is held until the brief names
             its headline.
  make       image production's cover job, every version in one job (`make.py covers --job`): people on, the ad's cast
             sheets as references, its product, and its filed 3D set: the brief's own, else the set the production's
             own takes, start frames or kept prints were made from (`pick_set`). Nothing is sent when no set is filed,
             the ad names no cast, or this machine has no face reader. A re-run makes only the versions not yet ready
             (`--only`). The tool refuses before anything is spent when a set, a kit or a headline is not right; the
             refusal is shown as said. Only a record the tool wrote for this run is read back.
  check      per cover: the tool's own verdict, 9:16 at least 1080 wide under 10 MB, the words off every face, every
             face against the ad's cast sheets (video-production face_gate), made by the tool (meta-upload
             made_by_tool, GATE-5), not the same picture as a sibling, and the card's four cover checks
             (meta-upload cover_rule) on the set as it will be filed. A face or sameness miss is made again from the
             next-strongest frame and the next swipe (`remakes` times), then held. A check that could not be read
             holds the version with its reason (`hold_unread`); a face check that stopped or whose judge did not
             answer (UNCHECKED, or an empty or unknown verdict) is not read, never a miss, so it is never made again
             (`face_unread`).
  file       to-file.json: the versions' videos in card order, the cover for each and its record. The filer takes them
             as `thumbs` and `cover_records` (to_check.py), video for video; a held version has none and the card's
             cover check holds it. A run withdraws the last hand-off before it starts, and a cover whose video was
             rendered again since is never handed over. The set goes over whole or not at all: while any version is
             held, every thumb is '' (`whole_hand_off`).

The stage is never offered or run for a production whose card is approved, live or already carries a cover for every
video (`skip_closed`, read from the card tree: meta-upload cards.py); such a production keeps "Open Versions". The card
is found by the full brief key, the Studio's filed-brief lookup included (`filed_brief`); a card with only some
versions' covers does not stop the rest being made (`whole_hand_off`).

Files, in briefs/<production>/covers/: <version>/frames/ (the sweep), <version>/<version>-frame.jpg (the picked
moment), job.json (what was sent), made/ (the image tool's out: covers, records, covers.json), stage.json (every pick
and check, the board's source) and to-file.json (the hand-off).

The brief's own choices win over the stage's (brief.json `covers`): {"avatar", "swipes": [...], "product", "set",
"people", "cast": [the cast ids the covers show; default the ad's whole cast], "<version>": {"headline", "swipe", "at",
"direction", "set", "product"}}.

SWITCH: cover-stage.json beside this file (`on`, `after_render`, and the parts `skip_closed`, `hold_unread`,
`concept_required`, `pick_set`, `filed_brief`, `face_unread`, `whole_hand_off`, `whole_sentences`), or VIDEO_STUDIO_COVERS_OFF=1 / =<part>[,<part>] on one machine. Row COVER-STAGE in
team/rollbacks.md.

THE THREE COVER RULES (faces against the cast and off the words, no sibling's picture or headline, a proven cover to
follow) are the chain's, called from here, never copied (owner ruling 2026-11-16, V57 (swipe is the backbone)):
components/video-edit/machine/cover_rules.py. This file runs the Studio's stage around them.
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")  # the Studio's production side (settings, takes, voices) until each seam is cut
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))  # this folder first, then the Studio it serves
import settings as ST  # noqa: E402
CR = ST.chain("video-edit", "cover_rules")     # the three cover rules: one home for every path

CONF = HERE / "cover-stage.json"
STEPS = [("frames", "Strongest moment of each version"), ("concept", "An Explore cover for each to follow"),
         ("direction", "Each cover's direction"), ("make", "Every cover made in image production"),
         ("check", "Faces, sameness and the card's cover checks"), ("file", "Covers handed to the filer")]
COVER_MIN_W, COVER_MAX_BYTES = 1080, 10_000_000
NO_MOVE = CR.NO_MOVE
NAME_THE_CAST = CR.NAME_THE_CAST
SAME_AT_BITS = CR.SAME_AT_BITS


# ---------------------------------------------------------------- the switch
def conf() -> dict:
    try:
        return json.loads(CONF.read_text())
    except (OSError, ValueError):
        return {}


def _env_off() -> set:
    return {x.strip() for x in os.environ.get("VIDEO_STUDIO_COVERS_OFF", "").split(",") if x.strip()}


def on() -> bool:
    """Is the cover stage on? No switch file: on."""
    return not (_env_off() & {"1", "all", "on"}) and conf().get("on", True) is not False


def after_render() -> bool:
    """Does the render step run straight on into the covers?"""
    return on() and "after_render" not in _env_off() and conf().get("after_render", True) is not False


PARTS = ("skip_closed", "hold_unread", "concept_required", "pick_set", "filed_brief", "face_unread",
         "whole_hand_off", "whole_sentences")


def part_on(name) -> bool:
    """One part of the stage (PARTS), on unless cover-stage.json says `"<name>": false` or this machine's
    VIDEO_STUDIO_COVERS_OFF names it."""
    return name not in _env_off() and conf().get(name, True) is not False


# ---------------------------------------------------------------- neighbours, loaded by path
def _by_path(name, f):
    f = Path(f)
    if not f.is_file():
        return None
    sys.path.insert(0, str(f.parent))
    spec = importlib.util.spec_from_file_location(name, f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MODS = {}


def _mod(key):
    """A neighbour the stage reads from, loaded once; None when this workspace does not carry it."""
    if key not in _MODS:
        where = {"rule": ST.part("meta-upload") / "cover_rule.py",
                 "made_by": ST.part("meta-upload") / "made_by_tool.py",
                 "find": ST.part("asset-index") / "swipes" / "covers.py",
                 "face_gate": ST.part("video-production") / "machine" / "face_gate.py",
                 "scene": ST.part("video-edit") / "machine" / "thumbs.py",
                 "cards": ST.part("meta-upload") / "cards.py"}[key]
        try:
            _MODS[key] = _by_path("cover_stage_" + key, where)
        except (Exception, SystemExit):  # noqa: BLE001 — a neighbour that cannot load is "not read", never a crash
            _MODS[key] = None
    return _MODS[key]


def index_dir() -> Path:
    """The cover swipe index (components/asset-index/swipes): VIDEO_STUDIO_COVER_INDEX, else runs/asset-index/swipes/covers."""
    return Path(os.environ.get("VIDEO_STUDIO_COVER_INDEX") or ST.REPO / "runs" / "asset-index" / "swipes" / "covers")


def image_tool() -> Path:
    return ST.part("image-production") / "make.py"


def same_at_bits() -> int:
    rule = _mod("rule")
    try:
        return int(rule.same_at_bits()) if rule else SAME_AT_BITS
    except Exception:  # noqa: BLE001
        return SAME_AT_BITS


def dhash(picture):
    rule = _mod("rule")
    if rule:
        return rule.dhash(picture)
    return CR.dhash(picture)


apart = CR.apart


# ---------------------------------------------------------------- the production
def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _save(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n")
    os.replace(tmp, p)


def folder(n, B=None) -> Path:
    return Path(B) if B else ST.BRIEFS / n


def versions_of(n, B=None) -> list:
    """The production's finished versions, control first, in the order they go on the card: the Studio's own list
    (video_studio.versions), each with its video as a full path."""
    B = folder(n, B)
    try:
        import video_studio as VS
        rows = VS.versions(n) if not B or Path(VS.bdir(n)).resolve() == B.resolve() else None
    except Exception:  # noqa: BLE001
        rows = None
    if rows is None:
        rows = _versions_here(n, B)
    return with_video(rows, B)


def with_video(rows, B) -> list:
    """The Studio's version rows (`file` relative to the briefs folder), each with its video as a full path."""
    root = Path(B).parent
    return [r if r.get("video") else dict(r, video=str((root / r["file"]).resolve())) for r in rows or []]


def _versions_here(n, B):
    cuts = sorted(B.glob("rough-cut-v*-sdr.mp4"), key=lambda f: int(re.search(r"-v(\d+)-", f.name).group(1)))
    out = [{"id": "control", "label": "Control", "file": "%s/%s" % (n, cuts[-1].name)}] if cuts else []
    for d in sorted(p for p in (B / "versions").glob("*") if p.is_dir()):
        f = sorted(d.glob("*-%s.mp4" % d.name))
        if f:
            out.append({"id": d.name, "label": d.name, "file": "%s/versions/%s/%s" % (n, d.name, f[0].name)})
    return out


def brief_of(B) -> dict:
    return _load(Path(B) / "brief.json", {}) or {}


def mine(brief) -> dict:
    """The ad's own cover choices (brief.json `covers`)."""
    c = brief.get("covers")
    return c if isinstance(c, dict) else {}


def _own(own, vid) -> dict:
    """The ad's own choices for one version (brief.json `covers.<version>`)."""
    v = own.get(vid)
    return v if isinstance(v, dict) else {}


def _studio():
    """The Video Studio's own module (video_studio.py): the running one when the Studio imported this stage, else
    loaded; None when it cannot load."""
    for name in ("video_studio", "__main__"):
        m = sys.modules.get(name)
        if m is not None and hasattr(m, "filed_brief") and hasattr(m, "versions"):
            return m
    try:
        import video_studio as VS
        return VS
    except (Exception, SystemExit):  # noqa: BLE001
        return None


def filed_key(brief, n=None):
    """The full brief key the production was filed under when brief.json never got it: the Studio's own lookup in
    the brand's brief list (video_studio.filed_brief), for a production filed straight from a card. None when it has
    none, or `filed_brief` is off."""
    if not part_on("filed_brief"):
        return None
    vs = _studio()
    try:
        return (vs.filed_brief(brief, n) or None) if vs else None
    except (Exception, SystemExit):  # noqa: BLE001
        return None


def brief_key(brief, n=None) -> str:
    """The production's brief key (`<brand>_<product>_<brief>`): brief.json's `brief_key`, else the number the brand's
    brief list filed it under (filed_key), else brief.json's `brief`, else the production's name."""
    return str(brief.get("brief_key") or filed_key(brief, n) or brief.get("brief") or n or "")


def brand_of(brief) -> str:
    b = brief.get("brand") or (brief.get("shot_fill") or {}).get("brand")
    if b:
        return str(b)
    key = brief_key(brief)
    return key.split("_", 1)[0] if "_" in key else key.split("-", 1)[0]


def avatar_slug(a):
    """An avatar as the cover index files it: lower-case, spaces and underscores to dashes."""
    s = re.sub(r"[\s_]+", "-", str(a or "").strip().lower()).strip("-")
    return s or None


def avatar_of(brief):
    a = mine(brief).get("avatar") or (brief.get("audience") or {}).get("avatar") or brief.get("avatar")
    return avatar_slug(a) if a else None


def product_of(brief):
    c = mine(brief)
    if "product" in c:
        return c["product"] or None
    return brief.get("product") or (brief.get("shot_fill") or {}).get("product") or None


def masters_of(brief, version=None) -> list:
    """The cover's cast sheets: each cast element's master (runs/ai-elements/<brand>/casting/<id>/full/master.png).
    The people one version's cover shows (brief.json `covers.<version>.cast`), else the people the covers show
    (`covers.cast`), else the ad's whole cast. The face
    gate needs every sheet it is handed to be on the picture, so a cover is checked against the people on it, not
    every person in the ad."""
    casting = Path(os.environ.get("VIDEO_STUDIO_CASTING") or ST.REPO / "runs" / "ai-elements")
    out = []
    own = (_own(mine(brief), version).get("cast") if version else None) or mine(brief).get("cast")
    for el in (own if isinstance(own, list) and own else brief.get("cast") or []):
        # a person banked with their master at the casting folder's top (master.jpg) is found too (2026-11-21,
        # brief-0380: Yai's master was casting/yai/master.jpg and the cover face check skipped her without a word)
        home = casting / brand_of(brief) / "casting" / str(el)
        m = next((home / x for x in ("full/master.png", "full/master.jpg", "master.png", "master.jpg")
                  if (home / x).is_file()), None)
        if m:
            out.append(str(m))
        else:
            print("covers: no master for %s in %s, so the cover face check cannot check them" % (el, home),
                  file=sys.stderr)
    return out


def opener_scene(brief, vid):
    """The scene a version opens on: its hook when it has one, else the production's first scene."""
    hooks = [str(h) for h in brief.get("hooks") or []]
    if vid != "control":
        for part in reversed(str(vid).split("-")):
            if part in hooks:
                return part
    return (brief.get("order") or [None])[0]


def opener_words(B, brief, scene) -> str:
    take = (brief.get("picks") or {}).get(scene)
    wf = _load(Path(B) / "scenes" / str(scene) / ("%s.json" % take), {}) if take else {}
    words = wf.get("words") or " ".join(str(st.get("prompt") or "") for st in wf.get("steps") or []
                                        if st.get("tool") in ("voice.ai", "voice.read"))
    if not str(words or "").strip():     # a read with no prompt (a sung slice, a kept read): its words in voice/reads.json
        words = ((_load(Path(B) / "voice" / "reads.json", {}) or {}).get("lines") or {}).get(str(scene), {}).get("text") or ""
    return " ".join(str(words or "").split())


ABBREV, NUMBERED, MIN_CLAUSE = CR.ABBREV, CR.NUMBERED, CR.MIN_CLAUSE
_END, _ends_here, _balanced, _norm = CR._END, CR._ends_here, CR.balanced, CR._norm


def sentences(words) -> list:
    """The lines of the words, whole (the chain's cover_rules.sentences; `whole_sentences` off: every . ? ! ends one)."""
    return CR.sentences(words, part_on("whole_sentences"))


def headline_for(vid, own_words, sibling_words, limit=8):
    """(headline, why): the chain's sibling rule (cover_rules.headline_for): the first line of this version's opener
    that its siblings do not open with, whole or cut at its first clause, within `limit` words."""
    return CR.headline_for(vid, own_words, sibling_words, limit, part_on("whole_sentences"))


# ---------------------------------------------------------------- 1 frames
def grab(video, t, dest) -> bool:
    """One frame of the video at second t."""
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", "%.3f" % max(0.0, t), "-i", str(video),
                        "-frames:v", "1", "-q:v", "2", str(dest)], capture_output=True)
    return r.returncode == 0 and Path(dest).is_file()


def face_reader():
    """The local face reader the edit line uses (video-edit thumbs.scenes, macOS Vision); None when this machine has none."""
    m = _mod("scene")
    return getattr(m, "scenes", None) if m else None


def _face_area(row) -> float:
    return max((float(b.get("w", 0)) * float(b.get("h", 0)) for b in (row or {}).get("faces") or []), default=0.0)


def sweep(video, dest, seconds=6, grab_=None, read=None) -> list:
    """One frame a second across the opener, each with how much of it the largest face fills. Best first."""
    grab_ = grab_ or grab
    rows = []
    for k in range(int(seconds)):
        t = k + 0.5
        f = Path(dest) / ("t%02d.jpg" % k)
        if grab_(video, t, f):
            rows.append({"t": t, "file": str(f)})
    if not rows:
        return []
    read = read if read is not None else face_reader()
    said = None
    if read:
        try:
            said = read([Path(r["file"]) for r in rows])
        except Exception as e:  # noqa: BLE001 — no reader is not a stop: the moments are then ranked by time
            said, rows[0]["reader"] = None, "the face reader stopped (%s)" % type(e).__name__
    for i, r in enumerate(rows):
        r["face"] = round(_face_area(said[i]), 4) if said and i < len(said) else None
        r["hash"] = dhash(r["file"])
    seen = any(r["face"] for r in rows)
    order = sorted(rows, key=lambda r: (-(r["face"] or 0), abs(r["t"] - 1.5))) if seen else \
        sorted(rows, key=lambda r: abs(r["t"] - 1.5))
    for i, r in enumerate(order):
        r["rank"] = i + 1
    return order


def pick_moment(cands, taken, near) -> tuple:
    """(row, why) — the strongest moment whose picture is not a sibling's picked one."""
    if not cands:
        return None, "no frame could be read from its video"
    for r in cands:
        if r.get("hash") and any(h and apart(r["hash"], h) <= near for h in taken):
            continue
        break
    else:
        r = max(cands, key=lambda c: min((apart(c["hash"], h) for h in taken if h and c.get("hash")), default=64))
    if r.get("face"):
        why = "the closest face of its opener: it fills %d%% of the frame at %.1f s" % (round(100 * r["face"]), r["t"])
    else:
        why = "no face read in its opener: %.1f s, nearest the hook's first beat" % r["t"]
    if r is not cands[0]:
        why += " (a stronger moment, %.1f s, is another version's picture)" % cands[0]["t"]
    return r, why


# ---------------------------------------------------------------- 2 concept
def index_rows() -> dict:
    rows = _load(index_dir() / "covers.json", [])
    rows = rows if isinstance(rows, list) else (rows or {}).get("covers") or []
    return {str(r.get("id")): r for r in rows if isinstance(r, dict) and r.get("id")}


def find_swipes(avatar, limit, find=None) -> dict:
    """The avatar's own Explore covers, best first: {"scope", "note", "covers"}."""
    if find is None:
        m = _mod("find")
        if not m or not (index_dir() / "covers.json").is_file():
            return {"scope": "none", "note": "no cover index in this workspace (%s)" % index_dir(), "covers": []}
        find = lambda a, n: m.find_covers(index_dir(), avatar=a, rank="likes", limit=n)  # noqa: E731
    try:
        return find(avatar_slug(avatar), limit) or {}
    except (Exception, SystemExit) as e:  # noqa: BLE001 — the index stopping is a held version, never a crash
        return {"scope": "none", "note": "the cover index could not be read (%s)" % (str(e) or type(e).__name__),
                "covers": []}


def swipe_row(sid, rows=None) -> dict:
    r = (rows if rows is not None else index_rows()).get(str(sid)) or {}
    return {"id": str(sid), "move": r.get("move"), "move_why": r.get("move_why"), "likes": r.get("likes"),
            "views": r.get("views"), "author": r.get("author"), "url": r.get("url"), "platform": r.get("platform"),
            "picture": r.get("frame_file")}


def _swipe_why(s, avatar, rank):
    bits = ["%s likes" % format(s["likes"], ",")] if s.get("likes") else []
    bits += ["%s views" % format(s["views"], ",")] if s.get("views") else []
    move = (s.get("move") or "").replace("-", " ")
    lead = ("%s on the %s Explore pull" % ("the most-liked cover" if rank == 1 else "number %d by likes" % rank, avatar)
            if avatar else "on the cover index")
    return lead + (", making a move: %s" % move if move and s.get("move") not in NO_MOVE else ", no move rated") + \
        (" (%s)" % ", ".join(bits) if bits else "")


# ---------------------------------------------------------------- 3 direction
def direction_template() -> str | None:
    """The image tool's standing cover direction (prompts/cover-direction-vN.md, highest N), the prompt below `---`."""
    best, best_v = None, -1
    for f in (ST.part("image-production") / "prompts").glob("cover-direction-*.md"):
        m = re.search(r"-v(\d+)", f.name)
        v = int(m.group(1)) if m else 0
        if v > best_v:
            best, best_v = f, v
    if not best:
        return None
    parts = re.split(r"^---\s*$", best.read_text(), maxsplit=1, flags=re.M)
    return " ".join((parts[1] if len(parts) > 1 else parts[0]).split())


def direction_for(headline, swipe) -> str | None:
    tmpl = direction_template()
    if not tmpl:
        return None
    move = (swipe.get("move") or "")
    concept = ""
    if move and move not in NO_MOVE:
        concept = " The move to make, taken from a real cover this audience already sees: %s." % move.replace("-", " ")
        if swipe.get("move_why"):
            concept += " What that cover does: %s." % str(swipe["move_why"]).rstrip(".")
    said = " ".join(str(headline).split()).replace('"', "'")
    return tmpl.replace("{headline}", said).replace("{concept}", concept)


# ---------------------------------------------------------------- 4 make
def run_tool(job_path, only=None):
    """image production's cover job, as it is run by hand: (exit code, what it said)."""
    cmd = [sys.executable, str(image_tool()), "covers", "--job", str(job_path)]
    for v in only or []:
        cmd += ["--only", v]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ST.REPO), timeout=7200)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-") or "version"


# ---------------------------------------------------------------- 5 check
def _fits(pic):
    try:
        from PIL import Image
        with Image.open(pic) as im:
            w, h = im.size
    except Exception:  # noqa: BLE001
        return False, "the picture cannot be opened"
    size = Path(pic).stat().st_size
    if abs(w / h - 9 / 16) > 0.01 or w < COVER_MIN_W or size > COVER_MAX_BYTES:
        return False, "%dx%d, %.1f MB: a cover is 9:16, at least %d wide, under 10 MB" % (w, h, size / 1e6, COVER_MIN_W)
    return True, "%dx%d, %.1f MB" % (w, h, size / 1e6)


def words_off_faces(pic, box_px, read=None):
    """(ok, short): the chain's rule (cover_rules.words_off_faces): the headline's box touches no face on the cover."""
    return CR.words_off_faces(pic, box_px, read if read is not None else face_reader())


def faces_against_cast(pic, masters, check=None):
    """(ok, short): the chain's rule (cover_rules.faces_against_cast): every face on the cover against the ad's cast
    sheets (video-production face_gate). None when the ad names no cast sheet."""
    if not masters:
        return None, NAME_THE_CAST
    unread = part_on("face_unread")
    if check is None:
        fg = _mod("face_gate")
        if not fg:
            return None, "the face gate is not in this workspace"
        check = CR.face_gate_check(fg, unread)
    return CR.faces_against_cast(pic, masters, check, unread)


_who, _not_read, _unanswered = CR.who, CR.not_read, CR.unanswered
READ_VERDICTS = CR.READ_VERDICTS       # the face judge's answers; any other verdict is no answer


def made_by_tool(pics, refuse=None):
    """{picture: (ok, short)} from the filer's own gate (GATE-5): True only for a picture the gate read and found in
    an image-production record; None (not read) when the gate is off for the video lane, stopped, or skipped it."""
    if refuse is None:
        m = _mod("made_by")
        if not m:
            return {p: (None, "the filer's gate is not in this workspace") for p in pics}
        try:
            if not m.on("video"):
                return {p: (None, "the filer's gate (GATE-5) is off for the video lane here") for p in pics}
        except (Exception, SystemExit) as e:  # noqa: BLE001
            return {p: (None, "the filer's gate could not be read (%s)" % type(e).__name__) for p in pics}
        refuse = lambda ps: m.refuse("video", ps)  # noqa: E731
    try:
        seen, bad = refuse([str(p) for p in pics])
    except (Exception, SystemExit) as e:  # noqa: BLE001
        return {p: (None, "the filer's gate could not be read (%s)" % type(e).__name__) for p in pics}
    out = {}
    for p in pics:
        hit = [b for b in bad if b.startswith(Path(p).name + ":")]
        rec = (seen or {}).get(str(p))
        out[p] = ((False, hit[0][:200]) if hit else
                  (True, "in an image-production record (%s)" % Path(str(rec.get("record") or "")).name
                   if isinstance(rec, dict) else "in an image-production record") if rec else
                  (None, "the filer's gate did not read it"))
    return out


def card_checks(rows, where):
    """The card's four cover checks (meta-upload cover_rule) on the covers as they will be filed."""
    rule = _mod("rule")
    if not rule:
        return {"cover_rule": {"ok": None, "why": "the card's cover checks (meta-upload cover_rule.py) are not in "
                                                  "this workspace"}}
    media = [r["video"] for r in rows]
    pairs = [(r["video"], Path(r["video"]).name, r["file"], r["file"]) for r in rows if r.get("file")]
    try:
        card = {"media": [Path(v).name for v in media], "lane": "video",
                "made_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "thumbs": {Path(r["video"]).name: r["file"] for r in rows if r.get("file")},
                "cover_records": rule.for_filing(pairs, [r.get("record") for r in rows if r.get("file")])}
        return rule.checks(Path(where), card, lane="video", state="1-check")   # {}: the rule is switched off here
    except (Exception, SystemExit) as e:  # noqa: BLE001
        return {"cover_rule": {"ok": None, "why": "the card's cover checks could not run (%s)" % e}}


def fill_record(rec_file, want):
    """The cover's record beside it: the image tool's own, kept whole; only what it does not say is filled in."""
    have = _load(rec_file, {}) or {}
    for k in ("version", "swipe", "headline"):
        if have.get(k) in (None, ""):
            have[k] = want[k]
    key = "source_frame" if "source_frame" in have else "frame"
    fr = have.get(key) if isinstance(have.get(key), dict) else {}
    for k, v in want["frame"].items():
        if fr.get(k) in (None, ""):
            fr[k] = v
    have[key] = fr
    _save(rec_file, have)
    return str(rec_file)


# ---------------------------------------------------------------- the card: approved, live or already covered
_CARDS = {}
CARDS_TTL = 60
OPEN_CARDS = ("1-check", "sent-back")


def _cards_root(m):
    """The card tree to read: META_CARDS_ROOT, else the shared drive's meta folder on this machine's mount; None when
    neither is here. The API copy is not fetched for this read."""
    if os.environ.get("META_CARDS_ROOT"):
        return Path(os.environ["META_CARDS_ROOT"])
    sd = getattr(m, "SD", None)
    try:
        base = sd.shared_assets() if sd else None
        return base / "meta" if base is not None and sd.mounted(base) else None
    except (Exception, SystemExit):  # noqa: BLE001
        return None


def _card_is(card, key, brand, names=None) -> bool:
    """Is this card the production's ad? Same brand, and the same full brief key (brand + product + brief), or an ad
    name that starts with the production's key."""
    if not key:
        return False
    if brand and card.get("brand") and str(card["brand"]) != brand:
        return False
    ad = str(card.get("ad_name") or "")
    if ad == key or ad.startswith(key + "_"):
        return True
    try:
        return bool(names and names.same_brief(ad, key))
    except (Exception, SystemExit):  # noqa: BLE001
        return False


def cards_for(brand, key) -> list:
    """[(state, card.json)] for every card of this ad in the card tree (meta-upload cards.py), newest first. Raises
    when the card tree cannot be read here."""
    m = _mod("cards")
    if not m:
        raise RuntimeError("the card tree's reader (meta-upload cards.py) is not in this workspace")
    root = _cards_root(m)
    if root is None or not root.is_dir():
        raise RuntimeError("the card tree (the shared drive's meta folder, or META_CARDS_ROOT) is not on this machine")
    k = (str(root), brand, key)
    hit = _CARDS.get(k)
    if hit and time.time() - hit[0] < CARDS_TTL:
        return hit[1]
    out = []
    for f in m.listing(brand=brand or None, r=root):
        try:
            card = m.load(f)
        except (OSError, ValueError):
            continue
        if not card.get("superseded_by") and _card_is(card, key, brand, getattr(m, "N", None)):
            out.append((m.where(f)["state"], card))
    _CARDS[k] = (time.time(), out)
    return out


def closed(n, B=None, brief=None, cards=None):
    """Why the cover stage is never offered or run for this production, or None: its card is approved or live, or a
    card of it already carries filed covers. A card tree that cannot be read is a reason too (covers are made only for
    an ad known not to be approved or covered). `cards(brand, key)` stands in for the card tree in tests."""
    if not part_on("skip_closed"):
        return None
    brief = brief if brief is not None else brief_of(folder(n, B))
    brand = brand_of(brief)
    keys = dict.fromkeys(k for k in (brief_key(brief, n), str(brief.get("brief_key") or brief.get("brief") or n or ""))
                         if k)
    key = next(iter(keys), "")
    rows = []
    try:
        for k in keys:
            rows += [r for r in (cards or cards_for)(brand, k) if r not in rows]
    except (Exception, SystemExit) as e:  # noqa: BLE001
        return "the ad's approval card could not be read (%s)" % (str(e) or type(e).__name__)
    for state_, card in rows:
        if state_ == "2-approved":
            return "its card is approved (%s)" % card.get("ad_name", key)
        if state_ == "3-live":
            return "its card is live on Meta (%s)" % card.get("ad_name", key)
    for state_, card in rows:
        if _covered(card):
            return "its card already carries filed covers (%s, %s)" % (card.get("ad_name", key), state_)
    return None


_VIDEO = (".mp4", ".mov", ".m4v", ".webm")


def _covered(card) -> bool:
    """Does the card carry its covers? Every video on it has one (`whole_hand_off`; a card that names no videos: any
    cover). A card with some versions' covers is not covered: the rest are still made."""
    thumbs = card.get("thumbs") or {}
    if not part_on("whole_hand_off"):
        return bool(thumbs or card.get("cover_records"))
    videos = [str(m) for m in card.get("media") or [] if str(m).lower().endswith(_VIDEO)]
    if not videos:
        return bool(thumbs)
    have = thumbs if isinstance(thumbs, dict) else {}
    return all(have.get(v) for v in videos)


# ---------------------------------------------------------------- the 3D set
_IMAGE_SUFFIX = (".png", ".jpg", ".jpeg", ".webp")
_SKIP_DIRS = {"covers", "node_modules", ".git"}


def _set_gate():
    """image production's set gate (kept prints of filed 3D sets), or None when this workspace does not carry it."""
    if "set_gate" not in _MODS:
        try:
            home = str(ST.part("image-production"))
            if home not in sys.path:
                sys.path.append(home)
            from image_production import set_gate as SG
            _MODS["set_gate"] = SG
        except (Exception, SystemExit):  # noqa: BLE001
            _MODS["set_gate"] = None
    return _MODS["set_gate"]


def _kept_print(brand, name):
    sg = _set_gate()
    if not sg:
        raise RuntimeError("image production's set gate is not in this workspace")
    return sg.kept_print(brand, sg.set_name(name))


def _sets_named(obj, out, where, depth=0):
    """Every 3D set a record names: a `set` field (a name, or {"name"}), or a picture inside a set's folder."""
    if depth > 12:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "set" and isinstance(v, str) and v.strip():
                out.append((Path(v.strip()).parent.name if v.strip().lower().endswith(_IMAGE_SUFFIX + (".json",))
                            else Path(v.strip()).name, where))
            elif k == "set" and isinstance(v, dict) and v.get("name"):
                out.append((str(v["name"]), where))
            else:
                _sets_named(v, out, where, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            _sets_named(v, out, where, depth + 1)
    elif isinstance(obj, str):
        m = re.search(r"/sets/([^/]+)/[^/]+$", obj)
        if m and obj.lower().endswith(_IMAGE_SUFFIX):
            out.append((m.group(1), where))


def _records_of(B, limit=4000):
    """The production's own records: its take records, start frames' run records and every other JSON beside them
    (not the cover stage's own folder)."""
    n = 0
    for dirpath, dirs, files in os.walk(B):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            p = Path(dirpath) / f
            try:
                if p.stat().st_size > 2_000_000:
                    continue
            except OSError:
                continue
            n += 1
            if n > limit:
                return
            yield p


def set_for(brief, B, brand, kept=None):
    """(set name, why) for the ad's filed 3D set, or (None, why not). The brief's own (`covers.set`) wins; else the set
    the production's own records were made from (its take records, start frames, the recipes of its generated shots)
    or a filed set whose record names this brief, most named first, the first with a kept print."""
    own = mine(brief)
    if own.get("set"):
        return str(own["set"]), "the ad's own (brief.json covers.set)"
    if not part_on("pick_set"):
        return None, "the ad names no set (brief.json covers.set) and the stage does not pick one (pick_set is off)"
    kept = kept or _kept_print
    B = Path(B)
    found = []
    gen = set()
    for p in _records_of(B):
        d = _load(p)
        if d is None:
            continue
        _sets_named(d, found, str(p.relative_to(B)))
        for src in ((d.get("sources") or {}).values() if isinstance(d, dict) and isinstance(d.get("sources"), dict) else []):
            if isinstance(src, dict) and src.get("generated"):
                gen.add(Path(str(src.get("file") or src.get("drive_location") or "")).stem)
    gen.discard("")
    if gen:
        for rf in sorted((ST.SOURCES / "generated").glob("recipes*.json")):
            for r in _load(rf, []) if isinstance(_load(rf, []), list) else []:
                if isinstance(r, dict) and r.get("name") in gen:
                    _sets_named({k: r.get(k) for k in ("set",)}, found, "recipe %s (%s)" % (r["name"], rf.name))
                    _sets_named((r.get("made") or {}).get("from_print") or "", found, "recipe %s (%s)" % (r["name"], rf.name))
    key = brief_key(brief)
    sets_home = ST.REPO / "runs" / "image-production" / brand / "sets"
    if key and "_" in key and sets_home.is_dir():
        for sj in sorted(sets_home.glob("*/set.json")):
            try:
                if key in sj.read_text():
                    found.append((sj.parent.name, "the set's own record names %s" % key))
            except OSError:
                continue
    if not found:
        return None, ("no record of this production names a 3D set (take records, start frames, generated shots' "
                      "recipes, or a filed set naming %s)" % (key or "its brief"))
    count = {}
    for name, _ in found:
        count[name] = count.get(name, 0) + 1
    order = sorted(dict.fromkeys(nm for nm, _ in found), key=lambda nm: -count[nm])
    tried = []
    for name in order:
        try:
            kp = kept(brand, name)
        except (Exception, SystemExit) as e:  # noqa: BLE001
            return None, "the filed 3D sets could not be read (%s)" % (str(e) or type(e).__name__)
        if kp:
            where = next(w for nm, w in found if nm == name)
            return name, "the 3D set this production was made from (%s; named %d time%s), its kept print filed" % (
                where, count[name], "" if count[name] == 1 else "s")
        tried.append(name)
    return None, "the sets its records name have no kept print filed: %s" % ", ".join(tried[:6])


# ---------------------------------------------------------------- the stage
def _sha(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    except OSError:
        return None


def _stamp(video):
    try:
        st = Path(video).stat()
        return {"mtime": st.st_mtime, "size": st.st_size}
    except OSError:
        return None


def _own_hash(own) -> str:
    return hashlib.sha256(json.dumps(own, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _ver_hash(own, vid, vids) -> str:
    """One version's own choices plus the ad-wide ones: a change to one version's cover (its second, its direction)
    remakes that version only, never the covers that already passed (2026-11-21)."""
    shared = {k: v for k, v in (own or {}).items() if k not in set(vids)}
    return _own_hash({"shared": shared, "mine": (own or {}).get(vid)})


def _still_ready(r, v) -> bool:
    """An earlier run's cover for this version still stands: ready, made from this same render, the same picture."""
    return bool(r and r.get("ready") and r.get("file") and r.get("video_stamp") is not None
                and r.get("video_stamp") == _stamp(v["video"]) and Path(str(r["file"])).is_file()
                and (not r.get("sha256") or _sha(r["file"]) == r["sha256"]))


def due(n, B=None, vers=None, cards=None) -> bool:
    """Does the production want its covers made? Some version has no ready cover made from its current video, and its
    card is not approved, live or already covered (closed)."""
    if not on():
        return False
    B = folder(n, B)
    vers = with_video(vers, B) if vers is not None else versions_of(n, B)
    if not vers:
        return False
    st = _load(B / "covers" / "stage.json", {}) or {}
    have = {r.get("version"): r for r in st.get("versions") or []}
    own_ = mine(brief_of(B))
    ids = [v["id"] for v in vers]
    same = (lambda vid: (st.get("own_hashes") or {}).get(vid) == _ver_hash(own_, vid, ids)) if st.get("own_hashes") \
        else (lambda vid: st.get("own_hash") == _own_hash(own_))
    if all(same(v["id"]) and _still_ready(have.get(v["id"]), v) for v in vers):
        return False
    return closed(n, B, cards=cards) is None


def _withdraw(n, B, rows):
    """The last hand-off stops counting the moment a run starts: a run that stops half way leaves no covers ready."""
    _save(folder(n, B) / "covers" / "to-file.json", {
        "production": n, "ready": False, "running": True, "media": [r["video"] for r in rows],
        "versions": [r["version"] for r in rows], "thumbs": ["" for _ in rows], "cover_records": ["" for _ in rows],
        "video_stamps": [None for _ in rows],
        "held": [{"version": r["version"], "why": "the cover stage is running"} for r in rows]})


def run(n, B=None, say=None, vers=None, make=None, find=None, read=None, grab_=None, face_check=None,
        refuse=None, kept=None, cards=None) -> dict:
    """The whole stage for one production. Returns stage.json. `say(step, state, said)` reports each step as it goes;
    `make`, `find`, `read`, `grab_`, `face_check`, `refuse`, `kept` and `cards` are the image tool, the cover index,
    the face reader, the frame grab, the cast face check, the filer's gate, the filed sets' kept prints and the card
    tree: the real ones unless a test passes its own. A version whose cover is still ready from an earlier run is kept
    as it is; only the others are made."""
    say = say or (lambda *a: None)
    make = make or run_tool
    B = folder(n, B)
    C = B / "covers"
    cf = conf()
    if not on():
        say("frames", "stopped", "The cover stage is switched off (cover-stage.json, VIDEO_STUDIO_COVERS_OFF).")
        return {"on": False}
    brief = brief_of(B)
    own = mine(brief)
    vers = with_video(vers, B) if vers is not None else versions_of(n, B)
    if not vers:
        say("frames", "stopped", "No rendered versions yet: render them first.")
        return {"on": True, "versions": []}
    shut = closed(n, B, brief, cards)
    if shut:
        say("frames", "stopped", "No covers made: %s." % shut)
        return {"on": True, "production": n, "closed": shut, "versions": []}
    oh = _own_hash(own)
    prev = _load(C / "stage.json", {}) or {}
    ids = [v["id"] for v in vers]
    vh = {vid: _ver_hash(own, vid, ids) for vid in ids}
    if prev.get("own_hashes"):
        before = {r.get("version"): r for r in prev.get("versions") or []
                  if (prev.get("own_hashes") or {}).get(r.get("version")) == vh.get(r.get("version"))}
    else:
        before = {r.get("version"): r for r in prev.get("versions") or []} if prev.get("own_hash") == oh else {}
    st = {"production": n, "on": True, "started": datetime.datetime.now().isoformat(timespec="seconds"),
          "brand": brand_of(brief), "avatar": avatar_of(brief), "product": product_of(brief), "own_hash": oh,
          "own_hashes": vh, "versions": []}
    rows = []
    for v in vers:
        old = before.get(v["id"])
        if _still_ready(old, v):
            rows.append(dict(old, label=v.get("label") or v["id"], video=v["video"], carried=True))
        else:
            rows.append({"version": v["id"], "label": v.get("label") or v["id"], "video": v["video"],
                         "video_stamp": _stamp(v["video"]), "opener": opener_scene(brief, v["id"]), "ready": False})
    st["versions"] = rows
    todo = [r for r in rows if not r.get("carried")]
    _withdraw(n, B, rows)
    if not todo:
        say("frames", "done", "every cover is still ready from its last run")
        return _hand_off(n, B, st, say)

    def held(r, why):
        r["held"], r["ready"] = why, False

    def put():
        _save(C / "stage.json", st)

    # 1 frames
    say("frames", "doing")
    near = same_at_bits()
    taken = [r.get("frame_hash") or (r.get("frame") or {}).get("hash") for r in rows if r.get("carried")]
    for r in todo:
        mine_v = _own(own, r["version"])
        cands = sweep(r["video"], C / _slug(r["version"]) / "frames", cf.get("opener_seconds", 6), grab_, read)
        if mine_v.get("at") is not None:
            f = C / _slug(r["version"]) / "frames" / "named.jpg"
            if (grab_ or grab)(r["video"], float(mine_v["at"]), f):
                cands = [{"t": float(mine_v["at"]), "file": str(f), "face": None, "hash": dhash(f), "rank": 0,
                          "named": True}] + cands
        r["sweep"] = cands
        pick, why = pick_moment(cands, taken, near)
        if pick is None:
            held(r, "no frame could be read from %s" % Path(r["video"]).name)
            continue
        if pick.get("named"):
            why = "the second the ad names (brief.json covers.%s.at): %.1f s" % (r["version"], pick["t"])
        ref = C / _slug(r["version"]) / ("%s-frame.jpg" % _slug(r["version"]))
        shutil.copyfile(pick["file"], ref)
        taken.append(pick.get("hash"))
        r["frame"] = {"t": pick["t"], "file": str(ref), "why": why, "rank": pick.get("rank"), "hash": pick.get("hash")}
    put()
    bad = [r for r in todo if r.get("held")]
    say("frames", "stopped" if bad else "done",
        "; ".join("%s: %s" % (r["version"], r["held"]) for r in bad) if bad else
        ", ".join("%s %.1f s" % (r["version"], r["frame"]["t"]) for r in todo))

    # 2 concept: every swipe is one of the avatar's own Explore covers with a rated move
    say("concept", "doing")
    avatar, idx = st["avatar"], index_rows()
    strict = part_on("concept_required")
    named = {r["version"]: _own(own, r["version"]).get("swipe") for r in todo}
    used = {(r.get("swipe") or {}).get("id") for r in rows if r.get("carried")}
    found = find_swipes(avatar, None, find) if avatar else \
        {"scope": "none", "note": "the ad names no avatar (brief.json audience.avatar or covers.avatar)", "covers": []}
    got = [c for c in found.get("covers") or [] if c.get("id")] if found.get("scope") == "avatar" else []
    theirs = {}
    for c in got:
        theirs[str(c["id"])] = c
        idx.setdefault(str(c["id"]), c)
    rank = {str(c["id"]): k for k, c in enumerate(got, 1)}

    def unfit(sid):
        """Why a swipe cannot give a cover its concept, or None."""
        sid = str(sid)
        if not strict:
            return None
        if sid not in theirs:
            if sid in idx:
                return "swipe %s is in the cover index but is not one of avatar %s's own Explore covers" % (
                    sid, avatar or "(none named)")
            return "swipe %s is not in the cover index, so it is not a real Explore cover" % sid
        if (theirs[sid].get("move") or "") in NO_MOVE:
            return ("swipe %s has no rated move, so it gives no concept (rate it: components/asset-index/swipes "
                    "covers.py moves --set %s=<move>)" % (sid, sid))
        return None

    pool = []
    for s in own.get("swipes") or []:           # the ad's own, in its order; one that does not fit holds its version
        if s in named.values() or s in used or s in [p["id"] for p in pool]:
            continue
        pool.append({"id": str(s), "why": "named by the ad (brief.json covers.swipes)", "unfit": unfit(s)})
    rated = [c for c in got if (c.get("move") or "") not in NO_MOVE]
    for c in rated + ([] if strict else [c for c in got if (c.get("move") or "") in NO_MOVE]):
        sid = str(c["id"])
        if sid not in named.values() and sid not in used and sid not in [p["id"] for p in pool]:
            pool.append({"id": sid, "why": _swipe_why(swipe_row(sid, idx), avatar, rank[sid])})
    st["concept_pool"] = [p["id"] for p in pool if not p.get("unfit")]
    st["index"] = {"scope": found.get("scope"), "note": found.get("note")}
    for r in todo:
        if r.get("held"):
            continue
        if named[r["version"]]:
            why = unfit(named[r["version"]])
            if why:
                held(r, why)
                continue
            s = swipe_row(named[r["version"]], idx)
            s["why"] = "named by the ad (brief.json covers.%s.swipe)" % r["version"]
        elif pool:
            p = pool.pop(0)
            if p.get("unfit"):
                held(r, p["unfit"])
                continue
            s = dict(swipe_row(p["id"], idx), why=p["why"])
        elif got and not rated and strict:
            held(r, "avatar %s's Explore covers in the cover index have no rated move yet, so none gives a concept: "
                    "rate them (components/asset-index/swipes covers.py moves --set <id>=<move>)" % avatar)
            continue
        else:
            held(r, "no Explore cover left to follow for avatar %s: %s. Pull that avatar's Explore feed into the "
                    "cover index (components/asset-index/swipes covers.py pull --avatar, then import)"
                 % (avatar or "(none named)", found.get("note") or "the index holds none of its covers"))
            continue
        r["swipe"] = s
    put()
    bad = [r for r in todo if r.get("held")]
    say("concept", "stopped" if bad else "done",
        bad[0]["held"][:240] if bad else ", ".join("%s → %s" % (r["version"], r["swipe"]["id"]) for r in todo))
    if bad:
        return _hand_off(n, B, st, say, early=True)

    # 3 direction
    say("direction", "doing")
    words = {r["version"]: opener_words(B, brief, r.get("opener") or opener_scene(brief, r["version"])) for r in rows}
    for r in todo:
        mine_v = _own(own, r["version"])
        if mine_v.get("headline"):
            r["headline"], r["headline_why"] = " ".join(str(mine_v["headline"]).split()), "the ad's own (brief.json covers)"
        else:
            r["headline"], r["headline_why"] = headline_for(
                r["version"], words[r["version"]], [w for k, w in words.items() if k != r["version"]],
                int(cf.get("headline_words", 8)))
        if not r["headline"]:
            held(r, "no headline: %s; name it in brief.json covers.%s.headline" % (r["headline_why"], r["version"]))
            continue
        r["direction"] = mine_v.get("direction") or direction_for(r["headline"], r["swipe"])
        r["direction_from"] = "the ad's own" if mine_v.get("direction") else "image production's standing cover direction"
    put()
    bad = [r for r in todo if r.get("held")]
    say("direction", "stopped" if bad else "done",
        bad[0]["held"][:240] if bad else "; ".join('%s "%s"' % (r["version"], r["headline"]) for r in todo))
    if bad:
        return _hand_off(n, B, st, say, early=True)

    # 4 make: nothing is sent until the set, the cast and the face reader are there
    say("make", "doing")
    masters = masters_of(brief)
    stop = None
    if all(_own(own, r["version"]).get("set") for r in rows):
        st["set"] = {"name": None, "why": "every version names its own (brief.json covers.<version>.set)"}
    else:
        name, why = set_for(brief, B, st["brand"], kept)
        st["set"] = {"name": name, "why": why}
        if not name:
            stop = ("no filed 3D set for this ad: %s. Every cover is made from one; the 3d-print skill builds and files "
                    "it (image-production picture_sets.py request)" % why)
    if not stop and part_on("hold_unread") and not masters:
        stop = NAME_THE_CAST
    if not stop and part_on("hold_unread") and read is None and face_reader() is None:
        stop = "no face reader on this machine, so the words-off-faces check cannot be read"
    if stop:
        for r in todo:
            held(r, stop)
        put()
        say("make", "stopped", stop[:240] + " Nothing was sent and nothing was spent.")
        return _hand_off(n, B, st, say, early=True)
    job = {"brand": st["brand"], "ad": str(brief.get("brief_key") or n), "out": str(C / "made"), "versions": [],
           "people": own.get("people", True)}
    per_version = any(_own(own, r["version"]).get("cast") for r in rows)
    if masters and not per_version:              # the image tool adds job and version references together
        job["references"] = masters
    if st["product"]:
        job["product"] = st["product"]
    if st["set"]["name"]:
        job["set"] = st["set"]["name"]
    for r in rows:
        mine_v = _own(own, r["version"])
        jv = {"version": r["version"], "headline": r["headline"], "frame": r["frame"]["file"], "video": r["video"],
              "t": r["frame"]["t"], "swipe": r["swipe"]["id"]}
        if r.get("direction"):
            jv["direction"] = r["direction"]
        for k in ("set", "product"):
            if k in mine_v:
                jv[k] = mine_v[k]
        if per_version:                            # each version's own people (covers.<version>.cast) as its references
            jv["references"] = masters_of(brief, r["version"])
        job["versions"].append(jv)
    only = [r["version"] for r in todo] if len(todo) < len(rows) else None
    since = _send(C, job)
    code, said = make(C / "job.json", only)
    st["make"] = {"exit": code, "said": (said or "")[-2000:], "only": only}
    if code not in (0, 1):
        why = " ".join((said or "").split())[:600]
        why = ("the image tool refused before spending anything: " + (why or "it gave no reason") if code == 2 else
               "the image tool stopped (exit %s), so nothing it left is used: %s" % (code, why or "it said nothing"))
        for r in todo:
            held(r, why)
        put()
        say("make", "stopped", why[:240])
        return _hand_off(n, B, st, say, early=True)
    _take_made(st, C, todo, since)
    put()
    made = [r for r in todo if r.get("file")]
    say("make", "done" if len(made) == len(todo) else "stopped",
        "%d of %d made" % (len(made), len(todo)) + ("" if len(made) == len(todo) else ": " + "; ".join(
            "%s %s" % (r["version"], r.get("tool_why") or "not made") for r in todo if not r.get("file"))[:200]))

    # 5 check, with a remake for a face or sameness miss
    say("check", "doing")
    remakes = int(cf.get("remakes", 1))
    for attempt in range(remakes + 1):
        _check(st, C, lambda v: masters_of(brief, v), read, face_check, refuse)
        put()
        again = [r for r in todo if r.get("file") and r.get("redo") and not r.get("held")]
        if not again or attempt == remakes:
            break
        snap = {r["version"]: json.loads(json.dumps(r, default=str)) for r in again}
        for r in again:
            nxt = _next_frame(r, [x.get("frame_hash") for x in rows if x is not r], near, C)
            if nxt is not None:
                r["frame"] = nxt
            while pool and pool[0].get("unfit"):
                pool.pop(0)
            if pool:
                p = pool.pop(0)
                r["swipe"] = dict(swipe_row(p["id"], idx), why=p["why"] + " (the first one was remade)")
                r["direction"] = _own(own, r["version"]).get("direction") or direction_for(r["headline"], r["swipe"])
            _job_row(job, r)
        since = _send(C, job)
        code, said = make(C / "job.json", [r["version"] for r in again])
        st["remake"] = {"exit": code, "said": (said or "")[-2000:], "versions": [r["version"] for r in again]}
        if code in (0, 1):
            _take_made(st, C, again, since, keep=True)
        for r in again:
            if code in (0, 1) and r.get("made_since") == since:
                r["remade"] = r.get("remade", 0) + 1
                continue
            why = (" ".join((said or "").split())[:300] if code not in (0, 1) else r.get("tool_why")) or "no reason given"
            v = r["version"]
            r.clear()
            r.update(snap[v])            # the board names the frame and swipe the cover it has was made from
            r["remake_failed"] = "the remake was not made (%s%s); the cover is still the first one" % (
                "exit %s: " % code if code not in (0, 1) else "", why)
            _job_row(job, r)
        if any(r.get("remake_failed") for r in again):
            _save(C / "job.json", job)   # job.json says what each cover on hand was made from
        put()
    for r in rows:
        if r.get("file") and not r.get("held"):
            fails = [c for c in r.get("checks") or []
                     if c["ok"] is False or (c["ok"] is None and part_on("hold_unread"))]
            r["ready"] = not fails
            if fails:
                held(r, "; ".join("%s: %s" % (c["name"], c["short"]) if c["ok"] is False else
                                  "%s not read: %s" % (c["name"], c["short"]) for c in fails)[:400])
        elif not r.get("held"):
            held(r, r.get("tool_why") or "the image tool made no cover for it")
        if r.get("remake_failed") and r.get("held") and r["remake_failed"] not in r["held"]:
            r["held"] = (r["held"] + "; made again, but " + r["remake_failed"])[:500]
    put()
    bad = [r for r in rows if not r["ready"]]
    say("check", "stopped" if bad else "done",
        "; ".join("%s: %s" % (r["version"], r["held"]) for r in bad)[:240] if bad else "%d covers pass" % len(rows))
    return _hand_off(n, B, st, say)


def _send(C, job) -> float:
    """job.json written for the image tool; returns its time: a record older than this is not from this run."""
    _save(C / "job.json", job)
    return (C / "job.json").stat().st_mtime


def _job_row(job, r):
    """The job's row for this version, set to what this version's cover is made from now."""
    for jv in job["versions"]:
        if jv["version"] == r["version"]:
            jv.update(frame=r["frame"]["file"], t=r["frame"]["t"], swipe=r["swipe"]["id"])
            if r.get("direction"):
                jv["direction"] = r["direction"]
            else:
                jv.pop("direction", None)


def _next_frame(r, others, near, C):
    """The next-strongest moment of this version not like a sibling's, saved as its reference frame."""
    used = r.get("used_frames") or [r["frame"]["t"]]
    for c in r.get("sweep") or []:
        if c["t"] in used:
            continue
        if c.get("hash") and any(h and apart(c["hash"], h) <= near for h in others):
            continue
        ref = C / _slug(r["version"]) / ("%s-frame.jpg" % _slug(r["version"]))
        shutil.copyfile(c["file"], ref)
        r["used_frames"] = used + [c["t"]]
        return {"t": c["t"], "file": str(ref), "rank": c.get("rank"), "hash": c.get("hash"),
                "why": "the next-strongest moment, %.1f s (the first cover was made again)" % c["t"]}
    return None


def _take_made(st, C, rows, since, keep=False):
    """Read the image tool's record of the ad (made/covers.json) onto these versions: only a record written by this run
    (at or after `since`), for a picture made by this run, from the frame and swipe this run sent. `keep`: a version
    whose record is not from this run keeps what it had (a remake that did not happen)."""
    f = C / "made" / "covers.json"
    try:
        fresh = f.stat().st_mtime >= since
    except OSError:
        fresh = False
    got = (_load(f, {}) or {}) if fresh else {}
    by = {_slug(c.get("version")): c for c in got.get("covers") or []}
    fail = {_slug(f_.get("version")): f_.get("why") for f_ in got.get("failed") or []}
    for r in rows:
        if r.get("held"):
            continue
        c = by.get(_slug(r["version"]))
        why = None
        if not fresh:
            why = ("the image tool wrote no record of this run (made/covers.json is %s)"
                   % ("from an earlier run" if f.exists() else "missing"))
        elif not c or not c.get("file") or not Path(str(c["file"])).is_file():
            why = fail.get(_slug(r["version"])) or "no cover in the tool's record of this run"
        else:
            src = c.get("source_frame") if isinstance(c.get("source_frame"), dict) else {}
            try:
                old_pic = Path(str(c["file"])).stat().st_mtime < since
            except OSError:
                old_pic = True
            if old_pic or (c.get("swipe") not in (None, "", r["swipe"]["id"])) or (
                    src.get("t") is not None and abs(float(src["t"]) - float(r["frame"]["t"])) > 1e-6):
                why = "the tool's record for it is not of the cover this run asked for"
        if why:
            if not keep:
                for k in ("file", "sha256", "record", "box_px", "tool_ok", "tool_problems", "checks"):
                    r.pop(k, None)
            r["tool_why"] = why
            continue
        r["file"], r["tool_ok"] = str(c["file"]), bool(c.get("ok"))
        r["tool_problems"] = list(c.get("problems") or []) + list(got.get("problems") or [])
        r["box_px"] = (c.get("words") or {}).get("box_px")
        r["sha256"] = c.get("sha256") or _sha(c["file"])
        r["made_since"] = since
        r.pop("tool_why", None)
        side = Path(c["file"]).with_suffix(".cover.json")
        r["record"] = fill_record(side, {"version": r["version"], "swipe": r["swipe"]["id"], "headline": r["headline"],
                                         "frame": {"video": r["video"], "t": r["frame"]["t"], "file": r["frame"]["file"]}})


def _check(st, C, masters, read, face_check, refuse):
    rows = [r for r in st["versions"] if r.get("file") and not r.get("held")]
    gate = made_by_tool([r["file"] for r in rows], refuse)
    near = same_at_bits()
    for r in rows:
        r["frame_hash"] = dhash(r["frame"]["file"])
        r["hash"] = dhash(r["file"])
    for i, r in enumerate(rows):
        checks = []
        checks.append({"name": "made", "ok": r.get("tool_ok") and not r.get("tool_problems"),
                       "short": "the image tool passed it" if r.get("tool_ok") and not r.get("tool_problems")
                       else "; ".join(r.get("tool_problems") or ["the image tool did not pass it"])[:200]})
        ok, short = _fits(r["file"])
        checks.append({"name": "size", "ok": ok, "short": short})
        ok, short = words_off_faces(r["file"], r.get("box_px"), read)
        checks.append({"name": "words off faces", "ok": ok, "short": short})
        kept = (_load(Path(r["file"]).with_suffix(".cover.json"), {}) or {}).get("kept_faces")
        if kept and kept.get("pass") and kept.get("verified") and kept.get("faces"):
            ok, short = True, "%d face(s) kept from the video's own frame, pixel for pixel" % len(kept["faces"])
        else:                                       # 2026-11-13: kept faces cannot drift; a redrawn face is checked
            ok, short = faces_against_cast(r["file"], masters(r["version"]) if callable(masters) else masters, face_check)
        checks.append({"name": "faces", "ok": ok, "short": short})
        ok, short = gate.get(r["file"], (None, "not read"))
        checks.append({"name": "made by the tool", "ok": ok, "short": short})
        twin = next((x["version"] for x in rows[:i] if x.get("hash") and r.get("hash")
                     and apart(x["hash"], r["hash"]) <= near), None)
        checks.append({"name": "differs", "ok": twin is None if r.get("hash") else None,
                       "short": "the same picture as %s" % twin if twin else "unlike its siblings"})
        r["checks"] = checks
        r["redo"] = any(c["ok"] is False for c in checks if c["name"] in ("faces", "differs"))
    card = card_checks(rows, C)
    st["card_checks"] = card
    for r in rows:
        for k, c in card.items():
            if c.get("ok") is not True:
                r["checks"].append({"name": "card: " + k.replace("cover_", ""), "ok": c.get("ok"),
                                    "short": str(c.get("why") or "")[:200]})


def _hand_off(n, B, st, say, early=False):
    """to-file.json: every version's video in card order, its cover and its record, '' where it has none."""
    C = folder(n, B) / "covers"
    rows = st.get("versions") or []
    st["ready"] = bool(rows) and all(r.get("ready") for r in rows)
    st["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
    give = (lambda r: st["ready"]) if part_on("whole_hand_off") else (lambda r: r.get("ready"))
    hand = {"production": n, "ready": st["ready"],
            "media": [r["video"] for r in rows],
            "versions": [r["version"] for r in rows],
            "thumbs": [r["file"] if give(r) else "" for r in rows],
            "cover_records": [r.get("record", "") if give(r) else "" for r in rows],
            "video_stamps": [r.get("video_stamp") for r in rows],
            "withheld": [r["version"] for r in rows if r.get("ready") and not give(r)],
            "held": [{"version": r["version"], "why": r.get("held")} for r in rows if not r.get("ready")]}
    _save(C / "to-file.json", hand)
    _save(C / "stage.json", st)
    if not early:
        say("file", "done" if st["ready"] else "stopped",
            "%d covers ready for the card" % len(rows) if st["ready"] else
            "%d of %d ready; held: %s" % (sum(1 for r in rows if r.get("ready")), len(rows),
                                          ", ".join(h["version"] for h in hand["held"])))
    return st


# ---------------------------------------------------------------- the filer's side
def filer_kwargs(n, media=None, B=None) -> dict:
    """{"thumbs": [...], "cover_records": [...]} for to_check.to_check, one per video in `media` (default: the
    production's versions in card order). A video with no ready cover gets '' (the filer skips it and the card's
    cover check holds the card): so does every video while a run is under way, and a video rendered again after its
    cover was made."""
    hand = _load(folder(n, B) / "covers" / "to-file.json", {}) or {}
    stamps = hand.get("video_stamps")
    if stamps is None:                       # a hand-off written before stamps were kept: the stage's own record
        rec = {r.get("version"): r.get("video_stamp")
               for r in (_load(folder(n, B) / "covers" / "stage.json", {}) or {}).get("versions") or []}
        stamps = [rec.get(v) for v in hand.get("versions") or []]
    by = {}
    for v, t, c, s in zip(hand.get("media") or [], hand.get("thumbs") or [], hand.get("cover_records") or [],
                          list(stamps or []) + [None] * len(hand.get("media") or [])):
        if hand.get("running") or not t or s is None or _stamp(v) != s or not Path(str(t)).is_file():
            t, c = "", ""
        by[Path(v).name] = (t, c)
        by.setdefault(Path(v).stem, (t, c))
    media = media if media is not None else hand.get("media") or []
    out = {"thumbs": [], "cover_records": []}
    for m in media:
        t, c = by.get(Path(str(m)).name) or by.get(Path(str(m)).stem) or ("", "")
        out["thumbs"].append(t)
        out["cover_records"].append(c)
    if part_on("whole_hand_off") and (not hand.get("ready") or not all(out["thumbs"])):
        out = {"thumbs": ["" for _ in media], "cover_records": ["" for _ in media]}   # a set is filed whole or not at all
    return out


# ---------------------------------------------------------------- the board
def _url(n, B, p):
    if not p:
        return None
    try:
        return "/files/%s/%s" % (n, Path(p).resolve().relative_to(Path(B).resolve()))
    except ValueError:
        return None


def state(n, B=None, cards=None) -> dict:
    """What the board shows: per version the cover, the frame it started from and why, the swipe it follows and why,
    its headline, direction and every check."""
    B = folder(n, B)
    st = _load(B / "covers" / "stage.json", None)
    if not on():
        return {"on": False, "production": n, "versions": []}
    shut = closed(n, B, cards=cards)
    if not st:
        return {"on": True, "production": n, "made": False, "closed": shut,
                "due": bool(versions_of(n, B)) and not shut, "versions": []}
    out = {"on": True, "production": n, "made": True, "ready": st.get("ready"), "avatar": st.get("avatar"),
           "finished": st.get("finished"), "index": st.get("index"), "set": st.get("set"), "closed": shut,
           "versions": []}
    for r in st.get("versions") or []:
        fr, sw = r.get("frame") or {}, r.get("swipe") or {}
        out["versions"].append({
            "version": r["version"], "label": r.get("label"), "ready": r.get("ready"), "held": r.get("held"),
            "video": _url(n, B, r.get("video")), "headline": r.get("headline"), "headline_why": r.get("headline_why"),
            "cover": _url(n, B, r.get("file")),
            "frame": {"t": fr.get("t"), "why": fr.get("why"), "url": _url(n, B, fr.get("file"))},
            "sweep": [{"t": c["t"], "face": c.get("face"), "url": _url(n, B, c.get("file")),
                       "picked": c["t"] == fr.get("t")} for c in sorted(r.get("sweep") or [], key=lambda c: c["t"])],
            "swipe": {"id": sw.get("id"), "why": sw.get("why"), "move": sw.get("move"), "likes": sw.get("likes"),
                      "views": sw.get("views"), "link": sw.get("url"),
                      "picture": "/coverswipe/%s" % sw["id"] if sw.get("picture") else None},
            "direction": r.get("direction"), "direction_from": r.get("direction_from"),
            "checks": r.get("checks") or [], "remade": r.get("remade", 0), "kept": bool(r.get("carried"))})
    return out


def swipe_picture(sid):
    """The swipe's picture in the cover index, or None."""
    r = index_rows().get(str(sid)) or {}
    if not r.get("frame_file"):
        return None
    p = (index_dir() / r["frame_file"]).resolve()
    return str(p) if index_dir().resolve() in p.parents and p.is_file() else None


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", choices=["run", "state", "file-args"])
    ap.add_argument("production")
    ap.add_argument("--media", nargs="*")
    a = ap.parse_args(argv)
    if a.what == "run":
        st = run(a.production, say=lambda s, state_, said="": print("  %s %-9s %s" % (
            {"done": "✓", "stopped": "✗", "doing": "…"}.get(state_, " "), s, said)))
        return 0 if st.get("ready") else 1
    if a.what == "state":
        print(json.dumps(state(a.production), indent=1, ensure_ascii=False))
        return 0
    k = filer_kwargs(a.production, a.media)
    print(" ".join(["--thumbs"] + [t or '""' for t in k["thumbs"]] + ["--cover-records"] + [c or '""' for c in k["cover_records"]]))
    return 0 if all(k["thumbs"]) else 1


if __name__ == "__main__":
    sys.exit(main())
