#!/usr/bin/env python3
"""Design intake — a brand's Figma email board, from the export to the
format bank, in one command. The same steps that built the Brand B bank
(2026-09-02/03), so the next brand's board goes through the same door.

    python3 sweep/intake.py <export.zip or folder> --brand <brand> [--serve-port 8791]

What happens, in order (each step writes where the next one reads):
  1 unpack    the export lands in the scratch bank folder (boards/<board>/…)
  2 capture   every artboard rendered to results/format-bank/<board>/NN.png
              (+ rects.json) — the export's own picture of each email
  3 index     sweep/layouts.py — the layout families and variants, theme tags
              → brands/<brand>/email-sms/design-formats/layouts.json|md and the
              local index page
  4 rebuild   sweep/rebuild.py — every export rebuilt as clean HTML on the
              brand's bedrock, with a replication spec per email
  5 qc        sweep/qc.py — copy, pictures, buttons, order checked against
              the source; results/format-bank/qc.md
  6 pictures  sweep/capture_clean.py — the rebuilds as pictures, then
              sweep/sheets.py contact sheets, then sweep/qa_index.py — the
              QA page and the team mirror (design-formats/rebuild-qa.md)

The export is expected as Figma's HTML export (Components.bundle.js per
board under boards/), the shape Brand B's bank arrived in. A different shape
stops at step 1 with a message saying what was found.
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SCRATCH = Path(os.environ.get("SWEEP_SCRATCH", "/private/tmp/claude-501/sweep"))


def run(cmd, **kw):
    print("→", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], **kw)
    if r.returncode:
        sys.exit(f"step failed: {' '.join(str(c) for c in cmd)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--serve-port", type=int, default=8791)
    ap.add_argument("--skip-pictures", action="store_true", help="stop after QC (no clean renders)")
    a = ap.parse_args()
    env = dict(os.environ, AI_WORKSPACE=os.environ.get("AI_WORKSPACE", "."))

    # 1 unpack
    bank = SCRATCH / f"format-bank-{a.brand}"
    src = Path(a.export)
    if src.is_file() and src.suffix == ".zip":
        bank.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as z:
            z.extractall(bank)
        print(f"unpacked {src.name} -> {bank}")
    elif src.is_dir():
        if bank.exists():
            shutil.rmtree(bank)
        shutil.copytree(src, bank)
        print(f"copied {src} -> {bank}")
    else:
        sys.exit(f"not a zip or a folder: {src}")
    # the bank's boards folder may sit one level down
    boards = next((p for p in [bank / "boards"] + list(bank.glob("*/boards")) if p.is_dir()), None)
    if boards is None:
        sys.exit(f"no boards/ folder in the export — found: {[p.name for p in bank.iterdir()][:12]}")
    if boards.parent != bank:
        bank = boards.parent
    found = sorted(p.name for p in boards.iterdir() if (p / "Components.bundle.js").is_file())
    if not found:
        sys.exit("no board carries a Components.bundle.js — this is not a Figma HTML export")
    print(f"{len(found)} board(s): {', '.join(found)}")

    # a local server the capture reads from
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(a.serve_port), "--bind", "127.0.0.1"],
                           cwd=bank, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # 2 capture the export's own render of every artboard
        run([sys.executable, HERE / "sweep" / "capture.py", "--bank", bank, "--url", f"http://127.0.0.1:{a.serve_port}/"], env=env)
        # 3 the layout index
        run([sys.executable, HERE / "sweep" / "layouts.py", "--bank", bank, "--brand", a.brand], env=env)
        # 4 the rebuild, 5 the checks
        run([sys.executable, HERE / "sweep" / "rebuild.py", "--bank", bank, "--brand", a.brand], env=env)
        run([sys.executable, HERE / "sweep" / "qc.py", "--bank", bank, "--brand", a.brand], env=env)
        if not a.skip_pictures:
            # 6 pictures, sheets, the QA page and the team mirror
            run(["caffeinate", "-i", sys.executable, HERE / "sweep" / "capture_clean.py"], env=env)
            run([sys.executable, HERE / "sweep" / "sheets.py"], env=env)
            run([sys.executable, HERE / "sweep" / "qa_index.py", a.brand], env=env)
    finally:
        srv.terminate()
    print("\ndone. QA page: http://localhost:8785/results/format-bank/qa-index.html")


if __name__ == "__main__":
    main()
