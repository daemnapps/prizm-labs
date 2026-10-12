#!/usr/bin/env python3
"""run.py — the one command for the video edit.

    python3 machine/run.py handoff <video-editor hand-off folder> [--dry-run] [--approve timeline|captions]   # THE VIDEO EDITOR: hand-off in, 9:16 master in its returned/, two stops
    python3 machine/run.py pack <handoff.zip|folder> --brand <brand> --label <label> [--stops]   # an editor handoff in, the finished video out
    python3 machine/run.py from-run <video-production-run-folder>          # the join: writes the kit from a production run
    python3 machine/run.py start  <kit-folder> --brand <brand> --label <label> [--dry-run] [--from <step>] [--controls <file>]
    python3 machine/run.py approve <run-folder> timeline|captions [--note "..."]
    python3 machine/run.py change  <run-folder> timeline|captions "what to change, in plain words" [--why "..."]
    python3 machine/run.py status  <run-folder>
    python3 machine/run.py render  <run-folder> [--only <version-id>...]   # every hook + cutdown from one cut sheet, 9:16 only

A KIT is what production hands over — `edit-kit.json` beside the media it names:

    voice     {src, words: <file of [{text,start,end}]> | null}
    music     {src} | null          sfx  [{id, src, at, for}]
    clips     [{id, src, roll: "a"|"b", scene, covers: [from_s, to_s], approved: true, still?: bool, source_start?: s}]
    brief     <path> | null         format / style_id  (element ids)

The run stops twice for the owner (steps.json): the TIMELINE, then the CAPTIONS.
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
import assemble as A  # noqa: E402
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


def format_look(controls: dict, kit: dict, override: dict) -> dict:
    """A kit's format picks its caption look (defaults.json caption_look.by_format — a song ad: the
    word box, the owner 2026-10-10) unless the run's own controls.json names one."""
    cl = controls.get("caption_look") or {}
    pick = (cl.get("by_format") or {}).get(kit.get("format") or "")
    if pick and "caption_look" not in (override or {}):
        controls = {**controls, "caption_look": {**cl, "value": pick}}
    return controls


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
    norm = lambda t: re.sub(r"[^a-z0-9' ]", " ", t.lower()).split()  # noqa: E731
    toks, of = [], []  # a word in the script's spelling may be several tokens ("five-star") — each keeps its word
    for k, w in enumerate(words):
        for tk in norm(w["text"]) or [""]:
            toks.append(tk); of.append(k)

    def find(phrase, begin):
        p = norm(phrase)
        for i in range(begin, len(toks) - len(p) + 1):
            if toks[i:i + len(p)] == p:
                return i, i + len(p) - 1
        raise SystemExit(f"b-roll cover `{phrase}` is not in the spoken words")
    i0 = next((i for i, k in enumerate(of) if words[k]["start"] >= after), 0)
    f0, _ = find(cover["from"], i0)
    _, t1 = find(cover["to"], f0)
    return words[of[f0]]["start"], words[of[t1]]["end"]


