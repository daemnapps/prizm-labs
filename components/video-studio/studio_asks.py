"""Studio asks: a button in the Studio hands one job to Claude, which runs it in the background and writes the result
back for the owner to read and OK.

Each ask is a folder: runs/studio-asks/<brand>/<id>/ask.json (what was asked, its state) + result.md (what came back) +
run.log. One ask runs at a time, in the order asked; the server picks up asks still queued when it starts again.

Every ask runs `claude -p` in the repo with a short tool list and the same rules: free steps only (anything that spends
stops for the owner's go on a price), never go live, never send, never approve, and nothing written outside the
brand's folder and runs/. A taste draft is written beside the live file (`<kind>.draft.md`); only the owner's
"Use this" replaces the live one, and the old one is kept.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parent.parent
SAFE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*\Z")
TASTES = ("copy", "video", "image", "email")
TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(python3 *)", "Bash(ls *)", "Bash(gh repo view *)",
         "Bash(gh repo list *)", "Bash(ffprobe *)", "Bash(ffmpeg *)"]
RULES = """Rules for this job, always:
- Free steps only. Anything that spends money stops: write the price into the result and stop for the owner's go.
- Never go live, never send, never approve, never post, never message anyone.
- Write only inside brands/{brand}/ and runs/. Never edit components/ or .claude/.
- Facts, numbers and the customer's own words, each with where it came from. No opinions, no padding.
- The owner reads the result on a page: short headings, tables and bullet lines, never long paragraphs.
- Finish by writing the result to {out} (Markdown). Its first line is one sentence saying what you found or made."""

KINDS = {
    "tune": {
        "name": "Tune this brand's {input} taste",
        "prompt": """Brand: {brand}. Job: draft a sharper version of this brand's {input} taste file, the file every {input}
skill reads for the brand's voice, look and rules.

Read: brands/{brand}/variables/{input}.md (the live file), brands/_TEMPLATE/variables/{input}.md (its shape),
brands/{brand}/rulings.md if it exists, runs/winners/{brand}/bank.json (the top 10 rows by purchases: their words,
headlines and hooks), runs/winners/{brand}/brief-next.md, and the language banks under brands/{brand}/core-avatars/.

Write the draft to brands/{brand}/variables/{input}.draft.md in the template's shape. Keep everything in the live file
that the evidence supports; add what the winners and the customer's words show; mark each added or changed line with
its source in a trailing comment like <!-- from: winners W1 -->. Never edit the live file.

In the result: what changed, as a table (line · before · after · why, with the number or quote behind it)."""},
    "deeper": {
        "name": "Go deeper: {input}",
        "prompt": """Brand: {brand}. Job: go deeper on this angle: "{input}".

Use what the brand already has (free): the language banks and profiles under brands/{brand}/core-avatars/, reviews and
surveys under brands/{brand}/customer/ (or wherever the brand keeps them), runs/winners/{brand}/ (bank.json,
brief-next.md, leaderboard), and the research rounds under runs/swipe-organic/{brand}/.

Find: the customer's exact words for this angle (quote them, with the file each came from), the desire and the
objection under it, which winners already used it and their numbers, and which proven formats fit it (the live lines
in components/video-production/formats/playbooks/ whose state is not parked).

