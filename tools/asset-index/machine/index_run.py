#!/usr/bin/env python3
"""index_run.py — both halves in one: a list of clips in, one searchable record
per clip out, in the shape machine/search.py already reads
(work/<brand>-<collection>/<clip_id>/clip.json + breakdown.json + frames, and the
collection's map in work/_maps/). The model watches a small proxy of the clip.

    python3 machine/index_run.py <list of clip paths> --brand <brand> --collection <name> [--workers 6] [--limit N]

The CLAUDE.md "Not done yet" note named this as the next piece (2026-10-13, built
when the owner found the Brand-B face-scrub footage had never been indexed and the
edit had nothing real to find). Brand-agnostic: the avatar list comes from
brands/<brand>/core-avatars/; nothing here names a brand. Clips already recorded
are skipped, so a run can stop and resume. Only Shared Assets paths are mapped.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPONENT = HERE.parent
REPO = COMPONENT.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools" / "video-teardown" / "tools"))
import shared_paths  # noqa: E402
import gemini_breakdown as gb  # noqa: E402

MODEL = "gemini-3-flash-preview"
DRIVE_MEDIA = "https://www.googleapis.com/drive/v3/files/{id}?alt=media&supportsAllDrives=true"


class DriveToken:
    """A read token for the Drive API from the service account (gdrive-creator's
    public engine). The clip is read where it sits: ffmpeg asks Drive for only the
    bytes it needs, instead of the mounted drive syncing the whole file."""
    def __init__(self):
        sys.path.insert(0, str(REPO / "components" / "gdrive-creator"))
        from gdrive_creator import engine
        self.creds = engine._creds()
        self.at = 0

    def header(self):
        import time
        from google.auth.transport.requests import Request
        if time.time() - self.at > 1800 or not self.creds.token:
            self.creds.refresh(Request())
            self.at = time.time()
        return f"Authorization: Bearer {self.creds.token}\r\n"   # the registry's flash model, as the teardown chain names it

PROMPT = """You are indexing one clip of footage a brand owns, so it can be found again by
search months from now ("woman rubs face scrub into her cheeks at a bathroom mirror").
Observation only: what is in it, never whether it is good, never what it could become.
Never name anyone, never guess race, ethnicity or identity.

Return exactly one JSON object with these fields:
- "format": one word for what the clip is (talking-head, demo, b-roll, before-after, product-shot, unboxing, fragment).
- "speaks_to": which of these audience ids the clip would speak to, by what is shown: {avatars}. [] if none.
- "scenes": a list, one per continuous stretch (a new one at every cut or big change):
  {{"t_start": seconds, "t_end": seconds, "visuals": what is seen and done, in plain words a person would search with,
    "spoken": what is said, word for word if clear, else "", "on_screen_text": words on screen, else null}}
