#!/usr/bin/env python3
"""
creator_queue.py — picked swipes in, one creator brief each out.

    python3 machine/creator_queue.py list --brand <brand>            what is picked and not yet briefed
    python3 machine/creator_queue.py next --brand <brand> [--dry-run] brief the oldest picked swipe
    python3 machine/creator_queue.py one  --brand <brand> --swipe <swipe_id> [--dry-run]

Station 2 of the creator system (2026-11-15). The swipe-pick station writes the
queue; this reads it and never writes it (one writer per file). What it has
briefed is its own ledger:

    reads   runs/swipe-organic/<brand>/creator-picks/picks.json   {"items": [{swipe_id, source_url, video, product?, …, state}]}
            waiting = state "picked" (tear it down, then write) or "torn" (the teardown
            already ran under label = swipe_id; write only). Progress is `state`;
            `status` keeps the rule-6 words.
    writes  runs/video-writing/<brand>/creator-briefs.json    {"briefed": {<swipe_id>: {brief, run, written}}}
            runs/video-writing/<brand>/<swipe_id>/brief--video--creator.md   (the brief; contract: components/briefs/creator-brief/README.md)
            runs/creator-machine/<brand>/hub/briefs.json      one draft entry per brief, append-only (delivery flips it)

One swipe per call, on purpose: a brief is a teardown plus a writing run, and
nothing here batches. Python 3.9, stdlib; the media is fetched with yt-dlp into
a temp folder only when the item names no local file, and the temp folder is
removed after the run copied it.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C            # noqa: E402
import workdir               # noqa: E402
import creator_brief as CB   # noqa: E402


def _safe(s):
    return re.sub(r"[^a-z0-9-]+", "-", str(s or "").lower()).strip("-")


def queue_path(brand):
    return C.workspace() / "runs" / "swipe-organic" / _safe(brand) / "creator-picks" / "picks.json"


def ledger_path(brand):
    return C.workspace() / "runs" / "video-writing" / _safe(brand) / "creator-briefs.json"


def items(brand):
    p = queue_path(brand)
    if not p.is_file():
        return []
    d = json.loads(p.read_text())
    rows = d.get("items") if isinstance(d, dict) else d
    return [r for r in rows or [] if isinstance(r, dict) and r.get("swipe_id")]


def ledger(brand):
    p = ledger_path(brand)
    return json.loads(p.read_text()) if p.is_file() else {"briefed": {}}


def waiting(brand):
    done = ledger(brand)["briefed"]
    return [r for r in items(brand)
            if str(r.get("state") or "") in ("picked", "torn") and r["swipe_id"] not in done]


def label_for(brand, item):
    """The teardown label IS the swipe id (the desk click and briefs.py use it too)."""
    return str(item["swipe_id"])


def torn_run(item):
    """A teardown that already ran for this pick, or None."""
    if str(item.get("state") or "") != "torn":
        return None
    t = item.get("teardown") or {}
    for cand in (t.get("run"), t.get("label"), item["swipe_id"]):
        if not cand:
            continue
        p = Path(str(cand))
        p = p if p.is_absolute() else C.workspace() / p
        if (p / "run.json").is_file():
            return p
        rd = workdir.run_dir(str(cand))
        if (rd / "run.json").is_file():
            return rd
    return None


def hub_add(brand, slug, rel, item=None):
    """One draft entry in the creator hub's briefs manifest — added once, never edited after.
    `winner` / `replaces` ride along only when the pick names them (delivery's five always-on briefs)."""
    p = C.workspace() / "runs" / "creator-machine" / _safe(brand) / "hub" / "briefs.json"
    d = json.loads(p.read_text()) if p.is_file() else {"briefs": []}
    if any(b.get("id") == slug for b in d.get("briefs") or []):
        return False
    d.setdefault("briefs", []).append({"id": slug, "page": rel, "status": "draft",
                                       "made": date.today().isoformat(),
                                       "made_by": "creator-brief-writing"})
    for k in ("winner", "replaces"):
        if (item or {}).get(k):
            d["briefs"][-1][k] = str(item[k])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    return True


def _media(item, tmp):
    v = str(item.get("video") or "")
    if v:
        p = Path(v)
        p = p if p.is_absolute() else C.workspace() / v
        if p.is_file():
            return p
    url = item.get("source_url")
    if not url:
        raise SystemExit(f"{item['swipe_id']}: no video file and no source_url")
    out = Path(tmp) / f"{_safe(item['swipe_id'])}.mp4"
    subprocess.run(["yt-dlp", "-q", "-f", "mp4/best", "-o", str(out), url], check=True)
    # run.py takes the swipe link from a post.json beside the video
    (Path(tmp) / "post.json").write_text(json.dumps({"url": url}))
    return out


def brief_one(brand, item, dry=False):
    label = label_for(brand, item)
    cmd = [sys.executable, str(HERE / "run.py"), "", "--brand", brand, "--route", "creator",
           "--label", label]
    if item.get("product"):
        cmd += ["--product", str(item["product"]), "--product-why", "set on the pick (the creator-picks queue)"]
    if item.get("avatar"):
        cmd += ["--for-avatar", str(item["avatar"])]
    if item.get("source_url"):
        cmd += ["--post-url", str(item["source_url"])]
    if item.get("why"):
        # why this swipe was picked travels into the run and onto its trail (logic layer W1, 2026-11-18)
        cmd += ["--picked-why", str(item["why"]),
                "--picked-by", str(item.get("picker") or item.get("picked_by") or "the picker")]
    if dry:
        cmd.append("--dry-run")
    torn = torn_run(item)
    tmp = tempfile.mkdtemp(prefix="creator-queue-")
    try:
        if torn is not None:
            # the teardown is paid for: write only, through the creator line
            label = torn.name
            cmd = [sys.executable, str(HERE / "line.py"), "creator", "--label", label, "--brand", brand]
            if item.get("product"):
                cmd += ["--product", str(item["product"])]
            if dry:
                cmd.append("--dry-run")
        else:
            cmd[2] = str(_media(item, tmp))
        print("▸", " ".join(cmd[1:]), flush=True)
        code = subprocess.call(cmd)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if dry or code != 0:
        return code, None
    rd = workdir.run_dir(label)
    st = json.loads((rd / "run.json").read_text())
    st["queue_item"] = {k: item.get(k) for k in ("swipe_id", "source_url", "views", "creator_handle",
                                                  "format", "picked") if item.get(k) is not None}
    (rd / "run.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
    out = CB.file(rd, st=st)                      # re-tagged with the queue item
    if out is None:
        print(f"{label}: the run stopped before the brief (see its board); not marked briefed")
        return 1, None
    import file_run                               # noqa: E402
    file_run.file_run(rd)
    rel = f"runs/video-writing/{_safe(brand)}/{_safe(st.get('slug') or label)}/{CB.NAME}"
    lp = ledger_path(brand)
    led = ledger(brand)
    led["briefed"][item["swipe_id"]] = {"brief": rel, "run": label, "written": date.today().isoformat()}
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(json.dumps(led, indent=1, ensure_ascii=False) + "\n")
    hub_add(brand, _safe(st.get("slug") or label), rel, item)
    print(f"brief: {rel}")
    return 0, rel


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("verb", choices=["list", "next", "one"])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--swipe")
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    a = ap.parse_args(argv)
    w = waiting(a.brand)
    if a.verb == "list":
        if not queue_path(a.brand).is_file():
            print(f"no queue yet: {queue_path(a.brand).relative_to(C.workspace())}")
        for r in w:
            print(f"{r['swipe_id']:<32} {r.get('views') or '':>10}  {r.get('source_url') or ''}")
        print(f"{len(w)} waiting")
        return 0
    if a.verb == "one":
        pick = [r for r in items(a.brand) if r["swipe_id"] == a.swipe]
        if not pick:
            sys.exit(f"no swipe '{a.swipe}' in {queue_path(a.brand)}")
    else:
        pick = sorted(w, key=lambda r: str(r.get("picked") or ""))[:1]
        if not pick:
            print("nothing waiting")
            return 0
    code, _ = brief_one(a.brand, pick[0], dry=a.dry)
    return code


if __name__ == "__main__":
    sys.exit(main())
