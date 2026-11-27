#!/usr/bin/env python3
"""Make the AI shots: the Studio's AI-lane step starts the production chain's own command for the brief and shows the
chain's run. It holds no production logic (owner ruling, 20 Nov 2026: the Studio lives on the chain and visualises it;
the underlying technology does the work; every production moves through the process).

    the chain   components/video-production/machine/ai_lane.py <writing run> — elements, voice, storyboard, pictures
                from 3D set prints, the camera and motion plan per scene from the director's pick, the clip plan with
                that plan in every prompt, then the clips. A clip without its camera and motion plan is refused there.
    this step   starts that command (its dry run, or the live run on the stage's go), then reads `ai_lane.py status`
                and says each station on the Studio's loading screen: the pictures waiting for a 3D print, every
                scene's camera and motion plan, the clips made. A clip the chain made for exactly one scene is laid
                into that scene's picked take (one ffmpeg.trim, the take as it was kept as <take>.before-ai-shots.json)
                so the Studio shows and cuts it; a clip covering several scenes is the chain's, taken by the hand-off
                from its run.

SWITCH: ai-shots-stage.json beside this file: `dry_run` (true: the chain's dry run only, nothing is spent; the
default), `cap_credits` (passed to the live run: it refuses when its dry run's high quote is over it).
VIDEO_STUDIO_AI_SHOTS_DRY_RUN=1 forces a dry run. No brand, product or person is named here.

    python3 ai_shots.py <production dir> [--dry-run]
"""
import json
import re
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402

CONF = HERE / "ai-shots-stage.json"
DEFAULTS = {"cap_credits": 450, "dry_run": True}
LANE = ST.chain("video-production", "ai_lane")          # the chain's command; its stations are its own
STEPS = [(sid, name) for sid, name in LANE.STATIONS]


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {} if default is None else default


def conf():
    c = dict(DEFAULTS, **{k: v for k, v in _load(CONF).items() if not k.startswith("_")})
    if os.environ.get("VIDEO_STUDIO_AI_SHOTS_DRY_RUN") in ("1", "true", "yes"):
        c["dry_run"] = True
    return c


def _take_file(B, brief, s):
    return Path(B) / "scenes" / s / (((brief.get("picks") or {}).get(s) or "take-1") + ".json")


def _writing_run(brief):
    return brief.get("brief") or brief.get("run")


def chain(args):
    """The chain's command, as its own process: (exit code, output)."""
    p = subprocess.run([sys.executable, str(Path(LANE.__file__))] + [str(a) for a in args], capture_output=True,
                       text=True, cwd=str(Path(LANE.__file__).parent))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def chain_status(brief, runner=chain):
    """`ai_lane.py status` for this production's brief, or {} when the chain cannot read it."""
    run = _writing_run(brief)
    if not run:
        return {}
    rc, out = runner(["status", run])
    try:
        return json.loads(out[out.index("{"):]) if rc == 0 else {}
    except ValueError:
        return {}


def covered(st):
    """The scenes the chain has made a clip for: {scene: (call id, clip path, scenes)}. The chain's own per-scene file
    (media/<scene>.mp4, written by its hand-off to the edit: a scene cut over two calls joined, a call over two scenes
    cut at its scenes) comes first, so every scene shows; else the call's clip."""
    out = {}
    run = Path((st or {}).get("run") or ".")
    for c in (st or {}).get("calls") or []:
        for s in c.get("scenes") or []:
            per = run / "media" / (s + ".mp4")
            if per.is_file():
                out[s] = (c["id"], str(per), [s])
            elif c.get("clip") and s not in out:
                out[s] = (c["id"], str(run / c["clip"]), c.get("scenes") or [])
    return out


def edit_groups(brief, edit):
    """{Studio scene: [the chain's scene rows]}: each chain scene goes to the Studio scene of the same id, else to the
    Studio scene before it in play order (a scene the Studio holds as part of its neighbour, a split's second half)."""
    order = list(brief.get("order") or [])
    out, cur = {}, None
    for r in edit.get("scenes") or []:
        if r["scene"] in order:
            cur = r["scene"]
        if cur:
            out.setdefault(cur, []).append(r)
    return out


