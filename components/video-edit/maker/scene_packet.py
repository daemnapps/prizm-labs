#!/usr/bin/env python3
"""The scene packet: every clip of a hand-off carries every reference it needs, as a file, and one full prompt that
names each of them by number (VIDEO-RULINGS V53, V59; 2026-11-25).

    python3 components/video-edit/maker/scene_packet.py <hand-off folder> [--check]

Why: a song ad's clips were handed over with their people, place, product and look attached; every other ad's clips
were handed over with the swipe's frames attached and the rest only named ("cast sheet", "cast:<name>"). On 0333 the
product's sheet sat in the folder and on no clip, and the start pictures were written with the hand left empty, so the first
clips came back with no product in them. One packet, built the same way for every clip of every ad, closes that.

Runs at the end of the hand-off build (maker_pack.py), on the finished folder: reads clips.json, elements.json,
run.json and the written brief in brief/; writes refs/<clip>/ files, `packet` on each clip, a "Scene packet" block
under each clip in CLIPS.md, and the references and prompts on run.json's steps. Safe to run again. Spends nothing,
deletes nothing. `--check` writes nothing and lists what is missing.

A packet row: {"role": person|product|place|prop|look, "name", "file" (in the folder, or None), "state"
(here | made in step N | words only), "use"}. `missing` lists what stops the clip: a person or the product with no file
and no step that makes it, or no prompt.
"""
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIC = (".png", ".jpg", ".jpeg", ".webp")

# the brief's old product words (V58 photoreal: "laid on at the edit", the hand left open). In a made shot the product is
# in the picture, so the words say so. Each one is only ever applied with the product's own sheet attached.
LAID_ON = re.compile(r"[;,.]?\s*(?:all\s+)?(?:owned footage or\s+)?laid on (?:in|at) the edit\b[^.;]*?(?:never generated|real (?:product )?(?:photo|photos|footage))\b"
                     r"(?:[,—–\- ]*never generated)?|[;,.]?\s*owned footage, never generated|[,—–\- ]*never generated", re.I)
OPEN_HAND = [
    (re.compile(r"(?:with )?(?:its|the|his|her|their) grip (?:is )?(?:left )?open(?P<at> on [\w' ]{2,30}?)? for (?:the real |the )?(?P<p>[^,.;]+?)(?= held| with|,|\.|;|$)", re.I),
     r"holding the \g<p>\g<at>"),
    (re.compile(r"grip (?:left )?open for (?:the real )?product laid on at the edit", re.I), "gripping the product"),
    (re.compile(r"\bholding the (?P<p>[^,.;]+?) held\b", re.I), r"holding the \g<p>"),
    (re.compile(r"holding the (?P<p>[\w' ]+?)'s place\b", re.I), r"holding the \g<p>"),
    (re.compile(r"palms set as if holding a box", re.I), "holding the product's box"),
    (re.compile(r",?\s*the (?:space between them|[\w ]{0,24}space(?: in (?:his|her|their) hands)?) (?:left )?clear for the real (?P<p>[^,.;]+)", re.I), r", the \g<p> between them"),
    (re.compile(r"the clear box space", re.I), "the box"),
    (re.compile(r"the space in (?:his|her|their) hands", re.I), "the box in the hands"),
    (re.compile(r"with its top clear where (?P<p>the [^,.;]+?) is laid on (?:at|in) the edit", re.I), r"with \g<p> standing on it"),
    (re.compile(r",?\s*(?:its|the product's) place (?:is )?(?:still )?(?:left )?clear(?: for the real [^,.;]+?)?(?: laid on (?:at|in) the edit)?(?=,|\.|;|$)", re.I), ", the product in place"),
]
OPEN_HAND += [
    (re.compile(r"\baround (?:an )?empty space(?: for (?:the |a )?[^,.;]+)?", re.I), "around the product"),
    (re.compile(r"\bthe space inside (?:it|them) left clear", re.I), "the product inside it"),
    (re.compile(r"\bReserve (?P<z>[^.;]*?) for (?:the )?(?P<p>complete|real|whole|front)", re.I), r"\g<z> holds the \g<p>"),
    (re.compile(r"\bReserved (?P<p>[\w -]+?) positions? occup(?:y|ies)", re.I), r"The \g<p> occupies"),
    (re.compile(r"\ban? (?:clear|empty|clear empty|bare) (?:area|space|placement area) remains\b", re.I), "the product stands"),
    (re.compile(r"\b(?:the )?(?:clear|empty|reserved) placement (?:area|space) occupies", re.I), "The product occupies"),
    (re.compile(r"\bClear space beside (?P<w>(?:her|his|their) (?:left|right) hand) occupies", re.I), r"The product in \g<w> occupies"),
    (re.compile(r",?\s*with space beneath the fingers reserved for tracked real texture", re.I), ", the product's real texture under the fingers"),
    (re.compile(r"(?P<a>\b[Tt]he [\w' ]{0,24}area) is reserved for (?:the )?real (?:tracked )?(?P<t>[\w ]{0,20}texture)"), r"\g<a> shows the product's real \g<t>"),
    (re.compile(r"\b[Tt]he (?:[\w' ]{0,24})?(?:area|side) (?:on|at) (?P<w>[\w'’]+ (?:left|right)) remains clear for the later product(?: composition)?"), r"The product stands on \g<w>"),
    (re.compile(r"\bthe clear spot where (?P<p>[^,.;]+?) stands", re.I), r"\g<p> standing there"),
    (re.compile(r"\ba clear space where (?P<p>[^,.;]+?) (?:stands|sits|is)\b", re.I), r"\g<p>"),
    (re.compile(r"\btrack(?:ed)? (?=real |the )", re.I), ""),
]
# a whole sentence that only speaks of laying the product on later
LATER = re.compile(r"[^.;/]*\b(?:never generate|real editorial overlay|composite|foreground occlusion|added only at the edit|no generated product)\b[^.;/]*[.;]?", re.I)
STILL_EMPTY = re.compile(r"laid on (?:in|at) the edit|grip (?:left )?open|(?:left|remains?|is|stays?) clear for (?:the )?(?:real |later )?product|place (?:left )?clear for the real"
                         r"|empty (?:hand|space|placement)|(?:real-)?product composite|added (?:only )?at the edit|reserved? for (?:the )?(?:real|tracked)|never generated?\b", re.I)


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _slug(x):
    return re.sub(r"[^a-z0-9]+", "-", str(x).lower()).strip("-")