def auto_cut(kit: dict, kit_dir: Path, work: Path, controls: dict, brand: str, label: str, level: bool = True) -> dict:
    """The fallback cut. Talking A-roll keeps its own sound and is cut at every
    pause longer than the pace dial; B-roll is laid over the words it names.
    The model's cut (prompts/stage-2-cut) replaces this; the gate treats both the same."""
    pace = controls["pace"]; max_pause = pace["options"][pace["value"]]["max_pause"]
    snd, cv = controls["sound"], controls["canvas"]
    picture, words, voice_cuts, t = [], [], [], 0.0
    pauses: list[dict] = []    # every mid-clip pause the trim cut or kept — the live timeline's Pauses lane (T-3)
    spelling: list[str] = []   # where the script's spelling could not be laid on the heard words
    past_end: list[str] = []   # talking clips whose word timings ran past the clip's own end
    mark_from = float((controls.get("pauses") or {}).get("mark_from_s", 0.35))
    talking = [c for c in kit["clips"] if c["roll"] == "a" and c.get("talks")]

    def scripted(c: dict, cw: list[dict]) -> list[dict]:
        """The heard words in the script's spelling (spelling.py) — the line production wrote, the swaps it sent."""
        if not cw or not c.get("line"):
            return cw
        import spelling as SP
        got, notes = SP.align(cw, c["line"], c.get("said"))
        spelling.extend(f"{c['id']}: {n}" for n in notes)
        return got

    def on_clock(w: dict, a: float, t0: float) -> dict:
        return {"text": w["text"], "start": round(w["start"] - a + t0, 3), "end": round(w["end"] - a + t0, 3),
                **{k: w[k] for k in ("heard", "unaligned") if w.get(k)}}

    def mark_pauses(cid: str, cw: list[dict], segs: list[tuple[float, float]], starts: list[float], what: str) -> None:
        """Every gap between two words that is a real pause (≥ mark_from, or cut by the pace dial): kept or cut, where on the final clock."""
        seg_of = lambda s: next((n for n, (a, b) in enumerate(segs) if a <= s < b + 1e-6), None)  # noqa: E731
        for x, y in zip(cw, cw[1:]):
            gap = round(y["start"] - x["end"], 3)
            if gap < mark_from and gap <= max_pause:
                continue  # a breath: always kept, never marked
            nx, ny = seg_of(x["start"]), seg_of(y["start"])
            if nx is None or ny is None:
                continue
            row = {"clip": cid, "what": what, "after": x["text"], "before": y["text"], "length": gap,
                   "source": [round(x["end"], 3), round(y["start"], 3)], "pace_max": max_pause}
            if nx == ny:
                a = segs[nx][0]
                row.update(action="kept", start=round(x["end"] - a + starts[nx], 3), end=round(y["start"] - a + starts[nx], 3))
            else:
                left = round(segs[nx][1] - x["end"] + y["start"] - segs[ny][0], 3)
                row.update(action="cut", at=round(starts[ny], 3), removed=round(gap - left, 3), left=left)
            pauses.append(row)

    for c in kit["clips"]:  # scene order is the kit's order
        if c["roll"] == "a" and c.get("talks"):
            cw = scripted(c, clip_words(c, kit_dir, work) if c.get("speaks", True) else [])
            src = str(level_clip(kit_dir / c["src"], work)) if level else c["src"]
            src_len = CS.probe_seconds(kit_dir / c["src"])
            segs = speech_segments(cw, max_pause) if cw else [(0.0, src_len or 0.0)]  # no words (room tone): the clip runs whole
            if src_len and cw:  # the sound ends where the clip ends (CUT-1): the word tool stretches the last word, and its breath, past it
                past = [w["text"] for w in cw if w["end"] > src_len + 0.05]
                if past:
                    past_end.append(f"{c['id']}: the word timings run {max(w['end'] for w in cw) - src_len:.2f}s past the clip's end ({src_len:.2f}s) "
                                    f"on “{' '.join(past)}” — the cut stops at the clip's last frame; listen for a line that stops short (T-7)")
                segs = [(a, round(min(b, src_len), 3)) for a, b in segs if a < src_len - 0.05]
                cw = [{**w, "end": min(w["end"], src_len)} for w in cw if w["start"] < src_len]
            starts = []
            for n, (a, b) in enumerate(segs):
                starts.append(round(t, 3))
                picture.append({"id": f"{c['id']}-{n + 1}", "roll": "a", "src": src, "start": round(t, 3), "duration": round(b - a, 3), "source_start": a,
                                "scene": c.get("scene"), "still": False, "talks": True, "volume_db": snd["voice_db"], "punch": 1.0 if n % 2 == 0 else 1.07,
                                "why": (c.get("why") or "she says the line") + (f" — part {n + 1}, the pause before it cut" if n else "")})
                words += [on_clock(w, a, t) for w in cw if a <= w["start"] < b]
                t += b - a
            if cw:
                mark_pauses(c["id"], cw, segs, starts, "talking clip — picture and sound cut together")
        elif "hold" in c and not c.get("voice"):  # a silent plate (card · screen · split · endcard): it carries the moment alone, for its hold
            import assemble as A
            d = A.hold_for(c)
            picture.append({"id": c["id"], "roll": "a", "src": c["src"], "start": round(t, 3), "duration": round(d, 3), "source_start": c.get("source_start", 0),
                            "scene": c.get("scene"), "still": bool(c.get("still")), "talks": False, "volume_db": None, "why": c.get("why") or "the plate carries this moment"})
            t += d
        elif c.get("voice"):  # B-roll over its slice of the voice read: no lips, so the voice is cut freely and the picture runs on
            cw = scripted(c, clip_words({"src": c["voice"]["src"], "words": c["voice"].get("words")}, kit_dir, work))
            vsrc = str(level_voice(kit_dir / c["voice"]["src"], work / c["id"])) if level else c["voice"]["src"]
            t0 = t
            segs, starts = speech_segments(cw, max_pause), []
            for n, (a, b) in enumerate(segs):
                starts.append(round(t, 3))
                voice_cuts.append({"id": f"{c['id']}-v{n + 1}", "src": vsrc, "start": round(t, 3), "duration": round(b - a, 3), "source_start": a, "volume_db": snd["voice_db"]})
                words += [on_clock(w, a, t) for w in cw if a <= w["start"] < b]
                t += b - a
            mark_pauses(c["id"], cw, segs, starts, "voice slice under B-roll — sound only")
            picture.append({"id": c["id"], "roll": "b", "src": c["src"], "start": round(t0, 3), "duration": round(t - t0, 3), "source_start": c.get("source_start", 0),
                            "scene": c.get("scene"), "still": bool(c.get("still")), "volume_db": None, "why": c.get("why") or "covers its slice of the voice"})
    voice = None
    if kit.get("voice") and not talking:  # a voiceover piece: the voice track is the clock
        words = words_for(kit, kit_dir, work)
        vsrc = str(level_voice(kit_dir / kit["voice"]["src"], work)) if level else kit["voice"]["src"]
        voice = {"src": vsrc, "start": 0, "volume_db": snd["voice_db"]}
        if kit["voice"].get("until_picture_ends"):  # a song bed with a tail: it stops when the picture does
            last = max((c["covers"][1] for c in kit["clips"] if isinstance(c.get("covers"), list)), default=None)
            if last:
                voice["duration"] = round(last, 3)
                words = [w for w in words if w["end"] <= last]
    cursor = 0.0
    for c in kit["clips"]:
        if (c.get("talks") and c["roll"] == "a") or c.get("voice") or not c.get("covers"):
            continue  # a clip with no placement is the model cut's to place
        s, e = span_of(c["covers"], words, cursor)
        if not isinstance(c["covers"], list):  # placed by words: a hair before the first, a hair after the last
            s = 0.0 if c.get("opens") else max(0.0, s - 0.08)
            e += 0.10
        cursor = e
        picture.append({"id": c["id"], "roll": c["roll"], "src": c["src"], "start": round(s, 3), "duration": round(e - s, 3), "source_start": c.get("source_start", 0),
                        "scene": c.get("scene"), "still": bool(c.get("still")), "volume_db": None, "why": c.get("why") or "covers the words it names"})
    overlays = []
    for o in kit.get("overlays") or []:
        o = dict(o)
        if o.get("with"):  # text that lives and dies with a clip — a hook on its scroll-stopper; a clip cut at its pauses is all its parts
            parts = [x for x in picture if x["id"] == o["with"] or x["id"].startswith(o["with"] + "-")]
            if not parts:
                continue
            o["start"] = min(x["start"] for x in parts)
            o["duration"] = round(max(x["start"] + x["duration"] for x in parts) - o["start"], 3)
        overlays.append(o)
    if kit.get("fps"):
        cv = {**cv, "fps": int(round(float(kit["fps"])))}
    return {"meta": {"brand": brand, "label": label, "format": kit.get("format"), "style_id": kit.get("style_id"), **cv},
            "held": kit.get("held") or [], "missing": kit.get("missing") or [], "notes_for_damon": (kit.get("notes_for_damon") or []) + past_end,
            "controls": controls, "cut_by": "auto", "voice": voice, "voice_cuts": voice_cuts,
            "music": ({"src": kit["music"]["src"], "start": 0, "volume_db": snd["music_db"]} if kit.get("music") else None),
            "sfx": [{**x, "volume_db": snd["sfx_db"]} for x in kit.get("sfx") or []],
            "picture": picture, "captions": {"look": controls["caption_look"]["value"], "words": words, "fixes": [], "spelling": spelling},
            "pauses": pauses, "overlays": overlays}


