#!/usr/bin/env python3
"""feed: write a brand's proven winning ads, with their numbers and words, for the writing prompts.

Normally driven by winners.py. Directly:
    feed.py --brand <brand> [--top 10] [--root REPO]
    feed.py --brand <brand> --window <since>_<until>     # prints another window; feed.md stays as it is

Read-only on its inputs. Offline. Stdlib only. Reads:
  runs/winners/<brand>/bank.json   the brand's bank
Writes:
  runs/winners/<brand>/feed.md     what the hook prompt's {winners} slot reads
Beside it, runs/winners/<brand>/taught.md: what the results taught (feed_sections.py): the top ad per angle with its
type, angle, concept and customer words; the desk's calls and where they differed from its suggestion; the send-back
reasons from the approval page; the score per prompt version. A file of its own, so the live hook prompt that reads
feed.md sees no change until a reviewed prompt asks for it.

Uses the bank's widest audit window (longest since-to-until; tie, the newest), so a shorter audit never replaces the
ranking. Winners: the top rows by purchases in that window, with their words; once a bar is set, only rows whose
numbers in that window clear it, and the file says so. The loser stays the contrast either way: the
row with the highest CPA among rows whose spend is above the window's median spend.
Creator videos (rows with a trybe id, banked by creators.py) get their own section after the loser, under the same
bar: once it is set, the ones that clear it; while it is open, the ones with at least one purchase. Each carries
its format, angle and hook from the per-video read. Ids are the bank's row ids. Exit 2 on bad input.
"""
import argparse, json, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402
import bank as B  # noqa: E402
import feed_sections as FS  # noqa: E402

DEFAULT_ROOT = paths.repo(__file__)


class BadInput(Exception):
    pass


def load_json(p):
    p = Path(p)
    if not p.is_file():
        raise BadInput(f"missing input file: {p}")
    try:
        return json.loads(p.read_text())
    except ValueError as e:
        raise BadInput(f"not valid JSON: {p} ({e})")


def rel(root, p):
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(p)


def money(x):
    return "—" if x is None else f"${x:,.0f}"


def num(x):
    return "—" if x is None else f"{x:,.0f}"


def roas(x):
    return "—" if x is None else f"{x:.2f}"


def clean(s):
    return " ".join(str(s).split()) if s else None


# ---------- source: the bank ----------

def pick_window(bank, label=None):
    """(since, until, pulled_at, audit) of the widest audit snapshot in the bank, or of the window named `label`."""
    best = None
    for r in bank["rows"]:
        for sn in r.get("snapshots") or []:
            if sn.get("kind") != "audit" or (label and f"{sn.get('since')}_{sn.get('until')}" != label):
                continue
            k = B.widest_key(sn)
            if best is None or k > best[0]:
                best = (k, sn)
    if not best:
        raise BadInput(f"the bank has no audit snapshot for window {label}" if label else "the bank has no audit snapshot")
    sn = best[1]
    return sn["since"], sn["until"], sn["pulled_at"], sn.get("audit")


