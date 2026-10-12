"""The two doors a picture actually goes through, behind one call.

    generate(entry, prompt, references, out, aspect, transport=None, key=None)

`entry` is a row out of this component's `models.json`; the provider it names
decides the request shape. Both doors take the same arguments and return the
same `{file, model, provider, request_id, usage}`, so nothing above this file
knows which vendor made a picture.

`transport(method, url, headers, body) -> (status, headers, body)` is the ONE
seam every real call goes through. Tests pass a stub; nothing in the test
suite ever opens a socket.

Lifted:
  - the OpenAI door, whole, from
    `tools/video-production/machine/direct_openai.py` — multipart
    `images/edits` with each reference sent as a repeated `image[]` part in
    the order given (OpenAI's own docs: "the first image in the list preserves
    the finest detail"), plain JSON `images/generations` with none, and the
    2.5 `invalid_input_fidelity_model` retry
  - the Google door from `tools/video-teardown/machine/frames.py` and
    `tools/video-production/machine/providers.json` `direct.google` —
    `generateContent` with `generationConfig.imageConfig.aspectRatio`

No model id, endpoint or key literal lives in this file.
"""
import base64
import json
import mimetypes
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from . import route as R

TIMEOUT = 420
TRIES = 3


class ProviderError(RuntimeError):
    pass


def http_transport(method, url, headers, body):
    """The real network call — the default `transport`. A timed-out or reset
    call is retried twice before it counts; an HTTP error is returned as the
    answer it is. (direct_openai.py: the first paid run died on one
    `Operation timed out` at frame 1 of 26.)"""
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    last = None
    for attempt in range(TRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers or {}), e.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = e
            time.sleep(5 * (attempt + 1))
    raise ProviderError(f"image call failed: {last} after {TRIES} attempts")


def _redacted(headers):
    return {k: ("Bearer <redacted>" if k.lower() == "authorization" else v)
            for k, v in headers.items()}


def _boundary():
    return f"----imgprod-{uuid.uuid4().hex}"


def _multipart(fields, files, boundary):
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                     f'{value}\r\n'.encode())
    for name, path in files:
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                     f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
                     + path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts)


def plan(entry, prompt, references, aspect):
    """The request as it WOULD be sent — headers redacted, no key read, no
    socket opened. This is what the free dry run prints."""
    provider = entry["provider"]
    if provider == "openai":
        url = entry["endpoints"]["edit" if references else "generate"]
        fields = {"model": entry["vendor_model"], "prompt": "<the prompt above>",
                  **{k: str(v) for k, v in (entry.get("params") or {}).items()}}
        size = R.size_for(entry, aspect)
        if size:
            fields["size"] = size
        return {"provider": provider, "method": "POST", "url": url, "fields": fields,
                "files": [str(p) for p in references],
                "headers": {"Authorization": "Bearer <redacted>"}}
    if provider == "google":
        url = entry["endpoints"]["generate"].replace("{model}", entry["vendor_model"])
        cfg = {"imageConfig": {"aspectRatio": aspect, **(entry.get("params") or {})}}
        return {"provider": provider, "method": "POST", "url": url + "?key=<redacted>",
                "generationConfig": cfg, "inline_images": [str(p) for p in references],
                "headers": {"Content-Type": "application/json"}}
    raise ProviderError(f"unknown provider `{provider}` in the route table")


