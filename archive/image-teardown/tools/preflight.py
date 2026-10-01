#!/usr/bin/env python3
"""Can this chain run today, for this brand, without anybody being asked?

    preflight.py --brand <b> --product <p> --avatar <a> --swipe <s>
    preflight.py --audit                    the agnostic audit alone

Damon, 2026-09-14: *"we're going to be running this every single day for
numerous brands and products that we stand up… there is no room for error or
me needing to step in and answer specific questions at all."*

So two kinds of check, and both have to be green before a run is worth
starting.

**Inputs** — every file the six stages will ask for, resolved now rather than
nine minutes into stage 3. A missing brand file is a one-line fix before the
run; found halfway through, it is an hour.

**Agnostic** — no brand, product, avatar or offer named anywhere in the code
or the prompts that drive a run. A hard-coded brand does not fail loudly; it
quietly aims the next brand's run at the last brand's files.

Exit is 0 only when nothing failed. Warnings do not fail the run.
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
sys.path.insert(0, str(HERE))
import paths as P

# The live path: what actually runs when a chain starts. Everything else in
# the folder is history, and holding it to this bar would only teach people
# to ignore the check.
LIVE = ["chain.py", "serve.py", "tools/run.py", "tools/briefs.py",
        "tools/brief_page.py", "tools/paths.py", "tools/gemini_text.py",
        "tools/gemini_image.py", "tools/claude_text.py"]

# Brands and products are looked up, never spelled. This list is read off the
# repo so the check cannot go stale as brands are stood up.
def known_names():
    """Brand and swipe folder names only.

    Product slugs are deliberately not scanned: `flex` and `core` are real
    <brand> products and also `display:flex` and `core-avatars`, so matching
    them buries the real findings under CSS. A brand or swipe name appearing
    in code is the failure that actually misroutes a run.
    """
    names = set()
    # A brand is a folder under brands/ that holds products; a swipe brand is
    # one under swipe-paid/ that holds blocks. Without those markers the scan
    # also picked up `prompts`, `teardown`, `organic` and `refs` — plain
    # subfolders — and drowned the real findings again.
    if P.BRANDS.is_dir():
        names |= {d.name.lower() for d in P.BRANDS.iterdir()
                  if (d / "products").is_dir()}
    for root, sub in ((P.SWIPE, "blocks"), (P.SWIPE_ORGANIC, "posts")):
        if root.is_dir():
            names |= {d.name.lower() for d in root.iterdir() if (d / sub).is_dir()}
    return {n for n in names if len(n) > 3}


def audit():
    """No brand or swipe named in the code that runs.

    Only executable lines count. A name in a comment or a docstring is
    someone explaining why a rule exists — often quoting the very run that
    proved it — and rewriting those to say `<brand>` loses the evidence. What
    breaks a run is a name in a default, a path or a literal.
    """
    import io, tokenize
    names = known_names()
    bad = []
    files = LIVE + sorted(str(q.relative_to(LANE)) for q in (LANE / "prompts").glob("*.md"))
    for rel in files:
        f = LANE / rel
        if not f.is_file():
            bad.append((rel, 0, "missing from the lane")); continue
        src = f.read_text(errors="replace")

        if f.suffix == ".py":
            # Strip comments and docstrings by tokenising, so only code is read.
            code = {}
            try:
                toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
            except (tokenize.TokenError, IndentationError):
                toks = []
            prev = tokenize.INDENT
            for tok in toks:
                if tok.type == tokenize.COMMENT:
                    continue
                if tok.type == tokenize.STRING and prev in (
                        tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE,
                        tokenize.NL, tokenize.ENCODING):
                    prev = tok.type; continue          # a docstring
                code.setdefault(tok.start[0], []).append(tok.string)
                if tok.type not in (tokenize.NL, tokenize.NEWLINE):
                    prev = tok.type
            lines = {n: " ".join(v) for n, v in code.items()}
        else:
            # An HTML comment at the head of a prompt is its provenance — who
            # ruled what, quoted — the same thing a code comment is, and the
            # board exempts it the same way. One quoted ruling in a stage-7
            # header was failing preflight, and so blocking `start`, for
            # every brand (found 2026-09-20). Blanked in place, so the line
            # numbers reported for everything else stay true.
            src = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"),
                         src, flags=re.S)
            lines = {n: l for n, l in enumerate(src.splitlines(), 1)
                     if not re.match(r"\s*(#|>|\||-{2,})", l)}

        for n, line in lines.items():
            low = line.lower()
            for name in names:
                if re.search(rf"\b{re.escape(name)}\b", low):
                    bad.append((rel, n, f"names {name!r}: {line.strip()[:88]}"))
    return bad


def inputs(brand, product, avatar, swipe):
    """Every file the stages will ask for, resolved now."""
    b = P.brand(brand)
    want = [
        ("brand folder",     b["root"]),
        ("avatar profile",   P.avatar_profile(brand, avatar) if avatar else b["avatars"]),
        ("product",          P.product(brand, product) if product else b["products"]),
        ("offer bank",       b["offer"]),
        ("identity anchors", b["identity"]),
        ("palette",          b["palette"]),
        ("casting roster",   b["cast"] / "roster.json", "warn"),
        ("angle bank",       P.BRANDS / brand / "strategy/angles.json"),
        ("language layer",   P.LANGUAGE),
        ("swipe library",    swipe_lib(swipe)),
        ("swipe on Drive",   drive_swipe(swipe)),
    ]
    out = []
    for row in want:
        label, path = row[0], row[1]
        kind = row[2] if len(row) > 2 else "fail"
        out.append((label, path, Path(path).exists(), kind))
    return out


def swipe_coverage(swipe):
    """How many of this library's blocks have a still on Drive.

    A block with no picture cannot be torn down, and the skip only showed
    up mid-run: six picks went in, three runs came out (2026-09-14, froya —
    43 of 71 blocks had a still). Counted before anything starts now.
    """
    if not swipe:
        return None
    sys.path.insert(0, str(HERE.parent))
    try:
        import chain
    except Exception:
        return None
    try:
        bs = chain.blocks(swipe)
    except SystemExit:
        return None
    have = sum(1 for b in bs if chain.pick_still(b, swipe))
    return have, len(bs)


def swipe_lib(swipe):
    """Paid ranks by duplication, organic by engagement. Both are libraries."""
    if not swipe:
        return P.SWIPE
    for root, sub in ((P.SWIPE, "blocks"), (P.SWIPE_ORGANIC, "posts")):
        d = root / swipe / sub
        if d.is_dir():
            return d
    return P.SWIPE / swipe / "blocks"


def drive_swipe(swipe):
    """Where the stills live. Drive names it `blocks` for some brands and
    `angles` for others; the repo standardised on `blocks` and the mirror
    never caught up."""
    if not swipe:
        return P.DRIVE
    for lib in ("swipe-paid", "swipe-organic"):
        for folder in ("blocks", "angles", "posts"):
            d = P.DRIVE / lib / swipe / folder
            if d.is_dir():
                return d
    return P.DRIVE / "swipe-paid" / swipe / "blocks"


def placeholders():
    """Every {name} a prompt asks for is supplied by the runner."""
    import run as R
    missing = []
    for stage in R.STAGES:
        pf = R.prompt_for(stage)
        wants = set(re.findall(r"\{([a-z_]+)\}", pf.read_text()))
        # what run_stage would supply, read off the source rather than run
        src = (HERE / "run.py").read_text()
        # The variables moved into `inputs_for` when the dry run arrived (the
        # live path and the dry run share one list); read from whichever
        # comes first so this check follows the code rather than a name.
        start = src.index("def inputs_for") if "def inputs_for" in src else src.index("def run_stage")
        blk = src[start:src.index("def main(")]
        # Some keys are assigned through a conditional expression —
        # v["baseline_injection" if ... else "brand_injection"] — so read
        # every quoted key on a `v[` line, not just the simple form.
        supplied = {m for line in blk.splitlines() if "v[" in line
                    for m in re.findall(r'"([a-z_]+)"', line)} | {"language_bank"}
        gap = wants - supplied
        if gap:
            missing.append((stage, pf.name, sorted(gap)))
    return missing


def briefs_have_drafts():
    """A brief with no draft prompt cannot be reviewed as a picture."""
    import json
    reg_f = LANE / "briefs.json"
    if not reg_f.is_file():
        return []
    reg = json.loads(reg_f.read_text())
    out = []
    for bid, rec in sorted(reg.get("briefs", {}).items()):
        if not rec.get("run"):
            continue
        b = LANE / "runs" / rec["run"] / "out/06-brief.md"
        if b.is_file() and "**The draft prompt**" not in b.read_text():
            out.append(bid)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand"); ap.add_argument("--product")
    ap.add_argument("--avatar"); ap.add_argument("--swipe")
    ap.add_argument("--audit", action="store_true")
    a = ap.parse_args()
    fails = 0

    print("AGNOSTIC — no brand, product or swipe named in what runs")
    bad = audit()
    for rel, n, why in bad:
        print(f"  FAIL  {rel}:{n}  {why}")
    print(f"  {'ok' if not bad else str(len(bad)) + ' to fix'}\n")
    fails += len(bad)

    print("PROMPTS — every {placeholder} is supplied by the runner")
    gaps = placeholders()
    for stage, name, gap in gaps:
        print(f"  FAIL  stage {stage} ({name}) asks for {', '.join(gap)}")
    print(f"  {'ok' if not gaps else str(len(gaps)) + ' to fix'}\n")
    fails += len(gaps)

    print("BRIEFS — every brief carries a draft prompt, not just a plate prompt")
    old = briefs_have_drafts()
    for bid in old:
        print(f"  warn  {bid} has no draft prompt (written before stage 6 emitted one)")
    print(f"  {'ok' if not old else str(len(old)) + ' to re-run'}\n")

    if a.brand:
        print("BASELINE — one cast and one product, named once for this brand")
        bl = LANE / "drafts" / a.brand / "baseline.json"
        if not bl.is_file():
            print(f"  warn  none yet — chain.py baseline --brand {a.brand} ...")
        else:
            import json as _j
            d = _j.loads(bl.read_text())
            c = d.get("cast")
            print(f"  ok    cast      {c['id'] + (' (pinned)' if d.get('cast_pinned') else ' (auto)') if c else 'nobody — this brand has no roster'}")
            pr = d.get("product_ref")
            print(f"  {'ok  ' if pr else 'warn'}  product   "
                  f"{pr['id'] if pr else (d.get('product','?') + ' — no Element found')}")
            slots = sorted((LANE / "drafts" / a.brand / "slots").glob("*.json")) \
                if (LANE / "drafts" / a.brand / "slots").is_dir() else []
            named = [s.name for s in slots
                     if c and c["id"] in s.read_text().lower()]
            print(f"  {'FAIL' if named else 'ok  '}  slot files"
                  f"  {len(slots)} · "
                  + (f"{len(named)} name a person: {', '.join(named)}" if named
                     else "none names a person"))
            if named:
                fails += len(named)
        print()

    if a.brand and not a.audit:
        print(f"INPUTS — {a.brand} / {a.product or '·'} / {a.avatar or '·'} / {a.swipe or '·'}")
        for label, p, ok, kind in inputs(a.brand, a.product, a.avatar, a.swipe):
            mark = "ok  " if ok else ("warn" if kind == "warn" else "FAIL")
            print(f"  {mark}  {label:<17} {p}")
            if not ok and kind != "warn":
                fails += 1
            elif not ok:
                print(f"        (optional — a brand with no roster casts nobody)")
        cov = swipe_coverage(a.swipe)
        if cov:
            have, tot = cov
            mark = "ok  " if have == tot else "warn"
            print(f"  {mark}  {'runnable blocks':<17} {have} of {tot} have a "
                  f"still on Drive")
            if have < tot:
                print(f"        (the rest cannot be torn down — a pick that "
                      f"lands on one is skipped)")
        print()

    print("READY" if not fails else f"{fails} thing{'s' if fails != 1 else ''} to fix")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
