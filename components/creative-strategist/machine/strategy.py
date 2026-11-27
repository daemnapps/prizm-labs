#!/usr/bin/env python3
"""strategy — the research route: an idea out of what is true about one sub-avatar, before any swipe, format or teller.

    strategy.py evidence --brand B --avatar A --sub S --product P --label L     everything we hold on him, ranked to his problem; no model
    strategy.py think    <run> [--model tier]                                   truths, tensions, insight, ideas; every receipt checked by code
    strategy.py check    <run>                                                  the receipt check again, no model
    strategy.py copy     <run>                                                  headlines and a body: his words and what has sold, AI phrasing refused, read cold
    strategy.py forms    <run> [--idea N]                                       the three forms in the bank that fit the idea, no swipe read
    strategy.py choose   <run> --by NAME [--idea N]                             the owner's pick (default: the one)
    strategy.py ask      <run> --ask LABEL --said "..." --funnel "..." [--form NO]   the ask every writing chain already reads, with the idea in it
    strategy.py hand     <run> --ask LABEL --to video|image                     the next command in that chain, ready to run; runs nothing
    strategy.py show     <run>                                                  the idea in plain words

The run is runs/creative-strategist/<brand>/strategy/<label>/. The swipe route (ask.py) is unchanged beside it. Nothing here
writes into brands/, spends credits or opens a run in another component.
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
for p in (HOME.parent / "brandpath", HOME.parent / "run-kit", HERE):
    sys.path.insert(0, str(p))
import brandpath  # noqa: E402
sys.path.insert(0, str(HOME.parent / "naming"))
import people as N  # noqa: E402                                  the one door to a person: a profile id, a new name or an old one (naming/PEOPLE.md)

PROMPTS, FORMS = HOME / "prompts", HOME / "definitions" / "forms.json"
DOCTRINE = HOME.parent / "marketing-doctrine" / "slices"
STOP = set("""about after again all also always and any are because been before being both but can cant come could does dont down each even ever every
for from get gets give goes going good got had has have having hear her here hers him his how into isnt its just keep kept know less like look made make
makes many more most much need never not now off one only other our out over own part same see seen she should show side some still such take than that
the their them then there these they thing things this those through too two under until use used using very want wants was way well were what when where
which while who whose why will with without work works would year years yet you your year-old man men guy skin face""".split())
NO_PRICE = ("unaware", "problem-aware", "solution-aware")


def root():
    return brandpath.repo()


def norm(t):
    return re.sub(r"[^a-z0-9$%]+", " ", str(t).lower().replace("’", "'").replace("'", "")).strip()


def words(t):
    return [w for w in re.findall(r"[a-z]{4,}", norm(t)) if w not in STOP]


# ------------------------------------------------------------------------------------------------------- evidence --
def person(brand, avatar, sub=""):
    """(avatar folder, sub-avatar folder) as the brand keeps them, from a profile id, a new name or an old name."""
    a, s, _ = N.folders(brand, avatar, sub)
    return a or avatar, s or sub


def sub_files(brand, avatar, sub):
    """The card and (when it exists) the profile of one sub-avatar."""
    avatar, sub = person(brand, avatar, sub)
    d = brandpath.brand_path(brand, "core-avatars", avatar, "sub-avatars", root=root() / "brands")
    key = re.sub(r"^sub-\d+-", "", str(sub))
    cards = sorted(p for p in d.glob("*.md") if re.sub(r"^sub-\d+-", "", p.stem) == key)
    profs = [p for p in ([d / c.stem / "profile.md" for c in cards[:1]] + [d / key / "profile.md"]) if p.is_file()]
    return (cards[0] if cards else None), (profs[0] if profs else None)


def bank(brand, avatar):
    """Every row of the avatar's language bank: short id -> row."""
    avatar = person(brand, avatar)[0]
    d = brandpath.brand_path(brand, "core-avatars", avatar, root=root() / "brands")
    out, pre = {}, "language_%s_%s_" % (brand, avatar)
    # the avatar's own rows and every sub-avatar's (a sub keeps its rows beside its card); spent rows are not a voice
    files = [f for f in sorted((d / "language").glob("**/*.json")) if "used" not in f.relative_to(d).parts]
    for f in files + sorted((d / "sub-avatars").glob("*/language/**/*.json")):
        try:
            rows = json.loads(f.read_text()).get("entries") or []
        except (OSError, ValueError, AttributeError):
            continue
        for e in rows:
            t = " ".join(str(e.get("text") or "").split())
            if not t or e.get("status") not in (None, "active"):
                continue
            aw = e.get("awareness")
            out[str(e.get("id", "")).replace(pre, "")] = {"text": t, "sub": e.get("sub"), "awareness": aw.get("level") if isinstance(aw, dict) else aw,
                                                          "use": e.get("use"), "source": (e.get("source") or {}).get("name", "")}
    return out


