#!/usr/bin/env python3
"""creators: creator videos in the bank, and the "what to brief next" file the swipe pick reads.

Normally driven by `winners.py creators --brand <b>`. Directly:
    creators.py --brand <brand> --results <trybe.json> [--checks <glob>] [--root REPO]

Results. A creator video's ad results come from funnel-tracking's `trybe.py` (its CLI): the warehouse's Meta ads
whose name ends with the video's 8-character trybe id, summed over the pull's window, with the Meta ad ids behind
them. `winners.py creators` runs that pull into runs/winners/<brand>/creators/<asof>/trybe.json.

Tags. The per-video read (the creator machine's check) writes one file per video with `hook_line`, `format`,
`angle`, `worked`; this reads them as data from runs/creator-machine/<brand>/*/checks/*.json (a checked file
beats an unread one; the newest wins).

Bank. Every creator video with spend lands as a bank row: id `<brand>-<first Meta ad id>` like every other ad (an
older results file without ad ids falls back to `<brand>-trybe-<trybe id>`), `trybe_id`, `creator`, `tags`, the
hook line as its hook words when the row has none, and one `creator` snapshot per pull window. A row the audit
or score already holds (shared ad id, or an ad name ending in the trybe id) is the same row. `state` comes from
the one bar, the bank's (bank.mark_states): open bar, every row is a candidate.

Brief next. runs/winners/<brand>/brief-next.json + .md: the formats, angles and hook lines of the creator videos
that won, ranked by purchases. Basis `winners` once the bar is set; `candidates` while it is open (videos with at
least one purchase); `none yet` before any. A video the per-video read has not tagged yet counts only under `tried`
(the swipe pick matches format words against swipes); so does a catch-all tag ("other", "none shown; ...", see
CATCH_ALL). `tried` lists every format and angle so far; `avoid` lists formats
that spent past the bar's min spend with no purchase (bar set only). Facts only; the swipe pick reads it.

Offline. Stdlib only. Read-only on its inputs. Exit 2 on bad input.
"""
import argparse, json, re, sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402
import bank as B  # noqa: E402

DEFAULT_ROOT = paths.repo(__file__)
CHECKS = "runs/creator-machine/{brand}/*/checks/*.json"
NOT_READ = "not read yet"
# Tags that say nothing about what to make. Kept under `tried`, never in formats, angles, hooks or avoid: the swipe
# pick matches format words against swipes, so a catch-all would match every untagged swipe.
CATCH_ALL = {"other", "others", "unknown", "mixed", "misc", "none", "n/a", "na", "unclear", "unread", "not", "no"}


def vague(text):
    """True when a tag is empty, unread or a catch-all ("other", "none shown; ...")."""
    t = (text or "").strip().lower()
    if not t or t == NOT_READ:
        return True
    first = re.split(r"[^a-z/]+", t)[0]
    return t.strip(" .;:") in CATCH_ALL or first in CATCH_ALL
EXAMPLES = 3


class BadInput(B.BadInput):
    pass


# ---------- reading ----------

def load_checks(root, brand, pattern=None):
    """{trybe_id: check}: a checked file beats an unread one, then the newest label wins."""
    out = {}
    for p in sorted(Path(root).glob((pattern or CHECKS).format(brand=brand))):
        try:
            d = json.loads(p.read_text())
        except ValueError:
            continue
        tid = d.get("trybe_id")
        if not tid:
            continue
        if d.get("state") == "checked" or out.get(tid, {}).get("state") != "checked":
            d["_path"] = B.rel(root, p)
            out[tid] = d
    return out


def load_results(path):
    d = B.load_json(path)
    if not isinstance(d, dict) or not isinstance(d.get("rows"), list) or not d.get("from") or not d.get("to"):
        raise BadInput(f"not a trybe.json (rows, from, to): {path}")
    return d


# ---------- bank ----------

def find(bank, ad_ids, tid):
    if ad_ids:
        r = B.find_row(bank, ad_ids)
        if r:
            return r
    for r in bank["rows"]:
        if r.get("trybe_id") == tid:
            return r
    for r in bank["rows"]:
        if any(str(n).endswith(tid) for n in (r.get("ad_names") or [])):
            return r
    return None


