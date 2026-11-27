#!/usr/bin/env python3
"""static_plan — the static side of the winner variation workflow: one winning image ad in, one-change rows out.

    static_plan.py --brand <b> --winner-run <image-teardown run on the picture as it ran> --label <name>
                   [--ad "<Meta ad name>"] [--statics <runs/winners/<b>/statics/<date>/statics.json>]
                   [--set <filed 3D set>] [--ask <ask.json>] [--rows 6] [--dry-run]

Ruled 2026-11-23: the winner variation workflow existed for video only, so winning statics went down the new-ad path
and came back reinvented. This is the image side of the same process, going deeper into what already won:

  read    the winner as it ran: a records-only image-teardown run on its live picture (stages 1 and 2: every element,
          zone and word, measured off the picture), its numbers from the winners statics list, its 3D set's record
  plan    locks (what carries the point) and levers (what can move), then N rows, each ONE lever: a copy row changes
          one word zone in the winner's own format and leaves the picture; a picture row changes one element in the
          same setting and leaves every word (prompts/stage-static-plan/)
  check   no model: one change per row, the winner's words kept on picture rows, only the lever zone changed on copy
          rows, every zone present, no word the order bans, no price the offer bank does not sell; sent back once
  hand    variations.json in image-writing's row shape (id, label, words, picture, swap), the shape image-edit's
          `vary.py --from-brief` and its set route already read

Plans only: the one model call is the planning stage. Writes runs/ad-variations/<brand>/<label>/: winner.json,
plan--sent.md, plan--answer-N.md, variation-plan.json, variations.json, VARIATIONS.md.
"""
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
REPO = COMP.parents[1]
sys.path.append(str(HERE))
sys.path.append(str(REPO / "components" / "run-kit"))
RUNS = REPO / "runs"                         # tests point this at a temp folder
MODEL = "claude-opus-5-5"                    # the planning stage: the designs tier
# v2 (2026-11-24): a picture lever the feed cannot see is not a variation
TOO_SMALL = re.compile(r"\b(light(ing)?|downlight|steam|haze|grade|grading|exposure|brightness|contrast|tilt|crop|"
                       r"camera distance|scale|hero size|condensation|vignette)\b", re.I)
PRICE = re.compile(r"\$\s?\d[\d,]*(?:\.\d\d)?")


