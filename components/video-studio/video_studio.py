"""Video Studio: every scene of a brief is a node with its own saved workflow.

  python3 video_studio.py serve [--port 8921]   the canvas page
  python3 video_studio.py run <brief> S1           rerun one scene alone (what the scheduled agent calls)
  python3 video_studio.py package <brief>          write the production package for HyperFrames

A workflow (briefs/<n>/scenes/<S>/take-N.json) holds every step: tool, model,
prompt, seed, inputs, params. A run writes the scene file, a thumbnail, its
caption layer and a run record next to it, so one scene remakes alone and the
assembly picks up whatever take is picked.
"""
import datetime
import glob
import hashlib
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.normpath(os.path.join(HERE, os.pardir, "video-edit", "machine", "studio")))  # the edit's own home (Video Edit), 2026-11-21
import settings as ST  # noqa: E402
import covers_stage as CS  # noqa: E402  (the cover stage: after render, every version's cover, by itself)
import edit_stage as ES  # noqa: E402  (the edit stage: after render, the swipe's edit moves laid, before the covers)
import ai_shots as AS  # noqa: E402  (an AI-lane production's AI shots made on the scene chain, before the hand-off)
BRIEFS = str(ST.BRIEFS)
SOURCES = str(ST.SOURCES)
DRIVE_ROOTS = ST.DRIVE_ROOTS
LOCK = threading.Lock()
RUNNING = {}
MAKING = {}   # AI shots with a take being made right now (Production view: pick a clip model, make a take)
RUNNABLE = {"ffmpeg.trim", "voice.read", "layer.photo", "layer.offer", "hyperframes.card", "gen.take"}  # tools this canvas can run today; others show what they wait on
WAITS = {"voice.ai": "AI voice", "gen.shot": "shot print", "gen.take": "take print", "human.read": "voice read", "capture.page": "page capture", "layer.photo": "edit layer",
         "layer.offer": "edit layer"}


# Phone look for generated shots: a lower-resolution sensor, softer and flatter colour, grain, a small handheld drift.
PHONE_LOOK = ("noise=alls=6:allf=t+u,"
              "crop=1040:1850:20+14*sin(t*1.7)+6*sin(t*4.1):35+10*sin(t*1.3)+5*sin(t*3.7),scale=1080:1920,setsar=1")


def upscaled(src, height):
    """An approved generated clip at delivery size: the house upscaler (MODEL-HOUSE behind.upscale: local Real-ESRGAN,
    components/local-studio/local.py) x4, then down to `height` (720 or 1080 tall, 9:16) with lanczos. Clips are made at
    480p and upscaled only once the cut is approved (brief deliver.upscale; owner, 10 Nov 2026). The x4 frames are kept
    in up/ so a second size costs nothing."""
    w = int(round(height * 9 / 16 / 2)) * 2
    out = os.path.join(SOURCES, "generated", "up", f"{height}-" + os.path.basename(src))
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
        return out
    have = int((subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=height", "-of", "csv=p=0", src],
                               capture_output=True, text=True).stdout.strip() or "0").split(",")[0])
    if have >= height:
        return src
    os.makedirs(os.path.dirname(out), exist_ok=True)
    up = os.path.join(SOURCES, "generated", "up")
    big = next((os.path.join(up, f"{h}-" + os.path.basename(src)) for h in (2160, 1440, 1080) if h > height
                and os.path.exists(os.path.join(up, f"{h}-" + os.path.basename(src)))
                and os.path.getmtime(os.path.join(up, f"{h}-" + os.path.basename(src))) >= os.path.getmtime(src)), None)
    if big:                                  # a larger upscale of the same take exists: bring it down, never upscale twice
        ff(["-i", big, "-an", "-vf", f"scale={w}:{height}:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", out])
        return out
    x4 = os.path.join(up, "x4-" + os.path.basename(src))
    if not os.path.exists(x4) or os.path.getmtime(x4) < os.path.getmtime(src):
        subprocess.run([sys.executable, str(ST.part("local-studio") / "local.py"), "upscale", src, "-o", x4, "--scale", "4"], check=True)
    ff(["-i", x4, "-an", "-vf", f"scale={w}:{height}:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", out])
    return out


