#!/usr/bin/env python3
"""feed_video — a finished video master into 1-check, as one card.

    feed_video.py <video-edit run folder | video-editor hand-off folder> [--links …] [--dry-run] [--root …]

The video editor (tools/video-edit/machine/handoff_run.py) calls `file_master()`
right after give_back() puts the master into the hand-off's returned/. Run by hand
it reads the run's status.json for its hand-off, and finds the master in the run
(`work/final.mp4`, else returned/); `--dry-run` plans a card for a run that has not
rendered yet, and writes nothing.

Writes `meta/<brand>/1-check/video/<ad name>/<ad name>_asset-01.mp4` + card.json.

Words: a `words.json` in the hand-off, else the brief's own copywriter runs
(card_words.for_brief — runs labelled with the brief's number or alias), else
empty lists (the card's check fails; the owner sees "no primary text · no headline").
Pages: the hand-off's link ids (briefs[].link_ids), plus any --links.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "components/naming"))
import names as N  # noqa: E402
import card_words as W  # noqa: E402
import to_check as T  # noqa: E402

HANDOFFS = [REPO / "lab/print-run/handoffs/video-editor", REPO / "runs/handoffs/video-editor"]


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


def file_master(brand, brief, product, batch, master, *, handoff=None, run=None, links=(),
                root=None, dry_run=False, replace=False, repo=REPO):
    """One finished master → one card. Returns (plan, words source)."""
    man = _read(Path(handoff) / "manifest.json") if handoff else None
    words, src = words_for(brand, brief, handoff, repo)
    pages = list(dict.fromkeys(list(links) + (handoff_links(man) if man else [])))
    run_rel = str(Path(run).resolve().relative_to(repo)) if run and Path(run).resolve().is_relative_to(repo) else (str(run) if run else None)
    p = T.to_check(brand, "video", "flexible", [master], words, pages,
                   {"tool": "video-edit", "run": run_rel, "creator": None},
                   product=product, brief=brief, batch=N.norm_batch(batch), root=root,
                   dry_run=dry_run, replace=replace)
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
    a = ap.parse_args()
    f = Path(a.folder)
    try:
        brand, brief, product, batch, master, handoff, run = (
            from_handoff(f) if (f / "manifest.json").is_file() else from_run(f))
        p, src = file_master(brand, brief, product, a.batch or batch, master, handoff=handoff, run=run,
                             links=a.links, root=a.root, dry_run=a.dry_run, replace=a.replace)
    except (T.Refused, ValueError) as e:
        sys.exit(f"REFUSED  {e}")
    print(T.show(p, verbose=True))
    print(f"           words from: {src}")
    if a.dry_run:
        print(json.dumps(p["card"], indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
