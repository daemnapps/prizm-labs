#!/usr/bin/env python3
"""winners: the one command for the five steps. Results, Audit, Bank, Feed, Score, per brand.

    python3 components/winners/winners.py audit  --brand <b> --since D --until D [--title T]
    python3 components/winners/winners.py tag    --brand <b> --window L --tags FILE
    python3 components/winners/winners.py videos --brand <b> --window L --top N
    python3 components/winners/winners.py mirror --brand <b> --window L
    python3 components/winners/winners.py bank   --brand <b> [--window L]
    python3 components/winners/winners.py feed   --brand <b> [--window L]
    python3 components/winners/winners.py score  --brand <b> [--days 90]
    python3 components/winners/winners.py creators --brand <b> [--days 90] [--results trybe.json]
    python3 components/winners/winners.py leaderboard --brand <b> [--no-pull]
    python3 components/winners/winners.py five   --brand <b>
    python3 components/winners/winners.py bar    --brand <b> [--min-spend N] [--max-cpa N] [--min-roas N] [--open]
                                                 [--creators [--min-purchases N]]
    python3 components/winners/winners.py status --brand <b>|all
    python3 components/winners/winners.py yoy    --brand <b> [--window L] [--from-month MM --to-month MM]
    python3 components/winners/winners.py store  --brand <b> [--weeks 12]
    python3 components/winners/winners.py messages --brand <b> status|next|check|page|start [run]
    python3 components/winners/winners.py shapes --brand <b> todo|check|build
    python3 components/winners/winners.py who    --brand <b> [--days N] [--source score|desk]
    python3 components/winners/winners.py system --brand <b>|all

Everything lands under runs/winners/<brand>/. A window is its folder under audit/, `<since>_<until>`.
Read only on every ad account. audit and videos read Meta; audit, score and store read the warehouse; the rest is offline.
Exit 2 with one plain sentence on bad input; exit 1 when a step stops part way.
"""
import argparse, datetime as dt, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
sys.path.append(str(HERE.parent / "brandpath"))
from run_kit import paths  # noqa: E402
import audit as A  # noqa: E402
import bank as B  # noqa: E402
import creators as CR  # noqa: E402
import leaderboard as LB  # noqa: E402
import messages as MG  # noqa: E402
import shapes as SH  # noqa: E402
import feed as F  # noqa: E402
import five as FV  # noqa: E402
import score as S  # noqa: E402
import winner_views as W  # noqa: E402
import statics as ST  # noqa: E402
import who_view as WV  # noqa: E402
import system as SY  # noqa: E402

BAD = (B.BadInput, F.BadInput, S.BadInput, W.BadInput, FV.BadInput, WV.BadInput)
AUDIT_STEPS = ("pull", "rank", "media", "dedupe", "sheets", "build")


