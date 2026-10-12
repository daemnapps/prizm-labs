#!/usr/bin/env python3
"""Map every finished brief onto the section vocabulary the design library speaks.

    python3 sectionise_brief.py --brand brand-b --month 2026-09
    python3 sectionise_brief.py --brand brand-b --month 2026-09 --report SECTIONS.md

The copy side of the machine writes BLOCKS — a headline, a paragraph, a button,
a picture. The design side buys SECTIONS — a hero, a routine, a pricing strip.
Two vocabularies for one email means every handoff is a translation done by
hand, and done differently every time.

This does the translation once, in writing. It walks each run's `design.json`
in order, groups consecutive blocks into sections, and gives each section ONE
name out of a FIXED sixteen. The name is chosen by what the section ARGUES, not
by what block types it holds: a headline over a paragraph over a button is a
hero; the same three blocks carrying a price are pricing.

The sixteen are not extensible here. When nothing fits, the closest name is
used and the section is recorded as low-confidence so a person can look — a
seventeenth name invented in a script is a vocabulary nobody else has.

Writes `sections.json` into each run folder. Reads `design.json`; never writes
it, and never touches anything under results/calendar-* or results/research-*.

Brand-agnostic: the brand is a flag. It resolves which calendar and which run
folders to read, and supplies the one token used to spot the brand's own
furniture (a wordmark line, a nav strip). No brand fact is written down here.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

from paths import HERE

# ---------------------------------------------------------------- vocabulary
# The vocabulary, verbatim, in the order a page is built top to bottom. Never
# add to this list in this file: the design library is the authority on it.
VOCAB = [
    "header", "hero", "symptoms", "mechanism", "product-row", "routine-steps",
    "cards", "b4a", "review", "stat-proof", "comparison", "offer", "pricing",
    "guarantee", "cta", "social", "footer",
]
# NOTE the handoff called this list sixteen names and wrote seventeen. The
# NAMES are what was handed over, so all seventeen stand; the count was the
# typo. Flagged rather than trimmed — dropping one would be inventing the
# vocabulary, which is the one thing this file must not do.

TEXTY = ("text", "label", "alt", "name", "price", "attribution", "subhead")

SOCIAL = re.compile(r"facebook|instagram|tiktok|youtube|twitter|x\.com|"
                    r"linkedin|pinterest|snapchat|threads", re.I)
LEGAL = re.compile(r"unsubscribe|organization\.full_address|no longer want to receive|"
                   r"no longer find value|privacy policy|all rights reserved", re.I)
TM = re.compile(r"[A-Za-z][A-Za-z0-9]*\s?[™®]")
MONEY = re.compile(r"\$\s?\d")
WAS = re.compile(r"\bwas\b\s*\$|\d+\s?% off|compare at|save \$", re.I)
ASK = re.compile(r"\breply\b|hit reply|\btell me\b|let me know|\bone word\b|"
                 r"\bsay it\b|\bwrite back\b", re.I)
BIGNUM = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{3,}\b")
NUMBERED = re.compile(r"(^|\n)\s*(\d[.)]|step (one|two|three|1|2|3))", re.I)
STEPS = re.compile(r"how to use|all you have to do is|step one|step two|first step|"
                   r"second step|\b\d\s?rules\b|three rules|rule \d|"
                   r"morning and night|twice a day|right after the wash", re.I)
BEFORE = re.compile(r"\bbefore\b|\bday 1\b|\bweek 1\b|\bused to\b|back then", re.I)
AFTER = re.compile(r"\bafter\b|\bday 90\b|\bweek 12\b|\bnow\b|\bthen it\b|came back", re.I)
REVIEW = re.compile(r"\bstars?\b|five[- ]star|5 stars|verified|\breviews?\b|"
                    r"\brating\b|their words|★", re.I)
COMPARE = re.compile(r"\bvs\b|\bversus\b|instead of|most products|most guys|"
                     r"other brands|the difference between|one drags|"
                     r"is not new|nothing secret|not the razor|not the product", re.I)
GUARANTEE = re.compile(r"\bguarantee|money back|\brefund|90 days|ninety days|"
                       r"if you (can ?not|cannot|don'?t) see|if your skin does ?n'?t|"
                       r"day 90 and day 1", re.I)
INCLUDED = re.compile(r"\bset\b|\bbundle\b|\bkit\b|\bincludes\b|comes with|"
                      r"\bstack\b|three steps|30-day supply|what you get", re.I)
THROWN_IN = re.compile(r"\bfree\b|thrown in|something extra|riding with|on us|"
                       r"\bincluded\b|\bbonus\b", re.I)
MECHANISM = re.compile(r"how it works|vibrations|reaches|deeper than|barrier|"
                       r"regulates|hydration|shields|ingredients|witch hazel|"
                       r"willow bark|vitamin|salicylic|benzo|at the source|"
                       r"built to|breaks down|per minute|seconds\b|hours\b", re.I)
SYMPTOM = re.compile(r"bumps|ingrown|dark marks|breakouts|razor|came back|"
                     r"still there|stopped working|you dropped|skipped|"
                     r"been here before|tightens|ran out|doing nothing|"
                     r"sat on your shelf|did nothing|failed you|blame the", re.I)


def words(block):
    """Every readable string on a block, in one bag."""
    out = []
    for k in TEXTY:
        v = block.get(k)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    for it in block.get("items") or []:
        if isinstance(it, str) and it.strip():
            out.append(it.strip())
    return out


def lead(blocks):
    """The section's own first words — what it says, before any naming."""
    for b in blocks:
        w = words(b)
        if w:
            return re.sub(r"\s+", " ", w[0]).strip()
    return ""