def _openai(entry, prompt, references, out, aspect, transport, key):
    params = dict(entry.get("params") or {})
    size = R.size_for(entry, aspect)
    if size:
        params["size"] = size
    model = entry["vendor_model"]

    if references:
        boundary = _boundary()
        fields = {"model": model, "prompt": prompt,
                  **{k: str(v) for k, v in params.items()}}
        files = [("image[]", Path(r)) for r in references]
        headers = {"Authorization": f"Bearer {key}",
                   "Content-Type": f"multipart/form-data; boundary={boundary}"}
        url = entry["endpoints"]["edit"]
        status, rh, rb = transport("POST", url, headers, _multipart(fields, files, boundary))
        if status == 400 and b"invalid_input_fidelity_model" in rb and "input_fidelity" in fields:
            # The 2.5 models do not take input_fidelity at all (learned live
            # 2026-09-18). Send the same edit without it rather than fail.
            fields.pop("input_fidelity")
            status, rh, rb = transport("POST", url, headers, _multipart(fields, files, boundary))
    else:
        # input_fidelity only exists on the edits endpoint; generations
        # rejects it as unknown.
        payload = {"model": model, "prompt": prompt,
                   **{k: v for k, v in params.items() if k != "input_fidelity"}}
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        status, rh, rb = transport("POST", entry["endpoints"]["generate"], headers,
                                   json.dumps(payload).encode())

    data = json.loads(rb.decode())
    if status is not None and status >= 400:
        raise ProviderError(f"OpenAI images error {status}: {json.dumps(data)[:400]}")
    items = data.get("data") or []
    b64 = items[0].get("b64_json") if items else None
    if not b64:
        raise ProviderError(f"no b64_json in response: {json.dumps(data)[:400]}")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(b64))
    rid = (rh.get("x-request-id") or rh.get("X-Request-Id")
           or rh.get("openai-request-id") or rh.get("Openai-Request-Id"))
    return {"file": str(out), "model": model, "provider": "openai",
            "request_id": rid, "usage": data.get("usage")}


def _google(entry, prompt, references, out, aspect, transport, key):
    model = entry["vendor_model"]
    url = entry["endpoints"]["generate"].replace("{model}", model) + f"?key={key}"
    parts = []
    for r in references:
        p = Path(r)
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        parts.append({"inline_data": {"mime_type": mime,
                                      "data": base64.b64encode(p.read_bytes()).decode()}})
    parts.append({"text": prompt})
    payload = {"contents": [{"parts": parts}],
               "generationConfig": {"imageConfig": {"aspectRatio": aspect,
                                                    **(entry.get("params") or {})}}}
    status, rh, rb = transport("POST", url, {"Content-Type": "application/json"},
                               json.dumps(payload).encode())
    data = json.loads(rb.decode())
    if status is not None and status >= 400:
        raise ProviderError(f"Google images error {status}: {json.dumps(data)[:400]}")
    b64 = None
    for c in data.get("candidates") or []:
        for p in (c.get("content") or {}).get("parts") or []:
            blob = p.get("inline_data") or p.get("inlineData")
            if blob and blob.get("data"):
                b64 = blob["data"]
                break
        if b64:
            break
    if not b64:
        raise ProviderError(f"no image part in response: {json.dumps(data)[:400]}")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(b64))
    return {"file": str(out), "model": model, "provider": "google",
            "request_id": rh.get("x-request-id"), "usage": data.get("usageMetadata")}


def generate(entry, prompt, references, out, aspect, transport=None, key=None):
    """One picture. Raises rather than writing a broken file."""
    transport = transport or http_transport
    name = R.key_name(entry)
    k = key if key is not None else R.key_value(name)
    if not k:
        raise SystemExit(f"no {name} on this machine — it is read from the environment, "
                         f"else the macOS Keychain (service daemn-{name}, account damon). "
                         f"Nothing was sent and nothing was spent.")
    refs = [Path(r) for r in (references or [])]
    if entry["provider"] == "openai":
        return _openai(entry, prompt, refs, out, aspect, transport, k)
    if entry["provider"] == "google":
        return _google(entry, prompt, refs, out, aspect, transport, k)
    raise ProviderError(f"unknown provider `{entry['provider']}` in the route table")


def conform(path, want):
    """Centre-crop a picture to the frame the request asked for, when the
    vendor could not make that frame. OpenAI's edit and person models take
    only 1024x1024, 1024x1536 and 1536x1024, so a 4:5 request comes back 2:3
    and the measured check then holds every 4:5 picture (found live,
    2026-09-22). The extra canvas is the vendor's, never the caller's; the
    crop takes it back. Returns "WxH -> WxH" when it cropped, None when the
    frame already fit or Pillow is absent. Never widens, never pads."""
    if not want:
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    p = Path(path)
    with Image.open(p) as im:
        w, h = im.size
        target = want["h"] / want["w"]
        if abs(h / w - target) <= 0.02:
            return None
        if h / w > target:                      # too tall: trim top and bottom
            nh = int(round(w * target)); top = (h - nh) // 2
            box = (0, top, w, top + nh)
        else:                                   # too wide: trim the sides
            nw = int(round(h / target)); left = (w - nw) // 2
            box = (left, 0, left + nw, h)
        im.crop(box).save(p)
        return f"{w}x{h} -> {box[2]-box[0]}x{box[3]-box[1]}"



