#!/usr/bin/env python3
"""The delivery rule — editors and designers never name a file.

    delivery_rule.py --brand <brand> [--folder <drive folder>] [--apply]

Every delivery folder is matched to its brief, and every file in it is renamed
from that brief's header in `brands/<brand>/briefs/briefs.json`:

    folder   brand_product_brief_batch               one per delivery
    file     brand_product_brief_batch_asset-NN.ext  one per cut / picture

The short form (the owner, 2026-09-29): everything else about the ads is in the
brief, looked up by its number. The file carries no funnel; the Meta ad is
the folder name + the funnel (`names.short_meta`), one ad per batch.
A folder already named in the older 13-part form is converted to the short
form (same product, brief and batch).

The swipe a brief was built from (`*control*`, `*reference*`) and unchosen
picks (`*candidate*`) are left as they are — they ride along, they are not the
work. A folder is left alone and LISTED — never guessed — when:
  - no brief matches its name,
  - its brief is missing a field a name needs (angle, product, concept …),
  - a file's frame does not match the brief's ratio.
A folder already in the short form is done and skipped.

Without --apply it only reports. With --apply it renames, writes
`naming.json` (old name -> new name, and the folder's own old name as
`folder_was`) into the folder, and rebuilds
`READY-TO-LAUNCH.md` at the top of the watched folder: every named delivery
grouped by the ad set it goes in (avatar + angle).

With --to-check, every named delivery ALSO goes to the owner's approval: copied into
Shared Assets/meta/<brand>/1-check/creator/<folder name>/ with its card
(components/meta-upload/feed_creator.py; the delivery folder stays as it is). Without
--apply that is a dry run that prints the cards it would write.

The watched folders are the brand's, in `brands/<brand>/briefs/delivery.json`,
so nothing here names a brand or a path (workspace rule 7).
"""
import argparse, json, re, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import names as N
BP = N.BP                # the brand-folder map (or brands/<brand>/… as in brands/_TEMPLATE)

WS = N.WS                # names.py's locator: run-kit paths.repo()
MEDIA = {".mp4": "video", ".mov": "video", ".m4v": "video",
         ".png": "static", ".jpg": "static", ".jpeg": "static", ".webp": "static"}
# Files that ride along in a delivery folder but are not the work: the swipe
# the brief was built from, and picks that were never chosen.
NOT_WORK = ("control", "reference", "swipe", "candidate")


def is_work(p):
    return p.is_file() and p.suffix.lower() in MEDIA and not any(w in p.name.lower() for w in NOT_WORK)


PART_ORDER = ["product", "media", "source", "talent", "avatar", "problem",
              "angle", "concept", "format", "brief", "ratio", "batch"]


def resolve(folder):
    """A watched folder on THIS computer. delivery.json names folders the way
    Drive shows them ("Shared Assets/…", "<Brand>/Ads/…"), not by one person's
    mount path, so the rule runs on whichever Mac anyone uses.
    Looked for in every Google Drive account mounted here: the shared drives,
    My Drive, and folders shared in by shortcut. A full path is used as is."""
    p = Path(folder).expanduser()
    if p.is_absolute():
        return p
    for acct in sorted((Path.home() / "Library" / "CloudStorage").glob("GoogleDrive-*")):
        for base in [acct / "Shared drives", acct / "My Drive", *(acct / ".shortcut-targets-by-id").glob("*")]:
            if (base / folder).is_dir():
                return base / folder
    return p


# The brief register every lane's `briefs.py open` writes to. A brief opened
# there has a number before anyone writes its naming header here, so a new
# brief's delivery is matched off the register too (2026-10-01) — never held
# as "no brief matches" for want of a hand-kept row.
# Image teardown graduated to components/ on 2026-10-01; the lab path is the
# fallback for a checkout that has not pulled the move.
REGISTER = next((f for f in (WS / "tools" / "image-teardown" / "briefs.json",
                             WS / "tools" / "image-teardown" / "briefs.json") if f.is_file()),
                WS / "tools" / "image-teardown" / "briefs.json")


