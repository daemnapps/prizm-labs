#!/usr/bin/env python3
"""THE AI LANE, END TO END — one accepted AI-lane brief through the production chain by itself (2026-11-20).

Owner ruling, 20 Nov 2026: every production moves through the process; the Video Studio lives on the chain and only
shows it; the underlying technology does the work. This is the chain's one command for an accepted AI-lane brief. It
runs nothing of its own: every station is the chain's existing door, in the chain's order (THE-CHAIN.md, station 3-4):

    1 elements        auto_elements.run       bind or make every person, place, prop and voice the brief names
    2 voice           run.py --voice-only     every line read in its speaker's banked voice, heard back
    3 storyboard      storyboard_plan.py      the brief's scenes grouped into the swipe's sections (BUDGET.md beside it)
    4 pictures        run.py --storyboard     only the storyboard's pictures, each from its filed 3D set print; a picture
                                              with no print is filed for the 3d-print skill (set-prints.json)
    5 camera + motion camera_motion.py        per scene, from the director's 5d pick (run.py --clips runs it)
    6 clips plan      run.py --clips          every clip's call, its prompt carrying its camera and motion plan; a clip
                                              without one is a problem, and the live clip door refuses the plan
    7 clips           run_v2.py clips --yes   the paid take of every clip (only with --yes, after a green plan)

The live order is run_v2.py's (`ordered`): this command calls it, then the clip run. The owner's go on THIS run (`--yes`)
is the one thing it adds: the elements and clip-gate steps that `production: auto` runs unattended are run for this
brief even while automation is paused (OUTLIER_SETTINGS for this process only, recorded on the run's trail).

THE DRY RUN walks every station, spends nothing and calls no paid model, inside a sealed shadow folder
(`runs/video-production/<brand>/<label>/dry-run/`), so nothing it writes (an estimated storyboard, a plan with no
voice yet) can be mistaken by a live run for real output. It ends with the quote and the exact live command.

    python3 ai_lane.py <writing run label | 5-brief.md> [--brand B] [--format F] [--label L] [--dry-run]
    python3 ai_lane.py <...> --yes                      the live run (spends: the owner's approval comes first)
    python3 ai_lane.py status <writing run label>       where the live run stands, station by station (json)

THE REAL LANE IS THIS CHAIN WITH ONE SWAP (owner ruling, 20 Nov 2026): a Real production runs every station above,
in the same order, with the same storyboard, camera and motion plan, clip plan and checks. Only generation changes, at
real_door.py: the elements station binds each brief person to a real cast-bank entry with footage (anyone else is a
footage extra, never made), the pictures station places a frame of the cast member's own best-matching moment where the
picture would go, and the clips station assembles each planned call from that person's moments. It spends no credits,
so the quote is zero and the cap never refuses it. A run is Real when --lane real is given, or the brief's json block
names "real_cast", or the run already holds real-cast.json; the cast is --cast BRIEF_ID=cast-bank-id,... (the first is
the lead), else the run's real-cast.json, else the brief's "real_cast".

    python3 ai_lane.py <...> --lane real --cast A=bank-a,B=bank-b --label L --dry-run     every station, real footage placed
    python3 ai_lane.py <...> --lane real --cast ... --label L --yes                       the live Real run (no credits)

The Studio's AI-lane step starts this command and shows its run; it holds no production logic of its own.
No brand, product or person is named here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
WRITING = Path(os.environ.get("VIDEO_STUDIO_WRITING") or WS / "runs" / "video-teardown" / "_work")
STATIONS = [("elements", "Elements bound or made"), ("voice", "Voice read and heard"),
            ("storyboard", "Storyboard and budget"), ("pictures", "Pictures from 3D set prints"),
            ("camera", "Camera and motion plan per scene"), ("clips-plan", "Clip plan, camera and motion in every prompt"),
            ("clips", "Clips made")]
PRINT_CREDITS = 2.5          # one 3D set print (image-production picture_sets.PRINT_CREDITS), read again below


def _load(path: Path, name: str):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def brief_doc(text: str) -> dict:
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text or "", re.S)
    try:
        return json.loads(blocks[-1]) if blocks else {}
    except ValueError:
        return {}


# ------------------------------------------------------------------ what the run is

def resolve(source: str, brand: str | None = None, fmt: str | None = None, label: str | None = None,
            lane: str | None = None, cast: str | None = None) -> dict:
    """{brief, writing_run, brand, format, label, brief_id}: the brief from a writing run's label or its path; the
    brand, the production label (the brief register's id, CLAUDE.md hard rule) and the format (the brief's own piece)
    unless given."""
    p = Path(source)
    brief = p if p.suffix == ".md" and p.is_file() else WRITING / source / "stages" / "5-brief.md"
    if not brief.is_file():
        raise SystemExit(f"no accepted brief at {brief}")
    wrun = brief.resolve().parent.parent
    doc = brief_doc(brief.read_text())
    piece = doc.get("piece") or {}
    reg = {}
    try:
        rows = _load(WS / "components" / "image-teardown" / "tools" / "briefs.py", "vp_lane_briefs").load()["briefs"]
    except (Exception, SystemExit):  # noqa: BLE001 -- inside another tool's process its reader can pick up a same-named module
        try:          # (a Studio's own `names`): the register file itself is read instead
            rows = json.loads((WS / "components" / "image-teardown" / "briefs.json").read_text()).get("briefs") or {}
        except (OSError, ValueError):
            rows = {}
    reg = next((dict(v, id=v.get("id") or k) for k, v in rows.items()
                if isinstance(v, dict) and v.get("run") == wrun.name), {}) or {}
    out = {"brief": str(brief), "writing_run": str(wrun), "brand": brand or reg.get("brand") or piece.get("brand"),
           "format": fmt or piece.get("format"), "label": label or reg.get("id"), "brief_id": reg.get("brief"),
           "register_label": reg.get("id")}
    missing = [k for k in ("brand", "format", "label") if not out[k]]
    if missing:
        raise SystemExit("cannot tell the run's " + ", ".join(missing) + " — pass " +
                         " ".join("--" + m for m in missing))
    # THE REAL LANE (real_door.py): the same stations, real footage at generation
    rd = _real_door()
    held = (_read(rd.cast_file(run_dir(out)), {}) or {}).get("cast") or {}
    named = rd.parse_cast(cast) if cast else (held or doc.get("real_cast") or {})
    if lane == "real" or (lane is None and named):
        if not named:
            raise SystemExit("a Real run needs its cast: --cast BRIEF_ID=cast-bank-id,... (the first is the lead)")
        out["lane"], out["cast"] = "real", dict(named)
    else:
        out["lane"] = "ai"
    return out


def _real_door():
    return _load(HERE / "real_door.py", "vp_lane_real_door")


def is_real(r: dict) -> bool:
    return r.get("lane") == "real"


def song_in(r: dict, dest: Path) -> bool:
    """A sung ad's song is made by hand and gated in its run; a Real run under its own label reads the passing take of
    the brief's own production run (the register's id) when it has none of its own. Copied in, never written back."""
    for home in [run_dir(r)] + ([run_dir(dict(r, label=r["register_label"]))] if r.get("register_label") else []):
        song = _read(home / "song" / "song.json", {}) or {}
        if song.get("pass") and (home / "song" / "song.mp3").is_file():
            if home / "song" != dest / "song":
                shutil.copytree(home / "song", dest / "song", dirs_exist_ok=True)
            return True
    return False


def accepted(wrun: Path) -> tuple[bool, list]:
    """The writing station's own acceptance of this exact brief (hash-bound): production takes nothing less."""
    wr = _load(WS / "components" / "video-writing" / "machine" / "writing_result.py", "vp_lane_writing_result")
    r = wr.inspect_result(wrun)
    why = [b.get("code") + ": " + str(b.get("detail"))[:120] for b in r.get("blockers") or []]
    if r.get("accepted"):
        return True, why
    # THE ELEMENTS BIND is production's own pointer write (elements_check.bind: a NEW person or place pointed at its
    # bank folder, the brief before it kept as <brief>-before-bind.md). The brief as accepted is that kept copy,
    # byte for byte, with nothing else stale: a binding, not an edit (2026-11-20).
    try:
        import hashlib
        st = json.loads((Path(wrun) / "run.json").read_text())
        rec = st.get("writing_acceptance") or {}
        src = Path(wrun) / ((r.get("source") or {}).get("path") or "stages/5-brief.md")
        kept = src.with_name(src.stem + "-before-bind.md")
        codes = {b.get("code") for b in r.get("blockers") or []}
        if (codes == {"acceptance_stale"} and kept.is_file() and rec.get("accepted") is True
                and hashlib.sha256(kept.read_bytes()).hexdigest() == rec.get("source_sha256")
                and rec.get("context_sha256") == wr.context_hash(Path(wrun), st)):
            return True, ["accepted before the elements bind (" + kept.name + ")"]
    except Exception:  # noqa: BLE001
        pass
    return False, why