def furniture(block, token):
    """A brand line, a nav strip — the page's own chrome, not an argument.

    Generic on purpose: the only brand fact is the token handed in by --brand.
    """
    w = " ".join(words(block))
    if not w or len(w) > 90:
        return False
    flat = re.sub(r"[^a-z0-9 ]", " ", w.lower())
    if token and token in flat.split():
        return True
    parts = [p for p in re.split(r"[·|•]", w) if p.strip()]
    return len(parts) >= 2 and all(len(p.strip()) <= 20 for p in parts)


# ------------------------------------------------------------------ grouping
CLOSERS = {"button"}            # a button ends the argument it was asked for
HEADS = {"headline", "subhead"}
PICTURES = {"image", "picture"}


def head_like(b):
    """A short line that opens something, whatever type it was filed as."""
    if b["type"] in HEADS:
        return True
    w = " ".join(words(b))
    return (b["type"] == "copy" and 0 < len(w) <= 50
            and w.upper() == w and w.strip().endswith("."))


def group(blocks, token):
    """Consecutive blocks into runs, on the shape of the argument.

    Three cuts, in this order: the tail furniture comes off first (it is the
    one part of an email whose shape is always the same), then a button closes
    whatever it was the call for, then a new heading opens a new argument —
    but only once the section already has something to open ON.
    """
    n = len(blocks)
    # --- tail: signoff / p.s. / nav / social / legal, taken from the end
    tail = n
    while tail > 0:
        b = blocks[tail - 1]
        w = " ".join(words(b))
        if (b["type"] in ("footer", "signoff", "ps", "divider")
                or LEGAL.search(w) or SOCIAL.search(w)
                or furniture(b, token)
                or (b["type"] in PICTURES and furniture(b, token))):
            tail -= 1
            continue
        break
    body, rest = list(range(tail)), list(range(tail, n))

    runs, cur = [], []
    for i in body:
        b = blocks[i]
        prev = blocks[i - 1] if cur else None
        cut = False
        if cur:
            body_so_far = [blocks[j] for j in cur]
            if prev is not None and prev["type"] == "preheader":
                cut = True                       # the envelope line stands alone
            elif prev is not None and prev["type"] in CLOSERS and b["type"] != "divider":
                cut = True                       # the call was made; next argument
            elif b["type"] in PICTURES:
                cut = True                       # a picture opens a band
            elif b["type"] == "product" and not any(
                    x["type"] == "product" for x in body_so_far):
                cut = True                       # a product opens its own row
            elif head_like(b) and (
                    any(x["type"] in CLOSERS for x in body_so_far)
                    or (any(head_like(x) for x in body_so_far)
                        and any(x["type"] in ("copy", "bullets", "product")
                                for x in body_so_far))):
                cut = True                       # a heading over a finished block
        if cut:
            runs.append(cur)
            cur = []
        cur.append(i)
    if cur:
        runs.append(cur)

    runs = merge_siblings(runs, blocks)

    # --- the tail, split where the social links sit
    if rest:
        soc = [i for i in rest if SOCIAL.search(" ".join(words(blocks[i])))]
        if soc:
            a = [i for i in rest if i < soc[0]]
            c = [i for i in rest if i > soc[-1]]
            for part in (a, soc, c):
                if part:
                    runs.append(part)
        else:
            runs.append(rest)
    return [r for r in runs if r]


