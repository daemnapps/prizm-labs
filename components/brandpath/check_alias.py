"""Old path vs brand_path, side by side, on the real brand folders.

    python3 components/brandpath/check_alias.py            # every brand under brands/
    python3 components/brandpath/check_alias.py --verbose  # every row, not only the differences
    python3 components/brandpath/check_alias.py --before origin/wave-a/code   # after the move (wave C)

For every reader that now goes through brandpath, this rebuilds the path the
reader used to build (today's literal folder names) and puts the brandpath
answer beside it. ALIAS ONLY means the two must agree: a reader must find the
same file it found yesterday.

A row is a DIFFERENCE when the two disagree about whether the path exists,
or point at two different existing paths. Two spellings of a path that
exists under NEITHER name are reported separately ("absent under both"):
no reader can tell them apart — every one tests `.exists()` / `.is_file()`
before reading — and brandpath spells the missing file where today's first
folder for it is, which is where the plan says it moves to.

Exit 1 on any difference. Reads only; names no brand (rule 7).

--before REF is the move-time proof (wave C). Today's places no longer exist
on disk, so "old" is read from the git tree at REF (the last commit before
the folders moved): a row is SAME when the brandpath answer is a file whose
blob hash equals the blob the old path had at REF (a folder: every file
under it, same hashes), DIFFERENCE when the old path existed at REF and the
answer is missing or differs. A second section walks EVERY file each brand
had at REF through `resolve_rel` — the same content must be found at its new
place. `RENAMED` lists the files whose name had to change in the move (a
clash with a file already in the target folder); they are checked by content
under the new name.
"""
import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brandpath as BP  # noqa: E402

WS = BP.repo()
BRANDS = WS / "brands"

# --before: {repo-relative path: blob sha} for everything under brands/ at REF
BASE = None

# files the move had to RENAME (their name clashed with a file already in the
# target folder): old repo-relative path under the brand -> new one. Checked by
# content under the new name; nothing else in the proof is special-cased.
RENAMED = {
    "calendar/README.md": "strategy/calendar-README.md",
}


def load_base(ref):
    out = subprocess.run(["git", "ls-tree", "-r", ref, "--", "brands/"], cwd=WS,
                         capture_output=True, text=True, check=True).stdout
    base = {}
    for line in out.splitlines():
        meta, _, path = line.partition("\t")
        base[path] = meta.split()[2]
    return base


def blob_sha(p):
    data = Path(p).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _rel(p):
    try:
        return Path(p).resolve().relative_to(WS.resolve()).as_posix()
    except ValueError:
        return None


def base_files_under(p):
    """{path under p: blob} for a FOLDER at REF; {} when nothing was there."""
    r = _rel(p)
    if r is None:
        return {}
    pre = r + "/"
    return {k[len(pre):]: v for k, v in BASE.items() if k.startswith(pre)}


def existed(p):
    """Did `p` exist before the move? On disk today, or at REF with --before."""
    if BASE is None:
        return Path(p).exists()
    r = _rel(p)
    return r is not None and (r in BASE or any(k.startswith(r + "/") for k in BASE))

