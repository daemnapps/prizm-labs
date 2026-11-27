#!/usr/bin/env python3
"""check.py — the check pass: one model look per described clip at its local 360p proxy, answering the
fixed questions in components/asset-index/prompts/check-pass-v<N>-owner.md (polish, handles, platform
marks, people, products, quality, and per scene: beat, burned-in text, text size, words).

    python3 check.py --brand <brand> --limit 5 --dry-run    # count and price, send nothing
    python3 check.py --brand <brand> --limit 5              # a first few
    python3 check.py --brand <brand> --workers 6 --budget 5 [--key-env NAME]

Reads the brand's library (library.json) and each record's local proxy; writes only
runs/asset-index/<brand>/library/check/. Resumable: a clip already answered is skipped. Stops before a
clip starts once --budget USD is spent. Every line keeps the prompt as sent, the model and the token
usage. The key is read by name: the shared loader's GEMINI_API_KEY, or --key-env NAME from the environment.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import library as LIB  # noqa: E402
sys.path.insert(0, str(REPO / "components" / "video-teardown" / "tools"))
import gemini_breakdown as gb  # noqa: E402  (key loader + HTTP retry; nothing written beside any file)

MODEL = "gemini-3-flash-preview"
PRICE = (0.50, 3.00)          # USD per 1M input / output tokens, components/models/models.json (6 Nov 2026)
CAP_S = 120                   # seconds of each clip sent
EST_PER_CLIP = 0.0028         # measured: 1,265 clips for $3.48 on 2026-11-06


def latest_prompt() -> tuple[Path, str]:
    ps = sorted((REPO / "components" / "asset-index" / "prompts").glob("check-pass-v*-owner.md"),
                key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    return ps[-1], ps[-1].read_text()


def beats_text() -> str:
    d = LIB.D["beat"]["values"]
    return "\n".join(f"- {k}: {v['means']}" for k, v in d.items()) + "\n- other: none of these"


def clips(brand: str) -> dict:
    rows = LIB.rows_of(brand)
    out = {}
    for r in rows:
        if r.get("kind") == "picture":
            continue
        rec = LIB._abs(r)
        c = out.setdefault(r["clip"], {"clip": r["clip"], "record": str(rec.parent) if rec else None, "scenes": []})
        c["scenes"].append((r["scene"], r["in"], r["out"], r["shows"]))
    return out


def clip_bytes(proxy: Path) -> bytes:
    base = ["ffmpeg", "-v", "error", "-t", str(CAP_S), "-i", str(proxy), "-an"]
    tail = ["-movflags", "frag_keyframe+empty_moov", "-f", "mp4", "pipe:1"]
    r = subprocess.run(base + ["-c:v", "copy"] + tail, capture_output=True)
    if r.returncode != 0 or len(r.stdout) < 1000:
        r = subprocess.run(base + ["-vf", "scale=-2:360", "-c:v", "libx264", "-crf", "32", "-preset", "veryfast"] + tail,
                           capture_output=True, check=True)
    return r.stdout


def one(c: dict, template: str, beats: str, k: str) -> dict:
    proxy = Path(c["record"]) / "proxy.mp4"
    scenes = "\n".join(f"{n}. {a:g}-{b:g} s: {v}" + ("  (after the first %d s, not sent)" % CAP_S if a >= CAP_S else "")
                       for n, a, b, v in c["scenes"])
    looks = LIB.BRAND.get("looks") or {k_: k_ for k_ in LIB.D["product"]["values"]}
    prompt = (template.replace("{scenes}", scenes).replace("{beats}", beats)
              .replace("{products}", "\n".join(f"- {k_}: {v}" for k_, v in looks.items())))
    blob = clip_bytes(proxy)
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "video/mp4", "data": base64.b64encode(blob).decode()}, "video_metadata": {"fps": 1}},
        {"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2,
                             "thinkingConfig": {"thinkingLevel": "low"}}}
    t0 = time.time()
    res = gb.req(f"{gb.BASE}/v1beta/models/{MODEL}:generateContent?key={k}", data=json.dumps(body).encode(),
                 headers={"Content-Type": "application/json"})
    text = res["candidates"][0]["content"]["parts"][0]["text"]
    ans = json.loads(text)
    if isinstance(ans, list):
        ans = ans[0]
    u = res.get("usageMetadata") or {}
    usage = {"prompt": u.get("promptTokenCount") or 0, "output": (u.get("candidatesTokenCount") or 0) + (u.get("thoughtsTokenCount") or 0)}
    usage["usd"] = round((usage["prompt"] * PRICE[0] + usage["output"] * PRICE[1]) / 1e6, 6)
    return {"clip": c["clip"], "model": MODEL, "answer": ans, "usage": usage, "seconds": round(time.time() - t0, 1),
            "sent_bytes": len(blob), "sent_prompt": prompt}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", dest="dry", action="store_true", help="count and price what would be sent; send nothing")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget", type=float, default=16.0)
    ap.add_argument("--key-env", default="", help="read the API key from this environment variable instead of the shared loader")
    a = ap.parse_args(argv)
    LIB.BRANDNAME[0] = a.brand
    LIB.use_brand(a.brand)
    OUT = LIB.libdir(a.brand) / "check"
    OUT.mkdir(parents=True, exist_ok=True)
    done = set()
    spent = 0.0
    for line in LIB.check_lines(OUT):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        done.add(d["clip"]); spent += (d.get("usage") or {}).get("usd", 0)
    pfile, template = latest_prompt()
    beats = beats_text()
    todo = [c for c in clips(a.brand).values() if c["clip"] not in done and c["record"]
            and (Path(c["record"]) / "proxy.mp4").is_file()]
    if a.limit:
        todo = todo[: a.limit]
    if a.dry:
        print(json.dumps({"would_check": len(todo), "est_usd": round(len(todo) * EST_PER_CLIP, 2), "spent_so_far": round(spent, 4)}))
        return 0
    import os
    k = os.environ.get(a.key_env, "").strip() if a.key_env else gb.key()
    if not k:
        sys.exit("no key in %s" % a.key_env)
    lock = threading.Lock()
    state = {"spent": spent, "ok": 0, "failed": 0, "stopped": None}
    fails = OUT / "failed.jsonl"

    def work(c):
        with lock:
            if state["spent"] >= a.budget:
                state["stopped"] = "budget $%.2f reached" % a.budget
                return
        try:
            r = one(c, template, beats, k)
        except Exception as e:  # noqa: BLE001 — one clip never stops the rest
            with lock:
                state["failed"] += 1
                with fails.open("a") as f:
                    f.write(json.dumps({"clip": c["clip"], "error": f"{type(e).__name__}: {str(e)[:200]}"}) + "\n")
            return
        r["prompt_file"] = pfile.name
        with lock:
            state["spent"] += r["usage"]["usd"]; state["ok"] += 1
            line = json.dumps(r, ensure_ascii=False) + "\n"
            with LIB.check_append_file(OUT, len(line.encode())).open("a") as f:
                f.write(line)
            if state["ok"] % 25 == 0:
                print(f"  {state['ok']} done, ${state['spent']:.2f}", flush=True)

    t0 = time.time()
    with cf.ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(work, todo))
    run = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": MODEL, "prompt_file": pfile.name,
           "prompt_sha256": hashlib.sha256(template.encode()).hexdigest(), "asked": len(todo), "ok": state["ok"],
           "failed": state["failed"], "spent_usd_total": round(state["spent"], 4), "wall_s": round(time.time() - t0),
           "stopped": state["stopped"], "price_per_1m": PRICE, "cap_seconds": CAP_S,
           "key": a.key_env or "GEMINI_API_KEY (shared loader)"}
    runs = OUT / "runs.json"
    hist = json.loads(runs.read_text()) if runs.is_file() else []
    hist.append(run)
    runs.write_text(json.dumps(hist, indent=1) + "\n")
    print(json.dumps(run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