def voices(brand, avatar):
    """Every line a piece for this avatar may stand on: its own bank, what research pulled for it, and the brand's own customers."""
    import who as W
    return W.bank(brand, avatar)


def rank(rows, problem, sub, limit=420):
    """The rows that are about HIS problem, his own first. Ranked by the words of his card and the position's problem
    words, rarer words counting more. Likes are not read: a loud row about something else is noise."""
    n, df = max(1, len(rows)), Counter()
    for r in rows.values():
        df.update(set(words(r["text"])))
    terms = Counter(words(problem))
    weigh = {w: math.log(1 + n / (1 + df[w])) for w in terms if df[w]}
    scored, seen = [], set()
    for i, r in rows.items():
        k = norm(r["text"])
        if len(k) < 12 or len(k) > 320 or k in seen:
            continue
        hit = [w for w in set(words(r["text"])) if w in weigh]
        mine = r["sub"] == sub
        if not hit and not mine:
            continue
        seen.add(k)
        lvl = {"problem-aware": 1.4, "solution-aware": 1.25, "unaware": 1.2, "product-aware": 1.0}.get(r["awareness"], 0.8)
        scored.append(((2.0 if mine else 0) + lvl * sum(weigh[w] for w in hit) / math.sqrt(4 + len(words(r["text"]))), i))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [i for _, i in scored[:limit]]


def text_of(path, cut=None):
    try:
        t = Path(path).read_text()
    except OSError:
        return ""
    return t[:cut] if cut else t


def never_list(position):
    """The phrases the position says are never used."""
    m = re.search(r"^NEVER:\s*(.+)$", position, re.M)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def evidence(brand, avatar, sub, product):
    avatar, sub = person(brand, avatar, sub)
    b = root() / "brands"
    at = lambda key, *rest: brandpath.brand_path(brand, key, *rest, root=b)          # noqa: E731
    card, prof = sub_files(brand, avatar, sub)
    if not card:
        raise SystemExit("refused: no card for sub-avatar %r under %s" % (sub, avatar))
    position = text_of(brandpath.brand_file(brand, "brand-identity", "position.md", root=b))
    m = re.search(r"^PROBLEM WORD:\s*(.+)$", position, re.M)
    rows = voices(brand, avatar)
    ids = rank(rows, text_of(card) + " " + (m.group(1) if m else ""), sub)
    pf = at("products", product + ".md")
    files = {"card": card, "profile": prof, "avatar": at("core-avatars", avatar, "profile.md"),
             "position": brandpath.brand_file(brand, "brand-identity", "position.md", root=b), "objections": at("core-avatars", "objection-bank.md"),
             "culture": at("core-avatars", avatar, "culture-map.md"), "product": pf,
             "failed": at("intake", "research", "failed-solutions.md"), "before_after": at("core-avatars", "before-afters.md")}
    have = {k: str(Path(v).relative_to(root())) for k, v in files.items() if v and Path(v).is_file()}
    own = sum(1 for r in rows.values() if r["sub"] == sub)
    gaps = []
    import who as W
    W.must_fit(brand, product, avatar, sub)
    if not W.filed(brand, avatar, sub):
        gaps.append("no full profile for this person yet: who.py build --brand %s --avatar %s --sub %s" % (brand, avatar, sub))
    if own < 30:
        gaps.append("only %d rows in the bank are his own" % own)
    for k, why in (("position", "no position"), ("objections", "no objection bank"), ("culture", "no culture map"), ("failed", "no failed-solutions record"), ("product", "no product file")):
        if k not in have:
            gaps.append(why)
    return {"brand": brand, "avatar": avatar, "sub": sub, "product": product, "made": date.today().isoformat(), "files": have, "rows": ids,
            "bank_rows": len(rows), "own_rows": own, "never": never_list(position), "gaps": gaps}


# --------------------------------------------------------------------------------------------------------- receipts --
def sources(ev):
    return {k: norm(text_of(root() / p)) for k, p in ev["files"].items()}


