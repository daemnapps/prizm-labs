#!/usr/bin/env python3
"""The calendar flow: a brand's record in, a month's slots out — built from
the ground up, in layers, each layer dated before the next is laid on it
(the owner, 2026-09-02: "ground up the calendar fundamentally").

    python3 calendar.py 2026-11 --brand <brand>
    python3 calendar.py 2026-11 --brand <brand> --dry-run         # free: spends and writes nothing (dryrun.py)
    python3 calendar.py 2026-11 --brand <brand> --stop-at-cells  # pause after stage 3
    python3 calendar.py 2026-11 --brand <brand> --continue        # resume from a hand-edited cells.json

Runs start to finish on the record — no checkpoint, no sign-off (the owner,
2026-08-31). One numbered folder per layer under
runs/marketing-calendar/<brand>/<month>/ (SI-22 (calendar months home)):

  1-holidays/    code  the public holidays that land in this month, with
                       their real dates (from the tool's holidays table —
                       calendar facts, the same for every brand)
  2-cultural/    code  the brand's own moments that land in this month,
                       each resolved to real dates from its anchor
  3-cells/       AI    who is live this month, who rests — no counts, no
                       ceiling, no floor; every why cites
  4-anchors/     code  every dated holiday and moment laid onto the month
                       at its real date, as ONE send to every live segment
                       it fits — a retail holiday as a full arc (a build-up
                       of 1-4 sends scaled by what the holiday earned
                       before, the ask, the close), an observance as one
                       send on the day; a member falling outside the month
                       belongs to the month it falls in
  5-concepts/    AI    the rest of the month, in order: an offer for every
                       anchored ask, then the concepts the month makes
                       timely, then the educational and other categories
  6-catalogue/   code  every send typed against the catalogue; any offer-
                       carrying ask completed into its arc
  7-offers/      code  every offer checked against the brand's offer bank —
                       an offer no variant can carry is stripped, and an
                       arc with no offer collapses to its holiday send
  8-affiliate/   code  one affiliate partner a week, every week, if the
                       brand has any on file (investor commitment, 2026-09-01)
  9-order/       code  dates resolved around the anchors, hours, sources,
                       links — no send budget exists; the only thing ever
                       refused is an exact duplicate

Then the board: checks.md (every rule, the per-person math) and briefs/
(one page per slot) beside slots.json and run.json at the month's root.
Brand-agnostic throughout: every fact resolves through brands/<brand>/.
"""
import argparse
import copy
import datetime
import json
import re
import sys
import time
from pathlib import Path


