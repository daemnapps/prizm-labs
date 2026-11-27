#!/usr/bin/env python3
"""The month's ratios: which offers, which email kinds and which audiences a month's emails carry, in what shares.

    python3 ratios.py --brand <brand> --month YYYY-MM            # the month's mix against its ratios (review layer on)
    python3 ratios.py --brand <brand> --month YYYY-MM --rebalance --by <who> [--write]
                                                                  # unwritten sends re-pointed through the review layer

RULED 2026-11-07 (owner): every calendar the machine programs keeps clean ratios on its offers, email kinds and
audiences. Before this, every sale send took the first product in the brand's storefront-order, so one product
filled the month and the next ones in the order got no sends at all.

The shares live in ONE file per brand, `brands/<brand>/email-sms/ratios.json`; nothing here knows a brand,
a product or a number:

    {
      "tolerance_points": 5,
      "offer":    {"shares": [{"keys": ["<offer key>", ...], "share": 50}, ...],   # a group rotates its keys
                   "pinned_types": ["early-access", "last-chance"],              # keep the first group's offer
                   "lead_types": ["sale-window"]},                               # keep it where the shares allow
      "category": {"shares": {"Promotional": 50, ...}},
      "audience": {"buckets": {"<name>": ["<segment suffix>", ...]}, "shares": {"<name>": 70, ...}}
    }

- offer: shares of the EMAILS that carry an offer. The planner (marketing_calendar.finish) re-points those sends to
  hit the shares exactly, spread evenly through the month in date order; a pinned type keeps the first group.
  Off target by more than the tolerance is a break in checks.md.
- category, audience: shares of all emails. Checked, not re-planned (a send's type and segment come from earlier
  layers): off target by more than the tolerance is a warning in checks.md, so a human sees it before the month
  stands.
- category, audience are also BALANCED (balance(), 2026-11-07): a send swaps to a type of the same role in an
  under-share kind, or to a segment of an under-share audience. What still cannot reach its share warns.
A brand with no ratios.json is unchanged and gets one warning saying so.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(brand_root):
    try:
        return json.loads((Path(brand_root) / "email-sms" / "ratios.json").read_text())
    except (FileNotFoundError, ValueError):
        return None


def _emails(slots):
    return [s for s in slots if s.get("channel", "email") == "email"]


def _has_offer(s):
    return not str(s.get("offer") or "none").strip().lower().startswith("none")


def _quotas(n, groups):
    """Largest remainder: n sends split by the groups' shares, whole numbers that add up to n."""
    tot = sum(g["share"] for g in groups) or 1
    raw = [n * g["share"] / tot for g in groups]
    q = [int(r) for r in raw]
    for i in sorted(range(len(groups)), key=lambda i: -(raw[i] - q[i]))[: n - sum(q)]:
        q[i] += 1
    return q


def plan_offers(sends, groups, pinned_types=()):
    """[(send, group index)] in date order: pinned types take group 0; the rest are dealt so each group's running
    count tracks its quota evenly through the month. Pure: changes nothing."""
    sends = sorted(sends, key=lambda s: (s.get("date") or "", s.get("id") or ""))
    q = _quotas(len(sends), groups)
    out, got = [], [0] * len(groups)
    pinned = [s for s in sends if s.get("type") in pinned_types]
    for s in pinned:
        out.append((s, 0))
        got[0] += 1
    free = [s for s in sends if s.get("type") not in pinned_types]
    left = [max(0, q[i] - got[i]) for i in range(len(groups))]
    n = sum(left) or 1
    dealt = [0] * len(groups)
    for i, s in enumerate(free, 1):
        g = max(range(len(groups)), key=lambda k: (left[k] * i / n - dealt[k], -k) if dealt[k] < left[k] else (-1e9, -k))
        if dealt[g] >= left[g]:
            g = 0
        dealt[g] += 1
        out.append((s, g))
    return out


def _point(s, key, singles):
    s["product"] = key
    s["offer"] = key
    s["offer_mix"] = [key] + list(singles.get(key) or [])


