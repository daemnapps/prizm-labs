#!/usr/bin/env python3
"""line.py — the whole edit line in one command, the same way every time, for any brand, product, person or swipe.

    python3 line.py <video-production-run> [--out <edit run dir>] [--brief brief-NNNN] [--batch batch-YYYY-MM-DD-x]
                    [--links <catalog link id> …] [--only control,<hook>] [--no-file]

From a finished production run (its clips, voices and plan) and the ad's own decisions.json (written by the editor:
what to cover, what to fix, the B-roll, the looks — see EDIT-STANDARD.md "The decisions"), to a card waiting for
Approve in Drive meta/<brand>/1-check/video/. Every step's check STOPS the line; nothing is delivered past a red one.

  1  plan        edit_map.py --hooks       one edit map per version (the control + every hook opening) — takes laid
                                            whole, no repairs (V15); the bank's music and SFX when called for (V14)
  1b music      music_bed.py              only when the swipe/brief has music and production picked none: one bed
                                            for the whole edit, then the plan again
  2  mouths      mouths.py, every version   the lead's mouth only moves when the lead is heard          STOPS
  3  render      render_map.py              per version, before a frame is made:
                                              mouths again · every scripted word heard (listen)         STOPS
                                            after: lips within a frame of the voice (syncheck)          STOPS
                                            then compose.py draws every word (map_sheet.py — one renderer, C13)
  3b audit      audit.py, every version    words cut · lips still · wrong shot · sync · words on a face or
                                            mouth on the finished frames · the swipe's music and SFX       STOPS
  4  scan        black frames, dead air, loudness, 9:16, every version                                 STOPS
  5  covers      image production           one cover per version, made by the image tool's cover job
                 make.py --purpose cover    (`cover_cmd` below) from a frame of that version's own video, the swipe
                                            it follows in the cover index and the version's headline, the ad's filed
                                            3D set (found in its records, `cover_set`) and one type for every version
                                            (`cover_type`); each cover's record (`<cover>.cover.json`) names that frame
                                            (the video's full path and sha256) and that swipe.
                                            STOPS on a missing headline, swipe, set or picture, or one not 9:16 / too big.
                                            thumbs.py (words laid on a frame) is retired as the cover step.
                                            Switch: steps.json `line.cover_job` / COVER_JOB_OFF (rollbacks COVER-JOB,
                                            COVER-JOB-SET-TYPE)
  5b copy       copywriter brief_words.py  the ad's primary text, headlines, descriptions written by the copy machine
                                            — used as it is when already written; nothing written STOPS the line;
                                            `line.py copy-early <run>` writes it beside production (E34)
                                            (components/copywriter, stages 0-9) — skipped only when this brief's copy
                                            is already written: every ad set ready for distribution gets its copy
                                            from the copywriter (ruling 2026-10-09)
  6  deliver     deliver.py                 names (components/naming), the card, the manifest          STOPS on a gap
  7  file        meta-upload to_check       the card + videos + covers into 1-check (refiled in place: the Drive link stays)

Writes <out>/line.json — every step, what it found, how long it took. Exit 0 = filed and waiting for Approve.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
PY = sys.executable


def approved(rj, brief):
    """The final OK on the finished control cut — an `approve` verdict on the ad's review request, from the board,
    the dashboard or a teammate's own Claude, or a legacy jsonl line — read through ad_approvals.py (AR-1 (shared
    ad approvals), AR-1b (approvals as verdicts)). Hook versions and thumbnails wait for it: they are made last, right
    after the final approval of the control cut (rulings 9 and 15 Oct)."""
    # Scope (video sync 2026-10-21, R8 / VIDEO-RULINGS V19): this OK only lets the hook versions and thumbnails be
    # made. It never sends anything live — Approve on Meta stays the owner's own press on the 1-check card.
    import ad_approvals
    keys = {k for k in (brief, rj.get("label"), rj.get("brief")) if k}
    src = str(rj.get("source_brief") or rj.get("brief_from") or "")
    for i, steps in ad_approvals.load(REPO).items():
        if "final" not in steps:
            continue                      # a production OK is not his OK on the finished cut
        if i and (i in keys or (len(i) > 5 and i in src) or any(i.endswith(k) or k.endswith(i) for k in keys)):
            return True
    return False


STEPS = [x["id"] for x in json.loads((HERE / "steps.json").read_text())["line"]["steps"]]   # one list, steps.json (E16)


class Red(SystemExit):
    pass


# ---------------------------------------------------------------- the ad's copy (E34, 2026-10-21)
# The copywriter ran on the edit's TAIL: 43 min at step 5b in the one measured full line, writing nothing (a reddit
# 408), then again inside filing (~49 min more). Now: copy already written is used as it is; a copywriter that writes
# nothing STOPS the line naming why; filing never runs it again; and `line.py copy-early <production run>` lets the
# batch runner write the copy beside production, the moment the brief lands.
def copy_words(brand: str, brief: str) -> tuple[dict, str | None]:
    """The words written for this brief — meta-upload's public `card_words.for_brief` (the approved copy set, else the
    brief's copywriter runs) — and where they came from. ({}, None) when there are none yet."""
    sys.path.insert(0, str(REPO / "components" / "meta-upload"))
    import card_words as W
    try:
        return W.for_brief(brand, brief)
    except Exception:  # noqa: BLE001 — unreadable copy is no copy; the line then writes it
        return {}, None