def resolve(receipts, rows, src):
    """Every fault in one claim's receipts. [] = each names a real row or file and quotes words that are in it."""
    bad = []
    if not receipts:
        return ["no receipt"]
    for r in receipts:
        ref, q = str(r.get("from", "")).strip(), norm(r.get("quote", ""))
        if len(q) < 3:
            bad.append("%s: no quote" % (ref or "?"))
        elif ref in rows:
            if q not in norm(rows[ref]["text"]):
                bad.append("%s does not say %r" % (ref, r.get("quote")))
        elif ref in src:
            if q not in src[ref]:
                bad.append("the %s does not say %r" % (ref, r.get("quote")))
        else:
            bad.append("%r is not a row or a file" % ref)
    return bad


NUM = re.compile(r"(?<![\w$])\$?\d[\d,.]*%?|\b(?:half an hour|an hour|a minute|seconds|minutes|hours|ten|eleven|twelve|"
                 r"(?:thir|four|fif|six|seven|eigh|nine)teen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundreds?|thousands?|dozens?)\b", re.I)


def verify(d, ev, rows=None):
    """{claim: [faults]} for a thought-out idea. Receipts resolve, numbers are sourced, nothing from the never list."""
    rows = voices(ev["brand"], ev["avatar"]) if rows is None else rows
    src, out, quoted = sources(ev), {}, ""
    for n, o in enumerate(d.get("observations") or [], 1):
        f = resolve(o.get("receipts") or [], rows, src)
        if f:
            out["observation %d" % n] = f
        else:
            quoted += " " + o.get("true", "") + " " + " ".join(str(r.get("quote", "")) for r in o["receipts"])
    if len(d.get("observations") or []) - sum(k.startswith("observation") for k in out) < 8:
        out["observations"] = ["fewer than eight hold up"]
    known = norm(" ".join(str(r.get("quote", "")) for o in d.get("observations") or [] for r in o.get("receipts") or []))
    say = {"insight": d.get("insight", ""), "the one": " ".join(str((d.get("the_one") or {}).get(k, "")) for k in ("idea", "line"))}
    for k, t in say.items():
        miss = sorted({x.group(0).lower() for x in NUM.finditer(t) if norm(x.group(0)) not in known})
        if miss:
            out.setdefault(k, []).append("no receipt for: " + ", ".join(miss))
        for nv in ev.get("never") or []:
            if norm(nv) in norm(t):
                out.setdefault(k, []).append("on the position's never list: %r" % nv)
    return out


# ------------------------------------------------------------------------------------------------------------ think --
def live_prompt(stem):
    fs = sorted(PROMPTS.glob(stem + "-v*-owner.md"), key=lambda p: int(re.search(r"-v(\d+)-", p.name).group(1)))
    if not fs:
        raise SystemExit("refused: no live prompt %s" % stem)
    return fs[-1]


