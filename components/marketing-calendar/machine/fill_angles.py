"""Holiday fill angles: one angle of its own for every holiday-period extra send.

Why (email_lead, 2026-11-06): layer 4 tops a holiday window up to 2-3 sends a day
(holiday_fill, owner 2026-10-09). Those extras are made before layer 5 writes
any angle, so each one copied the variants of the window's FIRST arc send.
December 2026 brand_a came out with 43 such sends, each to six segments at once,
all carrying the Lead cell's angle ("he has never had a routine") — told to
VIPs with five orders as well. The count is owner's rule and stays; the
repeated argument was the fault.

What this does: after layer 9 has dated and typed the month, every holiday
fill slot gets one new angle, written for its own type, product, offer and
date, true for every segment it goes to (buyers and not). One model call for
the whole month. Answers are cached in 9-order/fill-angles/angles.json by slot
signature (date, hour, type, offer), so --from-anchors and --reorder replays
reuse them and spend nothing; only a new or changed fill send is asked for.
The angle it replaces is kept on the variant as `angle_copied`.

One angle per send, not one per variant: the email line writes one version per
audience (decision log 2026-11-04), so this adds no emails.

An angle is the argument a send carries, not copy (folder rule 4): the email
line writes the words.
"""
import datetime
import json
from pathlib import Path

import runner as R

STAGE = "cal9-fill-angles"


def is_fill(slot):
    return bool(slot.get("holiday_fill")) or str(slot.get("why") or "").startswith("holiday period:")


def signature(slot, prompt_name=""):
    """A new prompt version asks again; a replay on the same version reuses the answer."""
    return "|".join([prompt_name] + [str(slot.get(k) or "") for k in ("date", "hour", "type", "offer")])


def _names():
    """components/naming/names.py — one product name (2026-11-19)."""
    import sys
    home = str(Path(__file__).resolve().parents[2] / "naming")
    if home not in sys.path:
        sys.path.append(home)
    import names
    return names


def _product_facts(brand_root, keys):
    """What each product is and does, from the brand's own product files
    (brands/<brand>/products/<key>.md or <key>/product.md): an angle may only
    claim what these say."""
    out = []
    for k in keys:
        root = Path(brand_root) / "products"
        f = _names().product_file(Path(brand_root).name, k, root=Path(brand_root).parent.parent) or next(   # one product name (2026-11-19)
            (x for x in (root / f"{k}.md", root / k / "product.md") if x.is_file()), None)
        if not f:
            out.append(f"### {k}\n(no product file: claim nothing about what it does)")
            continue
        text, keep, take = f.read_text(), [], False
        for line in text.splitlines():
            if line.startswith("## "):
                take = line[3:].strip().lower() in ("what it is", "what it does", "how to use it", "what's inside")
            if take or line.startswith("# "):
                keep.append(line)
        out.append(f"### {k}\n" + "\n".join(keep)[:1800])
    return "\n\n".join(out)


def _brand_context(brand_root):
    p = Path(brand_root) / "brand-identity" / "position.md"
    return p.read_text()[:12000] if p.is_file() else "(no position file)"


def _order_by(brand_root):
    """The brand's own holiday order-by table (operations/shipping.md), the one place a delivery date may come from."""
    f = Path(brand_root) / "operations" / "shipping.md"
    if not f.is_file():
        return "(no order-by dates on record: never promise delivery by any date)"
    keep, take = [], False
    for line in f.read_text().splitlines():
        if line.startswith("## "):
            take = "order-by" in line.lower()
        if take:
            keep.append(line)
    return "\n".join(keep)[:2500] or "(no order-by dates on record: never promise delivery by any date)"


def _row(s):
    segs = s.get("segments") or [s.get("segment")]
    try:
        day = datetime.date.fromisoformat(s["date"]).strftime("%A %d %B")
    except (KeyError, TypeError, ValueError):
        day = s.get("date")
    return (f"- {s['id']} · {day}, {s.get('hour')}:00 · type `{s.get('type')}` ({s.get('role')}) · "
            f"occasion {s.get('occasion')} · product {s.get('product')} · offer {s.get('offer')} · "
            f"to {', '.join(str(x).replace('Core | ', '') for x in segs if x)}")


def _known_angles(slots):
    out = []
    for s in slots:
        if is_fill(s):
            continue
        for v in s.get("variants") or []:
            a = isinstance(v, dict) and v.get("angle")
            if a and a not in out:
                out.append(a)
    return out


def parse(text, ids):
    """The model's JSON object {slot id: angle}; anything else is ignored."""
    t = text.strip()
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < 0:
        return {}
    try:
        got = json.loads(t[a:b + 1])
    except ValueError:
        return {}
    if not isinstance(got, dict):
        return {}
    return {k: v.strip() for k, v in got.items() if k in ids and isinstance(v, str) and v.strip()}


def apply(slots, brand, brand_root, order_dir, month, model=None, ask=None):
    """Give every holiday fill slot its own angle. Mutates slots; -> log lines."""
    fills = [s for s in slots if is_fill(s)]
    if not fills:
        return []
    d = Path(order_dir) / "fill-angles"
    d.mkdir(parents=True, exist_ok=True)
    cache_f = d / "angles.json"
    try:
        cache = json.loads(cache_f.read_text())
    except (OSError, ValueError):
        cache = {}
    pf = R.latest_prompt(STAGE)
    missing = [s for s in fills if signature(s, pf.name) not in cache]
    log = []
    if missing:
        filled = R.fill(pf.read_text(), {
            "brand": brand, "month": month,
            "position": _brand_context(brand_root),
            "known_angles": "\n".join(f"- {a}" for a in _known_angles(slots)),
            "sends": "\n".join(_row(s) for s in missing),
            "order_by": _order_by(brand_root),
            "products": _product_facts(brand_root, sorted({str(s.get("product")) for s in missing
                                                          if str(s.get("product") or "none") != "none"})),
        })
        (d / "prompt-sent.md").write_text(filled)
        mdl, why = R.pick_model("fill-angles", len(filled), model)
        print(f"  -> holiday fill angles ({pf.name} · {mdl}, {why}): {len(missing)} send(s)")
        out = (ask or R.claude)(filled, mdl)
        (d / "reasoning.md").write_text(out + "\n")
        got = parse(out, {s["id"] for s in missing})
        for s in missing:
            if s["id"] in got:
                cache[signature(s, pf.name)] = got[s["id"]]
        cache_f.write_text(json.dumps(cache, indent=1, ensure_ascii=False) + "\n")
        log.append(f"- holiday fill angles: {len(got)} of {len(missing)} new send(s) given an angle "
                   f"({pf.name}, sha {R.sha(pf)})")
        if len(got) < len(missing):
            log.append(f"- holiday fill angles: {len(missing) - len(got)} send(s) got no angle back "
                       "and keep the copied one; re-run to ask again")
    for s in fills:
        ang = cache.get(signature(s, pf.name))
        if not ang:
            continue
        # holiday_fill hands every extra send the SAME variants list (and deepcopy keeps the
        # sharing), so each slot gets its own copies before its angle is written
        s["variants"] = [dict(v) if isinstance(v, dict) else v for v in s.get("variants") or []]
        for v in s["variants"]:
            if isinstance(v, dict):
                if v.get("angle") and v["angle"] != ang and "angle_copied" not in v:
                    v["angle_copied"] = v["angle"]
                v["angle"] = ang
        if not s.get("variants"):
            s["angle"] = ang
        s["angle_source"] = "holiday fill angle (fill_angles.py)"
    return log