def lay_edit(B, brief, s, rows, run):
    """THE CHAIN'S CUT INTO THE STUDIO SCENE (2026-11-20): the scene's take becomes one ffmpeg.trim per chain scene it
    holds (the chain's edit/<scene>.mp4: picture, a split stacked) and one voice.read of their joined voice (the
    chain's own: the clip's lip-synced sound, or the locked read as voice-over), with its words for the captions. The
    take as it was is kept beside it as <take>.before-ai-shots.json. Display wiring only: nothing is made."""
    import subprocess
    run = Path(run)
    f = _take_file(B, brief, s)
    wf = _load(f)
    keep = f.with_name(f.stem + ".before-ai-shots.json")
    if not keep.exists():
        keep.write_text(json.dumps(wf, indent=1, ensure_ascii=False))
    vdir = Path(B) / "voice" / "chain"
    vdir.mkdir(parents=True, exist_ok=True)
    wav = vdir / (s + ".wav")
    parts, words, at, texts, marks = [], [], 0.0, [], []
    for r in rows:
        rw = [dict(w, start=round(w["start"] + at, 3), end=round(w["end"] + at, 3))
              for w in (_load(run / r["words"]).get("words") or [])]
        for o in r.get("overlays") or []:            # the brief's editor text and arrows, timed to their words
            t = land_at(rw, o.get("at_words"))
            if t is not None:
                marks.append(dict(o, t=t))
        if r.get("voice"):
            parts.append("[%d:a]apad=whole_dur=%.3f,atrim=duration=%.3f[a%d]" % (len(parts), r["seconds"], r["seconds"],
                                                                                len(parts)))
        words += [dict(w, start=round(w["start"] + at, 3), end=round(w["end"] + at, 3))
                  for w in (_load(run / r["words"]).get("words") or [])]
        texts.append(r.get("text") or "")
        at += float(r["seconds"])
    srcs = [r for r in rows if r.get("voice")]
    if srcs:
        cmd = ["ffmpeg", "-v", "error", "-y"]
        for r in srcs:
            cmd += ["-i", str(run / r["voice"])]
        cmd += ["-filter_complex", ";".join(parts) + ";" + "".join("[a%d]" % i for i in range(len(srcs)))
                + "concat=n=%d:v=0:a=1[a]" % len(srcs), "-map", "[a]", "-ac", "2", "-ar", "48000", str(wav)]
        subprocess.run(cmd, check=True)
    (vdir / (s + ".words.json")).write_text(json.dumps({"words": words}, ensure_ascii=False))
    rp = Path(B) / "voice" / "reads.json"
    reads = _load(rp)
    reads.setdefault("lines", {})[s] = {"text": " ".join(t for t in texts if t), "words": words,
                                        "from": "the production chain's own voice (edit_scenes.py)"}
    rp.write_text(json.dumps(reads, indent=1, ensure_ascii=False))
    steps = [{"id": "voice", "tool": "voice.read", "model": "the production chain", "prompt": None, "seed": None,
              "inputs": {"file": "voice/chain/%s.wav" % s}, "params": {"speaker": "chain", "tail": 0},
              "note": "the chain's own voice for this scene (edit_scenes.py)"}] if srcs else []
    sources = dict(wf.get("sources") or {})
    for r in rows:
        slot = "chain-" + r["scene"]
        steps.append({"id": slot, "tool": "ffmpeg.trim", "model": None, "prompt": None, "seed": None,
                      "inputs": {"source": "slot:" + slot, "in": 0.0, "out": float(r["seconds"])},
                      "params": {"weight": float(r["seconds"])},
                      "note": "the chain's scene %s (%s)" % (r["scene"], r.get("voice_from") or "")})
        sources[slot] = {"file": Path(r["file"]).name, "drive_location": str(run / r["file"]), "generated": True,
                         "made_from": r["scene"], "call": "edit_scenes"}
    steps += [x for x in wf.get("steps") or [] if x.get("tool") not in ("gen.shot", "voice.read", "voice.ai", "ffmpeg.trim",
                                                                         "hyperframes.card")]
    if marks:
        proj = Path(B) / "scenes" / s / "card"
        overlay_card(proj, marks, at, "%s-%s-chain-card" % (Path(B).name, s))
        steps.append({"id": "card", "tool": "hyperframes.card", "model": None, "prompt": None, "seed": None,
                      "inputs": {"project": "card"}, "params": {"in": 0.0, "out": round(at, 3)},
                      "note": "the brief's on-screen text and arrows, each on its words (edit_scenes overlays)"})
    f.write_text(json.dumps(dict(wf, steps=steps, sources=sources), indent=1, ensure_ascii=False))
    return f


