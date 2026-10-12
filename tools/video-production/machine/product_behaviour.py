"""PRODUCT BEHAVIOUR — how the real product sits, moves and works (2026-10-07).

the owner: "Every time that we pull in a product, we need to apply that product's
physics as well … go into the actual folders and assets themselves to make sure
we get this type of stuff. This is what's going to help reduce our time on each
generation."

A product kit measured the product's shape, size, colour and label, but not
what it can physically do — so the device, which has a domed base and rolls over, was
drawn standing upright on a table in five frames. This step reads the brand's
own files about the product and the list of its real pictures on the company
drive, and writes `behaviour` into kit.json: what it cannot do, every way it
rests (with the real pictures that show that rest, copied into the kit as
`sources/rest-*`), how it is held, what it does in use, and the wrong pictures
it keeps getting — every line with its receipt. `element_refs` puts the rest
pictures and these words on every frame the product is in.

    python3 tools/video-production/machine/product_behaviour.py <brand> <slug> [--dry-run]

`product_kit.py build` runs it at the end of every build.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
PROMPTS = HERE.parent / "prompts"
PIC = re.compile(r"\.(jpe?g|png|webp|gif)$", re.I)


def _kit():
    sys.path.insert(0, str(HERE))
    import product_kit as PK
    return PK


def names_of(brand: str, slug: str) -> list[str]:
    """The names the brand's files use for this product: the slug, its first
    word (device-face-brush → brush) and the aliases in images.json."""
    PK = _kit()
    out = [slug, slug.split("-")[0]] + PK.aliases(brand, slug)
    return [n for i, n in enumerate(out) if n and n not in out[:i]]


def brand_files(brand: str, slug: str, cap: int = 30000) -> list[tuple[str, str]]:
    """Every brand product file that names this product: its own file(s) whole,
    and from a shared file (one that names other products too) only the
    paragraphs that mention it."""
    root = WS / "brands" / brand / "products"
    names = names_of(brand, slug)
    pat = re.compile(r"\b(" + "|".join(re.escape(n.replace("-", " ")) + "|" + re.escape(n) for n in names) + r")\b", re.I)
    out = []
    for p in sorted(root.rglob("*.md")):
        text = p.read_text(errors="ignore")
        if not pat.search(text):
            continue
        own = any(p.stem.lower().startswith(n.lower()) for n in names)
        if not own:
            paras = [b for b in re.split(r"\n\s*\n", text) if pat.search(b)]
            text = "\n\n".join(paras)
        out.append((str(p.relative_to(WS)), text[:cap]))
    return out


def drive_pictures(brand: str, slug: str) -> tuple[Path | None, list[str]]:
    """The product's real pictures on the company drive, as paths under its
    product folder."""
    PK = _kit()
    base = PK.drive_brands()
    if not base:
        return None, []
    d = base / brand / "products" / slug
    if not d.is_dir():
        return None, []
    pics = sorted(str(p.relative_to(d)) for p in d.rglob("*") if PIC.search(p.name)
                  and "product-kit" not in p.parts and "versions" not in p.parts)
    return d, pics


def prompt_text(brand: str, slug: str) -> tuple[str, Path | None, list[str]]:
    sys.path.insert(0, str(WS / "components" / "run-kit"))
    from run_kit import prompts as P
    tpl = P.latest(PROMPTS, "product-behaviour")
    files = brand_files(brand, slug)
    d, pics = drive_pictures(brand, slug)
    sent = P.fill(Path(tpl).read_text(), {
        "product": f"{brand} · {slug} (also called: {', '.join(names_of(brand, slug)[1:]) or '—'})",
        "files": "\n\n".join(f"### {f}\n\n{t}" for f, t in files) or "(no brand file names it)",
        "pictures": "\n".join(f"- {p}" for p in pics) or "(no pictures on the drive)"})
    return sent, d, pics


def _small(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if subprocess.run(["sips", "-Z", "1600", str(src), "--out", str(dst)],
                      capture_output=True).returncode != 0:
        shutil.copy2(src, dst)


def build(brand: str, slug: str, dry_run: bool = False, call=None, log=print) -> dict | None:
    PK = _kit()
    kp = PK.home(brand, slug) / "kit.json"
    if not kp.exists():
        log(f"no kit for {brand}/{slug} — build the kit first")
        return None
    sent, d, pics = prompt_text(brand, slug)
    if dry_run:
        print(sent)
        return None
    if call is None:
        sys.path.insert(0, str(WS / "components" / "run-kit"))
        from run_kit import model as M
        mdl, _ = M.pick("checks", len(sent))
        call = lambda p: M.call(p, mdl, label="product behaviour")
    reply = call(sent)
    beh = json.loads(reply[reply.index("{"): reply.rindex("}") + 1])
    # the rest pictures: only real paths from the list, copied into the kit
    src_dir = PK.home(brand, slug) / "sources"
    for i, r in enumerate(beh.get("rests") or []):
        kept = []
        for p in (r.get("pictures") or [])[:2]:
            if p in pics and d is not None:
                dst = src_dir / f"rest-{i + 1}-{len(kept) + 1}{Path(p).suffix.lower() if Path(p).suffix.lower() != '.gif' else '.jpg'}"
                _small(d / p, dst)
                kept.append({"drive": p, "kit": str(dst.relative_to(PK.home(brand, slug)))})
        r["pictures"] = kept
    beh["read_from"] = [f for f, _ in brand_files(brand, slug)]
    beh["prompt"] = Path(next(iter(sorted((PROMPTS / "product-behaviour").glob("*.md"))))).name
    k = json.loads(kp.read_text())
    # a rest a person set by hand (the owner's throne) survives a rebuild, like a kit's hand_set
    old = k.get("behaviour") or {}
    for key in old.get("hand_set") or []:
        m = re.fullmatch(r"rests\[(\d+)\]", key)
        if m and len(old.get("rests") or []) > int(m.group(1)):
            i = int(m.group(1))
            beh.setdefault("rests", [])
            beh["rests"][i:i + 1] = [old["rests"][i]]
    if old.get("hand_set"):
        beh["hand_set"], beh["how"] = old["hand_set"], old.get("how", {})
    k["behaviour"] = beh
    kp.write_text(json.dumps(k, indent=1, ensure_ascii=False) + "\n")
    log(f"behaviour: {len(beh.get('cannot') or [])} cannot · {len(beh.get('rests') or [])} rest(s) · "
        f"{sum(len(r['pictures']) for r in beh.get('rests') or [])} rest picture(s) in the kit")
    return beh


def words(beh: dict | None, name: str = "the product") -> str:
    """The behaviour as one sentence for a picture prompt."""
    if not beh:
        return ""
    parts = []
    if beh.get("cannot"):
        parts.append(f"{name} " + "; ".join(c.rstrip(".") for c in beh["cannot"][:3]) + ".")
    rests = [r for r in beh.get("rests") or [] if r.get("how")]
    if rests:
        parts.append("When nobody is holding it, it " + " — or it ".join(r["how"].rstrip(".") for r in rests[:3])
                     + (" (the rest picture among the references)" if any(r.get("pictures") for r in rests) else "") + ".")
    if beh.get("alone"):        # the owner, 2026-10-09: a rule for when it is on its own, said outright
        parts.append(beh["alone"].rstrip(".") + ".")
    if beh.get("held"):
        parts.append("Held: " + beh["held"].rstrip(".") + ".")
    return " ".join(parts)


def motion_words(beh: dict | None, name: str = "the product") -> str:
    """The behaviour as one sentence for a CLIP prompt: what may happen to the
    product while the shot moves (the owner, 2026-10-09: the device is never left on its
    own — in the hand, or in its holder or case)."""
    if not beh:
        return ""
    parts = []
    if beh.get("alone"):
        parts.append(f"Throughout the clip, {name}: " + beh["alone"].rstrip(".") + ".")
    elif beh.get("cannot"):
        parts.append(f"Throughout the clip {name} " + "; ".join(c.rstrip(".") for c in beh["cannot"][:3]) + ".")
    if beh.get("held"):
        parts.append("While held it stays " + beh["held"].rstrip(".") + ".")
    return " ".join(parts)


def rest_refs(brand: str, slug: str, beh: dict | None) -> list[Path]:
    PK = _kit()
    out = []
    for r in (beh or {}).get("rests") or []:
        for p in r.get("pictures") or []:
            f = PK.home(brand, slug) / p["kit"]
            if f.exists():
                out.append(f)
        if out:
            break
    return out[:2]


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) != 2:
        print(__doc__); sys.exit(2)
    b = build(a[0], a[1], dry_run="--dry-run" in sys.argv)
    if b:
        print(json.dumps(b, indent=1, ensure_ascii=False))
