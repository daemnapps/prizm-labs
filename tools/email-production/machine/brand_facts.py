"""What this tool needs to know about a brand, read from the brand's own files
at run time — so no brand's name, products or page furniture is typed into
the code (rollout, 2026-09-20).

    import brand_facts as BF
    BF.run_brand(run_dir)            # the brand a run was made for, or an error naming run.json
    BF.runs_of(brand, results_dir)   # that brand's runs only — by each run's own run.json
    BF.furniture(brand)              # the brand's page-furniture words (email-sms/simple.json)
    BF.vocab(brand)                  # furniture alt texts + furniture lines, brand words included
    BF.product_names(brand)          # what the brand sells, by name (products/store.json + files)
    BF.machine(brand)                # brands/<brand>/email-sms/machine.json

WHY. The old-email source problem (seen live, 2026-09-20): the writer copied a
source email's nav and footer words into the new email's body. The words that
are furniture differ per brand, so they live with the brand:
`brands/<brand>/email-sms/simple.json` → `"furniture": [...]`.
"""
import json
import re
import sys
from pathlib import Path

if "paths" not in sys.modules:             # a caller may have taken this folder OFF the path on purpose
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # (its email.py shadows Python's `email`)
from paths import WORKSPACE                                   # noqa: E402

# Furniture every brand's email carries — no brand's words here.
GENERIC_ALTS = {"shop", "facebook", "instagram", "tiktok", "youtube"}
PLATFORMS = ("facebook", "instagram", "tiktok", "youtube")


def _root(brand, workspace=None):
    return Path(workspace or WORKSPACE) / "brands" / brand


def _json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def run_brand(run_dir, given=None):
    """The brand a run belongs to. `--brand` wins; otherwise the run's own
    run.json must say. There is no default brand — a run.json without one is
    an error that names the file."""
    if given:
        return given
    f = Path(run_dir) / "run.json"
    brand = _json(f, {}).get("brand")
    if not brand:
        sys.exit(f"no brand: {f} does not name one — pass --brand, there is no default brand")
    return brand


def runs_of(brand, results_dir, month_abbr=None, need="design.json"):
    """This brand's run folders under `results_dir` — decided by each run's own
    run.json, never by a folder-name prefix (a prefix rule silently drops a
    brand). A run whose run.json names no brand is skipped, and said so."""
    out = []
    for p in sorted(Path(results_dir).glob("*")):
        if not p.is_dir() or (need and not (p / need).is_file()):
            continue
        b = _json(p / "run.json", {}).get("brand")
        if not b:
            print(f"  skipped {p.name}: its run.json names no brand", file=sys.stderr)
            continue
        if b != brand:
            continue
        bare = p.name[len(brand) + 1:] if p.name.startswith(brand + "-") else p.name
        if month_abbr and not bare.startswith(month_abbr + "-"):
            continue
        out.append(p)
    return out


def month_abbr(month):
    """'2026-09' → 'sep' — how a month's runs are named."""
    names = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
    return names[int(str(month).split("-")[1]) - 1]


def look(brand, workspace=None):
    return _json(_root(brand, workspace) / "email-sms" / "simple.json", {})


def machine(brand, workspace=None):
    f = _root(brand, workspace) / "email-sms" / "machine.json"
    d = _json(f, None)
    if d is None:
        sys.exit(f"no {f} — this brand's plumbing facts are not on file")
    return d


def furniture(brand, workspace=None):
    """The brand's own furniture words, lowercased. Optional: a brand with none
    on file has none."""
    return [str(w).strip().lower() for w in (look(brand, workspace).get("furniture") or []) if str(w).strip()]


def vocab(brand, workspace=None):
    """{"alts": exact alt texts that are furniture, "lines": text that marks a
    furniture line, "signers": first names a '- Name' sign-off line opens with}."""
    lk = look(brand, workspace)
    names = {brand.lower()}
    alt = ((lk.get("logo") or {}).get("alt") or "").strip().lower()
    if alt:
        names.add(alt)
    alts = set(GENERIC_ALTS) | names | set(furniture(brand, workspace))
    alts |= {f"{n} on {p}" for n in names for p in PLATFORMS}
    lines = []
    for seg in re.split(r"[.—–|·]", lk.get("tagline") or ""):
        seg = re.sub(r"[™®]", "", seg).strip().lower()
        if len(seg.split()) >= 2:
            lines.append(seg)
    signers = []
    for s in lk.get("signoff") or []:
        s = re.sub(r"[™®]", "", str(s)).strip()
        if s:
            lines.append(s.lower().rstrip(","))
            if not s.endswith(","):
                signers.append(s.split()[0].lower())
    return {"alts": alts, "lines": lines, "names": names, "signers": signers}


