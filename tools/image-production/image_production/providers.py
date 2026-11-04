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
import re
import time
import urllib.error
import http.client
import urllib.request
import uuid
from pathlib import Path

from . import route as R

TIMEOUT = 420
TRIES = 4


class ProviderError(RuntimeError):
    """A picture door could not make the picture. `refused` is True when the model declined the picture itself (a safety
    refusal), as opposed to being busy or broken: the ladder moves to another MODEL on a refusal, and tries once more
    on the same model on any other failure."""

    def __init__(self, *args, refused=False):
        super().__init__(*args)
        self.refused = refused


REFUSAL = re.compile(r"moderation|safety|nsfw|content[ _-]?polic|refus|violat|blocked", re.I)


def http_transport(method, url, headers, body):
    """The real network call — the default `transport`. A timed-out or reset
    call is retried twice before it counts; an HTTP error is returned as the
    answer it is. (direct_openai.py: the first paid run died on one
    `Operation timed out` at frame 1 of 26.)"""
    if body is not None:  # a paid call is sent once, through curl — see _curl_transport
        return _curl_transport(method, url, headers, body)
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    last = None
    for attempt in range(TRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers or {}), e.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError,
                http.client.HTTPException) as e:
            last = e
            time.sleep(5 * (attempt + 1))
    if isinstance(last, http.client.IncompleteRead):
        return _curl_transport(method, url, headers, body)
    raise ProviderError(f"image call failed: {last} after {TRIES} attempts")


def _curl_transport(method, url, headers, body):
    """Python's reader on this Mac cuts long answers short behind the local
    network proxy (IncompleteRead on every 2-4 MB image, 2026-10-14) while
    curl reads the same answer whole — so a cut-short answer is fetched again
    through curl. Headers go through a private temp file, never argv."""
    import os, subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        hf = os.path.join(td, "h"); bf = os.path.join(td, "b")
        rh = os.path.join(td, "rh"); out = os.path.join(td, "o")
        with open(hf, "w") as f:
            f.write("".join(f"{k}: {v}\n" for k, v in headers.items()))
        os.chmod(hf, 0o600)
        cmd = ["curl", "-sS", "--retry", "5", "--retry-all-errors", "--retry-delay", "4", "--max-time", str(TIMEOUT),
               "-X", method, "-H", f"@{hf}", "-D", rh, "-o", out, url]
        if body is not None:
            with open(bf, "wb") as f:
                f.write(body)
            cmd[-1:-1] = ["--data-binary", f"@{bf}"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise ProviderError(f"image call failed through curl: {r.stderr.strip()[:300]}")
        status, hdrs = 0, {}
        for line in open(rh, errors="replace").read().splitlines():
            if line.startswith("HTTP/"):
                status, hdrs = int(line.split()[1]), {}
            elif ":" in line:
                k, v = line.split(":", 1); hdrs[k.strip()] = v.strip()
        return status, hdrs, open(out, "rb").read()


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


HIGGSFIELD_BIN = "higgsfield"
HF_SETUP = ("Higgsfield is not set up on this machine: ask Claude to install the Higgsfield command line and sign in "
            "(one click in the browser), then run this again. Nothing was sent and nothing was spent.")
HF_FRAME = {"9:16": "9:16"}


class _HfShell:
    """The real Higgsfield command line: a list of arguments (no shell), and a plain download of the result."""

    def which(self):
        import shutil
        return shutil.which(HIGGSFIELD_BIN) or ("/opt/homebrew/bin/higgsfield" if Path("/opt/homebrew/bin/higgsfield").is_file() else None)

    def run(self, argv, timeout=900):
        import subprocess
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr

    def fetch(self, url, dest):
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "company-image-production/1"})
        with urllib.request.urlopen(req, timeout=300) as r:
            dest.write_bytes(r.read())


def higgsfield_ready(hf=None):
    """The named precondition of the Higgsfield door: the command line is installed AND signed in. Returns the account
    ({credits, email, plan}) or raises ProviderError with a one-line instruction the owner can act on."""
    hf = hf or _HfShell()
    exe = hf.which()
    if not exe:
        raise ProviderError(HF_SETUP)
    code, out, err = hf.run([exe, "account", "status", "--json"], timeout=60)
    try:
        acct = json.loads(out)
    except ValueError:
        acct = {}
    if code != 0 or "credits" not in acct:
        raise ProviderError(HF_SETUP)
    return acct


