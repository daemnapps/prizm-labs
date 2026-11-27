#!/usr/bin/env python3
"""bank: keep one bank per brand, the record the feed, the score and the proven gate read.

Normally driven by winners.py. Directly:
    bank.py --brand <brand> --audit <runs/winners/<brand>/audit/<window>>       # rows from the audit's ranked.json
    bank.py --brand <brand> --score <runs/winners/<brand>/score/<asof>/score.json>  # chain-made ads the score joined
    [--root REPO]

Offline. Stdlib only. Read-only on its inputs. Writes runs/winners/<brand>/bank.json.

Audit inputs:
  <audit>/window.json          brand, since, until, pulled_at
  <audit>/ranked.json          rows[]: rank, name, spend, purchases, value, first, last, ids[], variants[], ...
                               and `core` = how many of the top rows make the Core set
  <audit>/teardowns/NN-*/teardown.md  hook (first spoken words + on-screen text), core message, offer: quoted

Row id: `<brand>-<first Meta ad id>`. A re-run matches an existing row by any shared ad id, so ids stay put.
Each row carries `snapshots`, one per audit window (since-until) or score window; a re-run with a window
already on the row changes nothing; a new window appends. A re-bank never drops words already in a row.
`state` is `winner` when the row's newest snapshot clears the `bar` at the top of the file, else `candidate`;
an open bar means every row is a candidate. `core` is counted from the widest audit window (longest since-to-until;
tie, the newest), so a shorter audit adds its snapshots and rows and leaves `core` and the rows' names and copy alone.
Paths in the file are relative to runs/winners/<brand>/.
Exit 2 on bad input.
"""
import argparse, datetime as dt, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402

DEFAULT_ROOT = paths.repo(__file__)
OPEN_NOTE = "Every row is a candidate. The bar for a winner is the brand owner's call and is open."
SET_NOTE = "A row is a winner when its newest snapshot clears the bar; every other row is a candidate."


def brand_dir(root, brand):
    return Path(root) / "runs" / "winners" / brand


def bank_path(root, brand):
    return brand_dir(root, brand) / "bank.json"


class BadInput(Exception):
    pass


def load_json(p):
    p = Path(p)
    if not p.is_file():
        raise BadInput(f"missing input file: {p}")
    try:
        return json.loads(p.read_text())
    except ValueError as e:
        raise BadInput(f"not valid JSON: {p} ({e})")


def rel(root, p):
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(p)


def r2(x):
    return None if x is None else round(float(x), 2)


def metrics(spend, purchases, value):
    spend, purchases, value = r2(spend), r2(purchases), r2(value)
    if purchases is not None and float(purchases).is_integer():
        purchases = int(purchases)
    return {"spend": spend, "purchases": purchases, "value": value,
            "cpa": r2(spend / purchases) if spend is not None and purchases else None,
            "roas": r2(value / spend) if value is not None and spend else None}


def window_days(since, until):
    """How long a window runs, in days; 0 when its dates can't be read."""
    try:
        return (dt.date.fromisoformat(str(until)) - dt.date.fromisoformat(str(since))).days
    except ValueError:
        return 0


def widest_key(w):
    """Sort key for an audit window (a source, snapshot or window.json): longest first, then the newest."""
    return (window_days(w.get("since"), w.get("until")), str(w.get("until")), str(w.get("pulled_at")), str(w.get("since")))


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# ---------- words: teardowns ----------