def _norm_words(t):
    return [w for w in re.sub(r"[^a-z0-9' ]+", " ", str(t or "").lower()).split() if w]


def land_at(words, at_words):
    """The second the words `at_words` start in a scene's laid words, or None."""
    want = _norm_words(at_words)[:4]
    got, at = [], []                     # every token of every word ("60-Day" is two), with the word it came from
    for w in words:
        for tok in _norm_words(w.get("w")):
            got.append(tok)
            at.append(w)
    for i in range(len(got) - len(want) + 1):
        if want and got[i:i + len(want)] == want:
            return float(at[i]["start"])
    return None


TEXT_Y = 0.17     # editor text above the heads, inside the safe zone (a centred pill sat beside a face, 0380 S10)
ARROW_Y = 0.74    # the arrow low in the frame, pointing down at the link below the video


def overlay_card(proj, marks, dur, cid):
    """A HyperFrames card (the Studio's hyperframes.card contract: assets/bg.mp4 under it, {{DUR}}) carrying the brief's
    editor text and arrows: the texts that land together show together, each group until the next lands; an arrow
    points down low in the frame from its words to the end. White type on a dark pill, above the heads, in the safe zone."""
    import html as H
    proj = Path(proj)
    (proj / "assets").mkdir(parents=True, exist_ok=True)
    (proj / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components",
                                                                 "assets": "assets"}}))
    (proj / "meta.json").write_text(json.dumps({"id": cid, "name": cid}))
    texts = sorted([m for m in marks if m.get("kind") == "text"], key=lambda m: m["t"])
    times = sorted({m["t"] for m in texts})
    groups = []
    for i, t in enumerate(times):
        end = times[i + 1] if i + 1 < len(times) else dur
        items = [m for m in texts if m["t"] == t]
        groups.append((t, end, items, TEXT_Y))
    els, js = [], []
    for g, (t, end, items, y) in enumerate(groups):
        pills = "".join('<div class="pill">%s</div>' % H.escape(m["text"]) for m in items)
        els.append('<div id="g%d" class="grp" style="top:%dpx">%s</div>' % (g, int(1920 * y), pills))
        js.append('tl.fromTo("#g%d",{opacity:0,scale:.92},{opacity:1,scale:1,duration:.12},%.3f);'
                  'tl.to("#g%d",{opacity:0,duration:.08},%.3f);' % (g, t, g, max(t + 0.2, end - 0.08)))
    for k, a in enumerate(m for m in marks if m.get("kind") == "arrow"):
        y = int(1920 * ARROW_Y)
        els.append('<div id="a%d" class="arrow" style="top:%dpx">&#8595;</div>' % (k, y))
        js.append('tl.fromTo("#a%d",{opacity:0,y:-20},{opacity:1,y:0,duration:.15},%.3f);' % (k, a["t"]))
    page = ("<!doctype html>\n<html><head><meta charset=\"utf-8\"><script src=\"https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js\"></script>\n"
            "<style>html,body{margin:0;background:#000}#stage{position:relative;width:1080px;height:1920px;overflow:hidden;"
            "background:#000;font-family:-apple-system,'SF Pro Display','Helvetica Neue',Helvetica,Arial,sans-serif}"
            "#bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}"
            ".grp{position:absolute;left:108px;right:108px;display:flex;flex-direction:column;align-items:center;gap:18px;opacity:0}"
            ".pill{background:rgba(0,0,0,.72);color:#fff;font-weight:800;font-size:58px;line-height:1.12;text-align:center;"
            "padding:16px 30px;border-radius:22px;max-width:864px}"
            ".arrow{position:absolute;left:0;right:0;text-align:center;color:#fff;font-size:150px;font-weight:900;opacity:0;"
            "text-shadow:0 6px 24px rgba(0,0,0,.55)}</style></head><body>\n"
            "<div id=\"stage\" data-composition-id=\"__CID__\" data-start=\"0\" data-width=\"1080\" data-height=\"1920\" "
            "data-fps=\"30\" data-duration=\"{{DUR}}\">\n"
            "<video id=\"bg\" class=\"clip\" data-start=\"0\" data-duration=\"{{DUR}}\" data-track-index=\"1\" "
            "data-timeline-label=\"the scene\" src=\"assets/bg.mp4\" data-media-start=\"0\" muted playsinline></video>\n"
            "<div class=\"clip\" data-start=\"0\" data-duration=\"{{DUR}}\" data-track-index=\"2\" "
            "data-timeline-label=\"editor text and arrows\" style=\"position:absolute;inset:0\">__ELS__</div>\n"
            "<script>\nconst tl = gsap.timeline({ paused: true });\n__JS__\n"
            "window.__timelines = window.__timelines || {};\nwindow.__timelines[\"__CID__\"] = tl;\n</script>\n</div></body></html>\n"
            ).replace("__CID__", cid).replace("__ELS__", "".join(els)).replace("__JS__", "\n".join(js))
    (proj / "index.template.html").write_text(page)
    return proj


