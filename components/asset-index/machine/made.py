#!/usr/bin/env python3
"""made.py — everything the AI tools have made for us, and whether it can be used again.

    made.py build [--brand B]                      read the runs and the element bank into the register (free)
    made.py pull                                   add the account's latest Higgsfield jobs to the register (free, read-only)
    made.py find --brand B [--kind K] "<words>"    what we already have that fits, best first
    made.py count [--brand B]

The register is runs/asset-index/_made/<brand>.jsonl, one row a file: what it shows, where it is, the job that made it, and
`reuse`: "any" (a place, a prop, a person, a silent shot, a picture), or "this ad" with the reason (the words spoken in it
belong to one script). Kept apart from the real footage index on purpose: an AI face is never offered as a real customer.

Before anything is paid: `close(brand, kind, words)` is what a door shows first. It never swaps anything in by itself.
Reads only; writes only under runs/asset-index/_made/. Any brand. Python 3.9, standard library.
"""
import argparse
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIC = (".png", ".jpg", ".jpeg", ".webp")
STOP = set("a an the of and or in on at to for with from by as is are was it its his her their he she they them this that "
           "one into onto over under up down out off not no same very real picture shot scene clip camera video exactly "
           "keep reference image frame phone".split())
SUBS = {"person": "casting", "place": "sets", "prop": "props"}


def repo():
    for d in [HERE, *HERE.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    raise FileNotFoundError("no workspace above " + str(HERE))


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ValueError):
        return default


def _rel(ws, p):
    """Repo-relative, or None: a path outside the workspace, or a file that is gone, is never a row."""
    p = Path(str(p))
    if not p.is_absolute():
        p = ws / p
    if "runs" in p.parts and not p.is_file():                                   # made on another machine: same place here
        i = p.parts.index("runs")
        p = ws.joinpath(*p.parts[i:])
    try:
        return str(p.relative_to(ws)) if p.is_file() else None
    except ValueError:
        return None


def words(text):
    out = []
    for w in re.findall(r"[a-z0-9']+", str(text or "").lower()):
        w = w.strip("'")
        for end in ("ing", "ed", "es", "s"):
            if len(w) > len(end) + 3 and w.endswith(end):
                w = w[:-len(end)]
                break
        if w and w not in STOP and len(w) > 1:
            out.append(w)
    return out


# ---- what we have ----

def gone(ws, brand):
    """People the brand has retired or never finished: never offered again, in a sheet or in a clip."""
    home = ws / "runs" / "ai-elements" / brand
    out = {str(p.get("person")) for p in (_load(home / "removal-list.json", {}) or {}).get("people") or []}
    out |= {str(r[1]) for r in (_load(home / "new-only.json", {}) or {}).get("extra_rows") or []
            if len(r) > 2 and r[0] == "people" and (r[2] or {}).get("group") == "old-core"}
    doc = (_load(ws / "runs" / "ai-elements" / "ELEMENTS-INDEX.json", {}) or {}).get("people") or {}
    return out | {str(e.get("id")) for e in doc.values() if e.get("brand") == brand and e.get("working") is False}


def elements(ws, brand):
    """The element bank: people, places, props (runs/ai-elements/ELEMENTS-INDEX.json)."""
    doc = _load(ws / "runs" / "ai-elements" / "ELEMENTS-INDEX.json", {}) or {}
    out = gone(ws, brand)
    for kind, key in (("person", "people"), ("place", "sets"), ("prop", "props")):
        for k, e in (doc.get(key) or {}).items():
            if not isinstance(e, dict) or e.get("brand") != brand or e.get("held") or (kind == "person" and e.get("id") in out):
                continue
            home = ws / str(e.get("folder") or "")
            files = [x for x in (_rel(ws, p) for p in e.get("pictures") or []) if x]
            for guess in ("sheets/headshot", "master", "plates/wide", "picture"):
                files += [x for x in (_rel(ws, home / (guess + ext)) for ext in PIC) if x]
            if not files:
                continue
            d = e.get("described") or {}
            what = " ".join(str(x) for x in (e.get("name"), e.get("what"), e.get("role"), d.get("words"), d.get("sex"), d.get("age"),
                                             d.get("ethnicity"), e.get("light"), e.get("time")) if x)
            yield {"id": "%s:%s" % (kind, e.get("id")), "brand": brand, "kind": kind, "what": what, "file": files[0], "reuse": "any",
                   "name": e.get("id")}


