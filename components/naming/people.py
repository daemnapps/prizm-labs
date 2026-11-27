#!/usr/bin/env python3
"""Names for who an ad is for (PEOPLE.md): check one, join the three, read one back.

    people.py check avatar|sub|demographic <name>
    people.py address <avatar> [<sub>] [<demographic>]
    people.py list <brand>
    people.py profile <brand> <avatar> [<sub>] [<demographic>]     the profile's name, label and old names, from either spelling
    people.py profiles <brand>                                      every profile of a brand with its name (what has no new name yet is flagged)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
import anatomy as A                                                                                        # noqa: E402
KINDS = ("tried", "when", "where", "since", "feels", "has")
AGES = ("18-24", "25-34", "35-44", "45-54", "55-64", "65-plus")
ETHNIC = ("black", "white", "latino", "east-asian", "south-asian", "middle-eastern", "mixed")
GENDERS = ("male", "female")
# a person's character, sex, age or race: the demographic's job, never an avatar's or sub-avatar's
NEVER = {"king", "guy", "man", "men", "woman", "women", "kid", "kids", "mom", "dad", "brother", "sister", "teen", "boy", "girl", "jefe", "rey", "fighter", "seeker", "hider",
         "buyer", "regular", "reckoner", "black", "white", "latino", "latina", "male", "female", "old", "young"}
WORD = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def demographic(name):
    """{gender, age, ethnicity, language} or None. Reads the older slash spelling too."""
    m = re.match(r"^(%s)[-/](%s)[-/](%s)(?:[-/]([a-z]+))?$" % ("|".join(GENDERS), "|".join(AGES), "|".join(ETHNIC)), name or "")
    return dict(zip(("gender", "age", "ethnicity", "language"), m.groups())) if m else None


def check(layer, name):
    """What is wrong with a name; [] when nothing is."""
    if layer == "demographic":
        return [] if demographic(name) and "/" not in name else ["not <gender>-<age>-<ethnicity>[-<language>] from the fixed lists"]
    bad = [] if WORD.match(name or "") else ["lowercase words joined by - only"]
    w = (name or "").split("-")
    bad += ["'%s' is a person, not a problem: that is the demographic" % x for x in w if x in NEVER]
    if layer == "avatar":
        if len(w) > 3:
            bad.append("an avatar is 1 to 3 words")
        if w[0] in KINDS:
            bad.append("opens like a sub-avatar")
    elif layer == "sub":
        if w[0] not in KINDS or len(w) < 2:
            bad.append("opens with its kind: " + ", ".join(KINDS))
        if len(w) > 5:
            bad.append("up to 5 words")
        if w[0] == "where" and not A.open_("-".join(w[1:])):
            bad.append("%s is not a part of the body on file (anatomy.py list)" % "-".join(w[1:]))
    else:
        bad.append("layer is avatar, sub or demographic")
    return bad


def address(avatar, sub="", demo=""):
    parts = [("avatar", avatar), ("sub", sub), ("demographic", (demo or "").replace("/", "-"))]
    for layer, n in parts:
        if n and check(layer, n):
            raise SystemExit("%s %s: %s" % (layer, n, "; ".join(check(layer, n))))
    return "_".join(n for _, n in parts if n)


_AL = {}
BRANDS = HERE.parents[1] / "brands"                          # where the brand folders are (a test points it at a dummy brand)


def _brand_files():
    """Each brand's own people file, when it has one: brands/<brand>/core-avatars/people.json (the brand's home for its names)."""
    out = {}
    try:
        for d in sorted(BRANDS.iterdir()):
            f = d / "core-avatars" / "people.json"
            if f.is_file():
                out[d.name] = f
    except OSError:
        pass
    return out


def aliases():
    """The aliases, read once and again only when a file changes (every tool's person lookup goes through here). A brand's own
    `brands/<brand>/core-avatars/people.json` (avatars, subs, demographics, merges) wins over its entry in the central file, which
    stays as the fallback while a brand's names move into its own folder."""
    f = HERE / "people-aliases.json"
    own = _brand_files()
    key = (f.stat().st_mtime, tuple((b, p.stat().st_mtime) for b, p in own.items()), str(BRANDS))
    if _AL.get("m") != key:
        d = json.loads(f.read_text())
        for b, p in own.items():
            d.setdefault("brands", {})[b] = json.loads(p.read_text())
        _AL.update(m=key, d=d)
    return _AL["d"]


def _narrowed(brand):
    """(old folder name, {sub, demographic}) for every card that is a sub-avatar narrowed by a signed demographic."""
    b = aliases()["brands"].get(brand) or {}
    return [(o, v) for o, v in (b.get("demographics") or {}).items() if isinstance(v, dict)]


def _avatar_of(brand, old):
    """The avatar folder that holds this old card (from the brand's sub-avatar files)."""
    root = BRANDS / brand / "core-avatars"
    for f in root.glob("*/sub-avatars/*%s.md" % old):
        return f.parent.parent.name
    return None


def merges(brand):
    """profile id -> {into, lens, ...} for every profile merged into another (profiles/CREATE.md gate 4): the owner's decision, kept in the aliases."""
    return (aliases()["brands"].get(brand) or {}).get("merges") or {}


def folders(brand, name, sub="", demo=""):
    """See _folders; a profile merged into another resolves to the one it was merged into."""
    a, s, d = _folders(brand, name, sub, demo)
    mg = merges(brand)
    if mg:
        pid = profile(brand, a, s, d)["id"]
        hit = mg.get(pid) or mg.get(profile(brand, a, s)["id"])
        if hit:
            return _folders(brand, hit["into"], "", d)
    return a, s, d


def _folders(brand, name, sub="", demo=""):
    """A PROFILE (or an avatar and sub-avatar, old or new spelling) as the brand folders spell it:
    (avatar folder, sub-avatar folder or "", demographic). The one door every tool uses to take a person: `--profile`
    carries `<avatar>[_<sub>][_<demographic>][/point]`; the older --avatar/--sub pair still works. A profile that is an
    avatar plus a demographic (the older `el-rey-cansado`) comes back as that sub-avatar's folder."""
    head = (name or "").partition("/")[0]
    if "_" in head and not sub:
        x = parse(head)
        name, sub, demo = x["avatar"], x["sub"], demo or x["demographic"]
    for old, dm in _narrowed(brand):                                 # a card that is a sub-avatar narrowed by a signed demographic
        if demo and demo == dm["demographic"] and sub in (dm["sub"], old) and canon(brand, name)[0] == _avatar_of(brand, old):
            return canon(brand, name)[0], old, ""
    a, s = canon(brand, name, sub)
    if not s and demo:
        b = aliases()["brands"].get(brand) or {}
        d = BRANDS / brand / "core-avatars" / a / "sub-avatars"
        for old, dm in (b.get("demographics") or {}).items():
            dm = dm["demographic"] if isinstance(dm, dict) else dm
            if dm == demo and d.is_dir() and any(f.name.endswith(old + ".md") for f in d.glob("*.md")):
                return a, old, ""                                # the older name that IS this demographic: its folder holds the profile
    return a, s, demo


def canon(brand, avatar, sub=""):
    """(avatar, sub) as the folders on disk spell them, from either the new or the old name."""
    if "_" in (avatar or "") and not sub:                       # a profile id: its avatar and sub-avatar
        a, s, _ = folders(brand, avatar)
        return a, s
    b = aliases()["brands"].get(brand) or {"avatars": {}, "subs": {}}
    new = b["avatars"].get(avatar, avatar)
    back = {v: k for k, v in b["avatars"].items()}
    subs = {v: k for k, v in (b["subs"].get(new) or {}).items()}
    if sub not in subs:                                       # the aliases file may list a sub-avatar under another avatar than its folder (PEOPLE.md, open call 1)
        subs = {v: k for m in b["subs"].values() for k, v in m.items()}
    return back.get(avatar, avatar), subs.get(sub, sub)


def new_names(brand, avatar, sub=""):
    """(avatar, sub) as PEOPLE.md names them, from either; what has no new name yet comes back as it is."""
    a, s = canon(brand, avatar, sub)
    b = aliases()["brands"].get(brand) or {"avatars": {}, "subs": {}}
    new = b["avatars"].get(a, a)
    for av, m in b["subs"].items():
        if s in m and (av == new or s not in (b["subs"].get(new) or {})):
            return new, m[s]
    return new, s


# ---------------------------------------------------------------- the profile and the points inside it (PEOPLE.md, "The profile")

POINT_KINDS = ("desire", "feeling", "belief", "role", "experience", "behavior", "doubt")
KIND_LEAD = {"tried": "Tried", "when": "When", "where": "", "since": "Since", "feels": "Feels", "has": "Has"}


def _title(words):
    w = [x for x in words.split("-") if x]
    return " ".join(w).capitalize() if w else ""


def sub_label(sub):
    """A sub-avatar as a page reads it: `where-back-of-head` -> Back of head, `tried-every-wash` -> Tried every wash."""
    kind, _, rest = (sub or "").partition("-")
    if kind in KIND_LEAD and rest:
        return _title(("%s-%s" % (KIND_LEAD[kind].lower(), rest)) if KIND_LEAD[kind] else rest)
    return _title(sub)


def demo_label(demo):
    d = demographic(demo)
    if not d:
        return ""
    who = {"male": "man", "female": "woman"}[d["gender"]]
    eth = {"east-asian": "East Asian", "south-asian": "South Asian", "middle-eastern": "Middle Eastern"}.get(d["ethnicity"], d["ethnicity"].capitalize())
    return "%s %s %s%s" % (eth, who, d["age"].replace("-", "\u2013").replace("plus", "+"), " (%s)" % d["language"].capitalize() if d.get("language") else "")


def profile(brand, avatar, sub="", demo=""):
    """The profile as one unit: avatar + sub-avatar + demographic (the person's own matrix). Reads old or new names.
    {"id": avatar[_sub][_demographic], "label": page words, "avatar", "sub", "demographic", "old": {"avatar", "sub"}, "named": True|False}
    A sub-avatar the aliases file lists as a DEMOGRAPHIC (an older name like `el-rey-cansado`) is read as its avatar with that demographic.
    `named` is False while the avatar or the sub still has no PEOPLE.md name."""
    oa, os_ = canon(brand, avatar, sub)
    b = aliases()["brands"].get(brand) or {"avatars": {}, "subs": {}, "demographics": {}}
    na, ns = new_names(brand, oa, os_)
    d = (demo or "").replace("/", "-")
    dm = (b.get("demographics") or {}).get(os_) if os_ else None
    if isinstance(dm, dict):                                         # a sub-avatar with the demographic it was written for (2026-11-27)
        d, ns = d or dm["demographic"], dm["sub"]
    elif os_ and dm and not ns == (b["subs"].get(na) or {}).get(os_):
        d, ns = d or dm, ""
    named = not check("avatar", na) and (not ns or not check("sub", ns))
    parts = [x for x in (na, ns, d) if x]
    label = " \u00b7 ".join(x for x in (_title(na), sub_label(ns), demo_label(d)) if x)
    return {"id": "_".join(parts), "label": label, "avatar": na, "sub": ns, "demographic": d, "old": {"avatar": oa, "sub": os_}, "named": named}


def parse(name):
    """`avatar[_sub][_demographic][/point]` back into its parts. The demographic is whichever last part reads as one."""
    head, _, point = (name or "").partition("/")
    parts = head.split("_")
    d = parts.pop() if len(parts) > 1 and demographic(parts[-1]) else ""
    return {"avatar": parts[0], "sub": parts[1] if len(parts) > 1 else "", "demographic": d, "point": point}


def point_id(kind, text):
    """The address of one point inside a profile: `<kind>-<first words of it>-<4 hex of the whole>`. A point refilled with
    the same words keeps its id; a reworded one is a new point."""
    import hashlib
    norm = " ".join(re.findall(r"[a-z0-9']+", (text or "").lower()))
    slug = "-".join(re.findall(r"[a-z0-9]+", " ".join(norm.split()[:6])))
    return "%s-%s-%s" % (kind, slug, hashlib.sha1(("%s|%s" % (kind, norm)).encode()).hexdigest()[:4])


def element(profile_id, kind, text):
    """One element of a profile, the unit an ad is made for and results are read against: `<profile>/<point id>`."""
    return "%s/%s" % (profile_id, point_id(kind, text))


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if a[:1] == ["check"] and len(a) == 3:
        bad = check(a[1], a[2])
        print("ok" if not bad else "; ".join(bad))
        return 1 if bad else 0
    if a[:1] == ["address"] and len(a) > 1:
        print(address(*a[1:4]))
        return 0
    if a[:1] == ["list"] and len(a) == 2:
        b = aliases()["brands"][a[1]]
        for old, new in b["avatars"].items():
            print("%-18s <- %s" % (new, old))
            for o, n in (b["subs"].get(new) or {}).items():
                print("   %-26s <- %s" % (n, o))
        for o, n in b["demographics"].items():
            print("%-26s <- %s" % ((n["sub"] + " · " + n["demographic"]) if isinstance(n, dict) else n, o))
        return 0
    if a[:1] == ["profile"] and len(a) > 2:
        print(json.dumps(profile(a[1], a[2], *(a[3:5])), indent=1, ensure_ascii=False))
        return 0
    if a[:1] == ["profiles"] and len(a) == 2:
        sys.path.insert(0, str(HERE.parent / "creative-strategist" / "machine"))
        import who as W                                                         # the public reader of the brand's people
        for av in W.avatars(a[1]):
            for sb in (W.subs(a[1], av) or [""]):
                x = profile(a[1], av, sb)
                print("%-52s %-46s %s%s" % (x["id"], x["label"], "<- %s %s" % (x["old"]["avatar"], x["old"]["sub"]), "" if x["named"] else "   (no PEOPLE.md name yet)"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
