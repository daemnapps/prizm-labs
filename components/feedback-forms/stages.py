#!/usr/bin/env python3
"""A brand's feedback stages, derived from first principles and its own facts — nothing assumed.

    python3 components/feedback-forms/stages.py --brand <b> [--label L]

principles.json says why each form exists (a moment only those people can tell us about), what must be true for
it, and what its timing depends on. brands/<b>/operations/feedback-variables.json holds the brand's facts (store,
email platform, how long its welcome and checkout emails run, how long its product takes to work, what its systems
call each event). For each moment:

  - a fact that is false (it sells no subscriptions)  -> the form is not for this brand and is left out
  - a fact nobody has given yet (null)               -> the form waits, blocked, naming the fact and where to find it
  - every fact known                                  -> ready: trigger, exclusions, wait, all from the facts

Writes a PROPOSAL only: runs/feedback-forms/<b>/stages-<label>/deliverable/feedback-stages.json and a matching
feedback-questions.json (forms that are not for this brand dropped), plus PROPOSAL.md. brands/ is never written.
Brand-agnostic: no brand is named here.
"""
import argparse
import copy
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build as B  # noqa: E402

PRINCIPLES = json.loads((HERE / "principles.json").read_text())
SUPPORTED = {"klaviyo"}


def facts(brand, root=None):
    own = B.ops(brand, root) / "feedback-variables.json"
    tpl = (root or B.WORKSPACE) / "brands" / "_TEMPLATE" / "operations" / "feedback-variables.json"
    raw = json.loads((own if own.is_file() else tpl).read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}, ("brand" if own.is_file() else "template")


def _val(f, name):
    return (f.get(name) or {}).get("value")


def _names(v):
    """An event value: one name, a {"metric", "where"} pair, or a list of either (one per store or checkout)."""
    if isinstance(v, dict):
        return f"{v.get('metric')} where {v.get('where')}" if v.get("where") else v.get("metric")
    if isinstance(v, list):
        if any(isinstance(x, dict) for x in v):
            return " or ".join(_names(x) for x in v if x)
        return " or ".join(str(x) for x in v if x) or None
    return v or None


def _split(name):
    """'Placed Order (Shopify)' -> ('Placed Order', 'Shopify')."""
    m = re.match(r"^(.*?)\s*\(([^()]+)\)\s*$", str(name))
    return (m.group(1), m.group(2)) if m else (str(name), "")


def _trigger(value, ev):
    """The flow trigger. More than one source (a list) means one flow per source, each with its own trigger."""
    if not value:
        return {"type": "metric", "metric": f"<{ev}>", "integration": ""}
    names = value if isinstance(value, list) else [value]
    first = names[0] if not isinstance(names[0], dict) else names[0].get("metric")
    metric, integration = _split(first)
    t = {"type": "metric", "metric": metric, "integration": integration}
    if isinstance(names[0], dict) and names[0].get("where"):
        t["filter"] = names[0]["where"]
    if len(names) > 1:
        t["one_flow_per_source"] = [dict(zip(("metric", "integration"), _split(n if not isinstance(n, dict) else n.get("metric")))) for n in names]
        t["integration"] = integration + " — and one more flow per source: " + ", ".join(_names(n) for n in names[1:])
    return t


def _need(f, name):
    meta = f.get(name) or {}
    return f"{name} — {meta.get('means', '')} (from {meta.get('from', 'the brand')})"