def apply_offers(slots, brand_root, singles=None):
    """The planner's step: re-point every offer-carrying email to the brand's offer shares. -> notes."""
    r = load(brand_root)
    if not r or not (r.get("offer") or {}).get("shares"):
        return []
    groups = r["offer"]["shares"]
    pins = tuple(r["offer"].get("pinned_types") or ())
    singles = singles or {}
    sends = [s for s in _emails(slots) if _has_offer(s)]
    turn = [0] * len(groups)
    notes = []
    for s, g in plan_offers(sends, groups, pins):
        keys = groups[g]["keys"]
        key = keys[turn[g] % len(keys)]
        turn[g] += 1
        if s.get("offer") != key or s.get("product") != key:
            notes.append(f"- {s.get('id')} ({s.get('date')}): offer `{s.get('offer')}` -> `{key}` (email-sms/ratios.json)")
        _point(s, key, singles)
        s["why"] = (s.get("why") or "") + f" · offer `{key}`: the brand's offer shares (email-sms/ratios.json)"
    return notes


def _segment_bucket(seg, buckets):
    seg = str(seg or "")
    for name, ends in buckets.items():
        if any(seg.endswith(e) for e in ends):
            return name
    return "other"


CATS = {"ask": "Promotional", "help": "Educational", "belong": "Cultural", "real": "Community", "brand": "Brand"}


def _spread(items, k):
    """k of items, evenly spaced through them (items in date order)."""
    if k <= 0 or not items:
        return []
    if k >= len(items):
        return list(items)
    step = len(items) / k
    return [items[int(i * step + step / 2)] for i in range(k)]


def _types(brand_root):
    try:
        d = json.loads((Path(brand_root) / "email-sms" / "email-types.json").read_text())
    except (FileNotFoundError, ValueError):
        return []
    return d.get("types") or []


def balance(slots, brand_root, movable=None):
    """Email kinds and audiences brought to the brand's shares (2026-11-07). -> [(send, field, new value)], applied.

    Kinds: a send in a kind over its share takes a type of the same ROLE from a kind under its share (a proof-drop that
    earns becomes a mechanism that earns; a guarantee that recovers becomes an objection-shot that recovers), so every
    arc keeps its shape and every offer stays where it is. Audiences: a send in an audience over its share goes to the
    first segment of an audience under its share. Pinned types never move; `movable` (ids) limits the sends that may.
    Picks are spread evenly through the month."""
    r = load(brand_root)
    if not r:
        return []
    pins = set((r.get("offer") or {}).get("pinned_types") or ())
    em = sorted(_emails(slots), key=lambda s: (s.get("date") or "", s.get("id") or ""))
    ok = [s for s in em if s.get("type") not in pins and (movable is None or s.get("id") in movable)]
    changes = []
    sh = (r.get("category") or {}).get("shares") or {}
    types = _types(brand_root)
    if sh and types:
        by = {}
        for t in types:
            c = CATS.get(t.get("well"))
            if c:
                by.setdefault((c, t.get("role")), []).append(t["key"])
        names = list(sh)
        q = dict(zip(names, _quotas(len(em), [{"share": sh[k]} for k in names])))
        for s in em:                                  # a kind with no share has a share of none
            if s.get("category") not in q:
                names.append(s.get("category"))
                q[s.get("category")] = 0
        have = {k: sum(1 for s in em if s.get("category") == k) for k in names}
        turn = {}
        def sources(k):                               # the kind with the fewest sends able to feed it goes first
            return sum(1 for s in ok if s.get("category") != k and have.get(s.get("category"), 0) > q.get(s.get("category"), 0)
                       and by.get((k, s.get("role"))))
        for under in sorted(names, key=lambda k: (sources(k), -(q[k] - have[k]))):
            for over in sorted(names, key=lambda k: -(have[k] - q[k])):
                need, spare = q[under] - have[under], have[over] - q[over]
                if need <= 0 or spare <= 0:
                    continue
                cand = [s for s in ok if s.get("category") == over and by.get((under, s.get("role")))]
                for s in _spread(cand, min(need, spare)):
                    opts = by[(under, s.get("role"))]
                    t = opts[turn.get(under, 0) % len(opts)]
                    turn[under] = turn.get(under, 0) + 1
                    changes += [(s, "type", t), (s, "category", under)]
                    s["type"], s["category"] = t, under
                    have[over] -= 1
                    have[under] += 1
                    ok.remove(s)
    au = r.get("audience") or {}
    if au.get("shares"):
        names = list(au["shares"])
        bk = au.get("buckets") or {}
        q = dict(zip(names, _quotas(len(em), [{"share": au["shares"][k]} for k in names])))
        have = {k: sum(1 for s in em if _segment_bucket(s.get("segment"), bk) == k) for k in names}
        ok = [s for s in em if s.get("type") not in pins and (movable is None or s.get("id") in movable)]
        for under in sorted(names, key=lambda k: -(q[k] - have[k])):
            for over in sorted(names, key=lambda k: -(have[k] - q[k])):
                need, spare = q[under] - have[under], have[over] - q[over]
                if need <= 0 or spare <= 0 or not bk.get(under):
                    continue
                cand = [s for s in ok if _segment_bucket(s.get("segment"), bk) == over]
                for s in _spread(cand, min(need, spare)):
                    pre = str(s.get("segment") or "").rsplit(" | ", 1)[0]
                    seg = f"{pre} | {bk[under][0]}" if " | " in str(s.get("segment") or "") else bk[under][0]
                    changes.append((s, "segment", seg))
                    s["segment"] = seg
                    have[over] -= 1
                    have[under] += 1
                    ok.remove(s)
    for s, f, v in changes:
        s["why"] = (s.get("why") or "") + f" · {f} `{v}`: the brand's shares (email-sms/ratios.json)"
    return changes