def merge_siblings(runs, blocks):
    """Three rules in a row are one section, not three.

    A run of label+copy pairs with no call between them is a single argument
    written in parts — splitting it gives the designer three sections where the
    page has one strip.
    """
    out = []
    for r in runs:
        if out:
            prev = out[-1]
            starts_label = head_like(blocks[r[0]])
            prev_open = not any(blocks[j]["type"] in CLOSERS for j in prev)
            prev_label = head_like(blocks[prev[0]])
            no_pictures = not any(blocks[j]["type"] in PICTURES for j in prev + r)
            if (starts_label and prev_open and prev_label and no_pictures
                    and len(prev) + len(r) <= 12):
                out[-1] = prev + r
                continue
        out.append(r)
    return out


# -------------------------------------------------------------------- naming
def features(blocks, idxs, token):
    f = {}
    bs = [blocks[i] for i in idxs]
    f["types"] = [b["type"] for b in bs]
    f["texts"] = [" ".join(words(b)) for b in bs]
    f["blob"] = " ".join(t for t in f["texts"] if t)
    f["n"] = len(bs)
    f["button"] = sum(1 for b in bs if b["type"] == "button")
    f["product"] = sum(1 for b in bs if b["type"] == "product")
    f["quote"] = sum(1 for b in bs if b["type"] == "quote")
    f["picture"] = sum(1 for b in bs if b["type"] in PICTURES)
    f["heads"] = sum(1 for b in bs if head_like(b))
    f["bullets"] = [b for b in bs if b["type"] == "bullets"]
    f["priced"] = any(MONEY.search(b.get("price") or "") for b in bs)
    f["tiers"] = sum(1 for b in bs if MONEY.search(b.get("price") or ""))
    f["imaged"] = any(b.get("image") or b.get("image_brief") for b in bs)
    f["tm"] = len(set(TM.findall(f["blob"])))
    f["furniture"] = all(furniture(b, token) or b["type"] in ("preheader", "divider")
                         for b in bs)
    f["shorts"] = sum(1 for t in f["texts"] if 0 < len(t) <= 170)
    return f


