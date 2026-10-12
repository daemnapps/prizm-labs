#!/usr/bin/env python3
"""line.py — the whole edit line in one command, the same way every time, for any brand, product, person or swipe.

    python3 line.py <video-production-run> [--out <edit run dir>] [--brief brief-NNNN] [--batch batch-YYYY-MM-DD-x]
                    [--links <catalog link id> …] [--only control,<hook>] [--no-file]

From a finished production run (its clips, voices and plan) and the ad's own decisions.json (written by the editor:
what to cover, what to fix, the B-roll, the looks — see EDIT-STANDARD.md "The decisions"), to a card waiting for
Approve in Drive meta/<brand>/1-check/video/. Every step's check STOPS the line; nothing is delivered past a red one.

  1  plan        edit_map.py --hooks       one edit map per version (the control + every hook opening)
  2  mouths      mouths.py, every version   the lead's mouth only moves when the lead is heard          STOPS
  3  render      render_map.py              per version, before a frame is made:
                                              mouths again · every scripted word heard (listen)         STOPS
                                            after: lips within a frame of the voice (syncheck)          STOPS
  4  scan        black frames, dead silence, loudness, 9:16, every version                             STOPS
  5  thumbs      thumbs.py                  a designed thumbnail per version (decisions.json `thumbs`)  STOPS if not 9:16 / too big
  5b copy       copywriter brief_words.py  the ad's primary text, headlines, descriptions written by the copy machine
                                            (tools/copywriter, stages 0-9) — skipped only when this brief's copy
                                            is already written (the owner, 2026-10-09: "whenever … an ad set of creatives
                                            is ready for distribution, we need to run the copywriter on those as well")
  6  deliver     deliver.py                 names (components/naming), the card, the manifest          STOPS on a gap
  7  file        meta-upload to_check       the card + videos + thumbnails into 1-check (refiled in place: the Drive link stays)

Writes <out>/line.json — every step, what it found, how long it took. Exit 0 = filed and waiting for Approve.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
PY = sys.executable


STEPS = ["plan", "mouths", "render", "scan", "thumbs", "copy", "deliver", "file"]


class Red(SystemExit):
    pass


def run(step: str, cmd: list[str], log: list[dict]) -> str:
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    log.append({"step": step, "ok": r.returncode == 0, "seconds": round(time.time() - t, 1), "said": out[-3000:]})
    print(f"  {'✓' if r.returncode == 0 else '✗'} {step:<10} {out.splitlines()[-1] if out else ''}", flush=True)
    if r.returncode != 0:
        raise Red(f"{step} stopped the line:\n{out[-2000:]}")
    return out


def scan(mp4: Path) -> dict:
    """Black frames, dead silence, loudness and shape of one finished file."""
    def ff(*a):
        return subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), *a, "-f", "null", "-"], capture_output=True, text=True).stderr
    black = ff("-vf", "blackdetect=d=0.05:pix_th=0.08", "-an").count("black_start")
    silence = ff("-af", "silencedetect=n=-60dB:d=0.05", "-vn").count("silence_start")
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", ff("-af", "ebur128", "-vn"))
    wh = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                         "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip()
    w, h = (int(x) for x in wh.split(","))
    return {"black": black, "silences": silence, "lufs": float(lufs[-1]) if lufs else None, "size": [w, h],
            "ok": black == 0 and silence == 0 and w * 16 == h * 9 and (lufs and abs(float(lufs[-1]) + 14) <= 1.5)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--brief"); ap.add_argument("--batch")
    ap.add_argument("--links", nargs="*", default=[]); ap.add_argument("--only"); ap.add_argument("--no-file", action="store_true")
    ap.add_argument("--from", dest="start", choices=STEPS, default="plan",
                    help="start at this step (the steps before it already ran clean, e.g. --from deliver after a naming gap)")
    a = ap.parse_args(argv)
    vm = Path(a.run).resolve()
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out).resolve() if a.out else REPO / "runs" / "video-edit" / rj["brand"] / rj["label"]
    log: list[dict] = []
    t0 = time.time()
    print(f"edit line · {rj['brand']} · {rj['label']}")
    go = lambda step: STEPS.index(step) >= STEPS.index(a.start)
    erj = json.loads((out / "run.json").read_text()) if (out / "run.json").exists() else {}
    brief = a.brief or erj.get("brief") or rj.get("brief")        # the register number, wherever it was opened
    try:
        if go("plan"):
            run("1 plan", [PY, str(HERE / "edit_map.py"), str(vm), "--out", str(out), "--hooks"], log)
        maps = ["edit-map.json"] + sorted(f.name for f in out.glob("edit-map-*.json"))
        names = {m: ("control" if m == "edit-map.json" else m[len("edit-map-"):-5]) for m in maps}
        want = set(a.only.split(",")) if a.only else set(names.values())
        for m, v in names.items():
            if v in want and go("mouths"):
                run(f"2 mouths {v}", [PY, str(HERE / "mouths.py"), str(vm), "--out", str(out), "--map", m], log)
        if go("render"):
            run("3 render", [PY, str(HERE / "render_map.py"), str(vm), "--out", str(out), "--only", ",".join(sorted(want))], log)
        bad = {}
        for v in (sorted(want) if go("scan") else []):
            s = scan(out / "renders" / f"{v}.mp4")
            log.append({"step": f"4 scan {v}", "ok": bool(s["ok"]), **s})
            print(f"  {'✓' if s['ok'] else '✗'} 4 scan {v:<6} black {s['black']} · silences {s['silences']} · {s['lufs']} LUFS · {s['size'][0]}x{s['size'][1]}")
            if not s["ok"]:
                bad[v] = s
        if bad:
            raise Red(f"4 scan stopped the line: {bad}")
        if go("thumbs"):
            run("5 thumbs", [PY, str(HERE / "thumbs.py"), str(vm), "--out", str(out), "--only", ",".join(sorted(want))], log)
        if go("copy") and brief:
            # THE COPY MACHINE before the card: the card reads the copywriter's stage 8 render for this brief
            # (meta-upload card_words); a brief already written is not written again
            cw = REPO / "tools" / "copywriter" / "machine" / "brief_words.py"
            done = any((REPO / "runs" / "copywriter" / rj.get("brand", "")).glob(f"*{brief}*-words/stage8--render.md"))
            if done:
                log.append({"step": "5b copy", "ok": True, "said": f"{brief}: copy already written by the copywriter"})
                print(f"  ✓ 5b copy      {brief}: already written by the copywriter")
            else:
                run("5b copy", [PY, str(cw), "--brand", rj.get("brand", ""), "--brief", brief], log)
        dcmd = [PY, str(HERE / "deliver.py"), str(out), str(out / "renders"), "--replace"]
        dcmd += (["--brief", brief] if brief else []) + (["--batch", a.batch] if a.batch else [])
        dcmd += (["--links", *a.links] if a.links else [])
        if go("deliver"):
            run("6 deliver", dcmd, log)
        if not a.no_file:
            card_dir = max((out / "deliverable").glob("*/card.json"), key=lambda p: p.stat().st_mtime).parent
            card = json.loads((card_dir / "card.json").read_text())
            man = json.loads((card_dir / "manifest.json").read_text())
            media = [str(out / "renders" / f"{x['version']}.mp4") for x in man["ads"]]
            words = card_dir / "words.json"
            words.write_text(json.dumps(card.get("words") or {}, ensure_ascii=False))
            fcmd = [PY, str(REPO / "components" / "meta-upload" / "to_check.py"), "--brand", card["brand"], "--lane", "video",
                    "--ad-name", card["ad_name"], "--product", card["product"], "--brief", card["brief_id"],
                    "--batch", man["batch"], "--media", *media, "--words", str(words), "--tool", "video-edit",
                    "--run", str(out.relative_to(REPO)) if out.is_relative_to(REPO) else str(out), "--replace",
                    "--links", *[p["link_id"] for p in card.get("pages") or []]]
            fcmd += (["--avatar", card["avatar"]] if card.get("avatar") else []) + (["--angle", card["angle"]] if card.get("angle") else [])
            thumbs = [out / "renders" / f"{x['version']}_thumb.jpg" for x in man["ads"]]
            if all(t.exists() for t in thumbs):
                fcmd += ["--thumbs", *map(str, thumbs)]           # each video's own designed thumbnail
            run("7 file", fcmd, log)
        ok, msg = True, "filed — waiting for Approve in meta/<brand>/1-check/video/" if not a.no_file else "delivered (not filed: --no-file)"
    except Red as e:
        ok, msg = False, str(e)
    (out / "line.json").write_text(json.dumps({"ok": ok, "result": msg.splitlines()[0], "minutes": round((time.time() - t0) / 60, 1),
                                               "steps": log}, indent=1, ensure_ascii=False))
    print(("DONE  " if ok else "STOPPED  ") + msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
