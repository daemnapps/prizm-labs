#!/usr/bin/env python3
"""feed_sections: what the results taught, added to the feed after the winners and the loser.

Normally driven by feed.py (`write`), which writes runs/winners/<brand>/taught.md beside feed.md. Directly, to print
the sections and write nothing:
    feed_sections.py --brand <brand> [--root REPO]

Read-only on its inputs. Offline. Stdlib only. Every section states facts with their source and says plainly when
its source has nothing; none gives a verdict. A source that can't be read costs its own section one line, never
the feed.

  Top ad per angle          runs/winners/<brand>/bank.json: the top row of each angle by purchases, with its type
                            (what is on screen, from the brand's tags.json), its angle and concept (the brief's own
                            record, components/image-teardown/briefs.json; else the creator read; else the audit's
                            message tag, said on the row) and the customer words its writing run traced
  Desk calls                runs/media-buying/<brand>/decisions.jsonl, through the desk's own summary
                            (components/media-buying/machine/calls.py): how many calls, and every call that differed
                            from the desk's suggestion, with its numbers and the reason on record
  Sent back                 runs/meta-upload/<brand>/SENT-BACK.json (components/meta-upload/sent_back.py): each
                            send-back reason from the approval page, counted, with the step it points at
  Score per prompt version  the newest runs/winners/<brand>/score/<asof>/score.json: ads, spend, purchases, CPA and
                            ROAS by hook prompt version and by brief prompt version
"""
import argparse, importlib.util, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit import paths  # noqa: E402
import bank as B  # noqa: E402

DEFAULT_ROOT = paths.repo(__file__)
ANGLES, WORDS, WORD_CHARS, DISAGREEMENTS, REASONS = 12, 4, 280, 8, 10
SOURCE_LINE = re.compile(r"^\s*-\s*\*\*Source:\*\*\s*(.+?)\s*$")
LANGUAGE_ROW = re.compile(r"^\s*-\s*[^|]+\|\s*(.+?)\s*$")
HOOK_FILES = ("4b-hooks.md", "4ab-reading-hooks.md")
ANGLE_FROM = {"brief": "the brief's record", "creator": "the creator read", "tag": "the audit's message tag"}


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def money(x):
    return "—" if x is None else f"${x:,.0f}"


def num(x):
    return "—" if x is None else f"{x:,.0f}"


def ratio(x):
    return "—" if x is None else f"{x:.2f}"


def clean(s):
    return " ".join(str(s).split()) if s else None


# ---------- top ad per angle ----------

def register_entries(root):
    """{brief key: entry} for the brief register, under its map key and its own `key`."""
    reg = (_json(Path(root) / "components" / "image-teardown" / "briefs.json") or {}).get("briefs")
    out = {}
    for k, e in (reg or {}).items() if isinstance(reg, dict) else []:
        if isinstance(e, dict):
            out[k] = e
            if e.get("key"):
                out.setdefault(e["key"], e)
    return out


def headers(root, brand):
    """{brief number: [header rows]} from brands/<brand>/briefs/briefs.json, read only."""
    rows = (_json(Path(root) / "brands" / brand / "briefs" / "briefs.json") or {}).get("briefs") or []
    out = {}
    for h in rows if isinstance(rows, list) else []:
        m = re.search(r"(\d{3,4})$", str(h.get("brief") or "")) if isinstance(h, dict) else None
        if m:
            out.setdefault(int(m.group(1)), []).append(h)
    return out


def brief_facts(key, reg, heads):
    """{angle, concept} for a brief key: a person's header wins over the register entry, then the brief's own
    declares block; nothing invented."""
    entry = reg.get(key) or {}
    parts = str(key or "").split("_")
    m = re.search(r"(\d{3,4})$", parts[-1]) if parts and parts[-1] else None
    head = {}
    if m:
        same = [h for h in heads.get(int(m.group(1)), []) if len(parts) < 3 or h.get("product") in (parts[1], None)]
        head = same[0] if len(same) == 1 else {}
    dec = entry.get("declares") if isinstance(entry.get("declares"), dict) else {}
    return {"angle": head.get("angle") or entry.get("angle"),
            "concept": head.get("concept") or entry.get("concept") or dec.get("concept")}


