#!/usr/bin/env python3
"""Rebuild a creator's briefs in the simplified shape (Damon's rulings, 2026-09-18).

    python3 simplify.py --brand <brand> --creator jeneeclaytonrdh    stage hers
    python3 simplify.py --brand <brand> --all                         every creator
    python3 simplify.py --brand <brand> --creator <h> --send          into her BRIEFS folder
    python3 simplify.py --brand <brand> --all --no-rerun              keep v5 concepts already written

Christine (18 Sep): the briefs overwhelm; one creator opted out, some went
silent; go back to the first brief's shape. Damon's rulings on the sample:
"I still want the separated briefs" · "we still want the script" · "remove
the image from the google doc itself" — no pictures at all.

So, per creator, her folder holds:

    Start here — <Brand> Content Brief — <Name>      the four shared sections, once
    <Concept> — <handle> · <brand> brief             one per video: the concept + the script
    <Concept> — inspiration video.mp4                the video the brief was built on

No pictures anywhere (Damon: "we literally don't need the pictures in the
google doc"). The inspiration is the source video itself — her own post on
the creator lane, the swipe on the general one — uploaded beside the brief
(Damon, 2026-09-18: "find the inspiration videos for each of these briefs
and put those in the folder too").

This does, for every run of hers that reached a final brief:

1. Rewrites the concept with stage 7b (v5): format · idea · two hooks · five
   beats · must-have shots · product points, then the script the machine
   lifts from the spec. Skipped when the run already holds a v5 concept.
2. Lays out the brief (gdoc.build) — words only.
3. Uploads. STAGED by default into work/<handle>/ on the Drive — unshared —
   so the result can be read first. `--send` updates the Doc she already has
   IN PLACE (same link, new contents, same title) and puts the Start-here Doc
   beside it in BRIEFS. Nothing is trashed.

The intro comes from `brands/<brand>/content-creators/brief-intro.md` (old: channels/creators/);
the concept from the machine; nothing here writes a word of its own.
"""
import argparse, json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain as C
import brand_folders as BF
import md as MD
import gdoc as G
import run as R

FRONT = re.compile(r"\A---\n.*?\n---\n", re.S)
LOG = C.runs_root() / "_simplified"


def say(m):
    print(m, flush=True)


def runs_for(brand, creator):
    """Her finished runs — or, with no creator, the brand's GENERAL briefs:
    swipe runs written to no one, for any creator to film."""
    out = []
    for rd in sorted(C.runs_root().iterdir()):
        rj = rd / "run.json"
        if not rj.is_file():
            continue
        try:
            st = json.loads(rj.read_text())
        except Exception:
            continue
        if st.get("brand") != brand:
            continue
        if creator:
            if (st.get("creator") or "") != creator:
                continue
        elif st.get("creator") or st.get("lane") != "swipe" \
                or (st.get("production_route") or "creator") == "ai":
            continue
        if not any((rd / c).is_file() for c in
                   ("stages/7-final-brief.md", "7-final-brief.md", "brief-final.md")):
            continue
        out.append((rd, st))
    return out


def creators_of(brand):
    seen = []
    for rd in sorted(C.runs_root().iterdir()):
        rj = rd / "run.json"
        if not rj.is_file():
            continue
        try:
            st = json.loads(rj.read_text())
        except Exception:
            continue
        who = st.get("creator")
        if who and st.get("brand") == brand and who not in seen and runs_for(brand, who):
            seen.append(who)
    return seen


def concept_ok(st):
    rec = (st.get("stages") or {}).get("stage7b") or {}
    return rec.get("status") == "done" and int(rec.get("version") or 0) >= 5


def rewrite_concept(rd, st):
    """Stage 7b, v5, through the machine's own stage runner — filled, sent
    and recorded exactly as a run would; the script block rides along."""
    plan = C.stages(st["brand"], st.get("asset_type", ""),
                    st.get("production_route") or "creator",
                    st.get("triage_lane") or "")
    stage = next((s for s in plan if s["key"] == "stage7b"), None)
    if not stage or int(stage.get("version") or 0) < 5:
        raise RuntimeError("stage 7b does not resolve to the v5 concept prompt")
    extras = {"video_count": "1",
              "brand_name": st["brand"].replace("-", " ").title(),
              "product": st.get("product") or product_of(rd, st)}
    R.RUNS = C.runs_root()
    if not R.run_stage(rd, st, stage, extras, redo=True):
        err = (st["stages"].get("stage7b") or {}).get("error", "")
        raise RuntimeError(f"stage 7b failed: {err[:200]}")
    R.save(rd, st)


