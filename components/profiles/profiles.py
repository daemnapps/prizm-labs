#!/usr/bin/env python3
"""profiles — the one door to a person (profile) and the one standard a profile is built and checked against.

    import profiles
    profiles.load(brand, "<avatar>[_<sub>][_<demographic>]")   the profile as ONE object, always the same shape
    profiles.check(brand, name)                                 what is wrong with it, by the standard (SPEC.md)
    profiles.audit(brand)                                       every profile of a brand against the standard
    profiles.doors(root)                                        tools that still take a person around this door
    profiles.pick(brand, avatar, product, seed)                 the profile a send speaks to when the plan names only the avatar

    python3 profiles.py audit  --brand <b>
    python3 profiles.py check  --brand <b> --profile <name>
    python3 profiles.py show   --brand <b> --profile <name>
    python3 profiles.py gate   --brand <b> --profile <name>     evidence and distinctness (CREATE.md gates 3, 4)
    python3 profiles.py init   --brand <b>                      the new-brand checklist: what stands between each profile and ads
    python3 profiles.py doors  [--save] [--strict]               --strict: every line building a person's path by hand

Reads only. It writes nothing in brands/ and spends nothing. A profile is BUILT by creative-strategist's who.py (the
card and the slots); this file joins what those wrote and says whether it meets the standard. Names: naming/PEOPLE.md.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMP = HERE.parent
ROOT = COMP.parent
for p in (COMP / "creative-strategist" / "machine", COMP / "naming"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import people as N                                                                                       # noqa: E402
import who as W                                                                                          # noqa: E402

# SPEC.md, as data. Every profile has every part; a part with no customer line is "open" and says why, never filled by guess.
CARD = ("desire", "opening", "doubt", "experiences", "emotions", "behaviors", "culture")     # who.py profile: the person on one page
SLOT_LISTS = ("desires", "roles", "beliefs", "experiences", "behaviors", "emotions")         # who.py fill: the deep slots
DOUBT_KINDS = tuple(W.DOUBTS)                                                                # four kinds of doubt
MIN_OWN = 25            # own customer lines a profile needs before ads are made for it (CREATE.md, gate 3); signed by the owner
SAME_PERSON = 0.5       # more than this share of a profile's lines also sit under ONE sibling: hold, the owner merges or keeps (gate 4)
def criteria(brand):
    """(MIN_OWN, SAME_PERSON) for a brand: its own `brands/<brand>/core-avatars/criteria.json` when it has one, else the defaults."""
    f = N.BRANDS / brand / "core-avatars" / "criteria.json"
    try:
        c = json.loads(f.read_text())
    except (OSError, ValueError):
        c = {}
    return int(c.get("min_own", MIN_OWN)), float(c.get("same_person", SAME_PERSON))


THIN = {"desires": 5, "roles": 3, "beliefs": 5, "experiences": 5, "behaviors": 5, "emotions": 5}   # below this a part is thin: a note, never a fail


def _card(brand, avatar, sub):
    if not sub:
        return None, "none"
    try:
        h, w = W.home(brand, avatar, sub), W.draft(brand, avatar, sub)
    except SystemExit:
        return None, "none"
    d = W.filed(brand, avatar, sub, newest=True)
    if not d:
        return None, "none"
    same = h.is_file() and w.is_file() and h.read_bytes() == w.read_bytes()        # filed from this very draft
    return d, ("filed" if h.is_file() and (not w.is_file() or same) else ("draft" if not h.is_file() else "update waiting"))


def load(brand, name, demographic=""):
    """The profile as one object. `parts` always has every key of the standard; each is {"state": "own"|"open", ...}."""
    a, s, d = N.folders(brand, name, "", demographic)
    prof = N.profile(brand, a, s, d)
    card, card_state = _card(brand, a, s)
    slots = W.slots(brand, a, s)
    slots_signed = W.slots_file(brand, a, s).parent.name == "slots"
    parts = {}
    for k in CARD:
        if not s:                                                   # a whole avatar: its card is the avatar's own profile.md, not a person card
            parts["card." + k] = {"state": "n/a"}
            continue
        v = (card or {}).get(k)
        has = bool(v) if not isinstance(v, dict) else bool(v.get("text") or v.get("lines"))
        parts["card." + k] = {"state": "own" if has else "open", "n": len(v) if isinstance(v, list) else (1 if has else 0)}
    for k in SLOT_LISTS:
        v = slots.get(k) or []
        parts["slot." + k] = {"state": "own" if v else "open", "n": len(v)}
    db = slots.get("doubts") or {}
    got = [x for x in DOUBT_KINDS if (db.get(x) or {}).get("said") and (db.get(x) or {}).get("rows")]
    parts["slot.doubts"] = {"state": "own" if len(got) == len(DOUBT_KINDS) else "open", "n": len(got), "of": len(DOUBT_KINDS)}
    parts["slot.awareness"] = {"state": "own" if slots.get("awareness_lead") else "open", "value": slots.get("awareness_lead")}
    parts["slot.stage"] = {"state": "own" if slots.get("stage") else "open"}
    lenses = [dict(v, merged=k) for k, v in N.merges(brand).items() if v["into"] == prof["id"]]
    return {"brand": brand, "id": prof["id"], "lenses": lenses, "label": prof["label"], "avatar": prof["avatar"], "sub": prof["sub"], "demographic": prof["demographic"],
            "old": prof["old"], "named": prof["named"], "folders": {"avatar": a, "sub": s}, "card_state": card_state,
            "slots_state": ("signed" if slots_signed else ("proposed" if slots else "none")),
            "own_lines": (card or {}).get("own_lines", 0), "draft_name": (card or {}).get("name"), "parts": parts,
            "gaps": list(slots.get("gaps") or []) + list((card or {}).get("missing") or []), "card": card, "slots": slots}


def check(brand, name, demographic=""):
    """(fails, notes). A fail breaks the standard; a note says a part is thin or unsigned. Lower levels are allowed, structure is not."""
    p = load(brand, name, demographic)
    fails, notes = [], []
    if not p["named"]:
        fails.append("its avatar or sub-avatar has no PEOPLE.md name yet (the owner signs names)")
    if p["draft_name"] and p["draft_name"] != p["id"]:
        fails.append("the card is filed under %s but its profile name is %s" % (p["draft_name"], p["id"]))
    if p["folders"]["sub"] and p["card_state"] == "none":
        fails.append("no profile card (who.py build)")
    if p["slots_state"] == "none":
        fails.append("no slots (who.py fill)")
    for k, v in p["parts"].items():
        if v["state"] == "open":
            notes.append("%s is open%s" % (k, (": " + _said_open(p, k)) if _said_open(p, k) else ""))
        elif k.startswith("slot.") and k[5:] in THIN and v["n"] < THIN[k[5:]]:
            notes.append("%s is thin (%d)" % (k, v["n"]))
    card = p["card"] or {}
    for k in ("desire", "opening", "doubt"):
        for i in (card.get(k) or {}).get("lines", []):
            if i not in (card.get("lines") or {}):
                fails.append("card.%s cites %s, which is not in its lines" % (k, i))
    for k in ("experiences", "emotions", "behaviors", "culture"):
        for x in card.get(k) or []:
            for i in x.get("lines", []):
                if i.startswith("culture:"):                        # a culture-map point, cited by its own id
                    continue
                if i not in (card.get("lines") or {}):
                    fails.append("card.%s cites %s, which is not in its lines" % (k, i))
    if p["slots_state"] != "none":
        for k, why in (("slot.doubts", "all four doubts, each with its line"), ("slot.awareness", "an awareness level"), ("slot.stage", "a market stage")):
            if p["parts"][k]["state"] == "open":
                fails.append("%s: the standard needs %s" % (k, why))
    if p["slots_state"] == "proposed":
        notes.append("the slots are a proposal, not signed by the owner")
    if p["card_state"] in ("draft", "update waiting"):
        notes.append("the card is a draft, not filed in the brand folder")
    if not p["demographic"]:
        notes.append("no demographic: it is chosen per piece")
    return fails, notes


def _said_open(p, k):
    """The gap that explains an empty part, when the build named one."""
    word = k.split(".", 1)[1]
    for g in p["gaps"]:
        if word.rstrip("s") in g.lower():
            return g[:120]
    return ""


def _listing(brand):
    out, seen = [], set()
    for a in W.avatars(brand):
        for s in [""] + W.subs(brand, a):
            prof = N.profile(brand, a, s)
            if prof["id"] in seen or prof["id"] in N.merges(brand):          # a merged profile is a lens of its keeper, not a profile
                continue
            seen.add(prof["id"])
            out.append(prof["id"] if s or True else a)
    return out


def audit(brand):
    rows = []
    for pid in _listing(brand):
        try:
            p = load(brand, pid)
            fails, notes = check(brand, pid)
        except SystemExit as e:
            rows.append({"id": pid, "error": str(e)})
            continue
        rows.append({"id": p["id"], "label": p["label"], "lenses": [x["lens"] for x in p["lenses"]], "card": p["card_state"], "slots": p["slots_state"], "own_lines": p["own_lines"],
                     "open": sorted(k for k, v in p["parts"].items() if v["state"] == "open"), "fails": fails, "notes": notes,
                     "counts": {k: v.get("n") for k, v in p["parts"].items() if "n" in v}})
    return rows


def rows_of(brand, name):
    """Every customer line a profile stands on, from its slots (desires, roles, beliefs, experiences, behaviors, emotions, doubts)."""
    p = load(brand, name)
    sl = p["slots"] or {}
    out = set()
    for k in SLOT_LISTS:
        for x in sl.get(k) or []:
            out.update(x.get("rows") or [])
    for v in (sl.get("doubts") or {}).values():
        out.update((v or {}).get("rows") or [])
    return out


def siblings(brand, name):
    """The other profiles of the same avatar that are a DIFFERENT sub-avatar (the ones this one must be told apart from). The same
    sub-avatar written for another demographic is the same person in another voice, so it is never a sibling."""
    f = N.folders(brand, name)
    me = N.profile(brand, f[0], f[1])
    out = []
    for pid in _listing(brand):
        g = N.folders(brand, pid)
        if g[0] != f[0] or not g[1]:
            continue
        other = N.profile(brand, g[0], g[1])
        if other["sub"] and other["sub"] != me["sub"]:
            out.append(pid)
    return out


def gate(brand, name):
    """CREATE.md's gates 3 and 4 as numbers. Returns {"own": n, "evidence": bool, "shared": {sibling: share of MY lines also under it}, "holds": [...]}.
    A hold is a question for the owner (merge, keep, or fill more), never an automatic change."""
    min_own, same = criteria(brand)
    mine = rows_of(brand, name)
    own = load(brand, name)["own_lines"] or len(mine)
    shared = {}
    for sid in siblings(brand, name):
        other = rows_of(brand, sid)
        if mine and other:
            shared[sid] = round(len(mine & other) / len(mine), 2)
    holds = []
    if own < min_own:
        holds.append("evidence: %d own lines, the standard is %d before ads are made for it" % (own, min_own))
    for sid, v in sorted(shared.items(), key=lambda kv: -kv[1]):
        if v > same:
            holds.append("same person?: %d%% of its lines also sit under %s" % (round(v * 100), sid))
    return {"own": own, "evidence": own >= min_own, "shared": shared, "holds": holds}


def init(brand):
    """The new-brand checklist: every profile the brand's folders hold and what stands between it and ads (read-only, spends nothing).
    [{"id", "label", "todo": [...]}]. An empty todo means it clears every gate."""
    out = []
    for pid in _listing(brand):
        p = load(brand, pid)
        todo = []
        if not p["named"]:
            todo.append("sign its name (people.py check, then the owner)")
        if p["folders"]["sub"] and p["card_state"] == "none":
            todo.append("build its card (who.py build)")
        if p["slots_state"] == "none":
            todo.append("fill its slots (who.py fill)")
        else:
            todo += ["profiles.py check: " + x for x in check(brand, pid)[0] if "no profile card" not in x]
        if p["slots_state"] != "none":
            todo += ["gate: " + h for h in gate(brand, pid)["holds"]]
        out.append({"id": pid, "label": p["label"], "named": p["named"], "todo": todo})
    return out


_OLD = re.compile(r"add_argument\(\s*['\"]--(avatar|sub|sub-avatar)['\"]")
_DOOR = ("profile_arg", "people.folders", "N.folders", "profile_args", "import profiles", "profiles.load", "avatar_folder(")
# a path to ONE person's folder built from a name: "core-avatars" / avatar, f".../core-avatars/{avatar}", brand_path(.., "core-avatars", avatar).
# Brand-wide files (language index, objection bank, avatars.json, casting) and globs over every avatar are not a person.
_PERSON_PATH = re.compile(r"""core-avatars["']\s*\)?\s*/\s*(?!["'(])[A-Za-z_]|core-avatars/\{|["']core-avatars["']\s*,\s*(?!["'])[A-Za-z_]""")
# flags spelled like a person but meaning something else: swipe-organic's --sub is a culture-dig key (naming/PEOPLE.md, "Not moved")
_NOT_PEOPLE = {"components/swipe-organic/affinity.py", "components/swipe-organic/recomment.py",
               "components/language-layer/language_layer/engine.py"}      # its own --profile is a stage-profile file, so the person flag cannot be --profile


def pick(brand, avatar, product="", seed=""):
    """The profile a send or an ad speaks to, when the plan names only the avatar: one of that avatar's profiles with a
    filed card whose problem the product may be used for (who.fits), the same one every time for the same seed, spread
    across the avatar's profiles as the seed changes. None when the avatar has no such profile: the run speaks to the
    whole avatar, as before."""
    if not avatar or avatar in ("none", "mixed"):
        return None
    try:
        a = N.folders(brand, avatar)[0]
    except SystemExit:
        return None
    pool = []
    for s in W.subs(brand, a):
        if product and W.fits(brand, product, a, s):
            continue
        if _card(brand, a, s)[1] != "filed":
            continue
        try:
            if check(brand, N.profile(brand, a, s)["id"])[0]:                    # a profile that breaks the standard is not written to
                continue
        except SystemExit:
            continue
        pool.append(s)
    if not pool:
        return None
    import hashlib
    s = pool[int(hashlib.sha256(str(seed).encode()).hexdigest(), 16) % len(pool)]
    prof = N.profile(brand, a, s)
    return {"id": prof["id"], "avatar": a, "sub": s, "demographic": prof.get("demographic") or "", "label": prof.get("label")}


def strict(root=None):
    """Every LINE that builds a person's folder path from a name by hand, door or no door in the same file: what must be
    gone before a brand's folders are renamed (naming/tidy_folders.py)."""
    root = Path(root or ROOT)
    out = []
    for f in sorted((root / "components").rglob("*.py")):
        rel = str(f.relative_to(root))
        if "/tests/" in rel or f.name.startswith("test_") or "components/naming" in rel or "components/profiles" in rel:
            continue
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            if _PERSON_PATH.search(line) and "avatar_folder(" not in line:
                out.append({"file": "%s:%d" % (rel, i), "why": line.strip()[:100]})
    return out


def doors(root=None):
    """Tools that take a person by the old avatar/sub flags, or read a brand's avatar folders, without going through the door."""
    root = Path(root or ROOT)
    off = []
    for top in ("components", "platform", "lab", "tools"):
        for f in sorted((root / top).rglob("*.py")) if (root / top).is_dir() else []:
            rel = str(f.relative_to(root))
            if any(x in rel for x in ("__pycache__", "/tests/", "/fixtures/", "worktrees", "/test_")) or f.name.startswith("test_"):
                continue
            try:
                s = f.read_text(errors="ignore")
            except OSError:
                continue
            door = any(x in s for x in _DOOR)
            if rel in _NOT_PEOPLE:
                continue
            if _OLD.search(s) and not door:
                off.append({"file": rel, "why": "takes --avatar/--sub without the profile door"})
            elif not door and "components/profiles" not in rel and "components/naming" not in rel and _PERSON_PATH.search(s):
                off.append({"file": rel, "why": "builds a person's folder path from a name, around the door"})
    return off


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("audit", "check", "show", "gate", "init", "doors", "pick"))
    ap.add_argument("--avatar")
    ap.add_argument("--product", default="")
    ap.add_argument("--seed", default="")
    ap.add_argument("--brand")
    ap.add_argument("--profile")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--strict", action="store_true", help="doors: every line that builds a person's path by hand")
    a = ap.parse_args(argv)
    if a.cmd == "doors":
        off = strict() if a.strict else doors()
        if a.save:
            d = ROOT / "runs" / "profiles" / "_system"
            d.mkdir(parents=True, exist_ok=True)
            (d / "doors.json").write_text(json.dumps(off, indent=1) + "\n")
        for x in off:
            print("%-70s %s" % (x["file"], x["why"]))
        print("%d tools around the door" % len(off))
        return 1 if off else 0
    if not a.brand:
        raise SystemExit("--brand is required")
    if a.cmd == "pick":
        print(json.dumps(pick(a.brand, a.avatar, a.product, a.seed), indent=1))
        return 0
    if a.cmd == "init":
        rows = init(a.brand)
        for r in rows:
            print("%-52s %s" % (r["id"], "ready" if not r["todo"] else "; ".join(r["todo"])))
        print("%d profile(s), %d ready" % (len(rows), sum(1 for r in rows if not r["todo"])))
        return 0
    if a.cmd == "audit":
        rows = audit(a.brand)
        for k, v in sorted(N.merges(a.brand).items()):
            print("%-48s MERGED into %s (lens: %s)" % (k, v["into"], v["lens"]))
        for r in rows:
            if "error" in r:
                print("%-48s ERROR %s" % (r["id"], r["error"]))
                continue
            print("%-48s card %-14s slots %-9s own %-4s open %-2d fails %d" % (r["id"], r["card"], r["slots"], r["own_lines"], len(r["open"]), len(r["fails"])))
        return 1 if any(r.get("fails") or r.get("error") for r in rows) else 0
    if not a.profile:
        raise SystemExit("--profile is required")
    if a.cmd == "check":
        fails, notes = check(a.brand, a.profile)
        for x in fails:
            print("FAIL", x)
        for x in notes:
            print("note", x)
        print("PASS" if not fails else "%d fail(s)" % len(fails))
        return 1 if fails else 0
    if a.cmd == "gate":
        g = gate(a.brand, a.profile)
        print("own lines %d (need %d)" % (g["own"], criteria(a.brand)[0]))
        for sid, v in sorted(g["shared"].items(), key=lambda kv: -kv[1]):
            print("  %3d%% of its lines also under %s" % (round(v * 100), sid))
        for h in g["holds"]:
            print("HOLD", h)
        print("CLEAR" if not g["holds"] else "%d hold(s)" % len(g["holds"]))
        return 1 if g["holds"] else 0
    p = load(a.brand, a.profile)
    p.pop("card"), p.pop("slots")
    print(json.dumps(p, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