# ---------------------------------------------------------------- the frame
# THE 9:16 FINISH — content taped down, only the strips painted.
#
# the owner, 2026-09-22: every asset is 9:16; faces and words sit inside a centred
# 4:5 zone. Thirteen live rolls the same day showed that ASKING a model to keep
# a 4:5 layout inside a taller frame fails — both doors reflow the layout to
# fill the height (the 4 Sep finding, again). So the content is not asked to
# stay still; it is made unable to move. The 4:5 content is placed in the
# middle of a tall canvas, a mask exposes ONLY the strips above and below, and
# the edit model paints the backdrop continuing into them. The content pixels
# come back untouched, so the zone holds by geometry, and the scene continues
# instead of a flat band.
#
# The canvas is an EXACT 9:16 the door can make (1152x2048 — both numbers
# divide by 16, which is this model's only rule; asked of the API 2026-09-22
# rather than assumed). The 4:5 content sits centred in it, so the only thing
# painted is the strip above and the strip below — no side strips, no crop.
OUT_W, OUT_H = 1080, 1920                         # what a finished asset is delivered at
_CANVAS = (1152, 2048)                            # exactly 9:16
_CONTENT_W = _CANVAS[0]                           # the content spans the full width
_CONTENT_H = _CONTENT_W * 5 // 4                  # 1440 — exactly 4:5
_TOP = (_CANVAS[1] - _CONTENT_H) // 2             # 304
_LEFT = 0

OUTPAINT_PROMPT = (
    "Extend this picture upward and downward. The visible picture is finished "
    "and must not change in any way. Paint only the transparent areas: continue "
    "the same backdrop — the same surface, the same light, the same colour and "
    "grain — seamlessly, with no edge, no band and no change of tone where it "
    "meets the picture. Put nothing new there: no object, no word, no logo, no "
    "shape, no person. Background only.")

# The same instruction when the sides are painted too — a picture taller than
# 4:5 (a 2:3, say) is fitted INSIDE the zone, so the backdrop continues left
# and right as well as up and down (the owner, 2026-09-29: any ratio in, 9:16 out).
OUTPAINT_PROMPT_ALL_SIDES = (
    "Extend this picture outward on every side where it is transparent. The "
    "visible picture is finished and must not change in any way. Paint only the "
    "transparent areas: continue the same backdrop — the same surface, the same "
    "light, the same colour and grain — seamlessly, with no edge, no band and no "
    "change of tone where it meets the picture. Put nothing new there: no object, "
    "no word, no logo, no shape, no person. Background only.")


def zone_box(w, h, frame_w, frame_h):
    """Where a WHOLE w x h picture sits in a 9:16 frame of frame_w x frame_h:
    as large as it can be while staying entirely inside the centred 4:5 safe
    zone (the team notes/SAFE-ZONE.md — feed crops a 9:16 to that window). Never
    cropped, never stretched. A 4:5 fills the zone exactly; anything wider
    (1:1, 16:9) spans the full width with more painted above and below;
    anything taller (2:3) is as tall as the zone with the sides painted too.
    Returns (left, top, right, bottom)."""
    zw, zh = frame_w, frame_w * 5 // 4
    ztop = (frame_h - zh) // 2
    s = min(zw / w, zh / h)
    pw, ph = int(round(w * s)), int(round(h * s))
    left, top = (zw - pw) // 2, ztop + (zh - ph) // 2
    return (left, top, left + pw, top + ph)


def is_9x16(w, h):
    return abs(h / w - 16 / 9) < 0.02


def content_4x5(im):
    """The 4:5 content inside whatever was handed over: a 4:5 as it is; a
    taller frame (a 2:3 from the OpenAI door, a 9:16 already finished) cropped
    to its centre 4:5. Anything wider is refused — it is not a 9:16 asset."""
    w, h = im.size
    if abs(h / w - 1.25) < 0.02:
        return im
    if h / w > 1.25:
        ch = int(round(w * 5 / 4)); top = (h - ch) // 2
        return im.crop((0, top, w, top + ch))
    raise ProviderError(f"{w}x{h} is wider than 4:5 — not content for a 9:16 asset")