In the result: 1) the words, verbatim, ranked by how often they appear; 2) five ad concepts, each one line: format ·
hook line in the customer's words · the proof it stands on."""},
    "make": {
        "name": "Make: {input}",
        "prompt": """Brand: {brand}. Job: make these planned variations: "{input}".

The plan is in the result.md of the variations job named in the input (under runs/studio-asks/{brand}/). Follow
.claude/skills/ad-variations/SKILL.md to set up only the variations named in the input, through the free steps, and
register each one in the production workflow so it shows in the Studio's Production. Stop at the price: write the
price per variation into the result and stop for the owner's go. In the result: each variation started, its name, where
it is now, and its price if known."""},
    "swipe": {
        "name": "Add a swipe: {input}",
        "prompt": """Brand: {brand}. Job: add this post as a swipe and tear it down: {input}

Follow .claude/skills/swipe-intake/SKILL.md, then .claude/skills/video-teardown/SKILL.md, for brand {brand}. Stop after
the teardown (no writing, no production). In the result: the teardown label and three lines on what the swipe is."""},
    "variations": {
        "name": "Plan variations of {input}",
        "prompt": """Brand: {brand}. Job: plan variations of this ad that is working now: "{input}".

Find it: a brief number is in the ad names (`..._brief-NNNN_...`); read its live numbers in the newest
runs/funnel-tracking/{brand}/<date>/warehouse.json and the desk's call in the newest runs/media-buying/{brand}/<date>/
report.json, its cards in runs/meta-upload/{brand}/ADS-INDEX.json, and its brief and teardown wherever the index points.
A creator ad carries trybe=<id> in its name; read its numbers the same way. Older all-time winners are in
runs/winners/{brand}/bank.json, only if the input names one.

Follow .claude/skills/ad-variations/SKILL.md, free planning steps only: stop before anything is made or paid for. In the
result: the variations planned (opening, offer, format), each with the winner's number it builds on and the price to
make it if one is known."""},
    "setup": {
        "name": "Fill setup: {input}",
        "prompt": """Brand: {brand}. Job: fill this item of the brand checklist: "{input}" (see brands/_TEMPLATE/onboarding.json
for the item, what it is for, and the files it fills).

Use what the brand already has first (its folder, its website, its reviews) and the brand-intake / brand-activation
skills under .claude/skills/. Write the item's files inside brands/{brand}/ in the template's shape, and put
"DRAFT · owner to confirm" at the top of anything you inferred. Never overwrite a file that already has the brand's own
content: write <name>.draft.<ext> beside it instead. In the result: each file written and what is still missing."""},
    "market": {
        "name": "Scan the market: {input}",
        "prompt": """Brand: {brand}. Job: scan the market for products and offers worth selling: "{input}".

Follow .claude/skills/product-research/SKILL.md (Kalodata for TikTok Shop, TrendTrack for stores and ads). Reads that
cost credits need the owner's go: plan the read, write the credits it would spend and stop, unless the input says a
credit cap. When the brand is _portfolio the scan is for no one brand: keep its files under runs/product-tracker/_system/.
Free reads (balances, lookups, what is already on file under runs/product-tracker/ and
runs/trendtrack/market/) you may do. In the result: the products ranked by 30-day revenue with growth, price, who
sells them, and the angle they sell on; then the credits a fresh read would spend."""},
    "onboard": {
        "name": "Bring in a brand: {input}",
        "prompt": """Job: bring this brand into the system: {input}
(the input is the brand's name and, when it has one, its own GitHub repository as owner/name).

The brand owns its own repository and its own data; we only get access. Read tools/client-copies/README.md and
.claude/CLAUDE.md ("Running clients"). Then:
1. If a repository is given, check our access with `gh repo view <owner/name>` (read-only). If we cannot see it, stop
   and say in the result exactly what the brand must do: create the repository (private) from Prizm Labs, and invite
   our GitHub account as a collaborator.
2. If the repository is already on this computer (a folder listed in ~/.prizm/brand-roots.json), read it there.
   Otherwise, if we can see it, bring it onto this computer with `python3 tools/client-copies/clients.py get <client>` when it is
   one of our client copies; otherwise only read it through gh. Never clone into ~/Projects.
3. Read its brand folder against brands/_TEMPLATE/onboarding.json, item by item: what is filled, what is missing.
4. In the result: a table of the 23 items (filled / missing), then "What to ask the brand for": a short numbered
   list in plain words the owner can forward as is, then the first run once it is filled (their top 5 ads by spend
   → teardowns → scripts → production)."""},
    "connect": {
        "name": "Look at {input}",
        "prompt": """Job: say what this GitHub repository is, read-only: {input}

Use `gh repo view {input}` (and its README through gh) only. Never clone, never write outside runs/. In the result: what
brand or business it belongs to, what it holds (store, pages, data, tools), when it last changed, and what the Studio
could read from it."""},
}

# Where each job goes after Claude: the stages the Studio shows as a strip on the job's page.
NEXT = {
    "tune": ["Claude drafts the taste", "You: Use this or Discard", "Every skill reads it"],
    "deeper": ["Claude reads the brand's words and winners", "You: pick a concept", "Make it as a new ad"],
    "variations": ["Claude plans the variations", "You: pick which to make", "Production (stops at the price)", "Approve"],
    "make": ["Claude sets them up in production", "Production (stops at the price)", "You: go on the price", "Approve"],
    "swipe": ["Claude saves and tears it down", "It lands in Swipes", "Make an ad from it"],
    "setup": ["Claude fills the item as a draft", "You: confirm in Settings"],
    "connect": ["Claude reads the repository", "You: decide to connect it"],
    "market": ["Claude plans the read (free)", "You: go on the credits", "New products on the radar"],
    "_handed": ["Handed off", "They run it on their own Claude", "The result comes back here"],
    "onboard": ["Claude checks access and reads their brand folder", "You: send them the ask list", "Their Claude fills the folder", "First run: top 5 ads → teardowns"],
}