def mix(slots, r):
    """{part: {name: (count, share %, target %)}} for a month's emails."""
    em = _emails(slots)
    out = {}
    o = (r.get("offer") or {}).get("shares") or []
    if o:
        sends = [s for s in em if _has_offer(s)]
        n = len(sends) or 1
        tot = sum(g["share"] for g in o) or 1
        part = {}
        q = _quotas(len(sends), o)
        for g, qk in zip(o, q):
            c = sum(1 for s in sends if s.get("offer") in g["keys"])
            # the 4th value is the whole-send quota: a small month cannot land inside the points, only on the quota
            part[" + ".join(g["keys"])] = (c, round(100 * c / n), round(100 * g["share"] / tot), qk)
        other = sum(1 for s in sends if not any(s.get("offer") in g["keys"] for g in o))
        if other:
            part["other offers"] = (other, round(100 * other / n), 0)
        out["offer"] = part
    for key, field in (("category", "category"), ("audience", "segment")):
        sh = (r.get(key) or {}).get("shares") or {}
        if not sh:
            continue
        n = len(em) or 1
        tot = sum(sh.values()) or 1
        if key == "audience":
            names = [_segment_bucket(s.get("segment"), r["audience"].get("buckets") or {}) for s in em]
        else:
            names = [str(s.get(field) or "") for s in em]
        part = {k: (names.count(k), round(100 * names.count(k) / n), round(100 * v / tot)) for k, v in sh.items()}
        rest = sum(1 for x in names if x not in sh)
        if rest:
            part["other"] = (rest, round(100 * rest / n), 0)
        out[key] = part
    return out


