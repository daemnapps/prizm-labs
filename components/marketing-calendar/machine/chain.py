#!/usr/bin/env python3
"""The chain, declared once — nine layers, in order, as data.

    python3 chain.py            # print the chain
    python3 chain.py --check    # check a brand has what each layer needs

Before this existed the sequence lived only in the order of statements inside
`calendar.py`, and every other thing that needed to describe it — the docs,
the board, the record on the platform — described it again by hand. Three
hand-written copies of one sequence is three things that drift. This is the
one copy; everything else reads it.

A layer is a stage in a chain in the ordinary sense: it takes what the layers
before it settled, adds exactly one kind of decision, writes that decision
down in its own numbered folder, and hands on. Seven are plain code and cost
nothing to re-run. Two think, and those two are the ones whose prompt and
output have to stay nameable forever — the owner's standing rule is that the
prompt is the product, so a month whose prompt version cannot be named is not
a month anyone can reason about.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

from paths import COMPONENTS
sys.path.append(str(COMPONENTS / "brandpath"))      # appended, never ahead of this tool
import brandpath as BP                                # noqa: E402

CODE, AI = "code", "ai"

# THE COMMERCIAL FLOOR — the owner, 2026-09-14: "every single month for every
# single brand, we should have 20% ask, 80% the rest. Really, every week should
# have an offer. I don't see a reason to not have offers every single week."
#
# A company rule, not a brand one, so it lives in the tool and no brand
# overrides it. It exists because the concepts prompt had only a BRAKE —
# "keep the month from being all asks" — and nothing at all telling it to
# sell, so both brands landed on three asks in a month and nothing noticed.
#
# The two numbers do not fight each other, and it is worth saying why: the
# 20% counts the ASK itself. Its warm-up and its cool-down are `earns` and
# `recovers`, so an arc puts one send in the 20% and two in the 80%.
ASK_SHARE = 0.20          # of the month's sends, the ones whose role is `asks`
OFFER_EVERY_WEEK = True   # no week passes without something to buy


def S(n, key, folder, name, by, does, out, unit, prompt=None, needs=()):
    return {"n": n, "key": key, "folder": folder, "name": name, "by": by,
            "does": does, "out": out, "unit": unit, "prompt": prompt,
            "needs": tuple(needs)}


def N(path, required, gives, without):
    """One thing a layer needs from the brand.

    `required` — the layer cannot run at all without it.
    `gives`    — what having it buys, in a few words.
    `without`  — what the layer does INSTEAD when it is absent.

    That last field is the point of this whole structure. A brand missing an
    optional file still gets a month, and the month looks exactly as confident
    as one planned on a full record — which is how Brand A came to be planned
    with three of its evidence inputs missing and nothing anywhere saying so
    (found 2026-09-13). A degraded layer has to announce itself.
    """
    return {"path": path, "required": required, "gives": gives, "without": without}


# The chain. Order is the list's order — nothing else decides it.
STAGES = [
    S(1, "holidays", "1-holidays", "The holidays", CODE,
      "The public holidays that land in this month, at their real dates. "
      "Calendar facts — the same for every brand.",
      "1-holidays/holidays.md", "holiday"),

    S(2, "moments", "2-cultural", "The brand's moments", CODE,
      "The brand's own cultural moments, each resolved to a real date from "
      "its anchor. A moment falling outside the month belongs to the month it "
      "falls in.",
      "2-cultural/moments.md", "moment",
      needs=[N("calendar/moments.json", True,
               "the brand's own claim on the year",
               "nothing to resolve — the month gets public holidays only, and "
               "every send is generic to the category")]),

    S(3, "cells", "3-cells", "Who is live", AI,
      "Which segments and avatars are in play this month and which rest. No "
      "counts, no ceiling, no floor — every why cites the record.",
      "3-cells/cells.json", "segment", prompt="cal3-cells",
      needs=[N("email-sms/audience-matrix.json", True,
               "who the brand can actually target, and how many of them",
               "the layer refuses — it will not invent a segment vocabulary"),
             N("email-sms/classified.json", False,
               "how cold each send type has gone",
               "no coldness table: the layer cannot argue from what has been "
               "neglected, so it reaches for the habitual type"),
             N("email-sms/learnings.md", False,
               "the numbered findings a decision cites",
               "every why is uncited — the checker flags them, and nothing "
               "grounds live-or-rest in money")]),

    S(4, "anchors", "4-anchors", "Pinned to the date", CODE,
      "Every dated holiday and moment PINNED to the month at its real date, as "
      "one send to each live segment it fits. A retail holiday becomes a full "
      "arc — a build-up scaled by what it earned before, the ask, the close. "
      "(Named 'the anchors' until 2026-09-14, which collided with a moment's "
      "own `anchor` field — that is the rule for FINDING a date, this is the "
      "act of putting sends on one.)",
      "4-anchors/anchors.md", "send",
      needs=[N("email-sms/ledger.json", False,
               "what each holiday earned before",
               "**every holiday gets a one-send arc.** The build-up cannot be "
               "scaled, so a holiday that liquidates the list is planned the "
               "same as one that does nothing"),
             N("email-sms/performance.json", False,
               "revenue per recipient, to compare against",
               "the same: no ratio, no scaling")]),

    S(5, "concepts", "5-concepts", "The concepts", AI,
      "The rest of the month, in order: an offer for every anchored ask, then "
      "the concepts the month makes timely, then education and the other "
      "categories.",
      "5-concepts/concepts.json", "move", prompt="cal5-concepts",
      needs=[N("products/offer-bank.md", True,
               "the only offers that exist",
               "the layer has nothing to assign and every ask lands offerless"),
             N("products", False,
               "what may be named in a send",
               "no product list: sends cannot name what they sell"),
             N("email-sms/learnings.md", False,
               "the evidence, as numbered findings",
               "the layer plans on coldness alone, with no economics")]),

    S(6, "catalogue", "6-catalogue", "Typed", CODE,
      "Every send typed against the brand's own catalogue; any offer-carrying "
      "ask completed into its full arc. A type the catalogue does not know is "
      "dropped, never invented around.",
      "6-catalogue/catalogue.md", "send",
      needs=[N("email-sms/email-types.json", False,
               "the brand's OWN kinds of send",
               "falls back to the tool's generic starter catalogue — the month "
               "is typed against types this brand never chose")]),

    S(7, "offers", "7-offers", "Offers checked", CODE,
      "Every offer checked against the brand's offer bank — the only place an "
      "offer may come from. An offer no variant can carry is stripped; an arc "
      "left with no offer collapses to its holiday send.",
      "7-offers/offers.md", "note",
      needs=[N("products/offer-bank.md", True,
               "the bank every offer is checked against",
               "nothing can be checked, so an invented offer would reach a "
               "customer — the one failure this layer exists to prevent")]),

    S(8, "affiliate", "8-affiliate", "The affiliate floor", CODE,
      "One affiliate partner a week, every week, if the brand has any on file.",
      "8-affiliate/affiliate.json", "slot",
      needs=[N("email-sms/affiliates.json", False,
               "partners to feature weekly",
               "**the layer is skipped and says so.** A brand with no affiliate "
               "arrangement gets no affiliate sends — the weekly floor is a "
               "standing commitment for brands that have one, not a rule about "
               "what a month must contain")]),

    S(9, "order", "9-order", "The order", CODE,
      "Dates resolved around the anchors, then hours, sources and links. One "
      "send a day. No send budget exists — the only thing ever refused is an "
      "exact duplicate.",
      "9-order/order.md", "slot",
      needs=[N("email-sms/classified.json", False,
               "this brand's own emails, to take each send's FORMAT from",
               "every slot comes out unfilled unless the brand declares a "
               "borrow — a send is written off a real email's shape, and a "
               "brand that has never sent anything has none of its own"),
             N("email-sms/format-sources.json", False,
               "where to borrow formats when the brand has none",
               "nothing to fall back on: a new brand's whole month is "
               "unfilled and nothing says why"),
             N("email-sms/learnings.md", False,
               "the brand's best-evidenced send hour",
               "falls back to 17:00 for every send, which is a guess wearing "
               "the same clothes as a measurement")]),
]

# ---------------------------------------------------------- the whole run ---
# The nine layers are the PLANNING. They are not the whole thing a person does
# to get a month, and a chain that only declares its middle leaves everyone to
# remember the ends. the owner, 2026-09-14: "establish this chain of all the stages
# that we did to get here."
#
# BEFORE runs per brand and rarely — it changes what the brand KNOWS.
# AFTER runs on every plan and is free.

def T(key, name, by, does, cmd, when):
    return {"key": key, "name": name, "by": by, "does": does,
            "cmd": cmd, "when": when}


BEFORE = [
    T("readiness", "Can this brand run it?", CODE,
      "Every layer's needs against what the brand actually has — full, "
      "degraded or blocked, and what a degraded layer loses.",
      "chain.py --check <brand>", "before a first month, and after any pull"),
    T("mine", "What the record already proves", CODE,
      "The brand's own sends, mined for moments it has been speaking into, "
      "each joined to what it earned. Free, safe weekly.",
      "moments_mine.py --brand <brand>", "monthly"),
    T("file", "File what the record proves", CODE,
      "Writes the proven moments into the brand's calendar, corrects entries "
      "the record contradicts, holds back anything it cannot place.",
      "moments_apply.py --brand <brand> --write", "after mining"),
    T("research", "What the brand has never touched", AI,
      "The avatar's year from the open web — graded, never `proven`, never "
      "filed without a person. Lives in the Control Room.",
      "dispatch.py moments-research brand=<brand> avatar=<avatar>",
      "when a brand's year is thin"),
    T("compare", "Two brands, side by side", CODE,
      "Shapes, not contents — where two brands have drifted apart in a way "
      "the chain will not notice on its own.",
      "compare.py", "whenever a brand is set up or changed"),
]

AFTER = [
    T("checks", "Check the month", CODE,
      "Every rule tested against the finished month: the arcs, the windows, "
      "the offers, the commercial floor, what each type says it needs.",
      "(runs inside the plan)", "every run"),
    T("calendar", "The calendar", CODE,
      "The month at its real dates, one brand at a time, every send opening "
      "on what goes to the writer.",
      "month.py  ·  served at /", "every run"),
    T("board", "The review board", CODE,
      "Where a person corrects the month — rewrite, approve, cut, note — "
      "before a word is written.",
      "board.py  ·  served at /board.html", "when reviewing"),
    T("record", "File the run", CODE,
      "One record per planned month on the platform plane: counts and "
      "pointers, never content.",
      "records.py --all", "every run"),
]

BY_KEY = {s["key"]: s for s in STAGES}
AI_KEYS = [s["key"] for s in STAGES if s["by"] == AI]
FOLDERS = [s["folder"] for s in STAGES]

# What a replay re-runs. A replay reuses what is already on disk for every
# layer it skips, so those layers' records must SURVIVE it — the month is
# still governed by their output, and a record that forgot which prompt wrote
# it is a month nobody can reproduce (this was a real bug: --from-anchors
# rebuilt the run record from scratch and lost both AI stages, 2026-09-13).
REPLAYS = {
    "from_anchors": {"label": "layers 4-9 re-run from disk",
                     "reruns": ["anchors", "catalogue", "offers", "affiliate", "order"],
                     "reuses": ["holidays", "moments", "cells", "concepts"]},
    "reorder":      {"label": "layer 9 and the board re-run from disk",
                     "reruns": ["order"],
                     "reuses": ["holidays", "moments", "cells", "anchors",
                                "concepts", "catalogue", "offers", "affiliate"]},
    "cont":         {"label": "resumed from an edited cells file",
                     "reruns": ["anchors", "concepts", "catalogue", "offers",
                                "affiliate", "order"],
                     "reuses": ["holidays", "moments", "cells"]},
}


# ------------------------------------------------------- recording a run ---

def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def blank(label, brand, month):
    return {"label": label, "brand": brand, "month": month,
            "lane_kind": "calendar", "stages": {}, "events": [],
            "generated_at": now()}


def carried(prior, replay):
    """A replay's starting record: the prior run's, with every layer this
    replay is about to re-run cleared, and every layer it reuses kept exactly
    as it was. Returns a fresh record when there is no prior run to carry."""
    if not prior or not prior.get("stages"):
        return None
    state = dict(prior)
    kept = {}
    for key in REPLAYS[replay]["reuses"]:
        s, row = BY_KEY[key], (prior.get("stages") or {}).get(key)
        if row:
            kept[key] = {**row, "carried": True}   # reused, not re-run just now
        else:
            # The layer's OUTPUT is on disk and still governs this month — the
            # replay is reading it right now — but nothing says which run wrote
            # it. That is a hole, and a hole that is written down is worth ten
            # times one that is merely absent: `stages` always carries all nine.
            kept[key] = {"n": s["n"], "name": s["name"], "by": s["by"],
                         "status": "unrecorded", "produced": None,
                         "unit": s["unit"], "out": s["out"], "carried": True,
                         "note": "reused from disk — no record of the run that "
                                 "wrote it, so the prompt version behind it "
                                 "cannot be named"}
    state["stages"] = kept
    state["events"] = list(prior.get("events") or [])
    return state


def event(state, what, **facts):
    state.setdefault("events", []).append(dict(at=now(), what=what, **facts))


def done(state, key, produced=None, seconds=None, **facts):
    """One layer finished. Every layer records the same shape, so a reader can
    ask any of them the same questions — which is the whole reason this
    function exists instead of nine hand-written dicts."""
    s = BY_KEY[key]
    row = {"n": s["n"], "name": s["name"], "by": s["by"], "status": "done",
           "produced": produced, "unit": s["unit"], "out": s["out"],
           "seconds": seconds, "at": now()}
    row.update({k: v for k, v in facts.items() if v not in (None, [], "")})
    # A layer that ran on a partial record carries that on its own row, so a
    # reader never has to hold two parts of the file side by side to find out
    # whether a thin result means a thin month or a thin brand.
    r = (state.get("brand_readiness") or {}).get(key)
    if r:
        row["ran_on"] = r["verdict"]
        row["losing"] = r["losing"]
    state.setdefault("stages", {})[key] = row
    return row


def ordered(state):
    """Every stage in chain order, whether it ran, was carried, or is missing."""
    out = []
    for s in STAGES:
        row = (state.get("stages") or {}).get(s["key"])
        # `unrecorded` outranks `carried`: both were reused from disk, but one
        # of them cannot name the prompt behind it, and that is the fact worth
        # surfacing. A reader who sees "carried" stops looking.
        out.append({**s, "run": row,
                    "status": ("missing" if not row
                               else row.get("status") if row.get("status") != "done"
                               else "carried" if row.get("carried")
                               else "done")})
    return out


# ------------------------------------------------------------- rendering ---

def table():
    """The chain as a markdown table. The docs print this rather than
    retyping it, so the table and the code cannot disagree."""
    L = ["| | Layer | Who | What |", "|---|---|---|---|"]
    for s in STAGES:
        who = "**AI**" if s["by"] == AI else "code"
        L.append(f"| {s['n']} | {s['name']} | {who} | {s['does']} |")
    return "\n".join(L)


def readiness(brand_root):
    """What this brand can and cannot do, layer by layer.

    Answers the question a run cannot answer for itself: is this month thin
    because the brand's year is thin, or because the chain was reading an
    empty folder? Returns one row per needed file, and a per-layer verdict:

        full      everything it wants is there
        degraded  it will run, with less — `without` says exactly what it
                  loses, and that sentence belongs in front of a person
        blocked   a required file is missing; the layer cannot run
    """
    root = Path(brand_root)
    out = []
    for s in STAGES:
        rows = []
        for nd in s["needs"]:
            p = BP.resolve_rel(root.name, nd["path"], root=root.parent)
            rows.append({**nd, "have": p.exists()})
        missing_req = [r for r in rows if r["required"] and not r["have"]]
        missing_opt = [r for r in rows if not r["required"] and not r["have"]]
        verdict = ("blocked" if missing_req
                   else "degraded" if missing_opt else "full")
        out.append({"n": s["n"], "key": s["key"], "name": s["name"],
                    "by": s["by"], "verdict": verdict, "needs": rows,
                    "losing": [r["without"] for r in missing_opt]})
    return out


def check(brand_root):
    """Back-compat: the flat (n, name, path, have) rows."""
    return [(L["n"], L["name"], r["path"], r["have"])
            for L in readiness(brand_root) for r in L["needs"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", metavar="BRAND", help="check a brand's files")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.json:
        print(json.dumps(STAGES, indent=1))
        return
    if a.check:
        from paths import brand_root, rel
        root = brand_root(a.check)
        print(f"{a.check} — {rel(root)}\n")
        MARK = {"full": "ok      ", "degraded": "DEGRADED", "blocked": "BLOCKED "}
        counts = {"full": 0, "degraded": 0, "blocked": 0}
        for L in readiness(root):
            counts[L["verdict"]] += 1
            print(f"  {MARK[L['verdict']]}  {L['n']}  {L['name']}")
            for r in L["needs"]:
                if r["have"]:
                    continue
                tag = "REQUIRED" if r["required"] else "optional"
                print(f"              missing {r['path']}  ({tag})")
                print(f"              -> {r['without']}")
        print(f"\n  {counts['full']} full · {counts['degraded']} degraded "
              f"· {counts['blocked']} blocked")
        if counts["blocked"]:
            print("  A blocked layer stops the run. Fix those first.")
        elif counts["degraded"]:
            print("  The month will build. It will be thinner than it looks,")
            print("  and the board says so on every run.")
        return
    def block(title, rows, note):
        print(f"\n## {title}\n\n{note}\n")
        for r in rows:
            who = "**AI**" if r["by"] == AI else "code"
            print(f"- **{r['name']}** ({who}) — {r['does']}")
            print(f"    `{r['cmd']}` · {r['when']}")

    block("Before the month", BEFORE,
          "Per brand, and rarely — these change what the brand KNOWS.")
    print("\n## The month — nine layers\n")
    print(table())
    print(f"\n{len(STAGES)} layers · {len(AI_KEYS)} think ({', '.join(AI_KEYS)}) "
          f"· {len(STAGES) - len(AI_KEYS)} are code and cost nothing to re-run")
    block("After the month", AFTER, "Every plan, and free.")


if __name__ == "__main__":
    main()
