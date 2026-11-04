#!/usr/bin/env python3
"""watch.py — the eye on every finished cut (step 4b of the edit-map line, 2026-10-23).

the owner, 2026-10-23: "I'm ok with using gemini for the watch so we have a consistent eye on our assets." The clips are
watched one by one in production (video-production's clip judge, the house judge); this watches the FINISHED cut the
same way a viewer would — the product real, one person throughout, lips on the voice, the words right and in their
bands, no slop, an opening that stops a thumb, an ending on the offer — with the prompt
`prompts/stage-4-watch/cut-watch-v1-owner.md`.

    python3 watch.py <renders/control.mp4> [--lines <production run>/lines.json] [--version control]

The model is the Generative Model House's `behind.judge` (busy fallbacks `behind.judge_busy`); the key GEMINI_API_KEY
comes through ve_keys. The cut is sent as a small 480p copy beside it (<version>.watch-proxy.mp4). The answer is kept
in <version>.watch.json with a fingerprint of the cut and the question, so a cut is never watched twice. A judge that
cannot answer never passes a cut — nobody watched it.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROMPT = HERE.parent / "prompts" / "stage-4-watch" / "cut-watch-v1-owner.md"
HOUSE = REPO / "components" / "generative-model-house" / "models.json"
INLINE_MAX = 18 * 1024 * 1024      # Gemini's inline request limit is 20 MB; the proxy stays under it
PASS_SCORE = 7


def models() -> list[str]:
    """The judge first, then the busy fallbacks — never a cost choice (VIDEO-RULINGS V17)."""
    behind = json.loads(HOUSE.read_text()).get("behind") or {}
    return [behind["judge"]] + list((behind.get("judge_busy") or {}).get("models") or [])


def lines_text(lines_file: Path | None) -> str:
    if not lines_file or not Path(lines_file).is_file():
        return ""
    data = json.loads(Path(lines_file).read_text())
    rows = data.items() if isinstance(data, dict) else enumerate(data)
    return "\n".join(f"- {v}" for _, v in rows if str(v or "").strip())


def proxy(mp4: Path) -> Path:
    """A 480-wide copy for the eye — the master is never sent or touched."""
    out = mp4.with_name(mp4.stem + ".watch-proxy.mp4")
    if out.exists() and out.stat().st_mtime >= mp4.stat().st_mtime:
        return out
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", "scale=480:-2", "-r", "24",
                    "-c:v", "libx264", "-crf", "30", "-preset", "veryfast", "-c:a", "aac", "-b:a", "64k", str(out)],
                   check=True)
    return out


def _gemini(model: str, prompt: str, video: Path, key: str) -> str:
    body = {"contents": [{"parts": [{"text": prompt},
                                    {"inline_data": {"mime_type": "video/mp4",
                                                     "data": base64.b64encode(video.read_bytes()).decode()}}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])


def ask(prompt: str, video: Path) -> tuple[str, str]:
    """(answer text, the model that answered). Busy → the next house model; anything else → raised."""
    import ve_keys
    key = ve_keys.key("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(ve_keys.missing("GEMINI_API_KEY"))
    last = None
    for model in models():
        for n in range(2):
            try:
                return _gemini(model, prompt, video, key), model
            except urllib.error.HTTPError as e:
                last = f"{model} HTTP {e.code}"
                if e.code in (429, 500, 503):
                    time.sleep(5 * (n + 1))
                    continue
                raise RuntimeError(last) from None
            except (TimeoutError, OSError) as e:
                last = f"{model} did not answer: {e}"
                time.sleep(5)
    raise RuntimeError(last or "no judge model in the house")


def _json_of(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").split("\n", 1)[-1]
    try:
        return json.loads(t[t.index("{"):t.rindex("}") + 1])
    except ValueError:
        return {}


def watch(mp4: Path, version: str = "control", lines_file: Path | None = None, asker=ask) -> dict:
    mp4 = Path(mp4)
    prompt = PROMPT.read_text().replace("{version}", version).replace("{lines}", lines_text(lines_file))
    fp = hashlib.sha256(mp4.read_bytes() + prompt.encode()).hexdigest()[:20]
    keep = mp4.with_name(mp4.stem + ".watch.json")
    if keep.exists():
        old = json.loads(keep.read_text())
        if old.get("fingerprint") == fp:
            return {**old, "remembered": True}
    try:
        video = proxy(mp4)
        if video.stat().st_size > INLINE_MAX:
            raise RuntimeError(f"the watch copy is {video.stat().st_size // 1_000_000} MB, over the inline limit")
        text, by = asker(prompt, video)
    except Exception as e:  # noqa: BLE001 — an unanswered judge never passes a cut
        return {"pass": False, "score": 0, "problems": [{"check": 0, "at": "", "what": f"nobody watched it: {e}"[:300]}],
                "by": None, "answered": False}
    ans = _json_of(text)
    try:
        score = float(ans.get("score"))
    except (TypeError, ValueError):
        return {"pass": False, "score": 0, "problems": [{"check": 0, "at": "", "what": "the judge's answer was unreadable"}],
                "by": by, "answered": False}
    probs = [p for p in ans.get("problems") or [] if isinstance(p, dict)]
    out = {"pass": bool(ans.get("pass")) and score >= PASS_SCORE, "score": score, "problems": probs,
           "stop_power": ans.get("stop_power"), "by": by, "answered": True, "fingerprint": fp,
           "prompt": PROMPT.name, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    keep.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the eye on one finished cut")
    ap.add_argument("mp4"); ap.add_argument("--lines"); ap.add_argument("--version", default="control")
    a = ap.parse_args(argv)
    r = watch(Path(a.mp4), a.version, Path(a.lines) if a.lines else None)
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    sys.exit(main())