def brief_doc(out):
    """The written brief as data (brief/<key>-brief.md), {} when it has none."""
    for f in sorted((Path(out) / "brief").glob("*-brief.md")):
        for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", f.read_text(encoding="utf-8", errors="ignore"), flags=re.S):
            try:
                d = json.loads(m.group(1))
            except ValueError:
                continue
            if isinstance(d, dict) and d.get("scenes"):
                return d
    return {}


def in_scene_words(text):
    """A start picture's or shot's words with the product in them, never an empty hand waiting for it."""
    t = str(text or "")
    for rx, to in OPEN_HAND:
        t = rx.sub(to, t)
    t = LATER.sub("", LAID_ON.sub("", t))
    return re.sub(r"holding the ([^,.;]+?) holding the \1", r"holding the \1", re.sub(r"\s+([,.;])", r"\1", t)).strip()


def _scene_ids(text):
    """'S1–S14, S17, S24a' -> {'S1', …, 'S14', 'S17', 'S24a'}."""
    got = set()
    for tok in re.split(r"[,;·]", str(text or "")):
        tok = tok.strip()
        m = re.match(r"^S(\d+)\s*[–—-]\s*S(\d+)$", tok)
        if m:
            got |= {"S%d" % i for i in range(int(m.group(1)), int(m.group(2)) + 1)}
        else:
            got |= set(re.findall(r"\bS\d+[A-Za-z]?(?:\.\d+(?:-\d+)?)?\b", tok))
    return got


def _halves(sc):
    s = sc.get("split") or {}
    return [h for h in (s.get("left"), s.get("right"), s.get("top"), s.get("bottom")) if isinstance(h, dict)]


def _frames(sc):
    return [f for f in [sc.get("first_frame")] + [h.get("first_frame") for h in _halves(sc)] if isinstance(f, dict)]


def _shots(sc):
    return list(sc.get("shots") or []) + [s for h in _halves(sc) for s in h.get("shots") or []]


