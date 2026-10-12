"""EVERY PERSON IS THE SWIPE'S PERSON — same gender (2026-10-01).

the owner: "why did you make doctor 3 a woman if you knew it was a man?" The swipe's
third surgeon is a man ("Dr. Raymond Lee", "Voice: Male"); our Doctor 3 was
cast as a woman a week earlier and nothing compared the two. The swipe match
checks places, roles, camera and order — not who each person IS.

This pairs each person in the brief with the swipe person they stand in for —
from the brief's own scene `source` lines, which name the swipe's people
("Surgeon 3 stands behind her …") — then compares gender:

  the swipe:  the teardown record's CAST block (`Voice: Male`, `Voice: Female`,
              or a man/woman word in the block);
  ours:       the banked person's spec (`voice.gender`, or the man/woman word in
              `who`), else the brief's own identity block.

A mismatch is a finding; unknown on either side is not. No model call.
Brand-agnostic: reads only the run's teardown, its brief and the cast bank.

    python3 cast_match.py <teardown run dir>
"""
import json, re, sys
from pathlib import Path

WS = Path(__file__).resolve().parents[3]
MAN = re.compile(r"\b(man|male|he|his|him|gentleman|guy)\b", re.I)
WOMAN = re.compile(r"\b(woman|female|she|her|hers|lady)\b", re.I)


def gender_of(text):
    t = text or ""
    m = re.search(r"Voice:\s*(Male|Female)", t, re.I)
    if m:
        return "man" if m.group(1).lower() == "male" else "woman"
    w, mm = len(WOMAN.findall(t)), len(MAN.findall(t))
    return "woman" if w > mm else "man" if mm > w else None


def swipe_people(teardown):
    """{name: {"block": text, "gender": …}} from the record's CAST section."""
    m = re.search(r"\*\*CAST\*\*(.*?)(?=\n\*\*[A-Z ]{4,}\*\*\s*\n)", teardown, re.S)
    part = m.group(1) if m else teardown
    out = {}
    for blk in re.split(r"\n(?=\*\*[^*\n]+\*\*\s*\n)", part):
        h = re.match(r"\*\*([^*\n]+)\*\*", blk.strip())
        if h:
            name = re.sub(r"\s*\(.*?\)", "", h.group(1)).strip()
            out[name] = {"block": blk, "gender": gender_of(blk)}
    return out


def ours_gender(c, brand):
    bid = c.get("bank_id") or ""
    if bid and bid.upper() != "NEW":
        sp = WS / "runs" / "ai-elements" / brand / "casting" / bid / "spec.json"
        if sp.exists():
            d = json.loads(sp.read_text())
            g = ((d.get("voice") or {}).get("gender") or "").lower()
            if g in ("man", "woman"):
                return g
            g = gender_of(d.get("who") or "")
            if g:
                return g
    return gender_of(c.get("identity_block") or "")


def pair(doc, people):
    """Each cast id → the swipe person its scenes stand in for (greedy, purest first)."""
    counts = {}
    for s in doc.get("scenes") or []:
        who = f"{s.get('who') or ''} {s.get('speaker') or ''}"
        src = s.get("source") or ""
        for c in doc.get("cast") or []:
            if c["id"] and c["id"].lower() in who.lower():
                for name in people:
                    if re.search(rf"\b{re.escape(name)}\b", src, re.I):
                        counts.setdefault(c["id"], {}).setdefault(name, 0)
                        counts[c["id"]][name] += 1
    order = sorted(counts, key=lambda k: -max(counts[k].values()) / sum(counts[k].values()))
    used, out = set(), {}
    for cid in order:
        for name, _ in sorted(counts[cid].items(), key=lambda kv: -kv[1]):
            if name not in used:
                out[cid] = name; used.add(name); break
    return out