def run_dir(r: dict, root: Path | None = None) -> Path:
    return Path(root or WS / "runs") / "video-production" / r["brand"] / r["label"]


def _py(args: list, env=None, log=None) -> tuple[int, str]:
    """One chain door as its own process (the doors keep module state), its output kept."""
    p = subprocess.run([sys.executable] + [str(a) for a in args], cwd=str(HERE), capture_output=True, text=True,
                       env=env)
    out = (p.stdout or "") + (p.stderr or "")
    if log is not None:
        log.write("$ " + " ".join(str(a) for a in args) + "\n" + out + "\n")
    return p.returncode, out


def take_sets(run: Path, brand: str) -> dict:
    """This run's kept 3D set prints into its pictures (take_prints.take_sets); said, never raises."""
    try:
        got = _load_path(HERE / "take_prints.py", "al_take_prints").take_sets(Path(run), brand)
        if got["taken"] or got["shots"] or got["set_aside"]:
            print(f"pictures: {len(got['taken'])} start and {len(got['shots'])} shot picture(s) taken from kept 3D set "
                  f"prints" + (f"; {len(got['set_aside'])} generated picture(s) set aside" if got["set_aside"] else ""),
                  flush=True)
        return got
    except Exception as e:  # noqa: BLE001
        print(f"pictures: the kept set prints were not taken ({type(e).__name__}: {str(e)[:160]})")
        return {}


def section_due(run: Path, calls: list, stale=()) -> bool:
    """A section is sent when any of its clips is missing or stale (made from pictures since changed); a clip filed as
    a gap for the edit (clips/gaps.json) is never sent again."""
    gaps = set((_read(Path(run) / "clips" / "gaps.json", {}) or {}).keys())
    calls = [c for c in calls if c["id"] not in gaps]
    return not all((Path(run) / "clips" / f"{c['id']}.mp4").is_file() for c in calls) or any(c["id"] in stale for c in calls)


MODEL_REFUSED = re.compile(r"ended '(nsfw)'|content (polic|safet|moderat)|moderation|flagged by|sensitive content",
                           re.I)


