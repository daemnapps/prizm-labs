#!/usr/bin/env python3
"""Two brands, side by side — what they share, where they drifted.

    python3 compare.py                          # every brand the workspace has
    python3 compare.py --brands brand-b brand-a

the owner, 2026-09-14: *"Some of the way that the blocks are set up looks
inconsistent between both brands as well. I need you to run a check."*

Everything the chain reads from a brand has a shape, and the shape is supposed
to be the same everywhere — that is what brand-agnostic means in practice. When
two brands drift apart, the chain does not fail; it quietly does something
different for one of them, and the month looks fine. Both brands lost their
whole offer bank for a day that way, because one file was reshaped and the
reader was not.

So this compares the SHAPES, not the contents. A brand having different offers
than another is the point. A brand keeping its offers under a different key is
a bug waiting for someone to notice.
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

from paths import WORKSPACE, COMPONENTS, brand_root, rel
sys.path.append(str(COMPONENTS / "brandpath"))      # appended, never ahead of this tool
import brandpath as BP                                # noqa: E402

# Every file the chain reads, and the shape it expects.
FILES = [
    ("email-sms/email-types.json", "the kinds of send this brand knows"),
    ("email-sms/audience-matrix.json", "who it can target"),
    ("products/offer-bank.md", "what it may sell"),
    ("calendar/moments.json", "its claim on the year"),
    ("email-sms/affiliates.json", "partners it features"),
    ("email-sms/classified.json", "its own sends, typed — the formats"),
    ("email-sms/format-sources.json", "where it borrows formats when it has none"),
    ("email-sms/ledger.json", "every send, with its campaign"),
    ("email-sms/performance.json", "what each send earned"),
    ("email-sms/learnings.md", "the evidence, as findings"),
]


def j(brand, rel_path, default=None):
    try:
        return json.loads(BP.resolve_rel(brand, rel_path, root=brand_root(brand).parent).read_text())
    except (OSError, ValueError):
        return default


def shape(v, depth=0):
    """A value's shape, not its content: {keys} for a dict, [shape] for a list."""
    if isinstance(v, dict):
        if depth > 1:
            return "{…}"
        return "{" + ", ".join(sorted(v)[:12]) + ("…" if len(v) > 12 else "") + "}"
    if isinstance(v, list):
        return f"[{len(v)} × {shape(v[0], depth + 1) if v else '—'}]"
    return type(v).__name__


def row(label, values, note=""):
    same = len(set(map(str, values))) == 1
    return {"label": label, "values": list(values), "same": same, "note": note}


