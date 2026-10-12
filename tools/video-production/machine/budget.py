"""THE BUDGET — what a brief will likely cost to produce, before anything is spent (2026-10-02).

Made from the storyboard (or, before there is one, roughly from the brief), with
every rate read from providers.json. No model is called, nothing is spent.

    python3 budget.py <production run | brief.md>

prints one summary line and writes <run>/BUDGET.md:

    LOW / LIKELY / HIGH in dollars (clips also in credits), broken out by
      pictures   count x tries per kept picture x $ per picture
      voices     characters of the lines x tries x the voice rate
      clips      billed seconds x tries x the clip door's rate
    a clip-model comparison — the ruled clip route first (Omni Flash on fal at
      the route's resolution, providers.json direct.omni_route, 3 Oct), then the
      older doors for reference (Seedance 720p / 1080p, MiniMax 2K, a mix)
    what this run has ALREADY spent on pictures, when it has made any
    the assumptions, one short plain list

storyboard_plan.build() runs this every time it writes STORYBOARD.md.
Brand-agnostic: every count comes from the run's own files.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_budget_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


platform = _load("platform")
mi = _load("model_inputs")

LEVELS = ("low", "likely", "high")

# ------------------------------------------------------------ measured tries
# How many calls it takes to keep one picture. Measured on the house's first
# full storyboard run (2 Oct 2026): the final round made 43 image calls for 22
# kept pictures (zone fixes and product fixes included) -> ~2 a picture; the
# whole day, rules still moving, came to ~121 GPT Image calls for 22 kept
# (~5.5) plus a withdrawn round on another model. LOW is every picture right
# the first time.
PICTURE_TRIES = {"low": 1.0, "likely": 2.0, "high": 5.5}
# Clips: no clip had been billed on a storyboard run when this was written —
# a guess until the ledger has clip rows: right first time / half need a
# second take / most need a second or third.
CLIP_TRIES = {"low": 1.0, "likely": 1.5, "high": 2.5}
# Voices: a line is re-read when the words, pitch or accent check fails.
VOICE_TRIES = {"low": 1.0, "likely": 1.5, "high": 3.0}

# ------------------------------------------------------------ picture tokens
# Text tokens in one picture prompt (the house prompts run ~3,000-10,000
# characters; ~4 characters a token).
PROMPT_TOKENS = {"low": 800, "likely": 1500, "high": 2500}
# References on a picture when the run has no element-refs.json yet (the
# elements + the swipe shot it copies).
REFS_DEFAULT = {"low": 3, "likely": 4, "high": 5}
OUT_TOKENS_FALLBACK = 2489          # providers.json direct.openai.proven note, if it cannot be read
# Voice rate fallback when providers.json carries none for the voice model:
# providers/research/elevenlabs.md — ~$0.10 per 1,000 characters (v3 /
# multilingual), and the monthly plan includes 220,000 characters.
VOICE_USD_PER_1K_FALLBACK = 0.10


def image_input_tokens(w: int, h: int) -> int:
    """OpenAI's documented image-input token math for GPT Image (vision cost
    table, gpt-image-1 row: 65 base + 129 a 512-px tile, after fitting the
    image inside 2048 x 2048 and scaling its short side to 768). Not in
    providers/research/gpt-image-2.md — an assumption, stated on the page."""
    s = min(1.0, 2048 / max(w, h))
    w, h = w * s, h * s
    s = 768 / min(w, h)
    w, h = w * s, h * s
    return 65 + 129 * math.ceil(w / 512) * math.ceil(h / 512)


# ------------------------------------------------------------ small helpers

def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def usd(x: float) -> str:
    return f"${x:,.2f}"


def mmss(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


# ------------------------------------------------------------ what gets made

def scenes_of(run: Path, sb: dict) -> list[dict]:
    """The brief's scenes: the storyboard's brief, else the run's plan.json."""
    b = sb.get("brief")
    for p in ([Path(b), run / Path(b).name] if b else []):
        if p.is_file():
            try:
                body = p.read_text()
                found = re.findall(r"```json\s*\n(.*?)\n```", body, re.S)
                if found:
                    sc = json.loads(found[-1]).get("scenes")
                    if sc:
                        return sc
            except (OSError, ValueError):
                pass
    return (_read(run / "plan.json", {}) or {}).get("scenes") or []


def _talks(sc: dict) -> bool:
    return bool(sc.get("to_camera")) and bool(str(sc.get("voice") or sc.get("say") or "").strip())