def section_made(run: Path, calls: list) -> bool:
    """The section's clips are all made, or the only ones missing were refused by the model's content filter: the lane
    goes on to the next section (2026-11-21, brief-0380: one refused render stopped the whole ad). A refusal is filed as
    a gap for the edit (clips/gaps.json; the edit holds a neighbouring shot or the section's made clip covers it). A
    failed submit, a door fault or any other shortfall stops the lane."""
    run = Path(run)
    led = _read(run / "clips" / "ledger.json", {}) or {}
    rows = led.get("calls", led) if isinstance(led, dict) else {}
    gaps, short = {}, []
    for c in calls:
        row = rows.get(c["id"]) or {}
        made = (run / "clips" / f"{c['id']}.mp4").is_file() and row.get("status") != "failed"
        if made:
            continue
        if row.get("status") == "failed" and MODEL_REFUSED.search(str(row.get("error") or "")):
            gaps[c["id"]] = {"scenes": c.get("scenes") or [], "section": c.get("section_id"),
                             "why": str(row.get("error"))[:200], "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        else:
            short.append(c["id"])
    if gaps:
        f = run / "clips" / "gaps.json"
        f.write_text(json.dumps({**(_read(f, {}) or {}), **gaps}, indent=1, ensure_ascii=False) + "\n")
        print("7 · clips refused by the model, left as gaps for the edit: " + ", ".join(gaps))
    return not short


def _stops(out: str) -> list[str]:
    rows = [ln.strip() for ln in out.splitlines()
            if re.match(r"\s*(STOP|REFUSED|GATE|HELD|preflight failed|\[rule \d+\])", ln)]
    return [r[:300] for r in dict.fromkeys(rows)]


# ------------------------------------------------------------------ the dry run

def dry_run(r: dict, keep: bool = True) -> dict:
    """Every station, nothing spent, in the sealed shadow folder. Returns the station rows and the quote."""
    real = run_dir(r)
    shadow_root = real / "dry-run"
    if shadow_root.exists():
        shutil.rmtree(shadow_root)            # the shadow is this command's own temp output, remade each time
    shadow_root.mkdir(parents=True)
    run = shadow_root / "video-production" / r["brand"] / r["label"]
    base = ["run.py", "start", r["brief"], "--brand", r["brand"], "--format", r["format"], "--label", r["label"],
            "--walk", "--runs-root", str(shadow_root)]
    rows, log = [], (shadow_root / "dry-run.log").open("w")
    ok, why = accepted(Path(r["writing_run"]))
    rows.append({"station": "brief", "state": "done" if ok else "stopped",
                 "said": "accepted by the writing station (this exact brief)" if ok else "; ".join(why)})
    # 1 elements: the sheet the elements station works from (binding and making happen on the live run)
    if is_real(r):
        # the Real lane binds its cast here too (nothing is made, so the dry run does what the live run does)
        try:
            er = _real_door().elements(run, r["brief"], r["brand"], r["cast"])
            rows.append({"station": "elements", "state": "done",
                         "said": f"{len(er['bound'])} bound to real cast ("
                                 + ", ".join(f"{b}={v['cast_bank']}" for b, v in er["bound"].items())
                                 + f"); {len(er['extras'])} footage extra(s), never made; "
                                 + f"{len(er['from_footage'])} place(s), prop(s) and product from footage; 0 made"})
        except SystemExit as e:
            rows.append({"station": "elements", "state": "stopped", "said": str(e)})
    else:
        ec = _load(HERE / "elements_check.py", "vp_lane_elements_check")
        text = Path(r["brief"]).read_text()
        sh = ec.sheet(text, r["brand"], root=WS, teardown=ec.resolve_teardown(Path(r["writing_run"])))
        tm = sh.get("to_make") or []
        rows.append({"station": "elements", "state": "done",
                     "said": f"{len(sh.get('items') or [])} element(s); {len(tm)} to bind or make on the live run: "
                             + ", ".join(f"{i.get('kind')} {i.get('id')}" for i in tm)})
    # 2 voice. A sung ad's song is made by hand (Suno) and gated in the real run; the shadow reads that passing take
    # (copied in, never written back), so the camera, clip plan and quote are worked out on the real song.
    if is_real(r):
        song_in(r, run)
    else:
        song = _read(real / "song" / "song.json", {}) or {}
        if song.get("pass") and (real / "song" / "song.mp3").is_file():
            shutil.copytree(real / "song", run / "song", dirs_exist_ok=True)
    rc, out = _py(base + ["--voice-only"], log=log)
    rows.append({"station": "voice", "state": "done" if rc == 0 else "stopped",
                 "said": "every line's speaker has a voice or the elements station makes it" if rc == 0
                 else "; ".join(_stops(out) or out.strip().splitlines()[-2:])})
    # 3 storyboard. A dry run reads no voice, so each spoken scene gets a SILENT stand-in of its estimated length in
    # the shadow's vo/ (WORDS_A_SECOND), only so the storyboard and the quote have lengths; never in a real run.
    est = stand_in_reads(run)
    rc, out = _py(["storyboard_plan.py", run, "--teardown", r["writing_run"], "--brief", r["brief"]], log=log)
    sb = _read(run / "storyboard.json", {}) or {}
    rows.append({"station": "storyboard", "state": "done" if rc == 0 and sb else "stopped",
                 "said": (f"{len(sb.get('sections') or [])} sections, {sb.get('seconds')} s; lengths estimated at "
                          f"{WORDS_A_SECOND} words a second ({est} spoken scenes) until the voice is read"
                          if sb else "; ".join(out.strip().splitlines()[-2:]))})
    # 4 pictures
    if is_real(r):
        waits = []
        rows.append(real_pictures_row(run) if sb else
                    {"station": "pictures", "state": "stopped", "said": "no storyboard, so no picture is placed"})
    else:
        rc, out = _py(base + ["--storyboard"], log=log)
        waits = (_read(run / "set-prints.json", {}) or {}).get("waiting") or []
        rows.append({"station": "pictures", "state": "done" if rc == 0 else "stopped",
                     "said": (f"{len(waits)} picture(s) wait for a 3D set print — the live run files them for the "
                              f"3d-print skill" if rc == 0 else "; ".join(_stops(out) or out.strip().splitlines()[-2:])),
                     "waiting": [w["picture"] for w in waits]})
    # 5 + 6 camera and motion, then the clip plan (run.py --clips runs both)
    rc, out = _py(base + ["--clips"], log=log)
    cm = _read(run / "clips" / "camera-motion.json", {}) or {}
    rows.append({"station": "camera", "state": "done" if cm.get("scenes") and not cm.get("held") else "stopped",
                 "said": f"{len(cm.get('scenes') or {})} scene(s) planned from the director's picks"
                         + (", held: " + "; ".join(f"{k} {v}" for k, v in cm["held"].items()) if cm.get("held") else ""),
                 "scenes": {k: v.get("words") for k, v in (cm.get("scenes") or {}).items()}})
    plan = _read(run / "clips" / "plan.json", {}) or {}
    calls = plan.get("calls") or []
    probs = plan.get("problems") or []
    waiting_pics = [p for p in probs if "needs the approved picture" in p or "no approved start picture" in p]
    other = [p for p in probs if p not in waiting_pics and not re.search(r"no cloned voice", p)]
    voice_later = [p for p in probs if re.search(r"no cloned voice", p)]
    prompt_only = [p for p in other if is_real(r) and for_the_prompt(p)]
    other = [p for p in other if p not in prompt_only]
    rows.append({"station": "clips-plan",
                 "state": "done" if plan and not other else "stopped",
                 "said": ("no clip plan: " + "; ".join(_stops(out) or out.strip().splitlines()[-2:]))[:600] if not plan else
                         (f"{len(calls)} call(s) planned now; {len(waiting_pics)} section(s) planned once their "
                          f"pictures are approved" + (f"; {len(voice_later)} voice(s) made by the elements station "
                                                      f"first" if voice_later else "")
                          + ("; " + "; ".join(other) if other else "")
                          + (f"; {len(prompt_only)} clip-prompt rule(s) noted, not stops: no prompt is sent on the "
                             f"Real lane (" + "; ".join(prompt_only) + ")" if prompt_only else "")),
                 "problems": probs})
    if is_real(r):
        q = REAL_QUOTE
        rows.append(real_clips_row(run) if plan.get("calls") else
                    {"station": "clips", "state": "stopped", "said": "no clip plan, so no clip is placed"})
    else:
        q = quote(run, waits)
        rows.append({"station": "clips", "state": "waiting", "said": "the paid clip run waits for the owner's go"})
    log.close()
    import hashlib
    res = {"schema": "ai-lane-dry-run/v1", "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "run": r, "shadow": str(run),
           "brief_sha256": hashlib.sha256(Path(r["brief"]).read_bytes()).hexdigest(),
           "stations": rows, "quote": q, "live": live_command(r)}
    (shadow_root / "dry-run.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str) + "\n")
    return res


REAL_QUOTE = {"real": True, "higgsfield_credits": {"low": 0, "likely": 0, "high": 0},
              "clip_credits": {"low": 0, "likely": 0, "high": 0}, "print_credits": 0, "prints": 0,
              "usd": {"low": 0, "likely": 0, "high": 0},
              "note": "Real lane: pictures and clips are the cast's own footage; nothing is generated"}


def for_the_prompt(problem: str) -> bool:
    """A clip-plan problem that guards a generation prompt (clip_rules.py CLIP RULE, clip_checklist.py CHECKLIST): kept
    on the Real run's record and shown, but no stop there, because the Real lane sends no prompt to any model."""
    return str(problem).startswith(("CLIP RULE", "CHECKLIST"))


def real_pictures_row(run: Path) -> dict:
    """The pictures station, Real: every listed picture placed from the cast's own footage (real_door.pictures)."""
    try:
        p = _real_door().pictures(run)
    except SystemExit as e:
        return {"station": "pictures", "state": "stopped", "said": str(e)}
    return {"station": "pictures", "state": "done" if not p["open"] else "stopped",
            "said": f"{p['placed']} picture(s) placed from the cast's own footage ("
                    + ", ".join(f"{k} {v}" for k, v in p["by_role"].items()) + f"), {p['kept']} already there"
                    + (f"; no moment for {', '.join(p['open'])}" if p["open"] else ""),
            "open": p["open"]}


def real_clips_row(run: Path) -> dict:
    """The clips station, Real: every planned call assembled from the cast's moments, then the cast check."""
    try:
        c = _real_door().clips(run)
        k = _real_door().check(run)
    except SystemExit as e:
        return {"station": "clips", "state": "stopped", "said": str(e)}
    ok = not c["open"] and c["made"] + c["kept"] == c["calls"] and k["cast_ok"]
    return {"station": "clips", "state": "done" if ok else "stopped",
            "said": f"{c['made']} clip(s) assembled from {c['pieces']} moment(s) of the cast's footage, "
                    f"{c['kept']} already there, of {c['calls']} planned"
                    + (f"; no moments for {', '.join(c['open'])}" if c["open"] else "")
                    + f"; cast check: {k['cast']}",
            "on_screen": k["on_screen"], "open": c["open"]}


WORDS_A_SECOND = 2.7       # a read's pace for a dry run's length estimate (the Studio's take sheet uses the same)


def stand_in_reads(run: Path) -> int:
    """Silent vo/<scene>.mp3 of each spoken scene's estimated length, in the dry run's shadow only. Returns how many."""
    lines = _read(run / "lines.json", {}) or {}
    (run / "vo").mkdir(parents=True, exist_ok=True)
    n = 0
    for sid, text in lines.items():
        words = len(str(text or "").split())
        f = run / "vo" / f"{sid}.mp3"
        if not words or f.exists():
            continue
        secs = max(1.0, round(words / WORDS_A_SECOND, 2))
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t",
                            str(secs), "-q:a", "9", str(f)], capture_output=True)
        n += r.returncode == 0
    (run / "vo" / "STAND-IN.txt").write_text("Silent stand-ins timed at %s words a second for the dry run's lengths; "
                                             "not a voice.\n" % WORDS_A_SECOND)
    return n


