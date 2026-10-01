"""RETIRED 2026-09-12 — THIS FILE RAN ON FAL. DO NOT USE IT.

Damon, 2026-09-12: "Everything should have been done in Higgsfield. How are
you using fal? Stop using fal. We're just using Higgsfield, and we're just
using the models that we've already proven worked."

What this cost: an entire ad. The talking beats were generated on kling3_0
with `sound: "off"` and no audio attached, so eighteen shots came back with a
mouth moving to nothing. This file's own header said Kling was RETIRED and it
was used anyway, because nothing recorded which model made a clip.

The replacement is `prompt.py` and `THE-CINEMA-LINE.md` — Higgsfield only,
`cinematic_studio_3_0` with the line IN the prompt and `generate_audio` true,
then `voice_change` onto the cast member's voice element.

(Corrected 2026-09-14. This header used to name `higgs.py`, which has never
existed in this repo, and seedance with an audio reference, which the Cinema
line then ruled out. A dead pointer sends the next session looking for a file
that isn't there and inventing one.)

Kept, not deleted, because it is the record of how the wrong thing happened.
Nothing imports it. Nothing should.
"""

#!/usr/bin/env python3
"""Sequence flow runner — timeline → stills → voice → clips → assembled draft.

Fresh implementation of the proven sandbox flow (see ../archive/sequence-flow.md).
The run's timeline.json is the edit surface. Every shot is its own unit:
regenerate one still, one voice line, or one clip by id and reassemble.

  python3 sequence.py <run> stills [s1 s2 ...]   # default: all (master first)
  python3 sequence.py <run> vo     [s1 s2 ...]
  python3 sequence.py <run> clips  [s1 s2 ...]   # duration follows the VO line
  python3 sequence.py <run> assemble             # free, deterministic

Runs live in machine/runs/<run>/ — timeline.json + notes.md are the record
in git; stills/, vo/, clips/ and draft media are generated local state.
Auth: FAL_KEY env var, or FAL_KEY=... in machine/.env.
"""

import base64, json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUEUE = "https://queue.fal.run"

# MODEL RULING (Damon, 2026-08-31): minimize the model set. Approved
# families ONLY: Google Omni · ByteDance Seedance/Seedream · GPT models.
# MiniMax and Kling are RETIRED.
# Each model plays to its strengths (Damon 2026-08-31):
#   Seedream    — character/scene stills + identity-chained edits
#   Nano Banana — EDITING: layout-exact recreations, compositing real
#                 artifacts into shots (screens, packshots, inserts)
#   GPT image   — photo-referenced portraits / exact-recreate work
#   Seedance + Omni — clips, per shot on the merits
#   ElevenLabs  — voice
MODEL_STILL_T2I = "fal-ai/bytedance/seedream/v4.5/text-to-image"
MODEL_STILL_EDIT = "fal-ai/bytedance/seedream/v4.5/edit"
MODEL_EDIT_COMPOSITE = "fal-ai/nano-banana/edit"
# Voice slot: ElevenLabs (Damon, 2026-08-31 — "constantly solid").
MODEL_VO = "fal-ai/elevenlabs/tts/multilingual-v2"
MODEL_CLIP = "fal-ai/bytedance/seedance/v1/pro/image-to-video"
# Omni is a first-class clip model in its own right (Damon 2026-08-31 —
# NOT a "cheap drafts" tier): first+last-frame transitions, generation,
# upscale. Pick per shot on the merits.
MODEL_CLIP_OMNI = "google/gemini-omni-flash/v1.1/image-to-video"


def key():
    k = os.environ.get("FAL_KEY")
    if not k:
        env = HERE / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.strip().startswith("FAL_KEY="):
                    k = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not k:
        sys.exit("No FAL_KEY. Export it or put FAL_KEY=... in machine/.env")
    return k