def name_section(f, pos, state):
    """One name out of the vocabulary, the evidence for it, and how sure it is.

    Priority order is the brief's own, read top down: the first rule that fires
    wins, so a hero that also mentions a price is still a hero.

    `sure` is False only where the call deserves a person: a single soft
    keyword inside a long mixed passage, or nothing matching at all and the
    closest name being used. Those are the rows SECTIONS.md lists.
    """
    b = f["blob"]
    long_mixed = len(b) > 700          # a passage broad enough for one word to mislead

    # --- what the page's shape decides, before any argument is read
    if any(t == "footer" for t in f["types"]) or (LEGAL.search(b) and not f["button"]):
        return "footer", ["legal / unsubscribe"], True
    if len(SOCIAL.findall(b)) >= 2:
        return "social", ["social handles"], True
    if pos == 0 and f["furniture"]:
        return "header", ["brand line / preheader at the very top"], True
    if f["button"] and not any(t not in ("button", "divider") for t in f["types"]):
        return "cta", ["a button alone"], True

    # --- 1. hero: the opening display line, its paragraph, its first button
    if (not state["hero"] and pos <= 3 and f["button"] and f["heads"]
            and not f["priced"]):
        state["hero"] = True
        return "hero", ["opening display line", "its first button"], True

    # --- 2. product-row: a block naming a product with a ™, alongside a picture.
    #     Two or more priced tiers standing together is a price table wearing
    #     product blocks — that argues cost, so it is let through to pricing.
    if f["tiers"] >= 2:
        return "pricing", ["priced tiers side by side", f"{f['tiers']} of them"], True
    if (f["picture"] or f["imaged"]) and (f["product"] or f["tm"]):
        return "product-row", ["a named product", "a picture"], True
    if f["product"] and f["tm"] and f["n"] <= 3:
        return "product-row", ["a product block naming a ™ product"], True

    # --- 3. routine-steps: numbered or sequenced instructions
    if STEPS.search(b) or NUMBERED.search(b):
        s, sure = ["sequenced instructions"], False
        if f["heads"] >= 3:
            s.append("labelled steps in a row")
            sure = True
        if NUMBERED.search(b) and STEPS.search(b):
            s.append("numbered")
            sure = True
        return "routine-steps", s, sure or not long_mixed

    # --- 4. cards: three or more short parallel claims
    if f["heads"] >= 3 and f["shorts"] >= 3:
        return "cards", ["parallel short claims", f"{f['heads']} labels"], True
    for bl in f["bullets"]:
        if len(bl.get("items") or []) >= 3:
            return "cards", ["a list of three or more"], True

    # --- 5. b4a: before/after, a progression
    if BEFORE.search(b) and AFTER.search(b) and re.search(
            r"cleared|came back|then it|used to|day 1|week 1|before and after", b, re.I):
        return "b4a", ["a before and an after", "in one argument"], not long_mixed

    # --- 6. review: a customer quote, stars, verified
    if f["quote"]:
        return "review", ["a quote block"], True
    if REVIEW.search(b):
        s = ["review language"]
        if BIGNUM.search(b):
            s.append("a count of reviews")
            return "review", s, True
        return "review", s, not long_mixed

    # --- 7. stat-proof: a single large number carrying the argument.
    #     A price is a number that argues cost, not proof — it goes to pricing.
    m = None if MONEY.search(b) else BIGNUM.search(b)
    if m and f["n"] <= 5 and len(b) <= 400:
        return "stat-proof", [f"the number {m.group(0)} carries it"], len(b) <= 200

    # --- 8. comparison: vs, instead of, ours against theirs
    if COMPARE.search(b):
        return "comparison", ["ours set against theirs"], not long_mixed

    # --- 9. guarantee: refund, money back, ninety days
    if GUARANTEE.search(b):
        return "guarantee", ["the promise, in writing"], not long_mixed

    # --- 10. pricing: a price, a compare-at, a discount
    if f["priced"] or MONEY.search(b):
        s = ["a price on it"]
        if WAS.search(b):
            s.append("a compare-at")
        return "pricing", s, True
    if WAS.search(b):
        return "pricing", ["a discount, no price shown"], False

    # --- 11. offer: what is in the set, with no price
    if INCLUDED.search(b) and (f["tm"] >= 1 or THROWN_IN.search(b)):
        s = ["what is in the set", "no price"]
        if THROWN_IN.search(b):
            s.append("something thrown in")
        return "offer", s, not long_mixed

    # --- 12. mechanism: how it works, plain numbers
    if MECHANISM.search(b):
        s = ["how it works"]
        if BIGNUM.search(b):
            s.append("plain numbers")
            return "mechanism", s, True
        return "mechanism", s, not long_mixed

    # --- 13. symptoms: what the problem costs him
    if SYMPTOM.search(b):
        return "symptoms", ["the cost of the problem"], not long_mixed

    # --- 14. cta: the ask, when the ask is the whole section. A reply is an
    #     action like any other — these sends ask for one constantly, and a
    #     one-line ask is a call-to-action band, not a paragraph of argument.
    if ASK.search(b) and f["n"] <= 4 and len(b) <= 240:
        return "cta", ["the ask is the whole section", "no other argument in it"], True

    # --- nothing fit. The closest name, and a flag on it for a person.
    if f["button"]:
        return "cta", [], False
    if f["product"] or f["tm"] or f["picture"]:
        return "product-row", [], False
    return "symptoms", [], False


