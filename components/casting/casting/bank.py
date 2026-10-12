"""The bank — who the brand has already banked, and who covers a role.

**READ ONLY.** The registry is the brand's own content, curated by people
(`the team notes/CLAUDE.md` rule 5: a machine reads `brands/<brand>/` and never
writes there). This module opens it, normalises the rows into one shape, and
answers one question: *who plays this role?* It proposes; it never writes.

Two shapes are read, because the two brands on disk keep their cast two
different ways and `the team notes/casting/build_cast.py` refuses the second:

    core-avatars/casting/roster.json     `people` — the people with the problem
    core-avatars/casting/authority.json  `people` — the credentialed voices,
                                         plus `_open`, the roles nobody covers
    core-avatars/casting/identities.json `people` — the generation handles
    ai-cast/<id>/character.md            the production bible, which for a
                                         brand with no registry JSON is the
                                         ONLY record that a person exists

A brand that keeps its cast the second way is answered, not refused. Refusing
it would mean this component says "no one plays that role" about a brand whose
people are all sitting one folder away — which is the exact failure the bank
exists to prevent, arriving from the other direction.

Brand-agnostic: no brand, person or role is named in this file.
"""
import json
import re
from pathlib import Path

from . import paths as P

# Words that say nothing about a role. "man" and "woman" are here on purpose:
# a role asked for as "a man who explains the routine" is about EXPLAINING.
STOP = {"the", "and", "for", "who", "with", "that", "this", "our", "one", "new",
        "man", "men", "woman", "women", "guy", "guys", "person", "people",
        "someone", "somebody", "his", "her", "him", "she", "they", "them",
        "from", "into", "onto", "about", "what", "when", "where", "which",
        "like", "some", "any", "all", "has", "have", "had", "was", "were",
        "are", "not", "can", "will", "would", "than", "then", "there"}

# The fields that say what a person is FOR. A word matching one of these is
# role evidence; a word matching a describing field (hair, build, wardrobe,
# note, setting) is not — it is a coincidence of vocabulary, and coverage
# decided on those is how a bank starts answering with the wrong person. A
# free-text `note` reading "Teenage acne. Never been in one of our ads." once
# made a 17-year-old cover the role "teenage skateboarder", which is exactly
# the kind of answer this split exists to stop.
ROLE_FIELDS = ("role", "fronts", "lane", "sub", "also_plays", "register",
               "problem", "why_she_exists", "why_he_exists")
SAID_FIELDS = ROLE_FIELDS + ("name", "reads", "hair", "build", "face", "note",
                             "setting", "wardrobe", "age", "production", "baseline")

# A role is COVERED when the record says MOST of what was asked for — strictly
# more than half of the asked-for words matched a role field. One shared word
# out of several is a candidate worth reading, not a casting decision.
COVERAGE = 0.5

WORD = re.compile(r"[a-z0-9]+")


def words(text):
    return set(w for w in WORD.findall(str(text or "").lower())
               if len(w) > 2 and w not in STOP)


def _read(path):
    """`(data, problem)`. A file that is NOT THERE is not a problem — a brand
    may keep its cast the other way. A file that is there and cannot be read
    IS one, and saying "nobody plays that role" because a record failed to
    parse is the worst answer this component could give."""
    p = Path(path)
    if not p.is_file():
        return None, None
    try:
        return json.loads(p.read_text()), None
    except (OSError, ValueError) as e:
        return None, "%s could not be read: %s: %s" % (P.rel(p), type(e).__name__, e)


def _flat(value):
    if isinstance(value, (list, tuple)):
        return " ".join(str(v) for v in value)
    return str(value or "")


def _person(row, where, source, handles, brand_name, start=None):
    cid = row.get("id") or ""
    pics = P.character(brand_name, cid, start) if cid else None
    return {
        "id": cid,
        "name": row.get("name") or (cid.title() if cid else ""),
        "where": where,
        "source": P.rel(source, start),
        "role_said": " · ".join(_flat(row.get(f)) for f in ROLE_FIELDS if row.get(f)),
        "said": " · ".join(_flat(row.get(f)) for f in SAID_FIELDS if row.get(f)),
        "row": row,
        "handles": handles or {},
        "bible": str(pics["bible"]) if pics and pics["bible"].is_file() else None,
        "master": str(pics["master"]) if pics and pics["master"].is_file() else None,
    }