def product_of(rd, st):
    """A run from before `--product` existed does not say which product it
    sells; its own spec does. The product folder whose name the spec uses
    most is the one — recorded on the run so it is never guessed twice."""
    base = C.WS / "brands" / st["brand"] / "products"
    slugs = [d.name for d in base.iterdir() if d.is_dir() and d.name != "reference"] if base.is_dir() else []
    if len(slugs) == 1:
        return slugs[0]
    spec = None
    for cand in ("stages/7-final-brief.md", "7-final-brief.md", "brief-final.md"):
        if (rd / cand).is_file():
            spec = (rd / cand).read_text().lower()
            break
    if not spec:
        return ""
    best, n_best = "", 0
    for slug in slugs:
        words = slug.replace("-", " ")
        n = spec.count(words)
        if n > n_best:
            best, n_best = slug, n
    if best:
        st["product"] = best
        R.save(rd, st)
    return best


def first_name(handle):
    """Her first name — from the tracker (creators.json, Christine's sheet)
    first, then her own profile in the creator library. Fancy unicode is
    flattened; a tracker row holding only a surname ("Patton") loses to the
    profile ("Mrs Patton" → the handle's own first name is not guessed)."""
    import unicodedata
    def plain(x):
        return re.sub(r"[^a-z0-9]", "", (x or "").lower())
    def first(x):
        x = unicodedata.normalize("NFKC", x or "").split("|")[0].strip()
        x = re.sub(r"[^\w' .-]", "", x).strip()
        toks = x.split()
        # "Mrs Patton" is how she names herself — keep it whole rather than
        # address her by a surname alone
        if len(toks) >= 2 and toks[0].lower().rstrip(".") in ("mrs", "mr", "ms", "dr"):
            return f"{toks[0].rstrip('.')} {toks[1]}"
        return toks[0].strip("'’.") if toks else ""
    cands = []
    try:
        for row in json.loads((C.MACHINE / "creators.json").read_text()):
            parts = [plain(x) for x in (row.get("url") or "").split("/")[3:]]
            if plain(handle) in parts and row.get("name"):
                cands.append(first(row["name"]))
    except Exception:
        pass
    try:
        prof = C.drive_root() / "lab" / "damon" / "creators" / handle / "profile.json"
        if prof.is_file():
            full = (json.loads(prof.read_text()).get("profile") or {}).get("fullName") or ""
            cands.append(first(full))
    except Exception:
        pass
    cands = [c for c in cands if c]
    if not cands:
        return handle
    for c in cands:
        if plain(c) and plain(handle).startswith(plain(c)):
            return c
    for c in cands:
        if " " in c:          # an honorific form beats a bare surname
            return c
    return cands[0]


def intro_html(brand, name, n, products, contact):
    f = BF.home(C.WS / "brands" / brand, "content-creators") / "brief-intro.md"
    if not f.is_file():
        raise RuntimeError(f"no shared intro for {brand}: {f}")
    body = FRONT.sub("", f.read_text(), count=1).strip()
    if name == "there":
        # the general brief is for anyone — nothing here is about her feed
        body = body.replace(
            "created specifically around your natural content style and real-life routines",
            "built on videos already working in our category — film them your way, in your own style")
    body = (body.replace("⟨name⟩", name).replace("⟨N⟩", str(n))
                .replace("⟨products⟩", products))
    if contact:
        body += f"\n\nQuestions on any of this? Email {contact} — we'll get you an answer.\n"
    html = MD.render(body)
    css = G.CSS.replace("h2{font-size:15pt;margin:18pt 0 4pt;page-break-before:always}",
                        "h2{font-size:15pt;margin:18pt 0 4pt}")
    return (f'<html><head><meta charset="utf-8"><title>intro</title>'
            f"<style>{css}</style></head><body>{html}</body></html>")