OWN = r"(hand|hands|thumb|thumbs|finger|fingers|fingertip|fingertips|forefinger|palm|wrist|forearm|arm|sleeve|coat|hair|bun|glasses|face|voice|look|gaze|mouth)\b"
FIELDS = ("happens", "outcome", "change", "state", "bracket", "do", "subject", "action", "composition", "location", "camera")


def _texts(scene):
    """(field, text) for every direction in a scene, beats included."""
    out = []
    def walk(o, key=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, k)
        elif isinstance(o, list):
            for v in o:
                walk(v, key)
        elif isinstance(o, str) and key in FIELDS:
            out.append((key, o))
    walk(scene)
    return out


def scene_mismatches(doc, brand):
    """The brief's DIRECTIONS must describe each person as their element is.
    A direction about one person only (it names that person and no other, or it
    is a beat in a scene that person carries alone) that uses the other gender's
    pronouns is a finding. the owner, 2026-10-01: "did the brief follow the element?"
    — Doctor 3 was recast as a man and his scenes still said "turns her hand over"."""
    cast = {c["id"]: ours_gender(c, brand) for c in doc.get("cast") or []}
    ids = [i for i in cast if i]
    found = []
    for sc in doc.get("scenes") or []:
        who = f"{sc.get('who') or ''}"
        solo = [i for i in ids if i.lower() in who.lower()]
        for field, text in _texts(sc):
            for clause in re.split(r"(?<=[.;:])\s+|\s+—\s+|,\s+(?=[A-Z])", text):
                low = clause.lower()
                hits = sorted((low.index(i.lower()), i) for i in ids if i.lower() in low)
                if hits:
                    # the words between a name and the next name are about that person
                    segs = [(pid, low[at + len(pid):(hits[k + 1][0] if k + 1 < len(hits) else len(low))])
                            for k, (at, pid) in enumerate(hits)]
                elif field == "do" and len(solo) == 1:
                    segs = [(solo[0], low)]
                else:
                    continue
                for pid, rest in segs:
                    g = cast.get(pid)
                    if g not in ("man", "woman"):
                        continue
                    # only the person's OWN body, clothes and look ("her hand", "his coat"):
                    # a bare "she/he/her" may be anyone in the shot ("behind her", "where he stands")
                    poss = "her" if g == "man" else "his"
                    m = re.search(rf"\b{poss}\s+(own\s+)?(right\s+|left\s+|other\s+)?{OWN}", rest)
                    if m:
                        found.append({"n": f"D-{sc.get('id')}", "element": f"{sc.get('id')} {field}: \"{clause.strip()[:110]}\"",
                                      "status": "Adapted", "why": f"{pid} is a {g} in the elements; this direction says \"{m.group(0)}\"",
                                      "clause": clause.strip()})
    return found


def readable_mismatches(body, doc, brand):
    """The brief's readable CAST block must describe the same person the
    elements do. the owner, 2026-10-01: "the brief informs the element check" — the
    JSON was rebound to a man while the readable block still said "low bun,
    pearl studs … her right hand", so the brief said two people at once."""
    found = []
    for c in doc.get("cast") or []:
        m = re.search(rf"^\*\*{re.escape(c['id'])}\*\* — (.*?)(?=\n\*\*Bank)", body, re.S | re.M)
        g = ours_gender(c, brand)
        if not m or g not in ("man", "woman"):
            continue
        said = gender_of(m.group(1))
        if said and said != g:
            found.append({"n": f"R-{c['id']}", "element": f"the brief's cast block for {c['id']}: \"{m.group(1).strip()[:110]}\"",
                          "status": "Adapted", "why": f"{c['id']} is a {g} in the elements; the brief's own description reads as a {said}"})
    return found