def customer_words(root, run):
    """The customer lines a writing run traced its openings to (the `Source:` lines of its hook stage), or []."""
    if not run:
        return []
    found = []
    for name in HOOK_FILES:
        f = Path(root) / run / "stages" / name
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        lines, in_block = text.splitlines(), False
        for line in lines:
            if line.startswith("LANGUAGE USED:"):
                in_block = True
                continue
            m = SOURCE_LINE.match(line) or (LANGUAGE_ROW.match(line) if in_block else None)
            if in_block and not line.strip().startswith("-"):
                in_block = False
            if m:
                w = clean(m.group(1))
                w = w if len(w) <= WORD_CHARS else w[:WORD_CHARS].rstrip() + "…"
                if w not in found:
                    found.append(w)
    return found[:WORDS]


def _tag_for(tags, row):
    for name in [row.get("name")] + list(row.get("ad_names") or []):
        t = tags.get(name) if name else None
        if isinstance(t, dict):
            return t
    return {}


def _snapshot(row, window):
    """The row's snapshot in the feed's window when it has one, else its newest; None when it has no purchases."""
    snaps = [s for s in row.get("snapshots") or [] if s.get("purchases") is not None]
    if not snaps:
        return None
    inside = [s for s in snaps if window and s.get("kind") == "audit"
              and (s.get("since"), s.get("until")) == (window.get("since"), window.get("until"))]
    return inside[0] if inside else snaps[-1]


def angle_rows(root, brand, bank):
    """One entry per angle: its top bank row by purchases, winners ahead of candidates."""
    home = B.brand_dir(root, brand)
    tags = _json(home / "tags.json")
    tags = tags if isinstance(tags, dict) else {}
    reg = register_entries(root)
    heads = headers(root, brand)
    window = B.widest_audit_source(bank)
    groups = {}
    for row in bank.get("rows") or []:
        sn = _snapshot(row, window)
        if sn is None or not sn.get("purchases"):         # an ad with no purchase is not the top of anything
            continue
        entry = brief_facts(row.get("brief_key"), reg, heads) if row.get("brief_key") else {}
        tag, read = _tag_for(tags, row), row.get("tags") if isinstance(row.get("tags"), dict) else {}
        if entry.get("angle"):
            angle, src = entry["angle"], "brief"
        elif read.get("angle"):
            angle, src = read["angle"], "creator"
        elif tag.get("message"):
            angle, src = tag["message"], "tag"
        else:
            angle, src = None, None
        e = {"id": row["id"], "name": row.get("name"), "state": row.get("state") or "candidate",
             "angle": clean(angle), "angle_from": src, "concept": clean(entry.get("concept")),
             "type": clean(tag.get("on_screen") or read.get("format")), "format": clean(row.get("format")),
             "purchases": sn.get("purchases"), "spend": sn.get("spend"), "cpa": sn.get("cpa"), "roas": sn.get("roas"),
             "window": f"{sn.get('since')} to {sn.get('until')}", "words": customer_words(root, row.get("run")),
             "has_run": bool(row.get("run"))}
        groups.setdefault((e["angle"] or "").lower(), []).append(e)
    out = []
    for key, rows in groups.items():
        rows.sort(key=lambda e: (e["state"] != "winner", -(e["purchases"] or 0), e["id"]))
        out.append(rows[0])
    out.sort(key=lambda e: (e["angle"] is None, e["state"] != "winner", -(e["purchases"] or 0), e["id"]))
    return out