LOCK = threading.Lock()
WAKE = threading.Event()
_worker = None


def _bdir(brand):
    import workflow_desk as WD
    return WD.bdir(brand)


def root():
    return WS / "runs" / "studio-asks"


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _read(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def _write(p, data):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    os.replace(tmp, p)


def default_hand(brand):
    """Who runs a job by default: a brand that keeps its folder in its own repository runs its own heavy jobs (its
    owner's Claude); every other brand's jobs go to the team. The owner's own Claude runs a job only when asked."""
    try:
        import workflow_desk as WD
        d = WD.bdir(brand)
        if d.is_dir() and not str(d).startswith(str(WS / "brands")):
            return "owner"
    except Exception:  # noqa: BLE001
        pass
    return "team"


def _hand_text(rec):
    return ("# Studio job: %s\n\nBrand: %s · asked %s · job %s\n\n## What to do\n\n%s\n\n"
            "## When it is done\n\nWrite the result where the job says, then close this note.\n"
            % (rec["name"], rec["brand"], rec["asked"], rec["id"], prompt_for(rec)))


def hand(rec, to):
    """Give a job to whoever runs it: 'owner' writes it into the brand's own repository (handoffs/from-studio/), for
    the owner's Claude to pick up; 'team' writes a team handoff note for whoever runs jobs (the team workspace);
    'here' runs it on this computer's Claude."""
    d = WS / rec["dir"]
    if to == "here":
        rec.update(state="queued", to="here")
        _write(d / "ask.json", rec)
        start_worker()
        WAKE.set()
        return rec
    if to == "owner":
        import workflow_desk as WD
        root = WD.bdir(rec["brand"]).parent.parent
        p = root / "handoffs" / "from-studio" / (rec["id"] + ".md")
    elif to == "team":
        p = WS / "runs" / "studio-asks" / "_team" / (rec["id"] + ".md")
    else:
        raise ValueError("hand it to owner, team or here")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_hand_text(rec))
    rec.update(state="handed", to=to, handed_at=now(), note=str(p))
    _write(d / "ask.json", rec)
    return rec


def create(kind, brand, text, by=None, to=None):
    """Make one ask and hand it to whoever runs it (default: the brand's owner or the team). Returns its record."""
    if kind not in KINDS:
        raise ValueError("unknown ask: " + str(kind))
    if not (kind in ("connect", "onboard") or (kind == "market" and not brand)) and (not brand or not SAFE.match(brand) or not _bdir(brand).is_dir()):
        raise ValueError("pick a brand")
    text = (text or "").strip()
    if not text or len(text) > 600:
        raise ValueError("say what to do (one line)")
    if kind == "tune" and text not in TASTES:
        raise ValueError("tune one of: " + ", ".join(TASTES))
    if kind == "connect" and not re.fullmatch(r"[\w.-]+/[\w.-]+", text):
        raise ValueError("a repository as owner/name")
    if kind == "swipe" and not re.match(r"https?://", text):
        raise ValueError("paste the post's link")
    brand = "_portfolio" if kind in ("connect", "onboard") or not brand else brand
    aid = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    d = root() / brand / aid
    rec = {"id": aid, "brand": brand, "kind": kind, "input": text, "name": KINDS[kind]["name"].format(input=text),
           "state": "queued", "asked": now(), "by": by, "dir": str(d.relative_to(WS))}
    _write(d / "ask.json", rec)
    return hand(rec, to or ("here" if brand == "_portfolio" else default_hand(brand)))


def listing(brand=None, limit=40):
    out = []
    base = root() / brand if brand else root()
    for f in sorted(base.glob("*/ask.json") if brand else base.glob("*/*/ask.json"), reverse=True)[:limit]:
        r = _read(f)
        if isinstance(r, dict):
            r["result"] = (f.parent / "result.md").is_file()
            out.append(r)
    return out


