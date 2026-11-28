"""The workflow desk: every video workflow, start to approval page, from one page (Video Studio, /desk).

A piece is one workflow run (runs/video-production/<brand>/workflow-<label>/workflow-state.json, written by
components/video-production/machine/workflow.py). The desk shows each station of its line, what that station was told
to do (the station's instructions; for writing, every stage's prompt as sent), what it made, its check, and the price.
It calls the existing commands and re-implements none of them:

  start     drama_start.py preset -> video-writing scratch.py (no swipe), then workflow.py run
  move on   workflow.py run <format> --brand B --label L          (never --allow-paid: paid stations wait on the go)
  the go    drama_lane.py open <film> ... then workflow.py complete --station <quote station>  (Drama / Singing lane)
            workflow.py go <format> ... --approved-by --said --cap                           (a quote with a go record)

Nothing paid runs from here without the owner's go typed on the page: his name, his words, the cap.
Brand-agnostic; Python 3.9, standard library.
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs

HERE = Path(__file__).resolve().parent
WS = HERE.parents[1]                                   # the repo root (tests point it elsewhere)
PY = sys.executable
SAFE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*\Z")
TEXT = {".md", ".json", ".txt", ".log", ".tsv", ".jsonl", ".html"}
MEDIA = {".mp4": "video/mp4", ".mov": "video/quicktime", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".png": "image/png", ".webp": "image/webp", ".mp3": "audio/mpeg", ".wav": "audio/wav"}

# The lines offered to the owner. Every other playbook is parked (workflow.py list --parked).
LINES = [
    {"id": "micro-drama", "name": "Micro drama", "what": "Characters act and talk on screen: a conflict, a turn on "
     "the product, a visible ending.", "starts": ["swipe", "own", "winner"]},
    {"id": "song-ad", "name": "Song ad", "what": "A story told as a song, every line a shot.",
     "starts": ["swipe", "own", "winner"]},
]
STARTS = {"swipe": "From a swipe", "own": "Our own story", "winner": "Winner swipe"}

# Plain names for what each station's output is, shown on the page instead of file names.
PLAIN = {"run.json": "Run record", "REQUEST.md": "What the pack asks for", "pack.json": "The pack",
         "quote.json": "The price", "lane.json": "The go on file", "sheets.json": "Sheets", "script.json": "Script",
         "plan.json": "Plan", "checks.json": "Prompt checks", "setups.json": "Setups", "jobs.json": "Clips made",
         "takes.json": "Takes looked at", "edit.json": "The edit", "meta-filed.json": "Filed to approval",
         "5-brief.md": "The brief", "CONCEPT-BRIEF.md": "Concept brief", "story-preset.md": "Story preset"}

JOBS = {}
JLOCK = threading.Lock()


# ---------- reading the workflow definitions (the runner's own module, read-only) ----------

def _workflow_mod():
    path = WS / "components/video-production/machine/workflow.py"
    spec = importlib.util.spec_from_file_location("desk_workflow", path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(mod)
    return mod


_W = {}


def W():
    if "m" not in _W:
        _W["m"] = _workflow_mod()
    return _W["m"]


def steps_for(fmt, route="ai"):
    """The line's stations, in order, as its playbook declares them."""
    return W().workflow(fmt, production_route=route or "ai")["steps"]


def fill(text, values):
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), text or "")


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(WS.resolve()))
    except ValueError:
        return str(p)


def inside(ref, roots=("runs", "components", "brands")):
    """A path the desk may read: under the repo's runs, components or brands (runs/ and brands/ may be links to
    where the data lives), never with '..' and never absolute."""
    if not ref or "\0" in ref or os.path.isabs(ref) or ".." in Path(ref).parts:
        return None
    if Path(ref).parts[0] not in roots:
        return None
    return (WS / ref)


# ---------- pieces ----------

def state_path(brand, label):
    return WS / "runs/video-production" / brand / ("workflow-" + label) / "workflow-state.json"


def pieces():
    out = []
    for f in sorted(glob.glob(str(WS / "runs/video-production/*/workflow-*/workflow-state.json"))):
        s = _read(f) or {}
        v = s.get("values") or {}
        brand, label = v.get("brand") or Path(f).parent.parent.name, v.get("label") or Path(f).parent.name[9:]
        fmt = s.get("format")
        line = next((l for l in LINES if l["id"] == fmt), None)
        nxt = s.get("next") or {}
        out.append({"brand": brand, "label": label, "format": fmt, "line": line["name"] if line else None,
                    "live_line": bool(line), "state": s.get("state"), "waiting_on": s.get("waiting_on"),
                    "next": nxt.get("name"), "next_id": nxt.get("station"), "quote": bool(nxt.get("quote")),
                    "done": len(s.get("receipts") or {}), "updated": s.get("updated") or "",
                    "source": v.get("source") or ("own" if v.get("route") == "scratch" else None)})
    out.sort(key=lambda r: r["updated"], reverse=True)
    return out


def _files(pattern, values):
    ref = fill(pattern, values)
    if not ref or "{" in ref:
        words = re.sub(r"\{(\w+)\}", lambda m: m.group(1).replace("_", " "), _plain(ref))
        return [{"path": ref, "name": words, "missing": True, "gap": True}]
    hits = sorted(glob.glob(str(WS / ref)))
    if not hits:
        return [{"path": ref, "name": _plain(ref), "missing": True}]
    return [{"path": str(Path(h).relative_to(WS)), "name": _plain(h), "missing": False} for h in hits]


def _plain(p):
    name = Path(str(p)).name
    return PLAIN.get(name, name)


def writing_stages(run_dir, component=None):
    """Each writing stage with its prompt (the template), what was sent (filled) and what came out."""
    run = _read(WS / run_dir / "run.json") if run_dir else None
    if not isinstance(run, dict):
        return []
    out = []
    order = run.get("_order") or list((run.get("stages") or {}).keys())
    for key in order:
        st = (run.get("stages") or {}).get(key)
        if not isinstance(st, dict):
            continue
        def ref(name):
            v = st.get(name)
            if not v:
                return None
            r = v if v.startswith(("components/", "runs/")) else str(Path(run_dir) / v)
            if not (WS / r).exists() and component:
                r = str(Path(component) / v)
            if not (WS / r).exists():                    # a prompt renamed for its owner tag (…-v2-<who>.md)
                hit = sorted(glob.glob(str(WS / re.sub(r"-[a-z]+(\.md)$", r"-*\1", r))))
                r = str(Path(hit[0]).relative_to(WS)) if hit else r
            return r if (WS / r).exists() else None
        out.append({"id": key, "name": st.get("name") or key, "status": st.get("status"),
                    "why": st.get("why") or st.get("reason"), "prompt": ref("prompt_file"),
                    "prompt_name": st.get("prompt_name"), "sent": ref("sent"), "out": ref("out"),
                    "model": st.get("model"), "finished": st.get("finished"), "version": st.get("version"),
                    "engine": st.get("engine"), "seconds": st.get("seconds")})
    return out


def film_dir(steps, values):
    """The Higgsfield film folder, read from the line's pack station."""
    for s in steps:
        if s.get("done_when") and "runs/higgsfield/" in s["done_when"]:
            d = fill(str(Path(s["done_when"]).parent), values)
            return d if "{" not in d else None
    return None


def gallery(film):
    """Pictures and clips the film folder holds, by kind, newest first; capped so the page stays light."""
    if not film or not (WS / film).is_dir():
        return {}
    kinds = {"sheets": ["refs", "film/sheets", "casting*"], "clips": ["clips", "film/clips"],
             "covers": ["covers"], "versions": ["deliverable", "opening-variants"]}
    out = {}
    for kind, subs in kinds.items():
        found = []
        for sub in subs:
            for d in glob.glob(str(WS / film / sub)):
                for p in Path(d).rglob("*"):
                    if p.suffix.lower() in MEDIA and p.is_file() and "versions" not in p.parts[-3:-1]:
                        found.append(p)
        found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if found:
            out[kind] = [{"path": film + "/" + str(p.relative_to(WS / film)), "name": p.name,
                          "video": p.suffix.lower() in (".mp4", ".mov")} for p in found[:24]]
            out[kind + "_count"] = len(found)
    return out


def checks(film):
    out = []
    for f in sorted(glob.glob(str(WS / film / "checks" / "*.json"))) if film else []:
        out.append({"stage": Path(f).stem, "path": film + "/checks/" + Path(f).name, "passed": True})
    return out


def quote_of(film, step, values):
    """The price the owner is shown, read from the quote station's own evidence."""
    q = None
    qref = None
    for pat in (step or {}).get("evidence", []) + [((step or {}).get("go") or {}).get("quote", "")]:
        ref = fill(pat, values)
        if ref.endswith("quote.json") and "{" not in ref and (WS / ref).is_file():
            qref, q = ref, _read(WS / ref)
            break
    if not isinstance(q, dict):
        return {"ready": False, "path": qref}
    models = []
    for mid, m in (q.get("models") or {}).items():
        models.append({"id": mid, "credits": m.get("credits"), "resolution": m.get("resolution"),
                       "default": mid == q.get("clip_model")})
    lane = _read(WS / film / "lane.json") if film else None
    return {"ready": True, "path": qref, "total_credits": q.get("total_credits"), "total_usd": q.get("total_usd"),
            "clip_model": q.get("clip_model"), "models": models, "clips": q.get("clips"), "sheets": q.get("sheets"),
            "balance": q.get("balance") or q.get("balance_credits"), "lines": q.get("lines") or q.get("items"),
            "lane_open": isinstance(lane, dict) and lane.get("state") == "open",
            "lane": {k: lane.get(k) for k in ("state", "clip_model", "cap_credits", "approved_by", "approved",
                                              "approved_at")} if isinstance(lane, dict) else None}