def load(brand):
    base = BP.brand_path(brand, "briefs", root=WS / "brands")
    f = base / "briefs.json"
    reg = json.loads(f.read_text()) if f.is_file() else {"briefs": []}
    cfg = json.loads((base / "delivery.json").read_text()) if (base / "delivery.json").is_file() else {}
    # One brief per brand + product + number (the owner, 2026-10-01: numbers count
    # per brand AND product). A register row is the same brief as a brand row
    # only when both are on the same count — old shared number, or the same
    # product's per-product number — never because the digits match.
    have = {(b.get("brief"), b.get("count") == N.PER_PRODUCT, None if b.get("count") != N.PER_PRODUCT
             else N.slug(b.get("product") or "")) for b in reg["briefs"]}
    if REGISTER.is_file():
        for code, r in sorted(json.loads(REGISTER.read_text()).get("briefs", {}).items()):
            new = r.get("brief") or N.brief_id(code)
            per = bool(N.parse_brief_key(code))
            ident = (new, per, N.slug(r.get("product") or "") if per else None)
            # A row with no product is kept too (2026-10-01): it cannot be named
            # (held "missing product"), but it is what makes a bare number that
            # a newer product also uses read as ambiguous rather than as the
            # newer brief.
            if r.get("brand") == brand and ident not in have:
                reg["briefs"].append({"brief": new, "type": r.get("type"), "product": r.get("product"),
                                      "avatar": r.get("avatar"), "aliases": [], "found_in": REGISTER.name,
                                      **({"count": N.PER_PRODUCT} if per else {})})
    return reg, cfg


def pick(briefs, want, product=None, exact_only=False, brand=None):
    """The one brief numbered `want` — of `product` when known. Two briefs
    sharing the number with no product to choose: AmbiguousBrief. With a
    product and no brief of it, the old shared-count brief with that number
    still stands in (a name written under the old count, often with the old
    squashed product word) — unless `exact_only` (the product was only
    spotted in a folder name)."""
    hits = [b for b in briefs if b.get("brief") == want]
    if product:
        exact = [b for b in hits if N.slug(b.get("product") or "") == N.slug(product)]
        hits = exact if exact or exact_only else [b for b in hits if b.get("count") != N.PER_PRODUCT]
    if len({(b.get("product"), b.get("count")) for b in hits}) > 1:
        raise N.AmbiguousBrief(f"{want} is used by more than one {(brand or '').upper() + ' ' if brand else ''}product "
                               f"({', '.join(sorted(b.get('product') or 'no product' for b in hits))}) — say which")
    return hits[0] if hits else None


def match_brief(folder_name, briefs, brand=None):
    """The brief a delivery belongs to, read off its folder name: an alias,
    or the brief number in any spelling (p136, brief-0136, Project 136)."""
    low = folder_name.lower()
    for b in briefs:
        for a in b.get("aliases") or []:
            if a and a.lower() in low:
                return b
    m = (re.search(r"brief[-_ ]?0*(\d{2,4})", low) or re.search(r"\bp0*(\d{2,4})\b", low)
         or re.search(r"project\s*0*(\d{2,4})", low))
    if m:
        want = f"brief-{int(m.group(1)):04d}"
        if m.re.pattern.startswith(r"\bp"):
            # pNNN is the old shared count's spelling: a per-product brief never had one
            return pick([b for b in briefs if b.get("count") != N.PER_PRODUCT], want, brand=brand)
        # a folder name that also carries the product picks between briefs sharing the number
        prods = {N.slug(b.get("product") or "") for b in briefs if b.get("product")}
        product = next((p for p in sorted(prods, key=len, reverse=True) if p and p in N.slug(low)), None)
        return pick(briefs, want, product, exact_only=True, brand=brand)
    return None


def ratio_of(path):
    """9x16 / 4x5 / 1x1 / 16x9 read off the file itself, or None."""
    try:
        if MEDIA.get(path.suffix.lower()) == "video":
            out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                  "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                  str(path)], capture_output=True, text=True, timeout=120).stdout
            w, h = (int(x) for x in out.strip().split(",")[:2])
        else:
            from PIL import Image
            w, h = Image.open(path).size
    except Exception:
        return None
    r = w / h
    for name, val in (("9x16", 9 / 16), ("4x5", 4 / 5), ("1x1", 1), ("16x9", 16 / 9)):
        if abs(r - val) < 0.02:
            return name
    return f"{w}x{h}"


