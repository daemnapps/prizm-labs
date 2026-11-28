#!/usr/bin/env python3
"""who — the one read of who an ad is for and what it must say to them. Every chain that writes calls it (public surface).

    import who
    who.block(brand, avatar, sub=None, demographic=None, what=None)   the text a writing step is handed
    who.stamp(brand, avatar, sub=None, demographic=None, what=None)   the same decisions as data, for the run's record
    who.resolve(brand, avatar, sub)                                   (id, card, profile, language folders): id or file name
    who.MARK                                                          the line a check looks for in a sent prompt

    python3 machine/who.py show --brand <b> --avatar <a> [--sub <s>] [--demographic male/25-34/black]
    python3 machine/who.py build --brand <b> --avatar <a> [--sub <s>] [--cap 2 --go "<owner's words>"]   start to finish; no --sub: every one
    python3 machine/who.py profile --brand <b> --avatar <a> --sub <s>      one person, written from their own lines, checked; a draft until the owner's yes files it in the brand folder
    python3 machine/who.py full --brand <b> --avatar <a> --sub <s> --demographic male-35-44-black      the full profile: person + look + message, joined now
    python3 machine/who.py fill --brand <b> --avatar <a> [--sub <s>] [--dry-run]     the deep slots, from customer rows
    python3 machine/who.py status [--brand <b>]                                      which slots are filled, per avatar

The definitions live once: components/GLOSSARY.md (avatar, sub-avatar, demographic) and components/marketing-doctrine
(desire, awareness, market stage, doubt, claim). This file holds none of them and names no brand.

`what` is what the chain already decided: desire, awareness, stage, doubt, claim. Anything missing is taken from the
avatar's filled slots, else said to be open. Filled slots: the brand's own core-avatars/<avatar>/slots.json once the
owner has signed it, else the proposal under runs/creative-strategist/<brand>/who/. Nothing is written to brands/.
"""
import argparse
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import strategy as S                                                                                       # noqa: E402
sys.path.append(str(HERE.parents[1] / "naming"))
import people as N                                                                                         # noqa: E402
import anatomy as A                                                                                        # noqa: E402
import body as BODY                                                                                        # noqa: E402

MARK = "## WHO THIS AD IS FOR, AND WHAT IT MUST SAY"
END = "## END OF WHO THIS AD IS FOR"
DOUBTS = ("does-it-work", "for-me", "worth-it", "trust-you")
LEVELS = ("unaware", "problem-aware", "solution-aware", "product-aware", "most-aware")
_ROWS = {}


def doctrine():
    return json.loads((S.DOCTRINE.parent / "frameworks.json").read_text())


def avatar_dir(brand, avatar):
    avatar = N.canon(brand, avatar)[0]                              # any spelling of the avatar, or a profile's
    return S.brandpath.brand_path(brand, "core-avatars", avatar, root=S.root() / "brands")


def profile_args(brand, profile="", avatar="", sub="", demographic=""):
    """What every tool takes a person by: (avatar, sub, demographic) as the folders spell them, from a PROFILE
    (`--profile razor-bumps_tried-everything[_male-35-44-black]`) or the older avatar/sub pair (PEOPLE.md)."""
    a, s, d = N.folders(brand, profile or avatar, sub, demographic)
    return a, s, d or demographic


def avatars(brand):
    d = S.brandpath.brand_path(brand, "core-avatars", root=S.root() / "brands")
    return sorted(p.parent.name for p in d.glob("*/profile.md"))


def subs(brand, avatar):
    d = avatar_dir(brand, avatar) / "sub-avatars"
    return [re.sub(r"^sub-\d+-", "", p.stem) for p in sorted(d.glob("*.md"))]


def resolve(brand, avatar, sub):
    """(id, card, profile, [language folders]) from a sub-avatar's id or its file name; ("", None, None, []) for none."""
    avatar, sub = N.canon(brand, avatar, re.sub(r"^sub-\d+-", "", str(sub or "").strip()))
    key = sub
    if not key or key in ("none", "core", "null"):
        return "", None, None, []
    card, prof = S.sub_files(brand, avatar, key)
    if not card:
        raise SystemExit("no sub-avatar %s under %s/%s: %s" % (sub, brand, avatar, ", ".join(subs(brand, avatar)) or "it has none"))
    homes = [p for p in (card.parent / card.stem / "language", card.parent / key / "language") if p.is_dir()]
    return key, card, prof, homes


def field(text, name):
    m = re.search(r"^- \*\*" + name + r"[^*]*\*\*:?\s*(.+)$", text, re.M | re.I)
    return re.sub(r"\*\*", "", m.group(1)).strip() if m else ""