class Pack(object):
    """One hand-off folder, read once."""

    def __init__(self, out, ws=None):
        self.out = Path(out)
        self.ws = Path(ws) if ws else HERE.parents[2]
        self.clips = _load(self.out / "clips.json", {}) or {}
        self.sheet = _load(self.out / "run.json", {}) or {}
        self.rows = _load(self.out / "elements.json", []) or []
        self.doc = brief_doc(self.out)
        self.brand = self.clips.get("brand") or self.sheet.get("brand") or self.out.parent.name
        self.style = self.clips.get("style") or (self.doc.get("piece") or {}).get("style_id")
        self.scenes = {s.get("id"): s for s in self.doc.get("scenes") or []}
        self.was = {}                               # a joined scene's shot keeps the shot it was written as
        for m in (self.doc.get("piece") or {}).get("make_list") or []:
            if m.get("shot") and m.get("was_shot"):
                self.was[str(m["shot"])] = str(m["was_shot"])
        self.bank = self._bank()

    # ── the banks ────────────────────────────────────────────────────────────────────────────────────────────────
    def _bank(self):
        try:
            import importlib.util as iu
            sp = iu.spec_from_file_location("scene_packet_style_chain",
                                            str(self.ws / "components" / "video-production" / "styles" / "style_chain.py"))
            m = iu.module_from_spec(sp)
            sp.loader.exec_module(m)
            return m
        except Exception:  # noqa: BLE001 — no style chain here: the folder's own files stand alone
            return None

    def banked(self, kind, eid):
        """An element's own folder and picture in the ad's style; a style the bank does not know is the filmed look, the
        element's master. -> (folder, picture) or (None, None)."""
        if not (self.bank and eid):
            return None, None
        try:
            r = self.bank.resolve(self.brand, kind, eid, self.style)
            if r.get("state") in ("master", "have") and r.get("picture"):
                return Path(r["dir"]), Path(r["picture"])
            return None, None
        except SystemExit:                          # an unknown style id stops the style chain; it never stops a packet
            pass
        except Exception:  # noqa: BLE001
            return None, None
        try:
            home = Path(self.bank.element_home(self.brand, kind, eid))
            pic = self.bank.picture_of(home) if home.is_dir() else None
            return (home, Path(pic)) if pic else (None, None)
        except (Exception, SystemExit):  # noqa: BLE001
            return None, None

    def owned(self, kind, name):
        """The picture we already own of a place or a prop of exactly this name (its slug, an article aside), straight
        from the brand's bank, whatever the ad's style: a file beats words. Never a near name. None when there is none."""
        s = re.sub(r"^(?:the|a|an)-", "", _slug(name))
        bank = self.ws / "runs" / "ai-elements" / str(self.brand) / ("sets" if kind == "set" else "props")
        for eid in (s, "the-" + s, "a-" + s) if s else ():
            home = bank / eid
            for pick in ([home / ("picture" + x) for x in PIC] if kind == "prop" else
                         [home / "plates" / ("wide" + x) for x in PIC] + [home / ("master" + x) for x in PIC]):
                if pick.is_file():
                    return pick
        return None

    def product(self):
        """(slug, name, its one sheet on this machine or in the folder, its size, the words that mean it). The sheet is
        the product's only reference (ruled 2026-11-23): never a packshot set, never old CGI."""
        slug = self.sheet.get("product") or (self.doc.get("piece") or {}).get("product") or ""
        if isinstance(slug, dict):
            slug = slug.get("id") or ""
        for sc in self.scenes.values():             # the brief's own shot records carry the product's id
            for sh in _shots(sc):
                p = (sh.get("subjects") or {}).get("product")
                if isinstance(p, dict) and p.get("id"):
                    slug = p["id"]
                    break
        for r in self.rows:                         # the banked row (the style chain's) is named by the slug
            if r.get("kind") == "product" and (self.ws / "runs" / "ai-elements" / self.brand / "products" / str(r.get("element"))).is_dir():
                slug = r["element"]
        kit = self.ws / "runs" / "ai-elements" / self.brand / "products" / str(slug)
        k = _load(kit / "kit.json", {}) or {}
        name = next((sh["subjects"]["product"].get("name") for sc in self.scenes.values() for sh in _shots(sc)
                     if isinstance((sh.get("subjects") or {}).get("product"), dict) and sh["subjects"]["product"].get("name")), None) \
            or str(slug).replace("-", " ")
        files = []
        pic = self.banked("product", slug)[1]
        if pic and "sheet" in pic.name:
            files.append(pic)
        files.append(kit / "model" / "product-sheet.png")
        files += [self.out / f for r in self.rows if r.get("kind") == "product" for f in r.get("files") or [] if "sheet" in Path(f).name]
        files += sorted((self.out / "refs").glob("product-*-sheet.png"))
        sheet = next((f for f in files if f.is_file()), None)
        size = k.get("size_cm") or {}
        size = ("%g cm tall, %g cm wide" % (size["height"], size["width"])) if isinstance(size, dict) and size.get("height") and size.get("width") else ""
        words = {str(a).lower() for a in k.get("aliases") or []} | {str(slug).replace("-", " ").lower()}
        words |= {w.lower() for w in re.findall(r"\b[A-Z]{3,}\b", str(name))}
        noun = re.findall(r"[a-z]+", str(k.get("what") or "").lower())
        if noun:                                    # "the brush", "the tube": only with its article, never a wooden brush
            words.add("the " + noun[-1])
        self.box = any("box" in f.name.lower() or "packag" in f.name.lower() for d in ("sources", "model", "box") for f in (kit / d).glob("*") if f.suffix.lower() in PIC)
        return {"slug": str(slug), "name": re.sub(r"[™®]", "", str(name)).strip(), "file": sheet, "size": size,
                "words": {w for w in words if len(w) > 2}, "cannot": ((k.get("behaviour") or {}).get("cannot") or [])[:3]}

    def others(self, text, first):
        """Every other product of the brand these words put in the shot, each with its own sheet (2026-11-25: a scene that
        names the scrub and the blue cream was given the scrub's sheet alone, and the cream was never in the picture)."""
        bank = self.ws / "runs" / "ai-elements" / str(self.brand) / "products"
        kits = {d.name: (_load(d / "kit.json", {}) or {}) for d in sorted(bank.glob("*")) if (d / "model" / "product-sheet.png").is_file()}
        look = {n: str(k.get("what") or "").lower() for n, k in kits.items()}
        got = []
        for n, k in kits.items():
            if n == first:
                continue
            tail, kind = n.split("-")[-1], (re.findall(r"[a-z]+", look[n]) or [""])[-1]
            colour = re.match(r"the ([a-z]+) ", look[n])
            own = [r"\b%s\b" % re.escape(n.replace("-", " "))]
            if colour and colour.group(1) != "cream" and list(look.values()).count(look[n]) == 1 and not any(m != n and look[m].startswith("the %s " % colour.group(1)) for m in look):
                own.append(r"\b%s (?:\w+ )?(?:%s|%s)\b" % (colour.group(1), re.escape(tail), re.escape(kind)))
            if any(re.search(x, text, re.I) for x in own) or any(re.search(r"\b%s\b" % re.escape(str(a).upper()), text) for a in k.get("aliases") or [] if len(str(a)) > 2):
                z = k.get("size_cm") or {}
                z = " (%g cm tall, %g cm wide)" % (z["height"], z["width"]) if isinstance(z, dict) and z.get("height") and z.get("width") else ""
                got.append((n.replace("-", " "), bank / n / "model" / "product-sheet.png", z))
        return got

    def person(self, c, sc, said=""):
        """A cast member's own sheets: (files in order, state). A banked one's headshot and the look the scene says; a
        new one's sheet, made in the run sheet's own cast step."""
        name = c.get("name") or c.get("id")
        for st in self.sheet.get("steps") or []:
            if st.get("cast_sheet") and re.search(r"cast sheet for %s\b" % re.escape(str(name)), st.get("what") or "", re.I):
                return [("returned/" + st["asset"], "made in step %d" % st["n"])]
        bid = c.get("bank_id")
        if bid and str(bid).upper() != "NEW":
            d, pic = self.banked("person", bid)
            if pic:
                got = [next((f for f in (d / "headshot.jpg", d / "headshot.png") if f.is_file()), pic)]
                try:
                    lk = d / self.bank.look_sheet(d, sc.get("id"), said)
                    if lk.is_file() and lk not in got:
                        got.append(lk)
                except (Exception, SystemExit):  # noqa: BLE001 — no look sheet here: the master carries them
                    pass
                return [(f, "here") for f in got]
        el = next((r for r in self.rows if r.get("kind") == "person" and _slug(r.get("element")) == _slug(name)
                   and "BANKED" in str(r.get("status")) and r.get("files")), None)
        return [(self.out / f, "here") for f in el["files"][:2]] if el else []

    # ── one clip ─────────────────────────────────────────────────────────────────────────────────────────────────
    def scene_of(self, c):
        for s in (c.get("brief_scene"), c.get("scene")):
            if s in self.scenes:
                return self.scenes[s]
        return {}

    def shots_of(self, c):
        """The brief's shots this clip makes: its own one when the scene's clips and shots are one to one, else all."""
        sc = self.scene_of(c)
        shots = _shots(sc)
        mine = [x for x in self.clips.get("clips") or [] if (x.get("brief_scene") or x.get("scene")) == sc.get("id") and x.get("tool") != "edit"]
        if sc and len(mine) > 1 and shots:
            ids = [x["id"] for x in mine]
            if all(x.get("part") for x in mine):                # parts of one shot: all of them are that shot
                return shots
            nos = [x.get("shot_nos") or [i] for i, x in enumerate(mine, 1)]
            if max(max(n) for n in nos) == len(shots):          # its own shots, by number
                return [shots[n - 1] for n in nos[ids.index(c["id"])]]
            if len(shots) >= len(mine):                         # more shots than clips: each clip its own share, in order
                k, n, m = ids.index(c["id"]), len(mine), len(shots)
                return shots[k * m // n:(k + 1) * m // n]
        return shots

    def names_of(self, sh):
        i = str(sh.get("id") or "")
        return {x for x in (i, self.was.get(i)) if x}

    def covered(self, c):
        s = c.get("brief_scene") or c.get("scene")
        return {s, c.get("id")} | {x.split(".")[0] for sh in self.shots_of(c) for x in self.names_of(sh)}

    def product_in(self, sh):
        """What the brief says the product does in this one shot: [] when it is not in it. PRODUCT LOCK (and the shot's
        own `in_shot` copy of it) names shots; a line that names other shots only is not this shot's."""
        mine = self.names_of(sh)
        scenes = {x.split(".")[0] for x in mine}
        rec = (sh.get("subjects") or {}).get("product")
        lines = list((rec or {}).get("in_shot") or []) if isinstance(rec, dict) else []
        for line in self.doc.get("product_lock") or [] if isinstance(self.doc.get("product_lock"), list) else []:
            line = line if isinstance(line, str) else " ".join(str(v) for v in line.values())
            m = re.match(r"\s*(S\d+[A-Za-z]?)\b\s*:", line)
            if m and (m.group(1) in scenes or any(re.search(r"\b%s\b" % re.escape(x), line) for x in mine)):
                lines.append(line)
        got, one = [], r"S\d+[A-Za-z]?\.\d+"
        group = re.compile(r"(?:shots? )?(%s(?:\s*(?:,|and|to|–|—|-)\s*%s)*)" % (one, one))
        for line in lines:
            body = re.sub(r"^\s*S\d+[A-Za-z]?\s*:\s*", "", str(line))
            marks = list(group.finditer(body))
            parts = [(set(), body)] if not marks else []
            for i, g in enumerate(marks):
                ids = set(re.findall(one, g.group(1)))
                for x, y in re.findall(r"(%s)\s*(?:to|–|—|-)\s*(%s)" % (one, one), g.group(1)):
                    (st, n), last = x.rsplit(".", 1), y.rsplit(".", 1)[1]
                    ids |= {"%s.%d" % (st, k) for k in range(int(n), int(last) + 1)}
                parts.append((ids, body[g.end():marks[i + 1].start() if i + 1 < len(marks) else len(body)]))
            tail = ""                                # "S2.2, on its base …": words after the last group belong to it
            for ids, words in parts:
                if ids and not ids & mine:
                    continue
                w = in_scene_words(words).strip(" .;,:—–-·") or tail
                if w and w not in got:
                    got.append(w)
                elif not w and ids:
                    got.append("in this shot")
        return list(dict.fromkeys(got))

    def rows_for(self, kind, cov, names=()):
        names = {_slug(n) for n in names if n}
        return [r for r in self.rows if r.get("kind") == kind and
                (_slug(r.get("element")) in names if names else _scene_ids(r.get("scenes")) & cov)]

    def start_text(self, c):
        """The words of the moment the clip opens on: its own shot's start picture, else the scene's first frame."""
        sc, shots = self.scene_of(c), self.shots_of(c)
        sp = str((shots[0] if shots else {}).get("start_picture") or "first_frame").strip()
        if self.own_words(c) and c.get("recipe"):
            style = str((sc.get("first_frame") or {}).get("style") or (self.doc.get("piece") or {}).get("style") or "")
            return "\n".join(x for x in (in_scene_words(re.split(r"(?<=[.!?])\.?\s", str(c["recipe"]).strip())[0]), style) if x)
        if sp.startswith("from ") and len(sp) < 24:
            return "Opens exactly where shot %s ends: use that clip's last frame as the start picture." % sp[5:]
        if sp and sp != "first_frame":
            style = str((sc.get("first_frame") or {}).get("style") or (self.doc.get("piece") or {}).get("style") or "")
            return "\n".join(x for x in (in_scene_words(sp), style) if x)
        if sc.get("first_frame"):
            return self.frame_words(sc["first_frame"])
        return "\n\n".join("%s half: %s" % (("First", "Second")[min(i, 1)], self.frame_words(h.get("first_frame") or {}))
                           for i, h in enumerate(_halves(sc)) if h.get("first_frame"))

    @staticmethod
    def frame_words(ff):
        return "\n".join(x for x in (in_scene_words(ff.get(k)) for k in
                                     ("subject", "composition", "action", "location", "lighting", "camera", "style")) if x)

    def clip_packet(self, c):
        sc, cov, shots = self.scene_of(c), self.covered(c), self.shots_of(c)
        subj = [sh["subjects"] for sh in shots if isinstance(sh.get("subjects"), dict)]
        first = c.get("start_words") if c.get("song_at") else self.start_text(c)
        text = " ".join([str(sc.get("who") or ""), str(first or ""), str(sc.get("happens") or ""), str(c.get("recipe") or ""),
                         " ".join(c.get("who") or [])])
        rows, missing = [], []

        def put(role, name, f, state, use, **kw):
            rows.append(dict({"role": role, "name": name, "file": f, "state": state, "use": use}, **kw))
        # people: the shot's own record first, then the clip's, then the words
        rec = {}
        for s in subj:
            for p in s.get("people") or []:
                if isinstance(p, dict):
                    rec.setdefault(_slug(p.get("id") or p.get("name")), p)
        who = {_slug(w) for w in c.get("who") or []}
        known = bool(who) or any("people" in s for s in subj)
        for p in self.doc.get("cast") or []:
            name = p.get("name") or p.get("id") or ""
            ids = {_slug(name), _slug(p.get("id") or name)}
            if not name or not ((ids & (who or set(rec))) if known else re.search(r"\b%s\b" % re.escape(name), text, re.I)):
                continue
            said = next((rec[i].get("look") for i in ids if i in rec and rec[i].get("look")), "") or \
                next((v for k, v in (sc.get("looks") or {}).items() if _slug(k) in ids), "")
            files = self.person(p, sc, said)
            if not files:
                missing.append("%s: no sheet here and no step makes one" % name)
                put("person", name, None, "missing", "")
            worn = re.sub(r"^NEW:\s*", "", str(said or ""))
            for i, (f, state) in enumerate(files):
                put("person", name, f, state, "%s's %s%s" % (name, "face and body: keep this exact person" if i == 0 else "outfit for this scene",
                    (", wearing " + worn) if worn and len(files) == 1 else ""))
        # the product
        P = self.product()
        per = [self.product_in(sh) for sh in shots]
        where = list(dict.fromkeys(w for x in per for w in x))
        says = lambda t: any(re.search(r"\b%s\b" % re.escape(w), str(t or ""), re.I) for w in P["words"])  # noqa: E731
        named = says(first) or says(c.get("recipe") if c.get("song_at") else " ".join(str(sh.get("gestures")) + str(sh.get("ends_on")) for sh in shots))
        if not (shots or sc):
            named = named or bool(self.rows_for("product", cov))
        had = any(Path(r).name.startswith(P["slug"]) for r in c.get("refs") or []) if P["slug"] else False
        named = named or had                        # a song ad's clip already carried it
        at_start = bool((per and per[0]) or says(first) or (had and not per))
        shown = (bool(where) or named) and c.get("route") != "screen" and c.get("tool") != "edit"
        texture = bool(where) and all(re.search(r"no package|no container|texture|granular|scrub material|cream material", w, re.I) for w in where)
        if shown and texture:                        # only what it holds: the pack's sheet lays its label on the skin (0380 S4.2)
            put("product", P["name"], None, "texture only", "%s, only what it holds, no pack in this clip: %s" % (P["name"], " / ".join(where)),
                at_start=at_start, texture=True)
        elif shown and P["slug"]:
            if P["file"]:
                put("product", P["name"], P["file"], "here",
                    "%s%s: the one real product, the same shape, colour, size and label as on this sheet%s" % (
                        P["name"], " (%s)" % P["size"] if P["size"] else "",
                        (". Where it is: " + " / ".join(where)) if where else ""), at_start=at_start)
            else:
                missing.append("%s: the product is in this clip and it has no casting sheet" % P["name"])
                put("product", P["name"], None, "missing", "")
        if shown and not texture:
            text = " ".join([" ".join(where), str(first or ""), " ".join(str(sh.get("gestures")) + str(sh.get("ends_on")) for sh in shots)])
            for n, f, z in self.others(text, P["slug"]):
                put("product", n, f, "here", "%s%s: also in this clip, the real one, the same shape, colour, size and label as on this sheet" % (n, z),
                    at_start=at_start)
        for r in [x for x in rows if x["role"] == "product" and isinstance(x["file"], Path) and "sheet" in x["file"].name]:
            f = _front(r["file"])                    # its printed words: on the sheet they are too small for the model to read
            if f:
                rows.insert(rows.index(r) + 1, dict(r, name=r["name"] + " front", file=f, front=True, use=(
                    "%s from the front, big: every printed word on it exactly as here, letter for letter. It stays closed as here unless the words open it" % r["name"])))
        # the places, the opening one first
        places = [c["where"]] if c.get("where") else list(dict.fromkeys(
            [(s.get("place") or {}).get("id") for s in subj if (s.get("place") or {}).get("id")] or [sc.get("setting_id")]))
        if not [p for p in places if p]:
            loc = " ".join(str(f.get("location") or "") for f in _frames(sc))
            places = [r["element"] for r in self.rows if r.get("kind") == "setting" and re.search(r"\b%s\b" % re.escape(str(r["element"])), loc, re.I)][:1]
        for n, pl in enumerate([p for p in places if p]):
            f, state = self.banked("set", _slug(pl))[1], "here"
            if f is None:
                state = "words only"
                for r in [x for x in self.rows if x.get("kind") == "setting" and _slug(x.get("element")).replace("-", "") == _slug(pl).replace("-", "")]:
                    pics = [x for x in r.get("files") or [] if Path(x).suffix.lower() in PIC]
                    pick = next((x for x in pics if "-mid" in x), pics[0] if pics else None)
                    if pick:
                        f, state = self.out / pick, "here" if "BANKED" in str(r.get("status")) else "swipe frame"
            if f is None:                        # a swipe frame already here stays: it is the ad's own layout
                mine = self.owned("set", pl)
                f, state = (mine, "here") if mine else (f, state)
            is_ = next((str(s["place"].get("is") or "") for s in subj if (s.get("place") or {}).get("id") == pl), "")
            put("place", pl, f, state, ("the room (%s): keep its layout, surfaces and light" % pl if state == "here" else
                                        ("%s, the swipe's room, for layout and light only: never its people, product or words" % pl if f else
                                         "%s, built from the brief's words" % pl) + ((": " + in_scene_words(is_)) if is_ else "")), at_start=n == 0)
        # the props
        defs = {_slug(p.get("name")): p for p in self.doc.get("props") or [] if isinstance(p, dict)}
        names = list(dict.fromkeys([(p if isinstance(p, str) else p.get("id") or p.get("name")) for s in subj for p in s.get("props") or []]
                                   or (sc.get("props") or [])))
        for nm in [x for x in names if x]:
            d, f = defs.get(_slug(nm), {}), None
            for r in self.rows_for("prop", cov, [nm]):
                pics = [x for x in r.get("files") or [] if Path(x).suffix.lower() in PIC]
                if pics:
                    f, banked = self.out / next((x for x in pics if "-mid" in x), pics[0]), "BANKED" in str(r.get("status"))
            mine = None if f else self.owned("prop", nm)
            if mine:
                f, banked = mine, True
            put("prop", nm, f, ("here" if banked else "swipe frame") if f else "words only",
                "%s: %s" % (nm, "; ".join(x for x in (d.get("look"), d.get("size")) if x) or "as the brief names it"))
        # the look
        for r in [r for r in self.rows if r.get("kind") == "look" and "the ad's look" in str(r.get("element")) and r.get("files")][:1]:
            put("look", r["element"], self.out / r["files"][0], "here", "the ad's look, only how it is rendered: never its people, place or objects")
        return rows, missing, first

    # ── the words ────────────────────────────────────────────────────────────────────────────────────────────────
    def own_words(self, c):
        """Does this clip's own recipe say what it is? A scene made as more clips than the brief has shots: the scene's words
        on every clip made the same clip twice (0378 S3, paid for twice, 2026-11-25)."""
        sc = self.scene_of(c)
        mine = [x for x in self.clips.get("clips") or [] if (x.get("brief_scene") or x.get("scene")) == sc.get("id") and x.get("tool") != "edit"]
        words = [str(x.get("recipe") or "").strip() for x in mine]
        return bool(sc) and not c.get("part") and len(mine) > max(1, len(_shots(sc))) and all(words) and len(set(words)) == len(words)

    def share(self, c):
        """The sentences of the scene's words that fall in this clip's time, when its scene is more clips than shots."""
        sc = self.scene_of(c)
        mine = [x for x in self.clips.get("clips") or [] if (x.get("brief_scene") or x.get("scene")) == sc.get("id") and x.get("tool") != "edit"]
        said = re.split(r"(?<=[.!?])[\"”']?\s+", re.sub(r"\s+", " ", str(sc.get("voice") or "")).strip())
        if len(said) < 2 * len(mine):                          # few sentences: cut at the commas too
            said = re.split(r"(?<=[.!?,;])[\"”']?\s+", " ".join(said))
        total, every = sum(float(x.get("secs") or 1) for x in mine) or 1, sum(len(x.split()) for x in said) or 1
        ends, t = [], 0.0
        for x in mine:
            t += float(x.get("secs") or 1) / total
            ends.append((x["id"], t))
        got, w = [], 0
        for x in said:
            mid = (w + len(x.split()) / 2) / every
            w += len(x.split())
            if next((i for i, e in ends if mid <= e + 1e-9), ends[-1][0]) == c["id"]:
                got.append(x)
        return " ".join(got).strip()

    def motion_words(self, c):
        """What happens, from the brief's own shots (never the swipe's action: its person is using another product)."""
        sc, shots = self.scene_of(c), self.shots_of(c)
        every = _shots(sc)
        hap = str(sc.get("happens") or "")
        if len(shots) == 1 and len(every) > 1:       # the scene's "Shot k: …" lines: this clip's own one
            k = every.index(shots[0]) + 1
            m = re.search(r"^Shot %d:\s*(.+)$" % k, hap, re.M)
            thin = not any(v and not str(v).startswith("n/a") for v in (shots[0].get("face"), shots[0].get("gestures"), shots[0].get("ends_on")))
            hap = m.group(1) if m else (hap if thin or not re.search(r"^Shot \d+:", hap, re.M) else "")
        if 1 < len(shots) < len(every) and re.search(r"^Shot \d+:", hap, re.M):      # a joined clip: only its own shots' lines
            mine = {every.index(x) + 1 for x in shots}
            hap = "\n".join(x for x in hap.split("\n") if not re.match(r"Shot \d+:", x) or int(re.match(r"Shot (\d+):", x).group(1)) in mine)
        L = [in_scene_words(hap)] if hap.strip() else []
        if len(shots) > 1 and (c.get("joined") or len(c.get("shot_nos") or []) > 1):
            L.insert(0, "One take, %d shots in order, a hard cut between each, about %.1f seconds a shot. Same people, clothes and light all through." % (
                len(shots), float(c.get("secs") or 0) / len(shots)))
        if c.get("part"):
            k, n = c["part"]
            L.insert(0, "Part %d of %d of one shot%s." % (k, n, "" if k == 1 else ", carrying straight on from the part before: the same framing, place, light and clothes"))
            if not c.get("says"):
                L[0] += " The %s of the action." % ("start" if k == 1 else "end" if k == n else "middle")
        for sh in shots:
            says = " ".join(str(x.get("say") or "") for x in sh.get("lines") or [] if isinstance(x, dict)).strip()
            if c.get("part"):                                  # a part of a long shot says its own sentences only
                says = (str(c.get("says") or "") if sh is shots[0] else "")
            g = sh.get("gestures")
            g = "; ".join(g) if isinstance(g, list) else (g or "")
            bits = [", ".join(x for x in (sh.get("angle"), sh.get("camera_move") or "hold") if x) + "."]
            bits += ["%s: %s." % (w, in_scene_words(v).rstrip(".")) for w, v in (("Face", sh.get("face")), ("Hands", g), ("Ends on", sh.get("ends_on")))
                     if v and not str(v).startswith("n/a")]
            if says:
                bits.append(('Heard over it, nobody speaks on camera: "%s"' if over(sc) else 'Says: "%s"') % says)
            L.append("%s: %s" % (sh.get("id"), " ".join(bits)))
        for h in _halves(sc):
            L += ["%s: %s" % (b.get("shot") or "", in_scene_words(b["do"])) for b in h.get("beats") or [] if b.get("do")]
        return "\n".join(x for x in L if x and x.strip())


def _no_box(text, name):
    """The product's box has no sheet yet, so a box is never drawn: the product itself is what is held."""
    text = re.sub(r"\breads (?=it\b)", "looks at ", re.sub(r"\breading (?=the (?:\w+ )?box)", "looking at ", text or ""))
    return re.sub(r"\b(?:the |a )?(?:product's |real |[A-Z][\w™®]+ )?(?:product )?box\b(?!ing|er)", "the " + name, text) if text else text


def _front(sheet):
    """The product's front view cut big from its own casting sheet (video-production/machine/product_front.py), or None."""
    import importlib.util as iu
    try:
        f = Path(__file__).resolve().parents[2] / "video-production" / "machine" / "product_front.py"
        sp = iu.spec_from_file_location("sp_product_front", str(f))
        m = iu.module_from_spec(sp)
        sp.loader.exec_module(m)
        return m.front(sheet)
    except Exception:  # noqa: BLE001  no ffmpeg here, or a sheet that is not a picture: the sheet goes alone
        return None


def over(sc):
    """The scene's words are a read over the picture: nobody speaks on camera in it. Two people talking to each other do."""
    return sc.get("to_camera") is False and sc.get("kind") in ("broll", "card", "split")


def _bind(rows, first=1):
    """V53's one wording: every reference by its number and its job."""
    return ["Image %d is %s." % (i, r["use"].rstrip(".")) for i, r in enumerate(rows, first)]


def apply(out, ws=None, write=True):
    """Every clip's packet. -> {"clips": n, "ready": n, "missing": {clip: [..]}, "words_only": {clip: [..]}}"""
    P = Pack(out, ws)
    out = P.out
    miss, soft, done = {}, {}, 0
    steps = P.sheet.get("steps") or []
    for c in P.clips.get("clips") or []:
        if c.get("tool") == "edit":
            continue
        rows, missing, start = P.clip_packet(c)
        for r in rows:                               # every file into the clip's own folder
            f = r["file"]
            if isinstance(f, Path):
                if f.suffix.lower() not in PIC:
                    r["file"] = None
                    continue
                dst = out / "refs" / c["id"] / ("%s-%s-%s" % (r["role"], _slug(r["name"])[:30], re.sub(r"^.*?([^/]+)$", r"\1", f.name)))
                if f.resolve().parent == dst.parent.resolve():
                    dst = f
                elif write:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dst)
                r["file"] = "refs/%s/%s" % (c["id"], dst.name)
        sung = bool(c.get("song_at"))
        own = P.own_words(c)
        said = P.share(c) if own else ""
        motion = (in_scene_words(c.get("recipe")) + ((" Heard over it: " if over(P.scene_of(c)) or re.search(r"voice plays over|no people", str(c.get("recipe")), re.I) else " Says: ") +
                                                     '"%s"' % said if said else "")) if sung or own else (P.motion_words(c) or in_scene_words(c.get("recipe")))
        use = [r for r in rows if r["file"] and r.get("at_start", True)]
        prod = next((r for r in rows if r["role"] == "product" and r["file"]), None)
        if not (start or motion):
            missing.append("no words: the brief gives this clip no picture and no action")
        prods = [r for r in rows if r["role"] == "product" and r["file"]]
        held = ("The product in Image %d is really in this picture, at its true size, exactly where these words put it: a hand that holds it is never "
                "empty, and no other product appears%s." % (use.index(prod) + 1, "".join(" but the one in Image %d" % i for i, r in enumerate(use, 1)
                                                                  if r["role"] == "product" and r is not prod and not r.get("front")))) if prod in use else ""
        extra = ["%s." % r["use"].rstrip(".") for r in rows if (r["role"] in ("prop", "place") or r.get("texture")) and not r["file"] and r["use"]]
        c["packet"] = {
            "references": rows, "missing": missing,
            "start_prompt": "\n".join(x for x in _bind(use) + [start or ""] + extra + [held] if x),
            # the clip's own call: the finished start picture first, then the product's sheet (the editor's own fix on
            # 0333, made standard): the model sees the product from every side while it moves
            "clip_prompt": "\n".join(x for x in ["Image 1 is the first frame: keep this exact person, clothing, props, room and light."] +
                                     _bind(prods, 2) + [motion or ""] +
                                     (["Wherever this clip shows or uses the product it is the one in Image 2, the same object from the first frame "
                                       "to the last: never bare hands doing its job, never another product%s." % (" but " + ", ".join("the one in Image %d" % i for i, r in enumerate(prods, 2) if i > 2 and not r.get("front")) if any(not r.get("front") for r in prods[1:]) else "")] if prod else []) if x)}
        if prod and not getattr(P, "box", True) and re.search(r"\bbox\b", str(start) + " ".join(str(r["use"]) for r in rows if r["role"] == "product")):
            for k in ("start_prompt", "clip_prompt"):
                c["packet"][k] = _no_box(c["packet"][k], prod["name"])
            for r in rows:
                if r["role"] == "product":
                    r["use"] = _no_box(r["use"], prod["name"])
            c["packet"]["note"] = "the brief says its box; there is no box sheet, so the product itself is held"
        left = None if not any(r["role"] == "product" for r in rows) else STILL_EMPTY.search(c["packet"]["start_prompt"] + "\n" + c["packet"]["clip_prompt"])
        if left:
            missing.append("the words still leave the product out: “%s”" % left.group(0))
        if missing:
            miss[c["id"]] = missing
        lacking = [r["name"] for r in rows if r["role"] in ("place", "prop") and not r["file"]]
        if lacking:
            soft[c["id"]] = lacking
        done += not missing
        # an ordinary clip's recipe is our own action: the swipe's "does" (another product's use) stays under Swipe frames
        if not sung and motion and (not c.get("recipe") or str(c["recipe"]).startswith("Remake the swipe moment")):
            c["recipe"] = motion
        _onto_steps(P, c, use, prod, sung)
    if write:
        (out / "clips.json").write_text(json.dumps(P.clips, indent=1, ensure_ascii=False))
        _into_clips_md(out, P.clips)
        if steps:
            (out / "run.json").write_text(json.dumps(P.sheet, indent=1, ensure_ascii=False) + "\n")
    n = len([c for c in P.clips.get("clips") or [] if c.get("tool") != "edit"])
    return {"clips": n, "ready": done, "missing": miss, "words_only": soft}


