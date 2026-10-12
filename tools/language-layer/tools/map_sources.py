#!/usr/bin/env python3
"""Give every language row a source id by the Naming Standard, and write the
brand's source registry.

    python3 tools/map_sources.py --brand B --dry-run   # the mapping and the hand calls left, nothing written
    python3 tools/map_sources.py --brand B             # propose source fields + the registry; the gatherer applies them
    python3 tools/map_sources.py --brand B --propose-only   # the proposal under runs/, nothing applied

Source ids — the type first, `_` between values, `-` inside one
(tools/language-layer/docs/STANDARD.md, "5 · Sources" and "Verified"):

  survey_<brand>_<survey>                 question = q-<nn>_<question>
  post_<platform>_<account>_<post id>     tiktok video id · instagram numeric media id · facebook post id
  ticket_<brand>_<system>                 review_<site>_<whose>
  community_<site>_<room>                 community_<site>_several  (+ rooms)
  copy_<brand>_<what>                     our own brand-written lines
  database_<brand>_<name>                 interview_<brand>_<date> · panel_<brand>_<date>

Fields written on `source`: id, kind, property (account or brand), property_raw,
item (the platform's own raw id), question, hand (firsthand | secondhand),
rooms. `ref` never points at a laptop. A row that already has a source id on
the standard keeps it. What the rules cannot decide comes from
brands/<brand>/core-avatars/language-sources-lookup.json (hand calls, each
citing where it was read); anything still undecided is listed, never guessed.
The registry: brands/<brand>/core-avatars/language-sources.json — generated.

`brands/` is read-only to machines (decision-log 2026-09-17): the source fields
and the registry are written as a PROPOSAL under
runs/language-layer/<brand>/sources-<date>/ and handed to the research
gatherer's apply step (`gather.py apply --proposal …`), the one machine ruled
to write the bank. The rows still left for a hand call are listed there too
(`hand-calls.json`).
"""
import argparse, collections, json, re, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import engine as E  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_names import check_source_id  # noqa: E402
from language_layer import proposal as P  # noqa: E402
from label import open_run, finish  # noqa: E402

IG = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def slug(s, n=48):
    s = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")
    return s[:n].rstrip("-")


def account(h):
    return slug((h or "").lstrip("@").replace(".", "-").replace("_", "-"), 40)


def ig_media_id(code):
    n = 0
    for ch in code[:11]:
        n = n * 64 + IG.index(ch)
    return str(n)


def clean_ref(ref):
    ref = str(ref or "")
    if ref.startswith("/Users/"):
        m = re.search(r"/devel/daemn/(.*)$", ref)
        return ("damon-sandbox:" + m.group(1)) if m else "local file (path withheld)"
    return ref


