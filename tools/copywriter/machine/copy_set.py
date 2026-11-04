#!/usr/bin/env python3
"""copy_set — one set of ad words per brand + product + angle, reused by every ad on that angle.

    copy_set.py write  --brand brand-a --product crush --angle razor-not-problem --topics razor-bumps,shaving,ingrown-hairs,neck
    copy_set.py check  --brand brand-a --product crush --angle razor-not-problem
    copy_set.py show   --brand brand-a --product crush --angle razor-not-problem [--page link_brand_a_store_method-quiz]
    copy_set.py approve --brand brand-a --product crush --angle razor-not-problem --by the owner
    copy_set.py list   [--brand brand-a]

the owner, 2 Oct 2026: "most of the time we don't actually need to change the copy for
each ad. unless it's a completely different angle, usually you can just use the same
formats … it'd be good to actually write fundamentally sound copy because right now,
this copy is awkward."

A set is written once, from the product file, the angle, the offer bank, the guarantee
and the market's own words (prompts/copy-set-v1-owner.md), checked (check()), and
approved once by the owner. Every card on that brand + product + angle then takes its words
from the approved set (meta-upload/card_words.for_brief): `{offer}` becomes the set's
offer line and `{click}` the line for the ad's page type, so the words always match the
page the ad sends people to. A new angle is the only thing that writes new copy.

Saved at runs/copywriter/<brand>/copy-sets/<product>_<angle>.json — id `copy_<brand>_<product>_<angle>`.
(Not in brands/: the brand tree is read-only to machines, and a set is this tool's deliverable.)
"""
import argparse, json, re, subprocess, sys, time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
COPY = HERE.parent
WS = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
sys.path.append(str(WS / "components/naming"))
sys.path.append(str(WS / "components/quality-checks"))
import names as N  # noqa: E402

PROMPTS = COPY / "prompts"


def latest_set_prompt():
    """Highest copy-set-vN wins (same rule as copy.py's latest_prompt)."""
    got = [(int(m.group(1)), f) for f in PROMPTS.glob("copy-set-v*-owner.md")
           for m in [re.search(r"-v(\d+)-", f.name)] if m]
    return max(got)[1]


PROMPT = latest_set_prompt()
MODEL = "claude-opus-5-5"
FORMATS = {"short": (25, 45), "standard": (70, 120), "proof": (50, 110)}
HEADLINE_MAX, DESCRIPTION_MAX = 40, 30
ORGANIC = re.compile(r"link in (my |the )?bio|comment (below|down)|follow (me|us|for)|\bDM\b|share this|tag a", re.I)
STAGES = ("injection", "expansion", "proof")


# ---------- the two rules (the owner, 2026-10-12) ----------
# "no prices in headlines or descriptions on meta unless it's clearly a promotion or value focused ad. this is
# literally tip of funnel brain rot so the copy should reflect unaware levels of copywriting as well."
# RULE 1 (price): no price, deal, pack offer or money-back line in a headline or description unless the ad is a
# promotion. RULE 2 (awareness): the words are written at the ad's awareness level, read from the doctrine
# (components/marketing-doctrine/frameworks.json) and never restated here — a level whose Must NOT names price
# also bars a price in the bodies. copy.py's copy gate uses these same functions.
DOCTRINE = WS / "components" / "marketing-doctrine"
PRICE_DEAL = re.compile(r"\$\s?\d[\d,.]*|\d+\s?%\s?off|\bbuy\s+(?:\d+|one|two|three)\b[^.\n]{0,20}\bget\b|"
                        r"\b(?:\d+|one|two|three)\s+free\b|\bfree\s+(?:shipping|pouch|gift|bonus)\b|\bdiscount|"
                        r"\bon sale\b|\bsale\b|\bdeal\b|\bsave\s+\$?\d|\bwas\s+\$|\bdown from\b|\bper (?:jar|unit|bottle)\b", re.I)
MONEY_BACK = re.compile(r"\bmoney[- ]?back\b|\brefund|\bguarantee", re.I)
PROMO_ANGLE = re.compile(r"\b(?:value|price|offer|deal|sale|discount|stock-up|bundle|promo|promotion)\b", re.I)


