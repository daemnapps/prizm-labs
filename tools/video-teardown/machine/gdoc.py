#!/usr/bin/env python3
"""Stage 8 — the finished brief as a Google Doc.

    python3 gdoc.py <run-slug>                 mirror + render, print what's needed
    python3 gdoc.py <run-slug> --ids ids.json  render with real Drive image ids

The last step of the chain, and until now the only one done by hand. It makes
one file: `<slug>-gdoc.html`, shaped so Google Docs' HTML import turns it into
a real document — headings that build the outline, a page break between
frames, and every frame picture in place.

This script does everything deterministic: mirror the run to the Drive, lay
out the document, put the picture URLs in. Turning that file into a real Doc
is `drive.py`, which run.py calls straight after as stage 9. It used to be a
session's job by hand, and a run whose session forgot ended with nothing
anyone could open (2026-08-26).

The pictures need a URL Docs can fetch — it takes neither a local path nor a
base64 data URI. Every file synced to the Drive carries its own Drive id in an
extended attribute, so once the run is mirrored each frame can name itself and
the ids come straight off the filesystem. No lookup, no search, no hand-fed id
list. (`--ids` still overrides, for a frame the mount has not finished syncing.)
"""
import argparse, hashlib, json, re, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C
import md as MD

# Google Drive stamps every synced file with its own id. run.py already leans
# on this to let a source video name itself; the frames can do the same.
DRIVE_XATTR = "com.google.drivefs.item-id#S"


def drive_id(path: Path):
    try:
        out = subprocess.run(["xattr", "-p", DRIVE_XATTR, str(path)],
                             capture_output=True, text=True)
        v = out.stdout.strip()
        return v if out.returncode == 0 and len(v) > 10 else ""
    except Exception:
        return ""


def ids_from_drive(slug):
    """Every frame, published under a name that changes when the picture does.

    A frame keeps its filename across regenerations, so Drive keeps its file
    id — and Google's image fetcher then serves the CACHED render of that id
    to Docs. Two documents built hours apart, from completely regenerated
    frames, came out fifteen bytes different: the same old pictures both
    times (2026-08-26). Stable ids are the problem here, not the feature.

    So each frame is published as `<key>-<hash of its bytes>.png`. Same
    picture, same name, same id, nothing re-uploaded. New picture, new name,
    new id, and Docs has no cache to serve.

    Raises C.MountError without a Drive mount (2026-08-27). It used to return
    `{}` there, which reads exactly like "the pictures are not synced yet" and
    is how a document quietly came out with every picture missing and no reason
    given.
    """
    dest = C.run_mirror_dir(slug) / "frames" / "doc"   # raises without a mount
    src = C.runs_root() / slug / "frames" / "frames"
    if not src.is_dir():
        return {}   # no frames at all — an honest empty, not a hidden failure
    dest.mkdir(parents=True, exist_ok=True)
    want, out = {}, {}
    for f in sorted(src.iterdir()):
        if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        tag = hashlib.md5(f.read_bytes()).hexdigest()[:10]
        pub = dest / f"{f.stem}-{tag}{f.suffix.lower()}"
        want[pub.name] = f.stem
        if not pub.exists():
            shutil.copy2(f, pub)
    # anything from an older build is dead weight and a stale link
    for old in dest.iterdir():
        if old.name not in want:
            old.unlink()
    for pub in sorted(dest.iterdir()):
        fid = drive_id(pub)
        if fid:
            out[want[pub.name]] = fid
    return out

IMG = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", re.M)

# Docs fetches this form server-side; the /file/d/ share link returns an
# interstitial page rather than the image and imports as a broken slot.
DRIVE_IMG = "https://drive.google.com/uc?export=view&id={id}"

CSS = """
body{font-family:Arial,Helvetica,sans-serif;font-size:11pt;line-height:1.5;color:#111}
h1{font-size:20pt;margin:0 0 4pt}
h2{font-size:15pt;margin:18pt 0 4pt;page-break-before:always}
h3{font-size:12pt;margin:12pt 0 3pt}
h4{font-size:11pt;margin:14pt 0 3pt;color:#222}
p{margin:0 0 8pt}
table{border-collapse:collapse;width:100%;margin:0 0 10pt}
td,th{border:1px solid #ccc;padding:5pt 7pt;vertical-align:top;font-size:10pt}
th{background:#f2f2f2;text-align:left}
blockquote{margin:0 0 8pt;padding:6pt 10pt;border-left:3px solid #888;background:#f7f7f7}
/* A frame is 9:16, so width sets the height: 280pt wide is ~500pt tall, and
   with the frame's own six lines above it that clears a page — which is why
   every picture was landing on the next page under a slab of white. 165pt is
   ~293pt tall, so the whole frame block fits together. */
img{width:165pt;display:block;margin:2pt 0 0}
.frame{page-break-inside:avoid;break-inside:avoid}
.slot{border:1px dashed #b00;color:#b00;padding:10pt;font-size:9pt}
.cap{font-size:9pt;color:#555;margin:2pt 0 12pt}
.notice{border:1pt solid #b00;background:#fff5f5;color:#7a0000;
  padding:8pt 10pt;margin:0 0 14pt;font-size:10pt}
"""


