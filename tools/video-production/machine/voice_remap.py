"""VOICES FOLLOW A RENUMBERED BRIEF — by their words, never re-recorded (2026-10-02).

the three-doctors run brief was rewritten from the frame map after its voices were made and
approved: three insert scenes came in, two lines were split across a cut, and
every scene from S5 on moved number. The words did not change. Re-recording would
throw away the takes the owner listened to; this keeps them:

    a scene whose line is word for word a recorded line   → that recording, copied
    a scene whose line is part of a recorded line          → the recording cut at
                                                             its words (speech-to-
                                                             text word times)
    anything else                                          → listed, never invented

The old vo/ is kept in vo/versions/<stamp>-before-remap/. Writes vo/<scene>.mp3,
lines.json and vo/manifest.json in the brief's numbering, and REMAP.json saying
where each came from. Brand-agnostic.

    python3 voice_remap.py <production run> --brief <brief.md> [--dry-run]
"""
import argparse, json, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
PAD = 0.06


def words(t):
    return re.sub(r"[^a-z0-9' ]", " ", (t or "").lower().replace("—", " ").replace("…", " ")).split()


def brief_lines(brief):
    body = Path(brief).read_text()
    doc = json.loads(re.findall(r"```json\s*\n(.*?)\n```", body, re.S)[-1])
    return [(s["id"], s["voice"], s.get("speaker")) for s in doc.get("scenes") or [] if (s.get("voice") or "").strip()]


def find_run(seq, sub, start=0):
    n = len(sub)
    for i in range(start, len(seq) - n + 1):
        if seq[i:i + n] == sub:
            return i
    return -1


def word_times(mp3, stt=None):
    """[(word, start, end)] for a recording — ElevenLabs speech-to-text."""
    if stt is None:
        import importlib.util as u
        sp = u.spec_from_file_location("vt_transcript", WS / "tools/video-teardown/machine/transcript.py")
        tr = u.module_from_spec(sp); sp.loader.exec_module(tr)
        stt = tr.scribe_only
    d = stt(mp3)
    out = []
    for w in d.get("words") or []:
        if w.get("type", "word") != "word":
            continue
        for x in words(w.get("text")):
            out.append((x, float(w["start"]), float(w["end"])))
    return out


def cut(src, dst, a, b):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{max(0.0, a):.3f}", "-to", f"{b:.3f}",
                    "-i", str(src), "-c:a", "libmp3lame", "-q:a", "2", str(dst)], check=True)