def quote(run: Path, waits: list) -> dict:
    """What the live run spends, from the chain's own budget (budget.py) and the print rate (picture_sets)."""
    try:
        b = _load(HERE / "budget.py", "vp_lane_budget").budget(run)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {str(e)[:160]}"}
    try:
        rate = float(_load(WS / "components" / "image-production" / "picture_sets.py", "vp_lane_ps").PRINT_CREDITS)
    except Exception:  # noqa: BLE001
        rate = PRINT_CREDITS
    cu = b.get("credit_usd") or 0.0
    ruled = next((o for o in b.get("options") or [] if o.get("ruled")), {}) or {}
    lines = b.get("lines") or {}
    prints = round(len(waits) * rate, 1)
    out = {"clip_seconds": (ruled.get("price") or {}).get("seconds"), "model": ruled.get("name"),
           "clip_credits": {k: (lines.get(k) or {}).get("clip_credits") for k in ("low", "likely", "high")},
           "print_credits": prints, "prints": len(waits),
           "swap_credits": {k: round(((lines.get(k) or {}).get("swaps") or 0) / cu) if cu else None
                            for k in ("low", "likely", "high")},
           "usd": {k: (lines.get(k) or {}).get("total") for k in ("low", "likely", "high")},
           "credit_usd": cu}
    out["higgsfield_credits"] = {k: round((out["clip_credits"].get(k) or 0) + prints + (out["swap_credits"].get(k) or 0))
                                 for k in ("low", "likely", "high")}
    return out