class BadUse(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise BadUse(message[0].upper() + message[1:].rstrip(".") + ".")


# ---------- brands and windows ----------

def known_brands(root):
    """Brands are data: the folders under brands/ (through brandpath) and under runs/winners/."""
    import brandpath
    names = set()
    for d in (brandpath.brands_dir(Path(root) / "brands"), Path(root) / "runs" / "winners"):
        if d.is_dir():
            names |= {p.name for p in d.iterdir() if p.is_dir() and p.name[0] not in "._"}
    return names


def check_brand(root, brand):
    if brand not in known_brands(root):
        raise BadUse(f"There is no brand called {brand}.")


def audit_dir(root, brand):
    return B.brand_dir(root, brand) / "audit"


def windows(root, brand):
    """[(until, pulled_at, label, window.json)], oldest first."""
    out = []
    d = audit_dir(root, brand)
    for f in (sorted(d.glob("*/window.json")) if d.is_dir() else []):
        w = json.loads(f.read_text())
        out.append((str(w.get("until")), str(w.get("pulled_at")), f.parent.name, w))
    return sorted(out, key=lambda x: x[:3])


def pick_window(root, brand, label=None):
    """-> (label, window.json). No label means the newest."""
    ws = windows(root, brand)
    if label:
        for w in ws:
            if w[2] == label:
                return w[2], w[3]
        raise BadUse(f"{brand} has no audit window called {label}.")
    if not ws:
        raise BadUse(f"{brand} has no audit yet.")
    return ws[-1][2], ws[-1][3]


def step_args(brand, label, win, **more):
    return argparse.Namespace(brand=brand, label=label, since=win.get("since"), until=win.get("until"),
                              title=more.get("title"), top=more.get("top"), tags=more.get("tags"))


def date(s, what):
    try:
        return dt.date.fromisoformat(s).isoformat()
    except ValueError:
        raise BadUse(f"{what} has to be a date written YYYY-MM-DD, not {s}.")


# ---------- the shared tail: bank, then feed ----------

def do_bank(root, brand, label):
    bank = B.load_bank(B.bank_path(root, brand), brand)
    n = B.ingest_audit(root, bank, brand, audit_dir(root, brand) / label)
    _, changed = B.write(root, bank)
    print(f"bank: {n} rows from {label}; {len(bank['rows'])} in the bank{'' if changed else ' (unchanged)'}")


def do_feed(root, brand):
    _, n, loser = F.write(root, brand)
    print(f"feed: {n} winners, loser {'yes' if loser else 'none'}")


# ---------- verbs ----------

def v_audit(root, a):
    since, until = date(a.since, "--since"), date(a.until, "--until")
    if since > until:
        raise BadUse("--since has to come before --until.")
    label = f"{since}_{until}"
    args = argparse.Namespace(brand=a.brand, label=label, since=since, until=until, title=a.title, top=None, tags=None)
    for name in AUDIT_STEPS:
        getattr(A, name)(args)
        if name == "pull" and not A.load(A.run_dir(a.brand, label) / "cells.json"):
            raise BadUse(f"No {a.brand} ad spent from {since} to {until}.")
    left = A.missing_tags(args)
    if left:
        print(f"{left} creatives still need tags. Next step: tag --brand {a.brand} --window {label} --tags <file>.")
        return 0
    do_bank(root, a.brand, label)
    do_feed(root, a.brand)
    return 0


def v_tag(root, a):
    label, win = pick_window(root, a.brand, a.window)
    try:
        tags = json.loads(Path(a.tags).read_text())
    except OSError:
        raise BadUse(f"The tags file {a.tags} can't be read.")
    except ValueError:
        raise BadUse(f"The tags file {a.tags} isn't valid JSON.")
    if not isinstance(tags, dict) or not all(isinstance(v, dict) for v in tags.values()):
        raise BadUse(f"The tags file {a.tags} has to map each creative to its tags.")
    args = step_args(a.brand, label, win, tags=a.tags)
    A.remember(args)
    A.build(args)
    do_bank(root, a.brand, label)
    do_feed(root, a.brand)
    return 0


def v_videos(root, a):
    if a.top < 1:
        raise BadUse("--top has to be at least 1.")
    label, win = pick_window(root, a.brand, a.window)
    A.videos(step_args(a.brand, label, win, top=a.top))
    return 0


def v_mirror(root, a):
    # pictures and videos stay out of git; they go to Shared Assets runs/winners/<brand>/<window>/ (builder card, O8)
    from run_kit import station
    label, _ = pick_window(root, a.brand, a.window)
    d = root / "runs" / "winners" / a.brand / "audit" / label
    got = station.push(d, "winners", a.brand, label)
    print("mirror: %d files to %s" % (got["placed"], got["to"]) + ("".join("\n  " + n for n in got["notes"])))
    return 0 if got["placed"] else 1


def v_bank(root, a):
    label, _ = pick_window(root, a.brand, a.window)
    do_bank(root, a.brand, label)
    return 0


def v_feed(root, a):
    if a.window:
        label, _ = pick_window(root, a.brand, a.window)
        sys.stdout.write(F.peek(root, a.brand, label))
        return 0
    do_feed(root, a.brand)
    return 0


def v_score(root, a):
    if a.days < 1:
        raise BadUse("--days has to be at least 1.")
    res = S.results(root, a.brand, a.days)
    o = S.build(root, a.brand, res=res)
    d = S.write(root, o)
    c = o["counts"]
    print(f"score: {c['matched']} of {c['ads']} ads joined to a prompt, from {o['results_from']}")
    bank = B.load_bank(B.bank_path(root, a.brand), a.brand)
    n = B.ingest_score(root, bank, a.brand, d / "score.json")
    B.write(root, bank)
    print(f"bank: {n} chain-made ads; {len(bank['rows'])} in the bank")
    try:
        do_feed(root, a.brand)
    except F.BadInput as e:
        print(f"feed: not rebuilt ({e})")
    return 0


def v_creators(root, a):
    """Creator videos: results through funnel-tracking's trybe.py (its CLI), banked under the one bar,
    the feed rebuilt, brief-next written for the swipe pick."""
    if a.days < 1:
        raise BadUse("--days has to be at least 1.")
    if a.results:
        res = Path(a.results)
        if not res.is_absolute():
            res = Path(root) / res
    else:
        out = B.brand_dir(root, a.brand) / "creators" / dt.date.today().isoformat()
        import subprocess
        script = Path(root) / "components" / "funnel-tracking" / "machine" / "trybe.py"
        subprocess.run([sys.executable, str(script), "--brand", a.brand, "--days", str(a.days), "--out", str(out)],
                       check=True, timeout=600)
        res = out / "trybe.json"
    n, d = CR.run(root, a.brand, res)
    print(f"creators: {n} videos with spend banked from {B.rel(root, res)}")
    try:
        do_feed(root, a.brand)
    except F.BadInput as e:
        print(f"feed: not rebuilt ({e})")
    print(f"brief next: {d['basis']}; formats {', '.join(e['format'] for e in d['formats']) or 'none yet'}"
          f" -> {B.rel(root, B.brand_dir(root, a.brand) / 'brief-next.json')}")
    return 0


def v_leaderboard(root, a):
    """Pull what is free and not yet pulled today (each campaign's report, Trybe since the program began and
    for the last 7 days), then rebuild the leaderboard. --no-pull builds from the files already there."""
    import subprocess
    today = dt.date.today().isoformat()
    home = B.brand_dir(root, a.brand)
    if not a.no_pull:
        camps, _ = LB.campaigns(root, a.brand)
        script = Path(root) / "components" / "swipe-organic" / "content_rewards.py"
        for c in camps:
            if c.get("link") and not (Path(root) / "runs/content-rewards" / a.brand / c["pool"] / today / "clips.json").is_file():
                subprocess.run([sys.executable, str(script), c["link"], "--brand", a.brand, "--pool", c["pool"], "--no-media"],
                               check=True, timeout=600)
        if not (home / "creators" / today / "trybe.json").is_file():
            v_creators(root, argparse.Namespace(brand=a.brand, days=90, results=None))
        week = home / "creators" / today / "week"
        if not (week / "trybe.json").is_file():
            subprocess.run([sys.executable, str(Path(root) / "components/funnel-tracking/machine/trybe.py"),
                            "--brand", a.brand, "--days", "7", "--out", str(week)], check=True, timeout=600)
    out, d = LB.write(root, a.brand)
    t = d["totals"]["all_time"]
    print(f"leaderboard: {d['totals']['people']} people · {t['views']:,} views · ${t['paid']:,.2f} paid "
          f"-> {B.rel(root, out)}")
    return 0


def v_five(root, a):
    p, d = FV.write(root, a.brand)
    print("five %s: %d of %d proven ads%s" % (a.brand, len(d["five"]), d["proven"], (" — " + d["short"]) if d["short"] else ""))
    for e in d["five"]:
        n = e["numbers"]
        print("  %d. %s · %s × %s · %s purchases · ROAS %s" % (e["rank"], e.get("name"), e.get("format"), e.get("angle"),
                                                              n.get("purchases"), n.get("roas")))
    print("  ->", p.relative_to(root))
    return 0


def v_statics(root, a):
    p, d = ST.write(root, a.brand, a.days, a.min_spend, a.min_roas)
    print("statics %s: %d winning image ads (last %d days, spend >= $%g)" % (a.brand, len(d["winners"]), a.days, a.min_spend))
    for i, r in enumerate(d["winners"][:12], 1):
        print("  %d. %s · %g sales · ROAS %s · %s · %s" % (i, r["ad_name"][:60], r["purchases"], r["roas"], r["brief"] or "-", r["state"]))
    print("  ->", p.relative_to(root))
    return 0


def bar_words(bar):
    parts = []
    if bar.get("min_spend") is not None:
        parts.append(f"at least ${bar['min_spend']:,.0f} spent")
    if bar.get("max_cpa") is not None:
        parts.append(f"${bar['max_cpa']:,.0f} a purchase or less")
    if bar.get("min_roas") is not None:
        parts.append(f"ROAS {bar['min_roas']:.2f} or more")
    if bar.get("min_purchases") is not None:
        parts.append(f"at least {bar['min_purchases']:g} purchase(s)")
    return ", ".join(parts) or "open"


def v_bar(root, a):
    if not B.bank_path(root, a.brand).is_file():
        raise BadUse(f"{a.brand} has no bank yet.")
    bank = B.load_bank(B.bank_path(root, a.brand), a.brand)
    given = {"min_spend": a.min_spend, "max_cpa": a.max_cpa, "min_roas": a.min_roas}
    if a.creators:
        given["min_purchases"] = a.min_purchases
    elif a.min_purchases is not None:
        raise BadUse("--min-purchases is for the creator bar; add --creators.")
    if any(v is not None and v < 0 for v in given.values()):
        raise BadUse("A bar value can't be negative.")
    key = "creator_bar" if a.creators else "bar"
    if not a.open and all(v is None for v in given.values()):
        print(f"{a.brand} bar: {bar_words(bank['bar'])}")
        print(f"{a.brand} creator bar: {bar_words(bank['creator_bar']) if bank.get('creator_bar') else 'the bar above'}")
        return 0
    if a.open or not bank.get(key):
        bank[key] = {k: None for k in given}
    bank[key].update({k: v for k, v in given.items() if v is not None})
    B.write(root, bank)
    won = sum(1 for r in bank["rows"] if r["state"] == "winner")
    print(f"{a.brand} {'creator bar' if a.creators else 'bar'}: {bar_words(bank[key])}; {won} winners, "
          f"{len(bank['rows']) - won} candidates")
    try:
        do_feed(root, a.brand)
    except F.BadInput as e:
        print(f"feed: not rebuilt ({e})")
    if any(r.get("trybe_id") for r in bank["rows"]):
        _, d = CR.write_brief_next(root, a.brand)
        print(f"brief next: {d['basis']}")
    return 0


def status_lines(root, brand):
    title = brand.upper()
    if not B.bank_path(root, brand).is_file():
        return [title, "  No bank yet."]
    bank = B.load_bank(B.bank_path(root, brand), brand)
    rows = bank["rows"]
    words = sum(1 for r in rows if any((r.get("words") or {}).values()))
    is_open = B.bar_is_open(bank)
    ws = windows(root, brand)
    window = "%s to %s" % (ws[-1][3].get("since"), ws[-1][3].get("until")) if ws else "none"
    sdir = B.brand_dir(root, brand) / "score"
    scores = sorted(p.name for p in sdir.iterdir() if (p / "score.json").is_file()) if sdir.is_dir() else []
    out = [title, f"  Bank rows {len(rows)} · Core {sum(1 for r in rows if r.get('core'))} · with words {words}",
           f"  Bar: {bar_words(bank['bar'])}",
           f"  Newest audit: {window} · Newest score: {scores[-1] if scores else 'none'}"]
    line = S.origin_line(json.loads((sdir / scores[-1] / "score.json").read_text())) if scores else None
    if line:
        out.append(f"  {line}")
    src = B.widest_audit_source(bank)
    scored = []
    for r in rows:
        if not is_open and r.get("state") != "winner":
            continue
        for sn in r.get("snapshots") or []:
            if src and sn.get("kind") == "audit" and (sn.get("since"), sn.get("until")) == (src["since"], src["until"]):
                scored.append((sn.get("purchases") or 0, r, sn))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    out.append("  Top 3 by purchases, widest audit (bar open, so these are candidates):" if is_open
               else "  Top 3 winners by purchases, widest audit:")
    for i, (p, r, sn) in enumerate(scored[:3], 1):
        out.append(f"    {i}. {r['name']}: {p:,.0f} purchases · {F.money(sn.get('cpa'))} a purchase · ROAS {F.roas(sn.get('roas'))}")
    if not scored:
        out.append("    None.")
    return out


def v_status(root, a):
    if a.brand == "all":
        d = Path(root) / "runs" / "winners"
        brands = sorted(p.name for p in d.iterdir() if (p / "bank.json").is_file()) if d.is_dir() else []
    else:
        check_brand(root, a.brand)
        brands = [a.brand]
    if not brands:
        print("No brand has a bank yet.")
    for i, b in enumerate(brands):
        print(("\n" if i else "") + "\n".join(status_lines(root, b)))
    return 0


def month(s, what):
    if s is None:
        return None
    if not (s.isdigit() and 1 <= int(s) <= 12):
        raise BadUse(f"{what} has to be a month written MM, not {s}.")
    return int(s)


def v_yoy(root, a):
    if (a.from_month is None) != (a.to_month is None):
        raise BadUse("--from-month and --to-month go together.")
    if a.window:
        pick_window(root, a.brand, a.window)
    md, _, doc = W.yoy(root, a.brand, a.window, month(a.from_month, "--from-month"), month(a.to_month, "--to-month"))
    print(W.yoy_line(doc))
    print(f"yoy: {B.rel(root, md)}")
    return 0


def v_store(root, a):
    if a.weeks < 1:
        raise BadUse("--weeks has to be at least 1.")
    md, _, doc = W.store(root, a.brand, a.weeks)
    print(W.store_line(doc))
    print(f"store: {B.rel(root, md)}")
    return 0


def v_who(root, a):
    """Sales by who each ad was for, from the files on disk."""
    if a.days is not None and a.days < 1:
        raise BadUse("--days has to be at least 1.")
    o = WV.build(root, a.brand, a.days, a.source)
    p = WV.write(root, o)
    t = o["total"]
    print(f"who: {t['ads']} ads, ${t['spend']:,.2f}, {t['purchases']:g} purchases, {o['window']}" + (f" ({o['note']})" if o.get("note") else ""))
    print("known, by spend: " + ", ".join(f"{k} {o['by'][k]['coverage']['spend']}%" for k, _ in WV.DIMS))
    print(f"  -> {B.rel(root, p)}")
    return 0


def v_messages(root, a):
    """Every winner through the same gates, from its teardown's core message to the next brief."""
    return MG.main([a.do] + ([a.run] if a.run else []) + ["--brand", a.brand, "--root", str(root)])


def v_shapes(root, a):
    """Every winner's story shape, rolled up by money, pointed at the story presets that carry it."""
    return SH.main([a.do, "--brand", a.brand, "--root", str(root)])


def v_system(root, a):
    """Where a brand stands on every step from ad results to a brief, and the next step on each. Files only."""
    if a.brand == "all":
        d = Path(root) / "runs" / "winners"
        brands = sorted(p.name for p in d.iterdir() if (p / "bank.json").is_file()) if d.is_dir() else []
    else:
        check_brand(root, a.brand)
        brands = [a.brand]
    for i, b in enumerate(brands):
        p, d = SY.write(root, b)
        print(("\n" if i else "") + b.upper())
        for s in d["steps"]:
            print("  %-20s %-10s %s%s" % (s["name"], SY.MARK[s["state"]], s["has"], ("  ->  " + s["next"]) if s["next"] else ""))
        print("  ->", B.rel(root, p))
    return 0


# ---------- the door ----------

def parser():
    ap = Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="verb", required=True, metavar="verb")
    def verb(name, fn, helptext):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--brand", required=True)
        p.add_argument("--root", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        p.set_defaults(fn=fn)
        return p
    p = verb("audit", v_audit, "pull, rank, media, dedupe, sheets, build; then bank and feed if nothing is left to tag")
    p.add_argument("--since", required=True); p.add_argument("--until", required=True); p.add_argument("--title")
    p = verb("tag", v_tag, "save tags, then build, bank and feed")
    p.add_argument("--window", required=True); p.add_argument("--tags", required=True)
    p = verb("videos", v_videos, "download the top videos of a window for teardowns")
    p.add_argument("--window", required=True); p.add_argument("--top", type=int, required=True)
    p = verb("mirror", v_mirror, "copy a window's pictures and videos to the Drive")
    p.add_argument("--window", required=True)
    p = verb("bank", v_bank, "bank an audit window, the newest if none is named")
    p.add_argument("--window")
    p = verb("feed", v_feed, "rebuild the feed from the bank's widest window; --window prints another one and writes nothing")
    p.add_argument("--window")
    p = verb("score", v_score, "results, then the join to prompts and borrowed winners, then bank the chain-made ads and rebuild the feed")
    p.add_argument("--days", type=int, default=90)
    p = verb("creators", v_creators, "creator videos: results by trybe id, bank them under the bar, rebuild the feed, write brief-next")
    p.add_argument("--days", type=int, default=90); p.add_argument("--results")
    p = verb("leaderboard", v_leaderboard, "creators and clippers ranked: reach, payout, sales, all-time and this week (free pulls)")
    p.add_argument("--no-pull", action="store_true")
    p = verb("statics", v_statics, "the winning image ads, each tied to its brief, chain run, approved picture and 3D set")
    p.add_argument("--days", type=int, default=30); p.add_argument("--min-spend", type=float, default=100.0)
    p.add_argument("--min-roas", type=float)
    verb("five", v_five, "the five always-on briefs: proven ads ranked on numbers, no two of one format and angle")
    p = verb("bar", v_bar, "set or show the winner bar")
    p.add_argument("--min-spend", type=float); p.add_argument("--max-cpa", type=float); p.add_argument("--min-roas", type=float)
    p.add_argument("--open", action="store_true", help="clear the bar first")
    p.add_argument("--creators", action="store_true", help="set the creator bar (rows with a trybe id) and leave the paid bar alone")
    p.add_argument("--min-purchases", type=float)
    verb("status", v_status, "one screen per brand")
    p = verb("yoy", v_yoy, "the same months in both years, by group, what's on screen and message, from an audit's cells")
    p.add_argument("--window"); p.add_argument("--from-month"); p.add_argument("--to-month")
    p = verb("store", v_store, "whole-store revenue against ad spend by week, from the warehouse")
    p.add_argument("--weeks", type=int, default=12)
    p = verb("messages", v_messages, "winners by core message: what is stuck, what to brief next, the page")
    p.add_argument("do", choices=("status", "next", "check", "page", "start")); p.add_argument("run", nargs="?")
    p = verb("shapes", v_shapes, "winners by story shape: what is uncalled, the check, the build (data, team copy, page)")
    p.add_argument("do", choices=("todo", "check", "build"))
    p = verb("who", v_who, "sales by avatar, sub-avatar, demographic, desire, awareness and doubt, from the files on disk")
    p.add_argument("--days", type=int); p.add_argument("--source", choices=("score", "desk"), default="score")
    verb("system", v_system, "where the brand stands on every step from ad results to a brief, and the next step on each")
    return ap


def main(argv=None):
    try:
        a = parser().parse_args(argv)
        root = Path(a.root) if getattr(a, "root", None) else paths.repo(__file__)
        A.REPO = root
        if a.verb not in ("status", "system"):
            check_brand(root, a.brand)
        return a.fn(root, a)
    except BadUse as e:
        print(str(e), file=sys.stderr)
        return 2
    except BAD as e:
        print(f"That can't be done: {e}.", file=sys.stderr)
        return 2
    except (Exception, SystemExit) as e:  # noqa: BLE001  the Meta helper exits on an error; a step stopping is one sentence too
        if isinstance(e, SystemExit) and e.code in (0, None, 2):
            raise
        print("The step stopped: %s." % (str(e).split("\n")[0][:200].rstrip(".") or type(e).__name__), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
