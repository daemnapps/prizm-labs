#!/usr/bin/env python3
"""Mine a brand's own record for the moments it has ALREADY been speaking into.

    python3 moments_mine.py --brand <brand>
    python3 moments_mine.py --brand <brand> --out runs/marketing-calendar/<brand>/moments-<YYYY-MM-DD>/mined.md

the owner, 2026-09-13: *"How do we even go through the research of identifying what
a brand moment is?"* Until now the honest answer was: a person read the sends
once and typed a file. Nothing re-ran, so a moment the brand started using last
month stayed invisible.

This is the half of that question the brand can answer about ITSELF, and it is
arithmetic rather than judgement, so it costs nothing and can run every week:

  **A moment is proven when the brand has sent into it more than once, around
  the same point in the year, and the record says what those sends earned.**

Two ways a send gets attached to a moment, and both leave a receipt:

  `holiday`   it landed inside a public holiday's window and its words name
              that holiday. The holiday table is layer 1's — real dates, per
              year, so a send is matched against the date that holiday
              actually fell on, never a remembered one.
  `recurring` its distinctive words came back at the same time of year in a
              different year. Two Februaries in a row talking about the same
              thing is a moment; one February is an email.

What this does NOT do, deliberately: it never names a moment the brand has not
already used. Everything it finds is `proven` by construction. Finding what the
avatar's world does that the brand has NEVER touched is the other half — that
is research, it needs the open web, and it belongs to the Control Room's
research recipes. This half just stops that half from re-discovering what the
brand already knows.

Nothing is written into the brand. The output is a proposal a person reads.
"""
import argparse
import datetime
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from paths import COMPONENTS, brand_root, rel
sys.path.append(str(COMPONENTS / "brandpath"))      # appended, never ahead of this tool
import brandpath as BP                                # noqa: E402
import holidays as H

# Words that carry no season. Stripped before anything is called distinctive,
# so "the", "your" and "skin" never look like a recurring theme.
STOP = set("""a an and are as at be been but by for from get give go had has have
he her here his how i if in is it its just let like make me my new no not now of
off on one only or our out over re she so some than that the their them then
there these they this to too up us use was we were what when where which who
why will with you your yours don dont doesn isn aren wasn weren won wont im ive
get got make made take taken day days time week weeks month months year years
today tomorrow yesterday best better good great new now more most all every
skin face hair beard shave shaving care routine product products use using
brand shop buy order sale off save deal deals free""".split())

WORD = re.compile(r"[a-z][a-z'’-]{2,}")

# The brand's OWN words — its name and what it sells — carry no season either,
# but they are the brand's knowledge, not this file's (workspace rule 7). They
# are read from the brand being mined, at run time, by `brand_stop_words`.
_BRAND_STOP = set()


def brand_stop_words(brand, root=None):
    """The words that are just this brand talking about itself: its folder
    name, its display name and site, and the handles and titles of its
    products (`products/store.json` when the brand has one). Nothing typed
    here — a brand with no store file contributes its name and nothing else."""
    root = Path(root) if root else brand_root(brand)
    texts = [brand, brand.replace("-", " ")]
    try:
        store = json.loads(BP.brand_path(root.name, "products", "store.json", root=root.parent).read_text())
    except (OSError, ValueError):
        store = {}
    if isinstance(store, dict):
        texts.append(str(store.get("brand") or ""))
        site = re.sub(r"^https?://(www\.)?", "", str(store.get("site") or ""))
        texts.append(site.split("/")[0].rsplit(".", 1)[0])
        for p in store.get("products") or []:
            if isinstance(p, dict):
                texts += [str(p.get("handle") or "").replace("-", " "),
                          str(p.get("title") or "")]
    out = set()
    for t in texts:
        for w in WORD.findall(t.lower()):
            w = w.strip("'’-")
            if len(w) > 2:
                out.add(w)
                out.update(x for x in w.split("-") if len(x) > 2)
    return out


def use_brand(brand, root=None):
    """Point the word filter at the brand being mined. Called by `mine`."""
    _BRAND_STOP.clear()
    _BRAND_STOP.update(brand_stop_words(brand, root))
    return set(_BRAND_STOP)


def words(*texts):
    out = set()
    for t in texts:
        for w in WORD.findall((t or "").lower()):
            w = w.strip("'’-")
            if len(w) > 2 and w not in STOP and w not in _BRAND_STOP:
                out.add(w)
    return out


def load(brand):
    root = brand_root(brand)
    def j(p, d):
        try:
            return json.loads(BP.resolve_rel(root.name, p, root=root.parent).read_text())
        except (FileNotFoundError, ValueError):
            return d
    ledger = j("email-sms/ledger.json", [])
    if not ledger:
        ledger = j("email-sms/sends/index.json", [])
    perf = {p["groupings"]["campaign_id"]: p["statistics"]
            for p in j("email-sms/performance.json", [])
            if p.get("groupings", {}).get("campaign_id")}
    known = set()
    mj = j("calendar/moments.json", {})
    for b in (mj.get("avatars") or {}).values():
        for m in b.get("moments", []):
            known.add(m["key"])
    return root, ledger, perf, known