def from_bank(root, brand, top, window=None):
    path = Path(root) / "runs/winners" / brand / "bank.json"
    bank = load_json(path)
    if not isinstance(bank, dict) or bank.get("brand") != brand or not isinstance(bank.get("rows"), list):
        raise BadInput(f"not a {brand} bank: {path}")
    since, until, pulled, audit = pick_window(bank, window)

    def snap(r):
        # by window, not by pull time: a second pull of one window adds rows without restamping the old ones
        for sn in r.get("snapshots") or []:
            if (sn.get("kind"), sn.get("since"), sn.get("until")) == ("audit", since, until):
                return sn
        return None

    rows = [(r, snap(r)) for r in bank["rows"]]
    rows = [(r, sn) for r, sn in rows if sn and sn.get("purchases") is not None]
    if not rows:
        raise BadInput(f"no rows with purchases in window {since} to {until}: {path}")

    def entry(r, sn):
        w = r.get("words") or {}
        src = r.get("source") or {}
        name = r.get("name") + (f" (headline \"{r['headline']}\")" if r.get("headline") else "")
        return {
            "id": r["id"], "name": name,
            "purchases": sn.get("purchases"), "spend": sn.get("spend"), "cpa": sn.get("cpa"), "roas": sn.get("roas"),
            "ran": f"{sn.get('first')} to {sn.get('last')}",
            "format": " · ".join(x for x in (r.get("format"), "Core" if r.get("core") else None) if x),
            "message_tag": None,
            "hook": clean(w.get("hook")), "core": clean(w.get("core_message")), "offer": clean(w.get("offer")),
            "missing": None if w.get("hook") else
            ("no teardown or registry words for this row yet" if not src.get("teardown") else "teardown has no hook"),
        }

    ranked = sorted(rows, key=lambda x: (-x[1]["purchases"], x[1].get("rank") or 0))
    bar = bank.get("bar") or {}
    open_bar = all(v is None for v in bar.values())
    listed = ranked if open_bar else [x for x in ranked if B.clears(bar, x[1])]
    winners = [entry(r, sn) for r, sn in listed[:top]]
    med = statistics.median(sn.get("spend") or 0 for _, sn in rows)
    above = [(r, sn) for r, sn in rows if (sn.get("spend") or 0) > med]
    pool = [x for x in above if x[1].get("cpa") is not None] or above
    pool.sort(key=lambda x: (-(x[1].get("cpa") if x[1].get("cpa") is not None else float("inf")),
                             x[1].get("roas") or 0))
    loser = None
    if pool:
        r, sn = pool[0]
        loser = entry(r, sn)
        loser["why"] = (f"highest CPA among the {len(above)} bank rows that spent more than the median "
                        f"({money(med)}) in this window; ROAS {roas(sn.get('roas'))}. These rows are the audit's "
                        "top creatives, so this is the weakest return among them, not a failed ad")
    head = {
        "source": f"`{rel(root, path)}` (audit `{audit}`, window {since} to {until}, pulled {pulled})",
        "asof": until,
        "spend_note": "Spend, CPA and ROAS are the audit's, summed over every copy of the ad in the window.",
        "caveats": ["Bar: OPEN (every bank row is a candidate; the brand owner sets min spend, max CPA, min ROAS)"
                    if open_bar else f"Bar: {json.dumps(bar)} (only rows that clear it are listed under Winners)"],
    }
    return head, winners, loser


# ---------- page ----------

def block(i, e, label):
    out = [f"### {label}{i} · `{e['id']}` · {e['name']}", ""]
    out.append(f"- Numbers: {num(e['purchases'])} purchases · spend {money(e['spend'])} · CPA {money(e['cpa'])}"
               f" · ROAS {roas(e['roas'])} · ran {e['ran']}")
    if e.get("format"):
        out.append(f"- Format: {e['format']}")
    if e.get("message_tag"):
        out.append(f"- Message tag: {e['message_tag']}")
    if e.get("hook") or e.get("core") or e.get("offer"):
        out.append(f"- Hook: {e['hook'] or 'not on file'}")
        out.append(f"- Core message: {e['core'] or 'not on file'}")
        out.append(f"- Offer: {e['offer'] or 'not on file'}")
    else:
        out.append(f"- Words: not on file ({e['missing']})")
    if e.get("why"):
        out.append(f"- Why it is the loser: {e['why']}")
    out.append("")
    return out


