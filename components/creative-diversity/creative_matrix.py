#!/usr/bin/env python3
"""THE CREATIVE MATRIX: the grid every batch goes through before anything is made, for any brand and any format.

    creative_matrix.py make  <brand> <batch> --people <sub>:<n>[,<sub>:<n>] [--kind image|video|carousel] [--have <id>,<id>]
    creative_matrix.py check <brand> <batch>            the rules, no model
    creative_matrix.py lock  <brand> <batch>            every row goes on the plan (creative_plan.py), so no other batch takes it
    creative_matrix.py cell  <brand> <batch> <row> <run folder>     the row rides with the run; its writers are handed it
    creative_matrix.py swipes <brand> <batch> <row>     every swipe we have whose own format is the row's
    creative_matrix.py back  <brand> <row id> profile=… …   what was really made, against its row
    creative_matrix.py show  <brand> <batch> [--html F]

    people -> grid -> check -> make -> read back -> file

A row is one picture or cut; a headline version is not a row. Seven columns: what is said (profile, awareness, angle) and
what is seen (format, face, setting, look). Every value is from a list; the rules are in dimensions.json `matrix` and are
checked by code. A model only picks among the open values for a person, with the fact of theirs it stands on. The record
is runs/creative-diversity/<brand>/batches/<batch>.json. Nothing calls Meta.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.append(str(HERE))
import creative_plan as PL  # noqa: E402

MX = json.loads((HERE / "dimensions.json").read_text())["matrix"]
SAID, SEEN = MX["said"], MX["seen"]
COLS = SAID + SEEN
RULE = {r["id"]: r for r in MX["rules"]}
AGES = ("18-24", "25-34", "35-44", "45-54", "55-64", "65-plus")
ETH = ("black", "white", "latino", "east-asian", "southeast-asian", "south-asian", "middle-eastern", "mixed")
KINDS = {"image": ("IMAGE_FORMATS", "IMAGE_STYLES"), "video": ("VIDEO_FORMATS", "VIDEO_STYLES"), "carousel": ("CAROUSEL_FORMATS", "IMAGE_STYLES")}


def values(brand, kind="image"):
    """{column: [allowed values]} from the brand's and the library's own lists."""
    L = PL._own("tag").lists(brand)
    ids = lambda t: re.findall(r"`([^`]+)`", t)                                                            # noqa: E731
    fm, st = KINDS[kind]
    formats = ids(L[fm]) + (ids(L["VIDEO_STRUCTURES"]) if kind == "video" else [])
    return {"awareness": ids(L["AWARENESS"]), "angle": ids(L["ANGLES"]), "format": formats, "setting": ids(L["SETTINGS"]), "look": ids(L[st]),
            "face": ["none"] + ["%s/%s/%s" % (g, a, e) for g in ("male", "female") for a in AGES for e in ETH],
            "_text": {"angle": L["ANGLES"], "setting": L["SETTINGS"]}}


def apart(a, b):
    """(columns apart, seen columns apart). A cell nobody knows is not a difference."""
    n, diff = PL.M.distance(a, b)
    return n, len([k for k in diff if k in SEEN])


def problems(rows, vals=None, outside=()):
    """Every rule a grid breaks, in plain words. rows: [{"id", "moves"}]; outside: [(name, moves)]."""
    bad = []
    for r in rows:
        for k in COLS:
            v = r["moves"].get(k)
            if not v:
                bad.append("%s: %s is empty" % (r["id"], PL.NAMES[k]))
            elif vals and k in vals and v not in vals[k] and not r.get("fixed"):
                bad.append("%s: %s `%s` is not on the list" % (r["id"], PL.NAMES[k], v))
    for a, b in combinations(rows, 2):
        if a.get("fixed") and b.get("fixed"):
            continue
        n, s = apart(a["moves"], b["moves"])
        if n < RULE["pair"]["min"] or s < RULE["seen"]["min"]:
            bad.append("%s and %s: %d apart, %d of them seen" % (a["id"], b["id"], n, s))
    for r in rows:
        if r.get("fixed"):
            continue
        for name, m in outside:
            known = [k for k in COLS if r["moves"].get(k) not in (None, "", "unclear") and m.get(k) not in (None, "", "unclear")]
            if len(known) < 5:
                continue
            n, s = apart(r["moves"], m)
            if n < RULE["pair"]["min"] or s < RULE["seen"]["min"]:
                bad.append("%s is too close to %s: %d apart, %d of them seen" % (r["id"], name, n, s))
    if len(rows) >= RULE["spread"]["from_rows"]:
        for k in SEEN:
            for v, c in Counter(r["moves"].get(k) for r in rows).items():
                if c > len(rows) * RULE["spread"]["max_share"]:
                    bad.append("%s: `%s` fills %d of %d rows" % (PL.NAMES[k], v, c, len(rows)))
    return bad


def outside_of(brand, mine=()):
    live, _ = PL.running(brand)
    return [("a running ad (%s)" % a, m) for a, m in live] + [("%s (%s)" % (k, r.get("state")), r["moves"]) for k, r in PL.ledger(brand).items() if k not in mine and r.get("state") != "dropped"]


def used(brand):
    c = {k: Counter() for k in COLS}
    for _, m in outside_of(brand):
        for k in COLS:
            if m.get(k):
                c[k][m[k]] += 1
    return c


def _who():
    p = str(ROOT / "components" / "creative-strategist" / "machine")
    if p not in sys.path:
        sys.path.append(p)
    import who
    return who


def avatar_of(brand, sub):
    W = _who()
    for a in W.avatars(brand):
        if sub in W.subs(brand, a):
            return a
    if sub in W.avatars(brand):                              # the whole avatar, no one narrowing thing
        return sub
    raise SystemExit("no person %s in %s" % (sub, brand))


def person_text(brand, sub):
    W = _who()
    a = avatar_of(brand, sub)
    t = W.full_page(W.full(brand, a, "" if sub == a else sub))
    d = W.section(W.S.text_of(W.avatar_dir(brand, a) / "profile.md"), "demographics")
    return "### `%s`\n\n%s\n\nDemographics this person may have: %s\n" % (sub, t[:5200], d[:900] or "see the person")


def ask_model(p):
    sys.path.append(str(ROOT / "components" / "run-kit"))
    from run_kit import model as M
    return M.call(p, M.pick("designs", len(p))[0], label="creative matrix")


def fill(brand, people, kind="image", have=(), ask=None, tries=4, pin=None):
    """The grid: [{"id", "moves", "picture", "fact", "fixed"}]. `people`: [(sub, n)]. `have`: ids on the plan that stay as they are."""
    vals, c, led = values(brand, kind), used(brand), PL.ledger(brand)
    fixed = [{"id": h, "moves": led[h]["moves"], "fixed": True, "picture": led[h].get("picture", "")} for h in have if h in led]
    out = outside_of(brand, mine=set(have))
    num = lambda k: " · ".join("`%s` %d" % (v, c[k][v]) for v in sorted(vals[k], key=lambda v: c[k][v]))   # noqa: E731
    text = lambda k: "\n".join("%s (%d)" % (l, c[k][re.findall(r"`([^`]+)`", l)[0]]) if "`" in l else l for l in vals["_text"][k].splitlines())   # noqa: E731
    near = "\n".join("- " + PL.short(m) for n, m in out if m.get("profile") in {p for p, _ in people})[:3000] or "none"
    base = (HERE / "prompts" / "matrix-fill-v1.md").read_text()
    for k, v in {"people": "\n".join(person_text(brand, p) for p, _ in people), "awareness": num("awareness"), "angles": text("angle"), "formats": num("format"), "settings": text("setting"),
                 "looks": num("look"), "fixed": "In this batch:\n" + ("\n".join("- " + PL.short(f["moves"]) for f in fixed) or "none") + "\n\nAlready out for these people:\n" + near,
                 "want": "; ".join("%d rows for `%s`" % (n, p) for p, n in people)}.items():
        base = base.replace("{" + k + "}", v)
    if pin:                                                   # what is already decided (the swipe's format, the run's face)
        base += "\n\nFixed already, the same in every row you give: " + "; ".join("%s = `%s`" % x for x in pin.items())
    note, rows, bad = "", [], ["not filled"]
    for _ in range(tries):
        raw = (ask or ask_model)(base.replace("{note}", note))
        m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.S)
        got = json.loads(m.group(1) if m else raw[raw.index("{"):raw.rindex("}") + 1])["rows"]
        n, rows = Counter(), []
        for g in got:
            g = PL.M.norm(g)                                         # a model answering in the old words still reads
            w = re.sub(r"^sub-\d+-", "", g.get("profile", ""))
            w = people[0][0] if len(people) == 1 else w              # one person asked for is the person, whatever it is called back
            n[w] += 1
            rows.append({"id": "%s-%d" % (w, n[w] + sum(1 for f in fixed if f["moves"].get("profile") == w)), "moves": dict({k: g.get(k) for k in COLS}, profile=w), "picture": g.get("picture", ""), "fact": g.get("fact", "")})
        for r in rows:
            r["moves"].update(pin or {})
        bad = problems(fixed + rows, {k: v for k, v in vals.items() if k not in (pin or {})}, out) + ["%d rows asked for %s, %d given" % (k, p, n[p]) for p, k in people if n[p] != k]
        if not bad:
            break
        note = "\n\nYOUR LAST GRID BROKE THESE. Change only the rows named and give every row again:\n" + "\n".join("- " + b for b in bad[:30]) + "\n\nYour last grid:\n" + json.dumps(got, ensure_ascii=False)
    return fixed + rows, bad


POINT_KINDS = (("desires", "want", "desire"), ("emotions", "feel", "feeling"), ("beliefs", "belief", "belief"), ("roles", "role", "role"),
               ("experiences", "fact", "experience"), ("behaviors", "does", "behavior"))


def points(brand, sub):
    """Every point in a person's own profile an ad can stand on (owner, 2026-11-26: "go into the actual profile of that
    consumer to understand what we can make the variations on"): each desire, feeling, belief, role and doubt, with the
    real lines it was read from. [{kind, point, said: [verbatim], rows, extra}]"""
    W = _who()
    a = avatar_of(brand, sub)
    s = W.slots(brand, a, "" if sub == a else sub)
    bank = W.bank(brand, a)
    words = lambda ids: [bank[i]["text"] for i in ids or [] if i in bank and len(bank[i]["text"]) <= 240][:2]   # noqa: E731
    out = []
    for key, field, kind in POINT_KINDS:
        for x in s.get(key) or []:
            out.append({"kind": kind, "point": x.get(field) or "", "said": words(x.get("rows")), "rows": x.get("rows") or [],
                        "extra": {k: v for k, v in x.items() if k in ("urgency", "staying", "human", "kind")}})
    for name, x in (s.get("doubts") or {}).items():
        out.append({"kind": "doubt", "point": name.replace("-", " "), "said": [x.get("said")] if x.get("said") else words(x.get("rows")),
                    "rows": x.get("rows") or [], "extra": {"lead": name == s.get("doubt_lead")}})
    for x in s.get("objections") or []:                       # every other doubt anyone voiced (who.py v3 fill)
        out.append({"kind": "doubt", "point": (x.get("kind") or "").replace("-", " "), "said": [x["said"]] if x.get("said") else words(x.get("rows")),
                    "rows": x.get("rows") or [], "extra": {"objection": True}})
    return [p for p in out if p["point"]]


def family_map(brand, winner, people):
    """Every variation a winner can have: its concept (angle + format) kept, aimed at each person it fits, one profile
    point at a time, each standing on that point's real lines. Free, no model. Written to
    runs/creative-diversity/<brand>/families/<winner>.json and returned."""
    led = PL.ledger(brand)
    if winner not in led:
        raise SystemExit("no row %s on the plan for %s" % (winner, brand))
    W, base = _who(), led[winner]["moves"]
    rows = []
    for sub in people:
        a = avatar_of(brand, sub)
        s = W.slots(brand, a, "" if sub == a else sub)
        for i, p in enumerate(points(brand, sub), 1):
            aw = {"doubt": "solution-aware" if p["point"] in ("does it work", "for me") else "product-aware"}.get(p["kind"],
                                                                                                                 s.get("awareness_lead") or base["awareness"])
            rows.append({"id": "%s-%s-%d" % (winner.replace(brand + "-batch-", ""), sub, i), "family": winner,
                         "moves": dict(base, profile=sub, awareness=aw, face="?", setting="?", look="?"),
                         "point": p, "made": False})
    out = {"brand": brand, "winner": winner, "concept": {k: base[k] for k in ("angle", "format")}, "people": list(people),
           "made": date.today().isoformat(), "rows": rows,
           "what": "every variation this winner can have: one person, one point in that person's own profile, its real lines"}
    f = PL.file(brand).parent / "families" / (winner + ".json")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def bank_map(brand, people=None):
    """EVERY proven ad in the brand's winners bank, each aimed at every person and every point of their profile (owner,
    2026-11-26: "it would be a printer ... scale what works, make as much of it as we can"). No caps, no model. One
    compact file: per winner its idea, format and numbers, and per person how many points it can stand on.
    runs/creative-diversity/<brand>/families/_bank.json"""
    bank = json.loads((ROOT / "runs" / "winners" / brand / "bank.json").read_text())["rows"]
    tags = json.loads((ROOT / "runs" / "winners" / brand / "tags.json").read_text())
    W = _who()
    people = people or [x for a in W.avatars(brand) for x in (W.subs(brand, a) or [a])]
    per = {}
    for p in people:
        try:
            per[p] = len(points(brand, p))
        except (Exception, SystemExit):                       # noqa: BLE001  a person with no profile yet counts 0
            per[p] = 0
    rows = []
    for r in bank:
        tg = next((tags[n] for n in (r.get("ad_names") or []) + [r.get("name")] if n in tags), {})
        snap = (r.get("snapshots") or [{}])[-1]
        rows.append({"id": r["id"], "name": r.get("name"), "state": r.get("state"), "core": r.get("core"),
                     "idea": tg.get("message") or (r.get("words") or {}).get("core_message") or r.get("headline"),
                     "on_screen": tg.get("on_screen"), "format": tg.get("format") or r.get("format"),
                     "purchases": snap.get("purchases"), "spend": snap.get("spend"), "cpa": snap.get("cpa"),
                     "variations": sum(per.values())})
    out = {"brand": brand, "made": date.today().isoformat(), "people": per, "winners": rows,
           "total": sum(x["variations"] for x in rows),
           "what": "every proven ad x every person x every point of that person's profile: the printer's full order book"}
    f = PL.file(brand).parent / "families" / "_bank.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def family(brand, winner, people, kind="image", ask=None):
    """A winner's variations (owner, 2026-11-26: "each of these creatives can have their own variations based off the
    matrix ... hundreds of ads every day, each aimed at an exact point"). The winner's concept stays (its angle and its
    format); every row moves who it is for, how aware he is, the face, the setting and the look, each row standing on
    that person's own words. Returns (rows, bad); the winner rides as the fixed row the others are kept apart from."""
    led = PL.ledger(brand)
    if winner not in led:
        raise SystemExit("no row %s on the plan for %s" % (winner, brand))
    pin = {k: led[winner]["moves"][k] for k in ("angle", "format")}
    rows, bad = fill(brand, people, kind, have=[winner], ask=ask, pin=pin)
    W = _who()
    for r in rows:
        if r.get("fixed"):
            continue
        sub = r["moves"]["profile"]
        try:
            a = avatar_of(brand, sub)
            bank, ids = W.his_rows(brand, a, "" if sub == a else sub, n=6)
            r["said"] = [bank[i]["text"] for i in ids if len(bank[i]["text"]) <= 220][:3]
            r["desire"] = W.desire_of(W.full_page(W.full(brand, a, "" if sub == a else sub)))
        except (Exception, SystemExit) as e:                  # noqa: BLE001  a row without its words still shows its gap
            r["said"], r["desire"] = [], "not found: " + str(e)[:80]
        r["family"] = winner
    return rows, bad