def _content(im, fit):
    """The pixels that get taped down: `content` = the centre 4:5 (the engine's
    own 4:5 content, a 2:3 from the vendor); `whole` = the picture as handed
    over, every pixel of it (any ratio in — nothing cropped)."""
    return im if fit == "whole" else content_4x5(im)


def outpaint_canvas(content_path, work_dir, fit="content"):
    """The two files the edit door takes: the canvas with the content taped in
    the middle (transparent elsewhere) and the mask whose transparent areas are
    the ONLY places the model may paint. Returns (canvas_path, mask_path)."""
    from PIL import Image
    work_dir = Path(work_dir); work_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(content_path) as im:
        src = _content(im.convert("RGB"), fit)
    box = zone_box(*src.size, *_CANVAS)
    c = src.resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS)
    canvas = Image.new("RGBA", _CANVAS, (0, 0, 0, 0))
    canvas.paste(c, box[:2])
    mask = Image.new("RGBA", _CANVAS, (0, 0, 0, 0))               # transparent = paint here
    mask.paste((255, 255, 255, 255), box)
    cp, mp = work_dir / "outpaint-canvas.png", work_dir / "outpaint-mask.png"
    canvas.save(cp, "PNG"); mask.save(mp, "PNG")
    return cp, mp


def finish_9x16(entry, content_path, out, transport=None, key=None, work_dir=None, fit="content"):
    """Content in, 9:16 asset out, content pixels untouched. Returns the
    provider record plus `content_box`, the rectangle of the original picture
    inside the finished asset, so a check can prove nothing inside it moved.

    fit="content" (the engine's 4:5 content, as before) or fit="whole" — ANY
    ratio in, the whole picture kept and fitted inside the 4:5 zone (the owner,
    2026-09-29: "any asset in any aspect ratio → a 9:16 asset out")."""
    from PIL import Image
    out = Path(out)
    work_dir = Path(work_dir or out.parent / "outpaint")
    with Image.open(content_path) as im:
        src_size = _content(im, fit).size
    box = zone_box(*src_size, OUT_W, OUT_H)
    sides = box[0] > 0
    canvas, mask = outpaint_canvas(content_path, work_dir, fit)
    transport = transport or http_transport
    k = key if key is not None else R.key_value(entry.get("key"))
    if not k:
        raise ProviderError(f"no {entry.get('key')} on this machine — the 9:16 finish cannot run")
    boundary = _boundary()
    fields = {"model": entry["vendor_model"], "prompt": OUTPAINT_PROMPT_ALL_SIDES if sides else OUTPAINT_PROMPT,
              "size": "x".join(map(str, _CANVAS)),
              **{k_: str(v) for k_, v in (entry.get("params") or {}).items() if k_ != "input_fidelity"}}
    files = [("image[]", canvas), ("mask", mask)]
    headers = {"Authorization": f"Bearer {k}",
               "Content-Type": f"multipart/form-data; boundary={boundary}"}
    status, rh, rb = transport("POST", entry["endpoints"]["edit"], headers,
                               _multipart(fields, files, boundary))
    data = json.loads(rb.decode())
    if status is not None and status >= 400:
        raise ProviderError(f"OpenAI outpaint error {status}: {json.dumps(data)[:400]}")
    items = data.get("data") or []
    b64 = items[0].get("b64_json") if items else None
    if not b64:
        raise ProviderError(f"no b64_json in outpaint response: {json.dumps(data)[:400]}")
    raw = work_dir / "outpaint-raw.png"
    raw.write_bytes(base64.b64decode(b64))

    with Image.open(raw) as im:
        im = im.convert("RGB")
        if im.size != _CANVAS:
            im = im.resize(_CANVAS, Image.LANCZOS)
        tall = im.crop((_LEFT, 0, _LEFT + _CONTENT_W, _CANVAS[1]))       # 864 x 1536 = 9:16
        tall = tall.resize((OUT_W, OUT_H), Image.LANCZOS)
        # TAPE IT DOWN, literally: the ORIGINAL content, resampled once from
        # its own pixels, is pasted over the model's answer at the exact box —
        # so even a model that ignored the mask cannot have moved it, and no
        # resize blends the painted strip into the content's edge.
        with Image.open(content_path) as src:
            tall.paste(_content(src.convert("RGB"), fit).resize((box[2] - box[0], box[3] - box[1]),
                                                                Image.LANCZOS), box[:2])
        out.parent.mkdir(parents=True, exist_ok=True)
        tall.save(out, "PNG")
    rid = (rh.get("x-request-id") or rh.get("X-Request-Id") or rh.get("openai-request-id"))
    return {"file": str(out), "model": entry["vendor_model"], "provider": "openai",
            "request_id": rid, "usage": data.get("usage"), "content_box": box,
            "content_from": str(content_path), "canvas": str(canvas), "mask": str(mask),
            "sides_painted": sides}