- "subject": who is on screen, as casting notes (apparent age bracket, gender, hair, clothing), or null.
- "setting": where, surfaces, light.
- "products_visible": every product seen, described exactly as it looks (colour of tube or jar, cap, label words you can read, texture of what is applied: e.g. "cream tube, gold label 'Brilliance Face Scrub'", "thick pale cream scrub with dark flecks"). [] if none.
- "product_on_skin": true if a product is being applied to or wiped off skin on camera.
- "where_on_body": face, neck, hands, arms, legs, body, or null.
- "shot": a list from selfie, handheld, locked-off, close-up, wide, insert, mirror, plus vertical or horizontal.
- "talking_head": true if a person talks to the camera.
- "usable_for": a list from hook, demo, application, before-after, testimonial, b-roll, product-shot, reaction, routine.
- "quality_notes": a list of plain notes (shaky, dark, blurry, watermark, burned-in captions, music only).
- "confidence": high, medium or low.
"""


class DriveRefused(RuntimeError):
    """The Drive would not serve the clip (403/429/5xx, or an unreadable answer). Never "not footage"."""


class QuotaExceeded(DriveRefused):
    """downloadQuotaExceeded (domain usageLimits): a daily limit. Not retried; the batch stops for the day."""


def drive_check(drive_id, tok, timeout=60):
    """Ask the Drive for the clip and close at the headers: nothing downloaded. Raises QuotaExceeded on the
    daily download limit, DriveRefused on any other refusal (corrections 2-3, LD-63 (describe on use))."""
    import urllib.request
    import urllib.error
    req = urllib.request.Request(DRIVE_MEDIA.format(id=drive_id),
                                 headers={"Authorization": tok.header().split(": ", 1)[1].strip()})
    try:
        urllib.request.urlopen(req, timeout=timeout).close()
    except urllib.error.HTTPError as e:
        try:
            reason = json.loads(e.read().decode("utf-8", "ignore"))["error"]["errors"][0]["reason"]
        except Exception:
            reason = None
        if reason == "downloadQuotaExceeded":
            raise QuotaExceeded("Drive download quota (downloadQuotaExceeded) on %s" % drive_id)
        raise DriveRefused("the Drive refused %s (HTTP %s%s)" % (drive_id, e.code, ", " + reason if reason else ""))
    except Exception as e:  # noqa: BLE001
        raise DriveRefused("the Drive did not answer for %s (%s)" % (drive_id, type(e).__name__))


# THE MODEL SETTINGS, in one place for every describing path (index_run's batch and describe_on_use) — LD-63
# (describe on use) correction 7. A thinking change from the post-123 A/B is made here, nowhere else.
GEN_CONFIG = {"response_mime_type": "application/json", "temperature": 0.2}


def ffprobe(p, hdr=None):
    r = subprocess.run(["ffprobe", "-v", "error", *(["-headers", hdr] if hdr else []), "-show_entries", "format=duration,size:stream=codec_type,width,height,codec_name",
                        "-of", "json", str(p)], capture_output=True, text=True)
    if r.returncode != 0 and hdr:
        # a refused READ is never "not footage" (1,032 clips were wrongly marked so on 2026-10-20)
        raise DriveRefused("ffprobe could not read the clip: " + (r.stderr or "").strip()[-200:])
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"duration_s": round(float((d.get("format") or {}).get("duration") or 0), 2), "width": v.get("width"),
            "height": v.get("height"), "codec": v.get("codec_name"),
            "has_audio": any(s.get("codec_type") == "audio" for s in d.get("streams", [])),
            "size_mb": round(int((d.get("format") or {}).get("size") or 0) / 1e6, 1)}


def avatars(brand):
    base = REPO / "brands" / brand / "core-avatars"
    ids = []
    for a in sorted(p for p in base.iterdir() if p.is_dir()):
        ids.append(a.name)
        ids += [s.stem for s in sorted((a / "sub-avatars").glob("*.md"))] if (a / "sub-avatars").is_dir() else []
    return ids


def one(path, out_dir, brand, k, avatar_ids, drive_id=None, tok=None, record_dir=None):
    """One clip described. `record_dir` (LD-63 (describe on use) correction 1): write into that RECORD folder
    (runs/asset-index/<brand>/<collection>/<drive-id>/) and MERGE meta and frames into its clip.json, keeping
    drive_id, label, words, kind; described becomes true. -> (clip id, recorded|kept|not footage, usage)."""
    path = Path(path)
    cid = Path(record_dir).name if record_dir else hashlib.sha1(str(path).encode()).hexdigest()[:10]
    src = DRIVE_MEDIA.format(id=drive_id) if drive_id else str(path)
    hdr = ["-headers", tok.header()] if drive_id else []
    d = Path(record_dir) if record_dir else out_dir / cid
    if (d / "breakdown.json").is_file():
        return cid, "kept", None
    d.mkdir(parents=True, exist_ok=True)
    meta = ffprobe(src, tok.header() if drive_id else None)
    if not meta["duration_s"]:
        return cid, "not footage", None
    proxy = d / "proxy.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *hdr, "-i", src, "-t", "90", "-vf", "scale=-2:360", "-r", "12",
                    "-c:v", "libx264", "-crf", "30", "-preset", "ultrafast", "-c:a", "aac", "-b:a", "48k", str(proxy)], check=True)
    frames = []
    # Frames are timed on the PROXY, which can be shorter than the original — capped at 90 s, and its
    # last frame can land before the original's container duration. A seek past its end made ffmpeg
    # write no frame and fail (4 clips, 2026-10-21, post 123). Clamp to the proxy's own length.
    pdur = ffprobe(proxy)["duration_s"] or min(meta["duration_s"], 90)
    for i, frac in enumerate((0.15, 0.5, 0.85), 1):
        at = round(pdur * frac, 2)
        f = d / f"frame_{i:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(max(0, min(at, pdur - 0.25))), "-i", str(proxy), "-frames:v", "1",
                        "-vf", "scale=-2:480", str(f)], check=True)
        frames.append({"file": f.name, "at_s": at})
    clip = {"clip_id": cid, "collection": (d.parent.name if record_dir else out_dir.name), "path": str(path),
            "filename": path.name,
            "folder": path.parent.parent.name if path.parent.name == "raw" else path.parent.name,
            "meta": meta, "frames": frames}
    if record_dir and (d / "clip.json").is_file():
        try:
            have = json.loads((d / "clip.json").read_text())
        except ValueError:
            have = {}
        merged = dict(have)
        merged["meta"] = {**(have.get("meta") or {}), **{k_: v for k_, v in meta.items() if v not in (None, 0)}}
        merged["frames"] = frames
        merged.setdefault("filename", path.name)
        clip = merged
    (d / "clip.json").write_text(json.dumps(clip, indent=1, ensure_ascii=False) + "\n")
    uri, mime, _ = gb.upload(k, proxy)
    body = {"contents": [{"parts": [{"file_data": {"file_uri": uri, "mime_type": mime}, "video_metadata": {"fps": 2}},
                                    {"text": PROMPT.format(avatars=", ".join(avatar_ids))}]}],
            "generationConfig": dict(GEN_CONFIG)}
    res = gb.req(f"{gb.BASE}/v1beta/models/{MODEL}:generateContent?key={k}", data=json.dumps(body).encode(),
                 headers={"Content-Type": "application/json"})
    text = res["candidates"][0]["content"]["parts"][0]["text"]
    bd = json.loads(text)
    if isinstance(bd, list):
        bd = bd[0]
    (d / "breakdown.json").write_text(json.dumps(bd, indent=1, ensure_ascii=False) + "\n")
    usage = usage_of(res)
    (d / "usage.json").write_text(json.dumps(usage, indent=1) + "\n")       # cost tracking (LD-56)
    if record_dir:
        c = json.loads((d / "clip.json").read_text())
        c.update({"described": True, "described_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        (d / "clip.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    return cid, "recorded", usage


def usage_of(res):
    """The response's usageMetadata as {model, prompt, candidates, thoughts, total, by_modality}."""
    u = (res or {}).get("usageMetadata") or {}
    return {"model": MODEL, "prompt": u.get("promptTokenCount") or 0, "candidates": u.get("candidatesTokenCount") or 0,
            "thoughts": u.get("thoughtsTokenCount") or 0, "total": u.get("totalTokenCount") or 0,
            "by_modality": u.get("promptTokensDetails") or []}


