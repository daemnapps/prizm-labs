#!/usr/bin/env python3
"""Ad volume: N concepts per brand per day, written, made at a cheap test tier, cut into hook versions, shown in the
Video Studio stage by stage, and filed on the approval page. No hand steps between the stages.

    python3 components/ad-volume/volume.py price [--concepts 40 --versions 5]       # the cost table, priced live
    python3 components/ad-volume/volume.py day <brand> [<brand> ...] --n 20         # the daily runner: every stage below
    python3 components/ad-volume/volume.py plan <brand> --n 20 [--formats micro-drama,song-ad,ai-skit]
    python3 components/ad-volume/volume.py make <batch> [--tier test] [--floor 310] [--max-credits 200]
    python3 components/ad-volume/volume.py edit <batch>
    python3 components/ad-volume/volume.py studio <batch>
    python3 components/ad-volume/volume.py file <batch> [--go]                     # a dry run unless --go

A batch is `vol-<yyyymmdd>-<brand>` in the Video Studio's briefs folder; each concept is its own production beside it
(`vol-<yyyymmdd>-<brand>-cNN`), so the Studio lists it, plays its versions and links its stage page.

Brand facts come from `brands/<brand>/volume.json` (the kit: cast, product, set pictures, avatar, product slug) and
`brands/<brand>/winner.json`; the writing reads the winner's teardown and the brand's language bank. Nothing here names a
brand. Money: `tiers.json` (the routes and the spend floor). The make step reads the account balance before every take
and stops at the floor; going past it is the owner's call.
"""
import argparse, concurrent.futures as cf, datetime as dt, hashlib, html, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "components" / "video-studio"))
import settings as ST  # noqa: E402  the Studio's own folders (VIDEO_STUDIO_DATA, VIDEO_STUDIO_WRITING)

TIERS = json.loads((HERE / "tiers.json").read_text())
FORMATS = {p.stem: json.loads(p.read_text()) for p in sorted((HERE / "formats").glob("*.json"))}
HF = os.environ.get("HIGGSFIELD_CLI") or shutil.which("higgsfield") or "higgsfield"
CLAUDE = os.environ.get("CLAUDE_CLI") or shutil.which("claude") or "claude"
W, H = 1080, 1920


# ---------- small helpers ----------
def load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def save(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False))


def briefs():
    return Path(ST.BRIEFS)


def batch_dir(batch):
    return briefs() / batch


def concept_dir(batch, cid):
    return briefs() / f"{batch}-{cid}"


def kit(brand):
    k = load(REPO / "brands" / brand / "volume.json")
    if not k:
        raise SystemExit(f"{brand}: no brands/{brand}/volume.json (the kit: cast, product, sets). Write it first.")
    return k


def shared_assets():
    """Kit files are written as `Shared Assets/...` labels; this finds the mount (meta-upload's own finder)."""
    sys.path.insert(0, str(REPO / "components" / "meta-upload"))
    import shared_drive as SD
    return Path(SD.shared_assets())


def resolve(label):
    """A kit file: `Shared Assets/...` on the shared drive, a repo-relative path, or an absolute path."""
    s = str(label)
    if s.startswith("Shared Assets/"):
        return shared_assets() / s[len("Shared Assets/"):]
    p = Path(s)
    return p if p.is_absolute() else REPO / p


def hf(*args, timeout=900):
    r = subprocess.run([HF, "--json", *map(str, args)], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"higgsfield {' '.join(map(str, args[:3]))}: {(r.stderr or r.stdout).strip()[:400]}")
    return json.loads(r.stdout or "null")


def balance():
    return float(hf("account", "status")["credits"])


# ---------- price ----------
ROUTES = [("wan3_0", "480p", None), ("wan3_0", "720p", None), ("wan3_0", "1080p", None),
          ("seedance_2_5", "480p", None), ("seedance_2_5", "720p", None), ("seedance_2_5", "1080p", None)]