def higgsfield_args(entry, prompt, references, aspect, exe=HIGGSFIELD_BIN):
    """The command line for one picture: the model's job type, the frame as an aspect ratio, variant / quality /
    resolution named every time (a call that names none gets the cheapest picture), references repeated."""
    params = dict(entry.get("params") or {})
    for need in entry.get("must_name") or ("quality", "resolution"):
        if need not in params:
            raise ProviderError(f"the Higgsfield row for {entry.get('vendor_model')!r} must name `{need}` (its default is the cheapest picture)")
    argv = [exe, "generate", "create", entry["vendor_model"], "--prompt", prompt, "--aspect_ratio", aspect]
    for k, v in params.items():
        argv += [f"--{k}", str(v)]
    for r in references:
        argv += ["--image-references", str(r)]
    return argv


def higgsfield_cost(entry, prompt, references, aspect, hf=None):
    """The credits one picture would cost: asked of Higgsfield, spends nothing."""
    hf = hf or _HfShell()
    exe = higgsfield_ready_exe(hf)
    argv = higgsfield_args(entry, prompt, [], aspect, exe)      # a quote needs no reference upload
    argv[2] = "cost"                                            # higgsfield generate cost <model> ... --json
    argv.append("--json")
    code, out, err = hf.run(argv, timeout=120)
    try:
        return float(json.loads(out)["credits"])
    except (ValueError, KeyError):
        raise ProviderError(f"Higgsfield would not quote this picture: {(out + err)[:200]}")


def higgsfield_ready_exe(hf):
    higgsfield_ready(hf)
    return hf.which()


def _higgsfield(entry, prompt, references, out, aspect, hf=None):
    """One picture through the Higgsfield command line (the owner, 2026-10-26: the keyed HTTP API does not sell GPT Image 2.5,
    Seedream 5 Pro or Nano Banana Pro; the command line does). Checks it is installed and signed in, runs
    `higgsfield generate create <model> ... --wait --json`, downloads `result_url` to `out`."""
    hf = hf or _HfShell()
    higgsfield_ready(hf)
    argv = higgsfield_args(entry, prompt, references, aspect, hf.which()) + ["--wait", "--wait-timeout", "10m", "--json"]
    code, so, se = hf.run(argv)
    try:
        jobs = json.loads(so)
    except ValueError:
        jobs = None
    if code != 0 or not isinstance(jobs, list) or not jobs:
        say = (so + se).strip()
        raise ProviderError(f"Higgsfield did not make the picture: {say[:300]}", refused=bool(REFUSAL.search(say)))
    job = jobs[0]
    if str(job.get("status", "")).lower() != "completed" or not job.get("result_url"):
        raise ProviderError(f"Higgsfield picture {job.get('id')} ended {job.get('status')!r}: {json.dumps(job)[:300]}",
                            refused=str(job.get("status", "")).lower() == "nsfw" or bool(REFUSAL.search(json.dumps(job))))
    hf.fetch(job["result_url"], out)
    return {"file": str(out), "model": entry.get("vendor_model"), "provider": "higgsfield",
            "request_id": job.get("id"), "usage": job.get("params")}


def generate(entry, prompt, references, out, aspect, transport=None, key=None):
    """One picture. Raises rather than writing a broken file."""
    if entry.get("provider") == "higgsfield":
        return _higgsfield(entry, prompt, [Path(r) for r in (references or [])], out, aspect, hf=transport)
    transport = transport or http_transport
    name = R.key_name(entry)
    k = key if key is not None else R.key_value(name)
    if not k:
        raise SystemExit(f"no {name} on this machine — it is read from the environment, "
                         f"else the macOS Keychain (service daemn-{name}, account owner). "
                         f"Nothing was sent and nothing was spent.")
    refs = [Path(r) for r in (references or [])]
    if entry["provider"] == "openai":
        return _openai(entry, prompt, refs, out, aspect, transport, k)
    if entry["provider"] == "google":
        return _google(entry, prompt, refs, out, aspect, transport, k)
    raise ProviderError(f"unknown provider `{entry['provider']}` in the route table")


