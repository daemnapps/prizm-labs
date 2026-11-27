#!/usr/bin/env python3
"""cover_rule — the cover rule as card checks: a video card is not ready until every one of its videos has its own
cover, each cover's record names the swipe it follows and a frame of that same video, and no two covers of the card
are the same picture.

    python3 cover_rule.py <card folder>          the four checks for one card, a line each
    python3 cover_rule.py --record <cover file>  the record the filer would read for one cover

Four checks, on a video card that is waiting (a card already approved or live is left as it is):
  cover_each     every video on the card has a cover in `thumbs`
  cover_swipe    every cover's record names the swipe it follows
  cover_frame    every cover's record names a source frame, and that frame is from the cover's own video
  cover_differs  no two covers of the card are the same picture (64-bit picture hash, the pre-flight measure)

THE RECORD of a cover is `cover_records[<cover file>]` on the card, written by the filer (to_check.py) from the first
of these it finds for the cover it is filing:
  1. `cover_records=[...]` passed to to_check (one per thumb, in order: a dict or a path to a JSON file)
  2. `<cover file minus its suffix>.cover.json` beside the cover
  3. the image-production `run.json` beside the cover or one folder up: its `cover` block, or the row of `pictures`
     with this file's name or sha256 that carries one
  4. the cover's line in image production's ledger (by sha256), when it carries the fields
The shape, wherever it is read from (`normalize` takes these names and nothing else):
  {"swipe": "<swipe id in the cover index>",
   "frame": {"video": "<the version's video: its full path (a bare file name is no proof)>", "video_sha256": "<that video's sha256>",
             "t": <seconds>, "file": "<the frame picture>"},
   "version": "<version id>", "headline": "<the cover's words>"}
WHOSE FRAME (`frame_check` "own-video"): a recorded `video_sha256` must be the filed video's (or its `.clean` twin's,
the same cut without words); else a `video` with a folder in it must be the filed video or its twin on this machine.
A bare file name (no folder, no `video_sha256`) is no proof: another ad's video can carry the same name. A record
that names no video is not proof of any video.
THE SWIPE (`swipe_check` "index"): the id must be a row of the cover index (`runs/asset-index/swipes/covers/covers.json`,
or `swipe_index` / META_COVER_INDEX); a placeholder ("x", "?", "swipe", "none.") is no swipe.

SWITCH: cover-rule.json beside this file. `on` false turns all four off; `checks.<name>` false turns one off;
`lanes.<lane>` picks the lanes (video on, creator off); `since` leaves cards filed before it alone. One machine:
META_COVER_RULE_OFF=all or a comma list of check names. Row COVER-RULE in team/rollbacks.md. `frame_check` "name" and
`swipe_check` "named" put those two checks back to reading names only (row COVER-RULE-PROOF). `bare_name` true reads
a bare file name as proof again (row COVER-RULE-BARE-NAME).
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CONF = HERE / "cover-rule.json"
INDEX = Path("runs") / "asset-index" / "swipes" / "covers"     # the cover index (components/asset-index/swipes/covers.py)
PREFLIGHT = HERE / "preflight.json"            # where pre-flight is installed its `covers.same_at_bits` is the one number
VIDEO = {".mp4", ".mov", ".m4v"}
PICTURE = {".png", ".jpg", ".jpeg", ".webp"}
KEYS = ("cover_each", "cover_swipe", "cover_frame", "cover_differs")
LABELS = {
    "cover_each": "A cover for every video",
    "cover_swipe": "Each cover names the swipe it follows",
    "cover_frame": "Each cover starts from a frame of its own video",
    "cover_differs": "Covers differ from each other",
}
HELD = ("1-check", "sent-back")                # a card in any other state is left exactly as it is
NO_SWIPE = {"", "none", "n/a", "na", "-", "tbd", "todo", "unknown", "null"}
SWIPE_ID = re.compile(r"[a-z]{2,3}-[A-Za-z0-9_-]{4,}")      # the index's own ids: <platform>-<post code>
SAME_AT_BITS = 8
ROUTE = "components/image-production/make.py --purpose cover"


# ---- the switch ----------------------------------------------------------------------------------------
def conf():
    try:
        return json.loads(CONF.read_text())
    except (OSError, ValueError):
        return {}


def on(check, lane="video"):
    """Is this check on for this lane? No switch file: the rule holds, on the video lane."""
    off = {x.strip() for x in os.environ.get("META_COVER_RULE_OFF", "").split(",") if x.strip()}
    if off & {"all", "1", check}:
        return False
    c = conf()
    if c.get("on") is False or (c.get("checks") or {}).get(check) is False:
        return False
    return bool((c.get("lanes") or {"video": True}).get(lane, False))


def mode(key, default):
    """A check's strictness from the switch file: `frame_check` ("own-video" | "name"), `swipe_check` ("index" |
    "named")."""
    return str(conf().get(key) or default)


def applies(card, lane, state):
    """A waiting card of a lane the rule is on for, filed on or after `since`."""
    since = str(conf().get("since") or "")
    return (state in HELD and any(on(k, lane) for k in KEYS)
            and (not since or str(card.get("made_at") or "") >= since))


def same_at_bits():
    try:
        return int(json.loads(PREFLIGHT.read_text())["covers"]["same_at_bits"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        return int(conf().get("same_at_bits", SAME_AT_BITS))
    except (ValueError, TypeError):
        return SAME_AT_BITS


# ---- the picture measure (the pre-flight hash) ---------------------------------------------------------
def dhash(picture):
    """64-bit difference hash of a picture, as hex; None when it can't be opened."""
    try:
        from PIL import Image
        with Image.open(picture) as im:
            px = list(im.convert("L").resize((9, 8)).tobytes())
    except Exception:  # noqa: BLE001
        return None
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = bits << 1 | (px[y * 9 + x] > px[y * 9 + x + 1])
    return f"{bits:016x}"