def price(concepts=40, versions=5, brands=2, seconds=None):
    """The cost table: credits per take, read live from the Higgsfield cost command, and a day of the lane per route."""
    seconds = seconds or TIERS["seconds"]
    rate = TIERS["read_15_nov_2026"]
    rows = []
    for job, res, _ in ROUTES:
        try:
            c = float(hf("generate", "cost", job, "--prompt", "x", "--duration", seconds, "--resolution", res)["credits"])
        except Exception as e:  # noqa: BLE001  a route the account cannot price is shown as such
            rows.append({"route": f"{job}@{res}", "error": str(e)[:120]})
            continue
        per_day = c * concepts * brands
        rows.append({"route": f"{job}@{res}", "credits_per_take": c,
                     "ads_per_day": concepts * versions * brands, "takes_per_day": concepts * brands,
                     "credits_per_day": per_day,
                     "usd_per_day_auto_refill": round(per_day / rate["credits_per_usd_auto_refill"], 2),
                     "usd_per_day_4000_pack": round(per_day / rate["credits_per_usd_4000_pack"], 2),
                     "usd_per_ad": round(c / versions / rate["credits_per_usd_auto_refill"], 3)})
    out = {"at": dt.datetime.now().isoformat(timespec="minutes"), "seconds": seconds, "concepts_per_brand": concepts,
           "versions_per_concept": versions, "brands": brands, "balance": balance(),
           "spend_floor": TIERS["spend_floor_credits"], "rows": rows}
    return out


# ---------- plan (writing) ----------
def _winner_text(brand):
    w = load(REPO / "brands" / brand / "winner.json") or {}
    run = Path(ST.WRITING) / str(w.get("winner") or "")
    parts = []
    for stage, cap in (("1-teardown.md", 14000), ("3-injection.md", 6000)):
        f = run / "stages" / stage
        if f.is_file():
            parts.append(f"### {stage}\n" + f.read_text()[:cap])
    return w, "\n\n".join(parts) or "(no teardown on file for the winner)"


def _bank_text(brand, k, limit=60):
    out = []
    q = [sys.executable, str(REPO / "components" / "language-layer" / "query_language.py"), "--brand", brand, "--limit", str(limit)]
    if k.get("avatar"):
        q += ["--avatar", k["avatar"]]
    r = subprocess.run(q, capture_output=True, text=True, timeout=300)
    out.append(r.stdout.strip() or "(language bank returned nothing)")
    bank = load(REPO / "runs" / "winners" / brand / "bank.json") or {}
    rows = sorted(bank.get("rows") or [], key=lambda r: -max([x.get("purchases") or 0 for x in r.get("snapshots") or []] or [0]))[:10]
    if rows:
        out.append("## Banked ad copy (the brand's proven ads, by purchases)")
        for r in rows:
            hook = ((r.get("words") or {}).get("hook") or "")[:300]
            out.append(f"- [{r.get('id')}] headline: {r.get('headline') or ''} | body: {(r.get('body') or '')[:400]} | spoken hook: {hook}")
    return "\n".join(out)


def _kit_text(k):
    lines = [f"product: {k.get('product_name')} — used: {k.get('product_use')}"]
    for c in k.get("cast") or []:
        lines.append(f"cast {c['name']} ({c.get('group', '')}): {c.get('looks', '')} · fits: {c.get('role', '')}")
    for s in k.get("sets") or []:
        lines.append(f"set {s['name']}: {s.get('looks', '')}")
    return "\n".join(lines)


def _claude(prompt, timeout=900):
    r = subprocess.run([CLAUDE, "-p", "--output-format", "text"], input=prompt, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"claude: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


def _json_from(text):
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {"concepts": []}


def plan(brand, n, formats=None, date=None, chunk=5):
    date = date or dt.date.today().strftime("%Y%m%d")
    formats = formats or list(FORMATS)
    k = kit(brand)
    w, winner = _winner_text(brand)
    bank = _bank_text(brand, k)
    batch = f"vol-{date}-{brand}"
    bd = batch_dir(batch)
    bd.mkdir(parents=True, exist_ok=True)
    base = (HERE / "prompts" / "concepts.md").read_text()
    jobs = []
    for i in range(0, n, chunk):
        m = min(chunk, n - i)
        fm = [formats[(i + j) % len(formats)] for j in range(m)]
        p = (base + "\n\n# FORMATS\n" + json.dumps({f: FORMATS[f] for f in sorted(set(fm))}, indent=1)
             + f"\n\n# WINNER ({w.get('label') or w.get('winner')})\n" + winner
             + "\n\n# BANK\n" + bank + "\n\n# KIT\n" + _kit_text(k)
             + f"\n\n# N\nWrite {m} concepts, in these formats in this order: {', '.join(fm)}. "
             + f"Number them c{i + 1:02d} to c{i + m:02d}.\n")
        jobs.append((i, p))
    (bd / "prompts").mkdir(exist_ok=True)
    concepts = []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_claude, p): (i, p) for i, p in jobs}
        for f in cf.as_completed(futs):
            i, p = futs[f]
            (bd / "prompts" / f"write-{i + 1:02d}.md").write_text(p)
            raw = f.result()
            (bd / "prompts" / f"write-{i + 1:02d}.out.txt").write_text(raw)
            concepts += _json_from(raw).get("concepts") or []
    concepts.sort(key=lambda c: c.get("id", ""))
    known = {c["name"] for c in k.get("cast") or []}
    for c in concepts:
        c["cast"] = [x for x in c.get("cast") or [] if x in known] or [next(iter(known))] if known else []
    save(bd / "batch.json", {"batch": batch, "brand": brand, "date": date, "winner": w, "formats": formats,
                             "made_at": dt.datetime.now().isoformat(timespec="minutes"), "concepts": concepts})
    return batch


