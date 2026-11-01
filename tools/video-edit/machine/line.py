#!/usr/bin/env python3
"""line.py — the whole edit line in one command, the same way every time, for any brand, product, person or swipe.

    python3 line.py <video-production-run> [--out <edit run dir>] [--brief brief-NNNN] [--batch batch-YYYY-MM-DD-x]
                    [--links <catalog link id> …] [--only control,<hook>] [--no-file]

From a finished production run (its clips, voices and plan) and the ad's own decisions.json (written by the editor:
what to cover, what to fix, the B-roll, the looks — see EDIT-STANDARD.md "The decisions"), to a card waiting for
Approve in Drive meta/<brand>/1-check/video/. Every step's check STOPS the line; nothing is delivered past a red one.

  1  plan        edit_map.py --hooks       one edit map per version (the control + every hook opening) — takes laid
                                            whole, no repairs (V15); the bank's music and SFX when called for (V14)
  1b music      music_bed.py              only when the swipe/brief has music and production picked none: one bed
                                            for the whole edit, then the plan again
  2  mouths      mouths.py, every version   the lead's mouth only moves when the lead is heard          STOPS
  3  render      render_map.py              per version, before a frame is made:
                                              mouths again · every scripted word heard (listen)         STOPS
                                            after: lips within a frame of the voice (syncheck)          STOPS
                                            then compose.py draws every word (map_sheet.py — one renderer, C13)
  3b audit      audit.py, every version    words cut · lips still · wrong shot · sync · words on a face or
                                            mouth on the finished frames · the swipe's music and SFX       STOPS
  4  scan        black frames, dead air, loudness, 9:16, every version                                 STOPS
  5  thumbs      thumbs.py                  a designed thumbnail per version (decisions.json `thumbs`)  STOPS if not 9:16 / too big
  5b copy       copywriter brief_words.py  the ad's primary text, headlines, descriptions written by the copy machine
                                            — used as it is when already written; nothing written STOPS the line;
                                            `line.py copy-early <run>` writes it beside production (E34)
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
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
PY = sys.executable


def approved(rj, brief):
    """The final OK on the finished control cut — an `approve` verdict on the ad's review request, from the board,
    the dashboard or a teammate's own Claude, or a legacy jsonl line — read through ad_approvals.py (AR-1 (shared
    ad approvals), AR-1b (approvals as verdicts)). Hook versions and thumbnails wait for it (the owner's rulings,
    9 + 15 Oct: "keep the variations and thumbnail creation for the end" / "I just want to … do the final
    approval, right before we create the scroll stopper variations and the thumbnails")."""
    # Scope (video sync 2026-10-21, R8 / VIDEO-RULINGS V19): this OK only lets the hook versions and thumbnails be
    # made. It never sends anything live — Approve on Meta stays the owner's own press on the 1-check card.
    import ad_approvals
    keys = {k for k in (brief, rj.get("label"), rj.get("brief")) if k}
    src = str(rj.get("source_brief") or rj.get("brief_from") or "")
    for i, steps in ad_approvals.load(REPO).items():
        if "final" not in steps:
            continue                      # a production OK is not his OK on the finished cut
        if i and (i in keys or (len(i) > 5 and i in src) or any(i.endswith(k) or k.endswith(i) for k in keys)):
            return True
    return False


STEPS = [x["id"] for x in json.loads((HERE / "steps.json").read_text())["line"]["steps"]]   # one list, steps.json (E16)


class Red(SystemExit):
    pass


# ---------------------------------------------------------------- the ad's copy (E34, 2026-10-21)
# The copywriter ran on the edit's TAIL: 43 min at step 5b in the one measured full line, writing nothing (a reddit
# 408), then again inside filing (~49 min more). Now: copy already written is used as it is; a copywriter that writes
# nothing STOPS the line naming why; filing never runs it again; and `line.py copy-early <production run>` lets the
# batch runner write the copy beside production, the moment the brief lands.
def copy_words(brand: str, brief: str) -> tuple[dict, str | None]:
    """The words written for this brief — meta-upload's public `card_words.for_brief` (the approved copy set, else the
    brief's copywriter runs) — and where they came from. ({}, None) when there are none yet."""
    sys.path.insert(0, str(REPO / "components" / "meta-upload"))
    import card_words as W
    try:
        return W.for_brief(brand, brief)
    except Exception:  # noqa: BLE001 — unreadable copy is no copy; the line then writes it
        return {}, None


def has_copy(words: dict) -> bool:
    """The card's minimum: a primary text and a headline."""
    return bool((words or {}).get("primary")) and bool((words or {}).get("headlines"))


def write_copy(brand: str, brief: str, log: list[dict] | None = None, step: str = "5b copy") -> str:
    """The copy for one brief, written once: used as it is when it exists; else the copywriter runs, and if it still
    wrote nothing the line STOPS, naming the copywriter's own last words — never a silent card with no copy."""
    log = log if log is not None else []
    w, where = copy_words(brand, brief)
    if has_copy(w):
        log.append({"step": step, "ok": True, "said": f"{brief}: copy already written ({where})"})
        print(f"  ✓ {step:<10} {brief}: already written ({where})")
        return where or ""
    cw = REPO / "tools" / "copywriter" / "machine" / "brief_words.py"
    t = time.time()
    r = subprocess.run([PY, str(cw), "--brand", brand, "--brief", brief], capture_output=True, text=True)
    said = (r.stdout + r.stderr).strip()
    w, where = copy_words(brand, brief)
    ok = has_copy(w)
    log.append({"step": step, "ok": ok, "seconds": round(time.time() - t, 1), "said": said[-3000:]})
    if not ok:
        print(f"  ✗ {step:<10} the copywriter wrote no copy for {brief}", flush=True)
        raise Red(f"{step} stopped the line: the copywriter wrote no copy for {brief} (exit {r.returncode}) — "
                  f"its last words:\n{said[-1500:] or '(nothing)'}\nFix the copywriter's run, then `line.py <run> --from copy`.")
    print(f"  ✓ {step:<10} {brief}: written by the copywriter ({where})")
    return where or ""


def copy_early(argv=None) -> int:
    """`line.py copy-early <production run> [--brief brief-NNNN]` — write the ad's copy now, beside production, so the
    line finds it written at 5b. Exit 0 = the copy is there."""
    ap = argparse.ArgumentParser(description="write the ad's copy as soon as the brief lands, beside production")
    ap.add_argument("cmd"); ap.add_argument("run"); ap.add_argument("--brief")
    a = ap.parse_args(argv)
    rj = json.loads((Path(a.run) / "run.json").read_text())
    brief = a.brief or rj.get("brief")
    if not brief:
        print("copy-early: this production run names no brief — nothing to write copy for")
        return 1
    try:
        write_copy(rj.get("brand", ""), brief, step="copy early")
        return 0
    except Red as e:
        print(str(e))
        return 1


class Done(Exception):
    pass


def _edit_auto() -> bool:
    import render_map
    return render_map._edit_auto()


def run(step: str, cmd: list[str], log: list[dict], env: dict | None = None) -> str:
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = (r.stdout + r.stderr).strip()
    log.append({"step": step, "ok": r.returncode == 0, "seconds": round(time.time() - t, 1), "said": out[-3000:]})
    print(f"  {'✓' if r.returncode == 0 else '✗'} {step:<10} {out.splitlines()[-1] if out else ''}", flush=True)
    if r.returncode != 0:
        raise Red(f"{step} stopped the line:\n{out[-2000:]}")
    return out


_APPROVED = {"on": False}


def soft(step: str, cmd: list[str], log: list[dict]) -> str:
    """A check that, on a draft with edit on Auto, or on a cut of APPROVED clips (`--approved`, L-66), is logged and
    carried past (the render itself still lists it)."""
    try:
        return run(step, cmd, log)
    except Red as e:
        if not (_edit_auto() or _APPROVED["on"]):
            raise
        print(f"  WARN {step}: carried past ({'the clips are approved: listed for a person' if _APPROVED['on'] else 'edit on Auto'})")
        return str(e)


def scan(mp4: Path, room: bool = True) -> dict:
    """Black frames, dead silence, loudness and shape of one finished file. With room tone under the cut (only when the
    swipe has room sound, V14) no moment may drop to silence at all; without it the breath between two lines is the
    voices' own tails, so only DEAD AIR counts — a silence of half a second or more (V15)."""
    def ff(*a):
        return subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), *a, "-f", "null", "-"], capture_output=True, text=True).stderr
    black = ff("-vf", "blackdetect=d=0.05:pix_th=0.08", "-an").count("black_start")
    silence = ff("-af", f"silencedetect=n=-60dB:d={0.05 if room else 0.5}", "-vn").count("silence_start")
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", ff("-af", "ebur128", "-vn"))
    wh = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                         "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip()
    w, h = (int(x) for x in wh.split(","))
    return {"black": black, "silences": silence, "lufs": float(lufs[-1]) if lufs else None, "size": [w, h],
            "ok": black == 0 and silence == 0 and w * 16 == h * 9 and (lufs and abs(float(lufs[-1]) + 14) <= 1.5)}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["copy-early"]:
        return copy_early(argv)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out"); ap.add_argument("--brief"); ap.add_argument("--batch")
    ap.add_argument("--links", nargs="*", default=[]); ap.add_argument("--only"); ap.add_argument("--no-file", action="store_true")
    ap.add_argument("--versions", action="store_true",
                    help="make the hook versions + thumbnails now (normally they wait for the owner's OK on the control cut)")
    ap.add_argument("--approved", action="store_true",
                    help="the clips, voice and script are approved (the board's Edit step): the edit only cuts them together; "
                         "its checks are listed, never a stop, and nothing is regenerated")
    ap.add_argument("--draft", action="store_true",
                    help="stop at the draft on the timeline: plan, word fixes, mouths, a draft render, scan — nothing delivered or filed")
    ap.add_argument("--from", dest="start", choices=STEPS, default="plan",
                    help="start at this step (the steps before it already ran clean, e.g. --from deliver after a naming gap)")
    a = ap.parse_args(argv)
    _APPROVED["on"] = bool(a.approved)
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
            # NO REPAIRS on this path (V15 "the edit cuts, it does not repair"; verify 2026-10-21 row 6): the old 1b step
            # re-said a cut-off line in a cloned voice (word_fix auto) on every cut. A take that cuts a line off goes
            # back to production; the audit names it (WORD CUT) and stops the line.
            # THE MUSIC the swipe or the brief calls for and production did not pick (V14, row 5): one bed made to
            # cover the whole edit (music_bed.py, ElevenLabs Music), then the cut re-planned to lay it
            m0 = json.loads((out / "edit-map.json").read_text())
            replan = False
            if (m0.get("music") or {}).get("what") and not (m0.get("music") or {}).get("made"):
                run("1b music", [PY, str(HERE / "music_bed.py"), str(vm), "--out", str(out)], log)
                replan = True
            # THE EFFECTS the swipe or the brief calls for and no bank has yet (E39): made for this edit through
            # production's bank maker, in the run's own bank — never an effect nobody called for (V14)
            if any(not c.get("made") for c in m0.get("sfx") or []):
                run("1c effects", [PY, str(HERE / "sfx_make.py"), str(vm), "--out", str(out)], log)
                replan = True
            if replan:
                run("1 plan", [PY, str(HERE / "edit_map.py"), str(vm), "--out", str(out), "--hooks"], log)
        maps = ["edit-map.json"] + sorted(f.name for f in out.glob("edit-map-*.json"))
        names = {m: ("control" if m == "edit-map.json" else m[len("edit-map-"):-5]) for m in maps}
        versions = a.versions or approved(rj, brief)
        # THE CONTROL CUT FIRST: hook versions and thumbnails are made only after his OK (approved() above)
        want = set(a.only.split(",")) if a.only else (set(names.values()) if versions else {"control"})
        if not versions and not a.only:
            print("  control cut only — hook versions + thumbnails wait for the owner's OK (Ad Runs board)")
        for m, v in names.items():
            if v in want and go("mouths"):
                (soft if a.draft else run)(f"2 mouths {v}", [PY, str(HERE / "mouths.py"), str(vm), "--out", str(out), "--map", m], log)
        if go("render"):
            run("3 render", [PY, str(HERE / "render_map.py"), str(vm), "--out", str(out), "--only", ",".join(sorted(want)),
                             *(["--draft"] if a.draft else []), *(["--approved"] if a.approved else [])], log)
        if go("audit"):
            # THE AUDIT, every version (E12–E14): before anyone watches it; a finding stops the line (a draft on Auto
            # carries it, listed — the final still holds it)
            (soft if a.draft or a.approved else run)("3b audit", [PY, str(HERE / "audit.py"), str(out), "--only", ",".join(sorted(want))], log)
        bad = {}
        for v in (sorted(want) if go("scan") else []):
            rj_v = json.loads((out / "renders" / f"{v}.json").read_text()) if (out / "renders" / f"{v}.json").exists() else {}
            s = scan(out / "renders" / f"{v}.mp4", bool(rj_v.get("room_tone", True)))
            log.append({"step": f"4 scan {v}", "ok": bool(s["ok"]), **s})
            print(f"  {'✓' if s['ok'] else '✗'} 4 scan {v:<6} black {s['black']} · silences {s['silences']} · {s['lufs']} LUFS · {s['size'][0]}x{s['size'][1]}")
            if not s["ok"]:
                bad[v] = s
        if bad and a.draft and _edit_auto():
            print(f"  WARN scan: {bad} (draft kept: edit on Auto; the final holds it)")
        elif bad:
            raise Red(f"4 scan stopped the line: {bad}")
        # THE WATCH (2026-10-23, the owner: "gemini for the watch so we have a consistent eye on our assets"): the house
        # judge watches every finished version the way a viewer would (watch.py); a cut nobody watched never passes
        seen_bad = {}
        for v in (sorted(want) if go("watch") else []):
            import watch as W
            w = W.watch(out / "renders" / f"{v}.mp4", v, vm / "lines.json")
            log.append({"step": f"4b watch {v}", "ok": bool(w["pass"]), **{k: w.get(k) for k in ("score", "problems", "by")}})
            print(f"  {'✓' if w['pass'] else '✗'} 4b watch {v:<6} {w.get('score')}/10 · {len(w.get('problems') or [])} problems · {w.get('by')}")
            if not w["pass"]:
                seen_bad[v] = [p.get("what") for p in w.get("problems") or []][:4]
        if seen_bad and a.draft and _edit_auto():
            print(f"  WARN watch: {seen_bad} (draft kept: edit on Auto; the final holds it)")
        elif seen_bad:
            raise Red(f"4b watch stopped the line: {seen_bad}")
        if a.draft:
            raise Done("draft on the timeline — ready to watch and render")
        if go("thumbs") and (versions or a.only):
            run("5 thumbs", [PY, str(HERE / "thumbs.py"), str(vm), "--out", str(out), "--only", ",".join(sorted(want))], log)
        if go("copy") and brief:
            # THE COPY MACHINE before the card (E34): copy already written — the approved copy set or this brief's
            # copywriter runs, read through meta-upload's card_words — is used as it is; else it is written once,
            # and a copywriter that writes nothing stops the line here, naming why
            write_copy(rj.get("brand", ""), brief, log)
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
            fcmd += (["--avatar", card["avatar"]] if card.get("avatar") else [])   # no --angle: the filer reads the brief's (naming ANGLE.md)
            thumbs = [out / "renders" / f"{x['version']}_thumb.jpg" for x in man["ads"]]
            if all(t.exists() for t in thumbs):
                fcmd += ["--thumbs", *map(str, thumbs)]           # each video's own designed thumbnail
            # the copy was settled at 5b: filing never runs the copywriter again (E34 — it once re-ran for ~49 min
            # after 5b had already failed); NO_AD_WORDS=1 is to_check's own switch for that
            run("7 file", fcmd, log, env={**os.environ, "NO_AD_WORDS": "1"})
        ok, msg = True, "filed — waiting for Approve in meta/<brand>/1-check/video/" if not a.no_file else "delivered (not filed: --no-file)"
    except Done as e:
        ok, msg = True, str(e)
    except Red as e:
        ok, msg = False, str(e)
    (out / "line.json").write_text(json.dumps({"ok": ok, "result": msg.splitlines()[0], "minutes": round((time.time() - t0) / 60, 1),
                                               "steps": log}, indent=1, ensure_ascii=False))
    print(("DONE  " if ok else "STOPPED  ") + msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