def angle_block(root, brand, bank):
    rows = angle_rows(root, brand, bank)
    out = ["## Top ad per angle", "",
           "The top bank row of each angle by purchases. Angle is the brief's own when the ad has a brief on record (its header in the brand's brief list, else the register), "
           "else the creator read's, else the audit's message tag; each row says which. State is the bank's: a winner "
           "clears the bar, a candidate has not or the bar is open.", ""]
    if not rows:
        return out + ["No bank row has a purchase on file.", ""]
    for i, e in enumerate(rows[:ANGLES], 1):
        out += [f"### A{i} · {e['angle'] or 'no angle on file'} · `{e['id']}` · {e['name']}", "",
                f"- Numbers: {num(e['purchases'])} purchases · spend {money(e['spend'])} · CPA {money(e['cpa'])}"
                f" · ROAS {ratio(e['roas'])} · window {e['window']}",
                f"- State: {e['state']}",
                f"- Type: {' · '.join(x for x in (e['type'], e['format']) if x) or 'not tagged'}",
                f"- Angle: {e['angle'] + ' (from ' + ANGLE_FROM[e['angle_from']] + ')' if e['angle'] else 'not on file'}",
                f"- Concept: {e['concept'] or 'not on file'}"]
        if e["words"]:
            out += ["- Customer words traced by its writing run:"] + [f"  - {w}" for w in e["words"]]
        else:
            out.append("- Customer words: not traced (" + ("its writing run lists none" if e["has_run"]
                                                           else "no writing run behind this ad") + ")")
        out.append("")
    if len(rows) > ANGLES:
        out += [f"{len(rows) - ANGLES} more angles are in the bank, below these by purchases.", ""]
    return out


# ---------- desk calls ----------