def sectionise(run_dir, token):
    design = json.loads((run_dir / "design.json").read_text())
    blocks = design.get("blocks", [])
    runs = group(blocks, token)
    state = {"hero": False}
    named = []
    for pos, idxs in enumerate(runs):
        f = features(blocks, idxs, token)
        nm, sig, sure = name_section(f, pos, state)
        assert nm in VOCAB, nm
        named.append({"name": nm, "blocks": idxs, "sig": sig, "sure": sure})

    named = fuse(named)

    out, weak = [], []
    for pos, s in enumerate(named):
        says = lead([blocks[i] for i in s["blocks"]])[:60]
        out.append({"name": f"{s['name']}-section", "blocks": s["blocks"], "says": says})
        if not s["sure"]:
            weak.append({"pos": pos, "name": f"{s['name']}-section", "says": says,
                         "why": (f"only {s['sig'][0]}, in a long mixed passage"
                                 if s["sig"] else
                                 "nothing in it matched — closest name used")})
    return out, weak


# A band that a picture cut in half is still one band. These are the names
# where two in a row mean the grouping split one argument, not that the email
# makes the same argument twice. The page-furniture names are NOT here: two
# calls to action in a row really are two buttons the designer must place.
FUSABLE = {"symptoms", "mechanism", "review", "routine-steps", "cards", "b4a",
           "pricing"}


def fuse(named):
    out = []
    for s in named:
        if out and out[-1]["name"] == s["name"] and s["name"] in FUSABLE:
            out[-1]["blocks"] = out[-1]["blocks"] + s["blocks"]
            out[-1]["sig"] = out[-1]["sig"] or s["sig"]
            out[-1]["sure"] = out[-1]["sure"] or s["sure"]
            continue
        out.append(dict(s))
    return out


# --------------------------------------------------------------------- shell
def resolve(brand, month):
    """Which calendar, and which run folders — from the brand, not from a list."""
    res = HERE / "results"
    if (res / f"calendar-{month}-{brand}" / "slots.json").is_file():
        return res / f"calendar-{month}-{brand}", f"{brand}-"
    if (res / f"calendar-{month}" / "slots.json").is_file():
        return res / f"calendar-{month}", ""
    raise SystemExit(f"no calendar for {brand} {month} under {res}")


def runs_for(cal, prefix):
    rows = json.loads((cal / "slots.json").read_text())
    rows = rows if isinstance(rows, list) else rows.get("slots", [])
    out = []
    for s in sorted(rows, key=lambda r: (r["date"], r["id"])):
        for p in sorted((HERE / "results").glob(f"{prefix}{s['id']}*")):
            if not p.is_dir() or not (p / "design.json").is_file():
                continue
            stem = p.name[len(prefix):].split("--")[0]
            if stem != s["id"]:
                continue
            out.append((p, s))
    return out


def cell(s):
    """Copy goes into a table cell, and this copy is full of `{{ a|b }}`."""
    return (s or "—").replace("|", "\\|")


