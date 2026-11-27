"""Render a Studio production: the edit built (to_studio.py), rendered for phones by HyperFrames, set to -14 LUFS,
every word heard back (swipe_check.py), then every hook and footage version the same way. Moved here from
video_studio.py's Next step (2026-11-21): the render is the edit's job; the Studio only shows its steps.

    render(n, B, say)  -> True when every step finished (a stopped step has already said why)"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO_HOME = Path(os.environ.get("VIDEO_STUDIO_HOME") or Path(__file__).resolve().parents[3] / "video-studio")
sys.path.insert(0, str(STUDIO_HOME)); sys.path.insert(0, str(HERE))
from scene_cut import ff, exact_level, probe_dur  # noqa: E402


def _tool(say, sid, args, timeout=3600):
    """One of the edit's own tools, run as it is run by hand; its last line is what the step says when it stops."""
    r = subprocess.run([sys.executable, str(HERE / args[0])] + args[1:], capture_output=True, text=True,
                       cwd=str(HERE), env=os.environ, timeout=timeout)
    tail = [ln for ln in (r.stdout + "\n" + r.stderr).splitlines() if ln.strip()]
    if r.returncode:
        say(sid, "stopped", (tail[-1] if tail else "the tool stopped")[:240])
    return r.returncode == 0, r.stdout


def render(n, B, say):
    """Every version of production n rendered and levelled; `say(step, state, words)` reports each step."""
    import video_studio as VS
    _cuts, _version_ids, load = VS._cuts, VS._version_ids, VS.load
    say("build", "doing")
    ok, out = _tool(say, "build", ["to_studio.py", n])
    if not ok:
        return False
    say("build", "done", (out.strip().splitlines() or [""])[-1][:120])
    say("render", "doing")
    cuts = _cuts(B)
    v = (int(re.search(r"-v(\d+)-", cuts[-1].name).group(1)) + 1) if cuts else 1
    raw, sdr = B / ("rough-cut-v%d-raw.mp4" % v), B / ("rough-cut-v%d-sdr.mp4" % v)
    r = subprocess.run(["hyperframes", "render", "--sdr", "--fps", "24000/1001", "--quality", "delivery", "-o", str(raw),
                        str(B / "studio")], capture_output=True, text=True, cwd=str(B / "studio"), timeout=3600)
    if r.returncode or not raw.exists():
        say("render", "stopped", ((r.stderr or r.stdout).strip().splitlines() or ["the render stopped"])[-1][:240])
        return False
    say("render", "done", "version %d, %.1f s" % (v, probe_dur(str(raw))))
    say("loud", "doing")
    m = subprocess.run(["ffmpeg", "-nostdin", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    js = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    af = ("loudnorm=I=-14:TP=-1:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
          % (js["input_i"], js["input_tp"], js["input_lra"], js["input_thresh"], js["target_offset"]))
    ff(["-i", str(raw), "-c:v", "copy", "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(sdr)])
    say("loud", "done", "%.1f LUFS" % exact_level(sdr))
    say("heard", "doing")
    r = subprocess.run([sys.executable, str(HERE / "swipe_check.py"), n, str(sdr)], capture_output=True, text=True,
                       cwd=HERE, env=os.environ, timeout=3600)
    res = [ln for ln in r.stdout.splitlines() if ln[:1] in ("✓", "✗")]
    bad = [ln for ln in res if ln.startswith("✗")]
    say("heard", "stopped" if bad or not res else "done",
         ("; ".join(bad)[:240] if bad else "%d of %d checks pass" % (len(res), len(res))) if res else "the check stopped")
    hooks = _version_ids(load(B / "brief.json"))
    if hooks:
        say("hooks", "doing")
        done_h, bad_h = [], []
        import to_studio as TS
        for h, var, hk in hooks:
            try:
                TS.build(n, hk, var)
                vd = B / "versions" / h
                raw, out = vd / "raw.mp4", vd / ("%s-%s.mp4" % (n, h))
                r = subprocess.run(["hyperframes", "render", "--sdr", "--fps", "24000/1001", "--quality", "delivery", "-o", str(raw),
                                    str(vd / "studio")], capture_output=True, text=True, cwd=str(vd / "studio"), timeout=3600)
                if r.returncode or not raw.exists():
                    bad_h.append(h); continue
                m = subprocess.run(["ffmpeg", "-nostdin", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
                                    "-f", "null", "-"], capture_output=True, text=True).stderr
                js = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
                af = ("loudnorm=I=-14:TP=-1:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
                      % (js["input_i"], js["input_tp"], js["input_lra"], js["input_thresh"], js["target_offset"]))
                ff(["-i", str(raw), "-c:v", "copy", "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
                exact_level(out)
                done_h.append(h)
                say("hooks", "doing", "%d of %d: %s" % (len(done_h), len(hooks), ", ".join(done_h)))
            except Exception as e:  # noqa: BLE001 — one hook that fails never stops the others
                bad_h.append("%s (%s)" % (h, str(e)[:60]))
        say("hooks", "stopped" if bad_h else "done",
             ("%d rendered; not: %s" % (len(done_h), ", ".join(bad_h))) if bad_h else "%d more versions" % len(done_h))
    return True
