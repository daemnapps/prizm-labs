#!/usr/bin/env python3
"""tidy_folders — a brand's person folders renamed to the names in PEOPLE.md, so a folder is spelled like its profile.

    python3 components/naming/tidy_folders.py plan  --brand <brand>     every move, every path rewrite; changes nothing
    python3 components/naming/tidy_folders.py apply --brand <brand>     makes them (git mv), then writes the aliases
    python3 components/naming/tidy_folders.py sweep --brand <brand>     after a copy takes the renamed folders from the team:
                                                                        moves anything still under an old name (unsaved
                                                                        slots, drafts, research) into the new folders

What moves, for any brand:
- `brands/<brand>/core-avatars/<old avatar>/`                 -> `<avatar>/`              (people-aliases `avatars`)
- `.../sub-avatars/sub-NN-<old>.md` and `sub-NN-<old>/`       -> `<sub>.md`, `<sub>/`      (`subs`; the number goes)
- a card that is a sub-avatar narrowed by a demographic       -> `<sub>_<demographic>.md`, `<sub>_<demographic>/`
- `brands/<brand>/core-avatars/<avatar>/slots/<old>.json` and
  `runs/creative-strategist/<brand>/who/<old avatar>/<old>.json` -> the same under the new names
What is rewritten: folder paths only (`core-avatars/<old>/`, `sub-avatars/sub-NN-<old>`) in the brand's own files and in
`runs/creative-strategist/<brand>/`, and the ids in `core-avatars/avatars.json`. Names used as values (a language row's
id, an ad set, a feedback question) stay as they are: old names keep resolving through the aliases' `was` list, and
nothing live is renamed (PEOPLE.md rule 5). After `apply`, the aliases map every folder to itself and `was` holds the
old names, so every tool reading a person through the door (`people.folders`, `profiles.load`) finds the new folders.
Brand-agnostic: every name comes from the aliases file and the brand's folders.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import people as N                                                                       # noqa: E402

ALIASES = HERE / "people-aliases.json"
TEXT = (".json", ".md", ".txt", ".html")


def root():
    return N.BRANDS.parent


def plan(brand):
    """{"moves": [(old, new)], "rewrites": [(old text, new text)], "avatars": {old: new}, "subs": {avatar: {old: new}}}."""
    b = (N.aliases()["brands"].get(brand) or {})
    if b.get("folders") == "named":
        return {"done": True, "moves": [], "rewrites": [], "avatars": {}, "subs": {}}
    core = N.BRANDS / brand / "core-avatars"
    A = b.get("avatars") or {}
    subs_all = {o: n for m in (b.get("subs") or {}).values() for o, n in m.items()}
    demos = {o: v for o, v in (b.get("demographics") or {}).items() if isinstance(v, dict)}
    moves, rewrites, av_map, sub_map = [], [], {}, {}
    for d in sorted(p for p in core.iterdir() if p.is_dir() and (p / "profile.md").is_file()):
        old_a, new_a = d.name, A.get(d.name, d.name)
        av_map[old_a] = new_a
        sub_map[new_a] = {}
        sd = d / "sub-avatars"
        for card in sorted(sd.glob("*.md")) if sd.is_dir() else []:
            old_s = re.sub(r"^sub-\d+-", "", card.stem)
            if old_s in demos:
                new_s = "%s_%s" % (demos[old_s]["sub"], demos[old_s]["demographic"])
            else:
                new_s = subs_all.get(old_s, old_s)
            sub_map[new_a][old_s] = new_s
            if card.stem != new_s:
                moves.append((card, sd / (new_s + ".md")))
                if (sd / card.stem).is_dir():
                    moves.append((sd / card.stem, sd / new_s))
                rewrites.append(("sub-avatars/%s" % card.stem, "sub-avatars/%s" % new_s))
            for slot_dir in (d / "slots", root() / "runs" / "creative-strategist" / brand / "who" / old_a):
                f = slot_dir / (old_s + ".json")
                if f.is_file() and old_s != new_s:
                    moves.append((f, slot_dir / (new_s + ".json")))
        if old_a != new_a:
            moves.append((d, core / new_a))
            rewrites.append(("core-avatars/%s/" % old_a, "core-avatars/%s/" % new_a))
            rewrites.append(("core-avatars/%s\"" % old_a, "core-avatars/%s\"" % new_a))
            w = root() / "runs" / "creative-strategist" / brand / "who" / old_a
            if w.is_dir():
                moves.append((w, w.parent / new_a))
    for old, new in [(o, n) for o, n in av_map.items() if o != n]:
        if (core / new).exists():
            raise SystemExit("refused: core-avatars/%s already exists beside %s; join them by hand first" % (new, old))
    return {"done": False, "moves": moves, "rewrites": rewrites, "avatars": av_map, "subs": sub_map}


def _files(brand):
    for top in (N.BRANDS / brand, root() / "runs" / "creative-strategist" / brand):
        for f in top.rglob("*") if top.is_dir() else []:
            if f.is_file() and f.suffix in TEXT and ".git" not in f.parts:
                yield f


def _git(*a):
    return subprocess.run(["git", "-C", str(root())] + list(a), capture_output=True, text=True)


def apply(brand, say=print):
    p = plan(brand)
    if p["done"]:
        say("already named: nothing to do")
        return p
    # 1. paths inside the brand's own files (before the moves, so every file is still where it was)
    changed = 0
    for f in list(_files(brand)):
        try:
            s = f.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        t = s
        for a, b in p["rewrites"]:
            t = t.replace(a, b)
        if t != s:
            f.write_text(t)
            changed += 1
    # 2. the moves, deepest first (sub folders before the avatar folder that holds them)
    for src, dst in sorted(p["moves"], key=lambda m: -len(m[0].parts)):
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        r = _git("mv", str(src), str(dst))
        if r.returncode != 0:                           # not tracked (a fresh run file): a plain move
            src.rename(dst)
    # 3. the roster: ids are the folder names
    av = N.BRANDS / brand / "core-avatars" / "avatars.json"
    if av.is_file():
        d = json.loads(av.read_text())
        for row in d.get("avatars") or []:
            old = row.get("id")
            new = p["avatars"].get(old, old)
            row["was"] = old if old != new else row.get("was")
            row["id"], row["folder"] = new, "core-avatars/%s" % new
            row["sub_avatars"] = [p["subs"].get(new, {}).get(s, s) for s in row.get("sub_avatars") or []]
            if row.get("was") is None:
                row.pop("was", None)
        av.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    # 4. the aliases: every folder maps to itself; the old names move to `was`
    write_aliases(brand, p)
    N._AL.clear()
    profile_ids(brand)
    say("moved %d, rewrote paths in %d file(s); the aliases now read the new folders" % (len(p["moves"]), changed))
    return p


def renamed_ids(brand):
    """(old profile id, new profile id) for every sub-avatar whose new name was itself renamed (aliases `renamed`)."""
    b = N.aliases()["brands"].get(brand) or {}
    return [("%s_%s" % (a, o), "%s_%s" % (a, n)) for a, m in (b.get("renamed") or {}).items() for o, n in m.items()]


def profile_ids(brand, say=print):
    """A renamed profile's name, carried by its filed card and its draft: rewritten, and the draft files renamed."""
    pairs = renamed_ids(brand)
    if not pairs:
        return 0
    n = 0
    drafts = root() / "runs" / "creative-strategist" / brand / "profiles"
    for old, new in pairs:
        for f in sorted(drafts.glob(old + ".*")) if drafts.is_dir() else []:
            dst = f.with_name(new + f.suffix)
            if not dst.exists():
                if _git("mv", str(f), str(dst)).returncode != 0:
                    f.rename(dst)
                n += 1
    for f in list(_files(brand)):
        try:
            s = f.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        t = s
        for old, new in pairs:
            t = re.sub(r"\b%s\b" % re.escape(old), new, t)
        if t != s:
            f.write_text(t)
            n += 1
    return n