def _json_or(path, default):
    """A brand file that is not there yet reads as empty — a brand with no
    history is a brand, not an error (Brand A, 2026-09-09)."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return default


def _text_or(path, default=""):
    try:
        return path.read_text()
    except FileNotFoundError:
        return default

from paths import HERE, WORKSPACE, RUNS, COMPONENTS, month_dir
sys.path.append(str(COMPONENTS / "brandpath"))      # appended, never ahead of this tool
import brandpath as BP                                # noqa: E402
import runner as R
from runner import fill, latest_prompt, sha, catalogue_path as _cat, doctrine
import brandrecord as C
import chain as CH
import holidays as H

SEED_TYPES = HERE.parent / "definitions" / "send-types.seed.json"


def catalogue_path(brand):
    return _cat(brand, WORKSPACE, seed=SEED_TYPES)

DEFAULT_MODEL = "claude-opus-5"
MONTH_ABBR = ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"]
CATS = {"ask": "Promotional", "help": "Educational", "belong": "Cultural",
        "real": "Community", "brand": "Brand", "affiliate": "Affiliate"}


# ---------------------------------------------------------------- helpers ---

def jfence(text, opener="["):
    """The whole fence body, not the first bracket pair — a non-greedy
    bracket match truncates any nested array (hit 2026-08-31)."""
    blocks = re.findall(r"```json\s*(.*?)```", text, re.S)
    for b in blocks:
        b = b.strip()
        if not b.startswith(opener):
            continue
        try:
            return json.loads(b)
        except json.JSONDecodeError:
            try:
                return json.JSONDecoder().raw_decode(b)[0]
            except Exception:
                continue
    sys.exit("stage returned no parseable ```json fence — read its raw output")


def creative_qc(tool, stage, run_dir, output, given=None, items=None):
    """THE CREATIVE QC LOOP (the owner, 2026-10-02: "installed for each of my
    production tools … for all stages in the creation process"): the output is
    reviewed against what it was given and the stage's bars
    (components/quality-checks/definitions/stages.json); the round is filed in
    <run>/qc-log/. Never stops the run on its own."""
    try:
        here = Path(__file__).resolve()
        comp = next(p for p in here.parents if (p / "quality-checks" / "marketing_chain_checks").is_dir())
        q = str(comp / "quality-checks")
        if q not in sys.path:
            sys.path.insert(0, q)
        from marketing_chain_checks import review
        f = review.after_stage(tool, stage, run_dir, output=output, items=items,
                               sources=[given] if given and Path(given).exists() else None)
        bad = [k for k, v in f.items() if isinstance(v, dict) and v.get("severity") in ("BLOCKER", "FIX")]
        if bad:
            print(f"  QC {stage}: {len(bad)} finding(s) — see qc-log/QC-LOG.md")
        return f
    except Exception as e:
        print(f"  QC {stage}: review not run ({type(e).__name__})")
        return {}


def run_ai(key, out_dir, model, stage_dir, **fields):
    """One thinking layer. The prompt AS ACTUALLY SENT and the full output land
    in the layer's own folder, and the file's sha is stamped — the prompt is
    the product, so a month has to be able to say which version decided it.

    Returns (output, meta). It records nothing itself: the caller hands the
    meta to `chain.done`, so every layer reaches the run record through one
    door and in one shape."""
    stage_dir.mkdir(parents=True, exist_ok=True)
    pf = latest_prompt(CH.BY_KEY[key]["prompt"])
    filled = fill(pf.read_text(), fields)
    (stage_dir / "prompt-sent.md").write_text(filled)
    # `model` is what --model forced, or None — then the layer's own tier picks.
    model, why = R.pick_model(key, len(filled), model)
    print(f"  -> layer {CH.BY_KEY[key]['n']}  ({pf.name} · {model}, {why})")
    t0 = time.time()
    output = R.claude(filled, model)     # looked up at call time, so a test can stub it
    secs = round(time.time() - t0, 1)
    (stage_dir / "reasoning.md").write_text(output + "\n")
    creative_qc("marketing-calendar", key, out_dir, stage_dir / "reasoning.md", stage_dir / "prompt-sent.md")
    rel = stage_dir.relative_to(out_dir)
    return output, {"seconds": secs, "chars_out": len(output), "model": model,
                    "model_why": why,
                    "prompt_name": pf.name, "prompt_sha256_12": sha(pf),
                    "reasoning": str(rel / "reasoning.md"),
                    "sent": str(rel / "prompt-sent.md")}


def save(out_dir, state):
    (out_dir / "run.json").write_text(json.dumps(state, indent=2) + "\n")


def month_bounds(month):
    y, mo = int(month[:4]), int(month[5:7])
    first = datetime.date(y, mo, 1)
    last = datetime.date(y + (mo == 12), (mo % 12) + 1, 1) - datetime.timedelta(days=1)
    return first, last


def L_avatars(brand_root):
    if C.L:
        return C.L.avatars(brand_root.name, WORKSPACE)
    return []


# ----------------------------------------------- layer 1 + 2: the skeleton ---

def resolve_moments(brand_root, month):
    """Every moment in the brand's calendar, resolved against THIS month from
    its anchor. Returns one row per (moment, avatar) with real dates."""
    first, last = month_bounds(month)
    y = first.year
    hol = {}
    for yr in (y - 1, y, y + 1):
        for r in H.table(yr):
            hol.setdefault(r["key"], []).append(r)
    data = json.loads(BP.brand_path(brand_root.name, "strategy", "moments.json", root=brand_root.parent).read_text())
    rows = []

    def overlaps(s, e):
        return s <= last and e >= first

    for av, block in data["avatars"].items():
        for m in block["moments"]:
            a = m.get("anchor") or {}
            row = dict(key=m["key"], avatar=av, audience=m.get("audience", av),
                       stream=m["stream"], evidence=m["evidence"],
                       note=m.get("note"), sent=m.get("sent") or [],
                       window_text=m.get("window", ""), kind=None,
                       start=None, end=None, peak=None, in_month=False)
            if a.get("live"):
                row["kind"] = "live"; row["in_month"] = True
            elif a.get("any"):
                row["kind"] = "any"; row["in_month"] = True
            elif a.get("holiday"):
                row["kind"] = "holiday"
                for r in hol.get(a["holiday"], []):
                    s = datetime.date.fromisoformat(r["start"])
                    e = s
                    if a.get("through"):
                        e2 = [x for x in hol.get(a["through"], [])
                              if datetime.date.fromisoformat(x["start"]) >= s]
                        if e2:
                            e = datetime.date.fromisoformat(e2[0]["end"])
                    else:
                        e = datetime.date.fromisoformat(r["end"])
                    # a holiday in the first days of next month is planned
                    # from this month (its run-up lives here)
                    if overlaps(s, e) or (last < s <= last + datetime.timedelta(days=10)):
                        row.update(start=s.isoformat(), end=e.isoformat(),
                                   peak=s.isoformat(), in_month=True,
                                   holiday_kind=r["kind"])
                        break
            elif a.get("window"):
                row["kind"] = "window"
                ms, me = a["window"]
                for yr in (y - 1, y, y + 1):
                    s = datetime.date(yr, int(ms[:2]), int(ms[3:]))
                    e = datetime.date(yr, int(me[:2]), int(me[3:]))
                    if e < s:                       # crosses the year end
                        e = datetime.date(yr + 1, int(me[:2]), int(me[3:]))
                    if overlaps(s, e):
                        row.update(start=s.isoformat(), end=e.isoformat(), in_month=True)
                        pk = a.get("peak")
                        if pk:
                            for r in hol.get(pk, []):
                                pd = datetime.date.fromisoformat(r["start"])
                                if s <= pd <= e:
                                    row["peak"] = pd.isoformat()
                                    row["peak_key"] = pk
                        break
            rows.append(row)
    return rows


def render_skeleton(month, hol_rows, moments, planned_keys):
    first, last = month_bounds(month)
    out = [f"# The month's skeleton — {first:%B %Y}", "",
           "## Public holidays landing in this month (real dates, the tool's table)"]
    if hol_rows:
        for r in hol_rows:
            when = r["start"] if r["span"] == 1 else f"{r['start']} to {r['end']}"
            flag = ("planned against" if r["key"] in planned_keys
                    else "NOT in this brand's calendar — available, unclaimed")
            out.append(f"- `{r['key']}` — {r['name']} · {when} · {r['kind']} · {flag}"
                       + (" · lead-in from next month" if r.get("lead_in") else ""))
    else:
        out.append("(none)")
    out += ["", "## This brand's cultural moments in window (resolved from their anchors)"]
    dated = [m for m in moments if m["in_month"] and m["kind"] in ("holiday", "window")]
    if dated:
        for m in sorted(dated, key=lambda x: x["start"]):
            when = (m["start"] if m["start"] == m["end"] else f"{m['start']} to {m['end']}")
            if m.get("peak") and m["peak"] != m["start"]:
                when += f" (peak {m['peak']})"
            out.append(f"- `{m['key']}` ({m['audience']}) · {m['stream']} · {when} · "
                       f"evidence: {m['evidence']}"
                       + (" · already sent: " + " / ".join(m["sent"]) if m["sent"] else ""))
            if m.get("note"):
                out.append(f"    ({m['note']})")
    else:
        out.append("(none)")
    live = [m for m in moments if m["kind"] == "live"]
    anyt = [m for m in moments if m["kind"] == "any"]
    out += ["", "## Live veins — cannot be planned; slots are held open for them"]
    out += [f"- `{m['key']}` ({m['avatar']}) · evidence: {m['evidence']}" for m in live] or ["(none)"]
    out += ["", "## Usable any time (no date claim)"]
    out += [f"- `{m['key']}` ({m['avatar']}) · evidence: {m['evidence']}" for m in anyt] or ["(none)"]
    out += ["", "Everything above is what this month IS. A moment not listed here is "
                "not in this month, and using it is a rule break."]
    return "\n".join(out)


# ------------------------------------------------------ layer 4: anchors ---

def holiday_history(brand_root, m, hol_names):
    """What this holiday has EARNED for this brand before — every past send
    whose campaign or subject names it, joined to its performance. Decides
    how long the build-up is (the owner, 2026-09-02: "3-4 build-up emails
    depending on the history of responsiveness of the audience to that
    holiday, so we can fully liquidate a list in that window")."""
    try:
        ledger = _json_or(brand_root / "email-sms/ledger.json", [])
        perf = {p["groupings"]["campaign_id"]: p["statistics"]
                for p in _json_or(brand_root / "email-sms/performance.json", [])}
    except (OSError, KeyError):
        return None
    words = {w.lower() for w in re.split(r"[^a-z']+", " ".join(hol_names).lower()) if len(w) > 3}
    words -= {"day", "week", "through"}
    words |= {w for w in m["key"].split("-") if len(w) > 3}
    hits = []
    for r in ledger:
        text = f"{r.get('campaign', '')} {r.get('subject', '')}".lower()
        if any(w in text for w in words):
            st = perf.get(r.get("id"), {})
            hits.append((r.get("sent"), r.get("subject"), st.get("revenue_per_recipient"),
                         st.get("recipients")))
    if not hits:
        return {"sends": 0, "ratio": None, "median": None, "hits": []}
    all_rpr = sorted(s["revenue_per_recipient"] for s in perf.values()
                     if s.get("recipients", 0) >= 1000 and s.get("revenue_per_recipient") is not None)
    median = all_rpr[len(all_rpr) // 2] if all_rpr else None
    got = [h[2] for h in hits if h[2] is not None]
    mean = sum(got) / len(got) if got else None
    ratio = (mean / median) if (mean is not None and median) else None
    return {"sends": len(hits), "ratio": ratio, "median": median, "mean": mean,
            "hits": sorted(hits, reverse=True)[:8]}


def build_up_length(hist):
    """1 send (the holiday itself) with no history; with history, the
    build-up scales with what the holiday earned against the brand's median
    revenue per recipient: weak 2 · at par 3 · strong 4."""
    if not hist or not hist["sends"]:
        return 1, "no prior send names this holiday — one holiday send, then the ask"
    r = hist["ratio"]
    if r is None:
        return 3, f"{hist['sends']} prior send(s), performance unjoined — three build-ups"
    if r >= 1.2:
        return 4, (f"{hist['sends']} prior send(s) earned {r:.1f}x the brand's median per "
                   "recipient — a strong holiday: four build-ups to liquidate the list")
    if r >= 0.8:
        return 3, f"{hist['sends']} prior send(s) earned {r:.1f}x the median — three build-ups"
    return 2, f"{hist['sends']} prior send(s) earned only {r:.1f}x the median — two build-ups"


BUILD_UP = ["anticipation", "proof-drop", "stack", "holiday"]   # last one is the day itself


def anchor_arcs(month, moments, cells, catalogue, brand_root=None, hol_rows=()):
    """Lay every dated moment onto the month at its real date, per live
    segment it fits. Deterministic. A retail or season-opening holiday is a
    full arc — warm-up, ask, close — around the day; an observance is one
    send on the day; a dated window with a peak (Christmas) is an arc that
    lands BEFORE the peak. Offers are left `[ASSIGN]` for the concepts stage
    to fill from the bank."""
    first, last = month_bounds(month)
    types = {t["key"]: t for t in catalogue["types"]}
    serve = [c for c in (cells or {}).get("serve", []) if c.get("live", True)]

    def clamp(d):
        return max(first, min(last, d))

    def fits(seg, m):
        vs = seg.get("variants") or []
        if m["audience"] == "all":
            return vs or [{"avatar": seg.get("avatar", "none"), "angle": ""}]
        hit = [v for v in vs if v.get("avatar") == m["audience"]]
        if not hit and seg.get("avatar") == m["audience"]:
            hit = [{"avatar": m["audience"], "angle": ""}]
        return hit

    # what gets anchored: a holiday landing in (or leading into) this month,
    # or a window whose PEAK lands in it — a Christmas window open in
    # November is in-window for concepts, but its arc belongs to December
    horizon = (last + datetime.timedelta(days=10)).isoformat()
    dated = [m for m in moments if m["in_month"] and m["kind"] in ("holiday", "window")
             and (m["kind"] == "holiday"
                  or (m.get("peak") and first.isoformat() <= m["peak"] <= horizon))]
    seen, anchors, n = set(), [], 0
    # audience-wide moments first, so a segment's one arc on a date is the
    # broad one; then dedup on (segment, date) — two moments on the same day
    # to the same segment would be two arcs on top of each other
    dated.sort(key=lambda x: (x["peak"] or x["start"], 0 if x["audience"] == "all" else 1))
    for m in dated:
        # ONE send per moment, to every live segment it fits — a holiday sale
        # is one email with several audiences, not several emails (the owner,
        # 2026-09-02: "that would get messy"). Variants are the union.
        segs, vs = [], []
        for seg in serve:
            key = (seg["segment"], m["peak"] or m["start"])
            if key in seen:
                continue
            hit = fits(seg, m)
            if not hit:
                continue
            seen.add(key)
            segs.append(seg["segment"])
            for v in hit:
                if v.get("avatar") not in {x.get("avatar") for x in vs}:
                    vs.append(v)
        if segs:
            s = datetime.date.fromisoformat(m["start"])
            e = datetime.date.fromisoformat(m["end"])
            hk = m.get("holiday_kind", "retail")
            # a retail or season-opening holiday sells; an observance
            # (Thanksgiving, Veterans Day) is marked, not sold; a window with
            # a peak (Christmas) sells, and lands before the peak
            sale = ((m["kind"] == "holiday" and hk in ("retail", "season-open"))
                    or (m["kind"] == "window" and bool(m.get("peak"))))
            if m.get("peak") and m["kind"] == "window":
                p = datetime.date.fromisoformat(m["peak"])
                warm, ask, close = p - datetime.timedelta(9), p - datetime.timedelta(6), p - datetime.timedelta(2)
            elif e > s:                                   # a through-window (Cyber Week)
                warm, ask, close = s - datetime.timedelta(3), s, e
            else:
                warm, ask, close = s - datetime.timedelta(4), s - datetime.timedelta(2), s
            gift = "gift" in m["key"] or m["key"] == "christmas"
            base = dict(cell={"segment": segs[0], "avatar": "mixed" if len(vs) > 1 else vs[0]["avatar"]},
                        segments=list(segs), variants=vs, occasion=m["key"], product="none",
                        anchored=True, moment_evidence=m["evidence"])
            if sale:
                n += 1
                aid = f"A{n}"
                ask_type = "gift-guide" if gift else "sale-window"
                names = [r["name"] for r in hol_rows
                         if r["key"] in ((m.get("peak_key") or ""), m["key"])] or [m["key"].replace("-", " ")]
                hist = holiday_history(brand_root, m, names) if brand_root else None
                n_up, reason = build_up_length(hist)
                ask_d = ask
                ups = BUILD_UP[-n_up:]
                # build-ups march toward the ask two days apart, the holiday
                # send itself closest to it. A member that falls outside this
                # month belongs to the month it falls in (the previous
                # month's run carries a lead-in) — never clamped onto day 1
                for i, tkey in enumerate(ups):
                    d = ask_d - datetime.timedelta(days=2 * (len(ups) - i))
                    if not (first <= d <= last):
                        continue
                    t = types.get(tkey, {})
                    anchors.append(dict(
                        base, anchor_id=f"{aid}-up{i + 1}", type=tkey,
                        category=CATS.get(t.get("well", "belong")), role=t.get("role", "earns"),
                        offer="none", _date=d.isoformat(),
                        product="none",
                        build_up=f"{i + 1} of {len(ups)}",
                        why=(f"build-up {i + 1} of {len(ups)} to the `{m['key']}` ask on "
                             f"{ask_d.isoformat()} — {reason} (anchored by code, layer 4)")))
                if first <= ask_d <= last:
                    anchors.append(
                        dict(base, anchor_id=aid, type=ask_type, category="Promotional", role="asks",
                             offer="[ASSIGN]", _date=ask_d.isoformat(),
                             why=f"the ask of the `{m['key']}` arc on its real date window "
                                 f"({m['start']}{' to ' + m['end'] if m['end'] != m['start'] else ''}) — "
                                 f"a {hk} moment; offer assigned from the bank in layer 5",
                             history=hist))
                if first <= close <= last:
                    anchors.append(
                        dict(base, anchor_id=f"{aid}-close", type="last-chance", category="Promotional",
                             role="recovers", offer="[ASSIGN]", _date=close.isoformat(),
                             why=f"close of the `{m['key']}` arc on {close.isoformat()} — the last day "
                                 "the offer stands; the offer travels with it"))
            elif first <= s <= last:
                n += 1
                anchors.append(dict(base, anchor_id=f"A{n}", type="moment", category="Cultural",
                                    role="earns", offer="none", _date=s.isoformat(),
                                    why=f"`{m['key']}` on its day, {m['start']} — an observance, marked, "
                                        "not sold (anchored by code, layer 4)"))
    return anchors


def render_anchors(anchors):
    if not anchors:
        return "(nothing anchored — no dated moment lands in this month for a live segment)"
    out = []
    for a in anchors:
        h = a.get("history")
        if h and h.get("sends"):
            out.append(f"\n**`{a['occasion']}` — what it earned before:** {h['sends']} send(s)"
                       + (f", ${h['mean']:.4f}/recipient vs the brand median ${h['median']:.4f}"
                          f" ({h['ratio']:.1f}x)" if h.get("ratio") else "")
                       + "\n" + "\n".join(f"    - {d} · “{s}”" + (f" · ${r:.4f}/recipient" if r else "")
                                          for d, s, r, _ in h["hits"]))
        vs = ", ".join(v["avatar"] for v in a["variants"])
        segs = a.get("segments") or [a["cell"]["segment"]]
        to = segs[0] if len(segs) == 1 else f"ONE send to {len(segs)} segments ({', '.join(x.replace('Core | ', '') for x in segs)})"
        out.append(f"- **{a['anchor_id']}** · {a['_date']} · {to} · "
                   f"`{a['type']}` ({a['role']}) · {a['occasion']} · offer: {a['offer']} · "
                   f"variants: {vs}")
    return "\n".join(out)


# ---------------------------------------- layers 6 + 7: catalogue, offers ---

def expand_arcs(moves, catalogue):
    """Every offer-carrying ask from the concepts stage becomes a complete
    arc — warm-up, ask, cool-down — from the catalogue's arc index. A
    promotional moment is never one email (RULED 2026-08-31)."""
    types = {t["key"]: t for t in catalogue["types"]}
    out, added, n = [], 0, 0
    for m in moves:
        out.append(m)
        if m.get("anchored"):
            continue
        spec = types.get(m.get("type"), {})
        arc = spec.get("arc") or {}
        off = str(m.get("offer") or "none").strip().lower()
        if spec.get("role") != "asks" or off.startswith("none"):
            continue
        n += 1
        m["_arc"] = f"C{n}"                 # a stable label — survives JSON, unlike id()
        seg = m.get("cell", {}).get("segment")
        pd = m.get("preferred_date") or ""
        # a peer already in the plan can serve as the warm-up (dated before
        # the ask) or the cool-down (dated after) — and then it is LINKED to
        # the ask, because an unlinked earns send is not an arc (the checker
        # wants follows/then, not proximity)
        free = [x for x in moves if x.get("cell", {}).get("segment") == seg and x is not m
                and "arc_for" not in x and not x.get("anchored")]
        warm_peers = sorted([x for x in free if x.get("type") in arc.get("warm_up", [])
                             and (x.get("preferred_date") or "") <= pd],
                            key=lambda x: x.get("preferred_date") or "", reverse=True)
        cool_peers = sorted([x for x in free if x.get("type") in arc.get("cool_down", [])
                             and (x.get("preferred_date") or "") > pd],
                            key=lambda x: x.get("preferred_date") or "")
        has_warm = has_cool = False
        if warm_peers:
            warm_peers[0]["arc_for"] = m["_arc"]; has_warm = True
        if cool_peers:
            cool_peers[0]["arc_for"] = m["_arc"]; has_cool = True
            # a linked cool-down closes the ask's offer, exactly as a generated
            # one does (make() below): left offer-free, a guarantee cool-down
            # breaks "needs an offer" (FOLD Y5, 2026-09-23)
            if str(cool_peers[0].get("offer") or "none").strip().lower().startswith("none"):
                cool_peers[0]["offer"] = m.get("offer")

        def make(kind, key, shift):
            t = types.get(key, {})
            d = None
            if pd:
                try:
                    d0 = datetime.date.fromisoformat(pd)
                    d1 = d0 + datetime.timedelta(days=shift)
                    # a cool-down stays inside the month: an ask late in the
                    # month closes on the month's last day, never in the next
                    last_ = (d0.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
                    if d1 > last_:
                        d1 = max(last_, d0 + datetime.timedelta(days=1))
                    if d1 < d0.replace(day=1):
                        d1 = d0.replace(day=1)
                    d = d1.isoformat()
                except ValueError:
                    d = None
            return {"cell": dict(m.get("cell", {})), "type": key,
                    "category": CATS[t.get("well", "ask")], "role": t.get("role"),
                    "occasion": m.get("occasion"), "product": m.get("product", "none"),
                    "offer": m.get("offer") if kind == "cool" else "none",
                    "preferred_date": d, "arc_generated": True, "arc_for": m["_arc"],
                    "why": (f"{kind}-{'up' if kind == 'warm' else 'down'} for the "
                            f"{m.get('type')} on {m.get('occasion')} — a promotional moment "
                            "is never one email (RULED 2026-08-31); from the catalogue's arc index")}
        # an ask on the month's last days moves up so its close can follow it
        if not has_cool and arc.get("cool_down") and pd:
            try:
                d0 = datetime.date.fromisoformat(pd)
                last_ = (d0.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
                if d0 >= last_ - datetime.timedelta(days=1):
                    pd = (last_ - datetime.timedelta(days=2)).isoformat()
                    m["preferred_date"] = pd
                    m["why"] = (m.get("why") or "") + " · moved up two days so its close lands inside the month"
            except ValueError:
                pass
        if not has_warm and arc.get("warm_up"):
            out.insert(len(out) - 1, make("warm", arc["warm_up"][0], -3)); added += 1
        if not has_cool and arc.get("cool_down"):
            out.append(make("cool", arc["cool_down"][0], 2)); added += 1
    return out, added


BANK_NOTES = {"guarantee", "social-proof", "cadence", "rules", "open",
              "funnel-shape", "page-pricing", "sms-capture",
              # note headings a bank may carry under the same style (Brand A's):
              "two-prices", "never-pair", "subscribe-save", "promo-calendar",
              "live-prices", "product-facts", "notes", "context"}


def offer_bank(brand_root, roster=()):
    """{avatar: {offer_key, ...}} — what each avatar may actually carry.

    THE SECOND READER. `brandrecord.render_offers` shows the bank to the model;
    this checks what the model came back with, and on 2026-09-14 the two
    disagreed: the model was correctly offered `glow-duo-bundle`, chose it, and
    this function then stripped it as "not in the offer bank at all". Two
    parsers of one file is how a brand loses its offers in a way that looks
    like the machine being careful.

    So it reads through the same rule now — a heading is an offer when its
    section says what the thing costs — and a FLAT bank (brand-wide, the owner's
    2026-09-13 shape) gives every avatar the same set, because those offers
    belong to the brand rather than to one avatar.
    """
    f = BP.brand_path(brand_root.name, "products", "offer-bank.md", root=brand_root.parent)
    if not f.is_file():
        return {}
    text = f.read_text()
    roster = list(roster)
    if C.bank_is_per_avatar(text, roster):
        bank, av = {}, None
        for ln in text.splitlines():
            if ln.startswith("## "):
                av = ln[3:].strip(); bank.setdefault(av, set())
            elif ln.startswith("### ") and av:
                key = ln[4:].strip().split(" ")[0].strip("`")
                if key not in BANK_NOTES:
                    bank[av].add(key)
        return bank
    keys = {ln.split("`")[1] for ln in C.render_offers(brand_root, roster).splitlines()
            if ln.startswith("- OFFER `")}
    return {a: set(keys) for a in roster} or {"all": keys}


def apply_offers(moves, assignments, brand_root):
    """Layer 7. Every offer on every send is checked against the brand's
    offer bank — the ONLY place an offer can come from (the owner, 2026-09-02).
    An anchored `[ASSIGN]` takes the concepts stage's assignment; an offer no
    variant of the send can carry is a documented borrow if it exists under
    another avatar, and stripped to none if it exists nowhere. An ask left
    with no offer collapses its arc to the warm-up send alone."""
    bank = offer_bank(brand_root, [a['key'] for a in L_avatars(brand_root)])
    every = set().union(*bank.values()) if bank else set()
    assign = {a.get("anchor_id"): a for a in (assignments or [])}
    log, out = [], []
    dead_anchor, dead_arc = set(), set()

    for m in moves:
        off = str(m.get("offer") or "none").strip()
        aid = m.get("anchor_id", "")
        if off == "[ASSIGN]":
            base = aid.replace("-close", "")
            a = assign.get(base)
            off = str((a or {}).get("offer") or "none").strip()
            m["offer"] = off
            if a and not off.lower().startswith("none"):
                m["why"] += f" · offer `{off}`: {a.get('why', '')}"
        if off.lower().startswith("none") or off.startswith("["):
            m["offer"] = "none"
            continue
        avs = [v["avatar"] for v in (m.get("variants") or [])] or [m.get("cell", {}).get("avatar")]
        carriers = [av for av in avs if off in bank.get(av, set())]
        if carriers:
            continue
        if off in every:
            owner = next(av for av, ks in bank.items() if off in ks)
            m["why"] += (f" · [UNFILLED: {', '.join(a for a in avs if a)} has no section in the "
                         f"offer bank — `{off}` is borrowed from {owner}'s section]")
            log.append(f"- {m.get('cell', {}).get('segment')} · `{m.get('type')}` on "
                       f"{m.get('occasion')}: `{off}` borrowed from {owner} (documented)")
            continue
        log.append(f"- {m.get('cell', {}).get('segment')} · `{m.get('type')}` on "
                   f"{m.get('occasion')}: `{off}` is not in the offer bank at all — STRIPPED")
        m["offer"] = "none"

    for m in moves:
        if m.get("role") == "asks" and str(m.get("offer", "none")).lower().startswith("none"):
            if m.get("anchored"):
                dead_anchor.add(m.get("anchor_id"))
            elif not m.get("arc_generated") and m.get("_arc"):
                dead_arc.add(m["_arc"])
    for m in moves:
        aid = m.get("anchor_id", "")
        base = re.sub(r"-(warm|close|up\d+)$", "", aid)
        is_up = bool(re.search(r"-(warm|up\d+)$", aid))
        if m.get("anchored") and base in dead_anchor and not is_up:
            log.append(f"- {m.get('cell', {}).get('segment')} · `{m['occasion']}` arc: no offer any "
                       f"variant can carry — collapsed to its holiday send; `{m['type']}` dropped")
            continue
        if m.get("anchored") and base in dead_anchor and is_up:
            # the holiday send now stands alone: `holiday` obliges a gift-guide
            # that will never come, so it is the plain `moment` on the day
            m["type"], m["role"] = "moment", "earns"
            m["why"] = (f"`{m['occasion']}` marked, not sold — no offer any variant of this "
                        "segment can carry, so the arc collapsed to this one send")
        if m.get("arc_generated") and m.get("arc_for") in dead_arc:
            log.append(f"- {m.get('cell', {}).get('segment')} · `{m['occasion']}`: ask lost its "
                       f"offer — generated `{m['type']}` dropped with it")
            continue
        if not m.get("arc_generated") and m.get("arc_for") in dead_arc:
            m.pop("arc_for")                          # a peer stands on its own again
        if not m.get("anchored") and not m.get("arc_generated") and m.get("_arc") in dead_arc:
            m["why"] += " · [offer stripped — this ask now stands as a plain send]"
        out.append(m)
    return out, log


def ensure_weekly_affiliate(moves, month, brand_root, cells):
    """Layer 8: one affiliate feature every week — a standing business
    requirement (the owner's investor, 2026-09-01). Never invents a partner."""
    f = brand_root / "email-sms" / "affiliates.json"
    if not f.is_file():
        return moves, 0, ("this brand has no affiliate roster on file — the weekly "
                          "slot is a commitment for brands that have partners, not a "
                          "rule about what a month must contain. Nothing scheduled.")
    doc = _json_or(f, {})
    rows = doc.get("affiliates")
    if rows is None:
        # The roster is there under a name this reader does not know. Silence
        # would be the worst answer: a partner the brand has recorded would
        # never be scheduled and nobody would ever find out. Brand A spent its
        # whole life in exactly that state under the key `partners` (2026-09-13).
        lists = {k: v for k, v in doc.items() if isinstance(v, list)}
        if lists:
            k = next(iter(lists))
            return moves, 0, (f"affiliates.json holds its roster under `{k}`, not "
                              f"`affiliates` — {len(lists[k])} partner(s) NOT scheduled. "
                              f"Rename the key; nothing else is wrong.")
        rows = []
    partners = [a for a in rows if a.get("status", "active") == "active"]
    if not partners:
        return moves, 0, ("the affiliate roster is empty — no partner recorded yet, "
                          "so nothing is scheduled")
    first, last = month_bounds(month)
    weeks = sorted({(first + datetime.timedelta(d)).isocalendar()[1]
                    for d in range((last - first).days + 1)})
    already = sum(1 for mv in moves if mv.get("category") == "Affiliate")
    shortfall = max(0, len(weeks) - already)
    if not shortfall:
        return moves, 0, f"{already} affiliate move(s) already cover the {len(weeks)} week(s)"
    serve = [c for c in (cells or {}).get("serve", []) if c.get("live", True)]
    seg = max(serve, key=lambda s: s.get("audience", 0), default=None)
    segment = (seg or {}).get("segment")
    if not segment:
        return moves, 0, "no live segment to carry it — cells stage served nothing"
    out = list(moves)
    for i in range(shortfall):
        wk = weeks[(already + i) % len(weeks)]
        in_week = [first + datetime.timedelta(d) for d in range((last - first).days + 1)
                   if (first + datetime.timedelta(d)).isocalendar()[1] == wk]
        day = next((x for x in in_week if x.weekday() == 2), in_week[len(in_week) // 2])
        partner = partners[(first.year * 12 + first.month + already + i) % len(partners)]
        out.append({"cell": {"segment": segment, "avatar": "none"}, "variants": [],
                    "type": "affiliate-feature", "category": "Affiliate", "role": "earns",
                    "occasion": f"affiliate: {partner.get('name', partner.get('key'))}",
                    "product": "none", "offer": "none",
                    "preferred_date": day.isoformat(),
                    "why": ("the standing weekly affiliate slot (RULED 2026-09-01 — an "
                            "investor commitment, not a data signal)"),
                    "affiliate": partner.get("key"), "arc_generated": False})
    return out, shortfall, f"{shortfall} weekly affiliate slot(s) added ({already} already proposed)"


def moment_windows(moments, run_up=11):
    """{key: [(start, end), ...]} — the dates a moment may be used on this
    month. A dated holiday's window reaches back `run_up` days, because its
    arc legitimately starts before the day (warm-up on the 3rd for the 7th);
    a peaked window reaches to its peak; `any`/`live` carry (None, None)."""
    out = {}
    for m in moments:
        if not m["in_month"]:
            continue
        if m["kind"] in ("any", "live"):
            out.setdefault(m["key"], []).append((None, None))
        elif m["start"]:
            s = datetime.date.fromisoformat(m["start"])
            if m["kind"] == "holiday":
                s -= datetime.timedelta(days=run_up)
            out.setdefault(m["key"], []).append((s.isoformat(), m["end"]))
    return out


# ------------------------------------------------------- layer 9: order ---

def window_of(mv, windows, first, last):
    """The dates a move may sit on: its moment's window, clipped to the month;
    the whole month when it is on no dated moment."""
    occ = (mv.get("occasion") or "").lower()
    lo, hi = first, last
    for key, wins in (windows or {}).items():
        if re.search(r"(?<![a-z0-9-])" + re.escape(key) + r"(?![a-z0-9-])", occ):
            spans = [(a, b) for a, b in wins if a is not None]
            if spans:
                lo = max(first, datetime.date.fromisoformat(min(a for a, _ in spans)))
                hi = min(last, datetime.date.fromisoformat(max(b for _, b in spans)))
            break
    return lo, hi


def broken_arcs(placed, catalogue, month, windows):
    """The concept arcs (layer 6's C1, C2 …) that layer 9 could not lay out
    whole: a member dropped or spilled past the month, no warm-up dated before
    an ask whose type calls for one, or a close dated past its moment's window.
    `placed` is the move list order_month has just dated in place."""
    first, last = month_bounds(month)
    types = {t["key"]: t for t in catalogue["types"]}
    asks = {mv["_arc"]: mv for mv in placed if mv.get("_arc")}
    out = []
    for label, ask in asks.items():
        members = [mv for mv in placed if mv.get("arc_for") == label]
        if ask.get("_overflow") or any(m.get("_dropped_arc") or m.get("_overflow") for m in members):
            out.append(label); continue
        ad = ask.get("_date")
        arc = types.get(ask.get("type"), {}).get("arc") or {}
        if arc.get("warm_up") and not any((m.get("_date") or "") < ad
                                          for m in members if m.get("_date")):
            out.append(label); continue
        _, hi = window_of(ask, windows, first, last)
        if any(m.get("role") in ("recovers", "closes") and m.get("_date")
               and m["_date"] > hi.isoformat() for m in members):
            out.append(label)
    return out


def fit_month(moves, month, brand_root, catalogue, findings_txt, windows=None):
    """Layer 9, laid out so no concept arc breaks. One send a day stands, and
    no send budget exists — so when a moment's window cannot hold every arc
    whole, the send the planner RANKED LOWEST among those crowding it leaves:
    a whole arc (warm-up, ask and close together) or a single send dated
    inside that window. Rank is the order layer 5 wrote the moves in. Never a
    warm-up alone, never a close pushed past its moment. Repeated until every
    arc left stands whole; anchored (dated holiday) sends are never cut here
    (2026-09-23, the email lead: "update the calendar following the rules so
    nothing breaks").

    Brand A's October is why: 25 sends planned into after-summer-reset's
    fifteen days (Oct 1-15) at one send a day — layer 9 then dropped every
    generated warm-up and pushed eight closes past the 15th."""
    first, last = month_bounds(month)
    rank = {id(mv): i for i, mv in enumerate(moves)}
    notes, cut = [], []
    while True:
        trial = copy.deepcopy(moves)
        slots, dropped, log = order_month(trial, month, brand_root, catalogue,
                                          findings_txt, windows=windows)
        broken = broken_arcs(trial, catalogue, month, windows)
        if not broken:
            return slots, dropped + cut, log + notes
        # the units competing for the broken arcs' days: the broken arcs, and
        # every single (non-arc, non-anchored) send dated inside their windows
        spans = [window_of(next(mv for mv in trial if mv.get("_arc") == lb),
                           windows, first, last) for lb in broken]
        units = [[mv for mv in moves if mv.get("_arc") == lb or mv.get("arc_for") == lb]
                 for lb in broken]
        for orig, tr in zip(moves, trial):
            if orig.get("_arc") or orig.get("arc_for") or orig.get("anchored"):
                continue
            d = tr.get("_date")
            if d and any(lo.isoformat() <= d <= hi.isoformat() for lo, hi in spans):
                units.append([orig])
        gone = max(units, key=lambda u: min(rank[id(mv)] for mv in u))
        head = next((mv for mv in gone if mv.get("_arc")), gone[0])
        what = (f"arc {head['_arc']} ({len(gone)} sends)" if head.get("_arc")
                else "a single send")
        notes.append(f"- {head['cell']['segment']} · `{head.get('type')}` — {what}: CUT. "
                     f"A concept arc could not stand whole (warm-up, ask and close on "
                     f"the right days, inside its moment) at one send a day, and this "
                     f"was the lowest-ranked send crowding that window.")
        cut += gone
        moves = [mv for mv in moves if all(mv is not g for g in gone)]


def order_month(moves, month, brand_root, catalogue, findings_txt, windows=None):
    """Dates resolved around the anchors (which already carry theirs),
    hours, sources, links. Deterministic. No send budget exists; the only
    thing refused is an exact duplicate — the same type on the same occasion
    to the same segment."""
    first, last = month_bounds(month)
    types = {t["key"]: t for t in catalogue["types"]}
    hour, local = 17, True
    mh = re.search(r"best-evidenced hour is (\d{1,2}):", findings_txt or "")
    if mh:
        hour = int(mh.group(1))

    # exact duplicates
    kept, dropped, seen = [], [], set()
    for mv in moves:
        key = (mv.get("cell", {}).get("segment"), mv.get("type"),
               (mv.get("occasion") or "")[:40], mv.get("anchor_id", ""))
        if key in seen:
            dropped.append(mv); continue
        seen.add(key); kept.append(mv)

    # dates: anchors first (fixed), then everything else into free days
    taken = {}                                   # segment -> set(date)
    day_used = set()                             # every date already carrying a send
    # ONE SEND A DAY (RULED 2026-09-10, the owner: "let's only do 1 send, not 2 on a
    # day for now"). A send may still go out in several versions, one per
    # avatar — that is one send. Two different sends never share a date.
    def busy(seg, d):
        return d in taken.get(seg, set())
    def taken_day(d):
        return d in day_used
    def take(seg, d):
        taken.setdefault(seg, set()).add(d); day_used.add(d)
    for mv in kept:
        if mv.get("_date"):
            take(mv["cell"]["segment"], mv["_date"])
    log = []
    # asks and stand-alone sends first; the warm-ups and cool-downs of a
    # concept arc are dated AFTER their ask is, so they land on the right
    # side of it (a cool-down placed before its ask is not a cool-down)
    ask_date = {}
    undated = [mv for mv in kept if not mv.get("_date")]
    undated.sort(key=lambda mv: 1 if mv.get("arc_for") else 0)
    for mv in undated:
        seg = mv["cell"]["segment"]
        want = mv.get("preferred_date")
        try:
            d = datetime.date.fromisoformat(want)
            if not (first <= d <= last):
                raise ValueError
        except (TypeError, ValueError):
            # no usable preference: the emptiest stretch this segment has
            days = [first + datetime.timedelta(i) for i in range((last - first).days + 1)]
            d = max(days, key=lambda x: min([abs((x - datetime.date.fromisoformat(t)).days)
                                             for t in taken.get(seg, set())] or [99]))
            log.append(f"- {seg} · `{mv.get('type')}`: no usable preferred date — placed in its "
                       f"emptiest stretch, {d.isoformat()}")
        # a move on a moment may only shift INSIDE that moment's window
        lo, hi = window_of(mv, windows, first, last)
        if mv.get("arc_for") and mv["arc_for"] in ask_date:
            ad = datetime.date.fromisoformat(ask_date[mv["arc_for"]])
            if mv.get("role") in ("recovers", "closes"):
                lo, hi = max(first, ad + datetime.timedelta(1)), last   # may trail the window
                d = max(d, ad + datetime.timedelta(1))
            else:
                # a warm-up sits before its ask — but never before its
                # moment's window; if the ask is on the window's first day
                # the warm-up shares it and the checker reads that
                hi = max(lo, min(hi, ad - datetime.timedelta(1)))
                d = max(lo, min(d, ad - datetime.timedelta(1)))
        if not (lo <= d <= hi):
            d = max(lo, min(hi, d))

        def free(x):
            return (lo <= x <= hi and not taken_day(x.isoformat())
                    and not busy(seg, x.isoformat())
                    and not busy(seg, (x - datetime.timedelta(1)).isoformat())
                    and not busy(seg, (x + datetime.timedelta(1)).isoformat()))
        placed = None
        for off in range(0, 16):                      # nearest free day, either side
            for cand in (d + datetime.timedelta(off), d - datetime.timedelta(off)):
                if free(cand):
                    placed = cand; break
            if placed:
                break
        if placed is None:                            # dense: any free day in range
            # the whole month, not just the window: a second send never shares a day
            span = [first + datetime.timedelta(i) for i in range((last - first).days + 1)]
            # ...but NEVER outside this move's own bounds first. Those bounds are
            # what keep a cool-down after its ask, and this fallback used to
            # ignore them: Brand A's `guarantee` wanted the 27th, found it taken,
            # and was moved to the 21st — four days BEFORE the sale it was
            # supposed to close (2026-09-14). A reassurance email before the
            # offer exists is not a cool-down, it is a mistake with a date on it.
            inside = [x for x in span if lo <= x <= hi]
            placed = next((x for x in sorted(inside, key=lambda x: abs((x - d).days))
                           if not taken_day(x.isoformat())), None)
            if placed is None and mv.get("arc_for"):
                # An arc member that cannot sit on the right side of its ask is
                # DROPPED, not relocated. A `guarantee` four days before the
                # sale it exists to close is worse than no guarantee at all —
                # it is a wrong email rather than a missing one, and the reader
                # cannot tell it was a scheduling accident. Brand A's September
                # is 16 days holding 17 sends; this is what full looks like.
                mv["_dropped_arc"] = True
                log.append(f"- {seg} · `{mv.get('type')}`: no free day left between "
                           f"{lo.isoformat()} and {hi.isoformat()}, where it belongs "
                           f"relative to its ask — DROPPED rather than placed out of "
                           f"order. The month is full; cut another send to make room "
                           f"for it, or let the arc stand short.")
                continue
            if placed is None:
                placed = next((x for x in sorted(span, key=lambda x: abs((x - d).days))
                               if not taken_day(x.isoformat())), None)
            if placed is None:
                # the month is full. One send a day outranks staying inside the
                # month, so the overflow spills onto the first free day after it
                # and is named as an overflow for a human to keep or cut.
                x = last + datetime.timedelta(1)
                while taken_day(x.isoformat()):
                    x += datetime.timedelta(1)
                placed = x
                mv["_overflow"] = True
                log.append(f"- {seg} · `{mv.get('type')}`: every day in {month} already carries a "
                           f"send (one a day) — this one spilled past the month onto "
                           f"{placed.isoformat()}; keep it there or cut it")
        if placed != d:
            log.append(f"- {seg} · `{mv.get('type')}`: preferred {d.isoformat()} already carried a "
                       f"send (one a day) or sat next to this segment's own — moved to "
                       f"{placed.isoformat()}")
        mv["_date"] = placed.isoformat(); take(seg, mv["_date"])
        if mv.get("_arc"):
            ask_date[mv["_arc"]] = mv["_date"]
    kept = [mv for mv in kept if not mv.get("_dropped_arc")]
    ordered = sorted(kept, key=lambda x: (x["_date"], x["cell"]["segment"]))

    # SOURCES — the FORMAT each send is written off.
    #
    # A send is written off a real email whose structure it borrows, so a brand
    # that has never sent anything has no formats of its own and every slot
    # comes out unfilled. the owner, 2026-09-14: "some brands might not have them,
    # and you got to develop them from scratch, or you use swipe files... these
    # are things that we have to make sure that the code is also checking for."
    #
    # So the pool is built in declared order and NO BRAND IS NAMED HERE.
    # Borrowing is a decision, written into the brand's own
    # email/format-sources.json with who made it and why. A borrowed source
    # carries the brand it came from, so nothing downstream has to guess.
    by_type, by_cat = {}, {}

    def add_pool(rows, from_brand=None):
        for r in sorted(rows, key=lambda r: r.get("sent", ""), reverse=True):
            ref = (from_brand, r["file"])
            by_type.setdefault(r.get("type"), []).append(ref)
            by_cat.setdefault(CATS.get(r.get("category"), r.get("category")),
                              []).append(ref)

    add_pool(_json_or(brand_root / "email-sms/classified.json", []))
    own = sum(len(v) for v in by_type.values())
    borrowed_from = []
    for b in (_json_or(brand_root / "email-sms/format-sources.json", {})
              .get("borrowed") or []):
        other = b.get("brand")
        if not other or other == brand_root.name:
            continue
        rows = _json_or(BP.brand_path(other, "email-sms", "classified.json",
                                      root=WORKSPACE / "brands"), [])
        want = b.get("types")
        if isinstance(want, list):
            rows = [r for r in rows if r.get("type") in want]
        if rows:
            add_pool(rows, from_brand=other)
            borrowed_from.append(f"{other} ({len(rows)})")
    if borrowed_from:
        print(f"     formats: {own} of this brand's own, borrowing from "
              + ", ".join(borrowed_from))
    elif not own:
        print("     NOTE: this brand has no sent emails to take formats from, and "
              "no borrowing is declared in email/format-sources.json — every slot "
              "will come out unfilled")

    used = set()

    def pick(mv):
        for pool in (by_type.get(mv.get("type"), []),
                     by_cat.get(mv.get("category"), [])):
            for ref in pool:
                if ref not in used:
                    used.add(ref)
                    return ref
        return (None, "[UNFILLED: no source of this type, own or borrowed]")

    slots, mo = [], first.month
    for i, mv in enumerate(ordered, 1):
        cell = mv.get("cell", {})
        spec = types.get(mv.get("type"), {})
        vs = mv.get("variants") or []
        src_brand, src_file = pick(mv)
        slots.append({
            "id": f"{MONTH_ABBR[mo - 1]}-{i:02d}", "date": mv["_date"], "hour": hour,
            "local": local, "segment": cell.get("segment"),
            "segments": list(mv.get("segments") or [cell.get("segment")]),
            "avatar": ("mixed" if len(vs) > 1 else (vs[0]["avatar"] if vs else cell.get("avatar", "none"))),
            "variants": vs,
            "category": mv.get("category") or CATS.get(spec.get("well", "help")),
            "type": mv.get("type"), "role": spec.get("role", mv.get("role")),
            "occasion": mv.get("occasion"), "product": mv.get("product", "none"),
            "offer": mv.get("offer", "none"), "follows": None, "then": None,
            "spent": f"see the library for prior `{mv.get('type')}` sends",
            "source": src_file, "source_brand": src_brand,
            "why": mv.get("why", ""),
            "anchored": bool(mv.get("anchored")),
            "arc_generated": bool(mv.get("arc_generated")),
            "affiliate": mv.get("affiliate"),
        })
    # links: anchored arcs by anchor id; concept arcs by their stable label
    by_mv = {id(mv): s for mv, s in zip(ordered, slots)}
    groups = {}
    for mv in ordered:
        aid = mv.get("anchor_id")
        if aid:
            groups.setdefault(("A", re.sub(r"-(warm|close|up\d+)$", "", aid),
                               mv["cell"]["segment"]), []).append(mv)
        elif mv.get("arc_for"):                       # generated, or a peer linked in
            groups.setdefault(("G", mv["arc_for"]), []).append(mv)
        elif mv.get("_arc"):                          # the ask itself
            groups.setdefault(("G", mv["_arc"]), []).append(mv)
    for g in groups.values():
        chain = [by_mv[id(x)] for x in sorted(g, key=lambda x: x["_date"])]
        for a, b in zip(chain, chain[1:]):
            a["then"] = b["id"]; b["follows"] = a["id"]
    slots, merged = merge_sends(slots, MONTH_ABBR[mo - 1])
    log += merged
    return slots, dropped, log


def merge_sends(slots, abbr):
    """The same email going to several segments is ONE send with several
    segments, not several sends (the owner, 2026-09-02: "that would get messy").
    Same date, type, occasion, product and offer -> one slot carrying
    `segments`; variants are the union by avatar; links follow the merge."""
    key = lambda s: (s["date"], s["type"], (s.get("occasion") or "").lower(),
                     s.get("product"), s.get("offer"), s.get("affiliate"))
    groups, order = {}, []
    for s in slots:
        k = key(s)
        if k not in groups:
            groups[k] = []; order.append(k)
        groups[k].append(s)
    alias, out, log = {}, [], []
    for k in order:
        g = groups[k]
        prime = g[0]
        segs = []
        for s in g:
            for x in (s.get("segments") or [s["segment"]]):
                if x not in segs:
                    segs.append(x)
        prime["segments"] = segs
        prime["segment"] = segs[0]
        if len(g) > 1:
            vs = []
            for s in g:
                for v in s.get("variants") or []:
                    if v.get("avatar") not in {x.get("avatar") for x in vs}:
                        vs.append(v)
            prime["variants"] = vs
            prime["avatar"] = "mixed" if len(vs) > 1 else (vs[0]["avatar"] if vs else prime["avatar"])
            prime["why"] = f"ONE send to {len(segs)} segments — " + prime["why"]
            for s in g[1:]:
                alias[s["id"]] = prime["id"]
            log.append(f"- {prime['date']} `{prime['type']}` on {prime.get('occasion')}: "
                       f"{len(g)} identical sends merged into one, to {', '.join(x.replace('Core | ', '') for x in segs)}")
        out.append(prime)
    # renumber in date order, remap links through the merge
    out.sort(key=lambda s: (s["date"], s["segment"]))
    renum = {}
    for i, s in enumerate(out, 1):
        renum[s["id"]] = f"{abbr}-{i:02d}"
    def fix(ref):
        if not ref:
            return ref
        ref = alias.get(ref, ref)
        return renum.get(ref, ref)
    for s in out:
        s["follows"], s["then"] = fix(s.get("follows")), fix(s.get("then"))
        s["id"] = renum[s["id"]]
    return out, log


# ------------------------------------------------------------------ main ---

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("month")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--model", default=None,
                    help="force ONE model onto both thinking layers. Left off, each "
                         "layer takes its tier from the run kit (both are `designs`)")
    ap.add_argument("--dry-run", "--dry", dest="dry_run", action="store_true",
                    help="spend nothing and write nothing: check the brand, run "
                         "layers 1-2, resolve both prompts and every field they "
                         "would be handed. Exits non-zero on a blocked brand")
    ap.add_argument("--continue", dest="cont", action="store_true",
                    help="resume from a hand-edited 3-cells/cells.json")
    ap.add_argument("--stop-at-cells", action="store_true",
                    help="pause after the cells stage — off by default")
    ap.add_argument("--reorder", action="store_true",
                    help="re-run layer 9 and the board only, from the moves already "
                         "on disk (8-affiliate/affiliate.json) — no AI, no cost; for "
                         "a change to ordering or checking rules")
    ap.add_argument("--start-day", type=int, default=None,
                    help="production starts on this day of the month: slots dated before it "
                         "are dropped from the order and the briefs (the owner, 2026-09-09: "
                         "September runs from the 14th)")
    ap.add_argument("--out", default=None,
                    help="where the month lands (default: runs/marketing-calendar/ "
                         "at the repo root; the month goes in <out>/<brand>/<month>/). "
                         "Every write goes under it — components rule 8, so this "
                         "engine makes no assumption about the machine it runs on")
    ap.add_argument("--from-anchors", action="store_true",
                    help="re-run layers 4-9 and the board from the cells and concepts "
                         "already on disk — no AI, no cost; for a change to how "
                         "holidays are anchored")
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        sys.exit(f"month must be YYYY-MM, got {args.month!r}")

    out_root = Path(args.out).expanduser().resolve() if args.out else RUNS
    if args.dry_run:
        import dryrun
        sys.exit(dryrun.run(args, sys.modules[__name__], out_root))
    out_root.mkdir(parents=True, exist_ok=True)
    import paths
    brand_root = paths.brand_root(args.brand)
    catalogue =json.loads(catalogue_path(args.brand).read_text())
    # One home per brand and month: runs/marketing-calendar/<brand>/<month>/
    # (SI-22 (calendar months home), 2026-10-07). The brand is a folder, so two
    # brands can never share — or steal — a month folder, which the old
    # `calendar-<month>[-<brand>]` naming had to guard against by hand. The
    # label stays the run's NAME in its records; it is no longer a folder.
    label = f"calendar-{args.month}-{args.brand}"
    out_dir = out_root / month_dir(args.brand, args.month).relative_to(RUNS)
    out_dir.mkdir(parents=True, exist_ok=True)
    today = f"{datetime.date.today():%A, %-d %B %Y}"
    D = {k: out_dir / k for k in ("1-holidays", "2-cultural", "3-cells", "4-anchors",
                                  "5-concepts", "6-catalogue", "7-offers", "8-affiliate", "9-order")}
    for d in D.values():
        d.mkdir(exist_ok=True)
    state_f = out_dir / "run.json"
    replay = ("reorder" if args.reorder else "from_anchors" if args.from_anchors
              else "cont" if args.cont else None)
    prior = _json_or(state_f, None)
    # A replay re-runs some layers and REUSES the rest from disk. The reused
    # layers still govern this month, so their records are carried forward
    # rather than rebuilt — losing them was how a replayed month ended up
    # unable to name the prompt that decided who was live (2026-09-13).
    state = (CH.carried(prior, replay) if replay else None) \
        or CH.blank(label, args.brand, args.month)
    # What this brand could and could not give the chain. Recorded on EVERY
    # run, because a thin month and a thin record look identical afterwards.
    ready = CH.readiness(brand_root)
    state["brand_readiness"] = {
        L["key"]: {"verdict": L["verdict"], "losing": L["losing"]}
        for L in ready if L["verdict"] != "full"}
    deg = [L for L in ready if L["verdict"] == "degraded"]
    blocked = [L for L in ready if L["verdict"] == "blocked"]
    for L in blocked:
        miss = ", ".join(r["path"] for r in L["needs"]
                         if r["required"] and not r["have"])
        print(f"  BLOCKED  layer {L['n']} {L['name']} needs {miss}")
    # THE INPUTS GATE — recorded in check.json, pass or HELD, before any model
    # runs. It stops nothing by itself: a blocked brand has always stopped on
    # the line below, and a degraded one has always run.
    try:
        import gates as G
        state["gates"] = {"inputs": G.inputs_gate(ready, out_dir)}
    except Exception as e:
        print(f"  SKIP  the inputs gate could not be recorded — {e}")
    if blocked:
        sys.exit(f"{args.brand} cannot run this chain yet — see above")
    if deg:
        print(f"  NOTE: {len(deg)} layer(s) run degraded for {args.brand} "
              f"(layers {', '.join(str(L['n']) for L in deg)}) — "
              f"`chain.py --check {args.brand}` says what each one loses")
    if replay:
        CH.event(state, CH.REPLAYS[replay]["label"],
                 reruns=CH.REPLAYS[replay]["reruns"])
        if not prior:
            print(f"  NOTE: no prior run.json here — the replay reuses the files on "
                  f"disk but cannot say which run wrote them")

    # LAYER 1 · THE HOLIDAYS  (code) -> 1-holidays/
    hol_rows = H.in_month(args.month, lead_in_days=10)
    moments = resolve_moments(brand_root, args.month)
    if args.reorder:
        moves = json.loads((D["8-affiliate"] / "affiliate.json").read_text())
        cells = json.loads((D["3-cells"] / "cells.json").read_text())
        # moves written before arcs carried stable labels linked by id();
        # rebuild the label from the ask each generated/linked peer belongs to
        n = 0
        for m in moves:
            if m.get("role") == "asks" and not m.get("anchored") and not m.get("arc_generated") \
                    and not m.get("_arc") and not str(m.get("offer", "none")).lower().startswith("none"):
                n += 1; m["_arc"] = f"C{n}"
        for m in moves:
            if isinstance(m.get("arc_for"), int):
                ask = next((a for a in moves if a.get("_arc")
                            and a["cell"]["segment"] == m["cell"]["segment"]
                            and a.get("occasion") == m.get("occasion")), None)
                if ask:
                    m["arc_for"] = ask["_arc"]
                else:
                    m.pop("arc_for")
        return finish(args, out_dir, D, state, moves, cells, moments, hol_rows,
                      brand_root, catalogue, label)
    # a holiday counts as planned when any moment anchors to it
    mj = json.loads(BP.brand_path(brand_root.name, "strategy", "moments.json", root=brand_root.parent).read_text())
    anchored_keys = {(m.get("anchor") or {}).get("holiday") for b in mj["avatars"].values()
                     for m in b["moments"]} | {(m.get("anchor") or {}).get("through") for b in mj["avatars"].values() for m in b["moments"]} \
        | {(m.get("anchor") or {}).get("peak") for b in mj["avatars"].values() for m in b["moments"]}
    (D["1-holidays"] / "holidays.md").write_text(
        f"# Public holidays in {args.month}\n\n" + H.render(hol_rows) + "\n\n"
        "Which of these the brand plans against is its own call, made in "
        "calendar/moments.json by anchoring a moment to the holiday's key.\n")
    (D["1-holidays"] / "holidays.json").write_text(json.dumps(hol_rows, indent=1) + "\n")
    CH.done(state, "holidays", len(hol_rows))
    print(f"  -> layer 1  (code: {len(hol_rows)} public holiday(s) land in {args.month})")

    # LAYER 2 · THE BRAND'S MOMENTS  (code) -> 2-cultural/
    skeleton = render_skeleton(args.month, hol_rows, moments, anchored_keys)
    inwin = [m for m in moments if m["in_month"]]
    (D["2-cultural"] / "moments.md").write_text(skeleton + "\n")
    (D["2-cultural"] / "moments.json").write_text(json.dumps(inwin, indent=1) + "\n")
    CH.done(state, "moments", len(inwin), unclaimed_retail=[
        r["key"] for r in hol_rows if r["kind"] == "retail" and r["key"] not in anchored_keys])
    unclaimed = [r["key"] for r in hol_rows if r["kind"] == "retail" and r["key"] not in anchored_keys]
    print(f"  -> layer 2  (code: {len(inwin)} moment(s) in window"
          + (f"; retail holidays the brand has no moment for: {', '.join(unclaimed)}" if unclaimed else "") + ")")
    save(out_dir, state)

    # LAYER 3 · WHO IS LIVE  (AI) -> 3-cells/
    sheet = C_state_sheet(brand_root, catalogue, args.month)
    (D["3-cells"] / "state-sheet.md").write_text(sheet)
    if args.from_anchors:
        cells = json.loads((D["3-cells"] / "cells.json").read_text())
    elif not args.cont:
        out, meta = run_ai("cells", out_dir, args.model, D["3-cells"],
                           today=today, month=args.month, state=sheet,
                           skeleton=skeleton)
        cells = jfence(out, "{")
        (D["3-cells"] / "cells.json").write_text(json.dumps(cells, indent=1) + "\n")
        CH.done(state, "cells", len((cells or {}).get("serve") or []), **meta)
        save(out_dir, state)
        if args.stop_at_cells:
            print(f"\n── PAUSED AFTER CELLS (you asked) — edit {D['3-cells'] / 'cells.json'} then --continue")
            return
    else:
        cells = json.loads((D["3-cells"] / "cells.json").read_text())

    # LAYER 4 · PINNED TO THE DATE  (code) -> 4-anchors/
    anchors = anchor_arcs(args.month, moments, cells, catalogue, brand_root, hol_rows)
    (D["4-anchors"] / "anchors.json").write_text(json.dumps(anchors, indent=1) + "\n")
    (D["4-anchors"] / "anchors.md").write_text(
        "# Anchored to real dates\n\nEvery dated holiday and moment, laid onto the month "
        "per live segment. A retail or season-opening holiday is a full arc around its "
        "day; an observance is one send on the day; a window with a peak lands before "
        "the peak.\n\n" + render_anchors(anchors) + "\n")
    CH.done(state, "anchors", len(anchors))
    print(f"  -> layer 4  (code: {len(anchors)} send(s) anchored to real dates)")
    save(out_dir, state)

    # LAYER 5 · THE CONCEPTS  (AI) -> 5-concepts/
    if args.from_anchors:
        concepts = json.loads((D["5-concepts"] / "concepts.json").read_text())
    else:
        out, meta = run_ai("concepts", out_dir, args.model, D["5-concepts"],
                           today=today, month=args.month, skeleton=skeleton,
                           anchored=render_anchors(anchors),
                           cells=json.dumps(cells, indent=1),
                           types=C.render_types(catalogue_path(args.brand)),
                           products=C.render_products(brand_root),
                           offers=C.render_offers(brand_root, [a['key'] for a in L_avatars(brand_root)]),
                           coldness=C.coldness(brand_root, catalogue),
                           findings="\n".join(C.findings(brand_root))
                           or "(no measured sends yet)",
                           techniques=doctrine("techniques"))
        concepts = jfence(out, "{")
        CH.done(state, "concepts", len(concepts.get("moves") or []),
                offer_assignments=len(concepts.get("offer_assignments") or []),
                **meta)
    assignments = concepts.get("offer_assignments") or []
    cmoves = concepts.get("moves") or []
    # EVERY SEND MAKES ITS OWN CASE (2026-09-14). The cells stage gives each
    # avatar ONE standing angle for the whole month — the problem that person
    # is living with. Inheriting it wholesale is how 35 emails came to carry 13
    # arguments, four of them the same email four times. So a move's OWN
    # variants win, and the cell's are only a fallback for a move that did not
    # write one; a fallback is recorded, because it is a send with nothing
    # specific to say.
    seg_variants = {c["segment"]: c.get("variants", [])
                    for c in (cells or {}).get("serve", [])}
    inherited = 0
    for mv in cmoves:
        own = [v for v in (mv.get("variants") or []) if (v.get("angle") or "").strip()]
        if own:
            mv["variants"] = own
            continue
        mv["variants"] = [dict(v, angle_inherited=True)
                          for v in seg_variants.get(mv.get("cell", {}).get("segment"), [])]
        inherited += 1
    angles = [(v.get("angle") or "").strip()
              for mv in cmoves for v in (mv.get("variants") or [])
              if (v.get("angle") or "").strip()]
    (D["5-concepts"] / "concepts.json").write_text(json.dumps(concepts, indent=1) + "\n")
    print(f"  -> layer 5  ({len(assignments)} offer assignment(s), {len(cmoves)} concept "
          f"move(s), {len(set(angles))} distinct angle(s) of {len(angles)}"
          + (f"; {inherited} move(s) wrote none and inherited the cell's" if inherited else "")
          + ")")
    save(out_dir, state)

    # LAYER 6 · TYPED  (code) -> 6-catalogue/
    types = {t["key"]: t for t in catalogue["types"]}
    bad, bad_seg = [], []
    # A SEGMENT IS LOOKED UP, NEVER COINED — the same rule the type already
    # holds to. The concepts stage proposed sends to "mixed — all 7 live
    # segments" (Brand A, 2026-09-14): a real intention, written as a segment
    # name that no platform can target. It reached the board as two breaks
    # after surviving three layers. Dropped here instead, and named.
    live_segs = {c.get("segment") for c in (cells or {}).get("serve", [])
                 if c.get("live", True)}
    for mv in cmoves:
        t = types.get(mv.get("type"))
        if not t:
            bad.append(mv.get("type")); continue
        seg = (mv.get("cell") or {}).get("segment")
        if live_segs and seg not in live_segs:
            bad_seg.append(f"{seg!r} ({mv.get('type')})"); continue
        mv["category"] = CATS[t["well"]]; mv["role"] = t["role"]
    cmoves = [mv for mv in cmoves if mv.get("type") in types
              and (not live_segs or (mv.get("cell") or {}).get("segment") in live_segs)]
    cmoves, added = expand_arcs(cmoves, catalogue)
    moves = anchors + cmoves
    # A TYPE IS AN EMAIL FORMAT, AND A FORMAT IS LOOKED UP (rollout, 2026-09-20).
    # The brand's catalogue still decides what can be PLANNED — it carries the
    # well and the role — but a dropped type is now also asked of the element
    # library (components/elements, format/email), so the month can say whether
    # the model coined a word or the brand simply does not carry a real format.
    # Unknown in both is a break in checks.md; see `finish`.
    not_a_format = []
    try:
        import gates as G
        _known = G.library_ids() | G.brand_type_ids(brand_root)
        not_a_format = sorted({str(b) for b in bad if str(b) not in _known}) if _known else []
    except Exception as e:
        print(f"  SKIP  the element library could not be asked — {e}")
    (D["6-catalogue"] / "moves.json").write_text(json.dumps(moves, indent=1, default=str) + "\n")
    (D["6-catalogue"] / "catalogue.md").write_text(
        f"# Typed against the catalogue\n\n{len(moves)} send(s). {added} arc move(s) added to "
        "complete promotional asks from the concepts stage.\n"
        + (f"\nDropped, not in the catalogue: {', '.join(map(str, bad))}\n" if bad else "")
        + (f"\nOf those, not an email format anywhere — neither the element library nor "
           f"this brand's catalogue: {', '.join(not_a_format)}\n" if not_a_format else "")
        + (f"\nDropped, not a live segment of this brand: {', '.join(bad_seg)}\n" if bad_seg else ""))
    CH.done(state, "catalogue", len(moves), arc_moves_added=added,
            not_in_catalogue=bad, not_a_format=not_a_format, not_a_live_segment=bad_seg)
    print(f"  -> layer 6  (code: {len(moves)} typed; {added} arc move(s) added; "
          f"{len(bad)} unknown type(s), {len(bad_seg)} invented segment(s) dropped)")

    # LAYER 7 · OFFERS CHECKED  (code) -> 7-offers/
    moves, olog = apply_offers(moves, assignments, brand_root)
    (D["7-offers"] / "moves.json").write_text(json.dumps(moves, indent=1, default=str) + "\n")
    (D["7-offers"] / "offers.md").write_text(
        "# Offers, checked against the bank\n\nEvery offer on every send checked against "
        "products/offer-bank.md — the only place an offer can come from.\n\n"
        + ("\n".join(olog) if olog else "- every offer stands as assigned") + "\n")
    CH.done(state, "offers", len(olog))
    print(f"  -> layer 7  (code: {len(olog)} offer note(s))")
    save(out_dir, state)

    # LAYER 8 · THE AFFILIATE FLOOR  (code) -> 8-affiliate/
    moves, aff_added, aff_note = ensure_weekly_affiliate(moves, args.month, brand_root, cells)
    (D["8-affiliate"] / "affiliate.json").write_text(json.dumps(moves, indent=1, default=str) + "\n")
    CH.done(state, "affiliate", aff_added, note=aff_note)
    print(f"  -> layer 8  ({aff_note})")
    finish(args, out_dir, D, state, moves, cells, moments, hol_rows, brand_root, catalogue, label)


def finish(args, out_dir, D, state, moves, cells, moments, hol_rows, brand_root, catalogue, label):
    """Layer 9 and the board — split out so --reorder can re-run them alone."""
    types = {t["key"]: t for t in catalogue["types"]}
    # LAYER 9 · THE ORDER  (code) -> 9-order/
    slots, dropped, dlog = fit_month(moves, args.month, brand_root, catalogue,
                                     "\n".join(C.findings(brand_root)),
                                     windows=moment_windows(moments))
    start_day = getattr(args, "start_day", None)
    if start_day:
        # production starts on a day inside the month: earlier slots leave the
        # order; ids are renumbered and the links between slots re-pointed
        before = len(slots)
        keep = [s_ for s_ in slots if int(s_["date"][-2:]) >= start_day]
        old_ids = {s_["id"]: s_ for s_ in keep}
        abbr = keep[0]["id"].rsplit("-", 1)[0] if keep else "m"
        remap = {}
        for n_, s_ in enumerate(keep, 1):
            remap[s_["id"]] = f"{abbr}-{n_:02d}"
        for s_ in keep:
            s_["id"] = remap[s_["id"]]
            for k_ in ("follows", "then"):
                if s_.get(k_):
                    s_[k_] = remap.get(s_[k_])       # a link to a dropped slot goes
        slots = keep
        dlog.append(f"- production starts on the {start_day}th (RULED 2026-09-09): "
                    f"{before - len(slots)} slot(s) dated earlier left the order; ids renumbered")
    (out_dir / "slots.json").write_text(json.dumps(slots, indent=1) + "\n")
    olines = ["# The order — dates resolved around the anchors", "",
              f"{len(slots)} slot(s) written to ../slots.json. Anchored sends kept their real "
              "dates; everything else took its preferred date or the nearest free day "
              "(no two sends to one segment on adjacent days).", ""]
    olines += dlog
    olines += ["", "## Every slot, in order", ""]
    for s in slots:
        segs = s.get("segments") or [s["segment"]]
        seg_txt = (segs[0] if len(segs) == 1 else
                   f"{len(segs)} segments ({', '.join(x.replace('Core | ', '') for x in segs)})")
        olines.append(f"- **{s['id']}** · {s['date']} {s['hour']:02d}:00 · {seg_txt} · "
                      f"`{s['type']}` — {s['occasion']}"
                      + (" · anchored" if s.get("anchored") else "")
                      + (f" · follows {s['follows']}" if s.get("follows") else "")
                      + (f" · then {s['then']}" if s.get("then") else ""))
    (D["9-order"] / "order.md").write_text("\n".join(olines) + "\n")
    if dropped:
        (D["9-order"] / "dropped.md").write_text(
            "# Dropped as exact duplicates\n\nNo send budget exists (RULED 2026-09-01). "
            "The only thing refused is the same type, on the same occasion, to the same "
            "segment twice.\n\n" + "\n".join(
                f"- {m.get('cell', {}).get('segment')} · `{m.get('type')}` on {m.get('occasion')}"
                for m in dropped) + "\n")
    CH.done(state, "order", len(slots), dropped=len(dropped))
    print(f"  -> layer 9  (code: {len(slots)} slots dated and linked"
          + (f", {len(dropped)} exact duplicate(s) dropped)" if dropped else ")"))

    # THE BOARD (code): every check, the math, the briefs
    roster = {a["key"] for a in L_avatars(brand_root)}
    subs = {a["key"]: set(a.get("subs") or []) for a in L_avatars(brand_root)}
    segments = C.brand_segments(brand_root)
    no_offer = C.offerless_avatars(brand_root, roster)
    windows = moment_windows(moments)
    all_keys = {m["key"] for m in moments}

    # A DATED ANGLE MUST BE INSIDE ITS OWN WINDOW (RULED 2026-09-10, the owner:
    # "I still see some labor day email in the figma for late september…
    # why are you not using the calendar in this chain?"). The cells stage
    # writes one angle per variant, and it was handing every avatar-one
    # variant a `labor-day` angle for sends running the 14th to the 30th —
    # Labor Day was the 7th. A stale angle is not passed on: the break is
    # recorded and the slot goes to the writer with no angle rather than a
    # wrong one, because an angle is the argument the whole email makes.
    # AN OFFER KEY MUST EXIST IN THE BANK. Layer 7 invents keys that read
    # plausibly — `named-sets`, `vitals-sub` — and the chain only discovers it
    # much later, at run time, after the plan has been reviewed and the board
    # built. Caught here instead, with the nearest real key proposed.
    # THE THIRD READER, and the last one. This file had three parsers of the
    # offer bank and on 2026-09-14 they disagreed three different ways about
    # the same document: the model was shown the right offers, layer 7 stripped
    # what it chose, and this check then called the survivor unknown and
    # proposed `never-pair` as the nearest real key. All three go through
    # `offer_bank()` now — one reader, one answer.
    _bank_map = offer_bank(brand_root, [a["key"] for a in L_avatars(brand_root)])
    _keys = set().union(*_bank_map.values()) if _bank_map else set()
    # WHAT THE TYPE SAYS IT NEEDS, AND WHETHER THE SLOT HAS IT.
    # The catalogue already declares this per type (`needs`) and nothing was
    # testing it, so a `product-finder` with no product and a `subscription-
    # invite` with no offer reached the board looking finished. the owner,
    # 2026-09-14: "I'm seeing offer and product. A lot of them are missing
    # things." Most are missing correctly — a send whose role is `earns` is
    # not supposed to carry an offer. These are the ones that are not.
    missing = []
    for s_ in slots:
        spec = types.get(s_.get("type")) or {}
        want = set(spec.get("needs") or [])
        for field, need in (("offer", "offer_file"), ("product", "product_file")):
            if need in want and str(s_.get(field) or "none").lower() == "none":
                missing.append(
                    f"{s_['id']} ({s_.get('date')}) · `{s_.get('type')}` declares it needs "
                    f"{'an' if field == 'offer' else 'a'} {field}, and carries none. "
                    f"Either give it one or plan a type that "
                    f"does not need it — the writer cannot invent one.")

    # THE COMMERCIAL FLOOR (CH.ASK_SHARE, CH.OFFER_EVERY_WEEK). The concepts
    # prompt aims at it; this is the wall. A month that does not sell is a
    # month nobody notices is not selling — that is exactly how both brands
    # ran at three asks with no complaint until the owner counted them by hand.
    ask_well = {k for k, t in types.items() if t.get("well") == "ask"}
    asks_ = [s_ for s_ in slots if s_.get("type") in ask_well]
    want = max(1, round(len(slots) * CH.ASK_SHARE))
    if len(asks_) < want:
        missing.append(
            f"the month sells too little: {len(asks_)} of {len(slots)} sends "
            f"ask ({round(len(asks_) / max(1, len(slots)) * 100)}%), and the rule "
            f"is {round(CH.ASK_SHARE * 100)}% — {want - len(asks_)} more ask(s) "
            f"needed. An ask is not a discount; it is a send that says what the "
            f"product is and what it costs.")
    if CH.OFFER_EVERY_WEEK:
        weeks = {}
        for s_ in slots:
            try:
                d_ = datetime.date.fromisoformat(s_["date"])
            except (ValueError, KeyError, TypeError):
                continue
            wk = d_.isocalendar()[:2]
            weeks.setdefault(wk, []).append(s_)
        for wk, rows in sorted(weeks.items()):
            if any(str(r.get("offer") or "none").lower() != "none" for r in rows):
                continue
            days = sorted(r["date"] for r in rows)
            missing.append(
                f"week of {days[0]} carries no offer at all ({len(rows)} send(s), "
                f"none of them selling anything). Every week has something to buy "
                f"— that is the rule, and a week without one is a week the brand "
                f"chose not to earn.")

    # TWO SENDS, ONE ARGUMENT. The prompt forbids it; this counts it, because
    # a month can obey every other rule and still be the same email written
    # four times (brand-b September: 35 emails, 13 arguments).
    by_angle = {}
    for s_ in slots:
        for v in (s_.get("variants") or []):
            a = (v.get("angle") or "").strip()
            if a:
                by_angle.setdefault(a, []).append(s_["id"])
    for a, ids in sorted(by_angle.items()):
        if len(set(ids)) > 1:
            missing.append(
                f"{', '.join(sorted(set(ids)))} all make the SAME argument — "
                f"\u201c{a[:80]}{'…' if len(a) > 80 else ''}\u201d. Two sends to a "
                f"person in one month must not put the same case; give each its "
                f"own, or cut one.")
    inh = sum(1 for s_ in slots for v in (s_.get("variants") or [])
              if v.get("angle_inherited"))
    if inh:
        missing.append(
            f"{inh} variant(s) carry the avatar's STANDING angle rather than one "
            f"written for the send — the concepts stage left them blank. A "
            f"standing angle is what the person is living with, not what this "
            f"email argues.")

    unknown = []
    for s_ in slots:
        o_ = s_.get("offer")
        if not o_ or o_ == "none" or not _keys or o_ in _keys:
            continue
        near = sorted(_keys, key=lambda k: -len(set(k.split("-")) & set(o_.split("-"))))
        unknown.append(f"{s_['id']} ({s_.get('date')}) carries offer `{o_}`, which the bank "
                       f"does not have. Nearest real keys: "
                       + ", ".join(f"`{k}`" for k in near[:3])
                       + ". Fix the slot before the chain runs — it fails at the door otherwise.")
    stale = list(unknown) + missing
    for s_ in slots:
        d_ = s_.get("date", "")
        for v_ in (s_.get("variants") or []):
            ang = v_.get("angle") or ""
            low = ang.lower()
            named, dead = [], []
            for key, wins in (windows or {}).items():
                # the key as written (labor-day) and as spoken (labor day)
                pat = r"(?<![a-z0-9])" + re.escape(key).replace(r"\-", "[- ]") + r"(?![a-z0-9])"
                if not re.search(pat, low):
                    continue
                spans = [(a_, b_) for a_, b_ in wins if a_ is not None]
                if not spans:
                    continue
                named.append(key)
                if not any(a_ <= d_ <= (b_ or a_) for a_, b_ in spans):
                    lo_ = min(a_ for a_, _ in spans); hi_ = max((b_ or a_) for _, b_ in spans)
                    dead.append((key, lo_, hi_))
            if not dead:
                continue
            if len(dead) < len(named):
                # one moment in the angle is live and another is not: the angle
                # stands, and the dead one is named so the copy leaves it out
                for key, lo_, hi_ in dead:
                    stale.append(f"{s_['id']} ({d_}) · {v_.get('avatar')}: the angle also names "
                                 f"`{key}` ({lo_} to {hi_}), which this send sits outside. The "
                                 f"angle stands on its live moment; the copy must not reach for "
                                 f"the dead one.")
                    v_["angle"] = re.sub(r"(?<![a-z0-9])" + re.escape(key).replace(r"\-", "[- ]")
                                         + r"(?![a-z0-9])[ ]*(and[ ]+)?", "", v_["angle"],
                                         flags=re.I).strip(" -—:")
                continue
            # every moment it names is dead. An angle IS the argument, so it is
            # replaced by the slot's own recorded problem rather than left empty.
            occ_ = (s_.get("occasion") or "")
            fallback = occ_.split("—", 1)[1].strip() if "—" in occ_ else None
            key, lo_, hi_ = dead[0]
            stale.append(f"{s_['id']} ({d_}) · {v_.get('avatar')}: the plan's angle was `{key}`, "
                         f"whose window is {lo_} to {hi_} — this send is outside it. "
                         + (f"Replaced with this slot's own recorded problem: “{fallback}”."
                            if fallback else
                            "Dropped, and this slot has no recorded problem to fall back on — "
                            "assign this variant an angle before it is written."))
            v_["angle_dropped"] = ang
            v_["angle"] = fallback
    if stale:
        (D["9-order"] / "stale-angles.md").write_text(
            "# Angles dropped for naming a moment this send sits outside\n\n"
            + "\n".join(f"- {x}" for x in stale) + "\n")
        (out_dir / "slots.json").write_text(json.dumps(slots, indent=1, default=str) + "\n")

    errors, warns = C.check(slots, args.month, types, brand_root / "email-sms/sends", roster, subs,
                            segments, no_offer, cells, moment_windows=windows,
                            moment_keys=all_keys,
                            retail_holidays=[r for r in hol_rows if r["kind"] in ("retail", "season-open")])
    if stale:
        errors = list(errors) + stale
    # THE ELEMENTS GATE. Every slot's type is an email format: it must be in the
    # element library (components/elements, format/email) OR the brand's own
    # catalogue. In neither is a break that names the real ids — on a finished
    # slot, and on anything layer 6 dropped (read from the run record, so a
    # --reorder or --from-anchors replay still knows what was dropped).
    el_breaks, picked = [], {}
    try:
        import gates as G
        dropped_types = [str(x) for x in ((state.get("stages") or {}).get("catalogue") or {})
                         .get("not_in_catalogue") or []]
        el_breaks, el_warns, picked = G.type_problems(
            [str(s_.get("type")) for s_ in slots], brand_root, dropped_types)
        errors = list(errors) + el_breaks
        warns = list(warns) + el_warns
        state["elements"] = {"format/email": picked}
    except Exception as e:
        print(f"  SKIP  the elements gate could not run — {e}")
    # The headline is written AFTER every break is in, so the page, run.json and
    # the last line printed all say one number (the headline used to be counted
    # before the stale-angle breaks were added, and read low).
    report = ["# The month, checked", "",
              f"{len(slots)} slots for {args.month}. {len(errors)} rule breaks · {len(warns)} warnings.", ""]
    if errors:
        report += ["## Breaks — fix before this month stands", ""] + [f"- {e}" for e in errors] + [""]
    if warns:
        report += ["## Warnings — a human reads these", ""] + [f"- {w}" for w in warns] + [""]
    report += ["", C.per_person(slots, C.responsiveness(brand_root))]
    (out_dir / "checks.md").write_text("\n".join(report) + "\n")
    state["checks"] = {"errors": len(errors), "warnings": len(warns),
                       "out": "checks.md", "at": CH.now()}
    state.update(slots=len(slots), errors=len(errors), warnings=len(warns))
    # check.json — the quality gates, in `components/quality-checks` `hold()`
    # shape. RECORDED, NEVER RAISED: a held month is still written and still
    # drawn, because adoption stays a human act and the review board is the
    # Review. The gate says HELD; the person decides.
    try:
        import gates as G
        state.setdefault("gates", {})["elements"] = G.record("elements", el_breaks, out_dir)
        state["gates"]["out"] = "check.json"
    except Exception as e:
        print(f"  SKIP  check.json could not be written — {e}")
    save(out_dir, state)
    # The board a human reviews: every send, its why, and the rules it passed.
    # Copy is NOT written here — the calendar says what exists and when, and
    # the copy machine reads this folder (moved out 2026-09-13 when the
    # calendar became its own component; the brief pages are the copy stage's
    # job, not the planner's).
    import board
    board.build(out_dir)
    # The month is already home — runs/marketing-calendar/<brand>/<month>/ —
    # so this files nothing (one home, no second copy); a scratch `--out` run
    # never reaches the shelf either. Kept so a failure still says SKIP and
    # never loses a month.
    try:
        import gates as G
        note = G.file_after_run(out_dir)
        if note:
            print(f"  filed  {note}")
    except Exception as e:
        print(f"  SKIP  the month is whole, but was not filed to runs/ — {e}")
    print(f"\n{len(slots)} slots · {len(errors)} breaks · {len(warns)} warnings")
    print(f"done -> {out_dir}\nAdoption stays a human act.")


def C_state_sheet(brand_root, catalogue, month):
    """The brand's facts on one sheet — for the cells stage."""
    roster = L_avatars(brand_root)
    matrix = json.loads((brand_root / "email-sms/audience-matrix.json").read_text())
    seg_lines = [f"- {s['name']} — " + (f"{s['profiles']:,} people" if s.get("profiles") is not None else "size not yet counted")
                 + f" ({s.get('rule', '')})" for s in matrix["segments"]]
    av_lines = [f"- {a['key']} — {a['rows']:,} language rows" for a in roster]
    r = C.responsiveness(brand_root)
    resp = ("Revenue per recipient against unsubscribe cost, joined from this brand's ledger "
            f"and performance record. {r['measured']} audiences with 3+ sends.\n\n"
            "| audience | sends | recipients | $/recipient | unsub% | click% |\n|---|---|---|---|---|---|\n"
            + "\n".join(f"| {x['audience']} | {x['sends']} | {x['recipients']:,.0f} | "
                        f"${x['rev_per_recipient']:.4f} | {x['unsub_pct']} | {x['click_pct']} |"
                        for x in r["audiences"])) if r else "(no measured sends yet — no frequency signal)"
    return "\n\n".join([
        f"# The state — {month}",
        "## Segments (the platform's own counts)\n" + "\n".join(seg_lines),
        "## Avatars and their language depth\n" + "\n".join(av_lines),
        "## The evidence, as findings\n" + ("\n".join(C.findings(brand_root)) or "(no measured sends yet)"),
        "## Coldness, computed\n" + C.coldness(brand_root, catalogue),
        "## Offers\n" + C.render_offers(brand_root, [a["key"] for a in roster]),
        "## What sending EARNS here, per audience (the frequency signal)\n" + resp,
    ])


if __name__ == "__main__":
    main()