def api(url, k, payload=None, tries=4):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode() if payload else None,
        headers={"Authorization": f"Key {k}", "Content-Type": "application/json"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            transient = e.code in (408, 429, 500, 502, 503, 504) or \
                "downstream_service_unavailable" in body
            if transient and attempt < tries - 1:
                wait_s = 20 * (attempt + 1)
                print(f"  transient {e.code}, retrying in {wait_s}s", flush=True)
                time.sleep(wait_s)
                continue
            raise RuntimeError(f"HTTP {e.code} from {url}\n{body[:500]}")


def submit(model, payload, k):
    sub = api(f"{QUEUE}/{model}", k, payload)
    return sub["status_url"], sub["response_url"]


def wait(status_url, response_url, k, label):
    t0 = time.time()
    while True:
        st = api(status_url + "?logs=0", k)
        if st.get("status") == "COMPLETED":
            return api(response_url, k)
        if st.get("status") in ("FAILED", "CANCELLED", "ERROR"):
            raise RuntimeError(f"{label} failed: {json.dumps(st)[:500]}")
        print(f"  {label}: {st.get('status')} ({int(time.time()-t0)}s)", flush=True)
        time.sleep(6)


def media_urls(obj, out=None):
    out = [] if out is None else out
    if isinstance(obj, dict):
        u = obj.get("url")
        if isinstance(u, str) and u.startswith("http"):
            out.append(u)
        [media_urls(v, out) for v in obj.values()]
    elif isinstance(obj, list):
        [media_urls(v, out) for v in obj]
    return out


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=600) as r, open(dest, "wb") as f:
        f.write(r.read())


def data_uri(path):
    return "data:image/jpeg;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def shrunk(path):
    """Downscale a still before shipping it as a reference/first-frame URI."""
    out = path.parent / (path.stem + "-sm.jpg")
    subprocess.run(["sips", "-Z", "1440", "-s", "format", "jpeg", str(path),
                    "--out", str(out)], capture_output=True)
    return out if out.exists() else path


def dur_of(path):
    p = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(p.stdout.strip())


def still_prompt(t, shot):
    L, w = t["locked"], t["wardrobe"][shot["outfit"]]
    return (f"{L['camera']}\n\nTHE PERSON: {L['character']} She is wearing {w}.\n\n"
            f"THE ROOM: {L['world']}\n\nTHE SHOT: {shot['still_action']}")


def clip_prompt(t, shot):
    return (f"{shot['motion']} She is speaking this line: \"{shot['say']}\" — "
            f"her mouth and expression follow real speech. "
            f"Realistic smartphone selfie video, no camera movement, no cuts.")


def load(run):
    rd = HERE / "runs" / run
    return json.loads((rd / "timeline.json").read_text()), rd


def pick(t, args):
    ids = [s["id"] for s in t["shots"]]
    want = [a for a in args if a in ids] or ids
    return [s for s in t["shots"] if s["id"] in want]


def cmd_stills(run, args):
    t, rd = load(run)
    k = key()
    shots = pick(t, args)
    master = rd / "stills" / "s1.png"
    explicit = bool([a for a in args if a.startswith("s")])
    if not master.exists() or (explicit and "s1" in [s["id"] for s in shots]):
        s1 = next(s for s in t["shots"] if s["id"] == "s1")
        print("still s1 (master, t2i)...", flush=True)
        res = wait(*submit(MODEL_STILL_T2I, {
            "prompt": still_prompt(t, s1), "num_images": 1,
            "image_size": "portrait_16_9"}, k), k, "s1")
        fetch(media_urls(res)[0], master)
        print(f"  saved {master}", flush=True)
    ref = data_uri(shrunk(master))
    todo = [(s, submit(MODEL_STILL_EDIT, {
                "prompt": "IMAGE 1 is the identity, room and camera-style reference. "
                          "Keep the exact same person (face, hair, skin), the exact "
                          "same room and light, and the exact same camera look.\n\n"
                          + still_prompt(t, s),
                "image_urls": [ref], "num_images": 1,
                "image_size": "portrait_16_9"}, k))
            for s in shots if s["id"] != "s1"]
    for s, (su, ru) in todo:
        res = wait(su, ru, k, f"still {s['id']}")
        dest = rd / "stills" / f"{s['id']}.png"
        fetch(media_urls(res)[0], dest)
        print(f"  saved {dest}", flush=True)


def cmd_vo(run, args):
    t, rd = load(run)
    k = key()
    voice = t.get("voice", {})
    payload_base = {"voice": voice.get("voice_id") or "Rachel",
                    "stability": voice.get("stability", 0.5),
                    "similarity_boost": voice.get("similarity", 0.75)}
    if voice.get("speed") not in (None, 1.0, 1):
        payload_base["speed"] = voice["speed"]
    todo = [(s, submit(MODEL_VO, {**payload_base, "text": s["say"]}, k))
            for s in pick(t, args)]
    for s, (su, ru) in todo:
        res = wait(su, ru, k, f"vo {s['id']}")
        dest = rd / "vo" / f"{s['id']}.mp3"
        fetch(media_urls(res)[0], dest)
        print(f"  saved {dest}  ({dur_of(dest):.1f}s)", flush=True)


