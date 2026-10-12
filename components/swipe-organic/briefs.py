#!/usr/bin/env python3
"""The daily brief line — each avatar feed's best untouched post goes through
the teardown machine and comes back as a brief waiting for a yes or a no.

    python3 briefs.py [--per-feed 1] [--parallel 3] [--only <feed>] [--dry-run]

  PICK      per avatar feed (a feed whose brand has a brands/<brand>/ folder):
            entertainment lane first, never torn before, a video we can download.
            Ranked by how hard it was SENT, then how far it punched past the
            creator's following, then views. The reason is written on the card.
  TEAR      yt-dlp → tools/video-teardown/machine/run.py --brand <brand>
            --no-frames  (the full chain to the stage-5 brief, nothing generated)
  QUEUE     one record per brief in records/desk/briefs/<label>.json — the page's
            "Briefs to review" tab reads these; the verdict (yes / no) is the owner's
            and is only ever written by the page.

The machine assigns its own audience at stage 1b. The record keeps BOTH: whose
feed the video came from, and who the machine wrote the brief for.
"""
import argparse, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import desklib as D

WS = D.WS
sys.path.append(str(WS / "components" / "brandpath"))
import brandpath as BP  # noqa: E402  anything under brands/<brand>/
MACHINE = WS / "tools/video-teardown/machine"


def _vt_workdir():
    """video-teardown's working-folder module, loaded by file (SI-56)."""
    m = sys.modules.get("vt_workdir")
    if m is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "vt_workdir", D.HERE.parents[1] / "tools" / "video-teardown" / "machine" / "workdir.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["vt_workdir"] = m
        spec.loader.exec_module(m)
    return m

QUEUE = D.HERE / "records" / "desk" / "briefs"
MEDIA = D.HERE / "records" / "desk" / "media"


def product_for(brand, core):
    f = QUEUE.parent / "products.json"
    m = (json.loads(f.read_text()) if f.exists() else {}).get(brand) or {}
    return m.get(core) or m.get("_default")


def sub_stem(feed):
    """The sub-avatar's card file stem — the key the teardown machine knows it by."""
    if not feed.get("sub"):
        return None
    hits = list(BP.brand_path(feed["brand"], "core-avatars", feed["core"], "sub-avatars", root=WS / "brands")
                .glob(f"*{feed['sub']}.md"))
    return hits[0].stem if hits else None


# Where a post sits in the scroll is where our version enters the awareness
# ladder: entertainment is watched before any problem is on the mind; educational
# is watched once someone has gone looking. Level keys are the doctrine slice's.
LANE_AWARENESS = {"entertainment": "unaware", "educational": "problem-aware"}


def torn():
    return {json.loads(f.read_text()).get("item") for f in QUEUE.glob("*.json")} if QUEUE.exists() else set()


def pick(feed, n, done):
    cs = [c for c in D.cards(feed["id"])
          if c["key"] not in done and c["keep"] is not False
          and (c.get("lane") in (None, "entertainment"))
          and c["platform"] in ("tiktok", "instagram", "youtube")
          and (c["platform"] != "instagram" or "/reel" in c["url"] or "/p/" in c["url"])]
    # a share rate only means something on a post that actually travelled
    cs.sort(key=lambda c: ((c.get("views") or 0) >= 100_000, c.get("sent") or 0, c.get("punch") or 0,
                           c.get("views") or 0), reverse=True)
    out = []
    for c in cs[:n]:
        why = (f"sent {c['sent']} times per 1K views" if c.get("sent") else
               f"{c['punch']}× the creator's following" if c.get("punch") else
               f"{c.get('views') or 0:,} views")
        out.append((c, f"top untouched entertainment post in this feed — {why}"))
    return out


ROUTE = None   # set from --route in main()