def awareness_levels():
    """The doctrine's awareness levels, by id (frameworks.json `awareness.levels`)."""
    d = json.loads((DOCTRINE / "frameworks.json").read_text())
    return {lv["id"]: lv for lv in d["awareness"]["levels"]}


def awareness_entry(level):
    """The doctrine entry for a level id, None for no level; an unknown id is refused with the real ids named."""
    if not level:
        return None
    lv = awareness_levels()
    if level not in lv:
        raise ValueError(f"awareness `{level}` is not a doctrine level — the levels are: {', '.join(lv)}")
    return lv[level]


def bars_price(level):
    """True when the doctrine's Must NOT for this level names price."""
    e = awareness_entry(level)
    return bool(e) and any("price" in m.lower() for m in e.get("must_not") or [])


def awareness_from_run(run, ws=WS):
    """The awareness a production / teardown run recorded for this ad ("awareness" in its brief.md json block,
    run.json, plan.json, doctrine.json or elements.json), or None."""
    if not run:
        return None
    d = Path(run) if Path(str(run)).is_absolute() else Path(ws) / str(run)
    for f in ("brief.md", "run.json", "plan.json", "doctrine.json", "elements.json"):
        if (d / f).is_file():
            m = re.search(r'"awareness"\s*:\s*"([a-z-]+)"', (d / f).read_text())
            if m and m.group(1) in awareness_levels():
                return m.group(1)
    return None


def angle_row(brand, angle, ws=WS):
    f = Path(ws) / "brands" / N.slug(brand) / "strategy" / "angles.json"
    if angle and f.is_file():
        for a in json.loads(f.read_text()).get("angles", []):
            if a.get("id") == angle:
                return a
    return None


def is_promo(brand, angle, flag=None, ws=WS):
    """A promotion / value ad? An explicit flag wins; else the angle row's own `promo`; else the angle row's id or
    name says offer/value/price/deal. Never guessed from the copy."""
    if flag is not None:
        return bool(flag)
    row = angle_row(brand, angle, ws) or {}
    if isinstance(row.get("promo"), bool):
        return row["promo"]
    return bool(row) and bool(PROMO_ANGLE.search(f"{row.get('id', '')} {row.get('name', '')}"))


def offer_problems(headlines, descriptions, promo, bodies=(), level=None):
    """RULE 1 + RULE 2 as a machine check. [] when it passes."""
    probs = []
    if not promo:
        for kind, rows in (("headline", headlines), ("description", descriptions)):
            for t in rows or []:
                m = PRICE_DEAL.search(t or "") or MONEY_BACK.search(t or "")
                if m:
                    probs.append(f"{kind} carries a price or offer (\"{m.group(0)}\") and the ad is not a promotion: \"{t}\"")
        if bars_price(level):
            for t in bodies or []:
                m = PRICE_DEAL.search(t or "")
                if m:
                    probs.append(f"a body carries a price or deal (\"{m.group(0)}\") at awareness `{level}`, whose "
                                 f"doctrine entry bars price")
    return probs


def set_id(brand, product, angle):
    return f"copy_{N.slug(brand)}_{N.slug(product)}_{N.slug(angle)}"


def set_path(brand, product, angle, ws=WS):
    return Path(ws) / "runs" / "copywriter" / N.slug(brand) / "copy-sets" / f"{N.slug(product)}_{N.slug(angle)}.json"


def load(brand, product, angle, ws=WS):
    p = set_path(brand, product, angle, ws)
    return json.loads(p.read_text()) if p.is_file() else None


def approved(brand, product, angle, ws=WS):
    """The set every ad on this angle uses, or None while there is no approved one."""
    s = load(brand, product, angle, ws) if brand and product and angle else None
    return s if s and s.get("status") == "approved" else None


def save(s, ws=WS):
    p = set_path(s["brand"], s["product"], s["angle"], ws)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n")
    return p


# ---------- what the writer reads ----------