def is_furniture_alt(alt, v):
    return (alt or "").strip().lower() in v["alts"]


def is_furniture_line(text, v):
    s = re.sub(r"[™®]", "", (text or "")).strip().lower()
    bare = re.sub(r"\W+$", "", s)
    if bare in v["names"]:
        return True
    if any(seg and seg in s for seg in v["lines"]):
        return True
    m = re.match(r"^[-–—]\s*(\w+)", s)
    return bool(m and m.group(1) in v["signers"])


def product_names(brand, workspace=None):
    """What the brand sells, by name: store.json titles and handles, plus the
    product files' own names. Longest first, so a set matches before its part."""
    root = _root(brand, workspace) / "products"
    names = set()
    for p in _json(root / "store.json", {}).get("products", []):
        for k in ("title", "handle"):
            v = (p.get(k) or "").strip()
            if v:
                names.add(v.lower())
                names.add(v.lower().replace("-", " "))
    if root.is_dir():
        for f in root.iterdir():
            if f.suffix == ".md" and f.stem.lower() not in ("readme",):
                names.add(f.stem.lower().replace("-", " "))
            elif f.is_dir() and (f / "product.md").is_file():
                names.add(f.name.lower().replace("-", " "))
    clean = {re.sub(r"[™®]", "", n).strip() for n in names}
    return sorted({n for n in names | clean if n}, key=len, reverse=True)


def product_only(brand, workspace=None):
    """A picture direction that is just a named product on its own."""
    names = product_names(brand, workspace)
    if not names:
        return re.compile(r"(?!x)x")                          # matches nothing
    alt = "|".join(re.escape(n) for n in names)
    return re.compile(rf"^(image of |the |a )?({alt})[\s\w™'.,-]*$", re.I)


# WHAT MAY BE SOLD, AND WHAT IS A DRAFT (the owner, 2026-09-21).
# A brand's files describe products that are not live — Brand B' own asset-bed
# names FADE, MEND and BEAST as "drafts nobody had mentioned" — and an email
# went out of the writer talking about one. The live list is a brand file, read
# at run time, never a list in code.
def catalogue(brand, workspace=None):
    """{heroes, hero_rule, sellable, never} from brands/<brand>/products/heroes.json.
    Missing file = an empty catalogue, and the caller says so rather than guessing."""
    d = _json(_root(brand, workspace) / "products" / "heroes.json", {})
    return {"heroes": d.get("heroes", []), "hero_rule": d.get("hero_rule", ""),
            "sellable": d.get("sellable", []),
            "never": (d.get("never") or {}).get("handles", []),
            "why_never": (d.get("never") or {}).get("why", "")}