def md_sections(text):
    """{heading without its number, lowercased: body} for every `## N. Heading` section."""
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(?:\d+\.\s*)?(.+?)\s*$", line)
        if m:
            if cur is not None:
                out.setdefault(cur, "\n".join(buf).strip())
            cur, buf = re.sub(r"\s*\(.*\)\s*$", "", m.group(1)).strip().lower(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out.setdefault(cur, "\n".join(buf).strip())
    return out


def unbold(s):
    return " ".join(s.replace("**", "").split())


def bullet(body, label):
    """Text after the label of the first `- **<label>...:**` bullet, else None."""
    for line in body.splitlines():
        m = re.match(r"^\s*-\s*\*\*" + re.escape(label) + r"[^*]*?:\*\*\s*(.+)$", line, re.I)
        if m:
            return unbold(m.group(1))
    return None


def teardown_words(path):
    s = md_sections(Path(path).read_text())
    words = {"hook": None, "core_message": None, "offer": None}
    hook = s.get("hook")
    if hook:
        spoken, screen = bullet(hook, "First spoken words"), bullet(hook, "On-screen text")
        parts = [f"Spoken: {spoken}" if spoken else None, f"On screen: {screen}" if screen else None]
        words["hook"] = " ".join(p for p in parts if p) or None
    if s.get("core message"):
        words["core_message"] = unbold(s["core message"])
    if s.get("offer"):
        lines = [unbold(re.sub(r"^\s*-\s*", "", l)) for l in s["offer"].splitlines() if l.strip()]
        words["offer"] = " ".join(lines) or None
    return words


def teardown_index(audit, rows):
    """{rank: (teardown path relative to the audit folder, words)}: folder NN-<slug> joins rank NN,
    checked against the row's name."""
    out = {}
    by_rank = {r["rank"]: r for r in rows}
    for f in sorted(Path(audit).glob("teardowns/*/teardown.md")):
        m = re.match(r"^(\d+)-(.+)$", f.parent.name)
        if not m:
            continue
        rank, slug = int(m.group(1)), norm(m.group(2))
        r = by_rank.get(rank)
        if not r or not (norm(r["name"]).startswith(slug[:12]) or slug.startswith(norm(r["name"])[:12])):
            raise BadInput(f"teardown folder {f.parent.name} does not match rank {rank} "
                           f"({r['name'] if r else 'no such rank'})")
        out[rank] = (str(f.relative_to(audit)), teardown_words(f))
    return out


# ---------- bank ----------

def empty_bank(brand):
    return {"brand": brand,
            "bar": {"min_spend": None, "max_cpa": None, "min_roas": None},
            "note": OPEN_NOTE,
            "sources": [], "rows": []}


def load_bank(path, brand):
    if not path.is_file():
        return empty_bank(brand)
    b = load_json(path)
    if not isinstance(b, dict) or b.get("brand") != brand or not isinstance(b.get("rows"), list):
        raise BadInput(f"bank file is not a {brand} bank: {path}")
    return b


def find_row(bank, ad_ids):
    s = set(ad_ids)
    for r in bank["rows"]:
        if s & set(r.get("ad_ids") or []):
            return r
    return None


def union(old, new):
    out = list(old or [])
    for x in new:
        if x not in out:
            out.append(x)
    return out


def add_snapshot(row, snap):
    for s in row.setdefault("snapshots", []):
        if s.get("since") == snap["since"] and s.get("until") == snap["until"] and s.get("kind") == snap["kind"]:
            return False  # same window: replaces nothing
    row["snapshots"].append(snap)
    row["snapshots"].sort(key=lambda s: (str(s.get("until")), str(s.get("pulled_at"))))
    return True


def upsert(bank, brand, ad_ids, fields, snap):
    row = find_row(bank, ad_ids)
    if row is None:
        row = {"id": f"{brand}-{ad_ids[0]}", "state": "candidate"}
        bank["rows"].append(row)
    row["ad_ids"] = union(row.get("ad_ids"), ad_ids)
    if "ad_names" in fields:
        row["ad_names"] = union(row.get("ad_names"), fields.pop("ad_names"))
    for k, v in fields.items():
        if k == "words":
            w = row.setdefault("words", {"hook": None, "core_message": None, "offer": None})
            for wk, wv in (v or {}).items():
                if wv:
                    w[wk] = wv
        elif k == "source":
            src = row.setdefault("source", {})
            src.update({sk: sv for sk, sv in v.items() if sv is not None or sk not in src})
        elif v is not None or k not in row:
            row[k] = v
    row.setdefault("state", "candidate")
    add_snapshot(row, snap)
    return row


def ingest_audit(root, bank, brand, audit):
    audit = Path(audit).expanduser()
    if not audit.is_dir():
        raise BadInput(f"audit folder not found: {audit}")
    win = load_json(audit / "window.json")
    ranked = load_json(audit / "ranked.json")
    if win.get("brand") != brand:
        raise BadInput(f"{audit}/window.json is brand {win.get('brand')!r}, not {brand!r}")
    for k in ("since", "until", "pulled_at"):
        if not win.get(k):
            raise BadInput(f"{audit}/window.json has no {k}")
    rows = ranked.get("rows") if isinstance(ranked, dict) else None
    if not isinstance(rows, list) or not rows:
        raise BadInput(f"{audit}/ranked.json has no rows")
    core = ranked.get("core")
    if not isinstance(core, int):
        raise BadInput(f"{audit}/ranked.json has no core count")
    for r in rows:
        for need in ("rank", "name", "spend", "purchases", "value", "ids"):
            if need not in r:
                raise BadInput(f"{audit}/ranked.json row {r.get('rank')} missing '{need}'")
        if not r["ids"]:
            raise BadInput(f"{audit}/ranked.json row {r['rank']} has no ad ids")

    folder = rel(brand_dir(root, brand), audit)
    tds = teardown_index(audit, rows)
    # a window narrower than one already banked adds snapshots and rows; a row's name and copy stay the widest window's
    widest = widest_audit_source(bank)
    narrower = bool(widest) and widest_key(win)[0] < widest_key(widest)[0]
    for r in sorted(rows, key=lambda r: r["rank"]):
        words, td = None, None
        if r["rank"] in tds:
            td, words = tds[r["rank"]]
            td = f"{folder}/{td}"
        fields = {
            "name": r["name"], "ad_names": list(r.get("variants") or [r["name"]]),
            "format": r.get("format"), "headline": r.get("headline"), "body": r.get("body"),
            **({"description": r["description"]} if r.get("description") else {}),
            "words": words, "core": r["rank"] <= core,
            "source": {"audit": folder, "teardown": td},
        }
        if narrower and find_row(bank, [str(x) for x in r["ids"]]):
            for k in ("name", "format", "headline", "body", "description", "core"):
                fields.pop(k, None)
            fields["source"] = {"teardown": td} if td else {}
        snap = {"kind": "audit", "since": win["since"], "until": win["until"], "pulled_at": win["pulled_at"],
                "audit": folder, "rank": r["rank"], **metrics(r["spend"], r["purchases"], r["value"]),
                "first": r.get("first"), "last": r.get("last")}
        upsert(bank, brand, [str(x) for x in r["ids"]], fields, snap)
    src = {"kind": "audit", "audit": folder, "since": win["since"], "until": win["until"],
           "pulled_at": win["pulled_at"], "creatives": ranked.get("creatives"), "rows": len(rows), "core": core,
           "total_purchases": ranked.get("total_purchases"), "total_spend": ranked.get("total_spend")}
    if not any(s.get("kind") == "audit" and s.get("audit") == folder and s.get("since") == src["since"]
               and s.get("until") == src["until"] for s in bank["sources"]):
        bank["sources"].append(src)  # same window: replaces nothing
    refresh_core(bank)
    return len(rows)


def newest_audit_source(bank):
    audits = [s for s in bank["sources"] if s.get("kind") == "audit"]
    return max(audits, key=lambda s: (str(s.get("until")), str(s.get("pulled_at")), str(s.get("since")))) if audits else None


def widest_audit_source(bank):
    audits = [s for s in bank["sources"] if s.get("kind") == "audit"]
    return max(audits, key=widest_key) if audits else None


def refresh_core(bank):
    """A row is Core only if it made the set in the widest audit window."""
    src = widest_audit_source(bank)
    if not src:
        return
    for row in bank["rows"]:
        row["core"] = any(sn.get("kind") == "audit" and sn.get("since") == src["since"] and sn.get("until") == src["until"]
                          and (sn.get("rank") or src["core"] + 1) <= src["core"] for sn in row.get("snapshots") or [])


# ---------- the bar ----------

def clears(bar, snap):
    """Does a snapshot clear every bar value that is set? A value the snapshot does not have does not clear."""
    for key, field, ok in (("min_spend", "spend", lambda v, b: v >= b), ("max_cpa", "cpa", lambda v, b: v <= b),
                           ("min_roas", "roas", lambda v, b: v >= b), ("min_purchases", "purchases", lambda v, b: v >= b)):
        if bar.get(key) is None:
            continue
        if snap.get(field) is None or not ok(snap[field], bar[key]):
            return False
    return True


def bar_is_open(bank):
    return all(v is None for v in (bank.get("bar") or {}).values())


def is_open(bar):
    return all(v is None for v in (bar or {}).values())


def bar_for(bank, row):
    """The bar a row is judged on: a creator video (a row with a trybe id) on the bank's `creator_bar` when one is
    set, every other row on `bar`. The creator bar exists so creator videos can be judged without moving paid rows."""
    cb = bank.get("creator_bar")
    if row.get("trybe_id") and cb and not is_open(cb):
        return cb
    return bank.get("bar") or {}


def mark_states(bank):
    """`state` for every row, from its newest snapshot, on its bar (bar_for). An open bar makes a row a candidate."""
    for row in bank["rows"]:
        snaps = row.get("snapshots") or []
        bar = bar_for(bank, row)
        row["state"] = "winner" if not is_open(bar) and snaps and clears(bar, snaps[-1]) else "candidate"
    bank["note"] = OPEN_NOTE if bar_is_open(bank) else SET_NOTE


def borrowed(root, run):
    """BORROWED_FROM lines the run printed (stages/4b-hooks.md, deliverable/*), or None."""
    found = []
    base = Path(root) / run
    files = [base / "stages" / "4b-hooks.md"] + sorted((base / "deliverable").glob("*")) if base.is_dir() else []
    for f in files:
        if not f.is_file() or f.suffix not in (".md", ".json", ".txt"):
            continue
        for m in re.finditer(r"BORROWED_FROM\s+(V\d+)\s*:\s*([^\s·]+)", f.read_text(errors="ignore")):
            if m.group(2).lower() != "none":
                item = {"variation": m.group(1), "id": m.group(2)}
                if item not in found:
                    found.append(item)
    return found or None


def ingest_score(root, bank, brand, score_path):
    p = Path(score_path).expanduser()
    if not p.is_absolute() and not p.is_file():
        p = Path(root) / score_path
    sj = load_json(p)
    if not isinstance(sj, dict) or sj.get("brand") != brand:
        raise BadInput(f"{p} is not a {brand} score.json")
    matched = sj.get("matched")
    if not isinstance(matched, list):
        raise BadInput(f"{p} has no 'matched' list")
    where = rel(brand_dir(root, brand), p)
    n = 0
    for a in matched:
        for need in ("ad_id", "ad_name", "spend", "purchases", "run"):
            if need not in a:
                raise BadInput(f"{p}: matched ad missing '{need}'")
        value = a.get("value")
        if value is None and a.get("roas") is not None:
            value = a["spend"] * a["roas"]
        fields = {"ad_names": [a["ad_name"]],
                  "brief_key": a.get("brief_key"), "run": a["run"],
                  "hook_prompt": a.get("hook_prompt"), "brief_prompt": a.get("brief_prompt"),
                  "borrowed_from": borrowed(root, a["run"]),
                  "source": {"score": where}}
        if not find_row(bank, [str(a["ad_id"])]):   # a row the audit named keeps that name
            fields["name"] = a["ad_name"]
        snap = {"kind": "score", "since": sj.get("since"), "until": sj.get("data_through"), "pulled_at": sj.get("asof"),
                "score": where, "rank": None, **metrics(a["spend"], a["purchases"], value)}
        row = upsert(bank, brand, [str(a["ad_id"])], fields, snap)
        row.setdefault("core", False)
        row.setdefault("words", {"hook": None, "core_message": None, "offer": None})
        n += 1
    src = {"kind": "score", "score": where, "asof": sj.get("asof"), "data_through": sj.get("data_through"),
           "rows": n}
    if not any(s.get("kind") == "score" and s.get("score") == src["score"] and s.get("asof") == src["asof"]
               for s in bank["sources"]):
        bank["sources"].append(src)
    return n


KEY_ORDER = ["id", "state", "core", "name", "ad_ids", "ad_names", "format", "trybe_id", "creator", "tags",
             "headline", "body", "description", "words", "brief_key", "run", "hook_prompt", "brief_prompt", "borrowed_from", "source", "snapshots"]


def ordered(bank):
    src = widest_audit_source(bank) or {}

    def best(r):
        a = [s for s in r.get("snapshots") or [] if s.get("kind") == "audit"]
        wide = [s for s in a if (s.get("since"), s.get("until")) == (src.get("since"), src.get("until"))]
        return (0, wide[0]["rank"]) if wide else (1, a[-1]["rank"]) if a else (2, r["id"])
    rows = []
    for r in sorted(bank["rows"], key=best):
        rows.append({k: r[k] for k in KEY_ORDER if k in r} | {k: v for k, v in r.items() if k not in KEY_ORDER})
    head = {"brand": bank["brand"], "bar": bank["bar"]}
    if bank.get("creator_bar") is not None:
        head["creator_bar"] = bank["creator_bar"]
    return {**head, "note": bank.get("note"), "sources": bank["sources"], "rows": rows}


def write(root, bank):
    """Marks every row against the bar and writes the file only if it changed. -> (path, changed)."""
    mark_states(bank)
    out = bank_path(root, bank["brand"])
    text = json.dumps(ordered(bank), indent=1, ensure_ascii=False) + "\n"
    changed = not out.is_file() or out.read_text() != text
    if changed:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    return out, changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--audit")
    ap.add_argument("--score")
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    a = ap.parse_args(argv)
    if not a.audit and not a.score:
        print("give --audit and/or --score", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[a-z0-9-]+", a.brand):
        print(f"bad brand: {a.brand!r}", file=sys.stderr)
        return 2
    root = Path(a.root)
    try:
        bank = load_bank(bank_path(root, a.brand), a.brand)
        msg = []
        if a.audit:
            msg.append(f"{ingest_audit(root, bank, a.brand, a.audit)} audit rows")
        if a.score:
            msg.append(f"{ingest_score(root, bank, a.brand, a.score)} chain-made ads")
    except BadInput as e:
        print(f"bad input: {e}", file=sys.stderr)
        return 2
    out, changed = write(root, bank)
    print(f"{a.brand}: {', '.join(msg)}; bank {len(bank['rows'])} rows -> {rel(root, out)}"
          f"{'' if changed else ' (unchanged)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