def brand_label(brand):
    """How the brand SPELLS ITS OWN NAME — read from the brand's folder, never
    typed here (rule 4; this used to be a two-brand map in the code).

    1. `brands/<brand>/brand.json` — `display_name` (or `name`), when the
       brand has one. That file is the intended home.
    2. else the brand's own `position.md` / `README.md` title, but ONLY when
       it is the same word as the folder name in another case — so a brand
       that writes itself in capitals keeps its capitals, and the Start-here
       Doc keeps the title it already has (same title = updated in place).
    3. else the folder name, title-cased."""
    home = C.WS / "brands" / brand
    try:
        meta = json.loads((home / "brand.json").read_text())
        name = str(meta.get("display_name") or meta.get("name") or "").strip()
        if name:
            return name
    except (OSError, ValueError, AttributeError):
        pass
    want = re.sub(r"[^a-z0-9]", "", brand.lower())
    for fname in ("brand-identity/position.md", "position.md", "README.md"):
        try:
            head = (home / fname).read_text().lstrip().splitlines()[0]
        except (OSError, IndexError):
            continue
        m = re.match(r"#\s+(.+?)(?:\s+[—–-]\s+.*)?$", head)
        if m and re.sub(r"[^a-z0-9]", "", m.group(1).lower()) == want \
                and m.group(1) != m.group(1).lower():
            return m.group(1).strip()
    return brand.title()


def contact_for(brand):
    f = BF.home(C.WS / "brands" / brand, "content-creators") / "contact.md"
    if not f.is_file():
        return ""
    t = f.read_text().strip()
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", t)
    # <brand>' file says OPEN and names an address it forbids printing
    return m.group(0) if (m and t.count("\n") < 3) else ""


def products_of(runs):
    names = []
    for rd, st in runs:
        p = (st.get("product") or "").replace("-", " ").title()
        if p and p not in names:
            names.append(p)
    return ", ".join(names) or "the products"


def staging_folder(who):
    """work/<handle>/PREVIEW — BRIEFS: a clean folder holding only what her
    BRIEFS folder would, so a preview reads like the real thing. Unshared."""
    import drive as _drive
    d = C.runs_mirror() / "work" / who
    d.mkdir(parents=True, exist_ok=True)
    parent = ""
    for attempt in range(10):
        parent = _drive.folder_id(d)
        if parent:
            break
        if attempt == 0:
            say("      waiting for the Drive to sync the staging folder …")
        time.sleep(6)
    if not parent:
        raise RuntimeError(f"the Drive never synced {d}")
    return _drive.folder("PREVIEW — BRIEFS", parent)


def doc_trashed(url):
    import drive as _drive
    m = re.search(r"/document/d/([A-Za-z0-9_-]+)", url or "")
    if not m:
        return False
    try:
        f = _drive.service().files().get(fileId=m.group(1), fields="trashed",
                                         supportsAllDrives=True).execute()
        return bool(f.get("trashed"))
    except Exception:
        return False


def example_link(video_url):
    """The last line of every brief: the example video, as a link."""
    if not video_url:
        return ""
    return ("## Example video\n\n[Watch the video this brief is built on]"
            f"({video_url}) — it's in your folder next to this brief.")


def inspiration_video(rd, st, home):
    """The video this brief was built on, beside it in the folder, named after
    the brief so the two sort together. Same name = updated in place.
    Returns (link, uploaded?) or (None, False) when the run has no video."""
    import drive as _drive
    src = rd / (st.get("source") or "source.mp4")
    if not src.is_file():
        return None, False
    name = R.doc_title(st).split(" — ")[0] + " — inspiration video" + src.suffix.lower()
    # already there at the same size → no re-upload (59 videos went up
    # twice on 2026-09-18 for a re-lay of the Docs alone)
    have = _drive.find_file(_drive.service(), name, home)
    if have:
        try:
            f = _drive.service().files().get(fileId=have["id"], fields="size",
                                             supportsAllDrives=True).execute()
            if int(f.get("size") or -1) == src.stat().st_size:
                return f"https://drive.google.com/file/d/{have['id']}/view", False
        except Exception:
            pass
    fid, new = _drive.upload_file(src, name, home)
    return f"https://drive.google.com/file/d/{fid}/view", new