def file(brand, batch):
    return PL.file(brand).parent / "batches" / (batch + ".json")


def save(brand, batch, rows, kind, bad):
    f = file(brand, batch)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"brand": brand, "batch": batch, "kind": kind, "made": date.today().isoformat(), "passes": not bad, "problems": bad, "rows": rows}, indent=1, ensure_ascii=False) + "\n")
    return f


def load(brand, batch):
    d = json.loads(file(brand, batch).read_text())
    PL.M.norm_items(d.get("rows"))                            # a grid saved before 26 Nov says who / argument
    return d


def lock(brand, batch):
    d = load(brand, batch)
    bad = problems(d["rows"], None, outside_of(brand, mine={r["id"] for r in d["rows"]} | {"%s/%s" % (batch, r["id"]) for r in d["rows"]}))
    if bad:
        raise SystemExit("refused: the grid does not pass\n- " + "\n- ".join(bad))
    for r in d["rows"]:
        if not r.get("fixed"):
            PL.claim(brand, "%s/%s" % (batch, r["id"]), r["moves"], by="matrix " + batch, force=True)
    return len(d["rows"])


def cell_text(r):
    m = r["moves"]
    return ("**This ad's row on the creative matrix (fixed; write inside it):**\n\n| Profile | Awareness | Angle | Format | Face | Setting | Look |\n|---|---|---|---|---|---|---|\n| %s |\n\nWhat is seen: %s" % (
        " | ".join(str(m[k]) for k in COLS), r.get("picture") or "as the row says"))


