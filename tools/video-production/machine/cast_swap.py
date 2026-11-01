#!/usr/bin/env python3
"""cast_swap — put a banked cast member into a real clip as the WHOLE character, not just a face.

the owner, 2026-10-12: "only faces have changed — you need to do the entire character, their body build, etc. You
should be uploading the entire casting sheet as reference for this work … establish this in the chain."

Every swap (Higgsfield Genjutsu `hf_mult_replace_object`, through the session's Higgsfield door) sends:
  video_references  the source clip (>= 4 s; pad forward+reverse below that — the cut keeps the forward part only)
  image_references  the cast member's BASELINE, in this order: headshot, look, details, angles-expressions (never the master, 2026-10-27);  was: master, turnaround, angles-expressions,
                    details, and the look that matches the clip's clothes (look_for)
and the one standard prompt below, so the face, head, hair, skin tone, body build and proportions all come from
the sheet, and the clip keeps only its motion, the real product, the place and the camera.

    python3 cast_swap.py refs   <cast-slug> [--wearing "<what the clip's person wears>"]   # the files to upload, in order
    python3 cast_swap.py prompt [--state before|after] [--keep "<what the clip must keep>"] [--erase "<caption text>"]
    python3 cast_swap.py put    <session.jsonl> <file> [<file> ...]   # PUT each file to the upload URL the door gave it

Brand-agnostic: the cast folder is found through the brand's casting root; nothing here names a brand or a person.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path
from typing import Optional

WS = Path(__file__).resolve().parents[3]
SHEETS = ("turnaround", "angles-expressions", "details")


def cast_dir(slug: str, brand: str) -> Path:
    d = WS / "runs" / "ai-elements" / brand / "casting" / slug / "full"
    if not (d / "master.png").exists():
        raise SystemExit(f"no casting sheet for {slug} under {d}")
    return d


def look_for(d: Path, wearing: str = "") -> Optional[Path]:
    """The look sheet whose name shares the most words with what the clip's person wears; else the first look."""
    looks = sorted((d / "sheets").glob("look-*.png"))
    if not looks:
        return None
    words = set(re.findall(r"[a-z]+", wearing.lower()))
    score = lambda p: len(words & set(p.stem.split("-")))
    return max(looks, key=score) if words else looks[0]


BASELINE = ("headshot", "details", "angles-expressions")


def refs(slug: str, brand: str, wearing: str = "") -> list:
    """The cast member's BASELINE, in the order the swap sends it: headshot, look, details, expressions. Never the master
    (the owner, 2026-10-27; the sheets' never_send_stems refuses it again at the door)."""
    d = cast_dir(slug, brand)
    sh = d / "sheets"
    lk = look_for(d, wearing)
    out = [sh / "headshot.png"] + ([lk] if lk else []) + [sh / f"{s}.png" for s in BASELINE[1:]]
    out = [f for f in out if f.exists()]
    if len(out) < 3:
        raise SystemExit(f"{slug} has no baseline yet (headshot, look, details, expressions): found {', '.join(f.stem for f in out) or 'none'}. "
                         "Build the baseline first; the master is never sent.")
    return out


STATE = {   # the brief's before / after, said in so many words on every swap (the owner, 2026-10-12: "being very clear on
            # his before state and after state")
    "before": "This is his BEFORE state: clusters of small raised razor bumps and flat dark marks down the front and "
              "sides of his neck and under his jaw, as the master and details sheets show them.",
    "after": "This is his AFTER state: his neck, the underside of his jaw and his jawline completely clear and smooth — "
             "no bumps, no dark marks, no stubble — the same skin tone and natural texture with visible pores, and a "
             "fresh lineup. Everything else about him, body included, is identical to the sheets.",
}


def prompt(keep: str = "", erase: str = "", state: str = "") -> str:
    keep = keep or "the real product in his hand, how he holds it and moves it on his face, the room, the camera and the light"
    text = ("Replace the person completely with the person in the reference sheets — the whole character, not only "
            "the face: the same face and head, hairline and haircut, beard, skin tone, age, height, body build, weight "
            "and proportions, arms and hands, exactly as the reference pictures (headshot, details and expressions) show him, "
            "dressed as the look sheet shows. Nothing of the original person remains. "
            f"Keep everything else exactly as in the source video: {keep}. One continuous take, the source's own motion "
            "and timing.")
    if state:
        text += " " + STATE[state]
    return text + (f" Erase the on-screen caption '{erase}' and every word on screen: no text anywhere." if erase
                   else " No words anywhere.")


def put(session: Path, files: list) -> None:
    """The Higgsfield door hands back one presigned upload URL per file, named after it; PUT each file to its URL."""
    urls = {}
    for line in session.read_text(errors="ignore").splitlines():
        if "upload_url" not in line:
            continue
        for m in re.finditer(r'--data-binary @([^ \']+) \'(https://upload\.higgsfield\.ai/[^\'\\]+)', line):
            urls[m.group(1)] = m.group(2)
    for f in map(Path, files):
        u = urls.get(f.name)
        if not u:
            print(f"{f.name}: no upload URL in the session"); continue
        ct = "video/mp4" if f.suffix.lower() in (".mp4", ".mov") else ("image/png" if f.suffix.lower() == ".png" else "image/jpeg")
        code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-X", "PUT", "-H", f"Content-Type: {ct}",
                               "--data-binary", f"@{f}", u], capture_output=True, text=True).stdout
        print(f.name, code)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("refs"); r.add_argument("slug"); r.add_argument("--brand", required=True); r.add_argument("--wearing", default="")
    p = sub.add_parser("prompt"); p.add_argument("--keep", default=""); p.add_argument("--erase", default="")
    p.add_argument("--state", choices=sorted(STATE), default="", help="before | after — required in practice: the brief says which")
    u = sub.add_parser("put"); u.add_argument("session"); u.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "refs":
        print("\n".join(str(x) for x in refs(a.slug, a.brand, a.wearing)))
    elif a.cmd == "prompt":
        print(prompt(a.keep, a.erase, a.state))
    else:
        put(Path(a.session), a.files)


if __name__ == "__main__":
    main()