def model_cut(kit: dict, kit_dir: Path, work: Path, run: Path, controls: dict, brand: str, label: str) -> dict:
    """The cut, decided by the model on top of the machine's lip-safe draft.
    The prompt as sent and the reply are saved beside the sheet. Any failure —
    no model, unreadable reply, a red sheet twice — falls back to the auto cut
    and says so on the sheet."""
    root = repo_root()
    sys.path.insert(0, str(root / "components" / "run-kit"))
    from run_kit import model as M, prompts as P
    placed = [c for c in kit["clips"] if c.get("talks") or c.get("voice") or "hold" in c]
    loose = [c for c in kit["clips"] if not (c.get("talks") or c.get("voice") or c.get("covers") or "hold" in c)]
    if not loose:  # every clip is already placed by the handoff: nothing for the model to decide
        sheet = auto_cut(kit, kit_dir, work, controls, brand, label)
        sheet["cut_by"] = "the machine — every clip was already placed by the handoff, so the cut prompt had nothing to decide"
        return sheet
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
    # >>> APPROVAL-PAGE LEARNINGS HOOK (components/meta-upload/learnings.py) — adds nothing unless learnings-hooks.json turns "video-edit" on
    try:
        import importlib.util as _iu
        _ls = _iu.spec_from_file_location("meta_learnings", Path(__file__).resolve().parents[2] / "meta-upload" / "learnings.py")
        _L = _iu.module_from_spec(_ls); _ls.loader.exec_module(_L)
        sent += _L.prompt_block("video-edit", 7, brand)
    except Exception:
        pass
    # <<< APPROVAL-PAGE LEARNINGS HOOK
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


