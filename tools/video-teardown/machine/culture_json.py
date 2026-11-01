#!/usr/bin/env python3
"""The culture read, as data — `stages/1k-culture.json` beside every `stages/1k-culture.md`.

    python3 culture_json.py <run-folder>     parse that run's culture read, write the JSON, print it
    python3 culture_json.py --backfill       every run with a culture read; a summary at the end

the owner, 2026-10-06 ("a bottoms up approach … based on the real language only"):
the culture map for each avatar is now built from the data, and one of its
sources is every culture read the machine has already made. Those reads are
written for people (stage 1k prints Markdown blocks R1, R2 …); this turns each
one into a record the culture-map generator can count and cite — run slug plus
R-id is the receipt.

Shape (the shared spec, BOTTOMUP-SPEC.md — the generator reads exactly this):

    {"schema": 1, "run", "brand", "avatar", "sub", "post_url",
     "culture_load": "HEAVY|LIGHT|NONE", "post_talk": {"count", "refrain"},
     "refs": [{"id": "R1", "name", "kind", "use": [...], "who", "borrowed",
               "receipts": [...], "confidence", "recognizes", "why_lands",
               "load_bearing", "breaks_it"}],
     "funny_or_straight": "funny|straight|mixed|null", "problem_slot",
     "keep": [...], "never": [...], "name_it_as": [...],
     "parsed_from": "1k-culture.md", "parsed_at": "<iso>"}

Who the read is for comes from the run's run.json (`declared_audience`, then
`audience._avatar` / `_sub_avatar`, then the 1b stage's AVATAR: / SUB-AVATAR:
lines); the post's link from run.json, the post's own files, or post-talk.json.

Every version of the 1k prompt parses: v1 has no USE / FUNNY OR STRAIGHT /
PROBLEM SLOT (those come out [] / null), v2 adds PROBLEM SLOT, v3 adds USE and
FUNNY OR STRAIGHT. Headings it doesn't know are skipped, a missing field is
null or [], and in a backfill one bad file is reported, never fatal.

The run writes this automatically after every new stage 1k (run.py); a parse
failure there is printed and the run carries on.
"""

import datetime as _dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
MD_NAME = "1k-culture.md"
JSON_NAME = "1k-culture.json"
SCHEMA = 1

USE_TAGS = ("laugh", "trust", "belonging", "nostalgia", "aspiration",
            "authority", "relief", "rebellion")

# label as printed (normalised: upper case, no bold) → the JSON field
REF_FIELDS = {
    "KIND": "kind",
    "USE": "use",
    "WHO, PRECISELY": "who",
    "WHO PRECISELY": "who",
    "WHO": "who",
    "WHAT IS BORROWED": "borrowed",
    "RECEIPTS": "receipts",
    "CONFIDENCE": "confidence",
    "WHO RECOGNIZES IT": "recognizes",
    "WHO RECOGNISES IT": "recognizes",
    "WHY IT LANDS": "why_lands",
    "LOAD-BEARING": "load_bearing",
    "LOAD BEARING": "load_bearing",
    "BREAKS IT": "breaks_it",
}
LATER_FIELDS = {
    "KEEP": "keep",
    "NEVER": "never",
    "NAME IT AS": "name_it_as",
    "FUNNY OR STRAIGHT": "funny_or_straight",
    "PROBLEM SLOT": "problem_slot",
}

# "- **LOAD-BEARING (keep these …):** text"  →  ("LOAD-BEARING", "text")
LABEL = re.compile(r"^\s*(?:[-*•]\s*)*\**\s*([A-Za-z][A-Za-z ,'/-]*?)\s*(?:\([^)]*\))?\s*\**\s*:\**\s*(.*)$")
HEADING = re.compile(r"^\s*#{2,4}\s*(.+?)\s*#*\s*$")
REF_HEAD = re.compile(r"^R(\d+)\s*(?:[—–-]+|:|\.)?\s*(.*)$")
CONFIDENCE_WORDS = ("CONFIRMED", "LIKELY", "POSSIBLE", "UNIDENTIFIED", "GUESS")


def _clean(s):
    s = (s or "").strip()
    s = re.sub(r"^\*+|\*+$", "", s).strip()
    return s


def _label(line):
    """(LABEL, rest) when the line opens with a known-looking label, else None."""
    m = LABEL.match(line)
    if not m:
        return None
    lab = re.sub(r"\s+", " ", m.group(1)).strip()
    if lab != lab.upper():                  # labels are printed in capitals; "The humor: …" is prose
        return None
    return lab, _clean(m.group(2))


def _bullet(line):
    m = re.match(r"^\s*[-*•]\s+(.*)$", line)
    return _clean(m.group(1)) if m else None


