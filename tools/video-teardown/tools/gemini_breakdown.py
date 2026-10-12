#!/usr/bin/env python3
"""Per-asset video breakdown via Gemini (Files API upload -> analyze).

Usage: python3 gemini_breakdown.py <video.mp4> [--model gemini-flash-latest]
                                   [--out breakdown.json] [--context "..."]

Reads GEMINI_API_KEY from the environment, then the repo .env (components/keys/loader.py).
Uploaded copy is ephemeral on
Google's side (auto-expires ~48h). Output: structured JSON breakdown
next to the video (or --out), consumable by the brief step.
"""

import argparse, json, mimetypes, os, sys, time, urllib.request
from pathlib import Path
import socket

# IPv4 first (2026-09-25): when this Mac's IPv6 route is down, every Google call
# sat 5 minutes per address before trying IPv4 — a whole run looked frozen.
_gai = socket.getaddrinfo
socket.getaddrinfo = lambda *a, **k: sorted(_gai(*a, **k), key=lambda r: r[0] != socket.AF_INET)

BASE = "https://generativelanguage.googleapis.com"

PROMPT = """You are analyzing one social-media video by a UGC creator, \
for a marketing team that writes creator briefs. Ground EVERY claim in \
what is actually shown or said — never invent; if something is unclear, \
say "unclear". Return JSON with exactly these keys:

- "scenes": array of {"t_start", "t_end", "visuals" (what is shown: \
setting, action, framing, camera movement), "on_screen_text" (verbatim, \
or null), "spoken" (verbatim words in this span, or null)}
- "audio": {"speech_style" (pace, tone, register — or null), "music" \
(described, or null), "sound_design" (cuts/sfx, or null)}
- "hook": {"first_3s" (exactly what happens), "technique" (the \
attention device used), "spoken_or_visual"}
- "format": one short label (e.g. talking-head, GRWM, voiceover-broll, \
text-overlay-montage, skit, tutorial, haul, before-after)
- "creator_presentation": {"appearance", "energy", "voice_register", \
"setting_style"} — evidence-based, neutral wording
- "product_or_brand": what if anything is promoted and how (or null)
- "structure": the video's arc in 2-3 sentences (how it opens, \
develops, closes; pacing)
- "performance_hypotheses": array of 2-4 {"element", "why_it_may_work"} \
— clearly hypotheses, each tied to an observed element
- "notes_for_brief": 2-3 sentences: what a script writer should imitate \
or avoid when writing FOR THIS CREATOR, based only on this video
"""



def _shared_keys():
    """The repo's one key loader (components/keys/loader.py): the environment,
    then the repo's .env, then — quietly — the owner's personal fallbacks."""
    import importlib.util
    import sys as _sys
    from pathlib import Path as _Path
    mod = _sys.modules.get("shared_keys_loader")
    if mod is None:
        path = next(p / "components" / "keys" / "loader.py"
                    for p in _Path(__file__).resolve().parents
                    if (p / "components" / "keys" / "loader.py").is_file())
        spec = importlib.util.spec_from_file_location("shared_keys_loader", str(path))
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["shared_keys_loader"] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            _sys.modules.pop("shared_keys_loader", None)
            raise
    return mod


def key():
    # Environment first: keys travel by VARIABLE NAME, so any vault that
    # exports GEMINI_API_KEY works; then the repo's .env (components/keys/loader.py).
    return _shared_keys().lookup("GEMINI_API_KEY", required=True).strip()


