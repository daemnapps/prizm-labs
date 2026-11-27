"""The ads' pictures for owner's page: each ad's own creative, from the warehouse's copy of the ad (no Meta API).

A picture ad -> its image; a video ad -> the video's full-size cover (object_story_spec.video_data.image_url),
falling back to Meta's small thumbnail. Downloaded once per run into <run>/art/<ad_id>.jpg (kept small), and
published as files beside the page (the Artifact's own files), so the private page needs nothing from outside.
"""
import base64, io, json, shutil, subprocess, urllib.request
from pathlib import Path

import warehouse as W

UA = {"User-Agent": "Mozilla/5.0"}


def sources(ad_ids):
    """ad_id -> {art, is_video, preview, body} from meta_ads."""
    if not ad_ids:
        return {}
    out = {}
    for r in W.rows("""select ad_id, thumbnail_url, image_url, video_id, preview_link, raw->'creative' cr
                       from meta_ads where ad_id = any(string_to_array(:'ids', ','));""", ids=",".join(ad_ids)):
        cr = json.loads(r["cr"]) if r["cr"] else {}
        oss = cr.get("object_story_spec") or {}
        vd = oss.get("video_data") or {}
        ld = oss.get("link_data") or {}
        art = vd.get("image_url") or r["image_url"] or ld.get("picture") or cr.get("image_url") or r["thumbnail_url"]
        body = (cr.get("body") or vd.get("message") or ld.get("message") or "").strip().split("\n")[0]
        out[r["ad_id"]] = {"art": art, "small": r["thumbnail_url"], "is_video": bool(r["video_id"]), "video_id": r["video_id"],
                           "preview": r["preview_link"] or cr.get("instagram_permalink_url"), "body": body[:140]}
    return out


def fetch(run_dir, ad_ids, width=360, embed=False):
    """Download each ad's picture once into <run>/art/, resized; returns ad_id -> its page path ("art/<id>.jpg",
    published beside the page) or, with embed, a data URI; None when the ad has no picture."""
    from PIL import Image
    art = Path(run_dir) / "art"
    art.mkdir(exist_ok=True)
    src = sources(ad_ids)
    uris = {}
    for aid in ad_ids:
        f = art / f"{aid}.jpg"
        if not f.exists():
            s = src.get(aid) or {}
            for u in (s.get("art"), s.get("small")):
                if not u:
                    continue
                try:
                    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as h:
                        im = Image.open(io.BytesIO(h.read())).convert("RGB")
                    im.thumbnail((width, width * 2))
                    im.save(f, "JPEG", quality=78, optimize=True)
                    break
                except Exception:
                    continue
        if f.exists():
            uris[aid] = ("data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode()) if embed else f"art/{aid}.jpg"
        else:
            uris[aid] = None
    return uris, src


def videos(run_dir, ad_ids, src, width=480):
    """ad_id -> "art/<id>.mp4" for the video ads whose public post can be fetched (yt-dlp, no Meta API). Kept in
    <run>/art/ like the pictures; a copy from an earlier run is reused. No tool or no public post = no video."""
    art, out = Path(run_dir) / "art", {}
    art.mkdir(exist_ok=True)
    for aid in ad_ids:
        f, vid = art / f"{aid}.mp4", (src.get(aid) or {}).get("video_id")
        if not f.exists():
            old = sorted(Path(run_dir).parent.glob(f"*/art/{aid}.mp4"))
            if old:
                shutil.copyfile(old[-1], f)
            elif vid and shutil.which("yt-dlp") and shutil.which("ffmpeg"):
                raw = art / f"{aid}.raw.mp4"
                try:
                    subprocess.run(["yt-dlp", "-q", "--no-warnings", "--socket-timeout", "30", "-f", "bv*[height<=1300]+ba/b", "--merge-output-format",
                                    "mp4", "-o", str(raw), f"https://www.facebook.com/reel/{vid}/"], capture_output=True, timeout=180)
                    if raw.exists():
                        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-vf", f"scale={width}:-2", "-c:v", "libx264", "-crf", "29",
                                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(f)], capture_output=True, timeout=300)
                except subprocess.TimeoutExpired:
                    pass
                finally:
                    if raw.exists():
                        raw.unlink()
        if f.exists() and f.stat().st_size < 14 * 1024 * 1024:
            out[aid] = f"art/{aid}.mp4"
    return out