def dry_next(fmt, brand, label):
    """Where the run truly stands: the runner's own read-only pass (workflow.py run --dry-run)."""
    try:
        r = subprocess.run([PY, str(WS / "components/video-production/machine/workflow.py"), "run", fmt,
                            "--brand", brand, "--label", label, "--dry-run"], cwd=str(WS),
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return {"error": str(e)}
    txt = r.stdout.strip()
    if txt.startswith("{"):
        try:
            return json.loads(txt)
        except ValueError:
            pass
    if "Workflow complete" in txt:
        return {"complete": True, "said": txt.splitlines()[-1]}
    return {"error": (r.stderr or txt).strip()[-600:]}


def piece(brand, label, live=True):
    sp = state_path(brand, label)
    s = _read(sp)
    if not isinstance(s, dict):
        return None
    v = dict(s.get("values") or {})
    fmt = s.get("format")
    try:
        steps = steps_for(fmt, v.get("production_route"))
    except Exception as e:  # noqa: BLE001 — a format the definitions no longer know is said, not crashed on
        return {"brand": brand, "label": label, "format": fmt, "error": "this line's stations could not be read: %s" % e}
    now = dry_next(fmt, brand, label) if live else {}
    next_id = now.get("station") or (s.get("next") or {}).get("station")
    if now.get("complete"):
        next_id = None
    receipts = s.get("receipts") or {}
    film = film_dir(steps, v)
    seen_next = False
    rows = []
    for i, st in enumerate(steps):
        if st["id"] == next_id:
            status, seen_next = "now", True
        elif not seen_next and (st["id"] in receipts or next_id is None and now.get("complete")):
            status = "done"
        elif not seen_next and next_id is None:
            status = "done" if st["id"] in receipts else "later"
        else:
            status = "later" if seen_next or st["id"] not in receipts else "done"
        evid = []
        for pat in ([st["done_when"]] if st.get("done_when") else []) + st.get("evidence", []):
            for f in _files(pat, v):
                if f not in evid:
                    evid.append(f)
        row = {"n": i + 1, "id": st["id"], "name": st["name"], "status": status,
               "who": {"command": "runs by itself", "decided": "decided by the system",
                       "review": "a person's review"}.get(st.get("executor"), "Claude does this"),
               "executor": st.get("executor", "agent"), "does": st.get("does", ""), "command": fill(st.get("run"), v) or None,
               "paid": bool(st.get("paid")), "quote": bool(st.get("quote")), "stops_for": st.get("stops_for"),
               "outputs": evid, "log": None}
        log = sp.parent / (st["id"] + ".log")
        if log.is_file():
            row["log"] = "runs/video-production/%s/workflow-%s/%s.log" % (brand, label, st["id"])
        if st["id"] in ("brief",) or st["id"].startswith("writ"):
            row["writing"] = writing_stages(v.get("writing_run") or ("runs/video-teardown/_work/" + v["teardown"]
                                                                        if v.get("teardown") else None))
        if st["id"] in ("swipe", "start"):
            row["writing"] = [w for w in writing_stages("runs/video-teardown/_work/" + v["teardown"])
                              if w["id"] < "stage3"] if v.get("teardown") else []
        if st.get("quote"):
            row["price"] = quote_of(film, st, v)
        rows.append(row)
    cur = next((r for r in rows if r["status"] == "now"), None)
    line = next((l for l in LINES if l["id"] == fmt), None)
    return {"brand": brand, "label": label, "format": fmt, "line": line["name"] if line else fmt,
            "live_line": bool(line), "values": v, "state": "complete" if now.get("complete") else s.get("state"),
            "waiting_on": s.get("waiting_on"), "reason": now.get("reason") or (s.get("next") or {}).get("reason"),
            "runner_error": now.get("error"), "stations": rows, "now": cur["id"] if cur else None,
            "film": film, "gallery": gallery(film), "checks": checks(film), "updated": s.get("updated"),
            "next_md": "runs/video-production/%s/workflow-%s/NEXT.md" % (brand, label)
            if (sp.parent / "NEXT.md").is_file() else None,
            "ask": ask_for(line["name"] if line else fmt, brand, label, cur),
            "jobs": [j for j in jobs_list() if j["piece"] == brand + "/" + label][:5]}


def ask_for(line, brand, label, cur):
    """The words to say to Claude when the next station is Claude's to do."""
    if not cur:
        return None
    if cur["quote"] and cur.get("price", {}).get("ready"):
        return None
    return "Carry on the %s workflow for %s, piece %s: %s." % (line.lower(), brand, label, cur["name"].lower())


# ---------- what a new piece starts from ----------

# ---------- brands that live in their own repositories ----------
# A brand can keep its folder in its own repository (it owns its data). Such repositories are listed, on this computer
# only, in ~/.prizm/brand-roots.json (a list of folders that each hold brands/<brand>/) or PRIZM_BRAND_ROOTS
# (folders separated by ":"). Nothing about them is written into this repository.

def brand_roots():
    roots = [r for r in os.environ.get("PRIZM_BRAND_ROOTS", "").split(":") if r]
    cfg = Path(os.path.expanduser("~/.prizm/brand-roots.json"))
    try:
        roots += [str(x) for x in json.loads(cfg.read_text())] if cfg.is_file() else []
    except (OSError, ValueError):
        pass
    return [Path(os.path.expanduser(r)) for r in roots if Path(os.path.expanduser(r), "brands").is_dir()]


def bdir(brand):
    """The brand's folder: this repository's brands/<brand>, else the first own-repository root that holds it."""
    here = WS / "brands" / brand
    if here.is_dir():
        return here
    for r in brand_roots():
        if (r / "brands" / brand).is_dir():
            return r / "brands" / brand
    return here


def brands():
    out = []
    dirs = sorted((WS / "brands").glob("*"))
    for r in brand_roots():
        dirs += [d for d in sorted((r / "brands").glob("*")) if d.is_dir() and not (WS / "brands" / d.name).exists()]
    for d in dirs:
        if not d.is_dir() or d.name.startswith(("_", ".")):
            continue
        av = sorted(p.name for p in (d / "core-avatars").glob("*") if p.is_dir() and not p.name.startswith((".", "_")))
        pr = sorted({p.stem if p.is_file() else p.name for p in (d / "products").glob("*")
                     if not p.name.startswith((".", "_")) and p.stem not in ("README", "DRIVE-INDEX")
                     and (p.is_dir() or p.suffix == ".md")})
        op = _read(d / "operations/brand.json")
        lab = op.get("label") if isinstance(op, dict) else None
        out.append({"id": d.name, "label": lab if lab and "<" not in lab else d.name,
                    "avatars": av, "products": pr, "winner": (d / "winner.json").is_file(),
                    "live": bool(glob.glob(str(WS / "runs/funnel-tracking" / d.name / "2*/warehouse.json")))})
    return out


_TD = {}


def teardowns(brand):
    """Swipes already torn down for this brand (a teardown is never made twice)."""
    out = []
    for f in glob.glob(str(WS / "runs/video-teardown/_work/*/run.json")):
        try:
            m = os.path.getmtime(f)
        except OSError:
            continue
        hit = _TD.get(f)
        if not hit or hit[0] != m:
            r = _read(f) or {}
            st = r.get("stages") or {}
            ok = (st.get("stage2") or {}).get("status") == "done" and (st.get("stage1") or {}).get("from") != "scratch"
            hit = (m, {"label": Path(f).parent.name, "brand": r.get("brand"), "ok": ok, "at": m,
                       "brief": (st.get("stage5") or {}).get("status") == "done"})
            _TD[f] = hit
        row = hit[1]
        if row["ok"] and row["brand"] == brand:
            out.append(row)
    out.sort(key=lambda r: r["at"], reverse=True)
    return out[:60]


def _swipe_row(label, r):
    d = "runs/video-teardown/_work/" + label
    st = r.get("stages") or {}
    aim = r.get("aim") if isinstance(r.get("aim"), dict) else {}
    names = r.get("names") if isinstance(r.get("names"), dict) else {}
    return {"label": label, "brand": r.get("brand"), "product": r.get("product"),
            "poster": d + "/" + r["poster"] if isinstance(r.get("poster"), str) and (WS / d / r["poster"]).is_file() else None,
            "video": d + "/" + r["source"] if isinstance(r.get("source"), str) and (WS / d / r["source"]).is_file() else None,
            "post_url": r.get("post_url") or (r.get("pick") or {}).get("post") if isinstance(r.get("pick"), dict) else r.get("post_url"),
            "lane": r.get("triage_lane"), "format": names.get("script_format") or r.get("format_id"),
            "avatar": aim.get("avatar"), "state": r.get("state"),
            "brief": (st.get("stage5") or {}).get("status") == "done",
            "done": sum(1 for v in st.values() if isinstance(v, dict) and v.get("status") == "done"),
            "stages": len(st)}


_SW = {}


def swipes(brand):
    """Every swipe torn down for a brand, newest first, with its cover: the Studio's swipe library."""
    out = []
    for f in glob.glob(str(WS / "runs/video-teardown/_work/*/run.json")):
        try:
            m = os.path.getmtime(f)
        except OSError:
            continue
        hit = _SW.get(f)
        if not hit or hit[0] != m:
            r = _read(f) or {}
            row = _swipe_row(Path(f).parent.name, r) if isinstance(r, dict) else None
            if row:
                row["at"] = m
                row["own"] = ((r.get("stages") or {}).get("stage1") or {}).get("from") == "scratch"
            hit = (m, row)
            _SW[f] = hit
        if hit[1] and hit[1]["brand"] == brand:
            out.append(hit[1])
    out.sort(key=lambda r: r["at"], reverse=True)
    return out[:200]


def swipe(label):
    """One teardown: the swipe, and every stage with its prompt, what was sent and what came out."""
    d = "runs/video-teardown/_work/" + label
    r = _read(WS / d / "run.json")
    if not isinstance(r, dict):
        return None
    row = _swipe_row(label, r)
    row["stages"] = writing_stages(d)
    return row


# ---------- the owner's morning: money, winners, research, brand setup (read-only) ----------

def _growth():
    """Revenue, spend and profit by day, from Outlier's money feed (it reads the warehouse; never Meta)."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:8880/api/growth", timeout=6) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 — the page says the feed is unreachable
        return None


def money():
    g = _growth()
    if not isinstance(g, dict):
        return {"ok": False, "why": "the money feed (Outlier) did not answer"}
    out = []
    for b, v in (g.get("brands") or {}).items():
        days = (v.get("daily") or [])[-7:]
        tot = {k: round(sum(d.get(k) or 0 for d in days), 2) for k in ("revenue", "spend", "profit", "orders", "new")}
        out.append({"brand": b, "label": v.get("label") or b, "days": days, "total": tot,
                    "last": days[-1]["d"] if days else None,
                    "roas": round(tot["revenue"] / tot["spend"], 2) if tot["spend"] else None})
    return {"ok": True, "built": g.get("built"), "brands": out}


def winners(brand, n=6):
    b = _read(WS / "runs/winners" / brand / "bank.json")
    rows = []
    for r in (b.get("rows") or []) if isinstance(b, dict) else []:
        snap = next((x for x in (r.get("snapshots") or []) if x.get("kind") == "audit"), None) or {}
        if not snap.get("purchases"):
            continue
        varied = bool(glob.glob(str(WS / "runs/ad-variations" / brand / ("p2f-" + r["id"] + "*"))))
        rows.append({"id": r["id"], "name": r.get("name"), "headline": r.get("headline"), "format": r.get("format"),
                     "purchases": snap.get("purchases"), "spend": snap.get("spend"), "cpa": snap.get("cpa"),
                     "roas": snap.get("roas"), "first": snap.get("first"), "last": snap.get("last"),
                     "pulled": snap.get("pulled_at"), "varied": varied})
    rows.sort(key=lambda x: x["purchases"] or 0, reverse=True)
    return rows[:n]


def research(brand):
    nxt = _read(WS / "runs/winners" / brand / "brief-next.json")
    rounds = []
    for d in sorted(glob.glob(str(WS / "runs/swipe-organic" / brand / "research-*")), key=os.path.getmtime, reverse=True)[:6]:
        w = _read(Path(d) / "worlds.json")
        rounds.append({"name": Path(d).name[len("research-"):], "at": os.path.getmtime(d),
                       "worlds": [{"world": x.get("world"), "count": x.get("count")} for x in (w or [])[:6]] if isinstance(w, list) else []})
    return {"next": {k: nxt.get(k) for k in ("made", "window", "videos_running", "angles", "hooks", "formats", "avoid", "tried", "bar")}
            if isinstance(nxt, dict) else None, "rounds": rounds}


def setup(brand):
    """The brand checklist (brands/_TEMPLATE/onboarding.json) with what this brand has done, skipped or filled."""
    t = _read(WS / "brands/_TEMPLATE/onboarding.json") or {}
    prog = _read(bdir(brand) / "onboarding-progress.json") or {}
    done, skipped = set(prog.get("done") or []), set(prog.get("skipped") or [])
    items = []
    for it in t.get("items") or []:
        fills = it.get("fills") or []
        paths = [f.split(" ")[0].rstrip(",") for f in fills]
        paths = [x for x in paths if x and not x.startswith("brands/")]
        have = [x for x in paths if glob.glob(str(bdir(brand) / re.sub(r"<[^>]+>", "*", x)))]
        fills = paths or fills
        state = "done" if it.get("id") in done else "skipped" if it.get("id") in skipped else (
            "filled" if fills and len(have) == len(fills) else "partial" if have else "todo")
        items.append({"id": it.get("id"), "group": it.get("group"), "name": it.get("name") or it.get("id"),
                      "why": it.get("why"), "required": it.get("required"), "when": it.get("when"),
                      "fills": fills, "have": have, "state": state})
    return {"brand": brand, "groups": t.get("groups"), "items": items, "progress": bool(prog)}


_SK = {}


def skills(brand):
    """Every skill this copy has: its job, where it came from (made here, the team's chain, or an outside collection),
    the engine it runs, and the brand's own taste file it reads (brands/<brand>/variables/), with whether this brand
    has filled it. Plus the outside collections the skills library indexes, counted by source."""
    stamps = _read(WS / "components/chain-mirror/stamps.json") or {}
    taste = {}
    for f in sorted((WS / "brands/_TEMPLATE/variables").glob("*.md")):
        if f.stem.lower() != "readme":
            mine = bdir(brand) / "variables" / f.name
            taste[f.stem] = {"file": "variables/" + f.name, "filled": mine.is_file() and mine.read_bytes() != f.read_bytes()}
    out = []
    for sk in sorted((WS / ".claude/skills").glob("*/SKILL.md")):
        m = os.path.getmtime(sk)
        hit = _SK.get(str(sk))
        if not hit or hit[0] != m:
            t = sk.read_text(errors="replace")
            desc = re.search(r"^description:\s*(.+)$", t, re.M)
            comp = re.search(r"Activates component:\*\*\s*`?(components/[\w./-]+)", t) or re.search(r"`(components/[\w-]+)", t)
            body = t
            if comp and (WS / comp.group(1).rstrip("/") / "CLAUDE.md").is_file():
                body += (WS / comp.group(1).rstrip("/") / "CLAUDE.md").read_text(errors="replace")
            reads = sorted(set(re.findall(r"variables/(copy|email|image|video)\.md", body)))
            d = (desc.group(1).strip() if desc else "")
            hit = (m, {"name": sk.parent.name, "job": re.split(r"(?<=[.!?])\s|\s—\s", d)[0][:180],
                       "component": comp.group(1).rstrip("/") if comp else None, "reads": reads})
            _SK[str(sk)] = hit
        row = dict(hit[1])
        rel = ".claude/skills/%s/SKILL.md" % row["name"]
        row["source"] = "team chain" if rel in stamps else "made here"
        row["taste"] = [dict(taste[r], kind=r) for r in row["reads"] if r in taste]
        out.append(row)
    cat = _read(WS / "skills-library/catalog.json") or []
    repos = {}
    for r in cat if isinstance(cat, list) else []:
        k = r.get("source") or "unknown"
        repos[k] = repos.get(k, 0) + 1
    return {"skills": out, "taste": taste,
            "collections": sorted(({"source": k, "skills": v} for k, v in repos.items()), key=lambda x: -x["skills"])}


def portfolio():
    """Every brand at a glance: money for the last 7 days and what waits on the approval page."""
    import urllib.request
    m = money()
    waiting = {}
    try:
        with urllib.request.urlopen("http://127.0.0.1:8795/api/cards?view=check", timeout=60) as r:
            for c in json.loads(r.read().decode("utf-8")).get("cards") or []:
                waiting[c.get("brand")] = waiting.get(c.get("brand"), 0) + 1
    except Exception:  # noqa: BLE001 — the page says the approval page did not answer
        waiting = None
    rows = []
    for b in brands():
        mb = next((x for x in m.get("brands", []) if x["brand"] == b["id"]), None) if m.get("ok") else None
        rows.append({"brand": b["id"], "money": mb, "now": live_ads(b["id"])["money"],
                     "waiting": None if waiting is None else waiting.get(b["id"], 0),
                     "swipes": len(swipes(b["id"])), "winners": len(winners(b["id"], 50))})
    return {"brands": rows, "money_ok": m.get("ok"), "approve_ok": waiting is not None}


def emails(brand):
    """The brand's email runs (runs/email-production/<brand>/<run>/run.json), newest first."""
    out = []
    for f in glob.glob(str(WS / "runs/email-production" / brand / "*/run.json")):
        r = _read(f) or {}
        d = Path(f).parent
        st = r.get("stages") or {}
        out.append({"label": d.name, "at": os.path.getmtime(f), "format": r.get("format"), "avatar": r.get("avatar"),
                    "done": sum(1 for v in st.values() if isinstance(v, dict) and v.get("status") == "done"),
                    "stages": len(st), "preview": (d / "deliverable/preview.html").is_file()})
    out.sort(key=lambda x: x["at"], reverse=True)
    return out[:120]


def email(brand, label):
    d = "runs/email-production/%s/%s" % (brand, label)
    r = _read(WS / d / "run.json")
    if not isinstance(r, dict):
        return None
    return {"label": label, "brand": brand, "format": r.get("format"), "avatar": r.get("avatar"),
            "preview": d + "/deliverable/preview.html" if (WS / d / "deliverable/preview.html").is_file() else None,
            "stages": writing_stages(d, "components/email-production")}


def creator_key(name):
    """A creator ad's creator, from its name (the part before the first `_`, e.g. `Sofiaand Stefan_FLEX…_trybe=…`)."""
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", re.split(r"_|\s+-\s+", name or "")[0]).strip()


def creators_live(brand):
    """Every creator whose ads spent in 30 days (ads tagged trybe=), with live numbers from the warehouse copy, their
    ads, their Trybe submissions and their profile when we keep one."""
    la = live_ads(brand)
    base = creators(brand)
    subs = (base.get("read") or {}).get("rows") or []
    prof = {p["handle"].lower(): p for p in base.get("profiles") or []}
    out = {}
    for a in la["ads"]:
        if not re.search(r"trybe=", a["name"] or "", re.I):
            continue
        k = creator_key(a["name"])
        g = out.setdefault(k, {"creator": k, "ads": [], "active": False})
        g["ads"].append(a)
        g["active"] = g["active"] or a["active"]
    rows = []
    for k, g in out.items():
        sm = lambda f: round(sum(a[f] for a in g["ads"]), 2)
        squash = re.sub(r"[^a-z]", "", k.lower())
        rows.append({"creator": k, "active": g["active"], "ads": g["ads"], "n": len(g["ads"]),
                     "spend7": sm("spend7"), "buys7": sm("buys7"), "spend30": sm("spend30"), "buys30": sm("buys30"),
                     "value30": sm("value30"),
                     "submissions": [x for x in subs if re.sub(r"[^a-z]", "", str(x.get("creator", "")).lower()) == squash],
                     "profile": prof.get(squash)})
    rows.sort(key=lambda r: -r["spend30"])
    return {"creators": rows, "through": (la.get("money") or {}).get("through"), "program": base.get("read"),
            "profiles": base.get("profiles")}


def creators(brand):
    """The brand's creators: the newest creator-program read (runs/winners/<brand>/creators/<date>/trybe.json) and the
    creators we keep a profile on (brands/<brand>/content-creators/<handle>/profile.md)."""
    reads = sorted(glob.glob(str(WS / "runs/winners" / brand / "creators/*/trybe.json")))
    t = _read(reads[-1]) if reads else None
    prof = []
    for d in sorted((bdir(brand) / "content-creators").glob("*/profile.md")):
        first = next((l.strip("# ").strip() for l in d.read_text(errors="replace").splitlines() if l.strip()), d.parent.name)
        prof.append({"handle": d.parent.name, "title": first, "path": str(d.relative_to(WS))})
    out = {"profiles": prof, "read": None}
    if isinstance(t, dict):
        out["read"] = {"made": t.get("made"), "from": t.get("from"), "to": t.get("to"), "creators": t.get("creators"),
                       "submissions": t.get("submissions"), "people": t.get("people") or [],
                       "rows": (t.get("rows") or [])[:60]}
    return out


_KN = {"m": None, "items": []}


def knowledge(q, limit=30):
    """Search daemn.co's knowledge (docs/knowledge/knowledge.json: every rule and lesson, with why and when)."""
    f = WS / "docs/knowledge/knowledge.json"
    try:
        m = os.path.getmtime(f)
    except OSError:
        return {"items": [], "total": 0}
    if _KN["m"] != m:
        k = _read(f) or {}
        _KN.update(m=m, items=k.get("items") or [])
    words = [w for w in re.findall(r"[a-z0-9]+", (q or "").lower()) if len(w) > 2]
    rows = []
    for it in _KN["items"]:
        hay = " ".join(str(it.get(x) or "") for x in ("title", "text", "why", "when", "kind")).lower()
        score = sum(hay.count(w) for w in words) if words else 1
        if score:
            rows.append((score, it))
    rows.sort(key=lambda x: -x[0])
    keep = ("kind", "title", "text", "why", "when", "source", "area", "topic")
    return {"total": len(_KN["items"]), "items": [{k: it.get(k) for k in keep if it.get(k)} for _, it in rows[:limit]]}


_GH = {"at": 0, "repos": None}


def github():
    """Repositories this computer's GitHub login can reach (its own and its organisations'), newest first; cached
    for an hour. Read-only."""
    import time
    if _GH["repos"] is not None and time.time() - _GH["at"] < 3600:
        return _GH["repos"]
    def gh(*a):
        r = subprocess.run(["gh", *a], capture_output=True, text=True, timeout=60)
        return r.stdout if r.returncode == 0 else ""
    owners = [""] + [o for o in gh("api", "user/orgs", "--jq", ".[].login").split() if o]
    repos = []
    for o in owners:
        txt = gh("repo", "list", *([o] if o else []), "--limit", "100", "--json", "name,owner,isPrivate,updatedAt,description")
        try:
            for r in json.loads(txt or "[]"):
                repos.append({"repo": r["owner"]["login"] + "/" + r["name"], "owner": r["owner"]["login"],
                              "private": r.get("isPrivate"), "updated": (r.get("updatedAt") or "")[:10],
                              "about": (r.get("description") or "")[:140]})
        except ValueError:
            pass
    repos.sort(key=lambda r: r["updated"], reverse=True)
    _GH.update(at=time.time(), repos={"repos": repos, "owners": [o for o in owners if o]})
    return _GH["repos"]


def _newest(pattern):
    hits = sorted(glob.glob(str(WS / pattern)))
    return hits[-1] if hits else None


def live_ads(brand):
    """Every ad that spent in the last 30 days, from the warehouse's daily copy (runs/funnel-tracking/<brand>/<date>/
    warehouse.json, never Meta), with the media-buying desk's own call on it (runs/media-buying/<brand>/<date>/
    report.json: off, keep, budget up …) and the brief its name carries."""
    wf = _newest("runs/funnel-tracking/%s/2*/warehouse.json" % brand)
    rf = _newest("runs/media-buying/%s/2*/report.json" % brand)
    w = _read(wf) if wf else None
    r = _read(rf) if rf else None
    calls = {str(f.get("id")): f for f in (r.get("flags") or [])} if isinstance(r, dict) else {}
    num = lambda v: float(v) if v not in (None, "") else 0.0
    rows = []
    for a in (w.get("ads") or []) if isinstance(w, dict) else []:
        c = calls.get(str(a.get("ad_id"))) or {}
        m = re.search(r"brief-(\d{4})", a.get("ad_name") or "")
        s7, b7, s30, b30 = num(a.get("spend7")), num(a.get("buys7")), num(a.get("spend30")), num(a.get("buys30"))
        s3 = num(a.get("spend3"))
        rows.append({"id": a.get("ad_id"), "name": a.get("ad_name"), "brief": m.group(1) if m else None,
                     "campaign": a.get("campaign"), "spend3": s3, "active": s3 > 0, "spend7": s7, "buys7": b7, "cpa7": round(s7 / b7, 2) if b7 else None,
                     "spend30": s30, "buys30": b30, "value30": num(a.get("value30")), "value7": num(a.get("value7")),
                     "roas7": round(num(a.get("value7")) / s7, 2) if s7 else None,
                     "cpa30": round(s30 / b30, 2) if b30 else None, "first_seen": a.get("first_seen"),
                     "call": c.get("action"), "why": c.get("why"), "break_even": c.get("break_even")})
    rows.sort(key=lambda x: -x["spend7"])
    money = None
    if isinstance(w, dict):
        o = w.get("orders") or {}
        money = {"through": w.get("spend_through"), "spend": w.get("spend") or {},
                 "revenue": {k: (v.get("blended") or {}).get("revenue") for k, v in o.items() if isinstance(v, dict)},
                 "orders": {k: (v.get("blended") or {}).get("orders") for k, v in o.items() if isinstance(v, dict)}}
    idx = _read(WS / "runs/meta-upload" / brand / "ADS-INDEX.json")
    briefs = {}
    for b in (idx.get("briefs") or []) if isinstance(idx, dict) else []:
        if b.get("number"):
            briefs[str(b["number"])] = {"angle": (b.get("angle") or "").replace("-", " "), "lanes": b.get("lanes") or [],
                                        "avatar": b.get("avatar"), "product": b.get("product")}
    return {"ads": rows, "money": money, "briefs": briefs, "calls_asof": r.get("asof") if isinstance(r, dict) else None,
            "rule": ((r or {}).get("rule") or {}).get("_what") if isinstance(r, dict) and isinstance(r.get("rule"), dict) else None,
            "from": str(Path(wf).relative_to(WS)) if wf else None}


def knowledge_server():
    """The knowledge service's address: PRIZM_KNOWLEDGE_URL, else the one the site's own knowledge page uses."""
    if os.environ.get("PRIZM_KNOWLEDGE_URL"):
        return os.environ["PRIZM_KNOWLEDGE_URL"].rstrip("/")
    try:
        m = re.search(r'const SERVER = "(https://[^"]+)"', (WS / "docs/knowledge/index.html").read_text())
        return m.group(1) if m else None
    except OSError:
        return None


def knowledge_ask(h, data):
    """Pass one question to the knowledge service and stream its answer (event: sources, then text) back as it
    comes. The service only answers its own site's address, so the Studio asks on the page's behalf."""
    import urllib.request
    q = str(data.get("q") or "").strip()[:1000]
    if not q:
        return h.send(400, {"error": "ask a question"})
    hist = [{"q": str(t.get("q", ""))[:1000], "a": str(t.get("a", ""))[:4000]} for t in (data.get("history") or [])[-4:]
            if isinstance(t, dict)]
    server = knowledge_server()
    if not server:
        return h.send(503, {"error": "no knowledge service is set up for this copy"})
    req = urllib.request.Request(server + "/ask", method="POST",
                                 data=json.dumps({"q": q, "stream": True, "history": hist}).encode(),
                                 headers={"Content-Type": "application/json", "Origin": "https://daemn.co",
                                          "User-Agent": "Mozilla/5.0 (Prizm Studio)"})
    try:
        r = urllib.request.urlopen(req, timeout=120)
    except Exception as e:  # noqa: BLE001 — said on the page
        return h.send(502, {"error": "the knowledge service did not answer: %s" % e})
    h.send_response(200)
    h.send_header("Content-Type", "text/event-stream")
    h.send_header("Cache-Control", "no-cache")
    h.end_headers()
    try:
        while True:
            chunk = r.read1(4096) if hasattr(r, "read1") else r.read(4096)
            if not chunk:
                break
            h.wfile.write(chunk)
            h.wfile.flush()
    except (BrokenPipeError, ConnectionResetError):
        pass
    return None


def brief_view(brand, number):
    """One brief as it went out: every batch's own files (served by the approval page), where each ad goes, and the
    live numbers of every ad that carries the brief number."""
    idx = _read(WS / "runs/meta-upload" / brand / "ADS-INDEX.json")
    b = next((x for x in (idx.get("briefs") or []) if str(x.get("number")) == str(number)), None) if isinstance(idx, dict) else None
    la = live_ads(brand)
    ads = [a for a in la["ads"] if a["brief"] == str(number)]
    if not b and not ads:
        return None
    cards = []
    for c in (b or {}).get("cards") or []:
        folder = (c.get("folder") or "").replace("Shared Assets/meta/", "", 1).strip("/")
        media = []
        for f in c.get("files") or []:
            name = f.get("asset") or ""
            if not name or not folder:
                continue
            kind = "video" if name.lower().endswith((".mp4", ".mov")) else "image"
            media.append({"name": name, "kind": kind, "src": "/media/%s/%s" % (folder, name), "thumb": "/thumb/%s/%s" % (folder, name)})
        cards.append({"ad_name": c.get("ad_name"), "state": c.get("state"), "lane": c.get("lane"), "format": c.get("format"),
                      "made": c.get("made"), "live": c.get("live"), "media": media,
                      "goes": [{"ad_id": m.get("ad_id"), "name": m.get("meta_ad_name"), "ad_set": m.get("ad_set"),
                                "campaign": m.get("campaign")} for m in c.get("meta_ads") or []]})
    keep = ("product", "avatar", "sub_avatar", "angle", "lanes", "state", "first_made", "last_change")
    return {"number": str(number), "brief": {k: (b or {}).get(k) for k in keep}, "cards": cards, "ads": ads,
            "rule": la.get("rule"), "through": (la.get("money") or {}).get("through")}


def pages(brand):
    """The brand's landing pages: its funnels (brands/<brand>/web/funnels/funnels.json) and, for every page a live ad
    points at (the last part of a briefed ad's name), that page's numbers from the warehouse copy."""
    f = _read(bdir(brand) / "web/funnels/funnels.json")
    funnels = []
    for x in (f.get("funnels") or []) if isinstance(f, dict) else []:
        funnels.append({"id": x.get("id"), "name": (x.get("name") or x.get("id") or "").split(" — ")[0],
                        "status": x.get("status"), "url": x.get("url"), "product": x.get("product"),
                        "pages": len(x.get("page_ids") or x.get("pages") or [])})
    by = {}
    for a in live_ads(brand)["ads"]:
        m = re.search(r"_batch-[^_]+_(.+)$", a["name"] or "")
        if not m:
            continue
        g = by.setdefault(m.group(1), {"page": m.group(1), "ads": 0, "briefs": set(), "spend7": 0.0, "buys7": 0.0,
                                       "spend30": 0.0, "buys30": 0.0, "value30": 0.0, "active": False})
        g["ads"] += 1
        g["active"] = g["active"] or a["active"]
        if a["brief"]:
            g["briefs"].add(a["brief"])
        for k in ("spend7", "buys7", "spend30", "buys30", "value30"):
            g[k] += a[k]
    rows = []
    for g in by.values():
        g["briefs"] = sorted(g["briefs"])
        rows.append(g)
    rows.sort(key=lambda g: -g["spend30"])
    return {"funnels": funnels, "pages": rows}


def hidden(brand):
    h = _read(WS / "runs/studio-asks" / brand / "hidden.json")
    return h if isinstance(h, list) else []


def hide(brand, item, on=True):
    """The owner's "Done, hide it" on a production row: kept in the Studio's own list, nothing else is touched."""
    if not SAFE.match(brand or "") or not item or len(item) > 300:
        raise ValueError("bad item")
    h = [x for x in hidden(brand) if x != item] + ([item] if on else [])
    p = WS / "runs/studio-asks" / brand / "hidden.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(h, indent=1))
    return {"hidden": h}


def market(brand):
    """Products winning and growing in the market, from the product tracker's newest read for this brand
    (runs/product-tracker/<brand>/<run>/list.json: Kalodata for TikTok Shop, TrendTrack for stores), newest first."""
    runs = sorted(glob.glob(str(WS / "runs/product-tracker/*/*/list.json")), key=os.path.getmtime, reverse=True)  # every scan: the market is not one brand's
    out = {"reads": [], "products": []}
    seen = set()
    for f in runs:
        l = _read(f) or {}
        out["reads"].append({"run": Path(f).parent.name, "question": l.get("question"), "ran_at": l.get("ran_at"),
                             "credits": l.get("credits_spent")})
        for src, blk in (l.get("sources") or {}).items():
            ps = (blk or {}).get("products") or {}
            for p in (ps.values() if isinstance(ps, dict) else ps):
                if not isinstance(p, dict) or p.get("key") in seen:
                    continue
                seen.add(p.get("key"))
                t = p.get("totals") or {}
                m30 = t.get("30") if t else p.get("month")
                prior = (t.get("60") or 0) - (t.get("30") or 0) if t else None
                wk = [w[2] for w in (p.get("weeks") or []) if isinstance(w, list) and len(w) > 2 and isinstance(w[2], (int, float))]
                if not t and len(wk) >= 8 and sum(wk[-8:-4]):
                    prior, m30 = sum(wk[-8:-4]), m30          # store products: the last 4 weeks against the 4 before
                    p = dict(p, _growth=round((sum(wk[-4:]) / sum(wk[-8:-4]) - 1) * 100))
                out["products"].append({"key": p.get("key"), "source": src, "name": p.get("name"), "shop": p.get("shop"),
                                        "price": p.get("price"), "where": p.get("money_is"), "month": m30,
                                        "growth": p.get("_growth") if "_growth" in p else (round((m30 / prior - 1) * 100) if prior and m30 else None),
                                        "week": t.get("7"), "units": p.get("units"), "for": p.get("for"),
                                        "launched": (p.get("launched") or "")[:10], "picture": p.get("picture"),
                                        "category": p.get("category") or p.get("for") or None,
                                        "link": p.get("link"), "pushers": p.get("pushers"), "run": Path(f).parent.name})
    out["products"].sort(key=lambda x: -(x["month"] or 0))
    return out


def pricing():
    """The owner's prices, kept on this computer only (~/.prizm/pricing.json), never in this repository."""
    p = _read(Path(os.path.expanduser("~/.prizm/pricing.json")))
    return p if isinstance(p, dict) else None


def bill(brand):
    """This brand's bill at the owner's prices, estimated from the last 30 days: retainer + the spend tier's % of ad
    spend (warehouse) + metered usage × (1 + surcharge)."""
    import studio_asks as SA
    pr = pricing()
    if not pr:
        return {"ok": False, "why": "no prices set on this computer"}
    spend = float(((live_ads(brand).get("money") or {}).get("spend") or {}).get("30") or 0)
    pct = next((t["pct"] for t in pr.get("spend_tiers") or [] if t.get("up_to") is None or spend <= t["up_to"]), 0)
    u = SA.usage(brand)
    month = datetime_now_month()
    used = next((m["cost"] for m in u["by_month"] if m["key"] == month), 0.0)
    sur = pr.get("usage_surcharge_pct") or 0
    lines = [{"what": "Retainer", "amount": pr.get("retainer_monthly") or 0},
             {"what": "%d%% of ad spend (last 30 days: $%s)" % (pct, format(round(spend), ",")), "amount": round(spend * pct / 100, 2)},
             {"what": "Usage this month at cost + %d%% (cost $%.2f)" % (sur, used), "amount": round(used * (1 + sur / 100), 2)}]
    return {"ok": True, "lines": lines, "total": round(sum(l["amount"] for l in lines), 2), "spend30": spend, "pct": pct,
            "cost": round(used, 2), "margin_on_usage": round(used * sur / 100, 2), "set": pr.get("set")}


def datetime_now_month():
    import datetime
    return datetime.date.today().isoformat()[:7]


# ---------- brands joining: the five onboarding steps, checked where they can be ----------
# Client details stay on this computer (~/.prizm/joining.json), never in this repository. Per-brand APIs and partner
# integrations (Meta, Shopify, reviews, Drive) live in Portal Commerce; this only tracks the steps.

JOIN_STEPS = [("repo", "They make their own repo"), ("invite", "They invite us"), ("folder", "Their Claude fills the brand folder"),
              ("asked", "We send what's missing"), ("first", "First run: top ads → teardowns")]


def _joinfile():
    return Path(os.path.expanduser(os.environ.get("PRIZM_JOINING") or "~/.prizm/joining.json"))


def joining_raw():
    j = _read(_joinfile())
    return j if isinstance(j, list) else []


_GHV = {}


def _gh_view(repo):
    """(exists, our permission) for owner/name, read-only, cached ten minutes."""
    import time
    hit = _GHV.get(repo)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    try:
        r = subprocess.run(["gh", "repo", "view", repo, "--json", "name,viewerPermission"], capture_output=True, text=True, timeout=30)
        v = (True, json.loads(r.stdout).get("viewerPermission")) if r.returncode == 0 else (False, None)
    except (OSError, subprocess.SubprocessError, ValueError):
        v = (False, None)
    _GHV[repo] = (time.time(), v)
    return v


def joining():
    out = []
    for j in joining_raw():
        done = dict(j.get("done") or {})
        st = {k: ("done" if done.get(k) else "todo") for k, _ in JOIN_STEPS}
        notes = {}
        if j.get("repo"):
            seen, perm = _gh_view(j["repo"])
            if seen:
                st["repo"] = "done"
                notes["repo"] = j["repo"]
                if perm in ("ADMIN", "MAINTAIN", "WRITE"):
                    st["invite"] = "done"
                notes["invite"] = (perm or "").lower() or None
        bid = j.get("brand")
        if bid and SAFE.match(bid) and bdir(bid).is_dir():
            items = setup(bid)["items"]
            ok = sum(1 for i in items if i["state"] in ("done", "filled", "skipped"))
            notes["folder"] = "%d of %d" % (ok, len(items))
            if ok >= len(items) - 3:
                st["folder"] = "done"
            elif ok:
                st["folder"] = "partly"
            if glob.glob(str(WS / "runs/video-teardown/_work" / (bid + "*"))):
                st["first"] = "done"
        cur = next((k for k, _ in JOIN_STEPS if st[k] != "done"), None)
        out.append({"name": j.get("name"), "repo": j.get("repo"), "brand": bid, "contact": j.get("contact"),
                    "added": j.get("added"), "steps": [{"id": k, "name": n, "state": st[k], "note": notes.get(k)} for k, n in JOIN_STEPS],
                    "now": cur, "ask": j.get("ask")})
    return {"brands": out}


def join_update(data):
    import datetime
    name = str(data.get("name") or "").strip()
    if not name or len(name) > 80:
        raise ValueError("give the brand's name")
    repo = str(data.get("repo") or "").strip() or None
    if repo and not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise ValueError("their repo as owner/name")
    brand = str(data.get("brand") or "").strip() or None
    if brand and not SAFE.match(brand):
        raise ValueError("bad brand id")
    rows = joining_raw()
    row = next((r for r in rows if r.get("name", "").lower() == name.lower()), None)
    if not row:
        row = {"name": name, "added": datetime.date.today().isoformat(), "done": {}}
        rows.append(row)
    for k in ("repo", "brand", "contact", "ask"):
        if data.get(k) is not None:
            row[k] = (str(data[k]).strip() or None) if k != "repo" else repo
    if data.get("step") in dict(JOIN_STEPS):
        row.setdefault("done", {})[data["step"]] = datetime.date.today().isoformat() if data.get("done", True) else None
    if data.get("remove"):
        rows = [r for r in rows if r is not row]
    f = _joinfile()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rows, indent=1))
    _GHV.pop(repo, None)
    return joining()


