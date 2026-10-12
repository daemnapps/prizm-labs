"""OMNI PROVIDER BENCH — the same Omni model through each door that sells it, on the
SAME inputs and the SAME words, timed and priced from each door's own numbers
(the owner 2026-10-03: "line up all the omni providers … speed, cost, and avatar / voice /
scene accuracy"). Brand-agnostic: the test cases come from a JSON file.

    python3 omni_bench.py <cases.json> --out <dir> [--doors fal,google]

A case: {"id", "kind": "talk"|"reference", "picture", "prompt", "seconds", "resolution",
         "swipe" (reference only, ≤3 s), "line" + "voice" (talk only)}
Each clip is then given the character's voice (ElevenLabs speech-to-speech, the same step
for every door) and checked by clip_qc.py. Results → <out>/bench.json.
"""
from __future__ import annotations

import argparse, base64, json, mimetypes, subprocess, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import omni, providers_fal  # noqa: E402

FAL_PER_S = {"360p": 0.03, "720p": 0.10, "1080p": 0.15, "4k": 0.30}     # fal pages, read 2026-10-03
FAL_REF = "google/gemini-omni-flash/v1.1/reference-to-video"


def _dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout.strip() or 0)


def _data(p):
    return f"data:{mimetypes.guess_type(str(p))[0] or 'application/octet-stream'};base64,{base64.b64encode(Path(p).read_bytes()).decode()}"


def fal(case, out):
    k = omni.fal_key_of(); t = time.time()
    if case["kind"] == "talk":
        body = {"prompt": case["prompt"], "image_url": _data(case["picture"]), "duration": case["seconds"],
                "aspect_ratio": "9:16", "resolution": case["resolution"]}
        slug = omni.cfg()["model"]
    else:
        body = {"prompt": case["prompt"], "image_urls": [_data(case["picture"])], "reference_video_urls": [_data(case["swipe"])],
                "duration": case["seconds"], "aspect_ratio": "9:16", "resolution": case["resolution"]}
        slug = FAL_REF
    sub = providers_fal.submit(slug, body, k, providers_fal.http_transport)
    res = providers_fal.wait(sub["status_url"], sub["response_url"], k, providers_fal.http_transport, slug)
    providers_fal.fetch(providers_fal.media_urls(res)[0], out)
    s = _dur(out)
    return {"door": "fal", "took_s": round(time.time() - t, 1), "seconds": round(s, 2),
            "usd": round(s * FAL_PER_S[case["resolution"]], 4), "price_source": "fal price page"}


def _google_upload(path, k):
    """Files API, resumable: start, then upload + finalize. -> file URI (waits until ACTIVE)."""
    data = Path(path).read_bytes(); mime = mimetypes.guess_type(str(path))[0] or "video/mp4"
    start = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={k}",
        data=json.dumps({"file": {"display_name": Path(path).name}}).encode(), method="POST",
        headers={"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                 "X-Goog-Upload-Header-Content-Length": str(len(data)), "X-Goog-Upload-Header-Content-Type": mime,
                 "Content-Type": "application/json"})
    url = urllib.request.urlopen(start, timeout=60).headers["X-Goog-Upload-URL"]
    up = urllib.request.Request(url, data=data, method="POST",
                                headers={"X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize",
                                         "Content-Length": str(len(data))})
    f = json.loads(urllib.request.urlopen(up, timeout=120).read())["file"]
    for _ in range(60):
        if f.get("state") == "ACTIVE":
            break
        time.sleep(2)
        f = json.loads(urllib.request.urlopen(f"https://generativelanguage.googleapis.com/v1beta/{f['name']}?key={k}", timeout=30).read())
    return f["uri"], mime


def google(case, out):
    k = omni._google_key(); t = time.time()
    items = [{"type": "image", "data": base64.b64encode(Path(case["picture"]).read_bytes()).decode(),
              "mime_type": mimetypes.guess_type(str(case["picture"]))[0] or "image/png"}]
    if case["kind"] == "reference":
        uri, mime = _google_upload(case["swipe"], k)
        items.append({"type": "video", "uri": uri, "mime_type": mime})
    items.append({"type": "text", "text": case["prompt"]})
    body = {"model": omni.GOOGLE_MODEL, "input": items,
            "response_format": {"type": "video", "resolution": case["resolution"], "aspect_ratio": "9:16",
                                "duration": f"{case['seconds']}s"}}
    if case["kind"] == "reference":
        # without this Google reads picture + video as "edit this video" (live 2026-10-03)
        body["generation_config"] = {"video_config": {"task": "reference_to_video"}}
    req = urllib.request.Request(f"{omni.GOOGLE_URL}?key={k}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    res = json.loads(urllib.request.urlopen(req, timeout=900).read())
    vid = omni._find(res, lambda d: d.get("type") == "video" and (d.get("data") or d.get("uri")))
    if vid.get("data"):
        out.write_bytes(base64.b64decode(vid["data"]))
    else:
        urllib.request.urlretrieve(vid["uri"], out)
    u = res.get("usage") or {}
    usd = (u.get("total_output_tokens", 0) / 1e6 * omni.GOOGLE_OUT_PER_M + u.get("total_input_tokens", 0) / 1e6 * omni.GOOGLE_IN_PER_M)
    return {"door": "google", "took_s": round(time.time() - t, 1), "seconds": round(_dur(out), 2), "usd": round(usd, 4),
            "price_source": "Google's own usage report", "tokens_out": u.get("total_output_tokens"),
            "tokens_in": u.get("total_input_tokens")}


DOORS = {"fal": fal, "google": google}


def finish(case, raw, out):
    """The same last steps for every door: the character's voice (talk), then the checks."""
    r = {}
    final = raw
    if case.get("parts"):
        voiced = omni.revoice_lines(raw, case["parts"], raw.with_name(raw.stem + "-voice.mp3"))
        final = omni.remux(raw, voiced, out)
        r["line_check"] = omni.lineparity.check(final, " ".join(p["line"] for p in case["parts"]))
    elif case["kind"] == "talk":
        voiced = omni.revoice(raw, case["voice"], raw.with_name(raw.stem + "-voice.mp3"))
        final = omni.remux(raw, voiced, out)
        r["line_check"] = omni.lineparity.check(final, case["line"])
    qc = subprocess.run([sys.executable, str(HERE / "clip_qc.py"), str(final), "--picture", case["picture"]]
                        + (["--voice", str(final)] if case["kind"] == "talk" or case.get("parts") else [])
                        + (["--swipe", case["swipe"]] if case.get("swipe") else [])
                        + ["--sheet", str(Path(out).with_suffix(".jpg"))], capture_output=True, text=True).stdout
    r["qc"] = json.loads(qc) if qc.strip() else None
    r["file"] = str(final)
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cases"); ap.add_argument("--out", required=True)
    ap.add_argument("--doors", default="fal,google")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cases = json.loads(Path(a.cases).read_text()); results = []
    bench = out / "bench.json"
    if bench.exists():
        results = json.loads(bench.read_text())
    for c in cases:
        for d in a.doors.split(","):
            raw = out / f"{c['id']}-{d}-raw.mp4"
            try:
                r = {"case": c["id"], **DOORS[d](c, raw)}
                r.update(finish(c, raw, out / f"{c['id']}-{d}.mp4"))
            except Exception as e:  # a door that fails is a result too
                r = {"case": c["id"], "door": d, "error": str(e)[:400]}
            results = [x for x in results if not (x["case"] == c["id"] and x["door"] == d)] + [r]
            bench.write_text(json.dumps(results, indent=1))
            print(json.dumps({k: v for k, v in r.items() if k != "qc"}), flush=True)