def _load_path(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def key_spent(run, rate) -> float:
    """Credits spent on the API key's own pool by this run's clips (2026-11-20): the key pool has no balance to read, so a
    clip the key door took is counted from its checkpoint (its seconds × the quote's credits a second)."""
    total = 0.0
    for c in Path(run).rglob("*.request.json"):
        rec = _read(c, {}) or {}
        if rec.get("door") == "key" and rec.get("request_id"):
            total += float(rec.get("seconds") or 0) * rate
    return round(total, 2)


def run_spent(run, rate, brand=None, label=None) -> float:
    """WHAT THIS RUN ITSELF SPENT (2026-11-21: on a shared account the whole account's spend stopped runs early): every
    clip it sent on any door (its request checkpoint: seconds × the quote's credits a second; a clip sent before
    checkpoints carried seconds takes its ledger row's), and every 3D print the print runner sent for this run (its
    records under runs/image-production/<brand>/print-runner/)."""
    run = Path(run)
    led = _read(run / "clips" / "ledger.json", {}) or {}
    led = led.get("calls", led) if isinstance(led, dict) else {}
    total = 0.0
    for c in run.rglob("*.request.json"):
        rec = _read(c, {}) or {}
        if not rec.get("request_id") or str(rec.get("state") or "") in ("failed", "nsfw", "cancelled", "canceled", "error"):
            continue                       # never sent, or ended failed (refunded)
        cid = c.name.replace("-raw.request.json", "").replace(".request.json", "")
        secs = rec.get("seconds") or (led.get(cid) or {}).get("seconds") or 0
        total += float(secs) * rate
    if brand and label:
        slug = str(label).replace("_", "-").lower()
        for f in (WS / "runs" / "image-production" / str(brand) / "print-runner").glob("*.json"):
            for rid, rep in ((_read(f, {}) or {}).get("requests") or {}).items():
                if str(rid).startswith(slug):
                    total += float(rep.get("credits") or 0)
    return round(total, 2)


def account_spent(rec, start, now_bal):
    """What the account spent since this run's first start: its own transaction list (spends only; a top-up never
    hides spend), else the balance drop. It counts every spend on the account in that window, so it never under-counts."""
    if rec.get("start_at"):
        try:
            if str(HERE) not in sys.path:
                sys.path.insert(0, str(HERE))
            import higgsfield_cli as CLI
            got = CLI.spent_since(rec["start_at"])
            if got is not None:
                return got
        except Exception:  # noqa: BLE001
            pass
    return round(start - now_bal, 2) if now_bal is not None else None


def balance():
    """The signed-in Higgsfield account's balance in credits, read-only, or None. It is the pool the clips spend from
    from (seedance.py DOORS: the account is the root; the API key only when VP_CLIP_DOORS names it, and a clip made
    there is counted by key_spent)."""
    try:
        root = WS / "components" / "image-production"
        if str(root) not in sys.path:
            sys.path.append(str(root))
        from image_production import providers as PV
        return float(PV.higgsfield_ready(PV._HfShell()).get("credits"))
    except Exception:  # noqa: BLE001
        return None


def rate_of(q: dict) -> float:
    """Credits a clip second, from the quote's own one-take numbers (budget.py); 3 when it cannot be read."""
    try:
        return float(q["clip_credits"]["low"]) / float(q["clip_seconds"])
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return 3.0


def live_command(r: dict) -> str:
    wr = Path(r["writing_run"]).name
    if is_real(r):
        return (f"/usr/bin/python3 components/video-production/machine/ai_lane.py {wr} --brand {r['brand']} "
                f"--format {r['format']} --label {r['label']} --lane real --cast "
                + ",".join(f"{k}={v}" for k, v in r["cast"].items()) + " --yes")
    return (f"/usr/bin/python3 components/video-production/machine/ai_lane.py {wr} --brand {r['brand']} "
            f"--format {r['format']} --label {r['label']} --yes --cap <credits>")


# ------------------------------------------------------------------ the live run

def _go_settings(run: Path) -> str:
    """This run's settings: production on auto and not paused, for this process only (the owner's go on this run)."""
    src = Path(os.environ.get("OUTLIER_SETTINGS") or WS / "runs" / "settings" / "settings.json")
    s = _read(src, {}) or {}
    s.setdefault("automation", {}).update({"production": "auto", "paused": False})
    f = Path(tempfile.mkdtemp(prefix="ai-lane-")) / "settings.json"
    f.write_text(json.dumps(s, indent=1))
    trail = run / "ai-lane.json"
    rec = _read(trail, {}) or {}
    rec.setdefault("go", []).append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "by": "the owner's go on this run (--yes)",
                                     "settings": "production auto, not paused, for this run's process only"})
    run.mkdir(parents=True, exist_ok=True)
    trail.write_text(json.dumps(rec, indent=1))
    return str(f)


def passing_dry_run(r: dict) -> dict | None:
    """The dry run of this exact brief on file, every station passed (and in this run's lane), or None."""
    run = run_dir(r)
    dr = _read(run / "dry-run" / "dry-run.json", {}) or {}
    import hashlib
    bp = Path(r["brief"])
    kept = bp.with_name(bp.stem + "-before-bind.md")
    shas = {hashlib.sha256(bp.read_bytes()).hexdigest()} | (
        {hashlib.sha256(kept.read_bytes()).hexdigest()} if kept.is_file() else set())
    if dr.get("brief_sha256") not in shas or not all(s["state"] in ("done", "waiting") for s in dr.get("stations") or [{}]):
        return None
    if ((dr.get("run") or {}).get("lane") or "ai") != r.get("lane", "ai"):
        return None
    return dr


