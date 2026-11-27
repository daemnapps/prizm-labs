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

def brands():
    out = []
    for d in sorted((WS / "brands").glob("*")):
        if not d.is_dir() or d.name.startswith(("_", ".")):
            continue
        av = sorted(p.name for p in (d / "core-avatars").glob("*") if p.is_dir() and not p.name.startswith((".", "_")))
        pr = sorted({p.stem if p.is_file() else p.name for p in (d / "products").glob("*")
                     if not p.name.startswith((".", "_")) and p.stem not in ("README", "DRIVE-INDEX")
                     and (p.is_dir() or p.suffix == ".md")})
        op = _read(d / "operations/brand.json")
        out.append({"id": d.name, "label": (op.get("label") if isinstance(op, dict) else None) or d.name,
                    "avatars": av, "products": pr, "winner": (d / "winner.json").is_file()})
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
    prog = _read(WS / "brands" / brand / "onboarding-progress.json") or {}
    done, skipped = set(prog.get("done") or []), set(prog.get("skipped") or [])
    items = []
    for it in t.get("items") or []:
        fills = it.get("fills") or []
        paths = [f.split(" ")[0].rstrip(",") for f in fills]
        paths = [x for x in paths if x and not x.startswith("brands/")]
        have = [x for x in paths if glob.glob(str(WS / "brands" / brand / re.sub(r"<[^>]+>", "*", x)))]
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
            mine = WS / "brands" / brand / "variables" / f.name
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
        rows.append({"brand": b["id"], "money": mb, "waiting": None if waiting is None else waiting.get(b["id"], 0),
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


def today(brand):
    return {"money": money(), "winners": winners(brand), "research": research(brand)}


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
    if not brand or not SAFE.match(brand) or not (WS / "brands" / brand).is_dir():
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
            if not (WS / "brands" / brand / "winner.json").is_file():
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
