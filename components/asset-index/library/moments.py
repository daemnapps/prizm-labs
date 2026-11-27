#!/usr/bin/env python3
"""moments.py — the clean moments inside every clip of a brand's footage, found ONCE when footage enters the index,
so editing is a lookup, not a measurement (owner rulings 16-17 Nov 2026: editing is frame by frame by default; clean
edits, no stray cuts or flashes, no awkward pauses; Real picks only from footage we have; the asset index is the goal
and editing leverages it).

THE PASS, per scene row of the library (library.json), our footage only:
  1. Read the scene by RANGE (only its seconds): the clip's local index proxy when the index already holds one (same
     clock, nothing fetched), else straight from Shared Assets by the key (gdrive-creator engine.media_request, ffmpeg
     -headers). A clip is never downloaded whole and nothing but a small strip picture is kept.
  2. One ffmpeg pass gives the motion per frame at 10 fps (mean change on a 32x18 grey copy, 0..255) and the shot
     changes the scene detector sees. The scene is split at its real cuts: the index's cuts.json, the measured ones,
     and sudden motion jumps (a frame far past the scene's usual motion), each padded by PAD.
  3. Each unbroken stretch (a long one in pieces of at most PIECE seconds) keeps its busiest 1.5-3 s window.
  4. The team's vision judge (video-production machine/vision_judge.py, the one door) looks at four frames of each
     window, a clip's moments in one ask, with the prompt in components/asset-index/prompts/moments-look-v<N>-owner.md:
     product in use (which product), text laid over the video, blur or a transition, dead time, people on screen.
     Scenes the check pass already marked as carrying burned-in text keep that mark and are not sent (they never play).
Writes runs/asset-index/<brand>/library/moments/: moments.jsonl (one row per moment), motion.jsonl (one row per scene:
its motion and cuts, so a shot of any length can be placed without reading the clip again), strips/ (the four-frame
pictures), runs.json. Resumable: a scene already read is skipped; a moment already judged is not asked again.

    python3 moments.py run  --brand <brand> --dry-run            # count, time and cost first; reads and sends nothing
    python3 moments.py run  --brand <brand> --budget 20 [--limit N] [--workers 8] [--no-judge]
    python3 moments.py find --brand <brand> "man scrubs face with the brush" --seconds 2 [--product flex]

For callers (the Video Studio, the chain): find(brand, words, seconds, need_product=...) -> clean moments of the right
length, best first; place(brand, clip, start, need) -> where in a clip a shot starts on a clean moment; look_at(brand,
clip, start, need) -> the judge's answers for that stretch; known(brand, clip) -> has this clip been read.
Brand-agnostic: products and their looks come from the brand's brand-vocabulary.json.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import library as LIB  # noqa: E402

FPS = 10              # motion is read at this many frames a second
MIN_W = 1.5           # a moment is at least this long; a shorter unbroken stretch is not a moment
MAX_W = 3.0           # and at most this long (b-roll plays at most 2.5 s, the end card 3 s)
PIECE = 8.0           # a longer unbroken stretch gives one moment per piece of at most this many seconds
PAD = 0.35            # nothing starts or ends within this of a cut or a whip (the chain's shot_timing.PAD)
SCENE_T = 0.25        # the scene detector's score that counts as a shot change (cuts.py's)
JUMP_MIN, JUMP_X = 30.0, 4.0   # a frame's change above both this and JUMP_X x the scene's median is a cut (shot_timing)
AT = (0.1, 0.37, 0.63, 0.9)    # where in the window the four judged frames sit (the chain's frame_look.AT)
PER_ASK = 8           # moments in one judge ask
NOT_OURS = ("/intake/", "/archive/", "/references/", "/swipe/", "/competitors/")   # never a shot of ours (shot_fill)
# measured 17 Nov 2026 on brand_a (see runs.json "measured"); the dry run's estimate, the budget's meter
EST_USD_ASK = 0.02    # one ask's fixed part (prompt + thinking), Gemini 3.1 Pro: 8 strips cost $0.053
EST_USD_STRIP = 0.0042  # each strip picture in an ask (about 1,100 picture tokens + its answer)
EST_READ_X = 200.0    # seconds of footage read per wall second per worker from the proxy
EST_DRIVE_X = 0.4     # ... and by range from the Drive on a 13 Mbps line (10 Mbps phone footage)
EST_ASK_S = 20.0      # one ask's wall seconds


def mdir(brand: str) -> Path:
    return LIB.libdir(brand) / "moments"


def latest_prompt() -> tuple:
    ps = sorted((HERE.parent / "prompts").glob("moments-look-v*-owner.md"),
                key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    return ps[-1], ps[-1].read_text()


def ours(r) -> bool:
    return r.get("kind") != "picture" and r.get("in") is not None and r.get("out") is not None and not any(
        x in str(r.get("label") or "") for x in NOT_OURS)


def _jsonl(f: Path) -> list:
    out = []
    try:
        for line in f.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    except OSError:
        pass
    return out


# ------------------------------------------------------------------ reading a scene by range
def source_of(brand: str, r) -> tuple:
    """(ffmpeg input args before -i's value..., kind). The local index proxy when there is one, else the Drive by key."""
    rec = LIB._abs(r)
    proxy = rec.parent / "proxy.mp4" if rec else None
    if proxy is not None and proxy.is_file() and proxy.stat().st_size > 0:
        return [], str(proxy), "proxy"
    root = REPO / "components" / "gdrive-creator"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from gdrive_creator import engine as E       # the team's one Drive door: a ranged read by the key
    url, head = E.media_request(r["clip"])
    return ["-headers", head], url, "drive"


def read_scene(brand: str, r, a: float, b: float) -> dict:
    """Motion per frame and the detector's shot changes for a..b seconds of the clip, read by range in one pass."""
    pre, src, kind = source_of(brand, r)
    fps = proxy_fps(src) if kind == "proxy" else FPS
    with tempfile.TemporaryDirectory() as d:
        mf = os.path.join(d, "m.txt")
        graph = ("[0:v]split=2[x][y];[x]fps=%d,scale=32:18,format=gray,tblend=all_mode=difference,signalstats,"
                 "metadata=print:key=lavfi.signalstats.YAVG:file='%s'[m];"
                 "[y]scale=160:-2,select='gt(scene,%s)',showinfo[s]" % (fps, mf.replace("'", r"\'"), SCENE_T))
        p = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-v", "info", *pre, "-ss", "%.3f" % a,
                            "-t", "%.3f" % (b - a), "-i", src, "-an", "-filter_complex", graph,
                            "-map", "[m]", "-f", "null", "-", "-map", "[s]", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=600)
        txt = open(mf).read() if os.path.exists(mf) else ""
    mv = [round(float(x), 2) for x in re.findall(r"YAVG=([0-9.]+)", txt)]
    # tblend's first frame is the first frame itself, not a difference: drop it
    mv = mv[1:]
    found = [a + float(t) for t in re.findall(r"pts_time:([0-9.]+)", p.stderr or "")]
    # a cut seen between two frames 1/fps apart lies somewhere in that gap: both ends count
    cuts = sorted({round(x, 2) for t in found for x in (t - 1.0 / fps, t)})
    if not mv and p.returncode != 0:
        raise RuntimeError("could not read %s %.1f-%.1f: %s" % (kind, a, b, (p.stderr or "")[-200:]))
    return {"mv": mv, "cuts": cuts, "source": kind, "fps": fps}