def sweep(brand, say=print):
    """A copy that took the renamed folders from the team may still hold files under the old names: work nobody saved
    (slots, drafts, research). Each is moved into its new folder; one that already exists there is left where it is and
    listed for a person to compare."""
    b = N.aliases()["brands"].get(brand) or {}
    was = b.get("was") or {}
    if b.get("folders") != "named":
        raise SystemExit("not renamed yet: run apply first")
    moved, left = [], []
    core = N.BRANDS / brand / "core-avatars"
    who = root() / "runs" / "creative-strategist" / brand / "who"

    def put(src, dst):
        if not src.exists() or src.is_symlink():
            return
        if src.is_dir():
            for f in sorted(x for x in src.rglob("*") if x.is_file()):
                put(f, dst / f.relative_to(src))
            for d in sorted((x for x in src.rglob("*") if x.is_dir()), key=lambda x: -len(x.parts)):
                try:
                    d.rmdir()
                except OSError:
                    pass
            try:
                src.rmdir()
            except OSError:
                pass
            return
        if dst.exists():
            if dst.read_bytes() != src.read_bytes():
                left.append(str(src.relative_to(root())))
            else:
                src.unlink()
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        moved.append(str(dst.relative_to(root())))

    for old_a, new_a in (was.get("avatars") or {}).items():
        put(core / old_a, core / new_a)
        put(who / old_a, who / new_a)
    for a, m in (was.get("subs") or {}).items():
        sd = core / a / "sub-avatars"
        for old_s, new_s in m.items():
            for f in sorted(sd.glob("sub-*-%s.md" % old_s)) + sorted(sd.glob("%s.md" % old_s)):
                put(f, sd / (new_s + ".md"))
            for d in sorted(sd.glob("sub-*-%s" % old_s)) + [sd / old_s]:
                if d.is_dir():
                    put(d, sd / new_s)
            put(who / a / (old_s + ".json"), who / a / (new_s + ".json"))
            put(core / a / "slots" / (old_s + ".json"), core / a / "slots" / (new_s + ".json"))
    n = profile_ids(brand)
    pairs = []                                          # paths inside files written before the rename (unsaved drafts, research)
    for o, nw in (was.get("avatars") or {}).items():
        pairs += [("core-avatars/%s/" % o, "core-avatars/%s/" % nw), ("core-avatars/%s\"" % o, "core-avatars/%s\"" % nw)]
    fixed = 0
    for f in list(_files(brand)):
        try:
            s = f.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        t = s
        for x, y in pairs:
            t = t.replace(x, y)
        for a, m in (was.get("subs") or {}).items():
            for o, nw in m.items():
                t = re.sub(r"sub-avatars/(?:sub-\d+-)?%s(?=[/.\"])" % re.escape(o), "sub-avatars/%s" % nw, t)
        if t != s:
            f.write_text(t)
            fixed += 1
    n += fixed
    say("swept %d file(s) into the new folders%s%s" % (len(moved), ", renamed %d profile name(s)" % n if n else "",
                                                       "; left for a person (a different copy is already there): " + ", ".join(left) if left else ""))
    return moved, left