# reader · today's relative path · brandpath key + parts
# (`*` in the old path stands for one folder/file name found on disk)
KEYED = [
    # video-production element_paths / promptify / plan_from_brief / casting
    ("cast list (ai-cast/casting)", "ai-cast/casting", ("ai-elements/characters", "casting")),
    ("cast folder (ai-cast)", "ai-cast", ("ai-elements/characters",)),
    ("element library (elements)", "elements", ("ai-elements",)),
    ("element index (elements/index.json)", "elements/index.json", ("ai-elements", "index.json")),
    ("registry (core-avatars/casting)", "core-avatars/casting", ("core-avatars", "casting")),
    # image-production paths (component + static)
    ("identity folder", "identity", ("brand-identity",)),
    ("identity anchors", "identity-anchors.md", ("brand-identity", "identity-anchors.md")),
    ("identity/anchors.md", "identity/anchors.md", ("brand-identity", "anchors.md")),
    ("identity/palette.md", "identity/palette.md", ("brand-identity", "palette.md")),
    ("identity/fonts.md", "identity/fonts.md", ("brand-identity", "fonts.md")),
    ("identity/logo-white.png", "identity/logo-white.png", ("brand-identity", "logo-white.png")),
    ("identity/logo-dark.png", "identity/logo-dark.png", ("brand-identity", "logo-dark.png")),
    ("products folder", "products", ("products",)),
    ("products/images.json", "products/images.json", ("products", "images.json")),
    ("products/store.json", "products/store.json", ("products", "store.json")),
    ("offer bank", "products/offer-bank.md", ("products", "offer-bank.md")),
    ("products/reference/look.md", "products/reference/look.md", ("products", "reference", "look.md")),
    ("offers folder", "offers", ("offers",)),
    # email / calendar / story-builder
    ("core avatars", "core-avatars", ("core-avatars",)),
    ("language index", "core-avatars/language-index.json", ("core-avatars", "language-index.json")),
    ("objection bank", "core-avatars/objection-bank.md", ("core-avatars", "objection-bank.md")),
    ("before-afters", "core-avatars/before-afters.md", ("core-avatars", "before-afters.md")),
    ("moments", "calendar/moments.json", ("strategy", "moments.json")),
    ("angles.json", "strategy/angles.json", ("strategy", "angles.json")),
    ("variables/email.md", "variables/email.md", ("variables", "email.md")),
    ("variables/video.md", "variables/video.md", ("variables", "video.md")),
    # intake (existing-content)
    ("ads", "existing-content/ads", ("intake", "ads")),
    ("angles.md", "existing-content/angles.md", ("intake", "angles.md")),
    ("landing pages", "existing-content/landing-pages", ("intake", "landing-pages")),
    ("email designs", "existing-content/emails/designs", ("intake", "emails", "designs")),
    ("email designs index", "existing-content/emails/designs/index.json", ("intake", "emails", "designs", "index.json")),
    ("intake folder", "existing-content", ("intake",)),
    # creators (video-teardown run / simplify / creator_profile)
    ("profile home", "channels/creators/profile-home.json", ("content-creators", "profile-home.json")),
    ("brief intro", "channels/creators/brief-intro.md", ("content-creators", "brief-intro.md")),
    ("contact", "channels/creators/contact.md", ("content-creators", "contact.md")),
    ("likeness folder", "channels/creators/likeness", ("content-creators", "likeness")),
    # competitors
    ("competitive folder", "competitive", ("competitors",)),
    ("qc dictionary", "qc-dictionary.json", ("competitors", "qc-dictionary.json")),
]

# today-relative paths that tools carry as DATA (checklists, needs tables,
# the chain config, the brand's own variable map) — through resolve_rel
DATA_RELS = [
    "core-avatars/language-index.json", "email/segments.md", "email/ledger.json",
    "email/learnings.md", "email/sends", "calendar/moments.json", "products/offer-bank.md",
    "identity-anchors.md", "existing-content/emails", "channels/creators/profile-home.json",
    "ai-cast/casting", "elements/index.json", "variables/video.md", "market.md",
    "identity/market.md", "strategy/market.md", "strategy/angles.json", "competitive",
    "identity/palette.md", "products/reference/look.md", "customer/avatar.md",
    "customer/language-bank.md", "customer/objection-bank.md", "products/", "products",
    "elements/character", "elements/environment", "elements/prop", "creators", "ai-cast",
    "hook-ledger.md", "element-facts.json", "story.md", "position.md",
]


def brands():
    return sorted(p.name for p in BRANDS.iterdir()
                  if p.is_dir() and not p.name.startswith(("_", ".")))


def names_in(folder, files=False):
    """Children of a folder as they were BEFORE the move: on disk, or at REF."""
    if BASE is not None:
        under = base_files_under(folder)
        names = {k.split("/")[0] for k in under if (("/" not in k) if files else ("/" in k))}
        return sorted(n for n in names if not n.startswith("."))
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir()
                  if (p.is_file() if files else p.is_dir()) and not p.name.startswith("."))


def read_before(p):
    """A file's text as it was before the move (disk, or the REF blob)."""
    if BASE is None:
        return Path(p).read_text()
    r = _rel(p)
    if r is None or r not in BASE:
        raise OSError(f"{p} not at REF")
    return subprocess.run(["git", "cat-file", "-p", BASE[r]], cwd=WS,
                          capture_output=True, text=True, check=True).stdout