def req(url, data=None, headers=None, method=None, raw=False, tries=4):
    for attempt in range(1, tries + 1):
        try:
            r = urllib.request.Request(url, data=data, headers=headers or {},
                                       method=method)
            with urllib.request.urlopen(r, timeout=300) as resp:
                b = resp.read()
                return (b, dict(resp.headers)) if raw else json.loads(b or b"{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries:
                wait = 10 * attempt
                print(f"  HTTP {e.code}, retry {attempt}/{tries - 1} "
                      f"in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise


def upload_cached(k, path):
    """Reuse a still-ACTIVE prior upload of this video (saves ~1 min/run)."""
    cache = path.with_suffix(".gemini-uri.json")
    # the cache is of THIS file's contents, not its name: a file replaced under
    # the same name was being judged as the old one (2026-10-02 — a remade
    # portrait checked as the previous picture, a re-recorded line as the old take)
    import hashlib
    sig = hashlib.md5(Path(path).read_bytes()).hexdigest()
    if cache.exists():
        c = json.loads(cache.read_text())
        if c.get("sig") == sig and time.time() - c["uploaded_at"] < 40 * 3600:
            try:
                f = req(f"{BASE}/v1beta/{c['name']}?key={k}", tries=1)
                if f.get("state") == "ACTIVE":
                    print("  (reusing cached upload)")
                    return c["uri"], c["mime"]
            except Exception:
                pass
    uri, mime, name = upload(k, path)
    cache.write_text(json.dumps({"uri": uri, "mime": mime, "name": name, "sig": sig,
                                 "uploaded_at": time.time()}))
    return uri, mime


def upload_bytes(k, blob, display_name, mime="video/mp4"):
    """Upload raw bytes to the Files API — no local file required."""
    size = len(blob)
    _, h = req(f"{BASE}/upload/v1beta/files?key={k}",
               data=json.dumps({"file": {"display_name": display_name}}).encode(),
               headers={"X-Goog-Upload-Protocol": "resumable",
                        "X-Goog-Upload-Command": "start",
                        "X-Goog-Upload-Header-Content-Length": str(size),
                        "X-Goog-Upload-Header-Content-Type": mime,
                        "Content-Type": "application/json"}, raw=True)
    up_url = h.get("X-Goog-Upload-URL") or h.get("x-goog-upload-url")
    info = req(up_url, data=blob,
               headers={"X-Goog-Upload-Command": "upload, finalize",
                        "X-Goog-Upload-Offset": "0",
                        "Content-Length": str(size)})
    f = info["file"]
    while f["state"] == "PROCESSING":
        time.sleep(3)
        f = req(f"{BASE}/v1beta/{f['name']}?key={k}")
    if f["state"] != "ACTIVE":
        sys.exit(f"upload failed: {f}")
    return f["uri"], mime, f["name"]


def stream_from_url(k, url, display_name="video.mp4"):
    """Fetch a remote video into memory and hand it to Gemini — nothing
    touches disk. IG/TikTok CDN links are short-lived: use at scrape time."""
    r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=180) as resp:
        blob = resp.read()
        mime = resp.headers.get("Content-Type", "video/mp4").split(";")[0]
    if not mime.startswith("video"):
        mime = "video/mp4"
    print(f"  streamed {len(blob)//1024} KB from source (no local file)")
    return upload_bytes(k, blob, display_name, mime)


def upload(k, path):
    mime = mimetypes.guess_type(str(path))[0] or "video/mp4"
    size = path.stat().st_size
    _, h = req(f"{BASE}/upload/v1beta/files?key={k}",
               data=json.dumps({"file": {"display_name": path.name}}).encode(),
               headers={"X-Goog-Upload-Protocol": "resumable",
                        "X-Goog-Upload-Command": "start",
                        "X-Goog-Upload-Header-Content-Length": str(size),
                        "X-Goog-Upload-Header-Content-Type": mime,
                        "Content-Type": "application/json"}, raw=True)
    up_url = h.get("X-Goog-Upload-URL") or h.get("x-goog-upload-url")
    info = req(up_url, data=path.read_bytes(),
               headers={"X-Goog-Upload-Command": "upload, finalize",
                        "X-Goog-Upload-Offset": "0",
                        "Content-Length": str(size)})
    f = info["file"]
    while f["state"] == "PROCESSING":
        time.sleep(3)
        f = req(f"{BASE}/v1beta/{f['name']}?key={k}")
    if f["state"] != "ACTIVE":
        sys.exit(f"upload failed: {f}")
    return f["uri"], mime, f["name"]


def search_receipts(cand):
    """What Google Search actually returned for a grounded answer, as a block
    the reader can check: the queries the model ran and every web page it was
    grounded on. Empty when the answer was not grounded."""
    gm = cand.get("groundingMetadata") or {}
    queries = gm.get("webSearchQueries") or []
    pages = [(c.get("web") or {}) for c in gm.get("groundingChunks") or []]
    pages = [p for p in pages if p.get("uri") or p.get("title")]
    if not queries and not pages:
        return ("\n\n---\n\n### SEARCH RECEIPTS — none\n\nFiled by the machine: the model "
                "ran no web search for this read, so any receipt above that says it came "
                "from a search is unverified.\n")
    out = ["", "", "---", "", "### SEARCH RECEIPTS — what Google Search returned for this read",
           "", "Filed by the machine from the model's grounding data, not written by the model."]
    if queries:
        out += ["", "Searches run:"] + [f"- {q}" for q in queries]
    if pages:
        out += ["", "Pages the read was grounded on:"]
        out += [f"- {p.get('title') or '(untitled)'} — {p.get('uri') or ''}" for p in pages]
    return "\n".join(out) + "\n"


def analyze(k, model, uri, mime, context, prompt=None, search=False):
    gen = {"temperature": 0.2}
    if prompt is None:  # default structured breakdown → force JSON
        prompt = PROMPT + (f"\nContext from the team: {context}"
                           if context else "")
        gen["response_mime_type"] = "application/json"
    # Frames per second the model watches (2026-09-24): the default of 1 missed a
    # hand entering frame for a few seconds. GEMINI_VIDEO_FPS overrides.
    fps = float(os.environ.get("GEMINI_VIDEO_FPS", "2"))
    body = {"contents": [{"parts": [
        {"file_data": {"file_uri": uri, "mime_type": mime}, "video_metadata": {"fps": fps}},
        {"text": prompt}]}],
        "generationConfig": gen}
    # GOOGLE SEARCH GROUNDING (2026-10-05, the culture read): the model may
    # search the web while it watches — to confirm who a character is, where a
    # quoted line comes from, what year a film is. Text answers only.
    if search and "response_mime_type" not in gen:
        body["tools"] = [{"google_search": {}}]
    # The model decides for itself whether to search, and on a long prompt it
    # sometimes answers from memory instead. A read that was asked to search and
    # did not is asked once more; if it still did not, the output says so.
    for attempt in (1, 2) if search and "tools" in body else (1,):
        out = req(f"{BASE}/v1beta/models/{model}:generateContent?key={k}",
                  data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json"})
        gm = ((out.get("candidates") or [{}])[0].get("groundingMetadata") or {})
        if not search or gm.get("webSearchQueries") or gm.get("groundingChunks"):
            break
        if attempt == 1:
            print("  the read ran no search — asking once more", file=sys.stderr)
    try:
        if search:
            # a grounded answer can come back in several text parts
            cand = out["candidates"][0]
            text = "".join(p.get("text", "") for p in cand["content"]["parts"]
                           if not p.get("thought"))
            if not text.strip():
                raise KeyError("no text")
            return text + search_receipts(cand)
        text = out["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        sys.exit(f"unexpected response: {json.dumps(out)[:800]}")
    if "response_mime_type" not in gen:  # custom prompt → raw text
        return text
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        sys.exit(f"model returned non-JSON: {text[:800]}")
    if isinstance(parsed, list):  # model sometimes wraps the object
        parsed = parsed[0] if len(parsed) == 1 and \
            isinstance(parsed[0], dict) else {"breakdown": parsed}
    return parsed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--model", default="gemini-3-flash-preview")
    ap.add_argument("--out")
    ap.add_argument("--context", default="")
    ap.add_argument("--prompt-file", help="test a custom prompt (plain-text "
                    "response, printed + saved as .txt)")
    ap.add_argument("--search", action="store_true",
                    help="let the model use Google Search while it reads "
                    "(custom prompts only); the searches and pages it was "
                    "grounded on are appended to the output")
    a = ap.parse_args()
    v = Path(a.video)
    k = key()
    print(f"[1/3] uploading {v.name} ({v.stat().st_size//1024} KB)")
    uri, mime = upload_cached(k, v)
    print(f"[2/3] analyzing with {a.model}")
    if a.prompt_file:
        pf = Path(a.prompt_file)
        custom = pf.read_text()
        gen_out = analyze(k, a.model, uri, mime, "", prompt=custom,
                          search=a.search)
        txt = gen_out if isinstance(gen_out, str) else json.dumps(
            gen_out, indent=2)
        # One file per (video, prompt, model) so prompt runs never clobber
        # each other, and every output says what produced it.
        out = Path(a.out) if a.out else (
            v.parent / f"{v.stem}--{pf.stem}--{a.model}.txt")
        header = (f"<!-- video: {v.name} | prompt: {pf.name} | "
                  f"model: {a.model} | run: "
                  f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} -->\n\n")
        out.write_text(header + txt)
        print(txt[:3000])
        print(f"[3/3] full output → {out}")
        return
    result = analyze(k, a.model, uri, mime, a.context)
    result["_meta"] = {"model": a.model, "video": str(v),
                       "analyzed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                    time.gmtime())}
    out = Path(a.out) if a.out else v.parent / "breakdown.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"[3/3] done → {out}")


if __name__ == "__main__":
    main()