def phone_copy(src, upscale=None):
    """A generated clip with a light phone look, applied last and never degrading the clip: a touch of contrast, colour
    and sensor grain at the clip's own size (480p while the cut is being made; `upscale` = 720 or 1080 once the cut is
    approved, upscaled first). No shrink, blur or crushing compression: that pass made the AI shots look low quality."""
    tag = f"{upscale}-" if upscale else "480-"
    out = os.path.join(SOURCES, "generated", "phone", "look-" + tag + os.path.basename(src))
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        base = upscaled(src, int(upscale)) if upscale else src
        os.makedirs(os.path.dirname(out), exist_ok=True)
        ff(["-i", base, "-an", "-vf", "eq=contrast=0.97:saturation=0.94,noise=alls=5:allf=t,fps=30",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", out])
    return out


def bdir(n):
    return os.path.join(BRIEFS, n)


def sdir(n, s):
    return os.path.join(bdir(n), "scenes", s)


def load(p):
    with open(p) as f:
        return json.load(f)


def save(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


# ---------------------------------------------------------------- one script: storyboard words = production lines
# The storyboard's Words box, this scene's voice lines and the print sheet's script are one script (owner, 9 Nov):
# a storyboard edit is pulled in when the scene is opened here; a line changed here is written back to the storyboard.
import script_lines as SL  # noqa: E402


def _board_file(idea):
    root = Path(os.environ.get("VIDEO_STUDIO_BOARD_DATA") or ST.REPO / "runs" / "storyboard")
    return root / "owner-edits" / (str(idea) + ".json")


def _board_words(idea, s):
    try:
        v = ((json.loads(_board_file(idea).read_text()).get("scene_edits") or {}).get(s) or {}).get("voice")
    except (OSError, ValueError):
        return None
    return v if isinstance(v, str) and v.strip() else None


def _push_board(idea, s, text):
    """Write a scene's words into the storyboard through its own save (revision-checked). True when saved."""
    import urllib.request as _u
    url = BOARD + "/api/cards/" + str(idea)
    try:
        cur = json.load(_u.urlopen(url, timeout=6))
        edits = dict(cur.get("scene_edits") or {})
        edits[s] = dict(edits.get(s) or {}, voice=text)
        body = {k: cur.get(k) or ("" if k in ("script", "notes", "lane", "requirements") else {}) for k in
                ("script", "notes", "lane", "requirements", "opening_edits", "production_notes")}
        body.update(revision=cur.get("revision"), scene_edits=edits,
                    source_hash=(cur.get("backend") or {}).get("production_brief_hash"))
        req = _u.Request(url, data=json.dumps(body).encode(), method="PUT", headers={"Content-Type": "application/json"})
        _u.urlopen(req, timeout=8).read()
        return True
    except Exception:  # noqa: BLE001 — the storyboard being down or busy leaves the line marked unsent, retried on open
        return False


def _set_wf_lines(wf, rows):
    """Lay the lines on a workflow: one voice step per line (kept steps keep their id, model and settings)."""
    steps = wf.get("steps") or []
    voice = [st for st in steps if st.get("tool") in ("voice.ai", "human.read")]
    old = [{"speaker": (st.get("params") or {}).get("speaker") or "", "say": st.get("prompt") or ""} for st in voice]
    renamed = {o["say"]: r["say"] for o, r in zip(old, rows) if o["say"] != r["say"]}
    if not voice:                       # a scene read some other way (a real recording): only its words change
        wf["words"] = " ".join(r["say"] for r in rows)
        return wf
    at = steps.index(voice[0])
    used = {st.get("id") for st in steps if st not in voice}
    made = []
    for k, r in enumerate(rows, 1):
        st = json.loads(json.dumps(voice[k - 1] if k <= len(voice) else voice[-1]))
        if k > len(voice) or not st.get("id") or st["id"] in used:
            st["id"] = next(i for i in ("voice-%d" % j for j in range(k, 999)) if i not in used)
        used.add(st["id"])
        st["prompt"] = r["say"]
        st["params"] = dict(st.get("params") or {}, speaker=r.get("speaker") or "", order=k)
        st["note"] = "AI voice read of %s line %d" % (r.get("speaker") or "the", k)
        made.append(st)
    wf["steps"] = [st for st in steps[:at] if st not in voice] + made + [st for st in steps[at:] if st not in voice]
    for st in wf["steps"]:
        p = st.get("params") or {}
        if st.get("tool") == "gen.take" and isinstance(p.get("script"), list):
            p["script"] = [{"speaker": r.get("speaker") or "", "say": r["say"]} for r in rows]
        for ln in p.get("lines") or []:
            if isinstance(ln, dict) and ln.get("say") in renamed:
                ln["say"] = renamed[ln["say"]]
    wf["words"] = " ".join(r["say"] for r in rows)
    return wf


def _set_print_lines(n, s, rows):
    """The print sheet (take.json) carries the same lines: a changed line is read again in its voice by take.py."""
    p = os.path.join(sdir(n, s), "take.json")
    if not os.path.exists(p):
        return
    tk = load(p)
    script = tk.get("script")
    if not isinstance(script, list) or SL.same(script, rows):
        return
    voiced = {k for k, c in (tk.get("cast") or {}).items() if isinstance(c, dict) and c.get("voice")}
    out = []
    for k, r in enumerate(rows):
        ln = dict(script[k]) if k < len(script) else {}
        if ln.get("speaker") == (r.get("speaker") or "") and SL.plain(ln.get("say")) == SL.plain(r["say"]):
            out.append(ln)              # the same words: the line and its read stay as they are
            continue
        if ln.get("say") != r["say"] or ln.get("speaker") != r.get("speaker"):
            if (r.get("speaker") or "") in voiced:
                ln.pop("read", None)
        ln["speaker"], ln["say"] = r.get("speaker") or "", r["say"]
        out.append(ln)
    tk["script"] = out
    save(p, tk)


def _wf_rows(wf):
    return [b for b in _beats(wf) if b.get("say")]


def pull_board_words(n, s, brief):
    """A storyboard edit made since this scene last matched it is laid on every take of the scene and its print sheet;
    a line changed here that never reached the storyboard is sent first."""
    idea = brief.get("idea")
    if not idea:
        return
    text = _board_words(idea, s)
    pick = os.path.join(sdir(n, s), str(brief["picks"].get(s)) + ".json")
    if text and os.path.exists(pick) and not load(pick).get("words_unsent"):
        cur = _wf_rows(load(pick))       # words written run together over several speakers: back to one line each
        tidy = SL.written(SL.lines(text, cur, (cur[0]["speaker"] if cur else "")))
        if tidy and tidy != text and "\n" in tidy and _push_board(idea, s, tidy):
            text = tidy
    for p in sorted(glob.glob(os.path.join(sdir(n, s), "take-*.json"))):
        wf = load(p)
        if wf.get("words_unsent"):
            if _push_board(idea, s, wf["words_unsent"]):
                wf["words_from"] = wf.pop("words_unsent")
                save(p, wf)
            continue
        if text is None or wf.get("words_from") == text:
            continue
        cur = _wf_rows(wf)
        rows = SL.lines(text, cur, (cur[0]["speaker"] if cur else ""))
        if rows and not SL.same(rows, cur):
            _set_wf_lines(wf, rows)
        wf["words_from"] = text
        save(p, wf)
        if rows and os.path.basename(p)[:-5] == brief["picks"].get(s):
            _set_print_lines(n, s, rows)


def push_wf_words(n, s, brief, before, wf):
    """Lines changed in production go back to the storyboard and the print sheet."""
    rows = _wf_rows(wf)
    if SL.same(rows, _wf_rows(before)):
        return wf
    wf["words"] = " ".join(r["say"] for r in rows)
    text = SL.written(rows)
    if brief.get("idea") and _push_board(brief["idea"], s, text):
        wf["words_from"] = text
        wf.pop("words_unsent", None)
    elif brief.get("idea"):
        wf["words_unsent"] = text
    _set_print_lines(n, s, rows)
    return wf


# ---------------------------------------------------------------- handoff: one click, idea -> brief -> production
# The owner, 9 Nov: after Prepare handoff, a loading screen confirms it, shows the brief being made step by step with a
# progress bar, then opens the next screen. Every step is the system's own door; a step that can't finish says why and
# the rest still run. The Queue's "Approve brief" door is not pressed here: it starts the older production line, and
# production for these ideas is this Studio.
HANDOFF = {}          # job id -> {"idea", "steps": [...], "done", "open"}
HANDOFF_STEPS = [("saved", "Approved script saved"), ("checks", "Brief checks, with your OK"),
                 ("production", "Production ready"), ("open", "Opening Production")]


def _ws():
    """The workspace the writing runs and the Queue live in."""
    return Path(ST.WRITING).resolve().parents[2]


def _lane():
    """The chain's rule for how an ad is made (components/video-production/machine/lane.py), loaded by its file from
    the workspace the writing runs live in. The Studio shows the call and its reason; it never decides one, and no
    reader here assumes a lane of its own (the logic layer, 2026-11-18)."""
    import importlib.util
    k = "chain_video_production_lane"
    if k not in sys.modules:
        # the workspace the writing runs live in first, else the one this Studio sits in
        f = next(x for x in (Path(ST.part("video-production", _ws())) / "machine" / "lane.py",
                             Path(ST.part("video-production")) / "machine" / "lane.py") if x.is_file())
        spec = importlib.util.spec_from_file_location(k, str(f))
        m = importlib.util.module_from_spec(spec)
        sys.modules[k] = m
        try:
            spec.loader.exec_module(m)
        except BaseException:
            sys.modules.pop(k, None)
            raise
    return sys.modules[k]


def lane_of(brief):
    """The lane a production runs in: {"lane", "why", "by"}, from the chain."""
    return _lane().of(brief)


def _say(job, sid, state, said=""):
    for st in job["steps"]:
        if st["id"] == sid:
            st["state"], st["said"] = state, said
    if job.get("file"):                  # a Next step runs in its own process: its state lives on disk
        save(job["file"], job)


def _post_queue(path, body):
    import urllib.request as _u
    import urllib.error as _ue
    req = _u.Request(ST.LEDGER + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        return json.loads(_u.urlopen(req, timeout=120).read() or b"{}")
    except _ue.HTTPError as e:
        try:
            return {"error": json.loads(e.read() or b"{}").get("error") or "the Queue said %s" % e.code}
        except ValueError:
            return {"error": "the Queue said %s" % e.code}
    except Exception:  # noqa: BLE001
        return {"error": "The Queue isn't answering on this Mac."}


def _checks_running(run):
    try:
        ps = subprocess.run(["ps", "-ax", "-o", "command="], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return any("brief_recheck.py" in ln and run in ln for ln in ps.splitlines())


def _restamp_writing(w, before_sha):
    """The checks stamp the brief's first line, which changes its fingerprint; the storyboard reads a changed
    fingerprint as a writing update still in progress and locks editing. A finished update is moved to the new one."""
    p, m = w / "stages" / "5-brief.md", w / "writing-update.json"
    if not (p.is_file() and m.is_file()):
        return
    now = hashlib.sha256(p.read_bytes()).hexdigest()
    try:
        old = json.loads(m.read_text())
    except ValueError:
        return
    if now == old.get("source_sha256") or old.get("state") != "complete" or old.get("source_sha256") != before_sha:
        return
    m.write_text(json.dumps({"state": "complete", "source_sha256": now, "reason": "The brief checks stamped the brief.",
                             "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             "previous_update": old, "validation": old.get("validation"),
                             "production_acceptance": old.get("production_acceptance", False)}, indent=2) + "\n")


def _checks_why(run, st5):
    """Why the brief checks held, in plain words: the check's own result first (its log), then the run's note."""
    log = _ws() / "runs" / "queue" / "jobs" / (run + "-approve.log")
    try:
        res = json.loads(log.read_text().strip().splitlines()[-1])
    except (OSError, ValueError, IndexError):
        res = {}
    err = str(res.get("swipe_match_error") or "")
    if "402" in err:
        return "The swipe check couldn't run: Google Gemini's prepaid credit is empty (402 Payment Required). Top it up, then press Make the brief again."
    if "429" in err:
        return "The swipe check couldn't run: Google Gemini's daily limit is used up. It resets at 3pm Thailand time."
    if err:
        return "The swipe check couldn't run: " + err[:200]
    if res.get("swipe_match") == "HELD" and not (Path(ST.WRITING) / run / "swipe-match.json").is_file():
        return "The swipe check couldn't run: it stopped before judging (most often Google Gemini's credit or daily limit)."
    if res.get("swipe_match") == "HELD":
        return "The swipe check found changes from the swipe that need your OK by number (SWIPE-MATCH.md in the run)."
    if res.get("manifest_core_missing"):
        return "The script is missing required parts: " + ", ".join(res["manifest_core_missing"][:6])
    return "Held: " + str(st5.get("error") or "a check flagged the script")[:240]


def _run_handoff(job):
    import time as _t
    idea = job["idea"]
    board = Path(os.environ.get("VIDEO_STUDIO_BOARD_DATA") or ST.REPO / "runs" / "storyboard")
    # 1. the approved script, as the storyboard saved it on the click
    _say(job, "saved", "doing")
    snap = board / "handoff-requests" / (idea + ".json")
    try:
        req = json.loads(snap.read_text())
    except (OSError, ValueError):
        _say(job, "saved", "stopped", "Press Prepare handoff on the storyboard first.")
        job["done"] = True
        return
    run = req.get("backendRun") or idea_runs().get(idea) or ""
    _say(job, "saved", "done", "%d scenes, exactly as you approved them" % len(req.get("scenes") or []))
    w = Path(ST.WRITING) / run
    rj_path = w / "run.json"
    rj = lambda: json.loads(rj_path.read_text()) if rj_path.is_file() else {}  # noqa: E731
    # 2. the brief's own checks, with his OK on what they flag (the Queue's advance door, never a rewrite)
    _say(job, "checks", "doing", "Running the brief's checks")
    bp5 = w / "stages" / "5-brief.md"
    before_sha = hashlib.sha256(bp5.read_bytes()).hexdigest() if bp5.is_file() else None
    st5 = (rj().get("stages") or {}).get("stage5") or {}
    if st5.get("status") == "done":
        _say(job, "checks", "done", "Already passed")
    elif not rj():
        _say(job, "checks", "stopped", "This idea's script isn't on this Mac.")
    else:
        r = {} if _checks_running(run) else _post_queue("/api/queue/advance", {"id": "%s_idea_%s" % (rj().get("brand"), run)})
        if r.get("error"):
            _say(job, "checks", "stopped", r["error"])
        else:
            t0 = _t.time()
            while _t.time() - t0 < 900:
                _t.sleep(4)
                st5 = (rj().get("stages") or {}).get("stage5") or {}
                if st5.get("status") == "done":
                    _say(job, "checks", "done", "Passed")
                    break
                if _t.time() - t0 > 20 and not _checks_running(run):
                    _say(job, "checks", "stopped", _checks_why(run, st5))
                    break
                _say(job, "checks", "doing", "Running the brief's checks · %ds" % int(_t.time() - t0))
            else:
                _say(job, "checks", "stopped", "Still running after 15 minutes; it carries on by itself.")
    _restamp_writing(w, before_sha)
    # his click is his Approve brief: recorded on the Queue's own card (the Queue's record-only door), so the board,
    # the Studio and every tool read Handed off · making; the approval door is not pressed (it starts the older line)
    if ((rj().get("stages") or {}).get("stage5") or {}).get("status") == "done":
        r = _post_queue("/api/queue/decided", {"kind": "produce", "id": run, "action": "approve"})
        st = next(x for x in job["steps"] if x["id"] == "checks")
        if st["state"] == "done":
            st["said"] = (st["said"] + " · your OK is on the Queue") if r.get("ok") else st["said"]
    # The brief number is not a step here: it names the delivery and the Meta ad, so it is given when the finished
    # ad is filed for approval (the register's own lane open on the production's filed run, as 0322 got its number).
    number = rj().get("brief")
    # 4. production: the idea's production, with the approved lines on every scene. HOW IT IS MADE is the chain's call
    # (lane.py: the maker route, the format, the style and the footage decision, with the reason) unless a person
    # picked a lane at Produce; the Studio shows the call (2026-11-18).
    call = _lane().chosen(job.get("lane"), w)
    lane = job["lane"] = call["lane"]
    job["lane_call"] = call
    if lane == "creator":                    # a creator films it: the creator brief joins the creator hub, open to every creator
        _say(job, "production", "doing", "Writing the creator brief from this swipe (about 10 minutes)…")
        try:
            import creator_lane as CL
            label = CL.branch(run)
            brand = json.loads((CL.WORK / label / "run.json").read_text()).get("brand")
            page = CL.write(label, brand)
            CL.to_hub(brand, page, label)
            _say(job, "production", "done", "In the creator hub as a draft, open to every creator once you say yes. Nothing is sent.")
            job["open"] = {"creator_hub": brand}
        except Exception as e:  # noqa: BLE001 — said on the screen
            _say(job, "production", "stopped", "The creator brief could not be made: " + str(e)[:200])
        _say(job, "open", "done")
        job["done"] = True
        return
    _say(job, "production", "doing")
    have = next((p for p in productions() if p.get("idea") == idea), None)
    # Produce again fills any scene the production is missing, the way it is picked now (a scene set aside, a scene
    # the storyboard added); takes already there are never touched (the seed skips them)
    gap = False
    if have:
        try:
            hb = load(os.path.join(bdir(have["n"]), "brief.json"))
            gap = any(not os.path.exists(_pick_take(have["n"], s, hb)) for s in hb.get("order") or [])
            # a lane switch at Produce (Real -> AI / AI + Real) re-seeds the takes still waiting on footage (16 Nov)
            if not gap and lane in ("ai", "mix"):
                gap = any(st.get("tool") == "footage.find" for s in hb.get("order") or []
                          for st in (load(_pick_take(have["n"], s, hb)).get("steps") or []))
        except (OSError, ValueError, KeyError):
            gap = False
    if not have or gap:
        try:
            subprocess.run(["/usr/bin/python3", os.path.join(HERE, "seed_from_brief.py"), idea, "--lane", lane,
                            "--lane-why", call["why"], "--lane-by", call["by"]], cwd=HERE,
                           capture_output=True, text=True, timeout=300, env=dict(os.environ))
        except (OSError, subprocess.SubprocessError):
            pass
        have = next((p for p in productions() if p.get("idea") == idea), None)
    if not have:
        _say(job, "production", "stopped", "Production could not be set up for this idea.")
        job["done"] = True
        return
    n = have["n"]
    bp = os.path.join(bdir(n), "brief.json")
    brief = load(bp)
    if lane in ("ai", "mix", "real") and brief.get("lane") != lane:   # the storyboard's Produce choice is the lane
        brief["lane"] = lane
        save(bp, brief)
    if number and brief.get("brief_key") is None:
        prod = rj().get("product") or ""
        try:
            sys.path.insert(0, str(_ws() / "components" / "naming"))
            import names as NM
            prod = NM.product_id(rj().get("brand"), prod) or prod
        except Exception:  # noqa: BLE001
            pass
        brief["brief_key"] = "%s_%s_%s" % (rj().get("brand"), prod, number)
        save(bp, brief)
    for s in brief.get("order") or []:
        try:
            pull_board_words(n, s, brief)
        except (OSError, ValueError, KeyError, TypeError):
            pass
    made = lane_of(brief)                    # the production's own record: what it is made as, and why
    _say(job, "production", "done", "%d scenes with your lines · made as %s: %s" % (
        len(brief.get("order") or []), _lane().label(made["lane"]), made["why"]))
    _say(job, "open", "done")
    job["open"] = {"stage": "production", "n": n}
    job["done"] = True


def handoff_start(idea, lane=None):
    for jid, j in HANDOFF.items():
        if j["idea"] == idea and not j["done"]:
            return {"job": jid}
    jid = "%s-%d" % (idea, int(datetime.datetime.now().timestamp()))
    HANDOFF[jid] = {"idea": idea, "done": False, "open": None, "lane": lane,
                    "steps": [{"id": i, "name": nm, "state": "waiting", "said": ""} for i, nm in HANDOFF_STEPS]}
    def safe(job):
        try:
            _run_handoff(job)
        except Exception as e:  # noqa: BLE001 — a step that breaks says so on the screen
            st = next((x for x in job["steps"] if x["state"] in ("doing", "waiting")), None)
            if st:
                st["state"], st["said"] = "stopped", "Something broke here: " + str(e)[:200]
            job["done"] = True
    threading.Thread(target=safe, args=(HANDOFF[jid],), daemon=True).start()
    return {"job": jid}


# ---------------------------------------------------------------- next step: one button runs production's next stage
# Rule (10 Nov): every production stage starts from one Studio button, as the handoff does. Production's Next step
# button runs whichever stage is due, on the same loading screen as the handoff.
# Each stage is the system's own tool, run as is; a stage that can't finish says why in plain words.
NEXT_STAGES = {
    "shots": ("Find our shots", [("list", "Shot list from the swipe"), ("fill", "Our footage searched for every shot"),
                                 ("picks", "Best owned clip placed on each shot"),
                                 ("said", "Everything the voice names placed from our footage")]),
    "voice": ("Read the narration", [("read", "Narration read and heard back"), ("place", "Each scene's lines placed")]),
    "cut": ("Cut the scenes", [("cut", "Every scene cut clean from its shots")]),
    "check": ("Check the edit", [("check", "Checked: clean cuts, every shot in, no clip twice")]),
    "render": ("Render the version", [("build", "The edit built from the cut"), ("render", "Rendered for phones, 1080 x 1920"),
                                      ("loud", "Sound set to -14 LUFS"), ("heard", "Every word heard back"),
                                      ("hooks", "Every hook and footage version rendered")]),
    "edit": ("Lay the swipe's edit moves", ES.STEPS),   # 2026-11-13: render → edit → covers (edit_stage.py)
    "covers": ("Make the covers", CS.STEPS),     # 2026-11-12: covers are the machine's job (covers_stage.py)
    # 2026-11-16 (owner): "when i say it's done everything needs to be on the queue with its brief number and the
    # instructions for the editor to carry out". A production whose rest waits on the maker's clips is handed off by
    # itself: numbered, packed (brief, clips, timeline, Premiere, HyperFrames), and on the queue as Ready for the editor
    # 2026-11-20 (owner): every production moves through the process. An AI-lane production's AI shots (gen.shot) are
    # made on the scene chain here (ai_shots.py: take sheet, camera and motion plan, start picture, take, laid in)
    # before the hand-off; no clip is made by hand
    "aishots": ("Make the AI shots", AS.STEPS),
    "maker": ("Hand off to the editor", [("number", "Brief number from the register"),
                                          ("pack", "Hand-off packed: brief, clips, timeline, Premiere, HyperFrames"),
                                          ("queue", "On the queue for the editor")]),
    # a sung ad (owner, 17 Nov 2026): the song comes first, made in Suno from the brief's song block, heard back line
    # by line, then every scene is laid on its time on the song (song_view.py; song.py makes and checks the song)
    "song": ("Make the song in Suno", [("suno", "Suno's boxes written from the brief's song block"),
                                       ("take", "A take from Suno added")]),
    "songcheck": ("Check the song", [("heard", "Every line heard on the song")]),
    "songcut": ("Cut to the song", [("cut", "Every scene laid on its time on the song")]),
}
SONG_TAKES = (".mp3", ".m4a", ".wav")


def song_of(n):
    """(sung brief, its production run) for a production whose writing brief is sung; (None, None) for a spoken ad.
    The brief is the writing run's own (brief.json "brief" names it); the song lives in the production run named after
    that writing run (song_view.production_run)."""
    import song_view as SV
    try:
        b = load(os.path.join(bdir(n), "brief.json"))
    except (OSError, ValueError):
        return None, None
    slug = str(b.get("brief") or "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", slug):
        return None, None
    wr = Path(ST.WRITING) / slug
    sb = SV.brief_of(wr) or {}
    brand = b.get("brand") or sb.get("brand") or (load(str(wr / "run.json")).get("brand") if (wr / "run.json").is_file() else None)
    run = SV.production_run(_ws() / "runs", brand, slug)
    if not SV.song_block(sb, run):              # the idea is a song ad only when its brief or its song run sings
        return None, None
    return sb, run


def _song_takes(run):
    """Takes made in Suno and added to the run (song/suno-takes/), oldest first."""
    d = Path(run) / "song" / "suno-takes"
    return sorted((f for f in d.iterdir() if f.suffix.lower() in SONG_TAKES), key=lambda f: f.stat().st_mtime) if d.is_dir() else []


def song_state(n):
    """The song card and the Song track of a sung production: style, BPM, vocal, the sections on the song's clock,
    each scene's time on the song, Suno's boxes once written, the takes added and the gate's verdict."""
    import song_view as SV
    sb, run = song_of(n)
    if not sb:
        return {"sung": False}
    v = SV.view(sb, run)
    v["times"] = SV.scene_times(load(os.path.join(bdir(n), "brief.json")).get("order") or [], v)
    sd = Path(run) / "song" if run else None
    v["suno"] = load(str(sd / "suno-inputs.json")) if sd and (sd / "suno-inputs.json").is_file() else None
    v["takes"] = [f.name for f in _song_takes(run)] if run else []
    v["cut"] = os.path.isfile(os.path.join(bdir(n), "song-cut.json"))
    return v


def song_due(n):
    """The song stage a sung production is at, or None (spoken, or the song is made, heard and laid out)."""
    try:
        sb, run = song_of(n)
        if not sb or not run:
            return None
        sd = Path(run) / "song"
        rec, takes = sd / "song.json", _song_takes(run)
        if takes and (not rec.exists() or takes[-1].stat().st_mtime > rec.stat().st_mtime):
            return "songcheck"                      # a take was added since the song was last heard
        if not (sd / "song.mp3").exists() or not load(str(rec)).get("pass"):
            return "song"
        cut, timing = Path(bdir(n)) / "song-cut.json", sd / "timing.json"
        if not cut.exists() or (timing.exists() and cut.stat().st_mtime < timing.stat().st_mtime):
            return "songcut"
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return None


def song_take_add(n, name, data):
    """A take made in Suno, added from the Song row: saved under song/suno-takes/ and never over an earlier one."""
    sb, run = song_of(n)
    if not sb or not run:
        raise ValueError("this ad is not sung")
    ext = os.path.splitext(str(name or ""))[1].lower()
    if ext not in SONG_TAKES or not data:
        raise ValueError("a take is an mp3, m4a or wav file")
    d = Path(run) / "song" / "suno-takes"
    d.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", os.path.splitext(os.path.basename(name))[0]).strip("-") or "take"
    f, k = d / (stem + ext), 2
    while f.exists():
        f, k = d / ("%s-%d%s" % (stem, k, ext)), k + 1
    f.write_bytes(data)
    return {"take": f.name}


def _song_tool(job, sid, args, timeout=900):
    """song.py (video-production's song door), run as it is run by hand; its last line is what the step says."""
    tool = Path(ST.part("video-production", _ws())) / "machine" / "song.py"
    r = subprocess.run([sys.executable, str(tool)] + [str(a) for a in args], capture_output=True, text=True,
                       cwd=str(tool.parent), env=os.environ, timeout=timeout)
    tail = [ln for ln in (r.stdout + "\n" + r.stderr).splitlines() if ln.strip()]
    if r.returncode:
        _say(job, sid, "stopped", (tail[-1] if tail else "the song door stopped")[:240])
    return r.returncode == 0


def _run_song(job):
    import song_view as SV
    n, stage = job["n"], job["stage"]
    sb, run = song_of(n)
    if not sb or not run:
        _say(job, job["steps"][0]["id"], "stopped", "This ad's brief is not sung.")
        return
    if stage == "song":
        _say(job, "suno", "doing")
        plan = Path(run) / "plan.json"
        if not plan.exists():                       # the run song.py reads: the sung brief as written, never edited
            brief = load(os.path.join(bdir(n), "brief.json"))
            Path(run).mkdir(parents=True, exist_ok=True)
            save(str(plan), dict(sb, brand=sb.get("brand") or brief.get("brand") or Path(run).parent.name,
                                 title=sb.get("title") or brief.get("title") or Path(run).name))
        if not _song_tool(job, "suno", [run, "--suno"]):
            return
        su = load(str(Path(run) / "song" / "suno-inputs.json"))
        _say(job, "suno", "done", "Style, lyrics and title ready on the Song row (%s)" % (su.get("model") or "Suno"))
        _say(job, "take", "later", "Make the song in Suno with those boxes, then add the take on the Song row.")
    elif stage == "songcheck":
        _say(job, "heard", "doing")
        takes = _song_takes(run)
        if not takes:
            _say(job, "heard", "stopped", "No take from Suno yet. Add one on the Song row.")
            return
        ok = _song_tool(job, "heard", [run, "--from-file", takes[-1]])
        rec = load(str(Path(run) / "song" / "song.json")) if (Path(run) / "song" / "song.json").is_file() else {}
        if rec.get("pass"):
            _say(job, "heard", "done", "Every line heard on %s" % takes[-1].name)
        elif ok or rec:
            _say(job, "heard", "stopped", ((rec.get("problems") or ["the song did not pass"])[0])[:240])
    elif stage == "songcut":
        _say(job, "cut", "doing")
        brief = load(os.path.join(bdir(n), "brief.json"))
        v = SV.view(sb, run)
        times = SV.scene_times(brief.get("order") or [], v)
        laid = {s: dict(t, seconds=round(t["end"] - t["start"], 2)) for s, t in times.items() if t}
        save(os.path.join(bdir(n), "song-cut.json"), {"song": os.path.relpath(str(Path(run) / "song" / "song.mp3"), str(_ws())), "seconds": v["seconds"],
                                                      "scenes": laid, "at": datetime.datetime.now().isoformat(timespec="seconds")})
        said = "%d of %d scenes on the song; the rest keep their own length" % (len(laid), len(times))
        if lane_of(brief)["lane"] != "ai":          # a footage lane plays the song itself: each scene's slice is its read
            try:
                said += "; " + lay_song_reads(n, brief, Path(run) / "song", laid, v["seconds"])
            except (RuntimeError, OSError, ValueError) as e:   # said on the screen; the song cut itself stands
                said += "; the song could not be laid as the scenes' reads: " + str(e)[:160]
        _say(job, "cut", "done", said)


def _lyric_words(ln, offset=0.0):
    """One sung line's words as the LYRIC spells them, on the song's measured times: the captions read the words a
    scene's read lists, and a transcriber's hearing ("do to his" for "through his teeth") must never reach the screen.
    Same count as heard: word for word. Otherwise the lyric's words share the line's heard span in proportion to
    their length."""
    said = [t for t in str(ln.get("line") or "").split() if t]
    heard = ln.get("words") or []
    if not said:
        return []
    line = ln.get("_n")
    if len(heard) == len(said):
        return [{"w": t, "start": round(h["start"] - offset, 3), "end": round(h["end"] - offset, 3), "line": line}
                for t, h in zip(said, heard)]
    a = float(ln["start"] if ln.get("start") is not None else heard[0]["start"]) - offset
    b = float(ln["end"] if ln.get("end") is not None else heard[-1]["end"]) - offset
    total = sum(len(t) + 1 for t in said)
    out, at = [], a
    for t in said:
        d = (b - a) * (len(t) + 1) / total
        out.append({"w": t, "start": round(at, 3), "end": round(at + d, 3), "line": line})
        at += d
    return out


def lay_song_reads(n, brief, song_dir, laid, seconds):
    """A sung ad on a footage lane (real, mix): the song IS each scene's read. Each sung scene gets its slice of the
    song (tiled, scene start to the next scene's start, so the song plays through unbroken) as its `voice.read`, and
    voice/reads.json gets its words (the song's measured line times) and its text (the locked lyric lines), so the
    scene runs as long as its slice, its shots split that time by weight, and its captions spell the lyrics. Written
    by the song cut itself, so a re-seeded production never runs without it (20 Nov 2026: a re-seed lost reads.json
    and every scene run failed). -> what was laid, in words."""
    B = Path(bdir(n))
    order = [s for s in brief.get("order") or [] if s in laid]
    if not order:
        return "no sung scene to lay"
    song = song_dir / "song.mp3"
    timing = load(str(song_dir / "timing.json")) if (song_dir / "timing.json").is_file() else {}
    starts = [0.0] + [float(laid[s]["start"]) for s in order[1:]]
    ends = starts[1:] + [float(seconds)]
    (B / "voice" / "song").mkdir(parents=True, exist_ok=True)
    rp = B / "voice" / "reads.json"
    reads = load(str(rp)) if rp.is_file() else {}
    reads.setdefault("voice", "the ad's song")
    reads.setdefault("lines", {})
    for s, a, b in zip(order, starts, ends):
        rel = "voice/song/%s.mp3" % s
        ff(["-ss", "%.3f" % a, "-to", "%.3f" % b, "-i", str(song), "-c:a", "libmp3lame", "-b:a", "192k", str(B / rel)])
        mine = [ln for ln in timing.get("lines") or [] if ln.get("start") is not None and a - 0.05 <= float(ln["start"]) < b]
        reads["lines"][s] = {"text": " ".join(ln["line"] for ln in mine),
                             "words": [w for k, ln in enumerate(mine) for w in _lyric_words(dict(ln, _n=k), a)]}
        tf = _pick_take(n, s, brief)
        wf = load(tf)
        steps = [st for st in wf.get("steps") or [] if st.get("tool") not in ("voice.read", "voice.ai")]
        steps.insert(0, {"id": "voice", "tool": "voice.read", "model": "the ad's song", "prompt": None, "seed": None,
                         "inputs": {"file": rel}, "params": {"speaker": "SINGER", "tail": 0},
                         "note": "this scene's slice of the song, at its place on the song (song-cut.json)"})
        save(tf, dict(wf, steps=steps))
    save(str(rp), reads)
    bf = B / "brief.json"                 # a footage ad told by its song: every clip must show what is sung (frame_look)
    bj = load(str(bf))
    if not (bj.get("shot_fill") or {}).get("shows_required"):
        bj.setdefault("shot_fill", {})["shows_required"] = True
        save(str(bf), bj)
    return "%d scenes read their slice of the song" % len(order)


def _cuts(B):
    return sorted(B.glob("rough-cut-v*-sdr.mp4"), key=lambda f: int(re.search(r"-v(\d+)-", f.name).group(1)))


def _pick_take(n, s, brief=None):
    brief = brief or load(os.path.join(bdir(n), "brief.json"))
    return os.path.join(sdir(n, s), brief["picks"][s] + ".json")


def next_due(n):
    """The stage production is at: the first one whose output is missing or older than what it is made from."""
    sung = song_due(n)                  # a sung ad: the song is made, heard and laid out before anything else
    if sung:
        return sung
    B = Path(bdir(n))
    brief = load(B / "brief.json")
    sl, pk = B / "shot-list.json", B / "picks.json"
    rows = load(sl)["shots"] if sl.exists() else None
    picks = load(pk).get("shots", {}) if pk.exists() else {}
    fill = B / "shot-fill.json"
    if rows is None or not fill.exists():
        return "shots"
    # in the AI lane every shot is made with AI and never gets a pick, so "no pick" must not send production back to
    # this step for ever (16 Nov); every other lane is unchanged
    # a production whose footage the chain decided (shot-fill "decided_by") has every shot decided: placed, or made /
    # found by its maker. Older productions keep the rule that every shot needs a pick
    chained = bool(load(fill).get("decided_by"))
    lane = lane_of(brief)["lane"]        # the chain's call (lane.py), the one lane source
    if lane != "ai" and not chained and any(r["id"] not in picks and not r.get("source") for r in rows):
        return "shots"
    takes = [load(_pick_take(n, s, brief)) for s in brief["order"]]
    # a hook version made from the opening's own shots (reply_card.py) is cut with the scenes, before the render
    for h in brief.get("hooks") or []:
        hf = B / "scenes" / h / (brief.get("picks", {}).get(h, "take-1") + ".json")
        ho = B / "scenes" / h / "out" / brief.get("picks", {}).get(h, "take-1") / (h + ".mp4")
        hw = load(hf) if hf.exists() else {}
        if hw.get("replaces") and not ho.exists() and all(st["tool"] in RUNNABLE for st in hw.get("steps") or []):
            return "cut"
    if any(st["tool"] == "voice.ai" for wf in takes for st in wf.get("steps") or []):
        return "voice"
    outs = [B / "scenes" / s / "out" / brief["picks"][s] / (s + ".mp4") for s in brief["order"]]
    # a scene whose take still waits on a print (an AI shot, a voice read, a capture) is made by its maker from the
    # hand-off folder, never cut here: cutting it is what failed (16 Nov, an AI-lane ad's "Cut to the swipe")
    ai = lane == "ai" or (chained and lane != "real")   # Real: every shot has its clip, so every scene is cut here (20 Nov)
    ready = [(s, o) for s, o, wf in zip(brief["order"], outs, takes)
             if not ai or all(st["tool"] in RUNNABLE for st in wf.get("steps") or [])]
    if any(not o.exists() or o.stat().st_mtime < max(pk.stat().st_mtime if pk.exists() else 0,
                                                       sl.stat().st_mtime if sl.exists() else 0,   # re-timed shots (a song)
                                                       os.path.getmtime(_pick_take(n, s, brief)), _card_t(B, s))
           for s, o in ready):
        return "cut"                     # a scene not made, or made before its own take or the picks changed
    if len(ready) < len(outs) and ai and not any(not o.exists() for s, o in ready):
        if lane == "ai" and AS.scenes_due(B, brief):    # AI shots still to make: made on the chain before any hand-off
            return "aishots"
        return "maker" if _maker_due(n, B, brief) else None   # the rest waits on its prints: handed off by itself
    chk = B / "SWIPE-CHECK.json"
    if not chk.exists() or chk.stat().st_mtime < max(o.stat().st_mtime for o in outs):
        return "check"
    cuts = _cuts(B)
    if not cuts or cuts[-1].stat().st_mtime < max(o.stat().st_mtime for o in outs):
        return "render"
    bed = B / "music" / "bed.json"                      # the bed (its effects) changed since the last render: render again
    if ES.on() and bed.exists() and bed.stat().st_mtime > cuts[-1].stat().st_mtime:
        return "render"
    for vid, _, _ in _version_ids(brief):  # each hook and each footage variation (and its hooks) is its own version
        v = B / "versions" / vid / ("%s-%s.mp4" % (n, vid))
        if not v.exists() or v.stat().st_mtime < cuts[-1].stat().st_mtime:
            return "render"
    if _edit_due(n, B):                 # every version rendered: the swipe's edit moves come before the covers
        return "edit"
    if CS.on() and _covers_due(n, B):   # every version rendered: its cover is next (covers_stage.py)
        return "covers"
    return None


def _run_json(brief):
    try:
        return load(os.path.join(ST.WRITING, brief["brief"], "run.json"))
    except (OSError, ValueError, KeyError):
        return {}


def _maker_due(n, B, brief):
    """The hand-off is due when there is none yet, the brief got its number since, or a take changed after packing."""
    rec = B / "maker-pack.json"
    if not rec.exists():
        return True
    r = load(rec)
    if (r.get("number") or None) != (_run_json(brief).get("brief") or None):
        return True
    t = rec.stat().st_mtime
    return any(os.path.getmtime(_pick_take(n, s, brief)) > t for s in brief.get("order") or [])


def _card_t(B, s):
    """When the scene's card layer (scenes/<s>/card, the layers template) last changed: a newer card makes the scene again."""
    f = Path(B) / "scenes" / s / "card" / "index.template.html"
    return f.stat().st_mtime if f.exists() else 0


def _edit_due(n, B):
    """The edit stage is due (edit_stage.due); nothing it reads can stop the Studio."""
    try:
        return ES.due(n, B)
    except (Exception, SystemExit):  # noqa: BLE001
        return False


def _covers_due(n, B):
    """The cover stage is due (covers_stage.due): never for a production whose card is approved, live or already
    covered, and nothing the stage reads can stop the Studio."""
    try:
        return CS.due(n, B, versions(n))
    except (Exception, SystemExit):  # noqa: BLE001
        return False


def _version_ids(brief):
    """Every version past the control: each hook, each footage variation (brief.json "variants") and its hooks."""
    hooks = brief.get("hooks") or []
    out = [(h, None, h) for h in hooks]
    for v in brief.get("variants") or {}:
        out += [(v, v, None)] + [("%s-%s" % (v, h), v, h) for h in hooks]
    return out


def _next_job(n):
    """The production's Next step job as its process last wrote it, while that process is alive."""
    f = Path(bdir(n)) / "next-job.json"
    try:
        j = load(str(f))
    except (OSError, ValueError):
        return None
    if not j.get("done"):
        try:
            os.kill(int(j.get("pid") or 0), 0)
        except (OSError, ValueError):
            for st in j["steps"]:
                if st["state"] in ("doing", "waiting"):
                    st["state"], st["said"] = "stopped", "The step's process ended before it finished. Press the button again."
            j["done"] = True
            save(str(f), j)
    return j


def job_by_id(jid):
    if jid in HANDOFF:
        return HANDOFF[jid]
    for f in glob.glob(os.path.join(BRIEFS, "*", "next-job.json")):
        try:
            if load(f).get("id") == jid:
                return _next_job(os.path.basename(os.path.dirname(f)))
        except (OSError, ValueError):
            continue
    return None


def next_state(n):
    j = _next_job(n)
    run = j if j and not j.get("done") else None
    due = None if run else next_due(n)
    label = NEXT_STAGES[due][0] if due else ("" if run else "Open Versions")
    if due == "shots" and lane_of(load(os.path.join(bdir(n), "brief.json")))["lane"] == "ai":
        label = "Plan the AI shots"   # all AI: no footage search (owner, 20 Nov)
    w = None if due or run else _waits_on_maker(n)
    if w:
        label = w                                       # the Studio cannot make these: who does, in plain words
    return {"due": due, "running": run["name"] if run else None, "label": label}


def _waits_on_maker(n):
    """What the picked takes still wait on that the Studio cannot make, in plain words, or None: AI shots go to the
    maker's folder; a Real shot with no clip of ours is found or filmed."""
    try:
        brief = load(os.path.join(bdir(n), "brief.json"))
        tools = {st["tool"] for s in brief["order"] for st in load(_pick_take(n, s, brief)).get("steps") or []} - RUNNABLE
    except (OSError, ValueError, KeyError):
        return None
    if "footage.find" in tools:
        return "Shots to find or film (no clip of ours yet)"
    if "gen.shot" in tools or "gen.take" in tools:
        return "AI shots go to the maker's folder"
    return None


def _tool(job, sid, args, timeout=3600):
    """One of the Studio's own tools, run as it is run by hand; its last lines are what the step says."""
    r = subprocess.run([sys.executable, os.path.join(HERE, args[0])] + args[1:], capture_output=True, text=True,
                       cwd=HERE, env=os.environ, timeout=timeout)
    tail = [ln for ln in (r.stdout + "\n" + r.stderr).splitlines() if ln.strip()]
    if r.returncode:
        _say(job, sid, "stopped", (tail[-1] if tail else "the tool stopped")[:240])
    return r.returncode == 0, r.stdout


def draft_picks(n):
    """Every shot with no pick gets the best owned clip shot_fill found for it (a local file only). A pick already in
    picks.json is never changed: the person's picks are the creative choice. Returns (placed, gaps)."""
    B = Path(bdir(n))
    fill = load(B / "shot-fill.json")
    pk = B / "picks.json"
    picks = load(pk) if pk.exists() else {"note": "Picks drafted by the Studio's Next step from shot-fill.json; change any.",
                                          "shots": {}, "sources": {}}
    picks.setdefault("shots", {}), picks.setdefault("sources", {})
    # THE LANE PICKED AT PRODUCE (owner, 16 Nov): ai = every shot made, our clips stay references only; mix = a clip is
    # placed only where it truly shows the shot (never a POV stand-in); real = our closest clip on every shot
    lane = lane_of(load(B / "brief.json"))["lane"]
    if lane == "ai":                     # a drafted pick from before the lane was set gives way; the person's own stay
        picks["shots"] = {k: v for k, v in picks["shots"].items() if not v.get("drafted")}
    placed, gaps = 0, []
    for r in fill["shots"]:
        if r.get("from") != "production shot list" or r["id"] in picks["shots"]:
            continue
        stand_in = "(POV stand-in)" in (r.get("shows") or "")
        if r["status"] != "REAL" or not r.get("file") or lane == "ai" or (lane == "mix" and stand_in):
            gaps.append(r["id"])
            continue
        key = "L-" + hashlib.md5(r["file"].encode()).hexdigest()[:8]
        picks["sources"][key] = r["file"]
        picks["shots"][r["id"]] = {"source": key, "in": r["in"], "note": "%s (library %.2f)" % (r["shows"][:90], r["score"]),
                                   "drafted": True}
        placed += 1
    save(str(pk), picks)
    return placed, gaps


def seed_reads(n):
    """voice/reads.json for a production that has none: every scene's narrator lines from its picked take, read in the
    ad's narrator (brief.json "narrator": {"voice_id", "voice"}), else the voice the brand's latest narrated ad used."""
    B = Path(bdir(n))
    brief = load(B / "brief.json")
    voice = brief.get("narrator")
    if not voice:                        # the speaker's own banked voice, from the casting bank (owner, 2026-11-20)
        try:
            import chain_view as CV
            voice = CV.speaker_voice(brief)
        except Exception:  # noqa: BLE001 -- no chain brief: the rules below
            voice = None
    if not voice:                        # the voice set for the people on screen (voices.py, rule 2026-11-12)
        import voices as VO
        face = VO.face_of(brief)
        if face:
            v = VO.voice_for(VO.brand_of(brief), face)
            voice = {"voice_id": v["voice_id"], "voice": v.get("name", "")}
    if not voice:
        brand = str(brief.get("brief") or "").split("-")[0]
        mine = []
        for f in Path(ST.BRIEFS).glob("*/voice/reads.json"):
            try:
                if str(load(f.parents[1] / "brief.json").get("brief") or "").startswith(brand + "-"):
                    mine.append(f)
            except (OSError, ValueError):
                continue
        if not mine:
            return False
        r = load(max(mine, key=lambda f: f.stat().st_mtime))
        voice = {"voice_id": r["voice_id"], "voice": r.get("voice", "")}
    lines = {}
    for s in brief["order"]:
        said = [st.get("prompt") or "" for st in load(_pick_take(n, s, brief)).get("steps") or [] if st["tool"] == "voice.ai"]
        if said:
            text = " ".join(x.strip() for x in said if x.strip())
            lines[s] = {"text": text, "sent": text}
    os.makedirs(B / "voice", exist_ok=True)
    save(str(B / "voice" / "reads.json"), {"voice_id": voice["voice_id"], "voice": voice.get("voice", ""), "model": "eleven_v3",
                                          "note": "Seeded by the Studio's Next step from the picked takes' narrator lines.",
                                          "lines": lines})
    return True


def _run_next(job):
    n, stage = job["n"], job["stage"]
    if stage in ("song", "songcheck", "songcut"):
        return _run_song(job)
    B = Path(bdir(n))
    if stage == "shots":
        _say(job, "list", "doing")
        # OUR SHOTS (owner, 20 Nov 2026): a Real or AI + Real ad's shots come from our script, one per spoken beat;
        # the swipe stays with the writing as inspiration and is not used in production. The AI lane keeps its list.
        ok, out = _tool(job, "list", ["our_shots.py" if lane_of(load(B / "brief.json"))["lane"] in ("real", "mix")
                                      else "swipe_shots.py", n])
        if not ok:
            return
        rows = load(B / "shot-list.json")["shots"]
        _say(job, "list", "done", "%d shots across %d scenes" % (len(rows), len({r["scene"] for r in rows})))
        _say(job, "fill", "doing")
        brief = load(B / "brief.json")
        # All AI (owner, 20 Nov): an AI-lane ad is made entirely with AI and its cast. No footage search, no clip picks,
        # nothing placed from the library: every shot is recorded as made with AI and production moves on.
        if lane_of(brief)["lane"] == "ai":
            (B / "shot-fill.json").write_text(json.dumps({"decided_by": "ai lane: every shot made with AI", "shots": [
                {"id": r["id"], "scene": r.get("scene"), "status": "AI", "from": "production shot list"} for r in rows]},
                indent=1) + "\n")
            for sid, said in (("fill", "All AI: no footage search"), ("picks", "%d shots, every one made with AI" % len(rows)),
                              ("said", "All AI: nothing placed from our footage")):
                _say(job, sid, "done", said)
            return
        if not (brief.get("shot_fill") or {}).get("brand"):
            _say(job, "fill", "stopped", "This ad has no library settings yet (which brand, whose hands). Ask Claude to set them.")
            return
        ok, out = _tool(job, "fill", ["shot_fill.py", n])
        if not ok:
            return
        fill = load(B / "shot-fill.json")
        mine = [r for r in fill["shots"] if r.get("from") == "production shot list"]
        _say(job, "fill", "done", "%d of %d found in our footage" % (sum(r["status"] == "REAL" for r in mine), len(mine)))
        _say(job, "picks", "doing")
        if brief.get("real_cast") and lane_of(brief)["lane"] in ("real", "mix"):
            # CAST FIRST (owner, 20 Nov 2026): a Real-lane production with a cast fills its shots by person, each role
            # from that person's own clips (cast_picks.py); the search's drafts only fill what the cast leaves open
            _tool(job, "picks", ["cast_picks.py", n])
        placed, gaps = draft_picks(n)
        lane = lane_of(brief)["lane"]
        if gaps and lane in ("ai", "mix"):     # the lane says these are made: no stop, no hand step
            _say(job, "picks", "done", ("%d placed from our footage, %d made with AI (the %s lane); our closest clips go with them as references"
                                        % (placed, len(gaps), "AI + Real" if lane == "mix" else "AI")))
        elif gaps:
            _say(job, "picks", "stopped", "%d placed. %s not matched by the search: picked by eye from our footage next (SHOT-FILL lists the nearest clips). AI only with your yes." % (placed, ", ".join(gaps)))
        else:
            _say(job, "picks", "done", "%d placed, every shot has a clip" % placed)
        # rule (owner, 10 Nov): everything the narration names gets its shot from the index when we own footage of it
        _say(job, "said", "doing")
        ok, out = _tool(job, "said", ["said_shots.py", n, "--place"])   # placed on its words, no hand step
        if ok:
            _say(job, "said", "done", ((out.strip().splitlines() or [""])[-1] + " (SAID-SHOTS lists the clips)")[:240])
    elif stage == "aishots":
        AS.run(n, B, say=lambda sid, state, said="": _say(job, sid, state, said))
    elif stage == "maker":
        brief = load(B / "brief.json")
        left = AS.scenes_due(B, brief) if lane_of(brief)["lane"] == "ai" else []
        if left:                         # the AI lane is handed off only once every AI shot is made (owner, 20 Nov)
            _say(job, "number", "stopped", "AI shots not made yet (%s): Make the AI shots comes first" % ", ".join(left))
            return
        _say(job, "number", "doing")
        num = _run_json(brief).get("brief")
        if not num:                      # the writing filer gives an accepted brief its register number (its own door)
            try:
                import importlib.util as _iu
                _sp = _iu.spec_from_file_location("studio_file_run", str(_ws() / "components" / "video-teardown" / "machine" / "file_run.py"))
                FR = _iu.module_from_spec(_sp)
                _sp.loader.exec_module(FR)
                rd = Path(ST.WRITING) / brief["brief"]
                dest = FR.file_run(rd)[0]
                FR.number_brief(rd, dest)
            except Exception as e:  # noqa: BLE001 — said on the screen; the pack still goes out under the production name
                _say(job, "number", "doing", "The filer could not number it: " + str(e)[:160])
            num = _run_json(brief).get("brief")
        _say(job, "number", "done" if num else "stopped",
             num or "No number yet: the brief's writing checks have not accepted it; packed under the production name for now")
        _say(job, "pack", "doing")
        import maker_pack as MP
        try:
            rec = MP.build(n)
        except Exception as e:  # noqa: BLE001 — said on the screen
            _say(job, "pack", "stopped", "The hand-off could not be packed: " + str(e)[:200])
            return
        old = load(B / "maker-pack.json") if (B / "maker-pack.json").exists() else {}
        if old.get("key") and old["key"] != rec["key"]:   # renamed by its brief number: the old folder is moved aside, never deleted
            for f in (old.get("folder"), old.get("drive")):
                if f and os.path.isdir(f):
                    side = os.path.join(os.path.dirname(f), "_superseded")
                    os.makedirs(side, exist_ok=True)
                    if not os.path.exists(os.path.join(side, os.path.basename(f))):
                        os.rename(f, os.path.join(side, os.path.basename(f)))
        save(str(B / "maker-pack.json"), dict(rec, number=num))
        _say(job, "pack", "done", "%s · %d clips to make · %d scenes made" % (rec["key"], rec["clips"], rec["made"]))
        _say(job, "queue", "doing")
        try:
            sys.path.insert(0, str(_ws() / "components" / "image-edit"))
            import handoff_index as HI
            HI.quiet_refresh(drive=True)
        except Exception:  # noqa: BLE001 — the queue reads the folder itself; the index is the front door
            pass
        _say(job, "queue", "done", "Ready for the editor on the queue" + ("" if rec.get("drive") else " (Drive copy pending)"))
    elif stage == "voice":
        _say(job, "read", "doing")
        if not (B / "voice" / "reads.json").exists() and not seed_reads(n):
            _say(job, "read", "stopped", "No narrator voice for this brand yet. Pick one, then press Next step again.")
            return
        ok, out = _tool(job, "read", ["voice_continuous.py", n])
        if not ok:
            return
        body = load(B / "voice" / "continuous" / "body.json")
        _say(job, "read", "done", "%.0f%% of the script heard back" % (100 * body["match"]))
        _say(job, "place", "doing")
        brief, reads = load(B / "brief.json"), load(B / "voice" / "reads.json")
        for s in brief["order"]:
            p = _pick_take(n, s, brief)
            wf = load(p)
            steps = []
            for st in wf["steps"]:
                if st["tool"] == "voice.ai" and s in body["scenes"]:
                    if any(x["tool"] == "voice.read" for x in steps):
                        continue
                    st = {"id": "voice", "tool": "voice.read", "model": body["model"], "prompt": reads["lines"][s]["text"],
                          "seed": body["seed"], "inputs": {"file": "voice/continuous/%s.mp3" % s},
                          "params": {"voice_id": body["voice_id"], "voice": reads.get("voice", ""),
                                     "speaker": st["params"].get("speaker", "NARRATOR"), "tail": 0},
                          "note": "one continuous narration read, cut at this scene's first word (voice/continuous/body.json)"}
                steps.append(st)
            save(p, dict(wf, steps=steps))
        _say(job, "place", "done", "%d scenes" % len(body["scenes"]))
    elif stage == "cut":
        _say(job, "cut", "doing")
        ok, out = _tool(job, "cut", ["swipe_cut.py", n, "--run"])
        if ok:
            made = sum(1 for ln in out.splitlines() if " run: ok " in ln)
            # every other scene whose take is ready (set up from our footage by the chain at Produce) is run as it is:
            # cut-to-the-swipe re-times only the scenes the picks name, and the rest must not wait for ever
            brief = load(B / "brief.json")
            for s in list(brief["order"]) + [h for h in brief.get("hooks") or [] if h in brief.get("picks", {})]:
                o = B / "scenes" / s / "out" / brief["picks"][s] / (s + ".mp4")
                wf = load(_pick_take(n, s, brief))
                pk = B / "picks.json"
                fresh = o.exists() and o.stat().st_mtime >= max(pk.stat().st_mtime if pk.exists() else 0,
                                                                 os.path.getmtime(_pick_take(n, s, brief)), _card_t(B, s))
                if fresh or not wf.get("steps") or any(st["tool"] not in RUNNABLE for st in wf["steps"]):
                    continue
                try:
                    run_scene(n, s)
                    made += 1
                except Exception as e:  # noqa: BLE001 - a scene that cannot be cut says so; the others still run
                    _say(job, "cut", "doing", "%s could not be cut: %s" % (s, str(e)[:120]))
            _say(job, "cut", "done", "%d scenes cut" % made)
    elif stage == "render":
        import studio_render as SR   # the render is Video Edit's (machine/studio/studio_render.py), 2026-11-21
        if not SR.render(n, B, lambda sid, state, said="": _say(job, sid, state, said)):
            return
        job["open"] = {"stage": "versions", "n": n}
        if next_due(n) == "edit":                            # no press: the edit pass follows the versions straight on
            _run_edit(job)
        if CS.after_render() and next_due(n) == "covers":   # no press: the covers follow the versions straight on
            _run_covers(job)
    elif stage == "edit":
        _run_edit(job)
        if CS.after_render() and next_due(n) == "covers":
            _run_covers(job)
    elif stage == "covers":
        _run_covers(job)
    elif stage == "check":
        _say(job, "check", "doing")
        r = subprocess.run([sys.executable, os.path.join(HERE, "swipe_check.py"), n], capture_output=True, text=True,
                           cwd=HERE, env=os.environ, timeout=3600)
        res = [ln for ln in r.stdout.splitlines() if ln[:1] in ("✓", "✗")]
        bad = [ln for ln in res if ln.startswith("✗")]
        _say(job, "check", "stopped" if bad or not res else "done",
             ("; ".join(bad)[:240] if bad else "%d of %d checks pass" % (len(res), len(res))) if res else (r.stderr.strip()[-240:] or "the check stopped"))


def _run_edit(job):
    """The edit stage (edit_stage.py) inside a Next step job: its steps join the job's, then it runs."""
    n = job["n"]
    if not any(st["id"] == ES.STEPS[0][0] for st in job["steps"]):
        job["steps"] += [{"id": i, "name": nm, "state": "waiting", "said": ""} for i, nm in ES.STEPS]
        if job.get("file"):
            save(job["file"], job)
    try:
        ES.run(n, B=Path(bdir(n)), say=lambda sid, state, said="": _say(job, sid, state, said))
    except SystemExit as e:              # a neighbour that exits is a stopped step, never the end of the job
        st = next((x for x in job["steps"] if x["state"] in ("doing", "waiting")), None)
        if st:
            st["state"], st["said"] = "stopped", "Something stopped here: " + (str(e) or "an exit")[:200]


def _run_covers(job):
    """The cover stage (covers_stage.py) inside a Next step job: its steps join the job's, then it runs."""
    n = job["n"]
    if not any(st["id"] == CS.STEPS[0][0] for st in job["steps"]):
        job["steps"] += [{"id": i, "name": nm, "state": "waiting", "said": ""} for i, nm in CS.STEPS]
        job["name"] = job.get("name", "") + " · then the covers" if job.get("stage") != "covers" else job.get("name")
        if job.get("file"):
            save(job["file"], job)
    try:
        CS.run(n, B=Path(bdir(n)), say=lambda sid, state, said="": _say(job, sid, state, said), vers=versions(n))
    except SystemExit as e:              # a neighbour that exits is a stopped step, never the end of the job
        st = next((x for x in job["steps"] if x["state"] in ("doing", "waiting")), None)
        if st:
            st["state"], st["said"] = "stopped", "Something stopped here: " + (str(e) or "an exit")[:200]
    job["open"] = {"stage": "covers", "n": n}


# ONE GO (owner, 2026-11-20: "zero hand steps, only his go and his review"): with `through`, the job runs every due
# stage of the production line in turn and stops at the first step that stops, or when the next due stage is not one
# of these (covers, versions, the hand-off and approval stay a person's press)
THROUGH = ("aishots", "cut", "check", "render", "edit")


def next_start(n, stage=None, through=False):
    """Starts the due stage (or the one named: `covers` remakes the covers now) in its own process (a Studio restart
    never kills a render half way); the loading screen reads its state from briefs/<n>/next-job.json. `through` runs
    every due stage of THROUGH in turn (one go)."""
    j = _next_job(n)
    if j and not j.get("done"):
        return {"job": j["id"]}
    stage = stage if stage in NEXT_STAGES else next_due(n)
    if not stage:
        return {"job": None, "edit": True}
    name, steps = NEXT_STAGES[stage]
    jid = "%s-%s-%d" % (n, stage, int(datetime.datetime.now().timestamp()))
    f = os.path.join(bdir(n), "next-job.json")
    job = {"id": jid, "idea": None, "n": n, "stage": stage, "name": name, "done": False, "file": f,
           "open": {"stage": "production", "n": n}, "steps": [{"id": i, "name": nm, "state": "waiting", "said": ""} for i, nm in steps]}
    if through:
        job["through"] = True
    save(f, job)
    env = dict(os.environ)
    env.setdefault("VISION_JUDGE_ORDER", "claude,local")   # the judge's Google fallback can hang on a network; never wait on it
    p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "next", n], cwd=HERE, env=env, start_new_session=True,
                         stdout=open(os.path.join(bdir(n), "next-job.log"), "a"), stderr=subprocess.STDOUT)
    return {"job": jid, "pid": p.pid}     # the job writes its own pid and steps; writing here could undo a step


def run_next_job(n):
    """The detached side of next_start: runs the job briefs/<n>/next-job.json names, writing each step as it goes."""
    f = os.path.join(bdir(n), "next-job.json")
    job = load(f)
    job["pid"] = os.getpid()
    save(f, job)
    import socket as _so
    _so.setdefaulttimeout(600)      # no network call may hang a production job (owner, 20 Nov: never stuck for no reason)

    def safe(job):
        try:
            _run_next(job)
        except Exception as e:  # noqa: BLE001 — a step that breaks says so on the screen
            st = next((x for x in job["steps"] if x["state"] in ("doing", "waiting")), None)
            if st:
                st["state"], st["said"] = "stopped", "Something broke here: " + str(e)[:200]
        for st in job["steps"]:
            if st["state"] == "waiting":
                st["state"] = "later"
        job["done"] = True
        save(f, job)
    safe(job)
    ran = [job["stage"]]
    while job.get("through") and not any(st["state"] == "stopped" for st in job["steps"]):
        stage = next_due(n)
        if stage not in THROUGH or stage in ran[-1:]:     # never the same stage twice in a row (nothing moved)
            break
        name, steps = NEXT_STAGES[stage]
        job = {"id": "%s-%s-%d" % (n, stage, int(datetime.datetime.now().timestamp())), "idea": None, "n": n,
               "stage": stage, "name": name, "done": False, "file": f, "through": True, "pid": os.getpid(),
               "open": {"stage": "production", "n": n}, "after": ran[:],
               "steps": [{"id": i, "name": nm, "state": "waiting", "said": ""} for i, nm in steps]}
        save(f, job)
        safe(job)
        ran.append(stage)


def wf_hash(wf):
    if wf.get("_hash_as"):
        return wf["_hash_as"]
    keep = {k: wf[k] for k in ("steps", "clock", "sources") if k in wf}
    return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:12]


_REACH = []


def _drive_reach():
    """gdrive-creator's reach (the team's one Drive door), loaded once; None where it is not installed."""
    if not _REACH:
        try:
            root = str(ST.part("gdrive-creator"))
            if root not in sys.path:
                sys.path.insert(0, root)
            from gdrive_creator import reach
            _REACH.append(reach)
        except Exception:  # noqa: BLE001 - no Drive door here: the synced folders below still serve
            _REACH.append(None)
    return _REACH[0]


def _shared_assets(loc):
    """A clip on Shared Assets straight from the Drive by the key (owner, 16 Nov 2026: "this needs to hook straight
    into the shared assets"): reach.readable reads by id with GDRIVE_SA_KEY and never trusts the synced copy, which
    can be a placeholder or a broken partial file. None when the path is not on Shared Assets or the door is shut."""
    s = str(loc)
    if "Shared Assets/" not in s:
        return None
    R = _drive_reach()
    if R is None:
        return None
    label = "Shared Assets/" + s.split("Shared Assets/", 1)[1]
    try:                             # a whole copy already here is used as it is: never pulled again (17 Nov)
        have = R.cache_root().joinpath(*label.split("/")[1:])
        if have.is_file() and have.stat().st_size > 0:
            return str(have)
    except Exception:  # noqa: BLE001
        pass
    try:
        return str(R.readable(label))
    except (Exception, SystemExit):  # noqa: BLE001 - not reachable by key: the synced folders below are tried
        return None


def _other_root(loc, brand, clip_id=None):
    """(url, header) for a clip under another footage root the brand lists (asset-index sources.py, read from
    brands/<brand>/footage-library.json), read by range through that root's reader; None when none applies."""
    if not brand or not loc:
        return None
    try:
        mod = sys.modules.get("asset_index_sources")
        if mod is None or not callable(getattr(mod, "ranged", None)):
            # a half-loaded or foreign module under this name is never trusted: load the reader from its own file,
            # and register it only once it has loaded (a long-running Studio must not keep a broken copy)
            import importlib.util as ilu
            sp = ilu.spec_from_file_location("asset_index_sources", str(ST.part("asset-index")) + "/machine/sources.py")
            mod = ilu.module_from_spec(sp)
            sp.loader.exec_module(mod)
            sys.modules["asset_index_sources"] = mod
        return mod.ranged(brand, loc, clip_id)
    except Exception as e:  # noqa: BLE001 - not readable by range here: the resolver below is tried, and the log says why
        print("other footage root not readable (%s): %s: %s" % (loc[-80:], type(e).__name__, str(e)[:200]),
              file=sys.stderr, flush=True)
        return None


def ranged(entry, brand=""):
    """(url, header) to read only the seconds a shot uses of one of our Shared Assets videos, by range with the key
    (gdrive-creator engine.media_request), when this Mac has no whole copy of it yet; None otherwise (owner, 17 Nov:
    no whole-clip downloads to cut 2 seconds)."""
    loc = str((entry or {}).get("drive_location") or "")
    if os.path.isabs(loc) and os.path.exists(loc):
        return None                      # synced on this Mac: read from disk, never by range through the Drive API (20 Nov)
    if "Shared Assets/" in loc:
        import glob as _g
        tail = "Shared Assets/" + loc.split("Shared Assets/", 1)[1]
        if any(os.path.exists(os.path.join(r, tail)) for r in _g.glob(os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/Shared drives"))):
            return None                  # the same clip synced in a Google Drive folder on this Mac
    if "Shared Assets/" not in loc:
        return _other_root(loc, brand, (entry or {}).get("clip_id"))
    if not loc.lower().endswith((".mov", ".mp4", ".m4v")):
        return None
    label = "Shared Assets/" + loc.split("Shared Assets/", 1)[1]
    R = _drive_reach()
    if R is None:
        return None
    try:
        full = R.cache_root().joinpath(*label.split("/")[1:])
        if full.is_file() and full.stat().st_size > 0:
            return None
        fid = (entry or {}).get("clip_id")
        if not fid and brand:
            import swipe_cut as SWC
            if hasattr(SWC, "_cuts_of"):          # the library's clip ids, where this swipe_cut reads them
                SWC._cuts_of(brand, label)
                fid = (SWC._CUTS.get(brand) or ({}, {}))[1].get(label)
        fid = fid or R.drive_id(label)
        if not fid:
            return None
        from gdrive_creator import engine as E
        return E.media_request(fid)
    except (Exception, SystemExit):  # noqa: BLE001 - not readable by range here: the whole clip, as before
        return None


def resolve(src):
    loc = src["drive_location"]
    if "Shared Assets/" in loc:                             # the synced original first: the cache can hold a half copy
        import glob as _g
        tail = "Shared Assets/" + loc.split("Shared Assets/", 1)[1]
        for r in _g.glob(os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/Shared drives")):
            if os.path.isfile(os.path.join(r, tail)) and os.path.getsize(os.path.join(r, tail)) > 0:
                return os.path.join(r, tail)
    got = _shared_assets(loc)
    if got and os.path.exists(got):                         # a library clip, straight from Shared Assets by key
        return got
    if os.path.isabs(loc) and os.path.exists(loc):          # a library clip, by its synced Drive path
        return loc
    if "Shared Assets/" in loc:                             # the same clip synced in a Google Drive folder on this Mac
        import glob as _g
        tail = "Shared Assets/" + loc.split("Shared Assets/", 1)[1]
        for r in _g.glob(os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/Shared drives")):
            if os.path.exists(os.path.join(r, tail)):
                return os.path.join(r, tail)
    if os.path.exists(os.path.join(SOURCES, loc)):  # a generated shot, kept beside the pulled sources
        return os.path.join(SOURCES, loc)
    rel = loc[len("Shared Assets/"):] if loc.startswith("Shared Assets/") else loc
    for root in DRIVE_ROOTS:
        p = os.path.join(root, rel)
        if os.path.exists(p):
            return p
    p = os.path.join(SOURCES, os.path.basename(loc))   # pulled from Drive by its link when no synced folder has it
    if os.path.exists(p):
        return p
    raise FileNotFoundError("source not found (set VIDEO_STUDIO_DRIVE or pull it by link): " + loc)


import scene_cut as SCUT  # noqa: E402  (the scene cut, its captions and the sound helpers: Video Edit's, 2026-11-21)
read_words, _read_words, ff, loudness, exact_level, probe_dur = (SCUT.read_words, SCUT._read_words, SCUT.ff, SCUT.loudness,
                                                                 SCUT.exact_level, SCUT.probe_dur)
SPELL, spelled, _caption_chunks = SCUT.SPELL, SCUT.spelled, SCUT._caption_chunks


def style_chain():
    """video-production styles/style_chain.py (the ad's style and its variants), or None where it is not installed."""
    import importlib.util
    f = ST.part("video-production") / "styles" / "style_chain.py"
    if not f.is_file():
        return None
    spec = importlib.util.spec_from_file_location("vs_style_chain", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def stale_elements(n, p):
    """Old elements can't make it into a take (owner, 10 Nov 2026: "when we update elements, we always check for old
    stuff so it can't make it through"). Every cast member names its casting element (`element`: the folder under
    runs/ai-elements/<brand>/casting/, `element_file`: which of its files, default sheets/look-1-beach.jpg) and their
    `sheet` must be that file as it is now; the start picture names the casting files it was made from (`picture_from`:
    [{element, file, sha256}]) and every one must still be current. Returns the problems, empty when all is current."""
    import hashlib
    sha = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest() if f and os.path.isfile(f) else None
    brief = load(os.path.join(bdir(n), "brief.json"))
    try:
        brand = load(os.path.join(ST.WRITING, brief["brief"], "run.json")).get("brand")
    except Exception:  # noqa: BLE001
        brand = None
    home = os.path.join(str(ST.REPO), "runs", "ai-elements", brand or "", "casting")
    # THE AD'S STYLE (owner ruling, 12 Nov 2026): every cast sheet is the element in the production's style, its
    # variant under styles/<style-id>/ when the master is in another (video-production styles/style_chain.py)
    from pathlib import Path
    SC = style_chain()
    try:
        style = SC.ad_style(n, briefs=ST.BRIEFS, writing=ST.WRITING)["id"] if SC else None
    except SystemExit:
        style = None
    out = []
    for name, c in (p.get("cast") or {}).items():
        if not isinstance(c, dict) or not c.get("sheet"):
            continue
        el = c.get("element")
        if not el:
            out.append(f"{name}: no casting element named; its sheet is not from casting")
            continue
        if SC and brand:
            # the bank that holds this element: the team workspace's or this Studio copy's own (style_chain.bank_roots)
            home = str(SC.element_home(brand, "person", el.partition("/styles/")[0]).parent)
        if SC:
            base_el, _, in_style = el.partition("/styles/")
            want = SC.element_ref(base_el, style, Path(home) / base_el) if os.path.isdir(os.path.join(home, base_el)) else el
            if want != el:
                out.append(f"{name}: {el} is not {base_el} in the ad's style ({style or 'photoreal'}): use {want}"
                           + ("" if os.path.isdir(os.path.join(home, want)) else
                              f" (make it: style_chain.py ensure-one {brand} person {base_el} {style})"))
                continue
        cur = os.path.join(home, el, c.get("element_file") or "sheets/look-1-beach.jpg")
        if not os.path.isfile(cur):
            out.append(f"{name}: casting file {el}/{c.get('element_file') or 'sheets/look-1-beach.jpg'} not found")
        elif sha(c["sheet"]) != sha(cur):
            out.append(f"{name}: the sheet in this take is not {el}'s current casting file (an older version)")
    made_from = p.get("picture_from")
    if p.get("cast") and p.get("picture") and not made_from:      # no picture yet is a step still to do, not an old element
        out.append("start picture: no record of which casting files it was made from")
    for r in made_from or []:
        cur = os.path.join(home, r.get("element", ""), r.get("file", ""))
        if sha(cur) != r.get("sha256"):
            out.append(f"start picture: made from {r.get('element')}/{r.get('file')} as it was before; that element has changed since")
    return out


def _take_steps(n, s, take, wf):
    """A gen.take step is the scene's whole take, set up on the step itself (params = take.py's take sheet: picture,
    cast and voices, speakers, script, motion, seconds, model, backups, camera, look; plus `upscale`, a Real-ESRGAN model
    run by the team's local-studio after the print). The print is made once (kept as out/<take>/print.mp4 and reused while
    the step is unchanged), upscaled if asked, then cut as a plain clip with its own sound (owner, 10 Nov 2026: "we need
    to put in this tool the actual video generation set up")."""
    import hashlib
    import subprocess
    import take as T
    out = os.path.join(sdir(n, s), "out", take)
    os.makedirs(out, exist_ok=True)
    wf = json.loads(json.dumps(wf))
    steps = []
    for st in wf["steps"]:
        if st["tool"] != "gen.take":
            steps.append(st)
            continue
        p = dict(st.get("params") or {})
        up = p.pop("upscale", None)
        key = hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:12]
        made = os.path.join(out, "print-%s.mp4" % key)
        sheet = os.path.join(sdir(n, s), "take.json")
        if os.path.exists(sheet):
            # the scene chain (16 Nov 2026): a scene with its take sheet is made by take.py scene, in order: our
            # direction, the rehearsal, the start picture from the set print, the input review, the take, its checks;
            # a hold stops it before anything is paid for, with the reason
            made = load(sheet).get("out") or os.path.join(sdir(n, s), "take.mp4")
            if not os.path.exists(made):
                try:
                    import take_sheet as TS     # the writing's dials onto the sheet first, so the direction carries them
                    TS.carry(bdir(n), s)
                except Exception as e:  # noqa: BLE001 -- the scene is still made; the sheet says what it carries
                    print("%s: dials not laid on: %s" % (s, e), file=sys.stderr)
                try:
                    T.scene(sdir(n, s))
                except SystemExit as e:
                    raise RuntimeError("%s: %s" % (s, e))
        elif not os.path.exists(made):
            T.make(dict(p, out=made))
        use = made
        if up:
            use = os.path.join(out, "print-%s-%s.mp4" % (key, up))
            if not os.path.exists(use):
                subprocess.run([sys.executable, str(ST.part("local-studio") / "local.py"), "upscale", made, "-o", use,
                                "--esrgan-model", up, "--scale", "2"], check=True)
        wf.setdefault("sources", {})[st["id"]] = {"file": os.path.basename(use), "drive_location": use, "generated": True}
        steps.append({"id": st["id"], "tool": "ffmpeg.trim", "model": None, "prompt": None, "seed": None,
                      "inputs": {"source": "slot:" + st["id"], "in": 0.0, "out": round(probe_dur(use), 3)},
                      "params": {}, "note": "the take print" + (" upscaled (" + up + ")" if up else "")})
    return steps, dict(wf, steps=steps)


def run_scene(n, s, take=None):
    brief = load(os.path.join(bdir(n), "brief.json"))
    take = take or brief["picks"][s]
    d = sdir(n, s)
    wf = load(os.path.join(d, take + ".json"))
    steps = wf["steps"]
    if any(st["tool"] == "gen.take" for st in steps):   # a one-take print: made here, then cut like any clip
        stale = [x for st in steps if st["tool"] == "gen.take" for x in stale_elements(n, st.get("params") or {})]
        if stale:                                        # never spend on a take built from old elements
            return {"ok": False, "stale": stale, "waits": ["current cast"]}
        steps, made_wf = _take_steps(n, s, take, wf)
        wf = dict(wf, sources=made_wf["sources"], _hash_as=wf_hash(wf))   # the run is stamped with the take as saved
    return SCUT.cut(n, s, take, wf, steps, brief)   # the cut itself is Video Edit's (machine/studio/scene_cut.py)


def scene_state(n, s, brief):
    try:
        pull_board_words(n, s, brief)
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        pass                            # the storyboard's words never stop a scene from opening
    d = sdir(n, s)
    takes = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(d, "take-*.json")))
    pick = brief["picks"].get(s, takes[0] if takes else None)
    wf = load(os.path.join(d, pick + ".json"))
    rp = os.path.join(d, "out", pick, "run.json")
    run = load(rp) if os.path.exists(rp) else None
    fresh = bool(run and run["workflow_hash"] == wf_hash(wf))
    waits = sorted({WAITS.get(st["tool"], st["tool"]) for st in wf["steps"] if st["tool"] not in RUNNABLE})
    status = "running" if RUNNING.get((n, s)) else ("made" if fresh else ("changed" if run else ("waiting" if waits else "ready")))
    stale = [x for st in wf.get("steps") or [] if st.get("tool") == "gen.take" for x in stale_elements(n, st.get("params") or {})]
    return {"scene": s, "takes": takes, "pick": pick, "workflow": wf, "run": run, "status": status, "waits": waits, "stale": stale}


def brief_state(n):
    brief = load(os.path.join(bdir(n), "brief.json"))
    return {"brief": brief, "label": brief_label(brief.get("brief_key")), "scenes": [scene_state(n, s, brief) for s in brief["order"]]}


def new_take(n, s):
    brief = load(os.path.join(bdir(n), "brief.json"))
    d = sdir(n, s)
    cur = load(os.path.join(d, brief["picks"][s] + ".json"))
    k = 1 + max(int(os.path.basename(p)[5:-5]) for p in glob.glob(os.path.join(d, "take-*.json")))
    cur["take"] = f"take-{k}"
    cur["from_take"] = brief["picks"][s]
    save(os.path.join(d, f"take-{k}.json"), cur)
    # the cut keeps the take it has until someone picks the copy (the owner 8 Nov: "New take" emptied a finished scene)
    return cur["take"]


def shot_frame(n, s, step_id):
    """A still of one shot in a scene (its source at the shot's in point), cached beside the scene's run."""
    brief = load(os.path.join(bdir(n), "brief.json"))
    pick = brief["picks"][s]
    wf = load(os.path.join(sdir(n, s), pick + ".json"))
    st = next(x for x in wf["steps"] if x.get("id") == step_id)
    src = (wf.get("sources") or {}).get(((st.get("inputs") or {}).get("source") or "")[5:])
    out = os.path.join(sdir(n, s), "out", "shots", pick + "-" + step_id + ".jpg")
    if os.path.exists(out):
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    t = float((st.get("inputs") or {}).get("in") or 0) + 0.3
    rg = ranged(src, (brief.get("shot_fill") or {}).get("brand") or "") if src else None
    if rg:                           # one frame read by range from Shared Assets, never the whole clip (17 Nov)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-headers", rg[1], "-ss", str(t), "-i", rg[0], "-frames:v", "1",
                        "-vf", "scale=270:-2", out], check=True, timeout=60)
        return out
    path = resolve(src) if src else None
    if not path or not os.path.exists(path):
        raise FileNotFoundError("no source for " + step_id)
    args = ["ffmpeg", "-v", "error", "-y"] + ([] if path.lower().endswith((".jpg", ".jpeg", ".png")) else ["-ss", str(t)])
    subprocess.run(args + ["-i", path, "-frames:v", "1", "-vf", "scale=270:-2", out], check=True, timeout=60)
    return out


def open_in_hyperframes(n, version=None):
    """The edit (or one version's edit) in HyperFrames' own studio, running locally, to show inside the Video Studio
    (the owner 8 Nov: in the Claude browser, local, not Chrome or the desktop app). Reuses a studio already running for
    that project; otherwise starts one in the background."""
    d = os.path.join(bdir(n), "versions", version, "studio") if version and version != "control" else os.path.join(bdir(n), "studio")
    if not os.path.isdir(d):
        raise FileNotFoundError("no HyperFrames project for " + (version or "the cut") + " yet")
    def running():
        r = subprocess.run(["hyperframes", "preview", "--list"], capture_output=True, text=True, timeout=30)
        for line in r.stdout.splitlines():
            m = re.search(r"Port (\d+)\s+studio\s+(.+?) \(PID", line)
            if m and os.path.realpath(m.group(2).strip()) == os.path.realpath(d):
                return int(m.group(1))
        return None
    port = running()
    if not port:
        import socket
        port = 3400
        while True:
            with socket.socket() as sk:
                if sk.connect_ex(("127.0.0.1", port)):
                    break
            port += 1
        subprocess.run(["hyperframes", "preview", d, "--background", "--port", str(port), "--open=false"],
                       capture_output=True, text=True, timeout=90)
        port = running() or port
    return {"project": os.path.relpath(d, HERE), "url": f"http://127.0.0.1:{port}/"}


def package(n):
    """Production package: each made scene's file at its place on the timeline, for HyperFrames."""
    st = brief_state(n)
    at, items = 0.0, []
    for sc in st["scenes"]:
        if sc["status"] != "made":
            items.append({"scene": sc["scene"], "status": sc["status"], "waits": sc["waits"]})
            continue
        r = sc["run"]
        base = os.path.join("scenes", sc["scene"])
        items.append({"scene": sc["scene"], "take": sc["pick"], "status": "made", "start": round(at, 3),
                      "end": round(at + r["duration"], 3),
                      "video": os.path.join(base, r["files"]["video"]),
                      "layers": {"captions": os.path.join(base, r["files"]["captions"])},
                      "recipe": os.path.join(base, sc["pick"] + ".json"), "workflow_hash": r["workflow_hash"]})
        at += r["duration"]
    pkg = {"schema": "production-package/v1", "brief": st["brief"]["brief"], "deliver": st["brief"]["deliver"],
           "made_seconds": round(at, 3), "scenes": items,
           "written": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    save(os.path.join(bdir(n), "production-package.json"), pkg)
    return pkg


# ---------------------------------------------------------------- the studio (one front door for video work)
# the owner 8 Nov: one centralized menu, one look, always clear which brief and stage; full reference for AI shots.
GEN = os.path.join(SOURCES, "generated")
BOARD = ST.BOARD
APPROVE = ST.APPROVE
_cache = {}


def _get(url, timeout=4, ttl=20):
    import time as _t
    import urllib.request as _u
    hit = _cache.get(url)
    if hit and _t.time() - hit[0] < ttl:
        return hit[1]
    try:
        v = json.load(_u.urlopen(url, timeout=timeout))
    except Exception:  # noqa: BLE001 — a tool that is down just shows as empty
        v = None
    _cache[url] = (_t.time(), v)
    return v


def filed_brief(b, n):
    """The brief number a production was filed under, read from the brand's brief list when the production's own record
    never got it (a session filed the approval card directly; 12 Nov: a live ad sat under "making" because only the brief
    list knew its number). A brief row names where it came from in `aliases`: the writing run, the production folder or
    the idea. Several briefs from one production (one card per face): the lowest number names it. None when no row does."""
    names = {str(x) for x in (b.get("brief"), n, b.get("idea")) if x}
    brand = str(b.get("brand") or (b.get("shot_fill") or {}).get("brand") or "")
    if not brand:
        try:
            brand = load(os.path.join(ST.WRITING, str(b.get("brief")), "run.json")).get("brand") or ""
        except Exception:  # noqa: BLE001
            brand = ""
    if not brand or not names:
        return None
    rows = []
    for root in dict.fromkeys([_ws(), Path(str(ST.REPO))]):     # the data workspace, then this Studio copy's own
        try:
            got = load(str(root / "brands" / brand / "briefs" / "briefs.json"))
        except Exception:  # noqa: BLE001
            continue
        rows += got.get("briefs", []) if isinstance(got, dict) else got
    hits = sorted((r["brief"], r["product"]) for r in rows if isinstance(r, dict) and r.get("brief") and r.get("product")
                  and names & {str(a) for a in (r.get("aliases") or [])})
    return "%s_%s_%s" % (brand, hits[0][1], hits[0][0]) if hits else None


def productions():
    out = []
    for bp in sorted(glob.glob(os.path.join(BRIEFS, "*", "brief.json"))):
        if os.path.islink(os.path.dirname(bp)):
            continue                     # an old folder name kept as a link (P02 -> idea-2) is not a second production
        try:
            b = load(bp)
        except (OSError, ValueError):
            continue
        n = os.path.basename(os.path.dirname(bp))
        key = str(b.get("brief_key") or filed_brief(b, n) or b.get("brief") or "")      # the numbered brief once it has one
        brand = key.split("_", 1)[0] if key.split("_", 1)[0] in dict(brands_here()) else None
        try:
            made = lane_of(b)
            made = dict(made, label=_lane().label(made["lane"]))
        except Exception:  # noqa: BLE001 -- the list never fails because the chain's rule could not be read
            made = None
        out.append({"n": n, "title": b.get("title") or n, "idea": b.get("idea"), "brand": brand, "key": key,
                    "scenes": len(b.get("order") or []),
                    "versions": len(versions(n)), "made_as": made})
    return out


def _names():
    """components/naming/names.py of this workspace, or None."""
    try:
        sys.path.insert(0, str(ST.part("naming")))
        import names as NM
        return NM
    except Exception:  # noqa: BLE001
        return None


def _same_brief_entry(key, by_id):
    """The ledger entry for this brief under another spelling of its product (`brand_a_flex_brief-0232` =
    `brand_a_flex-face-brush_brief-0232`). Brand + product + number must all agree: a number alone names a brief per
    brand AND product, so one product's 0324 never stands in for another product's 0324 (2026-11-11). With the
    rollback switch thrown (brief-labels.json "on": false) it matches brand + number as it used to."""
    NM = _names()
    if NM is None or not NM.brief_ids_on():
        brand, num = key.split("_", 1)[0], key.rsplit("_brief-", 1)[1]
        return next((x for k, x in by_id.items() if str(k).startswith(brand + "_") and str(k).endswith("_brief-" + num)), None)
    return next((x for k, x in by_id.items() if "_brief-" in str(k) and NM.same_brief(k, key)), None)


# Every lane, one identity (2026-11-11): the Studio will hold picture briefs beside video ones, and a number is shared
# across products, brands and lanes. An item is its lane + its full brief key; links carry both (brief=<key>&lane=…).
PICTURE_LANES = (None, "", "image", "image-teardown", "image-production", "image-edit", "picture")
OPEN_STATES = ("for-review", "approved", "in-production")


def pictures_on():
    """The picture lane shows in the Studio menu only once it is switched on (VIDEO_STUDIO_PICTURES=1, or
    "studio_pictures": true in components/naming/brief-labels.json): picture work has not moved into the Studio yet."""
    if str(os.environ.get("VIDEO_STUDIO_PICTURES") or "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    NM = _names()
    try:
        return bool(NM and NM._brief_labels().get("studio_pictures"))
    except Exception:  # noqa: BLE001
        return False


def picture_briefs(brand, reg=None):
    """The brand's open picture briefs, each by its full key (brand + product + number), from the brief register. A
    picture run folder named by number alone (brief-0324-plates) is never read for identity: its number can be two
    products' briefs."""
    NM = _names()
    if NM is None:
        return []
    out = []
    for r in NM.register_rows(brand, reg):
        if r.get("_table") != "briefs" or r.get("lane") not in PICTURE_LANES:
            continue
        key = NM.full_brief_key(r["key"])
        if not key or (r.get("state") or "for-review") not in OPEN_STATES:
            continue
        out.append({"production": None, "key": key, "label": brief_label(key), "lane": "image",
                    "id": "image:" + key, "name": r.get("title") or r.get("run") or key})
    return out


def brief_label(key):
    """The readable ID people see for a brief: "Acme · Body scrub · 0324" (names.brief_label), or ""."""
    NM = _names()
    try:
        got = NM.brief_label(key) if NM and key else ""
    except Exception:  # noqa: BLE001
        got = ""
    if got or not key:
        return got
    # a writing run already given its register number (run.json "brief": "brief-0377") shows it before the hand-off
    # (owner, 20 Nov: the brief number is seen as soon as the brief is approved)
    try:
        rj = json.loads((Path(ST.WRITING) / str(key) / "run.json").read_text())
        num = (re.search(r"brief-(\d+)", str(rj.get("brief") or "")) or [None, None])[1]
        if num:
            prod = str(rj.get("product") or "").replace("brilliance-", "").replace("-", " ").capitalize()
            return " · ".join(x for x in (str(rj.get("brand") or "").capitalize(), prod, num) if x)
    except (OSError, ValueError):
        pass
    return ""


def ledger_stages(prods):
    """key -> {"id", "name", "flag"} for every production, read from the ledger (the Queue). A piece the ledger has
    closed (sent to Meta and completed) is live. Names are the ledger's own stage names (components/naming/stages.json)."""
    d = _get(ST.LEDGER + "/api/queue", timeout=20, ttl=60) or {}
    names = {}
    try:
        names = {s["id"]: s["name"] for s in json.loads((ST.part("naming") / "stages.json").read_text())["stages"]}
    except (OSError, ValueError, KeyError):
        pass
    by_id = {}
    for e in d.get("items") or []:
        by_id[e.get("id")] = e
    for e in d.get("removed") or []:
        if str(e.get("note") or "").startswith("Completed") or e.get("stage") == "live":
            by_id.setdefault(e.get("id"), dict(e, stage="live"))
    out = {}
    for p in prods:
        key = p.get("key") or ""
        e = by_id.get(key)
        if e is None and p.get("run"):                           # a piece named by its writing run
            e = by_id.get(f"{key.split('_', 1)[0]}_idea_{p['run']}")
        if e is None and "_brief-" in key:                       # the same brief under another product spelling
            e = _same_brief_entry(key, by_id)
        if e:
            sid = e.get("stage")
            out[key] = {"id": sid, "name": names.get(sid, sid), "flag": e.get("flag")}
    return out


def idea_runs():
    """storyboard idea -> its writing run, from the board's matrix (the board's own data)."""
    try:
        board = Path(os.environ.get("VIDEO_STUDIO_BOARD_DATA") or ST.REPO / "runs" / "storyboard")
        return {f"idea-{a['n']}": a.get("line") for a in json.loads((board / "matrix.json").read_text()).get("ads", []) if a.get("line")}
    except (OSError, ValueError):
        return {}


def link_productions(prods, ideas=None):
    """A production made from an idea's writing run is that idea's production, even when its brief.json never said so:
    its key ends with the run's name. Fills `idea` and `run` on each production."""
    runs = idea_runs()
    for p in prods:
        key = str(p.get("key") or p.get("n") or "")
        if not p.get("idea"):
            p["idea"] = next((i for i, r in runs.items() if r and key.endswith(r)), None)
        p["run"] = runs.get(p.get("idea")) if p.get("idea") else None
    return prods


def _stage(sid):
    """A stage by its id, named as the team names it (components/naming/stages.json)."""
    try:
        names = {s["id"]: s["name"] for s in json.loads((ST.part("naming") / "stages.json").read_text())["stages"]}
    except (OSError, ValueError, KeyError):
        names = {}
    return {"id": sid, "name": names.get(sid, sid)}


def ledger_idea_stages(ideas):
    """idea -> its ledger stage, for storyboard ideas not yet in production: the board's matrix names each idea's
    writing run, and the ledger files a run as <brand>_idea_<run>."""
    d = _get(ST.LEDGER + "/api/queue", timeout=20, ttl=60) or {}
    try:
        names = {s["id"]: s["name"] for s in json.loads((ST.part("naming") / "stages.json").read_text())["stages"]}
    except (OSError, ValueError, KeyError):
        names = {}
    runs = idea_runs()
    items = list(d.get("items") or [])
    out = {}
    for i in ideas:
        run = runs.get(i.get("id"))
        if not run:
            continue
        e = next((x for x in items if str(x.get("id")) == f"{i.get('brand')}_idea_{run}"
                  or any(str(s).endswith(":" + run) for s in x.get("sources") or [])), None)
        if e:
            out[i["id"]] = {"id": e.get("stage"), "name": names.get(e.get("stage"), e.get("stage")), "flag": e.get("flag")}
    return out


def ledger_handoffs(ideas):
    """idea -> the hand-off the Queue records for it, when it was handed off outside the Studio's own Next step (the
    owner, 20 Nov: an idea already in the editor's or producer's queue reads With the editor, wherever it was packed).
    The Queue marks a packed hand-off with a `handoff:<role>/<brand>/<key>` source on the piece's card."""
    d = _get(ST.LEDGER + "/api/queue", timeout=20, ttl=60) or {}
    runs = idea_runs()
    items = list(d.get("items") or [])
    out = {}
    for i in ideas:
        run = runs.get(i.get("id"))
        if not run:
            continue
        for x in items:
            src = [str(s) for s in x.get("sources") or []]
            if not any(s.endswith(":" + run) for s in src) and str(x.get("id")) != f"{i.get('brand')}_idea_{run}":
                continue
            ho = next((s for s in src if s.startswith("handoff:")), None)
            if ho and x.get("stage") not in ("live",):
                key = ho.rsplit("/", 1)[-1]
                num = (re.search(r"brief-(\d+)", key) or [None, None])[1]
                out[i["id"]] = {"key": key, "number": num and "brief-" + num, "label": x.get("label") or brief_label(key),
                                "to": ho.split(":", 1)[1].split("/", 1)[0], "at": x.get("at"), "clips": None,
                                "drive": None, "timeline": None}
                break
    return out


REMOVED_IDEAS = os.path.join(os.path.dirname(BRIEFS), "removed-ideas.json")


def removed_ideas():
    """idea -> when it was removed (the owner, 20 Nov: a Remove button on every idea). Nothing is deleted: the idea
    folds into Removed at the bottom of the list, and Put back brings it back."""
    try:
        return load(REMOVED_IDEAS)
    except (OSError, ValueError):
        return {}


def remove_idea(idea, undo=False):
    """Off the Studio and off the idea queue, in one click: the Studio folds it away, and the Queue's own Remove (nothing
    deleted, Put back undoes it) takes its card off the queue. Put back reverses both."""
    if not re.fullmatch(r"idea-\d+", idea or ""):
        raise ValueError("no idea called %s" % idea)
    rec = removed_ideas()
    was = rec.get(idea) if isinstance(rec.get(idea), dict) else {}
    said = "Put back." if undo else "Removed from the Studio."
    run = idea_runs().get(idea)
    d = _get(ST.LEDGER + "/api/queue", timeout=20, ttl=0) or {}
    brand = next((i.get("brand") for i in (_get(BOARD + "/api/ideas", timeout=30, ttl=60) or []) if i.get("id") == idea), None)
    items = list(d.get("items") or []) + list(d.get("removed") or [])
    e = next((x for x in items if run and (str(x.get("id")) == "%s_idea_%s" % (brand, run)
              or any(str(s_).endswith(":" + run) for s_ in x.get("sources") or []))), None) if run else None
    took = None
    if undo:
        # Put back returns only a card this Remove took off; a card the team removed before stays as it was
        if was.get("queue"):
            r = _post_queue("/api/queue/remove", {"id": was["queue"], "undo": True})
            said += " " + (r.get("said") or r.get("error") or "")
        rec.pop(idea, None)
    else:
        if e and not e.get("removed"):
            r = _post_queue("/api/queue/remove", {"id": e["id"]})
            said += " " + (r.get("said") or r.get("error") or "")
            took = e["id"] if r.get("ok") else None
        else:
            said += " It was already off the idea queue." if e else " It had no card on the idea queue."
        rec[idea] = {"at": datetime.datetime.now().isoformat(timespec="seconds"), "queue": took}
    save(REMOVED_IDEAS, rec)
    return {"ok": True, "said": said.strip(), "removed": not undo}


def brands_here():
    """(brand, label) for every brand folder in this workspace; the label from the brand's own account file."""
    out = []
    root = ST.REPO / "brands"
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        if not d.is_dir() or d.name.startswith(("_", ".")):
            continue
        label = d.name
        acc = d / "meta" / "account.json"
        try:
            a = json.loads(acc.read_text())
            label = a.get("label") or (a.get("spelling") or {}).get(d.name) or d.name.capitalize()
        except (OSError, ValueError):
            continue                       # a brand with no account file runs no ads, so it has no video work here
        out.append((d.name, label))
    return out


def chain_cut_back(n):
    """True when an AI-lane production's cut was made from the production chain in the Studio after its hand-off: the
    ad is the Studio's again, never shown as with the editor (2026-11-20)."""
    try:
        mp = os.path.getmtime(os.path.join(bdir(n), "maker-pack.json"))
        return lane_of(load(os.path.join(bdir(n), "brief.json")))["lane"] == "ai" and any(
            c.stat().st_mtime > mp for c in _cuts(Path(bdir(n))))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def handoff_of(n):
    """The editor's hand-off for a production (maker-pack.json, written by the Next step's hand-off), or None."""
    try:
        r = load(os.path.join(bdir(n), "maker-pack.json"))
    except (OSError, ValueError):
        return None
    if not r.get("key") or not r.get("number"):
        return None
    if chain_cut_back(n):
        return None
    drive = None
    try:                                 # the Drive folder's web link, from the mounted copy's own id
        fid = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", r.get("drive") or ""],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        drive = ("https://drive.google.com/drive/folders/" + fid) if fid else None
    except (OSError, subprocess.SubprocessError):
        pass
    num = str(r["number"]).replace("brief-", "")
    # one label everywhere: brand · product · number, the register's own words (names.brief_label), same as every ad
    return {"key": r["key"], "number": r["number"], "label": brief_label(r["key"]) or ("Brief " + num), "clips": r.get("clips"),
            "drive": drive, "timeline": "/handoff/%s/TIMELINE.html" % n}


def menu():
    ideas = _get(BOARD + "/api/ideas", timeout=30, ttl=60) or []
    prods = link_productions(productions())
    by_idea = {p["idea"]: p for p in prods if p.get("idea")}
    for p in prods:
        if not p["brand"] and p.get("idea"):
            p["brand"] = next((i.get("brand") for i in ideas if i.get("id") == p["idea"]), None)
    cards = (_get(APPROVE + "/api/cards?view=check", timeout=6, ttl=30) or {}).get("cards") or []
    waiting = {}
    for c in cards:
        waiting.setdefault(c.get("brand"), []).append(c.get("ad_name") or c.get("id"))
    # every ad's stage comes from the ledger (the Queue), the same record the board and every tool read (the owner,
    # 8 Nov: "studio needs to function on the same ledger as the board because it's all one integrated system")
    stage_of = ledger_stages(prods)
    idea_stage = ledger_idea_stages(ideas)
    queued = ledger_handoffs(ideas)
    gone = removed_ideas()
    brands = []
    for b, label in brands_here():
        items = []
        for i in ideas:
            if i.get("brand") != b:
                continue
            p = by_idea.get(i["id"])
            # the ledger's stage, by the team's stage names (components/naming/stages.json); opening a production is
            # not a handoff: with no ledger record for it, the idea's own record holds, else it is still a swipe teardown
            stage = (stage_of.get(p["key"]) if p else None) or idea_stage.get(i["id"]) or _stage("idea")
            ho = None if (p and chain_cut_back(p["n"])) else ((handoff_of(p["n"]) if p else None) or queued.get(i["id"]))
            if ho:                       # handed to the editor: one line, never the old production board (owner, 17 Nov)
                stage = {"id": "with-editor", "name": "With the editor"}
            items.append({"idea": i["id"], "name": i.get("name"), "swipe": i.get("swipe"), "production": p and p["n"],
                          "key": p and p["key"], "label": (ho and ho["label"]) or brief_label((p and p["key"]) or idea_runs().get(i["id"])),
                          "versions": p and p["versions"], "handoff": ho, "removed": i["id"] in gone,
                          "stage": stage, "lane": "video", "id": "video:" + ((p and p["key"]) or i["id"]),
                          "made_as": p and p.get("made_as")})      # how it is made and why: the chain's call, shown
        loose = [p for p in prods if p["brand"] == b and not p.get("idea")]
        pics = picture_briefs(b) if pictures_on() else []
        pic_stage = ledger_stages(pics) if pics else {}
        for x in pics:
            x["stage"] = pic_stage.get(x["key"]) or _stage("making")
        brands.append({"id": b, "label": label, "ideas": items,
                       "productions": [{"production": p["n"], "name": p["title"], "key": p["key"], "label": brief_label(p["key"]),
                                        "lane": "video", "id": "video:" + (p["key"] or p["n"]),
                                        "stage": stage_of.get(p["key"]) or _stage("making")} for p in loose],
                       "pictures": pics,
                       "waiting": len(waiting.get(b, []))})
    return {"brands": brands, "board": bool(ideas), "approve": cards is not None}


def _recipes():
    """name -> (recipe dict, recipe file) over every recipe file the generator wrote."""
    out = {}
    for f in sorted(glob.glob(os.path.join(GEN, "recipes*.json"))):
        try:
            d = load(f)
        except (OSError, ValueError):
            continue
        rel = os.path.relpath(f, GEN)
        if isinstance(d, list):
            for r in d:
                out[r.get("name")] = (dict(r, kind="from a real frame"), rel)
        elif isinstance(d, dict):
            shots = d.get("shots") or {}
            for name, prompt in (shots.items() if isinstance(shots, dict) else []):
                out[name] = ({"name": name, "kind": "from a text prompt only", "action": prompt, "style": d.get("style"),
                              "model": d.get("model"), "seed": d.get("seed"), "job": (d.get("jobs") or {}).get(name)}, rel)
    return out


def _gen_file(rel):
    return rel if rel and os.path.isfile(os.path.join(GEN, rel)) else None


def clip_reference(n, s):
    """Everything behind each AI shot a scene uses: the real frame, every prompt, the models and settings, every take
    made (kept and rejected, with the reason), and where the shot sits in the scene."""
    import gen_ref as GR
    brief = load(os.path.join(bdir(n), "brief.json"))
    take = brief["picks"][s]
    wf = load(os.path.join(sdir(n, s), take + ".json"))
    rec = _recipes()
    out = []
    for slot, src in (wf.get("sources") or {}).items():
        if not src.get("generated"):
            continue
        name = os.path.splitext(os.path.basename(src.get("file") or src.get("drive_location") or ""))[0]
        r, rf = rec.get(name, ({}, None))
        made = r.get("made") or {}
        steps = []
        on_house = str(made.get("process") or "").startswith("house")
        OLD_EDIT, OLD_I2V = "fal-ai/nano-banana/edit", "fal-ai/bytedance/seedance/v1/lite/image-to-video"
        if r.get("kind") == "from a real frame":
            exact = {x.get("what"): x for x in made.get("steps") or []}
            ref = _gen_file(os.path.join("refs", r.get("ref") or ""))
            if r.get("still"):
                st = exact.get("still")
                steps.append({"what": "Still from the reference", "model": (st or {}).get("model") or (GR.EDIT if on_house else OLD_EDIT), "input": ref,
                              "prompt": (st or {}).get("sent", {}).get("prompt") or (r["still"] + GR.MATCH),
                              "prompt_note": "exactly as sent" if st else "rebuilt: the recipe's words plus the tool's camera-match clause",
                              "out": _gen_file(os.path.join("refs", name + "-still.jpg")),
                              "request_id": (st or {}).get("request_id"), "at": (st or {}).get("at")})
            cl = exact.get("clip")
            steps.append({"what": "Clip from the still" if r.get("still") else "Clip from the reference", "model": (cl or {}).get("model") or (GR.I2V if on_house else OLD_I2V),
                          "input": _gen_file(made.get("frame")) or (steps[-1]["out"] if steps else ref),
                          "prompt": (cl or {}).get("sent", {}).get("prompt") or (r.get("action", "") + GR.LOOK),
                          "prompt_note": "exactly as sent" if cl else "rebuilt: the recipe's action plus the tool's phone-look clause",
                          "settings": (cl or {}).get("sent") and {k: v for k, v in cl["sent"].items() if k not in ("prompt", "image_url")}
                          or {"resolution": "720p", "duration": "5 s", "seed": r.get("seed", 322)},
                          "out": _gen_file(name + ".mp4"), "request_id": (cl or {}).get("request_id"), "at": (cl or {}).get("at")})
        elif r:
            ref = None
            steps.append({"what": "Clip from a text prompt (no reference frame)", "model": r.get("model"), "input": None,
                          "prompt": (r.get("action") or "") + " " + (r.get("style") or ""), "prompt_note": "as written in the recipe",
                          "settings": {"seed": r.get("seed")}, "out": _gen_file(name + ".mp4"), "request_id": r.get("job")})
        else:
            ref = None
        phone = _gen_file(os.path.join("phone", name + ".mp4"))
        if phone:
            steps.append({"what": "Phone pass", "model": "ffmpeg (no AI)", "input": name + ".mp4",
                          "prompt": "Re-shot through a phone look: 432 px, grain, compression, handheld drift (video_studio.phone_copy)",
                          "prompt_note": "a fixed recipe, not a prompt", "out": phone})
        rejected = sorted(os.path.relpath(f, GEN) for f in glob.glob(os.path.join(GEN, "rejected", name + "*")))
        used = [{"step": st.get("id"), "in": (st.get("inputs") or {}).get("in"), "out": (st.get("inputs") or {}).get("out")}
                for st in wf.get("steps") or [] if (st.get("inputs") or {}).get("source") == "slot:" + slot]
        out.append({"slot": slot, "name": name, "kind": r.get("kind") or "no recipe found", "recipe_file": rf,
                    "process": made.get("process") if on_house else "made OFF the house process (fal: Nano Banana edit, Seedance lite 720p) — before 8 Nov",
                    "on_house": on_house, "house": GR.PROCESS,
                    "ref": ref, "steps": steps, "rejected_notes": r.get("rejected") or [], "rejected_files": rejected,
                    "error": r.get("error"), "used": used,
                    "clip_model": (r.get("clip_model") or GR.DEFAULT) if r.get("kind") == "from a real frame" else None,
                    "making": bool(MAKING.get(name))})
    return {"brief": n, "scene": s, "take": take, "shots": out}


# ---------------------------------------------------------------- motion: author a scene's motion and watch it; the motion
# chain passes or holds it on its own checks (Override is recorded)
MOTION_READING = {}   # (brief, scene) -> what is being read right now


def _beats(wf):
    """The scene's lines in order, each with its speaker: what the motion has to carry."""
    lines = [st for st in wf.get("steps") or [] if st.get("tool") in ("voice.ai", "human.read") and st.get("prompt")]
    lines.sort(key=lambda st: (st.get("params") or {}).get("order") or 0)
    if lines:
        return [{"speaker": (st.get("params") or {}).get("speaker") or "", "say": st["prompt"]} for st in lines]
    return [{"speaker": "", "say": w} for w in [wf.get("words")] if w]


def _swipe_of(brief):
    """The swipe this brief was written from, when its writing run holds it."""
    run = os.path.join(str(ST.WRITING), str(brief.get("brief") or ""))
    found = sorted(glob.glob(os.path.join(run, "*swipe*.mp4")))
    return found[0] if found else None


def motion_state(n, s):
    brief = load(os.path.join(bdir(n), "brief.json"))
    d = os.path.join(sdir(n, s), "motion")
    f = os.path.join(d, "motion.json")
    rec = load(f) if os.path.exists(f) else None
    wf = load(os.path.join(sdir(n, s), brief["picks"][s] + ".json"))
    swipe = _swipe_of(brief)
    base = "/files/" + n + "/scenes/" + s + "/motion/"
    reading = MOTION_READING.get((n, s))
    # the lines the motion carries: the take's own lines, one per speaker, when the scene has a continuous take (the
    # voice steps hold each written scene's paragraph under one speaker)
    td = take_dir(n, s)
    tk = load(os.path.join(td, "take.json")) if td else {}
    beats = [{"speaker": ln.get("speaker") or ln.get("who") or "", "say": ln.get("say") or ln.get("action") or ""}
             for ln in tk.get("script") or [] if ln.get("say") or ln.get("action")] or _beats(wf)
    if rec and rec.get("kind") == "directed":      # our direction: the reference's measures do not describe it
        rec = {k: v for k, v in rec.items() if k not in ("people_max", "frames", "frames_with_people", "hands_seen", "faces_seen", "cost_usd")}
    camera = ("%d shots, our own camera" % len(rec.get("camera_shots") or []) if rec and rec.get("kind") == "directed" else
              load(os.path.join(d, "camera.json")).get("summary") if os.path.exists(os.path.join(d, "camera.json")) else None)
    return {"brief": n, "scene": s, "status": "reading" if reading and not reading.get("error") else (rec or {}).get("status") or "none",
            "error": (reading or {}).get("error"), "reading": reading, "motion": rec, "beats": beats,
            "swipe": {"file": os.path.basename(swipe), "seconds": round(probe_dur(swipe), 1)} if swipe else None,
            "urls": ({"overlay": base + "rehearsal/" + ("overlay.mp4" if os.path.exists(os.path.join(d, "rehearsal", "overlay.mp4")) else "blocking.mp4")
                      + "?t=%d" % os.path.getmtime(os.path.join(d, "rehearsal", "blocking.mp4"))}
                     if rec and rec.get("kind") in ("directed", "programmed") and os.path.exists(os.path.join(d, "rehearsal", "blocking.mp4")) else
                     {k: base + v + ("?t=" + rec.get("tracked_at", "")) for k, v in (rec.get("files") or {}).items()} if rec else {}),
            "camera": camera, "has_take": os.path.exists(os.path.join(sdir(n, s), "take.json"))}


def _read_motion(n, s, clip, start, end, kind, name=None):
    key = (n, s)
    try:
        # through the motion chain (components/motion): the clip tracked, read, rehearsed in 3D, checked, and passed or
        # held on its own checks; nobody is asked
        chain = os.path.join(str(ST.part("motion")), "motion_chain.py")
        span = ["--source", clip, "--span", "%s-%s" % (float(start or 0), float(end))] if end else ["--clip", clip]
        r = subprocess.run([sys.executable, chain, "run", sdir(n, s)] + span + ["--only", "track,read,rehearse,preview"],
                           capture_output=True, text=True, timeout=3600)
        if r.returncode:
            MOTION_READING[key] = {"error": (r.stderr or r.stdout).strip()[-400:] or "the motion reader failed"}
            return
        MOTION_READING.pop(key, None)
    except Exception as e:  # noqa: BLE001  shown on the page
        MOTION_READING[key] = {"error": str(e)}


def _program_motion(n, s):
    key = (n, s)
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "motion_program.py"), "scene", sdir(n, s)],
                           capture_output=True, text=True, timeout=1800)
        if r.returncode:
            MOTION_READING[key] = {"error": (r.stderr or r.stdout).strip()[-400:] or "the motion programmer failed"}
            return
        MOTION_READING.pop(key, None)
    except Exception as e:  # noqa: BLE001  shown on the page
        MOTION_READING[key] = {"error": str(e)}


def motion_program(n, s):
    """Our own motion, programmed from the scene's take: Claude writes the blocking, the figures act it out."""
    if MOTION_READING.get((n, s)) and not MOTION_READING[(n, s)].get("error"):
        raise RuntimeError("this scene's motion is already being made")
    if not os.path.exists(os.path.join(sdir(n, s), "take.json")):
        raise RuntimeError("this scene has no take written yet")
    MOTION_READING[(n, s)] = {"kind": "programmed", "file": "the take", "since": datetime.datetime.now().strftime("%H:%M:%S")}
    threading.Thread(target=_program_motion, args=(n, s), daemon=True).start()
    return motion_state(n, s)


def motion_start(n, s, clip, start=0.0, end=None, kind="phone", name=None):
    if MOTION_READING.get((n, s)) and not MOTION_READING[(n, s)].get("error"):
        raise RuntimeError("this scene's motion is already being read")
    MOTION_READING[(n, s)] = {"kind": kind, "file": name or os.path.basename(clip), "since": datetime.datetime.now().strftime("%H:%M:%S")}
    threading.Thread(target=_read_motion, args=(n, s, clip, start, end, kind, name), daemon=True).start()
    return motion_state(n, s)


def motion_upload(n, s, name, kind, data):
    """A phone video (or a 3D render) dropped on the scene: kept in the scene's motion folder and read."""
    d = os.path.join(sdir(n, s), "motion")
    os.makedirs(d, exist_ok=True)
    ext = os.path.splitext(name or "")[1].lower() or ".mp4"
    if ext not in (".mp4", ".mov", ".m4v", ".webm"):
        raise RuntimeError("a video please: .mp4, .mov, .m4v or .webm")
    f = os.path.join(d, "source" + ext)                  # the scene's motion clip (the one before it is replaced)
    with open(f, "wb") as out:
        out.write(data)
    return motion_start(n, s, f, 0.0, None, kind if kind in ("phone", "3d", "swipe") else "phone", os.path.basename(name or ""))


def motion_approve(n, s, by=None):
    """An override, recorded: the motion chain passes or holds a scene's motion on its own checks; a person may pass
    held motion from the scene's Motion box, and the chain keeps who did and what it overrode."""
    home = str(ST.part("motion"))
    if home not in sys.path:
        sys.path.insert(0, home)
    import motion_chain as MC
    MC.approve(sdir(n, s), by or "the Video Studio's Override button")
    return motion_state(n, s)


# ---------------------------------------------------------------- direction: production's injection on the board
# (2026-11-15) The scene's source shots, read as capabilities (video-teardown production_spec), filled with our scene and
# directed: our own movement and camera (production_inject), rendered as the rehearsal; then the setup page from the
# take's own dry run (take.py scene --dry-run). Both free; the take itself stays on its own button.
DIRECTING = {}   # (brief, scene) -> what is running right now


def take_dir(n, s):
    """The folder of the scene's continuous take: the scene itself when it holds take.json, else its newest sub-folder
    that does (a hook made as one take keeps its own folder)."""
    d = sdir(n, s)
    if os.path.exists(os.path.join(d, "take.json")):
        return d
    subs = sorted(glob.glob(os.path.join(d, "*", "take.json")), key=os.path.getmtime)
    return os.path.dirname(subs[-1]) if subs else None


def direction_state(n, s):
    d = take_dir(n, s)
    run = DIRECTING.get((n, s))
    out = {"brief": n, "scene": s, "take_dir": d and os.path.relpath(d, BRIEFS), "running": run if run and not run.get("error") else None,
           "error": (run or {}).get("error"), "sheet": None, "review": None, "rehearsal": None, "source": None}
    if not d:
        return out
    rel = "/files/" + os.path.relpath(d, BRIEFS) + "/"
    try:
        import production_inject as PI
        src = PI.run_of(d, load(os.path.join(d, "take.json")))
        out["source"] = os.path.basename(str(src)) if src else None
        out["spec_made"] = bool(src and os.path.exists(os.path.join(str(src), "production-spec.json")))
    except Exception:  # noqa: BLE001
        pass
    f = os.path.join(d, "production-sheet.json")
    if os.path.exists(f):
        sh = load(f)
        spec = load(sh["spec"]) if sh.get("spec") and os.path.exists(sh["spec"]) else {}
        caps = {c.get("ref") or "%s.%s" % (x["id"], c.get("id")): dict(c, shot=x["id"]) for x in spec.get("shots") or [] for c in x.get("capabilities") or []}
        shots_at = [float(x.get("from") or 0) for x in ((sh.get("direction") or {}).get("camera") or {}).get("shots") or []]
        rows = []
        for b in sh.get("script") or []:
            c = caps.get(b.get("capability")) or {}
            t = float(b.get("from") or 0)
            rows.append({"line": b.get("line"), "from": b.get("from"), "to": b.get("to"),
                         "shot": sum(1 for a in shots_at if a <= t + 1e-6) or None,
                         "speaker": b.get("speaker") or (b.get("who") if b.get("say") else ""), "say": b.get("say") or "",
                         "who": b.get("who"), "action": b.get("action"), "prop": b.get("prop"), "target": b.get("target"),
                         "moves": b.get("moves") or {}, "from_script": b.get("from_script"),
                         "source": {"shot": c.get("shot"), "capability": c.get("capability"), "did": c.get("source_instance"),
                                    "picture": "/api/swipeshot/%s/%s/%s" % (n, s, c["shot"]) if c.get("shot") else None}})
        out["sheet"] = {"roles": sh.get("roles") or {}, "rows": rows, "line_check": sh.get("line_check") or [],
                        "beats": [{k: b.get(k) for k in ("from", "to", "who", "action", "prop", "target", "where", "say")}
                                  for b in sh.get("script") or []],
                        "shots": [{"from": x.get("from"), "words": x.get("words")} for x in ((sh.get("direction") or {}).get("camera") or {}).get("shots") or []],
                        "gaps": [{"capability": g.get("capability"), "tool": g.get("tool"), "gap": g.get("gap")} for g in sh.get("gaps") or []],
                        "at": datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%d %b %H:%M")}
    if os.path.exists(os.path.join(d, "motion", "rehearsal", "blocking.mp4")):
        out["rehearsal"] = rel + "motion/rehearsal/blocking.mp4?t=%d" % os.path.getmtime(os.path.join(d, "motion", "rehearsal", "blocking.mp4"))
    if os.path.exists(os.path.join(d, "review", "input-review.html")):
        out["review"] = rel + "review/input-review.html"
    return out


def _direct(n, s, what):
    key = (n, s)
    try:
        d = take_dir(n, s)
        if what == "inject":
            import production_inject as PI
            take = load(os.path.join(d, "take.json"))
            src = PI.run_of(d, take)
            if src is None:
                raise RuntimeError("this scene's take names no torn-down source (its motion reference) to read the production from")
            spec = os.path.join(str(src), "production-spec.json")
            if not os.path.exists(spec):
                sys.path.insert(0, str(ST.part("video-teardown") / "machine"))
                import production_spec as PS
                PS.run_spec(src)
            if os.path.exists(os.path.join(d, "take.before-inject.json")) and take.get("production_sheet"):
                take = load(os.path.join(d, "take.before-inject.json"))      # inject again from the take as written
                with open(os.path.join(d, "take.json"), "w") as f:
                    json.dump(take, f, indent=1, ensure_ascii=False)
            PI.inject(d, spec, write=True)
        else:                                       # the setup page: the take's own dry run, nothing made or paid
            r = subprocess.run([sys.executable, os.path.join(HERE, "take.py"), "scene", d, "--dry-run"],
                               capture_output=True, text=True, timeout=3600)
            if r.returncode:
                raise RuntimeError((r.stderr or r.stdout).strip()[-400:] or "the dry run failed")
        DIRECTING.pop(key, None)
    except (Exception, SystemExit) as e:  # noqa: BLE001  shown on the page
        DIRECTING[key] = {"error": str(e)[:600]}


def direction_start(n, s, what):
    if what not in ("inject", "setup"):
        raise RuntimeError("inject or setup")
    if DIRECTING.get((n, s)) and not DIRECTING[(n, s)].get("error"):
        raise RuntimeError("this scene is already being directed")
    if not take_dir(n, s):
        raise RuntimeError("this scene has no continuous take written yet")
    DIRECTING[(n, s)] = {"what": what, "since": datetime.datetime.now().strftime("%H:%M:%S")}
    threading.Thread(target=_direct, args=(n, s, what), daemon=True).start()
    return direction_state(n, s)


def versions(n):
    """The finished cut and each opening's version, newest render of each."""
    b = bdir(n)
    out = []
    cuts = sorted(glob.glob(os.path.join(b, "rough-cut-v*-sdr.mp4")),
                  key=lambda f: int(re.search(r"-v(\d+)-", f).group(1)) if re.search(r"-v(\d+)-", f) else 0)
    if cuts:
        out.append({"id": "control", "label": "Control", "file": os.path.relpath(cuts[-1], BRIEFS)})
    for d in sorted(glob.glob(os.path.join(b, "versions", "*"))):
        h = os.path.basename(d)
        f = sorted(glob.glob(os.path.join(d, "*-" + h + ".mp4")))
        if not f:
            continue
        title = h
        try:
            hb = load(os.path.join(b, "brief.json")).get("picks", {}).get(h)
            title = load(os.path.join(sdir(n, h), hb + ".json")).get("title") or h
        except Exception:  # noqa: BLE001
            pass
        out.append({"id": h, "label": title if title[:1] == "V" else h.replace("H", "V") + " · " + title,
                    "file": os.path.relpath(f[0], BRIEFS)})
    return out


# ONE ADDRESS (the owner, 8 Nov: "can we not just have this whole thing on one server?"). The Studio serves the storyboard
# board under /board/ and the approval page under /approve/. A request those pages make for their own absolute paths
# (/api/..., /files/...) carries the page as its Referer, so it goes back to the same app; the apps are untouched.
APPS = {"board": ST.BOARD, "approve": ST.APPROVE}
HOP = ("transfer-encoding", "connection", "content-length", "keep-alive", "x-frame-options")


def app_for(handler):
    """(app, path to send it) when this request belongs to the board or the approval page, else None."""
    path = urlparse(handler.path).path
    for name in APPS:
        if path == "/" + name or path.startswith("/" + name + "/"):
            rest = handler.path[len(name) + 1:]
            return name, rest if rest.startswith("/") else "/" + rest
    ref = urlparse(handler.headers.get("Referer") or "")
    if ref.netloc and ref.netloc == (handler.headers.get("Host") or ""):
        for name in APPS:
            if ref.path == "/" + name or ref.path.startswith("/" + name + "/"):
                SERVED[path] = name           # a script or style the app loaded: what it loads goes back to the app too
                return name, handler.path
        if ref.path in SERVED:
            SERVED[path] = SERVED[ref.path]
            return SERVED[ref.path], handler.path
    return None


SERVED = {}     # path -> app, for files an app's page loaded (their own requests name them as the Referer)


def proxy(handler, name, path):
    import http.client
    u = urlparse(APPS[name])
    body = handler.rfile.read(int(handler.headers.get("Content-Length") or 0) or 0) or None
    hdr = {k: v for k, v in handler.headers.items() if k.lower() not in ("host", "connection", "referer", "origin")}
    hdr["Host"] = u.netloc                      # the apps answer only their own address and origin
    hdr["X-Video-Studio"] = "1"                 # shown inside the Studio; the board sends a direct visit to the Studio
    if handler.headers.get("Origin"):
        hdr["Origin"] = f"{u.scheme}://{u.netloc}"
    if handler.headers.get("Referer"):
        hdr["Referer"] = f"{u.scheme}://{u.netloc}/"
    try:
        c = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=300)
        c.request(handler.command, path, body=body, headers=hdr)
        r = c.getresponse()
    except Exception as e:  # noqa: BLE001
        handler.send_response(502); handler.end_headers(); handler.wfile.write(f"{name} is not running: {e}".encode()); return
    handler.send_response(r.status)
    for k, v in r.getheaders():
        if k.lower() not in HOP:
            if k.lower() == "location" and v.startswith("/"):
                v = "/" + name + v                # a redirect stays inside the app
            handler.send_header(k, v)
    length = r.getheader("Content-Length")
    # The board's /api/cards and /api/storyboards are ~80 MB of JSON; uncompressed they never finish on a phone over
    # Tailscale, so the storyboard stays blank there. Text is gzipped when the browser accepts it (~85% smaller).
    ctype = (r.getheader("Content-Type") or "").lower()
    if ("gzip" in (handler.headers.get("Accept-Encoding") or "") and not r.getheader("Content-Encoding")
            and any(t in ctype for t in ("json", "javascript", "css", "html", "text/"))
            and (length is None or int(length) > 4096)):
        import gzip
        data = gzip.compress(r.read(), 5)
        handler.send_header("Content-Encoding", "gzip")
        handler.send_header("Vary", "Accept-Encoding")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)
        return
    if length is not None:
        handler.send_header("Content-Length", length)
        handler.end_headers()
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            handler.wfile.write(chunk)
    else:
        data = r.read()
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)