def ad_off(data):
    """The owner's Turn off on one ad: handed to Outlier's own pause (127.0.0.1:8880/api/ads/off), which checks the
    Meta ad's name before pausing it and logs the press. One Meta call per press; the Studio never calls Meta itself."""
    import urllib.request
    body = {"brand": data.get("brand"), "ad": data.get("ad"), "ids": data.get("ids") or [], "spend": data.get("spend"),
            "note": "Turn off in the Studio, confirmed"}
    if not SAFE.match(str(body["brand"] or "")) or not body["ad"] or not body["ids"]:
        raise ValueError("which ad?")
    req = urllib.request.Request("http://127.0.0.1:8880/api/ads/off", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 — said on the page
        raise RuntimeError("Outlier did not turn it off: %s" % e)


# ---------- Sauce: the owner's own pass over the spiced script ----------

def _section(text, title):
    m = re.search(r"^##\s*\d*\.?\s*" + re.escape(title) + r".*?$(.*?)(?=^##\s|\Z)", text or "", re.M | re.S | re.I)
    return m.group(1).strip() if m else ""


def sauce_list(brand):
    """Every script of this brand that has been through spice, newest first, and whether it has its sauce yet."""
    out = []
    for f in glob.glob(str(WS / "runs/video-teardown/_work/*/stages/4g-spice.md")):
        d = Path(f).parent.parent
        r = _read(d / "run.json") or {}
        if r.get("brand") != brand:
            continue
        out.append({"label": d.name, "at": os.path.getmtime(f), "poster": "runs/video-teardown/_work/%s/poster.jpg" % d.name
                    if (d / "poster.jpg").is_file() else None, "sauce": (d / "stages/4h-sauce.md").is_file(),
                    "sauced_at": os.path.getmtime(d / "stages/4h-sauce.md") if (d / "stages/4h-sauce.md").is_file() else None})
    out.sort(key=lambda x: (x["sauce"], -x["at"]))
    return {"scripts": out}


def sauce_get(label):
    d = WS / "runs/video-teardown/_work" / label
    sp = d / "stages/4g-spice.md"
    if not sp.is_file():
        return None
    spice = sp.read_text(errors="replace")
    sauce = (d / "stages/4h-sauce.md").read_text(errors="replace") if (d / "stages/4h-sauce.md").is_file() else None
    return {"label": label, "spice": spice, "script": _section(spice, "THE SPOKEN SCRIPT") or spice,
            "sheet": _section(spice, "THE SPICE SHEET"), "sauce": sauce,
            "poster": "runs/video-teardown/_work/%s/poster.jpg" % label if (d / "poster.jpg").is_file() else None}


def sauce_save(label, text, by=None):
    """The owner's sauce, saved beside the spice as stages/4h-sauce.md (the spice is never changed)."""
    import datetime
    d = WS / "runs/video-teardown/_work" / label
    if not SAFE.match(label or "") or not (d / "stages/4g-spice.md").is_file():
        raise ValueError("no spiced script with that name")
    text = (text or "").strip()
    if not text:
        raise ValueError("nothing written")
    (d / "stages/4h-sauce.md").write_text(text + "\n")
    (d / "stages/4h-sauce.json").write_text(json.dumps({"at": datetime.datetime.now().isoformat(timespec="seconds"),
                                                        "by": by or "owner", "chars": len(text), "from": "stages/4g-spice.md"}, indent=1))
    return {"ok": True, "path": "runs/video-teardown/_work/%s/stages/4h-sauce.md" % label}


def vary_candidates(la, n=6):
    """New ads worth varying: groups that carry a brief number or a creator (trybe) tag, that sold in the last 30 days
    and are under the desk's break-even (or that the desk says to keep or scale). Ranked by purchases."""
    groups = {}
    for a in la["ads"]:
        if a["brief"]:
            k = ("brief", a["brief"])
        elif re.search(r"trybe=", a["name"] or "", re.I):
            k = ("creator", re.split(r"_|\s+-\s+", a["name"])[0])
        else:
            continue
        groups.setdefault(k, []).append(a)
    out = []
    for (kind, key), rs in groups.items():
        s30, b30 = sum(r["spend30"] for r in rs), sum(r["buys30"] for r in rs)
        s7, b7 = sum(r["spend7"] for r in rs), sum(r["buys7"] for r in rs)
        if b30 < 2:
            continue
        be = max([r["break_even"] for r in rs if r.get("break_even")] or [0]) or None
        calls = {r["call"] for r in rs if r.get("call")}
        cpa30 = s30 / b30
        if not ((be and cpa30 <= be) or calls & {"keep", "budget_up", "double_down", "pull_up"}):
            continue
        brief = (la.get("briefs") or {}).get(key) if kind == "brief" else None
        out.append({"kind": kind, "key": key, "label": (brief or {}).get("angle") or "", "ads": len(rs),
                    "buys30": b30, "spend30": round(s30, 2), "cpa30": round(cpa30, 2), "value30": round(sum(r["value30"] for r in rs), 2),
                    "buys7": b7, "cpa7": round(s7 / b7, 2) if b7 else None, "break_even": be, "calls": sorted(calls),
                    "lanes": (brief or {}).get("lanes") or [], "example": rs[0]["name"]})
    out.sort(key=lambda x: (-x["buys30"], x["cpa30"]))
    return out[:n]


def _targets(brand):
    """The owner's lines for one brand, kept on this computer only (~/.prizm/targets.json or PRIZM_TARGETS):
    {"<brand>": {"mer": 2.5, "up": 0.10, "down": 0.05, "ceiling": 0, "bands": [1.15, 1.35]}}. Missing values stay
    drafts so the page can say so."""
    p = Path(os.environ.get("PRIZM_TARGETS") or Path.home() / ".prizm/targets.json")
    t = (_read(p) or {}).get(brand) if p.exists() else None
    t = t if isinstance(t, dict) else {}
    return {"mer": t.get("mer"), "up": t.get("up", 0.10), "down": t.get("down", 0.05), "ceiling": t.get("ceiling"),
            "bands": t.get("bands") or [1.15, 1.35], "set": sorted(k for k in t if not k.startswith("_"))}


def targets_save(data):
    """The operator's lines for one brand, changed any time from Today: MER line, raise and lower steps, the daily
    ceiling, the frequency bands. Kept on this computer only (never in the repo)."""
    brand = data.get("brand")
    if not SAFE.match(brand or ""):
        raise ValueError("bad brand")
    p = Path(os.environ.get("PRIZM_TARGETS") or Path.home() / ".prizm/targets.json")
    allt = (_read(p) or {}) if p.exists() else {}
    cur = dict(allt.get(brand) or {})

    def num(k, lo, hi):
        v = data.get(k)
        if v in (None, ""):
            return
        v = float(v)
        if not lo <= v <= hi:
            raise ValueError("%s must be between %s and %s" % (k, lo, hi))
        cur[k] = v
    num("mer", 0.1, 20)
    num("up", 0, 1)
    num("down", 0, 1)
    num("ceiling", 0, 10_000_000)
    b = data.get("bands")
    if b:
        lo, hi = float(b[0]), float(b[1])
        if not 0 < lo < hi < 20:
            raise ValueError("bands: top under middle, both above 0")
        cur["bands"] = [lo, hi]
    cur["_changed"] = time.strftime("%Y-%m-%d %H:%M")
    allt[brand] = cur
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(allt, indent=1))
    return _targets(brand)