# ---------- make (the takes) ----------
def _refs(k, c):
    files = []
    by = {x["name"]: x for x in (k.get("cast") or []) + (k.get("sets") or [])}
    for name in c.get("cast") or []:
        if name in by:
            files.append(by[name]["file"])
    files += [p["file"] for p in k.get("product_refs") or []][:2]
    s = by.get(c.get("set"))
    if s:
        files.append(s["file"])
    return [str(resolve(f)) for f in files if resolve(f).is_file()][:7]


def _take_prompt(c, k):
    look = {x["name"]: x.get("looks", "") for x in k.get("cast") or []}
    who = "; ".join(f"{n} = {look.get(n, '')}" for n in c.get("cast") or [])
    lyrics = (" Sung lyrics, in order: " + " / ".join(c["lyrics"])) if c.get("lyrics") else ""
    return (f"{c.get('take_prompt', '').strip()} People, matching the reference pictures in order: {who}. "
            f"Product: {k.get('product_name')}, as in its reference pictures.{lyrics} Vertical 9:16 phone video, "
            f"natural light, no on-screen text, no captions, no logos other than the product's own.")


def _args(tier, prompt, refs, seconds):
    t = TIERS["tiers"][tier]
    a = [t["job"], "--prompt", prompt, "--duration", seconds, "--resolution", t["resolution"],
         "--aspect_ratio", TIERS["aspect"]]
    if t.get("mode"):
        a += ["--mode", t["mode"]]
    if t.get("draft"):
        a += ["--draft", "true"]
    for r in refs:
        a += ["--image-references", r]
    return a


_UPLOADS = {}


def _upload(f, tries=3):
    """A kit picture uploaded once per run (the same cast sheet feeds many takes); a failed upload is tried again."""
    if f in _UPLOADS:
        return _UPLOADS[f]
    err = None
    for _ in range(tries):
        try:
            _UPLOADS[f] = hf("upload", "create", f)["id"]
            return _UPLOADS[f]
        except RuntimeError as e:
            err = e
    raise err


def _make_one(batch, c, k, tier, seconds, guard):
    d = concept_dir(batch, c["id"]) / "take"
    d.mkdir(parents=True, exist_ok=True)
    if (d / "take.mp4").is_file():
        return {"id": c["id"], "state": "made before"}
    prompt = _take_prompt(c, k)
    try:
        ids = [_upload(f) for f in _refs(k, c)]
        args = _args(tier, prompt, ids, seconds)
        cost = float(hf("generate", "cost", *args)["credits"])
    except Exception as e:  # noqa: BLE001  nothing was sent: the concept is reported and the batch goes on
        save(d / "sent.json", {"state": "failed", "error": f"before sending: {str(e)[:300]}", "prompt": prompt})
        return {"id": c["id"], "state": "failed", "error": str(e)[:200]}
    if not guard(cost):
        save(d / "sent.json", {"state": "held", "why": "spend floor", "credits": cost, "prompt": prompt})
        return {"id": c["id"], "state": "held (spend floor)", "credits": cost}
    rec = {"tier": tier, "route": f"{args[0]}@{TIERS['tiers'][tier]['resolution']}", "prompt": prompt,
           "refs": _refs(k, c), "uploads": ids, "credits": cost, "sent_at": dt.datetime.now().isoformat(timespec="seconds")}
    save(d / "sent.json", {**rec, "state": "sent"})
    try:
        job = hf("generate", "create", *args)
        jid = job[0] if isinstance(job, list) else (job or {}).get("id")
        jid = jid.get("id") if isinstance(jid, dict) else jid
        res = hf("generate", "wait", jid, timeout=3600)
        url = res.get("result_url") or ((res.get("results") or [{}])[0] or {}).get("url")
        if str(res.get("status", "")).lower() != "completed" or not url:
            raise RuntimeError(f"job {jid} ended {res.get('status')}")
        subprocess.run(["curl", "-sfL", "-o", str(d / "take.mp4"), url], check=True, timeout=600)
        save(d / "sent.json", {**rec, "state": "made", "job": jid, "url": url})
        return {"id": c["id"], "state": "made", "credits": cost}
    except Exception as e:  # noqa: BLE001  one refused or failed take never stops the batch
        save(d / "sent.json", {**rec, "state": "failed", "error": str(e)[:400]})
        return {"id": c["id"], "state": "failed", "error": str(e)[:200]}