def has_copy(words: dict) -> bool:
    """The card's minimum: a primary text and a headline."""
    return bool((words or {}).get("primary")) and bool((words or {}).get("headlines"))


def write_copy(brand: str, brief: str, log: list[dict] | None = None, step: str = "5b copy") -> str:
    """The copy for one brief, written once: used as it is when it exists; else the copywriter runs, and if it still
    wrote nothing the line STOPS, naming the copywriter's own last words — never a silent card with no copy."""
    log = log if log is not None else []
    w, where = copy_words(brand, brief)
    if has_copy(w):
        log.append({"step": step, "ok": True, "said": f"{brief}: copy already written ({where})"})
        print(f"  ✓ {step:<10} {brief}: already written ({where})")
        return where or ""
    cw = REPO / "components" / "copywriter" / "machine" / "brief_words.py"
    t = time.time()
    r = subprocess.run([PY, str(cw), "--brand", brand, "--brief", brief], capture_output=True, text=True)
    said = (r.stdout + r.stderr).strip()
    w, where = copy_words(brand, brief)
    ok = has_copy(w)
    log.append({"step": step, "ok": ok, "seconds": round(time.time() - t, 1), "said": said[-3000:]})
    if not ok:
        print(f"  ✗ {step:<10} the copywriter wrote no copy for {brief}", flush=True)
        raise Red(f"{step} stopped the line: the copywriter wrote no copy for {brief} (exit {r.returncode}) — "
                  f"its last words:\n{said[-1500:] or '(nothing)'}\nFix the copywriter's run, then `line.py <run> --from copy`.")
    print(f"  ✓ {step:<10} {brief}: written by the copywriter ({where})")
    return where or ""


def copy_early(argv=None) -> int:
    """`line.py copy-early <production run> [--brief brief-NNNN]` — write the ad's copy now, beside production, so the
    line finds it written at 5b. Exit 0 = the copy is there."""
    ap = argparse.ArgumentParser(description="write the ad's copy as soon as the brief lands, beside production")
    ap.add_argument("cmd"); ap.add_argument("run"); ap.add_argument("--brief")
    a = ap.parse_args(argv)
    rj = json.loads((Path(a.run) / "run.json").read_text())
    brief = a.brief or rj.get("brief")
    if not brief:
        print("copy-early: this production run names no brief — nothing to write copy for")
        return 1
    try:
        write_copy(rj.get("brand", ""), brief, step="copy early")
        return 0
    except Red as e:
        print(str(e))
        return 1


class Done(Exception):
    pass


# ---------------------------------------------------------------- the covers (2026-11-12)
# A cover is a picture made by image production, start to finish: one per version, from a frame of that version's own
# video, following a real cover in the cover index (components/asset-index/swipes), with the version's headline as
# its words. This line only gathers those four things, calls the image tool once per version, and writes the record
# the approval card's checks read (meta-upload cover_rule.py). Words laid on a frame (thumbs.py) are not a cover.
IMAGE_TOOL = REPO / "components" / "image-production" / "make.py"
COVER_INDEX = REPO / "runs" / "asset-index" / "swipes" / "covers"
COVER_FIND = REPO / "components" / "asset-index" / "swipes" / "covers.py"
COVER_MAX_BYTES, COVER_MIN_W = 10_000_000, 1080
OPENER_SECONDS = 6            # the strongest moment is looked for across the opener, one frame a second
NO_MOVE = ("as-shot", "unrated")


COVER_PARTS = ("find_set", "one_type")


def _cover_conf() -> dict:
    try:
        return json.loads((HERE / "steps.json").read_text())["line"].get("cover_job") or {}
    except (OSError, ValueError, KeyError):
        return {}


def _cover_off() -> set[str]:
    return {x.strip() for x in os.environ.get("COVER_JOB_OFF", "").split(",") if x.strip()}


def cover_job_on(part: str | None = None) -> bool:
    """The switch: steps.json `line.cover_job.on` (false = the retired frame covers, thumbs.py, run as before), or
    COVER_JOB_OFF=1 in one machine's environment. A part (`find_set`: the ad's set found in its records; `one_type`:
    every version set in one type) is on unless `line.cover_job.<part>` is false or COVER_JOB_OFF names it."""
    off = _cover_off()
    if off - set(COVER_PARTS):                    # 1, all, or anything else that is not a part name: the whole job
        return False
    c = _cover_conf()
    if c.get("on") is False:
        return False
    return part is None or (part not in off and c.get(part) is not False)


def cover_cmd(brand: str, version: str, frame: Path, swipe: str, headline: str, out: Path,
              product: str | None = None, set_: str | None = None, *, ad: str | None = None,
              video: Path | None = None, t: float | None = None, type_: Path | None = None) -> list[str]:
    """THE ONE PLACE this line names the image tool's cover job: a version id, a frame of that version's own video,
    the swipe id it follows and its headline; the ad it belongs to, that video and the frame's second in it, and the
    ad's one type for every version. The job's options change here and nowhere else."""
    cmd = [PY, str(IMAGE_TOOL), "--purpose", "cover", "--brand", brand, "--version", version, "--frame", str(frame),
           "--swipe", swipe, "--headline", headline, "--out", str(out)]
    cmd += (["--product", product] if product else []) + (["--set", set_] if set_ else [])
    cmd += (["--ad", ad] if ad else []) + (["--video", str(video)] if video else [])
    cmd += (["--frame-at", f"{float(t):g}"] if t is not None else []) + (["--type", str(type_)] if type_ else [])
    return cmd