def clips(ws, brand):
    """Every clip a production run made and kept: its plan says what it shows and whether a line is spoken in it."""
    out, seen_files = gone(ws, brand), set()
    for plan in sorted((ws / "runs" / "video-production" / brand).rglob("clips/plan.json")):
        if any(x == "dry-run" or x.startswith("_") for x in plan.parts[len(ws.parts):]):
            continue
        calls, led = (_load(plan, {}) or {}).get("calls") or [], _load(plan.with_name("ledger.json"), {}) or {}
        board = {}
        for f in (plan.parents[1] / "storyboard.json", plan.parents[1] / "plan.json"):
            for s in (_load(f, {}) or {}).get("scenes") or []:
                if isinstance(s, dict) and s.get("id"):
                    board.setdefault(s["id"], s)
        for c in calls:
            row = led.get(c.get("id")) or {}
            f = next((x for x in (_rel(ws, p) for p in (row.get("file"), row.get("raw"), plan.parent / (str(c.get("clip") or c.get("id")) + ".mp4")) if p) if x), None)
            if not f or out & {str(x) for x in c.get("people") or []}:
                continue
            size = (ws / f).stat().st_size
            if size in seen_files:                                              # the same clip kept under two names
                continue
            seen_files.add(size)
            seen = [str(c.get("prompt") or "")[:500]]
            for sid in c.get("scenes") or []:
                s = board.get(sid) or {}
                seen += [str(s.get(k)) for k in ("shows", "picture", "visual", "action", "setting", "happens") if isinstance(s.get(k), str)]
            seen += [str(x) for x in c.get("people") or []] + [str(r.get("job") or "")[:80] for r in c.get("image_refs") or []]
            said = [x.get("text") for x in c.get("lines") or [] if x.get("text") and x.get("on_camera")]
            run = str(plan.parents[1].relative_to(ws / "runs" / "video-production"))
            yield {"id": "clip:%s/%s" % (run, c.get("id")), "brand": brand, "kind": "clip", "what": " ".join(x for x in seen if x)[:1200],
                   "file": f, "seconds": c.get("seconds"), "job": row.get("request_id"), "run": run, "model": row.get("model") or c.get("model"),
                   "reuse": "this ad" if said else "any", "why": ("a line is spoken in it: " + said[0][:80]) if said else None}


def pictures(ws, brand):
    """Pictures the image engine filed, with the words they were made from."""
    for f in sorted((ws / "runs" / "image-production" / brand).rglob("*.recipe.json")):
        r = _load(f, {}) or {}
        pic = next((x for x in (_rel(ws, f.with_name(f.name.replace(".recipe.json", e))) for e in PIC) if x), None)
        if pic:
            yield {"id": "picture:" + pic, "brand": brand, "kind": "picture", "file": pic, "reuse": "any",
                   "what": str(r.get("direction") or r.get("prompt") or r.get("purpose") or "")[:900], "model": r.get("model")}


def history(ws, brand):
    """The account's own jobs, kept as pulled, whose words name this brand's products or whose file a run of it holds."""
    f = ws / "runs" / "asset-index" / "_made" / "account.jsonl"
    names = {p.name.replace("-", " ") for p in (ws / "runs" / "ai-elements" / brand / "products").glob("*") if p.is_dir()} | {brand}
    if not f.is_file():
        return
    for line in f.read_text().splitlines():
        r = json.loads(line)
        if any(re.search(r"\b%s\b" % re.escape(n), r["what"], re.I) for n in names):
            yield dict(r, brand=brand, id="job:" + r["job"])