def rate(model=MODEL):
    """(usd_per_1m_input, usd_per_1m_output) from components/models/models.json, or (None, reason)."""
    try:
        reg = json.loads((Path(__file__).resolve().parents[2] / "models" / "models.json").read_text())
        rows = reg.get("models") if isinstance(reg, dict) else reg
        e = next(m for m in rows if isinstance(m, dict) and m.get("id") == model)
    except (OSError, ValueError, StopIteration) as ex:
        return None, "no registry row for %s (%s)" % (model, type(ex).__name__)
    c = e.get("cost")
    if not isinstance(c, dict) or c.get("usd_per_1m_input") is None or c.get("usd_per_1m_output") is None:
        return None, "unpriced in components/models/models.json" + (": " + e["cost_reason"] if e.get("cost_reason") else "")
    return (float(c["usd_per_1m_input"]), float(c["usd_per_1m_output"])), None


def ledger(rows, done, seconds, brand, collection, runs=None):
    """runs/asset-index/<brand>/<collection>/ledger.json, one entry per run appended: clips recorded/kept/
    skipped, token totals, wall seconds and cost_usd — null with the reason while the model is unpriced,
    never a made-up number (LD-56 cost tracking)."""
    tot = {k: sum(int(r.get(k) or 0) for r in rows) for k in ("prompt", "candidates", "thoughts", "total")}
    r, why = rate()
    cost = None if r is None else round((tot["prompt"] * r[0] + (tot["candidates"] + tot["thoughts"]) * r[1]) / 1e6, 4)
    entry = {"run_id": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), "model": MODEL, "clips": done,
             "tokens": tot, "wall_seconds": round(seconds), "cost_usd": cost}
    if cost is None:
        entry["cost_reason"] = why
    f = Path(runs or (Path(__file__).resolve().parents[3] / "runs" / "asset-index")) / brand / collection / "ledger.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    try:
        led = json.loads(f.read_text())
    except (OSError, ValueError):
        led = {"brand": brand, "collection": collection, "runs": []}
    led["runs"].append(entry)
    f.write_text(json.dumps(led, indent=1) + "\n")
    return entry


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", help="a text file, one clip path per line; or a .json list of {id, path} from the Drive API (path relative to Shared Assets)")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--collection", required=True, help="e.g. creators; the folder is work/<brand>-<collection>")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    if a.clips.endswith(".json"):
        items = [(str(shared_paths.SHARED_ROOT / x["path"]), x["id"]) for x in json.loads(Path(a.clips).read_text())]
        tok = DriveToken()
    else:
        items = [(l.strip(), None) for l in Path(a.clips).read_text().splitlines() if l.strip()]
        tok = None
    items = [(p, i) for p, i in items if shared_paths.on_shared(p)][: a.limit or None]
    out_dir = shared_paths.WORK / f"{a.brand}-{a.collection}"
    out_dir.mkdir(parents=True, exist_ok=True)
    k = gb.key()
    av = avatars(a.brand)
    done = {"recorded": 0, "kept": 0, "failed": 0, "not footage": 0}
    m = shared_paths.load_map(out_dir)
    usages, t0 = [], time.time()
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(one, p, out_dir, a.brand, k, av, i, tok): p for p, i in items}
        for f in cf.as_completed(futs):
            p = futs[f]
            try:
                cid, how, use = f.result()
                done[how] += 1
                if use:
                    usages.append(use)
                m[cid] = {"path": p}
            except Exception as e:  # one bad clip never stops the rest
                done["failed"] += 1
                print(f"  failed: {Path(p).name}: {type(e).__name__}: {str(e)[:160]}", file=sys.stderr)
    shared_paths.MAPS.mkdir(parents=True, exist_ok=True)
    (shared_paths.MAPS / f"{out_dir.name}.json").write_text(json.dumps(m, indent=1) + "\n")
    print(json.dumps(done))
    print(json.dumps(ledger(usages, done, time.time() - t0, a.brand, a.collection)))


if __name__ == "__main__":
    main()