def rows_for(brand):
    """(reader, old path, new path) for one brand — every keyed reader, then
    the per-name readers filled from what is on disk, then the data paths."""
    b = BRANDS / brand
    out = []
    for label, old, key in KEYED:
        out.append((label, b / old, BP.brand_path(brand, *key, root=BRANDS)))
    # per-person: casting_home / cast_voice / cast_files / build_cast / identity_of
    for who in names_in(b / "ai-cast"):
        if who == "casting":
            continue
        out.append((f"cast person {who}", b / "ai-cast" / who,
                    BP.brand_path(brand, "ai-elements/characters", who, root=BRANDS)))
        for f in names_in(b / "ai-cast" / who, files=True):
            out.append((f"cast file {who}/{f}", b / "ai-cast" / who / f,
                        BP.brand_path(brand, "ai-elements/characters", who, f, root=BRANDS)))
    # per-product: email.py / element_paths.product_home / rewrite_briefs
    for p in names_in(b / "products"):
        out.append((f"product folder {p}", b / "products" / p, BP.brand_path(brand, "products", p, root=BRANDS)))
        out.append((f"product file {p}/product.md", b / "products" / p / "product.md",
                    BP.brand_path(brand, "products", p, "product.md", root=BRANDS)))
        out.append((f"identity_of products/{p}", b / "products" / p,
                    BP.brand_path(brand, "products", p, root=BRANDS)))
    for f in names_in(b / "products", files=True):
        out.append((f"product file {f}", b / "products" / f, BP.brand_path(brand, "products", f, root=BRANDS)))
    # per-creator: creator_files (profile .md under channels/creators, likeness jpg),
    # identity_of(creators/<handle>)
    handles = set(names_in(b / "creators")) | {Path(n).stem for n in names_in(b / "channels" / "creators", files=True)
                                              if n.endswith(".md")}
    for h in sorted(handles):
        out.append((f"creator profile {h}.md", b / "channels" / "creators" / f"{h}.md",
                    BP.brand_path(brand, "content-creators", f"{h}.md", root=BRANDS)))
        out.append((f"creator likeness {h}.jpg", b / "channels" / "creators" / "likeness" / f"{h}.jpg",
                    BP.brand_path(brand, "content-creators", "likeness", f"{h}.jpg", root=BRANDS)))
        out.append((f"identity_of creators/{h}", b / "creators" / h,
                    BP.brand_path(brand, "content-creators", h, root=BRANDS)))
    # element cards / index sources (gpt_drafts, board.py, plan_from_brief)
    idx = b / "elements" / "index.json"
    if existed(idx):
        try:
            items = json.loads(read_before(idx))
            items = items.get("elements") if isinstance(items, dict) and isinstance(items.get("elements"), list) \
                else [v for v in items.values() if isinstance(v, dict)] if isinstance(items, dict) else items
            for e in items or []:
                src = e.get("source") if isinstance(e, dict) else None
                if src:
                    out.append((f"element source {src}", b / src, BP.resolve_rel(brand, src, root=BRANDS)))
        except ValueError:
            pass
    # data-carried paths
    for rel in DATA_RELS:
        out.append((f"data path {rel}", b / rel, BP.resolve_rel(brand, rel, root=BRANDS)))
    # the video-teardown chain config, brand filled in
    cfg = WS / "tools/video-teardown/machine/chain_config.json"
    if cfg.is_file():
        def walk(x):
            if isinstance(x, dict):
                for v in x.values():
                    yield from walk(v)
            elif isinstance(x, list):
                for v in x:
                    yield from walk(v)
            elif isinstance(x, str) and x.startswith("brands/<brand>/"):
                yield x
        for src in sorted(set(walk(json.loads(cfg.read_text())))):
            rel = src[len("brands/<brand>/"):]
            out.append((f"chain_config {src}", b / rel, BP.resolve_rel(brand, rel, root=BRANDS)))
    # the brand's own variable maps (variables/*.md right-hand column)
    for vn in names_in(b / "variables", files=True):
        vf = b / "variables" / vn
        if vf.suffix != ".md":
            continue
        import re
        for m in re.finditer(r"^\s*\|?\s*`\{?([a-z_]+)\}?`\s*\|\s*`([^`]+)`", read_before(vf), re.M):
            rel = m.group(2).replace("<avatar>", "_avatar_")
            if rel.startswith("brands/") or rel.startswith("/") or (WS / rel).exists():
                continue
            out.append((f"variable map {vf.name}:{m.group(1)}", b / rel, BP.resolve_rel(brand, rel, root=BRANDS)))
    return out


