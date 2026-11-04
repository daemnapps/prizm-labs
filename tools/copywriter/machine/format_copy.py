#!/usr/bin/env python3
"""format_copy — the words beside one ad, written by filling our own winning formats.

    format_copy.py --brand brand-a --brief brief-0232 [--product flex] [--dry-run]

the owner, 2026-10-27: "we keep writing brand new ad copy over and over and over again per ad ... it's not in a proven
format ... we're just freeballing it based off of the brief." So the primary text, the headlines and the descriptions
are each one of the brand's own formats (`real_formats.py`: real ads that sold, stripped to [BLANKS]) with the blanks
filled for this ad from the product file, the market's words at the ad's awareness level and the spice
(`prompts/copy-format-fill-vN-owner.md`). Nothing is written from scratch.

Checked without a model, then sent back once with what broke: every line is a format it was handed, keeps that
format's shape (its paragraphs one for one, most of its own words in order — elements may change), leaves no [BLANK], carries no price or deal off a promotion,
no price that is not in the offer bank, no row it was not given, headlines ≤ 40 and descriptions ≤ 30 characters.
A line that still breaks is dropped and named in `run.json`.

Writes a copywriter run the approval card already reads (components/meta-upload/card_words.py):
`runs/copywriter/<brand>/<label>/` — `stage8--render.md` and `final--copy.md` (each body under the format it filled,
named with the real ad it came from), `run.json` (`read_check`, the formats used), the prompt as sent and the answer.
`brief_words.write` routes here whenever the brand has a format bank.
"""
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
COPY = HERE.parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
sys.path.append(str(HERE))
sys.path.append(str(WS / "components/quality-checks"))
import real_formats as RF  # noqa: E402

COUNTS = {"primary": 3, "headlines": 2, "descriptions": 2}
SHORTLIST = {"primary": 12, "headlines": 10, "descriptions": 8}
LIMIT = {"headlines": 40, "descriptions": 30}
TOOL = "format_copy"
CHECK_MODEL = "claude-sonnet-5-5"         # the story check applies written rules: the checks tier


def shortlists(brand, awareness, promo, ws=WS, moment=None):
    return {s: RF.pick(brand, s, awareness=awareness, promo=promo, n=SHORTLIST[s], ws=ws, moment=moment) for s in RF.SLOTS}


def formats_text(rows):
    if not rows:
        return "(none in the bank for this ad)"
    out = []
    for e in rows:
        n = e["numbers"]
        out.append(f"- {e['id']} — from our ad \"{e['name']}\": ${n['spend']:,.0f} spend, {n['purchases']} purchases, "
                   f"CPA ${n['cpa'] or 0:,.2f}, {e['awareness'] or 'level not read'}.\n  How it's built: {e['structure']}\n"
                   "  FORMAT:\n" + "\n".join("    " + l for l in e["format"].splitlines()))
    return "\n".join(out)


def ad_text(src):
    """The ad the words sit beside: for a picture run its brief (out/06-brief.md) over the swipe's read."""
    src = Path(src)
    brief = src.parent / "06-brief.md"
    if src.name == "01-teardown.md" and brief.is_file():
        src = brief
    t = src.read_text()
    return t if len(t) < 20000 else t[:20000] + "\n…"


def market_state(src):
    """The ad's awareness level as a picture teardown record reads it (its MARKET STATE section): the first level
    named there, or None. The same reading as image-teardown's run.awareness_of, from the record file itself."""
    f = Path(src)
    t = f.read_text().lower() if f.is_file() and f.name == "01-teardown.md" else ""
    at = t.find("market state")
    if at < 0:
        return None
    t = t[at:]
    hits = [(t.find(a), a) for a in ("most-aware", "product-aware", "solution-aware", "problem-aware", "unaware") if a in t]
    return min(hits)[1] if hits else None


