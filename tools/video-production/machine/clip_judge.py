"""The clip judge (CHANGES.md P5, VIDEO-RULINGS V3/V5/V8, 2026-10-21) — one take scored against its shot.

Every shot is made as three takes (clips_run.make_picked); this scores each one so the best is kept. It asks the
house judge (components/generative-model-house `behind.judge`, Gemini 3.1 Pro) to watch the take beside its
approved start picture, with the prompt `prompts/v2/clip-judge-v4-owner.md` (v4, 2026-10-28 — v3 + props make sense, the right object, the voice, the swipe's elements):

  dead pauses · lips closed while listening · kept its object · room unchanged · same person · the acting ·
  the camera move · no slop · absurd on purpose passes · stop-power (V24: how hard it stops a thumb)

    judge(run, take_file, call, scenes)  -> {"score", "pass", "problems", "by", "remembered"}
    shot_words(call, scenes)             -> the shot, in words, as the judge reads it

The answer is remembered by a fingerprint of the take and the question (v2_checks.ask), so a take is never
judged twice. A judge that cannot answer returns pass False with the reason — a take nobody watched is not shipped.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPT = HERE.parent / "prompts" / "v2" / "clip-judge-v4-owner.md"   # v4: props make sense, right object, voice, the swipe's elements (2026-10-28)


def _load(name: str, as_name: str | None = None):
    sp = importlib.util.spec_from_file_location(as_name or f"vm_cj_{name}", HERE / f"{name}.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def shot_words(call: dict, scenes: dict) -> str:
    """What the take had to show: its prompt as sent (the acting, the camera, who speaks and who listens)."""
    out = [f"- the clip prompt the model was sent:\n\n{call.get('prompt') or ''}"]
    on = [l for l in call.get("lines") or [] if l.get("on_camera")]
    off = [l for l in call.get("lines") or [] if not l.get("on_camera")]
    if on:
        out.append("- said ON camera: " + " / ".join(f'"{l.get("text")}"' for l in on))
    if off:
        out.append("- said OFF camera (the person on screen listens, lips closed): "
                   + " / ".join(f'"{l.get("text")}"' for l in off))
    if not call.get("lines"):
        out.append("- nobody speaks in this shot: every mouth stays closed")
    return "\n".join(out)


def judge(run: Path, take: Path, call: dict, scenes: dict, start_picture: Path | None = None, ask=None) -> dict:
    V = _load("v2_checks", "vm_cj_v2_checks")
    H = _load("house", "vm_cj_house")
    model = H.judge()
    sb = _load("scene_breakdown", "vm_cj_scene_breakdown")
    swipe = sb.judge_lines(sb.of_call(run, call)) or "- (this scene's swipe was not broken down: check 14 does not apply)"
    prompt = PROMPT.read_text().replace("{shot}", shot_words(call, scenes)).replace("{swipe}", swipe)
    files = [Path(take)] + ([Path(start_picture)] if start_picture else [])
    sg = _load("sheet_gates", "vm_cj_sheet_gates")      # the judge's sheet: formats, count and inline size
    found = sg.judge_files(model, files)
    if any(f["level"] == "error" for f in found):
        return {"score": 0, "pass": False, "problems": [{"check": 0, "what": "the judge's sheet refuses this request: " + " ".join(f["say"] for f in found if f["level"] == "error")[:300]}],
                "by": model, "remembered": False}
    try:
        text, info = (ask or V.ask)(run, f"{call.get('id')}-clip-judge", prompt, files, model=model)
    except Exception as e:                              # noqa: BLE001 — an unanswered judge never passes a take
        return {"score": 0, "pass": False, "problems": [{"check": 0, "what": f"the judge did not answer: {e}"[:300]}],
                "by": model, "remembered": False}
    ans = V.json_of(text) or {}
    try:
        score = float(ans.get("score"))
    except (TypeError, ValueError):
        return {"score": 0, "pass": False, "problems": [{"check": 0, "what": "the judge's answer was unreadable"}],
                "by": info.get("model") or model, "remembered": bool(info.get("remembered"))}
    probs = [p for p in ans.get("problems") or [] if isinstance(p, dict)]
    try:
        stop = float(ans.get("stop_power"))
    except (TypeError, ValueError):
        stop = 0.0
    return {"score": score, "pass": bool(ans.get("pass")) and score >= 7, "problems": probs, "stop_power": stop,
            "by": info.get("model") or model, "remembered": bool(info.get("remembered"))}


if __name__ == "__main__":
    import sys
    r, t, plan_id = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    plan = json.loads((r / "clips" / "plan.json").read_text())
    c = next(x for x in plan["calls"] if x["id"] == plan_id)
    print(json.dumps(judge(r, t, c, {}), indent=1))