def frame_key(src):
    """'frames/frames/c1s01.png' -> 'c1s01' — the name the manifest uses."""
    return Path(src).stem


def build(slug, ids=None, out=None, tail=""):
    """`tail` is Markdown appended after the brief — today the link to the
    example video beside it in her folder (Damon, 2026-09-18: "the last
    component in the brief itself, make a hyperlink to the example video")."""
    run = C.runs_root() / slug
    # The page (stage 7b) is what she reads; the spec is ours. A run that has
    # a page sends the page. Older runs without one still send the spec.
    brief = run / "stages" / "7b-page.md"
    if not brief.exists():
        brief = run / "7-final-brief.md"
    if not brief.exists():
        brief = run / "brief-final.md"
    # On the AI route the ai-lane brief IS the deliverable — stages 6/7/7b do
    # not run there (2026-09-18), so the stage-5 brief is what gets sent.
    if not brief.exists():
        brief = run / "stages" / "5-brief.md"
    if not brief.exists():
        sys.exit(f"no brief for {slug} — run the chain through stage 5 first")

    ids = ids or {}
    text = brief.read_text()
    if tail:
        text = text.rstrip() + "\n\n" + tail.strip() + "\n"
    placed, missing = 0, []

    # Each frame is a bold line, which Docs imports as bold body text — so a
    # 29-frame shot list arrives as one unnavigable slab and the outline shows
    # three entries. Promote every frame to a heading: the outline then lists
    # the frames, which is how anyone actually moves around a shot list.
    text = re.sub(r"^\*\*(Frame \d+[^*]*)\*\*\s*$", r"### \1", text, flags=re.M)

    def swap(m):
        nonlocal placed
        alt, src = m.group(1), m.group(2)
        # A slot the brief never filled stays visible as a slot; silently
        # dropping it would read as a frame that needs no picture.
        if src.strip() in ("—", "-", ""):
            return f'<p class="slot">{alt} — no picture generated</p>'
        key = frame_key(src)
        fid = ids.get(key)
        if not fid:
            missing.append(key)
            return (f'<p class="slot">{alt} — picture not yet on the Drive '
                    f'({key})</p>')
        placed += 1
        return (f'<img src="{DRIVE_IMG.format(id=fid)}" alt="{alt}">'
                f'<p class="cap">{alt}</p>')

    # Swap the pictures out before the markdown renderer sees them: it would
    # emit <img src="frames/frames/…"> which Docs imports as a broken slot.
    _holds = []

    def stash(m):
        _holds.append(swap(m))
        return f"\x00IMG{len(_holds)-1}\x00"

    text = IMG.sub(stash, text)
    body = MD.render(text)
    # Unwrap the whole paragraph the renderer put around the placeholder, not
    # just its opening tag — stripping one end leaves a stray </p>, and an
    # <img> nested in a <p> is where Docs' importer starts dropping pictures.
    for i, h in enumerate(_holds):
        body = re.sub(rf"<p>\s*\x00IMG{i}\x00\s*</p>", lambda _m, h=h: h, body)
        body = body.replace(f"\x00IMG{i}\x00", h)

    # The brief separates frames with a markdown rule. Where it lands right
    # after the picture the renderer swallows it into that paragraph and it
    # shows up as a literal "---" under the caption.
    body = re.sub(r"(</p>)\s*---\s*(</p>)", r"\1", body)
    body = body.replace("<p> ---</p>", "").replace("<p>---</p>", "")

    # Keep a frame and its picture on one page. Docs honours page-break-inside
    # on a block, so each frame gets one — the heading, its directions and its
    # picture travel together instead of the picture being pushed over alone.
    body = re.sub(r"(<h4>Frame )", r'</div><div class="frame"><h4>Frame ', body)
    if '<div class="frame">' in body:
        body = body.replace('</div><div class="frame">', '<div class="frame">', 1)
        # The transcript is not part of the last frame. Close the block before
        # it, or the whole script ends up inside a keep-together box.
        tail = re.search(r"<h2>The script, straight through</h2>", body)
        if tail:
            body = body[:tail.start()] + "</div>" + body[tail.start():]
        else:
            body += "</div>"

    # Every brief carries this, and it is generated rather than pasted in by
    # hand — a notice that has to appear on 60-odd documents is not a person's
    # job, and one missed is the one that matters (Damon, 2026-08-29).
    notice = (
        '<p class="notice"><strong>AI generation is for demonstrative purposes '
        'only.</strong> The AI images in this brief show framing and mood. '
        'Your AI image will NOT be used in advertising without your explicit '
        'consent.</p>')
    # The page carries the notice itself, directly above its pictures, where
    # it answers the question; wrapping it again top and bottom is noise.
    if "AI generation is for demonstrative purposes only" in text:
        notice = ""
    # A document with no pictures in it needs no notice about pictures
    # (Damon, 2026-09-18: the brief is words only).
    if not placed and not missing:
        notice = ""
    html = (f"<html><head><meta charset=\"utf-8\"><title>{slug}</title>"
            f"<style>{CSS}</style></head><body>{notice}{body}{notice}"
            f"</body></html>")
    # Inside the run, so it mirrors to the Drive with everything else and the
    # records plane can point at it. Beside the machine it was invisible to
    # anyone without this laptop.
    out = Path(out) if out else (run / f"{slug}-gdoc.html")
    out.write_text(html)
    return out, placed, missing


