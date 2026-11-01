"""proof.py: the brand's real proof, indexed, with one clean way to cut a picture out of it.

Proof is what a customer, a creator or the brand itself already made and we own:
before-and-afters, photo reviews, curated UGC, the brand's own social posts, the
starter pack. The clip index (extract.py) covers raw creator footage; this covers
everything a picture slot (an email, a page, a static ad) reaches for first
(the owner, 2026-10-09: "index all the possible before and afters and social media
posts … ensure we have a clean path to extract").

    python3 machine/proof.py index   --brand <brand> [--label proof] [--from-mount]
        (default: Drive's own metadata and thumbnails through gdrive-creator, GDRIVE_SA_KEY
         in the environment; nothing is downloaded. --from-mount reads every file, slowly.)
    python3 machine/proof.py fetch   --brand <brand> <id> [<id> ...]   (originals into the index's src/ cache, through Drive)
    python3 machine/proof.py extract --brand <brand> <id> [--part pair|before|after|full]
                                     [--ratio 1:1] [--w 600] [--at 0.5] --out <file.jpg>
    python3 machine/proof.py list    --brand <brand> [--kind before-after] [--problem acne]

Writes runs/asset-index/<brand>/<label>/: proof.json (the manifest, one entry per
item, each with a status), thumbs/, and proof.html (a contact sheet). Media is
never moved or copied on the Drive; extract writes only to --out.
Brand-agnostic: which folders count as proof is decided by folder-name keywords
(KINDS), never by a brand name.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shared_paths as SP  # noqa: E402

_GDRIVE = next((d / "gdrive-creator" for d in Path(__file__).resolve().parents
                if (d / "gdrive-creator" / "gdrive_creator").is_dir()), None)
if _GDRIVE is not None and str(_GDRIVE) not in sys.path:
    sys.path.append(str(_GDRIVE))
from gdrive_creator import reach as R      # noqa: E402

READABLE = R.readable    # the seam tests patch: a Drive-folder path → a path that reads (LD-20 (proof pictures by API))

# folder keyword -> kind. First match on the item's path inside the brand folder wins.
KINDS = [
    ("before-after", "before-after"), ("before_after", "before-after"), ("beforeafter", "before-after"),
    ("/reviews", "review"), ("testimonial", "review"),
    ("/organic", "social-post"), ("social", "social-post"),
    ("creators-curated", "ugc"), ("ugc", "ugc"),
    ("content-starter-pack", "starter-pack"),
]
SKIP_PARTS = ("/content-creators/", "/ai-elements/", "/products/", "/email-sms/", "/competitors/", "/archive/ai-cast", "/archive/retired", "/archive/rushes")
IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"}
VIDEO = {".mp4", ".mov", ".m4v"}
PROBLEMS = [("ingrown", "ingrown hairs"), ("razor", "razor bumps"), ("bump", "razor bumps"), ("acne", "acne"),
            ("darkmark", "dark marks"), ("dark", "dark marks"), ("hyperpig", "dark marks"), ("wrinkle", "wrinkles"),
            ("texture", "texture"), ("oil", "oily skin")]


def kind_of(rel):
    low = "/" + rel.lower()
    if any(p in low for p in SKIP_PARTS):
        return None
    for key, kind in KINDS:
        if key in low:
            return kind
    return None


def parse_name(rel):
    """Person, problem, raw/final, and social handle/date, from the file's own name and folders."""
    stem = Path(rel).stem
    low = rel.lower().replace(" ", "").replace("_", "").replace("-", "")
    problem = next((p for k, p in PROBLEMS if k in low), None)
    stage = "final" if "/finals/" in rel.lower() else ("raw" if "/raws/" in rel.lower() else None)
    person = None
    m = re.match(r"([A-Za-z][A-Za-z]+?)(?:[_ ]|BnA|$)", stem)
    if m and not re.match(r"(IMG|Screenshot|IG|TT|Copy|DSC|PXL|video|image)", m.group(1), re.I):
        person = m.group(1)
    parts = Path(rel).parts
    if "narrative-story-customers" in parts:
        person = parts[parts.index("narrative-story-customers") + 1].title()
    handle = date = None
    s = re.match(r"(?:IG|TT|FB)_(?:reel|post|video|carousel)_(.+?)_(\d{4}-\d{2}-\d{2})", stem, re.I)
    if s:
        handle, date = s.group(1), s.group(2)
    group = None
    for p in parts[:-1]:
        if p.lower() in ("black", "latino", "white", "asian"):
            group = p
    return dict(person=person, problem=problem, stage=stage, handle=handle, date=date, group=group)