def derive(f):
    """[(moment, stage dict or None)] — None means the form is not for this brand."""
    esp = _val(f, "email_platform")
    out = []
    for m in PRINCIPLES["moments"]:
        if any(_val(f, r) is False for r in m["requires"]):
            out.append((m, None))
            continue
        needs = [_need(f, r) for r in m["requires"] if _val(f, r) in (None, "", [])]
        if esp in (None, ""):
            needs.append(_need(f, "email_platform"))
        elif str(esp).lower() not in SUPPORTED:
            needs.append(f"email_platform {esp}: only {', '.join(sorted(SUPPORTED))} is built so far")
        ev = m["event"]
        metric = _names(_val(f, ev))
        w = m["wait"]
        days = [_val(f, w["after"])] + ([_val(f, w["plus"])] if w.get("plus") else [])
        for key, d in zip([w["after"], w.get("plus")], days):
            if key and d is None:
                needs.append(_need(f, key))
        filters = []
        order_ev = _names(_val(f, "order_placed_event")) or "the order event"
        refund_ev = _names(_val(f, "refund_event"))
        for ex in m.get("exclude", []):
            if ex == "has-ordered":
                filters.append(f"{order_ev} — zero times over all time")
            elif ex == "refunded":
                if refund_ev:
                    filters.append(f"{refund_ev} — zero times since starting this flow")
                elif _val(f, "refund_event") is None:
                    needs.append(_need(f, "refund_event"))
            elif ex == "subscription-order" and _val(f, "sells_subscriptions"):
                renewed = _names(_val(f, "subscription_renewed_event"))
                if renewed:
                    filters.append(f"{renewed} — zero times over all time (subscribers get their own form)")
                else:
                    needs.append(_need(f, "subscription_renewed_event"))
        flt = m.get("filter") or {}
        if "orders" in flt:
            filters.append(f"{order_ev} — " + ("equals 1 over all time" if flt["orders"] == 1 else "at least 2 over all time"))
        if "renewals" in flt and metric:
            filters.append(f"{metric} — at least 2 over all time")
        filters.append("Has not been in this flow over all time (one form per person per moment)")
        wait = sum(d for d in days if isinstance(d, (int, float)))
        stage = {"stage": m["stage"], "label": m["label"], "lane": m["lane"], "relationship": m["relationship"],
                 "known": m["known"], "why": m["why"], "status": "blocked" if needs else "ready",
                 "klaviyo": {"flow_name": f"Feedback · {m['stage']}",
                             "trigger": _trigger(_val(f, ev), ev),
                             "trigger_filters": [x for x in [_trigger(_val(f, ev), ev).get("filter")] if x], "flow_filters": filters,
                             "wait": f"{int(wait)} days" if not needs else f"<{' + '.join(k for k in (w['after'], w.get('plus')) if k)}>",
                             "why_the_wait": w["why"]}}
        if needs:
            stage["blocked_by"] = "needs " + "; ".join(dict.fromkeys(needs))
        out.append((m, stage))
    return out


def proposal(brand, root=None):
    f, origin = facts(brand, root)
    st_path, q_path = B.ops(brand, root) / "feedback-stages.json", B.ops(brand, root) / "feedback-questions.json"
    tpl = (root or B.WORKSPACE) / "brands" / "_TEMPLATE" / "operations"
    base_st = json.loads((st_path if st_path.is_file() else tpl / "feedback-stages.json").read_text())
    base_q = json.loads((q_path if q_path.is_file() else tpl / "feedback-questions.json").read_text())
    rows = derive(f)
    st = copy.deepcopy(base_st)
    st["stages"] = [s for _, s in rows if s]
    keep = {s["stage"] for s in st["stages"]}
    q = copy.deepcopy(base_q)
    q["stages"] = {k: v for k, v in q["stages"].items() if k in keep}
    if q.get("default_stage") not in keep:
        q["default_stage"] = next((s["stage"] for s in st["stages"] if s["lane"] == "customer"), next(iter(keep), None))
    return f, origin, rows, st, q


def main(argv=None, root=None):
    ap = argparse.ArgumentParser(description="Derive a brand's feedback stages from first principles and its facts.")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--label")
    a = ap.parse_args(argv)
    f, origin, rows, st, q = proposal(a.brand, root)
    label = a.label or dt.date.today().isoformat()
    out = (root or B.WORKSPACE) / "runs" / "feedback-forms" / a.brand / f"stages-{label}"
    (out / "deliverable").mkdir(parents=True, exist_ok=True)
    (out / "deliverable" / "feedback-stages.json").write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")
    (out / "deliverable" / "feedback-questions.json").write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n")
    lines = [f"# Feedback stages from first principles · {a.brand} · {label}", "",
             f"Facts from the {origin}. Target: brands/{a.brand}/operations/feedback-stages.json (applied by a person on the owner's yes).", "",
             "| Form | State | Why it exists | When | Trigger | Waiting on |", "|---|---|---|---|---|---|"]
    for m, s in rows:
        if s is None:
            lines.append(f"| {m['label']} | not for this brand | {m['why']} | | | |")
        else:
            k = s["klaviyo"]
            lines.append(f"| {s['label']} | {s['status']} | {s['why']} | {k['wait']} after the trigger ({k['why_the_wait']}) | {k['trigger']['metric']} | {s.get('blocked_by', '')} |")
    (out / "PROPOSAL.md").write_text("\n".join(lines) + "\n")
    ready = sum(1 for _, s in rows if s and s["status"] == "ready")
    blocked = sum(1 for _, s in rows if s and s["status"] == "blocked")
    dropped = sum(1 for _, s in rows if s is None)
    print(f"{ready} ready · {blocked} waiting on a fact · {dropped} not for this brand -> {out / 'PROPOSAL.md'}")
    bad = B.check(st, q)
    if bad:
        print("HELD: " + "; ".join(bad[:4]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