def parse_use(text):
    """'laugh · nostalgia — why' → ['laugh', 'nostalgia']; unknown words kept as written."""
    if not text:
        return []
    head = re.split(r"\s+[—–]\s+|\s+-\s+", text, maxsplit=1)[0]
    head = re.sub(r"\([^)]*\)", "", head)
    found = [t for t in re.findall(r"[a-z]+", head.lower()) if t in USE_TAGS]
    if found:
        return list(dict.fromkeys(found))
    parts = [p.strip().lower() for p in re.split(r"[·,/]|\band\b", head) if p.strip()]
    return [p for p in parts if p and len(p) < 30]


def _funny(text):
    if not text:
        return None
    w = re.findall(r"[a-z]+", text.lower())
    for word in w[:3]:
        if word in ("funny", "straight", "mixed"):
            return word
    return None


def _confidence(text):
    if not text:
        return None
    m = re.match(r"\s*\**([A-Za-z]+)", text)
    if not m:
        return None
    w = m.group(1).upper()
    return w if w.isalpha() else None


def _empty_ref(n, name):
    return {"id": f"R{n}", "name": name or None, "kind": None, "use": [], "who": None,
            "borrowed": None, "receipts": [], "confidence": None, "recognizes": None,
            "why_lands": None, "load_bearing": None, "breaks_it": None}


def parse(text):
    """The read's own fields (no run context). Never raises on odd text."""
    out = {"culture_load": None, "post_talk": {"count": None, "refrain": None}, "refs": [],
           "funny_or_straight": None, "problem_slot": None,
           "keep": [], "never": [], "name_it_as": []}
    section = None          # None (top) | "ref" | "later" | "skip"
    ref = None
    field = None            # the field continuation lines append to
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if re.match(r"^\s*-{3,}\s*$", line):
            section, ref, field = "skip", None, None
            continue
        h = HEADING.match(line)
        if h:
            title = _clean(h.group(1))
            field = None
            m = REF_HEAD.match(title)
            if m:
                ref = _empty_ref(int(m.group(1)), _clean(m.group(2)))
                out["refs"].append(ref)
                section = "ref"
            elif re.match(r"FOR EVERY LATER STAGE", title, re.I):
                section, ref = "later", None
            else:
                section, ref = "skip", None
            continue

        lab = _label(line)

        if section is None:
            if lab and lab[0] == "CULTURE LOAD":
                w = re.match(r"([A-Za-z]+)", lab[1])
                out["culture_load"] = w.group(1).upper() if w else None
                if out["culture_load"] not in ("HEAVY", "LIGHT", "NONE"):
                    out["culture_load"] = out["culture_load"] or None
            elif lab and lab[0] == "POST TALK":
                v = lab[1]
                if re.match(r"none\b", v, re.I):
                    out["post_talk"] = {"count": "none",
                                        "refrain": _clean(re.sub(r"^none\s*[—–-]*\s*", "", v, flags=re.I)) or None}
                else:
                    parts = re.split(r"\s+·\s+", v, maxsplit=1)
                    out["post_talk"] = {"count": parts[0].strip() or None,
                                        "refrain": (parts[1].strip() if len(parts) > 1 else None) or None}
            continue

        if section == "ref" and ref is not None:
            if lab and lab[0] in REF_FIELDS:
                field = REF_FIELDS[lab[0]]
                val = lab[1]
                if field == "receipts":
                    if val:
                        ref["receipts"].append(val)
                elif field == "use":
                    ref["use"] = parse_use(val)
                    ref["_use_raw"] = val
                elif field == "confidence":
                    ref["confidence"] = _confidence(val)
                else:
                    ref[field] = val or None
                continue
            b = _bullet(line)
            indented = raw[:1] in (" ", "\t")
            if field == "receipts" and b is not None:
                ref["receipts"].append(b)
                continue
            if lab and not indented:          # an unknown label: ignore it and what follows
                field = None
                continue
            if field and field not in ("receipts", "use", "confidence"):
                ref[field] = ((ref[field] or "") + " " + _clean(b if b is not None else line)).strip()
            elif field == "receipts" and line.strip():
                if ref["receipts"]:
                    ref["receipts"][-1] += " " + line.strip()
            continue

        if section == "later":
            if lab and lab[0] in LATER_FIELDS:
                field = LATER_FIELDS[lab[0]]
                val = lab[1]
                if field in ("keep", "never", "name_it_as"):
                    if val and not (field == "keep" and re.match(r"nothing cultural\b", val, re.I)):
                        out[field].append(val)
                elif field == "funny_or_straight":
                    out["funny_or_straight"] = _funny(val)
                else:
                    out["problem_slot"] = val or None
                continue
            if lab and not raw[:1] in (" ", "\t"):
                field = None
                continue
            # a continuation line (wrapped text, or a sub-bullet under KEEP:)
            b = _bullet(line)
            piece = b if b is not None else line.strip()
            if field in ("keep", "never", "name_it_as"):
                if b is not None or not out[field]:
                    out[field].append(piece)
                else:
                    out[field][-1] += " " + piece
            elif field == "problem_slot":
                out["problem_slot"] = ((out["problem_slot"] or "") + " " + piece).strip()
            continue
    for r in out["refs"]:
        r.pop("_use_raw", None)
    return out


