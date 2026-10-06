"""Story machine — render: a finished narration becomes a vertical video.

    python3 render.py <job.json>

job.json:
  title          the line read first and shown as the post card
  narration      the full story text (captions keep this spelling)
  voice_id       ElevenLabs voice
  say_as         {"term": "respelling"} swapped into the voice text only
  voice_speed    ElevenLabs speed (0.7-1.2), default 1.0
  target_wpm     final narration pace after speed-up (the format reads ~250-350), default 250
  clips          folder of B-roll segments (vertical mp4s, any length; 2-4 s pieces are cut here)
  handle         the name on the post card
  end_card       optional PNG (1080x1920) held for the last 3 s
  label          optional small line kept on screen the whole time (e.g. "Dramatized story")
  out            the mp4 to write

Every caption word appears as it is spoken: one word, dead centre, heavy
rounded white type, thick black outline. No faces, no music.
Key: ELEVENLABS_API_KEY in the environment, or the local key store.
"""
import base64
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import urllib.request

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.environ.get("STORY_FONT", os.path.join(HERE, "assets", "LilitaOne.ttf"))


def key():
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"]
    sys.path.insert(0, os.path.expanduser("~/.daemn"))
    import daemn_keys
    return daemn_keys.key("ELEVENLABS_API_KEY")