def cover_headline(mine: dict, m: dict) -> str | None:
    """The version's headline: the ad's own decision (`thumbs.<version>.text`), else the headline its map puts on
    screen at the opening."""
    if mine.get("text"):
        return " ".join(str(mine["text"]).split())
    for t in m.get("text") or []:
        if t.get("kind") == "hook headline" and t.get("words"):
            return " ".join(" ".join(str(w).split()) for w in t["words"])
    return None


def cover_moment(video: Path, tmp: Path, read=None) -> float:
    """The strongest moment of a version's opener, in seconds: of one frame a second, the one where a face fills the
    most of the picture (the closest reaction). No face read, or no reader on this machine: second 1."""
    try:
        if read is None:
            import thumbs as TH
            read = TH.scenes
        times = [float(t) for t in range(0, OPENER_SECONDS)]
        frames = []
        for t in times:
            f = Path(tmp) / f"m{int(t)}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t + 0.5:.2f}", "-i", str(video), "-frames:v", "1",
                            "-q:v", "3", str(f)], capture_output=True)
            if f.exists():
                frames.append((t + 0.5, f))
        if not frames:
            return 1.0
        rows = read([f for _, f in frames])
        area = [max((b["w"] * b["h"] for b in r.get("faces") or []), default=0.0) for r in rows]
        return frames[area.index(max(area))][0] if max(area) > 0 else 1.0
    except Exception:  # noqa: BLE001 — no reader is not a stop: the frame is then second 1
        return 1.0


def cover_video(out: Path, version: str) -> Path:
    """The file a version's cover frame is cut from: its clean picture (no words on it) when the render kept one, else
    the finished file."""
    clean = out / "renders" / f"{version}.clean.mp4"
    return clean if clean.exists() else out / "renders" / f"{version}.mp4"


def _sha256(f: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cover_frame(out: Path, version: str, t: float, dest: Path) -> Path:
    """One frame of this version's own finished video at second t: its clean picture (no words on it) when the render
    kept one, else the finished file."""
    src = cover_video(out, version)
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(src), "-frames:v", "1",
                        "-q:v", "2", str(dest)], capture_output=True, text=True)
    if r.returncode != 0 or not dest.exists():
        raise Red(f"5 covers stopped the line: no frame of {src.name} at {t:.1f}s ({(r.stderr or '').strip()[-300:]})")
    return dest


def cover_swipes(avatar: str | None, n: int, find=None) -> list[str]:
    """Up to n swipe ids from the cover index for this avatar, most liked first, covers that make a move before the
    ones that make none. Only the avatar's own covers count: a general discovery cover is not one that avatar sees."""
    if find is None:
        def find(avatar_, limit):
            r = subprocess.run([PY, str(COVER_FIND), "find", str(COVER_INDEX), "--avatar", avatar_, "--rank", "likes",
                                "--limit", str(limit), "--json"], capture_output=True, text=True)
            return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    if not avatar:
        return []
    got = find(avatar, max(n * 4, 12)) or {}
    if got.get("scope") != "avatar":
        return []
    rows = [c for c in got.get("covers") or [] if c.get("id")]
    rows = [c for c in rows if c.get("move") not in NO_MOVE] + [c for c in rows if c.get("move") in NO_MOVE]
    return [c["id"] for c in rows][:n]


def cover_facts(vm: Path, rj: dict, erj: dict, th: dict, brief: str | None = None) -> tuple[str | None, str | None]:
    """(avatar, product) for the covers, from the places the card's own are read (deliver.py): the ad's decisions,
    the run records, the production brief's own block (`piece` in brief.md), then the brief's header in the register."""
    piece = {}
    try:
        for m in re.finditer(r"```json\s*(\{.*?\})\s*```", (Path(vm) / "brief.md").read_text(), re.S):
            try:
                d = json.loads(m.group(1))
            except ValueError:
                continue
            if isinstance(d, dict) and isinstance(d.get("piece"), dict):
                piece = d["piece"]
                break
    except OSError:
        pass
    avatar = th.get("avatar") or erj.get("avatar") or rj.get("avatar") or piece.get("avatar")
    product = erj.get("product") or rj.get("product") or piece.get("product")
    if not avatar and brief:
        try:
            sys.path.insert(0, str(REPO / "components" / "naming"))
            import names as N
            avatar = (N.brief_header(rj.get("brand", ""), brief, product) or {}).get("avatar")
        except Exception:  # noqa: BLE001 — a brief the register cannot place names no avatar here
            avatar = None
    return (str(avatar) if avatar else None), (str(product) if product else None)


def _image_tool():
    """The image tool's library (components/image-production), for its free lookups: the filed sets and the type."""
    p = str(IMAGE_TOOL.parent)
    if p not in sys.path:
        sys.path.append(p)
    import image_production
    return image_production


def _kept(brand: str, name: str) -> bool:
    """Is `name` a filed 3D set of this brand with a kept print on this machine?"""
    SG = _image_tool().set_gate
    return SG.kept_print(brand, SG.set_name(name)) is not None


SET_KEYS = ("cover_set", "set", "from_print", "set_print")
SET_SCAN_FILES, SET_SCAN_BYTES = 400, 2_000_000


