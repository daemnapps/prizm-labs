#!/usr/bin/env python3
"""DESIGN — the step between the copy and the designer (the owner, 2026-09-09:
Calendar → Copy → Design from the bank, generating the pictures it needs →
Figma for the designer's tweaks → Klaviyo).

    python3 design_email.py results/<slot> [--brand <brand>] [--generate]

The chain writes the email as BLOCKS. Where the source email was all
pictures, the chain mirrors it: the copy sits inside image briefs
("typography card", "story card", "the close"). An email built from the
bank does not do that — copy is live text, buttons are buttons, pictures
are pictures. So this step:

  1 reads the chain's BLOCKS (stage8--blocks.md)
  2 turns every typographic picture into what it is: a headline, body copy,
    a button (the bracketed phrase) — the bedrock draws them live
  3 drops the header/footer strips the chain carried over (the bedrock's
    modules provide them)
  4 keeps real pictures: a named product gets the store photo
    (products/images.json); a scene gets a generation brief (fal_generate.py
    on --generate; until then the slot shows its brief)
  5 lifts every [UNFILLED: …] out of the copy into handoff.json as an open
    fact — the copywriter or designer closes it; nothing is invented
  6 picks the nearest format in the brand's bank by block signature and
    records it
  7 renders on the brand's bedrock (render_email.py) → email-final.html,
    and writes handoff.json: slot, format, every block with its copy, every
    picture with its source, the open facts, the segments and the date

Nothing here writes copy. It only moves what the chain wrote into the
right kind of block.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from paths import HERE, WORKSPACE

sys.path.insert(0, str(HERE / "machine"))
import brand_facts as BF             # brand words and a run's own brand, read at run time   # noqa: E402

TYPO_WORDS = ("typography card", "headline card", "story card", "the close", "bracketed phrase", "running prose",
              "set as prose", "text card", "no photo", "no product", "nothing else in the frame", "copy card",
              "quote card", "the line ", "as the largest thing")
FURNITURE_WORDS = ("wordmark", "logo/header", "identity bar", "footer brand strip", "brand strip", "footer strip",
                   "header bar", "inbox-tab", "social icon", "unsubscribe", "on facebook", "on instagram", "on tiktok",
                   "on youtube", "category tile", "category strip", "nav tile", "footer nav", "footer link", "shop-by")
# Which ALT TEXTS are furniture is the brand's own vocabulary — its name, its
# nav words, "<brand> on <platform>" — read at run time from
# brands/<brand>/email-sms/simple.json ("furniture"), never typed here (2026-09-20).
PRODUCT_WORDS = ("packshot", "product shot", "bottle", "the set", "cut-out", "cutout", "product on")


def blocks_of(run_dir):
    t = (run_dir / "stage8--blocks.md").read_text()
    m = re.search(r"```BLOCKS\s*(\[.*?\])\s*```", t, re.S)
    if not m:
        sys.exit("stage 8 wrote no BLOCKS fence")
    return json.loads(m.group(1))


def lift_unfilled(text, opens):
    """[UNFILLED: what Bernard expected] → removed from the copy, kept as an open fact."""
    def take(m):
        opens.append(m.group(1).strip())
        return ""
    # The chain writes its holes several ways — "[UNFILLED: x]", "[UNFILLED — x]",
    # "[UNFILLED-CONDITIONAL: x]". Only the first was ever lifted, so the others
    # shipped into the email body as a note to nobody.
    out = re.sub(r"\[UNFILLED[^\]:—-]*[:—-]\s*([^\]]*)\]", take, text or "")
    return re.sub(r"\s{2,}", " ", out).strip()


def split_bracket(text):
    """'The same neck for decades. [SEE BERNARD'S STORY]' → copy, button label."""
    labels = re.findall(r"\[([A-Z][A-Z0-9' ,.&!?-]{2,60})\]", text or "")
    copy = re.sub(r"\[[A-Z][A-Z0-9' ,.&!?-]{2,60}\]", "", text or "").strip()
    return copy, (labels[-1].strip() if labels else None)


def product_photo(brand, text):
    f = WORKSPACE / "brands" / brand / "products" / "images.json"
    if not f.is_file():
        return None, None
    prods = json.loads(f.read_text()).get("products", {})
    low = (text or "").lower()
    for slug, p in prods.items():
        names = [slug.replace("-", " "), (p.get("title") or "").lower()]
        if any(n and n in low for n in names):
            src = p.get("hero") or (p.get("all") or [None])[0]
            if src:
                url = src if src.startswith("http") else f"/brands/{brand}/{src}"
                return url, p.get("title") or slug
    return None, None


def format_signature(blocks):
    return "".join({"headline": "H", "subhead": "h", "copy": "T", "image": "I", "product": "P", "button": "B",
                    "quote": "Q", "bullets": "L", "divider": "-", "signoff": "s"}.get(b.get("type"), "") for b in blocks)