def order_start(q):
    """An order from the Creative Options board (brand, avatar, product, script format, a story preset or an arc,
    look, hook, seconds, tool) set up as a writing run through the from-scratch door, nothing written or spent yet.
    The combo rides on run.json so every brief can be matched back to the combination that made it."""
    import time as _t
    safe = lambda v: re.sub(r"[^a-z0-9-]", "", str(v or "").lower())[:60]
    brand, avatar, product = safe(q.get("brand")), safe(q.get("avatar")), safe(q.get("product"))
    if q.get("swipe"):
        return order_from_swipe(q, brand, avatar, product)
    if not (brand and avatar and product) or not (q.get("preset") or q.get("arc")):
        return {"ok": False, "error": "an order needs a brand, avatar, product and a story preset or an arc"}
    label = "order-%s-%s-%s" % (brand, safe(q.get("script")) or "piece", _t.strftime("%Y%m%d-%H%M%S"))
    cmd = [sys.executable, os.path.join(os.path.dirname(HERE), "video-writing", "machine", "scratch.py"), label,
           "--brand", brand, "--product", product, "--avatar", avatar]
    if q.get("preset"):
        cmd += ["--preset", safe(q["preset"])]
    else:
        cmd += ["--arc", safe(q.get("arc")), "--format", safe(q.get("script")), "--style", safe(q.get("look"))]
    if q.get("look") and q.get("preset"):
        cmd += ["--style", safe(q["look"])]
    for k in ("sub", "demographic"):
        if q.get(k):
            cmd += ["--" + k, str(q[k])]
    if q.get("seconds"):
        cmd += ["--seconds", str(int(q["seconds"]))]
    combo = {k: q.get(k) for k in ("source", "script", "preset", "arc", "brief", "look", "hook", "seconds", "tool") if q.get(k)}
    cmd += ["--combo", json.dumps(combo)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return {"ok": False, "error": (r.stderr or r.stdout).strip().splitlines()[-1:] or ["the order could not be set up"]}
    out = {"ok": True, "label": label, "run": "runs/video-teardown/_work/" + label, "combo": combo,
           "next": "set up: the writing fills it when started (nothing spent yet)"}
    if q.get("write", True):
        out.update(order_write(label))
    return out


ORDERS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "runs", "video-teardown", "_work")