def repair(run_dir, brief_name="5-brief.md"):
    """Make the brief say what the element is — mechanical, no model, only the
    words that are about the person: their own pronouns in the clauses flagged
    D-, and their readable cast block rewritten from the banked element. The
    brief's fingerprint changes, so the swipe match, the manifest and the owner's
    read must run again — the chain's rule: upstream changes re-run downstream."""
    d = Path(run_dir)
    p = d / "stages" / brief_name
    body = p.read_text()
    brand = json.loads((d / "run.json").read_text()).get("brand")
    doc = json.loads(re.findall(r"```json\s*\n(.*?)\n```", body, re.S)[-1])
    changed = []
    for f in scene_mismatches(doc, brand):
        pid = f["why"].split(" is a ")[0]
        g = "man" if " is a man " in f["why"] else "woman"
        clause = f["clause"]
        fixed = swap_own(clause, pid, g, others=[c["id"] for c in doc.get("cast") or []])
        if fixed != clause and clause in body:
            body = body.replace(clause, fixed); changed.append(f["n"])
    for c in doc.get("cast") or []:
        g = ours_gender(c, brand)
        bid = c.get("bank_id") or ""
        sp = WS / "runs" / "ai-elements" / brand / "casting" / bid / "spec.json"
        m = re.search(rf"^(\*\*{re.escape(c['id'])}\*\* — )(.*?)(\nLoad-bearing:[^\n]*)?(?=\n\*\*Bank)", body, re.S | re.M)
        if not m or g not in ("man", "woman") or not sp.exists() or gender_of(m.group(0)) in (None, g):
            continue
        e = json.loads(sp.read_text())
        look = next(iter((e.get("looks") or {}).values()), {}).get("outfit") or e.get("base") or ""
        new = m.group(1) + f"{e['who']}; {look}. An original character resembling no real person."
        if m.group(3):
            new += swap_own(m.group(3), "", g, whole=True)
        body = body[:m.start()] + new + body[m.end():]; changed.append(f"R-{c['id']}")
    p.write_text(body)
    return changed


def swap_own(text, pid, g, whole=False, others=()):
    """her→his (or his→her) on the person's own body words, in the words after
    their name up to the next person's name (or in the whole text)."""
    a = ("her", "his") if g == "man" else ("his", "her")
    if whole or not pid or pid not in text:
        head, rest = "", text
    else:
        at = text.index(pid) + len(pid)
        stops = [text.find(o, at) for o in others if o != pid and text.find(o, at) > -1]
        end = min(stops) if stops else len(text)
        head, rest, tail = text[:at], text[at:end], text[end:]
        return head + re.sub(rf"\b{a[0]}\b(?=\s+(own\s+)?(right\s+|left\s+|other\s+)?{OWN})", a[1], rest) + tail
    rest = re.sub(rf"\b{a[0]}\b(?=\s+(own\s+)?(right\s+|left\s+|other\s+)?{OWN})", a[1], rest)
    return head + rest


def check(run_dir, brief_name="5-brief.md"):
    d = Path(run_dir)
    st = json.loads((d / "run.json").read_text())
    brand = st.get("brand")
    tear = (d / "stages" / "1-teardown.md").read_text()
    body = (d / "stages" / brief_name).read_text()
    blk = re.findall(r"```json\s*\n(.*?)\n```", body, re.S)
    doc = json.loads(blk[-1]) if blk else {}
    people = swipe_people(tear)
    pairs = pair(doc, people)
    found = []
    for c in doc.get("cast") or []:
        name = pairs.get(c["id"])
        if not name:
            continue
        theirs, ours = people[name]["gender"], ours_gender(c, brand)
        if theirs and ours and theirs != ours:
            found.append({"n": f"P-{c['id']}", "element": f"{c['id']} ({c.get('bank_id')}) stands in for the swipe's {name}",
                          "status": "Adapted", "why": f"the swipe's {name} is a {theirs}; ours is a {ours}"})
    found += readable_mismatches(body, doc, brand)
    found += scene_mismatches(doc, brand)
    return pairs, found


if __name__ == "__main__":
    pairs, found = check(sys.argv[1])
    print(json.dumps({"pairs": pairs, "mismatches": found}, indent=1, ensure_ascii=False))