def loop(brand):
    """The morning loop for one brand: the money line against the owner's MER line, the spend proposal it implies
    (a proposal only: spend never moves from here), the funnel stage of each live ad by its 7-day frequency, and
    the next promo windows from the marketing calendar."""
    t = _targets(brand)
    g = _growth()
    days = [d for d in (((g or {}).get("brands") or {}).get(brand) or {}).get("daily") or [] if isinstance(d, dict)]
    while days and not days[-1].get("spend"):  # the newest day has no spend yet: not a whole day
        days = days[:-1]
    days = days[-30:]
    line = [{"d": d["d"], "revenue": d.get("revenue") or 0, "spend": d.get("spend") or 0,
             "contribution": d.get("contribution") or 0, "profit": d.get("profit") or 0,
             "mer": round((d.get("revenue") or 0) / d["spend"], 2) if d.get("spend") else None} for d in days]
    w7 = line[-7:]
    s7, r7 = sum(d["spend"] for d in w7), sum(d["revenue"] for d in w7)
    mer7 = round(r7 / s7, 2) if s7 else None
    prop = None
    if t["mer"] and mer7 and w7:
        per = s7 / len(w7)
        up = mer7 >= t["mer"]
        step = t["up"] if up else -t["down"]
        to = per * (1 + step)
        if up and t["ceiling"]:
            to = min(to, float(t["ceiling"]))
        prop = {"dir": "raise" if up else "lower", "mer7": mer7, "line": t["mer"], "now": round(per), "to": round(to),
                "step": step, "ceiling": t["ceiling"], "profit7": round(sum(d["profit"] for d in w7))}
    rf = _newest("runs/media-buying/%s/2*/report.json" % brand)
    r = _read(rf) if rf else None
    lo, hi = (t["bands"] + [1.15, 1.35])[:2]
    stages = {k: {"ads": 0, "spend": 0.0} for k in ("top", "middle", "bottom")}
    for f in (r.get("flags") or []) if isinstance(r, dict) else []:
        fq = f.get("freq7")
        if not fq or f.get("action") == "off":
            continue
        k = "top" if fq < lo else "middle" if fq < hi else "bottom"
        stages[k]["ads"] += 1
        stages[k]["spend"] += float((f.get("windows") or {}).get("7", {}).get("spend") or 0) if isinstance(
            (f.get("windows") or {}).get("7"), dict) else 0.0
    today_ = time.strftime("%Y-%m-%d")
    promos = []
    for sf in sorted(glob.glob(str(WS / "runs/marketing-calendar" / brand / "2*" / "slots.json"))):
        for sl in _read(sf) or []:
            if isinstance(sl, dict) and str(sl.get("date") or "") >= today_:
                promos.append({"date": sl.get("date"), "occasion": sl.get("occasion"), "offer": sl.get("offer"),
                               "product": sl.get("product"), "category": sl.get("category"), "segment": sl.get("segment")})
    promos.sort(key=lambda x: str(x["date"]))
    seen, uniq = set(), []
    for x in promos:  # one row per day and occasion: the calendar holds one slot per segment and channel
        k = (x["date"], x["occasion"])
        if k not in seen:
            seen.add(k)
            uniq.append(dict(x, slots=sum(1 for y in promos if (y["date"], y["occasion"]) == k)))
    promos = uniq
    return {"targets": t, "line": line, "mer7": mer7, "proposal": prop, "stages": stages, "bands": [lo, hi],
            "stages_asof": r.get("asof") if isinstance(r, dict) else None, "promos": promos[:6]}


