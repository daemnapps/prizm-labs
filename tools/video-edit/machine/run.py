#!/usr/bin/env python3
"""run.py — the one command for the video edit.

    python3 machine/run.py from-run <video-machine-run-folder>          # the join: writes the kit from a production run
    python3 machine/run.py start  <kit-folder> --brand <brand> --label <label> [--dry-run] [--from <step>] [--controls <file>]
    python3 machine/run.py approve <run-folder> timeline|captions [--note "..."]
    python3 machine/run.py change  <run-folder> timeline|captions "what to change, in plain words" [--why "..."]
    python3 machine/run.py status  <run-folder>

A KIT is what production hands over — `edit-kit.json` beside the media it names:

    voice     {src, words: <file of [{text,start,end}]> | null}
    music     {src} | null          sfx  [{id, src, at, for}]
    clips     [{id, src, roll: "a"|"b", scene, covers: [from_s, to_s], approved: true, still?: bool, source_start?: s}]
    brief     <path> | null         format / style_id  (element ids)

The run stops twice for Damon (steps.json): the TIMELINE, then the CAPTIONS.
`approve` moves it on; `change` records what he asked for and why, reopens the
stop, and the session edits the cut sheet as a NEW version — a change is never
a regeneration. `--dry-run` checks everything and spends nothing.

Output: runs/video-edit/<brand>/<label>/ (runs/README.md). Tests pass their own
--runs-root and never touch that tree.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
sys.path.insert(0, str(HERE))
import compose as C  # noqa: E402
import cutsheet as CS  # noqa: E402
import timeline_page as TP  # noqa: E402

STEPS = [s["id"] for s in json.loads((HERE / "steps.json").read_text())["steps"]]


def repo_root() -> Path:
    for p in [TOOL, *TOOL.parents]:
        if (p / "runs" / "README.md").exists() or (p / ".git").exists():
            return p
    return TOOL


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def read(p: Path, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def controls_for(override: Path | None) -> dict:
    c = read(HERE / "defaults.json")
    for k, v in (read(override, {}) if override else {}).items():
        c[k] = {**c[k], **v} if isinstance(c.get(k), dict) and isinstance(v, dict) else v
    return c


# ---------------------------------------------------------------- the steps
def gather(kit_dir: Path) -> tuple[dict, list[str]]:
    kit = read(kit_dir / "edit-kit.json")
    if kit is None:
        return {}, [f"no edit-kit.json in {kit_dir} — production has not handed this over"]
    red = []
    talking = [c for c in kit.get("clips") or [] if c.get("roll") == "a" and c.get("talks")]
    voiced = [c for c in kit.get("clips") or [] if c.get("voice")]
    if not talking and not voiced and not (kit.get("voice") or {}).get("src"):
        red.append("kit: no sound to cut to — either a talking A-roll clip or an approved voice track")
    voiced = [c for c in kit.get("clips") or [] if c.get("voice")]
    for c in kit.get("clips") or []:
        if not c.get("approved"):
            red.append(f"kit.clips ({c.get('id')}): not approved — an unapproved clip never reaches the edit")
        if c.get("roll") not in ("a", "b"):
            red.append(f"kit.clips ({c.get('id')}): no roll label — the teardown and the brief say which is A-roll and which is B-roll")
    if not any(c.get("roll") == "a" or c.get("voice") for c in kit.get("clips") or []):
        red.append("kit.clips: nothing carries the words — no A-roll and no B-roll over a voice slice")
    return kit, red


def words_for(kit: dict, kit_dir: Path, work: Path) -> list[dict]:
    wf = (kit.get("voice") or {}).get("words")
    if wf:
        d = read(kit_dir / wf)
        ws = d["words"] if isinstance(d, dict) else d
    else:  # time the words off the approved audio
        subprocess.run(["hyperframes", "transcribe", str(kit_dir / kit["voice"]["src"]), "--dir", str(work)], check=True, capture_output=True)
        d = read(work / "transcript.json")
        ws = d["words"] if isinstance(d, dict) else d
    return [{"text": w.get("text") or w.get("word"), "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)} for w in ws if (w.get("text") or w.get("word", "")).strip()]


def level_voice(src: Path, work: Path, target: float = -16.0) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    """One pass of loudness levelling so the voice lands where a phone expects
    it (−16 LUFS). The approved read is never touched — this is a copy."""
    out = work / "voice.level.wav"  # wav: an mp3 re-encode adds its own delay
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11", "-ar", "48000", str(out)], check=True)
    return out


def level_clip(src: Path, work: Path, target: float = -16.0) -> Path:
    """A talking clip carries its own sound — that is what keeps the lips right.
    Level a COPY: picture stream untouched, sound to −16 LUFS."""
    out = work / f"{src.stem}.level.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "copy", "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out)], check=True)
    return out


def clip_words(clip: dict, kit_dir: Path, work: Path) -> list[dict]:
    w = clip.get("words")
    if isinstance(w, list):
        return w
    return words_for({"voice": {"src": clip["src"], "words": w}}, kit_dir, work)


def speech_segments(words: list[dict], max_pause: float, lead: float = 0.10, tail: float = 0.14) -> list[tuple[float, float]]:
    """Source-time spans to KEEP: split wherever the silence between two words
    is longer than the pace dial allows, leaving a breath on each side."""
    segs, start, last = [], None, None
    for w in words:
        if start is None:
            start = max(0.0, w["start"] - lead)
        elif w["start"] - last["end"] > max_pause:
            half = max_pause / 2
            segs.append((start, last["end"] + min(tail, half)))
            start = w["start"] - min(lead, half)
        last = w
    if start is not None:
        segs.append((start, last["end"] + tail))
    return [(round(a, 3), round(b, 3)) for a, b in segs]


def span_of(cover, words: list[dict], after: float = 0.0) -> tuple[float, float]:
    """Where a B-roll clip goes. `cover` is [from_s, to_s], or {"from": "<word(s)>",
    "to": "<word(s)>"} — named by the WORDS it covers, so it survives re-timing."""
    if isinstance(cover, (list, tuple)):
        return float(cover[0]), float(cover[1])
    norm = lambda t: re.sub(r"[^a-z0-9' ]", "", t.lower()).split()
    toks = [norm(w["text"])[0] if norm(w["text"]) else "" for w in words]

    def find(phrase, begin):
        p = norm(phrase)
        for i in range(begin, len(toks) - len(p) + 1):
            if toks[i:i + len(p)] == p:
                return i, i + len(p) - 1
        raise SystemExit(f"b-roll cover `{phrase}` is not in the spoken words")
    i0 = next((i for i, w in enumerate(words) if w["start"] >= after), 0)
    f0, _ = find(cover["from"], i0)
    _, t1 = find(cover["to"], f0)
    return words[f0]["start"], words[t1]["end"]


def auto_cut(kit: dict, kit_dir: Path, work: Path, controls: dict, brand: str, label: str, level: bool = True) -> dict:
    """The fallback cut. Talking A-roll keeps its own sound and is cut at every
    pause longer than the pace dial; B-roll is laid over the words it names.
    The model's cut (prompts/stage-2-cut) replaces this; the gate treats both the same."""
    pace = controls["pace"]; max_pause = pace["options"][pace["value"]]["max_pause"]
    snd, cv = controls["sound"], controls["canvas"]
    picture, words, voice_cuts, t = [], [], [], 0.0
    talking = [c for c in kit["clips"] if c["roll"] == "a" and c.get("talks")]
    for c in kit["clips"]:  # scene order is the kit's order
        if c["roll"] == "a" and c.get("talks"):
            cw = clip_words(c, kit_dir, work)
            src = str(level_clip(kit_dir / c["src"], work)) if level else c["src"]
            for n, (a, b) in enumerate(speech_segments(cw, max_pause)):
                picture.append({"id": f"{c['id']}-{n + 1}", "roll": "a", "src": src, "start": round(t, 3), "duration": round(b - a, 3), "source_start": a,
                                "scene": c.get("scene"), "still": False, "talks": True, "volume_db": snd["voice_db"], "punch": 1.0 if n % 2 == 0 else 1.07,
                                "why": (c.get("why") or "she says the line") + (f" — part {n + 1}, the pause before it cut" if n else "")})
                words += [{"text": w["text"], "start": round(w["start"] - a + t, 3), "end": round(w["end"] - a + t, 3)} for w in cw if a <= w["start"] < b]
                t += b - a
        elif c.get("voice"):  # B-roll over its slice of the voice read: no lips, so the voice is cut freely and the picture runs on
            cw = clip_words({"src": c["voice"]["src"], "words": c["voice"].get("words")}, kit_dir, work)
            vsrc = str(level_voice(kit_dir / c["voice"]["src"], work / c["id"])) if level else c["voice"]["src"]
            t0 = t
            for n, (a, b) in enumerate(speech_segments(cw, max_pause)):
                voice_cuts.append({"id": f"{c['id']}-v{n + 1}", "src": vsrc, "start": round(t, 3), "duration": round(b - a, 3), "source_start": a, "volume_db": snd["voice_db"]})
                words += [{"text": w["text"], "start": round(w["start"] - a + t, 3), "end": round(w["end"] - a + t, 3)} for w in cw if a <= w["start"] < b]
                t += b - a
            picture.append({"id": c["id"], "roll": "b", "src": c["src"], "start": round(t0, 3), "duration": round(t - t0, 3), "source_start": c.get("source_start", 0),
                            "scene": c.get("scene"), "still": bool(c.get("still")), "volume_db": None, "why": c.get("why") or "covers its slice of the voice"})
    voice = None
    if kit.get("voice") and not talking:  # a voiceover piece: the voice track is the clock
        words = words_for(kit, kit_dir, work)
        vsrc = str(level_voice(kit_dir / kit["voice"]["src"], work)) if level else kit["voice"]["src"]
        voice = {"src": vsrc, "start": 0, "volume_db": snd["voice_db"]}
    cursor = 0.0
    for c in kit["clips"]:
        if (c.get("talks") and c["roll"] == "a") or c.get("voice") or not c.get("covers"):
            continue  # a clip with no placement is the model cut's to place
        s, e = span_of(c["covers"], words, cursor)
        s = 0.0 if c.get("opens") else max(0.0, s - 0.08)
        e += 0.10
        cursor = e
        picture.append({"id": c["id"], "roll": c["roll"], "src": c["src"], "start": round(s, 3), "duration": round(e - s, 3), "source_start": c.get("source_start", 0),
                        "scene": c.get("scene"), "still": bool(c.get("still")), "volume_db": None, "why": c.get("why") or "covers the words it names"})
    overlays = []
    for o in kit.get("overlays") or []:
        o = dict(o)
        if o.get("with"):  # text that lives and dies with a clip — a hook on its scroll-stopper
            c = next(x for x in picture if x["id"] == o["with"])
            o["start"], o["duration"] = c["start"], c["duration"]
        overlays.append(o)
    return {"meta": {"brand": brand, "label": label, "format": kit.get("format"), "style_id": kit.get("style_id"), **cv},
            "controls": controls, "cut_by": "auto", "voice": voice, "voice_cuts": voice_cuts,
            "music": ({"src": kit["music"]["src"], "start": 0, "volume_db": snd["music_db"]} if kit.get("music") else None),
            "sfx": [{**x, "volume_db": snd["sfx_db"]} for x in kit.get("sfx") or []],
            "picture": picture, "captions": {"look": controls["caption_look"]["value"], "words": words, "fixes": []},
            "overlays": overlays}