def build(brand, ws=None):
    ws = ws or repo()
    rows, jobs = {}, set()
    for src in (elements, clips, pictures, history):
        for r in src(ws, brand):
            if r.get("job") and r["job"] in jobs:
                continue
            jobs.add(r.get("job"))
            rows.setdefault(r["id"], {k: v for k, v in r.items() if v is not None})
    out = ws / "runs" / "asset-index" / "_made" / (brand + ".jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows.values()))
    return list(rows.values())


def pull(ws=None, ask=None):
    """The latest 100 pictures, clips and sounds of the signed-in account, appended once each. Read-only, no credits."""
    ws = ws or repo()
    f = ws / "runs" / "asset-index" / "_made" / "account.jsonl"
    f.parent.mkdir(parents=True, exist_ok=True)
    have = {json.loads(x)["job"] for x in f.read_text().splitlines()} if f.is_file() else set()

    def cli(kind):
        out = subprocess.run(["higgsfield", "generate", "list", "--json", "--" + kind, "--size", "100"], capture_output=True, text=True,
                             timeout=120, stdin=subprocess.DEVNULL).stdout
        return json.loads(out)
    new = 0
    with f.open("a") as w:
        for kind, name in (("image", "picture"), ("video", "clip"), ("audio", "sound")):
            for j in (ask or cli)(kind):
                p = j.get("params") or {}
                what = re.sub(r"\s+", " ", str(p.get("prompt") or p.get("text") or ""))[:1200]
                if j.get("status") != "completed" or j["id"] in have or not j.get("result_url") or not what:
                    continue
                talk = re.search(r"[\"“][^\"”]{12,}[\"”]", what) and kind == "video" and p.get("generate_audio") is not False
                have.add(j["id"])
                new += 1
                w.write(json.dumps({"job": j["id"], "kind": name, "what": what, "url": j["result_url"], "at": j.get("created_at"),
                                    "model": j.get("job_type"), "seconds": p.get("duration"), "reuse": "this ad" if talk else "any",
                                    "why": "words are spoken in it" if talk else None}, ensure_ascii=False) + "\n")
    return new


# ---- finding it again ----

def read(brand, ws=None):
    f = (ws or repo()) / "runs" / "asset-index" / "_made" / (brand + ".jsonl")
    return [json.loads(x) for x in f.read_text().splitlines()] if f.is_file() else []


def find(brand, text, kind=None, n=5, rows=None, reuse="any", ws=None):
    """Best first. `score` is the share of what was asked for that the row shows, rarer words counting more."""
    rows = read(brand, ws) if rows is None else rows
    rows = [r for r in rows if (not kind or r["kind"] == kind) and (not reuse or r.get("reuse") == reuse)]
    bags = [set(words(r["what"])) for r in rows]
    df = Counter(w for b in bags for w in b)
    want = set(words(text))
    if not want:
        return []
    w = {x: math.log(1 + (len(rows) + 1) / (1 + df[x])) for x in want}
    tot = sum(w.values()) or 1
    out = []
    for r, b in zip(rows, bags):
        hit = sum(w[x] for x in want & b) / tot
        if hit:
            out.append(dict(r, score=round(hit * (0.75 + 0.25 * min(1, len(want) / max(1, len(b)))), 3)))
    out.sort(key=lambda r: -r["score"])
    return out[:n]


def close(brand, kind, text, floor=0.5, n=3, rows=None, ws=None):
    """What a door shows before it pays for a new one."""
    return [r for r in find(brand, text, kind, n, rows, ws=ws) if r["score"] >= floor]


def brands(ws):
    return sorted(d.name for d in (ws / "runs" / "ai-elements").iterdir() if (d / "casting").is_dir())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["build", "pull", "find", "count"])
    ap.add_argument("text", nargs="?", default="")
    ap.add_argument("--brand")
    ap.add_argument("--kind")
    a = ap.parse_intermixed_args(argv)
    ws = repo()
    if a.cmd == "pull":
        print(json.dumps({"new": pull(ws)}))
    elif a.cmd == "find":
        print(json.dumps(find(a.brand, a.text, a.kind), indent=1, ensure_ascii=False))
    else:
        for b in [a.brand] if a.brand else brands(ws):
            rows = build(b, ws) if a.cmd == "build" else read(b, ws)
            print(json.dumps({"brand": b, "rows": len(rows), "kinds": Counter(r["kind"] for r in rows),
                              "reusable": sum(r["reuse"] == "any" for r in rows)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