def today(brand):
    la = live_ads(brand)
    return {"loop": loop(brand), "money": money(), "winners": winners(brand), "research": research(brand), "now": la["money"],
            "off": [a for a in la["ads"] if a["call"] == "off"], "calls": [a for a in la["ads"] if a["call"] not in (None, "too_early", "keep", "off")],
            "calls_asof": la["calls_asof"], "vary": vary_candidates(la),
            "low_roas": sum(1 for a in la["ads"] if a["active"] and a["spend7"] >= 50 and (a["roas7"] or 0) < 0.5
                            and not (a["buys7"] > 0 and not a["value7"]))}


def preset(brand, avatar):
    """The drama story preset for a no-swipe film (drama_start.py preset: free, no model)."""
    r = subprocess.run([PY, str(WS / "components/video-production/machine/drama_start.py"), "preset",
                        "--brand", brand, "--avatar", avatar], cwd=str(WS), capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise ValueError((r.stderr or r.stdout).strip()[-400:] or "no preset")
    txt = r.stdout.strip()
    return json.loads(txt if txt.startswith("{") else txt.splitlines()[-1])


# ---------- jobs: one background command at a time per piece ----------

def jobs_list():
    with JLOCK:
        return sorted(({k: v for k, v in j.items() if k != "proc"} for j in JOBS.values()),
                      key=lambda j: j["started"], reverse=True)


def busy(key):
    with JLOCK:
        return any(j["piece"] == key and j["state"] == "running" for j in JOBS.values())


def launch(key, what, cmds, log):
    """Run commands one after another in the background; stop at the first that fails. Returns the job."""
    if busy(key):
        raise RuntimeError("this piece is already moving: wait for it to finish")
    jid = uuid.uuid4().hex[:10]
    log.parent.mkdir(parents=True, exist_ok=True)
    job = {"id": jid, "piece": key, "what": what, "state": "running", "started": time.time(), "log": str(log.relative_to(WS)) if str(log).startswith(str(WS)) else rel(log),
           "log_path": str(log), "steps": [c[0] for c in cmds], "exit": None}
    with JLOCK:
        JOBS[jid] = job

    def go():
        code = 0
        with open(log, "a") as out:
            for label_, argv, ok in cmds:
                out.write("\n== %s\n$ %s\n" % (label_, " ".join(Path(a).name if i == 1 else a for i, a in enumerate(argv))))
                out.flush()
                try:
                    code = subprocess.run(argv, cwd=str(WS), stdout=out, stderr=subprocess.STDOUT, timeout=6 * 3600).returncode
                except (OSError, subprocess.SubprocessError) as e:
                    out.write(str(e) + "\n")
                    code = 1
                if code not in ok:
                    break
        with JLOCK:
            job.update(state="finished" if code in cmds[-1][2] or code == 0 else "stopped", exit=code,
                       finished=time.time())

    threading.Thread(target=go, daemon=True).start()
    return {k: v for k, v in job.items() if k != "proc"}


def job_view(jid):
    with JLOCK:
        j = dict(JOBS.get(jid) or {})
    if not j:
        return None
    try:
        j["tail"] = Path(j["log_path"]).read_text(errors="replace")[-6000:]
    except OSError:
        j["tail"] = ""
    j.pop("log_path", None)
    return j


def wf(*a):
    return [PY, str(WS / "components/video-production/machine/workflow.py")] + list(a)


def start(q):
    """A new piece: a line, a start (swipe / own story / winner swipe), a brand and a name. Free steps only."""
    fmt, how, brand = q.get("format"), q.get("start"), q.get("brand")
    label = re.sub(r"[^a-z0-9-]+", "-", (q.get("label") or "").lower()).strip("-")
    if fmt not in {l["id"] for l in LINES}:
        raise ValueError("pick a line: micro drama or song ad")
    if how not in STARTS:
        raise ValueError("pick how it starts")
    if not brand or not SAFE.match(brand) or not bdir(brand).is_dir():
        raise ValueError("pick a brand")
    if not label:
        raise ValueError("give the piece a short name")
    label = label if label.startswith(brand) else brand + "-" + label
    if state_path(brand, label).is_file():
        raise ValueError("a piece with that name is already on the desk: open it instead")
    sets = ["--set", "format=" + fmt]
    cmds = []
    if how == "own":
        avatar, product, pid = q.get("avatar"), q.get("product"), q.get("preset")
        for k, x in (("avatar", avatar), ("product", product)):
            if not x or not SAFE.match(x):
                raise ValueError("pick the " + k)
        if not pid:
            pid = preset(brand, avatar).get("id")
        if not pid or not SAFE.match(str(pid)):
            raise ValueError("no story preset could be picked for this person")
        cmds.append(("Set up our own story", [PY, str(WS / "components/video-writing/machine/scratch.py"), label,
                                              "--brand", brand, "--product", product, "--avatar", avatar,
                                              "--preset", str(pid)], (0,)))
        sets += ["--set", "source=own", "--set", "route=scratch", "--set", "teardown=" + label,
                 "--set", "source_record=runs/video-teardown/_work/%s/vars/story-preset.md" % label,
                 "--set", "writing_run=runs/video-teardown/_work/" + label,
                 "--set", "brief=runs/video-teardown/_work/%s/stages/5-brief.md" % label,
                 "--set", "product=" + product, "--set", "avatar=" + avatar]
    else:
        td = q.get("teardown")
        if not td or not SAFE.match(td) or not (WS / "runs/video-teardown/_work" / td / "run.json").is_file():
            raise ValueError("pick a swipe that is already torn down")
        sets += ["--set", "source=swipe", "--set", "teardown=" + td,
                 "--set", "source_record=runs/video-teardown/_work/%s/run.json" % td,
                 "--set", "writing_run=runs/video-teardown/_work/" + td,
                 "--set", "brief=runs/video-teardown/_work/%s/stages/5-brief.md" % td]
        if how == "winner":
            if not (bdir(brand) / "winner.json").is_file():
                raise ValueError("this brand has no winner on file yet")
            sets += ["--set", "winner=brands/%s/winner.json" % brand]
    film = label
    sets += ["--set", "pack_label=" + film, "--set", "production_label=" + film]
    cmds.append(("Start the workflow", wf("run", fmt, "--brand", brand, "--label", label, *sets), (0, 2)))
    log = state_path(brand, label).parent / "desk-start.log"
    return {"brand": brand, "label": label, "job": launch(brand + "/" + label, "Start", cmds, log)}


def move_on(brand, label):
    """Run every station that runs by itself, up to the next one Claude does or the price (never a paid one)."""
    s = _read(state_path(brand, label))
    if not isinstance(s, dict):
        raise ValueError("no such piece")
    log = state_path(brand, label).parent / "desk-run.log"
    return launch(brand + "/" + label, "Move on",
                  [("Move on", wf("run", s["format"], "--brand", brand, "--label", label), (0, 2))], log)


def give_go(brand, label, q):
    """The owner's go on the price he sees on this page. His name, his own words and the cap are all required."""
    who, said = str(q.get("approved_by") or "").strip(), str(q.get("said") or "").strip()
    try:
        cap = float(q.get("cap"))
    except (TypeError, ValueError):
        cap = 0
    if not who or not said:
        raise ValueError("the go needs your name and your own words")
    if cap <= 0:
        raise ValueError("set the most it may spend")
    s = _read(state_path(brand, label))
    if not isinstance(s, dict):
        raise ValueError("no such piece")
    v, fmt = s.get("values") or {}, s["format"]
    steps = steps_for(fmt, v.get("production_route"))
    nxt = dry_next(fmt, brand, label)
    step = next((x for x in steps if x["id"] == nxt.get("station")), None)
    if not step or not step.get("quote"):
        raise ValueError("this piece is not at its price yet")
    film = film_dir(steps, v)
    price = quote_of(film, step, v)
    if not price.get("ready"):
        raise ValueError("the price is not written yet: Claude prices it first")
    log = state_path(brand, label).parent / "desk-go.log"
    if step.get("go"):
        cmds = [("Record the go", wf("go", fmt, "--brand", brand, "--label", label, "--approved-by", who,
                                     "--said", said, "--cap", str(cap)), (0,))]
    else:
        model = q.get("model") or price.get("clip_model")
        if model and not SAFE.match(model):
            raise ValueError("unknown clip model")
        total = price.get("total_credits")
        if isinstance(total, (int, float)) and cap < total:
            raise ValueError("the cap is below the price (%s credits)" % total)
        cmds = [("Open the lane on your go", [PY, str(WS / "components/video-studio/higgsfield/drama_lane.py"),
                                             "open", str(WS / film), "--quote", str(WS / price["path"]),
                                             "--approved-by", who, "--said", said, "--cap", str(cap),
                                             "--format", fmt] + (["--model", model] if model else []), (0,))]
    cmds.append(("Mark the price done", wf("complete", fmt, "--brand", brand, "--label", label,
                                           "--station", step["id"], "--note", "go given on the desk"), (0,)))
    return launch(brand + "/" + label, "The go", cmds, log)


# ---------- files ----------

def read_text(ref, limit=400_000):
    p = inside(ref)
    if not p or not p.is_file() or p.suffix.lower() not in TEXT:
        return None
    data = p.read_bytes()[:limit]
    return {"path": ref, "name": _plain(ref), "text": data.decode("utf-8", errors="replace"),
            "cut": p.stat().st_size > limit}


# ---------- HTTP (called from video_studio.py's handler) ----------

def handle(h, method, parts, query, body):
    """Answer /desk and /api/desk/*. `h` is the Studio's request handler (send, file)."""
    q = {k: v[0] for k, v in parse_qs(query or "").items()}
    try:
        if parts == ["desk"] and method == "GET":
            return h.send(200, (HERE / "desk.html").read_bytes(), "text/html; charset=utf-8")
        if parts == ["next"] and method == "GET":           # the new Studio: one app for every ad (studio-next.html)
            return h.send(200, (HERE / "studio-next.html").read_bytes(), "text/html; charset=utf-8")
        api = parts[2:]
        if method == "GET":
            if api == ["lines"]:
                return h.send(200, {"lines": LINES, "starts": STARTS})
            if api == ["pieces"]:
                return h.send(200, {"pieces": pieces()})
            if api == ["brands"]:
                return h.send(200, {"brands": brands()})
            if api == ["today"] and SAFE.match(q.get("brand", "")):
                return h.send(200, today(q["brand"]))
            if api == ["skills"] and SAFE.match(q.get("brand", "")):
                return h.send(200, skills(q["brand"]))
            if api == ["emails"] and SAFE.match(q.get("brand", "")):
                return h.send(200, {"emails": emails(q["brand"])})
            if api == ["email"] and SAFE.match(q.get("brand", "")) and SAFE.match(q.get("label", "")):
                em = email(q["brand"], q["label"])
                return h.send(200, em) if em else h.send(404, {"error": "no such email run"})
            if api == ["page"]:                              # an email's own preview page, shown in a frame
                p = inside(q.get("path", ""), ("runs",))
                if p and p.is_file() and p.suffix.lower() == ".html" and "email-production" in p.parts:
                    return h.send(200, p.read_bytes(), "text/html; charset=utf-8")
                return h.send(404, {"error": "no such page"})
            if api == ["ads"] and SAFE.match(q.get("brand", "")):
                return h.send(200, live_ads(q["brand"]))
            if api == ["brief"] and SAFE.match(q.get("brand", "")) and re.fullmatch(r"\d{3,5}", q.get("n", "")):
                bv = brief_view(q["brand"], q["n"])
                return h.send(200, bv) if bv else h.send(404, {"error": "no brief with that number for this brand"})
            if api == ["hidden"] and SAFE.match(q.get("brand", "")):
                return h.send(200, {"hidden": hidden(q["brand"])})
            if api == ["market"] and SAFE.match(q.get("brand", "")):
                return h.send(200, market(q["brand"]))
            if api == ["pages"] and SAFE.match(q.get("brand", "")):
                return h.send(200, pages(q["brand"]))
            if api == ["creators"] and SAFE.match(q.get("brand", "")):
                return h.send(200, creators_live(q["brand"]) if q.get("live") else creators(q["brand"]))
            if api == ["knowledge"]:
                return h.send(200, knowledge(q.get("q", "")))
            if api == ["github"]:
                return h.send(200, github())
            if api == ["asks"]:
                import studio_asks as SA
                SA.start_worker()                               # a restarted Studio picks up asks still open
                return h.send(200, {"asks": SA.listing(q.get("brand") if SAFE.match(q.get("brand", "")) else None)})
            if api == ["sauce"] and SAFE.match(q.get("brand", "")):
                return h.send(200, sauce_list(q["brand"]))
            if api == ["sauce-one"] and SAFE.match(q.get("label", "")):
                sg = sauce_get(q["label"])
                return h.send(200, sg) if sg else h.send(404, {"error": "no spiced script with that name"})
            if api == ["joining"]:
                return h.send(200, joining())
            if api == ["bill"] and SAFE.match(q.get("brand", "")):
                return h.send(200, bill(q["brand"]))
            if api == ["usage"] and SAFE.match(q.get("brand", "")):
                import studio_asks as SA
                return h.send(200, SA.usage(q["brand"]))
            if len(api) == 3 and api[0] == "ask":
                import studio_asks as SA
                a = SA.one(api[1], api[2])
                return h.send(200, a) if a else h.send(404, {"error": "no such ask"})
            if api == ["portfolio"]:
                return h.send(200, portfolio())
            if api == ["setup"] and SAFE.match(q.get("brand", "")):
                return h.send(200, setup(q["brand"]))
            if api == ["swipes"] and SAFE.match(q.get("brand", "")):
                return h.send(200, {"swipes": swipes(q["brand"])})
            if api == ["swipe"] and SAFE.match(q.get("label", "")):
                sw = swipe(q["label"])
                return h.send(200, sw) if sw else h.send(404, {"error": "no teardown for that swipe"})
            if api == ["teardowns"] and SAFE.match(q.get("brand", "")):
                return h.send(200, {"teardowns": teardowns(q["brand"])})
            if api == ["preset"] and SAFE.match(q.get("brand", "")) and SAFE.match(q.get("avatar", "")):
                return h.send(200, preset(q["brand"], q["avatar"]))
            if len(api) == 3 and api[0] == "piece" and SAFE.match(api[1]) and SAFE.match(api[2]):
                p = piece(api[1], api[2], live=q.get("quick") != "1")
                return h.send(200, p) if p else h.send(404, {"error": "no such piece"})
            if api == ["text"]:
                t = read_text(q.get("path", ""))
                return h.send(200, t) if t else h.send(404, {"error": "that file cannot be shown"})
            if api == ["media"]:
                p = inside(q.get("path", ""), ("runs",))
                if p and p.is_file() and p.suffix.lower() in MEDIA:
                    return h.file(str(p))
                return h.send(404, {"error": "no such picture or clip"})
            if len(api) == 2 and api[0] == "job":
                j = job_view(api[1])
                return h.send(200, j) if j else h.send(404, {"error": "no such job"})
        if method == "POST":
            data = json.loads(body or b"{}") or {}
            if api == ["start"]:
                return h.send(200, start(data))
            if api == ["knowledge-ask"]:                        # the knowledge chat (same service daemn.co/knowledge asks)
                return knowledge_ask(h, data)
            if api == ["ask"]:                                  # a Studio button hands one job to Claude
                import studio_asks as SA
                return h.send(200, SA.create(data.get("kind"), data.get("brand"), data.get("input"), data.get("by"), data.get("to")))
            if api == ["ask-hand"]:                             # move a job: to the brand's owner, the team, or here
                import studio_asks as SA
                rec = SA.one(str(data.get("brand") or ""), str(data.get("id") or ""))
                if not rec:
                    return h.send(404, {"error": "no such job"})
                rec = {k: v for k, v in rec.items() if k not in ("result", "steps", "next", "draft", "live")}
                return h.send(200, SA.hand(rec, data.get("to")))
            if api == ["joining"]:
                return h.send(200, join_update(data))
            if api == ["sauce"]:
                return h.send(200, sauce_save(data.get("label"), data.get("text"), data.get("by")))
            if api == ["ad-off"]:
                return h.send(200, ad_off(data))
            if api == ["targets"]:
                return h.send(200, targets_save(data))
            if api == ["hide"]:
                return h.send(200, hide(data.get("brand"), data.get("item"), data.get("on", True) is not False))
            if api == ["taste"]:                                # the owner's "Use this" / "Discard" on a taste draft
                import studio_asks as SA
                return h.send(200, SA.use_taste(data.get("brand"), data.get("kind"), bool(data.get("use"))))
            if len(api) == 4 and api[0] == "piece" and SAFE.match(api[1]) and SAFE.match(api[2]):
                if api[3] == "run":
                    return h.send(200, move_on(api[1], api[2]))
                if api[3] == "go":
                    return h.send(200, give_go(api[1], api[2], data))
        return h.send(404, {"error": "not found"})
    except ValueError as e:
        return h.send(400, {"error": str(e)})
    except RuntimeError as e:
        return h.send(409, {"error": str(e)})
    except Exception as e:  # noqa: BLE001 — said on the page; the Studio stays up
        return h.send(500, {"error": "%s: %s" % (type(e).__name__, e)})
