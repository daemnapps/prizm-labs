#!/usr/bin/env python3
"""Check every connection the image lane depends on, and say what is broken.

    check.py                   every check, brand-side ones for EVERY brand on file
    check.py --brand <brand>   the same, brand-side checks for that brand only
    check.py --json            the same, as data (the board and the map read this)

A map of where things live goes stale the moment something moves. This does
not describe the wiring — it exercises it: opens the files, runs the query,
counts what came back. Every check names what it looked for, so a failure
tells you where to go rather than that something, somewhere, is wrong.
"""

import json, os, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

LAB, LANE, DRIVE = P.LAB, P.LANE, P.DRIVE
WS = P.REPO                                              # ai-workspace, for git — found, not counted


def brands_asked():
    """`--brand <x>`, or every brand folder on file. The self-check was pinned
    to one brand, so it reported the lane healthy while another brand's offer
    bank was missing. No brand is the default; with none named, all are checked."""
    if "--brand" in sys.argv:
        i = sys.argv.index("--brand")
        if i + 1 >= len(sys.argv):
            sys.exit("--brand wants a folder name under brands/")
        name = sys.argv[i + 1]
        if not (P.BRANDS / name).is_dir():
            sys.exit(f"no brand folder at {P.BRANDS / name}")
        return [name]
    return sorted(d.name for d in P.BRANDS.iterdir()
                  if d.is_dir() and not d.name.startswith(("_", ".")))

CHECKS = []


def check(group, name, what):
    """Register a check. `what` returns (ok, detail) or raises."""
    CHECKS.append((group, name, what))
    return what


# ---------------------------------------------------------------- the swipes

def swipe_records():
    d = P.SWIPE
    brands = sorted(p.name for p in d.iterdir()
                    if p.is_dir() and not p.name.startswith("_")
                    and (p / "angles").is_dir()) if d.is_dir() else []
    if not brands:
        return False, f"no brands with angle records under {d}"
    n = sum(len(list((d / b / "angles").glob("*.md"))) for b in brands)
    return True, f"{len(brands)} brands, {n} angle records — {', '.join(brands)}"


def swipe_media():
    d = DRIVE / "swipe-paid"
    if not d.is_dir():
        return False, f"Drive not mounted at {d}"
    tot, ang = 0, 0
    for b in sorted(p for p in d.iterdir() if p.is_dir()):
        for a in sorted((b / "angles").glob("*")) if (b / "angles").is_dir() else []:
            ph = a / "photos"
            if ph.is_dir():
                ang += 1
                tot += len(list(ph.glob("*.jpg"))) + len(list(ph.glob("*.png")))
    return (tot > 0), f"{tot} statics across {ang} angles on Drive"


def swipe_intake():
    r = subprocess.run([sys.executable, str(LANE / "tools/swipe_intake.py"),
                        "--list", "<competitor>"], capture_output=True, text=True)
    if r.returncode != 0:
        return False, (r.stderr.strip().splitlines() or ["failed"])[-1]
    rows = [l for l in r.stdout.splitlines() if l.strip().startswith(("0", "1"))]
    return bool(rows), f"intake lists {len(rows)} angles carrying statics"


# ------------------------------------------------------------- the brand side

def language_layer(brand):
    q = P.LANGUAGE
    if not q.is_file():
        return False, f"query tool missing at {q}"
    env = dict(os.environ, AI_WORKSPACE=str(P.BRANDS.parent))
    r = subprocess.run([sys.executable, str(q), "--brand", brand,
                        "--stage", "hooks"], capture_output=True, text=True, env=env)
    out = r.stdout
    if "no rows matched" in out or not out.strip():
        return False, "query returned no rows — check the avatar path"
    rows = out.count('\n- "')
    head = next((l for l in out.splitlines() if l.startswith("_")), "")
    return rows > 0, f"{rows} hook rows returned · {head.strip('_ ')}"


def brand_files(brand):
    BRAND = P.brand(brand)
    want = {"offer bank": BRAND["offer"], "avatars": BRAND["avatars"],
            "products": BRAND["products"]}
    missing = [k for k, v in want.items() if not v.exists()]
    if missing:
        return False, "missing from the lab: " + ", ".join(missing)
    n = len(list(BRAND["products"].iterdir()))
    return True, f"offer bank + {n} product entries, all under brands/"