def lay_made(B, brief, st, probe=None):
    """Every scene the chain has already made laid into its picked take (no chain run, nothing spent): [scenes]. The
    chain's cut (edit/EDIT.json) when it has one, else each one-scene clip."""
    run = Path((st or {}).get("run") or "")
    edit = _load(run / "edit" / "EDIT.json") if st and st.get("run") else {}
    if edit.get("scenes"):
        laid = []
        for s, rows in edit_groups(brief, edit).items():
            if any(x.get("tool") == "gen.shot" for x in _load(_take_file(B, brief, s)).get("steps") or []):
                lay_edit(B, brief, s, rows, run)
                laid.append(s)
        return laid
    made = []
    for s, (call_id, clip, scenes) in covered(st).items():
        if len(scenes) == 1 and s in (brief.get("order") or []) and any(
                x.get("tool") == "gen.shot" for x in _load(_take_file(B, brief, s)).get("steps") or []):
            lay(B, brief, s, clip, call_id, probe or _probe)
            made.append(s)
    return made


def scenes_due(B, brief, st=None):
    """The scenes whose picked take still holds AI shots (gen.shot steps) and that the chain has not made a clip for,
    in the production's order. `st` is the chain's status (read when not given and a scene still holds AI shots)."""
    holding = [s for s in brief.get("order") or []
               if any(x.get("tool") == "gen.shot" for x in _load(_take_file(B, brief, s)).get("steps") or [])]
    if not holding:
        return []
    made = covered(chain_status(brief) if st is None else st)
    # a scene still holding AI shots is due when the chain has no clip for it, or has one ready to lay into it (its own
    # one-scene file): the step lays it, nothing spent; a clip over several scenes with no per-scene file is the chain's
    return [s for s in holding if s not in made or len(made[s][2]) == 1]