def live(r: dict, cap: float | None = None, clips: bool = True) -> int:
    ok, why = accepted(Path(r["writing_run"]))
    if not ok:
        print("REFUSED: the brief is not accepted by the writing station — " + "; ".join(why))
        return 2
    run = run_dir(r)
    # The quote comes first (the owner approves a number): a dry run of this exact brief must be on file, every
    # station passed, and its high quote under the cap when one is given.
    dr = passing_dry_run(r)
    if dr is None:
        print("REFUSED: no passing dry run of this exact brief on file — run the same command with --dry-run first")
        return 2
    if is_real(r):
        return live_real(r, clips)
    q = (dr.get("quote") or {})
    likely = (q.get("higgsfield_credits") or {}).get("likely")
    if cap is not None and (likely is None or likely > cap):
        print(f"REFUSED: the quote's likely spend ({likely} credits) is over the cap ({cap}); nothing was spent")
        return 2
    # THE CAP IS A STOP, NOT A NUMBER ON A PAGE (2026-11-20): what this run spends is read off the live balance, from
    # the balance at its first start (kept on the run's trail), and the clips go section by section, never into a
    # section whose estimate would carry the spend past the cap.
    trail = run / "ai-lane.json"
    rec = _read(trail, {}) or {}
    bal = balance()
    if bal is None and cap is not None:
        print("REFUSED: the Higgsfield balance cannot be read, so the cap cannot be held; nothing was spent")
        return 2
    if cap is not None:
        run.mkdir(parents=True, exist_ok=True)
        rec.setdefault("start_balance", bal)
        rec.setdefault("start_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        rec.setdefault("key_spent_at_start", key_spent(run, rate_of(q)))
        rec.setdefault("own_spent_at_start", run_spent(run, rate_of(q), r["brand"], r["label"]))
        rec["cap"] = cap
        trail.write_text(json.dumps(rec, indent=1))
    # THE PICTURES ARE THE KEPT 3D SET PRINTS (2026-11-21, brief-0380: the step generated six stills over 18 kept
    # prints): every kept print is taken first, and the picture door is never called in this lane (VP_PRINTS_ONLY)
    env = dict(os.environ, OUTLIER_SETTINGS=_go_settings(run), VP_PRINTS_ONLY="1")
    log = (run / "ai-lane.log").open("a")
    take_sets(run, r["brand"])
    print("1-6 · elements, voice, storyboard, pictures, camera and motion, clip plan (run_v2.py start)", flush=True)
    rc, out = _py(["run_v2.py", "start", r["brief"], "--brand", r["brand"], "--format", r["format"],
                   "--label", r["label"]], env=env, log=log)
    print(out[-4000:])
    # THE 3D PRINTS, ON THIS RUN'S GO (2026-11-20: the one step that had no runner): pictures waiting for their print
    # are printed by image-production's print runner (the 3d-print skill, headless, one print each) under this run's
    # cap, then the picture step goes on from the kept prints. Without a cap the prints wait, said.
    waits = (_read(run / "set-prints.json", {}) or {}).get("waiting") or []
    if waits and cap is not None:
        try:
            pr = _load_path(WS / "components" / "image-production" / "print_runner.py", "al_print_runner")
            todo = pr.waiting(r["brand"], run=r["label"])
            mine = run_spent(run, rate_of(q), r["brand"], r["label"]) - float(
                (_read(trail, {}) or {}).get("own_spent_at_start") or 0)
            room = max(0.0, cap - mine)
            print(f"5b · 3D prints: {len(todo)} request(s) for {len(waits)} waiting picture(s), {room} credits of room",
                  flush=True)
            got = pr.clear(r["brand"], todo, room) if todo else {"requests": {}, "stopped": None}
            for rid, rep in got["requests"].items():
                print(f"  {rid}: {'kept' if rep.get('kept') else 'not kept'} — {rep.get('note') or ''}")
            if got.get("stopped"):
                print("  STOPPED: " + got["stopped"])
            if any(rep.get("kept") for rep in got["requests"].values()):
                take_sets(run, r["brand"])
                rc, out = _py(["run_v2.py", "start", r["brief"], "--brand", r["brand"], "--format", r["format"],
                               "--label", r["label"]], env=env, log=log)
                print(out[-4000:])
        except Exception as e:  # noqa: BLE001 -- the prints wait, said; nothing is made around them
            print(f"5b · 3D prints did not run ({type(e).__name__}: {str(e)[:200]})")
    plan = _read(run / "clips" / "plan.json", {}) or {}
    if clips and (rc not in (0, None) or plan.get("problems") or not plan.get("calls")):
        print("STOP before any clip is paid for — the stations above say why (ai-lane.log); "
              "a re-run of this command goes on from where it stopped")
        log.close()
        return rc or 2
    if not clips:
        end = balance()
        rec = _read(trail, {}) or {}
        start = float(rec.get("start_balance") or bal or 0)
        rec.setdefault("spend", []).append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "start_balance": start,
                                            "balance": end, "spent": round(start - end, 2) if end is not None else None,
                                            "stopped": "before the clips (--no-clips)"})
        trail.write_text(json.dumps(rec, indent=1))
        done = rc in (0, None) and (run / "clips" / "camera-motion.json").is_file()
        print(("STOP before the clips (--no-clips): pictures and the camera and motion plan are in"
               if done else "STOPPED before the pictures: the stations above say why (ai-lane.log)")
              + f"; spent {round(start - end, 2) if end is not None else '?'} credits (balance {end})")
        log.close()
        return 0 if done else (rc or 2)
    if cap is None:
        print("7 · clips (run_v2.py clips --yes)")
        rc, out = _py(["run_v2.py", "clips", str(run), "--yes"], env=env, log=log)
        print(out[-4000:])
        log.close()
        return rc
    rate = rate_of(q)
    start = float((_read(trail, {}) or {}).get("start_balance") or bal)
    key0 = float((_read(trail, {}) or {}).get("key_spent_at_start", key_spent(run, rate)))
    sections = list(dict.fromkeys(c.get("section_id") for c in plan["calls"]))
    rc = 0
    # A CLIP MADE FROM PICTURES SINCE CHANGED IS NOT DONE (2026-11-21, brief-0380: five clips made from the old stills
    # counted as made and their sections were skipped): a section is skipped only when every clip is there and none is
    # stale (clips_run.stale_calls); a stale clip is set aside and made again by its section's run
    try:
        stale = set(_load_path(HERE / "clips_run.py", "al_clips_run").stale_calls(run, plan["calls"]))
    except Exception as e:  # noqa: BLE001 -- unread: every section with a missing clip still runs
        stale = set()
        print(f"7 · clips: the stale check did not run ({type(e).__name__}: {str(e)[:160]})")
    if stale:
        print("7 · clips made from pictures since changed, to make again: " + ", ".join(sorted(stale)))
    for sec in sections:
        calls = [c for c in plan["calls"] if c.get("section_id") == sec]
        if not section_due(run, calls, stale):
            continue
        now_bal = balance()
        own0 = float((_read(trail, {}) or {}).get("own_spent_at_start") or 0)
        spent = round(run_spent(run, rate, r["brand"], r["label"]) - own0, 2)   # this run's own, not the account's
        est = round(sum(max(4.0, float(c.get("seconds") or c.get("duration") or 4)) for c in calls) * rate, 1)
        if spent + est > cap:
            print(f"STOP at the cap: {spent} of {cap} credits spent, section {sec} needs about {est} more — "
                  f"nothing more is sent (balance {now_bal})")
            rc = 3
            break
        print(f"7 · clips {sec} (about {est} credits; {spent} of {cap} spent so far)")
        rc, out = _py(["run_v2.py", "clips", str(run), "--only", sec, "--yes"], env=env, log=log)
        print(out[-1500:])
        # THE SECTION'S OWN CLIPS DECIDE (2026-11-21, brief-0380: the whole-ad count "INCOMPLETE 8/10" after section
        # G02 stopped the loop, so G05 and G06 were never sent): the lane goes on while this section's clips are all made
        if not section_made(run, calls):
            print(f"STOP after section {sec}: not all its clips were made (ai-lane.log) — nothing more is sent")
            rc = rc or 2
            break
        rc = 0
    end = balance()
    rec = _read(trail, {}) or {}
    on_key = round(key_spent(run, rate) - key0, 2)
    total = round(run_spent(run, rate, r["brand"], r["label"]) - float(rec.get("own_spent_at_start") or 0), 2)
    acct = account_spent(rec, start, end)
    rec.setdefault("spend", []).append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "start_balance": start,
                                        "balance": end, "on_api_key": on_key, "spent": total,
                                        "account_spent_in_window": acct})
    trail.write_text(json.dumps(rec, indent=1))
    print(f"spent this run: {total if total is not None else '?'} credits (account balance {end}"
          + (f"; {on_key} of it on the API key" if on_key else "") + ")")
    log.close()
    return rc