def count(sb: dict, scenes: list[dict]) -> dict:
    """{"pictures": [ids], "clips": [{id, seconds, talking}], "sections": n}
    — the same pictures and clips clips_plan makes from this storyboard."""
    cp = _load("clips_plan")
    by_id = {s.get("id"): s for s in scenes}
    pics, clips = [], []
    for g in sb.get("sections") or []:
        if g.get("reuses"):
            continue
        p = cp.picture_ids(g)
        own = [o["id"] for o in p["own"]]
        pics += [x for x in [p["start"], p["end"]] + own if x]
        if not g.get("clips"):
            continue
        clock = cp.section_clock(g)
        for ci, c in enumerate(g["clips"], 1):
            scs = [by_id.get(s) or {"id": s} for s in c.get("scenes") or []]
            ts = [clock[s] for s in c.get("scenes") or [] if s in clock]
            sec = (max(z for _, z in ts) - min(a for a, _ in ts)) if ts else float(c.get("seconds") or 0)
            talking = any(_talks(s) for s in scs) if scenes else "lip" in str(g.get("maker") or "")
            clips.append({"id": f"{g['id']}-C{ci}", "seconds": round(sec, 2), "talking": talking})
        # a picture for another camera set-up inside the section is its own clip
        wins = cp.shot_windows(g) if g.get("maker") == "motion transfer" else []
        for o in p["own"]:
            ks = [w for w in wins if w[0] in o["drives"]]
            if not ks:
                continue
            t0, t1 = min(a for _, a, _ in ks), max(z for _, _, z in ks)
            on = [by_id.get(s) or {} for s, (a, z) in clock.items() if z > t0 and a < t1]
            clips.append({"id": f"{g['id']}-{o['copies']}", "seconds": round(t1 - t0, 2),
                          "talking": any(_talks(s) for s in on)})
    return {"pictures": pics, "clips": clips, "sections": len(sb.get("sections") or [])}


def rough_storyboard(scenes: list[dict]) -> dict:
    """Before the storyboard exists: one section per scene, one picture each,
    one clip per scene that has seconds (cards get a picture, no clip)."""
    secs = []
    for i, s in enumerate(scenes, 1):
        card = s.get("kind") == "card" or s.get("type") == "card"
        sec = float(s.get("seconds") or 0)
        secs.append({"id": f"G{i:02d}", "scenes": [s["id"]], "maker": "lip-sync" if _talks(s) else "from the brief",
                     "frames": [{"what": "card background" if card else "start frame", "from": s["id"]}],
                     "clips": [] if card or not sec else [{"scenes": [s["id"]], "seconds": sec}],
                     "voice": {s["id"]: sec} if sec and not card else {}})
    return {"sections": secs}


def characters(run: Path, scenes: list[dict]) -> int:
    lines = _read(run / "lines.json", None)
    if isinstance(lines, dict) and lines:
        return sum(len(str(v)) for v in lines.values())
    return sum(len(str(s.get("voice") or s.get("say") or "")) for s in scenes)


# ------------------------------------------------------------ rates

def credit_usd(reg: dict) -> float | None:
    """$ a Higgsfield credit — the same arithmetic platform.estimate uses."""
    per = (reg.get("credits_per_dollar") or {}).get("higgsfield")
    return 1 / float(per) if per else None


def picture_model(reg: dict) -> str:
    return ((reg.get("doors") or {}).get("still") or {}).get("model") or "gpt-image-2.5-sunburst"


def out_tokens(reg: dict, model: str) -> int:
    note = str((((reg.get("direct") or {}).get("openai") or {}).get("proven") or {}).get(model) or "")
    m = re.search(r"on ([\d,]+) tokens", note)
    return int(m.group(1).replace(",", "")) if m else OUT_TOKENS_FALLBACK


def ref_size(reg: dict) -> tuple[int, int]:
    size = str((((reg.get("direct") or {}).get("openai") or {}).get("params") or {}).get("size") or "1024x1536")
    w, h = (int(x) for x in size.split("x"))
    return w, h


def refs_per_picture(run: Path) -> dict:
    """References a picture carries: the run's element-refs.json (+1, the
    blurred swipe shot every copied picture carries), else the default."""
    er = _read(run / "element-refs.json", None)
    ns = [len(v) for v in er.values() if isinstance(v, list)] if isinstance(er, dict) else []
    if not ns:
        return dict(REFS_DEFAULT)
    return {"low": min(ns) + 1, "likely": round(statistics.mean(ns) + 1, 1), "high": max(ns) + 1}