_PFPS: dict = {}


def proxy_fps(f: str) -> float:
    """The index proxy's own frame rate (2 fps on the 2026 index): motion is read at what the file holds."""
    if f not in _PFPS:
        try:
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                                "-of", "csv=p=0", f], capture_output=True, text=True, timeout=30).stdout.strip()
            n, d = (r.split("/") + ["1"])[:2]
            _PFPS[f] = min(float(FPS), max(1.0, float(n) / float(d or 1)))
        except Exception:  # noqa: BLE001
            _PFPS[f] = 2.0
    return _PFPS[f]


def jump_cuts(mv: list, a: float, fps: float = FPS) -> list:
    """Frames that jump far past the scene's usual motion: cuts the detector rated soft. Both ends of the gap."""
    if not mv:
        return []
    med = sorted(mv)[len(mv) // 2]
    return sorted({round(a + x / fps, 2) for i, m in enumerate(mv) if m > max(JUMP_MIN, JUMP_X * med) for x in (i, i + 1)})


def stretches(a: float, b: float, cuts, clip_end: float | None = None) -> list:
    """The unbroken stretches of a..b between the cuts, each kept PAD clear of a cut (a scene's own edges are cuts
    too, unless it is the clip's start or end)."""
    edges = sorted({a, b} | {c for c in cuts if a < c < b})
    out = []
    for x, y in zip(edges, edges[1:]):
        x2 = x + (PAD if x > 0.05 else 0.0)
        y2 = y - (PAD if clip_end is None or y < clip_end - 0.05 else 0.0)
        if y2 - x2 >= MIN_W:
            out.append((round(x2, 2), round(y2, 2)))
    return out


def busiest(mv: list, a: float, s0: float, s1: float, w: float, fps: float = FPS) -> tuple:
    """(start, mean motion) of the w seconds inside s0..s1 with the most movement; mv starts at second a, fps a second."""
    k = max(1, int(round(w * fps)))
    i0 = max(0, int(round((s0 - a) * fps)))
    i1 = int(round((s1 - w - a) * fps))
    best = None
    for i in range(i0, max(i0, i1) + 1):
        seg = mv[i:i + k]
        sc = sum(seg) / len(seg) if seg else 0.0
        if best is None or sc > best[1]:
            best = (round(min(max(s0, a + i / fps), s1 - w), 2), round(sc, 2))
    return best


def windows(mv: list, a: float, spans: list, fps: float = FPS) -> list:
    """Each unbroken stretch (long ones in pieces of at most PIECE s) -> its busiest window of MIN_W..MAX_W seconds."""
    out = []
    for s0, s1 in spans:
        n = max(1, int((s1 - s0) // PIECE) + (1 if (s1 - s0) % PIECE > 1e-6 and (s1 - s0) > PIECE else 0))
        step = (s1 - s0) / n
        for j in range(n):
            p0, p1 = s0 + j * step, s0 + (j + 1) * step
            w = min(MAX_W, p1 - p0)
            if w < MIN_W:
                continue
            at, sc = busiest(mv, a, p0, p1, w, fps)
            out.append({"stretch": [s0, s1], "in": at, "out": round(at + w, 2), "motion": sc})
    return out


def strip(brand: str, r, at: float, w: float, out: Path) -> Path:
    """The four frames of a window side by side, one picture (the chain's frame_look.strip), read by range."""
    pre, src, _ = source_of(brand, r)
    span = w * (AT[-1] - AT[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *pre, "-ss", "%.3f" % (at + w * AT[0]), "-t",
                    "%.3f" % (span + 0.05), "-i", src, "-vf",
                    "fps=%.4f,scale=-2:360,tile=%dx1" % (len(AT) / max(span, 0.1), len(AT)), "-frames:v", "1",
                    "-q:v", "5", str(out)], check=True, capture_output=True, timeout=300)
    return out


# ------------------------------------------------------------------ the judge
def _judge_door():
    f = REPO / "components" / "video-production" / "machine" / "vision_judge.py"
    import importlib.util
    if "moments_vision_judge" not in sys.modules:
        d = str(f.parent)
        if d not in sys.path:
            sys.path.append(d)
        spec = importlib.util.spec_from_file_location("moments_vision_judge", f)
        m = importlib.util.module_from_spec(spec)
        sys.modules["moments_vision_judge"] = m
        spec.loader.exec_module(m)
    return sys.modules["moments_vision_judge"]


_SWAPPED: list = []


def _backup_key(a) -> bool:
    """The company Gemini key out of credit (HTTP 402) -> the backup key, once, for the rest of the run (owner,
    16 Nov: the backup key is on the company card; use it without asking)."""
    if _SWAPPED or not any("402" in str(t.get("error") or "") for t in getattr(a, "tried", []) or []):
        return False
    _SWAPPED.append(1)
    try:
        sys.path.insert(0, str(REPO / "components" / "keys"))
        import loader as K
        k = K.key("GEMINI_API_KEY_PERSONAL", required=False) or ""
    except Exception:  # noqa: BLE001
        k = os.environ.get("GEMINI_API_KEY_PERSONAL", "")
    if k.strip():
        os.environ["GEMINI_API_KEY"] = k.strip()
        return True
    return False


def _probe_key():
    """Before the first ask: if the company key answers 402, take the backup key now (no ask races the swap)."""
    try:
        VJ = _judge_door()
        VJ.ask('Answer {"ok": true}', [], want_json=True, order_=["gemini"])
    except Exception as e:  # noqa: BLE001
        if "402" in str(e):
            class _A:
                tried = [{"error": "402"}]
            _backup_key(_A())


def ask_prompt(template: str, n: int, seconds: list) -> str:
    looks = LIB.BRAND.get("looks") or {k: k for k in (LIB.D.get("product") or {}).get("values") or {}}
    return (template.replace("{n}", str(n))
            .replace("{seconds}", ", ".join("%d: %.1f s" % (i + 1, s) for i, s in enumerate(seconds)))
            .replace("{products}", "\n".join("- %s: %s" % (k, v) for k, v in looks.items())))


def judge(template: str, ms: list, strips: list, ask=None) -> tuple:
    """One ask for up to PER_ASK moments -> ([answer per moment], who answered)."""
    q = ask_prompt(template, len(ms), [m["out"] - m["in"] for m in ms])
    if ask is None:
        VJ = _judge_door()
        a = VJ.ask(q, [str(s) for s in strips], want_json=True)
        if getattr(a, "backend", "") != "gemini" and _backup_key(a):
            a = VJ.ask(q, [str(s) for s in strips], want_json=True)
        who = getattr(a, "backend", "") + (" (%s)" % a.model if getattr(a, "model", "") else "")
        j = VJ.json_of(str(a))
    else:
        j, who = ask(q, strips), "test"
    if isinstance(j, dict):
        j = j.get("moments") or j.get("pictures") or [j]
    got = {}
    for i, x in enumerate(j or []):
        if isinstance(x, dict):
            got[int(x.get("n") or i + 1)] = x
    return [got.get(i + 1) for i in range(len(ms))], who


# ------------------------------------------------------------------ the pass
def by_clip_ids(rows) -> list:
    return list(dict.fromkeys(r["clip"] for r in rows))


def true_length(brand: str, r) -> float | None:
    """The clip's real length in seconds (the index record's clip.json), or None when unknown."""
    rec = LIB._abs(r)
    try:
        d = json.loads((rec.parent / "clip.json").read_text()) if rec else {}
        v = float((d.get("meta") or {}).get("duration_s") or 0)
        return v or None
    except (OSError, ValueError, TypeError):
        return None


def mark_past_end(brand: str) -> int:
    """Moments written before the clamp that sit past their clip's real end: marked gone (a later line wins)."""
    LIB.BRANDNAME[0] = brand
    rows = {(r["clip"], r["scene"]): r for r in LIB.rows_of(brand)}
    latest = {}
    for m in _jsonl(mdir(brand) / "moments.jsonl"):
        latest[m["id"]] = m
    lens, gone = {}, []
    for m in latest.values():
        if m.get("past_end"):
            continue
        r = rows.get((m["clip"], m["scene"]))
        if r is None:
            continue
        if m["clip"] not in lens:
            lens[m["clip"]] = true_length(brand, r)
        L = lens[m["clip"]]
        if L and m["out"] > L + 0.05:
            gone.append(dict(m, past_end=True, needs_judge=False,
                             judge={"dead": True, "from": "past the clip's real end (%.1f s): a scene label overran" % L}))
    if gone:
        with (mdir(brand) / "moments.jsonl").open("a") as fh:
            for m in gone:
                fh.write(json.dumps(m, ensure_ascii=False, separators=(",", ":")) + "\n")
    _ROWS.pop(brand, None)
    return len(gone)


def plan(brand: str, rows=None) -> list:
    """Scenes of our footage not read yet."""
    rows = rows if rows is not None else LIB.rows_of(brand)
    done = {(x["clip"], x["scene"]) for x in _jsonl(mdir(brand) / "motion.jsonl")}
    return [r for r in rows if ours(r) and (r["clip"], r["scene"]) not in done]


def estimate(brand: str, todo: list) -> dict:
    cutsf = LIB.libdir(brand) / "cuts.json"
    allcuts = json.loads(cutsf.read_text()) if cutsf.is_file() else {}
    secs, moments, judged, proxy, dsecs = 0.0, 0, 0, 0, 0.0
    per_clip = {}
    for r in todo:
        a, b = float(r["in"]), float(r["out"])
        secs += b - a
        inner = [c for c in allcuts.get(r["clip"], []) if a < c < b]
        k = sum(max(1, int((y - x) // PIECE) + 1) for x, y in zip([a] + inner, inner + [b]) if y - x >= MIN_W + 2 * PAD)
        moments += k
        if (r.get("text_marks") or ["clean"]) == ["clean"]:
            judged += k
            per_clip[r["clip"]] = per_clip.get(r["clip"], 0) + k
        rec = LIB._abs(r)
        has = bool(rec and (rec.parent / "proxy.mp4").is_file())
        proxy += has
        dsecs += 0 if has else b - a
    asks = sum(-(-n // PER_ASK) for n in per_clip.values())
    usd = asks * EST_USD_ASK + judged * EST_USD_STRIP
    return {"scenes": len(todo), "footage_seconds": round(secs), "drive_seconds": round(dsecs), "read_from_proxy": proxy, "read_from_drive": len(todo) - proxy,
            "moments_est": moments, "judged_est": judged, "asks_est": asks, "est_usd": round(usd, 2)}


def run(brand: str, budget: float, limit: int | None = None, workers: int = 8, judge_on: bool = True,
        dry: bool = False, ask=None, clips=()) -> dict:
    LIB.BRANDNAME[0] = brand
    rows = LIB.rows_of(brand)
    todo = plan(brand, rows)
    if clips:
        want = {_key(c) for c in clips}
        todo = [r for r in todo if r["clip"] in want or _key(r.get("label")) in want]
    if limit:
        clips_ = list(dict.fromkeys(r["clip"] for r in todo))[:limit]
        todo = [r for r in todo if r["clip"] in set(clips_)]
    est = estimate(brand, todo)
    latest = {}
    for m in _jsonl(mdir(brand) / "moments.jsonl"):
        latest[m["id"]] = m
    unjudged = [m for m in latest.values() if m.get("judge") is None and m.get("needs_judge") and not m.get("past_end")]
    w_ = max(1, workers)
    est["est_minutes"] = round(((est["footage_seconds"] - est["drive_seconds"]) / EST_READ_X / w_
                                + est["drive_seconds"] / EST_DRIVE_X / min(w_, 4)
                                + est["asks_est"] * EST_ASK_S / w_ + est["judged_est"] * 0.3 / w_) / 60, 1)
    est["waiting_for_judge_from_before"] = len(unjudged)
    if dry:
        return {"dry_run": True, "brand": brand, **est, "budget": budget}
    D = mdir(brand)
    (D / "strips").mkdir(parents=True, exist_ok=True)
    cutsf = LIB.libdir(brand) / "cuts.json"
    allcuts = json.loads(cutsf.read_text()) if cutsf.is_file() else {}
    ends = {}
    for r in rows:
        if r.get("out") is not None:
            ends[r["clip"]] = max(ends.get(r["clip"], 0.0), float(r["out"]))
    for cid in by_clip_ids(todo):
        d_ = true_length(brand, next(r for r in todo if r["clip"] == cid))
        if d_:
            ends[cid] = d_                 # the clip's real length wins over scene labels written past its end
    lock = threading.Lock()
    st = {"read": 0, "moments": 0, "failed": 0, "judged": 0, "asks": 0, "usd": 0.0, "stopped": None, "drive": 0}
    by_clip = {}
    for r in todo:
        by_clip.setdefault(r["clip"], []).append(r)
    pfile, template = latest_prompt()
    t0 = time.time()

    def write(f: str, items: list):
        with lock:
            with (D / f).open("a") as fh:
                for x in items:
                    fh.write(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n")

    scene_of = {(r["clip"], r["scene"]): r for r in rows}

    def judge_clip(cid: str, pend: list):
        """Strips + the judge for a clip's moments, in asks of PER_ASK, inside the budget."""
        for i in range(0, len(pend), PER_ASK):
            batch = pend[i:i + PER_ASK]
            with lock:
                if st["usd"] >= budget:
                    st["stopped"] = "budget $%.2f reached" % budget
                    return
            try:
                pics = []
                for m in batch:
                    f = D / "strips" / (hashlib.md5(m["id"].encode()).hexdigest()[:12] + ".jpg")
                    if not f.is_file():
                        strip(brand, scene_of[(cid, m["scene"])], m["in"], m["seconds"], f)
                    m["strip"] = "strips/" + f.name
                    pics.append(f)
                answers, who = judge(template, batch, pics, ask)
            except Exception as e:  # noqa: BLE001 - not judged here: the moment waits for the next pass
                write("failed.jsonl", [{"clip": cid, "judge": [m["id"] for m in batch], "error": str(e)[:200]}])
                continue
            for m, ans in zip(batch, answers):
                if ans:
                    m["judge"] = {k: ans.get(k) for k in ("product_in_use", "product", "text_on_screen", "blur_or_transition",
                                                          "dead", "people", "who", "shows", "why")}
                    m["judged_by"] = who
                    m["prompt_file"] = pfile.name
            with lock:
                st["asks"] += 1
                st["judged"] += sum(1 for a_ in answers if a_)
                st["usd"] += EST_USD_ASK + EST_USD_STRIP * len(batch)

    def one_clip(cid: str):
        out_m, out_s, pend = [], [], []
        for r in by_clip[cid]:
            a, b = float(r["in"]), min(float(r["out"]), ends.get(cid) or float(r["out"]))
            if b - a < MIN_W:                    # too short (or labelled past the clip's end): read, nothing fetched
                out_s.append({"clip": cid, "scene": r["scene"], "in": a, "out": b, "fps": None, "mv": [], "cuts": [],
                              "source": "too short" if b > a else "past the clip's end", "label": r.get("label")})
                with lock:
                    st["read"] += 1
                continue
            try:
                got = read_scene(brand, r, a, b)
            except Exception as e:  # noqa: BLE001 - one scene never stops the rest
                with lock:
                    st["failed"] += 1
                write("failed.jsonl", [{"clip": cid, "scene": r["scene"], "error": str(e)[:200]}])
                continue
            mv, fps = got["mv"], got["fps"]
            b = min(b, a + (len(mv) + 1) / fps) if mv else b    # only the seconds that held frames
            # the index's cuts.json was measured on the 2 fps proxy: a cut there lies in the half second before it
            known = {round(x, 2) for c in allcuts.get(cid, []) if a - 0.5 < float(c) < b + 0.5 for x in (float(c) - 0.5, float(c))}
            cuts = sorted(known | set(got["cuts"]) | set(jump_cuts(mv, a, fps)))
            spans = stretches(a, b, cuts, ends.get(cid))
            ws = windows(mv, a, spans, fps)
            clean = (r.get("text_marks") or ["clean"]) == ["clean"]
            out_s.append({"clip": cid, "scene": r["scene"], "in": a, "out": b, "fps": fps, "mv": mv, "cuts": cuts,
                          "source": got["source"], "label": r.get("label")})
            for k, w in enumerate(ws, 1):
                m = {"id": "%s:%s:%d" % (cid, r["scene"], k), "clip": cid, "scene": r["scene"], "label": r.get("label"),
                     **w, "seconds": round(w["out"] - w["in"], 2), "scene_text_marks": r.get("text_marks"),
                     "scene_shows": (r.get("shows") or "")[:200], "judge": None, "needs_judge": clean}
                if not clean:
                    m["judge"] = {"text_on_screen": True, "from": "check pass: the scene carries burned-in text (%s)"
                                  % ", ".join(r.get("text_marks") or [])}
                    m["needs_judge"] = False
                out_m.append(m)
                if clean and judge_on:
                    pend.append(m)
            with lock:
                st["read"] += 1
                st["drive"] += got["source"] == "drive"
        judge_clip(cid, pend)
        write("motion.jsonl", out_s)
        write("moments.jsonl", out_m)
        with lock:
            st["moments"] += len(out_m)
            if st["read"] and st["read"] % 200 < len(by_clip[cid]):
                print("  %d scenes, %d moments, %d judged, ~$%.2f, %ds" % (st["read"], st["moments"], st["judged"],
                                                                          st["usd"], time.time() - t0), flush=True)

    if judge_on and ask is None:
        _probe_key()
    with cf.ThreadPoolExecutor(workers) as ex:
        list(ex.map(one_clip, list(by_clip)))
    # moments read before but never judged (a budget stop, a judge that could not answer): judged now
    if judge_on:
        late = {}
        for m in unjudged:
            if (m["clip"], m["scene"]) in scene_of:
                late.setdefault(m["clip"], []).append(m)

        def late_clip(cid: str):
            judge_clip(cid, late[cid])
            write("moments.jsonl", [m for m in late[cid] if m.get("judge")])
        with cf.ThreadPoolExecutor(workers) as ex:
            list(ex.map(late_clip, list(late)))
    res = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "brand": brand, "estimate": est,
           "scenes_read": st["read"], "read_from_drive": st["drive"], "moments": st["moments"], "judged": st["judged"],
           "asks": st["asks"], "est_usd": round(st["usd"], 2), "failed_scenes": st["failed"], "stopped": st["stopped"],
           "wall_s": round(time.time() - t0), "prompt_file": pfile.name,
           "prompt_sha256": hashlib.sha256(template.encode()).hexdigest(), "budget": budget, "workers": workers}
    f = D / "runs.json"
    hist = json.loads(f.read_text()) if f.is_file() else []
    hist.append(res)
    f.write_text(json.dumps(hist, indent=1) + "\n")
    _ROWS.pop(brand, None)
    return res


# ------------------------------------------------------------------ for callers
_ROWS: dict = {}
_LOCK = threading.Lock()


def _key(label_or_clip) -> str:
    s = str(label_or_clip or "")
    return "Shared Assets/" + s.split("Shared Assets/", 1)[1] if "Shared Assets/" in s else s


def _load(brand: str) -> dict:
    """{"moments": [...], "by_clip": {clip id or label: [moments]}, "scenes": {clip: [motion rows]}}; cached."""
    with _LOCK:
        if brand not in _ROWS:
            D = mdir(brand)
            ms = {}
            for m in _jsonl(D / "moments.jsonl"):
                ms[m["id"]] = m                       # a later line (re-judged) wins
            by, sc = {}, {}
            for m in ms.values():
                by.setdefault(m["clip"], []).append(m)
                if m.get("label"):
                    by.setdefault(_key(m["label"]), []).append(m)
            for s in _jsonl(D / "motion.jsonl"):
                sc.setdefault(s["clip"], []).append(s)
                if s.get("label"):
                    sc.setdefault(_key(s["label"]), []).append(s)
            _ROWS[brand] = {"moments": list(ms.values()), "by_clip": by, "scenes": sc}
        return _ROWS[brand]


def known(brand: str, clip) -> bool:
    """Has the moments pass read this clip (by Drive id or Shared Assets path)?"""
    return bool(_load(brand)["scenes"].get(_key(clip)))


def product_key(name: str | None, brand: str | None = None) -> str | None:
    """The brand's product key for a product's name as a brief writes it ("FLEX face brush" -> "flex")."""
    if not name:
        return None
    if brand and not LIB.BRAND:
        LIB.rows_of(brand)
    s = str(name).lower()
    keys = list((LIB.BRAND.get("looks") or {}).keys()) or list(((LIB.D.get("product") or {}).get("values") or {}).keys())
    if s in keys:
        return s
    hit = [k for k in keys if re.search(r"\b%s\b" % re.escape(k.split("-")[0]), s)]
    return hit[0] if hit else None


def clean(m, need_product: str | None = None) -> tuple:
    """(clean, why) for a moment: judged, no text over the video, no blur or transition, not dead; the right product in
    use when one is needed."""
    j = m.get("judge")
    if not j:
        return False, "not judged yet"
    bad = [k for k, want in (("text_on_screen", False), ("blur_or_transition", False), ("dead", False)) if bool(j.get(k)) != want]
    if need_product:
        if not j.get("product_in_use"):
            bad.append("product not in use")
        elif str(j.get("product") or "").lower() != need_product:
            bad.append("another product (%s)" % j.get("product"))
    return not bad, ", ".join(bad) or "clean"


def sized(m, seconds: float) -> tuple | None:
    """(in, out) of `seconds` inside the moment's unbroken stretch, centred on its busiest window; None when the stretch
    is shorter."""
    s0, s1 = m["stretch"]
    if s1 - s0 + 1e-6 < seconds:
        return None
    mid = (m["in"] + m["out"]) / 2
    a = min(max(s0, mid - seconds / 2), s1 - seconds)
    return round(a, 2), round(a + seconds, 2)


def find(brand: str, words: str, seconds: float, need_product: str | None = None, n: int = 10, exclude=(),
         people: str | None = None) -> list:
    """Clean moments of our footage for a shot, best first: the asset index's search ranks the scenes by the shot's
    words; each scene's clean moments that can play `seconds` unbroken come back, one per clip, already free of
    captions, cuts and dead time. need_product: a product key (or name) that must be in use. exclude: clip ids or
    Shared Assets paths already used. people: "none" / "hands" / "one" / "two+" to match who is on screen."""
    L = _load(brand)
    if not L["moments"]:
        return []
    need = product_key(need_product, brand) if need_product else None
    if need_product and not need:
        need = str(need_product).lower()
    import importlib.util
    if "moments_search" not in sys.modules:
        spec = importlib.util.spec_from_file_location("moments_search", HERE.parent / "machine" / "search.py")
        S_ = importlib.util.module_from_spec(spec)
        sys.modules["moments_search"] = S_
        spec.loader.exec_module(S_)
    S = sys.modules["moments_search"]
    hits = S.search(words, brand=brand, per=600)
    ex = {_key(x) for x in exclude or ()}
    out = []
    for h in hits:
        cid, lab = h.get("clip_id"), _key(h.get("shared_path"))
        if cid in ex or lab in ex or any(x in lab for x in NOT_OURS):
            continue
        ms = L["by_clip"].get(cid) or L["by_clip"].get(lab) or []
        best = None
        for m in ms:
            ok, _ = clean(m, need)
            if not ok or (people and str((m.get("judge") or {}).get("people") or "") != people):
                continue
            io = sized(m, seconds)
            if io is None:
                continue
            near = h.get("in") is not None and m["stretch"][0] <= float(h["out"] or 0) and float(h["in"]) <= m["stretch"][1]
            rank = (float(h.get("score") or 0) * (1.0 if near else 0.85), float(m.get("motion") or 0))
            if best is None or rank > best[0]:
                best = (rank, m, io)
        if best:
            (sc, mot), m, io = best
            out.append({"clip": m["clip"], "label": m.get("label"), "in": io[0], "out": io[1], "score": round(sc, 3),
                        "motion": mot, "moment": m["id"], "judge": m["judge"], "strip": m.get("strip"),
                        "shows": (m["judge"] or {}).get("shows") or m.get("scene_shows"), "stretch": m["stretch"]})
    out.sort(key=lambda x: (-x["score"], -x["motion"]))
    return out[:n]


def place(brand: str, clip, start: float, need: float, need_product: str | None = None, reach: float = 6.0,
          avoid=()):
    """Where a shot of `need` seconds starts in one clip: on its clean moment nearest to `start` (within `reach`
    seconds first, else anywhere in the clip) whose unbroken stretch holds `need`. -> (start, moment) or None (no clean
    moment can play it: swap the clip). Only for a clip the pass has read (known). avoid: (in, out) sections of this
    clip other shots already play (one clip section per shot)."""
    ms = _load(brand)["by_clip"].get(_key(clip)) or []
    cand = []
    for m in ms:
        if not clean(m, need_product)[0]:
            continue
        io = sized(m, need)
        if io is None or any(io[0] < b_ and a_ < io[1] for a_, b_ in avoid or ()):
            continue
        d = abs((io[0] + io[1]) / 2 - (float(start or 0) + need / 2))
        cand.append((d > reach, d, -float(m.get("motion") or 0), io[0], m))
    if not cand:
        return None
    cand.sort(key=lambda x: x[:3])
    return cand[0][3], cand[0][4]


def look_at(brand: str, clip, start: float, need: float):
    """The judge's answers for the moment a shot of start..start+need plays inside (same unbroken stretch, overlapping
    its judged window), or None when no judged moment covers it."""
    ms = _load(brand)["by_clip"].get(_key(clip)) or []
    a, b = float(start), float(start) + need
    best = None
    for m in ms:
        s0, s1 = m["stretch"]
        if not (s0 - 0.05 <= a and b <= s1 + 0.05) or not m.get("judge"):
            continue
        ov = min(b, m["out"]) - max(a, m["in"])
        if ov > 0 and (best is None or ov > best[0]):
            best = (ov, m)
    return best[1] if best else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--brand", required=True)
    r.add_argument("--budget", type=float, default=10.0, help="stop asking the judge once this many USD (estimated) are spent")
    r.add_argument("--limit", type=int, help="at most this many clips")
    r.add_argument("--workers", type=int, default=8)
    r.add_argument("--no-judge", dest="judge", action="store_false", help="read and split only; judge later")
    r.add_argument("--dry-run", dest="dry", action="store_true")
    r.add_argument("--clips", default="", help="only these clips first: Drive ids or Shared Assets paths, comma separated")
    g = sub.add_parser("tidy", help="mark moments past their clip's real end")
    g.add_argument("--brand", required=True)
    f = sub.add_parser("find")
    f.add_argument("--brand", required=True)
    f.add_argument("words")
    f.add_argument("--seconds", type=float, default=2.0)
    f.add_argument("--product")
    f.add_argument("-n", type=int, default=8)
    a = ap.parse_args(argv)
    LIB.BRANDNAME[0] = a.brand
    LIB.rows_of(a.brand)
    if a.cmd == "run":
        cl = [c.strip() for c in a.clips.split(",") if c.strip()]
        print(json.dumps(run(a.brand, a.budget, a.limit, a.workers, a.judge, a.dry, clips=cl), indent=1))
    elif a.cmd == "tidy":
        print(json.dumps({"marked_past_end": mark_past_end(a.brand)}))
    else:
        for h in find(a.brand, a.words, a.seconds, a.product, a.n):
            print("%.3f  %-48s %6.2f-%-6.2f motion %5.1f  %s" % (h["score"], str(h["label"]).rsplit("/", 1)[-1][:48],
                                                                h["in"], h["out"], h["motion"], (h["shows"] or "")[:70]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