def product_text(brand, product):
    base = WS / "brands" / N.slug(brand) / "products"
    names = [str(product)]
    try:                                                       # the catalog id and its aliases (2026-10-28)
        cid = N.product_id(brand, product)
        names += [cid] + list(N.product_aliases(brand, cid) or []) if cid else []
    except Exception:                                          # noqa: BLE001
        pass
    for name in dict.fromkeys(x for x in names if x):
        for cand in (base / f"{name}.md", base / name / "product.md"):
            if cand.is_file():
                return cand.read_text()
        if (base / name).is_dir():
            return "\n\n".join(p.read_text() for p in sorted((base / name).glob("*.md")))
    sys.exit(f"no product file for {brand} {product} under {base}")


def angle_text(brand, angle, given=None):
    if given:
        return given
    f = WS / "brands" / N.slug(brand) / "strategy" / "angles.json"
    if f.is_file():
        for a in json.loads(f.read_text()).get("angles", []):
            if a.get("id") == angle:
                return f"{a.get('name')}\n{a.get('what')}"
    sys.exit(f"angle {angle} is not in {f.relative_to(WS)} — pass --angle-text with what the angle argues")


def offer_text(brand, product):
    """The offer bank's table and this product's own section."""
    f = WS / "brands" / N.slug(brand) / "products" / "offer-bank.md"
    t = f.read_text()
    m = re.search(rf"^## {re.escape(N.slug(product))}\b.*?(?=^## |\Z)", t, re.M | re.S)
    table = t.split("\n---", 1)[0]
    return table + ("\n\n" + m.group(0).strip() if m else ""), t


def guarantee_text(brand):
    f = WS / "brands" / N.slug(brand) / "offers" / "guarantees.json"
    if not f.is_file():
        return "(none on file — write no guarantee line)"
    g = json.loads(f.read_text()).get("guarantees", {})
    return "\n".join(f"- {v.get('surface', k)}: \"{v.get('verbatim', '')}\"" for k, v in g.items())


def _language_call(brand, stage, avatar, topics, limit, awareness=None):
    """One language.py query -> (stdout, problem). A failed call or an empty set is a PROBLEM, said on stderr —
    never quietly zero rows (2026-10-27)."""
    cmd = [sys.executable, str(HERE / "language.py"), "--brand", brand, "--stage", stage, "--limit", str(limit)]
    if avatar:
        cmd += ["--avatar", avatar]
    if topics:
        cmd += ["--topics", topics]
    if awareness:
        cmd += ["--awareness", awareness]
    r = subprocess.run(cmd, capture_output=True, text=True)
    why = None
    if r.returncode != 0:
        why = (f"the language query failed ({stage}, exit {r.returncode}): "
               f"{((r.stderr or '').strip().splitlines() or ['no output'])[-1][:200]}")
    elif "no rows matched" in r.stdout:
        why = f"the language layer returned no rows for {stage} ({avatar or 'every avatar'}, {awareness or 'any level'})"
    if why:
        print(f"  ! {why}", file=sys.stderr)
    return (r.stdout if r.returncode == 0 else ""), why


def language_rows(brand, avatar, topics, limit=25, awareness=None, problems=None):
    """The rows the set is written from: the avatar's, at the ad's awareness level first (the owner, 2026-10-27:
    "awareness levels and verbatims and spice are the foundation of what we're doing here"). Each failed or empty
    stage is appended to `problems` when a list is given."""
    out, seen = [], set()
    for st in STAGES:
        stdout, why = _language_call(brand, st, avatar, topics, limit, awareness)
        if why and problems is not None:
            problems.append(why)
        lines = stdout.splitlines()
        for i, ln in enumerate(lines):
            m = re.match(r"- \[(language_[^\]]+)\]", ln)
            if m and m.group(1) not in seen:
                seen.add(m.group(1))
                out.append(ln + ("\n" + lines[i + 1] if i + 1 < len(lines) and lines[i + 1].startswith("  _") else ""))
    return out


def spice_rows(brand, avatar, awareness=None, limit=25):
    """The copy spice (the language layer's own `spice` stage) for the headlines: what makes the words land."""
    stdout, why = _language_call(brand, "spice", avatar, None, limit, awareness)
    return (f"(no spice rows: {why} — write the headlines from the language rows above; never invent a quote)"
            if why else stdout.strip())