def picture_usd(reg: dict, run: Path) -> dict:
    """$ one picture call, LOW/LIKELY/HIGH, from the door's token rates."""
    model = picture_model(reg)
    m = reg["models"].get(model) or {}
    r = next((x for x in m.get("rates") or [] if x.get("usd_per_m_out")), None)
    refs = refs_per_picture(run)
    w, h = ref_size(reg)
    per_ref = image_input_tokens(w, h)
    out_t = out_tokens(reg, model)
    res = {"model": model, "refs": refs, "per_ref_tokens": per_ref, "out_tokens": out_t,
           "usd_in": (r or {}).get("usd_per_m_in"), "usd_out": (r or {}).get("usd_per_m_out")}
    for lv in LEVELS:
        if r:
            tin = PROMPT_TOKENS[lv] + refs[lv] * per_ref
            res[lv] = round(tin / 1e6 * r.get("usd_per_m_in", 0) + out_t / 1e6 * r["usd_per_m_out"], 4)
        else:
            job = next((x.get("usd_per_job") for x in m.get("rates") or [] if x.get("usd_per_job")), None)
            res[lv] = float(job or 0)
    # the ledger records the real $ of every picture from 2026-10-02 on — once
    # a run has any, its average is the LIKELY figure
    real = [x["usd"] for x in _read(run / "ledger.json", []) or []
            if x.get("model") == model and x.get("tokens") and x.get("usd")]
    if real:
        res["likely"] = round(statistics.mean(real), 4)
        res["measured"] = len(real)
    return res


def voice_rate(reg: dict) -> tuple[float, str]:
    m = (reg.get("models") or {}).get("elevenlabs") or {}
    for r in m.get("rates") or []:
        if r.get("usd_per_1k_chars"):
            return float(r["usd_per_1k_chars"]), f"providers.json ({r.get('read', '?')})"
    return VOICE_USD_PER_1K_FALLBACK, "providers/research/elevenlabs.md (no voice rate in providers.json)"


# ------------------------------------------------------------ the clip options

def clip_options(reg: dict) -> list[dict]:
    """The comparison, each tied to providers.json rows; the ruled door marked."""
    ruled_m, ruled_r = mi.model_of("motion"), mi.fixed_resolution("motion")
    tier = (mi.door_params("motion") or {}).get("bitrate_mode")
    opts = [
        {"name": "Seedance 2.5 · 720p", "talking": ("seedance_2_5", "720p", tier), "motion": ("seedance_2_5", "720p", tier)},
        {"name": "Seedance 2.5 · 1080p", "talking": ("seedance_2_5", "1080p", tier), "motion": ("seedance_2_5", "1080p", tier)},
        {"name": "MiniMax H3 · 2K", "talking": ("minimax_h3", "2K", None), "motion": ("minimax_h3", "2K", None)},
        {"name": "Mixed — MiniMax 2K for talking-to-camera, Seedance 720p for motion",
         "talking": ("minimax_h3", "2K", None), "motion": ("seedance_2_5", "720p", tier)},
    ]
    for o in opts:
        o["ruled"] = o["talking"][:2] == o["motion"][:2] == (ruled_m, ruled_r)
    # THE RULED CLIP ROUTE (the owner, 2026-10-03): Omni Flash on fal animates every approved picture
    # (providers.json direct.omni_route). While it is the clips default it is the ruled door here.
    omni = (reg.get("direct") or {}).get("omni_route") or {}
    if omni.get("usd_per_s") and omni.get("resolution"):
        ruled_omni = bool(omni.get("default_for_clips"))
        if ruled_omni:
            for o in opts:
                o["ruled"] = False
        opts.insert(0, {"name": f"Omni Flash · {omni['resolution']} (fal)", "omni": omni, "ruled": ruled_omni})
    if not any(o["ruled"] for o in opts):
        opts.insert(0, {"name": f"{ruled_m} · {ruled_r or 'house'} (the ruled door)", "ruled": True,
                        "talking": (ruled_m, ruled_r, tier), "motion": (ruled_m, ruled_r, tier)})
    return opts


def billed(seconds: float, model: dict, station: str, slug: str) -> list[int]:
    """The seconds a clip is billed for: whole seconds, never under the door's
    floor; a clip past the model's cap is split into equal pieces."""
    lo = model.get("min_seconds") or (mi.duration_span(station, slug) or [4])[0] or 4
    cap = model.get("max_seconds") or 15
    n = max(1, math.ceil(seconds / cap - 1e-9))
    return [int(max(lo, math.ceil(seconds / n - 1e-6))) for _ in range(n)]