def prompt_file():
    files = sorted((COMP / "prompts" / "stage-static-plan").glob("stage-static-plan-v*-owner.md"),
                   key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    if not files:
        sys.exit("no static plan prompt")
    return files[-1]


def body(p):
    t = Path(p).read_text()
    return t.split("\n---\n", 1)[1].strip() if "\n---\n" in t else t


def fill(t, **kw):
    for k, v in kw.items():
        t = t.replace("{" + k + "}", str(v))
    return t


def read(p, limit=None):
    p = Path(p)
    if not p.is_file():
        return None
    t = p.read_text()
    return t[:limit] if limit else t


def strip_comment(t):
    return re.sub(r"^<!--.*?-->\s*", "", t or "", flags=re.S)


def winner_sheet(brand, run, ad=None, statics=None, set_name=None, ask=None):
    """Everything the plan reads, from files the chain already wrote."""
    rd = RUNS / "image-teardown" / brand / run
    if not rd.is_dir():
        sys.exit(f"no run {run}: open one on the winner's live picture (image-teardown chain.py open) and run its records")
    teardown = strip_comment(read(rd / "out" / "01-teardown.md"))
    copy = strip_comment(read(rd / "out" / "02-replication-spec.md"))
    if not teardown or not copy:
        sys.exit(f"{run} has no teardown records yet (stages 1 and 2)")
    numbers = "not on the list"
    if statics and ad:
        rows = json.loads(Path(statics).read_text()).get("winners") or []
        r = next((x for x in rows if x.get("ad_name") == ad), None)
        if r:
            numbers = (f"{r['ad_name']}: ${r['spend']:,.0f} spent, {r['purchases']:g} sales, ROAS {r['roas']}, CPA {r['cpa']}, "
                       f"{r['first']} to {r['last']}, {r['status']}")
    set_text = "none (no 3D set on record)"
    if set_name:
        sj = RUNS / "image-production" / brand / "sets" / set_name / "set.json"
        if sj.is_file():
            s = json.loads(sj.read_text())
            kept = [p for p in s.get("prints") or [] if str(p.get("note", "")).startswith("kept")]
            set_text = json.dumps({"set": set_name, "signage": s.get("signage"), "camera": s.get("camera"),
                                   "light": s.get("light"), "kept": [p.get("note") for p in kept][-1:]}, indent=1)
    ask_text, never, avatar, product = "none: a variation round with no moment or offer change", [], None, None
    if ask:
        a = json.loads(Path(ask).read_text())
        never = list((a.get("offer") or {}).get("never") or [])
        ask_text = json.dumps({"ask": a.get("ask"), "avatar": a.get("avatar"), "product": a.get("product"),
                               "moment": a.get("moment"), "offer": a.get("offer"), "funnel": a.get("funnel"),
                               "already_made": a.get("already_made") or [], "limits": a.get("limits") or []}, indent=1)
        avatar, product = a.get("avatar"), a.get("product")
    who, aim = who_for(brand, rd, avatar, json.loads(Path(ask).read_text()) if ask else {})
    return {"who": who, "aim": aim, "brand": brand, "run": run, "ad": ad, "numbers": numbers, "teardown": teardown, "copy": copy,
            "set": set_text, "set_name": set_name, "ask": ask_text, "never": never,
            "language": language(rd, avatar), "product": product_rules(brand, product)}


def who_for(brand, rd, avatar=None, rec=None):
    """(who.block's text, who.stamp's answer) for the order and the parent run: the order's own avatar, sub-avatar and
    decisions first, then the run's `aim`, its sub_avatar and the level its winner already speaks at."""
    import brandctx as BC
    try:
        rj = json.loads((Path(rd) / "run.json").read_text())
    except (OSError, ValueError):
        rj = {}
    sub, demo, what = BC.aim_of(rec)
    r_sub, r_demo, r_what = BC.aim_of(rj)
    head = re.search(r"The avatar:\s*([\w-]+)(?:\s*→\s*sub-avatar\s*([\w-]+))?", read(Path(rd) / "vars" / "avatar.md", 300) or "")
    mine = (rj.get("aim") or {}).get("avatar") or rj.get("avatar") or (head.group(1) if head else None)
    avatar = avatar or mine
    if avatar == mine:                                   # the run's own decisions hold only for its own avatar
        sub = sub or r_sub or (read(Path(rd) / "vars" / "sub_avatar.md") or "").strip() or (head.group(2) if head else None)
        demo, what = demo or r_demo, dict(r_what, **what)
    if not what.get("awareness"):
        m = re.search(r"market state.*?\b(%s)\b" % "|".join(BC.LEVELS), (read(Path(rd) / "out" / "01-teardown.md") or "").lower(), re.S)
        what["awareness"] = m.group(1) if m else None
    what["product"] = rec.get("product") or rj.get("product")
    what["creative"] = True
    args = BC.who_args(brand, avatar, sub, demo, what)
    return (BC.who_text(args), BC.who().stamp(*args)) if args else ("", {})


def language(rd, avatar):
    """The run's own customer-language pull, only when it is this avatar's."""
    t = read(Path(rd) / "out" / ".language-injection.md")
    if t and (not avatar or f" for {avatar}," in t[:400]):
        return t
    return "none on file for this avatar on this run: keep to the winner's own wording and the offer"


def product_rules(brand, product):
    """How the product rests, is held and must never be shown, off its kit."""
    for k in sorted((RUNS / "ai-elements" / brand / "products").glob("*/kit.json")):
        d = json.loads(k.read_text())
        if product and (product in (d.get("aliases") or []) or product in (k.parent.name, d.get("product"))
                        or k.parent.name.startswith(product + "-")):
            b = d.get("behaviour") or {}
            return json.dumps({"cannot": b.get("cannot"), "rests": [x.get("how") for x in b.get("rests") or []],
                               "held": b.get("held"), "in_use": b.get("in_use"), "never_show": b.get("never_show")}, indent=1)
    return "none on file"


def offer_prices(brand):
    t = read(REPO / "brands" / brand / "products" / "offer-bank.md") or ""
    return {p.replace(" ", "") for p in PRICE.findall(t)}


def check(plan, *, never=(), prices=None, n_rows=6):
    """Every problem, plainly. The rows unchanged. No model."""
    probs = []
    rows = plan.get("rows") or []
    if len(rows) < n_rows:
        probs.append(f"{len(rows)} rows, {n_rows} were asked")
    base = None
    pic = [r for r in rows if r.get("kind") == "picture"]
    if (plan.get("control") or {}).get("words"):
        base = plan["control"]["words"]
    if pic:
        base = base or pic[0].get("words")
        for r in pic:
            if r.get("words") != base:
                probs.append(f"{r.get('id')}: a picture row whose words differ from the other picture rows (the winner's words stay)")
    zones = len(base) if base else None
    kinds = {r.get("kind") for r in rows}
    if len(rows) >= 4 and not ({"picture", "copy"} <= kinds):
        probs.append("rows of only one kind: at least two picture rows and two copy rows")
    for r in rows:
        rid = r.get("id")
        words = r.get("words") or []
        if r.get("kind") not in ("picture", "copy"):
            probs.append(f"{rid}: kind must be picture or copy")
        if r.get("kind") == "picture" and not (r.get("picture") or "").strip():
            probs.append(f"{rid}: a picture row with no picture change")
        if r.get("kind") == "picture" and TOO_SMALL.search(r.get("lever") or ""):
            probs.append(f"{rid}: the lever ({r.get('lever')}) is too small to see at feed size")
        if r.get("kind") == "copy":
            if (r.get("picture") or "").strip():
                probs.append(f"{rid}: a copy row that also changes the picture (two changes)")
            if base is not None:
                if len(words) != zones:
                    probs.append(f"{rid}: {len(words)} word zones, the winner has {zones}")
                else:
                    changed = [i for i, (a, b) in enumerate(zip(words, base)) if a.strip() != b.strip()]
                    if len(changed) != 1:
                        probs.append(f"{rid}: changes {len(changed)} word zones; a copy row changes exactly one")
        text = " ".join(words).lower()
        for n in never:
            if n and n.lower() in text:
                probs.append(f"{rid}: carries a banned line ({n})")
        if prices is not None:
            for p in PRICE.findall(" ".join(words)):
                if p.replace(" ", "") not in prices:
                    probs.append(f"{rid}: {p} is not a price the offer bank sells")
    return probs


def to_rows(plan):
    """image-writing's variation row shape, the one image-edit's vary --from-brief and its set route read."""
    out = []
    c = plan.get("control") or {}
    if c.get("words"):
        out.append({"id": "control", "label": "The winner, dressed for this round", "words": [" / ".join(c["words"])],
                    "picture": c.get("picture") or "", "swap": [], "lever": "control", "kind": "control", "zone": "",
                    "why": "", "status": "draft"})
    for r in plan.get("rows") or []:
        out.append({"id": r.get("id"), "label": f"{r.get('label')} · {r.get('kind')} lever: {r.get('lever')}",
                    "words": [" / ".join(r.get("words") or [])], "picture": r.get("picture") or "",
                    "swap": [], "lever": r.get("lever"), "kind": r.get("kind"), "zone": r.get("zone") or "",
                    "why": r.get("why") or "", "status": "draft"})
    return out


def parse_json(out):
    m = re.search(r"```json\s*(.*?)```", out, re.S)
    raw = m.group(1) if m else out
    return json.loads(raw[raw.find("{"):])


def ask_model(text):
    from run_kit import claude_door
    r = claude_door.run(["--model", MODEL, "--output-format", "text"],
                        text + "\n\nReturn only the deliverable. No tools, no preamble.", timeout=None, cwd=str(COMP))
    if r.returncode or not r.stdout.strip():
        sys.exit("the planner failed: " + (r.stderr or r.stdout or "")[:300])
    return r.stdout.strip()


def plan(brand, run, label, ad=None, statics=None, set_name=None, ask=None, n_rows=6, dry_run=False, ask_fn=None, say=print):
    sheet = winner_sheet(brand, run, ad, statics, set_name, ask)
    sys.path.append(str(HERE))
    import brandctx as BC
    rules = BC.BrandContext(REPO, brand).rules()
    p = prompt_file()
    base = fill(body(p), numbers=sheet["numbers"], teardown=sheet["teardown"], copy=sheet["copy"], set=sheet["set"],
                ask=sheet["ask"], rules=rules, n_rows=n_rows, language=sheet["language"], product=sheet["product"])
    if sheet["who"]:
        base += "\n\n---\n\n" + sheet["who"]
    say(f"static plan: {run} · {len(base):,} characters · {p.name} → runs/ad-variations/{brand}/{label}")
    if dry_run:
        return {"chars": len(base), "prompt": p.name}
    d = RUNS / "ad-variations" / brand / label
    d.mkdir(parents=True, exist_ok=True)
    (d / "winner.json").write_text(json.dumps({k: v for k, v in sheet.items() if k not in ("teardown", "copy", "language", "product", "who")}, indent=1))
    ask_fn = ask_fn or ask_model
    prices = offer_prices(brand)
    result, probs = None, []
    for attempt in (1, 2):
        sent = base if attempt == 1 else (base + "\n\n## What broke last time — fix every one, keep what was fine\n\n" +
                                          "\n".join("- " + x for x in probs) + "\n\nYour last answer:\n```json\n" +
                                          json.dumps(result, indent=1) + "\n```")
        (d / f"plan--sent-{attempt}.md").write_text(sent)
        out = ask_fn(sent)
        (d / f"plan--answer-{attempt}.md").write_text(out)
        try:
            result = parse_json(out)
        except (ValueError, json.JSONDecodeError) as e:
            probs = [f"the answer was not readable json: {e}"]
            continue
        probs = check(result, never=sheet["never"], prices=prices, n_rows=n_rows)
        if not probs:
            break
    result = result or {}
    bad = {re.match(r"(\S+?):", x).group(1) for x in probs if re.match(r"(\S+?):", x)}
    kept = dict(result, rows=[r for r in result.get("rows") or [] if r.get("id") not in bad])
    doc = {"tool": "static_plan", "at": datetime.now().isoformat(timespec="seconds"), "brand": brand, "winner_run": run,
           "ad": ad, "set": set_name, "ask": str(ask) if ask else None, "aim": sheet["aim"], "prompt": p.name, "model": MODEL,
           "control": kept.get("control") or {}, "locks": kept.get("locks") or [], "levers": kept.get("levers") or [], "rows": kept.get("rows") or [],
           "dropped": sorted(bad), "open": probs, "status": "draft"}
    (d / "variation-plan.json").write_text(json.dumps(doc, indent=1))
    (d / "variations.json").write_text(json.dumps({"source": "static_plan", "from": "variation-plan.json",
                                                   "winner_run": run, "variations": to_rows(kept)}, indent=1))
    (d / "VARIATIONS.md").write_text(md(doc))
    say(f"  {len(doc['rows'])} rows · {len(doc['locks'])} locks · {len(doc['levers'])} levers" +
        (f" · dropped {', '.join(doc['dropped'])}" if doc["dropped"] else "") + f" → {d}")
    return doc


def md(doc):
    out = [f"# Winner variations · {doc['winner_run']}", "", f"Ad: {doc.get('ad') or '—'} · 3D set: {doc.get('set') or '—'}", "",
           "## Locks", ""] + [f"- **{x.get('element')}** — {x.get('why')}" for x in doc["locks"]]
    out += ["", "## Levers", ""] + [f"{x.get('rank')}. **{x.get('element')}** ({x.get('kind')}) — {x.get('why')}" for x in doc["levers"]]
    c = doc.get("control") or {}
    if c:
        out += ["", "## Control (the winner, dressed for this round)", "", f"Words: {' / '.join(c.get('words') or [])}", "",
                f"Picture: {c.get('picture') or 'as it ran'}"]
    out += ["", "## Rows (one change each)", "", "| id | kind | lever | words | picture change | tests |", "|---|---|---|---|---|---|"]
    for r in doc["rows"]:
        out.append(f"| {r.get('id')} | {r.get('kind')} | {r.get('lever')} | {' / '.join(r.get('words') or [])} | {r.get('picture') or '—'} | {r.get('why')} |")
    if doc["open"]:
        out += ["", "## Dropped or open", ""] + ["- " + x for x in doc["open"]]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True); ap.add_argument("--winner-run", required=True); ap.add_argument("--label", required=True)
    ap.add_argument("--ad"); ap.add_argument("--statics"); ap.add_argument("--set"); ap.add_argument("--ask")
    ap.add_argument("--rows", type=int, default=6); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    plan(a.brand, a.winner_run, a.label, a.ad, a.statics, a.set, a.ask, a.rows, a.dry_run)


if __name__ == "__main__":
    main()
