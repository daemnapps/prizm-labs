#!/usr/bin/env python3
"""
offer.py — build, validate and emit offer sheet payloads for offer-agent.

Usage:
    python offer.py new <offer_id> <out.md>
    python offer.py validate <file.md>
    python offer.py to-json <file.md> <out.json>
    python offer.py schema

THE HARD STOP: `envelope_active: no` fails validation outright. Absence of a
human-set envelope is not permission to improvise — it means nobody has decided
what the brand can afford. Margin and discount are RECOMPUTED from the math table
and compared to the bounds, never read from the verdict column.

The validator is the point. A offer sheet that does not pass it is not a offer sheet,
it is a draft with a filename — and the whole reason this skill exists is that
the gate below is not a matter of anyone's judgement on the day.
"""
import sys, re, json, pathlib, argparse, datetime

HERE = pathlib.Path(__file__).resolve().parent
MASTER = HERE.parent / "assets" / "Offer-MASTER.md"

SECTIONS = ['## METADATA', '## ENVELOPE', '## PROVENANCE', '## STRUCTURE', '## MARGIN MATH', '## ENVELOPE CHECK', '## COLLISION']
ENUMS = {'overlap': ['none', 'sequenced', 'deliberate'], 'verdict': ['PASS', 'BREACH']}


def _section(text, name):
    m = re.search(rf"^#+ {re.escape(name.lstrip('# '))}[ \t]*$(.*?)(?=^#+ |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def _fields(chunk):
    """`- **key**: value` pairs. Values still wrapped in the template's
    parenthetical prompt are treated as UNFILLED, not as content.

    CAUTION: the separator is `[ \t]*`, never `\s*`. `\s` matches newlines, so on
    an EMPTY field it runs past the line ending and captures the NEXT field's
    line as this field's value — silently consuming that field entirely. The
    symptom is a populated field reported as missing, which sends you hunting
    through the document instead of looking at the parser."""
    out = {}
    for m in re.finditer(r"^- \*\*(\w+)\*\*:[ \t]*(.*)$", chunk, re.M):
        v = m.group(2).strip().strip('"')
        if v and not v.startswith("("):
            out[m.group(1)] = v
    return out


def _rows(chunk, ncols):
    rows = []
    for line in chunk.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip().strip('"') for c in line.strip().strip("|").split("|")]
        if len(cells) < ncols or set("".join(cells)) <= set("-: "):
            continue
        if cells[0].lower() in ['bound', 'unit price', 'field']:
            continue
        rows.append(cells)
    return rows


def _items(chunk):
    return [m.group(1).strip() for m in re.finditer(r"^- (?!\*\*)(.+)$", chunk, re.M)
            if not m.group(1).strip().startswith("(")]


def parse(path):
    text = pathlib.Path(path).read_text()
    ident = re.search(r"# OFFER — (\S+)", text)
    doc = {"offer_id": ident.group(1) if ident else None}
    meta = {}
    for c in _rows(_section(text, "METADATA"), 2):
        meta[c[0].strip().lower().replace(" ", "_")] = c[1]
    doc["metadata"] = meta
    doc["envelope"] = _fields(_section(text, "ENVELOPE"))
    doc["provenance"] = _fields(_section(text, "PROVENANCE"))
    doc["structure"] = _fields(_section(text, "STRUCTURE"))
    mm = _rows(_section(text, "MARGIN MATH"), 7)
    doc["margin"] = dict(zip(
        ["unit_price", "unit_cost", "cogs", "discount_pct", "net_take", "contribution", "margin_pct"],
        mm[0])) if mm else {}
    doc["envelope_check"] = [
        {"bound": c[0], "says": c[1], "offer": c[2], "verdict": (c[3] if len(c) > 3 else "").upper()}
        for c in _rows(_section(text, "ENVELOPE CHECK"), 4)]
    doc["collision"] = _fields(_section(text, "COLLISION"))
    return doc, text


def new(args):
    out = pathlib.Path(args.out)
    if out.exists():
        sys.exit(f"FAIL: {out} exists — one offer sheet per offer_id, never overwrite")
    t = MASTER.read_text().replace("{offer_id}", getattr(args, "offer_id"))
    t = t.replace("{date}", datetime.date.today().isoformat())
    out.write_text(t)
    print(f"created {out}")
    print("Load the ENVELOPE first. If there is no active envelope, stop and escalate.")