def batch_for(day, taken):
    """batch-YYYY-MM-DD-<letter>, the next letter free that day."""
    for letter in "abcdefghijklmnopqrstuvwxyz":
        b = f"batch-{day}-{letter}"
        if b not in taken:
            taken.add(b)
            return b
    raise SystemExit(f"26 batches on {day} already")


def unit_for(brand, b, batch):
    return N.short_unit(brand, b["product"], b.get("brief") or "none", batch)


def brief_key(b):
    return b.get("brief") or (b.get("aliases") or [None])[0]


def plan(brand, root, reg):
    briefs = reg["briefs"]
    need = reg.get("_required_to_name", ["product"])
    taken = set()
    for p in root.iterdir():
        d = N.parse_any(p.name) if p.is_dir() else None
        if d:
            taken.add(d["batch_id"] if d["form"] != "short" else d["batch"])
    done, todo, held = [], [], []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        d = N.parse_any(folder.name)
        files = sorted(p for p in folder.iterdir() if is_work(p))
        if d and d["form"] == "short":
            # a folder already named as its unit can still hold files the
            # editor dropped under their own names: name those, in order
            unit = folder.name
            def num(f):
                q = N.parse_any(f.name) or {}
                a = q.get("asset_id") if q.get("ad_name") == unit else None
                return int(a.split("-")[1]) if a else None
            loose = [f for f in files if num(f) is None]
            if loose:
                n0 = max([num(f) or 0 for f in files] + [0])
                todo.append((folder, unit, [(f, N.short_file(unit, n0 + i) + f.suffix.lower())
                                            for i, f in enumerate(loose, 1)], d.get("brief_id")))
            else:
                done.append(folder)
            continue
        if d and d["form"] == "new":
            # the older 13-part name: same product, brief and batch, short form
            try:
                b = (pick(briefs, d["brief"], d["product"] if d["product"] != "none" else None, brand=brand) if d["brief"] != "none"
                     else next((x for x in briefs if not x.get("brief") and x.get("concept") == d["concept"]), None))
            except N.AmbiguousBrief as e:
                held.append((folder.name, str(e)))
                continue
            product = d["product"] if d["product"] != "none" else (b or {}).get("product")
            if not product:
                held.append((folder.name, f"{brief_key(b) if b else d['brief']} is missing product"))
                continue
            unit = N.short_unit(brand, product, d["brief"], d["batch"])
            todo.append((folder, unit, [(f, N.short_file(unit, (N.parse_any(f.name) or {}).get("asset_n") or i) + f.suffix.lower())
                                        for i, f in enumerate(files, 1)], brief_key(b) if b else None))
            continue
        if not files:
            continue
        try:
            b = match_brief(folder.name, briefs, brand)
        except N.AmbiguousBrief as e:
            held.append((folder.name, str(e)))
            continue
        if not b:
            held.append((folder.name, "no brief matches this folder name"))
            continue
        missing = [k for k in need if not b.get(k)]
        if missing:
            held.append((folder.name, f"{brief_key(b)} is missing {', '.join(missing)}"))
            continue
        bad = [(f.name, r) for f in files if (r := ratio_of(f)) and b.get("ratio") and r != b["ratio"]]
        if bad:
            held.append((folder.name, f"frame {bad[0][1]} on {bad[0][0]} — the brief says {b['ratio']}"))
            continue
        day = date.fromtimestamp(min(f.stat().st_mtime for f in files)).isoformat()
        unit = unit_for(brand, b, batch_for(day, taken))
        todo.append((folder, unit, [(f, N.short_file(unit, i) + f.suffix.lower())
                                    for i, f in enumerate(files, 1)], brief_key(b)))
    return done, todo, held


def apply(todo):
    for folder, unit, files, key in todo:
        prev = {}
        if (folder / "naming.json").is_file():
            prev = json.loads((folder / "naming.json").read_text())
        log = prev.get("files", [])
        for f, new in files:
            if f.name != new:
                f.rename(folder / new)
                log.append({"was": f.name, "now": new})
        # the folder's name before the rule renamed it (2 Oct 2026): the work queue
        # matches a renamed delivery back to its package by it — kept from the
        # first renaming, never overwritten by a later one
        was = prev.get("folder_was") or (folder.name if folder.name != unit else None)
        (folder / "naming.json").write_text(json.dumps(
            {**{k: v for k, v in prev.items() if k not in ("unit", "brief", "named", "files", "folder_was")},
             "unit": unit, "brief": key or prev.get("brief"), "named": date.today().isoformat(),
             **({"folder_was": was} if was else {}), "files": log}, indent=1, ensure_ascii=False))
        if folder.name != unit:
            folder.rename(folder.parent / unit)