def cell(brand, batch, row, run):
    d = load(brand, batch)
    r = next((x for x in d["rows"] if x["id"] == row), None)
    if not r:
        raise SystemExit("no row %s on %s" % (row, batch))
    f = Path(run) / "matrix-cell.json"
    f.write_text(json.dumps({"brand": brand, "batch": batch, "row": row, "id": "%s/%s" % (batch, row), "moves": r["moves"], "picture": r.get("picture"), "text": cell_text(r)}, indent=1, ensure_ascii=False) + "\n")
    return f


def back(planned, made):
    """(columns that came out as planned, [(column, planned, made)])"""
    planned, made = PL.M.norm(planned), PL.M.norm(made)
    off = [(k, planned[k], made.get(k)) for k in COLS if made.get(k) not in (None, "", "unclear") and made.get(k) != planned[k]]
    return len(COLS) - len(off), off


def row_of(run):
    try:
        r = json.loads((Path(run) / "matrix-cell.json").read_text())
    except (OSError, ValueError):
        return {}
    if isinstance(r, dict) and isinstance(r.get("moves"), dict):
        r["moves"] = PL.M.norm(r["moves"])                    # a cell written before 26 Nov says who / argument
    return r


def start(run, brand, person, kind="image", pin=None, ask=None, say=print):
    """NO ROW, NO START. The run's row: the one it was given, fitted to its swipe; else one is made now for its person.
    Raises ValueError with the rules it breaks. `pin`: what the swipe and the order already decide (format, face)."""
    run, pin = Path(run), {k: v for k, v in (pin or {}).items() if v}
    r = row_of(run)
    if r:
        off = {k: v for k, v in pin.items() if r["moves"].get(k) != v}
        if not off:
            return r
        mv = dict(r["moves"], **off)                         # the swipe decides its own format: the row moves to it, if the grid still holds
        near = [(n, m) for n, m in outside_of(brand, mine={r["id"], run.name})]
        bad = problems([{"id": r["row"], "moves": mv}], None, near)
        if bad:
            raise ValueError("the swipe is %s and the row is not; moving the row breaks the grid: %s" % (", ".join("%s %s" % (PL.NAMES[k], v) for k, v in off.items()), "; ".join(bad[:4])))
        PL.claim(brand, r["id"], mv, by="matrix " + r["batch"], force=True)
        r = dict(r, moves=mv, text=cell_text({"moves": mv, "picture": r.get("picture")}))
        (run / "matrix-cell.json").write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
        say("  matrix: the row moved to its swipe (%s)" % ", ".join("%s %s" % x for x in off.items()))
        return r
    person = re.sub(r"^sub-\d+-", "", person or "")
    old = PL.ledger(brand).get(run.name)
    rows, bad = fill(brand, [(person, 1)], kind, ask=ask, pin=pin)
    if bad:
        raise ValueError("no row fits: " + "; ".join(bad[:4]))
    x = dict(rows[0], id=run.name)
    save(brand, run.name, [x], kind, [])
    PL.claim(brand, run.name, x["moves"], by="matrix, made for this run", brief=(old or {}).get("brief"), force=True)
    r = {"brand": brand, "batch": run.name, "row": run.name, "id": run.name, "moves": x["moves"], "picture": x.get("picture"), "text": cell_text(x)}
    (run / "matrix-cell.json").write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n")
    say("  matrix: its row is made (%s)" % PL.short(x["moves"]))
    return r