def validate(args):
    doc, text = parse(args.run)
    ok, flags = [], []

    def need(cond, okmsg, flagmsg):
        (ok if cond else flags).append(okmsg if cond else flagmsg)

    need(bool(doc.get("offer_id")) and doc["offer_id"] != "{offer_id}",
         f"offer_id: {doc.get('offer_id')}", "NO OFFER_ID in the title line")
    for s in SECTIONS:
        need(s.lstrip("# ") in text, f"section {s}", f"MISSING SECTION: {s}")
    if "Delete this instruction line" in text:
        flags.append("TEMPLATE INSTRUCTION line(s) still present")

    def num(v):
        try:
            return float(re.sub(r"[^0-9.\-]", "", str(v)))
        except (TypeError, ValueError):
            return None

    av = doc["metadata"].get("avatar_id", "")
    need(bool(re.fullmatch(r"AV-\d{2}(\.[a-z])?", av or "")), f"avatar: {av}",
         "AVATAR ID missing or malformed — without it the collision check is impossible")

    env = doc["envelope"]
    active = (env.get("envelope_active") or "").lower()
    if active != "yes":
        flags.append("HARD STOP: no active envelope (envelope_active is "
                     f"'{active or 'blank'}'). Absence of bounds is not an open field — it "
                     "means nobody has decided what this brand can afford. Escalate; do not "
                     "structure an offer.")
    else:
        ok.append("envelope active")

    prov = doc["provenance"]
    need(bool(prov.get("finding")), "provenance.finding",
         "NO FINDING CITED — an offer with no provenance is a guess with a price on it")
    need(bool(prov.get("competitor")), "provenance.competitor", "NO COMPETITOR OBSERVATION cited")
    for k in ("finding", "competitor"):
        if (prov.get(k) or "").lower().startswith("none") and not prov.get("note"):
            flags.append(f"provenance.{k} is 'none' with no reason in note")

    st = doc["structure"]
    for k in ("included", "price", "terms", "risk_reversal"):
        need(bool(st.get(k)), f"structure.{k}", f"STRUCTURE missing {k}")

    m = doc["margin"]
    need(bool(m), "margin table present", "MARGIN MATH empty — a price with no arithmetic is a wish")
    for k, v in m.items():
        if num(v) is None:
            flags.append(f"margin.{k} is not a number ('{v}') — missing cost data stops the "
                         "sheet, it does not get estimated")

    # Recomputed, not read. Same reason the truth gate is recomputed: a bound
    # you have to remember to check is not a bound.
    floor, mp = num(env.get("floor_margin_pct")), num(m.get("margin_pct"))
    if floor is not None and mp is not None:
        need(mp >= floor, f"margin {mp} clears floor {floor}",
             f"MARGIN BREACH: {mp} pct against a floor of {floor} pct. The floor is a floor, "
             "not an opening position. Escalate — this is not a flag to override.")
    cap, disc = num(env.get("max_discount_pct")), num(m.get("discount_pct"))
    if cap is not None and disc is not None:
        need(disc <= cap, f"discount {disc} within cap {cap}",
             f"DISCOUNT BREACH: {disc} pct against a cap of {cap} pct. Escalate.")

    checks = doc["envelope_check"]
    need(bool(checks), f"envelope checks: {len(checks)}", "ENVELOPE CHECK empty — walk every bound")
    for c in checks:
        if c["verdict"] not in ENUMS["verdict"]:
            flags.append(f"envelope check '{c['bound']}': verdict must be PASS or BREACH")
        elif c["verdict"] == "BREACH":
            flags.append(f"BREACH on '{c['bound']}' — stop and escalate")

    col = doc["collision"]
    need(col.get("overlap") in ENUMS["overlap"], f"overlap: {col.get('overlap')}",
         f"COLLISION overlap must be one of {ENUMS['overlap']}")
    need(bool(col.get("cannibalisation")), "cannibalisation named",
         "CANNIBALISATION blank — an offer that only adds is rare enough to be suspicious of")

    print(f"\n=== OFFER VALIDATION: {pathlib.Path(args.run).name} ===\n")
    for o in ok:
        print(f"  ok    {o}")
    print()
    if flags:
        for f in flags:
            print(f"  FLAG  {f}")
        print(f"\n{len(flags)} issue(s). A BREACH is an escalation, not a flag to override.\n")
        sys.exit(1)
    print("  PASS  offer is inside the envelope. Emit with to-json.\n")


def to_json(args):
    doc, _ = parse(args.run)
    pathlib.Path(args.out).write_text(json.dumps(doc, indent=2))
    print(f"wrote payload -> {args.out}")
    print("This payload is the offers write. critic-agent re-checks it; this PASS is not approval.")


def schema(args):
    print(json.dumps({"sections": SECTIONS, "enums": ENUMS}, indent=2))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("offer_id"); n.add_argument("out")
    v = sub.add_parser("validate"); v.add_argument("run")
    t = sub.add_parser("to-json"); t.add_argument("run"); t.add_argument("out")
    sub.add_parser("schema")
    a = p.parse_args()
    {"new": new, "validate": validate, "to-json": to_json, "schema": schema}[a.cmd](a)


if __name__ == "__main__":
    main()