def ingest(root, bank, brand, results_path, checks):
    """Bank every creator video that spent. -> how many rows."""
    res = load_results(results_path)
    where = B.rel(B.brand_dir(root, brand), results_path)
    n = 0
    for v in res["rows"]:
        tid, m = v.get("trybe_id"), v.get("meta") or {}
        if not tid or not m.get("spend"):
            continue
        ad_ids = [str(x) for x in (m.get("ad_ids") or [])]
        row = find(bank, ad_ids, tid)
        if row is None:
            row = {"id": f"{brand}-{ad_ids[0]}" if ad_ids else f"{brand}-trybe-{tid}", "state": "candidate",
                   "core": False, "name": f"{v.get('creator') or 'creator'} · {tid}", "format": "Video",
                   "words": {"hook": None, "core_message": None, "offer": None}}
            bank["rows"].append(row)
        row["ad_ids"] = B.union(row.get("ad_ids"), ad_ids)
        row["ad_names"] = B.union(row.get("ad_names"), [str(x) for x in (m.get("ad_names") or [])])
        row["trybe_id"], row["creator"] = tid, v.get("creator")
        c = checks.get(tid) or {}
        tags = {k: c.get(k) for k in ("format", "angle", "hook_line", "worked") if c.get(k)}
        if tags:
            row["tags"] = tags
        w = row.setdefault("words", {"hook": None, "core_message": None, "offer": None})
        if not w.get("hook") and c.get("hook_line"):
            w["hook"] = c["hook_line"]
        src = row.setdefault("source", {})
        src["creator_results"] = where
        if c.get("_path"):
            src["check"] = c["_path"]
        row.setdefault("core", False)
        B.add_snapshot(row, {"kind": "creator", "since": res["from"], "until": res["to"], "pulled_at": res.get("made"),
                             "results": where, "rank": None,
                             **B.metrics(m.get("spend"), m.get("meta_purchases"), m.get("meta_purchase_value"))})
        n += 1
    src = {"kind": "creator", "results": where, "since": res["from"], "until": res["to"], "pulled_at": res.get("made"),
           "rows": n}
    if not any(s.get("kind") == "creator" and s.get("results") == where for s in bank["sources"]):
        bank["sources"].append(src)
    return n


# ---------- reading the bank back ----------

def newest(row, kind="creator"):
    snaps = [s for s in row.get("snapshots") or [] if s.get("kind") == kind]
    return snaps[-1] if snaps else None


def creator_rows(bank):
    """[(row, newest creator snapshot)] for every creator video in the bank, best first."""
    out = [(r, newest(r)) for r in bank["rows"] if r.get("trybe_id")]
    out = [(r, s) for r, s in out if s]
    out.sort(key=lambda x: (-(x[1].get("purchases") or 0), -(x[1].get("roas") or 0), -(x[1].get("spend") or 0)))
    return out


def creator_bar(bank):
    """The bar creator videos are judged on: the bank's `creator_bar` when set, else its `bar`."""
    return B.bar_for(bank, {"trybe_id": "-"})


def basis(bank):
    """-> (word, rows): the creator videos the next briefs learn from, under the creator bar."""
    rows = creator_rows(bank)
    bar = creator_bar(bank)
    if B.is_open(bar):
        won = [(r, s) for r, s in rows if (s.get("purchases") or 0) >= 1]
        return ("candidates" if won else "none yet"), won
    won = [(r, s) for r, s in rows if B.clears(bar, s)]
    return ("winners" if won else "none yet"), won


def winner_ids(root, brand):
    """{trybe_id} of the creator videos that clear the brand's bar. Empty while the bar is open."""
    p = B.bank_path(root, brand)
    if not p.is_file():
        return set()
    bank = B.load_bank(p, brand)
    bar = creator_bar(bank)
    if B.is_open(bar):
        return set()
    return {r["trybe_id"] for r, s in creator_rows(bank) if B.clears(bar, s)}


def tag(r, k):
    return (r.get("tags") or {}).get(k) or NOT_READ


def example(r, s):
    return {"trybe_id": r["trybe_id"], "creator": r.get("creator"), "bank_id": r["id"],
            "format": None if vague(tag(r, "format")) else tag(r, "format"),
            "angle": None if vague(tag(r, "angle")) else tag(r, "angle"),
            "hook_line": (r.get("tags") or {}).get("hook_line"),
            "purchases": s.get("purchases"), "spend": s.get("spend"), "roas": s.get("roas")}


def group(rows, key):
    g = OrderedDict()
    for r, s in rows:
        k = tag(r, key)
        e = g.setdefault(k, {key: k, "videos": 0, "purchases": 0, "spend": 0.0, "value": 0.0, "examples": []})
        e["videos"] += 1
        e["purchases"] += s.get("purchases") or 0
        e["spend"] += s.get("spend") or 0
        e["value"] += s.get("value") or 0
        if len(e["examples"]) < EXAMPLES:
            e["examples"].append(example(r, s))
    out = []
    for e in g.values():
        e["spend"], e["roas"] = round(e["spend"], 2), (round(e["value"] / e["spend"], 2) if e["spend"] else None)
        e.pop("value")
        out.append(e)
    out.sort(key=lambda e: (-e["purchases"], -(e["roas"] or 0), -e["spend"]))
    return out