def row_texts(rows):
    """{id: the exact sentence} from the rendered rows."""
    got = {}
    for r in rows:
        m = re.match(r'- \[(language_[^\]]+)\] "(.*)"', r.splitlines()[0])
        if m:
            got[m.group(1)] = m.group(2)
    return got


# ---------- write ----------

def claude(text, model):
    # NO ACCOUNT IS WIRED IN (the owner, 2026-10-23): run_kit's claude_door picks the
    # credential — company key, long-life token, then this machine's login.
    if str(WS / "components/run-kit") not in sys.path:
        sys.path.append(str(WS / "components/run-kit"))
    from run_kit import claude_door
    last = None
    for attempt in (1, 2, 3):
        r = claude_door.run(["--model", model, "--output-format", "text"],
                            text + "\n\nReturn only the deliverable. No tools, no preamble.",
                            timeout=None, cwd=str(COPY))
        if not r.returncode and r.stdout.strip():
            return r.stdout.strip()
        last = r
        time.sleep(5 * attempt)
    sys.exit(f"the writer failed 3 times: {(last.stderr or last.stdout or '').strip()[:300]}")


def parse(out):
    m = re.search(r"```json\s*(\{.*\})\s*```", out, re.S) or re.search(r"(\{.*\})", out, re.S)
    if not m:
        sys.exit("the writer returned no json block:\n" + out[:800])
    return json.loads(m.group(1))


def _controls(ws=WS):
    """The creative controls slice (components/creative-controls), bound by path."""
    f = ws / "components" / "creative-controls" / "slices" / "controls.md"
    return f.read_text().strip() if f.is_file() else ""


def ad_format_text(fmt, ws=WS):
    """The ad format's row from the element library (format.video / format.image), or a plain 'not given'."""
    if not fmt:
        return "not given — the words fit any ad on this angle"
    for f in sorted((Path(ws) / "components/elements/library").glob("format.*.json")):
        for r in json.loads(f.read_text()).get("rows") or []:
            if r.get("id") == fmt:
                return f"{r.get('name')} ({fmt}): {r.get('what')}"
    return f"{fmt} (no row in the element library's format lists)"


def write(brand, product, angle, *, avatar=None, topics=None, angle_given=None, model=MODEL, dry_run=False,
          answer=None, prompt_out=None, awareness=None, promo=None, ad_format=None):
    offers, _ = offer_text(brand, product)
    awareness_entry(awareness)                       # an unknown level is refused before anything is spent
    lang_problems = []
    rows = language_rows(brand, avatar, topics, awareness=awareness, problems=lang_problems)
    spice = spice_rows(brand, avatar, awareness)
    cited = rows + [ln for ln in spice.splitlines() if ln.startswith("- [language_")]   # a headline may cite spice
    promo = is_promo(brand, angle, promo)
    fill = {"brand": brand, "product": product_text(brand, product), "angle": angle_text(brand, angle, angle_given),
            "offers": offers, "guarantee": guarantee_text(brand),
            "language": "\n".join(rows) or ("(NO language rows came back: " + "; ".join(lang_problems)
                                            + " — write without customer words and say so; never invent a quote)"),
            "spice_bank": spice,
            "awareness": awareness or "not given",
            "awareness_levels": (DOCTRINE / "slices" / "awareness.md").read_text().strip(),
            "promo": ("yes — a promotion / value ad" if promo else "no — not a promotion"),
            "price_in_bodies": ("barred" if (bars_price(awareness) and not promo) else "allowed"),
            "ad_format": ad_format_text(ad_format),
            "creative_controls": _controls()}
    template = PROMPT.read_text().split("\n---\n", 1)[1]
    sent = template
    for k, v in fill.items():
        sent = sent.replace("{" + k + "}", v)
    if prompt_out:
        Path(prompt_out).write_text(sent)
    if dry_run:
        print(sent)
        print(f"\n-- {len(rows)} language rows · {awareness or 'no'} awareness level · {len(sent):,} chars · model {model}"
              " · nothing written" + (f" · LANGUAGE PROBLEMS: {'; '.join(lang_problems)}" if lang_problems else ""))
        return None
    # --answer: the writer's reply from another session (the Mac's headless login can lapse)
    got = parse(Path(answer).read_text() if answer else claude(sent, model))
    old = load(brand, product, angle)
    s = {"id": set_id(brand, product, angle), "brand": N.slug(brand), "product": N.slug(product),
         "angle": N.slug(angle), "avatar": avatar, "topics": topics,
         "awareness": awareness, "promo": promo, "ad_format": ad_format, "language_problems": lang_problems,
         "status": "draft", "version": (old or {}).get("version", 0) + 1,
         "written_at": datetime.now().isoformat(timespec="seconds"), "model": model,
         "prompt": str(PROMPT.relative_to(WS)), **got,
         "rows": {k: v for k, v in row_texts(cited).items() if k in set(got.get("rows_used") or [])}}
    s["checks"] = check(s, rows_all=row_texts(cited))
    p = save(s)
    print(f"wrote {s['id']} v{s['version']} (draft) → {p.relative_to(WS)}")
    return s