def picture_words(src):
    f = Path(src).parent / "approved-words.md"
    if f.is_file():
        got = [l.split("`")[1] for l in f.read_text().splitlines() if l.count("`") >= 2]
        if got:
            return "\n".join(got)
    return "(not given)"


def product_text_of(brand, product):
    """The product file's words, for a fact check ("" when it cannot be read)."""
    try:
        import copy_set as CS
        return CS.product_text(brand, product) or ""
    except Exception:                                      # noqa: BLE001  a missing file never blocks the check
        return ""


def check(got, lists, *, promo, awareness, brand, product, cited, offer_lines=None):
    """{slot: [(item, [problems])]} for the answer."""
    import copy_set as CS
    import quality_checks as Q
    ids = {s: {e["id"]: e for e in lists[s]} for s in RF.SLOTS}
    _, bank = CS.offer_text(brand, product)
    live = " ".join("$" + f"{float(p):.2f}" for p in sorted(Q.prices_in(bank)))
    out = {}
    for s in RF.SLOTS:
        rows = []
        for it in got.get(s) or []:
            t, fid, bad = (it.get("text") or "").replace("\\n", "\n").strip(), it.get("format"), []
            it["text"] = t
            e = ids[s].get(fid)
            if not e:
                bad.append(f"format {fid!r} is not one it was handed")
            elif not RF.keeps(e["format"], t):
                bad.append(f"does not keep the shape of {fid}: its paragraphs one for one and most of its own words, in order")
            if re.search(r"\[[A-Z][A-Z ]+\]", t):
                bad.append("a [BLANK] was left unfilled")
            # relevance (2026-10-29): a
            # line about a subscription, a code, a bundle or a payment plan stands only when this ad's offer has one
            offer_now = " ".join(offer_lines) if offer_lines else (CS.offer_text(brand, product)[0] or "")
            for word, pat in (("subscription", r"subscri"), ("code", r"\bcode\b"), ("payment plan", r"payment plan|installment|klarna|afterpay"),
                              ("trial", r"\btrial\b"), ("refill", r"refill")):
                if re.search(rf"(?i){pat}", t) and not re.search(rf"(?i){pat}", offer_now):
                    bad.append(f'talks about a {word}, which this offer does not have: not relevant to this ad')
            # a format word that leans on a blank ("Free [INGREDIENT] Infused [FREE GIFT]") stays only when that blank
            # had something true to fill it (2026-10-28: "USB-C Infused Charging Base", "Black Friday Infused ...")
            for m in re.finditer(r"(?i)([\w-]+)[ -](infused|enriched|powered|formulated)\b", t):
                # the phrase itself must be the product's ("silver-infused" is; "Black Friday Infused" is not)
                if not re.search(rf"(?i)\b{re.escape(m.group(1))}[ -]{m.group(2)}\b", product_text_of(brand, product)):
                    bad.append(f'"{m.group(0)}" is left over from the format: the product file says no such thing; '
                               f'drop "{m.group(2)}" with its blank')
            if s in LIMIT and len(t) > LIMIT[s]:
                bad.append(f"{len(t)} characters (max {LIMIT[s]})")
            heads = [t] if s == "headlines" else []
            descs = [t] if s == "descriptions" else []
            bodies = [t] if s == "primary" else []
            bad += CS.offer_problems(heads, descs, promo, bodies=bodies, level=awareness)
            said = " ".join("$" + f"{float(p):.2f}" for p in sorted(Q.prices_in(t)))
            bad += Q.price_check(said, live) if said else []
            bad += [f"cites a row it wasn't given: {r}" for r in it.get("rows_used") or [] if cited and r not in cited]
            rows.append((it, bad))
        if s == "primary" and len({it.get("format") for it, b in rows if not b}) < len([1 for _, b in rows if not b]):
            rows = [(it, b + ["two primary texts from one format"]) if i and it.get("format") in
                    {x.get("format") for x, _ in rows[:i]} else (it, b) for i, (it, b) in enumerate(rows)]
        out[s] = rows
    return out