def brief_next(bank):
    word, rows = basis(bank)
    every = creator_rows(bank)
    bar = creator_bar(bank)
    is_open = B.is_open(bar)
    avoid = []
    if not is_open and bar.get("min_spend") is not None:
        dead = [(r, s) for r, s in every if (s.get("spend") or 0) >= bar["min_spend"] and not s.get("purchases")]
        avoid = [{k: e[k] for k in ("format", "videos", "spend", "purchases")} for e in group(dead, "format")
                 if not vague(e["format"])]
    snaps = [s for _, s in every]
    return {"brand": bank["brand"], "made": datetime.now().isoformat(timespec="seconds"), "status": "draft",
            "bar": bar, "bar_open": is_open, "basis": word,
            "window": {"since": min((s["since"] for s in snaps), default=None),
                       "until": max((s["until"] for s in snaps), default=None)},
            "videos_running": len(every),
            "formats": [e for e in group(rows, "format") if not vague(e["format"])],
            "angles": [e for e in group(rows, "angle") if not vague(e["angle"])],
            "hooks": [example(r, s) for r, s in rows if not vague((r.get("tags") or {}).get("hook_line"))][:10],
            "avoid": avoid,
            "tried": {"formats": [{k: e[k] for k in ("format", "videos", "spend", "purchases")} for e in group(every, "format")],
                      "angles": [{k: e[k] for k in ("angle", "videos", "spend", "purchases")} for e in group(every, "angle")]}}


def money(x):
    return "—" if x is None else f"${x:,.0f}"


def render(d, bar_words):
    say = {"winners": "creator videos that clear the bar",
           "candidates": "the bar is open, so these are the creator videos with at least one purchase",
           "none yet": "no creator video has cleared the bar yet" if not d["bar_open"]
           else "no creator video has a purchase yet"}[d["basis"]]
    out = [f"# Brief next — {d['brand']}", "",
           f"Bar: {bar_words}. Basis: {d['basis']} ({say}). {d['videos_running']} creator videos running, "
           f"results {d['window']['since']} to {d['window']['until']}.", ""]
    for key, title in (("formats", "Formats"), ("angles", "Angles")):
        out += [f"## {title} to brief more of", ""]
        if not d[key]:
            out += ["None yet.", ""]
            continue
        k = key[:-1]
        out += [f"| {k.title()} | Videos | Purchases | Spend | ROAS |", "|---|---|---|---|---|"]
        out += [f"| {e[k]} | {e['videos']} | {e['purchases']} | {money(e['spend'])} | {e['roas'] or '—'} |" for e in d[key]]
        out.append("")
    out += ["## Hook lines that sold", ""]
    out += [f"- {h['hook_line']} — {h['format'] or 'format not named'} · {h['angle'] or 'angle not named'} · "
            f"{h['purchases']} purchases · `{h['trybe_id']}`"
            for h in d["hooks"]] or ["None yet."]
    out += ["", "## Avoid", ""]
    out += [f"- {a['format']}: {a['videos']} videos, {money(a['spend'])} spent, no purchase" for a in d["avoid"]] or \
        ["Nothing listed (the bar is open, or no format spent past it without a purchase)."]
    out += ["", "## Tried so far", ""]
    out += [f"- {e['format']}: {e['videos']} videos, {money(e['spend'])}, {e['purchases']} purchases"
            for e in d["tried"]["formats"]] or ["No creator video has run yet."]
    return "\n".join(out).rstrip() + "\n"


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


def write_brief_next(root, brand):
    bank = B.load_bank(B.bank_path(root, brand), brand)
    d = brief_next(bank)
    out = B.brand_dir(root, brand)
    out.mkdir(parents=True, exist_ok=True)
    (out / "brief-next.json").write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    (out / "brief-next.md").write_text(render(d, bar_words(d["bar"])))
    return out / "brief-next.json", d


def run(root, brand, results_path, checks_glob=None):
    """Bank the results, write the bank, then brief-next. -> (rows banked, brief-next dict)."""
    bank = B.load_bank(B.bank_path(root, brand), brand)
    n = ingest(root, bank, brand, results_path, load_checks(root, brand, checks_glob))
    B.write(root, bank)
    _, d = write_brief_next(root, brand)
    return n, d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--checks", help="glob under the root, {brand} filled in; default " + CHECKS)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9-]+", a.brand):
        print(f"bad brand: {a.brand!r}", file=sys.stderr)
        return 2
    try:
        n, d = run(Path(a.root), a.brand, Path(a.results), a.checks)
    except B.BadInput as e:
        print(f"bad input: {e}", file=sys.stderr)
        return 2
    print(f"{a.brand}: {n} creator videos banked; brief next: {d['basis']}, "
          f"{len(d['formats'])} formats, {len(d['angles'])} angles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