def omni_billed(seconds: float, span: list) -> list[int]:
    """Omni's billed seconds: whole seconds a call, within the route's span (3–10 s), a clip past
    the cap split into equal calls — never padded beyond the floor."""
    lo, cap = int(span[0]), int(span[1])
    n = max(1, math.ceil(seconds / cap - 1e-9))
    return [int(min(cap, max(lo, math.ceil(seconds / n - 1e-6)))) for _ in range(n)]


def price_clips(clips: list[dict], opt: dict, reg: dict) -> dict:
    cr = sec = usd_ = 0.0
    missing = []
    if opt.get("omni"):
        om = opt["omni"]
        rate = float(om["usd_per_s"][om["resolution"]])
        for c in clips:
            for b in omni_billed(c["seconds"], om.get("seconds_range") or [3, 10]):
                sec += b
                usd_ += b * rate
        return {"seconds": sec, "credits": 0.0, "usd": round(usd_, 2), "missing": []}
    for c in clips:
        slug, res, tier = opt["talking"] if c["talking"] else opt["motion"]
        m = reg["models"].get(slug) or {}
        st = "talking" if c["talking"] else "motion"
        for b in billed(c["seconds"], m, st, slug):
            e = platform.estimate(m, b, reg, tier, res)
            if not e["rate"] or (e["rate"].get("resolution") not in (None, res)):
                e = platform.estimate(m, b, reg, None, res)
            if e["credits"] is None and e["usd"] is None:
                missing.append(slug)
                continue
            sec += b
            cr += e["credits"] or 0
            usd_ += e["usd"] or 0
    return {"seconds": sec, "credits": round(cr, 1), "usd": round(usd_, 2), "missing": sorted(set(missing))}


# ------------------------------------------------------------ already spent

def _fmt(b: bytes) -> str | None:
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "webp"
    return None


SKIP_DIRS = {"clips", "vo", "batches", "section-fit", "qc-log"}


def _ts(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def spent(run: Path, reg: dict, pic: dict | None = None) -> dict | None:
    """What this run has ALREADY spent on pictures: the ledger's image jobs,
    plus image files on disk the ledger never saw (made after its last row).
    Files are told apart by format: the OpenAI door returns the size/format in
    providers.json direct.openai.params, anything else is the Google image door.
    `-shaped` files are local reshapes (no call), `-before-` files are copies
    of an earlier take — neither is counted as a new call outside the ledger."""
    run = Path(run)
    led = _read(run / "ledger.json", []) or []
    gpt = picture_model(reg)
    goog = ((reg.get("direct") or {}).get("google") or {}).get("image_model") or "gemini-3-pro-image"
    out_fmt = str((((reg.get("direct") or {}).get("openai") or {}).get("params") or {}).get("output_format") or "png")
    stations = {"still", "edit", "cast"}
    img_rows = [r for r in led if (reg["models"].get(r.get("model")) or {}).get("station") in stations]
    times = [t for t in (_ts(r.get("at")) for r in led) if t]
    t_end = (max(times) + timedelta(minutes=2)) if times else None
    files = {}
    for f in run.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        rel = f.relative_to(run).parts
        if rel and rel[0] in SKIP_DIRS:
            continue
        b = f.read_bytes()
        fmt = _fmt(b)
        if not fmt:
            continue
        files.setdefault(hashlib.md5(b).hexdigest(), (f, fmt))
    if not img_rows and not files:
        return None
    out = {}
    for model, want in ((gpt, lambda fmt: fmt == out_fmt), (goog, lambda fmt: fmt != out_fmt)):
        rows = [r for r in img_rows if r.get("model") == model]
        fs = [f for f, fmt in files.values() if want(fmt) and "-shaped" not in f.stem]
        after = [f for f in fs if t_end and "-before-" not in f.stem
                 and datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) > t_end]
        inside = len(fs) - len(after)
        lo = len(rows) + len(after)
        hi = max(len(rows), inside) + len(after)
        if not lo and not hi:
            continue
        real = sum(r["usd"] for r in rows if r.get("usd") and r.get("tokens"))
        m = reg["models"].get(model) or {}
        if model == gpt and pic:
            each = (pic["low"], pic["high"])
        else:
            job = next((x.get("usd_per_job") for x in m.get("rates") or [] if x.get("usd_per_job")), 0) or 0
            each = (job, job)
        out[model] = {"ledger": len(rows), "files": len(fs), "after_ledger": len(after),
                      "calls": (lo, hi), "each": each, "real_usd": round(real, 2),
                      "usd": (round(lo * each[0], 2), round(hi * each[1], 2))}
    return out or None