def story_check(checked, elements, ask):
    """Each line read against THIS ad's elements (the owner, 2026-10-27: "we got to put in our actual elements that make
    sense, that are relevant to the brief itself"; a Thai grandmother's turmeric story reached an 80s-filter ad's card).
    One cheap call for every line that passed the format check; a line that tells another ad's story gets the reason."""
    items = [(s, i, it) for s in RF.SLOTS for i, (it, bad) in enumerate(checked[s]) if not bad]
    if not items or not elements:
        return checked
    lines = "\n".join(f"{n + 1}. [{s}] {it['text']}" for n, (s, i, it) in enumerate(items))
    q = ("THIS AD'S ELEMENTS:\n" + json.dumps(elements, ensure_ascii=False, indent=1) + "\n\nTHE LINES:\n" + lines +
         "\n\nFor each line: does it tell ANOTHER story than this ad's? It fails ONLY when its subject is another person, "
         "place, family or era (a different woman's history, another country's village, a parent's life told as the story). "
         "A short line that names only some of this ad's elements fits. The brand's own claims, its origin and recipe, its "
         "ingredients, its proof and its guarantee always fit. "
         "Return only a json list, one object per line in order: {\"n\": 1, \"fits\": true|false, \"why\": \"…\"}.")
    try:
        import copy_set as CS
        got = CS.parse('{"r": ' + re.search(r"\[.*\]", ask(q), re.S).group(0) + "}")["r"]
    except Exception as e:  # noqa: BLE001  a check that cannot run says so on the run, it never passes a line silently
        for s, i, it in items:
            checked[s][i] = (it, ["the story check could not run: " + str(e)[:120]])
        return checked
    for (s, i, it), g in zip(items, got):
        if g.get("fits") is False:
            checked[s][i] = (it, [f"not this ad's story: {g.get('why') or 'another story'}"])
    return checked


def problems_of(checked):
    return [f"{s} {i + 1} ({it.get('format')}): {p}" for s, rows in checked.items()
            for i, (it, bad) in enumerate(rows) for p in bad]


def render(checked, lists, run_note=""):
    """The stage 8 shape card_words reads: each body under its format, then HEADLINES and DESCRIPTIONS."""
    by = {e["id"]: e for s in RF.SLOTS for e in lists[s]}
    out = []
    for it, bad in checked["primary"]:
        if bad:
            continue
        e = by[it["format"]]
        out += [f"**FORMAT: {e['id']} · from our ad \"{e['name']}\"**", "", "**BODY A**", "", it["text"], "",
                f"*({len(it['text'].split())} words)*", "", "---", ""]
    for s, head in (("headlines", "HEADLINES"), ("descriptions", "DESCRIPTIONS")):
        out += [f"**{head}**", ""]
        n = 0
        for it, bad in checked[s]:
            if bad:
                continue
            n += 1
            e = by[it["format"]]
            out.append(f"{n}. **{it['text']}** — {e['id']} (from \"{e['name']}\")")
        out.append("")
    if run_note:
        out += ["---", "", run_note, ""]
    return "\n".join(out)