def model_cut(kit: dict, kit_dir: Path, work: Path, run: Path, controls: dict, brand: str, label: str) -> dict:
    """The cut, decided by the model on top of the machine's lip-safe draft.
    The prompt as sent and the reply are saved beside the sheet. Any failure —
    no model, unreadable reply, a red sheet twice — falls back to the auto cut
    and says so on the sheet."""
    root = repo_root()
    sys.path.insert(0, str(root / "components" / "run-kit"))
    from run_kit import model as M, prompts as P
    placed = [c for c in kit["clips"] if c.get("talks") or c.get("voice")]
    loose = [c for c in kit["clips"] if not (c.get("talks") or c.get("voice"))]
    draft = auto_cut({**kit, "clips": placed, "overlays": []}, kit_dir, work, controls, brand, label)
    hook = next((o for o in kit.get("overlays") or [] if o.get("kind") == "hook"), None)
    brief = kit.get("brief")
    brief_text = (root / brief).read_text() if brief and (root / brief).is_file() else "none given"
    learned = read(TOOL / "learned.json", {"rules": []})["rules"]
    fields = {"draft": json.dumps({"picture": [{k: c[k] for k in ("id", "roll", "start", "duration")} for c in draft["picture"]],
                                   "voice_cuts": [{k: v[k] for k in ("id", "start", "duration")} for v in draft["voice_cuts"]],
                                   "words": draft["captions"]["words"], "ends_at": CS.end_of(draft)}, ensure_ascii=False),
              "broll": json.dumps([{"id": c["id"], "seconds": CS.probe_seconds(kit_dir / c["src"]), "shows": c.get("shows") or c.get("why"),
                                    "opens": bool(c.get("opens")), "kit_says": c.get("covers")} for c in loose], ensure_ascii=False),
              "brief": brief_text, "roll_map": json.dumps(kit.get("roll_map") or "none given", ensure_ascii=False),
              "hook": (hook or {}).get("text") or "none", "controls": json.dumps({k: controls[k] for k in ("caption_look", "sound", "safe_zone")}, ensure_ascii=False),
              "learned": json.dumps(learned, ensure_ascii=False) if learned else "nothing on file yet"}
    path = P.latest(TOOL / "prompts" / "stage-2-cut", "stage2-cut")
    sent = P.fill(Path(path).read_text(), fields)
    by_id = {c["id"]: c for c in loose}
    fix = ""
    for attempt in (1, 2):
        (run / f"stage2-cut--sent{'' if attempt == 1 else '-retry'}.md").write_text(sent + fix)
        mdl, _ = M.pick("designs", len(sent))
        reply = M.call(sent + fix, mdl, label="video-edit cut")
        (run / f"stage2-cut--reply{'' if attempt == 1 else '-retry'}.md").write_text(reply)
        try:
            d = json.loads(reply[reply.index("{"): reply.rindex("}") + 1])
            sheet = json.loads(json.dumps(draft))
            for b in d.get("broll") or []:
                c = by_id[b["id"]]
                sheet["picture"].append({"id": c["id"], "roll": "b", "src": c["src"], "start": round(float(b["start"]), 3), "duration": round(float(b["duration"]), 3),
                                         "source_start": round(float(b.get("source_start", 0)), 3), "scene": c.get("scene"), "still": bool(c.get("still")), "volume_db": None, "why": b.get("why", "")})
            sheet["overlays"] = d.get("overlays") or []
            sheet.update({"cut_by": f"model ({mdl}) on the machine's lip-safe draft · prompt {Path(path).name}", "missing": d.get("missing") or [], "notes_for_damon": d.get("notes_for_damon") or []})
            red = CS.check(sheet, kit_dir)
            if not red:
                return sheet
            fix = "\n\n## Your last answer was refused by the gate. Fix exactly these and answer again:\n" + "\n".join("- " + r for r in red)
        except Exception as e:  # unreadable reply
            fix = f"\n\n## Your last answer could not be read as JSON ({e}). Answer again with JSON only."
    sheet = auto_cut(kit, kit_dir, work, controls, brand, label)
    sheet["cut_by"] = "auto — the model's cut was refused twice; see stage2-cut--reply-retry.md"
    return sheet