def rpr_median(perf, floor=1000):
    vals = sorted(s["revenue_per_recipient"] for s in perf.values()
                  if s.get("recipients", 0) >= floor
                  and s.get("revenue_per_recipient") is not None)
    return vals[len(vals) // 2] if vals else None


def earned(rows, perf, median):
    """What this cluster of sends earned against the brand's own median."""
    got = [perf[r["id"]]["revenue_per_recipient"] for r in rows
           if r.get("id") in perf
           and perf[r["id"]].get("revenue_per_recipient") is not None]
    if not got or not median:
        return None, None
    mean = sum(got) / len(got)
    return mean, mean / median


# ------------------------------------------------------- the two detectors ---

def by_holiday(ledger, years, run_up=14):
    """A send inside a holiday's run-up whose words name that holiday."""
    table = {}
    for y in years:
        for r in H.table(y):
            table.setdefault(r["key"], []).append(r)
    names = {k: words(rows[0]["name"], k.replace("-", " "))
             for k, rows in table.items()}
    hits = defaultdict(list)
    for r in ledger:
        try:
            d = datetime.date.fromisoformat(r["sent"])
        except (ValueError, KeyError, TypeError):
            continue
        w = words(r.get("subject"), r.get("campaign"), r.get("preview"))
        for key, rows in table.items():
            if not (names[key] & w):
                continue
            for hol in rows:
                s = datetime.date.fromisoformat(hol["start"])
                e = datetime.date.fromisoformat(hol["end"])
                if s - datetime.timedelta(days=run_up) <= d <= e + datetime.timedelta(days=2):
                    hits[key].append(r)
                    break
    return hits


def by_recurrence(ledger, min_years=2, slack=21, house=0.04):
    """A distinctive word that comes back at the same point in a later year.

    Deliberately strict, because the whole value of this file is that it never
    proposes a pattern that isn't one. The first cut of it offered `same` and
    `feedback` as moments — two emails that happened to share a common word in
    two different Februaries. Three filters kill that:

    - a **house word** — one appearing in more than `house` of all sends — is
      how the brand always talks, not a season. Dropped before anything else.
    - a cluster needs **three sends across two years**, or three years. Two
      emails is a coincidence with a date on it.
    - and a finding needs **two words that travel together** (applied in
      `merge`). A season has a vocabulary; a coincidence has one word.
    """
    when = defaultdict(list)
    for r in ledger:
        try:
            d = datetime.date.fromisoformat(r["sent"])
        except (ValueError, KeyError, TypeError):
            continue
        for w in words(r.get("subject"), r.get("campaign")):
            when[w].append((d, r))
    cap = max(3, int(len(ledger) * house))
    when = {w: rows for w, rows in when.items() if len(rows) <= cap}
    out = {}
    for w, rows in when.items():
        if len(rows) < min_years:
            continue
        by_year = defaultdict(list)
        for d, r in rows:
            by_year[d.year].append((d, r))
        if len(by_year) < min_years:
            continue
        # a cluster: one send per year, all within `slack` days of each other
        # in the year's cycle
        best = None
        for anchor_year, anchor_rows in by_year.items():
            for ad, ar in anchor_rows:
                doy = ad.timetuple().tm_yday
                pick = []
                for y, yrows in by_year.items():
                    near = [(d, r) for d, r in yrows
                            if min(abs(d.timetuple().tm_yday - doy),
                                   365 - abs(d.timetuple().tm_yday - doy)) <= slack]
                    if near:
                        pick.append(min(near, key=lambda x: x[0]))
                if len(pick) >= min_years and (best is None or len(pick) > len(best)):
                    best = pick
        if not best:
            continue
        yrs = len({d.year for d, _ in best})
        if yrs >= 3 or (yrs >= 2 and len(best) >= 3):
            out[w] = sorted(best, key=lambda x: x[0])
    return out


def merge(recurring, min_share=0.6):
    """Words that travel together describe ONE moment, not five. Group by the
    set of sends they point at; a word whose sends are mostly another word's
    sends joins it rather than standing as its own finding."""
    items = [(w, {id(r) for _, r in rows}, rows) for w, rows in recurring.items()]
    items.sort(key=lambda x: -len(x[1]))
    groups = []
    for w, ids, rows in items:
        for g in groups:
            overlap = len(ids & g["ids"]) / max(1, min(len(ids), len(g["ids"])))
            if overlap >= min_share:
                g["words"].append(w)
                g["ids"] |= ids
                for d, r in rows:
                    if r not in [x[1] for x in g["rows"]]:
                        g["rows"].append((d, r))
                break
        else:
            groups.append({"words": [w], "ids": set(ids), "rows": list(rows)})
    for g in groups:
        g["rows"].sort(key=lambda x: x[0])
    # a season has a vocabulary; a coincidence has one word
    return [g for g in groups if len(g["words"]) >= 2]


# ------------------------------------------------------------- the report ---

def render(brand, found, known, median, ledger):
    L = [f"# Moments this brand has already been speaking into — {brand}", "",
         f"Mined {datetime.date.today().isoformat()} from {len(ledger)} sends "
         f"in the brand's own record. Nothing here is invented: every line "
         f"names the emails that prove it.", ""]
    if median:
        L += [f"The brand's median revenue per recipient is **${median:.4f}** "
              f"(sends over 1,000 recipients). Everything below is measured "
              f"against that.", ""]
    else:
        L += ["_No performance data joined — this brand's record carries no "
              "revenue per recipient, so nothing below can be ranked by what "
              "it earned._", ""]

    new = [f for f in found if not f["known"]]
    old = [f for f in found if f["known"]]
    L += [f"**{len(found)} found · {len(new)} not in the brand's moments file "
          f"· {len(old)} already there.**", ""]
    if not found:
        L += ["Nothing recurred. Either the record is too short, or this brand "
              "has not yet built a habit anywhere in the year.", ""]

    for title, rows in (("Not in the moments file yet", new),
                        ("Already in the moments file — confirmed by the record", old)):
        if not rows:
            continue
        L += [f"## {title}", ""]
        for f in rows:
            ratio = (f"**{f['ratio']:.1f}x** the brand's median"
                     if f["ratio"] else "no performance joined")
            L += [f"### `{f['key']}`  ·  {f['how']}  ·  {ratio}",
                  f"_{f['when']}_  ·  {len(f['sends'])} send(s)"
                  + (f"  ·  words: {', '.join(f['words'][:6])}" if f.get("words") else ""),
                  ""]
            for d, r in f["sends"]:
                L.append(f"- {d.isoformat()} — {r.get('subject', '(no subject)')}")
            L += ["", f"**Proposed anchor:** `{f['anchor']}`", ""]

    L += ["---", "",
          "## What this cannot tell you", "",
          "This reads the brand's own sends and nothing else, so it can only "
          "find moments the brand has ALREADY used. Everything here is "
          "`proven` by construction.", "",
          "What the avatar's world does that this brand has never touched "
          "needs the open web, and that is the research side — "
          "`dispatch.py moments-research brand=<brand> avatar=<avatar>`. "
          "Run this first so that research does not spend its time "
          "rediscovering what the record already knows.", "",
          "**Nothing here is filed into the brand.** A person moves it.", ""]
    return "\n".join(L) + "\n"


def mine(brand):
    root, ledger, perf, known = load(brand)
    use_brand(brand, root)
    if not ledger:
        sys.exit(f"{brand} has no send record to mine "
                 f"({rel(root / 'email-sms/ledger.json')})")
    years = sorted({int(r["sent"][:4]) for r in ledger if r.get("sent")})
    median = rpr_median(perf)
    found = []

    for key, rows in by_holiday(ledger, years).items():
        seen, uniq = set(), []
        for r in rows:
            if r.get("id") not in seen:
                seen.add(r.get("id"))
                uniq.append((datetime.date.fromisoformat(r["sent"]), r))
        uniq.sort(key=lambda x: x[0])
        mean, ratio = earned([r for _, r in uniq], perf, median)
        yrs = sorted({d.year for d, _ in uniq})
        found.append({
            "key": key, "how": "holiday", "sends": uniq, "ratio": ratio,
            "known": key in known, "anchor": f'{{"holiday": "{key}"}}',
            "when": (f"{len(yrs)} year(s): {', '.join(map(str, yrs))}"
                     if len(yrs) > 1 else f"once, in {yrs[0]}")})

    hol_ids = {r["id"] for f in found for _, r in f["sends"] if r.get("id")}
    for g in merge(by_recurrence(ledger)):
        rows = [(d, r) for d, r in g["rows"] if r.get("id") not in hol_ids]
        if len({d.year for d, _ in rows}) < 2:
            continue
        mean, ratio = earned([r for _, r in rows], perf, median)
        months = sorted({d.strftime("%B") for d, _ in rows})
        key = "-".join(sorted(g["words"], key=lambda w: -sum(
            1 for _, r in rows if w in words(r.get("subject"), r.get("campaign"))))[:3])
        lo = min(d for d, _ in rows); hi = max(d for d, _ in rows)
        found.append({
            "key": key, "how": "recurring", "sends": rows, "ratio": ratio,
            "known": key in known, "words": sorted(g["words"]),
            "anchor": f'{{"window": ["{lo:%m-%d}", "{hi:%m-%d}"]}}',
            "when": f"{', '.join(months)} across "
                    f"{len({d.year for d, _ in rows})} years"})

    found.sort(key=lambda f: (f["known"], -(f["ratio"] or 0), -len(f["sends"])))
    return found, known, median, ledger


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    found, known, median, ledger = mine(a.brand)
    doc = render(a.brand, found, known, median, ledger)
    if a.out:
        p = Path(a.out).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(doc)
        print(f"-> {rel(p)}  ({len(found)} moment(s) found, "
              f"{sum(1 for f in found if not f['known'])} new)")
        return
    print(doc)


if __name__ == "__main__":
    main()
