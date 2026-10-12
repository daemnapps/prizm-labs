"""FACE LOCK — the person in a made clip must stay the person on their casting sheet, frame by
frame (the owner 2026-10-03: "you're literally changing this woman's eye color and face throughout
a lot of these generations … troubleshoot the problem at a fundamental level").

  eyes   the iris colour around both pupils (macOS Vision landmarks), every sampled frame,
         against the casting sheet's — blue-grey turning brown shows here as a number
  face   the face model's own same/different verdict (identity.py), on start / middle / end
Returns {"ok", "eyes": {...}, "face": {...}}. Brand-agnostic; the casting sheet is passed in.

    python3 face_lock.py <clip.mp4|picture.png> --master <casting master.jpg>
"""
from __future__ import annotations

import argparse, importlib.util, json, math, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("vm_vp_keys", HERE / "vp_keys.py")
vp_keys = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vp_keys)
EYE_TOL = 0.06        # iris colour distance allowed from the casting sheet (calibrated 3 Oct, see notes)
FACE_MIN = 2          # of 3 frames the face model must call SAME


def _tool():
    b = HERE / "vision" / ".build" / "eyes"
    if not b.exists():
        b.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", str(HERE / "vision" / "eyes.swift"), "-o", str(b)], check=True)
    return b


def iris(img_path) -> tuple | None:
    """Mean colour (r, g, b in 0..1) of both irises, pupil core and glints left out."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as t:
        im = Image.open(img_path).convert("RGB"); im.save(Path(t) / "a.png")
        out = subprocess.run([str(_tool()), t], capture_output=True, text=True).stdout.split()
    if len(out) < 9:
        return None
    fx, fy, fw, fh, lx, ly, rx, ry = map(float, out[1:9])
    if fw <= 0 or lx < 0 or rx < 0:
        return None
    W, H = im.size; px = im.load(); rad = max(2, int(0.028 * fw * W)); acc = [0, 0, 0, 0]
    for cx, cy in ((lx * W, ly * H), (rx * W, ry * H)):
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                d = math.hypot(dx, dy)
                if d > rad or d < rad * 0.35:
                    continue
                x, y = int(cx + dx), int(cy + dy)
                if 0 <= x < W and 0 <= y < H:
                    r, g, b = px[x, y]; v = (r + g + b) / 3
                    if 25 < v < 225:
                        acc[0] += r; acc[1] += g; acc[2] += b; acc[3] += 1
    if acc[3] < 6:
        return None
    return tuple(c / acc[3] / 255 for c in acc[:3])


def hue_key(c):
    """Blue-ness against brown-ness: (b - r), with the brightness taken out."""
    s = sum(c) or 1
    return (c[2] - c[0]) / s


FALLBACK_MODEL = "gpt-5.5"


FAL_VISION = "openrouter/router/vision"
FAL_VISION_MODEL = "google/gemini-2.5-flash"


def same_person_fal(picture, master) -> str:
    """The face judge on fal's vision route (Gemini through fal) — the owner's working account."""
    import base64, io, re
    from PIL import Image
    import omni, providers_fal as pf
    def url(p):
        im = Image.open(p).convert("RGB"); im.thumbnail((900, 900)); b = io.BytesIO(); im.save(b, "JPEG", quality=90)
        return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    q = ("Image 1 is the approved picture. Image 2 is a frame from a video that must show the SAME person (or the same "
         "people, if there are several). Judge strictly, like a casting director checking continuity. For EACH image separately write: "
         "eye colour (exact: blue, blue-grey, green, hazel, light brown, dark brown), face shape, nose, lips, the pattern "
         "of spots/freckles, hair colour and cut. Then compare. Any change in eye colour is DIFFERENT. A different face "
         "shape, nose or lips is DIFFERENT. Lighting, angle, expression, closed eyes, glasses and clothes do not count. If image 2 shows no face of the "
         "person (hands only, a product, the back of the head), the verdict is NO_FACE. Reply with JSON only: "
         "{\"eyes_1\": \"...\", \"eyes_2\": \"...\", \"differences\": [\"...\"], \"verdict\": \"SAME\" or \"DIFFERENT\" or \"NO_FACE\"}")
    try:
        k = omni.fal_key_of()
        sub = pf.submit(FAL_VISION, {"prompt": q, "image_urls": [url(master), url(picture)], "model": FAL_VISION_MODEL,
                                     "temperature": 0}, k, pf.http_transport)
        r = pf.wait(sub["status_url"], sub["response_url"], k, pf.http_transport, FAL_VISION)
        t = str(r.get("output") or r)
        m = re.search(r"\{.*\}", t, re.S)
        v = (json.loads(m.group(0)).get("verdict") or "UNCHECKED").upper() if m else "UNCHECKED"
        return "SAME" if v == "NO_FACE" else v          # nobody's face to change: nothing to fail
    except Exception:
        return "UNCHECKED"


LIGHT = {"blue", "blue-grey", "grey", "green"}
DARK = {"hazel", "light brown", "brown"}


def face_crop_url(img_path, margin=0.25):
    """The largest face, cropped close and enlarged — a model reading eye colour off a whole frame
    guesses (3 Oct: three models disagreed on full frames, agreed on crops)."""
    import base64, io
    from PIL import Image
    im = Image.open(img_path).convert("RGB")
    with tempfile.TemporaryDirectory() as t:
        im.save(Path(t) / "a.png")
        o = subprocess.run([str(_tool()), t], capture_output=True, text=True).stdout.split()
    if len(o) < 5:
        return None
    fx, fy, fw, fh = map(float, o[1:5])
    if fw <= 0:
        return None
    W, H = im.size
    c = im.crop((max(0, (fx - margin * fw) * W), max(0, (fy - margin * fh) * H),
                 min(W, (fx + fw * (1 + margin)) * W), min(H, (fy + fh * (1 + margin)) * H)))
    c = c.resize((768, max(1, int(768 * c.height / c.width))), Image.LANCZOS)
    b = io.BytesIO(); c.save(b, "JPEG", quality=95)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def eye_family(img_path) -> str | None:
    """'light' / 'dark' eyes of the largest face, read by Gemini on fal from a close crop; None when
    there is no face or the eyes are closed or hidden."""
    import re
    import omni, providers_fal as pf
    u = face_crop_url(img_path)
    if not u:
        return None
    q = ("This is a close crop of one face. What colour are the irises? Answer with JSON only: "
         "{\"eyes\": one of \"blue\", \"blue-grey\", \"grey\", \"green\", \"hazel\", \"light brown\", \"brown\", "
         "\"not visible\"}. \"not visible\" if the eyes are closed or hidden.")
    try:
        k = omni.fal_key_of()
        sub = pf.submit(FAL_VISION, {"prompt": q, "image_urls": [u], "model": FAL_VISION_MODEL, "temperature": 0},
                        k, pf.http_transport)
        r = pf.wait(sub["status_url"], sub["response_url"], k, pf.http_transport, FAL_VISION)
        m = re.search(r"\{.*\}", str(r.get("output") or r), re.S)
        v = json.loads(m.group(0)).get("eyes", "") if m else ""
    except Exception:
        return None
    return "light" if v in LIGHT else "dark" if v in DARK else None


def eyes_held(clip, picture, n=3) -> dict:
    """The gate: the picture's eye colour (light/dark) against n frames of the clip. Fails only when
    most of the frames that show the eyes read the other colour — one odd read never fails a clip."""
    ref = eye_family(picture)
    fr = frames(clip)
    picks = [fr[int(i * (len(fr) - 1) / max(1, n - 1))] for i in range(n)] if fr else []
    reads = [eye_family(f) for f in picks]
    seen = [r for r in reads if r]
    off = sum(1 for r in seen if ref and r != ref)
    return {"picture": ref, "frames": reads, "ok": not (ref and seen and off * 2 > len(seen) and off >= 2)}


def same_person_claude(picture, master) -> str:
    """Claude on the owner's own plan, headless (`claude -p`, read-only), looking at both images —
    used when the paid face models cannot answer (3 Oct: Gemini 402, OpenAI out of credits)."""
    import shutil, os
    if not shutil.which("claude"):
        return "UNCHECKED"
    from PIL import Image
    tmp = Path(tempfile.mkdtemp()); a, b = tmp / "casting.jpg", tmp / "frame.jpg"
    for src, dst in ((master, a), (picture, b)):
        im = Image.open(src).convert("RGB"); im.thumbnail((900, 900)); im.save(dst, quality=90)
    q = (f"Read the image {a} (a casting sheet of one woman) and the image {b} (a frame from a video). Is the woman in the "
         "second image the same person as the first: same face shape, same eye colour, same pattern of brown age spots and "
         "freckles, same hair? Lighting and angle may differ. Reply with JSON only: {\"verdict\": \"SAME\" or \"DIFFERENT\", \"why\": \"...\"}")
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    try:
        r = subprocess.run(["claude", "-p", "--allowed-tools", "Read", "--output-format", "json"], input=q,
                           capture_output=True, text=True, env=env, timeout=300, cwd=str(tmp))
        t = json.loads(r.stdout or "{}").get("result") or ""
        import re
        m = re.search(r"\{.*\}", t, re.S)
        return (json.loads(m.group(0)).get("verdict") or "UNCHECKED").upper() if m else "UNCHECKED"
    except Exception:
        return "UNCHECKED"


def same_person_openai(picture, master) -> str:
    """Second opinion when the usual face model cannot answer (3 Oct: its account returned 402,
    so every face check said UNCHECKED and nothing failed)."""
    import base64, urllib.request
    def url(p):
        from PIL import Image; import io
        im = Image.open(p).convert("RGB"); im.thumbnail((768, 768)); b = io.BytesIO(); im.save(b, "JPEG", quality=88)
        return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    q = ("Image 1 is a casting sheet of one woman. Image 2 is a frame from a video. Is the woman in image 2 the same person "
         "as image 1 — same face shape, same eye colour, same pattern of brown age spots and freckles, same hair? Lighting and "
         "angle may differ. Answer JSON only: {\"verdict\": \"SAME\" or \"DIFFERENT\", \"why\": \"...\"}.")
    body = {"model": FALLBACK_MODEL, "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": [{"type": "text", "text": q},
                                                      {"type": "image_url", "image_url": {"url": url(master)}},
                                                      {"type": "image_url", "image_url": {"url": url(picture)}}]}]}
    try:
        req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {vp_keys.key('OPENAI_API_KEY')}"})
        t = json.loads(urllib.request.urlopen(req, timeout=180).read())["choices"][0]["message"]["content"]
        return (json.loads(t).get("verdict") or "UNCHECKED").upper()
    except Exception:
        return "UNCHECKED"


def frames(clip, n=6):
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
                             capture_output=True, text=True).stdout or 0)
    t = tempfile.mkdtemp(); out = []
    for k in range(n):
        f = Path(t) / f"f{k}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, d * (0.04 + 0.92 * k / (n - 1))):.2f}", "-i", str(clip),
                        "-frames:v", "1", str(f)], check=True)
        out.append(f)
    return out


def check(clip, master, use_face_model=True) -> dict:
    ref = iris(master)
    fl = frames(clip) if str(clip).endswith(".mp4") else [Path(clip)]
    keys = [(f, iris(f)) for f in fl]
    seen = [(f, hue_key(c)) for f, c in keys if c]
    res = {"eyes": {"casting": round(hue_key(ref), 3) if ref else None,
                    "frames": [round(k, 3) for _, k in seen]}}
    if ref and seen:
        worst = max(abs(k - hue_key(ref)) for _, k in seen)
        res["eyes"].update({"worst_off": round(worst, 3), "ok": worst <= EYE_TOL})
    if use_face_model:
        import identity
        picks = [fl[0], fl[len(fl) // 2], fl[-1]] if len(fl) >= 3 else fl
        v = []
        for p in picks:
            got = same_person_fal(p, master)             # the owner 3 Oct: "just use fal" for vision
            if got not in ("SAME", "DIFFERENT"):
                got = identity.check(str(p), [str(master)], votes=1)[0]["verdict"]
            if got not in ("SAME", "DIFFERENT"):
                got = same_person_claude(p, master)      # the face model must answer; a dead key never passes a clip
            if got not in ("SAME", "DIFFERENT"):
                got = same_person_openai(p, master)
            v.append(got)
        res["face"] = {"verdicts": v, "ok": v.count("SAME") >= min(FACE_MIN, len(v))}
    res["ok"] = all(x.get("ok", True) for x in res.values() if isinstance(x, dict))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("clip"); ap.add_argument("--master", required=True)
    ap.add_argument("--no-face-model", action="store_true")
    a = ap.parse_args()
    print(json.dumps(check(a.clip, a.master, not a.no_face_model), indent=1))