# ── who the read is for ──────────────────────────────────────────────────────

def _load_json(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return {}


def _from_1b(run):
    f = Path(run) / "stages" / "1b-audience.md"
    if not f.is_file():
        return {}
    text = f.read_text(errors="replace")
    try:
        import chain as _C
        return _C.audience_from(text)
    except Exception:
        out = {}
        for k in ("AVATAR", "SUB-AVATAR"):
            m = re.search(rf"^{k}:[ \t]*(.+)$", text, re.M | re.I)
            if m:
                v = m.group(1).strip().strip("`")
                out["_" + k.lower().replace("-", "_")] = (
                    None if v.lower().startswith(("none", "unknown")) else v.split()[0])
        return out


def _ok(v):
    v = str(v or "").strip().strip("`")
    return None if not v or v.lower() in ("none", "null", "unknown", "n/a") else v


def audience(run, st):
    """(avatar, sub) for the run: declared, then the run's audience, then stage 1b."""
    da = st.get("declared_audience")
    da = da if isinstance(da, dict) else ({"avatar": da} if isinstance(da, str) else {})
    au = st.get("audience") if isinstance(st.get("audience"), dict) else {}
    avatar = _ok(da.get("avatar")) or _ok(au.get("_avatar"))
    b = None
    if not avatar:
        b = _from_1b(run)
        avatar = _ok(b.get("_avatar"))
    sub = _ok(da.get("sub"))
    if not sub and _ok(au.get("_avatar")) in (None, avatar):
        sub = _ok(au.get("_sub_avatar"))
    if not sub:
        b = b if b is not None else _from_1b(run)
        if _ok(b.get("_avatar")) in (None, avatar):
            sub = _ok(b.get("_sub_avatar"))
    return avatar, sub


def _post_url(run, st):
    try:
        import culture as _cu
        u = _cu.post_url(run, st)
        if u:
            return u
    except Exception:
        pass
    u = str(_load_json(Path(run) / "post-talk.json").get("url") or "").strip()
    return u if u.startswith("http") else None


def _brand(run, st):
    b = _ok(st.get("brand"))
    if b:
        return b
    parts = Path(run).resolve().parts
    for i, p in enumerate(parts[:-2]):
        if p == "runs" and parts[i + 1] in ("video-teardown", "video-writing"):
            # the working folder (runs/video-teardown/_work/) is not a brand
            return None if parts[i + 2] == "_work" else parts[i + 2]
    return None


def build(run, md=None):
    """The full record for one run folder."""
    run = Path(run)
    md = Path(md) if md else run / "stages" / MD_NAME
    st = _load_json(run / "run.json")
    st = st if isinstance(st, dict) else {}
    avatar, sub = audience(run, st)
    rec = {"schema": SCHEMA, "run": st.get("slug") or run.name, "brand": _brand(run, st),
           "avatar": avatar, "sub": sub, "post_url": _post_url(run, st)}
    rec.update(parse(md.read_text(errors="replace")))
    rec["parsed_from"] = md.name
    rec["parsed_at"] = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    return rec


def write(run, md=None):
    """Parse and write stages/1k-culture.json beside the read. Returns the record."""
    md = Path(md) if md else Path(run) / "stages" / MD_NAME
    rec = build(run, md)
    (md.parent / JSON_NAME).write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return rec


def all_reads(root=WORKSPACE):
    root = Path(root)
    # the first also reaches the working folder, runs/video-teardown/_work/
    pats = ["runs/video-teardown/*/*/stages/" + MD_NAME,
            "runs/video-writing/*/*/stages/" + MD_NAME]
    seen = []
    for p in pats:
        seen += sorted(root.glob(p))
    return seen


def backfill(root=WORKSPACE, say=print):
    done, failed = [], []
    for md in all_reads(root):
        run = md.parent.parent
        try:
            done.append((run, write(run, md)))
        except Exception as e:
            failed.append((run, f"{type(e).__name__}: {e}"))
            say(f"  FAILED  {run}: {type(e).__name__}: {e}")
    say(f"culture reads: {len(done)} parsed, {len(failed)} failed")
    return done, failed


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--backfill":
        _, failed = backfill()
        return 1 if failed else 0
    run = Path(argv[0])
    if run.name == MD_NAME:
        run = run.parent.parent
    if not (run / "stages" / MD_NAME).is_file():
        print(f"no culture read in {run} (stages/{MD_NAME})", file=sys.stderr)
        return 1
    print(json.dumps(write(run), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    sys.exit(main(sys.argv[1:]))