def one(brand, aid):
    if not (SAFE.match(brand or "") and SAFE.match(aid or "")):
        return None
    d = root() / brand / aid
    r = _read(d / "ask.json")
    if not isinstance(r, dict):
        return None
    p = d / "result.md"
    if p.is_file():
        r["result"] = p.read_text(errors="replace")[-200_000:]
    r["steps"] = steps(d)
    r["next"] = NEXT.get(r.get("kind"), [])
    if r.get("kind") == "tune":
        draft = _bdir(brand) / "variables" / (r["input"] + ".draft.md")
        live = _bdir(brand) / "variables" / (r["input"] + ".md")
        r["draft"] = draft.read_text(errors="replace") if draft.is_file() else None
        r["live"] = live.read_text(errors="replace") if live.is_file() else None
    return r


def use_taste(brand, kind, keep=False):
    """The owner's "Use this": the draft replaces the live taste file (the old one kept), or "Discard" drops it."""
    if not SAFE.match(brand or "") or kind not in TASTES:
        raise ValueError("bad brand or taste")
    v = _bdir(brand) / "variables"
    draft, live = v / (kind + ".draft.md"), v / (kind + ".md")
    if not draft.is_file():
        raise ValueError("no draft to use")
    if keep:
        if live.is_file():
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.copy2(live, v / (kind + ".before-" + stamp + ".md"))
        os.replace(draft, live)
        return {"ok": True, "used": str(live.relative_to(WS))}
    draft.unlink()
    return {"ok": True, "discarded": True}


def prompt_for(rec):
    out = rec["dir"] + "/result.md"
    k = KINDS[rec["kind"]]
    return (k["prompt"].format(brand=rec["brand"], input=rec["input"]) + "\n\n"
            + RULES.format(brand=rec["brand"], out=out))


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _events(d):
    """The run's live log: one JSON event per line (claude --output-format stream-json)."""
    out = []
    p = Path(d) / "run.log"
    if not p.is_file():
        return out
    for line in p.read_text(errors="replace").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def _short(path):
    return "/".join(str(path).split("/")[-2:])


def steps(d, limit=30):
    """What Claude has done so far, in plain words: each file read or written, each search, each command."""
    out = []
    for ev in _events(d):
        if ev.get("type") != "assistant":
            continue
        for c in (ev.get("message") or {}).get("content") or []:
            if c.get("type") == "tool_use":
                n, i = c.get("name"), c.get("input") or {}
                if n == "Read":
                    out.append("Read " + _short(i.get("file_path", "")))
                elif n in ("Write", "Edit"):
                    out.append(("Wrote " if n == "Write" else "Edited ") + _short(i.get("file_path", "")))
                elif n == "Grep":
                    out.append('Searched for "%s"' % str(i.get("pattern", ""))[:60])
                elif n == "Glob":
                    out.append("Listed " + str(i.get("pattern", ""))[:60])
                elif n == "Bash":
                    out.append("Ran " + str(i.get("command", ""))[:70])
                else:
                    out.append(n)
            elif c.get("type") == "text" and c.get("text", "").strip():
                out.append("Note: " + c["text"].strip().splitlines()[0][:110])
    return {"count": len(out), "last": out[-limit:]}


def _final_text(d):
    for ev in reversed(_events(d)):
        if ev.get("type") == "result":
            return ev.get("result") or ""
    return ""


