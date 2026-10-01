#!/usr/bin/env python3
"""Which library rows an approved concept brief is made in — asked of the
element library, never coined.

    elements_pick.py candidates [video,image,…]   print the rows the pick step is handed

A format comes ONLY from the library's format list for its medium, a style
from the style list, a framework from the framework list, an awareness level
and a sophistication stage from the doctrine lists
(`components/elements/library/`, read through `machine/elements.py`).

Three answers exist for any id, and nothing else:

    a real, defined row      picked, handed off
    a real row still saying  named as a candidate, flagged "named, not defined
    `[TO DEFINE`             yet", and NOT handed off
    an id not on its list    REFUSED, with the real ids named — never guessed,
                             never "closest match"

Nothing here edits the library.
"""
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
import paths as P                                             # noqa: E402
import slots as S                                             # noqa: E402

# medium → (its format list, its style list or None). The medium IS the
# library's asset name, so a new medium is a new row here and nothing else.
MEDIA = {
    "video": (("format", "video"), ("style", "video")),
    "image": (("format", "image"), ("style", "image")),
    "copy":  (("format", "copy"), None),
    "page":  (("format", "page"), None),
    "email": (("format", "email"), None),
}
FRAMEWORK = ("framework", "all")
AWARENESS = ("doctrine", "awareness")
SOPHISTICATION = ("doctrine", "sophistication")
NOT_DEFINED = "named, not defined yet"


def library():
    """The element library's own reader — components/elements/machine/elements.py."""
    machine = str(P.ELEMENTS / "machine")
    if machine not in sys.path:
        sys.path.append(machine)
    import elements as E
    return E


def key(pair):
    return f"{pair[0]}/{pair[1]}"


def lists_for(media):
    out = [FRAMEWORK, AWARENESS, SOPHISTICATION]
    for m in media:
        fmt, style = MEDIA[m]
        out.append(fmt)
        if style:
            out.append(style)
    return out


def missing_lists(media=tuple(MEDIA)):
    E = library()
    out = []
    for pair in lists_for(media):
        try:
            if not E.rows(*pair):
                out.append(f"the element library's {key(pair)} list is empty")
        except E.Unknown as e:
            out.append(str(e.args[0]))
    return out


def undefined(row):
    """A row Damon has named that nobody has defined yet."""
    return "[TO DEFINE" in str(row.get("what") or "")


def ids(pair):
    return [r["id"] for r in library().rows(*pair)]


def check_media(media):
    bad = [m for m in media if m not in MEDIA]
    if bad:
        raise ValueError(f"no medium called {', '.join(bad)} — the ones there are: {', '.join(MEDIA)}")
    return list(media)


def lookup(pair, rid):
    """(row, problem). An id off its list is refused with the real ids named."""
    E = library()
    bad = E.check({pair: rid})
    if bad:
        return None, f"{key(pair)}: REFUSED — {bad[0]}"
    return E.get(pair[0], pair[1], rid), None


def _table(pair):
    out = [f"### {key(pair)}\n", "| id | name | what it is |", "|---|---|---|"]
    for r in library().rows(*pair):
        what = re.sub(r"\s+", " ", str(r.get("what") or "")).replace("|", "/")
        if undefined(r):
            what = f"NOT DEFINED YET — may be named as a candidate only. {what}"
        out.append(f"| `{r['id']}` | {r.get('name') or ''} | {what} |")
    return "\n".join(out) + "\n"


def candidates(media):
    """The candidate rows the pick step is handed: id · name · what."""
    out = []
    for m in media:
        fmt, style = MEDIA[m]
        out.append(f"## medium: {m}\n")
        out.append(_table(fmt))
        out.append(_table(style) if style else f"(the library holds no style list for {m} — `style` is null)\n")
    out.append("## every medium\n")
    out.append(_table(FRAMEWORK))
    return "\n".join(out)


def doctrine_ids_line(pair):
    return ", ".join(f"`{i}`" for i in ids(pair))


# ------------------------------------------------------------------ reading the picks

def parse(text, media):
    return S.block(text, "FORMATS", aliases=("FORMAT PICKS", "PICKS"), keys=tuple(media))


def from_flag(flag):
    """`video:expert-consult,image:stickynote+candid-ugc` → the same shape the
    pick step answers in. The owner's own picks skip the model and are checked
    exactly as hard."""
    out = {}
    for part in [p.strip() for p in (flag or "").split(",") if p.strip()]:
        medium, _, rest = part.partition(":")
        fmt, _, style = rest.partition("+")
        if not (medium and fmt):
            raise ValueError(f"`{part}` is not `<medium>:<format id>` or `<medium>:<format id>+<style id>`")
        out[medium.strip()] = {"format": fmt.strip(), "style": style.strip() or None, "candidates": [],
                               "why": "picked by hand at approval"}
    return out