def drive_id(path):
    """gdrive-creator reach.drive_id(): by the key when there is one, else the mount's drivefs xattr
    (LD-47 (Drive sweep) step 2)."""
    try:
        return R.drive_id(path)
    except Exception:
        return None


def layout(w, h):
    """How a before/after sits in the frame: side by side, stacked, or one picture."""
    r = w / float(h)
    if r >= 1.55:
        return "side-by-side"
    if r <= 0.66:
        return "stacked"
    return "single"


def video_info(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height:format=duration", "-of", "json", str(path)],
                             capture_output=True, text=True, timeout=120)
        j = json.loads(out.stdout or "{}")
        st = (j.get("streams") or [{}])[0]
        return int(st.get("width") or 0), int(st.get("height") or 0), float(j.get("format", {}).get("duration") or 0)
    except Exception:
        return 0, 0, 0.0


def frame_at(path, t, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % t, "-i", str(path), "-frames:v", "1", "-q:v", "3", str(out)],
                   capture_output=True, timeout=180)
    return Path(out).exists()


def make_id(rel):
    s = re.sub(r"[^a-z0-9]+", "-", Path(rel).with_suffix("").as_posix().lower()).strip("-")
    return s[-80:]


def one(root, rel, kind, thumbs):
    from PIL import Image
    path = root / rel
    ext = path.suffix.lower()
    e = dict(id=make_id(rel), kind=kind, rel=rel, ext=ext, status="draft", **parse_name(rel))
    e["drive_id"] = drive_id(path)
    e["drive_url"] = ("https://drive.google.com/file/d/%s/view" % e["drive_id"]) if e["drive_id"] else None
    th = thumbs / (e["id"] + ".jpg")
    try:
        if ext in VIDEO:
            w, h, dur = video_info(path)
            e.update(media="video", w=w, h=h, seconds=round(dur, 1))
            if not th.exists():
                frame_at(path, max(0.0, dur * 0.4), th)
                if th.exists():
                    im = Image.open(th); im.thumbnail((384, 384)); im.save(th, quality=80)
        else:
            if ext == ".heic":
                tmp = thumbs / (e["id"] + ".heic.jpg")
                subprocess.run(["sips", "-s", "format", "jpeg", str(path), "--out", str(tmp)], capture_output=True, timeout=120)
                im = Image.open(tmp)
            else:
                im = Image.open(path)
            w, h = im.size
            e.update(media="image", w=w, h=h)
            if not th.exists():
                im = im.convert("RGB"); im.thumbnail((384, 384)); im.save(th, quality=80)
        e["layout"] = layout(e["w"], e["h"]) if kind == "before-after" and e.get("w") else None
        e["thumb"] = "thumbs/" + th.name if th.exists() else None
    except Exception as ex:
        e["error"] = str(ex)[:200]
    return e


# ---------- the fast road: Drive's own metadata and thumbnails, nothing downloaded ----------
GDC = HERE.parents[1] / "gdrive-creator"


def _svc():
    sys.path.insert(0, str(GDC))
    from gdrive_creator import engine as G  # the component's public surface: service()
    return G.service()