def helpers_pass(sheet: dict, kit_dir: Path, controls: dict, make_cutouts: bool = True) -> None:
    """The AI helpers (helpers venv — machine/helpers.py): MediaPipe tracks the faces in every
    clip a person can be in and the text is placed again off them (and annotations on the
    face follow them); BiRefNet cuts the presenter out of every greenscreen `cutout` scene
    (cached by the picture's hash); librosa finds the music's beats and the B-roll covers
    and graphic hits snap to them within the tolerance dial. No venv → placement keeps
    subject_box / face-blind, a cut-out scene shows the presenter whole (a WARN), beats
    come from the tempo grid. A dry run makes no cut-out — it only says which are cached."""
    import beats as BT
    import cutout as CO
    import faces as FC
    import follow as FL
    import placement as P
    notes = FC.attach(sheet, kit_dir)
    if any(c.get("face_track") for c in sheet.get("picture") or []):
        P.place(sheet)
    notes += CO.attach(sheet, kit_dir, make_missing=make_cutouts)
    BT.attach(sheet, kit_dir, controls)
    sheet["follow_notes"] = FL.apply(sheet)  # last: on the face track, and on each annotation's start AFTER the beat snap moved it
    sheet["helper_notes"] = notes + [f"beats: {len((sheet.get('music') or {}).get('beats') or [])} on the final clock ({(sheet.get('music') or {}).get('beats_by', 'no music')}); "
                                     f"{len(sheet.get('beat_snaps') or [])} snapped within {sheet.get('beat_snap_tolerance_s', '—')}s"] + (sheet.get("follow_notes") or [])
    for n in sheet["helper_notes"]:
        print("HELP  " + n)


def latest_sheet(run: Path) -> Path | None:
    sheets = sorted(run.glob("cutsheet-v*.json"), key=lambda p: int(p.stem.split("-v")[1]))
    return sheets[-1] if sheets else None


def render(run: Path, kit_dir: Path, sheet: dict, name: str, captions: bool, quality: str, out: Path | None = None) -> Path:
    project = run / "work" / name
    C.compose(sheet, kit_dir, project, captions=captions)
    out = out or run / "work" / f"{name}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    for cmd in (["hyperframes", "lint", str(project)],
                ["hyperframes", "render", str(project), "--output", str(out), "--quality", quality, "--quiet"]):
        r = subprocess.run(cmd, capture_output=True, text=True)
        (run / "work" / f"{name}.{cmd[1]}.log").write_text(r.stdout + r.stderr)
        if r.returncode != 0:
            raise SystemExit(f"{cmd[1]} failed — see {run / 'work' / (name + '.' + cmd[1] + '.log')}")
    if sheet.get("mix"):
        master(out, sheet["mix"])
    return out


