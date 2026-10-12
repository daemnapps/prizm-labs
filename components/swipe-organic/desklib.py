#!/usr/bin/env python3
"""Shared pieces for the feed desk — the model call, job status, thumbnails,
the Apify spend read, and the one function that turns a feed's store into
cards. dig.py, sift.py, daily.py and desk.py all read from here so the page
and the jobs can never disagree about what a feed holds.
"""
import json, os, re, shutil, subprocess, sys, tempfile, urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit.paths import repo  # noqa: E402  the one workspace locator (triage page 12)
WS = repo(HERE)
FEEDS = HERE / "records" / "avatar-feeds"
JOBS = HERE / "records" / "desk" / "jobs"
PROMPTS = HERE / "prompts"
CLAUDE = shutil.which("claude") or "/opt/homebrew/bin/claude"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def iso(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


# ------------------------------------------------------------------ the model
def ask_model(prompt, model="haiku", timeout=600):
    """One prompt in, text out, through the Claude CLI this Mac is signed in
    to. Runs from an empty folder so no project instructions leak in."""
    env = {**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:"
           + os.environ.get("PATH", "")}
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([CLAUDE, "-p", "--model", model, "--output-format", "text"],
                           input=prompt, capture_output=True, text=True,
                           timeout=timeout, cwd=d, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"model call failed: {(r.stderr or r.stdout)[:200]}")
    return r.stdout


def json_from(text):
    """The first JSON object or list in a model reply, fenced or not."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    body = m.group(1) if m else text
    start = min([i for i in (body.find("{"), body.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("no JSON in the model reply")
    return json.JSONDecoder().raw_decode(body[start:])[0]


def prompt(name, **slots):
    text = (PROMPTS / name).read_text()
    for k, v in slots.items():
        text = text.replace("{" + k + "}", str(v))
    return text


# ------------------------------------------------------------------ jobs
def job_write(job, **fields):
    JOBS.mkdir(parents=True, exist_ok=True)
    f = JOBS / f"{job}.json"
    cur = json.loads(f.read_text()) if f.exists() else {"id": job, "started": now(), "steps": []}
    if "step" in fields:
        cur["steps"].append({"at": now(), "say": fields.pop("step")})
    cur.update(fields)
    cur["updated"] = now()
    f.write_text(json.dumps(cur, indent=1))
    return cur


def jobs(limit=12):
    if not JOBS.exists():
        return []
    rows = [json.loads(f.read_text()) for f in JOBS.glob("*.json")]
    return sorted(rows, key=lambda j: j.get("started", ""), reverse=True)[:limit]


# ------------------------------------------------------------------ spend
def apify_spend():
    """Dollars used / allowed this billing cycle on the main Apify account."""
    try:
        import apify as A
        with urllib.request.urlopen(f"{A.API}/users/me/limits?token={A.token()}", timeout=20) as r:
            d = json.load(r)["data"]
        return round(d["current"]["monthlyUsageUsd"], 2), round(d["limits"]["maxMonthlyUsageUsd"], 2)
    except Exception:
        return None, None


# ------------------------------------------------------------------ thumbnails
def cache_covers(feed, limit=400):
    """CDN thumbnail links die within days. Save each one beside the feed the
    day it is pulled, so the page still has pictures next month."""
    root = FEEDS / feed
    items = json.loads((root / "items.json").read_text())["items"]
    cov = root / "covers"
    cov.mkdir(exist_ok=True)
    def grab(it):
        dest = cov / (re.sub(r"[^A-Za-z0-9_-]", "", str(it["id"])) + ".jpg")
        if dest.exists() or not it.get("cover"):
            return 0
        try:
            req = urllib.request.Request(it["cover"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
            if len(data) > 1500:
                dest.write_bytes(data)
                return 1
        except Exception:
            pass
        return 0
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=12) as pool:
        return sum(pool.map(grab, list(items.values())[:limit * 3]))


# ------------------------------------------------------------------ the store, as cards
def feeds():
    out = []
    for d in sorted(FEEDS.iterdir()):
        if not (d / "sources.json").exists():
            continue
        S = json.loads((d / "sources.json").read_text())
        sweeps = [json.loads(l) for l in (d / "sweeps.jsonl").read_text().splitlines()] \
            if (d / "sweeps.jsonl").exists() else []
        live = [s for s in S["sources"] if s.get("status") != "retired"]
        out.append({"id": d.name, "title": S.get("title") or d.name.replace("--", " · "),
                    "ask": S.get("ask"), "made": S.get("made"), "brand": S.get("brand"),
                    "core": S.get("core") or (S.get("avatar") if not S.get("sub") else None), "sub": S.get("sub"),
                    "whose": S.get("whose"),
                    "sources": len(live),
                    "probation": sum(1 for s in live if s.get("status") == "probation"),
                    "last": sweeps[-1] if sweeps else None, "sweeps": len(sweeps),
                    "source_list": live})
    return out


def cards(feed):
    root = FEEDS / feed
    if not (root / "items.json").exists():
        return []
    items = json.loads((root / "items.json").read_text())["items"]
    obs = {}
    if (root / "observations.jsonl").exists():
        for line in (root / "observations.jsonl").read_text().splitlines():
            o = json.loads(line)
            obs.setdefault(o["item"], []).append(o)
    t = datetime.now(timezone.utc)
    out = []
    for key, it in items.items():
        rows = [o for o in obs.get(key, []) if o.get("views")]
        views = rows[-1]["views"] if rows else None
        likes = next((o["likes"] for o in reversed(obs.get(key, [])) if o.get("likes")), None)
        shares = next((o["shares"] for o in reversed(obs.get(key, [])) if o.get("shares")), None)
        # sent-to-a-friend rate — the entertainment signal (TikTok only; the others hide shares)
        sent = round(shares / views * 1000, 1) if shares and views and views >= 10_000 else None
        rise = None
        if len(rows) >= 2 and rows[0]["views"] and rows[-1]["views"] >= 10_000:
            t0, t1 = iso(rows[0]["at"]), iso(rows[-1]["at"])
            if t0 and t1:
                days = max((t1 - t0).total_seconds() / 86400, 0.25)
                rise = round((rows[-1]["views"] / rows[0]["views"] - 1) / days * 100, 1)
        posted, seen = iso(it.get("posted")), iso(it.get("first_seen"))
        fol = it.get("followers")
        # how far past the creator's own size the post went — the outlier read
        punch = round(views / fol, 1) if views and fol and fol >= 500 else None
        cid = re.sub(r"[^A-Za-z0-9_-]", "", str(it["id"]))
        sift = it.get("sift") or {}
        out.append({
            "key": key, "feed": feed, "platform": it["platform"], "url": it["url"],
            "author": it.get("author") or "", "caption": (it.get("caption") or "")[:220],
            "tags": it.get("hashtags") or [],
            "cover": f"/cover/{feed}/{cid}.jpg" if (root / "covers" / f"{cid}.jpg").exists() else it.get("cover"),
            "posted": posted.strftime("%b %d") if posted else None,
            "age": (t - posted).days if posted else None,
            "seen_days": (t - seen).days if seen else None,
            "views": views, "likes": likes, "shares": shares, "sent": sent, "rise": rise, "punch": punch,
            "kind": sift.get("kind"), "lane": sift.get("lane"),
            "source": it.get("source", ""), "receipt": it.get("receipt", ""),
            # his own read, on the cards that carry one (his saves): which brand
            # it was saved for, and whether it is ad-shaped or culture
            "brand_fit": it.get("brand_fit"), "swipe_lane": it.get("swipe_lane"),
            "keep": sift.get("keep"), "what": sift.get("what"),
            "format": sift.get("format"), "why": sift.get("why"),
        })
    return out


# ------------------------------------------------------------------ the research chain, stage by stage
def chain(feed):
    """What each stage was sent and what it gave back — for one feed. The page
    shows this so the research process itself can be read and tightened."""
    root = FEEDS / feed
    S = json.loads((root / "sources.json").read_text())
    items = json.loads((root / "items.json").read_text())["items"] if (root / "items.json").exists() else {}
    sweeps = [json.loads(l) for l in (root / "sweeps.jsonl").read_text().splitlines()] \
        if (root / "sweeps.jsonl").exists() else []
    disc = [json.loads(l) for l in (root / "discoveries.jsonl").read_text().splitlines()] \
        if (root / "discoveries.jsonl").exists() else []
    def read(rel):
        f = root / rel
        return f.read_text() if f.exists() else None
    sifted = [it for it in items.values() if it.get("sift")]
    kinds = {}
    for it in sifted:
        k = (it["sift"].get("lane") or "?") + " · " + (it["sift"].get("kind") or "?")
        kinds.setdefault(k, {"kept": 0, "dropped": 0})["kept" if it["sift"]["keep"] else "dropped"] += 1
    sample = lambda keep: [{"author": it.get("author"), "caption": (it.get("caption") or "")[:110],
                            "kind": it["sift"].get("kind"), "why": it["sift"].get("why"), "url": it["url"]}
                           for it in sifted if it["sift"]["keep"] is keep][:12]
    return {"feed": feed, "ask": S.get("ask"), "stages": [
        {"n": 1, "name": "Plan", "does": "Turns the ask into searches, hashtags and a keep/drop rule.",
         "model": "Claude Sonnet", "prompt_file": "feed-plan-v3.md", "prompt": read("prompts-as-sent/plan.md"),
         "output": json.loads(read("plan.json")) if read("plan.json") else None},
        {"n": 2, "name": "Pull", "does": "Runs every search on TikTok, Instagram and YouTube; turns away ads, old posts and small posts at the door.",
         "model": "Apify scrapers", "entry": S.get("entry"),
         "output": (sweeps[-1] if sweeps else None)},
        {"n": 3, "name": "Sift", "does": "Sorts every new post into a lane: entertainment, educational, selling or junk. Only the first two stay.",
         "model": "Claude Haiku", "prompt_file": "feed-sift-v3.md", "prompt": read("prompts-as-sent/sift-latest.md"),
         "output": {"kinds": kinds, "kept": sample(True), "dropped": sample(False)}},
        {"n": 4, "name": "Follow", "does": "Follows the winners to the creators behind them and seats those creators on trial.",
         "model": "no model — follows the edges", "output": disc[-12:]},
        {"n": 5, "name": "Repeat", "does": "Every morning at 5:30 stages 2–4 run again on every feed.",
         "model": "the daily run", "output": {"pulls_so_far": len(sweeps)}},
    ]}