def mirror(slug):
    """Mirror the run, and when it CANNOT, say so and record it on the run.

    Returns the destination, or None with `mirror_error` written into run.json.
    The document still gets built afterwards — the words are safe on this disk;
    it is the loss that needs telling."""
    try:
        dest = C.mirror_to_drive(slug)
        print(f"  mirrored to Drive: {dest}")
        return dest
    except C.MountError as e:
        rj = C.runs_root() / slug / "run.json"
        if rj.exists():
            C.record_mirror_error(rj.parent, json.loads(rj.read_text()), e)
            print(f"  NOT MIRRORED — {e}")
            print("  recorded on the run as mirror_error: this run has NOT "
                  "reached the team")
        else:
            print(f"  NOT MIRRORED — {e}")
        return None


def main():
    ap = argparse.ArgumentParser(description="The final brief, as a Google Doc.")
    ap.add_argument("slug")
    ap.add_argument("--ids", help="JSON map of frame key -> Drive file id")
    ap.add_argument("--no-mirror", action="store_true")
    ap.add_argument("--url", help="the Doc's link, once it has been created — "
                                  "recorded on the run so the records plane can "
                                  "point at it")
    a = ap.parse_args()

    if a.url:
        rj = C.runs_root() / a.slug / "run.json"
        st = json.loads(rj.read_text())
        st["gdoc_url"] = a.url
        rj.write_text(json.dumps(st, indent=2))
        print(f"  recorded on the run: {a.url}")

    mirrored = mirror(a.slug) if not a.no_mirror else None

    # The mount is the ONLY source of truth. There used to be a cache beside
    # the run, filling in for frames Drive had not finished syncing — and it
    # filled them in with the PREVIOUS build's ids, which is precisely how a
    # rebuilt document came out carrying old pictures (2026-08-26). A missing
    # id is a wait; a wrong id is a wrong document. Wait.
    n_frames = len([f for f in (C.runs_root() / a.slug / "frames" / "frames").iterdir()
                    if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]) \
        if (C.runs_root() / a.slug / "frames" / "frames").is_dir() else 0
    if a.ids:
        ids = json.loads(Path(a.ids).read_text())
    else:
        ids = {}
        for attempt in range(12):
            try:
                ids = ids_from_drive(a.slug)
            except C.MountError as e:
                # No mount is not "still syncing" — waiting would never end.
                print(f"  NO PICTURES — {e}")
                print("  the document is still written, with a visible slot "
                      "where each picture belongs")
                break
            if n_frames and len(ids) >= n_frames:
                break
            print(f"  waiting for the Drive to finish syncing "
                  f"({len(ids)}/{n_frames})…")
            time.sleep(15)
    if ids:
        print(f"  {len(ids)} picture id(s) read off the Drive")
    out, placed, missing = build(a.slug, ids)
    # The document is written INTO the run, so it needs a second pass to reach
    # the Drive — the first one ran before it existed.
    if not a.no_mirror and mirrored:
        mirror(a.slug)
    print(f"  {out}")
    print(f"  {placed} picture(s) placed, {len(missing)} still needing a Drive id")
    if missing:
        print("  needs ids for: " + ", ".join(sorted(set(missing))[:6])
              + (" …" if len(set(missing)) > 6 else ""))
        try:
            print(f"  frames are on the Drive at: "
                  f"{C.run_mirror_dir(a.slug) / 'frames' / 'frames'}")
        except C.MountError:
            pass   # already said so, loudly, above


if __name__ == "__main__":
    main()