def ledger(brand):
    f = root() / "runs" / "creative-strategist" / brand / "strategy" / "ledger.jsonl"
    return f, [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.is_file() else []


def siblings(run, brand, avatar):
    """What the other sub-avatars of this avatar already think with: no two men get the same picture or the same turn."""
    out = []
    for f in sorted(run.parent.glob("*/idea.json")):
        if f.parent == run:
            continue
        try:
            ev, d = json.loads((f.parent / "evidence.json").read_text()), json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if ev.get("avatar") == avatar and d.get("the_one"):
            out.append("- %s (another man): %s | seen as: %s" % (ev["sub"], d["the_one"].get("line", ""), d["the_one"].get("see", "")[:180]))
    return out


def too_close(run, d):
    """The other man whose idea this one repeats, or "": four tenths of the shorter idea's own words are the same."""
    ev = json.loads((run / "evidence.json").read_text())
    key = lambda o: set(words(" ".join([o.get("idea", ""), o.get("line", "")])))            # noqa: E731
    mine = key(d.get("the_one") or {})
    common = set(words(text_of(root() / ev["files"]["position"], 4000))) if "position" in ev["files"] else set()
    for f in sorted(run.parent.glob("*/idea.json")):
        if f.parent == run:
            continue
        try:
            o, e = json.loads(f.read_text()), json.loads((f.parent / "evidence.json").read_text())
        except (OSError, ValueError):
            continue
        his = key(o.get("the_one") or {}) - common
        if e.get("avatar") == ev["avatar"] and min(len(mine - common), len(his)) >= 4 and len((mine - common) & his) >= .4 * min(len(mine - common), len(his)):
            return e["sub"]
    return ""


def fill(run, stem, extra=None):
    import who as W
    ev = json.loads((run / "evidence.json").read_text())
    rows, t = voices(ev["brand"], ev["avatar"]), ev["files"]
    get = lambda k, cut=None: text_of(root() / t[k], cut) if k in t else "NONE ON FILE"      # noqa: E731
    _, past = ledger(ev["brand"])
    v = {"card": get("card"), "profile": get("profile", 16000), "avatar": get("avatar"), "position": get("position"), "objections": W.objections(ev["brand"], ev["avatar"]) or "NONE ON FILE FOR THIS AVATAR",
         "culture": get("culture"), "failed": get("failed", 7000), "product": get("product", 7000),
         "rows": "\n".join('[%s] "%s"' % (i, rows[i]["text"]) for i in ev["rows"] if i in rows),
         "never": "\n".join("- " + x for x in ev["never"]) or "none", "gaps": "\n".join("- " + x for x in ev["gaps"]) or "none",
         "past": "\n".join(["- %s: %s" % (p.get("sub"), p.get("line")) for p in past[-60:]] + siblings(run, ev["brand"], ev["avatar"])) or "none yet",
         "awareness": text_of(DOCTRINE / "awareness.md"), "sophistication": text_of(DOCTRINE / "sophistication.md"), "desire": text_of(DOCTRINE / "desire.md")}
    v.update(extra or {})
    p = live_prompt(stem).read_text()
    for k, x in v.items():
        p = p.replace("{" + k + "}", x)
    left = sorted(set(re.findall(r"\{([a-z_]+)\}", live_prompt(stem).read_text())) - set(v))
    if left:
        raise SystemExit("refused: the prompt asks for %s and nothing supplies it" % ", ".join(left))
    return p + "\n\n" + W.block(ev["brand"], ev["avatar"], ev["sub"], what={"product": ev["product"], "creative": True}, rows_n=0)


def ask_model(prompt, tier="designs", caller=None):
    if caller:
        return caller(prompt)
    from run_kit import model as M
    m, _ = M.pick(tier, len(prompt))
    return M.call(prompt, m, label="strategy")


def parse(text):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    return json.loads(m.group(1) if m else text[text.index("{"):text.rindex("}") + 1])


def think(run, caller=None, tries=3):
    """Run the thinking step; a claim whose receipt does not resolve is sent back, and what still fails is dropped."""
    ev = json.loads((run / "evidence.json").read_text())
    rows, base, note, d, bad = voices(ev["brand"], ev["avatar"]), fill(run, "research-to-idea"), "", None, {}
    for n in range(1, tries + 1):
        sent = base + note
        (run / "research-to-idea-sent.md").write_text(sent)
        text = ask_model(sent, caller=caller)
        (run / ("research-to-idea-answer-%d.md" % n)).write_text(text)
        d = parse(text)
        bad = verify(d, ev, rows)
        twin = too_close(run, d)
        if twin:
            bad.setdefault("the one", []).append("this is %s's idea; find another" % twin)
        if not bad:
            break
        note = ("\n\n---\n\nYOUR LAST ANSWER WAS HELD. Fix only these, keep the rest, and answer in full again:\n"
                + "\n".join("- %s: %s" % (k, "; ".join(x)) for k, x in bad.items()) + "\n\nYour last answer:\n\n```json\n" + json.dumps(d, ensure_ascii=False) + "\n```\n")
    d["observations"] = [o for o in d.get("observations") or [] if not resolve(o.get("receipts") or [], rows, sources(ev))]
    d["held"] = verify(d, ev, rows)
    if too_close(run, d):
        d["held"].setdefault("the one", []).append("the same idea as %s" % too_close(run, d))
    (run / "idea.json").write_text(json.dumps(d, indent=1, ensure_ascii=False))
    return d


# ------------------------------------------------------------------------------------------------------------ copy --
TELLS = [("a dash", re.compile(r"[\u2013\u2014]|\s-\s")),
         ("a flip", re.compile(r"\b(?:didn.?t|weren.?t|wasn.?t|isn.?t|aren.?t|don.?t|doesn.?t|never|not)\b[^.?!]{2,70}[.?!]\s+(?:you|it|it.?s|they|your|that.?s|he|the \w+ (?:was|is|did|does))\b", re.I)),
         ("not X but Y", re.compile(r"\bnot (?:just |only |about )?[^.?!,]{2,40},? but\b|\bit.?s not about\b|\bthe real (?:problem|reason|issue)\b", re.I)),
         ("a stock line", re.compile(r"here.?s the thing|let that sink|what if\b|\bimagine\b|game.?chang|say goodbye|unlock|elevate|journey|the truth is|spoiler", re.I))]


def tells(text):
    """What in a line reads like a machine wrote it. [] = nothing caught."""
    out = [n for n, rx in TELLS if n != "a flip" and rx.search(text)]
    ss = [x.split() for x in re.split(r"(?<=[.?!])\s+", text.strip()) if x]
    flip = dict(TELLS)["a flip"]
    # a flip is two SHORT sentences turning on each other; a plain "your hands never reach it. Your face wash ..." is not one
    if any(len(a) <= 8 and len(b) <= 8 and flip.search(" ".join(a + b)) for a, b in zip(ss, ss[1:])):
        out.append("a flip")
    for a, b in zip(ss, ss[1:]):
        if 2 <= len(a) <= 8 and 2 <= len(b) <= 8 and (a[0].lower() == b[0].lower() or a[-1].lower() == b[-1].lower()):
            out.append("a mirror")
            break
    return out


def problem_terms(ev):
    m = re.search(r"^PROBLEM WORD:\s*(.+?)(?:\bnever\b|$)", text_of(root() / ev["files"].get("position", "-")), re.M)
    own = words(re.sub(r"\([^)]*\)", " ", m.group(1)) if m else "")
    try:                                                   # the person's own problem words (card and profile), never a list fixed for one brand
        import who as W
        own += words(W.problem_words(ev["brand"], ev["avatar"], ev["sub"]))
    except Exception:                                      # noqa: BLE001  without a card the position's problem word stands alone
        pass
    return set(own) | {w.rstrip("s") for w in own}


def sold(brand, limit=40):
    """What has sold for the brand: headlines and the first sentence of each text, with sales. [] when there is no library."""
    try:
        sys.path.insert(0, str(HOME.parent / "meta-upload"))
        import copy_library as CL
        lib = CL.library(brand, n=400)
    except Exception:                                      # noqa: BLE001  a brand with no copy library still gets copy
        return []
    first = lambda t: re.split(r"(?<=[.?!])\s", t.strip())[0][:170].replace("\n", " ")      # noqa: E731
    rows = [(o.get("purchases") or 0, first(o["text"])) for k in ("primary", "headlines") for o in lib.get(k) or []]
    out, seen = [], set()
    for n, t in sorted(rows, reverse=True):
        if n and norm(t) not in seen and not re.search(r"\bsale\b|\$\d|free|% off", t, re.I):
            seen.add(norm(t))
            out.append((n, t))
    return out[:limit]


def line_faults(h, ev, rows):
    t, bad = h.get("text", ""), []
    bad += tells(t)
    if len(t.split()) > 12:
        bad.append("over 12 words")
    if not (set(words(t)) | {w.rstrip("s") for w in words(t)} | set(norm(t).split())) & problem_terms(ev):
        bad.append("does not name the problem or what he does about it")
    if h.get("kind") == "his words":
        r = rows.get(h.get("row"))
        left = norm(t).split()
        src = iter(norm(r["text"]).split()) if r else iter(())
        if not r or not all(w in src for w in left):
            bad.append("not his words")
    for nv in ev.get("never") or []:
        if norm(nv) in norm(t):
            bad.append("on the never list")
    return bad


def read_cold(lines_, winners, caller=None):
    """A reader with no context, shown our lines mixed with lines that sold. {line: fault}. If the reader also throws out
    half of what really sold, the reading is worth nothing and nothing is held by it."""
    import random
    mix = list(lines_) + [t for _, t in winners[:10]]
    random.Random(7).shuffle(mix)
    ask = ("Each line below is a phone ad headline. You know nothing else. For each: what problem is it about, in three words (or 'unclear'), and does it sound like a "
           "person talking ('person') or like something trying to be clever or written by a machine ('machine')?\n\n" + "\n".join("%d. %s" % (i, t) for i, t in enumerate(mix, 1))
           + '\n\nOne fenced json block: {"lines": [{"n": 1, "about": "", "sounds": "person|machine"}]}')
    got = {int(x["n"]): x for x in parse(ask_model(ask, tier="checks", caller=caller)).get("lines") or [] if str(x.get("n", "")).isdigit()}
    fault = {}
    for i, t in enumerate(mix, 1):
        g = got.get(i) or {}
        if "unclear" in str(g.get("about", "")).lower():
            fault[t] = "unclear cold"
        elif g.get("sounds") == "machine":
            fault[t] = "reads like a machine"
    real = [t for _, t in winners[:10]]
    if real and sum(t in fault for t in real) * 2 >= len(real):
        return {}
    return {t: f for t, f in fault.items() if t in lines_}


def copy(run, caller=None, tries=3):
    """Headlines and a body for the run's idea. What fails is sent back with its reason; only what passes is kept."""
    d, ev = json.loads((run / "idea.json").read_text()), json.loads((run / "evidence.json").read_text())
    rows, win = voices(ev["brand"], ev["avatar"]), sold(ev["brand"])
    voice = root() / "brands" / ev["brand"] / "core-avatars" / ev["avatar"] / "language" / "rules.md"
    base = fill(run, "idea-to-copy", {"truths": "\n".join("- %s  [%s]" % (o["true"], "; ".join('%s "%s"' % (r["from"], r["quote"]) for r in o["receipts"])) for o in d["observations"]),
                                      "insight": d.get("insight", ""), "winners": "\n".join("- (%d sold) %s" % w for w in win) or "none on file",
                                      "voice": text_of(voice, 14000) or "none on file", "not_cleared": "\n".join("- " + x for x in d.get("not_cleared") or []) or "none"})
    kept, dropped, body, point, note = [], [], "", "", ""
    for n in range(1, tries + 1):
        (run / "idea-to-copy-sent.md").write_text(base + note)
        text = ask_model(base + note, caller=caller)
        (run / ("idea-to-copy-answer-%d.md" % n)).write_text(text)
        got = parse(text)
        bad = {}
        good = []
        for h in got.get("headlines") or []:
            f = line_faults(h, ev, rows)
            if f:
                bad[h.get("text", "")] = ", ".join(f)
            elif norm(h["text"]) not in {norm(k["text"]) for k in kept}:
                good.append(h)
        cold = read_cold([h["text"] for h in good], win, caller) if good else {}
        bad.update(cold)
        kept += [h for h in good if h["text"] not in cold]
        dropped += [{"text": t, "why": w} for t, w in bad.items()]
        b = tells(got.get("body", ""))
        if not b and got.get("body"):
            body, point = body or got["body"], point or got.get("point", "")
        if len(kept) >= 5 and body:
            break
        note = ("\n\n---\n\nTHESE WERE THROWN OUT. Write new ones, plainer, and do not repeat any of them:\n" + "\n".join("- %s (%s)" % x for x in bad.items())
                + ("\n- the body: %s" % ", ".join(b) if b else "") + "\n\nAlready kept, do not repeat: " + " | ".join(k["text"] for k in kept))
    d["copy"] = {"headlines": kept, "body": body, "point": point, "thrown_out": dropped}
    (run / "idea.json").write_text(json.dumps(d, indent=1, ensure_ascii=False))
    return d["copy"]


def forms(run, pick=None, caller=None):
    d = json.loads((run / "idea.json").read_text())
    one = chosen(d, pick)
    fb = json.loads(FORMS.read_text())["forms"]
    text = ask_model(fill(run, "idea-to-form", {"idea": json.dumps(one, ensure_ascii=False), "insight": d.get("insight", ""),
                                                "forms": "\n".join("%s · %s · lends: %s" % (f["no"], f["what"], f["lends"]) for f in fb)}), tier="checks", caller=caller)
    got = parse(text)
    ok = {str(f["no"]): f for f in fb}
    d["forms"] = [dict(ok[str(x["no"])], why=x.get("why", "")) for x in got.get("forms") or [] if str(x.get("no")) in ok][:3]
    (run / "idea.json").write_text(json.dumps(d, indent=1, ensure_ascii=False))
    return d["forms"]


def chosen(d, n=None):
    if n is None:
        return d.get("chosen") or d["the_one"]
    ideas = d.get("ideas") or []
    if not 1 <= int(n) <= len(ideas):
        raise SystemExit("refused: idea %s is not one of 1 to %d" % (n, len(ideas)))
    return ideas[int(n) - 1]


def choose(run, by, n=None):
    d = json.loads((run / "idea.json").read_text())
    if d.get("held"):
        raise SystemExit("refused: held: " + "; ".join("%s: %s" % (k, ", ".join(v)) for k, v in d["held"].items()))
    d["chosen"] = dict(chosen(dict(d, chosen=None), n), by=by, at=date.today().isoformat())
    (run / "idea.json").write_text(json.dumps(d, indent=1, ensure_ascii=False))
    ev = json.loads((run / "evidence.json").read_text())
    f, past = ledger(ev["brand"])
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a") as h:
        h.write(json.dumps({"at": date.today().isoformat(), "brand": ev["brand"], "avatar": ev["avatar"], "sub": ev["sub"], "run": run.name,
                            "insight": d.get("insight"), "line": d["chosen"].get("line")}, ensure_ascii=False) + "\n")
    return d["chosen"]


def strategy_block(run, form_no=None):
    """What an ask carries (CONTRACT.md `strategy`)."""
    d, ev = json.loads((run / "idea.json").read_text()), json.loads((run / "evidence.json").read_text())
    if not d.get("chosen"):
        raise SystemExit("refused: no idea is chosen yet (strategy.py choose)")
    one, level = d["chosen"], str(d.get("awareness", "")).split(":")[0].strip().lower()
    out = {"route": "research", "record": str((run / "idea.json").relative_to(root())), "who": "%s / %s" % (ev["avatar"], ev["sub"]), "awareness": d.get("awareness", ""),
           "insight": d.get("insight", ""), "idea": one.get("idea", ""), "line": (d.get("copy") or {}).get("point") or one.get("line", ""), "see": one.get("see", ""),
           "truths": [{"true": o["true"], "receipt": "; ".join('%s "%s"' % (r["from"], r["quote"]) for r in o["receipts"])} for o in d["observations"]],
           "headlines": [h["text"] for h in (d.get("copy") or {}).get("headlines") or []], "body": (d.get("copy") or {}).get("body", ""),
           "no_price": level in NO_PRICE, "not_cleared": list(d.get("not_cleared") or [])}
    if form_no:
        f = next((x for x in json.loads(FORMS.read_text())["forms"] if str(x["no"]) == str(form_no)), None)
        if not f:
            raise SystemExit("refused: form %s is not in the bank" % form_no)
        out["form"] = f
    return out


def make_ask(run, label, said, funnel, form_no=None, force=False):
    import ask as A
    ev = json.loads((run / "evidence.json").read_text())
    sec = ev["product"]
    rec, notes = A.build(root(), {"brand": ev["brand"], "product": sec, "avatar": ev["avatar"], "ask": label, "said": said, "funnel": funnel, "sub_avatar": ev["sub"], "moment": "evergreen"})
    rec["strategy"] = strategy_block(run, form_no)
    if rec["strategy"]["no_price"]:
        rec["offer"]["lines"] = [x for x in rec["offer"]["lines"] if not re.search(r"\$\s?\d|\d\s?%|\bfree\b|\bsave\b", x, re.I)]
        rec["offer"]["never"] = sorted(set(rec["offer"]["never"]) | {"any price, discount or deadline"})
    import who as W
    level = re.match(r"[a-z-]+", str(rec["strategy"].get("awareness", "")).lower())
    rec["aim"] = W.stamp(ev["brand"], ev["avatar"], ev["sub"], what={"awareness": level.group(0) if level else None})
    f = root() / "runs" / "creative-strategist" / ev["brand"] / label / "ask.json"
    if f.exists() and not force:
        raise SystemExit("refused: %s exists (--force)" % f.relative_to(root()))
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return f, notes


def story(run):
    """The idea as the story file video-writing's from-scratch door takes (no swipe): every beat, person and line comes from it."""
    d, ev = json.loads((run / "idea.json").read_text()), json.loads((run / "evidence.json").read_text())
    one = chosen(d)
    f = run / "story.md"
    f.write_text("\n".join(["# " + (one.get("line") or "The idea"), "", "Who: %s / %s. Awareness: %s." % (ev["avatar"], ev["sub"], d.get("awareness", "")), "",
                            "The insight: " + d.get("insight", ""), "", "The idea: " + one.get("idea", ""), "", "What we see: " + one.get("see", ""), "",
                            "What it leaves in his head: " + one.get("line", ""), "", "## What is true (nothing else about him may be claimed)", ""]
                           + ["- %s  [%s]" % (o["true"], "; ".join('%s "%s"' % (r["from"], r["quote"]) for r in o["receipts"])) for o in d["observations"]]
                           + ["", "## Not cleared, never use", ""] + (["- " + x for x in d.get("not_cleared") or []] or ["- none"])) + "\n")
    return f


def hand(run, label, to):
    """The next command in the chain that makes it. Nothing is opened, spent or sent here."""
    d, ev = json.loads((run / "idea.json").read_text()), json.loads((run / "evidence.json").read_text())
    f = root() / "runs" / "creative-strategist" / ev["brand"] / label / "ask.json"
    if not f.is_file():
        raise SystemExit("refused: no ask %s yet (strategy.py ask)" % label)
    rec = json.loads(f.read_text())
    ref, level = str(f.relative_to(root())), re.match(r"[a-z-]+", str(d.get("awareness", "")).lower())
    if to == "video":
        st = story(run)
        return ["python3 components/video-writing/machine/scratch.py %s --brand %s --product %s --avatar %s --sub %s --awareness %s --ask %s --preset <story preset> --story %s --dry"
                % (label, ev["brand"], ev["product"], ev["avatar"], ev["sub"], level.group(0) if level else "problem-aware", ref, st.relative_to(root()))]
    form = (rec.get("strategy") or {}).get("form")
    if not form:
        raise SystemExit("refused: a static needs a form to borrow (strategy.py ask --form NO)")
    run_name = "%s-batch-%s" % (ev["brand"], label)
    return ["python3 components/image-teardown/chain.py open --brand %s --name %s --source paid --file <%s>" % (ev["brand"], label, form["swipe"]["label"]),
            "python3 components/image-teardown/tools/run.py %s all --brand %s --avatar %s --product %s --sub %s --ask %s" % (run_name, ev["brand"], ev["avatar"], ev["product"], ev["sub"], ref)]


def show(run):
    d, ev = json.loads((run / "idea.json").read_text()), json.loads((run / "evidence.json").read_text())
    out = ["%s / %s" % (ev["avatar"], ev["sub"]), "insight: " + d.get("insight", ""), "line: " + d["the_one"].get("line", ""), "idea: " + d["the_one"].get("idea", ""),
           "true: %d with receipts" % len(d["observations"])]
    out += ["HELD %s: %s" % (k, "; ".join(v)) for k, v in (d.get("held") or {}).items()] + ["gap: " + g for g in ev["gaps"]] + ["missing: " + m for m in d.get("missing_research") or []]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = ap.add_subparsers(dest="do", required=True)
    q = s.add_parser("evidence")
    for k in ("brand", "avatar", "sub", "product", "label"):
        q.add_argument("--" + k, required=True)
    for k in ("think", "check", "copy", "forms", "choose", "ask", "hand", "show"):
        q = s.add_parser(k)
        q.add_argument("run")
        if k in ("forms", "choose"):
            q.add_argument("--idea", type=int)
        if k == "choose":
            q.add_argument("--by", required=True)
        if k == "ask":
            for x in ("ask", "said", "funnel"):
                q.add_argument("--" + x, required=True)
            q.add_argument("--form")
            q.add_argument("--force", action="store_true")
        if k == "hand":
            q.add_argument("--ask", required=True)
            q.add_argument("--to", choices=("video", "image"), required=True)
    a = ap.parse_args(argv)
    if a.do == "evidence":
        run = root() / "runs" / "creative-strategist" / a.brand / "strategy" / a.label
        ev = evidence(a.brand, a.avatar, a.sub, a.product)
        run.mkdir(parents=True, exist_ok=True)
        (run / "evidence.json").write_text(json.dumps(ev, indent=1, ensure_ascii=False))
        print("%s: %d of %d rows about his problem, %d his own" % (run.relative_to(root()), len(ev["rows"]), ev["bank_rows"], ev["own_rows"]))
        print("\n".join("gap: " + g for g in ev["gaps"]))
        return 0
    run = Path(a.run)
    run = run if run.is_absolute() else root() / run
    if a.do == "think":
        d = think(run)
        print(show(run))
        return 1 if d["held"] else 0
    if a.do == "check":
        bad = verify(json.loads((run / "idea.json").read_text()), json.loads((run / "evidence.json").read_text()))
        print("\n".join("%s: %s" % (k, "; ".join(v)) for k, v in bad.items()) or "every receipt resolves")
        return 1 if bad else 0
    if a.do == "copy":
        c = copy(run)
        print("\n".join("%s  [%s %s]" % (h["text"], h.get("kind", ""), h.get("row", "")) for h in c["headlines"]))
        print("\n" + c["body"] + "\n\nthrown out: %d" % len(c["thrown_out"]))
        return 0 if c["headlines"] and c["body"] else 1
    if a.do == "forms":
        for f in forms(run, a.idea):
            print("%s · %s · %s" % (f["no"], f["what"], f["why"]))
    elif a.do == "choose":
        print(choose(run, a.by, a.idea).get("line", ""))
    elif a.do == "ask":
        f, notes = make_ask(run, a.ask, a.said, a.funnel, a.form, a.force)
        print(f.relative_to(root()))
        print("\n".join("note: " + n for n in notes))
    elif a.do == "hand":
        print("\n".join(hand(run, a.ask, a.to)))
    else:
        print(show(run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