def report(brand, month, rows, freq, flagged, total):
    unused = [v for v in VOCAB if not freq["n"].get(v)]
    L = [f"# Sections — {brand}, {month}", "",
         "One language for two halves of the machine. The copy side writes",
         "BLOCKS — a headline, a paragraph, a button. The design side buys",
         "SECTIONS — a hero, a routine, a pricing strip. This is the map between",
         "them: every finished brief this month, grouped into sections and each",
         "section given ONE name from the fixed vocabulary below.",
         "",
         "A section is named by what it ARGUES, not by which block types it",
         "holds. A headline over a paragraph over a button is a hero; the same",
         "three blocks carrying a price are pricing.",
         "",
         f"Generated by `sectionise_brief.py --brand {brand} --month {month}`.",
         f"{len(rows)} runs, {total} sections. Each run's own map is the",
         "`sections.json` sitting beside its `design.json`; re-run the command to",
         "rebuild both that and this page.", "",
         "## The vocabulary", "",
         f"{len(VOCAB)} names, fixed. A section gets one of these or the closest one",
         "to it — a further name is never invented here, because the design",
         "library is the authority on what a section is called.", ""]
    for v in VOCAB:
        L.append(f"- `{v}-section`")
    L += ["",
          "> One thing to settle with design: the handoff that set this vocabulary",
          f"> called it sixteen names and then listed {len(VOCAB)}. The NAMES are what",
          "> was handed over, so all "
          f"{len(VOCAB)} stand and the count is treated as the typo.",
          "> Dropping one to make the arithmetic work would be inventing the",
          "> vocabulary, which is the one thing this must not do.",
          "", "## How often each name was used", "",
          f"Across {len(rows)} runs and {total} sections.", "",
          "| section | uses | runs |", "| --- | ---: | ---: |"]
    for v in VOCAB:
        n = freq["n"].get(v, 0)
        L.append(f"| `{v}-section` | {n} | {len(freq['runs'].get(v, set()))} |")
    if unused:
        L += ["",
              "Never used this month: "
              + ", ".join(f"`{v}-section`" for v in unused)
              + ". Not a gap in the vocabulary — a fact about the month. "
                "Those arguments were made inside other sections rather than "
                "given a band of their own."]
    L += ["", "## Sections a person should look at", ""]
    if not flagged:
        L.append("None — every section was named on two or more signals.")
    else:
        L += [f"{len(flagged)} sections across "
              f"{len(set(f['run'] for f in flagged))} runs were named on thin "
              "evidence.",
              "Either nothing in the passage matched a rule and the closest name",
              "was used, or one keyword carried the call inside a long mixed",
              "passage. The name written into `sections.json` is the machine's",
              "best guess; these are the ones worth a person's eye.", "",
              "| run | date | section | named | why | says |",
              "| --- | --- | ---: | --- | --- | --- |"]
        for f in flagged:
            L.append(f"| `{f['run']}` | {f['date']} | {f['pos']} | "
                     f"`{f['name']}` | {cell(f['why'])} | {cell(f['says'])} |")
    L += ["", "## What this does not do", "",
          "It does not touch a brief. `design.json` is read and never written,",
          "and nothing under `results/calendar-*` or `results/research-*` is",
          "opened for writing. The only new file in a run folder is",
          "`sections.json`.", "",
          "It knows nothing about any brand. `--brand` resolves which calendar",
          "and which run folders to read, and supplies the one token used to",
          "spot a brand's own furniture — a wordmark line, a nav strip. Every",
          "other brand fact stays in the brand's own folder.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--month", default="2026-09")
    ap.add_argument("--report", default=None,
                    help="also write the summary to this file")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the table, write nothing")
    a = ap.parse_args()

    cal, prefix = resolve(a.brand, a.month)
    token = a.brand.lower()
    rows = runs_for(cal, prefix)
    if not rows:
        raise SystemExit(f"no runs for {a.brand} {a.month}")

    freq = {"n": Counter(), "runs": {}}
    flagged, total = [], 0
    print(f"{'run':<26} {'date':<11} sections")
    print("-" * 100)
    for run_dir, slot in rows:
        secs, weak = sectionise(run_dir, token)
        if not a.dry_run:
            (run_dir / "sections.json").write_text(
                json.dumps(secs, indent=1, ensure_ascii=False) + "\n")
        total += len(secs)
        for s in secs:
            v = s["name"][:-len("-section")]
            freq["n"][v] += 1
            freq["runs"].setdefault(v, set()).add(run_dir.name)
        for w in weak:
            flagged.append({**w, "run": run_dir.name, "date": slot["date"]})
        names = " → ".join(s["name"][:-len("-section")] for s in secs)
        print(f"{run_dir.name:<26} {slot['date']:<11} {names}")

    print("-" * 100)
    print(f"{len(rows)} runs · {total} sections")
    print()
    print(f"{'section':<16} uses  runs")
    for v in VOCAB:
        print(f"{v:<16} {freq['n'].get(v, 0):>4}  {len(freq['runs'].get(v, set())):>4}")
    print()
    if flagged:
        print(f"named on thin evidence ({len(flagged)} sections, "
              f"{len(set(f['run'] for f in flagged))} runs):")
        for f in flagged:
            print(f"  {f['run']:<26} #{f['pos']:<2} {f['name']:<20} "
                  f"{f['says'][:44]!r}")
    else:
        print("every section named on two or more signals.")

    if a.report and not a.dry_run:
        p = Path(a.report)
        p = p if p.is_absolute() else HERE / p
        p.write_text(report(a.brand, a.month, rows, freq, flagged, total))
        print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