def make(batch, tier=None, floor=None, max_credits=None, workers=4, only=None):
    b = load(batch_dir(batch) / "batch.json")
    k = kit(b["brand"])
    tier = tier or TIERS["default_tier"]
    floor = TIERS["spend_floor_credits"] if floor is None else floor
    seconds = TIERS["seconds"]
    import threading
    lock = threading.Lock()
    spent = {"credits": 0.0}

    def guard(cost):
        with lock:
            if max_credits is not None and spent["credits"] + cost > max_credits:
                return False
            if balance() - cost < floor:
                return False
            spent["credits"] += cost
            return True

    cs = [c for c in b["concepts"] if not only or c["id"] in only]
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(lambda c: _make_one(batch, c, k, tier, seconds, guard), cs))
    b.setdefault("make", []).append({"at": dt.datetime.now().isoformat(timespec="minutes"), "tier": tier,
                                      "floor": floor, "spent": spent["credits"], "results": res})
    save(batch_dir(batch) / "batch.json", b)
    return res


# ---------- edit (versions) ----------
def _font(size):
    from PIL import ImageFont
    cands = [os.environ.get("AD_VOLUME_FONT")] + [str(r / "components/video-edit/looks/fonts" / f) for r in
             [REPO, Path(os.environ.get("VIDEO_STUDIO_CODE", REPO))] for f in
             ("proxima-nova-semibold/semibold.woff2", "tiktok-sans/latin-2.woff2")]
    for f in cands:
        if f and Path(f).is_file():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size)