def _sets_in(obj, found: list[str]) -> None:
    """Every set a record names: a `set` / `cover_set` (a name, or {name}), or a kept print it started from
    (`from_print`, `set_print`: the print's folder is the set)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SET_KEYS and isinstance(v, str) and v.strip():
                found.append(Path(v.strip()).parent.name if k in ("from_print", "set_print") else v.strip())
            elif k in ("set", "cover_set") and isinstance(v, dict) and isinstance(v.get("name"), str):
                found.append(v["name"].strip())
            else:
                _sets_in(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _sets_in(v, found)


def cover_set(vm: Path, out: Path, rj: dict, erj: dict, brand: str, product: str | None, brief: str | None,
              kept=None, sets_home: Path | None = None) -> tuple[str | None, str]:
    """The ad's filed 3D set for its covers when its decisions name none, and where it was found: the run records
    (`set` / `cover_set`), the production brief's `piece`, any record of the production or edit run that names a set or
    the kept print it started from (the set the most of them name), then the brand's filed sets whose record names
    this brief, this production or this product (only when exactly one does). Every candidate must be a filed set with
    a kept print on this machine (`kept`, the image tool's own check). (None, where it looked) when none is."""
    kept = kept or _kept
    looked = []

    def ok(name):
        try:
            return bool(name) and kept(brand, name)
        except Exception:  # noqa: BLE001 — a lookup that fails names no set
            return False
    for where, name in (("the edit run's record", erj.get("cover_set") or erj.get("set")),
                        ("the production run's record", rj.get("cover_set") or rj.get("set"))):
        if isinstance(name, dict):
            name = name.get("name")
        if isinstance(name, str) and ok(name.strip()):
            return name.strip(), where
    looked.append("the run records")
    try:
        for m in re.finditer(r"```json\s*(\{.*?\})\s*```", (Path(vm) / "brief.md").read_text(), re.S):
            try:
                piece = (json.loads(m.group(1)) or {}).get("piece") or {}
            except (ValueError, AttributeError):
                continue
            name = piece.get("set") if isinstance(piece, dict) else None
            if isinstance(name, str) and ok(name.strip()):
                return name.strip(), "the production brief"
    except OSError:
        pass
    looked.append("the production brief")
    found, seen = [], 0
    for root in (Path(vm), Path(out)):
        for f in sorted(root.rglob("*.json")) if root.is_dir() else []:
            if seen >= SET_SCAN_FILES:
                break
            try:
                if f.stat().st_size > SET_SCAN_BYTES:
                    continue
                seen += 1
                _sets_in(json.loads(f.read_text()), found)
            except (OSError, ValueError):
                continue
    counts = {}
    for name in found:
        counts[name] = counts.get(name, 0) + 1
    for name in sorted(counts, key=lambda n: -counts[n]):
        if ok(name):
            return name, f"the production's records ({counts[name]} name it)"
    looked.append("the production's records")
    home = sets_home or REPO / "runs" / "image-production" / brand / "sets"
    keys = {k for k in (brief, rj.get("label"), rj.get("brief"), erj.get("label")) if k}
    prod = {product} if product else set()
    by_ad, by_product = [], []
    for sj in sorted(home.glob("*/set.json")) if home.is_dir() else []:
        try:
            d = json.loads(sj.read_text())
        except (OSError, ValueError):
            continue
        runs = {str(x) for x in (d.get("runs") or []) + ([d["run"]] if d.get("run") else [])}
        named = {str(x) for x in (d.get("products") or []) + ([d["product"]] if d.get("product") else [])}
        if keys & runs:
            by_ad.append(sj.parent.name)
        elif prod & named:
            by_product.append(sj.parent.name)
    for pool, where in ((by_ad, "the filed sets naming this ad"), (by_product, "the filed sets naming this product")):
        pool = [n for n in pool if ok(n)]
        if len(pool) == 1:
            return pool[0], where
    looked.append("the brand's filed sets (runs/image-production/<brand>/sets/*/set.json) naming this ad or product")
    return None, ", ".join(looked)


def cover_type(brand: str, ad: str, product: str | None, headlines: list[str], dest: Path, typer=None) -> Path | None:
    """The ad's one type for every version's cover, written to `dest` as {"ad", "type"} (the image tool's own
    cover-type.json shape): the image tool's type fitted to every version's headline at once, kept clear of where the
    product sits. None when the tool sets no words itself (its words step is off). `typer(brand, product, headlines)`
    is the tool's fit unless a test passes its own. STOPS with the tool's own reason when no size fits them all."""
    if typer is None:
        def typer(brand_, product_, headlines_):
            CV = _image_tool().covers
            if not CV.on("words_step"):
                return None
            spot = CV.planned_box(brand_, product_) if CV.on("product_with_set") else None
            return CV.ad_type(headlines_, None, clear_of=[spot] * len(headlines_))
    try:
        style = typer(brand, product, headlines)
    except Exception as ex:  # noqa: BLE001 — the tool's refusal is the line's stop
        raise Red(f"5 covers stopped the line: no one type fits every version's headline ({ex})")
    if style is None:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"ad": ad, "type": style}, indent=1, ensure_ascii=False, default=str) + "\n")
    return dest