def module_rows(brand):
    """The changed reader MODULES themselves, asked the question directly:
    the dict / function each returns, against the literal each used to
    build. Import trouble is reported, never hidden."""
    b = BRANDS / brand
    out, notes = [], []

    def try_import(folder, name):
        sys.path.insert(0, str(WS / folder))
        try:
            return importlib.import_module(name)
        except Exception as e:  # noqa: BLE001
            notes.append(f"{folder}/{name}: {type(e).__name__}: {e}")
            return None
        finally:
            sys.path.remove(str(WS / folder))

    ip = try_import("tools/image-production", "image_production.paths")
    if ip:
        d = ip.brand(brand)
        for k, old in (("identity", b / "identity"), ("products", b / "products"),
                       ("product_images", b / "products" / "images.json"),
                       ("elements", b / "elements"), ("offers", b / "offers")):
            out.append((f"image_production.paths.brand[{k}]", old, d[k]))
    st = try_import("tools/image-production/static/tools", "paths")
    if st and hasattr(st, "brand") and hasattr(st, "BRANDS"):
        d = st.brand(brand)
        for k, old in (("identity", b / "identity"), ("logo_white", b / "identity/logo-white.png"),
                       ("logo_dark", b / "identity/logo-dark.png"), ("products", b / "products"),
                       ("offer", b / "products/offer-bank.md")):
            out.append((f"static/tools/paths.brand[{k}]", old, d[k]))
    for m in ("paths", "brandpath"):
        sys.modules.pop(m, None)
    cp = try_import("components/casting", "casting.paths")
    if cp:
        d = cp.brand(brand)
        old_regs = [p for p in (b / "core-avatars" / "casting", b / "ai-cast" / "casting") if existed(p)]
        out.append(("casting.paths.brand[cast]", b / "ai-cast", d["cast"]))
        out.append(("casting.paths.brand[registry]", old_regs[0] if old_regs else b / "core-avatars" / "casting", d["registry"]))
        for i, r in enumerate(d["registries"]):
            out.append((f"casting.paths.registries[{i}]", old_regs[i] if i < len(old_regs) else None, r))
    it = try_import(next((p for p in ("tools/image-teardown/tools", "lab/owner/image-teardown/tools")
                         if (WS / p / "paths.py").is_file()), "tools/image-teardown/tools"), "paths")
    if it and hasattr(it, "brand") and hasattr(it, "LANE"):
        d = it.brand(brand)
        old_id = next((f for f in (b / "identity-anchors.md", b / "identity/anchors.md", b / "identity/palette.md")
                       if existed(f)), b / "identity-anchors.md")
        for k, old in (("avatars", b / "core-avatars"), ("products", b / "products"),
                       ("offer", b / "products/offer-bank.md"), ("identity", old_id),
                       ("palette", b / "identity/palette.md"), ("cast", b / "ai-cast/casting")):
            out.append((f"image-teardown paths.brand[{k}]", old, d[k]))
    sys.modules.pop("paths", None)
    ep = try_import("tools/video-production/machine", "element_paths")
    if ep:
        out.append(("element_paths.cast_list", b / "ai-cast" / "casting", ep.cast_list(brand, WS)))
        for p in names_in(b / "products"):
            out.append((f"element_paths.product_home {p}", b / "products" / p, ep.product_home(brand, p, WS)))
        for who in names_in(b / "ai-cast"):
            if who != "casting":
                # casting_home has one answer: runs/ only (SI-98 (shelf and index homes))
                new = ep.casting_root(brand, WS) / who
                out.append((f"element_paths.casting_home {who}", new,
                            ep.casting_home(brand, who, WS)))
    return out, notes