def tear(job):
    feed, c, why = job
    label = re.sub(r"[^a-z0-9]+", "-", f"feed-{feed['sub'] or feed['core']}-{c['key'].split(':')[-1]}".lower()).strip("-")[:60]
    rec_f = QUEUE / f"{label}.json"
    rec = {"label": label, "item": c["key"], "feed": feed["id"], "brand": feed["brand"],
           "core": feed["core"], "sub": feed["sub"], "feed_title": feed["title"],
           "url": c["url"], "author": c["author"], "caption": c["caption"], "cover": c["cover"],
           "views": c.get("views"), "sent": c.get("sent"), "picked_why": why,
           "lane": c.get("lane"), "awareness": LANE_AWARENESS.get(c.get("lane") or "entertainment"),
           "product": product_for(feed["brand"], feed["core"]),
           "queued": D.now(), "status": "running", "verdict": None}
    rec_f.write_text(json.dumps(rec, indent=1))
    media = MEDIA / label
    media.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["yt-dlp", "-o", str(media / "video.%(ext)s"), "--no-playlist",
                        "-f", "mp4/best", c["url"]], capture_output=True, timeout=300)
        vids = [v for v in media.glob("video.*") if v.suffix.lower() in (".mp4", ".mov", ".m4v", ".webm", ".mkv")]
        if not vids:
            raise RuntimeError("the video would not download")
        with (media / "machine.log").open("w") as log:
            r = subprocess.run([sys.executable, str(MACHINE / "run.py"), str(vids[0]),
                                "--brand", feed["brand"], "--label", label, "--no-frames"]
                               + (["--route", ROUTE] if ROUTE else [])
                               + (["--product", rec["product"]] if rec["product"] else [])
                               # the video came from this person's own feed — declare it
                               + (["--for-avatar", feed["core"]] if feed.get("core") else [])
                               + (["--for-sub", sub_stem(feed)] if sub_stem(feed) else [])
                               + (["--for-awareness", rec["awareness"]]
                                  if feed.get("core") and rec.get("awareness") else []),
                               stdout=log, stderr=subprocess.STDOUT, cwd=str(MACHINE), timeout=2 * 3600)
        run_dir = _vt_workdir().run_dir(label, WS)
        ok = r.returncode == 0 and (run_dir / "brief-final.md").exists()
        rec.update(status="ready" if ok else "failed", finished=D.now(),
                   why_failed=None if ok else f"machine exit {r.returncode} — {(media / 'machine.log').read_text()[-300:]}")
    except Exception as e:
        rec.update(status="failed", finished=D.now(), why_failed=str(e)[:300])
    rec_f.write_text(json.dumps(rec, indent=1))
    print(f"  {label}: {rec['status']}", flush=True)
    return rec["status"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-feed", type=int, default=1)
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--only")
    ap.add_argument("--item", help="tear down this one post (its feed key), picked by hand on the page")
    ap.add_argument("--route", choices=["creator", "ai", "founder"],
                    help="the route he picked; without it the post is torn down and "
                         "writing waits for a route (the route lock)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    global ROUTE
    ROUTE = a.route
    QUEUE.mkdir(parents=True, exist_ok=True)
    done = torn()
    jobs = []
    for f in D.feeds():
        if not f.get("brand") or not BP.brand_root(f["brand"], root=WS / "brands").is_dir() \
                or (a.only and f["id"] != a.only):
            continue
        if a.item:
            jobs += [(f, c, "picked by hand on the page") for c in D.cards(f["id"]) if c["key"] == a.item][:1]
            continue
        for c, why in pick(f, a.per_feed, done):
            jobs.append((f, c, why))
    print(f"{len(jobs)} teardowns queued")
    for f, c, why in jobs:
        print(f"  {f['id']}: @{c['author']} — {why}")
    if a.dry_run or not jobs:
        return
    with ThreadPoolExecutor(max_workers=a.parallel) as pool:
        res = list(pool.map(tear, jobs))
    print(f"ready {res.count('ready')} · failed {res.count('failed')}")


if __name__ == "__main__":
    main()