def cover_delivered(folder: Path, frame: Path | None = None) -> Path:
    """The picture the image tool delivered into this folder: the one its run record names, else the newest picture
    that is not the frame it was handed."""
    try:
        pics = json.loads((folder / "run.json").read_text()).get("pictures") or []
        named = [folder / Path(str(p.get("file") or p.get("name") or "")).name for p in pics if isinstance(p, dict)]
        named = [p for p in named if p.is_file()]
        if named:
            return named[0]
    except (OSError, ValueError):
        pass
    pics = [p for p in folder.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
            and p != frame and p.is_file()]
    if not pics:
        raise Red(f"5 covers stopped the line: the image tool delivered no picture into {folder}")
    return max(pics, key=lambda p: p.stat().st_mtime)


def make_covers(vm: Path, out: Path, rj: dict, want, log: list[dict], *, brief: str | None = None, call=None,
                find=None, moment=None, frame=None, kept=None, typer=None, sets_home=None) -> dict:
    """One cover per version through the image tool's cover job; returns {version: record} and writes it to
    <out>/covers/covers.json, each cover's record beside it as <cover>.cover.json. Anything missing STOPS the line with
    its plain reason. `call`, `find`, `moment`, `frame`, `kept` and `typer` are the image tool, the cover index, the
    moment reader, the frame grab, the filed-set check and the type fit: the real ones unless a test passes its own."""
    import tempfile
    from PIL import Image
    call, frame, moment = call or run, frame or cover_frame, moment or cover_moment
    dec = json.loads((out / "decisions.json").read_text()) if (out / "decisions.json").exists() else {}
    th = dec.get("thumbs") or {}
    erj = json.loads((out / "run.json").read_text()) if (out / "run.json").exists() else {}
    versions = [v for v in ["control"] + sorted(f.stem[len("edit-map-"):] for f in out.glob("edit-map-*.json")) if v in set(want)]
    avatar, product = cover_facts(vm, rj, erj, th, brief)
    named = {v: (th.get(v) or {}).get("swipe") for v in versions}
    pool = [s for s in (th.get("swipes") or []) if s not in named.values()]
    if len(pool) < sum(1 for v in versions if not named[v]):
        pool += [s for s in cover_swipes(avatar, len(versions) * 2, find) if s not in named.values() and s not in pool]
    brand = rj.get("brand", "")
    ad = str(brief or erj.get("brief") or rj.get("brief") or rj.get("label") or out.name)

    def edit_map(v):
        return json.loads((out / ("edit-map.json" if v == "control" else f"edit-map-{v}.json")).read_text())
    for v in versions:
        if not (out / "renders" / f"{v}.mp4").exists():
            raise Red(f"5 covers stopped the line: {v} has no finished video ({v}.mp4) to take its cover's frame from")
        if not cover_headline(th.get(v) or {}, edit_map(v)):
            raise Red(f"5 covers stopped the line: {v} has no headline for its cover — its map shows none at the "
                      f"opening; write `thumbs.{v}.text` in decisions.json")
    # THE AD'S SET when its decisions name none: found in its own records (cover_set), never a guess
    found_set, set_from = (None, "")
    if cover_job_on("find_set") and not th.get("set") and any(not (th.get(v) or {}).get("set") for v in versions):
        found_set, set_from = cover_set(vm, out, rj, erj, brand, product, brief, kept=kept, sets_home=sets_home)
    # ONE TYPE for every version of the ad (every version that has a headline, made now or not), fitted once
    type_file = None
    if cover_job_on("one_type"):
        every = ["control"] + sorted(f.stem[len("edit-map-"):] for f in out.glob("edit-map-*.json"))
        lines = [h for h in (cover_headline(th.get(v) or {}, edit_map(v)) for v in every
                             if (out / ("edit-map.json" if v == "control" else f"edit-map-{v}.json")).exists()) if h]
        type_file = cover_type(brand, ad, product, lines, out / "covers" / "cover-type.json", typer=typer)
    got = {}
    for v in versions:
        mine = th.get(v) or {}
        m = edit_map(v)
        video = out / "renders" / f"{v}.mp4"
        headline = cover_headline(mine, m)
        swipe = named[v] or (pool.pop(0) if pool else None)
        if not swipe:
            raise Red(f"5 covers stopped the line: no swipe for {v}'s cover — the cover index has no covers left for "
                      f"avatar {avatar or '(none named)'}. Pull that avatar's feed into the index "
                      f"(components/asset-index/swipes: covers.py pull --avatar, then index), or name the swipes in "
                      f"decisions.json `thumbs.swipes`")
        folder = out / "covers" / v
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            t = float(mine["at"]) if mine.get("at") is not None else (
                float(th["at"]) if th.get("at") is not None else moment(video, Path(tmp)))
        fr = frame(out, v, t, folder / f"{v}_frame.jpg")
        source = cover_video(out, v)
        set_ = mine.get("set") or th.get("set") or found_set
        cmd = cover_cmd(brand, v, fr, swipe, headline, folder, product=product, set_=set_,
                        ad=ad, video=source, t=round(t, 2), type_=type_file)
        try:
            call(f"5 covers {v}", cmd, log)
        except Red as e:
            if set_:
                raise
            raise Red(f"{e}\n5 covers: no filed 3D set for this ad — looked in decisions.json `thumbs.set`, "
                      f"{set_from or 'nothing (the finder is off)'}. File the ad's set (the 3d-print skill: "
                      f"picture_sets.py put), or name it in decisions.json `thumbs.set`.") from None
        pic = cover_delivered(folder, fr)
        with Image.open(pic) as im:
            w, h = im.size
        if abs(w / h - 9 / 16) > 0.01 or w < COVER_MIN_W or pic.stat().st_size > COVER_MAX_BYTES:
            raise Red(f"5 covers stopped the line: {pic.name} is {w}x{h}, {pic.stat().st_size / 1e6:.1f} MB — a cover "
                      f"is 9:16, at least {COVER_MIN_W} wide, under 10 MB")
        rec = {"version": v, "swipe": swipe, "headline": headline,
               "frame": {"video": str(source), "video_sha256": _sha256(source), "t": round(t, 2), "file": fr.name},
               "made_by": "image-production make.py --purpose cover"}
        if set_:
            rec["set_from"] = ("the ad's decisions" if (mine.get("set") or th.get("set")) else set_from)
        cover_record(pic.with_suffix(".cover.json"), rec)
        got[v] = {"file": str(pic), **rec}
    twice = {s for s in [r["swipe"] for r in got.values()] if [r["swipe"] for r in got.values()].count(s) > 1}
    if twice:
        print(f"  NOTE 5 covers: more than one version follows {', '.join(sorted(twice))} (the ad's decisions name it for each)")
    (out / "covers").mkdir(exist_ok=True)
    (out / "covers" / "covers.json").write_text(json.dumps(got, indent=1, ensure_ascii=False) + "\n")
    log.append({"step": "5 covers", "ok": True, "said": "; ".join(f"{v}: follows {r['swipe']}, frame at {r['frame']['t']}s" for v, r in got.items())
                + (f"; set {found_set} from {set_from}" if found_set else "")
                + (f"; one type: {type_file.name}" if type_file else "")})
    return got