def order_from_swipe(q, brand, avatar, product):
    """An order on one of our teardowns: a new piece from that swipe (video-writing run.py's own fork: the record is
    copied, the media linked, nothing torn down again), the order's picks on it, then the writing starts. The swipe is
    the backbone; a story preset, when picked, rides on top."""
    import importlib.util
    import time as _t
    src = os.path.join(ORDERS, re.sub(r"[^A-Za-z0-9._-]", "", str(q["swipe"])))
    if not os.path.isfile(os.path.join(src, "run.json")):
        return {"ok": False, "error": "no teardown called " + str(q["swipe"])}
    if not (brand and avatar and product):
        return {"ok": False, "error": "an order needs a brand, avatar and product"}
    label = "order-%s-%s-%s" % (brand, re.sub(r"[^a-z0-9-]", "", str(q.get("script") or "swipe")), _t.strftime("%Y%m%d-%H%M%S"))
    mp = os.path.join(os.path.dirname(HERE), "video-writing", "machine")
    if mp not in sys.path:
        sys.path.append(mp)                     # fork reads its own neighbours (writing_result)
    spec = importlib.util.spec_from_file_location("vw_run", os.path.join(mp, "run.py"))
    vw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vw)
    d = str(vw.fork(src, label))
    st = json.load(open(os.path.join(d, "run.json")))
    combo = {k: q.get(k) for k in ("source", "swipe", "script", "preset", "look", "hook", "seconds", "tool") if q.get(k)}
    st.update(brand=brand, product=product, combo=combo, target_seconds=q.get("seconds"),
              declared_audience=dict(st.get("declared_audience") or {}, avatar=avatar))
    if not (st.get("writing_lane") or {}).get("lane"):
        # every swipe is matched with a winner first (owner, 2026-11-23): the writing runs the match (stage 2w) and
        # waits for the owner's pick on this board
        st["writing_lane"] = {"lane": "winner", "winner": None, "set": _t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                              "why": "an order on this swipe: matched with a winner, the owner picks"}
    json.dump(st, open(os.path.join(d, "run.json"), "w"), indent=1, ensure_ascii=False)
    if q.get("preset"):
        mp = os.path.join(os.path.dirname(HERE), "video-writing", "machine")
        if mp not in sys.path:
            sys.path.append(mp)
        import writing_v2 as W
        W.name_preset(d, re.sub(r"[^a-z0-9-]", "", q["preset"]))
    out = {"ok": True, "label": label, "run": "runs/video-teardown/_work/" + label, "combo": combo,
           "next": "set up on the swipe"}
    if q.get("write", True):
        out.update(order_write(label))
    return out