def drive_walk(svc, folder_id):
    """Every file under a Drive folder, with its path relative to that folder."""
    out, stack = [], [(folder_id, "")]
    fields = ("nextPageToken,files(id,name,mimeType,thumbnailLink,imageMediaMetadata(width,height),"
              "videoMediaMetadata(durationMillis,width,height))")
    while stack:
        fid, prefix = stack.pop()
        token = None
        while True:
            r = svc.files().list(q="'%s' in parents and trashed=false" % fid, fields=fields, pageSize=1000, pageToken=token,
                                 supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            for f in r.get("files", []):
                rel = (prefix + "/" + f["name"]).lstrip("/")
                if f["mimeType"] == "application/vnd.google-apps.folder":
                    if not f["name"].startswith(".") and not any(p in "/" + rel.lower() + "/" for p in SKIP_PARTS):
                        stack.append((f["id"], rel))
                else:
                    f["rel"] = rel; out.append(f)
            token = r.get("nextPageToken")
            if not token:
                break
    return out


def split_of(im):
    """Where a before/after is joined: a hard seam down the middle (side by side) or across it (stacked)."""
    n = 120
    px = list(im.convert("L").resize((n, n)).getdata())
    col = [sum(abs(px[y * n + x + 1] - px[y * n + x]) for y in range(n)) / float(n) for x in range(n - 1)]
    row = [sum(abs(px[(y + 1) * n + x] - px[y * n + x]) for x in range(n)) / float(n) for y in range(n - 1)]
    med = lambda v: sorted(v)[len(v) // 2] + 1e-6
    lo, hi = int(n * .45), int(n * .55)
    cmid, rmid = max(col[lo:hi]), max(row[lo:hi])
    if cmid / med(col) > 2.6 and cmid >= rmid:
        return "side-by-side"
    if rmid / med(row) > 2.6:
        return "stacked"
    return "single"


def one_drive(svc, f, kind, thumbs):
    import io as _io
    from PIL import Image
    rel = f["rel"]; ext = Path(rel).suffix.lower()
    e = dict(id=make_id(rel), kind=kind, rel=rel, ext=ext, status="draft", **parse_name(rel))
    e["drive_id"] = f["id"]; e["drive_url"] = "https://drive.google.com/file/d/%s/view" % f["id"]
    v, im_md = f.get("videoMediaMetadata"), f.get("imageMediaMetadata")
    if ext in VIDEO or v:
        e.update(media="video", w=(v or {}).get("width"), h=(v or {}).get("height"), seconds=round(int((v or {}).get("durationMillis") or 0) / 1000.0, 1))
    else:
        e.update(media="image", w=(im_md or {}).get("width"), h=(im_md or {}).get("height"))
    th = thumbs / (e["id"] + ".jpg")
    try:
        if not th.exists() and f.get("thumbnailLink"):
            url = re.sub(r"=s\d+$", "", f["thumbnailLink"]) + "=s400"
            resp, body = svc._http.request(url)
            if resp.status == 200:
                Image.open(_io.BytesIO(body)).convert("RGB").save(th, quality=82)
        if th.exists():
            e["thumb"] = "thumbs/" + th.name
            if kind == "before-after" and e["media"] == "image":
                lay = layout(e["w"], e["h"]) if e.get("w") else "single"
                e["layout"] = lay if lay != "single" else split_of(Image.open(th))
    except Exception as ex:
        e["error"] = str(ex)[:200]
    return e


def index_drive(brand, label="proof", workers=8, root=None):
    root = SP.brand_root(brand, root)
    fid = drive_id(root)
    if not fid:
        raise SystemExit("could not read the Drive id of %s" % root)
    out = SP.runs_root() / brand / label
    thumbs = out / "thumbs"; thumbs.mkdir(parents=True, exist_ok=True)
    svc = _svc()
    files = drive_walk(svc, fid)
    todo = [(f, kind_of(f["rel"])) for f in files if Path(f["rel"]).suffix.lower() in IMAGE | VIDEO]
    todo = [(f, k) for f, k in todo if k]
    print("proof (drive): %d items" % len(todo), flush=True)
    items = []
    for i, (f, k) in enumerate(todo):   # the API client is not thread-safe; thumbnails are small
        items.append(one_drive(svc, f, k, thumbs))
        if (i + 1) % 50 == 0:
            print("  %d/%d" % (i + 1, len(todo)), flush=True)
    _write(out, brand, items)
    print("wrote %s (%d items)" % (out / "proof.json", len(items)))
    return out


def index(brand, label="proof", workers=8, root=None):
    root = SP.brand_root(brand, root)
    out = SP.runs_root() / brand / label
    thumbs = out / "thumbs"; thumbs.mkdir(parents=True, exist_ok=True)
    old = {}
    if (out / "proof.json").exists():
        old = {e["rel"]: e for e in json.load(open(out / "proof.json")).get("items", []) if not e.get("error")}
    todo = []
    for dp, dn, fn in os.walk(root):
        reldir = "/" + os.path.relpath(dp, root).lower() + "/"
        dn[:] = [d for d in dn if not d.startswith(".") and not any(p in reldir + d.lower() + "/" for p in SKIP_PARTS)]
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), root)
            if Path(f).suffix.lower() not in IMAGE | VIDEO:
                continue
            k = kind_of(rel)
            if k:
                todo.append((rel, k))
    items = [old[r] for r, _ in todo if r in old]
    fresh = [(r, k) for r, k in todo if r not in old]
    fresh.sort(key=lambda rk: (Path(rk[0]).suffix.lower() in VIDEO, rk[1] != "before-after"))  # photos and before-afters first; videos stream slowly
    print("proof: %d items (%d already indexed, %d to read)" % (len(todo), len(items), len(fresh)), flush=True)
    done = 0
    with ThreadPoolExecutor(workers) as ex:
        for e in ex.map(lambda rk: one(root, rk[0], rk[1], thumbs), fresh):  # noqa: E731
            items.append(e); done += 1
            if done % 25 == 0:
                print("  %d/%d" % (done, len(fresh)), flush=True)
                _write(out, brand, items)
    _write(out, brand, items)
    print("wrote %s (%d items)" % (out / "proof.json", len(items)))
    return out


