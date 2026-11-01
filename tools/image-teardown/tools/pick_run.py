#!/usr/bin/env python3
"""One swipe-bank pick, torn down and briefed — the mini's road for the owner's picks.

    python3 tools/pick_run.py --brand brand-a --product flex --avatar fed-up-king \
        --pick tt-7679242758120328462 --ask runs/creative-strategist/brand-a/flex-problem-native-quiz/ask.json \
        [--sub bald-bumps-guy] [--source organic|paid] [--dry-run]

the owner, 2026-10-23: "Moving forward, I need to send this stuff to the mini, not
sitting on my computer." A pick is a picture he ticked on the Swipe Bank page.
The picture is put on the shared Drive at `Shared Assets/swipe/picks/<brand>/<pick>.jpg`
when the pick is filed; this script fetches it back by name through
gdrive-creator (the mount on a person's Mac, the API with the person's own key
on the mini — components rule 4), opens one run on it (`chain.py open`) and
runs every stage under the given order (`--ask`: its offer and funnel win over
the offer bank), then makes the pictures (`tools/pictures.py`; `--no-pictures`
stops at the brief). Gates hold as everywhere else; a held run still writes its
brief and says why.

Prints the run's slug last, so the caller can find the run.
"""
import argparse, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import paths as P  # noqa: E402


def fetch(brand, pick, dest):
    sys.path.append(str(P.REPO / "components" / "gdrive-creator"))
    from gdrive_creator import reach
    return reach.get(["swipe", "picks", brand], f"{pick}.jpg", dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True); ap.add_argument("--product", required=True)
    ap.add_argument("--avatar", required=True); ap.add_argument("--pick", required=True)
    ap.add_argument("--ask", required=True, help="the order file (ask.json), repo-relative")
    ap.add_argument("--sub", help="the sub-avatar, when the pick is for one")
    ap.add_argument("--source", choices=("organic", "paid"),
                    help="where the swipe came from (default: organic for tt-/ig- picks, else paid)")
    ap.add_argument("--no-pictures", action="store_true",
                    help="stop at the brief; make no pictures")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch the picture and resolve every stage; open no run, call no model")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        pic = fetch(a.brand, a.pick, tmp)
        if pic is None:
            sys.exit(f"no picture at Shared Assets/swipe/picks/{a.brand}/{a.pick}.jpg — file the pick first")
        print(f"picture: {pic}")
        if a.dry_run:
            print("dry run: picture found; no run opened")
            return
        source = a.source or ("organic" if a.pick.split("-")[0] in ("tt", "ig", "igp") else "paid")
        r = subprocess.run([sys.executable, str(ROOT / "chain.py"), "open", "--brand", a.brand,
                            "--file", str(pic), "--name", f"pick-{a.pick}", "--source", source],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode:
            sys.exit(f"could not open the run: {(r.stderr or r.stdout).strip()[-400:]}")
        slug = r.stdout.strip().splitlines()[-1]
    cmd = [sys.executable, str(HERE / "run.py"), f"runs/{slug}", "all", "--brand", a.brand,
           "--avatar", a.avatar, "--product", a.product, "--ask", a.ask]
    if a.sub:
        cmd += ["--sub", a.sub]
    code = subprocess.run(cmd, cwd=ROOT).returncode
    if code == 0 and not a.no_pictures:
        # The pictures (the owner, 2026-10-23: "These statics are brilliant. Let's
        # ensure that this is established in our chains."): the brand step's
        # written frame, made into the ad by image-production.
        code = subprocess.run([sys.executable, str(HERE / "pictures.py"), f"runs/{slug}", "--brand", a.brand,
                               "--product", a.product], cwd=ROOT).returncode
    print(slug)
    sys.exit(code)


if __name__ == "__main__":
    main()
