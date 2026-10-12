#!/usr/bin/env python3
"""Run every selected video that has not been briefed yet.

    python3 batch.py --dry-run          what would run, and roughly how long
    python3 batch.py                     three at a time
    python3 batch.py --workers 4         more, if the image API can take it
    python3 batch.py --creator mara-creator

    python3 batch.py --brand <b> --product <p> --to 3 <video> [<video> …]
    python3 batch.py --brand <b> --product <p> --to 3 --source <folder>
    python3 batch.py --answers answers.json    the owner's numbers → re-run each held run

Every batch — the picks or a list of swipes — ends with ONE PAGE of everything
waiting on the owner (runs/batches/<date>-<n>-<brand>/BATCH.html + .md): structure
changes and questions, missing swipe lines, swipe-match changes, blanks left
after research, checks that could not run — numbered, answered in
answers.json ({"<run>": "<numbers>|all"}). Nothing here decides for him
(2026-09-25, the owner: "at least batch 5 … the more we can batch, the more money
we can make").

Runs are independent — own folder, own outputs, own Doc — so they parallelise
cleanly. What is NOT independent is the shared timing file (now locked) and the
image API, which is the real ceiling: frames already fires six concurrent
requests inside a single run, so four runs is twenty-four in flight. Frames
falls back on its own (pro, then flash, then a still from the video), so
pushing the count trades picture quality for wall clock rather than breaking.

One video failing never stops the batch. It is recorded, named at the end with
the stage it died on, and every other video carries on.
"""
import argparse, datetime as dt, html, json, re, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C, library as L

RUNS = C.runs_root()
WS = HERE.parents[2]
OUT = WS / "runs" / "batches"
STAGE_OF = {"stage3": "3", "stage5": "5"}


SELECTED = "creators/SELECTED-2026-08-27.json"
lock = threading.Lock()


def briefed(vid):
    """Has this id already produced a brief?"""
    for d in C.runs_root().iterdir():
        f = d / "run.json"
        if not f.is_file():
            continue
        try:
            lab = (json.loads(f.read_text()).get("label") or "").upper()
        except Exception:
            continue
        if lab.startswith(vid.upper() + "-") and (d / "brief-final.md").is_file():
            return d.name
    return None


def slug_for(vid, name):
    clean = "".join(ch if ch.isalnum() or ch == " " else "" for ch in (name or ""))
    return f"{vid}-{'-'.join(clean.lower().split())[:40]}".strip("-")


def todo(brand, only_creator=None):
    """What the picking board says to brief.

    Reads PICKING.json — the file the live board writes when someone ticks a
    video. It used to read a separate selections file, so a pick made on the
    board never reached the runner and the two could disagree without saying
    so (2026-08-29). One file, one truth."""
    root = L.root()
    pick = json.loads((root / "creators/PICKING.json").read_text())
    out = []
    for h, c in pick["creators"].items():
        if only_creator and h != only_creator:
            continue
        # Deeper-pass finds live in their own list, and their ranks are the
        # N-ids. Reading only `posts` silently dropped every N pick — Creator H's
        # whole set is N-ids, so she would have briefed nothing.
        by = {p["rank"]: p for p in
              list(c.get("posts", [])) + list(c.get("deeper", []))}
        vids = []
        for sid in c.get("selected", []):
            p = by.get(sid)
            if not p:
                continue
            # An N pick was downloaded into the posts folder numbered 11+.
            want = sid if not sid.startswith("N") else f"{int(sid[1:]) + 10:02d}"
            d = next((x for x in (root / "creators" / h / "posts").iterdir()
                      if x.is_dir() and x.name.startswith(want + "-")), None)
            vids.append({"id": p["id"], "name": p.get("name", ""),
                         "video": str((d / "video.mp4").relative_to(root)) if d else None})
        c = {"creator": c["name"], "owes": c.get("owes", 5), "videos": vids}
        for i in c.get("videos", []):
            if briefed(i["id"]):
                continue
            v = root / i["video"]
            if not v.is_file():
                out.append({**i, "handle": h, "creator": c["creator"],
                            "owes": c["owes"], "video": None})
                continue
            out.append({**i, "handle": h, "creator": c["creator"],
                        "owes": c["owes"], "video": v})
    return out