def _onto_steps(P, c, use, prod, sung):
    """The same references and words on the run sheet's own steps, so the door sends them and nobody attaches by hand."""
    for st in [x for x in P.sheet.get("steps") or [] if isinstance(x, dict)]:
        m = re.search(r"(start picture|clip) for (\S+)", st.get("what") or "")
        if not m or m.group(2) not in (c["id"], c["id"].split("-shot-")[0] if c["id"].endswith("-shot-1") and
                                       len([x for x in P.clips["clips"] if (x.get("brief_scene") or x["scene"]) == (c.get("brief_scene") or c["scene"])]) == 1 else c["id"]):
            continue
        folder = ((P.sheet.get("handoff") or {}).get("folder")) or ""
        drive = ((P.sheet.get("handoff") or {}).get("drive")) or ""

        def ref(n, r, **kw):
            made = r["file"].startswith("returned/")
            d = {"n": n, "kind": "image", "role": r["use"], "element": None, "packet": r["role"]}
            if made:
                d.update(file="%s (%s)" % (Path(r["file"]).name, r["state"].replace("made in step", "step") + " makes it"), exists=False)
            else:
                d.update(local=r["file"], file="%s/%s" % (folder, r["file"]) if folder else r["file"], exists=True,
                         drive="%s/%s" % (drive, r["file"]) if drive else "")
            d.update(kw)
            return d
        if m.group(1) == "start picture":
            if sung:                                 # a song ad's start picture has its one print board already
                continue
            keep = [x for x in st.get("references") or [] if x.get("look_only") and not x.get("packet")]
            st["references"] = [ref(i, r, **({"look_only": True} if r["state"] == "swipe frame" else {})) for i, r in enumerate(use, 1)] + keep
            for i, x in enumerate(st["references"], 1):
                x["n"] = i
            sent = [r for r in use if r["state"] != "swipe frame"]
            if st.get("print"):
                st["print"]["reference"] = [x["file"] for x in st["references"] if not x.get("look_only")]
                # the print takes one picture: several go on one numbered board (make.py), so the words count the board's own
                words = c["packet"]["start_prompt"].split("\n")
                binds = _bind(sent)
                body = [x for x in words if not re.match(r"Image \d+ is ", x)]
                room = [r["use"].rstrip(".") + " (its frame shapes the 3D set, it is not on the board)." for r in use if r["state"] == "swipe frame"]
                if prod in sent:
                    body = [re.sub(r"The product in Image \d+", "The product in Image %d" % (sent.index(prod) + 1), x) for x in body]
                st["prompt"] = "\n".join(([("The reference is one board; its pictures are numbered left to right, top to bottom."
                                            if len(sent) > 1 else "")] + binds + body + room))
                st["prompt"] = "\n".join(x for x in st["prompt"].split("\n") if x)
            else:
                st["prompt"] = c["packet"]["start_prompt"]
            st["draft"] = False if c["packet"]["start_prompt"] else st.get("draft", True)
            st["prompt_source"] = "the scene packet: every reference by number, then the brief's first frame"
        else:
            refs = [x for x in st.get("references") or [] if x.get("packet") != "product"]
            if prod:                                 # the product's sheet goes to the clip model too, beside the start picture
                pos = 1 + len([x for x in refs if x.get("kind") == "image"])
                for x in refs:
                    if x.get("media_role") == "start_image":
                        x["media_role"] = "image_references"
                for k, r in enumerate([prod] + [x for x in use if x["role"] == "product" and x is not prod]):
                    refs.insert(len([x for x in refs if x.get("kind") == "image"]), ref(pos + k, r, media_role="image_references"))
                s = st.setdefault("settings", {})
                if str(s.get("endpoint") or "").endswith("image-to-video"):
                    s["endpoint"] = s["endpoint"].replace("image-to-video", "reference-to-video")
                for i, x in enumerate(refs, 1):
                    x["n"] = i
                st["references"] = refs
                if sung:
                    if "is the one real product" not in st.get("prompt", "") and "the one real product" not in st.get("prompt", ""):
                        st["prompt"] = "\n".join([st.get("prompt", "").split("\n")[0]] + _bind([prod], pos) + st.get("prompt", "").split("\n")[1:])
            if not sung:
                st["prompt"] = c["packet"]["clip_prompt"]
                st["draft"] = False if c["packet"]["clip_prompt"] else st.get("draft", True)
                st["prompt_source"] = "the scene packet: every reference by number, then the brief's own shots"