def _write(out, brand, items):
    ex = out / "exclude.json"
    words = [w.lower() for w in json.load(open(ex)).get("never_use", [])] if ex.exists() else []
    for e in items:
        if any(w in (e.get("rel") or "").lower() for w in words):
            e["state"] = "excluded"
    items = sorted(items, key=lambda e: (e["kind"], e.get("problem") or "~", e["rel"] or ""))
    counts = {}
    for e in items:
        counts[e["kind"]] = counts.get(e["kind"], 0) + 1
    json.dump(dict(brand=brand, counts=counts, items=items,
                   _what="Real proof the brand owns, one entry per file. status is draft until a person approves an item for use; state is free for notes."),
              open(out / "proof.json", "w"), indent=1)
    _page(out, brand, items, counts)


def _page(out, brand, items, counts):
    E = html.escape
    cards = "".join(
        '<figure data-k="%s"><img loading="lazy" src="%s" alt=""><figcaption><b>%s</b> %s<br><small>%s</small></figcaption></figure>' % (
            E(e["kind"]), E(e.get("thumb") or ""), E(e.get("person") or e.get("handle") or Path(e["rel"]).stem[:28]),
            E(" · ".join(x for x in (e.get("problem"), e.get("layout"), e.get("stage"), e.get("group"), e.get("media") == "video" and "%ss video" % e.get("seconds")) if x)),
            E(e["id"])) for e in items)
    page = ("<!doctype html><meta charset=utf-8><title>%s proof</title><style>body{font:13px system-ui;background:#111;color:#eee;margin:16px}"
            "main{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px}figure{margin:0}img{width:100%%;aspect-ratio:1;object-fit:cover;border-radius:6px;background:#222}"
            "small{color:#888;word-break:break-all}</style><h1>%s proof · %s</h1><main>%s</main>") % (
        E(brand), E(brand), E(", ".join("%d %s" % (v, k) for k, v in counts.items())), cards)
    open(out / "proof.html", "w").write(page)


def load(brand, label="proof"):
    return json.load(open(SP.runs_root() / brand / label / "proof.json"))


def fetch(brand, ids, label="proof"):
    """Download originals through Drive (gdrive-creator) into the index's own src/ cache; extract reads them from there."""
    data = load(brand, label)
    by = {e["id"]: e for e in data["items"]}
    dest = SP.runs_root() / brand / label / "src"; dest.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(GDC))
    from gdrive_creator import engine as G
    svc = G.service()
    for i in ids:
        e = by.get(i)
        if not e:
            raise SystemExit("no proof item %r (see proof.py list)" % i)
        out = dest / (e["id"] + e["ext"])
        if not out.exists() or out.stat().st_size == 0:
            part = out.with_name(out.name + ".part")   # a dropped connection never leaves a half file under the real name
            G.get_media(e["drive_id"], str(part), svc=svc)
            part.rename(out)
        print(out)


