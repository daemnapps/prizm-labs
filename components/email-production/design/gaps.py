"""Find every gap in a designed email and fill what the brand's own files can fill, before any person is asked.

the owner, 2026-10-18 (the Brand-B product card showed "[UNFILLED: price]" and a tiny scene where the product belonged):
"we should be able to prompt the system to fill in gaps first, then if we need to do manual changes we do that, but
we want to get the system automating as much of this process as possible."

    python3 tools/email-production/design/gaps.py runs/email-production/<brand>/<label> [--fill]

A gap is anything a reader would see as unfinished: an "[UNFILLED: …]" note from the copy chain, a product card with
no price, a picture slot never made, a picture the judge held or the model refused. fill() closes what the files
answer, in this order, and leaves the rest as a plain question for a person:

    price       the offer bank's live price for that product (brands/<brand>/products/offer-bank.md, read only).
                Never for a sale the bank has no offer for: a "Black Friday price" with no Black Friday offer stays a
                gap for the person who sets offers. Inventing one is the one thing this must never do.
    picture     an unmade or refused slot is sent through the picture step again (line.make_pictures)
    product picture on a product card: the brand's real product cut-out (its look file's products), never a scene
    other words the smallest patch that closes the gap (prompts/design4-patch-v1-owner.md): only the gap changes,
                every section people already ruled on stays exactly as it is; then the promise check reads it again

Every fill is written into the email's layout, recorded in <run>/gaps.json (what was missing, what filled it, from
where), and the email is rebuilt and checked; the final check holds anything still open.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EM = HERE.parent
REPO = EM.parents[1]
UNF = re.compile(r"\[UNFILLED[^\]]*\]")
SALE = re.compile(r"black friday|cyber monday|sale|deal|% off|discount|price drop", re.I)


def offer_bank(brand):
    """{product name lowercased: {"price", "funnel", "slug"}} from the brand's offer bank, read only."""
    f = REPO / "brands" / brand / "products" / "offer-bank.md"
    out = {}
    if not f.is_file():
        return out
    cur = None
    for line in f.read_text().splitlines():
        m = re.match(r"^## ([a-z0-9-]+) — (.+)$", line)
        if m:
            cur = {"slug": m.group(1), "name": m.group(2).strip()}
            out[cur["name"].lower()] = cur
            continue
        if not cur:
            continue
        m = re.match(r"^- Price: \*\*(\$[\d.]+)\*\*", line)
        if m:
            cur["price"] = m.group(1)
        m = re.match(r"^- Sold in the CPK funnel at: (\$\d+(?:\.\d\d)?) \(1 Tube\)", line)
        if m:
            cur["funnel"] = m.group(1)
    return out


def sale_offer(brand, occasion):
    """The offer bank's block for this occasion (e.g. `### black-friday`) as {"name", "card", "prices"}, or None."""
    f = REPO / "brands" / brand / "products" / "offer-bank.md"
    if not occasion or not f.is_file():
        return None
    occ = occasion.split(" ")[0].lower()
    for block in re.split(r"\n#{2,3} ", f.read_text())[1:]:
        head = block.split("\n", 1)[0].lower()
        if (head.startswith(occ) or occ.replace("-", " ") in head) and re.search(r"\$\d", block):
            card = re.search(r"^\| Card price \| (.+?) \|\s*$", block, re.M)
            return {"name": block.split("\n", 1)[0], "card": card.group(1).strip() if card else None,
                    "prices": sorted(set(re.findall(r"\$\d+(?:\.\d\d)?", block)))}
    return None


def _walk_fields(sec, path=""):
    for k, v in (sec.items() if isinstance(sec, dict) else enumerate(sec)):
        p = "%s.%s" % (path, k) if path else str(k)
        if isinstance(v, str):
            yield p, v
        elif isinstance(v, (dict, list)) and k not in ("picture",):
            yield from _walk_fields(v, p)