def generate_ladder(rungs, prompt, references, out, aspect, transport=None):
    """One picture, the work always getting done (the owner, 2026-10-26): GPT Image 2.5 first; busy or broken, one more try on
    GPT; if GPT REFUSES a picture we are allowed to make, the next model (Seedream 5 Pro) with the same prompt, same
    references and same frame; if that fails, Nano Banana Pro; the transitional OpenAI direct door last. Each rung is
    {"name", "entry", "retry": bool, "max_images": int|None}. A rung that cannot take this many references is skipped and
    says so. Returns the winning record plus `made_by` (the rung) and `ladder` (every attempt, so the run record shows which
    model made the picture and why). Raises ProviderError naming every attempt when none worked."""
    log, refs = [], list(references or [])
    for rung in rungs:
        e = rung["entry"]
        cap = rung.get("max_images")
        if cap is not None and len(refs) > cap:
            log.append({"rung": rung["name"], "model": e.get("vendor_model"), "outcome": "skipped",
                        "why": f"{len(refs)} pictures is more than this model takes ({cap})"})
            continue
        tries = 2 if rung.get("retry") else 1
        for n in range(1, tries + 1):
            try:
                rec = generate(e, prompt, refs, out, aspect, transport=transport)
            except (ProviderError, SystemExit) as ex:
                refused = bool(getattr(ex, "refused", False))
                log.append({"rung": rung["name"], "model": e.get("vendor_model"), "try": n,
                            "outcome": "refused" if refused else "failed", "why": str(ex)[:240]})
                if refused:
                    break                       # a refusal is the model's answer: another try would be refused too
                continue
            log.append({"rung": rung["name"], "model": e.get("vendor_model"), "try": n, "outcome": "made"})
            return {**rec, "made_by": rung["name"], "ladder": log}
    raise ProviderError("no model made the picture: " + "; ".join(
        f"{x['rung']} {x['outcome']}" + (f" ({x['why']})" if x.get("why") else "") for x in log))


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
# Every photo and video asset (not email) is made 9:16 from the start, with the safe zone asked in the prompt and
# measured by the judge (the owner, 2026-10-26). The old "content at 4:5, then outpaint the strips" finish is removed: it
# came out inconsistent. A delivered asset is 1080x1920.
OUT_W, OUT_H = 1080, 1920


def is_9x16(w, h):
    return abs(h / w - 16 / 9) < 0.02


def _region_by_plain_edit(entry, prompt, picture, base, box, region, out, work_dir, hf=None):
    """A region edit on a door with NO mask (Higgsfield's GPT Image; the owner, 2026-10-26: no model beyond GPT Image 2.5).
    The rulebook's own method: an ordinary edit that names the one area that changes and says everything else stays,
    then the approved original is pasted back everywhere outside the rectangle, so 'nothing else moved' is still a fact
    about the file. KNOWN RISK, found live on 2026-09-22 with OpenAI: a model told to change one line may recompose the
    whole frame, so the rectangle can come back with a shifted copy of the layout. The paste-back cannot fix that;
    the judge and the first live picture are what will show it."""
    from PIL import Image
    l, t, r, b = region
    where = (f"Change ONLY the area from {l:g}% to {r:g}% across and {t:g}% to {b:g}% down. Everything outside that area "
             "stays exactly as it is: every person and face, the layout, every other word, the product, the colours, the camera angle.")
    raw = work_dir / "region-raw.png"
    rec = generate(entry, prompt.rstrip() + "\n\n" + where, [Path(picture)], raw, "9:16", transport=hf)
    w, h = base.size
    with Image.open(raw) as im:
        res = im.convert("RGB")
        if res.size != (w, h):
            res = res.resize((w, h), Image.LANCZOS)
        keep = base.copy()
        keep.paste(res.crop(box), (box[0], box[1]))             # only the rectangle travels
        out.parent.mkdir(parents=True, exist_ok=True)
        keep.save(out, "PNG")
    return {"file": str(out), "model": rec.get("model"), "provider": rec.get("provider"), "request_id": rec.get("request_id"),
            "usage": rec.get("usage"), "region_px": box, "canvas": str(picture), "mask": None, "method": "plain edit, original pasted back"}


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
    if entry.get("provider") == "higgsfield":
        return _region_by_plain_edit(entry, prompt, picture, base, box, (l, t, r, b), out, work_dir, transport)
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