def _meter(d):
    """What the run cost, as Claude reports it at the end (list price), its tokens and its length."""
    for ev in reversed(_events(d)):
        if ev.get("type") == "result":
            u = ev.get("usage") or {}
            return {"cost_usd": ev.get("total_cost_usd"), "minutes": round((ev.get("duration_ms") or 0) / 60000, 1),
                    "tokens_in": (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
                    + (u.get("cache_read_input_tokens") or 0), "tokens_out": u.get("output_tokens") or 0,
                    "models": sorted((ev.get("modelUsage") or {}).keys()), "turns": ev.get("num_turns")}
    return None


def _finish(rec, code):
    d = WS / rec["dir"]
    raw = (d / "run.log").read_text(errors="replace") if (d / "run.log").is_file() else ""
    log = _final_text(d) or raw
    if not (d / "result.md").is_file() and code == 0 and log.strip():
        (d / "result.md").write_text(log.strip() + "\n")
    ok = code == 0 and (d / "result.md").is_file()
    rec.update(state="done" if ok else "failed", finished=now(), why=None if ok else (log.strip()[-400:] or "no output"))
    rec.pop("pid", None)
    m = _meter(d)
    if m:
        rec["usage"] = m
    b = re.search(r"brief[\s-]*(\d{4})", rec.get("input") or "", re.I)
    if b:
        rec["brief"] = b.group(1)
    _write(d / "ask.json", rec)
    return rec


def usage(brand):
    """Every job's cost for a brand, by month, by kind of job and by brief: the meter the bill is made from."""
    rows = []
    for f in (root() / brand).glob("*/ask.json") if SAFE.match(brand or "") else []:
        r = _read(f) or {}
        u = r.get("usage") or {}
        if u.get("cost_usd") is None:
            continue
        rows.append({"id": r.get("id"), "kind": r.get("kind"), "name": r.get("name"), "brief": r.get("brief"),
                     "month": (r.get("asked") or "")[:7], "cost": u["cost_usd"], "minutes": u.get("minutes"),
                     "tokens": (u.get("tokens_in") or 0) + (u.get("tokens_out") or 0), "state": r.get("state")})
    def roll(key):
        out = {}
        for x in rows:
            k = x.get(key) or "—"
            o = out.setdefault(k, {"key": k, "jobs": 0, "cost": 0.0, "minutes": 0.0})
            o["jobs"] += 1
            o["cost"] = round(o["cost"] + x["cost"], 4)
            o["minutes"] = round(o["minutes"] + (x["minutes"] or 0), 1)
        return sorted(out.values(), key=lambda o: -o["cost"])
    rows.sort(key=lambda x: x["id"] or "", reverse=True)
    return {"total": round(sum(x["cost"] for x in rows), 4), "jobs": len(rows), "by_month": roll("month"),
            "by_kind": roll("kind"), "by_brief": roll("brief"), "rows": rows[:100],
            "basis": "Claude's own report of each job at list price; Higgsfield and data-tool credits are kept with their runs"}


def run_one(rec, runner=None):
    """Run one ask. The Claude run is its own process (a Studio restart never kills it); its exit code is written to
    exit.txt so a restarted Studio can finish the record."""
    import time
    d = WS / rec["dir"]
    if runner:                                          # tests: a fake run, in this process
        rec.update(state="running", started=now())
        _write(d / "ask.json", rec)
        code, log = runner(["claude", "-p", prompt_for(rec)], d)
        (d / "run.log").write_text(log)
        return _finish(rec, code)
    if rec.get("state") == "running" and _alive(rec.get("pid")):
        pid = rec["pid"]                               # started before a restart: wait for it
    else:
        (d / "exit.txt").unlink(missing_ok=True)
        dirs = sorted({os.path.realpath(WS / x) for x in ("runs", "brands")})   # the data folders are often links
        try:                                                    # brands kept in their own repositories, read in place
            import workflow_desk as WD
            dirs += [str(r) for r in WD.brand_roots()]
        except Exception:  # noqa: BLE001
            pass
        cmd = ["claude", "-p", prompt_for(rec), "--output-format", "stream-json", "--verbose",
               "--add-dir", *dirs, "--allowedTools", *TOOLS]
        wrapper = 'cd "$1" && shift && "$@" > "$OUT/run.log" 2>&1; echo $? > "$OUT/exit.txt"'
        try:
            pr = subprocess.Popen(["/bin/sh", "-c", wrapper, "ask", str(WS), *cmd], start_new_session=True,
                                  env=dict(os.environ, OUT=str(d)), stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            (d / "run.log").write_text("could not run: %s" % e)
            return _finish(rec, 1)
        pid = pr.pid
        rec.update(state="running", started=now(), pid=pid)
        _write(d / "ask.json", rec)
    deadline = time.time() + 50 * 60
    while _alive(pid) and not (d / "exit.txt").is_file() and time.time() < deadline:
        time.sleep(5)
        try:
            os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            pass
    try:
        code = int((d / "exit.txt").read_text().strip())
    except (OSError, ValueError):
        code = 1
    return _finish(rec, code)


def _next():
    q = []
    for f in root().glob("*/*/ask.json"):
        r = _read(f)
        if isinstance(r, dict) and r.get("state") in ("queued", "running") and r.get("to", "here") == "here":
            q.append(r)
    q.sort(key=lambda r: r.get("asked") or "")
    return q[0] if q else None


def _loop():
    while True:
        rec = _next()
        if not rec:
            WAKE.wait(60)
            WAKE.clear()
            continue
        run_one(rec)


def start_worker():
    global _worker
    with LOCK:
        if _worker and _worker.is_alive():
            return
        if os.environ.get("STUDIO_ASKS_OFF"):
            return
        _worker = threading.Thread(target=_loop, daemon=True, name="studio-asks")
        _worker.start()
