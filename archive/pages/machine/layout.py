#!/usr/bin/env python3
"""Stage 7 — lay the page out on the section library, with a picture brief for
every picture slot. Runs once per page in a finished run (the base, then each
sub-avatar page). Brand-agnostic: the library is the machine's kit, the words
are the run's, the identity and photographs are the brand's.

    python3 layout.py scrub-base-01            # every page in the run
    python3 layout.py scrub-base-01 --only base
    python3 layout.py scrub-base-01 --only texture-seeker

Writes runs/<label>/stage7[-<sub>]--layout.md (the prompt as sent beside it)
and, parsed, runs/<label>/layout[-<sub>].json for the pictures and build steps.
"""
import argparse, json, re, sys, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "machine"))
import run as RUN                                                                       # noqa: E402
from run import claude, latest_prompt, fill, sha, WORKSPACE, MODELS, SPEC, STAGES, say, model_for, UsageLimit   # noqa: E402
import page_paths as P                                                                  # noqa: E402

KIT = HERE / "kit"


def section_bank():
    d = json.loads((KIT / "_includes" / "landing" / "_blocks.json").read_text())
    lines = []
    for b in d["blocks"]:
        imgs = [v for v in b["variables"] if re.search(r"image|photo|poster|logo|icon|thumb", v)]
        lines.append(f"- **{b['id']}** ({b['family']}) — {b['what']}\n  slots: {', '.join(b['variables'])}\n  picture slots: {', '.join(imgs) or 'none'}")
    return "\n".join(lines)


def references(brand, product_dir):
    imgs = sorted((WORKSPACE / product_dir / "images").glob("*"))
    lines = [f"- `{p.relative_to(WORKSPACE)}`" for p in imgs if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    ident = P.identity_dir(brand)                      # brand-identity/, old identity/
    lines += [f"- `{p.relative_to(WORKSPACE)}` (identity mark)" for p in sorted(ident.glob("*")) if p.suffix.lower() in (".png", ".svg")]
    return "\n".join(lines) or "(none on file)"


def identity(brand):
    ident = P.identity_dir(brand)                      # brand-identity/, old identity/
    out = []
    for name in ("web-tokens.md", "palette.md", "README.md"):
        p = ident / name
        if p.exists():
            out.append(f"--- {p.relative_to(WORKSPACE)} ---\n\n{p.read_text().strip()}")
    return "\n\n".join(out) or "(no identity on file)"


def page_words(brand, funnel, fmt, page_name):
    p = WORKSPACE / "brands" / brand / "funnels" / funnel / fmt / f"{page_name}.md"
    txt = p.read_text()
    fm, body = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S).groups()
    m = re.search(r"^## (The offer it hands to|What to watch|Before you build it)", body, re.M)
    words = body[: m.start()].strip() if m else body.strip()
    notes = body[m.start():].strip() if m else "(no notes)"
    return fm, words, notes


def parse_json(text):
    m = re.search(r"```json\s*(.*?)```", text, re.S)
    return json.loads(m.group(1) if m else text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label"); ap.add_argument("--only", default=None)
    ap.add_argument("--product-dir", default=None, help="workspace-relative product folder holding images/ (default: derived from the run's product file)")
    ap.add_argument("--model", default=None, help="force a model (default: the layout stage's tier)")
    a = ap.parse_args()
    RUN.FORCED_MODEL = a.model
    run = P.need_run(a.label)            # either home: runs/page-machine/<brand>/, then the old runs/
    state = json.loads((run / "run.json").read_text())
    brand, funnel, fmt, base = state["brand"], state["funnel"], state["format"], state["page_name"]
    product_file = state.get("product")
    if not product_file:
        sys.exit("the run state carries no product file — rerun run.py --resume once so it is recorded")
    product_dir = a.product_dir or state.get("product_dir")
    if not product_dir:
        sys.exit("say where the product's photographs are: --product-dir brands/<brand>/products/<product>")
    state["product_dir"] = product_dir
    today = datetime.date.today().isoformat()
    pages = [("base", base)] + [(s, f"{base}-{re.sub(r'[^a-z0-9]', '', s)}") for s in state.get("subs", [])]
    if a.only:
        pages = [p for p in pages if p[0] == a.only]
    prompt_file = latest_prompt("stage7")
    base_layout = run / "layout.json"
    base_pics = "(none yet)"
    if base_layout.exists():
        bl = json.loads(base_layout.read_text())
        made = json.loads((run / "pictures.json").read_text()) if (run / "pictures.json").exists() else {}
        rows = []
        for sec in bl["sections"]:
            for pic in sec.get("pictures", []):
                if pic.get("aspect") in (None, "none") or pic.get("reuse"): continue
                what = "the brand's own photograph: " + pic["use"] if pic.get("use") else (pic.get("brief") or "")[:260]
                rows.append(f"- `{pic['id']}` ({sec['block']} · {pic['field']} · {pic.get('aspect')}) — {what}")
        base_pics = "\n".join(rows) or base_pics
    for key, page_name in pages:
        fm, words, notes = page_words(brand, funnel, fmt, page_name)
        fields = dict(today=today, body=words, brief_notes=notes, section_bank=section_bank(),
                      references=references(brand, product_dir), identity=identity(brand),
                      product_file=(WORKSPACE / product_file).read_text(),
                      avatar=(WORKSPACE / "brands" / brand / "core-avatars" / state["avatar"] / "profile.md").read_text(),
                      page_name=page_name, page_format=fmt, page_next=state["next"],
                      base_pictures=base_pics)
        if key != "base":
            fields["body"] = words + "\n\n(This is a sub-avatar variation of the base page. Its base layout and pictures are already made.)"
        else:
            fields["body"] = words + "\n\n(This page's pictures are already made and listed above; reuse them by exact id wherever they fit, and brief a new one only for a slot none of them serves.)"
        filled, left = fill(prompt_file.read_text(), fields)
        if left: sys.exit(f"unfilled: {left}")
        name = "stage7" if key == "base" else f"stage7-{key}"
        (run / f"{name}--sent.md").write_text(filled)
        model, _why = model_for("stage7", len(filled))
        say(f"  -> {name}  ({prompt_file.name} · {model} · {len(filled):,} chars in)")
        import time; t0 = time.time()
        try:
            out = claude(filled, model)
        except UsageLimit as e:
            sys.exit(f"STOPPED — {e}\n  nothing is lost: pages already laid out are kept; run this again once usage is back")
        (run / f"{name}--layout.md").write_text(out + "\n")
        try:
            plan = parse_json(out)
            (run / f"layout{'' if key == 'base' else '-' + key}.json").write_text(json.dumps(plan, indent=1))
            npics = sum(len(s.get("pictures", [])) for s in plan["sections"])
            say(f"     done in {round(time.time()-t0)}s · {len(plan['sections'])} sections · {npics} pictures")
        except Exception as e:
            say(f"     !! could not parse the layout JSON: {e}")
        state["stages"][name] = dict(status="done", seconds=round(time.time() - t0, 1), model=model,
                                     chars_in=len(filled), chars_out=len(out), prompt_name=prompt_file.name,
                                     prompt_sha256_12=sha(prompt_file), out=f"{name}--layout.md", sent=f"{name}--sent.md")
        (run / "run.json").write_text(json.dumps(state, indent=1))


if __name__ == "__main__":
    main()
