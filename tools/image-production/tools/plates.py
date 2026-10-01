#!/usr/bin/env python3
"""The plates a batch needs, and the files that come back. Two halves.

    plates.py prepare --run runs/<brand>/<batch>     what to generate
    plates.py ingest  --run runs/<brand>/<batch> --results results.json

Damon, 2026-09-14: *"we do not have a higgsfield key so remove that from this
workflow entirely."*

There is no API key and there is not going to be one, so there is no
unattended generation path and nothing in this lane should imply there is.
Higgsfield's image models are reached through its MCP, which a script cannot
call — so the middle of this step is driven by a session, and the two halves
either side of it are code.

**prepare** reads the batch spec and writes `inbox/jobs.json`: one entry per
ad, with the prompt exactly as it will be sent, the aspect, and the reference
ids. Nothing is generated.

**the session** generates those prompts on Higgsfield — **the model each job
names**, the aspect each job names, the cast and product as `<<<element>>>`
ids — and writes `{slug: path-to-png}` into a results file.

Every job carries a `model` and a `model_why`. A frame with a person in it
goes to `gpt_image_2`, everything else to `nano_banana_pro` — the split the
AvatarHype table makes and we had never tested. `--ab <model>` generates every
plate both ways so a side-by-side can only be showing you the model.

**ingest** pads each 4:5 frame out to 9:16 with bands off its own edges,
checks the bands, and files it into `inbox/` where the finisher expects it.

Same shape as `make_variations.py`, for the same reason, and the reason is
written down in both places so nobody wires an API path back in.
"""
import argparse, json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pad as PAD


PERSON_MODEL = "gpt_image_2"      # a photoreal human
OBJECT_MODEL = "nano_banana_pro"  # everything else, and every edit


def model_for(ad, spec, override=None):
    """Which model paints this plate, and the reason, recorded either way.

    Ruled 2026-09-14 from the AvatarHype model table: generating a photoreal
    PERSON and editing a frame are two different jobs, and they route to two
    different models. We had been sending every plate to nano_banana_pro and
    using gpt_image_2 only for cast stills — the split was never tested.

    `cast` on the ad is the signal and it is already declared, so nothing is
    inferred from the prompt text. An ad that names its own model still wins:
    a measured exception outranks a default.
    """
    if override:
        return override, "forced on the command line"
    if ad.get("model"):
        return ad["model"], "named by the ad"
    if spec.get("model"):
        return spec["model"], "named by the batch"
    if ad.get("cast"):
        return PERSON_MODEL, f"a person is in frame (cast: {ad['cast']})"
    return OBJECT_MODEL, "no person in frame"


def prepare(run: Path, override=None, ab=None):
    spec = json.loads((run / "batch.json").read_text())
    jobs = []
    for ad in spec["ads"]:
        pf = run / "prompts" / f"{ad['slug']}.txt"
        if not pf.is_file():
            print(f"  ! {ad['slug']}: no prompt at prompts/{ad['slug']}.txt")
            continue
        model, why = model_for(ad, spec, override)
        prompt = pf.read_text().strip()
        arms = [(ad["slug"], model, why)]
        if ab and ab != model:
            # Same prompt, same refs, one model different — so the only thing
            # a side-by-side can be showing you is the model.
            arms = [(f"{ad['slug']}@{model}", model, why),
                    (f"{ad['slug']}@{ab}", ab, "A/B arm")]
        for slug, m, w in arms:
            jobs.append({
                "slug": slug,
                "aspect": ad.get("aspect", "4:5"),
                "model": m,
                "model_why": w,
                "prompt": prompt,
            })
    inbox = run / "inbox"; inbox.mkdir(parents=True, exist_ok=True)
    f = inbox / "jobs.json"
    f.write_text(json.dumps({"batch": spec.get("batch"), "jobs": jobs}, indent=1))
    by = {}
    for j in jobs:
        by[j["model"]] = by.get(j["model"], 0) + 1
    print(f"{len(jobs)} plates to generate → {f}")
    for m, n in sorted(by.items()):
        print(f"  {n:>3} on {m}")
    print("generate these on Higgsfield through the MCP, then:")
    print(f"  plates.py ingest --run {run} --results <results.json>")
    return f


def ingest(run: Path, results: Path):
    res = json.loads(results.read_text())
    inbox = run / "inbox"; inbox.mkdir(parents=True, exist_ok=True)
    ok, bad = [], []
    for slug, src in res.items():
        s = Path(src)
        if not s.is_file():
            bad.append((slug, "no file at " + src)); continue
        raw = inbox / f"{slug}-4x5.png"
        shutil.copy(s, raw)
        try:
            # 4:5 in, 9:16 out, bands taken off the frame's own edges.
            PAD.pad(raw, inbox / f"{slug}.png")
            ok.append(slug)
        except Exception as e:
            bad.append((slug, f"pad failed: {e}"))
    for s in ok:
        print(f"  ✓ {s}")
    for s, why in bad:
        print(f"  ✗ {s} — {why}")
    print(f"{len(ok)} in the inbox, {len(bad)} failed")
    return ok, bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--run", required=True)
    p.add_argument("--model", help="force one model for every plate")
    p.add_argument("--ab", help="also generate every plate on this model, "
                               "slug@model, for a side-by-side")
    i = sub.add_parser("ingest"); i.add_argument("--run", required=True)
    i.add_argument("--results", required=True)
    a = ap.parse_args()
    r = Path(a.run).resolve()
    if not (r / "batch.json").is_file():
        sys.exit(f"no batch.json in {r}")
    if a.cmd == "prepare":
        prepare(r, a.model, a.ab)
    else:
        ingest(r, Path(a.results).resolve())