def edit_in_region(entry, prompt, picture, region, out, transport=None, key=None, work_dir=None):
    """An edit the model may only paint INSIDE a rectangle.

    the owner's fixes were held three times on 2026-09-22 because a model handed a
    whole picture and told to change one line redrew the product's own label.
    Putting the original back outside the rectangle afterwards fixed the label
    and produced a worse defect: the model had re-composed the whole frame, so
    the band carried a SHIFTED copy of the layout. The only thing that works is
    the one the 9:16 finish already proved — take the choice away. The picture
    goes in as the canvas, a mask exposes the rectangle alone, the model paints
    there and nowhere else, and the original is pasted back outside it so the
    guarantee is a fact about the file.

    `region` is (left, top, right, bottom) as percentages. Returns the provider
    record plus `region_px`.
    """
    from PIL import Image
    out = Path(out)
    work_dir = Path(work_dir or out.parent / "region")
    work_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(picture) as im:
        base = im.convert("RGB")
        w, h = base.size
    l, t, r, b = region
    box = (int(round(l / 100 * w)), int(round(t / 100 * h)),
           int(round(r / 100 * w)), int(round(b / 100 * h)))
    canvas = base.convert("RGBA")
    mask = Image.new("RGBA", (w, h), (255, 255, 255, 255))      # opaque = keep
    mask.paste((0, 0, 0, 0), box)                               # transparent = paint here
    cp, mp = work_dir / "region-canvas.png", work_dir / "region-mask.png"
    canvas.save(cp, "PNG"); mask.save(mp, "PNG")

    transport = transport or http_transport
    k = key if key is not None else R.key_value(entry.get("key"))
    if not k:
        raise ProviderError(f"no {entry.get('key')} on this machine — a region edit cannot run")
    boundary = _boundary()
    fields = {"model": entry["vendor_model"], "prompt": prompt,
              **{x: str(v) for x, v in (entry.get("params") or {}).items() if x != "input_fidelity"}}
    size = R.size_for(entry, None) if False else None
    files = [("image[]", cp), ("mask", mp)]
    headers = {"Authorization": f"Bearer {k}",
               "Content-Type": f"multipart/form-data; boundary={boundary}"}
    status, rh, rb = transport("POST", entry["endpoints"]["edit"], headers,
                               _multipart(fields, files, boundary))
    data = json.loads(rb.decode())
    if status is not None and status >= 400:
        raise ProviderError(f"OpenAI region edit error {status}: {json.dumps(data)[:400]}")
    items = data.get("data") or []
    b64 = items[0].get("b64_json") if items else None
    if not b64:
        raise ProviderError(f"no b64_json in region-edit response: {json.dumps(data)[:400]}")
    raw = work_dir / "region-raw.png"
    raw.write_bytes(base64.b64decode(b64))
    with Image.open(raw) as im:
        res = im.convert("RGB")
        if res.size != (w, h):
            res = res.resize((w, h), Image.LANCZOS)
        keep = base.copy()
        keep.paste(res.crop(box), (box[0], box[1]))             # only the rectangle travels
        out.parent.mkdir(parents=True, exist_ok=True)
        keep.save(out, "PNG")
    rid = (rh.get("x-request-id") or rh.get("X-Request-Id") or rh.get("openai-request-id"))
    return {"file": str(out), "model": entry["vendor_model"], "provider": "openai",
            "request_id": rid, "usage": data.get("usage"), "region_px": box,
            "canvas": str(cp), "mask": str(mp)}