def validate(answer, media, frameworks_from_brief=()):
    """(record, problems). `problems` hold the run; a not-defined row never
    does — it is flagged and its medium is simply not handed off."""
    picks, flagged, refused, problems = {}, [], [], []
    for m in media:
        a = answer.get(m)
        if a in (None, "", "none") or (isinstance(a, dict) and a.get("format") in (None, "", "none")):
            picks[m] = {"format": None, "hand_off": False,
                        "why": (a or {}).get("why") if isinstance(a, dict) else None,
                        "held_back": "the pick step named no format for this medium"}
            continue
        if isinstance(a, str):
            a = {"format": a}
        fmt_pair, style_pair = MEDIA[m]
        rec = {"format": None, "style": None, "framework": None, "candidates": [], "why": a.get("why"),
               "hand_off": True, "held_back": None, "notes": []}

        rid = str(a.get("format")).strip().strip("`")
        row, bad = lookup(fmt_pair, rid)
        if bad:
            refused.append({"list": key(fmt_pair), "id": rid}); problems.append(bad)
            rec["hand_off"] = False
        else:
            rec["format"] = {"id": row["id"], "name": row.get("name"), "what": row.get("what"),
                             "status": row.get("status"), "source": row.get("source")}
            if undefined(row):
                rec["hand_off"] = False
                rec["held_back"] = f"format `{rid}` is {NOT_DEFINED}"
                flagged.append({"list": key(fmt_pair), "id": rid, "flag": NOT_DEFINED})

        sid = a.get("style")
        if sid not in (None, "", "none"):
            sid = str(sid).strip().strip("`")
            if not style_pair:
                rec["notes"].append(f"a style was named (`{sid}`) but the library holds no style list for {m}; it is not carried")
            else:
                srow, bad = lookup(style_pair, sid)
                if bad:
                    refused.append({"list": key(style_pair), "id": sid}); problems.append(bad)
                elif undefined(srow):
                    flagged.append({"list": key(style_pair), "id": sid, "flag": NOT_DEFINED})
                    rec["notes"].append(f"style `{sid}` is {NOT_DEFINED} — the hand-off carries no style")
                else:
                    rec["style"] = {"id": srow["id"], "name": srow.get("name"), "what": srow.get("what")}

        fid = a.get("framework") or (frameworks_from_brief[0] if frameworks_from_brief else None)
        if fid:
            fid = str(fid).strip().strip("`")
            frow, bad = lookup(FRAMEWORK, fid)
            if bad:
                refused.append({"list": key(FRAMEWORK), "id": fid}); problems.append(bad)
            else:
                rec["framework"] = {"id": frow["id"], "name": frow.get("name"), "what": frow.get("what")}

        for cid in a.get("candidates") or []:
            cid = str(cid).strip().strip("`")
            crow, bad = lookup(fmt_pair, cid)
            if bad:
                refused.append({"list": key(fmt_pair), "id": cid}); problems.append(bad)
                continue
            flag = NOT_DEFINED if undefined(crow) else None
            rec["candidates"].append({"id": cid, "flag": flag})
            if flag:
                flagged.append({"list": key(fmt_pair), "id": cid, "flag": NOT_DEFINED})
        picks[m] = rec

    extra = sorted(set(answer) - set(media))
    if extra:
        problems.append("the answer picks for media nobody asked for: " + ", ".join(extra))
    seen, uniq = set(), []
    for f in flagged:
        if (f["list"], f["id"]) not in seen:
            seen.add((f["list"], f["id"])); uniq.append(f)
    return {"picks": picks, "flagged": uniq, "refused": refused,
            "library": "components/elements/library"}, problems


def read(answer_text, media, frameworks_from_brief=()):
    try:
        record, problems = validate(parse(answer_text, media), media, frameworks_from_brief)
    except ValueError as e:
        record, problems = {"picks": {}, "flagged": [], "refused": [], "library": "components/elements/library"}, [str(e)]
    record["problems"] = problems
    return record, problems


if __name__ == "__main__":
    if sys.argv[1:2] == ["candidates"]:
        print(candidates(check_media((sys.argv[2] if len(sys.argv) > 2 else ",".join(MEDIA)).split(","))))
    else:
        print(__doc__)