def _bible_rows(brand_name, start=None):
    """A brand whose cast lives only as `ai-cast/<id>/character.md`.

    The bible is prose written for a person to read, so nothing is parsed out
    of it beyond its own words: the whole file is the person's `said`, and the
    title line is the name. That is enough to answer who plays a role, and it
    invents nothing the file does not say.
    """
    out = []
    root = P.brand(brand_name, start)["cast"]
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        f = d / "character.md"
        if not (d.is_dir() and f.is_file()):
            continue
        try:
            text = f.read_text()
        except OSError:
            continue
        lines = text.splitlines()
        first = next((ln.strip("# ").strip() for ln in lines
                      if ln.strip().startswith("#")), d.name)
        # The bible is long, and the one line that says what the character is
        # FOR is its lead: the title, then the paragraph before the first
        # sub-heading. Everything after that is wardrobe, voice and provenance,
        # which describe rather than cast.
        head, seen_title = [], False
        for ln in lines:
            if ln.strip().startswith("## ") and seen_title:
                break
            if ln.strip().startswith("#"):
                seen_title = True
            head.append(ln)
        head = "\n".join(head)
        out.append({
            "id": d.name, "name": first, "where": "bible",
            "source": P.rel(f, start),
            "role_said": head, "said": text,
            "row": {"id": d.name, "name": first},
            "handles": {},
            "bible": str(f),
            "master": str(d / "master-sheet.png") if (d / "master-sheet.png").is_file() else None,
        })
    return out


def read(brand_name, start=None):
    """Everything the brand has banked. `{people, open, sources, problems}`."""
    P.need_brand(brand_name, "the cast bank", start)
    b = P.brand(brand_name, start)
    idata, iproblem = _read(b["identities"])
    ident = (idata or {}).get("people") or {}
    people, sources, problems, gaps = [], [], [], []
    if iproblem:
        problems.append(iproblem)
    if len(b.get("registries") or []) > 1:
        problems.append(
            "this brand has TWO cast registries on disk — %s. One of them is a "
            "move in progress; until it finishes, the first is read and the "
            "second is invisible, which splits a cast without saying so."
            % ", ".join(P.rel(x, start) for x in b["registries"]))

    for key, where in (("authority", "authority"), ("roster", "roster")):
        data, problem = _read(b[key])
        if problem:
            problems.append(problem)
        if data is None:
            continue
        sources.append(P.rel(b[key], start))
        rows = data.get("people") or []
        if not isinstance(rows, list):
            problems.append("%s carries a `people` that is not a list" % P.rel(b[key], start))
            rows = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("id"):
                problems.append("a row in %s has no `id`" % P.rel(b[key], start))
                continue
            handles = dict(ident.get(row["id"]) or {})
            for f in ("element_id", "soul_id", "soul_status", "hf_voice_element_id",
                      "hands_element_id", "environment_element_id"):
                if row.get(f):
                    handles[f] = row[f]
            people.append(_person(row, where, b[key], handles, brand_name, start))
        for line in (data.get("_open") or []):
            gaps.append({"said": str(line), "source": P.rel(b[key], start)})

    banked = set(p["id"] for p in people)
    for row in _bible_rows(brand_name, start):
        if row["id"] in banked:
            for p in people:                       # the bible completes the row
                if p["id"] == row["id"]:
                    p["bible"] = row["bible"]
                    p["said"] = p["said"] + " · " + row["said"]
            continue
        people.append(row)
        if P.rel(P.brand(brand_name, start)["cast"], start) not in sources:
            sources.append(P.rel(P.brand(brand_name, start)["cast"], start))

    if not people:
        problems.append(
            "no cast records for `%s` — this brand has neither %s nor a built "
            "character under %s, so nothing can say who plays a role"
            % (brand_name, "/".join(P.REGISTRY_FOLDER) + "/{roster,authority}.json",
               "/".join(P.CAST_FOLDER) + "/<id>/character.md"))
    return {"brand": brand_name, "people": people, "open": gaps,
            "sources": sources, "problems": problems}


# ------------------------------------------------------------------ casting

def castable(person):
    """What this person can front today, and what is missing before they can
    front the rest. The two open items `authority.json` has carried since it
    opened, read off the record rather than assumed."""
    h = person.get("handles") or {}
    why = []
    if not h.get("element_id"):
        why.append("no Element banked — banking one needs the upload widget, "
                   "which is a person at a machine, not a headless run")
    if not h.get("hf_voice_element_id"):
        why.append("no voice element — every presenter needs one before "
                   "fronting a Cinema Studio ad")
    picture = bool(person.get("master"))
    return {
        # the fal chain takes image urls, so a banked picture is enough
        "image_chain": picture,
        "cinema": bool(h.get("element_id") and h.get("hf_voice_element_id")),
        "why": why,
        "handles": {k: v for k, v in h.items() if v},
    }


def score(person, want):
    """(points, role_hits, hits) for one person against the asked-for words.

    A word matching a field that says what the person is FOR counts three; a
    word matching a describing field counts one. Coverage needs at least one
    of the first kind — a shared adjective is not a casting decision."""
    role_hits = sorted(words(person.get("role_said")) & want)
    all_hits = sorted(words(person.get("said")) & want)
    other = [h for h in all_hits if h not in role_hits]
    return len(role_hits) * 3 + len(other), role_hits, all_hits