# ------------------------------------------------------------ the budget

def budget(run: Path, sb: dict | None = None, reg: dict | None = None, brief=None) -> dict:
    run = Path(run)
    reg = reg or platform.registry()
    rough = False
    if sb is None:
        sb = _read(run / "storyboard.json", None)
    scenes = scenes_of(run, {"brief": str(brief)} if brief else (sb or {}))
    if not sb:
        rough = True
        sb = rough_storyboard(scenes)
    n = count(sb, scenes)
    pic = picture_usd(reg, run)
    chars = characters(run, scenes)
    v_rate, v_src = voice_rate(reg)
    opts = clip_options(reg)
    for o in opts:
        o["price"] = price_clips(n["clips"], o, reg)
    ruled = next(o for o in opts if o["ruled"])
    lines = {}
    for lv in LEVELS:
        p = len(n["pictures"]) * PICTURE_TRIES[lv] * pic[lv]
        v = chars / 1000 * v_rate * VOICE_TRIES[lv]
        c = ruled["price"]["usd"] * CLIP_TRIES[lv]
        lines[lv] = {"pictures": round(p, 2), "voices": round(v, 2), "clips": round(c, 2),
                     "clip_credits": round(ruled["price"]["credits"] * CLIP_TRIES[lv]),
                     "total": round(p + v + c, 2)}
    return {"run": str(run), "rough": rough, "count": n, "picture": pic, "chars": chars,
            "voice_rate": v_rate, "voice_src": v_src, "options": opts, "ruled": ruled["name"],
            "lines": lines, "credit_usd": credit_usd(reg), "spent": spent(run, reg, pic)}


def summary(b: dict) -> str:
    L = b["lines"]
    return (f"budget: {usd(L['low']['total'])}–{usd(L['high']['total'])}, likely {usd(L['likely']['total'])} "
            f"(pictures {usd(L['likely']['pictures'])} · voices {usd(L['likely']['voices'])} · "
            f"clips {usd(L['likely']['clips'])} on {b['ruled']}) — BUDGET.md")


