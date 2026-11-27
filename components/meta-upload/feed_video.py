#!/usr/bin/env python3
"""feed_video — a brief's finished video masters into 1-check, as one flexible card (every version in it).

    feed_video.py <video-edit run folder | video-editor hand-off folder> [--links …] [--dry-run] [--root …]

The video editor (components/video-edit/machine/handoff_run.py) calls `file_master()`
right after give_back() puts the master into the hand-off's returned/. Run by hand
it reads the run's status.json for its hand-off, and finds the master in the run
(`work/final.mp4`, else returned/); `--dry-run` plans a card for a run that has not
rendered yet, and writes nothing.

Writes `meta/<brand>/1-check/video/<ad name>/<ad name>_asset-01.mp4` + card.json.

Words: a `words.json` in the hand-off, else the brief's own copywriter runs
(card_words.for_brief — runs labelled with the brief's number or alias), else
empty lists (the card's check fails, and the card shows "no primary text · no headline").
Pages: the hand-off's link ids (briefs[].link_ids), plus any --links.
Covers: `thumbs` (one per master, in order) and `cover_records` when the caller passes them; when it passes neither,
the Video Studio's hand-off for these masters (`<VIDEO_STUDIO_DATA>/briefs/<production>/covers/to-file.json`, written
by its cover stage) when it is there, ready and fresh: it says `ready` (every version has its cover; a hand-off with
a held version or a run still going files none, so the card never carries some versions' covers and reads as covered),
it was made after every master was last written, and every master is the same file the cover stage made its cover
from (`stage.json` video_stamp). A stale, unready or missing hand-off files no covers, and the card's cover check holds
it. Switch: cover-rule.json `to_file`, META_FILE_MASTER_COVERS_OFF=1 (row FILE-MASTER-COVERS); `to_file_ready`,
META_FILE_MASTER_COVERS_OFF=ready (row FILE-MASTER-COVERS-READY).
"""
import argparse, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import names as N  # noqa: E402
import card_words as W  # noqa: E402
import to_check as T  # noqa: E402

# runs/handoffs first, the old print-run staging last (2026-10-28)
HANDOFFS = [REPO / "runs/handoffs/video-editor", REPO / "lab/owner/print-run/handoffs/video-editor"]