def section(text, name):
    m = re.search(r"^### " + re.escape(name) + r"\b.*?$(.*?)(?=^### |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def slots_file(brand, avatar, sub=""):
    """The signed slots in the brand when they exist, else the proposal under runs/."""
    name = (sub or "avatar") + ".json"
    d = S.root() / "runs" / "creative-strategist" / brand / "who" / avatar
    signed = avatar_dir(brand, avatar) / "slots" / name
    return signed if signed.is_file() else d / name


def slots(brand, avatar, sub=""):
    f = slots_file(brand, avatar, sub)
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        return {}
    return _row_ids_now(brand, d)


def _row_ids_now(brand, d):
    """A slot written before the folders were renamed cites another avatar's line as `<old avatar>:<id>`; the bank now
    keys it by the avatar's folder. Every cited id is read as the bank keys it."""
    def fix(i):
        if not isinstance(i, str) or ":" not in i:
            return i
        a, _, rest = i.partition(":")
        return "%s:%s" % (N.canon(brand, a)[0], rest)

    def walk(x):
        if isinstance(x, dict):
            return {k: ([fix(i) for i in v] if k == "rows" and isinstance(v, list) else walk(v)) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        return x
    return walk(d)


def datasets(brand, avatar):
    """Every file this avatar's lines come from, newest state included: the brand's own banks and the research pulls."""
    d = avatar_dir(brand, avatar)
    fs = [f for f in sorted((d / "language").glob("**/*.json")) if "used" not in f.relative_to(d).parts] + sorted((d / "sub-avatars").glob("*/language/**/*.json"))
    fs += sorted(f for f in (S.root() / "runs" / "research" / brand).glob("person-*/rows.json") if _avatar_of(f) == avatar)
    return fs


def answers(brand, avatar):
    """The files of the brand's other people that hold answers to the brand (customers, leads, people who left)."""
    out = []
    for a in avatars(brand):
        if a != avatar:
            d = avatar_dir(brand, a) / "language"
            out += sorted(d.glob("customers/**/*.json")) + sorted(d.glob("churned/**/*.json")) + [f for f in (d / "leads.json",) if f.is_file()]
    return out


def _avatar_of(f):
    try:
        return json.loads(f.read_text()).get("avatar")
    except (OSError, ValueError):
        return None


def research_rows(brand, avatar, every=False):
    """Lines the research component has pulled for this avatar (runs/research/<brand>/person-*/rows.json), same shape as the
    bank. A pull brings strangers too: only lines a profile's sort has read as this person's count, unless `every`."""
    out = {}
    for f in (S.root() / "runs" / "research" / brand).glob("person-*/rows.json"):
        try:
            d = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if d.get("avatar") == avatar:
            for e in d.get("entries") or []:
                if not every and not e.get("his"):
                    continue
                out[e["id"]] = {"text": e["text"], "sub": e.get("sub"), "awareness": None, "use": e.get("use"), "source": (e.get("source") or {}).get("name", ""), "ref": (e.get("source") or {}).get("ref")}
    return out


SAID = ("customer_", "lead_", "churned_")                    # people answering the brand itself, filed under whichever avatar was first


def bank(brand, avatar):
    k = (brand, avatar)
    if k not in _ROWS:
        rows = dict(S.bank(brand, avatar))
        rows.update(research_rows(brand, avatar))
        for a in avatars(brand):             # a customer answers the brand, not a folder: everyone's answers, ranked by this person's own problem
            if a != avatar:
                every = S.bank(brand, a)
                rows.update({"%s:%s" % (a, i): dict(r, sub=None) for i, r in every.items() if len(rows) < 60 or i.startswith(SAID)})
        _ROWS[k] = rows
    return _ROWS[k]


def desire_of(text):
    """The person's want, in the words the file states it: the Core desire slot, else its first "I want"."""
    m = re.search(r'["“](I (?:want|need) [^"”]{10,})["”]', text, re.S)
    one = " ".join((m.group(1) if m else field(text, "Core desire")).split())
    return one


def problem_words(brand, avatar, sub):
    key, card, _, _ = resolve(brand, avatar, sub)
    prof = S.text_of(avatar_dir(brand, avatar) / "profile.md")
    t = S.text_of(card) if card else ""
    mine = " ".join([field(t, n) for n in ("Who", "Core desire", "Pain", "One-line story")] + re.findall(r'^\s+- ["“](.+?)["”]', t, re.M))
    if card and not mine.strip():
        mine = t[:1800]
    if mine.strip():
        return mine
    d = re.search(r"^#+ .*desire.*?$(.*?)(?=^#|^\*\*\d\.|\Z)", prof, re.M | re.S | re.I)
    return " ".join([desire_of(prof), field(prof, "Problem"), (d.group(1)[:1500] if d else ""), " ".join(re.findall(r'["“]([^"”]{12,160})["”]', prof)[:14])])


def his_rows(brand, avatar, sub, n=24):
    rows = bank(brand, avatar)
    # about the problem first: a row filed under this sub-avatar only because its research found it is not about it
    about = problem_words(brand, avatar, sub)
    ids = S.rank(rows, about, "", limit=400)
    keep = {w for w in S.words(about) if sum(1 for r in rows.values() if w in r["text"].lower()) <= max(6, len(rows) * .18)}
    two = [i for i in ids if len(keep & set(S.words(rows[i]["text"]))) >= 2]
    cited = []                                        # the rows a filled slot stands on were read as about this person
    for s in ([slots(brand, avatar, sub)] if sub else []) + [slots(brand, avatar)]:
        for x in [x for k in ("desires", "emotions", "beliefs", "roles") for x in s.get(k) or []] + list((s.get("doubts") or {}).values()):
            cited += [i for i in x.get("rows") or [] if i in rows and i not in cited and len(rows[i]["text"]) <= 320]
        cited = cited[:n // 2]
    mine = [i for i in two if sub and rows[i]["sub"] == sub and i not in cited][:n // 3]
    got = cited + mine + [i for i in two if i not in mine and i not in cited]
    if len(got) < n // 2:
        got += [i for i in ids if i not in got and len(rows[i]["text"]) >= 25][:n // 2 - len(got)]
    return rows, got[:n]


def objections(brand, avatar):
    d = S.brandpath.brand_path(brand, "core-avatars", root=S.root() / "brands")
    t = S.text_of(d / "objection-bank.md")
    if not t:
        return ""
    t = re.sub(r"\A---\n.*?\n---\n", "", t, flags=re.S)
    known = lambda a: [a] + N.older(brand, a)                    # the bank may head a part with a name the folder had before
    names = [x for a in known(avatar) for x in (a, a.replace("-", " "))]
    others = [x for o in avatars(brand) if o != avatar for a in known(o) for x in (a, a.replace("-", " "))]
    parts = re.split(r"^(?=#{1,2} )", t, flags=re.M)
    hit = [k for k, p in enumerate(parts) if any(n in p.split("\n", 1)[0].lower() for n in names)]
    if hit:
        out = []
        for k in hit:
            out.append(parts[k])
            for p in parts[k + 1:]:
                if any(a in p.split("\n", 1)[0].lower() for a in others):
                    break
                out.append(p)
        t = "".join(out)
    elif not any(n in t[:900].lower() for n in names):      # the bank is another person's: never lend one avatar's doubts to another
        return ""
    quotes = re.findall(r"^(?:#{3,4} .+|[-*] .+)$", t, re.M)
    return "\n".join(quotes)


# a person's race or who owns the company is the demographic's or nobody's: never a role, belief or habit handed to a writer
OWNED = re.compile(r"\b(black|white|latin[oa]|hispanic|asian)\b[^;]{0,12}\b(man|men|woman|women|person|people)\b|\b(men|women|people) of colou?r\b|-owned\b|started by a\b", re.I)
SAME = {"latino": ("spanish", "hispanic", "bicultural"), "hispanic": ("spanish", "latino", "bicultural")}      # one people, two words


def mine_line(x, mine, names, demo):
    """A line of a shared section that belongs to somebody else: labelled for another sub-avatar, or in a language this person is not being spoken to in."""
    m = re.match(r"\*\*([a-z0-9 -]+):\*\*", x.strip(), re.I)
    if m and re.sub(r"[^a-z]+", " ", m.group(1).lower()).strip() in names - {mine}:
        return False
    if "different context" in x:                  # the map's own note that a line is not about this person
        return False
    spanish = len(re.findall(r"\b(te|lo|que|por|en|si|ver|solo|ti|una|para|como|mi|los|las|el|ruego)\b", " ".join(re.findall(r'["“]([^"”]+)["”]', x)).lower()))
    return spanish < 4 or bool(demo & {"latino", "hispanic", "spanish"})


def culture(brand, avatar, sub="", demographic=""):
    """The person's world, from the avatar's culture map: what everyone in it shares, plus the named sub-avatar's and
    demographic's own part. Receipts stay in the map; another sub-avatar's part is never handed over."""
    t = S.text_of(avatar_dir(brand, avatar) / "culture-map.md")
    if not t:
        return ""
    def as_written(x):                     # a map written before the folders were renamed heads a part with the older name
        for o in N.older(brand, avatar, x) if x else []:
            if o in t:
                return o
        return x
    names = {re.sub(r"[^a-z]+", " ", as_written(x).lower()).strip() for x in subs(brand, avatar)}
    mine = re.sub(r"[^a-z]+", " ", as_written(sub or "").lower()).strip()
    # a demographic's words are matched, never its age band's digits
    demo = {w for w in re.findall(r"[a-z]{4,}", (demographic or "").lower())} - {"male", "female"}
    demo |= {a for w in demo for a in SAME.get(w, ())}
    out = []
    for title, n in (("What they watch and listen to", 6), ("Who they trust", 4), ("References and slang", 8), ("What they care about", 6), ("What they laugh at", 5),
                     ("What moves them that isn't a joke", 4), ("Off-limits", 12)):
        m = re.search(r"^## " + re.escape(title) + r"\s*$(.*?)(?=^## |\Z)", t, re.M | re.S)
        if not m:
            continue
        got = []
        for k, part in enumerate(re.split(r"^### ", m.group(1), flags=re.M)):
            head = re.sub(r"[^a-z]+", " ", part.split("\n", 1)[0].lower()).strip() if k else ""
            owner = next((x for x in names if x and x in head), "") or next((x for x in names if head and head.split(" ")[0] == x.split(" ")[0]), "")
            his = bool(mine and mine == owner) or bool(demo & set(head.split()))
            if owner and not his:
                continue
            for other in ("spanish", "hispanic", "latino"):
                if other in head.split() and not his:
                    break
            else:
                lines = re.findall(r"^[-*] (.+)$", part, re.M)
                lines = [re.sub(r"\s*\[(?!name)[^\]]*\]", "", x).strip() for x in lines if mine_line(x, mine, names, demo)]
                got = (lines[:n] + got) if his else (got + lines[:n])
        if got:
            cap = n + (4 if mine or demo else 0)
            out += ["- **%s:** %s" % (title, " | ".join(x[:170] for x in got[:cap]))]
    return "\n".join(out)


def body_parts(brand, want="yes"):
    """{product: [part]} marked `want` (yes or no): components/naming/body.py, the one door."""
    return {k: BODY.parts(brand, k, want, S.root()) for k in BODY.load(brand, S.root())}


def where_of(brand, avatar, sub):
    """The body part a person is about, when their one thing is a place (`where-<part>`); "" otherwise."""
    ns = N.new_names(brand, avatar, sub or "")[1]
    return ns[len("where-"):] if ns.startswith("where-") else ""


def fits(brand, product, avatar, sub):
    """None when the product may be used where this person's problem is, or the person is about no place; else the reason it may not."""
    return BODY.why_not(brand, product, where_of(brand, avatar, sub), S.root())


def must_fit(brand, product, avatar, sub):
    """A product is never written for a place it is ruled out for: the run stops here and says so."""
    bad = fits(brand, product, avatar, sub) if product else None
    if bad:
        raise SystemExit("refused: %s. Pick another product or another person, or change the Body Map." % bad)


def spot(brand, avatar, sub, product=""):
    """The place as data: the part, what is true of it, how people say it, and which products may be used there."""
    w = where_of(brand, avatar, sub)
    if not w:
        return {}
    fit = {k: BODY.why_not(brand, k, w, S.root()) for k in BODY.load(brand, S.root())}
    return {"part": w, "true": place(brand, avatar, sub), "said_as": A.phrases(w), "goes_with": A.together(w) if not product else BODY.together(brand, product, w, S.root()), "products_yes": sorted(k for k, v in fit.items() if not v),
            "products_no": sorted(k for k, v in fit.items() if v), "product": product or None}


def body_lines(brand, avatar, sub, product=""):
    """What a writing step reads about the body: the one place this person is about, and only the product in this piece."""
    sp = spot(brand, avatar, sub, product)
    out = []
    if sp:
        out += ["", "**The place, true of anyone:** " + sp["true"], "- People call it: " + ", ".join(sp["said_as"][:8])]
        if product and BODY.members(brand, product, S.root()):
            out += ["- " + BODY.rule(brand, product, sp["part"], S.root())]
        elif sp["products_yes"] or sp["products_no"]:
            out += ["- Places close by may be mentioned with it: " + ", ".join(x.replace("-", " ") for x in sp["goes_with"])]
            out += ["- May be used there: %s. Never there: %s" % (", ".join(sp["products_yes"]) or "none", ", ".join(sp["products_no"]) or "none")]
    elif product and BODY.rule(brand, product, "", S.root()):
        out += ["", "**Where this product goes (nowhere else is shown or claimed):** " + BODY.rule(brand, product, "", S.root())]
    return out


def place(brand, avatar, sub):
    """What is simply true of the place this person is about: a writer may lean on it, and it needs no customer line."""
    ps = [A.parts()[x] for x in A.open_(where_of(brand, avatar, sub))]
    if not ps:
        return ""
    say = lambda p: "%s: %s" % (p["name"].lower(), ", ".join(x for x in ("coarse hair grows there" if p["hair"] else "", "often shaved" if p["shaved"] == "often" else "",      # noqa: E731
                                                                          "cannot be seen without a mirror or someone else" if not p["sees"] else "", "covered by clothes" if p["covered"] == "yes" else "") if x) or "open skin")
    return "; ".join(say(p) for p in ps[:6])


def taken_board(brand, who):
    """What is running and being made, so this ad is a new one to the platform (creative-diversity creative_plan.py). "" when it cannot be read."""
    if S.root() != Path(__file__).resolve().parents[3]:
        return ""                                            # a made-up workspace has no plan
    p = str(HERE.parents[1] / "creative-diversity")
    if p not in sys.path:
        sys.path.append(p)
    try:
        import creative_plan as PL
        return PL.board(brand, who)
    except Exception as e:                                   # noqa: BLE001 -- the board never costs a run
        print("  what is already taken could not be read (%s: %s)" % (type(e).__name__, str(e)[:100]))
        return ""


def mechanics():
    """The measured conversion mechanics, one line each, and the gates they cite (marketing-doctrine mechanics.json).
    The lab-only and unproven ones are tests with a holdout and are never handed to a writer here."""
    try:
        m = json.loads((S.DOCTRINE.parent / "mechanics.json").read_text())
    except (OSError, ValueError):
        return ""
    rows, used = [], {"subscription", "chance"}
    for r in m["mechanics"]:
        if r["tier"] != "measured":
            continue
        moves = ["%s: %s" % (k, r[k]) for k in ("ad", "email", "page") if r.get(k) and not r[k].lower().startswith("no move")]
        if moves:
            rows += ["- `%s` %s %s" % (r["id"], r["does"], " ".join(moves))]
            used |= set(r["gates"])
    gates = ["- `%s` %s Pass: %s" % (g["id"], g["ask"], g["pass"]) for g in m["gates"] if g["id"] in used]
    return "\n".join(rows + ["", "Every one that is used passes these, yes or no:", ""] + gates)


def decide(brand, avatar, sub="", what=None):
    """desire, awareness, stage, doubt, claim: what the chain decided, else what the filled slots lead with."""
    w = {k: v for k, v in (what or {}).items() if v}
    for s in ([slots(brand, avatar, sub)] if sub else []) + [slots(brand, avatar)]:
        if not s:
            continue
        if not w.get("desire") and s.get("desires"):
            x = s["desires"][0]
            w["desire"] = "%s (%s)" % (x.get("want", ""), ", ".join(x.get("human") or []))
        if not w.get("awareness") and s.get("awareness_lead"):
            w["awareness"] = s["awareness_lead"]
        if not w.get("stage") and s.get("stage"):
            w["stage"] = s["stage"]
        if not w.get("doubt") and s.get("doubt_lead"):
            w["doubt"] = s["doubt_lead"]
    return w


def name(brand, avatar, sub="", demographic=""):
    """The one name of a profile: avatar_sub-avatar_demographic (components/naming/PEOPLE.md)."""
    return N.profile(brand, avatar, sub or "", demographic or "")["id"]          # a sub-avatar signed as a demographic is named as one (2026-11-27)


def looks(brand, avatar, sub="", demographic=""):
    """What they look like and how they sound: the demographic, what the problem shows on them, and who is cast for it."""
    d = N.demographic(demographic or "")
    ct = S.text_of(resolve(brand, avatar, sub)[1] or "")
    out = []
    if d:
        who_ = "%s, %s, %s" % (d["gender"], d["age"], d["ethnicity"]) + ((", speaks " + d["language"]) if d["language"] else "")
        out += ["- **Who:** " + who_ + ". Everyone on screen in this piece is this."]
    m = re.search(r"Casting:\s*(.+)", ct)
    if m:                                    # what the problem looks like on them; the race and age in an old card are the demographic's job
        shown = re.sub(r"\b(black|white|latin[oa]|afro-latino/latino|hispanic|asian)\b\s*", "", re.sub(r"\b(early|mid|late)[- ]?(teens|\d0s)(\s*[–-]\s*(early|mid|late)?\s*\d0s)?|~?\d\d[–-]\d\d|~\d\d", "", m.group(1)), flags=re.I)
        out += ["- **What shows:** " + re.sub(r"\s+", " ", re.sub(r"^[\s,]*(man|woman|teen)?[\s,]*", "", shown)).strip()]
    fit = [c["id"] for c in cast(brand, demographic)]
    if d:
        out += ["- **Cast on file:** " + (", ".join(fit[:6]) + (" and %d more" % (len(fit) - 6) if len(fit) > 6 else "") if fit else "nobody yet")]
    return "\n".join(out)


def no_never(brand, text):
    """A card line without the parts the brand has said it never says."""
    bad = {w for x in S.never_list(S.text_of(S.brandpath.brand_path(brand, "brand-identity", "position.md", root=S.root() / "brands"))) for w in S.words(x) if len(w) > 6}
    return re.sub(r"\s+", " ", " ".join(p for p in re.split(r"(?<=[.;])\s+", text) if not bad & set(S.words(p))) or text).strip()


def who_line(brand, avatar):
    g = "female" if re.search(r"^gender:\s*(female|women)", section(S.text_of(avatar_dir(brand, avatar) / "profile.md"), "demographics"), re.M | re.I) else "male"
    return g, {"male": "a man", "female": "a woman"}[g]


def write_profile(brand, avatar, sub, caller=None, tries=2):
    """One person's profile, written in the method's order from their own lines, checked line by line, read cold.
    Returns (markdown, data). Nothing is pasted from the avatar; what no line shows is a research question."""
    avatar, _ = N.canon(brand, avatar)
    key, card, _, _ = resolve(brand, avatar, sub)
    ct = S.text_of(card)
    gender, person = who_line(brand, avatar)
    na, ns = N.new_names(brand, avatar, key)
    thing = "%s (%s)" % (ns.replace("-", " "), no_never(brand, field(ct, "Pain") or desire_of(ct)))
    pulled = research_rows(brand, avatar, every=True)
    rows = dict(bank(brand, avatar), **{i: r for i, r in pulled.items() if r["sub"] == key})
    words_ = set(S.words(ns.replace("-", " ") + " " + field(ct, "Core desire") + " " + field(ct, "One-line story") + " " + section(ct, "language-delta")[:600]))
    ids = S.rank(rows, problem_words(brand, avatar, key), "", limit=420)
    ids += [i for i, r in rows.items() if i not in ids and (r["sub"] == key or len(words_ & set(S.words(r["text"]))) >= 2) and 10 <= len(r["text"]) <= 700][:500]
    listed = lambda xs: "\n".join('[%s] "%s"' % (i, rows[i]["text"]) for i in xs) or "none"                                # noqa: E731

    def ask(stem, **v):
        p = S.live_prompt(stem).read_text()
        for k, x in v.items():
            p = p.replace("{" + k + "}", x)
        return S.parse(S.ask_model(p, caller=caller))
    got = ask("profile-sort", who=person, thing=thing, rows=listed(ids))
    own, asks = [i for i in got.get("his") or [] if i in rows], [i for i in got.get("asks") or [] if i in rows]
    mark_his(brand, avatar, key, set(own) | set(asks))
    shared = [i for i in S.rank(bank(brand, avatar), problem_words(brand, avatar, ""), "", limit=160) if i not in own and i not in asks][:60]
    world = culture(brand, avatar, key)
    base = S.live_prompt("profile").read_text()
    for k, x in {"who": person, "thing": thing, "gender": gender, "own": listed(own), "asks": listed(asks), "shared": listed(shared), "culture": world or "none"}.items():
        base = base.replace("{" + k + "}", x)
    note, d, dropped = "", {}, []
    for _ in range(tries):
        d = S.parse(S.ask_model(base + note, caller=caller))
        d, dropped = keep(d, set(own), set(asks), set(shared))
        bad = ask("profile-check", who=person, thing=thing, profile=json.dumps({k: v for k, v in d.items() if k != "missing"}, ensure_ascii=False, indent=1)).get("bad") or []
        if not bad and not dropped:
            break
        note = "\n\n---\n\nYOUR LAST ANSWER WAS HELD. Fix only these and answer in full again; an entry that cannot be fixed is removed and its question goes in `missing`:\n" + "\n".join(
            "- %s: %s" % (b.get("text", "")[:120], b.get("why", "")) for b in bad) + "".join("\n- " + x for x in dropped)
    words_bad = [S.norm(b.get("text", "")) for b in bad]
    for k in ("experiences", "emotions", "behaviors", "culture"):
        d[k] = [x for x in d.get(k) or [] if S.norm(x["text"]) not in words_bad]
    d.update({"name": name(brand, avatar, key), "own_lines": len(own), "asks": len(asks)})
    return "", d


def mark_his(brand, avatar, key, ids):
    """What the sort read as this person's, kept on the pulled lines themselves so every reader sees the same answer."""
    for f in (S.root() / "runs" / "research" / brand).glob("person-%s-*/rows.json" % key):
        d = json.loads(f.read_text())
        if d.get("avatar") == avatar:
            for e in d["entries"]:
                e["his"] = e["id"] in ids
            f.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    _ROWS.pop((brand, avatar), None)


def keep(d, own, asks, shared):
    """Only entries whose lines exist; `own` is what the line says it is, not what the writer called it."""
    out, dropped = {}, []

    def ok(x):
        x["lines"] = [i for i in x.get("lines") or [] if i in own or i in asks or i in shared]
        x["from"] = "own" if any(i in own or i in asks for i in x["lines"]) else "shared"
        return bool(x["lines"])
    for k in ("desire", "opening", "doubt"):
        x = d.get(k) or {}
        out[k] = x if x.get("text") and ok(x) else None
        if x.get("text") and not out[k]:
            dropped.append("%s stands on no line" % k)
    for k in ("experiences", "emotions", "behaviors", "culture"):
        out[k] = []
        for x in d.get(k) or []:
            if k == "culture" and x.get("text"):
                x["lines"], x["from"] = x.get("lines") or [], x.get("from") or "shared"
                out[k].append(x)
            elif x.get("text") and ok(x):
                out[k].append(x)
            else:
                dropped.append("%s: %s stands on no line" % (k, str(x.get("text"))[:80]))
    out["missing"] = d.get("missing") or []
    return out, dropped


def where(brand, avatar):
    """line id -> the dataset file it lives in (repo-relative), read now."""
    out, pre = {}, "language_%s_%s_" % (brand, avatar)
    for f, p in [(f, pre) for f in datasets(brand, avatar)] + [(f, None) for f in answers(brand, avatar)]:
        try:
            for e in json.loads(f.read_text()).get("entries") or []:
                i = str(e.get("id", ""))
                if p is None:
                    m = re.match(r"language_%s_(.+?)_((?:customer|lead|churned)_.+)$" % re.escape(brand), i)
                    i = "%s:%s" % m.groups() if m else i
                out[re.sub(r"^language_%s_[^_]+_" % re.escape(brand), "", i) if p else i] = str(f.relative_to(S.root()))
        except (OSError, ValueError, AttributeError):
            continue
    return out


def fingerprint(brand, avatar, key=""):
    """What a profile was built from: changes when any dataset, card, profile or cast file it reads changes."""
    import hashlib
    _, card, _, _ = resolve(brand, avatar, key) if key else ("", None, None, [])
    fs = datasets(brand, avatar) + [avatar_dir(brand, avatar) / "profile.md", avatar_dir(brand, avatar) / "culture-map.md", card, cast_file(brand)]
    h = hashlib.sha256()
    for f in fs:
        if f and Path(f).is_file():
            h.update(Path(f).read_bytes())
    return h.hexdigest()[:16]


def cast_file(brand):
    return S.brandpath.brand_path(brand, "ai-elements", "characters", "casting", "cards-v6.json", root=S.root() / "brands")


def cast(brand, demographic):
    """Everyone cast who matches a demographic, read live: the cards plus the cast the machine has made."""
    d = N.demographic(demographic or "")
    if not d:
        return []
    try:
        cards = json.loads(cast_file(brand).read_text()).get("cards") or []
    except (OSError, ValueError, AttributeError):
        cards = []
    out = [{"id": c["id"], "kind": c.get("kind") or "card"} for c in cards if (c.get("gender"), c.get("age-band"), c.get("ethnic-appearance")) == (d["gender"], d["age"], d["ethnicity"])]
    have = {c["id"] for c in cards}
    for f in sorted((S.root() / "runs" / "ai-elements" / brand / "casting").glob("*/spec.json")):      # everyone made since the cards were written
        try:
            x = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if f.parent.name not in have and read_person(str(x.get("who") or "")) == (d["gender"], d["age"], d["ethnicity"]):
            out.append({"id": f.parent.name, "kind": "made"})
    return out


def read_person(text):
    """(gender, age band, ethnicity) a cast description states in words; None where it does not say."""
    t = text.lower()
    g = "female" if re.search(r"\b(woman|girl|mother|grandmother|lady|female)\b", t) else ("male" if re.search(r"\b(man|guy|boy|father|male|brother)\b", t) else None)
    m = re.search(r"\b(?:about|age[d]?|~)?\s*(\d\d)(?:s\b|[- ]year|\b)", t)
    words_ = {"twenties": 25, "thirties": 35, "forties": 45, "fifties": 55, "sixties": 65, "seventies": 75}
    n = int(m.group(1)) if m and 18 <= int(m.group(1)) <= 90 else next((v for k, v in words_.items() if k in t), None)
    band = next((b for b, lo, hi in (("18-24", 18, 24), ("25-34", 25, 34), ("35-44", 35, 44), ("45-54", 45, 54), ("55-64", 55, 64), ("65-plus", 65, 99)) if n and lo <= n <= hi), None)
    e = next((k for k, p in (("latino", r"latin|hispanic|mexican|dominican|puerto"), ("black", r"\bblack (american |)(man|woman|guy|girl)|african|deep brown skin|dark brown skin"), ("south-asian", r"south asian|indian"), ("east-asian", r"east asian|korean|chinese|japanese"),
                             ("middle-eastern", r"middle eastern|arab"), ("mixed", r"\bmixed\b"), ("white", r"\bwhite (american |)(man|woman|guy)|fair skin|caucasian")) if re.search(p, t)), None)
    return g, band, e


def profiles_dir(brand):
    """Where a person is written before the owner has seen it, and the index of all of them."""
    return S.root() / "runs" / "creative-strategist" / brand / "profiles"


def home(brand, avatar, sub):
    """A person's one home: the sub-avatar's own folder in the brand (the 2026-09-18 one-home rule). Nothing here writes it:
    a draft is shown to the owner, and their yes files it."""
    avatar, _ = N.canon(brand, avatar)
    key, card, _, _ = resolve(brand, avatar, sub)
    return card.parent / card.stem / "profile.json"


def draft(brand, avatar, sub):
    avatar, _ = N.canon(brand, avatar)
    return profiles_dir(brand) / (name(brand, avatar, resolve(brand, avatar, sub)[0]) + ".json")


def unknowns(brand, avatar, sub):
    """(who this is, what the profile does not know yet, lines already theirs): what the research component searches for."""
    avatar, _ = N.canon(brand, avatar)
    key, card, _, _ = resolve(brand, avatar, sub)
    ct = S.text_of(card) if card else ""
    ns = N.new_names(brand, avatar, key)
    person = "%s. The one thing: %s. %s" % (desire_of(S.text_of(avatar_dir(brand, avatar) / "profile.md")), ns[1].replace("-", " "), no_never(brand, field(ct, "Pain") or desire_of(ct)))
    sp = spot(brand, avatar, key)
    if sp:
        person += " It is about one place on the body: the %s. People call it: %s." % (sp["part"].replace("-", " "), ", ".join(sp["said_as"])) + (" Close by, and often said with it: %s." % ", ".join(x.replace("-", " ") for x in sp["goes_with"]) if sp["goes_with"] else "")
    d = filed(brand, avatar, key, newest=True)
    if d:
        rows = bank(brand, avatar)
        mine = [i for x in d.get("experiences", []) + d.get("emotions", []) + d.get("behaviors", []) for i in x.get("lines", [])]
        return person, d.get("missing") or [], [rows[i]["text"] for i in dict.fromkeys(mine) if i in rows]
    return person, [], []


def index(brand):
    """The database of people: one row each, where it stands and whether its sources have moved on since it was written."""
    out = []
    for a in avatars(brand):
        for sub in subs(brand, a):
            h, w = home(brand, a, sub), draft(brand, a, sub)
            d = filed(brand, a, sub, newest=True)
            if not d:
                continue
            state = "in the brand folder" if h.is_file() and not w.is_file() else ("waiting for the owner" if not h.is_file() else "update waiting for the owner")
            out.append({"name": d["name"], "avatar": a, "sub": sub, "state": state, "own_lines": d["own_lines"], "unknown": len(d.get("missing") or []), "built": d.get("built"),
                        "stale": fingerprint(brand, a, sub) != d.get("built_from"), "file": str((h if h.is_file() else w).relative_to(S.root()))})
    if out:
        profiles_dir(brand).mkdir(parents=True, exist_ok=True)
        (profiles_dir(brand) / "index.json").write_text(json.dumps({"brand": brand, "people": out}, indent=1, ensure_ascii=False) + "\n")
    return out


def file_profile(brand, avatar, sub, demographic="", caller=None):
    """Write or refresh one person as a draft: the data (.json, the truth) and the page a person reads (.md)."""
    _, d = write_profile(brand, avatar, sub, caller=caller)
    av, _ = N.canon(brand, avatar)
    key = resolve(brand, av, sub)[0]
    w = where(brand, av)
    used = []
    for x in [d["desire"], d["doubt"], d["opening"]] + d["experiences"] + d["emotions"] + d["behaviors"] + d["culture"]:
        used += [i for i in (x or {}).get("lines", []) if i not in used]
    d.update({"brand": brand, "avatar": av, "sub": key, "built": datetime.date.today().isoformat(), "built_from": fingerprint(brand, av, key),
              "lines": {i: {"text": bank(brand, av)[i]["text"], "dataset": w.get(i)} for i in used if i in bank(brand, av)},
              "reads": {"datasets": sorted(set(w.values())), "card": str(resolve(brand, av, key)[1].relative_to(S.root())),
                        "culture": str((avatar_dir(brand, av) / "culture-map.md").relative_to(S.root())), "doctrine": "components/marketing-doctrine/slices"}})
    f = draft(brand, av, key)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    t = person_page(d)
    f.with_suffix(".md").write_text(t)
    index(brand)
    return f, t


def title(brand, avatar, sub="", demographic=""):
    say = lambda x: x.replace("-", " ").title()                                                                           # noqa: E731
    na, ns = N.new_names(brand, avatar, sub or "")
    kind, thing = (ns.split("-", 1) + [""])[:2] if ns else ("", "")
    d = N.demographic(demographic or "")
    return " · ".join(x for x in (say(na), ("%s: %s" % (kind.title(), thing.replace("-", " "))) if thing else say(ns or ""),
                                  ("%s %s, %s" % (d["ethnicity"].title(), {"male": "man", "female": "woman"}[d["gender"]], d["age"])) if d else "") if x)


def person_page(d):
    mark = lambda x: "" if x.get("from") == "own" else "  *(shared with the wider problem)*"                               # noqa: E731
    one = lambda x: ((x["text"] + mark(x)) if x else "*not known yet*")                                                    # noqa: E731
    many = lambda xs: ["- " + x["text"] + mark(x) for x in xs] or ["- *not known yet*"]                                     # noqa: E731
    out = ["# " + title(d["brand"], d["avatar"], d["sub"]), "", "%d lines are this person's own." % d["own_lines"], ""]
    out += ["## Wants", "", one(d["desire"]), "", "## Has been through", ""] + many(d["experiences"]) + ["", "## Feels", ""] + many(d["emotions"]) + ["", "## Does", ""] + many(d["behaviors"])
    out += ["", "## World", ""] + many(d["culture"]) + ["", "## Doubts", "", one(d["doubt"]), "", "## Would stop for", "", one(d["opening"])]
    if d.get("missing"):
        out += ["", "## Research still has to answer", ""] + ["- " + x for x in d["missing"]]
    return "\n".join(out + ["", "## Every line it stands on", ""] + ['- [%s] "%s"' % (i, x["text"]) for i, x in d["lines"].items()]) + "\n"


def full(brand, avatar, sub="", demographic="", what=None):
    """THE full profile an asset is made from: the person, the look and the message, joined now from where each lives. {} for no avatar."""
    if not brand or not avatar:
        return {}
    avatar, _ = N.canon(brand, avatar)
    key = resolve(brand, avatar, sub)[0]
    p = filed(brand, avatar, key) if key else {}
    h = home(brand, avatar, key) if key else None
    return {"name": name(brand, avatar, key, demographic), "title": title(brand, avatar, key, demographic), "brand": brand, "joined": datetime.date.today().isoformat(),
            "person": p or {"avatar": avatar, "sub": key or None, "desire": {"text": desire_of(S.text_of(avatar_dir(brand, avatar) / "profile.md"))}, "note": "no finished profile yet: the avatar and card only"},
            "person_lives_in": str((h if h and h.is_file() else draft(brand, avatar, key)).relative_to(S.root())) if key and p else None,
            "look": {"demographic": (demographic or "").replace("/", "-") or None, "cast": cast(brand, demographic), "shows": looks(brand, avatar, key, demographic), "world": culture(brand, avatar, key, demographic)},
            "body": spot(brand, avatar, key, (what or {}).get("product")), "product_rule": BODY.rule(brand, (what or {}).get("product"), where_of(brand, avatar, key), S.root()) or None,
            "message": stamp(brand, avatar, key, demographic, what)}


def full_page(f):
    p, m = f["person"], f["message"]
    out = ["# Who this is for: " + f["title"], "", "`%s`" % f["name"], ""]
    if p.get("lines") is not None:
        out += person_page(p).split("\n", 3)[-1].split("## Every line it stands on")[0].strip().split("\n")
    else:
        out += ["Wants: " + ((p.get("desire") or {}).get("text") or "not known yet")]
    b = f.get("body") or {}
    if b or f.get("product_rule"):
        out += ["", "## Where on the body", ""] + (["**%s.**" % b["true"].capitalize(), "", "People call it: " + ", ".join(b["said_as"][:8])] + (["", "Goes with: " + ", ".join(x.replace("-", " ") for x in b.get("goes_with") or [])] if b.get("goes_with") else []) if b else [])
        out += [x for x in (f.get("product_rule"), ("May be used there: " + ", ".join(b["products_yes"])) if b.get("products_yes") else "", ("Never there: " + ", ".join(b["products_no"])) if b.get("products_no") else "") if x]
    out += ["", "## Looks like", "", f["look"]["shows"] or "*not named*", "", "## What this piece says", ""]
    out += ["- **%s:** %s" % (k.title(), m[k]) for k in ("desire", "awareness", "stage", "doubt", "claim") if m.get(k)]
    if p.get("lines"):
        out += ["", "## Their words", ""] + ['- "%s"' % x["text"] for x in list(p["lines"].values())[:20]]
    return "\n".join(out) + "\n"


def attach(folder, brand, avatar, sub="", demographic="", what=None):
    """Save the full profile with the piece being made (profile.json, profile.md), so the brief carries all of it wherever
    it goes. Never stops a run: what cannot be joined is printed and nothing is written."""
    try:
        f = full(brand, avatar, sub, demographic, what)
        if not f:
            return None
        d = Path(folder)
        d.mkdir(parents=True, exist_ok=True)
        (d / "profile.json").write_text(json.dumps(f, indent=1, ensure_ascii=False) + "\n")
        (d / "profile.md").write_text(full_page(f))
        return d / "profile.json"
    except Exception as e:  # noqa: BLE001
        print("  profile not saved with this piece (%s: %s)" % (type(e).__name__, str(e)[:100]))
        return None


def build(brand, avatar, sub, demographic="", cap=None, go=None, caller=None, pull=None, say=print):
    """One person, start to finish: write from what we hold, name what is missing, research it, write again.
    With no `go` it stops after the plan and its price and spends nothing. Returns (file, state)."""
    P = _research()
    f, _ = file_profile(brand, avatar, sub, demographic, caller=caller)
    d = json.loads(f.read_text())
    say("1 written from what we hold: %d own lines, %d questions open" % (d["own_lines"], len(d["missing"])))
    if not d["missing"]:
        return f, "full"
    plan = P.plan(brand, d["avatar"], d["sub"], caller=caller)
    h = P.folder(brand, d["sub"])
    h.mkdir(parents=True, exist_ok=True)
    (h / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
    say("2 research plan: %d searches, at most $%.2f" % (sum(len(plan[k]["searches"]) for k in ("reddit", "youtube", "tiktok")), P.PRICE))
    if not (cap and go):
        return f, "planned"
    lines, notes = (pull or P.pull)(plan, cap)
    P.file_rows(brand, d["avatar"], d["sub"], lines, "go: %s; cap $%.2f" % (go, cap))
    P.record(brand, d["avatar"], d["sub"], cap, go, lines, notes)
    say("3 researched: %d lines%s" % (len(lines), ("; could not read " + "; ".join(notes)) if notes else ""))
    _ROWS.clear()
    f, _ = file_profile(brand, avatar, sub, demographic, caller=caller)
    d = json.loads(f.read_text())
    say("4 written again: %d own lines, %d questions open" % (d["own_lines"], len(d["missing"])))
    return f, "researched"


def _research():
    p = str(HERE.parents[1] / "research-gatherer")
    if p not in sys.path:
        sys.path.append(p)
    from research_gatherer import person as P
    return P


def refresh(brand, caller=None):
    """Rewrite every profile whose sources changed since it was written."""
    done = []
    for x in index(brand):
        if x["stale"]:
            done.append(file_profile(brand, x["avatar"], x["sub"], caller=caller)[0])
    return done


def stamp(brand, avatar, sub=None, demographic=None, what=None):
    avatar, _ = N.canon(brand, avatar)
    key = resolve(brand, avatar, sub)[0]
    w = decide(brand, avatar, key, what)
    return {"avatar": avatar, "sub": key or None, "demographic": demographic or None,
            "desire": w.get("desire"), "awareness": w.get("awareness"), "stage": w.get("stage"), "doubt": w.get("doubt"), "claim": w.get("claim"),
            "profile": name(brand, avatar, key, demographic), "where": where_of(brand, avatar, key) or None}


def filed(brand, avatar, sub, demographic="", newest=False):
    """One person's profile: the owner's filed one in the brand folder, else the draft (`newest`: the draft first). {} for none.
    A profile belongs to the person; the look is joined to it (`full`)."""
    try:
        fs = [home(brand, avatar, sub), draft(brand, avatar, sub)]
    except (SystemExit, AttributeError):
        return {}
    for f in (reversed(fs) if newest else fs):
        try:
            return json.loads(f.read_text())
        except (OSError, ValueError):
            continue
    return {}


def catalog(brand):
    """Read available strategist profiles without rebuilding the index or writing brand files.

    Filed profiles win over drafts, exactly as full()/block() do. Each receipt names
    the actual JSON and its hash; broad avatar summaries are not candidates.
    """
    import hashlib
    out = []
    for avatar in avatars(brand):
        for sub in subs(brand, avatar):
            if N.profile(brand, avatar, sub)["id"] in N.merges(brand):          # a merged profile is a lens of its keeper: the keeper's card stands for it
                continue
            source = next((p for p in (home(brand, avatar, sub), draft(brand, avatar, sub)) if p.is_file()), None)
            if source is None:
                continue
            try:
                raw = source.read_bytes()
                profile = json.loads(raw)
                if not isinstance(profile, dict) or not profile.get("name") or not profile.get("desire"):
                    raise ValueError("profile needs a name and desire")
                if N.canon(brand, profile.get("avatar") or "", profile.get("sub") or "") != (avatar, sub):     # either spelling, one home
                    raise ValueError("profile avatar/sub do not match its home")
            except (OSError, ValueError) as e:
                raise SystemExit("cannot read strategist profile %s: %s" % (source.relative_to(S.root()), e))
            out.append({"name": profile["name"], "avatar": avatar, "sub": sub,
                        "source": str(source.relative_to(S.root())), "sha256": hashlib.sha256(raw).hexdigest(),
                        "state": "filed" if source == home(brand, avatar, sub) else "draft", "profile": profile})
    return out


def catalog_block(brand):
    """Audience selection reads these complete people, not the legacy language-bank roster."""
    rows = catalog(brand)
    if not rows:
        return ""
    out = ["## CREATIVE STRATEGIST PROFILES — audience selection", "",
           "Select one of these specific profiles for OUR version of the swipe. Print its exact AVATAR and "
           "SUB-AVATAR keys in the existing output slots and explain the fit from its own evidence. "
           "These profiles replace the broad avatar roster as the selection source. Do not select a broad avatar "
           "with SUB-AVATAR: none. If none fits, say none fit and explain; writing will wait for a suitable profile. "
           "An explicitly declared profile still wins. A declared avatar alone narrows the candidates but does not "
           "select a person. Do not infer the person's experiences from the swipe or from the number of source lines. "
           "Unknowns remain unknown; a draft remains a draft, never owner-approved by selection.", ""]
    for row in rows:
        out += ["### " + row["name"], "AVATAR: " + row["avatar"], "SUB-AVATAR: " + row["sub"],
                "Source: `%s` (sha256 %s; %s)" % (row["source"], row["sha256"], row["state"]), "",
                person_page(row["profile"]), ""]
    return "\n".join(out)


def selection(brand, avatar, sub=None):
    """Validate a chain's chosen person against the catalog; never silently fall back when profiles exist.

    Returns its source receipt, or None for a brand with no strategist profiles yet.
    """
    rows = catalog(brand)
    if not rows:
        return None
    avatar, _ = N.canon(brand, avatar)
    key = resolve(brand, avatar, sub)[0] if avatar else ""
    row = next((r for r in rows if r["avatar"] == avatar and r["sub"] == key), None)
    if row is None:
        raise SystemExit("choose a specific creative-strategist profile before writing; selected %s/%s; available: %s" %
                         (avatar or "none", key or "none", ", ".join(r["name"] for r in rows)))
    return {k: v for k, v in row.items() if k != "profile"}


def person(p):
    """The finished profile as a writing step reads it."""
    t = lambda x: (x or {}).get("text") or "not known yet"                                                                # noqa: E731
    many = lambda xs: "; ".join(x["text"] for x in xs or []) or "not known yet"                                           # noqa: E731
    out = ["**This person, written from their own lines (the profile `%s`). Where the group and the person differ, the person wins:**" % p["name"], "",
           "- Wants: " + t(p.get("desire")), "- Has been through: " + many(p.get("experiences")), "- Feels: " + many(p.get("emotions")), "- Does: " + many(p.get("behaviors")),
           "- World: " + many(p.get("culture")), "- Doubts: " + t(p.get("doubt")), "- Would stop for: " + t(p.get("opening"))]
    if p.get("missing"):
        out += ["- Not known, so never claimed: " + "; ".join(p["missing"])]
    return out + ["", "**Their lines, word for word:**", ""] + ['- [%s] "%s"' % (i, x["text"]) for i, x in list((p.get("lines") or {}).items())[:24]]


def block(brand, avatar, sub=None, demographic=None, what=None, rows_n=24):
    if not brand or not avatar:
        return ""
    avatar, _ = N.canon(brand, avatar)
    key, card, prof, _ = resolve(brand, avatar, sub)
    must_fit(brand, (what or {}).get("product"), avatar, key)
    profile, ct = S.text_of(avatar_dir(brand, avatar) / "profile.md"), S.text_of(card) if card else ""
    core, own, w = slots(brand, avatar), slots(brand, avatar, key) if key else {}, decide(brand, avatar, key, what)
    D, out = doctrine(), [MARK, ""]
    out += ["One read of the person and the message, the same for every step. Where another part of this prompt differs about "
            "WHO it speaks to or WHICH desire, awareness level or doubt it works on, this wins. The ask, the owner's script and the brand's facts still win over this.", ""]
    out += ["- **Avatar (a whole person, led by one desire):** %s. %s" % (avatar, (desire_of(profile) or "see the profile"))]
    if key:
        out += ["- **Sub-avatar (the one thing that sets this person apart):** %s. %s" % (key, field(ct, r"Id / narrowed by") or "see the card")]
        for lab, n in (("What they want, in their words", "Core desire"), ("What it is like", "Pain"), ("Their story in a line", "One-line story")):
            if field(ct, n):
                out += ["- **%s:** %s" % (lab, field(ct, n))]
        if not field(ct, "Pain"):
            body = re.split(r"^### (?:rooms|language-refs|face)\b", ct.split("\n---\n")[-1], flags=re.M)[0].strip()
            out += ["", "\n".join(body.splitlines()[:22])]
        delta = section(ct, "language-delta")
        if delta:
            out += ["", "**Words only this sub-avatar says:**", "", delta[:1600]]
    else:
        out += ["- **Sub-avatar:** none named. Speak to the problem the whole avatar shares; never to one sub-avatar's situation."]
    demo = section(profile, "demographics")
    out += ["", "- **Demographic (the face, the words, the place; never a new problem or argument):** " + (demographic or "not named. Stay inside: " + ("; ".join(x.strip("- ") for x in demo.splitlines()[:6] if x.strip()) or "the people this avatar's own words come from"))]
    out += ["", "**What this piece works on:**", ""]
    lv = next((x for x in D["awareness"]["levels"] if x["id"] == w.get("awareness")), None)
    out += ["- **Desire:** %s" % (w.get("desire") or "open. Pick one and say which")]
    out += ["- **Awareness:** %s" % (w.get("awareness") or "open. Pick one level and say which") + ((". Must: %s. Must not: %s." % ("; ".join(lv["must"]), "; ".join(lv["must_not"]))) if lv else "")]
    out += ["- **Market stage:** %s" % (w.get("stage") or "open")]
    if w.get("leads_with"):
        out += ["- **So the argument leads with:** %s" % w["leads_with"]]
    dd = next((x for x in D["belief"]["doubts"] if x["id"] == w.get("doubt")), None)
    out += ["- **The one doubt it closes:** " + (("`%s` “%s” Closed by: %s." % (dd["id"], dd["says"], dd["closes_with"])) if dd else (w.get("doubt") or "open") + ". Pick one of the four and close only that one")]
    out += ["- **The claim:** %s" % (w.get("claim") or "from the brand's signed claims, or the line the piece already carries")]
    for s, title in ((own, "This sub-avatar, from their own words"), (core, "The avatar, from their own words")):
        if not s:
            continue
        q = lambda xs, k, n=5: "; ".join("%s%s" % (x.get(k, ""), (" [%s]" % x["rows"][0]) if x.get("rows") else "") for x in [x for x in xs or [] if not OWNED.search(str(x.get(k, "")))][:n]) or "none on file"   # noqa: E731
        out += ["", "**%s:**" % title, "", "- Wants, ranked: " + q(s.get("desires"), "want", 3), "- Who they say they are: " + q([x for x in s.get("roles") or [] if x.get("kind") != "becoming"], "role"),
                "- Who they want to become: " + q([x for x in s.get("roles") or [] if x.get("kind") == "becoming"], "role"), "- Already believe: " + q(s.get("beliefs"), "belief"),
                "- What has happened to them, what they used: " + q(s.get("experiences"), "fact", 6),
                "- Feel, and why: " + q(s.get("emotions"), "feel", 4), "- Habits: " + q(s.get("behaviors"), "does", 5)]
        for k in DOUBTS:
            x = (s.get("doubts") or {}).get(k)
            if x and x.get("said"):
                out += ["- Doubt `%s`: “%s” [%s]" % (k, x["said"], (x.get("rows") or [""])[0])]
    pf = filed(brand, avatar, key, demographic) if key else {}
    if pf:
        out += [""] + person(pf)
    rows, ids = ({}, []) if pf else his_rows(brand, avatar, key, rows_n)
    if ids:
        out += ["", "**Customer words about this problem, word for word:**", ""]
        out += ['- [%s] "%s"' % (i, rows[i]["text"]) for i in ids]
    elif not pf:
        out += ["", "**Customer words: none on file for this person. Invent none.**"]
    lk = looks(brand, avatar, key, demographic)
    if lk:
        out += ["", "**What they look like and how they sound (every picture, voice and cast choice):**", "", lk]
    if (what or {}).get("creative"):                         # an ad, never an email or a page
        out += ["", "**The picture:** show the thing THIS person is likeliest to stop for. A real photo, creator footage, AI-made, 3D or screen-native are all open (AI-made through the image process); none is the default."]
        if what.get("cell"):
            out += ["", what["cell"]]
        taken = taken_board(brand, key or avatar)
        out += [taken] if taken else []
    world = culture(brand, avatar, key, demographic)
    if world:
        out += ["", "**Their world (know it on every piece):**", "", "The words, the humour, the picture and the edit should feel like theirs. Use a reference where it makes them recognise "
                "themselves or the benefit faster. It is never decoration, never carries the piece instead of the benefit, and never comes from a world that is not theirs. Off-limits is hard.", "", world]
    out += body_lines(brand, avatar, key, (what or {}).get("product"))
    how = mechanics()
    if how:
        out += ["", "**The reason to act (one, or none):**", "", "Borrow the mechanic, never the bet: they always get what they paid for. Choose ONE that fits this person, this awareness level and "
                "this surface, and use its move. Use only a count, date, stock level, price or guarantee already stated in this prompt; one that is not there drops the mechanic and is never estimated. "
                "The awareness level's must-nots, the ask and the brand's rules win over it. When none fits, write without one. Never name the mechanic in the piece. Disclosure lives on the page; no small print is added to an ad.", "", how]
    never = S.never_list(S.text_of(S.brandpath.brand_path(brand, "brand-identity", "position.md", root=S.root() / "brands")))
    ob = objections(brand, avatar)
    if ob:
        out += ["", "**What stops them buying (the brand's own list):**", "", ob[:2200].rstrip()]
    return "\n".join(out + ["", "Products they tried are told as a kind of product, never by a name, a bottle or a label someone could recognise."]
                     + (["Never said in this brand: " + "; ".join(never) + "."] if never else []) + ["", END, ""])


# ------------------------------------------------------------------------------------------------------------ fill --
READ_ALL = 2400          # rows read per person, in rounds of ROUND (owner, 2026-11-26: fill from every line, never a top 420)
ROUND = 400


def fill_rows(brand, avatar, key):
    """Every row a person's profile is read from: their own rows first, then the bank ranked by their problem."""
    rows = bank(brand, avatar)
    ids = S.rank(rows, problem_words(brand, avatar, key), key or "", limit=READ_ALL)
    if len(ids) < 120:
        ids += [i for i in rows if i not in ids and 12 <= len(rows[i]["text"]) <= 320][:160]
    return [i for i in ids if 8 <= len(rows[i]["text"]) <= 700], rows


def fill_prompt(brand, avatar, sub, ids=None, found=None):
    key, card, prof, _ = resolve(brand, avatar, sub)
    allids, rows = fill_rows(brand, avatar, key)
    ids = ids if ids is not None else allids[:ROUND]
    v = {"person": (S.text_of(card) if card else "") + "\n\n" + (S.text_of(prof) if prof else ""), "avatar": S.text_of(avatar_dir(brand, avatar) / "profile.md"),
         "position": S.text_of(S.brandpath.brand_path(brand, "brand-identity", "position.md", root=S.root() / "brands"), 9000), "rows": "\n".join('[%s] "%s"' % (i, rows[i]["text"]) for i in ids),
         "desire": S.text_of(S.DOCTRINE / "desire.md"), "belief": S.text_of(S.DOCTRINE / "belief.md"), "awareness": S.text_of(S.DOCTRINE / "awareness.md"), "sophistication": S.text_of(S.DOCTRINE / "sophistication.md"),
         "core": json.dumps(slots(brand, avatar), ensure_ascii=False)[:6000] if key else "this is the avatar itself", "which": ("sub-avatar " + key) if key else ("avatar " + avatar),
         "found": json.dumps({k: v for k, v in (found or {}).items() if k in SLOT_LISTS + ("doubts", "objections")}, ensure_ascii=False) if found else "nothing yet: this is the first round"}
    p = S.live_prompt("who-slots").read_text()
    for k, x in v.items():
        p = p.replace("{" + k + "}", x)
    return p, ids, rows


def check_slots(d, ids, rows):
    """A slot whose row does not exist, or whose quote is not in that row, is dropped and named."""
    ok, bad, idset = {}, [], set(ids)
    good = lambda x: [i for i in x.get("rows") or [] if i in idset]                                                        # noqa: E731
    for k in ("desires", "roles", "beliefs", "experiences", "behaviors", "emotions"):
        ok[k] = []
        for x in d.get(k) or []:
            x["rows"] = good(x)
            (ok[k] if x["rows"] else bad).append(x if x["rows"] else "%s: %s has no row behind it" % (k, str(x)[:80]))
    life = {x["id"] for x in doctrine()["desire"]["human_desires"]["life_forces"] + doctrine()["desire"]["human_desires"]["learned"]}
    for x in ok["desires"]:
        x["human"] = [h for h in x.get("human") or [] if h in life]
    ok["doubts"] = {}
    for k in DOUBTS:
        x = (d.get("doubts") or {}).get(k) or {}
        x["rows"] = good(x)
        said = S.norm(x.get("said") or "")
        if said and any(said in S.norm(rows[i]["text"]) for i in x["rows"]):
            ok["doubts"][k] = x
        elif x.get("said"):
            bad.append("doubt %s: its words are not in the row it cites" % k)
    ok["objections"] = []
    for x in d.get("objections") or []:
        x["rows"] = good(x)
        said = S.norm(x.get("said") or "")
        if said and x.get("kind") in DOUBTS and any(said in S.norm(rows[i]["text"]) for i in x["rows"]):
            ok["objections"].append(x)
        elif x.get("said"):
            bad.append("objection: its words are not in the row it cites")
    ok["doubt_lead"] = d.get("doubt_lead") if d.get("doubt_lead") in ok["doubts"] else (next(iter(ok["doubts"]), None))
    for k, allowed in (("awareness_lead", LEVELS),):
        ok[k] = d.get(k) if d.get(k) in allowed else None
    ok["stage"] = d.get("stage")
    ok["gaps"] = d.get("gaps") or []
    return ok, bad


SLOT_LISTS = ("desires", "roles", "beliefs", "experiences", "behaviors", "emotions")
SLOT_TEXT = {"desires": "want", "roles": "role", "beliefs": "belief", "experiences": "fact", "behaviors": "does", "emotions": "feel"}


def merge_slots(have, got):
    """Every round's entries added to what earlier rounds found: a new entry is added, one already there gains rows."""
    if not have:
        return got
    for k in SLOT_LISTS:
        idx = {S.norm(x.get(SLOT_TEXT[k]) or ""): x for x in have.get(k) or []}
        for x in got.get(k) or []:
            t = S.norm(x.get(SLOT_TEXT[k]) or "")
            if not t:
                continue
            if t in idx:
                idx[t]["rows"] = list(dict.fromkeys((idx[t].get("rows") or []) + (x.get("rows") or [])))
            else:
                have.setdefault(k, []).append(x); idx[t] = x
    for k, x in (got.get("doubts") or {}).items():         # a doubt already filled keeps its words; a second voice is an objection
        if k not in (have.get("doubts") or {}):
            have.setdefault("doubts", {})[k] = x
        else:
            got.setdefault("objections", []).append(dict(x, kind=k))
    seen = {S.norm(x.get("said") or "") for x in have.get("objections") or []} | {S.norm(x.get("said") or "") for x in (have.get("doubts") or {}).values()}
    for x in got.get("objections") or []:
        if S.norm(x.get("said") or "") not in seen:
            have.setdefault("objections", []).append(x); seen.add(S.norm(x.get("said") or ""))
    for k in ("doubt_lead", "awareness_lead", "stage"):
        have[k] = have.get(k) or got.get(k)
    have["gaps"] = list(dict.fromkeys((have.get("gaps") or []) + (got.get("gaps") or [])))
    return have


def fill(brand, avatar, sub=None, caller=None, tries=2, today=None, rounds=None):
    """Read every row the person stands on, ROUND rows at a time, each round adding what the earlier ones had not found."""
    key = resolve(brand, avatar, sub)[0]
    allids, rows = fill_rows(brand, avatar, key)
    chunks = [allids[i:i + ROUND] for i in range(0, len(allids), ROUND)][:rounds]
    best, bad, read = None, [], 0
    for ids in chunks:
        p, ids, rows = fill_prompt(brand, avatar, key, ids=ids, found=best)
        note, got_best = "", None
        for _ in range(tries + 1):
            try:
                d = S.parse(S.ask_model(p + note, caller=caller))
            except ValueError:                         # a broken answer is asked again, never the end of the person (2026-11-26)
                note = "\n\n---\n\nYOUR LAST ANSWER WAS NOT VALID JSON. Answer again as one valid JSON object."
                continue
            got, bad = check_slots(d, ids, rows)
            size = lambda g: sum(len(g[k]) for k in SLOT_LISTS) + len(g["doubts"]) + len(g.get("objections") or [])   # noqa: E731
            if got_best is None or size(got) > size(got_best):
                got_best = got
            if not bad:
                break
            note = "\n\n---\n\nYOUR LAST ANSWER WAS HELD. Cite only rows printed above, quote a doubt word for word from its row, answer in full again:\n" + "\n".join("- %s" % b for b in bad)
        if got_best is not None:
            best = merge_slots(best, got_best)
        read += len(ids)
    counts = Counter(rows[i]["awareness"] or "not labelled" for i in rows)
    best.update({"brand": brand, "avatar": avatar, "sub": key or None, "state": "proposed", "made": today or datetime.date.today().isoformat(), "rows_read": read, "rounds": len(chunks), "awareness_rows": dict(counts), "dropped": bad})
    f = S.root() / "runs" / "creative-strategist" / brand / "who" / avatar / ((key or "avatar") + ".json")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(best, indent=1, ensure_ascii=False) + "\n")
    return f, best


def status(brand):
    out = []
    for a in avatars(brand):
        for s in [""] + subs(brand, a):
            d = slots(brand, a, s)
            out.append({"avatar": a, "sub": s or None, "state": d.get("state") or "empty", "desires": len(d.get("desires") or []), "roles": len(d.get("roles") or []), "beliefs": len(d.get("beliefs") or []),
                        "experiences": len(d.get("experiences") or []), "behaviors": len(d.get("behaviors") or []), "emotions": len(d.get("emotions") or []), "doubts": len(d.get("doubts") or {}), "awareness": d.get("awareness_lead"), "stage": bool(d.get("stage"))})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("do", choices=("show", "fill", "status", "profile", "full", "build", "index", "refresh"))
    ap.add_argument("--brand", required=True)
    ap.add_argument("--profile", help="a profile: <avatar>[_<sub>][_<demographic>] (PEOPLE.md); replaces --avatar/--sub")
    ap.add_argument("--avatar")
    ap.add_argument("--sub")
    ap.add_argument("--demographic")
    ap.add_argument("--cap", type=float, help="dollars per person, at most")
    ap.add_argument("--go", help="the owner's words for the spend; without it a build stops after the plan and its price")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.profile:
        a.avatar, a.sub, a.demographic = profile_args(a.brand, a.profile, a.avatar or "", a.sub or "", a.demographic or "")
    if a.do == "status":
        for x in status(a.brand):
            print(json.dumps(x))
        return 0
    if a.do == "profile":
        print(file_profile(a.brand, a.avatar, a.sub, a.demographic)[1])
        return 0
    if a.do == "full":
        print(full_page(full(a.brand, a.avatar, a.sub, a.demographic)))
        return 0
    if a.do == "build":
        for x in ([a.sub] if a.sub else subs(a.brand, N.canon(a.brand, a.avatar)[0])):
            print("== %s" % x)
            print(*build(a.brand, a.avatar, x, a.demographic or "", cap=a.cap, go=a.go))
        return 0
    if a.do == "index":
        for x in index(a.brand):
            print(json.dumps(x))
        return 0
    if a.do == "refresh":
        print(refresh(a.brand) or "nothing has changed")
        return 0
    if a.do == "show":
        print(block(a.brand, a.avatar, a.sub, a.demographic))
        return 0
    if a.dry_run:
        p, ids, _ = fill_prompt(a.brand, a.avatar, a.sub)
        print("%d rows, %d characters, prompt %s" % (len(ids), len(p), S.live_prompt("who-slots").name))
        return 0
    f, d = fill(a.brand, a.avatar, a.sub)
    print(f, {k: len(d[k]) for k in ("desires", "roles", "beliefs", "emotions", "doubts")}, "dropped", len(d["dropped"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
