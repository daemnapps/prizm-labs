#!/usr/bin/env python3
"""Programmed motion: a scene's own take turned into stand-in figures in 3D, before any video model is paid for
(components/video-production/BRIEF-SPEC.md rule 7; ruled 2026-11-09: our own motion is the default).

    python3 motion_program.py <take.json> --out <dir> [--model opus|sonnet|gemini-3.1-pro-preview] [--no-render]
    python3 motion_program.py scene <scene dir>          the scene's take.json, programmed into <scene dir>/motion/

1. The timeline: each line's window from its read's length (a line with no read: its words at 2.7 a second).
2. The blocking: the take (staging, cast, every line's `do`, `moves` and `camera`) and the timeline go to Claude, on
   the plan of whoever runs it (the `claude` command line, no metered key), with prompts/motion-program.md; it answers
   with people, beats and a camera in blocking_blender.py's words. A `gemini-*` model name sends it to Gemini instead.
3. The figures: Blender renders the stand-ins and writes their exact skeletons (no reading back from pictures).
4. The preview: skeleton.mp4 (OpenPose colours, what the pose route drives a take with), overlay.mp4, sheet.jpg,
   camera.json, motion.json. Programmed motion is ready as made; nobody has to approve it.

Every call is kept: sent.json (the prompt exactly as sent), answer.json (the model's words), spec.json (what was built).
Claude needs the `claude` command line signed in; Gemini reads GEMINI_API_KEY through the key loader. No brand,
product or person is named here.
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402
import motion as MO  # noqa: E402

PROMPT = HERE / "prompts" / "motion-program.md"
MODEL = "opus"            # Claude, on the signed-in plan; a gemini-* name goes to Gemini
ACTIONS = ("walk", "walk_to", "reach", "mic", "turn", "lean", "nod", "shake", "tilt", "laugh")


def timeline(take, gap=0.35, lead=0.5):
    """Each line's window: its read's length, one after another."""
    t, rows = lead, []
    for k, ln in enumerate(take.get("script") or []):
        n = MO.seconds_of(ln["read"]) if ln.get("read") and Path(ln["read"]).exists() else 0
        n = n or max(0.8, len(str(ln.get("say", "")).split()) / 2.7)
        rows.append({"line": k + 1, "speaker": ln.get("speaker"), "from": round(t, 2), "to": round(t + n, 2)})
        t += n + gap
    return rows, round(t + 0.6, 2)


def _take_words(take):
    keep = {k: take[k] for k in ("staging", "look", "camera") if take.get(k)}
    cast = take.get("cast") or {}
    keep["cast"] = {n: ({"look": c.get("look")} if isinstance(c, dict) else {}) for n, c in cast.items()}
    keep["script"] = [{k: ln[k] for k in ("speaker", "say", "do", "moves", "camera") if ln.get(k)} for ln in take.get("script") or []]
    return json.dumps(keep, indent=1, ensure_ascii=False)


def ask(text, model=MODEL):
    if not model.startswith("gemini"):
        return ask_claude(text, model)
    key = ST.key("GEMINI_API_KEY")
    if not key:
        raise SystemExit("no GEMINI_API_KEY in the key file")
    body = {"contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    for attempt in range(4):
        try:
            r = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                       headers={"Content-Type": "application/json", "x-goog-api-key": key})
            res = json.load(urllib.request.urlopen(r, timeout=300))
            parts = res["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts if not p.get("thought")), res.get("usageMetadata") or {}
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            raise SystemExit(f"Gemini {e.code}: {e.read()[:300].decode('utf8', 'replace')}")


def ask_claude(text, model):
    """One answer from Claude through the signed-in command line: no tools, one turn, JSON back."""
    import os
    import shutil
    import tempfile
    cli = os.environ.get("MOTION_CLAUDE") or shutil.which("claude")
    if not cli:
        raise SystemExit("no `claude` command line here: sign in to Claude Code, or pass a gemini-* model")
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}   # the plan, never a metered key
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([cli, "-p", "--output-format", "json", "--model", model, "--max-turns", "1", "--tools", "",
                            "--strict-mcp-config", "--setting-sources", ""],      # the prompt alone: no tools, no settings
                           input=text + "\n\nAnswer with the JSON only, no other words.", capture_output=True, text=True,
                           cwd=d, env=env, timeout=900)
    try:
        res = json.loads(r.stdout)
    except ValueError:
        raise SystemExit("Claude gave no answer: " + (r.stderr or r.stdout)[-300:])
    if res.get("is_error"):
        raise SystemExit("Claude: " + str(res.get("result"))[:300])
    out = str(res.get("result") or "").strip()
    if out.startswith("```"):
        out = out.split("\n", 1)[1].rsplit("```", 1)[0]
    return out, {"model": model, "usage": res.get("usage"), "seconds": round((res.get("duration_ms") or 0) / 1000, 1)}


def clean(spec, seconds):
    """Only people, actions and times the figures can carry; what was dropped is said."""
    names = [p["name"] for p in spec.get("people") or []]
    dropped, beats = [], []
    for b in spec.get("beats") or []:
        acts = [a for a in ACTIONS if a in b]
        if b.get("who") not in names or not acts:
            dropped.append(b)
            continue
        f0 = max(0.0, min(seconds, float(b.get("from") or 0)))
        f1 = max(f0 + 0.2, min(seconds, float(b.get("to") or f0 + 1)))
        for a in acts:
            beats.append({"from": round(f0, 2), "to": round(f1, 2), "who": b["who"], a: b[a],
                          **({"hands": b["hands"]} if a == "reach" and b.get("hands") else {})})
    cam = spec.get("camera") or {}
    cam["follow"] = [f for f in cam.get("follow") or [] if f.get("who") in names]
    return {"people": spec["people"], "beats": beats, "camera": cam, "notes": spec.get("notes") or [],
            "dropped": dropped}


def program(take, out_dir, model=MODEL, render=True):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows, seconds = timeline(take)
    text = PROMPT.read_text().replace("{take}", _take_words(take)).replace(
        "{timeline}", "\n".join(f"line {r['line']} ({r['speaker']}): {r['from']}-{r['to']} s" for r in rows)).replace(
        "{seconds}", str(seconds))
    (out / "sent.json").write_text(json.dumps({"model": model, "prompt": text}, indent=1, ensure_ascii=False))
    answer, usage = ask(text, model)
    (out / "answer.json").write_text(answer)
    try:
        got = json.loads(answer)
    except ValueError:
        raise SystemExit("the motion programmer answered with no JSON: " + answer[:300])
    spec = clean(got, seconds)
    spec.update({"seconds": seconds, "fps": 16, "size": [480, 854], "render": render,
                 "sky": take.get("sky") or [0.55, 0.72, 0.92], "floor": take.get("floor") or [0.82, 0.74, 0.58]})
    (out / "spec.json").write_text(json.dumps(spec, indent=1))
    rec = MO.blocking(out / "spec.json", out / "blocking.mp4", exact=True, motion_dir=out)
    m = rec["motion"]
    m.update({"kind": "programmed", "status": "ready", "model": model, "timeline": rows, "notes": spec["notes"],
              "dropped": len(spec["dropped"]), "beats": len(spec["beats"]), "people_names": [p["name"] for p in spec["people"]],
              "tokens": usage, "seconds_to_program": round(time.time() - t0, 1)})
    m["take_motion"].update({"approved": True, "pose": str(out / "skeleton.mp4")})
    (out / "motion.json").write_text(json.dumps(m, indent=1))
    return m


def program_scene(scene_dir, model=MODEL):
    take_file = Path(scene_dir) / "take.json"
    if not take_file.exists():
        raise SystemExit(f"this scene has no take written yet ({take_file})")
    return program(json.loads(take_file.read_text()), Path(scene_dir) / "motion", model)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    model = a[a.index("--model") + 1] if "--model" in a else MODEL
    if a[0] == "scene":
        print(json.dumps(program_scene(a[1], model), indent=1))
    else:
        out = a[a.index("--out") + 1] if "--out" in a else "motion"
        print(json.dumps(program(json.loads(Path(a[0]).read_text()), out, model, "--no-render" not in a), indent=1))
