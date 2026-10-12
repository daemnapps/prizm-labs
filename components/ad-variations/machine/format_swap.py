#!/usr/bin/env python3
"""format_swap.py — the variation cycle's swap step: a proven ad's CONCEPT re-told in another video's FORMAT.

    python3 format_swap.py --concept <teardown run> --format <format teardown> --brand <brand> \\
        --product glow-face-scrub --avatar spot-cover [--dials "awareness: problem-aware"] --label <name> [--dry-run]

the owner, 5 Oct 2026: "taking the teardown records then change the format … the same concept just a new format."
The concept is read from a video-teardown run (`stages/1-teardown.md`, `1c-doctrine.md`, `1-transcript.md`) or an
image-teardown run (`01-teardown.md`, `02-replication-spec.md`); the format from any teardown that carries a
teardown + spec (an organic swipe's `records/teardowns/<code>/stage1-teardown.md` + `stage2-spec.md`, or a
video-teardown run). Brand context comes only from `brands/<brand>/` (brandctx). Writes
`runs/ad-variations/<brand>/swap-<label>/` — `sent.md` (the prompt as filled), `run.json`, and the answer as
`spec.md` (written by the model, or by the session when the model login is out: the run stops at WAITING).
Plans only; generates nothing.
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "run-kit"))
from run_kit import paths  # noqa: E402
REPO = paths.repo(HERE)
sys.path.insert(0, str(HERE))
import brandctx as BC  # noqa: E402

PROMPTS = HERE.parent / "prompts" / "stage-format-swap"
CAP = 24000


def newest_prompt():
    ps = sorted(p for p in PROMPTS.glob("stage-format-swap-v*-damon.md"))
    return max(ps, key=lambda p: int(p.stem.split("-v")[1].split("-")[0]))


def first(d, names, cap=CAP):
    for n in names:
        p = Path(d) / n
        if p.is_file():
            t = p.read_text(errors="replace")
            return (t if len(t) <= cap else t[:cap] + f"\n… [cut at {cap:,} of {len(t):,} characters — full file: {p}]"), str(p)
    return "(not on file)", None


def concept_inputs(d):
    t, a = first(d, ["stages/1-teardown.md", "01-teardown.md", "stage1-teardown.md"])
    doc, b = first(d, ["stages/1c-doctrine.md", "02-replication-spec.md", "stage2-spec.md"], 16000)
    tr, c = first(d, ["stages/1-transcript.md", "transcript.md"], 16000)
    return t, doc, tr, [x for x in (a, b, c) if x]


def format_inputs(d):
    t, a = first(d, ["stage1-teardown.md", "stages/1-teardown.md", "01-teardown.md"])
    s, b = first(d, ["stage2-spec.md", "stages/2-spec.md", "02-replication-spec.md"])
    return t, s, [x for x in (a, b) if x]


def brand_context(brand, product, avatar):
    bc = BC.BrandContext(REPO, brand, avatar)
    parts = [bc.rules()]
    for rel, lim in ((f"products/{product}/product.md", 12000), ("products/offer-bank.md", 14000),
                     (f"core-avatars/{avatar}/profile.md", 9000)):
        t = bc.file(rel, lim)
        parts.append(f"=== brands/{brand}/{rel} ===\n{t if t is not None else BC.MISSING}")
    return "\n\n".join(parts), bc.read_files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--concept", required=True); ap.add_argument("--format", required=True)
    ap.add_argument("--brand", required=True); ap.add_argument("--product", required=True)
    ap.add_argument("--avatar", required=True); ap.add_argument("--dials", default="none — the concept's own awareness, hook and angle")
    ap.add_argument("--label", required=True); ap.add_argument("--model", default=None, help="run the model; default stops at WAITING for the session")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    ct, cd, ctr, cfiles = concept_inputs(a.concept)
    ft, fs, ffiles = format_inputs(a.format)
    brand, bfiles = brand_context(a.brand, a.product, a.avatar)
    prompt = newest_prompt()
    filled = prompt.read_text().format(concept_teardown=ct, concept_doctrine=cd, concept_transcript=ctr,
                                       format_teardown=ft, format_spec=fs, brand_context=brand, dials=a.dials)
    out = REPO / "runs" / "ad-variations" / a.brand / f"swap-{a.label}"
    missing = [n for n, v in (("concept teardown", ct), ("format teardown", ft), ("format spec", fs)) if v == "(not on file)"]
    if a.dry_run:
        print(json.dumps({"out": str(out), "prompt": prompt.name, "chars": len(filled), "missing": missing,
                          "concept": cfiles, "format": ffiles}, indent=1)); return
    if missing:
        raise SystemExit(f"format_swap: missing {', '.join(missing)}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "sent.md").write_text(filled)
    run = {"label": a.label, "brand": a.brand, "product": a.product, "avatar": a.avatar, "dials": a.dials,
           "concept": a.concept, "format": a.format, "prompt": prompt.name, "concept_files": cfiles,
           "format_files": ffiles, "brand_files": bfiles, "opened": datetime.now().isoformat(timespec="seconds")}
    if a.model:
        sys.path.insert(0, str(REPO / "components" / "run-kit"))
        from run_kit import model as M
        (out / "spec.md").write_text(M.call(filled, a.model, "format-swap") + "\n")
        run["state"] = "done"
    else:
        run["state"] = "WAITING — the session writes spec.md from sent.md"
    (out / "run.json").write_text(json.dumps(run, indent=1))
    print(json.dumps({"out": str(out), "state": run["state"], "chars": len(filled)}, indent=1))


if __name__ == "__main__":
    main()