def extract(brand, item_id, part="full", ratio=None, w=600, at=0.5, out=None, label="proof", root=None, focus=0.5):
    """Cut one item into a ready picture: the pair, the before half, the after half, or a frame of a video."""
    from PIL import Image
    data = load(brand, label)
    e = next((x for x in data["items"] if x["id"] == item_id), None)
    if not e:
        raise SystemExit("no proof item %r (see proof.py list)" % item_id)
    cached = SP.runs_root() / brand / label / "src" / (e["id"] + e["ext"])
    src = cached
    if not cached.exists():
        # the Drive folder when it reads, else the API copy by name — a launchd job cannot open the folder (LD-18 (headless policy off))
        try:
            src = READABLE(SP.brand_root(brand, root) / e["rel"])
        except (R.NoDrive, SystemExit) as x:
            raise SystemExit("proof item %r does not read here or through Drive: %s" % (item_id, x))
    if e.get("media") == "video":
        tmp = Path(out).with_suffix(".frame.jpg")
        frame_at(src, max(0.0, (e.get("seconds") or 1) * at), tmp)
        im = Image.open(tmp).convert("RGB"); tmp.unlink()
    else:
        im = Image.open(src).convert("RGB")
    W, H = im.size
    if part in ("before", "after"):
        lay = e.get("layout") or layout(W, H)
        if lay == "side-by-side":
            im = im.crop((0, 0, W // 2, H) if part == "before" else (W - W // 2, 0, W, H))
        elif lay == "stacked":
            im = im.crop((0, 0, W, H // 2) if part == "before" else (0, H - H // 2, W, H))
        else:
            raise SystemExit("%s is one picture (%s), it has no separate %s half" % (item_id, lay, part))
    if ratio:
        a, b = (float(x) for x in ratio.split(":"))
        r = a / b; W, H = im.size
        if W / float(H) > r:
            nw = int(H * r); x = int((W - nw) * focus); im = im.crop((x, 0, x + nw, H))
        else:
            nh = int(W / r); y = int((H - nh) * focus); im = im.crop((0, y, W, y + nh))
    if w and im.width > w:
        im = im.resize((w, int(w * im.height / im.width)), Image.LANCZOS)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=88)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("index"); a.add_argument("--brand", required=True); a.add_argument("--label", default="proof"); a.add_argument("--workers", type=int, default=8)
    a.add_argument("--from-mount", action="store_true", help="read every file through the mounted Drive (slow) instead of Drive's own metadata")
    b = sub.add_parser("extract"); b.add_argument("--brand", required=True); b.add_argument("id"); b.add_argument("--part", default="full", choices=["full", "pair", "before", "after"])
    b.add_argument("--ratio"); b.add_argument("--w", type=int, default=600); b.add_argument("--at", type=float, default=0.5); b.add_argument("--focus", type=float, default=0.5); b.add_argument("--out", required=True); b.add_argument("--label", default="proof")
    f = sub.add_parser("fetch"); f.add_argument("--brand", required=True); f.add_argument("ids", nargs="+"); f.add_argument("--label", default="proof")
    c = sub.add_parser("list"); c.add_argument("--brand", required=True); c.add_argument("--kind"); c.add_argument("--problem"); c.add_argument("--label", default="proof")
    o = ap.parse_args()
    if o.cmd == "index":
        (index if o.from_mount else index_drive)(o.brand, o.label, o.workers)
    elif o.cmd == "fetch":
        fetch(o.brand, o.ids, o.label)
    elif o.cmd == "extract":
        print(extract(o.brand, o.id, "full" if o.part == "pair" else o.part, o.ratio, o.w, o.at, o.out, o.label, focus=o.focus))
    else:
        for e in load(o.brand, o.label)["items"]:
            if e.get("state") != "excluded" and (not o.kind or e["kind"] == o.kind) and (not o.problem or (e.get("problem") or "") == o.problem):
                print("%-60s %-13s %-14s %s" % (e["id"], e["kind"], e.get("problem") or "", e.get("drive_url") or ""))


if __name__ == "__main__":
    main()