# ---------- check ----------

def words(t):
    return len(re.findall(r"[A-Za-z0-9$%'’.-]+", (t or "").replace("{offer}", "").replace("{click}", "")))


def check(s, rows_all=None):
    """Every rule the prompt sets that a machine can test. [] when it passes."""
    import quality_checks as Q
    probs = []
    have = {p.get("format"): p.get("text", "") for p in s.get("primary") or []}
    offer_ok = bool(s.get("promo")) or not bars_price(s.get("awareness"))
    for f, (lo, hi) in FORMATS.items():
        t = have.get(f)
        if t is None:
            probs.append(f"{f}: missing")
            continue
        if not t.strip():
            if f != "proof":
                probs.append(f"{f}: empty")
            continue
        n = words(t)
        if not lo <= n <= hi:
            probs.append(f"{f}: {n} words (wants {lo}–{hi})")
        if offer_ok and "{offer}" not in t:
            probs.append(f"{f}: no {{offer}} line")
        if not offer_ok and "{offer}" in t:
            probs.append(f"{f}: carries {{offer}} at awareness `{s.get('awareness')}`, whose doctrine entry bars price")
        if not t.rstrip().endswith("{click}"):
            probs.append(f"{f}: the last line is not {{click}}")
    every = [p.get("text", "") for p in s.get("primary") or []] + list(s.get("headlines") or []) + \
        list(s.get("descriptions") or []) + [s.get("offer_line", "")] + list((s.get("click") or {}).values())
    for t in every:
        if ORGANIC.search(t or ""):
            probs.append(f"organic ask: \"{ORGANIC.search(t).group(0)}\"")
    for h in s.get("headlines") or []:
        if len(h) > HEADLINE_MAX:
            probs.append(f"headline over {HEADLINE_MAX} characters: \"{h}\"")
    for d in s.get("descriptions") or []:
        if len(d) > DESCRIPTION_MAX:
            probs.append(f"description over {DESCRIPTION_MAX} characters: \"{d}\"")
    if len(s.get("headlines") or []) < 1:
        probs.append("no headline")
    for k in ("quiz", "product"):
        if not (s.get("click") or {}).get(k):
            probs.append(f"no click line for a {k} page")
    if offer_ok and not s.get("offer_line"):
        probs.append("no offer line")
    probs += offer_problems(s.get("headlines"), s.get("descriptions"), bool(s.get("promo")),
                            bodies=list(have.values()), level=s.get("awareness"))
    _, bank = offer_text(s["brand"], s["product"])
    said = " ".join("$" + f"{float(p):.2f}" for p in sorted(Q.prices_in(" ".join(every))))
    live = " ".join("$" + f"{float(p):.2f}" for p in sorted(Q.prices_in(bank)))
    probs += Q.price_check(said, live)
    # a quote in the proof body must be a customer's sentence, word for word
    rows = rows_all or s.get("rows") or {}
    norm = lambda x: re.sub(r"\s+", " ", x).strip().lower()
    for q in re.findall(r"[\"“]([^\"”]{12,})[\"”]", have.get("proof") or ""):
        if not any(norm(q) in norm(v) for v in rows.values()):
            probs.append(f"proof quote not found in the market's rows: \"{q[:60]}\"")
    for rid in s.get("rows_used") or []:
        if rows and rid not in rows:
            probs.append(f"cites a row it wasn't given: {rid}")
    return probs