def markdown(b: dict, label: str = "") -> str:
    L, n, pic = b["lines"], b["count"], b["picture"]
    talk = sum(1 for c in n["clips"] if c["talking"])
    clip_sec = sum(c["seconds"] for c in n["clips"])
    cu = b["credit_usd"]
    out = [f"# Budget{' — ' + label if label else ''}", "",
           "What this brief will likely cost to make, worked out before anything is made. "
           "No model was called for this page." + (" **Rough** — there is no storyboard yet, so every "
                                                    "scene is counted as its own section." if b["rough"] else ""), "",
           f"**Key:** {n['sections']} sections · {len(n['pictures'])} pictures · {len(n['clips'])} clips "
           f"({talk} talking to camera, {len(n['clips']) - talk} motion) · {mmss(clip_sec)} of clip · "
           f"{b['chars']:,} characters of lines", "",
           "| | Low | Likely | High |", "|---|---|---|---|"]
    out.append(f"| Pictures ({len(n['pictures'])} × "
               f"{PICTURE_TRIES['low']:g} / {PICTURE_TRIES['likely']:g} / {PICTURE_TRIES['high']:g} tries × "
               f"{usd(pic['low'])} / {usd(pic['likely'])} / {usd(pic['high'])} a picture) | "
               + " | ".join(usd(L[lv]["pictures"]) for lv in LEVELS) + " |")
    out.append(f"| Voices ({b['chars']:,} characters × "
               f"{VOICE_TRIES['low']:g} / {VOICE_TRIES['likely']:g} / {VOICE_TRIES['high']:g} tries) | "
               + " | ".join(usd(L[lv]["voices"]) for lv in LEVELS) + " |")
    out.append(f"| Clips on {b['ruled']} ({CLIP_TRIES['low']:g} / {CLIP_TRIES['likely']:g} / "
               f"{CLIP_TRIES['high']:g} tries) | "
               + " | ".join(f"{usd(L[lv]['clips'])} · {L[lv]['clip_credits']:,} cr" for lv in LEVELS) + " |")
    out.append("| **Total** | " + " | ".join(f"**{usd(L[lv]['total'])}**" for lv in LEVELS) + " |")
    out += ["", f"At scale: 10 briefs like this ≈ **{usd(10 * L['likely']['total'])}** "
                f"({usd(10 * L['low']['total'])}–{usd(10 * L['high']['total'])}).", "",
            "## Clips — the same clips on each model", "",
            "| Model | Billed | Credits (one take each) | Low | Likely | High |", "|---|---|---|---|---|---|"]
    for o in b["options"]:
        pr = o["price"]
        mark = " ← the ruled door" if o["ruled"] else ""
        miss = f" (no rate on file for {', '.join(pr['missing'])})" if pr["missing"] else ""
        out.append(f"| {o['name']}{mark}{miss} | {mmss(pr['seconds'])} | {pr['credits']:,.0f} | "
                   + " | ".join(usd(pr["usd"] * CLIP_TRIES[lv]) for lv in LEVELS) + " |")
    sp = b.get("spent")
    if sp:
        out += ["", "## Already spent in this run — pictures", "",
                "| Model | Calls | $ a picture | Spent |", "|---|---|---|---|"]
        for model, s in sp.items():
            lo, hi = s["calls"]
            calls = f"{lo}" if lo == hi else f"{lo}–{hi}"
            each = usd(s["each"][0]) if s["each"][0] == s["each"][1] else f"{usd(s['each'][0])}–{usd(s['each'][1])}"
            spend = usd(s["usd"][0]) if s["usd"][0] == s["usd"][1] else f"{usd(s['usd'][0])}–{usd(s['usd'][1])}"
            out.append(f"| {model} | {calls} | {each} | {spend} |")
        out += ["", "Calls = the jobs on the run's ledger, plus pictures on disk made after the ledger's last "
                    "row; the higher figure counts every distinct picture file when there are more files than "
                    "ledger rows."]
    out += ["", "## Assumptions", "",
            f"- A credit is {('$%.4f' % cu) if cu else '?'} ({round(1 / cu) if cu else '?'} credits a dollar, providers.json). "
            "Clip rates are the latest providers.json reading for that model and resolution.",
            f"- A picture is {pic['model']}: {pic['out_tokens']:,} output tokens (providers.json note) at "
            f"${pic['usd_out']}/M, plus input at ${pic['usd_in']}/M — {PROMPT_TOKENS['low']:,}–{PROMPT_TOKENS['high']:,} "
            f"tokens of prompt and {pic['refs']['low']:g}–{pic['refs']['high']:g} references at "
            f"~{pic['per_ref_tokens']:,} tokens each (OpenAI's image-input math: 65 + 129 a tile; "
            "not in our research notes, so an assumption)."
            + (f" Likely is the average of {pic['measured']} real pictures on this run's ledger." if pic.get("measured") else ""),
            f"- Tries per kept picture {PICTURE_TRIES['low']:g} / {PICTURE_TRIES['likely']:g} / "
            f"{PICTURE_TRIES['high']:g}: measured on the first full storyboard run (2 Oct) — the final round "
            "took ~2 calls a kept picture with zone and product fixes; the whole day, rules still moving, ~5.5.",
            f"- Clip tries {CLIP_TRIES['low']:g} / {CLIP_TRIES['likely']:g} / {CLIP_TRIES['high']:g}: a guess — "
            "no storyboard clip had been billed yet. Each clip is billed in whole seconds, never under the "
            "model's floor (4 s); a clip past a model's cap is split.",
            f"- Voices at ${b['voice_rate']:.2f} per 1,000 characters ({b['voice_src']}); on the monthly plan "
            "these characters are usually already paid for.",
            "- Not counted: product kits and the QC reviewer calls (small — cents a run, no rate on file), "
            "music and sound effects."]
    return "\n".join(out) + "\n"


def write(run, sb: dict | None = None, reg: dict | None = None, brief=None) -> dict:
    """Work the budget out and write <run>/BUDGET.md; returns the budget."""
    run = Path(run)
    b = budget(run, sb, reg, brief)
    (run / "BUDGET.md").write_text(markdown(b, run.name))
    b["line"] = summary(b)
    return b


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("target", help="a production run folder, or a brief (.md) inside one")
    a = ap.parse_args(argv)
    t = Path(a.target)
    run = t if t.is_dir() else t.parent
    b = write(run, brief=t if t.is_file() else None)
    print((run / "BUDGET.md").read_text())
    print(b["line"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