def _real_settings(run: Path) -> str:
    """A Real run's settings, for its process only: the automatic elements step stays off (paused), so no person,
    place or prop is ever made for it; the Real elements station binds the cast instead."""
    src = Path(os.environ.get("OUTLIER_SETTINGS") or WS / "runs" / "settings" / "settings.json")
    s = _read(src, {}) or {}
    s.setdefault("automation", {}).update({"paused": True})
    f = Path(tempfile.mkdtemp(prefix="real-lane-")) / "settings.json"
    f.write_text(json.dumps(s, indent=1))
    return str(f)


def live_real(r: dict, clips: bool = True) -> int:
    """THE LIVE REAL RUN: the chain's own doors for voice, storyboard, camera and motion and the clip plan; real_door at
    elements, pictures and clips. No credits: no balance is read and no cap applies. The pictures station places every
    listed picture BEFORE the clip plan runs, so the chain's picture-making step is never reached."""
    run = run_dir(r)
    run.mkdir(parents=True, exist_ok=True)
    rd = _real_door()
    env = dict(os.environ, OUTLIER_SETTINGS=_real_settings(run))
    log = (run / "ai-lane.log").open("a")
    start = ["run_v2.py", "start", r["brief"], "--brand", r["brand"], "--format", r["format"], "--label", r["label"],
             # the Real elements station (real-cast.json) is this run's elements lock: the brief's AI people are bound
             # to real footage or are extras, so the AI bank's lock (which would ask for them to be made) is not asked
             "--no-elements-lock"]
    trail = run / "ai-lane.json"
    rec = _read(trail, {}) or {}
    rec.setdefault("go", []).append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "lane": "real", "cast": r["cast"],
                                     "spend": "none: real footage at every generation station"})
    trail.write_text(json.dumps(rec, indent=1))

    def stop(msg, rc=2):
        print("STOP — " + msg + " (ai-lane.log)")
        log.close()
        return rc

    try:
        er = rd.elements(run, r["brief"], r["brand"], r["cast"])
    except SystemExit as e:
        return stop(f"elements: {e}")
    print(f"1 · elements: {len(er['bound'])} bound to real cast, {len(er['extras'])} footage extra(s), 0 made")
    song_in(r, run)
    rc, out = _py(start + ["--voice-only"], env=env, log=log)
    print("2 · voice: " + ("done" if rc in (0, None) else "; ".join(_stops(out) or out.strip().splitlines()[-2:])))
    if rc not in (0, None):
        return stop("the voice station stopped", rc)
    rc, out = _py(["run_v2.py", "storyboard", str(run), "--brief", r["brief"]], env=env, log=log)
    if rc not in (0, None) or not (run / "storyboard.json").is_file():
        return stop("the storyboard station stopped", rc or 2)
    print("3 · storyboard: " + str(len((_read(run / "storyboard.json", {}) or {}).get("sections") or [])) + " sections")
    row = real_pictures_row(run)
    print("4 · pictures: " + row["said"])
    if row["state"] != "done":
        return stop("a listed picture has no real moment; nothing is generated in its place")
    rc, out = _py(start + ["--clips"], env=env, log=log)
    plan = _read(run / "clips" / "plan.json", {}) or {}
    cm = _read(run / "clips" / "camera-motion.json", {}) or {}
    print(f"5 · camera + motion: {len(cm.get('scenes') or {})} scene(s)" + (" held" if cm.get("held") else ""))
    stops = [p for p in plan.get("problems") or [] if not for_the_prompt(p)]
    print(f"6 · clips plan: {len(plan.get('calls') or [])} call(s)" + ("; " + "; ".join(plan["problems"])
                                                                      if plan.get("problems") else ""))
    if not plan.get("calls") or stops or (rc not in (0, None) and not plan.get("problems")):
        return stop("the clip plan is not green", rc or 2)
    if not clips:
        log.close()
        print("STOP before the clips (--no-clips): pictures and the camera and motion plan are in; nothing spent")
        return 0
    row = real_clips_row(run)
    print("7 · clips: " + row["said"])
    log.close()
    return 0 if row["state"] == "done" else 2