def packshot(brand):
    p = P.brand(brand)["products"]
    n = len(list(p.rglob("*.png"))) + len(list(p.rglob("*.jpg"))) if p.is_dir() else 0
    return (n > 0), f"{n} product references (composited, never generated)"


def anchors(brand):
    BRAND = P.brand(brand)
    want = {"identity-anchors.md": BRAND["identity"],
            "hook-ledger.md": BRAND["hook_ledger"]}
    missing = [k for k, v in want.items() if not v.is_file()]
    return (not missing), ("missing: " + ", ".join(missing)) if missing else \
        "identity anchors + hook ledger, in the lab"


# ------------------------------------------------------------------ the chain

STAGES = [("1", "stage1-image-teardown"), ("2", "stage2-image-replication"),
          ("2b", "stage2b-image-elements"),
          ("3", "stage3-image-injection"), ("4", "stage4b-image-hook"),
          ("5", "stage4e-image-variations"), ("6", "stage6-image-brief")]


def prompts():
    d = LANE / "prompts"
    have = [n for _, n in STAGES if list(d.glob(n + "*.md"))]
    miss = [n for _, n in STAGES if not list(d.glob(n + "*.md"))]
    return (not miss), (f"all {len(have)} stages present" if not miss
                        else "missing: " + ", ".join(miss))


def lexicon():
    if P.LEXICON.is_file():
        n = len(P.LEXICON.read_text().splitlines())
        return True, f"{n} lines, at {P.LEXICON.relative_to(LAB)}"
    return False, f"visual lexicon not found at {P.LEXICON}"


def runners():
    # fal_client.py is not checked: fal was retired 2026-09-13 and the client
    # is parked under tools/superseded/. Pictures are made on Higgsfield, in
    # the image-production lane, which checks its own key.
    want = {"gemini_text.py": P.GEMINI_TEXT, "gemini_image.py": P.GEMINI_IMAGE,
            "claude_text.py": P.CLAUDE_TEXT, "compose.py": P.COMPOSE}
    miss = [k for k, v in want.items() if not v.is_file()]
    return (not miss), ("missing: " + ", ".join(miss)) if miss else \
        "text, vision and compositor runners present"


def api_key():
    """Keys by NAME, never by path — the vault, then the environment."""
    import os
    found, missing = [], []
    vault = Path.home() / ".daemn/keys.env"
    txt = vault.read_text() if vault.is_file() else ""
    for name in ("GEMINI_API_KEY",):
        if os.environ.get(name) or f"{name}=" in txt:
            found.append(name)
        else:
            missing.append(name)
    if (Path.home() / ".gemini.env").is_file() and "GEMINI_API_KEY" not in found:
        found.append("GEMINI_API_KEY")
        missing = [m for m in missing if m != "GEMINI_API_KEY"]
    return (not missing), (", ".join(found) + " present" if not missing
                           else "missing: " + ", ".join(missing))


def claude_cli():
    r = subprocess.run(["claude", "--version"], capture_output=True, text=True)
    if r.returncode != 0:
        return False, "claude CLI not on PATH — stages 3-6 cannot run"
    return True, r.stdout.strip().split()[0] if r.stdout.strip() else "present"


def imagemagick():
    r = subprocess.run(["magick", "-version"], capture_output=True, text=True)
    if r.returncode != 0:
        return False, "ImageMagick not on PATH — the type layer cannot be set"
    return True, r.stdout.splitlines()[0].split("(")[0].strip()


# ------------------------------------------------------------------ the media

def media_rule():
    gi = LANE / ".gitignore"
    if not gi.is_file():
        return False, "no .gitignore — pictures would enter git"
    t = gi.read_text()
    ok = "*.png" in t and "*.jpg" in t
    stray = subprocess.run(["git", "-C", str(WS), "ls-files", "image-teardown"],
                           capture_output=True, text=True).stdout.splitlines()
    bad = [s for s in stray if s.lower().endswith((".png", ".jpg", ".jpeg"))]
    if bad:
        return False, f"{len(bad)} pictures tracked in git — should be Drive only"
    return ok, "pictures excluded from git, none tracked"


