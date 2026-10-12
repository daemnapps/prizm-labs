#!/usr/bin/env python3
"""The seam between the calendar and the copy machine, before a run is spent.

    python3 copy_plan.py ../../runs/marketing-calendar/<brand>/2026-09
    python3 copy_plan.py <run> --only sep-01,sep-04

the owner, 2026-09-14: *"we need to have a clear workflow that is extracting from
this calendar so it knows the content of what we're doing, and then goes through
the copy machine to then write those emails."*

The extraction already happens — `brief.chain_argv` turns a slot into a chain
run. What was missing is being able to SEE it. A month's copy costs real money
and an hour, and the failures that matter are all visible beforehand: a slot
with no format to write from, a type that declares it needs an offer and has
none, a variant with no angle. Every one of those produces an email that is
wrong rather than an email that is missing, which is the expensive kind.

So this resolves every send the way the copy machine will, and says what each
one would be handed — without calling a model. Nothing here writes.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from paths import HERE, WORKSPACE, calendar_tool


def brand_dir(brand):
    return WORKSPACE / "brands" / brand
import brief

sys.path.insert(0, str(HERE / "machine"))
import email_elements as EE          # asks components/elements: is this type a real one?   # noqa: E402

sys.path.append(str(calendar_tool("machine")))
import review as R                                            # noqa: E402



def nearest_shape(brand, slot, n=3):
    """Sends on file whose shape is closest to the type being asked for — so a
    blocked slot can be pointed at one instead of guessed about."""
    if not brand:
        return ""
    idx = brand_dir(brand) / "email-sms/sends/index.json"
    if not idx.is_file():
        return ""
    try:
        rows = json.loads(idx.read_text())
    except Exception:
        return ""
    rows = rows if isinstance(rows, list) else sum(
        [v for v in rows.values() if isinstance(v, list)], [])
    words = [w for w in re.split(r"[-_\s]+", (slot.get("type") or "")) if len(w) > 3]
    hits = [r for r in rows if isinstance(r, dict)
            and any(w in f"{r.get('subject','')} {r.get('file','')}".lower() for w in words)]
    return " · ".join(f"`{r.get('file')}`" for r in hits[:n])


# An `affiliate-*` send needs a PARTNER, and the roster is the only thing that
# knows. Kept apart from the shape check on purpose: the two failed together
# once and got reported as one problem (2026-09-21).
def partner_problem(brand, slot):
    if not brand or "affiliate" not in (slot.get("type") or ""):
        return []
    f = brand_dir(brand) / "email-sms/affiliates.json"
    if not f.is_file():
        return [("blocked", "an affiliate email with no roster on file — "
                 f"`brands/{brand}/email-sms/affiliates.json` does not exist")]
    try:
        live = [a for a in json.loads(f.read_text()).get("affiliates", [])
                if a.get("status", "active") == "active"]
    except Exception as e:
        return [("blocked", f"could not read the affiliate roster ({e})")]
    if not live:
        return [("blocked", "no active partner on the roster — "
                 f"`brands/{brand}/email-sms/affiliates.json` lists none, and a partner is never invented")]
    keys = [a["key"] for a in live]
    named = slot.get("affiliate")
    if not named:
        return [("thin", "no partner named on the slot, and the roster has "
                 f"{len(keys)}: {', '.join(keys)} — the writer would have to pick")]
    if named not in keys:
        return [("blocked", f"partner `{named}` is not active on the roster — on file: {', '.join(keys)}")]
    a = next(x for x in live if x["key"] == named)
    if "traffic" in (a.get("commission") or "").lower():
        return [("note", f"`{named}` is traffic-only — no earnings or commission claim goes in the copy")]
    return []


def flag(argv, slot, avatar, angle, brand=None):
    """What would go wrong, in the order it would bite."""
    out = []
    src = slot.get("source") or ""
    if argv is None or src.startswith("["):
        # A blocked line that only says NO says nothing. It cost a wrong answer
        # to the owner on 2026-09-21: an `affiliate-feature` read as blocked, and
        # "no shape on file" was relayed to him as "no affiliate on file" —
        # while the partner had been recorded since 2026-09-02. A block now names what
        # WOULD unblock it, and never speaks for a roster it has not read.
        out.append(("blocked", "no shape to write from — this brand has never sent an "
                    f"email of type `{slot.get('type')}`, and nothing is borrowed from "
                    "another brand. Point the slot's `source` at a send on file whose "
                    "SHAPE fits" + (f" — nearest on file: {near}" if (near := nearest_shape(brand, slot)) else "")
                    + ". This is about the SHAPE only; it says nothing about "
                    "whether the thing the email is about exists."))
    out += partner_problem(brand, slot)
    # THE TYPE IS AN EMAIL FORMAT, and it has to be a real one (2026-09-20):
    # in the element library (components/elements, format/email) or in the
    # brand's own email/email-types.json. Unknown in both is refused here,
    # with the real ids named, before a step is paid for.
    if brand:
        why = EE.type_problem(brand, slot.get("type"))
        if why:
            out.append(("blocked", why))
    # THE OFFER HAS TO RESOLVE, not merely exist (2026-09-15). The calendar
    # assigns an offer by key; the chain then looks that key up in the bank and
    # DIES if it is not there. A whole month passed this file as "ready" while
    # every offer-carrying send was going to exit on `no offer in the bank` —
    # the two readers had drifted apart and nothing compared them. Checking a
    # field is present is not checking it points at something.
    key = (argv[argv.index("--offer") + 1]
           if argv and "--offer" in argv else slot.get("offer")) or "none"
    if brand and key != "none":
        try:
            sys.path.insert(0, str(HERE))
            import offers as OFFERS
            why = OFFERS.refuse(brand, key)
            if why:
                out.append(("blocked", f"offer `{key}` would be refused — {why} — "
                            "the chain exits before writing a word"))
        except Exception as e:
            out.append(("thin", f"could not read the offer bank ({e}) — the "
                        "offer is unverified"))
    if not angle:
        out.append(("thin", "no angle — the writer reasons from the avatar alone"))
    if not avatar or avatar in ("none", "mixed"):
        out.append(("thin", "no avatar — no language bank to write from"))
    if not (slot.get("occasion") or "").strip():
        out.append(("thin", "no occasion — nothing anchors it to the month"))
    if argv and "--research" in argv:
        p = Path(argv[argv.index("--research") + 1])
        if not p.is_absolute():
            p = HERE / p
        if not p.is_file():
            out.append(("thin", f"no live read on disk ({p.name}) — the week "
                        "this lands in is unresearched"))
    return out


def resolve(run_dir, only=None):
    run_dir = Path(run_dir).resolve()
    slots = json.loads((run_dir / "slots.json").read_text())
    state = json.loads((run_dir / "run.json").read_text())
    brand = state["brand"]
    rev = R.load(run_dir)
    slots = R.applied(slots, rev)

    rows, cut = [], []
    for s in slots:
        if s["_review"]["status"] == "cut":
            cut.append(s["id"])
            continue
        if only and s["id"] not in only:
            continue
        note = s["_review"]["note"]
        for avatar, angle, label in brief.variant_runs(s, brand):
            argv = brief.chain_argv(s, brand, avatar, angle, label, note=note or None)
            rows.append({
                "label": label, "slot": s["id"], "date": s.get("date"),
                "type": s.get("type"), "segment": s.get("segment"),
                "avatar": avatar, "angle": angle,
                "offer": (argv[argv.index("--offer") + 1]
                          if argv and "--offer" in argv else s.get("offer")),
                "source": s.get("source"), "source_brand": s.get("source_brand"),
                "note": note, "edits": list((s["_review"]["edits"] or {}).keys()),
                "argv": argv, "flags": flag(argv, s, avatar, angle, brand),
            })
    # THE SAME ARGUMENT, TWICE. The cells stage attaches an angle to a
    # (segment, avatar) CELL, and every send to that cell inherits it — so a
    # month of 35 emails can carry 13 distinct arguments and nobody counts.
    # Two emails making the same case to the same person in the same month is
    # the uniqueness problem showing up before a word is written (2026-09-14).
    seen = {}
    for r in rows:
        a = (r["angle"] or "").strip()
        if a:
            seen.setdefault(a, []).append(r["label"])
    for r in rows:
        a = (r["angle"] or "").strip()
        peers = [x for x in seen.get(a, []) if x != r["label"]]
        if peers:
            r["flags"].append(("repeat", f"the same angle as {', '.join(peers[:3])}"
                               + (f" and {len(peers) - 3} more" if len(peers) > 3 else "")))
    return brand, rows, cut, state


def render(brand, rows, cut, state, run_dir):
    blocked = [r for r in rows if any(k == "blocked" for k, _ in r["flags"])]
    thin = [r for r in rows if r not in blocked
            and any(k not in ("note",) for k, _ in r["flags"])]
    clean = [r for r in rows if r not in blocked and r not in thin]
    notes = [r for r in rows if any(k == "note" for k, _ in r["flags"])]
    angles = {(r["angle"] or "").strip() for r in rows if (r["angle"] or "").strip()}
    L = [f"# What the copy machine would be handed — {brand} {state.get('month','')}",
         "",
         f"{len(rows)} email(s) from {len({r['slot'] for r in rows})} send(s)"
         + (f", {len(cut)} send(s) cut by a reviewer" if cut else "") + ".", "",
         f"**{len(clean)} ready · {len(thin)} thin · {len(blocked)} blocked.** "
         "Nothing here was written; no model was called.", "",]
    if notes:
        L += ["**Rules riding with a send** — not a shortfall; the writer obeys them.", ""]
        L += [f"- **{r['slot']}** — " + "; ".join(m for k, m in r["flags"] if k == "note")
              for r in notes] + [""]
    L += [
         f"**{len(angles)} distinct argument(s) across {len(rows)} email(s).** "
         + ("Every email makes its own case." if len(angles) == len(rows) else
            f"{len(rows) - len(angles)} email(s) repeat an argument another one "
            "already makes — see below."), ""]
    if blocked:
        L += ["## Blocked — these cannot run", ""]
        for r in blocked:
            L.append(f"- **{r['label']}** ({r['date']} · `{r['type']}`) — "
                     + "; ".join(m for k, m in r["flags"] if k == "blocked"))
        L.append("")
    if thin:
        L += ["## Thin — they will run, and the writer is short of something", ""]
        for r in thin:
            L.append(f"- **{r['label']}** ({r['date']} · `{r['type']}`) — "
                     + "; ".join(m for _, m in r["flags"]))
        L.append("")

    L += ["## Every email, and what it is handed", ""]
    for r in rows:
        mark = ("BLOCKED" if r in blocked else "thin" if r in thin else "ready")
        L += [f"### {r['label']} — {r['date']} · `{r['type']}` · {mark}", "",
              f"- **to** {r['segment']} · **as** {r['avatar'] or '—'}",
              f"- **about** {r['angle'] or '(no angle)'}",
              f"- **sells** {r['offer'] or 'none'}"]
        if r["source"]:
            where = f"{r['source_brand'] or brand}/{r['source']}"
            L.append(f"- **shape from** `{where}`"
                     + ("  ← borrowed from another brand" if r["source_brand"] else ""))
        if r["note"]:
            L.append(f"- **the reviewer said** {r['note']}")
        if r["edits"]:
            L.append(f"- **reviewer rewrote** {', '.join(r['edits'])}")
        L.append("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--only", help="comma-separated slot ids")
    ap.add_argument("--out")
    ap.add_argument("--quiet", action="store_true", help="just the counts")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    brand, rows, cut, state = resolve(a.run_dir, only)
    if a.quiet:
        b = sum(1 for r in rows if any(k == "blocked" for k, _ in r["flags"]))
        t = sum(1 for r in rows
                if any(k not in ("note", "blocked") for k, _ in r["flags"])) - 0
        print(f"{brand} {state.get('month','')}: {len(rows)} email(s) · "
              f"{len(rows) - t - b} ready · {t} thin · {b} blocked")
        return
    doc = render(brand, rows, cut, state, a.run_dir)
    if a.out:
        Path(a.out).write_text(doc)
        print(f"-> {a.out}")
    else:
        print(doc)


if __name__ == "__main__":
    main()