def finished(brand, brief, made):
    """The finished picture against its row; the plan keeps what was made. {"as_planned": n, "off": [...]} or None with no row."""
    row = next((r for k, r in PL.ledger(brand).items() if brief in (k, r.get("brief"))), None)
    if not row:
        return None
    ok, off = back(row["moves"], made)
    PL.made(brand, brief, made)
    return {"as_planned": ok, "off": [list(x) for x in off], "seen_off": len([x for x in off if x[0] in SEEN])}


def swipes(brand, fmt, kind="image"):
    """Every swipe already torn down whose own format is this one: (views it has, where it is)."""
    out = {}
    for f in (ROOT / "runs" / ("image-teardown" if kind != "video" else "video-teardown")).glob("*/*/elements.json"):
        try:
            d = json.loads(f.read_text())
            src = json.loads((f.parent / "source.json").read_text())
        except (OSError, ValueError):
            continue
        if fmt in (d.get("labels") or {}).values():
            for x in src.get("files") or [src.get("block_file")]:
                out[x] = {"swipe": x, "from": src.get("swipe"), "seen_in": str(f.parent.relative_to(ROOT))}
    return sorted(out.values(), key=lambda x: str(x["swipe"]))


def table(d):
    out = ["# Creative matrix: " + d["batch"], "", "%s. %d rows." % ("Passes" if d["passes"] else "Does not pass", len(d["rows"])), "", "| Row | Profile | Awareness | Angle | Format | Face | Setting | Look | What is seen |", "|---|---|---|---|---|---|---|---|---|"]
    out += ["| %s | %s | %s |" % (r["id"], " | ".join(str(r["moves"].get(k)) for k in COLS), r.get("picture") or "") for r in d["rows"]]
    return "\n".join(out + [""] + ["- " + b for b in d["problems"]]) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("do", choices=("make", "family", "map", "bank", "check", "lock", "cell", "swipes", "back", "show"))
    ap.add_argument("brand")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--people", default="")
    ap.add_argument("--kind", choices=tuple(KINDS), default="image")
    ap.add_argument("--have", default="")
    a = ap.parse_args(argv)
    if a.do == "make":
        people = [(p.split(":")[0], int((p.split(":") + ["1"])[1])) for p in a.people.split(",") if p]
        rows, bad = fill(a.brand, people, a.kind, [h for h in a.have.split(",") if h])
        save(a.brand, a.rest[0], rows, a.kind, bad)
        print(table(load(a.brand, a.rest[0])))
        return 1 if bad else 0
    if a.do == "bank":                                       # creative_matrix.py bank <brand>: every winner x every person x every point
        m = bank_map(a.brand)
        print("%d winners x %d people = %s variations" % (len(m["winners"]), len(m["people"]), format(m["total"], ",")))
        return 0
    if a.do == "map":                                        # creative_matrix.py map <brand> <winner row id> --people a,b,c
        m = family_map(a.brand, a.rest[0], [p.split(":")[0] for p in a.people.split(",") if p])
        print("%d variations for %s across %d people" % (len(m["rows"]), a.rest[0], len(m["people"])))
        return 0
    if a.do == "family":                                     # creative_matrix.py family <brand> <winner row id> --people …
        people = [(p.split(":")[0], int((p.split(":") + ["1"])[1])) for p in a.people.split(",") if p]
        rows, bad = family(a.brand, a.rest[0], people, a.kind)
        name = a.rest[1] if len(a.rest) > 1 else "family-" + a.rest[0].replace(a.brand + "-batch-", "")
        save(a.brand, name, rows, a.kind, bad)
        print(table(load(a.brand, name)))
        return 1 if bad else 0
    if a.do == "swipes":                                      # creative_matrix.py swipes <brand> <format, or batch row>
        fmt = a.rest[0] if len(a.rest) == 1 else next(r["moves"]["format"] for r in load(a.brand, a.rest[0])["rows"] if r["id"] == a.rest[1])
        for x in swipes(a.brand, fmt, a.kind):
            print("%s  (%s)" % (x["swipe"], x["seen_in"]))
        return 0
    if a.do == "back":
        row = PL.ledger(a.brand)[a.rest[0]]["moves"]
        ok, off = back(row, dict(x.split("=", 1) for x in a.rest[1:]))
        print("%d of 7 as planned%s" % (ok, "".join("\n- %s: planned %s, made %s" % (PL.NAMES[k], p, m) for k, p, m in off)))
        return 0 if len(off) < 2 else 1
    d = load(a.brand, a.rest[0])
    if a.do == "check":
        bad = problems(d["rows"], None, outside_of(a.brand, mine={r["id"] for r in d["rows"]} | {"%s/%s" % (a.rest[0], r["id"]) for r in d["rows"]}))
        print("passes" if not bad else "\n".join("- " + b for b in bad))
        return 1 if bad else 0
    if a.do == "lock":
        print("%d rows on the plan" % lock(a.brand, a.rest[0]))
    elif a.do == "cell":
        print(cell(a.brand, a.rest[0], a.rest[1], a.rest[2]))
    else:
        print(table(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