MARK = "**Scene packet**"
FIX = ("If it comes back wrong, do not make it again: open it in Higgsfield's Editing Room, pick only the bad seconds (4 at least), "
       "say what is wrong and what it should be. The rest of the clip, its sound and its length stay.")


def _into_clips_md(out, doc):
    f = Path(out) / "CLIPS.md"
    if not f.is_file():
        return
    by = {c["id"]: c for c in doc.get("clips") or [] if c.get("packet")}
    res, cur, skip = [], None, False
    for line in f.read_text(encoding="utf-8").split("\n"):
        h = re.match(r"### (\S+) · ", line)
        if line.startswith("#"):
            skip = False
            cur = h.group(1) if h else None
        if line.startswith(MARK):                    # an earlier run's block: written again below
            skip = True
            continue
        if skip and not line.startswith("<!-- /packet -->"):
            continue
        if line.startswith("<!-- /packet -->"):
            skip = False
            continue
        c = by.get(cur)
        if c and line.startswith("**Recipe (exact):** "):
            if not c.get("song_at"):
                continue                             # the packet's prompts are the words to send
        if c and line.startswith("- Also use: ") and not c.get("song_at"):
            near = [x for x in c.get("named_refs") or [] if x.startswith("our nearest clip")]
            if not near:
                continue                             # names with no file: the packet attaches the files
            line = "- Also use: " + ", ".join(near)
        if c and line.startswith("- Swipe frames: ") and not c.get("song_at"):
            line = line.replace("- Swipe frames: ", "- Swipe frames (framing and timing only; never upload as a person or product): ")
        res.append(line)
        if h and c:
            p = c["packet"]
            res += ["", MARK + (" · **NOT READY: " + "; ".join(p["missing"]) + "**" if p["missing"] else " · ready: attach these, send these words"), "",
                    "| Image | What | File |", "|---|---|---|"]
            n = 0
            for r in p["references"]:
                if r["file"]:
                    n += 1
                res.append("| %s | %s: %s | %s |" % (n if r["file"] else "–", r["role"], str(r["name"]).replace("|", "/"),
                           ("`%s`%s" % (r["file"], "" if r["state"] == "here" else " (%s)" % r["state"])) if r["file"] else r["state"]))
            res += ["", "Start picture:", "", "```", p["start_prompt"], "```", "", "Clip:", "", "```", p["clip_prompt"], "```", FIX, "<!-- /packet -->"]
    f.write_text(re.sub(r"\n{3,}", "\n\n", "\n".join(res)))


def main(argv=None):
    a = list(argv if argv is not None else sys.argv[1:])
    check = "--check" in a
    a = [x for x in a if not x.startswith("--")]
    if not a:
        raise SystemExit(__doc__.split("\n\n")[1])
    r = apply(a[0], write=not check)
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 1 if r["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