def problems(slots, brand_root):
    """-> (breaks, warnings) for checks.md."""
    r = load(brand_root)
    if r is None:
        return [], ["no email-sms/ratios.json: offers, email kinds and audiences run without shares"]
    tol = r.get("tolerance_points", 5)
    breaks, warns = [], []
    for part, rows in mix(slots, r).items():
        off = [f"{k} {c[1]}% (target {c[2]}%)" for k, c in rows.items()
               if abs(c[1] - c[2]) > tol and not (len(c) > 3 and c[0] == c[3])]
        if not off:
            continue
        line = f"ratio · {part}: " + "; ".join(off) + f" — email-sms/ratios.json, ±{tol} points"
        (breaks if part == "offer" else warns).append(line)
    return breaks, warns


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--month", required=True)
    ap.add_argument("--rebalance", action="store_true",
                    help="re-point the month's UNWRITTEN offer-carrying emails toward the shares, as reviewer edits")
    ap.add_argument("--by", default=None)
    ap.add_argument("--write", action="store_true", help="with --rebalance: write review.json (default: show only)")
    a = ap.parse_args(argv)
    repo = HERE.parents[2]
    brand_root = repo / "brands" / a.brand
    run_dir = repo / "runs" / "marketing-calendar" / a.brand / a.month
    sys.path.insert(0, str(HERE))
    import review as RV
    raw = json.loads((run_dir / "slots.json").read_text())
    data = RV.load(run_dir)

    def laid(slots):
        out = []
        for s in slots:
            s = dict(s)
            s.update((data["slots"].get(s["id"]) or {}).get("edits") or {})
            out.append(s)
        return out
    slots = laid(raw)
    r = load(brand_root)
    if r is None:
        print(f"{a.brand}: no email-sms/ratios.json")
        return 1
    if a.rebalance:
        sys.path.insert(0, str(repo / "components" / "email-production" / "adapter"))
        import calendar_view as CV
        done = {i.get("slot") for i in CV.month_items(a.month, root=repo, clone=None)["items"]
                if i.get("brand") == a.brand and i.get("status") != "unwritten"}
        groups = r["offer"]["shares"]
        sends = [s for s in _emails(slots) if _has_offer(s)]
        fixed = [s for s in sends if s["id"] in done]
        free = [s for s in sends if s["id"] not in done]
        q = _quotas(len(sends), groups)
        have = [sum(1 for s in fixed if s.get("offer") in g["keys"]) for g in groups]
        need = [max(0, q[i] - have[i]) for i in range(len(groups))]
        pins = tuple(r["offer"].get("pinned_types") or ())
        # an open send whose offer's group still needs sends keeps its offer: move only what must move
        gof = {k: i for i, g in enumerate(groups) for k in g["keys"]}
        move = []
        lead_t = tuple(r["offer"].get("lead_types") or ())
        # pinned first, then the types that should keep the lead offer, then the rest by date
        for s in sorted(free, key=lambda s: (s.get("type") not in pins, s.get("type") not in lead_t,
                                             s.get("date") or "", s["id"])):
            g = gof.get(s.get("offer"))
            if g is not None and need[g] > 0 and (s.get("type") not in pins or g == 0):
                need[g] -= 1
            else:
                move.append(s)
        sub = [{"keys": g["keys"], "share": need[i]} for i, g in enumerate(groups)]
        if sum(need) == 0:
            sub = groups
        turn = [sum(1 for s in sends if s.get("offer") in g["keys"] and s not in move) for g in groups]
        changes = []
        for s, g in plan_offers(move, sub, pins):
            keys = groups[g]["keys"]
            key = keys[turn[g] % len(keys)]
            turn[g] += 1
            if s.get("offer") != key or s.get("product") != key:
                changes.append((s["id"], s.get("date"), s.get("offer"), key))
                s["offer"] = s["product"] = key
        for c in changes:
            print(f"  {c[0]} {c[1]}: {c[2]} -> {c[3]}")
        if a.write and changes:
            if not a.by:
                print("--by is required with --write")
                return 2
            for sid, _d, _o, key in changes:
                RV.edit(a.brand, a.month, sid, "product", key, a.by, root=repo, commit=False)
                RV.edit(a.brand, a.month, sid, "offer", key, a.by, root=repo, commit=False)
                RV.mark(a.brand, a.month, sid, (data["slots"].get(sid) or {}).get("status") or "pending", a.by,
                        note=f"Offer shares (email-sms/ratios.json): this send now carries `{key}`.",
                        root=repo, commit=False)
            print(f"  {len(changes)} send(s) re-pointed in review.json")
        # kinds and audiences, on the same unwritten sends
        moved = balance(slots, brand_root, movable={s["id"] for s in _emails(slots) if s["id"] not in done})
        for s, f, v in moved:
            print(f"  {s['id']} {s.get('date')}: {f} -> {v}")
        if a.write and moved:
            for s, f, v in moved:
                RV.edit(a.brand, a.month, s["id"], f, v, a.by, root=repo, commit=False)
            for sid in sorted({s["id"] for s, _f, _v in moved}):
                RV.mark(a.brand, a.month, sid, (data["slots"].get(sid) or {}).get("status") or "pending", a.by,
                        note="Email kind / audience moved to the brand's shares (email-sms/ratios.json).",
                        root=repo, commit=False)
            print(f"  {len({s['id'] for s, _f, _v in moved})} send(s) re-kinded or re-aimed in review.json")
    for part, rows in mix(slots, r).items():
        print(f"{part}: " + " · ".join(f"{k} {c[0]} = {c[1]}% (target {c[2]}%)" for k, c in rows.items()))
    b, w = problems(slots, brand_root)
    for x in b:
        print("BREAK  " + x)
    for x in w:
        print("WARN   " + x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