def _probe(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    return round(float(r.stdout.strip()), 3)


def lay(B, brief, s, made, call_id, probe=_probe):
    """The chain's clip into the scene's picked take: its gen.shot steps become one ffmpeg.trim of the clip, at the
    first shot's place; the take as it was is kept beside it as <take>.before-ai-shots.json. Display wiring only."""
    f = _take_file(B, brief, s)
    wf = _load(f)
    keep = f.with_name(f.stem + ".before-ai-shots.json")
    if not keep.exists():
        keep.write_text(json.dumps(wf, indent=1, ensure_ascii=False))
    shot_ids = [x["id"] for x in wf.get("steps") or [] if x.get("tool") == "gen.shot"]
    steps, laid = [], False
    for x in wf.get("steps") or []:
        if x.get("tool") != "gen.shot":
            steps.append(x)
        elif not laid:
            steps.append({"id": "ai-take", "tool": "ffmpeg.trim", "model": None, "prompt": None, "seed": None,
                          "inputs": {"source": "slot:ai-take", "in": 0.0, "out": probe(made)}, "params": {},
                          "note": "the scene's AI shots (%s), made by the production chain (ai_lane.py): clip %s"
                                  % (", ".join(shot_ids), call_id)})
            laid = True
    sources = dict(wf.get("sources") or {}, **{"ai-take": {"file": os.path.basename(str(made)), "drive_location": str(made),
                                                           "generated": True, "made_from": shot_ids, "call": call_id}})
    f.write_text(json.dumps(dict(wf, steps=steps, sources=sources), indent=1, ensure_ascii=False))
    return f


def run(n, B, say, dry_run=None, runner=chain, probe=_probe):
    """The stage: start the chain's command for this production's brief, then show its run, station by station.
    `say(step, state, said)` reports each step on the Studio's loading screen."""
    B = Path(B)
    c = conf()
    dry = c["dry_run"] if dry_run is None else dry_run
    brief = _load(B / "brief.json")
    wr = _writing_run(brief)
    first = STEPS[0][0]
    if not wr:
        say(first, "stopped", "this production names no writing run (brief.json `brief`): the chain cannot start")
        return {"made": [], "dry_run": dry, "stopped": "no writing run"}
    # what the chain has ALREADY made goes into the Studio's scenes first, with no chain run and nothing spent
    have = lay_made(B, brief, chain_status(brief, runner), probe)
    if not scenes_due(B, brief, chain_status(brief, runner)):
        say(first, "done", "the chain's clips are in every scene (%d laid now)" % len(have))
        return {"made": have, "dry_run": dry, "rc": 0, "left": []}
    say(first, "doing", "the production chain: ai_lane.py %s %s" % (wr, "--dry-run" if dry else "--yes"))
    args = [wr, "--json", "--dry-run"] if dry else [wr, "--yes", "--cap", c["cap_credits"]]
    rc, out = runner(args)
    if dry:
        try:
            res = json.loads(out[out.index("{"):])
        except ValueError:
            say(first, "stopped", ("the chain's dry run stopped: " + out.strip()[-300:]) or "no output")
            return {"made": [], "dry_run": True, "rc": rc}
        rows = {s["station"]: s for s in res.get("stations") or []}
        for sid, _ in STEPS:
            r = rows.get(sid) or {}
            say(sid, {"done": "done", "waiting": "done"}.get(r.get("state"), "stopped" if r else "done"),
                (r.get("said") or "")[:600])
        q = (res.get("quote") or {}).get("higgsfield_credits") or {}
        return {"made": [], "dry_run": True, "rc": rc, "quote": q, "live": res.get("live"), "shadow": res.get("shadow")}
    st = chain_status(brief, runner)
    names = dict(STEPS)
    for row in st.get("stations") or []:
        extra = ""
        if row["id"] == "pictures" and st.get("waiting_prints"):
            extra = "%d waiting for a 3D set print" % len(st["waiting_prints"])
        if row["id"] == "camera":
            extra = "%d scene(s) planned" % len(st.get("camera_motion") or {}) + (
                "; held: " + ", ".join(st.get("camera_held") or {}) if st.get("camera_held") else "")
        if row["id"] == "clips":
            extra = "%d of %d clip(s) made" % (sum(1 for x in st.get("calls") or [] if x.get("clip")),
                                               len(st.get("calls") or []))
        say(row["id"], "done" if row["done"] else "stopped", (extra or names.get(row["id"], ""))[:600])
    made = have + lay_made(B, brief, st, probe)
    return {"made": made, "dry_run": False, "rc": rc, "left": scenes_due(B, brief, st)}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    out = run(Path(sys.argv[1]).name, Path(sys.argv[1]), lambda sid, st, said="": print("%-11s %-8s %s" % (sid, st, said)),
              dry_run=True if "--dry-run" in sys.argv else None)
    print(json.dumps(out, indent=1, default=str))
