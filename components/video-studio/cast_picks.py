#!/usr/bin/env python3
"""Cast picks: a Real-lane production's shots, filled by PERSON first (owner, 20 Nov 2026: "Casting always needs to be
consistent and clearly defined so that way we can leverage the casting over and over again. Same thing as we would do
with AI cast as well").

    python3 cast_picks.py <production> [--dry-run]

The production names its real cast in brief.json "real_cast": {brief cast id: cast-bank id}. Each cast-bank entry
(runs/ai-elements/<brand>/casting/<id>/spec.json) carries "real_footage": {"where": [path parts of the person's clip
folder], "only_scenes_with": [words a scene must show, optional]}. The FIRST real_cast entry is the lead.

For every row of the production's shot list:
  - who plays it: the first real_cast member the writing brief's scene names in "who", else the lead;
  - what it shows: the words over that slot (a sung ad: the lyric sung over it, from the song's timing; else the
    row's phrase), then the row's own picture text;
  - the clip: the asset index searched inside that person's footage only (search `where`, several scenes a clip),
    placed on a clean moment when the index has measured one, never a moment already used in this ad, never another
    brand's product; a role whose footage is spent falls back to the lead's own moments (same story, same person).
A pick a person made by hand (no "by" mark from this step) is never replaced. Captioned footage is used and marked
(owner, 6 Nov). Writes picks.json and prints the cast and any slot left open. Brand-agnostic.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as ST  # noqa: E402
import shot_fill as SF  # noqa: E402

BY = "cast pick: the role played by one person throughout, the moment that shows the line (cast_picks.py)"
OTHER_BRANDS = ("milk makeup", "cerave", "cetaphil", "neutrogena", "olay", "nivea", "la roche", "the ordinary",
                "garnier", "clinique", "kiehl", "l'oreal", "loreal", "aveeno", " jar")
FALLBACK = ("man smiles at camera", "man shows his clear skin", "man checks his face in the mirror",
            "man speaks to camera", "close-up of man's face", "man in bathroom")
def fallback(rf):
    """The lead's own plain moments when a line finds nothing, in the lead's own gender (a woman's ad never asks for a man)."""
    if str(rf.get("demographic") or "").startswith("female"):
        return [re.sub(r"\bman\b", "woman", q).replace("his ", "her ") for q in FALLBACK]
    return list(FALLBACK)


STOP = set("the a an and or but to of in on at my me i it its it's your you he his she her him is was were be "
           "that this with for from bro got gonna get just like what who now no not".split())


def _bank(brand, cid):
    for root in (ST.WRITING.parents[2] / "runs" / "ai-elements" / brand / "casting" / cid,):
        for f in ("spec.json", "element.json"):
            if (root / f).is_file():
                return json.load(open(root / f))
    return {}


def _words(text):
    return " ".join(w for w in re.findall(r"[a-z']+", (text or "").lower()) if w not in STOP and len(w) > 2)


def _line_at(timing, t):
    lines = [x for x in (timing or {}).get("lines") or [] if x.get("start") is not None]
    if not lines:
        return ""
    return min(lines, key=lambda x: 0 if x["start"] <= t <= x["end"] else min(abs(t - x["start"]), abs(t - x["end"])))["line"]


def roles_of(brand, cast):
    """{brief cast id: the cast-bank entry's real_footage} for a real cast; refuses an entry with no clip folder."""
    roles = {}
    for bid, cid in cast.items():
        rf = (_bank(brand, cid).get("real_footage") or {})
        if not rf.get("where"):
            raise SystemExit("cast-bank entry %s has no real_footage.where (the person's clip folder)" % cid)
        roles[bid] = rf
    return roles


def role_for(cast, roles, lead, said="", *texts):
    """Who plays a shot: the part its line names (real_footage.plays), else the first cast id its own texts name in
    order (the shot's picture text first, then the scene's "who"), else the lead."""
    said = (said or "").lower()
    by_part = sorted((said.find(w), b) for b, rf_ in roles.items() if b != lead
                     for w in (rf_.get("plays") or {}) if w and said.find(w) >= 0)
    if by_part:
        return by_part[0][1]
    for text in texts:
        hit = next((b for b in cast if re.search(r"\b%s\b" % re.escape(b), str(text or ""), re.I)), None)
        if hit:
            return hit
    return lead


STILLS = (".jpg", ".jpeg", ".png", ".heic", ".webp")


TO_CAMERA = ("to the camera", "into the camera", "at the camera and talk", "at the camera and speak",
             "addresses the camera", "talking head", "talks to camera", "speaks to camera", "speaking to camera",
             "talking to camera", "vlog", "explains", "talks about", "speaks about", "discusses", "interview",
             "continues talking", "presenter", "presents", "follow-up question", "asks a question", "the script",
             "podcast", "microphone", "on stage", "lecture", "speak", "talk", "convers", "advice", "asking",
             "reports", "explain", "says", "saying", "responding", "sentence", "discuss", "delivers", "concludes", "emphasiz", "a take about", "monologue")


def to_camera(shows):
    """A clip of a person talking to us (a talking-head take), by its library description."""
    t = str(shows or "").lower()
    return any(w in t for w in TO_CAMERA)


PERSON = ("man", "men", "woman", "women", "person", "people", "guy", "girl", "boy", "he ", "she ", "his ", "her ",
          "group", "couple", "crowd", "someone", "presenter", "subject")
DARK = ("dark", "dimly", "dim ", "black screen", "cuts to black", "blurry", "empty", "silhouette", "night")


def face_ok(shows, face_words):
    """A shot with a person in it shows the cast member (his description words), or no face words are set."""
    if not face_words:
        return True
    t = " " + str(shows or "").lower() + " "
    if not any((" " + w) in t or t.startswith(w) for w in PERSON):
        return True                                    # hands, a POV, an object: no face to match
    return any(w in t for w in face_words)


def dark(shows):
    t = str(shows or "").lower()
    return any(w in t for w in DARK)


def moving(h):
    """A video clip, never a still picture (a still is not b-roll): the index's kind, and the file's own extension."""
    return (h.get("kind") or "video") == "video" and not str(h.get("shared_path") or "").lower().endswith(STILLS)


class Matcher:
    """THE CAST MATCHER, shared by every Real-lane step (cast_picks here, the production chain's real_door): the asset
    index searched inside one person's footage only (search `where`, several scenes a clip), other brands' products
    refused, placed on a clean measured moment when the index has one, never on a stretch already used in this ad."""

    def __init__(self, brand, roots, used=None, product=None):
        self.brand, self.roots, self.product = brand, list(roots or []), product
        self.S, self.LB, self.MO = SF._search_mod(), SF._library_mod(), SF._moments_mod()
        self.used = list(used or [])                   # (file, in, out) stretches this ad already plays
        self.cache = {}

    def hits(self, q, where, need_words=None):
        k = (q, tuple(where), tuple(need_words or ()))
        if k not in self.cache:
            hs = SF.marked(self.S.search(q, brand=self.brand, per=200, where=where, scenes_per_clip=6), self.brand, self.LB)
            aw, af = (getattr(self, "avoid", {}) or {}).get(tuple(where), ((), ()))
            fw = (getattr(self, "faces", {}) or {}).get(tuple(where), ())
            self.cache[k] = [h for h in hs if moving(h)
                             # the cast-bank entry's own exclusions: what this person's folder holds that is not the
                             # story (another person's video, business footage, a screen recording)
                             and not any(w in (h.get("shows") or "").lower() for w in aw)
                             and not any(x.lower() in (h.get("shared_path") or "").lower() for x in af)
                             and not any(b in (h.get("shows") or "").lower() for b in OTHER_BRANDS)
                             # a line's shot shows the action its line says: a person talking to the camera is
                             # never the picture for a line he is not saying to us (owner, 21 Nov)
                             and not to_camera(h.get("shows"))
                             # every face on screen is the cast: in a folder that also holds other people, a shot with
                             # a person in it must describe this person (real_footage.face_words); hands, POV and
                             # objects pass. A dark or empty shot never carries a line (owner, 21 Nov)
                             and face_ok(h.get("shows"), fw) and not dark(h.get("shows"))
                             and not SF.off_product(h.get("shared_path") or "", self.product)
                             and (not need_words or any(w in (h.get("shows") or "").lower() for w in need_words))]
        return self.cache[k]

    def place(self, cands, need):
        """(hit, file, start) of the best candidate whose `need` seconds are free, or None."""
        for h in sorted(cands, key=lambda h: -h["score"]):
            if not SF.tone_ok(h.get("shows"), getattr(self, "feeling", None)):
                continue                               # positive imagery never over negative words, nor the reverse
            f = SF.local_file(h, self.roots)
            if not f and h.get("shared_path") and not str(h["shared_path"]).startswith("Shared Assets/"):
                f = h["shared_path"]                   # another footage root the brand lists: the cut reads it by range
            if not f:
                continue
            start = float(h.get("in") or 0)
            path = h.get("shared_path")
            if self.MO and path and self.MO.known(self.brand, path):
                got = self.MO.place(self.brand, path, start, need, None,
                                    avoid=[(a, b) for ff, a, b in self.used if ff == f])
                if got:
                    start = got[0]
            if any(ff == f for ff, _a, _b in self.used):
                continue                               # ONE USE PER CLIP (owner, 21 Nov): a clip file plays once per ad
            return h, f, start
        return None

    def take(self, f, start, need):
        self.used.append((f, start, start + need))

    def queries(self, *texts):
        return [q for q in (_words(t) for t in texts) if q]

    def find(self, role, roles, lead, need, texts, feeling=None):
        """THE ROLE'S MOMENT for a shot: that person's footage on the shot's own words; when it is spent, the lead's
        own moments on the same words (reacting), then the lead's plain moments. -> (hit, file, start, who) or None."""
        qs = self.queries(*texts)
        rf = roles[role]
        self.feeling = feeling                         # the emotion map's feeling for this shot (shot_fill.tone_ok)
        got = self.place([h for q in qs for h in self.hits(q, rf["where"], rf.get("only_scenes_with"))], need)
        who = role
        if not got and role != lead:
            got = self.place([h for q in qs + fallback(roles[lead])
                              for h in self.hits(q, roles[lead]["where"], roles[lead].get("only_scenes_with"))], need)
            who = lead + " (reacting, %s's line)" % role
        if not got:
            got = self.place([h for q in fallback(roles[lead]) for h in self.hits(q, roles[lead]["where"], None)], need)
            who = lead + " (another moment of his)"
        return (got + (who,)) if got else None


def run(n, dry=False):
    B = ST.BRIEFS / n
    brief = json.load(open(B / "brief.json"))
    cast = brief.get("real_cast") or {}
    if not cast:
        raise SystemExit("brief.json has no real_cast: name the production's real cast (brief cast id -> cast-bank id)")
    cfg = brief.get("shot_fill") or {}
    brand = cfg.get("brand")
    roles = roles_of(brand, cast)
    lead = next(iter(cast))
    import song_view as SV
    wb = SV.brief_of(Path(ST.WRITING) / str(brief.get("brief") or "")) or {}
    who = {s.get("id"): str(s.get("who") or "") for s in wb.get("scenes") or []}
    timing = {}
    try:
        import video_studio as VS
        _sb, srun = VS.song_of(n)
        if srun and (Path(srun) / "song" / "timing.json").is_file():
            timing = json.load(open(Path(srun) / "song" / "timing.json"))
    except Exception:  # noqa: BLE001 — an unsung ad: the rows' own phrases
        timing = {}
    rows = json.load(open(B / "shot-list.json"))["shots"]
    roots = cfg.get("library_roots") or []
    pk = json.load(open(B / "picks.json")) if (B / "picks.json").exists() else {"shots": {}, "sources": {}}
    pk.setdefault("shots", {}), pk.setdefault("sources", {})
    def mine(v):                                       # a pick this step (or a drafted search pick) made: replaceable
        return bool(v.get("drafted")) or str(v.get("by") or "").startswith(("cast pick", "lyric pick"))
    sl_rows = json.load(open(B / "shot-list.json"))["shots"]
    beats = SF.said_beats(n, [dict(r) for r in sl_rows], brief, cfg)   # the emotion map: picture + feeling per shot
    M = Matcher(brand, roots, [(pk["sources"].get(v["source"]), float(v.get("in") or 0), float(v.get("in") or 0) + 2.0)
                               for k, v in pk["shots"].items() if not mine(v)], product=cfg.get("product"))
    M.avoid = {tuple(rf["where"]): (tuple(w.lower() for w in rf.get("avoid_words") or ()), tuple(rf.get("avoid_files") or ()))
               for rf in roles.values()}
    M.faces = {tuple(rf["where"]): tuple(w.lower() for w in rf.get("face_words") or ()) for rf in roles.values()}
    placed, open_ = {}, []

    for r in rows:
        if r["id"] in pk["shots"] and not mine(pk["shots"][r["id"]]):
            continue                                   # a person's own pick stays
        sid = r["scene"]
        # who is IN this shot: the part its line names (the cast-bank entry's real_footage.plays: "the trainer", "my
        # girl"), else the person its own picture text names first, else the scene's cast in order, else the lead
        mid0 = float(r.get("at") or 0) + (float(r.get("seconds") or 2.0) + 0.1) / 2
        said = (_line_at(timing, mid0) if timing else (r.get("phrase") or ""))
        role = role_for(cast, roles, lead, said, r.get("shows"), who.get(sid, ""))
        need = float(r.get("seconds") or 2.0) + 0.1
        mid = float(r.get("at") or 0) + need / 2
        line = _line_at(timing, mid) if timing else (r.get("phrase") or "")
        beat = beats.get(r["id"]) or {}
        got = M.find(role, roles, lead, need, tuple(x for x in (beat.get("picture"), line, r.get("shows")) if x),
                     feeling=beat.get("feeling"))
        if not got:
            # no unused clip of the cast shows it: the beat plays on as the shot before it (swipe_cut: join), never a
            # clip the ad already plays nor a stranger's face (owner, 21 Nov)
            open_.append(r["id"])
            placed[r["id"]] = {"join": True, "by": BY, "role": role, "note": "joined: no unused clip of %s shows '%s'"
                               % (role, line[:40])}
            continue
        h, f, start, by_role = got
        M.take(f, start, need)
        key = "L-" + hashlib.md5(f.encode()).hexdigest()[:8]
        pk["sources"][key] = f
        placed[r["id"]] = {"source": key, "in": start, "by": BY, "role": by_role.split(" ")[0], "role_note": by_role,
                           "note": "%s · %s (on '%s'; library %.2f)" % (by_role, (h.get("shows") or "")[:80], line[:40], h["score"])}
    pk["shots"].update(placed)
    pk["real_cast"] = cast
    # the cut's cast gate (swipe_cut.cast_check): role -> the creator's folder name, from the person's clip folder
    folder = lambda w: [p for p in w.strip("/").split("/") if p][-1]  # noqa: E731
    pk.setdefault("people", {})["cast"] = {b: folder(roles[b]["where"][0]) for b in cast}
    if not dry:
        json.dump(pk, open(B / "picks.json", "w"), indent=1, ensure_ascii=False)
    from collections import Counter
    print("cast: " + ", ".join("%s=%s" % kv for kv in cast.items()))
    print("placed %d · open %d · %s" % (len(placed), len(open_), dict(Counter(v.get("role_note", "joined") for v in placed.values()))))
    if open_:
        print("open: " + ", ".join(open_))
    return placed, open_


if __name__ == "__main__":
    run(sys.argv[1], dry="--dry-run" in sys.argv)
