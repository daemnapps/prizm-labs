#!/usr/bin/env python3
"""Re-run stage 8 for finished runs, at current prompts.

    python3 rerender.py [label ...] [--model MODEL] [--dry-run]

Every run is re-rendered against ITS OWN brand, avatar and product — read from
that run's run.json, never pinned here. A run whose record does not say which
brand, avatar or product it was written for is skipped with a line saying so
(older runs predate the `product` field; re-run those through copy.py with
--rerun-from stage8, which takes --product). Finds runs in both homes:
runs/copy-machine/<brand>/<label>/ and results/<label>/.

Uses the same brand variable map copy.py does (brands/<brand>/variables/copy.md).
"""
import datetime
import json
import re
import sys

import context
import copy as C
import formats as F
import paths as P


def brand_files(brand, avatar):
    """{language_bank, offer_file} for one brand + avatar, through the brand's
    own variables/copy.md — the same map copy.py reads."""
    root = P.WORKSPACE / "brands" / brand
    rels = {"language_bank": "customer/language-bank.md", "offer_file": "offers/offer-bank.md"}
    m = root / "variables" / "copy.md"
    if m.is_file():
        for hit in re.finditer(r"^\s*\|?\s*`\{?([a-z_]+)\}?`\s*\|\s*`([^`]+\.(?:md|json|/))`?",
                               m.read_text(), re.M):
            rels[hit.group(1)] = hit.group(2)
    out = {}
    for var in ("language_bank", "offer_file"):
        rel = rels[var].replace("<avatar>", avatar or "")
        f = root / rel
        out[var] = f.read_text().strip() if f.is_file() else ""
    return root, out


def main(argv):
    dry = "--dry-run" in argv or "--dry" in argv
    model = None
    if "--model" in argv:
        model = argv[argv.index("--model") + 1]
    labels = [a for i, a in enumerate(argv)
              if not a.startswith("--") and (i == 0 or argv[i - 1] != "--model")]
    runs = ([P.find_run(l) or P.RESULTS / l for l in labels] if labels
            else [d for d in P.all_runs() if (d / "stage8--render.md").is_file()])
    for d in runs:
        label = d.name
        if not (d / "stage7--close.md").is_file():
            print(f"  skip {label} — no argument to render"); continue
        st = json.loads((d / "run.json").read_text())
        brand, avatar, product = st.get("brand"), st.get("avatar"), st.get("product")
        lacking = [n for n, v in (("brand", brand), ("avatar", avatar), ("product", product)) if not v]
        if lacking:
            print(f"  skip {label} — its run.json does not say its {', '.join(lacking)}; "
                  "re-run it with copy.py --rerun-from stage8 instead"); continue
        product_text = C.read(product)
        if not product_text:
            print(f"  skip {label} — product file not found: {product}"); continue
        root, files = brand_files(brand, avatar)
        if dry:
            print(f"  would re-render {label}  (brand {brand} · avatar {avatar} · {product})"); continue
        R = lambda n: (d / n).read_text()
        ctx, _, _ = context.load((st.get("context") or {}).get("picked") or [])
        rec = d / "stage1--record.md"
        try:
            C.run_stage("stage8", d, model, st,
                today=datetime.date.today().strftime("%A, %-d %B %Y"), triage=R("stage0--triage.md"),
                spec=R("stage2--spec.md"), injection=R("stage7--close.md"),
                record=rec.read_text() if rec.is_file() else "",
                placement=R("stage4--placement.md"), hooks=R("stage5--hooks.md"),
                product_file=product_text, offer_file=files["offer_file"],
                language_bank=files["language_bank"],
                brand_context=ctx, formats=F.render(root),
                output_formats=st.get("output_formats") or ", ".join(F.keys(root)),
                channel=st.get("channel", "Meta (feed / Reels)"))
        except C.UsageLimit as e:
            sys.exit(f"USAGE LIMIT — stopped at {label}: {e}")
        (d / "run.json").write_text(json.dumps(st, indent=2) + "\n")
        print(f"  re-rendered {label}")


if __name__ == "__main__":
    main(sys.argv[1:])
