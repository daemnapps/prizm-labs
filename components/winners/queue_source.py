#!/usr/bin/env python3
"""winners as a queue source: what the results say to make next, one observation.

    queue_source.py [--brand <b> ...] [--root <queue root>] [--repo REPO] [--now <UTC>] [--dry-run]

Results reach the queue here. Every bank row that is a winner (its newest numbers clear its bar) becomes one piece:
iterate on it. A brand whose bar is open has no winner, so it adds nothing; the bar is the brand owner's
(`winners.py bar`). Read-only on its inputs, offline:
  runs/winners/<brand>/bank.json                       the winners, their numbers, the bar
  runs/ad-variations/<brand>/*/next-ask.json            the variation plan of a winner and its next ask, when there
                                                        is one (components/ad-variations/machine/next_ask.py)

Writes, through creative-queue's public surface only:
  <root>/observations/winners.json      qcore.write_observation; root default runs/queue-shadow/ (the live
                                        runs/queue/ is refused by qcore.check_root while the live switch is off)

Each entry is one piece: id `<brand>_idea_<product>_iterate_<winner>`, lane `iteration`, the winner's bank row id, its
numbers and window, the bar it cleared, its variation plan and next ask when on file, and the plain next step.
Nothing here ranks iteration against new tests, runs a paid or outbound step, or writes a decision: people's
decisions in the queue override every field.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))         # appended, never ahead of this component
sys.path.append(str(HERE.parent / "creative-queue"))
from run_kit import paths  # noqa: E402
import bank as B  # noqa: E402
import qcore  # noqa: E402

SOURCE = "winners"
TYPES = {"video": "video-ad", "image": "image-ad"}
ROLES = {"video-ad": "video editor", "image-ad": "designer"}
BAR_WORDS = (("min_spend", "spend of at least ${:,.0f}"), ("max_cpa", "${:,.0f} a purchase or less"),
             ("min_roas", "ROAS {:.2f} or more"), ("min_purchases", "at least {:g} purchases"))


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def bar_of(bank, row):
    """The bar this row is judged on (the bank's own rule when it has one for the row, else the bank's bar)."""
    pick = getattr(B, "bar_for", None)
    return (pick(bank, row) if pick else bank.get("bar")) or {}


def bar_words(bar):
    return ", ".join(text.format(bar[k]) for k, text in BAR_WORDS if bar.get(k) is not None) or "open"


def plans(repo, brand):
    """{winner row id or teardown run label: pointer} for every variation plan of the brand with a next-ask record."""
    out = {}
    home = Path(repo) / "runs" / "ad-variations" / brand
    for f in sorted(home.glob("*/next-ask.json")) if home.is_dir() else []:
        ptr = _json(f)
        plan = _json(f.parent / "variation-plan.json")
        run = ((plan or {}).get("source") or {}).get("teardown_run") if isinstance(plan, dict) else None
        if isinstance(ptr, dict) and ptr.get("winner"):
            out[ptr["winner"]] = ptr
        if isinstance(ptr, dict) and run:
            out[Path(str(run)).name] = ptr
    return out


def product_of(brand, row):
    key = str(row.get("brief_key") or "")
    parts = key.split("_")
    return parts[1] if len(parts) >= 3 and parts[0] == brand and parts[1] != "none" else None


def pieces(repo, brand):
    """([piece], note) for one brand: its winners, top by purchases first."""
    bank = _json(B.bank_path(repo, brand))
    if not isinstance(bank, dict) or not isinstance(bank.get("rows"), list):
        return [], "no bank"
    by_run = plans(repo, brand)
    out = []
    for row in bank["rows"]:
        snaps = row.get("snapshots") or []
        if row.get("state") != "winner" or not snaps:
            continue
        sn = snaps[-1]
        kind = "video" if row.get("trybe_id") else str(row.get("format") or "").lower()
        typ = TYPES.get(kind)
        product = product_of(brand, row)
        tail = row["id"][len(brand) + 1:] if row["id"].startswith(brand + "-") else row["id"]
        ptr = by_run.get(row["id"]) or (by_run.get(Path(str(row["run"])).name) if row.get("run") else None)
        nxt = (ptr or {}).get("next") or {}
        if nxt.get("ask"):
            step = "the next ask is on file: variation %s" % nxt.get("id")
        elif ptr:
            step = "its plan has no variation left to ask: %d asked, %d held" % (len(ptr.get("asked") or []),
                                                                                  len(ptr.get("held") or []))
        else:
            step = "no variation plan yet: plan its variations, then file the next ask"
        bar = bar_of(bank, row)
        out.append({
            "id": "%s_idea_%s_iterate_%s" % (brand, product or "brand", tail),
            "lane": "iteration", "brand": brand, "product": product, "type": typ,
            "title": "Iterate · %s · %s" % (row.get("name") or row["id"], brand),
            "winner": row["id"],
            "numbers": {k: sn.get(k) for k in ("purchases", "spend", "cpa", "roas") if sn.get(k) is not None},
            "window": "%s to %s" % (sn.get("since"), sn.get("until")),
            "bar": bar_words(bar),
            "plan": (ptr or {}).get("plan"), "variation": nxt.get("id"), "ask": nxt.get("ask"),
            "next_step": step,
            "role": "creator manager" if row.get("trybe_id") else ROLES.get(typ),
            "priority": "normal",
            "observed_stage": "brief" if nxt.get("ask") else "idea",
        })
    out.sort(key=lambda p: (-(p["numbers"].get("purchases") or 0), p["id"]))
    for i, p in enumerate(out, 1):
        n = p["numbers"]
        p["rank"] = i
        p["why"] = ("winner in the bank: %s purchases, %s a purchase, ROAS %s, %s; it clears the bar (%s)" % (
            "{:,.0f}".format(n["purchases"]) if n.get("purchases") is not None else "—",
            "${:,.0f}".format(n["cpa"]) if n.get("cpa") is not None else "—",
            "{:.2f}".format(n["roas"]) if n.get("roas") is not None else "—", p["window"], p["bar"]))
    note = None if out else ("the bar is open, so no row is a winner" if B.bar_is_open(bank) else "no row clears the bar")
    return out, note


def entries(all_pieces):
    keep = ("lane", "brand", "product", "type", "title", "winner", "numbers", "window", "bar", "plan", "variation",
            "ask", "next_step", "role", "priority", "rank", "why", "observed_stage")
    return {p["id"]: {k: p[k] for k in keep if p.get(k) is not None} for p in all_pieces}


def build(repo, brands):
    got, notes = [], {}
    for b in brands:
        ps, note = pieces(repo, b)
        got += ps
        if note:
            notes[b] = note
    return got, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", action="append", help="default: every brand with a bank")
    ap.add_argument("--root", help="the queue root; default runs/queue-shadow/")
    ap.add_argument("--repo", help="the workspace; default is found upward")
    ap.add_argument("--now", help="the observation's UTC time, YYYY-MM-DDTHH:MM:SSZ; default is now")
    ap.add_argument("--dry-run", action="store_true", help="print the pieces; write nothing")
    a = ap.parse_args(argv)
    repo = Path(a.repo) if a.repo else paths.repo(__file__)
    try:
        root = qcore.check_root(a.root or qcore.shadow_root(repo), repo)
    except qcore.Refused as err:
        print(err, file=sys.stderr)
        return 2
    home = repo / "runs" / "winners"
    brands = a.brand or (sorted(p.name for p in home.iterdir() if (p / "bank.json").is_file()) if home.is_dir() else [])
    got, notes = build(repo, brands)
    for p in got[:12]:
        print("%3d  %-9s %-9s %s" % (p["rank"], p["brand"], p.get("type") or "-", p["title"]))
    for b, note in sorted(notes.items()):
        print("%s: nothing to queue (%s)" % (b, note))
    print("%d winners to iterate on, %d with a next ask on file" % (len(got), sum(1 for p in got if p.get("ask"))))
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    path = root / "observations" / (SOURCE + ".json")
    if not got and not path.is_file():
        print("no observation written: there is nothing to say yet")
        return 0
    wrote = qcore.write_observation(root, SOURCE, entries(got), now=a.now)
    print(("wrote %s" % B.rel(repo, wrote)) if wrote else "unchanged: the observation already says this")
    return 0


if __name__ == "__main__":
    sys.exit(main())