# ---------- use ----------

def page_kind(page_type=None, link_id=None):
    """quiz or product — from the brief's landing page type (page_pick), else its link id."""
    k = f"{page_type or ''} {link_id or ''}"
    return "quiz" if ("quiz" in k or "portal" in k) else "product"     # a portal is a quiz-shaped page


def fill(s, link_id=None, page_type=None):
    """The words a card shows: {primary, headlines, descriptions}, tokens filled for this page."""
    click = (s.get("click") or {}).get(page_kind(page_type, link_id)) or ""
    def f(t):
        return t.replace("{offer}", s.get("offer_line", "")).replace("{click}", click).strip()
    return {"primary": [f(p["text"]) for p in s.get("primary") or [] if (p.get("text") or "").strip()],
            "headlines": list(s.get("headlines") or []),
            "descriptions": list(s.get("descriptions") or [])}


def approve(brand, product, angle, by):
    s = load(brand, product, angle)
    if not s:
        sys.exit("no set to approve")
    if s.get("checks"):
        sys.exit("the set fails its checks; fix them first:\n  " + "\n  ".join(s["checks"]))
    s.update(status="approved", approved_by=by, approved_at=datetime.now().isoformat(timespec="seconds"))
    save(s)
    print(f"approved {s['id']} v{s['version']} by {by}")


def all_sets(brand=None, ws=WS):
    base = Path(ws) / "runs" / "copywriter"
    globs = [base / N.slug(brand)] if brand else sorted(p for p in base.iterdir() if p.is_dir())
    return [json.loads(p.read_text()) for b in globs for p in sorted((b / "copy-sets").glob("*.json"))]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["write", "check", "show", "approve", "list"])
    ap.add_argument("--brand")
    ap.add_argument("--product")
    ap.add_argument("--angle")
    ap.add_argument("--angle-text")
    ap.add_argument("--avatar")
    ap.add_argument("--topics")
    ap.add_argument("--page")
    ap.add_argument("--by")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prompt-out", help="also save the prompt as sent")
    ap.add_argument("--awareness", help="the ad's awareness level, a doctrine id (e.g. unaware)")
    ap.add_argument("--promo", dest="promo", action="store_true", default=None, help="a promotion / value ad")
    ap.add_argument("--not-promo", dest="promo", action="store_false", help="not a promotion (overrides the angle row)")
    ap.add_argument("--ad-format", help="the ad format id from the element library (e.g. song-ad)")
    ap.add_argument("--answer", help="a file holding the writer's reply, instead of calling the model")
    a = ap.parse_args()
    if a.cmd == "list":
        for s in all_sets(a.brand):
            print(f"{s['id']:<55} v{s['version']} {s['status']:<9} {len(s.get('checks') or [])} problem(s)")
        return
    if a.cmd == "write":
        write(a.brand, a.product, a.angle, avatar=a.avatar, topics=a.topics, angle_given=a.angle_text,
              model=a.model, dry_run=a.dry_run, answer=a.answer, prompt_out=a.prompt_out,
              awareness=a.awareness, promo=a.promo, ad_format=a.ad_format)
        return
    s = load(a.brand, a.product, a.angle) or sys.exit("no set")
    if a.cmd == "check":
        s["checks"] = check(s)
        save(s)
        print("\n".join(s["checks"]) or "passes")
    elif a.cmd == "show":
        print(json.dumps(fill(s, a.page), indent=1, ensure_ascii=False))
    elif a.cmd == "approve":
        approve(a.brand, a.product, a.angle, a.by or sys.exit("--by"))


if __name__ == "__main__":
    main()