def same_content(old, new):
    """With --before: does `new` hold, today, exactly what `old` held at REF?
    A file: equal blob hashes. A folder: every file under it, equal hashes."""
    r = _rel(old)
    if r in BASE:
        return Path(new).is_file() and blob_sha(new) == BASE[r]
    under = base_files_under(old)
    if not under:
        return False
    if not Path(new).is_dir():
        return False
    for k, sha in under.items():
        f = Path(new) / k
        if not f.is_file() or blob_sha(f) != sha:
            return False
    return True


def classify(old, new):
    if old is None:
        return "DIFF"
    if BASE is not None:
        if old == new and Path(new).exists():
            return "same"          # a data path already spelled in the new name
        if existed(old):
            return "same" if same_content(old, new) else "DIFF"
        return "absent-both" if not Path(new).exists() else "DIFF"
    if old == new:
        return "same"
    if old.exists() or new.exists():
        return "DIFF"
    return "absent-both"


def sweep(brand):
    """Every file the brand had at REF -> where resolve_rel says it is now.
    Returns (checked, moved, [problems])."""
    b = BRANDS / brand
    problems, moved, checked = [], 0, 0
    for rel, sha in sorted(base_files_under(b).items()):
        if rel == BP.FOLDERS_FILE:
            continue
        checked += 1
        new = b / RENAMED[rel] if rel in RENAMED else BP.resolve_rel(brand, rel, root=BRANDS)
        if not new.is_file():
            problems.append(f"{rel} -> {new.relative_to(b).as_posix()}  MISSING")
        elif blob_sha(new) != sha:
            problems.append(f"{rel} -> {new.relative_to(b).as_posix()}  CONTENT DIFFERS")
        elif new != b / rel:
            moved += 1
    return checked, moved, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--before", metavar="REF",
                    help="the git ref the folders were moved FROM; old paths and their content are read there")
    a = ap.parse_args()
    global BASE
    if a.before:
        BASE = load_base(a.before)
        print(f"before = {a.before}  ({len(BASE)} files under brands/ at that ref)")
    total = {"same": 0, "absent-both": 0, "DIFF": 0}
    sweep_total = {"checked": 0, "moved": 0, "problems": 0}
    notes_all = []
    for brand in brands():
        rows = rows_for(brand)
        mrows, notes = module_rows(brand)
        rows += mrows
        notes_all += [f"{brand}: {n}" for n in notes]
        counts = {"same": 0, "absent-both": 0, "DIFF": 0}
        print(f"\n== brands/{brand}  ({len(rows)} reader paths)")
        for label, old, new in rows:
            kind = classify(old, new)
            counts[kind] += 1
            if kind != "same" or a.verbose:
                o = old.relative_to(b := BRANDS / brand).as_posix() if old else "—"
                n = new.relative_to(b).as_posix() if new.is_relative_to(b) else str(new)
                mark = {"same": "  =", "absent-both": "  ~", "DIFF": "!!!"}[kind]
                print(f"  {mark} {label:44} old {o:52} new {n}")
        print(f"   identical {counts['same']} · absent under both names (spelling differs) {counts['absent-both']}"
              f" · DIFFERENCES {counts['DIFF']}")
        for k in total:
            total[k] += counts[k]
        if BASE is not None:
            checked, moved, problems = sweep(brand)
            sweep_total["checked"] += checked
            sweep_total["moved"] += moved
            sweep_total["problems"] += len(problems)
            print(f"   every file at REF: {checked} checked · {moved} found at a new place · "
                  f"{checked - moved - len(problems)} unmoved · PROBLEMS {len(problems)}")
            for pr in problems:
                print(f"  !!! {pr}")
    if notes_all:
        print("\nmodules that could not be asked directly (import trouble):")
        for n in notes_all:
            print("  -", n)
    print(f"\nTOTAL identical {total['same']} · absent-both {total['absent-both']} · DIFFERENCES {total['DIFF']}")
    if BASE is not None:
        print(f"TOTAL files at REF {sweep_total['checked']} · moved {sweep_total['moved']} · PROBLEMS {sweep_total['problems']}")
    sys.exit(1 if total["DIFF"] or sweep_total["problems"] else 0)


if __name__ == "__main__":
    main()