def catalogue_block(brand, workspace=None):
    """The catalogue as the writer is handed it — a labelled block, not prose."""
    c = catalogue(brand, workspace)
    if not c["sellable"]:
        return ("(no product catalogue on file for this brand — "
                f"brands/{brand}/products/heroes.json is missing, so nothing may be linked)")
    heroes = {h: None for h in c["heroes"]}
    lines = ["THE THREE THAT CARRY THE WEIGHT — an email with nothing more specific to "
             "point at ends on one of these:"]
    for h in c["heroes"]:
        row = next((s for s in c["sellable"] if s["handle"] == h), None)
        lines.append(f"  - {row['title'] if row else h} — {row['url'] if row else '(not live)'}")
    lines += ["", "EVERYTHING ELSE THAT IS LIVE — link one of these when the email is about it:"]
    lines += [f"  - {s['title']} — {s['url']}" for s in c["sellable"] if s["handle"] not in heroes]
    # A brand may route one product to more than one page by audience
    # (`url_leads`, `url_subscription` …) and say how in `hero_rule`; the writer
    # has to be handed both, or it links the default page to everyone.
    alt = [f"  - {s['title']} · {k[4:].replace('_', ' ')} — {v}"
           for s in c["sellable"] for k, v in s.items() if k.startswith("url_") and v]
    if c["hero_rule"] or alt:
        lines += ["", "WHICH PAGE — the brand's own rule:"]
        lines += [f"  {c['hero_rule']}"] if c["hero_rule"] else []
        lines += alt
    lines += ["", "WHAT MAY BE SAID ABOUT ANY OF THEM. A number, a material, a speed, a "
              "depth, an ingredient or a certification appears only if that product's own "
              "file says it, in the words the file uses. If the file does not carry the "
              "figure, the sentence is written without one — \"deeper than your hands "
              "reach\" is true and \"0.3 to 0.4mm, four times deeper\" is invented. A "
              "specific that cannot be pointed at in a file is the fastest way to make an "
              "honest email a false one.",
              "", "A GUARANTEE IS A REFUND PROMISE, NEVER A RESULTS CLAIM, and never an "
              "efficacy timeframe. Its length is how long a reader has to ask for their "
              "money back — it is not how long the product takes to work, and it is never "
              "written as one length chosen over another (\"ninety days instead of "
              "thirty\") because that turns a refund window into a claim about results.",
              "", "NEVER A PROPORTION OF PEOPLE NOBODY COUNTED. \"Most men never finish "
              "the first set\", \"almost nobody quit because it didn't work\", \"nine out "
              "of ten\" — a share of customers is a measurement, and unless a file carries "
              "that number it was invented. Write the one reader instead: what HE did is "
              "the avatar's own material and is on file; what most men do is not.",
              "", "NEVER A NUMBER YOU WORKED OUT. \"You decided it 78 days early\", \"that "
              "is six weeks of\", a date, a count of days, a price difference — arithmetic "
              "invents a fact as surely as a made-up spec does, because the figures it "
              "starts from are not on file either. Say the thing without the sum.",
              "", "A SET IS WHAT ITS OWN FILE SAYS IT IS, and nothing else is inside it. "
              "Do not put a product into a set because it would help the argument; if the "
              "email wants to talk about another product, it talks about it as another "
              "product.",
              "", "SPELLING IS AMERICAN. moisturize, millimeter, color, fiber."]
    if c["never"]:
        lines += ["", "NEVER WRITTEN ABOUT AND NEVER LINKED — these are drafts, not products. "
                  "Naming one is a defect, whatever the brand's other files say about it:",
                  "  " + " · ".join(c["never"]).upper()]
    return "\n".join(lines)


# THE FACTS OF EVERY LIVE PRODUCT, not just the one a send names (2026-09-21).
# Once every email had to end on a product, emails began talking about products
# their slot never named — WIDGET, GADGET — and the check, handed one product file,
# called every one of those statements unsupported. The catalogue decides what
# is read, so a draft's file is never opened.
#
# ONE READ FOR EVERY CHECKER (HE-3 (shared brand facts), 2026-10-02). The text
# is now marketing-chain-checks' `brand_facts`, so the writer's own check and
# qc-checks read the same thing; this keeps its API. A fact a person ruled true
# (HE-1 (fact rulings)) is handed on in one labelled section, so stage 8c does
# not flag it again. Never a price: those stay offer-bank-only, and
# `rulings.verified_facts` drops any ruling whose fact carries one.
VERIFIED_TITLE = ("Ruled true by a person since the files were written — "
                  "a fact here is supported, though no file says it yet")


def _shared_facts(brand, workspace=None):
    if "marketing_chain_checks.facts" not in sys.modules:
        # FOUND, never counted — and not through `paths`, which a caller may
        # have loaded from another machine before this file.
        home = next(str(d / "components" / "quality-checks") for d in Path(__file__).resolve().parents
                    if (d / "components" / "quality-checks").is_dir())
        if home not in sys.path:
            sys.path.append(home)                # appended, never ahead of this machine
    from marketing_chain_checks.facts import brand_facts
    return brand_facts(brand, root=workspace or WORKSPACE)


def catalogue_facts(brand, workspace=None, limit=None):
    f = _shared_facts(brand, workspace)
    text = f["product_facts"]
    verified = [v["fact"].strip() for v in f["verified_facts"] if (v.get("fact") or "").strip()]
    if verified:
        text += f"\n\n----- {VERIFIED_TITLE} -----\n" + "\n".join(f"- {v}" for v in verified)
    return text if not limit else text[:limit]