def compare(brands):
    out = []

    # --- the files themselves -------------------------------------------
    for path, what in FILES:
        have = [BP.resolve_rel(b, path, root=brand_root(b).parent).exists() for b in brands]
        out.append(row(path, ["yes" if h else "MISSING" for h in have], what))

    # --- the type catalogue ---------------------------------------------
    cats = {b: {t["key"]: t for t in (j(b, "email-sms/email-types.json", {}) or {}).get("types", [])}
            for b in brands}
    out.append(row("types · count", [len(cats[b]) for b in brands]))
    allk = set().union(*cats.values()) if cats else set()
    for b in brands:
        only = sorted(allk - set(cats[b]))
        if only:
            out.append(row(f"types · {b} is MISSING", [", ".join(only[:8])],
                           "a type another brand has and this one does not"))
    for field in ("role", "well"):
        for b in brands:
            c = collections.Counter(t.get(field) for t in cats[b].values())
            out.append(row(f"types · {field}", [json.dumps(dict(sorted(c.items())))
                                                for bb in brands
                                                for c in [collections.Counter(
                                                    t.get(field) for t in cats[bb].values())]][:len(brands)]))
            break
    # a type shared by both should agree about what it IS
    drift = []
    for k in sorted(set.intersection(*(set(c) for c in cats.values())) if cats else []):
        for field in ("role", "well"):
            vals = {cats[b][k].get(field) for b in brands}
            if len(vals) > 1:
                drift.append(f"{k}.{field}: " + " vs ".join(
                    f"{b}={cats[b][k].get(field)}" for b in brands))
        needs = {b: tuple(sorted(cats[b][k].get("needs") or [])) for b in brands}
        if len(set(needs.values())) > 1:
            drift.append(f"{k}.needs: " + " vs ".join(
                f"{b}={'/'.join(needs[b]) or 'none'}" for b in brands))
    out.append(row("types · shared types that DISAGREE",
                   [len(drift)] * len(brands),
                   "; ".join(drift[:4]) if drift else "none — a shared type means "
                   "the same thing in both"))

    # --- the offer bank --------------------------------------------------
    import brandrecord as C
    for b in brands:
        pass
    banks, shapes = {}, {}
    for b in brands:
        text = ""
        f = BP.brand_path(b, "products", "offer-bank.md", root=brand_root(b).parent)
        if f.is_file():
            text = f.read_text()
        roster = [a["key"] for a in (C.L.avatars(b, WORKSPACE) if C.L else [])]
        offers = [l.split("`")[1] for l in C.render_offers(brand_root(b), roster).splitlines()
                  if l.startswith("- OFFER `")] if text else []
        banks[b] = offers
        shapes[b] = ("per-avatar" if C.bank_is_per_avatar(text, roster) else "flat")
    out.append(row("offer bank · shape", [shapes[b] for b in brands],
                   "how the file is laid out — BOTH must be readable by the same rule"))
    out.append(row("offer bank · usable offers", [len(banks[b]) for b in brands]))

    # --- products -----------------------------------------------------------
    pshape, pn = [], []
    for b in brands:
        found = C.product_files(brand_root(b))
        kinds = {"folder" if f.name == "product.md" else "flat" for _, f in found}
        pshape.append(" + ".join(sorted(kinds)) or "none")
        pn.append(len(found))
    out.append(row("products · shape", pshape,
                   "flat = products/<slug>.md, folder = products/<slug>/product.md — "
                   "the reader takes both; `none` means every send reads as productless"))
    out.append(row("products · count", pn))

    # --- affiliates -------------------------------------------------------
    for b in brands:
        pass
    aff_keys, aff_n = [], []
    for b in brands:
        d = j(b, "email-sms/affiliates.json", {}) or {}
        lists = {k: v for k, v in d.items() if isinstance(v, list)}
        aff_keys.append(", ".join(lists) or "—")
        aff_n.append(len(d.get("affiliates") or []))
    out.append(row("affiliates · the key holding the roster", aff_keys,
                   "the reader knows `affiliates`; any other name is invisible to it"))
    out.append(row("affiliates · partners", aff_n))

    # --- segments and avatars --------------------------------------------
    segs = [len((j(b, "email-sms/audience-matrix.json", {}) or {}).get("segments") or [])
            for b in brands]
    out.append(row("segments", segs))
    sized = []
    for b in brands:
        m = (j(b, "email-sms/audience-matrix.json", {}) or {}).get("segments") or []
        sized.append(f"{sum(1 for s in m if s.get('profiles'))} of {len(m)} counted")
    out.append(row("segments · with a size", sized,
                   "an uncounted segment cannot be split into variants"))
    avs = []
    for b in brands:
        a = C.L.avatars(b, WORKSPACE) if C.L else []
        avs.append(f"{len(a)} ({sum(1 for x in a if x.get('rows'))} with language)")
    out.append(row("avatars", avs))

    # --- moments -----------------------------------------------------------
    ev = []
    for b in brands:
        d = j(b, "calendar/moments.json", {}) or {}
        ms = [m for blk in (d.get("avatars") or {}).values() for m in blk.get("moments", [])]
        c = collections.Counter(m.get("evidence") for m in ms)
        ev.append(f"{len(ms)} · " + " ".join(f"{k}:{v}" for k, v in sorted(c.items())))
    out.append(row("moments", ev, "proven = the brand's own sends prove it"))

    # --- formats -----------------------------------------------------------
    fmt = []
    for b in brands:
        cl = j(b, "email-sms/classified.json", []) or []
        types_with = len({r.get("type") for r in cl if r.get("type")})
        fmt.append(f"{len(cl)} sends covering {types_with} types")
    out.append(row("formats to write from", fmt))
    for b in brands:
        cl = j(b, "email-sms/classified.json", []) or []
        have = {r.get("type") for r in cl}
        gap = sorted(k for k in cats[b] if k not in have)
        out.append(row(f"formats · {b} types with NO example",
                       [f"{len(gap)} of {len(cats[b])}"],
                       ", ".join(gap[:10]) + ("…" if len(gap) > 10 else "")))
    return out


def render(brands, rows):
    w = max(len(r["label"]) for r in rows) + 2
    L = [f"# Brand check — {' vs '.join(brands)}", "",
         "Shapes, not contents. Different offers is the point; a different "
         "SHAPE is a bug waiting to be noticed.", "",
         "| | " + " | ".join(brands) + " | |",
         "|---|" + "---|" * len(brands) + "---|"]
    drifted = 0
    for r in rows:
        mark = "" if r["same"] else " ⚠"
        drifted += not r["same"]
        vals = " | ".join(f"`{v}`" for v in r["values"])
        if len(r["values"]) < len(brands):
            vals = f"{vals} |" + " |" * (len(brands) - len(r["values"]) - 1)
        L.append(f"| **{r['label']}**{mark} | {vals} | {r['note']} |")
    L += ["", f"**{drifted} row(s) differ.** A difference is not automatically "
              "wrong — read each one.", ""]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brands", nargs="+")
    ap.add_argument("--out")
    a = ap.parse_args()
    brands = a.brands or sorted(
        d.name for d in (WORKSPACE / "brands").iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "email-sms").is_dir())
    doc = render(brands, compare(brands))
    if a.out:
        Path(a.out).write_text(doc)
        print(f"-> {rel(Path(a.out))}")
    else:
        print(doc)


if __name__ == "__main__":
    main()