def _read(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.is_file() else None


def handoff_links(manifest):
    out = []
    for b in manifest.get("briefs") or []:
        out += b.get("link_ids") or []
    return out + list((manifest.get("ids") or {}).get("links") or [])


def words_for(brand, brief, handoff=None, repo=REPO):
    """(words, where from)."""
    if handoff and (Path(handoff) / "words.json").is_file():
        return W.from_file(Path(handoff) / "words.json"), str(Path(handoff) / "words.json")
    w, src = W.for_brief(brand, brief, repo)
    return w, src or "nothing found"


TO_FILE_PARTS = ("ready",)            # META_FILE_MASTER_COVERS_OFF names these to turn one part off; any other value, all


def _covers_off():
    return {x.strip() for x in os.environ.get("META_FILE_MASTER_COVERS_OFF", "").split(",") if x.strip()}


def _rule():
    try:
        return json.loads((HERE / "cover-rule.json").read_text())
    except (OSError, ValueError):
        return {}


def to_file_on():
    """Does file_master read the Video Studio's cover hand-off? cover-rule.json `to_file` (default on), and not
    META_FILE_MASTER_COVERS_OFF (1, or anything but a part name) on this machine."""
    if _covers_off() - set(TO_FILE_PARTS):
        return False
    return _rule().get("to_file") is not False


def needs_ready():
    """Does file_master file a hand-off's covers only when it says ready? cover-rule.json `to_file_ready` (default
    on), and not META_FILE_MASTER_COVERS_OFF=ready on this machine."""
    return "ready" not in _covers_off() and _rule().get("to_file_ready") is not False


def studio_data():
    return Path(os.environ.get("VIDEO_STUDIO_DATA") or REPO / "runs" / "video-studio")


def _same(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return False


def _stamp(f):
    try:
        st = Path(f).stat()
        return st.st_mtime, st.st_size
    except OSError:
        return None


def studio_covers(masters, production=None, data=None):
    """(thumbs, cover_records, where, note) for these masters from the Video Studio's cover hand-off. `thumbs` and
    `cover_records` line up with `masters` (None where a master has no ready cover); both are None when no fresh
    hand-off covers these masters. `production` names the studio production; without it the hand-off whose videos
    are exactly these files is used."""
    data = Path(data or studio_data()) / "briefs"
    files = [data / production / "covers" / "to-file.json"] if production else sorted(data.glob("*/covers/to-file.json"))
    for f in files:
        hand = _read(f) if f.is_file() else None
        if not isinstance(hand, dict):
            continue
        media = [str(m) for m in hand.get("media") or []]
        at = []
        for m in masters:
            i = next((k for k, x in enumerate(media) if _same(x, m)), None)
            if i is None and production:                  # named by the caller: the studio's own name for it counts
                i = next((k for k, x in enumerate(media) if Path(x).name == Path(m).name), None)
            at.append(i)
        if None in at:
            if production:
                return None, None, str(f), f"{f}: covers no file named {Path(masters[at.index(None)]).name}"
            continue
        if needs_ready() and hand.get("ready") is not True:
            held = "; ".join("%s: %s" % (h.get("version"), h.get("why") or "held") for h in hand.get("held") or []
                             if isinstance(h, dict))
            return None, None, str(f), (f"{f}: the hand-off is not ready, so no cover is filed until every version "
                                        f"has one" + (f" (held: {held})" if held else
                                                      " (its cover run is still going)" if hand.get("running") else ""))
        made = f.stat().st_mtime
        stage = _read(f.parent / "stage.json") or {}
        stamps = {Path(str(r.get("video"))).name: r.get("video_stamp") for r in stage.get("versions") or []
                  if isinstance(r, dict) and r.get("video")}
        for m in masters:
            now = _stamp(m)
            was = stamps.get(Path(m).name)
            if now is None:
                return None, None, str(f), f"{f}: {Path(m).name} is not on this machine"
            if now[0] > made + 1:
                return None, None, str(f), f"{f}: {Path(m).name} was written after the covers were handed off"
            if isinstance(was, dict) and (abs(float(was.get("mtime") or 0) - now[0]) > 1 or was.get("size") != now[1]):
                return None, None, str(f), f"{f}: {Path(m).name} is not the video its cover was made from"
        thumbs = [str((hand.get("thumbs") or [])[i]) if i < len(hand.get("thumbs") or []) else "" for i in at]
        recs = [str((hand.get("cover_records") or [])[i]) if i < len(hand.get("cover_records") or []) else "" for i in at]
        gone = [t for t in thumbs if t and not Path(t).is_file()]
        if gone:
            return None, None, str(f), f"{f}: cover not on this machine: {Path(gone[0]).name}"
        return [t or None for t in thumbs], [r or None for r in recs], str(f), ""
    return None, None, None, "no Video Studio cover hand-off covers these files"


def file_master(brand, brief, product, batch, master, *, handoff=None, run=None, links=(),
                root=None, dry_run=False, replace=False, repo=REPO, thumbs=None, cover_records=None,
                production=None, openings=None):
    """A brief's finished masters → its one card (flexible: every version rides in it, in order).
    `master` is one file or a list (the control first, then each hook). `thumbs` (a cover per master, in order) and
    `cover_records` go to the filer as given; with neither, the Video Studio's fresh cover hand-off for these masters
    is read (`studio_covers`; `production` names it). `openings` names the opening each master carries, in order;
    with none, the filer reads it from the edit's own record beside each render (openings.py). The card carries the
    brief's `concept` and one `openings` row per asset. Returns (plan, words source); the plan's `covers_from` says
    where the covers came from, or why none did."""
    man = _read(Path(handoff) / "manifest.json") if handoff else None
    words, src = words_for(brand, brief, handoff, repo)
    pages = list(dict.fromkeys(list(links) + (handoff_links(man) if man else [])))
    run_rel = str(Path(run).resolve().relative_to(repo)) if run and Path(run).resolve().is_relative_to(repo) else (str(run) if run else None)
    masters = [master] if isinstance(master, (str, Path)) else list(master)
    covers_from = "passed by the caller" if thumbs is not None or cover_records is not None else None
    if covers_from is None and to_file_on():
        thumbs, cover_records, where, note = studio_covers(masters, production)
        covers_from = where if thumbs is not None else note
    elif covers_from is None:
        covers_from = "not read (cover-rule.json to_file, META_FILE_MASTER_COVERS_OFF)"
    p = T.to_check(brand, "video", "flexible", masters, words, pages,
                   {"tool": "video-edit", "run": run_rel, "creator": None},
                   product=product, brief=brief, batch=N.norm_batch(batch), root=root,
                   dry_run=dry_run, replace=replace, thumbs=thumbs, cover_records=cover_records,
                   openings=openings)
    p["covers_from"] = covers_from
    return p, src


def from_run(folder, repo=REPO):
    """A video-edit run folder → (brand, brief, product, batch, master, handoff folder, run folder)."""
    folder = Path(folder).resolve()
    st = _read(folder / "status.json") or {}
    rj = _read(folder / "run.json") or {}
    brand = st.get("brand") or rj.get("brand")
    name = st.get("handoff")
    handoff = next((h / brand / name for h in HANDOFFS if name and (h / brand / name / "manifest.json").is_file()), None)
    if not handoff:
        raise T.Refused(f"{folder.name}: its hand-off ({name}) is not in this checkout")
    return from_handoff(handoff, run=folder, repo=repo)


def from_handoff(handoff, run=None, repo=REPO):
    handoff = Path(handoff).resolve()
    man = _read(handoff / "manifest.json") or {}
    if man.get("role") != "video-editor":
        raise T.Refused(f"{handoff.name} is not a video-editor hand-off")
    b = (man.get("briefs") or [{}])[0]
    brand, brief = man["brand"], b.get("id")
    pid = str(b.get("product_id") or "")
    product = pid.split("_", 2)[2] if pid.count("_") >= 2 else None
    returned = (_read(Path(run) / "run.json") or {}).get("steps", {}).get("returned") if run else None
    batch = (returned or {}).get("batch") or man.get("batch")
    master = None
    if returned and returned.get("file"):
        master = Path(returned["file"])
    elif run and (Path(run) / "work/final.mp4").is_file():
        master = Path(run) / "work/final.mp4"
    elif run:
        master = Path(run) / "work/final.mp4"          # not rendered yet — a dry run plans it anyway
    else:
        master = next(iter(sorted((handoff / "returned").glob("*.mp4"))), handoff / "returned/master.mp4")
    if not batch:
        batch = N.next_batch(brand)
    return brand, brief, product, batch, master, handoff, run


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", help="a video-edit run folder, or a video-editor hand-off folder")
    ap.add_argument("--links", nargs="*", default=[], help="catalog link ids, added to the hand-off's own")
    ap.add_argument("--batch", help="override the batch")
    ap.add_argument("--root", help="the meta/ folder (default $META_CARDS_ROOT or the Drive)")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--production", help="the Video Studio production whose cover hand-off (covers/to-file.json) to read")
    a = ap.parse_args()
    f = Path(a.folder)
    try:
        brand, brief, product, batch, master, handoff, run = (
            from_handoff(f) if (f / "manifest.json").is_file() else from_run(f))
        p, src = file_master(brand, brief, product, a.batch or batch, master, handoff=handoff, run=run,
                             links=a.links, root=a.root, dry_run=a.dry_run, replace=a.replace,
                             production=a.production)
    except (T.Refused, ValueError) as e:
        sys.exit(f"REFUSED  {e}")
    print(T.show(p, verbose=True))
    print(f"           words from: {src}")
    print(f"           covers from: {p.get('covers_from')}")
    print(f"           concept: {p['card'].get('concept') or 'none on the brief'} · openings: "
          + (", ".join(f"{o['asset']} {o.get('opening') or 'not known'}" for o in p["card"].get("openings") or []) or "none"))
    if a.dry_run:
        print(json.dumps(p["card"], indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