def one(job, brand):
    if not job["video"]:
        return job["id"], "no video on the Drive", None
    cmd = ["python3", str(HERE / "run.py"), str(job["video"]),
           "--brand", brand, "--creator", job["handle"],
           "--label", slug_for(job["id"], job["name"]),
           "--video-count", str(job["owes"])]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERE))
    mins = (time.time() - t0) / 60
    tail = (r.stdout or "") + (r.stderr or "")
    if "through to the end" in tail:
        url = ""
        for line in tail.splitlines():
            if "Doc " in line and "http" in line:
                url = line.split("http", 1)[1]
                url = "http" + url.strip()
        with lock:
            print(f"  ✔ {job['id']:<9} {job['creator']:<8} {mins:4.1f} min"
                  f"{'  ' + url if url else ''}", flush=True)
        return job["id"], None, url
    stage = ""
    for line in tail.splitlines():
        if "stopped at" in line:
            stage = line.strip()
    with lock:
        print(f"  ✖ {job['id']:<9} {job['creator']:<8} {mins:4.1f} min  "
              f"{stage or 'failed'}", flush=True)
    return job["id"], stage or "failed", None


def label_of(video):
    return re.sub(r"[^a-z0-9]+", "-", Path(video).stem.lower()).strip("-")[:40]


def run_one(video, brand, product, to, label=None, frm=None, approve=None):
    cmd = [sys.executable, str(HERE / "run.py"), str(video), "--brand", brand, "--to", str(to),
           "--label", label or label_of(video)]
    if product:
        cmd += ["--product", product]
    if frm:
        cmd += ["--from", str(frm)]
    if approve:
        cmd += ["--approve-structure", approve]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd="/tmp")
    return r.returncode, (r.stdout + r.stderr)[-3000:]


def open_items(label):
    """Everything in one run that waits on the owner."""
    d = RUNS / label
    st = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else {}
    items = []
    for f, kind in (("STRUCTURE-CHECK.md", "structure"), ("SWIPE-MATCH.md", "swipe match")):
        p = d / f
        if p.exists():
            for line in p.read_text().splitlines():
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                if len(c) >= 3 and c[0] and c[0] not in ("#", "---") and not set(c[0]) <= set("-:"):
                    items.append({"kind": kind, "n": c[0], "what": " — ".join(x for x in c[1:] if x)[:400]})
    for stage in ("3-injection.md", "5-brief.md"):
        p = d / "stages" / stage
        if p.exists():
            for s in sorted(set(re.findall(r"\[(?:SLOT|UNFILLED)[^\]]*\]", p.read_text()))):
                items.append({"kind": "blank", "n": "—", "what": f"{stage.split('-')[0]}: {s}"})
    if st.get("missed_checks"):
        for c in st["missed_checks"].get("checks", []):
            items.append({"kind": "check could not run", "n": "—", "what": c})
    stages = st.get("stages", {})
    held = [k for k, v in stages.items() if v.get("status") in ("held", "error")]
    return {"label": label, "held_at": held, "items": items,
            "last_done": max((k for k, v in stages.items() if v.get("status") == "done"), default="—")}


def page(batch_dir, rows):
    md = [f"# Batch {batch_dir.name}", "",
          "Everything waiting on the owner, run by run. Answer in `answers.json` — "
          '`{"<run>": "<numbers>|all"}` — then `batch_swipes.py --answers answers.json`.', ""]
    h = [f"<title>Batch {html.escape(batch_dir.name)}</title><style>body{{font:15px/1.5 -apple-system,sans-serif;"
         "max-width:1000px;margin:0 auto;padding:24px 16px;background:#F5F4F0;color:#17191E}}.run{{background:#fff;"
         "border:1px solid #DFDDD6;border-radius:12px;padding:16px;margin:14px 0}}td{{border-bottom:1px solid #DFDDD6;"
         "padding:6px;vertical-align:top}}table{{border-collapse:collapse;width:100%}}.ok{{color:#15803D}}.hold{{color:#B42318}}</style>",
         f"<h1>Batch {html.escape(batch_dir.name)}</h1><p>Everything waiting on you, run by run. Reply with numbers per run.</p>"]
    for r in rows:
        state = "clean — nothing waiting" if not r["items"] else f"{len(r['items'])} waiting"
        md += [f"## {r['label']} — {state}", f"last step done: {r['last_done']} · held at: {', '.join(r['held_at']) or 'nothing'}", ""]
        h.append(f"<div class='run'><h2>{html.escape(r['label'])} <span class='{'ok' if not r['items'] else 'hold'}'>· {state}</span></h2>")
        if r["items"]:
            md += ["| # | Kind | What |", "|---|---|---|"] + [f"| {i['n']} | {i['kind']} | {i['what'].replace('|', '/')} |" for i in r["items"]]
            h.append("<table>" + "".join(f"<tr><td><b>{html.escape(i['n'])}</b></td><td>{html.escape(i['kind'])}</td>"
                                         f"<td>{html.escape(i['what'])}</td></tr>" for i in r["items"]) + "</table>")
        md.append("")
        h.append("</div>")
    (batch_dir / "BATCH.md").write_text("\n".join(md) + "\n")
    (batch_dir / "BATCH.html").write_text("\n".join(h))
    (batch_dir / "batch.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")