def who_plays(brand_name, role, start=None, banked=None):
    """**The one question.** Returns the person already banked for this role,
    or the gap — never a new face.

    `{brand, role, covered, person, where, candidates, castable, gap,
      bank: {...}, problems}`
    """
    data = banked if banked is not None else read(brand_name, start)
    want = words(role)
    if not want:
        return {"brand": brand_name, "role": role, "covered": False, "person": None,
                "where": None, "candidates": [], "castable": None,
                "gap": {"role": role, "said": "no role was named — the role is the "
                                              "question, and it cannot be read from "
                                              "anywhere else"},
                "bank": _summary(data), "problems": data["problems"]}

    ranked = []
    for p in data["people"]:
        pts, role_hits, hits = score(p, want)
        if not pts:
            continue
        ranked.append({"id": p["id"], "name": p["name"], "where": p["where"],
                       "source": p["source"], "points": pts,
                       "role_words": role_hits, "words": hits,
                       "why": "%s (%s) — the role asks for %s, and %s"
                              % (p["name"] or p["id"], p["where"],
                                 ", ".join(sorted(want)),
                                 ("the record says " + ", ".join(role_hits))
                                 if role_hits else
                                 ("only its describing fields say "
                                  + ", ".join(hits))),
                       "person": p})
    ranked.sort(key=lambda r: (-r["points"], r["id"]))

    top = ranked[0] if ranked else None
    covered = bool(top and top["role_words"]
                   and len(top["role_words"]) > COVERAGE * len(want))
    gap = None
    if not covered:
        gap = {"role": role,
               "said": "nobody in this brand's bank is recorded as playing this "
                       "role — no record says more than half of what was asked for",
               "near": [r["why"] for r in ranked[:3]],
               "open_items": [g["said"] for g in data["open"]],
               "next": "build one: the nine steps, starting with the footage search"}
    return {"brand": brand_name, "role": role, "covered": covered,
            "person": top["person"] if covered else None,
            "where": top["person"]["where"] if covered else None,
            "why": top["why"] if top else None,
            "candidates": [{k: v for k, v in r.items() if k != "person"} for r in ranked[:5]],
            "castable": castable(top["person"]) if covered else None,
            "gap": gap, "bank": _summary(data), "problems": data["problems"]}


def _summary(data):
    counts = {}
    for p in data["people"]:
        counts[p["where"]] = counts.get(p["where"], 0) + 1
    return {"people": len(data["people"]), "by_record": counts,
            "sources": data["sources"], "open": len(data["open"])}


# THE OTHER END OF THE SPECTRUM (the owner, 2026-09-22). Casting answers "who plays
# this role?"; this answers the reverse — "who do we have for THIS avatar?" The
# link is one field, `lane`, on the cast row: the core avatar this person
# serves. It points from the cast to the avatar and never the other way, so the
# avatar folders stay what they are — information about people and market, with
# no pictures and no cast in them.
def _items(value):
    """The list a field holds. `_flat` joins a list into one string for scoring;
    these two want the items back, and a bare string is ONE item, never its
    letters."""
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v is not None]
    v = str(value or "").strip()
    return [v] if v and v.lower() not in ("none", "null", "[]") else []


def for_avatar(brand_name, avatar, start=None):
    """Everyone this brand has for one core avatar, split by what they are for."""
    data = read(brand_name, start)
    want = str(avatar or "").strip().lower()
    out = {"brand": brand_name, "avatar": avatar, "authority": [], "roster": [],
           "also": [], "problems": list(data.get("problems", []))}
    if not want:
        out["problems"].append("name a core avatar")
        return out
    for p in data["people"]:
        row = p.get("row") or {}
        lane = str(row.get("lane") or "").strip().lower()
        also = [x.strip().lower() for x in _items(row.get("also_plays"))]
        if lane == want:
            out["authority" if p["where"] == "authority" else "roster"].append(p)
        elif want in also:
            out["also"].append(p)
    out["covered"] = bool(out["authority"] or out["roster"])
    out["why"] = (f"{len(out['authority'])} authority, {len(out['roster'])} roster"
                  + (f", {len(out['also'])} who also play them" if out["also"] else "")
                  if out["covered"] else
                  f"nobody in this brand's bank names `{avatar}` as the avatar they serve")
    return out


def avatars(brand_name, start=None):
    """Every core avatar the cast names, and how many people each one has."""
    data, seen = read(brand_name, start), {}
    for p in data["people"]:
        row = p.get("row") or {}
        for lane in [row.get("lane"), *_items(row.get("also_plays"))]:
            key = str(lane or "").strip()
            if key and key.lower() not in ("none", "null"):
                seen.setdefault(key, {"authority": 0, "roster": 0})
                seen[key]["authority" if p["where"] == "authority" else "roster"] += 1
    return seen