def order_write(label):
    """Start the writing chain on an order in the background (owner, 2026-11-21: "run whatever needs to run"). The log
    and the process id sit in the order's own folder; the board reads them through /api/orders."""
    d = os.path.join(ORDERS, label)
    if not os.path.isfile(os.path.join(d, "run.json")):
        return {"writing": "no such order"}
    if order_alive(d):
        return {"writing": "already writing"}
    os.makedirs(os.path.join(d, "order"), exist_ok=True)
    log = open(os.path.join(d, "order", "writing.log"), "ab")
    pr = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(HERE), "video-writing", "machine", "run.py"), d],
                          stdout=log, stderr=subprocess.STDOUT, cwd=os.path.dirname(os.path.dirname(HERE)),
                          start_new_session=True)
    open(os.path.join(d, "order", "pid"), "w").write(str(pr.pid))
    return {"writing": "started", "next": "writing now: the brief lands on the board when it is done"}


def winner_pick(label, q):
    """The owner's winner for a swipe order (stage 2w ranked them; nothing is picked by the chain), then the writing
    starts. A run already written gets a new run beside it, written on the pick."""
    import importlib.util
    mp = os.path.join(os.path.dirname(HERE), "video-writing", "machine", "winner_match.py")
    spec = importlib.util.spec_from_file_location("vs_winner_match", mp)
    wm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wm)
    win = re.sub(r"[^A-Za-z0-9._-]", "", str(q.get("winner") or ""))
    try:
        got = wm.pick_winner(label, win, str(q.get("why") or "picked on the Studio board"))
    except SystemExit as e:
        return {"ok": False, "error": str(e)}
    out = {"ok": True, "run": got["run"], "new": got["new"]}
    if got["run"].startswith("order-") or got["run"] == label:
        out.update(order_write(got["run"]))
    else:
        out["writing"] = "picked: start its writing with video-writing run.py " + got["run"]
    return out


