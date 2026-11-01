import json, subprocess, base64, re
from pathlib import Path
S = Path(__file__).parent; T = S / "tree"; OUT = S / "thumbs"
import sys; sys.path.append(str(Path(__file__).resolve().parents[3] / "brandpath"))
import drive_index  # components/brandpath: Shared Assets on whoever's Drive is signed in
SA = Path(drive_index.mount() or drive_index.NO_MOUNT)  # LD-55 (Drive literal check): named in drive_index only
res = {}

def enc(p):
    return "data:image/jpeg;base64," + base64.b64encode(Path(p).read_bytes()).decode()

def shrink(src, dst, w=220):
    subprocess.run(["magick", str(src), "-resize", f"{w}x", "-quality", "72", str(dst)], check=True, capture_output=True)
    return enc(dst)

def dur(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)

def frames(v, key, n=6):
    d = dur(v); out = []
    for i in range(n):
        t = d * (0.04 + 0.92 * i / (n - 1)) if n > 1 else 0.5
        dst = OUT / f"{key}-{i}.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(v), "-frames:v", "1", "-vf", "scale=220:-2", "-q:v", "6", str(dst)], capture_output=True)
        if dst.exists(): out.append({"t": round(t, 1), "src": enc(dst)})
    return out

# winners (video)
for d in sorted((SA / "lab/damon/swipes").glob("top1-brand-b-*")):
    m = re.search(r"\*\*Source\*\* (.+?)\s*$", (d / "asset.md").read_text(), re.M)
    if m and Path(m.group(1)).is_file():
        res["runs/video-teardown/brand-b/" + d.name] = {"kind": "video", "frames": frames(Path(m.group(1)), d.name)}
        print("ok", d.name)
# statics
st = {
 "runs/image-teardown/brand-b/brand-b-batch-top-static-mofu-showing-hands": SA / "brands/brand-b/intake/ads/paid-ads/ads-2026/body-scrub/middle-of-the-funnel/problem-why-dark-spots-come-back/MOFU-Ads-Mechanism-01.jpg",
 "runs/image-teardown/brand-b/brand-b-batch-top-static-hands-photostrip-p140": SA / "lab/damon/image-production/runs/260902b/ads/brand-b-bodyscrub-static-ai-none-spothider-darkspots-pigmentmemory-handsapplication-photostrip-p140-9x16-260902b-a01.png",
}
for k, p in st.items():
    if p.is_file():
        res[k] = {"kind": "static", "frames": [{"t": None, "src": shrink(p, OUT / (Path(k).name + ".jpg"), 320)}]}; print("ok", k)
# formats: Drive strips
for code in ["DavXLyHKZSB", "Dbmik5RNWQV", "DUe1HtWjI3p"] + [p["id"] for p in json.loads((T / "components/swipe-organic/hua-jin/posts.json").read_text())["posts"][:10]]:
    sd = SA / "lab/damon/swipe-organic/records/swipe-videos" / code
    imgs = sorted((sd / "strip").glob("*.jpg"))[:6]
    if imgs:
        key = ("components/swipe-organic/records/teardowns/" if code in ("DavXLyHKZSB", "Dbmik5RNWQV", "DUe1HtWjI3p") else "components/swipe-organic/records/swipe-videos/") + code
        res[key] = {"kind": "video", "frames": [{"t": None, "src": shrink(i, OUT / f"{code}-{n}.jpg")} for n, i in enumerate(imgs)]}
        print("ok", code, len(imgs))
    elif (sd / "video.mp4").is_file():
        key = "components/swipe-organic/records/swipe-videos/" + code
        res[key] = {"kind": "video", "frames": frames(sd / "video.mp4", code)}; print("ok vid", code)
(S / "thumbs.json").write_text(json.dumps(res))
print(len(res), "items", round((S / "thumbs.json").stat().st_size / 1e6, 2), "MB")