def latest_sheet(run: Path) -> Path | None:
    sheets = sorted(run.glob("cutsheet-v*.json"), key=lambda p: int(p.stem.split("-v")[1]))
    return sheets[-1] if sheets else None


def render(run: Path, kit_dir: Path, sheet: dict, name: str, captions: bool, quality: str) -> Path:
    project = run / "work" / name
    C.compose(sheet, kit_dir, project, captions=captions)
    out = run / "work" / f"{name}.mp4"
    for cmd in (["hyperframes", "lint", str(project)],
                ["hyperframes", "render", str(project), "--output", str(out), "--quality", quality, "--quiet"]):
        r = subprocess.run(cmd, capture_output=True, text=True)
        (run / "work" / f"{name}.{cmd[1]}.log").write_text(r.stdout + r.stderr)
        if r.returncode != 0:
            raise SystemExit(f"{cmd[1]} failed — see {run / 'work' / (name + '.' + cmd[1] + '.log')}")
    return out


def final_checks(video: Path, sheet: dict) -> list[dict]:
    want = CS.end_of(sheet)
    have = CS.probe_seconds(video) or 0
    res = [{"check": "length matches the sheet", "pass": abs(have - want) < 0.25, "detail": f"{have:.2f}s rendered, {want:.2f}s on the sheet"}]
    black = subprocess.run(["ffmpeg", "-v", "info", "-i", str(video), "-vf", "blackdetect=d=0.2:pix_th=0.05", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    res.append({"check": "picture never goes black", "pass": "black_start" not in black, "detail": "no black frames" if "black_start" not in black else "black frames found"})
    loud = subprocess.run(["ffmpeg", "-v", "info", "-i", str(video), "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = None
    for line in loud.splitlines():
        if line.strip().startswith("I:") and "LUFS" in line:
            lufs = float(line.split("I:")[1].split("LUFS")[0])
    res.append({"check": "voice level in range", "pass": lufs is not None and -20 <= lufs <= -12, "detail": f"{lufs} LUFS (want −20 to −12)"})
    import syncheck
    for c in sheet["picture"]:
        if c.get("talks"):
            lag = syncheck.lag(video, c["start"], Path(c["src"]), c["source_start"], min(c["duration"], 4.0))
            res.append({"check": f"lips in time — {c['id']}", "pass": lag is not None and abs(lag) <= 0.045,
                        "detail": "could not measure" if lag is None else f"sound is {abs(lag) * 1000:.0f} ms {'late' if lag > 0 else 'early'} against her own clip (one frame is 42 ms)"})
    return res


# ---------------------------------------------------------------- commands
def start(a) -> int:
    kit_dir = Path(a.kit).resolve()
    runs_root = Path(a.runs_root).resolve() if a.runs_root else repo_root() / "runs" / "video-edit"
    run = runs_root / a.brand / a.label
    state = read(run / "run.json", {"machine": "video-edit", "brand": a.brand, "label": a.label, "kit": str(kit_dir), "started": now(), "steps": {}})
    controls = controls_for(Path(a.controls) if a.controls else None)
    first = STEPS.index(a.from_step) if a.from_step else 0

    def done(step, **kw):
        state["steps"][step] = {"state": "done", "at": now(), **kw}
        if not a.dry_run:
            write(run / "run.json", state)

    kit, red = gather(kit_dir)
    if red:
        print("\n".join("RED   " + r for r in red)); return 1
    if first <= STEPS.index("gather"):
        done("gather", clips=len(kit["clips"]), a_roll=sum(c["roll"] == "a" for c in kit["clips"]), b_roll=sum(c["roll"] == "b" for c in kit["clips"]))

    work = run / "work"
    sheet_path = latest_sheet(run)
    if first <= STEPS.index("cut") or sheet_path is None:
        import tempfile
        if a.dry_run:
            sheet = auto_cut(kit, kit_dir, Path(tempfile.mkdtemp()), controls, a.brand, a.label, level=False)
        else:
            work.mkdir(parents=True, exist_ok=True)
            try:
                sheet = model_cut(kit, kit_dir, work, run, controls, a.brand, a.label) if a.cut == "model" else auto_cut(kit, kit_dir, work, controls, a.brand, a.label)
            except Exception as e:
                sheet = auto_cut(kit, kit_dir, work, controls, a.brand, a.label)
                sheet["cut_by"] = f"auto — the model could not be reached ({type(e).__name__})"
            sheet_path = run / "cutsheet-v1.json"
            write(sheet_path, sheet)
            done("cut", by=sheet["cut_by"], sheet=sheet_path.name)
    else:
        sheet = read(sheet_path)

    red = CS.check(sheet, kit_dir)
    if red:
        print("\n".join("RED   " + r for r in red)); print(f"{len(red)} to fix — nothing renders red"); return 1
    print(f"GREEN  gate — {len(sheet['picture'])} clips, {CS.end_of(sheet):.2f}s, {len(sheet['captions']['words'])} timed words")
    if a.dry_run:
        print("dry run: every input checked, nothing rendered, nothing filed"); return 0
    done("gate")

    stops = state.setdefault("stops", {})
    if stops.get("timeline") != "approved":
        rough = render(run, kit_dir, sheet, "rough-cut", captions=False, quality="draft")
        page = TP.write(run, sheet, stage="timeline", video=rough)
        stops["timeline"] = "waiting"; write(run / "run.json", state)
        print(f"STOP 1 — the timeline: {page}"); return 0
    if stops.get("captions") != "approved":
        cap = render(run, kit_dir, sheet, "captioned", captions=True, quality="draft")
        page = TP.write(run, sheet, stage="captions", video=cap)
        stops["captions"] = "waiting"; write(run / "run.json", state)
        print(f"STOP 2 — the captions: {page}"); return 0

    final = render(run, kit_dir, sheet, "final", captions=sheet["controls"]["captions"]["value"] == "on", quality=controls["quality"])
    done("export", file=str(final))
    checks = final_checks(final, sheet)
    write(run / "deliverable" / "checks.json", checks)
    done("checks", passed=all(c["pass"] for c in checks))
    write(run / "deliverable" / "cutsheet.json", sheet)
    done("file", note="record filed; the video goes to the same path on the Drive under the naming convention")
    TP.write(run, sheet, stage="done", video=final, checks=checks)
    for c in checks:
        print(("PASS  " if c["pass"] else "HELD  ") + c["check"] + " — " + c["detail"])
    print(f"final: {final}")
    return 0 if all(c["pass"] for c in checks) else 1


def from_run(a) -> int:
    import kit_from_run as K
    kit, notes = K.build(Path(a.vm_run))
    runs_root = Path(a.runs_root).resolve() if a.runs_root else repo_root() / "runs" / "video-edit"
    kit_dir = runs_root / kit["brand"] / kit["label"] / "kit"
    write(kit_dir / "edit-kit.json", kit)
    ok = [c for c in kit["clips"] if c["approved"]]
    print(f"kit written: {kit_dir / 'edit-kit.json'}")
    print(f"{len(kit['clips'])} clips found · {len(ok)} approved · {sum(1 for c in kit['clips'] if c.get('talks'))} talking A-roll · {sum(1 for c in kit['clips'] if c.get('voice'))} B-roll over voice")
    for n in notes:
        print("  note  " + n)
    print(f"next: run.py start {kit_dir} --brand {kit['brand']} --label {kit['label']}")
    return 0


def approve(a) -> int:
    run = Path(a.run).resolve(); state = read(run / "run.json")
    state.setdefault("stops", {})[a.stop] = "approved"
    state.setdefault("approvals", []).append({"stop": a.stop, "at": now(), "note": a.note})
    write(run / "run.json", state)
    print(f"{a.stop} approved — run `start` again to carry on"); return 0


def change(a) -> int:
    run = Path(a.run).resolve(); state = read(run / "run.json")
    sheet_path = latest_sheet(run)
    n = int(sheet_path.stem.split("-v")[1]) + 1
    with (run / "changes.jsonl").open("a") as f:
        f.write(json.dumps({"at": now(), "stop": a.stop, "asked": a.ask, "why": a.why, "from": sheet_path.name, "to": f"cutsheet-v{n}.json"}, ensure_ascii=False) + "\n")
    write(run / f"cutsheet-v{n}.json", read(sheet_path))
    state.setdefault("stops", {})[a.stop] = "reopened"; write(run / "run.json", state)
    print(f"recorded. Edit {run / f'cutsheet-v{n}.json'} to do what was asked, then `start --from gate`.")
    return 0


def status(a) -> int:
    run = Path(a.run).resolve(); state = read(run / "run.json")
    for s in STEPS:
        st = (state["steps"].get(s) or {}).get("state") or state.get("stops", {}).get(s) or "—"
        print(f"{s:10} {st}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("kit"); s.add_argument("--brand", required=True); s.add_argument("--label", required=True)
    s.add_argument("--dry-run", action="store_true"); s.add_argument("--from", dest="from_step", choices=STEPS); s.add_argument("--controls"); s.add_argument("--runs-root"); s.add_argument("--cut", choices=["model", "auto"], default="model")
    s.set_defaults(fn=start)
    f = sub.add_parser("from-run"); f.add_argument("vm_run"); f.add_argument("--runs-root"); f.set_defaults(fn=from_run)
    p = sub.add_parser("approve"); p.add_argument("run"); p.add_argument("stop", choices=["timeline", "captions"]); p.add_argument("--note", default=""); p.set_defaults(fn=approve)
    c = sub.add_parser("change"); c.add_argument("run"); c.add_argument("stop", choices=["timeline", "captions"]); c.add_argument("ask"); c.add_argument("--why", default=""); c.set_defaults(fn=change)
    t = sub.add_parser("status"); t.add_argument("run"); t.set_defaults(fn=status)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