def status(r: dict) -> dict:
    """Where the live run stands, station by station, read from its files (the Studio shows this)."""
    run = run_dir(r)
    cm = _read(run / "clips" / "camera-motion.json", {}) or {}
    plan = _read(run / "clips" / "plan.json", {}) or {}
    sp = dict(_read(run / "set-prints.json", {}) or {})
    # a picture that waited for its 3D print and has since been made (on the picture record) waits no more: the wait
    # list is written by the pass that held it, and a later pass that makes it may not write the list again
    made = _read(run / "direct.json", {}) or {}
    sp["waiting"] = [w for w in sp.get("waiting") or [] if not ((made.get(w.get("picture")) or {}).get("file")
                                                                and Path(made[w["picture"]]["file"]).is_file())]
    calls = [{"id": c.get("id"), "section": c.get("section") or c.get("section_id"), "scenes": c.get("scenes") or [],
              "clip": (str((run / "clips" / f"{c.get('id')}.mp4").relative_to(run))
                       if (run / "clips" / f"{c.get('id')}.mp4").is_file() else None),
              "camera_motion": bool((c.get("camera_motion") or {}).get("ok"))} for c in plan.get("calls") or []]
    # elements: the lock, not the sheet (the sheet is the to-do list)
    done = {"elements": (run / "elements-lock.json").is_file(), "voice": (run / "vo" / "timing.json").is_file(),
            "storyboard": (run / "storyboard.json").is_file(),
            "pictures": (bool(_read(run / "direct.json", {})) and not sp.get("waiting")) or (
                is_real(r) and bool((_read(run / "real-pictures.json", {}) or {}).get("pictures") is not None)
                and not (_read(run / "real-pictures.json", {}) or {}).get("open")),
            "camera": bool(cm.get("scenes")) and not cm.get("held"),
            "clips-plan": bool(plan.get("calls")) and not plan.get("problems"),
            "clips": bool(calls) and all(c["clip"] for c in calls)}
    pictures = sorted(str(p.relative_to(run)) for p in (run / "media").glob("*.png")) if (run / "media").is_dir() else []
    clips = sorted(str(p.relative_to(run)) for p in (run / "clips").rglob("*.mp4")) if (run / "clips").is_dir() else []
    return {"run": str(run), "label": r["label"], "lane": r.get("lane", "ai"),
            "real": {k: _read(run / f, None) for k, f in (("cast", "real-cast.json"), ("check", "real-check.json"))}
            if is_real(r) else None, "stations": [{"id": k, "name": n, "done": done[k]} for k, n in STATIONS],
            "waiting_prints": sp.get("waiting") or [], "camera_motion": {k: v.get("words") for k, v in
                                                                         (cm.get("scenes") or {}).items()},
            "camera_held": cm.get("held") or {}, "problems": plan.get("problems") or [],
            "pictures": pictures, "clips": clips, "calls": calls, "dry_run": _read(run / "dry-run" / "dry-run.json", None)}


def render(res: dict) -> str:
    lane = "Real lane" if res["run"].get("lane") == "real" else "AI lane"
    out = [f"{lane} · {res['run']['label']} · {res['run']['format']} · dry run (nothing spent)", ""]
    for s in res["stations"]:
        out.append(f"  {s['state']:<8} {s['station']:<11} {s['said']}")
    q = res.get("quote") or {}
    if q.get("real"):
        out += ["", "Quote: 0 credits, $0 — " + q["note"]]
    elif q and not q.get("error"):
        out += ["", f"Quote (Higgsfield credits, low / likely / high): "
                    f"{q['higgsfield_credits']['low']} / {q['higgsfield_credits']['likely']} / {q['higgsfield_credits']['high']}"
                    f"  = clips {q['clip_credits']['low']}/{q['clip_credits']['likely']}/{q['clip_credits']['high']} "
                    f"({q.get('model')}, {q.get('clip_seconds')} s billed) + {q['prints']} 3D prints {q['print_credits']} "
                    f"+ swaps {q['swap_credits']['low']}/{q['swap_credits']['likely']}/{q['swap_credits']['high']}",
                f"All-in dollars (pictures, voice, clips, swaps): ${q['usd']['low']} / ${q['usd']['likely']} / ${q['usd']['high']}"]
    out += ["", "Live run (on the owner's go): " + res["live"], f"Shadow run: {res['shadow']}"]
    return "\n".join(out)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("source", nargs="+", help="[status] <writing run label | 5-brief.md>")
    ap.add_argument("--brand"); ap.add_argument("--format"); ap.add_argument("--label")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="the live run: spends, on the owner's approval")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-clips", dest="clips", action="store_false",
                    help="with --yes: stop before the clips (pictures and the camera and motion plan only)")
    ap.add_argument("--cap", type=float, help="with --yes: refuse when the dry run's high quote is over this many credits")
    ap.add_argument("--lane", choices=("ai", "real"),
                    help="real: the same stations with the cast's own footage at generation (real_door.py)")
    ap.add_argument("--cast", help="the Real cast: BRIEF_ID=cast-bank-id,... (the first is the lead)")
    a = ap.parse_args(argv)
    verb = a.source[0] if a.source[0] == "status" and len(a.source) > 1 else None
    r = resolve(a.source[-1], a.brand, a.format, a.label, a.lane, a.cast)
    if verb == "status":
        print(json.dumps(status(r), indent=1, ensure_ascii=False, default=str))
        return 0
    if a.dry_run or not a.yes:
        res = dry_run(r)
        print(json.dumps(res, indent=1, ensure_ascii=False, default=str) if a.json else render(res))
        if not a.dry_run:
            print("\n(no --yes: this was the dry run; the live run spends and waits for the owner's go)")
        return 0 if all(s["state"] in ("done", "waiting") for s in res["stations"]) else 2
    return live(r, a.cap, a.clips)


if __name__ == "__main__":
    sys.exit(main())