def cover_record(side: Path, rec: dict) -> None:
    """The cover's record beside it. The image tool's own record, when it wrote one there, is kept whole: only what
    it does not say (the version, the swipe, the headline, the frame's video, second and file) is filled in."""
    try:
        theirs = json.loads(side.read_text())
    except (OSError, ValueError):
        theirs = None
    if not isinstance(theirs, dict) or not theirs:
        side.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
        return
    for k in ("version", "swipe", "headline"):
        if theirs.get(k) in (None, ""):
            theirs[k] = rec[k]
    key = "frame" if "frame" in theirs else "source_frame" if "source_frame" in theirs else None
    if key is None or not theirs[key]:
        theirs["frame" if key is None else key] = rec["frame"]
    elif isinstance(theirs[key], dict):
        for k, val in rec["frame"].items():
            if theirs[key].get(k) in (None, ""):
                theirs[key][k] = val
    side.write_text(json.dumps(theirs, indent=1, ensure_ascii=False, default=str) + "\n")


def cover_files(out: Path, versions: list[str]) -> list[Path] | None:
    """The covers to file, one per version in order, or None when any version has none (the card then says so)."""
    try:
        got = json.loads((out / "covers" / "covers.json").read_text())
    except (OSError, ValueError):
        return None
    files = [Path(got[v]["file"]) if v in got else None for v in versions]
    return files if all(f is not None and f.exists() for f in files) else None


def _edit_auto() -> bool:
    import render_map
    return render_map._edit_auto()


def run(step: str, cmd: list[str], log: list[dict], env: dict | None = None) -> str:
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = (r.stdout + r.stderr).strip()
    log.append({"step": step, "ok": r.returncode == 0, "seconds": round(time.time() - t, 1), "said": out[-3000:]})
    print(f"  {'✓' if r.returncode == 0 else '✗'} {step:<10} {out.splitlines()[-1] if out else ''}", flush=True)
    if r.returncode != 0:
        raise Red(f"{step} stopped the line:\n{out[-2000:]}")
    return out


_APPROVED = {"on": False}


def soft(step: str, cmd: list[str], log: list[dict]) -> str:
    """A check that, on a draft with edit on Auto, or on a cut of APPROVED clips (`--approved`, L-66), is logged and
    carried past (the render itself still lists it)."""
    try:
        return run(step, cmd, log)
    except Red as e:
        if not (_edit_auto() or _APPROVED["on"]):
            raise
        print(f"  WARN {step}: carried past ({'the clips are approved: listed for a person' if _APPROVED['on'] else 'edit on Auto'})")
        return str(e)