def mapper(brand):
    lk_file = E.bank_dir(E.brand_dir(brand)) / "language-sources-lookup.json"
    lk = json.loads(lk_file.read_text()) if lk_file.exists() else {}
    posts = {k.lower(): v for k, v in (lk.get("posts") or {}).items()}
    qnum = collections.defaultdict(dict)

    def question(sid, q):
        d = qnum[sid]
        if q not in d:
            d[q] = len(d) + 1
        return f"q-{d[q]:02d}_{slug(q, 60)}"

    def m(r):
        s = r.get("source") or {}
        name, ref, t = s.get("name") or "", str(s.get("ref") or ""), (s.get("type") or "").lower()
        low = name.lower()
        if s.get("id") and not check_source_id(s["id"]):
            return None                                           # already on the standard
        # a hand call first
        for key, v in posts.items():
            if key in low:
                return dict(id=f"post_{v['platform']}_{account(v['account'])}_{v['item']}", kind="post",
                            property=account(v["account"]), property_raw=v["account"], item=v["item"],
                            hand=v.get("hand", "firsthand"),
                            ref=f"https://www.tiktok.com/@{v['account']}/video/{v['item']}" if v["platform"] == "tiktok" else clean_ref(ref))
        mm = re.search(r"tiktok\.com/@([\w.]+)/video/(\d+)", ref)
        if mm:
            return dict(id=f"post_tiktok_{account(mm.group(1))}_{mm.group(2)}", kind="post",
                        property=account(mm.group(1)), property_raw=mm.group(1), item=mm.group(2), hand="firsthand")
        mm = re.search(r"instagram\.com/(?:p|reel)/([\w-]+)", ref)
        if mm or ("instagram" in low and re.search(r"-([A-Za-z0-9_-]{11})", ref)):
            code = mm.group(1) if mm else re.search(r"-([A-Za-z0-9_-]{11})", ref).group(1)
            who = re.search(r"@([\w.]+)", name)
            acct = who.group(1) if who else brand
            return dict(id=f"post_instagram_{account(acct)}_{ig_media_id(code)}", kind="post",
                        property=account(acct), property_raw=acct, item=code, hand="firsthand")
        mm = re.search(r"facebook\.com/(?:([\w.]+)/posts|reel)/(\d+)", ref)
        if mm:
            acct = mm.group(1) or brand
            return dict(id=f"post_facebook_{account(acct)}_{mm.group(2)}", kind="post",
                        property=account(acct), property_raw=acct, item=mm.group(2), hand="firsthand")
        if t == "survey":
            # a survey is named by the sheet it came from when there is one —
            # one sheet, one survey, however the rows spelled its title
            sheet = re.search(r"([\w-]+)\.csv", ref)
            head = sheet.group(1) if sheet else re.sub(r"\(.*?\)", "", re.split(r"\s+[—-]\s+|\s+Q:", name)[0])
            survey = slug(re.sub(r"(?i)\bsurvey\b", "", head))
            sid = f"survey_{brand}_{survey}"
            q = re.search(r"Q:\s*(.+)$", name) or re.search(r"Q:\s*(.+)$", ref)
            return dict(id=sid, kind="survey", property=brand, hand="firsthand",
                        question=question(sid, q.group(1).strip()) if q else None)
        if t == "ticket" or "gorgias" in low:
            return dict(id=f"ticket_{brand}_gorgias", kind="ticket", property=brand, hand="firsthand")
        if t in ("interview",) or "interview" in low:
            d = re.search(r"(\d{4}-\d{2}-\d{2})", ref) or re.search(r"(\d{4}-\d{2}-\d{2})", name)
            return dict(id=f"interview_{brand}_{d.group(1) if d else 'undated'}", kind="interview", property=brand, hand="firsthand")
        if t in ("panel",) or "panel" in low or "focus group" in low:
            d = re.search(r"(\d{4}-\d{2}-\d{2})", name) or re.search(r"(\d{4}-\d{2}-\d{2})", ref)
            return dict(id=f"panel_{brand}_{d.group(1) if d else 'undated'}", kind="panel", property=brand, hand="firsthand")
        if t == "review" or "review" in low:
            site = "amazon" if "amazon" in low else slug(low.split()[0])
            whose = "competitor" if "competitor" in low else brand
            return dict(id=f"review_{site}_{whose}", kind="review", property=whose,
                        hand="secondhand" if "secondhand" in low else "firsthand")
        if t == "database":
            return dict(id=f"database_{brand}_{slug(re.split(r'[(—]', name)[0], 40)}", kind="database", property=brand, hand="firsthand")
        subs = re.findall(r"r/(\w+)", name)
        if subs:
            if len(set(subs)) > 1:
                return dict(id="community_reddit_several", kind="community", property="reddit",
                            rooms=sorted(set(subs)), hand="secondhand" if "secondhand" in low or "bank" in ref else "firsthand")
            return dict(id=f"community_reddit_{account(subs[0])}", kind="community", property="reddit", hand="firsthand")
        if (r.get("speaker") or "") in ("brand", "creator"):
            return dict(id=f"copy_{brand}_{slug(name, 40)}", kind="copy", property=brand, hand="firsthand")
        dom = re.search(r"([a-z0-9-]+\.(?:org|com|net))", low)
        named = re.search(r"forum\s*[—-]\s*([A-Za-z][\w.]*)", name)
        if dom or named:
            site = slug(dom.group(1) if dom else named.group(1), 30)
            several = "communities" in low or site in ("forums", "forum")
            room = "guide" if "guide" in low else "forum"
            return dict(id=f"community_{'web' if several else site}_{'several' if several else room}", kind="community",
                        property="web" if several else site, hand="secondhand" if "secondhand" in low else "firsthand")
        return {"unresolved": f"{t or 'no type'} · {name[:80]}"}
    return m


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--dry-run", action="store_true", help="print the mapping and the hand calls; write nothing, not even a proposal")
    ap.add_argument("--propose-only", action="store_true", help="write the proposal under runs/ and stop — nothing applied")
    ap.add_argument("--run", default=None)
    a = ap.parse_args(argv)
    m = mapper(a.brand)
    base = E.bank_dir(E.brand_dir(a.brand))
    reg, left, bad, n = {}, collections.Counter(), collections.Counter(), 0
    hand = []
    files = []
    for lang in E._lang_dirs(a.brand):
        if lang.is_dir():
            files += [f for f in sorted(lang.rglob("*.json")) if E.USED_DIR not in f.relative_to(lang).parts]
    folder = open_run(a.brand, "sources", a.run)
    prop = P.Proposal(a.brand, "language-layer tools/map_sources.py", folder)
    for f in files:
        raw = f.read_text()
        try:
            d = json.loads(raw)
        except Exception:
            continue
        for i, e in enumerate(d.get("entries") or []):
            got = m(e)
            s = dict(e["source"]) if isinstance(e.get("source"), dict) else {}
            before = dict(s)
            if got is None:
                pass
            elif "unresolved" in got:
                left[got["unresolved"]] += 1
                hand.append(dict(id=e.get("id"), file=P.rel(f), source=before, text=(e.get("text") or "")[:200]))
                if str(s.get("ref") or "").startswith("/Users/"):
                    s["ref"] = clean_ref(s["ref"])
            else:
                why = check_source_id(got["id"])
                if why:
                    bad[f"{got['id']} — {why}"] += 1
                    continue
                ref = got.pop("ref", None)
                s.update({k: v for k, v in got.items() if v is not None})
                s["ref"] = ref or clean_ref(s.get("ref"))
                n += 1
            if s != before:
                prop.row(f, i, e, source=s)
            sid = s.get("id")
            if sid:
                g = reg.setdefault(sid, dict(id=sid, kind=s.get("kind"), property=s.get("property"),
                                             rows=0, first=None, last=None, hand=s.get("hand")))
                g["rows"] += 1
                dt = str(s.get("date") or s.get("said") or "")[:10]
                if dt:
                    g["first"] = min(filter(None, [g["first"], dt])); g["last"] = max(filter(None, [g["last"], dt]))
    own = set()
    oa = E.brand_dir(a.brand) / "channels" / "own-accounts.json"
    if oa.exists():
        j = json.loads(oa.read_text())
        own = {account(x) for x in (j.get("names") or []) + (j.get("handles") or [])} | {a.brand}
    for g in reg.values():
        g["owner"] = "ours" if (g.get("property") or "") in own or g["kind"] in ("survey", "ticket", "database", "interview", "panel", "copy") else "theirs"
    print(f"{n:,} rows mapped · {len(prop.rows):,} rows changed · {len(reg)} sources · "
          f"{sum(left.values())} rows left for a hand call · {sum(bad.values())} off standard")
    for k, v in left.most_common(20):
        print(f"  HAND CALL ({v} rows): {k}")
    for k, v in bad.most_common(10):
        print(f"  OFF STANDARD ({v}): {k}")
    if a.dry_run:
        return 0
    prop.whole(base / "language-sources.json", dict(
        _what="Every source this brand's language bank draws from — generated by tools/language-layer/tools/map_sources.py; never hand-edited.",
        brand=a.brand, built=date.today().isoformat(),
        sources=sorted(reg.values(), key=lambda g: -g["rows"])))
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "hand-calls.json").write_text(json.dumps(hand, indent=1, ensure_ascii=False) + "\n")
    return finish(prop, a, dict(rows_mapped=n, rows_changed=len(prop.rows), sources=len(reg),
                                rows_left_for_a_hand_call=sum(left.values()), off_standard=sum(bad.values())),
                  [f"HAND CALL ({v} rows): {k}" for k, v in left.most_common(12)])


if __name__ == "__main__":
    sys.exit(main())
