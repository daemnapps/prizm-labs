#!/usr/bin/python3
"""Sort every unlabelled teardown into our locked names (script format, production format, look) from what the
teardown already wrote (triage + the spec's FORMAT and skeleton). Writes runs/creative-controls/format-labels/:
labels.json, and every prompt and reply. Changes no teardown record. Read by the Creative Options board.

    /usr/bin/python3 components/creative-controls/label_teardown_formats.py [--missing | --fix]
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

WS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WS / "components/run-kit"))
from run_kit import claude_door  # noqa: E402

OUT = WS / "runs/creative-controls/format-labels"
FIX = "--fix" in sys.argv          # second pass: teardowns whose label is not a script format (a production or hook name)
MISS = "--missing" in sys.argv     # rerun the ids a reply skipped
PRE = "fix-batch" if FIX else ("miss-batch" if MISS else "batch")
SKIPPED = set(json.loads((OUT / "labels.json").read_text()).get("missing") or []) if MISS else set()
(OUT / "calls").mkdir(parents=True, exist_ok=True)
N = json.loads((WS / "components/video-production/formats/names.json").read_text())
LISTS = {k: N[k]["names"] for k in ("script_format", "production_format", "style")}


def item(r):
    st = r / "stages"
    tri = (st / "0-triage.md").read_text()[:700] if (st / "0-triage.md").is_file() else ""
    spec = (st / "2-spec.md").read_text() if (st / "2-spec.md").is_file() else ""
    if not spec and (st / "1-teardown.md").is_file():
        spec = (st / "1-teardown.md").read_text()
    phases = re.findall(r"^\|\s*([^|\n]{3,60}?)\s*\|\s*([^|\n]{3,90}?)\s*\|", spec, re.M)[2:12]
    fmt = re.search(r"FORMAT\*?\*?\s*\n+(.+)", spec)
    return {"id": r.name, "triage": tri.strip(), "format_said": (fmt.group(1)[:400] if fmt else spec[:500]).strip(),
            "phases": "; ".join("%s (%s)" % p for p in phases)}


def prompt(batch):
    lists = "\n".join("%s: %s" % (k, "; ".join("`%s` %s%s" % (x["id"], x["name"], (" (" + x["what"] + ")") if x.get("what") else "")
                                             for x in v)) for k, v in LISTS.items())
    return ("Sort each video teardown below into our locked names. Use ONLY ids from these lists, or `none` when "
            "nothing fits (never invent a name):\n\n" + lists +
            "\n\nscript_format = what the video SAYS and how its argument runs; production_format = how it is MADE "
            "(people on screen, voice, song); style = what it LOOKS like (real phone footage is phone-ugc).\n\n"
            "Reply with ONE json block only: {\"<id>\": {\"script_format\": \"..\", \"production_format\": \"..\", "
            "\"style\": \"..\", \"why\": \"<8 words>\"}, ...} with every id below.\n\n"
            + "\n\n".join("### %s\n%s\nFORMAT AS WRITTEN: %s\nPHASES: %s" % (i["id"], i["triage"], i["format_said"], i["phases"])
                          for i in batch))


def call(n_batch):
    n, batch = n_batch
    f = OUT / "calls" / ("%s-%03d.md" % (PRE, n))
    if f.is_file() and f.read_text().strip():
        return f.read_text()
    p = prompt(batch)
    (OUT / "calls" / ("%s-%03d.prompt.md" % (PRE, n))).write_text(p)
    r = claude_door.run(["--model", "haiku", "--output-format", "text", "--allowed-tools", ""], p, timeout=600)
    f.write_text(r.stdout or "")
    return r.stdout or ""


def main():
    runs = []
    for f in sorted((WS / "runs/video-teardown/_work").glob("*/run.json")):
        try:
            d = json.loads(f.read_text())
        except ValueError:
            continue
        cur = (d.get("layers") or {}).get("format") or d.get("format_id")
        sids = {x["id"] for x in LISTS["script_format"]}
        if d.get("brand") in ("brand_a", "brand_b") and ((MISS and f.parent.name in SKIPPED) or
                                                        (not MISS and ((FIX and cur and cur not in sids) or (not FIX and not cur)))):
            if (f.parent / "stages/0-triage.md").is_file() or (f.parent / "stages/1-teardown.md").is_file():
                runs.append((f.parent, d["brand"]))
    items = [item(r) for r, _ in runs]
    brand = {r.name: b for r, b in runs}
    batches = [items[i:i + 20] for i in range(0, len(items), 20)]
    with ThreadPoolExecutor(4) as ex:
        replies = list(ex.map(call, enumerate(batches)))
    ok = {k: set(x["id"] for x in v) for k, v in LISTS.items()}
    labels, bad = {}, []
    for rep in replies:
        m = re.search(r"\{.*\}", rep, re.S)
        try:
            got = json.loads(m.group(0)) if m else {}
        except ValueError:
            got = {}
        for rid, v in got.items():
            if rid not in brand:
                continue
            row = {k: (v.get(k) if v.get(k) in ok[k] else None) for k in LISTS}
            row.update(brand=brand[rid], why=str(v.get("why", ""))[:80], by="haiku, from the teardown's own spec")
            labels[rid] = row
    missing = [i["id"] for i in items if i["id"] not in labels]
    lf = OUT / "labels.json"
    if (FIX or MISS) and lf.is_file():
        old = json.loads(lf.read_text())
        old["labels"].update(labels)
        if MISS:
            old["missing"] = [i for i in old.get("missing") or [] if i not in labels]
        old["count"] = len(old["labels"])
        if FIX:
            old["fixed_from_other_names"] = sorted(labels)
        lf.write_text(json.dumps(old, indent=1))
        print("%s: %d labelled" % ("second pass" if FIX else "skipped ids", len(labels)))
        return
    (OUT / "labels.json").write_text(json.dumps({
        "what": "Script format, production format and look for every teardown that had none, read from its own triage "
                "and spec by a reading model, using only the locked names list (none = nothing fits). Changes no "
                "teardown record. state: machine-read, not checked by a person.",
        "made": "2026-11-21", "count": len(labels), "missing": missing, "labels": labels}, indent=1))
    print("labelled %d of %d; missing %d" % (len(labels), len(items), len(missing)))


def briefs_main():
    """--briefs: every video brief in each brand's register, sorted into the same names from its own fields (title,
    concept, angle, how it was made, its moves, what was heard). Writes brief-labels.json beside labels.json."""
    items, brand = [], {}
    for b in ("brand_a", "brand_b"):
        f = WS / "brands" / b / "briefs" / "briefs.json"
        for r in json.loads(f.read_text()).get("briefs") or [] if f.is_file() else []:
            if r.get("media") != "video" or not r.get("brief"):
                continue
            brand[r["brief"]] = b
            keep = {k: r.get(k) for k in ("title", "concept", "angle", "angle_why", "format", "talent", "source", "moves",
                                          "promo", "promo_why", "angle_read") if r.get(k)}
            items.append({"id": r["brief"], "triage": json.dumps(keep, ensure_ascii=False)[:1200], "format_said":
                          str(r.get("format") or ""), "phases": ""})
    global PRE
    PRE = "brief-batch"
    batches = [items[i:i + 20] for i in range(0, len(items), 20)]
    with ThreadPoolExecutor(4) as ex:
        replies = list(ex.map(call, enumerate(batches)))
    ok = {k: set(x["id"] for x in v) for k, v in LISTS.items()}
    labels = {}
    for rep in replies:
        m = re.search(r"\{.*\}", rep, re.S)
        try:
            got = json.loads(m.group(0)) if m else {}
        except ValueError:
            got = {}
        for rid, v in got.items():
            if rid in brand:
                row = {k: (v.get(k) if v.get(k) in ok[k] else None) for k in LISTS}
                row.update(brand=brand[rid], why=str(v.get("why", ""))[:80], by="haiku, from the brief register's own fields")
                labels[rid] = row
    (OUT / "brief-labels.json").write_text(json.dumps({
        "what": "Script format, production format and look for every video brief in the brand registers, read from the "
                "register's own fields by a reading model, using only the locked names (none = nothing fits). Changes no "
                "brief. state: machine-read, not checked by a person.", "made": "2026-11-21", "count": len(labels),
        "missing": [i["id"] for i in items if i["id"] not in labels], "labels": labels}, indent=1))
    print("briefs: labelled %d of %d" % (len(labels), len(items)))


if __name__ == "__main__":
    briefs_main() if "--briefs" in sys.argv else main()