def render(brand, head, winners, loser, creators=None):
    if head is None:
        return "\n".join([f"# Winning ads — {brand}", "", "No audit in the bank yet; creator videos only.", ""]
                         + creator_block(creators)).rstrip() + "\n"
    out = [f"# Winning ads — {brand}", "",
           f"Source: {head['source']}",
           f"As of: {head['asof']}",
           f"Ranked by purchases, top {len(winners)}. {head['spend_note']} Numbers and words are the source's, "
           "quoted as written; the ids are the ones to cite in `borrowed_from`.", ""]
    for c in head["caveats"]:
        out.append(f"Caveat from the source: {c}")
    if head["caveats"]:
        out.append("")
    out += ["## Winners", ""]
    for i, e in enumerate(winners, 1):
        out += block(i, e, "W")
    if not winners:
        out += ["No row clears the bar.", ""]
    out += ["## Loser", ""]
    if loser:
        out += block(1, loser, "L")
    else:
        out += ["None in the data.", ""]
    out += creator_block(creators)
    return "\n".join(out).rstrip() + "\n"


# ---------- creator videos ----------

def creator_entries(bank, top):
    """(basis word, [entry]) for the creator videos in the bank, under the one bar (creators.basis)."""
    import creators as CR
    word, rows = CR.basis(bank)
    out = []
    for r, sn in rows[:top]:
        t = r.get("tags") or {}
        out.append({"id": r["id"], "trybe_id": r["trybe_id"], "creator": r.get("creator"),
                    "purchases": sn.get("purchases"), "spend": sn.get("spend"), "cpa": sn.get("cpa"),
                    "roas": sn.get("roas"), "ran": f"{sn.get('since')} to {sn.get('until')}",
                    "format": t.get("format"), "angle": t.get("angle"), "hook": t.get("hook_line"),
                    "worked": t.get("worked")})
    return word, out


def creator_block(creators):
    if not creators:
        return []
    word, rows = creators
    say = {"winners": "creator videos that clear the bar",
           "candidates": "the bar is open, so these are creator videos with at least one purchase",
           "none yet": "none clears the bar yet"}[word]
    out = ["## Creator videos", "", f"Basis: {word} ({say}). Numbers are the platform's, from the creator results "
           "pull; tags are the per-video read's.", ""]
    for i, e in enumerate(rows, 1):
        out += [f"### C{i} · `{e['id']}` · {e['creator']} · trybe {e['trybe_id']}", "",
                f"- Numbers: {num(e['purchases'])} purchases · spend {money(e['spend'])} · CPA {money(e['cpa'])}"
                f" · ROAS {roas(e['roas'])} · ran {e['ran']}",
                f"- Format: {e['format'] or 'not read yet'} · Angle: {e['angle'] or 'not read yet'}",
                f"- Hook: {clean(e['hook']) or 'not on file'}"]
        if e.get("worked"):
            out.append(f"- Why it worked (the read): {clean(e['worked'])}")
        out.append("")
    if not rows:
        out += ["None yet.", ""]
    return out


def write(root, brand, top=10):
    """Rebuilds feed.md. -> (path, how many winners, whether there is a loser)."""
    bank = load_json(Path(root) / "runs/winners" / brand / "bank.json")
    has_creators = any(r.get("trybe_id") for r in bank.get("rows") or [])
    try:
        head, winners, loser = from_bank(root, brand, top)
    except BadInput:
        if not has_creators:
            raise
        head, winners, loser = None, [], None
    creators = creator_entries(bank, top) if has_creators else None
    out = Path(root) / "runs/winners" / brand / "feed.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(brand, head, winners, loser, creators))
    FS.write(root, brand)
    return out, len(winners), bool(loser)


def peek(root, brand, window, top=10):
    """The page for another audit window, as text. Writes nothing."""
    return render(brand, *from_bank(root, brand, top, window))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--window", help="print this audit window instead; feed.md is not touched")
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    a = ap.parse_args(argv)
    if not 8 <= a.top <= 10:
        print("--top must be 8 to 10", file=sys.stderr)
        return 2
    root = Path(a.root)
    try:
        if a.window:
            sys.stdout.write(peek(root, a.brand, a.window, a.top))
            return 0
        out, n, loser = write(root, a.brand, a.top)
    except BadInput as e:
        print(f"bad input: {e}", file=sys.stderr)
        return 2
    print(f"{a.brand}: {n} winners, loser {'yes' if loser else 'none'} -> {rel(root, out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