def scan(mp4: Path, room: bool = True) -> dict:
    """Black frames, dead silence, loudness and shape of one finished file. With room tone under the cut (only when the
    swipe has room sound, V14) no moment may drop to silence at all; without it the breath between two lines is the
    voices' own tails, so only DEAD AIR counts — a silence of half a second or more (V15)."""
    def ff(*a):
        return subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), *a, "-f", "null", "-"], capture_output=True, text=True).stderr
    black = ff("-vf", "blackdetect=d=0.05:pix_th=0.08", "-an").count("black_start")
    silence = ff("-af", f"silencedetect=n=-60dB:d={0.05 if room else 0.5}", "-vn").count("silence_start")
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", ff("-af", "ebur128", "-vn"))
    wh = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                         "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip()
    w, h = (int(x) for x in wh.split(","))
    return {"black": black, "silences": silence, "lufs": float(lufs[-1]) if lufs else None, "size": [w, h],
            "ok": black == 0 and silence == 0 and w * 16 == h * 9 and (lufs and abs(float(lufs[-1]) + 14) <= 1.5)}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["copy-early"]:
        return copy_early(argv)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--brief"); ap.add_argument("--batch")
    ap.add_argument("--links", nargs="*", default=[]); ap.add_argument("--only"); ap.add_argument("--no-file", action="store_true")
    ap.add_argument("--versions", action="store_true",
                    help="make the hook versions + thumbnails now (normally they wait for the owner's OK on the control cut)")
    ap.add_argument("--approved", action="store_true",
                    help="the clips, voice and script are approved (the board's Edit step): the edit only cuts them together; "
                         "its checks are listed, never a stop, and nothing is regenerated")
    ap.add_argument("--draft", action="store_true",
                    help="stop at the draft on the timeline: plan, word fixes, mouths, a draft render, scan — nothing delivered or filed")
    ap.add_argument("--from", dest="start", choices=STEPS, default="plan",
                    help="start at this step (the steps before it already ran clean, e.g. --from deliver after a naming gap)")
    a = ap.parse_args(argv)
    _APPROVED["on"] = bool(a.approved)
    vm = Path(a.run).resolve()
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out).resolve() if a.out else REPO / "runs" / "video-edit" / rj["brand"] / rj["label"]
    log: list[dict] = []
    t0 = time.time()
    print(f"edit line · {rj['brand']} · {rj['label']}")
    go = lambda step: STEPS.index(step) >= STEPS.index(a.start)
    erj = json.loads((out / "run.json").read_text()) if (out / "run.json").exists() else {}
    brief = a.brief or erj.get("brief") or rj.get("brief")        # the register number, wherever it was opened
    try:
        if go("plan"):
            run("1 plan", [PY, str(HERE / "edit_map.py"), str(vm), "--out", str(out), "--hooks"], log)
            # NO REPAIRS on this path (V15 "the edit cuts, it does not repair"; verify 2026-10-21 row 6): the old 1b step
            # re-said a cut-off line in a cloned voice (word_fix auto) on every cut. A take that cuts a line off goes
            # back to production; the audit names it (WORD CUT) and stops the line.
            # THE MUSIC the swipe or the brief calls for and production did not pick (V14, row 5): one bed made to
            # cover the whole edit (music_bed.py, ElevenLabs Music), then the cut re-planned to lay it
            m0 = json.loads((out / "edit-map.json").read_text())
            replan = False
            if (m0.get("music") or {}).get("what") and not (m0.get("music") or {}).get("made"):
                run("1b music", [PY, str(HERE / "music_bed.py"), str(vm), "--out", str(out)], log)
                replan = True
            # THE EFFECTS the swipe or the brief calls for and no bank has yet (E39): made for this edit through
            # production's bank maker, in the run's own bank — never an effect nobody called for (V14)
            if any(not c.get("made") for c in m0.get("sfx") or []):
                run("1c effects", [PY, str(HERE / "sfx_make.py"), str(vm), "--out", str(out)], log)
                replan = True
            if replan:
                run("1 plan", [PY, str(HERE / "edit_map.py"), str(vm), "--out", str(out), "--hooks"], log)
        maps = ["edit-map.json"] + sorted(f.name for f in out.glob("edit-map-*.json"))
        names = {m: ("control" if m == "edit-map.json" else m[len("edit-map-"):-5]) for m in maps}
        versions = a.versions or approved(rj, brief)
        # THE CONTROL CUT FIRST: hook versions and thumbnails are made only after his OK (approved() above)
        want = set(a.only.split(",")) if a.only else (set(names.values()) if versions else {"control"})
        if not versions and not a.only:
            print("  control cut only — hook versions + thumbnails wait for the owner's OK (Ad Runs board)")
        for m, v in names.items():
            if v in want and go("mouths"):
                (soft if a.draft else run)(f"2 mouths {v}", [PY, str(HERE / "mouths.py"), str(vm), "--out", str(out), "--map", m], log)
        if go("render"):
            run("3 render", [PY, str(HERE / "render_map.py"), str(vm), "--out", str(out), "--only", ",".join(sorted(want)),
                             *(["--draft"] if a.draft else []), *(["--approved"] if a.approved else [])], log)
        if go("audit"):
            # THE AUDIT, every version (E12–E14): before anyone watches it; a finding stops the line (a draft on Auto
            # carries it, listed — the final still holds it)
            (soft if a.draft or a.approved else run)("3b audit", [PY, str(HERE / "audit.py"), str(out), "--only", ",".join(sorted(want))], log)
        bad = {}
        for v in (sorted(want) if go("scan") else []):
            rj_v = json.loads((out / "renders" / f"{v}.json").read_text()) if (out / "renders" / f"{v}.json").exists() else {}
            s = scan(out / "renders" / f"{v}.mp4", bool(rj_v.get("room_tone", True)))
            log.append({"step": f"4 scan {v}", "ok": bool(s["ok"]), **s})
            print(f"  {'✓' if s['ok'] else '✗'} 4 scan {v:<6} black {s['black']} · silences {s['silences']} · {s['lufs']} LUFS · {s['size'][0]}x{s['size'][1]}")
            if not s["ok"]:
                bad[v] = s
        if bad and a.draft and _edit_auto():
            print(f"  WARN scan: {bad} (draft kept: edit on Auto; the final holds it)")
        elif bad:
            raise Red(f"4 scan stopped the line: {bad}")
        # THE WATCH (ruling 2026-10-23: one consistent model eye on every asset): the house
        # judge watches every finished version the way a viewer would (watch.py); a cut nobody watched never passes
        seen_bad = {}
        for v in (sorted(want) if go("watch") else []):
            import watch as W
            w = W.watch(out / "renders" / f"{v}.mp4", v, vm / "lines.json")
            log.append({"step": f"4b watch {v}", "ok": bool(w["pass"]), **{k: w.get(k) for k in ("score", "problems", "by")}})
            print(f"  {'✓' if w['pass'] else '✗'} 4b watch {v:<6} {w.get('score')}/10 · {len(w.get('problems') or [])} problems · {w.get('by')}")
            if not w["pass"]:
                seen_bad[v] = [p.get("what") for p in w.get("problems") or []][:4]
        if seen_bad and a.draft and _edit_auto():
            print(f"  WARN watch: {seen_bad} (draft kept: edit on Auto; the final holds it)")
        elif seen_bad:
            raise Red(f"4b watch stopped the line: {seen_bad}")
        if a.draft:
            raise Done("draft on the timeline — ready to watch and render")
        if go("thumbs") and (versions or a.only):
            if cover_job_on():
                # THE COVERS (2026-11-12): made by image production's cover job, one per version; thumbs.py's frame
                # covers are retired and refuse to run while this switch is on
                made = make_covers(vm, out, rj, want, log, brief=brief)
                print(f"  ✓ 5 covers   {len(made)} cover(s) from image production: " + ", ".join(sorted(made)))
            else:
                run("5 thumbs", [PY, str(HERE / "thumbs.py"), str(vm), "--out", str(out), "--only", ",".join(sorted(want))], log)
        if go("copy") and brief:
            # THE COPY MACHINE before the card (E34): copy already written — the approved copy set or this brief's
            # copywriter runs, read through meta-upload's card_words — is used as it is; else it is written once,
            # and a copywriter that writes nothing stops the line here, naming why
            write_copy(rj.get("brand", ""), brief, log)
        dcmd = [PY, str(HERE / "deliver.py"), str(out), str(out / "renders"), "--replace"]
        dcmd += (["--brief", brief] if brief else []) + (["--batch", a.batch] if a.batch else [])
        dcmd += (["--links", *a.links] if a.links else [])
        if go("deliver"):
            run("6 deliver", dcmd, log)
        if not a.no_file:
            card_dir = max((out / "deliverable").glob("*/card.json"), key=lambda p: p.stat().st_mtime).parent
            card = json.loads((card_dir / "card.json").read_text())
            man = json.loads((card_dir / "manifest.json").read_text())
            media = [str(out / "renders" / f"{x['version']}.mp4") for x in man["ads"]]
            words = card_dir / "words.json"
            words.write_text(json.dumps(card.get("words") or {}, ensure_ascii=False))
            fcmd = [PY, str(REPO / "components" / "meta-upload" / "to_check.py"), "--brand", card["brand"], "--lane", "video",
                    "--ad-name", card["ad_name"], "--product", card["product"], "--brief", card["brief_id"],
                    "--batch", man["batch"], "--media", *media, "--words", str(words), "--tool", "video-edit",
                    "--run", str(out.relative_to(REPO)) if out.is_relative_to(REPO) else str(out), "--replace",
                    "--links", *[p["link_id"] for p in card.get("pages") or []]]
            fcmd += (["--avatar", card["avatar"]] if card.get("avatar") else [])   # no --angle: the filer reads the brief's (naming ANGLE.md)
            if cover_job_on():
                thumbs = cover_files(out, [x["version"] for x in man["ads"]])
                if thumbs:      # each video's own cover; its record sits beside it (<cover>.cover.json) for the filer.
                    fcmd += ["--thumbs", *map(str, thumbs)]   # with none, the card files and its cover check holds it
            else:
                thumbs = [out / "renders" / f"{x['version']}_thumb.jpg" for x in man["ads"]]
                if all(t.exists() for t in thumbs):
                    fcmd += ["--thumbs", *map(str, thumbs)]       # each video's own designed thumbnail
            # the copy was settled at 5b: filing never runs the copywriter again (E34 — it once re-ran for ~49 min
            # after 5b had already failed); NO_AD_WORDS=1 is to_check's own switch for that
            run("7 file", fcmd, log, env={**os.environ, "NO_AD_WORDS": "1"})
        import to_drive  # LAST: every step above has read the finished files; they go to the Drive's same path
        to_drive.hand(out)
        ok, msg = True, "filed — waiting for Approve in meta/<brand>/1-check/video/" if not a.no_file else "delivered (not filed: --no-file)"
    except Done as e:
        ok, msg = True, str(e)
    except Red as e:
        ok, msg = False, str(e)
    # THE LEARN STEP, LAST (the edit's declared `learn`, run by the machine since 2026-11-18): the changes made on this
    # edit since its last lesson become lessons banked by stage. No change = no model call; it never changes `ok`.
    try:
        import learn as LN
        got = LN.safe(out)
        log.append({"step": "8 learn", "ok": True, **{k: v for k, v in got.items() if k != "state"}, "result": got["state"]})
        if got.get("lessons"):
            print("  ✓ 8 learn    " + got.get("note", ""))
    except Exception as e:  # noqa: BLE001
        log.append({"step": "8 learn", "ok": True, "result": "not run", "note": f"{type(e).__name__}: {e}"})
    (out / "line.json").write_text(json.dumps({"ok": ok, "result": msg.splitlines()[0], "minutes": round((time.time() - t0) / 60, 1),
                                               "steps": log}, indent=1, ensure_ascii=False))
    print(("DONE  " if ok else "STOPPED  ") + msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