def order_alive(d):
    try:
        pid = int(open(os.path.join(d, "order", "pid")).read().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


WRITING_STEPS = [("stage2w", "Winner"), ("stage3", "Injection"), ("stage4i", "Idea"), ("stage4v2a", "Hooks"), ("stage4v2b", "Script"),
                 ("stage4e", "Audit"), ("stage4g", "Spice"), ("stage5", "Brief")]


def orders_list():
    """Every order on this machine, newest first: its combo, where the writing is, and whether the brief is ready."""
    out = []
    for d in sorted(glob.glob(os.path.join(ORDERS, "order-*")), reverse=True):
        try:
            st = json.load(open(os.path.join(d, "run.json")))
        except (OSError, ValueError):
            continue
        stages = st.get("stages") or {}
        steps = [{"name": n, "status": (stages.get(k) or {}).get("status") or "waiting"} for k, n in WRITING_STEPS]
        brief = os.path.isfile(os.path.join(d, "stages", "5-brief.md"))
        res = {}
        if os.path.isfile(os.path.join(d, "writing-result.json")):
            try:
                res = json.load(open(os.path.join(d, "writing-result.json")))
            except ValueError:
                res = {}
        alive = order_alive(d) or any(x["status"] == "running" for x in steps)
        held = next((s for k, s in ((k, stages.get(k) or {}) for k, _ in WRITING_STEPS) if s.get("status") in ("held", "error")
                     and "dry run" not in str(s.get("error", ""))), None)
        state = ("writing" if alive else "pick a winner" if st.get("waiting_for") == "winner pick" else "brief ready" if brief and res.get("accepted") else
                 "brief written" if brief else "held" if held else
                 "set up" if not any(x["status"] == "done" for x in steps) else "stopped")
        tail = ""
        if os.path.isfile(os.path.join(d, "order", "writing.log")):
            lines = [x for x in open(os.path.join(d, "order", "writing.log"), errors="replace").read().splitlines() if x.strip()]
            tail = lines[-1][:200] if lines else ""
        match = None
        if os.path.isfile(os.path.join(d, "winner-match.json")):
            try:
                m = json.load(open(os.path.join(d, "winner-match.json")))
                match = {"verdict": m.get("verdict"), "pick": (st.get("writing_lane") or {}).get("winner")
                         if (st.get("writing_lane") or {}).get("picked_by") else m.get("pick"),
                         "top": [{k: x.get(k) for k in ("winner", "label", "score", "fit", "reason")} for x in
                                 (m.get("winners") or [])[:3]]}
            except ValueError:
                match = None
        out.append({"match": match, "waiting_pick": st.get("waiting_for") == "winner pick",
                    "label": os.path.basename(d), "brand": st.get("brand"), "product": st.get("product"),
                    "avatar": (st.get("declared_audience") or {}).get("avatar"), "combo": st.get("combo") or {},
                    "opened": st.get("opened"), "state": state, "steps": steps, "brief": brief,
                    "accepted": bool(res.get("accepted")), "why": (held or {}).get("error", "")[:240], "log": tail,
                    "cost": round(sum(float((stages.get(k) or {}).get("cost_usd") or 0) for k, _ in WRITING_STEPS), 2)})
    return {"orders": out}


def order_script(d):
    """The brief's scene block as a plain script: one line per scene, its time, what happens, the words."""
    f = os.path.join(d, "stages", "5-brief.md")
    blocks = re.findall(r"```json\s*\n(.*?)\n```", open(f).read(), re.S) if os.path.isfile(f) else []
    try:
        doc = json.loads(blocks[-1]) if blocks else {}
    except ValueError:
        doc = {}
    lines = []
    for i, sc in enumerate(doc.get("scenes") or []):
        words = sc.get("voice") or sc.get("words") or sc.get("lyrics") or ""
        if isinstance(words, list):
            words = " / ".join(str(w.get("line") if isinstance(w, dict) else w) for w in words)
        what = sc.get("happens") or sc.get("action") or ""
        lines.append("%s. %s%s" % (i + 1, what, (" — " + str(words)) if words else ""))
    return "\n".join(lines)


def order_handoff(label):
    """What to paste into Higgsfield for this order's tool: the tool's own line with our script as the film's script
    (Drama Ads makes a given script as written). Our writing; Higgsfield's production."""
    d = os.path.join(ORDERS, label)
    st = json.load(open(os.path.join(d, "run.json")))
    combo, script = st.get("combo") or {}, order_script(d)
    tool = combo.get("tool") or ""
    brand = (st.get("brand") or "").upper()
    product = (st.get("product") or "").replace("-", " ")
    if (st.get("story_preset") or {}).get("id") and (tool.startswith("Drama") or not tool):
        cat = os.path.join(os.path.dirname(HERE), "workflow-teardown", "sources", "higgsfield", "drama-ads", "catalog",
                           st["story_preset"]["id"] + ".md")
        card = ""
        if os.path.isfile(cat):
            m = re.search(r'"id":\s*"([0-9a-f-]{36})"', open(cat).read())
            card = m.group(1) if m else ""
        head = "/drama-ads card %s «%s»; mode: ask; idea: " % (card, st["story_preset"]["name"])
        return head + ("Make it as this script, written for %s's %s, %s seconds. Keep every line word for word:\n%s"
                       % (brand, product, combo.get("seconds") or "", script))
    return "%s for %s %s, %s seconds, made as this script, every line word for word:\n%s" % (
        tool or "Make this ad", brand, product, combo.get("seconds") or "", script)


def order_page(label):
    d = os.path.join(ORDERS, label)
    f = os.path.join(d, "stages", "5-brief.md")
    if not os.path.isfile(f):
        return None
    import html as _h
    st = json.load(open(os.path.join(d, "run.json")))
    combo = " · ".join(str(v) for v in (st.get("combo") or {}).values() if v)
    hand = order_handoff(label)
    return ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>%s</title><style>body{font:14px/1.5 -apple-system,system-ui,sans-serif;max-width:900px;margin:0 auto;"
            "padding:24px 16px;background:#f3f4f7;color:#15171d}h1{font-size:22px;margin:0 0 4px}.c{font:12px ui-monospace,"
            "Menlo,monospace;color:#5d6372}.box{background:#15171d;color:#f3f4f7;border-radius:12px;padding:16px;margin:16px 0}"
            ".box pre{white-space:pre-wrap;font:13px/1.45 ui-monospace,Menlo,monospace;margin:8px 0}button{background:#d6336c;"
            "color:#fff;border:0;border-radius:999px;padding:8px 14px;font-weight:600;cursor:pointer}pre.brief{white-space:"
            "pre-wrap;background:#fff;border:1px solid #dfe2ea;border-radius:12px;padding:16px;font:12.5px/1.5 ui-monospace,"
            "Menlo,monospace}</style><h1>%s</h1><div class=c>%s</div><div class=box><b>Paste into Higgsfield</b><pre id=h>%s"
            "</pre><button onclick=\"navigator.clipboard.writeText(document.getElementById('h').textContent).then(()=>"
            "this.textContent='Copied ✓')\">Copy</button></div><h2 style='font-size:16px'>The brief</h2><pre class=brief>%s</pre>"
            % (_h.escape(label), _h.escape(label), _h.escape(combo), _h.escape(hand), _h.escape(open(f).read())))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        got = app_for(self)
        if got:
            return proxy(self, *got)
        u = urlparse(self.path)
        parts = [unquote(p) for p in u.path.strip("/").split("/") if p]
        if parts in (["desk"], ["next"]) or parts[:2] == ["api", "desk"]:    # the workflow desk + the new Studio
            import workflow_desk as WD
            return WD.handle(self, "GET", parts, u.query, None)
        if not parts or parts == ["studio"]:
            return self.send(200, open(os.path.join(HERE, "studio.html"), "rb").read(), "text/html; charset=utf-8")
        if len(parts) == 2 and parts[0] == "creator-hub" and re.fullmatch(r"[a-z0-9-]+", parts[1]):
            # the creator hub with every outstanding brief (drafts waiting for a yes, and open ones), built fresh (16 Nov)
            import creator_lane as CL
            hub = CL.WS / "lab" / "owner" / "creator-machine" / "machine" / "hub.py"
            subprocess.run([sys.executable, str(hub), "--brand", parts[1], "--preview"], cwd=str(hub.parent),
                           capture_output=True, text=True, timeout=120)
            f = CL.WS / "runs" / "creator-machine" / parts[1] / "hub" / "preview.html"
            if not f.is_file():
                return self.send(404, {"error": "no creator hub for " + parts[1]})
            return self.send(200, f.read_bytes(), "text/html; charset=utf-8")
        if len(parts) == 3 and parts[0] == "handoff" and parts[2] == "TIMELINE.html":
            ho = load(os.path.join(bdir(parts[1]), "maker-pack.json")) if os.path.exists(os.path.join(bdir(parts[1]), "maker-pack.json")) else {}
            f = os.path.join(ho.get("folder") or "", "TIMELINE.html")
            if not os.path.isfile(f):
                return self.send(404, {"error": "no hand-off timeline for " + parts[1]})
            return self.send(200, open(f, "rb").read(), "text/html; charset=utf-8")
        if parts == ["canvas"]:
            return self.send(200, open(os.path.join(HERE, "canvas.html"), "rb").read(), "text/html; charset=utf-8")
        if parts == ["higgsfield"]:   # every Higgsfield tool, one shelf per kind of video (21 Nov)
            return self.send(200, open(os.path.join(HERE, "higgsfield", "higgsfield.html"), "rb").read(), "text/html; charset=utf-8")
        if len(parts) == 2 and parts[0] == "swipe-poster":   # a teardown's cover, for the order board's swipe row
            f = os.path.join(ORDERS, re.sub(r"[^A-Za-z0-9._-]", "", parts[1]), "poster.jpg")
            return self.file(f) if os.path.isfile(f) else self.send(404, {"error": "no cover"})
        if parts == ["api", "orders"]:      # every order and where its writing is (21 Nov)
            return self.send(200, orders_list())
        if len(parts) == 2 and parts[0] == "orders":   # one order's brief and its Higgsfield paste
            page = order_page(re.sub(r"[^a-z0-9-]", "", parts[1]))
            return self.send(200, page.encode("utf-8"), "text/html; charset=utf-8") if page else self.send(404, {"error": "no brief yet"})
        if parts == ["options"]:   # Creative Options: every way to make an ad, built fresh from the files (21 Nov)
            sys.path.insert(0, os.path.join(os.path.dirname(HERE), "creative-controls", "page"))
            import build_preset_page as BP
            return self.send(200, BP.page_html().encode("utf-8"), "text/html; charset=utf-8")
        if parts == ["higgsfield", "catalog.json"]:
            return self.send(200, open(os.path.join(HERE, "higgsfield", "catalog.json"), "rb").read(), "application/json")
        if parts == ["higgsfield", "recipes.json"]:   # the Recipes shelf: components/workflow-teardown/index.json (21 Nov)
            f = os.path.join(os.path.dirname(HERE), "workflow-teardown", "index.json")
            if not os.path.isfile(f):
                return self.send(404, {"error": "no workflow-teardown index yet"})
            return self.send(200, open(f, "rb").read(), "application/json")
        if parts[:2] == ["api", "next"] and len(parts) == 3:
            return self.send(200, next_state(parts[2]))
        if parts[:2] == ["api", "song"] and len(parts) == 3:        # a sung ad's song card and Song track
            return self.send(200, song_state(parts[2]))
        if parts[:2] == ["api", "song"] and len(parts) == 4 and parts[3] == "song.mp3":
            _, run = song_of(parts[2])
            f = os.path.join(str(run), "song", "song.mp3") if run else ""
            return self.file(f) if f and os.path.isfile(f) else self.send(404, {"error": "no song yet"})
        if parts[:2] == ["api", "handoff-job"] and len(parts) == 3:
            j = job_by_id(parts[2])
            return self.send(200, j) if j else self.send(404, {"error": "no such job"})
        if parts == ["api", "menu"]:
            return self.send(200, menu())
        if parts == ["api", "clipmodels"]:
            import gen_ref as GR
            return self.send(200, {"models": GR.clip_choices()})
        if parts[:2] == ["api", "clip"] and len(parts) == 4:
            return self.send(200, clip_reference(parts[2], parts[3]))
        if parts[:2] == ["api", "shotframe"] and len(parts) == 5:
            try:
                return self.file(shot_frame(parts[2], parts[3], parts[4]))
            except Exception as e:  # noqa: BLE001
                return self.send(404, {"error": str(e)})
        if parts[:2] == ["api", "motion"] and len(parts) == 4:
            return self.send(200, motion_state(parts[2], parts[3]))
        if parts[:2] == ["api", "direction"] and len(parts) == 4:
            return self.send(200, direction_state(parts[2], parts[3]))
        if parts[:2] == ["api", "swipeshot"] and len(parts) == 5 and re.fullmatch(r"K\d{1,3}", parts[4]):
            # the swipe shot a production row re-makes: its middle still from the teardown's frame map
            d = take_dir(parts[2], parts[3])
            try:
                import production_inject as PI
                src = PI.run_of(d, load(os.path.join(d, "take.json"))) if d else None
            except Exception:  # noqa: BLE001
                src = None
            f = os.path.join(str(src), "framemap", "shots", parts[4] + "-mid.jpg") if src else ""
            return self.file(f) if f and os.path.isfile(f) else self.send(404, {"error": "no still for that shot"})
        if parts[:2] == ["api", "chainrun"] and len(parts) == 3:    # the production chain's run, read-only (chain_view)
            import chain_view as CV
            bd = bdir(parts[2])
            if not bd or not os.path.isdir(bd):
                return self.send(404, {"error": "no such production"})
            return self.send(200, CV.view(parts[2], load(os.path.join(bd, "brief.json"))))
        if parts[:2] == ["api", "chainpic"] and len(parts) == 4:    # the run's own start picture for a frame
            import chain_view as CV
            bd = bdir(parts[2])
            if not bd or not os.path.isdir(bd):
                return self.send(404, {"error": "no such production"})
            r, run, _ = CV.run_of(load(os.path.join(bd, "brief.json")))
            f = CV.pictures_of(run).get(parts[3]) if run else None
            return self.file(f) if f else self.send(404, {"error": "no picture for that frame yet"})
        if parts[:2] == ["api", "chaincast"] and len(parts) == 4:   # a cast member's headshot from our cast bank
            import chain_view as CV
            bd = bdir(parts[2])
            r, _, _ = CV.run_of(load(os.path.join(bd, "brief.json"))) if bd and os.path.isdir(bd) else (None, None, None)
            f = CV.headshot((r or {}).get("brand"), parts[3]) if r else None
            return self.file(f) if f else self.send(404, {"error": "no headshot"})
        if parts[:2] == ["api", "chainswipe"] and len(parts) == 4:  # the swipe shot a planned shot builds on
            import chain_view as CV
            bd = bdir(parts[2])
            f = CV.swipe_still(load(os.path.join(bd, "brief.json")), parts[3]) if bd and os.path.isdir(bd) else None
            return self.file(f) if f else self.send(404, {"error": "no still for that swipe shot"})
        if parts[:2] == ["api", "checks"] and len(parts) == 3:      # every check the production ran (checks_board.py)
            import checks_board as CB
            bd = bdir(parts[2])
            if not bd or not os.path.isdir(bd):
                return self.send(404, {"error": "no such production"})
            return self.send(200, CB.checks(parts[2], bd))
        if parts[0] == "castfile" and len(parts) >= 4:               # a cast's pictures, for the Checks panel
            import checks_board as CB
            f = (CB.CASTING / parts[1] / "casting" / os.path.join(*parts[2:])).resolve()
            if CB.CASTING.resolve() in f.parents and f.is_file():
                return self.file(str(f))
            return self.send(404, {"error": "no such cast file"})
        if parts[:2] == ["api", "productions"] and len(parts) == 2:
            return self.send(200, {"productions": link_productions(productions())})
        if parts[:2] == ["api", "versions"] and len(parts) == 3:
            return self.send(200, {"versions": versions(parts[2])})
        if parts[:2] == ["api", "covers"] and len(parts) == 3:       # the cover stage: what it picked and why
            try:
                return self.send(200, CS.state(parts[2], Path(bdir(parts[2]))))
            except (Exception, SystemExit) as e:  # noqa: BLE001 — the board says so; the Studio stays up
                return self.send(500, {"error": "the covers could not be read: %s" % (str(e) or type(e).__name__)})
        if parts[0] == "coverswipe" and len(parts) == 2:              # a swipe's picture from the cover index
            p = CS.swipe_picture(parts[1])
            return self.file(p) if p else self.send(404, {"error": "no such swipe picture"})
        if parts[0] == "gen" and len(parts) >= 2:
            p = os.path.realpath(os.path.join(GEN, *parts[1:]))
            if not p.startswith(os.path.realpath(GEN)) or not os.path.isfile(p):
                return self.send(404, {"error": "not found"})
            return self.file(p)
        if parts[:2] == ["api", "brief"] and len(parts) == 3:
            return self.send(200, brief_state(parts[2]))
        if parts[0] == "files" and len(parts) >= 3:
            p = os.path.realpath(os.path.join(BRIEFS, *parts[1:]))
            if not p.startswith(os.path.realpath(BRIEFS)) or not os.path.isfile(p):
                return self.send(404, {"error": "not found"})
            return self.file(p)
        self.send(404, {"error": "not found"})

    def _other(self):
        got = app_for(self)
        if got:
            return proxy(self, *got)
        self.send(405, {"error": "method not allowed"})

    do_PUT = do_DELETE = do_PATCH = _other

    def file(self, p):
        ctype = {"mp4": "video/mp4", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "mp3": "audio/mpeg",
                 "json": "application/json"}.get(p.rsplit(".", 1)[-1].lower(), "application/octet-stream")
        size = os.path.getsize(p)
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else 0
            end = int(b) if b else size - 1
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 16, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

    def do_POST(self):
        got = app_for(self)
        if got:
            return proxy(self, *got)
        u = urlparse(self.path)
        parts = [unquote(p) for p in u.path.strip("/").split("/") if p]
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0) or 0)
        if parts[:2] == ["api", "desk"]:                        # the workflow desk (workflow_desk.py)
            import workflow_desk as WD
            return WD.handle(self, "POST", parts, u.query, body)
        try:
            if len(parts) == 3 and parts[:2] == ["api", "handoff"]:
                q = json.loads(body or b"{}") or {}                      # the lane picked at Produce (16 Nov)
                # a lane picked at Produce is the person's; none sent = the chain's call (lane.py), never an assumed "ai"
                return self.send(200, handoff_start(parts[2], q.get("lane") if q.get("lane") in ("ai", "mix", "real", "creator") else None))
            if parts == ["api", "order"]:      # Creative Options: an order becomes a writing run and the writing starts (21 Nov)
                return self.send(200, order_start(json.loads(body or b"{}") or {}))
            if len(parts) == 3 and parts[:2] == ["api", "winner-pick"]:   # the owner picks the winner, writing starts
                return self.send(200, winner_pick(re.sub(r"[^A-Za-z0-9._-]", "", parts[2]), json.loads(body or b"{}") or {}))
            if len(parts) == 3 and parts[:2] == ["api", "order-write"]:   # (re)start the writing on an order
                return self.send(200, order_write(re.sub(r"[^a-z0-9-]", "", parts[2])))
            if len(parts) == 3 and parts[:2] == ["api", "next"]:
                q = json.loads(body or b"{}") or {}                      # {"through": true}: one go (2026-11-20)
                return self.send(200, next_start(parts[2], through=bool(q.get("through"))))
            if len(parts) == 3 and parts[:2] == ["api", "remove-idea"]:     # Remove / Put back (owner, 20 Nov)
                try:
                    return self.send(200, remove_idea(parts[2], bool((json.loads(body or b"{}") or {}).get("undo"))))
                except ValueError as e:
                    return self.send(400, {"error": str(e)})
            if len(parts) == 4 and parts[:2] == ["api", "song"] and parts[3] == "take":   # a take made in Suno
                try:
                    return self.send(200, song_take_add(parts[2], self.headers.get("X-Name") or "", body))
                except ValueError as e:
                    return self.send(409, {"error": str(e)})
            if len(parts) == 3 and parts[:2] == ["api", "covers"]:    # make the covers now (the same Next step job)
                if not CS.on():
                    return self.send(409, {"error": "the cover stage is switched off (cover-stage.json)"})
                try:
                    shut = CS.closed(parts[2], Path(bdir(parts[2])))
                except (Exception, SystemExit) as e:  # noqa: BLE001
                    shut = "the ad's card could not be read (%s)" % (str(e) or type(e).__name__)
                if shut:                                               # an approved, live or covered card is left alone
                    return self.send(409, {"error": "no covers are made for this ad: " + shut})
                return self.send(200, next_start(parts[2], "covers"))
            if len(parts) == 5 and parts[:2] == ["api", "direction"]:
                try:
                    return self.send(200, direction_start(parts[2], parts[3], parts[4]))
                except RuntimeError as e:
                    return self.send(409, {"error": str(e)})
            if len(parts) == 5 and parts[:2] == ["api", "motion"]:
                n, s, act = parts[2], parts[3], parts[4]
                if act == "upload":
                    from urllib.parse import parse_qs
                    q = {k: v[0] for k, v in parse_qs(u.query).items()}
                    return self.send(200, motion_upload(n, s, q.get("name") or "phone.mp4", q.get("kind") or "phone", body))
                q = json.loads(body or b"{}")
                if act == "swipe":
                    swipe = _swipe_of(load(os.path.join(bdir(n), "brief.json")))
                    if not swipe:
                        return self.send(400, {"error": "this brief's swipe is not in its writing run"})
                    return self.send(200, motion_start(n, s, swipe, float(q.get("from") or 0), q.get("to") and float(q["to"]), "swipe"))
                if act == "approve":
                    return self.send(200, motion_approve(n, s, q.get("by")))
                if act == "program":
                    return self.send(200, motion_program(n, s))
            if len(parts) == 5 and parts[:2] == ["api", "scene"]:
                n, s, act = parts[2], parts[3], parts[4]
                if act == "run":
                    with LOCK:
                        if RUNNING.get((n, s)):
                            return self.send(409, {"error": "already running"})
                        RUNNING[(n, s)] = True
                    try:
                        return self.send(200, run_scene(n, s))
                    except SystemExit as e:      # a take the model refused (take.py stops with SystemExit): say so, don't drop the request
                        return self.send(200, {"ok": False, "refused": str(e)[:1200]})
                    finally:
                        RUNNING.pop((n, s), None)
                if act == "save":
                    wf = json.loads(body)
                    brief = load(os.path.join(bdir(n), "brief.json"))
                    take = brief["picks"][s]
                    wf["take"] = take
                    p = os.path.join(sdir(n, s), take + ".json")
                    before = load(p) if os.path.exists(p) else {}
                    for k in ("words_from", "words_unsent"):
                        if k in before and k not in wf:
                            wf[k] = before[k]
                    wf = push_wf_words(n, s, brief, before, wf)
                    save(p, wf)
                    return self.send(200, scene_state(n, s, brief))
                if act == "take":
                    return self.send(200, {"take": new_take(n, s)})
                if act == "pick":
                    take = json.loads(body)["take"]
                    brief = load(os.path.join(bdir(n), "brief.json"))
                    if not os.path.exists(os.path.join(sdir(n, s), take + ".json")):
                        return self.send(400, {"error": "no such take"})
                    brief["picks"][s] = take
                    save(os.path.join(bdir(n), "brief.json"), brief)
                    return self.send(200, scene_state(n, s, brief))
            if parts[:2] == ["api", "shot"] and len(parts) == 4 and parts[3] in ("pick", "take"):
                import gen_ref as GR                  # a person's clip-model pick for one AI shot, and a new take on it
                name, model = parts[2], json.loads(body or b"{}").get("model")
                if parts[3] == "pick":
                    r = GR.set_pick(name, model)
                    return self.send(200, {"name": name, "clip_model": r.get("clip_model") or GR.DEFAULT})
                with LOCK:
                    if MAKING.get(name):
                        return self.send(409, {"error": "a take of this shot is already being made"})
                    MAKING[name] = True
                try:
                    return self.send(200, GR.remake(name, model))
                except SystemExit as e:
                    return self.send(400, {"error": str(e)})
                finally:
                    MAKING.pop(name, None)
            if parts[:2] == ["api", "package"] and len(parts) == 3:
                return self.send(200, package(parts[2]))
            if parts[:2] == ["api", "hyperframes"] and len(parts) == 3:
                q = json.loads(body or b"{}")
                return self.send(200, open_in_hyperframes(parts[2], q.get("version")))
            if parts[:2] == ["api", "produce"] and len(parts) == 3 and re.fullmatch(r"(?:idea-|brief)\d+", parts[2]):
                q = json.loads(body or b"{}") or {}
                picked = q.get("cast") or {}                                     # the cast picked at Produce (16 Nov)
                extra = ["--cast", json.dumps(picked)] if isinstance(picked, dict) and picked else []
                if q.get("lane") in ("ai", "mix", "real"):                      # the lane picked at Produce
                    extra += ["--lane", q["lane"]]
                r = subprocess.run([sys.executable, os.path.join(HERE, "seed_from_brief.py"), parts[2]] + extra,
                                   capture_output=True, text=True, timeout=120)
                if r.returncode:
                    return self.send(500, {"error": (r.stderr or "could not set up production")[-300:]})
                return self.send(200, json.loads(r.stdout.strip().splitlines()[-1]))
        except Exception as e:  # shown on the canvas, never swallowed
            return self.send(500, {"error": str(e)})
        self.send(404, {"error": "not found"})


def main(argv):
    if not argv or argv[0] == "serve":
        port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8921
        print(f"Video Studio on http://127.0.0.1:{port} — the board at /board/, the approval page at /approve/")
        ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
    elif argv[0] == "run":
        print(json.dumps(run_scene(argv[1], argv[2]), indent=1))
    elif argv[0] == "package":
        print(json.dumps(package(argv[1]), indent=1))
    elif argv[0] == "next":
        run_next_job(argv[1])


if __name__ == "__main__":
    main(sys.argv[1:])