def launch_sheet(brand, root):
    """Every named delivery, grouped by the ad set it goes in (avatar + angle
    from its brief)."""
    groups = {}
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        d = N.parse_any(folder.name)
        if not d or d["form"] != "short":
            continue
        key = d["brief"] if d["brief"] != "none" else None
        if not key and (folder / "naming.json").is_file():
            key = json.loads((folder / "naming.json").read_text()).get("brief")
        try:
            b = N.brief_header(brand, key, d["product"]) if key else None
        except N.AmbiguousBrief:
            b = None
        angle = (b or {}).get("angle")
        adset = N.SEP.join(["adset", brand, (b or {}).get("avatar") or "none", angle or "none"])
        files = sorted(p.name for p in folder.iterdir() if is_work(p))
        groups.setdefault(adset, []).append((folder.name, len(files)))
    lines = ["# Ready to launch", "",
             f"Built {date.today().isoformat()} by the delivery rule. Every named delivery here, grouped by",
             "the Meta ad set it goes in. At launch each batch is one Meta ad named",
             "`<folder name>_<funnel id>` (funnel ids: `brands/<brand>/web/funnels/funnels.json`).", ""]
    for adset in sorted(groups):
        flag = "  ← the brief has no angle yet: no ad set until it does" if adset.endswith("_none") else ""
        lines += [f"## `{adset}`{flag}", ""]
        lines += [f"- `{name}` — {n} file(s)" for name, n in groups[adset]] + [""]
    (root / "READY-TO-LAUNCH.md").write_text("\n".join(lines))
    return groups


def to_check(brand, root, links=(), cards_root=None, dry_run=False, since=None):
    """Every named delivery here into 1-check as a card (meta-upload/feed_creator.py)."""
    sys.path.insert(0, str(WS / "components" / "meta-upload"))
    import feed_creator as FC
    try:
        res = FC.feed_root(brand, root, since=since, links=links, root=cards_root, dry_run=dry_run)
    except FC.T.Refused as e:
        print(f"  TO CHECK refused: {e}")
        return []
    print(f"  to check: {sum(1 for p, _, _ in res if p)} card(s){' (dry run)' if dry_run else ''}")
    for p, why, _ in res:
        print("    " + (FC.T.show(p).replace("\n", "\n    ") if p else f"REFUSED {why}"))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--folder", action="append",
                    help="a delivery folder to watch; default: the brand's delivery.json")
    ap.add_argument("--apply", action="store_true", help="rename; without it, report only")
    ap.add_argument("--to-check", action="store_true",
                    help="also file every named delivery into meta/<brand>/1-check/<lane>/ (dry run without --apply)")
    ap.add_argument("--links", nargs="*", default=[], help="with --to-check: catalog link ids for the cards")
    ap.add_argument("--root", help="with --to-check: the meta/ folder (default $META_CARDS_ROOT or the Drive)")
    ap.add_argument("--since", help="with --to-check: only deliveries from this date (YYYY-MM-DD) on")
    a = ap.parse_args()
    reg, cfg = load(a.brand)
    roots = [resolve(p) for p in (a.folder or cfg.get("watch", []))]
    if not roots:
        sys.exit(f"no folder given and brands/{a.brand}/briefs/delivery.json watches none")
    for root in roots:
        if not root.is_dir():
            print(f"not reachable on this computer: {root} (is Google Drive for desktop signed in to an account that can see it?)")
            continue
        done, todo, held = plan(a.brand, root, reg)
        print(f"== {root.parent.name + '/' if root.name == 'DELIVERABLES' else ''}{root.name}: {len(done)} named · {len(todo)} to name · {len(held)} held")
        for folder, unit, files, _ in todo:
            print(f"  NAME {folder.name}\n       -> {unit}  ({len(files)} file(s))")
        for name, why in held:
            print(f"  HELD {name}: {why}")
        if a.apply:
            apply(todo)
            launch_sheet(a.brand, root)
        if a.to_check:
            to_check(a.brand, root, a.links, a.root, dry_run=not a.apply, since=a.since)


if __name__ == "__main__":
    main()