def start_here(brand, who, home):
    """The one Start-here Doc in her folder: the brand's four shared sections,
    her name and how many briefs she has. Same name = updated in place."""
    import drive as _drive
    runs = [(rd, st) for rd, st in runs_for(brand, who)
            if not doc_trashed(st.get("gdoc_url") or "")]
    name = first_name(who) if who else "there"
    LOG.mkdir(parents=True, exist_ok=True)
    ih = LOG / f"{brand}-{who}-intro.html"
    ih.write_text(intro_html(brand, name, max(len(runs), 1), products_of(runs),
                             contact_for(brand)))
    title = (f"Start here — {brand_label(brand)} Content Brief — {name}" if who
             else f"Start here — {brand_label(brand)} Content Brief")
    return _drive.upload_doc(ih, title, home)


def build(brand, who, rerun=True, send=False):
    import drive as _drive
    runs = runs_for(brand, who)
    if not runs:
        say(f"  {who}: no finished runs")
        return None
    say(f"▶ {who} ({brand}) — {len(runs)} brief(s){' — SENDING' if send else ' — staged'}")
    home = _drive.creator_share(who, brand=brand)["briefs"] if send else staging_folder(who)
    name = first_name(who)
    made = {"creator": who, "brand": brand, "name": name, "sent": send,
            "intro": None, "briefs": [], "built": R.now()}

    url, new = start_here(brand, who, home)
    made["intro"] = url
    say(f"  Start here  {'created' if new else 'updated'} — {url}")

    for i, (rd, st) in enumerate(runs, 1):
        if rerun and not concept_ok(st):
            say(f"  {i}. {rd.name}: writing the concept (7b v5)")
            try:
                rewrite_concept(rd, st)
            except Exception as e:
                say(f"      FAILED — {str(e)[:160]}")
                made.setdefault("failed", []).append({"run": rd.name, "error": str(e)[:300]})
                continue
        elif not concept_ok(st):
            say(f"  {i}. {rd.name}: no v5 concept and --no-rerun — skipped")
            continue
        else:
            say(f"  {i}. {rd.name}: concept already v5")
        try:
            ids = G.ids_from_drive(rd.name)
        except Exception:
            ids = {}
        if send and doc_trashed(st.get("gdoc_url") or ""):
            # somebody retired this brief on purpose — a variant with a
            # newer run. Leave it retired: no rebuild, no video beside it.
            say(f"      brief is in the trash — retired by a person; left alone")
            continue
        # the video goes up first so the brief can end with a link to it
        vurl = None
        try:
            vurl, vnew = inspiration_video(rd, st, home)
            if vurl:
                st["video_url"] = vurl
                say(f"      video {'uploaded' if vnew else 'already there'} — {vurl}")
        except Exception as e:
            say(f"      video SKIPPED — {str(e)[:100]}")
        out, placed, missing = G.build(rd.name, ids, tail=example_link(vurl))
        st["gdoc_html"] = out.name
        btitle = R.doc_title(st)
        if send:
            burl, bnew = R.update_doc(st.get("gdoc_url") or "", out, btitle, home)
            st["gdoc_url"] = burl
        else:
            burl, bnew = _drive.upload_doc(out, btitle, home)
        R.save(rd, st)
        words = len((rd / st["stages"]["stage7b"]["out"]).read_text().split())
        made["briefs"].append({"run": rd.name, "title": btitle, "words": words,
                               "brief": burl, "video": vurl})
        say(f"      brief {'created' if bnew else 'updated'} — {words} words — {burl}")
        try:
            C.mirror_to_drive(rd.name)
        except Exception:
            pass
    (LOG / f"{brand}-{who}.json").write_text(json.dumps(made, indent=2))
    return made


def main():
    ap = argparse.ArgumentParser(description="Rebuild a creator's briefs in the simplified shape.")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--creator")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-rerun", action="store_true")
    ap.add_argument("--send", action="store_true",
                    help="update the Docs she already has, in her BRIEFS folder")
    a = ap.parse_args()
    if not (a.creator or a.all):
        ap.error("say who: --creator <handle> or --all")
    targets = [a.creator] if a.creator else creators_of(a.brand)
    for who in targets:
        build(a.brand, who, rerun=not a.no_rerun, send=a.send)


if __name__ == "__main__":
    main()
