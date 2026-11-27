#!/usr/bin/env python3
"""from_higgsfield.py — the join between a Higgsfield preset film and the edit: takes a finished
Higgsfield run (its song, its scene clips laid on the song's windows, its sung lines) and writes the
edit kit this tool already cuts, so the cut, captions, hooks, covers and filing run here, not there.

    python3 machine/from_higgsfield.py <higgsfield run> [--label L] [--caption LOOK] [--hook ID=<clip file or url> …]

Reads `runs/higgsfield/<brand>/<run>/cut.json` ({song, clips:[{i, start, end, url}]}) and `lines.tsv`
(start, end, phrase) — both written by components/video-studio/higgsfield/hf_pack.py and the run.
Writes `runs/video-edit/<brand>/<label>/kit/` (song.mp3, clips/S01.mp4…, song-words.json,
edit-kit.json): a song-ad kit, the song the clock, each clip muted on its window.

Each `--hook ID=<clip>` writes a sibling kit `<label>-<id>` that is the same film with the opening
scene's picture swapped for the hook clip (same song, same windows: a scroll-stopper version, nothing
else changed); `@<seconds>` on the clip plays the hook only that far, then cuts into the original opening at the
same second. Its media is the control's, named repo-relative, never copied twice.

Covers, once the versions are rendered (the image tool's cover job, one per version, line.py's own pieces):
    python3 machine/from_higgsfield.py covers <out> --brand B --product P --ad AD --set SET --version "id|video|swipe|headline" …

Hand the versions to the Studio production, so its cover stage and the filer run on them:
    python3 machine/from_higgsfield.py to-studio <versions run> <studio production> --brief-key K --cast <ids> --covers covers.json

Then each kit runs the usual line: `python3 machine/run.py start <kit> --brand <brand> --label <label>`.
Nothing here generates a clip; downloads are the run's own finished files.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def repo() -> Path:
    for d in HERE.parents:
        if (d / "components").is_dir() and (d / "runs").is_dir():
            return d
    raise SystemExit("workspace not found")


def fetch(src: str, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_file() and dst.stat().st_size > 0:
        return dst
    if src.startswith("http"):
        req = urllib.request.Request(src, headers={"User-Agent": "video-edit"})
        with urllib.request.urlopen(req, timeout=120) as r, open(dst, "wb") as f:
            f.write(r.read())
    else:
        dst.write_bytes(Path(src).expanduser().read_bytes())
    return dst


def seconds(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out or 0)


def fps(p: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                          "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True).stdout.strip()
    a, _, b = out.partition("/")
    return int(round(float(a) / float(b or 1))) if a else 24


def words_from_lines(tsv: Path) -> list[dict]:
    """Each sung phrase's words spread evenly across the phrase's own span (the phrase times are the song's)."""
    out = []
    for row in tsv.read_text().splitlines():
        parts = row.split("\t")
        if len(parts) < 3 or not parts[2].strip():
            continue
        a, b, ws = float(parts[0]), float(parts[1]), parts[2].split()
        step = (b - a) / len(ws)
        out += [{"text": w, "start": round(a + i * step, 3), "end": round(a + (i + 1) * step - 0.02, 3)} for i, w in enumerate(ws)]
    return out


def song_words(root: Path, hf_run: Path) -> list[dict]:
    """The song's real word times: the transcript beside the song the pack sent (production's own, same clock),
    else each lyric line's words spread across the line (lines.tsv) — a fallback that groups captions unevenly."""
    pack = hf_run / "pack.json"
    song = json.loads(pack.read_text()).get("song") if pack.is_file() else None
    tr = (root / song).parent / "transcript.json" if song else None
    if tr and tr.is_file():
        d = json.loads(tr.read_text())
        ws = d["words"] if isinstance(d, dict) else d
        out = []
        for w in ws:
            t = (w.get("text") or "").strip()
            if w.get("type", "word") != "word" or not t:
                continue
            if out and not any(ch.isalnum() for ch in t):  # a lone mark ("." "…") belongs on the word before it
                if not out[-1]["text"].endswith(t):
                    out[-1]["text"] += t
                continue
            out.append({"text": t, "start": round(float(w["start"]), 3), "end": round(max(float(w["end"]), float(w["start"]) + 0.02), 3)})
        return out
    return words_from_lines(hf_run / "lines.tsv")


def build(hf_run: Path, label: str | None = None, hooks: list[str] | None = None, caption: str | None = None) -> list[Path]:
    root = repo()
    hf_run = hf_run.resolve()
    cut = json.loads((hf_run / "cut.json").read_text())
    brand = hf_run.parent.name
    label = label or hf_run.name.replace("singing-ads-", "")
    kit = root / "runs" / "video-edit" / brand / label / "kit"
    fetch(cut["song"], kit / "song.mp3")
    words = song_words(root, hf_run)
    (kit / "song-words.json").write_text(json.dumps({"words": words}, indent=1) + "\n")
    clips, short = [], []
    for c in cut["clips"]:
        sid = f"S{c['i'] + 1:02d}"
        f = fetch(c["url"], kit / "clips" / f"{sid}.mp4")
        need, have = c["end"] - c["start"], seconds(f)
        if have + 0.05 < need:
            short.append(f"{sid}: clip {have:.2f}s under a {need:.2f}s window — the last frame holds {need - have:.2f}s")
        clips.append({"id": sid, "src": f"clips/{sid}.mp4", "scene": sid, "approved": True, "roll": "a", "talks": False,
                      "covers": [round(c["start"], 3), round(c["end"], 3)], **({"opens": True} if c["i"] == 0 else {}),
                      "why": f"{sid} under its sung lines (Higgsfield {hf_run.name})", "hf_source": c["url"]})
    base = {"from_higgsfield": str(hf_run.relative_to(root)), "brand": brand, "label": label, "format": "song-ad",
            "style_id": "family-3d", "fps": fps(kit / clips[0]["src"]), "version": "control",
            "voice": {"src": "song.mp3", "words": "song-words.json", "kind": "the song (the script of record, the clock)",
                      "until_picture_ends": True},
            "music": None, "sfx": [], "overlays": [], "clips": clips, "held": [], "missing": [], "notes_for_owner": short}
    (kit / "edit-kit.json").write_text(json.dumps(base, indent=1) + "\n")
    if caption:  # the job's own caption look (looks/bank.json id), read by run.py --controls and v2.py
        (kit / "controls.json").write_text(json.dumps({"caption_look": {"value": caption}}, indent=1) + "\n")
    made = [kit]
    rel = lambda p: str(p.relative_to(root))  # noqa: E731
    for h in hooks or []:
        hid, _, src = h.partition("=")
        until = None  # ID=<clip>@<seconds>: the hook plays to that second, then the original opening carries on from there
        if "@" in src.rsplit("/", 1)[-1]:
            src, _, at = src.rpartition("@")
            until = float(at)
        hkit = root / "runs" / "video-edit" / brand / f"{label}-{hid}" / "kit"
        hclip = fetch(src, hkit / "clips" / f"{hid}.mp4")
        hk = json.loads(json.dumps(base))
        (hkit / "song-words.json").write_text((kit / "song-words.json").read_text())  # words are read kit-relative; the song itself is shared
        hk.update(label=f"{label}-{hid}", version=hid, voice={**base["voice"], "src": rel(kit / "song.mp3")})
        for c in hk["clips"]:
            c["src"] = rel(kit / c["src"])
        first = hk["clips"][0]
        need, have = first["covers"][1] - first["covers"][0], seconds(hclip)
        first.update(id=f"{hid}-{first['scene']}", src=f"clips/{hid}.mp4", why=f"hook {hid}: the scroll-stopper opens on its own clip",
                     hf_source=src if src.startswith("http") else None)
        hk["notes_for_owner"] = [n for n in hk["notes_for_owner"] if not n.startswith(first["scene"])] + (
            [f"{hid}: hook clip {have:.2f}s under a {need:.2f}s window"] if have + 0.05 < need and until is None else [])
        if until is not None:
            a0, b0 = first["covers"]
            cut_at = round(a0 + until, 3)
            if not a0 < cut_at < b0:
                raise SystemExit(f"{hid}: @{until} falls outside the opening window {a0}–{b0}")
            first["covers"] = [a0, cut_at]
            rest = {**base["clips"][0], "src": rel(kit / base["clips"][0]["src"]), "covers": [cut_at, b0], "source_start": round(until, 3),
                    "id": f"{base['clips'][0]['id']}-rest", "why": f"the original opening from {until}s, after hook {hid}"}
            rest.pop("opens", None)
            hk["clips"].insert(1, rest)
        (hkit / "edit-kit.json").write_text(json.dumps(hk, indent=1) + "\n")
        if caption:
            (hkit / "controls.json").write_text((kit / "controls.json").read_text())
        made.append(hkit)
    return made


def covers(out: Path, brand: str, product, ad: str, set_: str, versions: list[str]) -> dict:
    """One cover per version through the image tool's cover job, the same pieces line.py step 5 uses: the version's
    strongest opener frame, its headline, the swipe it follows, the ad's filed 3D set, one type for every version.
    `versions` rows are `<id>|<video>|<swipe>|<headline>`. Writes <out>/covers/<id>/ and <out>/covers/covers.json."""
    import line as L
    rows = []
    for v in versions:
        parts = v.split("|")
        vid, video, swipe, headline = parts[:4]
        at = float(parts[4]) if len(parts) > 4 and parts[4] else None  # the second the cover line describes, else the biggest face
        rows.append((vid, Path(video).resolve(), swipe, headline.replace("\\n", "\n"), at))
    type_file = L.cover_type(brand, ad, product, [r[3] for r in rows], out / "covers" / "cover-type.json")
    got = {}
    for vid, video, swipe, headline, at in rows:
        folder = out / "covers" / vid
        folder.mkdir(parents=True, exist_ok=True)
        import tempfile
        if at is not None:
            t = at
        else:
            with tempfile.TemporaryDirectory() as tmp:
                t = L.cover_moment(video, Path(tmp))
        fr = folder / f"{vid}_frame.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(fr)], check=True)
        cmd = L.cover_cmd(brand, vid, fr, swipe, headline, folder, product=product, set_=set_, ad=ad, video=video,
                          t=round(t, 2), type_=type_file)
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(f"COVER {vid}: exit {r.returncode}  {(r.stdout or r.stderr).strip().splitlines()[-1:] }")
        if r.returncode != 0:
            print((r.stdout + r.stderr)[-1500:])
            continue
        pic = L.cover_delivered(folder, fr)
        got[vid] = {"file": str(pic), "version": vid, "swipe": swipe, "headline": headline, "set": set_,
                    "frame": {"video": str(video), "t": round(t, 2), "file": fr.name},
                    "made_by": "image-production make.py --purpose cover"}
    (out / "covers" / "covers.json").write_text(json.dumps(got, indent=1, ensure_ascii=False) + "\n")
    return got


def to_studio(versions_run: Path, production: Path, brief_key: str, cast: list, covers: dict) -> list:
    """Hand the finished versions to the Studio's production for its cover stage and the filer: the control as
    `rough-cut-v<N>-sdr.mp4`, each hook as `versions/<id>/<production>-<id>.mp4` (links to the edit's own masters,
    never copies), and brief.json given the brief key, brand, cast, hooks and the ad's own cover choices (`covers`).
    Fields the production already has are kept unless named here."""
    deliv = versions_run / "deliverable"
    n = production.name
    made = []
    ctrl = next(deliv.glob("*_control.mp4"))
    k = 1 + max([int(m.group(1)) for f in production.glob("rough-cut-v*-sdr.mp4") for m in [re.search(r"-v(\d+)-", f.name)] if m] or [0])
    dst = production / f"rough-cut-v{k}-sdr.mp4"
    dst.symlink_to(ctrl.resolve()); made.append(dst)
    hooks = []
    for f in sorted(deliv.glob("*.mp4")):
        if f == ctrl:
            continue
        hid = "H" + f.stem.rsplit("-h", 1)[-1]
        d = production / "versions" / hid
        d.mkdir(parents=True, exist_ok=True)
        dst = d / f"{n}-{hid}.mp4"
        if dst.is_symlink() or dst.exists():
            dst.unlink()
        dst.symlink_to(f.resolve()); made.append(dst); hooks.append(hid)
    bj = production / "brief.json"
    b = json.loads(bj.read_text()) if bj.is_file() else {}
    b.update(brief_key=brief_key, brand=brief_key.split("_", 1)[0], cast=cast, hooks=hooks, covers={**(b.get("covers") or {}), **covers})
    bj.write_text(json.dumps(b, indent=1, ensure_ascii=False) + "\n")
    return made


def main(argv=None) -> int:
    if argv is None and len(sys.argv) > 1 and sys.argv[1] == "to-studio":
        ap = argparse.ArgumentParser(prog="from_higgsfield.py to-studio")
        ap.add_argument("versions_run"); ap.add_argument("production"); ap.add_argument("--brief-key", required=True)
        ap.add_argument("--cast", nargs="+", required=True); ap.add_argument("--covers", required=True, help="the ad's cover choices, a JSON file")
        a = ap.parse_args(sys.argv[2:])
        for f in to_studio(Path(a.versions_run), Path(a.production), a.brief_key, a.cast, json.loads(Path(a.covers).read_text())):
            print("LINKED", f)
        return 0
    if argv is None and len(sys.argv) > 1 and sys.argv[1] == "covers":
        ap = argparse.ArgumentParser(prog="from_higgsfield.py covers")
        ap.add_argument("out"); ap.add_argument("--brand", required=True); ap.add_argument("--product", help="only when the cover line calls for the product: it is laid in from its real model")
        ap.add_argument("--ad", required=True); ap.add_argument("--set", dest="set_", required=True)
        ap.add_argument("--version", action="append", required=True, help="<id>|<video>|<swipe>|<headline, \\n between lines>")
        a = ap.parse_args(sys.argv[2:])
        got = covers(Path(a.out), a.brand, a.product, a.ad, a.set_, a.version)
        return 0 if len(got) == len(a.version) else 1
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run", help="runs/higgsfield/<brand>/<run>")
    ap.add_argument("--label")
    ap.add_argument("--caption", default=None, help="caption look id from looks/bank.json; default: the bank's pick (tiktok-native, lower third, owner 2026-11-21)")
    ap.add_argument("--hook", action="append", default=[], help="ID=<clip file or url>[@seconds]: a version opening on that clip; @s plays it only to that second, then the original opening carries on")
    a = ap.parse_args(argv)
    for k in build(Path(a.run), a.label, a.hook, a.caption):
        kit = json.loads((k / "edit-kit.json").read_text())
        print(f"KIT   {k}  ({len(kit['clips'])} clips{'; ' + '; '.join(kit['notes_for_owner']) if kit['notes_for_owner'] else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
