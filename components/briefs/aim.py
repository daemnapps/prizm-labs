#!/usr/bin/env python3
"""WHO A BRIEF IS FOR, read back off what is on file: one brief key in, its aim out.

    import aim
    aim.aim_of("<brand>", "<brief key>")     {avatar, sub, demographic, desire, awareness, stage, doubt, claim, from, conflicts}
    ix = aim.Aims("<brand>")                 read once, then ix.of(key) for many briefs (a report, an index)

    python3 components/briefs/aim.py <brief key or number> --brand <b>

The fields are the ones every writing run stamps (components/creative-strategist/machine/who.py `stamp`). Each field is
the first answer on file, else None; `from` says which file answered:

  1 the brief's own record   naming's brief_record: sub_avatar, moves.face, moves.awareness, angle (the claim), avatar
  2 a run's `aim`            the runs behind the brief, writing first, then the runs they were made from
  3 those runs' older fields declared_audience, audience, market_state
  4 its sprint's ad fields   sprint.json beside the run (sub, awareness, desire)

A source that names another avatar than the one already answered is skipped whole and listed in `conflicts`: one
avatar's sub-avatar or desire is never lent to another. A run written for another product is not read. Nothing is guessed, nothing is written, brands/ is only read.
Python 3.9.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))
import briefs_index as BI  # noqa: E402

FIELDS = ("avatar", "sub", "demographic", "desire", "awareness", "stage", "doubt", "claim")
ORDER = ("video-writing", "image-writing", "outlier-brief", "copywriter", "ad-variations", "ad-volume", "image-teardown",
         "video-teardown", "video-production", "image-production", "video-edit", "image-edit")
LOOSE = ("image-writing", "outlier-brief", "copywriter", "ad-variations", "ad-volume")  # no place in the briefs index: only an explicit brief_key counts
OTHER_AD = ("copied_from", "forked_from", "branched_from")      # a run made from another AD: that ad's person is not this one's
LEVEL = re.compile(r"\b(?:(problem|solution|product|most)[\s-]?aware|unaware)\b", re.I)


def sub_id(v):
    """A sub-avatar's id from its id or its file name (`sub-03-x` is `x`); None for the avatar itself."""
    s = re.sub(r"^sub-\d+-", "", str(v or "").strip())
    return None if s.lower() in ("", "none", "core", "null") else s


def level(v):
    """The awareness level a field states, or None when it states none or two."""
    if isinstance(v, dict):
        v = v.get("awareness")
    got = {(m.group(1).lower() + "-aware") if m.group(1) else "unaware" for m in LEVEL.finditer(str(v or ""))}
    return got.pop() if len(got) == 1 else None


def text(v):
    s = " ".join(str(v).split()) if isinstance(v, (str, int, float)) else ""
    return s if s and s.lower() not in ("none", "null", "open") else None


def tidy(d):
    """One source's fields in the stamp's shape. A demographic of `none` is an answer: no face on screen."""
    face = " ".join(str(d.get("demographic") or "").split()) or None
    out = {"avatar": text(d.get("avatar")), "sub": sub_id(d.get("sub")), "demographic": face, "awareness": level(d.get("awareness"))}
    out.update({k: text(d.get(k)) for k in ("desire", "stage", "doubt", "claim")})
    return out


def from_record(rec):
    """The brief's own record: the brand's header over the register entry."""
    mv = rec.get("moves") if isinstance(rec.get("moves"), dict) else {}
    a = rec.get("aim") if isinstance(rec.get("aim"), dict) else {}
    return tidy({"avatar": rec.get("avatar") or a.get("avatar"), "sub": rec.get("sub_avatar") or mv.get("who") or a.get("sub"),
                 "demographic": mv.get("face") or a.get("demographic"), "awareness": rec.get("awareness") or mv.get("awareness") or a.get("awareness"),
                 "desire": rec.get("desire") or a.get("desire"), "stage": a.get("stage"), "doubt": rec.get("doubt") or a.get("doubt"),
                 "claim": rec.get("claim") or a.get("claim") or rec.get("angle")})


def from_older(d):
    """The fields a writing run kept before it stamped an aim."""
    g = lambda k: d.get(k) if isinstance(d.get(k), dict) else {}                                          # noqa: E731
    dec, aud, ms = g("declared_audience"), g("audience"), g("market_state")
    return tidy({"avatar": dec.get("avatar") or aud.get("_avatar") or aud.get("avatar"),
                 "sub": dec.get("sub") or aud.get("_sub_avatar") or aud.get("sub_avatar"),
                 "awareness": dec.get("awareness") or ms.get("awareness"), "desire": ms.get("lead_desire"), "stage": ms.get("sophistication")})