def _desk(root, brand):
    f = HERE.parent / "media-buying" / "machine" / "calls.py"      # the desk's own summary, beside this component
    spec = importlib.util.spec_from_file_location("media_buying_calls", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.for_brand(root, brand)


def _numbers(n):
    parts = []
    if n.get("spend") is not None:
        parts.append(f"spend {money(n['spend'])}")
    if n.get("purchases") is not None:
        parts.append(f"{num(n['purchases'])} purchases")
    if n.get("cpa") is not None:
        parts.append(f"CPA {money(n['cpa'])}")
    if n.get("break_even") is not None:
        parts.append(f"break-even {money(n['break_even'])}")
    return " · ".join(parts)


def desk_block(root, brand, summary=None):
    src = f"`runs/media-buying/{brand}/decisions.jsonl`"
    out = ["## Desk calls", ""]
    s = summary if summary is not None else _desk(root, brand)
    if not s.get("calls"):
        return out + [f"No call is on record yet ({src}).", ""]
    out += [f"Source: {src}. {s['calls']} calls on record: {s['agreed']} took the desk's suggestion, "
            f"{s['disagreed']} did not.", ""]
    for k, b in (s.get("by_suggestion") or {}).items():
        over = ", ".join(f"{c} ×{n}" for c, n in sorted(b["overruled_to"].items())) or "none"
        out.append(f"- Desk suggested {k}: {b['calls']} calls, {b['agreed']} agreed, changed to: {over}")
    out.append("")
    dis = s.get("disagreements") or []
    if dis:
        out += ["Where the call differed from the desk's suggestion, newest first:", ""]
        for d in dis[:DISAGREEMENTS]:
            nums = _numbers(d.get("numbers") or {})
            out.append(f"- {d.get('asof')} · {d.get('flag')} · {d.get('name')} · desk suggested {d.get('suggested')}, "
                       f"the call was {d.get('call')}" + (f" · {nums}" if nums else "")
                       + f" · reason on record: {d.get('why') or 'none'}")
        if len(dis) > DISAGREEMENTS:
            out.append(f"- and {len(dis) - DISAGREEMENTS} older")
        out.append("")
    return out


# ---------- sent back ----------

def sent_back_block(root, brand):
    rel = f"runs/meta-upload/{brand}/SENT-BACK.json"
    out = ["## Sent back from the approval page", ""]
    d = _json(Path(root) / rel)
    if not isinstance(d, dict):
        return out + [f"No send-back summary on file (`{rel}`).", ""]
    if not d.get("total"):
        return out + [f"No ad has been sent back (`{rel}`).", ""]
    out += [f"Source: `{rel}`. {d['total']} send-backs, {d.get('since')} to {d.get('until')}. Reasons and counts "
            "only; what was typed with each one stays with the approval cards.", ""]
    for r in (d.get("reasons") or [])[:REASONS]:
        at = ", ".join(f"{s.get('step')} {s.get('name')} ({s.get('tool')})" for s in r.get("steps") or [])
        out.append(f"- {r.get('label')}: {r.get('count')} · points at {at or 'no step'} · last {r.get('last')}"
                   + (f" · ads: {', '.join(r['units'])}" if r.get("units") else ""))
    out.append("")
    return out


# ---------- score per prompt version ----------

def newest_score(root, brand):
    d = B.brand_dir(root, brand) / "score"
    folders = sorted(p for p in d.iterdir() if (p / "score.json").is_file()) if d.is_dir() else []
    return (folders[-1] / "score.json") if folders else None


def _table(rows):
    out = ["| Version | Ads | Spend | Purchases | CPA | ROAS |", "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r.get('version')} | {r.get('ads')} | {money(r.get('spend'))} | {num(r.get('purchases'))} | "
                   f"{money(r.get('cpa'))} | {ratio(r.get('roas'))} |")
    return out


def score_block(root, brand):
    out = ["## Score per prompt version", ""]
    f = newest_score(root, brand)
    o = _json(f) if f else None
    if not isinstance(o, dict):
        return out + ["No score on file yet.", ""]
    c = o.get("counts") or {}
    out += [f"Source: `{B.rel(root, f)}` (ad data through {o.get('data_through')}). {c.get('matched', 0)} of "
            f"{c.get('ads', 0)} ads are joined to the prompt version that wrote them; an ad counts once under its "
            "hook prompt and once under its brief prompt.", ""]
    for title, key in (("Hook prompt", "by_hook_prompt"), ("Brief prompt", "by_brief_prompt")):
        rows = o.get(key) or []
        out += [f"{title}:", ""] + (_table(rows) if rows else ["No ad is joined to one yet."]) + [""]
    return out


# ---------- all of them ----------

SECTIONS = (("Top ad per angle", lambda root, brand, bank: angle_block(root, brand, bank)),
            ("Desk calls", lambda root, brand, bank: desk_block(root, brand)),
            ("Sent back from the approval page", lambda root, brand, bank: sent_back_block(root, brand)),
            ("Score per prompt version", lambda root, brand, bank: score_block(root, brand)))


def text(root, brand, bank=None):
    """The sections as one block of text, to follow the feed's own page. Never raises."""
    if bank is None:
        bank = _json(B.bank_path(root, brand))
    if not isinstance(bank, dict):
        bank = {"rows": [], "sources": []}
    out = ["", "# What the results taught", ""]
    for title, make in SECTIONS:
        try:
            out += make(root, brand, bank)
        except Exception as e:                   # noqa: BLE001 — one source never costs the feed
            out += [f"## {title}", "", f"Not read ({type(e).__name__}: {str(e)[:120]}).", ""]
    return "\n".join(out).rstrip() + "\n"


def write(root, brand):
    """runs/winners/<brand>/taught.md, rewritten only when it changed. -> the path."""
    out = B.brand_dir(root, brand) / "taught.md"
    text_ = text(root, brand).lstrip("\n")
    if not out.is_file() or out.read_text() != text_:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text_)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    a = ap.parse_args(argv)
    sys.stdout.write(text(Path(a.root), a.brand))
    return 0


if __name__ == "__main__":
    sys.exit(main())
