#!/usr/bin/env python3
"""
pull.py — write a finished job from a hosted door into the brief, on disk.

Since 2026-09-18 the board's queue is drained by `drain.py` on the direct
doors, which writes takes and plan rows itself; this stays for the case
where a take was made in a house (Higgsfield, fal) and comes back as a URL.

    python3 pull.py <run> raw    A2=<url> A7=<url> ...
    python3 pull.py <run> voiced A2=<url> ...

The session that drained the queue hands the result URLs here. This downloads
them into cinema/raw/ or cinema/voiced/, records the job and the model beside
the beat, and then CHECKS THE ONE THING THAT MATTERS:

  A talking clip whose duration equals a voiceover file sample-for-sample was
  built by muxing audio onto a picture — the old route, the one that drifts.
  Cinema Studio picks its own length. If a clip matches an mp3 exactly, this
  says so, loudly, instead of letting it pass as the good thing.

It also refuses a silent clip: generate_audio true means the model speaks, and
a clip with no audio stream did not come from this stage.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path


def ffprobe(path: Path, stream: str) -> str:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", stream,
         "-show_entries", "stream=duration,codec_name",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True)
    return r.stdout.strip()



def archive(run: Path, kind: str, sid: str, row: dict, why: str) -> None:
    """Keep the take that is being replaced, with the reason it was replaced.

    Nothing is ever overwritten in place. A rejected take and the sentence
    explaining why it was rejected are the only record of what the prompt
    actually does, and that record is what stops the same mistake being made
    a third time.
    """
    cur = run / ("finals" if kind in ("clips","broll") else "iterations") / kind / f"{sid}.mp4"
    if not cur.exists():
        return
    vs = row.setdefault("versions", [])
    n = len(vs) + 1
    vdir = run / "iterations" / "versions"
    vdir.mkdir(parents=True, exist_ok=True)
    dest = vdir / f"{sid}-{kind}-v{n}.mp4"
    cur.rename(dest)
    key = "revoice" if kind == "voiced" else "generate"
    vs.append({"v": n, "file": f"cinema/versions/{dest.name}",
               "job_id": (row.get(key) or {}).get("job_id"),
               "rejected_because": why or "replaced without a reason given"})


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    run = Path(sys.argv[1]).expanduser().resolve()
    kind = sys.argv[2]
    if kind not in ("raw", "voiced", "broll"):
        sys.exit("kind must be raw, voiced or broll")
    pairs = dict(a.split("=", 1) for a in sys.argv[3:])
    pp = run / "out" / "plan.json"
    d = json.loads(pp.read_text())
    out = run / ("finals" if kind in ("clips","broll") else "iterations") / kind
    out.mkdir(parents=True, exist_ok=True)
    vo = run / "aroll"

    for sid, url in pairs.items():
        pool = d.get("cutaways", []) if kind == "broll" else d["scenes"]
        row = next((s for s in pool if s["id"] == sid), None)
        if row is None:
            print(f"  {sid}  NO SUCH ROW — skipped")
            continue
        f = out / f"{sid}.mp4"
        archive(run, kind, sid, row, row.pop("change", "")
                or row.get("redo", ""))
        urllib.request.urlretrieve(url, f)
        dur = float(ffprobe(f, "v:0").splitlines()[-1] or 0)
        aud = ffprobe(f, "a:0")
        key = "revoice" if kind == "voiced" else "generate"
        row.setdefault(key, {})
        row[key].update({"status": "completed", "url": url,
                         "file": f"cinema/{kind}/{sid}.mp4",
                         "seconds_out": round(dur, 3)})
        flags = []
        if kind == "broll":
            # silent by design: a cutaway sits under her voice, which never
            # stops. Audio ON a cutaway is the defect here, not audio off.
            if aud:
                flags.append("HAS AUDIO — a cutaway must be silent or it "
                             "fights the take it covers")
        elif not aud:
            flags.append("NO AUDIO STREAM — this did not come from Cinema Studio")
        for mp3 in (sorted(vo.glob("*.mp3")) if kind != "broll" else []):
            md = float(ffprobe(mp3, "a:0").splitlines()[-1] or 0)
            if abs(md - dur) < 0.02:
                flags.append(f"DURATION MATCHES {mp3.name} ({md:.3f}s) — "
                             "muxed audio, the old route")
        row[key]["checks"] = flags or ["ok"]
        mark = "!!" if flags else "ok"
        print(f"  {mark} {sid}  {dur:6.2f}s  audio={aud.splitlines()[0] if aud else 'NONE'}")
        for fl in flags:
            print(f"       {fl}")
    pp.write_text(json.dumps(d, indent=1))
    print(f"\nwrote {len(pairs)} into cinema/{kind}/ and recorded in plan.json")


if __name__ == "__main__":
    main()
