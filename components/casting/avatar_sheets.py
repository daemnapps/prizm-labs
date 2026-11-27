#!/usr/bin/env python3
"""avatar_sheets.py — turn one avatar list into uniform casting sheets, through the sheet maker.

    python3 components/casting/avatar_sheets.py <avatars.json> [--dry-run]

An avatar is a NEW person built for a customer group, never a customer. Customer groups are read as WORDS (their counts
and their look); a customer's own picture is refused as a reference, here, before anything is spent. Each avatar's spec
goes to video-production's make_character.py with the three core pictures (master, headshot,
angles-expressions), then gets the core.json layout and a proposed talent card, which goes in the run folder for a person to move.
The list names everything brand-specific; this file names no brand and no person.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
from casting.cards import validate  # noqa: E402

CORE = ["master", "headshot", "angles-expressions"]
NOT_A_REFERENCE = re.compile(r"before[-_ ]?(and[-_ ]?)?after|/proof/|testimonial|customer|review", re.I)


def refused(a: dict) -> list:
    """Every reason this avatar may not be built. A customer's picture is the one this file exists to stop."""
    out = []
    for r in a.get("real_references") or []:
        if NOT_A_REFERENCE.search(str(r.get("file", ""))) or NOT_A_REFERENCE.search(str(r.get("from", ""))):
            out.append(f"{a.get('id')}: {r.get('file')} reads as a customer picture; customers are never a reference")
    if not a.get("group"):
        out.append(f"{a.get('id')}: no `group`: name the customer group in words")
    return out + validate(a["card"], a.get("brand", ""))


def spec_of(a: dict, brand: str, base: dict) -> dict:
    s = {k: a[k] for k in ("id", "who", "adjustments", "real_references", "character")}
    s.update(brand=brand, base=a.get("base") or base["base"], details=a.get("details") or base["details"],
             looks=a.get("looks") or base["looks"])
    s["adjustments"] = list(a["adjustments"]) + list(base.get("adjustments_common") or [])
    return s


def core_json(a: dict) -> dict:
    return {"_what": "The one layout every core person follows: headshot, expressions, outfits, voice.",
            "person": a["id"], "headshot": "sheets/headshot.jpg", "expressions": "sheets/angles-expressions.jpg",
            "outfits": a.get("outfits") or [], "closet": "../../wardrobe/wardrobe.json",
            "voice": None, "skin": ["clear", "razor-bumps-neck"], "gaps": ["voice"], "styles": {},
            "built_for": a["group"], "not_a_real_customer": True}


def finish(a: dict, home: Path, sp: Path):
    """The small copies, the real reference and the records a partial sheet run does not write."""
    from PIL import Image
    pics = {"master.jpg": "full/master.png", "sheets/headshot.jpg": "full/sheets/headshot.png",
            "sheets/angles-expressions.jpg": "full/sheets/angles-expressions.png"}
    for small, big in pics.items():
        im = Image.open(home / big).convert("RGB")
        im.thumbnail((1600, 1600))
        (home / small).parent.mkdir(parents=True, exist_ok=True)
        im.save(home / small, quality=85)
    (home / "reference").mkdir(exist_ok=True)
    refs = []
    for r in a["real_references"]:
        f = (sp.parent / r["file"]).resolve()
        (home / "reference" / f.name).write_bytes(f.read_bytes())
        refs.append({**r, "file": f"reference/{f.name}"})
    (home / "spec.json").write_text(sp.read_text())
    (home / "core.json").write_text(json.dumps(core_json(a), indent=1))
    (home / "provenance.json").write_text(json.dumps({
        "element": a["id"], "kind": "person", "real_references": refs, "adjustments": a["adjustments"],
        "built_for": a["group"], "not_a_real_customer": True,
        "customer_pictures_sent_to_a_model": 0}, indent=1))
    (home / "character.md").write_text(f"# {a['character']['title']}\n\n{a['who']}\n\nBuilt for: {a['group']}.\n\n"
                                       "An invented person. Never shown or described as a real customer.\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("avatars")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*", help="only these avatar ids")
    x = ap.parse_args(argv)
    path = Path(x.avatars).resolve()
    d = json.loads(path.read_text())
    brand, repo, maker = d["brand"], HERE.parents[1], HERE.parent / "video-production" / "machine" / "make_character.py"
    people = [a for a in d["avatars"] if not x.only or a["id"] in x.only]
    bad = [p for a in people for p in refused({**a, "brand": brand})]
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 1
    specs, cards = path.parent / "specs", []
    specs.mkdir(exist_ok=True)
    for a in people:
        sp = specs / f"{a['id']}.json"
        sp.write_text(json.dumps(spec_of(a, brand, d), indent=1))
        home = repo / "runs" / "ai-elements" / brand / "casting" / a["id"]
        cmd = [sys.executable, str(maker), str(sp), "--out", str(home), "--only", *CORE] + (["--dry-run"] if x.dry_run else [])
        if subprocess.run(cmd).returncode:
            return 1
        if not x.dry_run:
            finish(a, home, sp)
        cards.append(a["card"])
    (path.parent / "proposed-cards.json").write_text(json.dumps(cards, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