def write(brand, brief, product, src, *, awareness=None, promo=False, avatar=None, topics=None, label,
          dry_run=False, ask=None, check_ask=None, model="claude-opus-5-5", ws=WS, say=print, moment=None,
          offer_lines=None):
    """Write the words for one ad. Returns {"run", "label", "rc", "words", "problems"} or None when the brand has no
    format bank (the caller then uses the old chain)."""
    import copy_set as CS
    if not RF.load(brand, ws):
        return None
    awareness = awareness or market_state(src)
    lists = shortlists(brand, awareness, promo, ws, moment=moment)
    if not lists["primary"]:
        return None
    # The formats are handed over, not chosen (the owner, 2026-10-27: "we're just using the formats and changing elements,
    # that's it"): the top of each shortlist, best results first at the ad's awareness level, is what gets filled.
    lists = {s: lists[s][:COUNTS[s]] for s in RF.SLOTS}
    CS.awareness_entry(awareness)
    lang_problems = []
    rows = CS.language_rows(brand, avatar, topics, awareness=awareness, problems=lang_problems)
    spice = CS.spice_rows(brand, avatar, awareness)
    cited = CS.row_texts(rows + [l for l in spice.splitlines() if l.startswith("- [language_")])
    offers, _ = CS.offer_text(brand, product)
    fill = {"awareness": awareness or "not given",
            "awareness_levels": (CS.DOCTRINE / "slices" / "awareness.md").read_text().strip(),
            "promo": "yes — a promotion / value ad" if promo else "no — not a promotion",
            "price_in_bodies": "allowed" if promo else "barred",
            "creative_controls": CS._controls(), "the_ad": ad_text(src), "picture_words": picture_words(src),
            "brand": brand, "product": CS.product_text(brand, product), "offers": offers,
            "guarantee": CS.guarantee_text(brand),
            "language": "\n".join(rows) or ("(NO language rows came back: " + "; ".join(lang_problems)
                                            + " — fill from the product file and say so; never invent a quote)"),
            "spice_bank": spice,
            "primary_formats": formats_text(lists["primary"]), "headline_formats": formats_text(lists["headlines"]),
            "description_formats": formats_text(lists["descriptions"])}
    prompt_file = RF.latest_prompt("copy-format-fill")
    sent = prompt_file.read_text().split("\n---\n", 1)[1]
    for k, v in fill.items():
        sent = sent.replace("{" + k + "}", v)
    run = Path(ws) / "runs/copywriter" / RF.slug(brand) / label
    if dry_run:
        say(f"  format copy: {len(lists['primary'])} primary · {len(lists['headlines'])} headline · "
            f"{len(lists['descriptions'])} description formats handed over · {len(rows)} language rows · "
            f"{len(sent):,} characters · {model} → {run.relative_to(ws)}")
        return {"run": run, "label": label, "rc": 0, "words": None, "problems": lang_problems, "sent": sent}
    ask = ask or (lambda t: CS.claude(t, model))
    answer = ask(sent)
    got = CS.parse(answer)
    elements = got.get("elements") or {}
    ask_check = check_ask or (lambda q: CS.claude(q, CHECK_MODEL))
    checked = story_check(check(got, lists, promo=promo, awareness=awareness, brand=brand, product=product, cited=cited, offer_lines=offer_lines),
                          elements, ask_check)
    tries = 1
    if problems_of(checked):
        again = sent + "\n\n## Sent back once\n\nYour answer broke these; fix each and return the whole json again:\n" + \
            "\n".join(f"- {p}" for p in problems_of(checked)) + "\n\nYour answer was:\n" + answer
        answer2 = ask(again)
        tries = 2
        try:
            got2 = CS.parse(answer2)
            checked2 = story_check(check(got2, lists, promo=promo, awareness=awareness, brand=brand, product=product, offer_lines=offer_lines,
                                         cited=cited), got2.get("elements") or elements, ask_check)
            if len(problems_of(checked2)) <= len(problems_of(checked)):
                checked, answer = checked2, answer + "\n\n--- sent back once ---\n\n" + answer2
        except (ValueError, SystemExit):
            pass
    # A line that still fails is rewritten on its own, with the reason, before it is ever dropped (the owner, 2026-10-27, on
    # the long story version dropped from a card: "we need the story version too"): up to two focused rewrites each.
    by_id = {e["id"]: e for s in RF.SLOTS for e in lists[s]}
    for s in RF.SLOTS:
        for i, (it, bad) in enumerate(checked[s]):
            for _ in range(2):
                if not bad or it.get("format") not in by_id:
                    break
                e = by_id[it["format"]]
                fix = (sent + "\n\n## Rewrite ONE line\n\nOnly the " + s + " line below, from format " + e["id"] + ". It broke:\n- "
                       + "\n- ".join(bad) + "\n\nThe line was:\n" + it["text"] + "\n\nTHIS AD'S ELEMENTS:\n"
                       + json.dumps(elements, ensure_ascii=False) + "\n\nTell it as THIS ad's story, from its own person, in "
                       "the format's own structure. Return only one fenced json block: {\"" + s + "\": [{\"format\": \""
                       + e["id"] + "\", \"text\": \"…\", \"rows_used\": []}]}")
                try:
                    one = CS.parse(ask(fix))
                except (ValueError, SystemExit):
                    break
                one = {k: v for k, v in one.items() if k == s}
                c1 = story_check(check(one, {**{x: [] for x in RF.SLOTS}, s: [e]}, promo=promo, awareness=awareness,
                                       brand=brand, product=product, cited=cited, offer_lines=offer_lines), elements, ask_check)
                if c1[s]:
                    it, bad = c1[s][0]
                    answer += f"\n\n--- {s} {i + 1} rewritten on its own ---\n\n" + it["text"]
            checked[s][i] = (it, bad)
    left = problems_of(checked)
    good = {s: sum(1 for _, b in checked[s] if not b) for s in RF.SLOTS}
    note = ("Dropped after the send-back and two rewrites: " + "; ".join(left)) if left else ""
    run.mkdir(parents=True, exist_ok=True)
    text = render(checked, lists, note)
    (run / "format-fill--sent.md").write_text(sent)
    (run / "format-fill--answer.md").write_text(answer)
    for f in ("stage8--render.md", "final--copy.md"):
        (run / f).write_text(text)
    passed = good["primary"] >= 1 and good["headlines"] >= 1
    rec = {"tool": TOOL, "brand": RF.slug(brand), "brief": brief, "product": product, "avatar": avatar,
           "awareness": awareness, "promo": promo, "source_path": str(Path(src).resolve().relative_to(Path(ws).resolve()))
           if str(Path(src).resolve()).startswith(str(Path(ws).resolve())) else str(src),
           "prompt": str(prompt_file.relative_to(ws)), "model": model, "tries": tries,
           "written_at": datetime.now().isoformat(timespec="seconds"), "language_problems": lang_problems,
           "formats_used": {s: [it["format"] for it, b in checked[s] if not b] for s in RF.SLOTS},
           "kept": good, "elements": elements,
           "read_check": {"passed": passed, "by": "format check + story check against this ad's elements", "problems": left},
           "status": "draft"}
    (run / "run.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    (run / "check.json").write_text(json.dumps({"held": not passed, "problems": left}, indent=1) + "\n")
    words = {s: [it["text"] for it, b in checked[k] if not b] for s, k in
             (("primary", "primary"), ("headlines", "headlines"), ("descriptions", "descriptions"))}
    say(f"  format copy: {good['primary']} primary · {good['headlines']} headlines · {good['descriptions']} descriptions"
        f" → {run.relative_to(ws)}" + (f" ({len(left)} dropped)" if left else ""))
    return {"run": run, "label": label, "rc": 0 if passed else 2, "words": words, "problems": left}


def main():
    sys.path.append(str(HERE))
    import brief_words as BW
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--brief", required=True)
    ap.add_argument("--product")
    ap.add_argument("--source")
    ap.add_argument("--awareness")
    ap.add_argument("--promo", action="store_true", default=None)
    ap.add_argument("--label")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    res = BW.write(a.brand, a.brief, a.product, source=a.source, dry_run=a.dry_run, label=a.label,
                   awareness=a.awareness, promo=a.promo)
    print(res.get("source"))
    if res.get("words"):
        for k, v in res["words"].items():
            for x in v:
                print(f"[{k}] {x}\n")


if __name__ == "__main__":
    main()