def mirror():
    m = LAB / "mirror.py"
    if not m.is_file():
        return False, "mirror.py missing"
    r = subprocess.run([sys.executable, str(m), "--check"],
                       capture_output=True, text=True, cwd=str(LAB))
    if r.returncode != 0:
        return False, (r.stderr.strip().splitlines() or ["failed"])[-1][:90]
    tot = next((l for l in r.stdout.splitlines() if "TOTAL" in l), "")
    dang = next((l for l in r.stdout.splitlines() if "dangling" in l), "")
    detail = " ".join(tot.split()[1:6]) if tot else "dry run clean"
    return ("warn" if dang else True), detail + (" · " + dang.strip() if dang else "")


def runs():
    d = LANE / "runs"
    live = [p for p in d.iterdir() if p.is_dir() and p.name != "archive"] if d.is_dir() else []
    if not live:
        return "warn", "no live runs"
    det = []
    for p in sorted(live):
        n = len(list((p / "out").glob("*.md"))) if (p / "out").is_dir() else 0
        det.append(f"{p.name} ({n} stages)")
    return True, " · ".join(det)


def lab_only():
    """Nothing in the lane may read outside lab/damon. Ruled 2026-08-28."""
    hits = []
    # check.py states the rule and paths.py documents it — both name the old
    # root in prose. Everything else naming it is a real reach.
    for f in sorted(LANE.rglob("*.py")) + sorted(LANE.rglob("*.sh")):
        if "/runs/" in str(f) or f.name in ("check.py", "paths.py"):
            continue
        for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            if "devel/daemn" in line and not line.lstrip().startswith("#"):
                hits.append(f"{f.relative_to(LANE)}:{i}")
    return (not hits), ("reaches outside the lab: " + ", ".join(hits[:4])) if hits \
        else "no tool reads outside lab/damon"


for g, n, f in [
    ("The swipes", "Angle records in git", swipe_records),
    ("The swipes", "Creatives on Drive", swipe_media),
    ("The swipes", "Intake opens a run from a swipe id", swipe_intake),
    ("The chain", "Every stage prompt", prompts),
    ("The chain", "Shared visual vocabulary", lexicon),
    ("The chain", "Model runners", runners),
    ("The chain", "Model keys", api_key),
    ("The chain", "Claude runner reachable", claude_cli),
    ("The chain", "Nothing reaches outside the lab", lab_only),
    ("The chain", "Type compositor", imagemagick),
    ("The media", "Pictures stay out of git", media_rule),
    ("The media", "Drive mirror", mirror),
    ("The media", "Live runs", runs),
]:
    check(g, n, f)

# The brand-side checks, once per brand asked for.
for _b in brands_asked():
    for n, f in [("Language layer answers a query", language_layer),
                 ("Avatar, product and offer", brand_files),
                 ("Product photography", packshot),
                 ("Identity anchors and hook ledger", anchors)]:
        check(f"The brand · {_b}", n, (lambda f=f, b=_b: f(b)))


def run():
    out = []
    for group, name, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        out.append(dict(group=group, name=name,
                        state="warn" if ok == "warn" else ("ok" if ok else "fail"),
                        detail=detail))
    return out


if __name__ == "__main__":
    res = run()
    if "--json" in sys.argv:
        print(json.dumps(res, indent=2))
        sys.exit(0)
    mark = {"ok": "  ok  ", "warn": " warn ", "fail": " FAIL "}
    last = None
    for r in res:
        if r["group"] != last:
            last = r["group"]
            print(f"\n{last}")
        print(f"  [{mark[r['state']]}] {r['name']:<38} {r['detail']}")
    bad = [r for r in res if r["state"] == "fail"]
    warn = [r for r in res if r["state"] == "warn"]
    print(f"\n{len(res)-len(bad)-len(warn)} ok · {len(warn)} warn · {len(bad)} failing")
    sys.exit(1 if bad else 0)
