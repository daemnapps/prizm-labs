#!/usr/bin/env python3
"""Output formats, as data.

Formats used to be a markdown table someone hand-edited. That is the same
mistake the language layer already corrected: a record kept as prose drifts,
cannot be queried, and cannot be extended without editing prose. Formats are
rows now — `formats.json` — and this renders them for whichever stage needs
them.

A new format is a new row. A brand or channel that needs a different shape
overrides by key rather than forking the file.

    python3 formats.py                 # what the machine writes, readable
    python3 formats.py --keys          # just the keys
"""

import json
import sys

from paths import HERE

FILE = HERE / "bank" / "formats.json"


def load(brand_root=None):
    """The catalogue, with a brand's overrides applied if it has any.

    A brand may keep `formats.json` of its own shape — same schema, only the
    keys it wants to change. Anything it does not mention it inherits.
    """
    d = json.loads(FILE.read_text())
    rows = {f["key"]: f for f in d["formats"]}
    if brand_root:
        b = brand_root / "formats.json"
        if b.is_file():
            try:
                over = json.loads(b.read_text())
                for f in over.get("formats", []):
                    rows.setdefault(f["key"], {}).update(f)
                d["defaults"].update(over.get("defaults", {}))
            except Exception as e:
                print(f"     brand formats.json ignored ({e})")
    d["formats"] = list(rows.values())
    return d


def keys(brand_root=None):
    return [f["key"] for f in load(brand_root)["formats"]]


def render(brand_root=None, only=None):
    """The catalogue as a stage reads it. Only what a writer needs to obey."""
    d = load(brand_root)
    want = {k.strip() for k in only.split(",")} if only else None
    out = ["# Output formats", "",
           "Each row is a shape this machine writes. **The length is the "
           "format's, never the source's** — what transfers from a source is "
           "its persuasion structure, not how many words its own medium "
           "happened to need.", ""]
    for f in d["formats"]:
        if want and f["key"] not in want:
            continue
        ln = f.get("length", {})
        out.append(f"## `{f['key']}` — {f.get('name', f['key'])}")
        out.append(f"- **What it is:** {f.get('what','')}")
        if ln:
            out.append(f"- **Length:** {ln.get('min')}–{ln.get('max')} {ln.get('unit','words')}"
                       f" — hit this range; count as you write, not after")
        out.append(f"- **Form:** {f.get('form','')}")
        if f.get("opens_with"):
            out.append(f"- **Opens with:** {f['opens_with']}")
        if f.get("reads_as"):
            out.append(f"- **Reads as:** {f['reads_as']}")
        if f.get("carries_offer"):
            out.append(f"- **Carries the offer:** {f['carries_offer']}")
        if f.get("requires"):
            out.append(f"- **Requires:** {f['requires']}")
        out.append(f"- **Bodies wanted:** {f.get('variations', d['defaults']['variations'])}"
                   f" — genuinely different runs at the argument, not rewordings")
        out.append("")
    h, ds = d["defaults"]["headlines"], d["defaults"]["descriptions"]
    out += ["## For the set, once", "",
            f"- **Headlines:** exactly {h['count']}, {h['words'][0]}–{h['words'][1]} words each, "
            "drawn from this source's own language — never a line that would fit any ad.",
            f"- **Descriptions:** exactly {ds['count']}, {ds['words'][0]} words each. "
            "Flat statement of what it is; no persuasion verbs.", ""]
    return "\n".join(out)


if __name__ == "__main__":
    if "--keys" in sys.argv:
        print(", ".join(keys()))
    else:
        print(render())