def loudness(video: Path) -> tuple[float | None, float | None]:
    """Integrated LUFS and true peak (dBTP) of a file's sound, measured by ffmpeg's ebur128."""
    err = subprocess.run(["ffmpeg", "-nostats", "-v", "info", "-i", str(video), "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    lufs = tp = None
    summary = err[err.rfind("Summary:"):] if "Summary:" in err else err
    for line in summary.splitlines():
        t = line.strip()
        if t.startswith("I:") and "LUFS" in t:
            lufs = float(t.split("I:")[1].split("LUFS")[0])
        if t.startswith("Peak:") and "dBFS" in t:
            tp = float(t.split("Peak:")[1].split("dBFS")[0])
    return lufs, tp


def master(video: Path, mix: dict) -> dict:
    """The final mix: −14 LUFS integrated, −1 dBTP (the sheet's `mix`). Two passes of
    ffmpeg loudnorm on the sound only; the picture is copied untouched."""
    lufs, tp = mix.get("lufs", -14), mix.get("true_peak_db", -1)
    has_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(video)],
                               capture_output=True, text=True).stdout.strip()
    if not has_audio:
        return {"mastered": False, "why": "no sound in the file"}
    af = f"loudnorm=I={lufs}:TP={tp - 0.5}:LRA=11"
    err = subprocess.run(["ffmpeg", "-nostats", "-v", "info", "-i", str(video), "-af", af + ":print_format=json", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = json.loads(err[err.rindex("{"): err.rindex("}") + 1])
    af2 = (af + f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
           f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    tmp = video.with_suffix(".master.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-c:v", "copy", "-af", af2 + f",alimiter=limit={10 ** ((tp - 0.3) / 20):.4f}:level=false",
                    "-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(tmp)], check=True)
    tmp.replace(video)
    got = loudness(video)
    return {"mastered": True, "lufs": got[0], "true_peak_db": got[1]}


def creative_qc(tool, stage, run_dir, output, given=None, items=None):
    """THE CREATIVE QC LOOP (the owner, 2026-10-02: "installed for each of my
    production tools … for all stages in the creation process"): the output is
    reviewed against what it was given and the stage's bars
    (components/marketing-chain-checks/definitions/stages.json); the round is filed in
    <run>/qc-log/. Never stops the run on its own."""
    try:
        here = Path(__file__).resolve()
        comp = next(p for p in here.parents if (p / "marketing-chain-checks" / "marketing_chain_checks").is_dir())
        q = str(comp / "marketing-chain-checks")
        if q not in sys.path:
            sys.path.insert(0, q)
        from marketing_chain_checks import review
        f = review.after_stage(tool, stage, run_dir, output=output, items=items,
                               sources=[given] if given and Path(given).exists() else None)
        bad = [k for k, v in f.items() if isinstance(v, dict) and v.get("severity") in ("BLOCKER", "FIX")]
        if bad:
            print(f"  QC {stage}: {len(bad)} finding(s) — see qc-log/QC-LOG.md")
        return f
    except Exception as e:
        print(f"  QC {stage}: review not run ({type(e).__name__})")
        return {}


def final_checks(video: Path, sheet: dict) -> list[dict]:
    want = CS.end_of(sheet)
    have = CS.probe_seconds(video) or 0
    res = [{"check": "length matches the sheet", "pass": abs(have - want) < 0.25, "detail": f"{have:.2f}s rendered, {want:.2f}s on the sheet"}]
    black = subprocess.run(["ffmpeg", "-v", "info", "-i", str(video), "-vf", "blackdetect=d=0.2:pix_th=0.05", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    res.append({"check": "picture never goes black", "pass": "black_start" not in black, "detail": "no black frames" if "black_start" not in black else "black frames found"})
    lufs, tp = loudness(video)
    mix = sheet.get("mix") or {}
    if mix:
        want, ceil = mix.get("lufs", -14), mix.get("true_peak_db", -1)
        res.append({"check": "mix mastered", "pass": lufs is not None and abs(lufs - want) <= 1.0 and tp is not None and tp <= ceil + 0.1,
                    "detail": f"{lufs} LUFS integrated, {tp} dBTP peak (want {want} ±1 LUFS, peak at or under {ceil} dBTP)"})
    else:
        res.append({"check": "voice level in range", "pass": lufs is not None and -20 <= lufs <= -12, "detail": f"{lufs} LUFS (want −20 to −12)"})
    import syncheck
    for c in sheet["picture"]:
        if c.get("talks"):
            lag = syncheck.lag(video, c["start"], Path(c["src"]), c["source_start"], min(c["duration"], 4.0))
            res.append({"check": f"lips in time — {c['id']}", "pass": lag is not None and abs(lag) <= 0.045,
                        "detail": "could not measure" if lag is None else f"sound is {abs(lag) * 1000:.0f} ms {'late' if lag > 0 else 'early'} against her own clip (one frame is 42 ms)"})
    return res


def render_versions(run: Path, kit_dir: Path, sheet: dict, quality: str, only: list[str] | None = None) -> list[dict]:
    """Every version from ONE cut sheet (ELEMENTS.md §4, as the owner narrowed it 2026-09-23):
    one video per hook on the same body, the 15/30/60 cutdowns by priority, a cover per
    hook, every file named by components/naming — 9:16 only. Each version sheet is
    gated before it renders — nothing renders red."""
    import versions as V
    out_dir = run / "deliverable" / "versions"
    specs = [x for x in V.plan(sheet) if not only or x["id"] in only]
    batch = None
    try:
        for d in TOOL.parents:
            if (d / "components" / "naming" / "names.py").is_file():
                sys.path.insert(0, str(d / "components" / "naming"))
                import names as N
                batch = (sheet.get("name") or {}).get("batch") or N.next_batch(sheet["meta"]["brand"])
                break
    except Exception:
        batch = None
    rows = []
    for n, spec in enumerate(specs, 1):
        vs = V.variant(sheet, spec)
        red = CS.check(vs, kit_dir)
        name, note = V.file_name(vs, V.RATIO, n, batch)
        row = {"version": spec["id"], "ratio": V.RATIO, "hook": (spec.get("hook") or {}).get("id"), "length": spec["length"],
               "scenes": spec["order"], "dropped": spec.get("dropped"), "fits": spec.get("fits", True), "name": name, "name_note": note}
        if red:
            row.update(state="red", red=red)
            rows.append(row); print(f"RED   {spec['id']}: {red[0]}"); continue
        video = render(run, kit_dir, vs, f"v-{spec['id']}", captions=vs["controls"]["captions"]["value"] == "on", quality=quality,
                       out=out_dir / f"{name}.mp4")
        lufs, tp = loudness(video)
        row.update(state="made", file=str(video.relative_to(run)), seconds=CS.probe_seconds(video), lufs=lufs, true_peak_db=tp)
        if spec["length"] == "full":  # the cover: this hook's first frame, hook text on
            cover = out_dir / "covers" / f"{name}.png"
            cover.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0", "-i", str(video), "-frames:v", "1", str(cover)], check=True)
            row["cover"] = str(cover.relative_to(run))
        rows.append(row)
        print(f"MADE  {spec['id']:<10} {row['seconds']:.2f}s  {lufs} LUFS  {tp} dBTP  → {name}.mp4" + (f"   ({note})" if note else ""))
    write(out_dir / "manifest.json", {"from_sheet": (latest_sheet(run) or Path("?")).name, "batch": batch, "versions": rows})
    return rows


# ---------------------------------------------------------------- commands
def start(a) -> int:
    kit_dir = Path(a.kit).resolve()
    runs_root = Path(a.runs_root).resolve() if a.runs_root else repo_root() / "runs" / "video-edit"
    run = runs_root / a.brand / a.label
    import handoff_run as H  # kit_rel: run.json's kit is written from the repo root (triage page 12)
    state = read(run / "run.json", {"machine": "video-edit", "brand": a.brand, "label": a.label, "kit": H.kit_rel(kit_dir, repo_root()), "started": now(), "steps": {}})
    controls = controls_for(Path(a.controls) if a.controls else None)
    first = STEPS.index(a.from_step) if a.from_step else 0

    def done(step, **kw):
        state["steps"][step] = {"state": "done", "at": now(), **kw}
        if not a.dry_run:
            write(run / "run.json", state)

    kit, red = gather(kit_dir)
    if red:
        print("\n".join("RED   " + r for r in red)); return 1
    controls = format_look(controls, kit, read(Path(a.controls), {}) if a.controls else {})
    if first <= STEPS.index("gather"):
        done("gather", clips=len(kit["clips"]), a_roll=sum(c["roll"] == "a" for c in kit["clips"]), b_roll=sum(c["roll"] == "b" for c in kit["clips"]))

    work = run / "work"
    sheet_path = latest_sheet(run)
    if first <= STEPS.index("cut") or sheet_path is None:
        import tempfile
        if a.dry_run:
            sheet = auto_cut(kit, kit_dir, Path(tempfile.mkdtemp()), controls, a.brand, a.label, level=False)
            A.assemble(sheet, kit, controls, a.brand)
            helpers_pass(sheet, kit_dir, controls, make_cutouts=False)
        else:
            work.mkdir(parents=True, exist_ok=True)
            try:
                sheet = model_cut(kit, kit_dir, work, run, controls, a.brand, a.label) if a.cut == "model" else auto_cut(kit, kit_dir, work, controls, a.brand, a.label)
            except Exception as e:
                sheet = auto_cut(kit, kit_dir, work, controls, a.brand, a.label)
                sheet["cut_by"] = f"auto — the model could not be reached ({type(e).__name__})"
            A.assemble(sheet, kit, controls, a.brand)  # every element the kit carries, laid on the cut
            helpers_pass(sheet, kit_dir, controls)     # faces tracked per frame → text re-placed; music beats → snaps
            sheet_path = run / "cutsheet-v1.json"
            write(sheet_path, sheet)
            done("cut", by=sheet["cut_by"], sheet=sheet_path.name)
    else:
        sheet = read(sheet_path)

    red = CS.check(sheet, kit_dir)
    if red:
        print("\n".join("RED   " + r for r in red)); print(f"{len(red)} to fix — nothing renders red"); return 1
    print(f"GREEN  gate — {len(sheet['picture'])} clips, {CS.end_of(sheet):.2f}s, {len(sheet['captions']['words'])} timed words")
    for w in CS.warnings(sheet):  # renders, but not as asked — a font or icon not fetched, a face-blind scene, a layer moved off a face
        print("WARN  " + w)
    import retention as RT  # the retention checks: warnings and a score, never a block (the owner, 2026-09-23)
    print("\n".join(RT.lines(RT.check(sheet))))
    if a.dry_run:
        print("dry run: every input checked, nothing rendered, nothing filed"); return 0
    done("gate")

    stops = state.setdefault("stops", {})
    if a.straight:  # a test run: no stops, straight to the finished file; the page is where he says what to change
        for stop in ("timeline", "captions"):
            if stops.get(stop) != "approved":
                stops[stop] = "approved"
                state.setdefault("approvals", []).append({"stop": stop, "at": now(), "note": "straight-through test run — nobody looked at this stop"})
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
    # THE CREATIVE QC LOOP (2026-10-02): six frames of the finished cut, reviewed
    # against the cut sheet (what the brief and kit said would be on screen)
    try:
        qd = run / "deliverable" / "qc-frames"; qd.mkdir(parents=True, exist_ok=True)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(final)],
                                   capture_output=True, text=True).stdout.strip() or 0)
        frames_ = []
        for n in range(6):
            fp = qd / f"f{n + 1}.jpg"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{dur * (n + 0.5) / 6:.2f}", "-i", str(final),
                            "-frames:v", "1", "-vf", "scale=-2:960", str(fp)], check=True)
            frames_.append(fp)
        creative_qc("video-edit", "cut", run, None, items=[{"id": "cut", "output": frames_,
                    "compare": [run / "deliverable" / "cutsheet.json"] if (run / "deliverable" / "cutsheet.json").exists() else []}])
    except Exception as e:
        print(f"  QC cut: review not run ({type(e).__name__})")
    import retention as RT
    rt = RT.check(sheet, final)  # measured again on the rendered file: the loop score and the loudest words
    write(run / "deliverable" / "retention.json", rt)
    print("\n".join(RT.lines(rt)))
    done("checks", passed=all(c["pass"] for c in checks))
    write(run / "deliverable" / "cutsheet.json", sheet)
    done("file", note="record filed; the video goes to the same path on the Drive under the naming convention")
    TP.write(run, sheet, stage="done", video=final, checks=checks)
    for c in checks:
        print(("PASS  " if c["pass"] else "HELD  ") + c["check"] + " — " + c["detail"])
    print(f"final: {final}")
    if getattr(a, "versions", False):
        rows = render_versions(run, kit_dir, sheet, controls["quality"])
        done("versions", made=sum(r["state"] == "made" for r in rows), red=sum(r["state"] == "red" for r in rows))
    return 0 if all(c["pass"] for c in checks) else 1


def render_cmd(a) -> int:
    """Every version from the run's latest cut sheet — one per hook, the cutdowns, the covers (9:16 only)."""
    run = Path(a.run).resolve(); state = read(run / "run.json")
    sheet = read(latest_sheet(run))
    import handoff_run as H  # kit_dir_of: a repo-relative kit, or an old record's absolute one
    kit_dir = H.kit_dir_of(state, repo_root())
    red = CS.check(sheet, kit_dir)
    if red:
        print("\n".join("RED   " + r for r in red)); return 1
    rows = render_versions(run, kit_dir, sheet, a.quality or controls_for(None)["quality"], only=a.only)
    print(f"{sum(r['state'] == 'made' for r in rows)} made · {sum(r['state'] == 'red' for r in rows)} red — {run / 'deliverable' / 'versions' / 'manifest.json'}")
    return 0 if all(r["state"] == "made" for r in rows) else 1


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


def pack(a) -> int:
    """The front door: an editor handoff (zip or folder) in, the finished video out."""
    import kit_from_pack as K
    runs_root = Path(a.runs_root).resolve() if a.runs_root else repo_root() / "runs" / "video-edit"
    run = runs_root / a.brand / a.label
    kit_dir = run / "kit"
    print(f"reading the handoff: {a.pack}")
    kit, notes = K.build(Path(a.pack), kit_dir, run, a.brand, a.label)
    write(kit_dir / "edit-kit.json", kit)
    print(f"{len(kit['clips'])} clips in · {len(kit['held'])} held out · {len(kit['overlays'])} cards · {'bed: ' + kit['voice']['src'] if kit.get('voice') else 'each clip keeps its own sound'}")
    for h in kit["held"]:
        print(f"  held  {h.get('clip')}: {h.get('why')}")
    for m in kit["missing"]:
        print(f"  missing  {m}")
    for n in notes:
        print(f"  note  {n}")
    a.kit = str(kit_dir)
    return start(a)


def handoff(a) -> int:
    """The video editor as a tool (handoff_run.py): a video-editor hand-off folder in, the master
    in its returned/ out, stopping at the timeline and the captions; --approve carries on."""
    import handoff_run as H
    return H.run(a, sys.modules[__name__])


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
    s.add_argument("--straight", action="store_true", help="no stops: render the finished file straight away (a test run)")
    s.add_argument("--versions", action="store_true", help="after the final file, render every version (one per hook, the cutdowns, the covers) — 9:16 only")
    s.set_defaults(fn=start)
    r = sub.add_parser("render"); r.add_argument("run"); r.add_argument("--only", nargs="*"); r.add_argument("--quality")
    r.set_defaults(fn=render_cmd)
    k = sub.add_parser("pack"); k.add_argument("pack"); k.add_argument("--brand", required=True); k.add_argument("--label", required=True)
    k.add_argument("--straight", action="store_true", default=True); k.add_argument("--stops", dest="straight", action="store_false", help="stop at the timeline and captions like a normal run")
    k.add_argument("--dry-run", action="store_true"); k.add_argument("--controls"); k.add_argument("--runs-root"); k.add_argument("--cut", choices=["model", "auto"], default="model")
    k.set_defaults(fn=pack, from_step=None)
    h = sub.add_parser("handoff", help="a video-editor hand-off folder → one 9:16 master in its returned/, stopping at the two review points")
    h.add_argument("folder"); h.add_argument("--approve", choices=["timeline", "captions"]); h.add_argument("--note", default="")
    h.add_argument("--dry-run", action="store_true"); h.add_argument("--controls"); h.add_argument("--runs-root"); h.add_argument("--cut", choices=["model", "auto"], default="model")
    h.add_argument("--versions", action="store_true", help="after the master, also render one per hook and the cutdowns (open decision A-2)")
    h.set_defaults(fn=handoff)
    f = sub.add_parser("from-run"); f.add_argument("vm_run"); f.add_argument("--runs-root"); f.set_defaults(fn=from_run)
    p = sub.add_parser("approve"); p.add_argument("run"); p.add_argument("stop", choices=["timeline", "captions"]); p.add_argument("--note", default=""); p.set_defaults(fn=approve)
    c = sub.add_parser("change"); c.add_argument("run"); c.add_argument("stop", choices=["timeline", "captions"]); c.add_argument("ask"); c.add_argument("--why", default=""); c.set_defaults(fn=change)
    t = sub.add_parser("status"); t.add_argument("run"); t.set_defaults(fn=status)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