def remap(run, brief, dry_run=False, stt=None, source=None):
    """`source`: a kept vo/versions/<stamp>-before-remap folder to remap from again."""
    run = Path(run)
    src_dir = Path(source) if source else run / "vo"
    old = json.loads(((src_dir / "lines.json") if source else (run / "lines.json")).read_text())
    oman = json.loads((src_dir / "manifest.json").read_text())
    have = {k: (words(v), src_dir / f"{k}.mp3") for k, v in old.items() if (src_dir / f"{k}.mp3").exists()}
    plan, lost = {}, []
    bl = brief_lines(brief)
    for n, (sid, text, spk) in enumerate(bl):
        w = words(text)
        near = set(words(" ".join(t for _, t, _ in bl[max(0, n - 1):n + 2] if t != text)))
        exact = next((k for k, (ow, _) in have.items() if ow == w), None)
        if exact:
            plan[sid] = {"from": exact, "how": "same words", "text": text}
            continue
        parent = [k for k, (ow, _) in have.items() if find_run(ow, w) >= 0]
        if parent:
            # a split line came from the recording that also holds its neighbours' words
            best = max(parent, key=lambda k: (len(near & set(have[k][0])), -len(have[k][0])))
            plan[sid] = {"from": best, "how": "part of", "text": text}
        else:
            lost.append(sid)
    if dry_run:
        return plan, lost

    stamp = time.strftime("%Y%m%d-%H%M%S")
    if source:
        keep = Path(source)
    else:
        keep = run / "vo" / "versions" / f"{stamp}-before-remap"
        keep.mkdir(parents=True, exist_ok=True)
        for f in (run / "vo").glob("*.mp3"):
            shutil.copy2(f, keep / f.name)
        for f in ("manifest.json", "timing.json"):
            if (run / "vo" / f).exists():
                shutil.copy2(run / "vo" / f, keep / f)
        shutil.copy2(run / "lines.json", keep / "lines.json")
    stage = run / "vo" / f".remap-{stamp}"
    stage.mkdir()
    times, cursor = {}, {}
    for sid, p in plan.items():
        src = keep / f"{p['from']}.mp3"
        if p["how"] == "same words":
            shutil.copy2(src, stage / f"{sid}.mp3")
            continue
        if p["from"] not in times:
            times[p["from"]] = word_times(src, stt)
        wt = times[p["from"]]
        # the parts of one split recording are found in order, each after the last
        i = find_run([x[0] for x in wt], words(p["text"]), cursor.get(p["from"], 0))
        if i < 0:
            lost.append(sid); continue
        j = i + len(words(p["text"])) - 1
        cursor[p["from"]] = j + 1
        prev_end = wt[i - 1][2] if i > 0 else 0.0
        next_start = wt[j + 1][1] if j + 1 < len(wt) else wt[j][2] + 0.4
        a = max(prev_end, wt[i][1] - PAD) if i > 0 else 0.0
        b = min(next_start, wt[j][2] + 0.25) if j + 1 < len(wt) else wt[j][2] + 0.4
        cut(src, stage / f"{sid}.mp3", a, b)
        p["cut"] = [round(a, 3), round(b, 3)]
    for f in (run / "vo").glob("S*.mp3"):
        f.unlink()
    for f in stage.glob("*.mp3"):
        f.rename(run / "vo" / f.name)
    stage.rmdir()
    new_lines = {sid: p["text"] for sid, p in plan.items()}
    (run / "lines.json").write_text(json.dumps(new_lines, indent=1, ensure_ascii=False) + "\n")
    man = {}
    for sid, p in plan.items():
        rec = dict(oman.get(p["from"]) or {})
        rec.update({"file": f"vo/{sid}.mp3", "remapped_from": p["from"], "how": p["how"], "chars": len(p["text"])})
        man[sid] = rec
    (run / "vo" / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n")
    (run / "REMAP.json").write_text(json.dumps({"at": stamp, "brief": str(brief), "kept": str(keep),
                                                 "plan": plan, "not_found": lost}, indent=1, ensure_ascii=False) + "\n")
    return plan, lost


def seconds_of(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 3)
    except ValueError:
        return None


def refresh(run, brief, gap=0.15):
    """Everything downstream that reads the voices by scene number — timing.json
    (the clip door's durations), the manifest's start/end, the one track — is
    rebuilt in the brief's order from the recordings now in vo/ (2026-10-02, QC
    C1: the remap rewrote the manifest only, and timing still spoke the old
    numbering)."""
    run = Path(run).resolve()   # the concat list is read from vo/, so paths must be whole
    rm = json.loads((run / "REMAP.json").read_text()) if (run / "REMAP.json").exists() else {"plan": {}}
    keep = Path(rm.get("kept") or "")
    old_t = json.loads((keep / "timing.json").read_text()) if (keep / "timing.json").exists() else \
        json.loads((run / "vo" / "timing.json").read_text())
    man = json.loads((run / "vo" / "manifest.json").read_text())
    t = {k: v for k, v in old_t.items() if k not in ("voices", "scenes", "total", "at")}
    t["voices"], t["scenes"] = {}, {}
    clock, order = 0.0, []
    for sid, text, spk in brief_lines(brief):
        f = run / "vo" / f"{sid}.mp3"
        if not f.exists():
            continue
        src = (rm["plan"].get(sid) or {}).get("from", sid)
        sec = seconds_of(f) or 0.0
        base = dict((old_t.get("scenes") or {}).get(src) or {})
        if (rm["plan"].get(sid) or {}).get("how") == "part of":
            base.pop("lines", None)        # those windows were the whole recording's, not this cut's
        base.update({"start": round(clock, 3), "end": round(clock + sec, 3), "seconds": sec,
                     "file": f"vo/{sid}.mp3", "chars": len(text), "remapped_from": src})
        t["scenes"][sid] = base
        t["voices"][sid] = (old_t.get("voices") or {}).get(src) or {}
        if sid in man:
            man[sid].update({"start": base["start"], "end": base["end"]})
        order.append(f)
        clock += sec + gap
    t["total"] = round(clock - gap, 3) if order else 0.0
    t["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (run / "vo" / "timing.json").write_text(json.dumps(t, indent=1, ensure_ascii=False) + "\n")
    (run / "vo" / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n")
    if order:
        lst = run / "vo" / ".track-list.txt"
        sil = run / "vo" / ".gap.mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                        "-t", str(gap), "-c:a", "libmp3lame", "-q:a", "2", str(sil)], check=True)
        lst.write_text("".join(f"file '{f}'\nfile '{sil}'\n" for f in order))
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-q:a", "2", str(run / "vo" / "track.mp3")], check=True)
        lst.unlink(); sil.unlink()
    stale = run / "vo" / "audio-check.json"
    if stale.exists():
        stale.rename(run / "vo" / f"audio-check-before-remap-{time.strftime('%Y%m%d')}.json")
    return t


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run"); ap.add_argument("--brief", required=True); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-version", help="remap again from a kept vo/versions/<stamp>-before-remap folder")
    a = ap.parse_args()
    plan, lost = remap(a.run, a.brief, a.dry_run, source=a.from_version)
    if not a.dry_run:
        t = refresh(a.run, a.brief)
        print(f"timing, manifest and the track rebuilt in the brief's order: {len(t['scenes'])} lines, {t['total']} s")
    same = sum(1 for p in plan.values() if p["how"] == "same words")
    print(f"{len(plan)} line(s): {same} the same recording, {len(plan) - same} cut from a longer one"
          + (f" · NOT FOUND: {', '.join(lost)}" if lost else ""))
    for sid, p in plan.items():
        if p["how"] != "same words":
            print(f"  {sid} ← part of {p['from']}{' ' + str(p.get('cut')) if p.get('cut') else ''}: {p['text'][:70]}")
    sys.exit(1 if lost else 0)