def swipes(a):
    """A list of swipes (or a folder, or the owner's answers) — the swipe batch."""
    if a.answers:
        bdir = Path(a.batch) if a.batch else max(OUT.iterdir(), key=lambda p: p.stat().st_mtime)
        meta = json.loads((bdir / "meta.json").read_text())
        ans = json.loads(Path(a.answers).read_text())
        for label, nums in ans.items():
            v = meta["videos"].get(label)
            if not v:
                print(f"  {label}: not in this batch"); continue
            held = open_items(label)["held_at"]
            frm = STAGE_OF.get(held[0]) if held else None
            code, _ = run_one(v, meta["brand"], meta.get("product"), meta["to"], label, frm=frm, approve=nums)
            print(f"  {label}: re-run from {frm or 'where it stopped'} with {nums} → exit {code}")
        page(bdir, [open_items(l) for l in meta["videos"]])
        print(f"  page: {bdir / 'BATCH.html'}")
        return 0
    vids = list(a.videos)
    if a.source:
        vids += sorted(str(p) for p in Path(a.source).expanduser().glob("*") if p.suffix.lower() in (".mp4", ".mov", ".m4v"))
    bdir = OUT / f"{dt.date.today().isoformat()}-{len(vids)}-{a.brand}"
    bdir.mkdir(parents=True, exist_ok=True)
    meta = {"brand": a.brand, "product": a.product, "to": a.to, "videos": {label_of(v): v for v in vids}}
    (bdir / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    rows = []
    for i, v in enumerate(vids, 1):
        label = label_of(v)
        print(f"  [{i}/{len(vids)}] {label} …", flush=True)
        run_one(v, a.brand, a.product, a.to, label)
        r = open_items(label)
        rows.append(r)
        print(f"      {'clean' if not r['items'] else str(len(r['items'])) + ' waiting'} · last done {r['last_done']}")
        page(bdir, rows)
    print(f"  page: {bdir / 'BATCH.html'}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Brief every selected video — or a list of swipes.")
    ap.add_argument("--brand", required="--answers" not in sys.argv,
                    help="which brand's picks to brief. Named every time — a "
                         "default here would quietly run one brand's videos "
                         "as another's (rule 4).")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--creator")
    ap.add_argument("--dry-run", dest="dry", action="store_true")
    ap.add_argument("videos", nargs="*", help="swipes to run (instead of the picking board)")
    ap.add_argument("--source", help="a folder of swipes to run")
    ap.add_argument("--product")
    ap.add_argument("--to", default="3", help="the step every swipe stops at")
    ap.add_argument("--answers", help="the owner's answers.json — re-run each held run with his numbers")
    ap.add_argument("--batch", help="the batch folder --answers applies to (default: the newest)")
    a = ap.parse_args()
    if a.videos or a.source or a.answers:
        return swipes(a)

    jobs = todo(a.brand, a.creator)
    if not jobs:
        print("  nothing left to brief")
        return 0

    per = 25  # minutes, measured across Mara's three
    print(f"\n  {len(jobs)} video(s) to brief, {a.workers} at a time")
    print(f"  roughly {len(jobs) * per / a.workers / 60:.1f} hours "
          f"(one at a time it would be {len(jobs) * per / 60:.1f})")
    missing = [j["id"] for j in jobs if not j["video"]]
    if missing:
        print(f"  {len(missing)} have no video on the Drive: {', '.join(missing[:6])}")
    by = {}
    for j in jobs:
        by.setdefault(j["creator"], []).append(j["id"])
    for k, v in by.items():
        print(f"     {k:<9} {', '.join(v)}")
    if a.dry:
        print("\n  dry run — nothing started")
        return 0

    print()
    fails = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for vid, err, _ in ex.map(lambda j: one(j, a.brand), jobs):
            if err:
                fails.append((vid, err))
    print(f"\n  {len(jobs) - len(fails)} briefed, {len(fails)} stopped short")
    for vid, err in fails:
        print(f"     {vid}: {err}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