def apart(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


# ---- a cover's record ----------------------------------------------------------------------------------
def _first(d, *names):
    for n in names:
        v = d.get(n)
        if v not in (None, "", {}, []):
            return v
    return None


def normalize(raw):
    """Any of the accepted spellings -> {"swipe", "frame": {"video", "t", "file"}, "version", "headline"}, keeping
    only what was said. None when `raw` says nothing about a cover."""
    if not isinstance(raw, dict):
        return None
    if raw.get("manual") is True:                           # a hand-made cover: nothing to trace, nothing to hold
        return {"manual": True, **{k: raw[k] for k in ("version", "by") if raw.get(k)}}
    if isinstance(raw.get("cover"), dict):
        raw = {**{k: v for k, v in raw.items() if k != "cover"}, **raw["cover"]}
    swipe = _first(raw, "swipe", "swipe_id")
    if isinstance(swipe, dict):
        swipe = _first(swipe, "id", "swipe", "swipe_id")
    frame = _first(raw, "frame", "source_frame")
    fr = {}
    if isinstance(frame, dict):
        fr = {"video": _first(frame, "video", "from", "source"), "t": _first(frame, "t", "at", "seconds"),
              "file": _first(frame, "file", "path"), "video_sha256": _first(frame, "video_sha256")}
    elif isinstance(frame, str) and frame.strip():
        fr = {"file": frame.strip()}
    if fr and not fr.get("video"):
        fr["video"] = _first(raw, "video", "source_video")
    if fr and not fr.get("video_sha256"):
        fr["video_sha256"] = _first(raw, "video_sha256")
    if fr and fr.get("t") is None and _first(raw, "t", "at") is not None:
        fr["t"] = _first(raw, "t", "at")
    out = {"swipe": str(swipe).strip() if swipe is not None else None,
           "frame": {k: v for k, v in fr.items() if v is not None} or None,
           "version": _first(raw, "version", "version_id"), "headline": _first(raw, "headline", "words")}
    out = {k: v for k, v in out.items() if v is not None}
    return out if out.get("swipe") or out.get("frame") else None


def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _from_run(cover):
    """The cover block of an image-production run record beside the cover (or one folder up)."""
    cover, digest = Path(cover), None
    for d in (cover.parent, cover.parent.parent):
        rec = _json(d / "run.json")
        if not isinstance(rec, dict):
            continue
        for row in rec.get("pictures") or []:
            if not isinstance(row, dict):
                continue
            named = Path(str(row.get("file") or row.get("name") or "")).name == cover.name
            if not named and row.get("sha256"):
                digest = digest or _sha256(cover)
                named = row["sha256"] == digest
            got = named and normalize(row)
            if got:
                return got, str(d / "run.json")
        got = normalize(rec) or normalize(rec.get("request") if isinstance(rec.get("request"), dict) else None)
        if got:
            return got, str(d / "run.json")
    return None, None


def _from_ledger(cover):
    """The cover's own line in image production's ledger, when the tool wrote the fields there."""
    try:
        import made_by_tool as MBT
        led = Path(MBT.pv().ledger_path())
        digest = _sha256(cover)
        lines = led.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:  # noqa: BLE001 — no ledger on this checkout is no record here
        return None, None
    for line in reversed(lines):
        if digest not in line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        got = row.get("sha256") == digest and normalize(row)
        if got:
            return got, str(led)
    return None, None


def read_record(cover, given=None):
    """(record, where it was read) for one cover file about to be filed; ({}, None) when nothing names one."""
    cover = Path(cover)
    if given is not None:
        raw = _json(given) if isinstance(given, (str, Path)) else given
        got = normalize(raw)
        if got:
            return got, str(given) if isinstance(given, (str, Path)) else "passed to the filer"
    side = cover.with_suffix(".cover.json")
    got = normalize(_json(side))
    if got:
        return got, str(side)
    if cover.is_file():
        for reader in (_from_run, _from_ledger):
            got, where = reader(cover)
            if got:
                return got, where
    return {}, None


def _twin(video):
    """The same cut without words, when the render kept one beside it: <name>.clean<suffix>."""
    video = Path(video)
    return video.with_name(f"{video.stem}.clean{video.suffix}")


def _own_video(frame, version, video, base=None):
    """Is the frame this record names a frame of `video` (the source file the cover is being filed with)? `base` is the
    folder a relative path in the record is read from (the cover's own folder)."""
    video = Path(video)
    named = (frame or {}).get("video")
    if mode("frame_check", "own-video") == "name":           # rolled back: the name, the stem or the path, as before
        if named:
            n = Path(str(named))
            if n.name == video.name or n.stem == video.stem:
                return True
            try:
                return n.resolve() == video.resolve()
            except OSError:
                return False
        return bool(version) and str(version) == video.stem and bool(frame)
    mine = [f for f in (video, _twin(video)) if f.is_file()]
    digest = str((frame or {}).get("video_sha256") or "").strip().lower()
    if digest:
        return any(_sha256(f) == digest for f in mine)
    if not named:
        return False                                          # a version id or a frame alone proves no video
    n = Path(str(named)).expanduser()
    if len(n.parts) > 1:                                      # a path: it must be this video on this machine
        tries = [n] if n.is_absolute() else [Path(base) / n] if base else [n]
        for t in tries:
            try:
                if t.is_file() and any(t.resolve() == f.resolve() for f in mine):
                    return True
            except OSError:
                continue
        return False
    if conf().get("bare_name") is True:                       # rolled back: a bare file name is read as before
        return n.name in (video.name, _twin(video).name)
    return False                                              # a bare file name proves no video


def _bare(frame):
    """Does the record name its video by a bare file name only (no folder, no video_sha256)?"""
    named = str((frame or {}).get("video") or "").strip()
    return bool(named) and len(Path(named).parts) == 1 and not (frame or {}).get("video_sha256")


def for_filing(pairs, given=None):
    """{cover name on the card: record} for the covers being filed. `pairs` is [(video source, video name on the
    card, cover source, cover name on the card)]; `given` an optional list of records, one per pair. The frame's video
    is rewritten to the card's own name for it when it is the cover's own video, and kept as said when it is not."""
    out = {}
    for i, (vsrc, vname, csrc, cname) in enumerate(pairs):
        g = given[i] if given and i < len(given) else None
        rec, where = read_record(csrc, g)
        if not rec:
            continue
        fr = dict(rec.get("frame") or {})
        if fr:
            said = fr.get("video")
            if _own_video(fr, rec.get("version"), vsrc, Path(csrc).parent):
                fr["video"] = vname
                if said and Path(str(said)).name != vname:
                    fr["source"] = Path(str(said)).name
            else:
                if _bare(fr) and mode("frame_check", "own-video") != "name":
                    fr["bare"] = True                         # refused because the name alone proves nothing
                fr["video"] = Path(str(said)).name if said else None
                fr["own"] = False                             # read and refused at filing: not this video's frame
            if fr.get("file"):
                fr["file"] = Path(str(fr["file"])).name
            rec["frame"] = {k: v for k, v in fr.items() if v is not None}
        rec["record"] = where
        out[cname] = rec
    return out


# ---- the swipe ------------------------------------------------------------------------------------------
def index_file():
    """The cover index's covers.json: META_COVER_INDEX, else the switch's `swipe_index` (from the repo root), else
    runs/asset-index/swipes/covers. A folder or the file itself."""
    where = os.environ.get("META_COVER_INDEX") or conf().get("swipe_index") or str(INDEX)
    f = Path(where).expanduser()
    f = f if f.is_absolute() else REPO / f
    return f / "covers.json" if f.suffix.lower() != ".json" else f


def index_ids():
    """Every swipe id in the cover index; None when the index is not on this machine."""
    rows = _json(index_file())
    if isinstance(rows, dict):
        rows = rows.get("covers") or rows.get("rows")
    if not isinstance(rows, list):
        return None
    return {str(r.get("id")).strip() for r in rows if isinstance(r, dict) and r.get("id")}


def _rel(f):
    try:
        return str(Path(f).relative_to(REPO))
    except ValueError:
        return str(f)


_UNREAD = object()


def swipe_problem(swipe, ids=_UNREAD):
    """Why this swipe is not one, or None when it is. `ids` is the index's ids when the caller already read them."""
    if swipe.lower() in NO_SWIPE:
        return "its cover's record names no swipe"
    if mode("swipe_check", "index") == "named":               # rolled back: any name but the empty ones passes
        return None
    ids = index_ids() if ids is _UNREAD else ids
    if ids is not None and swipe in ids:                      # a row of the index: the only proof
        return None
    if not SWIPE_ID.fullmatch(swipe):
        return f"its cover's record names \"{swipe}\", a placeholder, not a swipe id from the cover index"
    if ids is None:
        return f"the cover index is not on this machine ({_rel(index_file())}), so swipe {swipe} cannot be checked"
    return f"swipe {swipe} is not in the cover index ({_rel(index_file())})"


# ---- the four checks -----------------------------------------------------------------------------------
def _short(name):
    import re
    m = re.search(r"(asset-\d+)", name)
    return m.group(1) if m else name


def checks(folder, card, lane=None, state=None):
    """{check: {"ok", "why"}} for a waiting video card; {} when the rule does not apply to it."""
    folder = Path(folder)
    lane = lane or card.get("lane") or folder.parent.name
    state = state or folder.parents[1].name
    if not applies(card, lane, state):
        return {}
    out = {}

    def put(k, bad, good, fix=""):
        if on(k, lane):
            why = "; ".join(bad[:4]) + (f" (+{len(bad) - 4} more)" if len(bad) > 4 else "") + (f". {fix}" if fix else "")
            out[k] = {"ok": not bad, "why": why if bad else good}
    videos = [f for f in card.get("media") or [] if Path(f).suffix.lower() in VIDEO]
    if not videos:
        return {}
    recs = card.get("cover_records") or {}
    thumbs = {v: t for v, t in (card.get("thumbs") or {}).items() if v in videos}
    hand = {v: t for v, t in thumbs.items() if (recs.get(t) or {}).get("manual")}
    thumbs = {v: t for v, t in thumbs.items() if v not in hand}   # hand-made covers skip swipe/frame; still counted below

    # every video has a cover
    bare = [_short(v) for v in videos if v not in thumbs and v not in hand]
    put("cover_each", [f"{len(bare)} of {len(videos)} video(s) with no cover: {', '.join(bare[:6])}"] if bare else [],
        f"{len(thumbs) + len(hand)} video(s), a cover each" + (f" ({len(hand)} by hand)" if hand else ""),
        f"Each version gets its own cover, made with {ROUTE} and filed with its video before Approve")
    if not thumbs:
        for k in ("cover_swipe", "cover_frame", "cover_differs"):
            put(k, [], "no cover on the card yet")
        return out

    # every cover's record names the swipe it follows, a real row of the cover index
    bad, ids = [], index_ids()
    for v, t in thumbs.items():
        why = swipe_problem(str((recs.get(t) or {}).get("swipe") or "").strip(), ids)
        if why:
            bad.append(f"{_short(v)}: {why}")
    put("cover_swipe", bad, f"{len(thumbs)} cover(s), each names its swipe: " + ", ".join(
        dict.fromkeys(str((recs.get(t) or {}).get("swipe")) for t in thumbs.values())),
        "Name the swipe each cover follows (the cover job's swipe id) and file the card again")

    # every cover's record names a source frame from its own video
    bad = []
    for v, t in thumbs.items():
        fr = (recs.get(t) or {}).get("frame") or {}
        if not fr or (fr.get("t") is None and not fr.get("file")):
            bad.append(f"{_short(v)}: its cover's record names no source frame")
        elif fr.get("bare") and fr.get("own") is False:
            bad.append(f"{_short(v)}: its cover's record names its video by file name only ({fr.get('video')}), "
                       "with no folder and no video_sha256, which another ad's video can match")
        elif fr.get("video") != v or fr.get("own") is False:
            bad.append(f"{_short(v)}: its cover's frame is from {fr.get('video') or 'no named video'}, not from its own video")
    put("cover_frame", bad, f"{len(thumbs)} cover(s), each from a frame of its own video",
        "Each cover starts from a frame of its own version (the cover job's frame): make it from that frame and file the card again")

    # no two covers of the card are the same picture
    near, hashes, blind = same_at_bits(), [], []
    for v, t in thumbs.items():
        h = dhash(folder / t)
        (hashes.append((v, h)) if h else blind.append(_short(v)))
    same = [f"{_short(a)} ≈ {_short(b)} ({apart(ha, hb)} of 64 bits apart)"
            for i, (a, ha) in enumerate(hashes) for b, hb in hashes[i + 1:] if apart(ha, hb) <= near]
    put("cover_differs", [f"the same picture: {x}" for x in same],
        f"{len(hashes)} cover(s), no two alike" + (f"; not read: {', '.join(blind)}" if blind else ""),
        f"Covers of one card are different pictures (two are the same at {near} bits or fewer)")
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", nargs="?")
    ap.add_argument("--record", help="print the record the filer would read for this cover file")
    a = ap.parse_args(argv)
    if a.record:
        rec, where = read_record(a.record)
        print(json.dumps({"record": rec, "read_from": where}, indent=1, ensure_ascii=False))
        return 0 if rec else 1
    if not a.folder:
        ap.error("a card folder, or --record <cover file>")
    folder = Path(a.folder)
    got = checks(folder, json.loads((folder / "card.json").read_text()))
    if not got:
        print("the cover rule does not apply to this card (not a waiting video card, or switched off)")
        return 0
    for k, v in got.items():
        print(f"  {'PASS' if v['ok'] else 'FAIL'}  {LABELS[k]} — {v['why']}")
    return 0 if all(v["ok"] for v in got.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