def cmd_clips(run, args):
    t, rd = load(run)
    k = key()
    todo = []
    for s in pick(t, args):
        still = rd / "stills" / f"{s['id']}.png"
        vo = rd / "vo" / f"{s['id']}.mp3"
        if not still.exists():
            print(f"skip {s['id']}: no still yet")
            continue
        secs = max(4, min(10, round(dur_of(vo) + 0.6))) if vo.exists() else 8
        try:
            todo.append((s, submit(MODEL_CLIP, {
                "prompt": clip_prompt(t, s),
                "image_url": data_uri(shrunk(still)),
                "duration": "10" if secs > 5 else "5"}, k)))
        except RuntimeError:
            print(f"  {s['id']}: submit failed, skipping (redo later)", flush=True)
    failed = []
    for s, (su, ru) in todo:
        try:
            res = wait(su, ru, k, f"clip {s['id']}")
            dest = rd / "clips" / f"{s['id']}.mp4"
            fetch(media_urls(res)[0], dest)
            print(f"  saved {dest}", flush=True)
        except Exception as e:
            failed.append(s["id"])
            print(f"  clip {s['id']} FAILED: {str(e)[:200]}", flush=True)
    if failed:
        print(f"redo with: python3 sequence.py {run} clips {' '.join(failed)}",
              flush=True)


def text_card(text, dest):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lines = text.split(" | ")
    size = 56
    while size > 24:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size,
                                  index=1)
        if max(d.textlength(l, font=font) for l in lines) <= 980:
            break
        size -= 2
    y = int(1920 * 0.13)
    for line in lines:
        w = d.textlength(line, font=font)
        x = (1080 - w) / 2
        for dx in (-3, 3):
            for dy in (-3, 3):
                d.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 220))
        d.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += size + 20
    img.save(dest)


def cmd_assemble(run, _args):
    t, rd = load(run)
    segs = []
    for s in t["shots"]:
        clip, vo = rd / "clips" / f"{s['id']}.mp4", rd / "vo" / f"{s['id']}.mp3"
        if not clip.exists():
            print(f"skip {s['id']}: no clip yet")
            continue
        length = dur_of(vo) + 0.4 if vo.exists() else dur_of(clip)
        seg = rd / "clips" / f"{s['id']}-seg.mp4"
        base = ("scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,fps=30,"
                f"tpad=stop_mode=clone:stop_duration=12,trim=duration={length:.2f}")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip)]
        if vo.exists():
            cmd += ["-i", str(vo)]
        else:
            cmd += ["-f", "lavfi", "-t", f"{length:.2f}",
                    "-i", "anullsrc=r=44100:cl=stereo"]
        if s.get("on_screen"):
            card = rd / "clips" / f"{s['id']}-card.png"
            text_card(s["on_screen"], card)
            cmd += ["-i", str(card),
                    "-filter_complex", f"[0:v]{base}[v0];[v0][2:v]overlay=0:0[v]",
                    "-map", "[v]", "-map", "1:a"]
        else:
            cmd += ["-filter_complex", f"[0:v]{base}[v]",
                    "-map", "[v]", "-map", "1:a"]
        cmd += ["-t", f"{length:.2f}", "-c:v", "libx264", "-preset", "fast",
                "-crf", "21", "-c:a", "aac", "-ar", "44100", str(seg)]
        subprocess.run(cmd, check=True)
        segs.append(seg)
        print(f"  seg {s['id']}: {length:.1f}s", flush=True)
    lst = rd / "concat.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segs))
    out = rd / "draft.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe",
                    "0", "-i", str(lst), "-c", "copy", str(out)], check=True)
    print(f"draft: {out}  ({dur_of(out):.1f}s)", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    run, cmd, rest = sys.argv[1], sys.argv[2], sys.argv[3:]
    {"stills": cmd_stills, "vo": cmd_vo, "clips": cmd_clips,
     "assemble": cmd_assemble}[cmd](run, rest)