def _set(sec, path, value):
    parts = path.split(".")
    cur = sec
    for p in parts[:-1]:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    last = parts[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value


def _pictures(x, out):
    if isinstance(x, dict):
        if "alt" in x or "todo" in x:
            if any(k in x for k in ("todo", "photo", "proof", "stage", "refused")):
                out.append(x)
        for v in x.values():
            _pictures(v, out)
    elif isinstance(x, list):
        for v in x:
            _pictures(v, out)
    return out


NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
STEP = re.compile(r"\bstep (one|two|three|four|five|[1-5])\b", re.I)
CLAIM = re.compile(r"\b(two|three|four|five|[2-5])[ -]steps?\b", re.I)


def sequence_gaps(spec):
    """A numbered sequence the email starts and never finishes: it says "two steps" and labels STEP ONE but no STEP
    TWO (2026-10-18, the sleeves email: the cream's step was in the copy, the brief and the job card, and the layout
    dropped it). Returns [(section index to add after, the missing step numbers, the claim)]."""
    text = []
    for i, s in enumerate(spec.get("sections", [])):
        for _, v in _walk_fields(s):
            text.append((i, v))
    labelled = {}
    for i, v in text:
        for m in STEP.finditer(v):
            labelled.setdefault(NUM[m.group(1).lower()], i)
    claims = [NUM[m.group(1).lower()] for _, v in text for m in CLAIM.finditer(v)]
    if not labelled or not claims:
        return []
    want = max(claims)
    missing = [n for n in range(1, want + 1) if n not in labelled]
    if not missing:
        return []
    words = {2: "two", 3: "three", 4: "four", 5: "five"}
    return [(max(labelled.values()), missing, "%s steps" % words.get(want, want))]


def find(run):
    run = Path(run)
    spec = json.loads((run / "design" / "email.json").read_text())
    rj = json.loads((run / "run.json").read_text()) if (run / "run.json").is_file() else {}
    occasion = (rj.get("assignment") or {}).get("occasion") or ""
    words = json.dumps(spec, ensure_ascii=False)
    try:                                 # parts a person marked right: an unchecked picture there was looked at
        ok = set(json.loads((run / "klaviyo" / "card.json").read_text()).get("sections_ok") or [])
    except (OSError, ValueError):
        ok = set()
    gaps = []
    for i, s in enumerate(spec["sections"]):
        for path, v in _walk_fields(s):
            if UNF.search(v):
                gaps.append({"section": i, "type": s.get("s"), "field": path, "kind": "price" if "price" in path or "price" in v.lower() else "words",
                             "now": v, "why": UNF.search(v).group(0)})
        if s.get("s") == "product" and not (s.get("price") or "").strip():
            gaps.append({"section": i, "type": "product", "field": "price", "kind": "price", "now": "", "why": "no price on the product card"})
        for p in _pictures(s, []):
            if "todo" in p:
                why = ("refused: " + p["refused"][:160] if p.get("refused") else
                       "made, but thrown away because the picture judge could not run (%s): press Make the missing parts "
                       "to try again" % p["unjudged"][:120] if p.get("unjudged") else "picture not made yet")
                gaps.append({"section": i, "type": s.get("s"), "field": "picture", "kind": "picture",
                             "now": p.get("todo", "")[:160], "why": why})
            elif p.get("unchecked") and i not in ok:
                gaps.append({"section": i, "type": s.get("s"), "field": "picture", "kind": "picture", "now": p.get("alt", "")[:160],
                             "why": "made, but the picture judge could not check it (%s): look at it yourself, and mark the "
                                    "part right if it is" % p["unchecked"][:120]})
        if s.get("s") == "product" and isinstance(s.get("picture"), dict) and s["picture"].get("source") != "cut" and "stage" not in s["picture"]:
            gaps.append({"section": i, "type": "product", "field": "picture", "kind": "product picture", "now": s["picture"].get("alt", ""),
                         "why": "a product card shows the real product, cut out"})
    for after, missing, claim in sequence_gaps(spec):
        gaps.append({"section": after, "type": spec["sections"][after].get("s"), "field": "the next step", "kind": "words",
                     "now": "", "why": "the email says \"%s\" but has no STEP %s card" % (claim, " or ".join(
                         {1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE"}[n] for n in missing))})
    pf = run / "design" / "promises.json"            # the whole-email reader's broken promises (design/promises.py)
    if pf.is_file():
        try:
            for r in json.loads(pf.read_text()).get("broken", []):
                w = r.get("where")
                i = (w[-1] if isinstance(w, list) and w else int(re.findall(r"\d+", str(w))[-1]) if re.findall(r"\d+", str(w)) else 1) - 1
                if any(g["field"] == "the next step" and g["section"] == i for g in gaps):
                    continue
                gaps.append({"section": max(0, min(i, len(spec["sections"]) - 1)), "type": "promise", "field": "a promise",
                             "kind": "words", "now": "", "why": "%s — missing: %s" % (r.get("promise"), r.get("missing")), "fix": r.get("fix")})
        except (ValueError, OSError, IndexError):
            pass
    return {"spec": spec, "occasion": occasion, "sale_words": bool(SALE.search(words)), "gaps": gaps}


def patch(run, brand, lk, gaps):
    """Close the given gaps with the fewest ops on the layout (prompts/design4-patch-v1-owner.md); writes the layout,
    re-reads it with the promise check, returns {"ops", "closed", "cannot_fill"}."""
    run = Path(run)
    d = run / "design"
    spec = json.loads((d / "email.json").read_text())
    import line
    import promises as PM
    sys.path.insert(0, str(REPO / "components" / "run-kit"))
    from run_kit import model as M
    lean_call = PM.lean()                    # LD-62 (lean model calls)
    truth, _ = line.product_truth(brand)
    job = spec.get("job") or (json.loads((d / "job.json").read_text()) if (d / "job.json").is_file() else {})
    cf = run / "deliverable" / "email.json"
    copy = json.loads(cf.read_text()) if cf.is_file() else {}
    secs = "\n".join("%s: %s" % (k, v) for k, v in line.GUIDE.items())
    gl = "\n".join("- section %d (%s): %s%s" % (g["section"] + 1, g["type"], g["why"], (". Suggested fix: " + g["fix"]) if g.get("fix") else "") for g in gaps)
    p = (EM / "prompts" / "design4-patch-v1-owner.md").read_text()
    for k, v in (("rulings", PM.rulings(run, spec)), ("product_truth", truth), ("sections", secs),
                 ("job", json.dumps(job, indent=1, ensure_ascii=False)), ("copy", json.dumps(copy, indent=1, ensure_ascii=False)[:30000]),
                 ("gaps", gl), ("spec", json.dumps({k: v for k, v in spec.items() if k != "job"}, indent=1, ensure_ascii=False))):
        p = p.replace("{%s}" % k, v)
    (d / "design4--prompt.md").write_text(p)
    model, _ = M.pick("designs", len(p))
    text = M.call(p, model, label="design4-" + run.name, runner=lean_call.design_runner(M))
    res = None
    for attempt in range(2):                 # an answer that won't parse goes back once with the reason, never dropped
        m = re.search(r"\{.*\}", text or "", re.S)
        try:
            res = json.loads(m.group(0)) if m else None
        except ValueError as e:
            res, why = None, str(e)
        else:
            why = "no JSON object in the answer"
        if res is not None or attempt:
            break
        text = M.call(p + "\n\nYOUR LAST ANSWER WAS NOT VALID JSON (%s). Return the same ops as one valid JSON object, nothing else." % why,
                      model, label="design4-fix-" + run.name, runner=lean_call.design_runner(M))
    res = res or {"ops": [], "cannot_fill": ["the patch answer would not parse twice"]}
    ops = res.get("ops") or []
    secs_now = spec["sections"]
    for op in sorted(ops, key=lambda o: -int(o.get("index", 0))):          # highest index first: earlier indexes hold
        i = int(op.get("index", 0))
        if op.get("op") == "insert_after" and isinstance(op.get("section"), dict) and op["section"].get("s"):
            secs_now.insert(i + 1, op["section"])
        elif op.get("op") == "set" and 0 <= i < len(secs_now) and op.get("field") and op["field"] != "s" \
                and not (op["field"] in ("picture", "pictures", "hero", "tiles") or (isinstance(op.get("value"), dict) and ("photo" in op["value"] or "proof" in op["value"]))):
            # a picture is never "fixed" by rewriting its description: the words must match the picture people see
            # (2026-10-18: a patch rewrote an alt to claim cards and an envelope were in frame; the file was unchanged)
            secs_now[i][op["field"]] = op.get("value")
    spec.setdefault("patches", []).append({"ops": ops, "closed": res.get("closed"), "cannot_fill": res.get("cannot_fill"), "model": model})
    (d / "email.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    try:
        PM.check(run, spec, job, copy)                 # read whole again: what is still broken stays a gap
    except Exception as e:  # noqa: BLE001
        res.setdefault("cannot_fill", []).append("the promise check could not re-read it: %r" % e)
    return res


def fill(run, brand=None, lk=None, make_pictures=True, redesign=True, pictures_only=False):
    """Fill every gap the brand's files answer; returns {"filled": [...], "open": [...]} and writes <run>/gaps.json.
    pictures_only: the page's Make the missing parts makes pictures and nothing else; a price or a promise stays for
    the team (the team, 2026-10-28: the patch applied a promise note that was noise and swapped a real photo on nov-04)."""
    run = Path(run)
    brand = brand or run.parent.name
    found = find(run)
    spec, gaps = found["spec"], found["gaps"]
    bank = offer_bank(brand)
    has_sale = sale_offer(brand, found["occasion"])
    filled, left = [], []
    for g in gaps:
        s = spec["sections"][g["section"]]
        if pictures_only and "picture" not in g["kind"]:
            left.append(dict(g, ask="the team's to settle: Make the missing parts only makes pictures"))
            continue
        if g["kind"] == "price":
            name = (s.get("name") or "").lower()
            row = bank.get(name) or next((v for k, v in bank.items() if k in name or name in k), None) if name else None
            ctx = " ".join(v for _, v in _walk_fields(s)).lower()
            sale_card = bool(SALE.search(ctx)) or ("black friday" in json.dumps(spec).lower() and found["occasion"].startswith("black"))
            if sale_card and has_sale and has_sale.get("card"):
                _set(s, g["field"], UNF.sub(has_sale["card"], g["now"]) if g["now"] else has_sale["card"])
                filled.append(dict(g, now=has_sale["card"], by="offer bank",
                                   source="brands/%s/products/offer-bank.md (%s)" % (brand, has_sale["name"])))
                continue
            if sale_card and not has_sale:
                left.append(dict(g, ask="Set the %s offer in the offer bank: this card sells a %s price and the bank has none, "
                                        "so no price was invented." % (found["occasion"].split(" ")[0] or "sale", found["occasion"].split(" ")[0] or "sale")))
                continue
            price = row and (row.get("funnel") or row.get("price"))
            if not price:
                left.append(dict(g, ask="No price for %s in the offer bank." % (s.get("name") or "this product")))
                continue
            _set(s, g["field"], UNF.sub(price, g["now"]) if g["now"] else price)
            filled.append(dict(g, now=price, by="offer bank", source="brands/%s/products/offer-bank.md (%s)" % (brand, row["slug"])))
        elif g["kind"] == "product picture":
            key = next((k for k in ((lk or {}).get("products") or {}) if not k.startswith("_") and k.split("-")[0] in (s.get("name") or "").lower()), None)
            if not key:
                left.append(dict(g, ask="No cut-out of this product in the brand's look file."))
                continue
            s["picture"] = {"stage": "product:%s" % key, "alt": s["picture"].get("alt", ""), "source": "cut"}
            filled.append(dict(g, by="brand look file", source="products.%s" % key))
        elif g["kind"] == "picture":
            left.append(dict(g, ask="remake", auto=True))
        else:
            left.append(dict(g, ask="fill this from the email's own copy chain", auto=True))
    (run / "design" / "email.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    auto = [g for g in left if g.get("auto")]
    if auto and make_pictures and any(g["kind"] == "picture" for g in auto):
        import line
        line.make_pictures(brand, run, lk or line.L.load(brand))
        still = {(g["section"]) for g in find(run)["gaps"] if g["kind"] == "picture"}
        for g in [g for g in auto if g["kind"] == "picture"]:
            (left.remove(g), filled.append(dict(g, by="picture step"))) if g["section"] not in still else g.update(ask="the picture step could not make it: %s" % g["why"])
    words = [g for g in auto if g["kind"] == "words"]
    if words and redesign:
        # The smallest change that makes the email whole (design4-patch): only the gaps change, every section people
        # already ruled on stays exactly as it is. (2026-10-18: a full redesign to add STEP TWO rebuilt the whole
        # email around a new concept and dropped a price ruling. Never again for a gap.)
        try:
            res = patch(run, brand, lk, words)
        except Exception as e:  # noqa: BLE001
            res = {"error": str(e)[:300]}
        still = {(g["section"], g["field"], g["why"]) for g in find(run)["gaps"]}
        for g in words:
            if not res.get("error") and (g["section"], g["field"], g["why"]) not in still and not any(
                    g["why"][:40] in c for c in res.get("cannot_fill", [])):
                left.remove(g); filled.append(dict(g, by="patch: the smallest change, nothing else touched"))
            else:
                g["ask"] = "a person: " + (res.get("error") or "; ".join(res.get("cannot_fill", [])) or "the patch did not close it")
        if res.get("ops") and make_pictures:
            import line
            line.make_pictures(brand, run, lk or line.L.load(brand))
    out = {"filled": filled, "open": [{k: v for k, v in g.items() if k != "auto"} for g in left]}
    (run / "gaps.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for r in args:
        if "--fill" in sys.argv:
            sys.path.append(str(HERE))
            import look as L
            res = fill(r, lk=L.load(Path(r).parent.name))
            print("%s  filled %d · open %d" % (Path(r).name, len(res["filled"]), len(res["open"])))
            for g in res["filled"]:
                print("   filled  section %d %s: %s (%s)" % (g["section"] + 1, g["field"], g.get("now"), g.get("source") or g.get("by")))
            for g in res["open"]:
                print("   OPEN    section %d %s: %s" % (g["section"] + 1, g["field"], g.get("ask")))
        else:
            for g in find(r)["gaps"]:
                print("%s  section %d %s %s: %s" % (Path(r).name, g["section"] + 1, g["type"], g["field"], g["why"]))