def write_aliases(brand, p, path=ALIASES):
    d = json.loads(path.read_text())
    b = d["brands"].setdefault(brand, {})
    was = b.setdefault("was", {"avatars": {}, "subs": {}})
    for o, n in p["avatars"].items():
        if o != n:
            was["avatars"][o] = n
    for a, m in p["subs"].items():
        for o, n in m.items():
            if o != n:
                was["subs"].setdefault(a, {})[o] = n
    b["avatars"] = {n: n for n in p["avatars"].values()}
    subs = {}
    for a, m in p["subs"].items():
        for n in m.values():
            if "_" not in n:
                subs.setdefault(a, {})[n] = n
    b["subs"] = subs
    demos = {}
    for o, v in (b.get("demographics") or {}).items():
        if isinstance(v, dict):
            demos["%s_%s" % (v["sub"], v["demographic"])] = v
    b["demographics"] = demos
    b["folders"] = "named"
    path.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("plan", "apply", "sweep"))
    ap.add_argument("--brand", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        p = plan(a.brand)
        if p["done"]:
            print("already named")
            return 0
        for s, d in p["moves"]:
            print("move  %s\n   -> %s" % (s.relative_to(root()), d.relative_to(root())))
        for o, n in p["rewrites"]:
            print("path  %s -> %s" % (o, n))
        return 0
    if a.cmd == "sweep":
        sweep(a.brand)
        return 0
    apply(a.brand)
    return 0


if __name__ == "__main__":
    sys.exit(main())