def _text_png(text, out, y_frac=0.30, size=86, box=False):
    """White words, black outline, centred, wrapped to the frame (the platform caption look)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    f = _font(size)
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if dr.textlength(t, font=f) > W * 0.84 and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = t
    lines.append(cur)
    lh = int(size * 1.18)
    y = int(H * y_frac) - lh * len(lines) // 2
    if box:
        dr.rounded_rectangle([60, y - 30, W - 60, y + lh * len(lines) + 30], 28, fill=(0, 0, 0, 150))
    for ln in lines:
        x = (W - dr.textlength(ln, font=f)) / 2
        dr.text((x, y), ln, font=f, fill="white", stroke_width=max(4, size // 12), stroke_fill="black")
        y += lh
    img.save(out)
    return out


def _render(take, out, hook_png=None, end_png=None, hook_s=2.5, end_s=2.0):
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", take],
                               capture_output=True, text=True).stdout.strip() or 12)
    ins, fl, last = ["-i", str(take)], [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[v0]"], "v0"
    n = 1
    for png, en in ((hook_png, f"between(t,0,{hook_s})"), (end_png, f"gte(t,{max(0, dur - end_s):.2f})")):
        if png:
            ins += ["-i", str(png)]
            fl.append(f"[{last}][{n}:v]overlay=0:0:enable='{en}'[v{n}]")
            last, n = f"v{n}", n + 1
    has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                     "-of", "csv=p=0", take], capture_output=True, text=True).stdout.strip())
    amap = ["-map", "0:a", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-ar", "48000"] if has_audio else ["-an"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fl), "-map", f"[{last}]", *amap,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
                    "-movflags", "+faststart", str(out)], check=True, timeout=600)
    return out


def edit(batch):
    b = load(batch_dir(batch) / "batch.json")
    done = []
    for c in b["concepts"]:
        cd = concept_dir(batch, c["id"])
        take = cd / "take" / "take.mp4"
        if (load(cd / "take" / "sent.json") or {}).get("state") != "made" or not take.is_file():
            continue                     # a take still downloading, held or failed is not cut
        lay = cd / "layers"
        lay.mkdir(exist_ok=True)
        end = _text_png(c.get("end_card") or "", lay / "end.png", y_frac=0.78, size=64, box=True) if c.get("end_card") else None
        if (cd / "rough-cut-v1-sdr.mp4").is_file() and all((cd / "versions" / h["id"] / f"{cd.name}-{h['id']}.mp4").is_file()
                                                           for h in c.get("hooks") or []):
            done.append(c["id"])
            continue
        _render(take, cd / "rough-cut-v1-sdr.mp4", hook_png=None, end_png=end)
        for h in c.get("hooks") or []:
            vd = cd / "versions" / h["id"]
            vd.mkdir(parents=True, exist_ok=True)
            png = _text_png(h["text"], lay / f"{h['id']}.png")
            _render(take, vd / f"{cd.name}-{h['id']}.mp4", hook_png=png, end_png=end)
        done.append(c["id"])
    return done


# ---------- studio (every stage's prompt and output, on the Studio) ----------
def _wf_hash(wf):
    keep = {k: wf[k] for k in ("steps", "clock", "sources") if k in wf}
    return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:12]


def studio(batch):
    b = load(batch_dir(batch) / "batch.json")
    k = kit(b["brand"])
    for c in b["concepts"]:
        cd = concept_dir(batch, c["id"])
        sent = load(cd / "take" / "sent.json") or {}
        brief = {"schema": "scene-canvas-brief/v1", "brief": f"{batch}-{c['id']}", "number": f"{batch}-{c['id']}",
                 "title": f"{FORMATS.get(c.get('format'), {}).get('name', c.get('format'))} · {c.get('title', '')}",
                 "lane": "volume", "batch": batch, "brand": b["brand"], "product": k.get("product"),
                 "order": ["S1"], "picks": {"S1": "take-1"}, "cast": c.get("cast"),
                 "hooks": [h["id"] for h in c.get("hooks") or []],
                 "deliver": {"width": W, "height": H, "video": "h264", "audio": "aac 48 kHz"},
                 "stages_page": "stages.html"}
        if c.get("brief"):
            brief["brief_key"] = f"{b['brand']}_{k.get('product')}_{c['brief']}"     # the numbered brief: links the card
        save(cd / "brief.json", brief)
        steps = [
            {"id": "write", "tool": "volume.write", "model": "claude (signed-in plan)", "prompt": "batch prompts/ (see stages page)",
             "seed": None, "inputs": {"winner": (b.get("winner") or {}).get("winner"), "format": c.get("format"),
                                      "bank_ids": c.get("bank_ids")},
             "params": {}, "note": f"{c.get('premise', '')} · angle: {c.get('angle', '')}"},
            {"id": "take", "tool": "volume.take", "model": sent.get("route"), "prompt": sent.get("prompt"), "seed": None,
             "inputs": {"refs": [Path(r).name for r in sent.get("refs") or []]},
             "params": {"credits": sent.get("credits"), "tier": sent.get("tier"), "state": sent.get("state")},
             "note": f"{sent.get('state', 'not made')} · {sent.get('credits', '?')} credits"},
            {"id": "edit", "tool": "volume.edit", "model": None, "prompt": None, "seed": None,
             "inputs": {"hooks": {h["id"]: h["text"] for h in c.get("hooks") or []}, "end_card": c.get("end_card")},
             "params": {}, "note": "control + one version per hook: hook words 0-2.5 s, end card last 2 s, -14 LUFS"}]
        wf = {"schema": "scene-workflow/v1", "brief": brief["brief"], "scene": "S1", "take": "take-1",
              "title": c.get("title", ""), "lane": "ai", "roll": "A", "clock": {"locked": True},
              "words": " ".join(bt.get("says", "") for bt in c.get("beats") or []), "steps": steps}
        save(cd / "scenes" / "S1" / "take-1.json", wf)
        cut = cd / "rough-cut-v1-sdr.mp4"
        if cut.is_file():
            od = cd / "scenes" / "S1" / "out" / "take-1"
            od.mkdir(parents=True, exist_ok=True)
            if not (od / "S1.mp4").exists():
                os.link(cut, od / "S1.mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "3", "-i", str(cut), "-frames:v", "1", "-vf",
                            "scale=360:-2", str(od / "S1.jpg")], check=False)
            save(od / "S1.captions.json", {"lines": []})
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                        str(cut)], capture_output=True, text=True).stdout.strip() or 0)
            usd = (sent.get("credits") or 0) / TIERS["read_15_nov_2026"]["credits_per_usd_auto_refill"]
            save(od / "run.json", {"scene": "S1", "take": "take-1", "workflow_hash": _wf_hash(wf),
                                   "ran_at": sent.get("sent_at"), "seconds_to_make": 0, "duration": dur,
                                   "cost_usd": round(usd, 2), "made_by": "ad-volume", "clock_check": None,
                                   "files": {"video": "out/take-1/S1.mp4", "thumb": "out/take-1/S1.jpg",
                                             "captions": "out/take-1/S1.captions.json"}})
        (cd / "stages.html").write_text(_stages_page(b, c, sent, cd))
    (batch_dir(batch) / "index.html").write_text(_batch_page(b))
    return [concept_dir(batch, c["id"]).name for c in b["concepts"]]


CSS = ("body{font:15px/1.45 -apple-system,system-ui,sans-serif;margin:0;padding:16px;background:#111;color:#eee}"
       "h1{font-size:20px}h2{font-size:16px;margin:22px 0 8px}pre{white-space:pre-wrap;background:#1d1d1d;padding:10px;"
       "border-radius:8px;font-size:12.5px;max-height:420px;overflow:auto}.row{display:flex;gap:10px;flex-wrap:wrap}"
       "video{width:180px;border-radius:8px;background:#000}.card{background:#1a1a1a;border-radius:10px;padding:12px;"
       "margin:10px 0}.chip{display:inline-block;background:#2a2a2a;border-radius:20px;padding:2px 9px;margin:2px;font-size:12px}"
       "a{color:#8cf}")


def _stages_page(b, c, sent, cd):
    e = html.escape
    vids = "".join(f"<div><video controls preload=metadata src='{e(p.relative_to(cd).as_posix())}'></video><div class=chip>{e(p.parent.name if p.parent.name != cd.name else 'control')}</div></div>"
                   for p in [cd / "rough-cut-v1-sdr.mp4", *sorted((cd / "versions").glob("*/*.mp4"))] if p.is_file())
    beats = "".join(f"<tr><td>{bt.get('at')}</td><td>{e(bt.get('who', ''))}</td><td>{e(bt.get('does', ''))}</td><td>{e(bt.get('says', ''))}</td></tr>"
                    for bt in c.get("beats") or [])
    return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{e(c.get('title', ''))}</title><style>{CSS}td{{padding:4px 8px;vertical-align:top;border-bottom:1px solid #333}}</style>"
            f"<h1>{e(c['id'])} · {e(c.get('title', ''))}</h1><div><span class=chip>{e(c.get('format', ''))}</span>"
            f"<span class=chip>{e(b['brand'])}</span><span class=chip>{e(sent.get('route') or 'not made')}</span>"
            f"<span class=chip>{e(str(sent.get('credits', '?')))} credits</span></div>"
            f"<h2>1 · Writing — output</h2><div class=card><b>{e(c.get('angle', ''))}</b><br>{e(c.get('premise', ''))}"
            f"<table>{beats}</table><div>Hooks: {''.join('<span class=chip>' + e(h['id'] + ' · ' + h['text']) + '</span>' for h in c.get('hooks') or [])}</div>"
            f"<div>End card: {e(c.get('end_card') or '')}</div><div>Bank lines used: {e(', '.join(c.get('bank_ids') or []))}</div></div>"
            f"<h2>1 · Writing — prompt</h2><p><a href='../{e(b['batch'])}/index.html#prompts'>the batch's writing prompts</a></p>"
            f"<h2>2 · Take — prompt</h2><pre>{e(sent.get('prompt') or '')}</pre>"
            f"<div>References: {''.join('<span class=chip>' + e(Path(r).name) + '</span>' for r in sent.get('refs') or [])}</div>"
            f"<h2>2 · Take — output</h2><div class=row>{'<video controls src=take/take.mp4></video>' if (cd / 'take/take.mp4').is_file() else e(sent.get('state') or 'not made') + ' ' + e(sent.get('error') or '')}</div>"
            f"<h2>3 · Edit — versions</h2><div class=row>{vids}</div>")


def _batch_page(b):
    e = html.escape
    cards = []
    for c in b["concepts"]:
        cd = concept_dir(b["batch"], c["id"])
        sent = load(cd / "take" / "sent.json") or {}
        v = cd / "versions" / ((c.get("hooks") or [{}])[0].get("id") or "H1")
        first = next(iter(sorted(v.glob("*.mp4"))), None)
        cards.append(f"<div class=card><b>{e(c['id'])}</b> · {e(c.get('format', ''))} · {e(c.get('title', ''))}"
                     f" · <span class=chip>{e(sent.get('state') or 'not made')}</span>"
                     f" · <a href='../{e(cd.name)}/stages.html'>stages</a><div class=row>"
                     + (f"<video controls preload=metadata src='../{e(cd.name)}/{e(first.relative_to(cd).as_posix())}'></video>" if first else "")
                     + "</div></div>")
    prompts = "".join(f"<h2>{e(p.name)}</h2><pre>{e(p.read_text()[:20000])}</pre>"
                      for p in sorted((batch_dir(b['batch']) / "prompts").glob("*")))
    made = sum(1 for c in b["concepts"] if (concept_dir(b["batch"], c["id"]) / "take/take.mp4").is_file())
    spent = sum(m.get("spent", 0) for m in b.get("make") or [])
    return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{e(b['batch'])}</title><style>{CSS}</style><h1>{e(b['batch'])}</h1>"
            f"<div><span class=chip>{len(b['concepts'])} concepts</span><span class=chip>{made} takes made</span>"
            f"<span class=chip>{spent:g} credits</span></div>{''.join(cards)}<a id=prompts></a><h2>Writing prompts and outputs</h2>{prompts}")


# ---------- file (approval page) ----------
def _brief_for(batch, b, c, k):
    """One concept = one brief = one card (the approval page holds one waiting card per brief, at most 10 videos).
    The concept is filed as a lane run (runs/ad-volume/<brand>/<concept>) and numbered by the brief register, which
    also reads its angle; nothing is coined here."""
    run = REPO / "runs" / "ad-volume" / b["brand"] / f"{batch}-{c['id']}"
    (run / "deliverable").mkdir(parents=True, exist_ok=True)
    save(run / "run.json", {**(load(run / "run.json") or {}), "brand": b["brand"], "product": k.get("product"),
                            "avatar": k.get("avatar"), "opened": b.get("made_at"), "format": c.get("format"),
                            "winner": (b.get("winner") or {}).get("winner"), "studio": concept_dir(batch, c["id"]).name})
    beats = "\n".join(f"- {bt.get('at')} {bt.get('who', '')}: {bt.get('does', '')} — \"{bt.get('says', '')}\"" for bt in c.get("beats") or [])
    hooks = "\n".join(f"- {h['id']}: {h['text']}" for h in c.get("hooks") or [])
    (run / "deliverable" / "brief.md").write_text(
        f"# {c.get('title', c['id'])}\n\nFormat: {c.get('format')}\nAngle: {c.get('angle', '')}\nPremise: {c.get('premise', '')}\n\n"
        f"## Beats\n{beats}\n\n## Hooks\n{hooks}\n\nEnd card: {c.get('end_card', '')}\nBank lines: {', '.join(c.get('bank_ids') or [])}\n")
    sys.path.insert(0, str(REPO / "components" / "image-teardown" / "tools"))
    sys.path.insert(0, str(REPO / "components" / "naming"))
    import briefs as BR
    bid, rec = BR.open_brief(str(run.relative_to(REPO)), b["brand"], product=k.get("product"), avatar=k.get("avatar"),
                             kind="video-ai")
    num = rec.get("brief") or bid
    _words(b["brand"], num, k.get("product"), run / "deliverable" / "brief.md")
    return num


def _words(brand, brief, product, source):
    """The card's primary texts, headlines and descriptions: the house copywriter, reading this concept's brief."""
    sys.path.insert(0, str(REPO / "components" / "meta-upload"))
    import card_words as CW
    w, _ = CW.for_brief(brand, brief, product=product)
    if not CW.missing(w):
        return
    subprocess.run([sys.executable, str(REPO / "components" / "copywriter" / "machine" / "brief_words.py"), "--brand", brand,
                    "--brief", brief, "--product", product, "--source", str(source.relative_to(REPO))],
                   cwd=REPO, check=False, timeout=1800)


def file(batch, go=False):
    sys.path.insert(0, str(REPO / "components" / "meta-upload"))
    import feed_video as FV
    b = load(batch_dir(batch) / "batch.json")
    k = kit(b["brand"])
    out = []
    day_ = b.get("date") or dt.date.today().strftime("%Y%m%d")
    for i, c in enumerate(b["concepts"]):
        cd = concept_dir(batch, c["id"])
        control = cd / "rough-cut-v1-sdr.mp4"
        if not control.is_file():
            out.append({"id": c["id"], "state": "no cut"})       # a held or failed take is not numbered or filed
            continue
        card_batch = f"batch-{day_[:4]}-{day_[4:6]}-{day_[6:]}-a"
        try:
            brief_id = (_brief_for(batch, b, c, k) if go else c.get("brief") or k.get("brief") or "none")
        except BaseException as e:  # noqa: BLE001  a concept the register will not number is reported, not hidden
            out.append({"id": c["id"], "state": "refused", "why": f"brief register: {str(e)[:250]}"})
            continue
        if go:
            c["brief"] = brief_id
        masters = [control] + sorted((cd / "versions").glob("*/*.mp4"))
        try:
            p, src = FV.file_master(b["brand"], brief_id, k.get("product"), card_batch,
                                    [str(m) for m in masters], dry_run=not go, production=cd.name,
                                    replace=bool(c.get("brief")))
            out.append({"id": c["id"], "brief": brief_id, "state": p.get("state"), "card": str(p.get("target") or ""), "words": src,
                        "covers": p.get("covers_from"), "checks": p.get("checks") or p.get("cover_checks")})
        except BaseException as e:  # noqa: BLE001  a refused card is reported with its reason, never hidden
            out.append({"id": c["id"], "state": "refused", "why": str(e)[:300]})
    b.setdefault("file", []).append({"at": dt.datetime.now().isoformat(timespec="minutes"), "go": go, "results": out})
    save(batch_dir(batch) / "batch.json", b)
    return out


# ---------- the daily runner ----------
def day(brands, n, formats=None, tier=None, floor=None, max_credits=None, go=False):
    report = {}
    for brand in brands:
        batch = plan(brand, n, formats)
        made = make(batch, tier=tier, floor=floor, max_credits=max_credits)
        edit(batch)
        studio(batch)
        filed = file(batch, go=go)
        studio(batch)                    # again: each production now carries its numbered brief
        report[brand] = {"batch": batch, "made": made, "filed": filed}
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("price"); p.add_argument("--concepts", type=int, default=40); p.add_argument("--versions", type=int, default=5)
    p.add_argument("--brands", type=int, default=2)
    p = sp.add_parser("plan"); p.add_argument("brand"); p.add_argument("--n", type=int, default=10); p.add_argument("--formats")
    p.add_argument("--date")
    p = sp.add_parser("make"); p.add_argument("batch"); p.add_argument("--tier"); p.add_argument("--floor", type=float)
    p.add_argument("--max-credits", type=float); p.add_argument("--only")
    for name in ("edit", "studio"):
        p = sp.add_parser(name); p.add_argument("batch")
    p = sp.add_parser("file"); p.add_argument("batch"); p.add_argument("--go", action="store_true")
    p = sp.add_parser("day"); p.add_argument("brands", nargs="+"); p.add_argument("--n", type=int, default=10)
    p.add_argument("--formats"); p.add_argument("--tier"); p.add_argument("--floor", type=float)
    p.add_argument("--max-credits", type=float); p.add_argument("--go", action="store_true")
    a = ap.parse_args(argv)
    fm = a.formats.split(",") if getattr(a, "formats", None) else None
    r = {"price": lambda: price(a.concepts, a.versions, a.brands),
         "plan": lambda: plan(a.brand, a.n, fm, a.date),
         "make": lambda: make(a.batch, a.tier, a.floor, a.max_credits, only=a.only.split(",") if a.only else None),
         "edit": lambda: edit(a.batch), "studio": lambda: studio(a.batch), "file": lambda: file(a.batch, a.go),
         "day": lambda: day(a.brands, a.n, fm, a.tier, a.floor, a.max_credits, a.go)}[a.cmd]()
    print(json.dumps(r, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