def sh(*args):
    if args and args[0] == "ffmpeg":
        args = ("ffmpeg", "-nostdin") + tuple(args[1:])  # in the background ffmpeg can block forever waiting on keyboard input
    subprocess.run(args, check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


# ---------- voice ----------

def tts_chunk(text, voice_id, speed, prev="", nxt=""):
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps",
        data=json.dumps({"text": text, "model_id": "eleven_multilingual_v2",
                         "previous_text": prev[-600:], "next_text": nxt[:300],
                         "voice_settings": {"stability": 0.6, "similarity_boost": 0.8, "speed": speed}}).encode(),
        headers={"xi-api-key": key(), "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=600))
    a = d["alignment"]
    return base64.b64decode(d["audio_base64"]), a["characters"], a["character_start_times_seconds"], a["character_end_times_seconds"]


def voice(text, voice_id, speed, work):
    """One take, one voice. Splitting the read into pieces made the voice change between
    pieces (2026-10-06), so the whole story goes in a single call (the model takes up to
    10,000 characters). Its drift in volume is fixed afterwards by leveling, not by splitting."""
    chunks = [text.strip()]
    if len(text) > 9500:
        half = text.rfind("\n", 0, len(text) // 2)
        chunks = [text[:half].strip(), text[half:].strip()]
    files, chars, starts, ends, offset = [], [], [], [], 0.0
    for i, c in enumerate(chunks):
        audio, ch, st, en = tts_chunk(c, voice_id, speed, chunks[i - 1] if i else "",
                                      chunks[i + 1] if i + 1 < len(chunks) else "")
        f = os.path.join(work, f"v{i}.mp3")
        open(f, "wb").write(audio)
        files.append(f)
        chars += list(ch) + [" "]
        starts += [s + offset for s in st] + [en[-1] + offset]
        ends += [e + offset for e in en] + [en[-1] + offset]
        offset += duration(f)
    lst = os.path.join(work, "v.txt")
    open(lst, "w").write("".join(f"file '{f}'\n" for f in files))
    out = os.path.join(work, "voice_raw.wav")
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ar", "44100", "-ac", "1", out)
    return out, chars, starts, ends


def words_from(chars, starts, ends):
    words, cur, s0 = [], "", None
    for c, s, e in zip(chars, starts, ends):
        if c.isspace():
            if cur:
                words.append([cur, s0, e_prev])
            cur, s0 = "", None
        else:
            if not cur:
                s0 = s
            cur += c
            e_prev = e
    if cur:
        words.append([cur, s0, e_prev])
    return words


def speed_up(src, words, target_wpm, work):
    natural = len(words) / (words[-1][2] / 60)
    factor = max(1.0, min(target_wpm / natural, 1.8))
    out = os.path.join(work, "voice.wav")
    chain = []
    f = factor
    while f > 2.0:
        chain.append("atempo=2.0")
        f /= 2.0
    chain.append(f"atempo={f:.4f}")
    # even the level across the whole read, then set it to social-video loudness
    chain += ["dynaudnorm=f=150:g=31:p=0.9:m=20", "loudnorm=I=-14:TP=-1.5:LRA=7"]
    sh("ffmpeg", "-y", "-i", src, "-af", ",".join(chain), out)
    for w in words:
        w[1] /= factor
        w[2] /= factor
    print(f"voice: {natural:.0f} wpm natural -> x{factor:.2f} -> {natural * factor:.0f} wpm")
    return out


# ---------- captions and cards ----------

def outlined(draw, xy, text, font, fill, stroke, width):
    draw.text(xy, text, font=font, fill=fill, stroke_width=width, stroke_fill=stroke, anchor="mm")


def caption_png(word, path, label=""):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = 118
    font = ImageFont.truetype(FONT, size)
    while d.textlength(word, font=font) > W - 140 and size > 60:
        size -= 6
        font = ImageFont.truetype(FONT, size)
    outlined(d, (W / 2, H * 0.56), word, font, "white", "black", 12)
    if label:
        outlined(d, (W / 2, 120), label, ImageFont.truetype(FONT, 38), (255, 255, 255, 230), "black", 5)
    img.save(path)


def post_card(title, handle, path):
    """The title set as a social post, the format's first two seconds."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    body = ImageFont.truetype(FONT, 50)
    lines, cur = [], ""
    for w in title.split():
        if d.textlength((cur + " " + w).strip(), font=body) > 780:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    box_h = 150 + 64 * len(lines) + 40
    x0, y0 = 110, int(H * 0.30)
    d.rounded_rectangle([x0, y0, W - x0, y0 + box_h], 34, fill=(255, 255, 255, 250))
    d.ellipse([x0 + 34, y0 + 34, x0 + 114, y0 + 114], fill=(214, 130, 40, 255))
    d.text((x0 + 134, y0 + 52), handle, font=ImageFont.truetype(FONT, 40), fill=(20, 20, 20))
    for i, ln in enumerate(lines):
        d.text((x0 + 40, y0 + 140 + 64 * i), ln, font=body, fill=(20, 20, 20))
    img.save(path)


def caption_track(words, total, title_end, label, work, card=None, end_card=None, end_hold=0.0):
    """One transparent frame per word, held for exactly as long as the word is on screen.
    The post card (first seconds) and the end card (last seconds) are baked into this same
    layer: four separately-synced layers froze ffmpeg mid-render (2026-10-06)."""
    blank = os.path.join(work, "c_blank.png")
    caption_png("", blank, label)
    rows, t = [], 0.0
    if card:
        head = os.path.join(work, "c_card.png")
        base = Image.open(blank).convert("RGBA")
        base.alpha_composite(Image.open(card).convert("RGBA"))
        base.save(head)
        rows.append((head, title_end))
        t = title_end
    speech_end = total - end_hold
    for i, (w, s, e) in enumerate(words):
        s = max(s, title_end)
        nxt = words[i + 1][1] if i + 1 < len(words) else speech_end
        e = max(e, min(nxt, s + 0.6))
        if e <= s:
            continue
        if s > t:
            rows.append((blank, s - t))
        p = os.path.join(work, f"c{i:04d}.png")
        caption_png(re.sub(r"^[^\w“\"']+|[,;:]+$", "", w), p, label)
        rows.append((p, e - s))
        t = e
    if end_card:
        if speech_end > t:
            rows.append((blank, speech_end - t))
        end = os.path.join(work, "c_end.png")
        Image.open(end_card).convert("RGBA").resize((W, H)).save(end)
        rows.append((end, end_hold))
    else:
        rows.append((blank, max(total - t, 0.1)))
    lst = os.path.join(work, "c.txt")
    open(lst, "w").write("".join(f"file '{p}'\nduration {d:.3f}\n" for p, d in rows) + f"file '{rows[-1][0]}'\n")
    out = os.path.join(work, "captions.mov")
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"fps={FPS},format=rgba",
       "-c:v", "png", out)
    return out


# ---------- b-roll ----------

def broll(folder, total, work, seed=7):
    """Cut every source into 2-4 s pieces, crop to vertical, shuffle, and lay them end to end."""
    random.seed(seed)
    srcs = sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith((".mp4", ".mov", ".webm", ".mkv")))
    pieces = []
    for s in srcs:
        d = duration(s)
        t = 0.6
        while t + 2.0 < d - 0.4:
            ln = random.uniform(2.2, 3.6)
            pieces.append((s, t, min(ln, d - 0.4 - t)))
            t += ln + random.uniform(0.5, 3.0)
    if not pieces:
        raise SystemExit(f"no usable clips in {folder}")
    # Rotate by category (the file-name prefix before "_") so one long source can't crowd the rest out.
    groups = {}
    for p in pieces:
        groups.setdefault(os.path.basename(p[0]).split("_")[0], []).append(p)
    for g in groups.values():
        random.shuffle(g)
    order = list(groups)
    random.shuffle(order)
    pieces = [groups[k][i] for i in range(max(map(len, groups.values()))) for k in order if i < len(groups[k])]
    segs, t, i = [], 0.0, 0
    while t < total:
        s, st, ln = pieces[i % len(pieces)]
        out = os.path.join(work, f"b{i:04d}.mp4")
        sh("ffmpeg", "-y", "-ss", f"{st:.2f}", "-t", f"{ln:.2f}", "-i", s, "-an",
           "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,eq=saturation=1.12",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out)
        segs.append(out)
        t += ln
        i += 1
    lst = os.path.join(work, "b.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in segs))
    out = os.path.join(work, "broll.mp4")
    sh("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-t", f"{total:.2f}", "-c", "copy", out)
    print(f"b-roll: {len(segs)} cuts from {len(srcs)} sources")
    return out


# ---------- assemble ----------

def render(job):
    work = tempfile.mkdtemp(prefix="story-render-")
    spoken = job["title"].strip() + "\n\n" + job["narration"].strip()
    for term, say in job.get("say_as", {}).items():
        spoken = spoken.replace(term, say)
    raw, chars, starts, ends = voice(spoken, job["voice_id"], job.get("voice_speed", 1.0), work)
    words = words_from(chars, starts, ends)
    vo = speed_up(raw, words, job.get("target_wpm", 250), work)
    end_hold = 3.0 if job.get("end_card") else 0.6
    total = duration(vo) + end_hold
    title_words = len(job["title"].split())
    title_end = words[min(title_words, len(words)) - 1][2] + 0.15
    card = os.path.join(work, "card.png")
    post_card(job["title"], job.get("handle", "@stories"), card)
    caps = caption_track(words, total, title_end, job.get("label", ""), work,
                         card=card, end_card=job.get("end_card"), end_hold=end_hold if job.get("end_card") else 0.0)
    bg = broll(job["clips"], total, work, job.get("seed", 7))
    sh("ffmpeg", "-y", "-i", bg, "-i", caps, "-i", vo,
       "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto:eof_action=repeat[v]", "-map", "[v]", "-map", "2:a",
       "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "25", "-maxrate", "3500k", "-bufsize", "7000k",
       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", job["out"])
    print(f"wrote {job['out']} ({total:.0f}s)")
    return job["out"]


if __name__ == "__main__":
    render(json.load(open(sys.argv[1])))