def nearest_format(brand, sig):
    """The rebuilt email in the brand's bank whose block signature is closest."""
    # a brand's bank is the folder that carries its name, or the brand's own
    # design-formats bank; the unsuffixed legacy folder counts only when its
    # own run.json says it is this brand's
    roots = [HERE / "results" / f"format-bank-{brand}",
             WORKSPACE / "brands" / brand / "email-sms" / "design-formats" / "format-bank" / "boards"]
    legacy = HERE / "results" / "format-bank"
    try:
        if json.loads((legacy / "run.json").read_text()).get("brand") == brand:
            roots.append(legacy)
    except (OSError, ValueError):
        pass
    best = None
    for spec in (s for root in roots for s in root.glob("*/[0-9][0-9]-spec.json")):
        try:
            sp = json.loads(spec.read_text())
        except ValueError:
            continue
        s2 = "".join({"text": "T", "image": "I", "cta": "B", "glass": "G", "panel": "G", "tile": "G", "row": "R"}.get(b.get("block"), "")
                     for sec in sp.get("sections", []) for b in sec.get("blocks", []))
        s2 = s2.replace("TT", "T")
        # a cheap distance: shared kind counts
        score = sum(min(sig.count(k), s2.count(k)) for k in "HTIBPG") - abs(len(sig) - len(s2)) * 0.2
        if best is None or score > best[0]:
            best = (score, spec.parent.name, spec.stem.replace("-spec", ""), s2)
    return {"board": best[1], "email": best[2], "signature": best[3]} if best else None


def design(run_dir, brand, generate=False):
    run = json.loads((run_dir / "run.json").read_text())
    raw = blocks_of(run_dir)
    furniture = BF.vocab(brand)
    out, opens, pictures, dropped = [], [], [], []
    for b in raw:
        t = b.get("type")
        if t == "image":
            brief = (b.get("image_brief") or "").lower()
            alt = b.get("alt") or ""
            if any(w in brief for w in FURNITURE_WORDS) or BF.is_furniture_alt(alt, furniture):
                dropped.append({"why": "furniture the bedrock provides", "alt": alt[:80]})
                continue
            typographic = any(w in brief for w in TYPO_WORDS) or (len(alt) > 40 and not any(w in brief for w in PRODUCT_WORDS)
                                                                and ("photo" not in brief and "photograph" not in brief))
            if typographic:
                copy, label = split_bracket(lift_unfilled(alt, opens))
                if copy:
                    kind = "headline" if (len(copy) <= 90 and copy.count(". ") <= 1) else "copy"
                    out.append({"type": kind, "text": copy, "from": "typographic picture"})
                if label:
                    nice = re.sub(r"(\w)'S\b", r"\1's", label.title()) if label.isupper() else label
                    out.append({"type": "button", "label": nice, "href": b.get("href") or "#"})
                continue
            url, title = product_photo(brand, brief + " " + alt)
            if url:
                out.append({"type": "product", "image": url, "alt": title, "href": b.get("href") or "#", "image_brief": b.get("image_brief")})
                pictures.append({"kind": "product photo", "source": url, "alt": title})
            else:
                out.append({"type": "image", "image_brief": b.get("image_brief"), "alt": lift_unfilled(alt, opens), "href": b.get("href") or "#",
                            "generate": True})
                pictures.append({"kind": "to generate", "brief": b.get("image_brief"), "alt": alt[:120]})
            continue
        if t in ("headline", "subhead", "copy", "quote", "preheader", "signoff", "ps"):
            b = dict(b); b["text"] = lift_unfilled(b.get("text"), opens)
        if t == "button":
            b = dict(b); b["label"] = lift_unfilled(b.get("label"), opens)
        out.append(b)
    sig = format_signature(out)
    fmt = nearest_format(brand, sig)
    (run_dir / "design.json").write_text(json.dumps({"blocks": out, "signature": sig, "format": fmt,
                                                     "dropped": dropped, "open_facts": opens, "pictures": pictures}, indent=1) + "\n")
    (run_dir / "stage8--blocks.design.md").write_text("# THE EMAIL, DESIGNED — the chain's blocks moved into live blocks\n\n```BLOCKS\n"
                                                        + json.dumps(out, indent=1) + "\n```\n")
    if generate and any(p["kind"] == "to generate" for p in pictures):
        subprocess.run([sys.executable, "fal_generate.py", str(run_dir), "--brand", brand], cwd=HERE)
    import render_email
    try:                      # the HTML render is a record, not the deliverable (the owner, 2026-09-09: drafts are built in Figma)
        render_email.build(run_dir, brand, blocks_file=run_dir / "stage8--blocks.design.md")
    except Exception as ex:   # noqa: BLE001
        print(f"note: HTML render skipped for {run_dir.name}: {type(ex).__name__}: {str(ex)[:160]}")
    subj = ""
    sf = run_dir / "stage5--subjects.md"
    if sf.is_file():
        m = re.search(r"\*\*Subject:\*\*\s*(.+)", sf.read_text())
        subj = m.group(1).strip() if m else ""
    handoff = {"slot": run.get("label"), "brand": brand, "subject": subj, "format": fmt, "signature": sig,
               "blocks": out, "pictures": pictures, "open_facts": opens, "dropped": dropped,
               "email_html": str(run_dir / "email-final.html"), "note": "The designer tweaks; nothing here is final art. Open facts must be closed by a person before send."}
    (run_dir / "handoff.json").write_text(json.dumps(handoff, indent=1) + "\n")
    print(f"{run_dir.name}: {len(out)} live blocks · format {fmt['board'] + '/' + fmt['email'] if fmt else '—'} · "
          f"{sum(1 for p in pictures if p['kind'] == 'product photo')} product photos · {sum(1 for p in pictures if p['kind'] == 'to generate')} to generate · "
          f"{len(opens)} open facts · {len(dropped)} furniture dropped")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--brand", default=None)
    ap.add_argument("--generate", action="store_true", help="generate the pictures the design calls for (FAL)")
    a = ap.parse_args()
    rd = Path(a.run_dir)
    if not rd.is_absolute():
        rd = HERE / rd
    brand = BF.run_brand(rd, a.brand)
    design(rd, brand, generate=a.generate)


if __name__ == "__main__":
    main()