class Aims:
    """One brand's briefs, with the runs behind each, read once."""

    def __init__(self, brand, repo=None):
        self.brand, self.repo = brand, Path(repo or BI.REPO)
        self.N, self.reg = BI.names(self.repo), BI.Register(self.repo)
        self._raw = BI._read(self.repo / "components" / "image-teardown" / "briefs.json") or {}
        self.runs, self._docs = {}, {}
        for p in BI.place_runs(self.repo, self.reg, brand=brand):
            if p["register"]:
                self.runs.setdefault(p["register"], []).append(p["folder"])
        for st in LOOSE:
            for f in sorted((self.repo / "runs" / st / brand).glob("*/run.json")):
                d = BI._read(f)
                k = self.reg.lookup(d.get("brief_key")) if isinstance(d, dict) and d.get("brief_key") else None
                if k:
                    self.runs.setdefault(k, []).append(BI.rel(f.parent, self.repo))

    def register_key(self, key):
        k = self.reg.lookup(key)
        if k and self.reg.rows[k].get("brand") in (self.brand, None):
            return k
        num = self.N.brief_number(key)
        q = self.N.parse_brief_key(key)
        hits = self.reg.by_number(self.brand, num, None if not q or q[1] == "none" else q[1]) if num else []
        return hits[0] if len(hits) == 1 else None

    def record(self, key, rk=None):
        """The brief's own record: the brand's header over the register entry, as naming's brief_record merges them. A
        number two briefs share is settled by the register key, else it is no answer."""
        q = self.N.parse_brief_key(key)
        product = q[1] if q and q[1] != "none" else None
        c = self.N.brief_candidates(self.brand, q[2] if q and product is None else key, product, self._raw)
        hit = ([x for x in c if rk and (x["register"] or {}).get("key") == rk] or (c if len(c) == 1 else [None]))[0]
        if not hit:
            return {}
        head = {k: v for k, v in (hit["header"] or {}).items() if v not in (None, "")}
        return {**(hit["register"] or {}), **head}

    def docs(self, folder):
        """[(record path, run record)] of one run folder."""
        if folder not in self._docs:
            got = [(BI.rel(f, self.repo), BI._read(f)) for f in BI.records(self.repo / folder)]
            self._docs[folder] = [(p, d) for p, d in got if isinstance(d, dict)]
        return self._docs[folder]

    def folders(self, rk):
        """The run folders behind one brief: the register's own run, the placed ones writing first, then what each was made from."""
        own = str((self.reg.rows.get(rk) or {}).get("run") or "").rstrip("/")
        first = [own] if BI.RUN_PATH.search(own) and (self.repo / own).is_dir() else []
        rank = {s: i for i, s in enumerate(ORDER)}
        out = first + sorted(set(self.runs.get(rk) or []) - set(first), key=lambda f: (f.split("/")[-1] != own.split("/")[-1], rank.get(f.split("/")[1], 99), f))
        for f in out:                                  # grows while it is read: the runs each run was made from
            if len(out) > 60:
                break
            for _, d in self.docs(f):
                for st, b, lab in BI._linked({k: v for k, v in d.items() if k not in OTHER_AD}, self.repo):
                    g = "runs/%s/%s/%s" % (st, b, lab)
                    if b == self.brand and g not in out and (self.repo / g).is_dir():
                        out.append(g)
        return out

    def same_product(self, rk, d):
        """False when the run was written for another product than the brief's (a body cut filed on a face brief)."""
        mine, its = (self.reg.rows.get(rk) or {}).get("product"), d.get("product")
        if not mine or not isinstance(its, str):
            return True
        pid = lambda p: self.N.product_id(self.brand, p) or p                                              # noqa: E731
        return pid(mine) == pid(its)

    def sprint(self, folder, d):
        """The sprint ad this run was made for, when its record names the sprint."""
        lab, ad = d.get("sprint"), str(d.get("ad") or d.get("pick") or "")
        sp = BI._read(self.repo / Path(folder).parent / str(lab) / "sprint.json") if lab else None
        if not isinstance(sp, dict):
            return None
        hit = next((a for a in sp.get("ads") or [] if isinstance(a, dict) and str(a.get("id")) == ad), None)
        if not hit:
            return None
        return tidy({"avatar": hit.get("avatar") or sp.get("avatar"), "sub": hit.get("sub"), "demographic": hit.get("demographic"),
                     "awareness": hit.get("awareness"), "desire": hit.get("desire"), "doubt": hit.get("doubt"), "claim": hit.get("claim")})

    def of(self, key):
        out = dict({k: None for k in FIELDS}, **{"from": {}, "conflicts": []})

        def take(src, where):
            if out["avatar"] and src["avatar"] and src["avatar"] != out["avatar"]:
                if where not in [c["source"] for c in out["conflicts"]] and any(src[k] for k in FIELDS[1:]):
                    out["conflicts"].append({"source": where, "avatar": src["avatar"]})
                return
            for k in FIELDS:
                if out[k] is None and src[k] is not None:
                    out[k], out["from"][k] = src[k], where

        rk = self.register_key(key)
        take(from_record(self.record(key, rk)), "brief record")
        runs = [(f, p, d) for f in (self.folders(rk) if rk else []) for p, d in self.docs(f) if self.same_product(rk, d)]
        for _, p, d in runs:
            if isinstance(d.get("aim"), dict):
                take(tidy(d["aim"]), p + " aim")
        for _, p, d in runs:
            take(from_older(d), p)
        for f, p, d in runs:
            s = self.sprint(f, d)
            if s:
                take(s, p + " sprint")
        return out


def aim_of(brand, brief_key, repo=None, index=None):
    """One brief's aim (the fields above, None where nothing on file says). `index`: an Aims already read."""
    return (index or Aims(brand, repo)).of(brief_key)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("key")
    ap.add_argument("--brand", required=True)
    a = ap.parse_args(argv)
    print(json.dumps(aim_of(a.brand, a.key), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
