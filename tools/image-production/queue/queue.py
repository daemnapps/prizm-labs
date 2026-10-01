#!/usr/bin/env python3
"""The production queue — RUN-01's state, what is left, and the steps.

    queue.py state            the whole picture as JSON
    queue.py plan             derive queue.json (fixes + missing pictures)
    queue.py run              work the queue (API door if a key exists, else hand the
                              generator list to a session via manual.md)
    queue.py intake <id> <png>   a generated picture arrives: pad, judge, name, record, upload
    queue.py review <asset> keep|kill [why]
    queue.py sync ["message"]  commit this lane's paths and push to damon/creative-record
    queue.py kit              the Meta bulk-import sheet + pictures folder

Damon never runs this. serve.py calls it from the page; a session calls it
from the terminal. Everything here is idempotent — run it twice, the second
run finds nothing to do.
"""
import datetime as dt, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[3]
RUNS_ROOT = WS / "image-production/runs/<brand>"
RUNS = ["ev-260907a", "gr-260907b", "gr-260907c"]
TARGET = 3
sys.path.insert(0, str(WS / "image-production/tools"))
sys.path.insert(0, str(WS / "components/naming"))
sys.path.insert(0, str(WS / "creative-ledger"))
sys.path.insert(0, str(WS / "components/video-teardown/machine"))


def _vault():
    """Every key lives in ~/.daemn/keys.env. Load it into the environment once,
    so the Drive pipe and the judge find their credentials without anyone
    exporting anything. Silent if the vault is not there — the callers already
    say what is missing."""
    import os
    try:
        import keys
    except Exception:
        return
    for k, v in (keys.all_keys() or {}).items():
        os.environ.setdefault(k, v)


_vault()
BAR_PARTS = ("90days", "ifyourskindoesnttransform", "fullrefund", "youkeeptheflex")
DRIVE_ROOT = "10m4iiEGrPQtivHBtINjf_NkUr-OajyWI"


def load(p, default):
    p = Path(p)
    return json.loads(p.read_text()) if p.is_file() else default


def save(p, d):
    Path(p).write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


def log(msg):
    line = f"{dt.datetime.now():%H:%M:%S} {msg}"
    with open(HERE / "log.txt", "a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower().replace("™", ""))


def bar_flag(bar):
    """The guarantee, word for word — anything else on a guarantee format is a flag."""
    b = norm(bar)
    if not b: return None
    if "doest" in b and "doesnt" not in b: return "bar typo: DOES'T"
    if b.count("ifyourskindoesnttransform") > 1: return "bar line printed twice"
    missing = [x for x in BAR_PARTS if x not in b]
    return f"bar incomplete — missing {', '.join(missing)}" if missing else None


# ------------------------------------------------------------------ state ---
def state():
    ocr = load(RUNS_ROOT / "_ocr.json", {})
    ids = load(RUNS_ROOT / "_drive-ids.json", {})
    slop = {k: v for k, v in load(HERE / "slop.json", {}).items() if not k.startswith("_")}
    review = load(HERE / "review.json", {})
    queue = {i["id"]: i for i in load(HERE / "queue.json", {"items": []})["items"]}
    meta = load(HERE / "meta" / "status.json", {})
    roster = {p["id"]: p for p in load(WS / "brands/<brand>/core-avatars/casting/roster.json", {"people": []})["people"]}
    units = []
    for run in RUNS:
        spec = load(RUNS_ROOT / run / "batch.json", {"ads": []})
        specs = {a["slug"]: a for a in spec["ads"]}
        for mf in sorted((RUNS_ROOT / run / "ads").glob("*/manifest.json")):
            m = load(mf, {}); slug = mf.parent.name; ad = specs.get(slug, {})
            rows = [r for r in m.get("ads", []) if (mf.parent / r["file"]).is_file()]
            a01 = ocr.get(rows[0]["file"], {}) if rows else {}
            assets = []
            for r in sorted(rows, key=lambda r: r["name"]):
                o = ocr.get(r["file"], {}); flags = []
                if r["file"] in slop: flags.append(slop[r["file"]])
                if o.get("headline") and a01.get("headline") and norm(o["headline"]) != norm(a01["headline"]) and r is not rows[0]:
                    flags.append(f"drifted — headline '{o['headline'][:40]}' ≠ a01")
                bf = bar_flag(o.get("offer_bar", "")) if m.get("format") not in ("apology", "captionbox", "commentreply", "routinelabel") else None
                if bf: flags.append(bf)
                v = review.get(r["name"], {})
                assets.append({"name": r["name"], "file": r["file"], "path": str((mf.parent / r["file"]).relative_to(WS)),
                               "headline": o.get("headline", ""), "bar": o.get("offer_bar", ""),
                               "drive": (ids.get(r["file"]) or {}).get("id"), "flags": sorted(set(flags)),
                               "verdict": v.get("verdict"), "why": v.get("why"), "qc": (r.get("qc") or {}).get("status", "pass")})
            kept = [a for a in assets if a["verdict"] != "kill" and not a["flags"]]
            have = len([a for a in assets if a["verdict"] != "kill"])
            need = max(0, TARGET - have)
            slopn = sum(1 for a in assets if a["flags"] and a["verdict"] != "kill")
            rejected = sorted(p.name for p in (mf.parent / "rejected").glob("*.png")) if (mf.parent / "rejected").is_dir() else []
            man = roster.get(m.get("talent"), {})
            q = [i for i in queue.values() if i["slug"] == slug and i["run"] == run]
            units.append({"run": run, "slug": slug, "ad_name": m.get("ad_name"), "man": f"{man.get('name', m.get('talent'))} {man.get('age', '')}".strip(),
                          "talent": m.get("talent"), "format": m.get("format"), "angle": m.get("angle"), "concept": m.get("concept"),
                          "headline": (ad.get("copy") or {}).get("headline") or a01.get("headline", ""), "sub": ad.get("sub"),
                          "have": have, "need": need, "slop": slopn, "assets": assets, "rejected": rejected,
                          "queue": [{"id": i["id"], "kind": i["kind"], "target": i["target"], "status": i["status"]} for i in q],
                          "meta": meta.get(m.get("ad_name"))})
    total_need = sum(u["need"] for u in units); total_slop = sum(u["slop"] for u in units)
    unreviewed = sum(1 for u in units for a in u["assets"] if not a["verdict"] and not a["flags"])
    gate = []
    if total_slop: gate.append(f"{total_slop} slop pictures to fix")
    if total_need: gate.append(f"{total_need} pictures still to make")
    if not (HERE / "kit").is_dir(): gate.append("Meta kit not built yet")
    gate.append("Meta: the main account is not on the connector — the kit goes in through Ads Manager's bulk import, in your Chrome")
    notes = []
    for u in units:
        for a in u["assets"]:
            if a["verdict"]:
                notes.append({"asset": a["name"], "unit": u["slug"], "man": u["man"], "format": u["format"], "headline": u["headline"],
                              "verdict": a["verdict"], "why": a["why"] or "", "at": review.get(a["name"], {}).get("at"), "path": a["path"]})
    notes.sort(key=lambda n: n["at"] or "", reverse=True)
    return {"stamp": dt.datetime.now().isoformat(timespec="seconds"), "target": TARGET, "notes": notes,
            "counts": {"units": len(units), "done": sum(1 for u in units if u["need"] == 0 and u["slop"] == 0),
                       "pictures": sum(u["have"] for u in units), "to_make": total_need, "slop": total_slop,
                       "unreviewed": unreviewed, "in_meta": sum(1 for u in units if u["meta"]),
                       "queued": sum(1 for i in queue.values() if i["status"] not in ("done",)),
                       "needs_session": sum(1 for i in queue.values() if i["status"] == "needs-session")},
            "gate": gate, "drive": DRIVE_ROOT, "units": units,
            "trash": load(RUNS_ROOT / "_drive-trash.json", []), "generator": "api" if _hf_key() else "session"}


def _hf_key():
    try:
        import hf; return bool(hf.key())
    except Exception:
        return False


# THE PRODUCT ELEMENT — ruled 2026-09-09 by Damon: "go look at the device. You
# already have that identity tied in Higgsfield. All you need to do is swap the
# device." A described device is a guessed device, and it guessed wrong for five
# days. The Element id goes in the prompt, always, for any format that shows it.
PRODUCT = "<<<8fad5612-d46f-4c19-baec-c3a636f22a4e>>>"
NO_PRODUCT = {"captionbox", "commentreply", "checklist"}
DEVICE = (f". The face-brush device is {PRODUCT} — that exact product, matched in shape, colour and finish, "
          "sized to the hand and gripped with the fingers wrapped around it. When it is pressed against the "
          "face, the BRISTLE side is the side touching the skin — so what the CAMERA sees is the smooth "
          "matte back of the pod with the hand over it, and the bristles are hidden against the cheek. "
          "Bristles facing the camera while the pod is on the skin is wrong")

# The skin has to look like the problem the copy names, and no worse. A render
# that overshoots into rash or wound is both unattractive and a Meta policy
# risk on shocking imagery (2026-09-10: the first re-do of Ray and Beto came
# back looking like a skin disease).
SKIN = (". Any razor bumps, ingrown hairs or dark marks are ordinary shaving irritation on otherwise "
        "healthy skin — small raised bumps and faded post-inflammatory marks along the jaw and neck. "
        "Not a rash, not a wound, not blood, not inflamed or weeping skin")
GUARANTEE = "90 DAYS. IF YOUR SKIN DOESN'T TRANSFORM, FULL REFUND. YOU KEEP THE FLEX™."


def fix_text(why):
    """The one change a fix asks for, in words the editor can act on."""
    w = why.lower()
    if "bar" in w or "does't" in w or "90days" in w:
        return ("The bottom guarantee bar must read exactly, on one clean strip, nothing outside it: "
                f"\"{GUARANTEE}\" — correct the spelling, put every word inside the bar, print it once.")
    if "grow grow" in w: return "On the poster card, the words 'grow grow' become 'grow' — one word, nothing else changes."
    if "!" in w: return "Remove the stray exclamation mark glyph; nothing else changes."
    if "wordmark" in w: return "Remove the <brand> FLEX wordmark; nothing else changes."
    out = "Fix only this, nothing else: " + why
    if re.search(r"bump|ingrown|mark|irritat|shav", why, re.I):
        out += SKIN
    return out


# ------------------------------------------------------------------- plan ---
def plan():
    """What the queue must make, slot by slot.

    A slot is (unit, aNN). It needs work when the picture is missing, when
    Damon killed it, or when it carries a flag. **A kill carries his words
    into the instruction** — the note lives in review.json, not on the
    picture, so it survives the picture being pulled out. The reference is
    the unit's own a01 when one is alive, else the killed frame itself
    (in killed/), because the picture was nearly right — one thing was wrong
    and he said what."""
    st = state(); old = {i["id"]: i for i in load(HERE / "queue.json", {"items": []})["items"]}
    briefs = load(HERE / "variation-briefs.json", {})
    review = load(HERE / "review.json", {})
    items = []
    for u in st["units"]:
        vb = load(RUNS_ROOT / u["run"] / "ads" / u["slug"] / "variations.json", {})
        shots = vb.get("brief") or briefs.get(u["format"]) or briefs.get("portraitvoid")
        unit_dir = RUNS_ROOT / u["run"] / "ads" / u["slug"]
        live = {int(a["name"][-2:]): a for a in u["assets"]}
        a01 = live.get(1)
        # every killed slot for this unit, from his own record
        killed = {}
        for name, v in review.items():
            if v["verdict"] != "kill" or not name.startswith(u["ad_name"] + "-a"): continue
            killed[int(name[-2:])] = v
        for i in range(1, TARGET + 1):
            a = live.get(i); k = killed.get(i)
            note = (k or {}).get("why", "").strip()
            if a and not a["flags"] and not note:
                continue                                     # a clean live picture: nothing to do
            if a and a["flags"] and not note:                # the machine found the defect
                drift = any("drifted" in f for f in a["flags"])
                src = a01 if (drift and a01) else a
                change = (shots[(i - 2) % len(shots)] if drift else fix_text("; ".join(a["flags"])))
                items.append({"id": f"{u['run']}.{u['slug']}.a{i:02d}", "kind": "fix", "run": u["run"], "slug": u["slug"], "target": i,
                              "source": src["path"], "source_name": src["name"], "change": change, "why": "; ".join(a["flags"])})
                continue
            # killed, or simply missing
            ref = a or a01
            if not ref and k:                                # every picture killed — edit the killed frame
                dead = sorted((unit_dir / "killed").glob(f"{u['ad_name']}-a{i:02d}-*.png")) if (unit_dir / "killed").is_dir() else []
                if dead:
                    ref = {"path": str(dead[-1].relative_to(WS)), "name": f"{u['ad_name']}-a{i:02d}"}
            if not ref:
                continue                                     # nothing to edit from — needs a fresh build, not a variation
            shot = shots[(i - 2) % len(shots)] if i > 1 else "the same shot as the reference"
            if note:
                change = (f'Damon rejected the last version of this picture. His words: "{note}". '
                          f'Make this one so that is fixed. {shot}{DEVICE}. Everything else — the man, the words, the layout, '
                          f'the bottom bar — stays exactly as the reference.')
                why = f"killed by Damon: {note}"
            else:
                change = shot + DEVICE
                why = "unit below 3"
            items.append({"id": f"{u['run']}.{u['slug']}.a{i:02d}", "kind": "redo" if note else "fill",
                          "run": u["run"], "slug": u["slug"], "target": i,
                          "source": ref["path"], "source_name": ref["name"], "change": change, "why": why})
    for it in items:
        o = old.get(it["id"], {})
        # a re-do after a kill starts clean: his verdict supersedes anything the machine did before
        fresh = it["kind"] == "redo" and o.get("change") != it["change"]
        it["status"] = "queued" if fresh else o.get("status", "queued")
        it["attempts"] = 0 if fresh else o.get("attempts", 0)
        for k in ("src_crop", "name", "log"):
            if k in o and not fresh: it[k] = o[k]
        if "filed" in o and not fresh: it["filed"] = o["filed"]
    save(HERE / "queue.json", {"planned": dt.datetime.now().isoformat(timespec="seconds"), "items": items})
    log(f"plan: {sum(i['kind']=='redo' for i in items)} re-dos on Damon's word, "
        f"{sum(i['kind']=='fix' for i in items)} machine fixes, {sum(i['kind']=='fill' for i in items)} to make")
    return items


# -------------------------------------------------------------------- run ---
def run(limit=None):
    q = load(HERE / "queue.json", {"items": []}); done = 0
    todo = [i for i in q["items"] if i["status"] in ("queued", "failed") and i["attempts"] < 2]
    if _hf_key():
        import hf, pad
        for it in todo[: limit or len(todo)]:
            src = WS / it["source"]; it["attempts"] += 1
            try:
                # the API needs a fetchable picture: the unit's a01 already sits on Drive
                ids = load(RUNS_ROOT / "_drive-ids.json", {}); fid = (ids.get(Path(it["source"]).name) or {}).get("id")
                if not fid: it["status"] = "failed"; it["log"] = "source not on Drive"; continue
                urls, status = hf.edit(f"https://drive.google.com/uc?export=download&id={fid}", it["change"], "4:5")
                if not urls: it["status"] = "failed"; it["log"] = status; continue
                out = HERE / "inbox" / f"{it['id']}.png"; hf.fetch(urls[0], out)
                it["status"] = "generated"; save(HERE / "queue.json", q)
                done += intake(it["id"], out, q)
            except SystemExit as e:
                it["status"] = "failed"; it["log"] = str(e)[:200]
            save(HERE / "queue.json", q)
    else:
        # no key: the generator is a session with the Higgsfield connector open
        lines = ["# For the session — generate these with the connector, then `queue.py intake <id> <png>`", ""]
        for it in todo:
            it["status"] = "needs-session"
            lines.append(f"- `{it['id']}` ← edit `{it['source']}` · **{it['change']}**  ({it['why']})")
        (HERE / "manual.md").write_text("\n".join(lines) + "\n")
        save(HERE / "queue.json", q)
        log(f"run: no generator key — {len(todo)} items handed to the session (manual.md)")
    return done


def refresh_ocr(unit_dir, file_name):
    """A fixed or new picture says new words — read them off the pixels so the
    slop checks judge the picture that exists, not the one it replaced."""
    try:
        import ocr_copy
        ocr = load(RUNS_ROOT / "_ocr.json", {}); ocr[file_name] = ocr_copy.lift(unit_dir / file_name); save(RUNS_ROOT / "_ocr.json", ocr)
    except Exception as e:
        log(f"ocr refresh failed for {file_name[-30:]}: {e}")


def intake(item_id, png, q=None):
    """A generated picture arrives for a queue item."""
    import finish
    q = q or load(HERE / "queue.json", {"items": []})
    it = next((i for i in q["items"] if i["id"] == item_id), None)
    if not it: raise SystemExit(f"{item_id} is not in the queue")
    ok, res = finish.add_asset(RUNS_ROOT / it["run"], it["slug"], png, it["target"], it["change"], it["source_name"])
    it["attempts"] = it.get("attempts", 0) + 1
    if ok:
        it["status"] = "done"; it["name"] = res; log(f"intake: {item_id} → {res}")
        refresh_ocr(RUNS_ROOT / it["run"] / "ads" / it["slug"], res + ".png")
        rv = load(HERE / "review.json", {}); rv.pop(res, None); save(HERE / "review.json", rv)
        # the headline audit judged the picture that was just replaced — its
        # verdict is about bytes that no longer exist. Drop it so the audit
        # re-judges, or a fixed picture stays condemned by its own old frame.
        ha = load(HERE / "headline-audit.json", {})
        if ha.pop(res, None) is not None: save(HERE / "headline-audit.json", ha)
        sl = load(HERE / "slop.json", {}); sl.pop(Path(it["source"]).name if it["kind"] == "fix" and it["target"] != 1 else "", None)
        # a fixed picture is no longer slop under its own name
        for k in [k for k in sl if k.endswith(f"-a{it['target']:02d}.png") and it["slug"] in k]: sl.pop(k)
        save(HERE / "slop.json", sl)
    else:
        it["status"] = "failed"; it["log"] = "; ".join(res)[:300]; log(f"intake: {item_id} rejected — {it['log'][:120]}")
    save(HERE / "queue.json", q)
    sync(f"queue: {item_id} {'done' if ok else 'rejected'}")
    return 1 if ok else 0


# ----------------------------------------------------------------- review ---
def review(asset, verdict, why=""):
    rv = load(HERE / "review.json", {})
    rv[asset] = {"verdict": verdict, "why": why, "at": dt.datetime.now().isoformat(timespec="seconds")}
    save(HERE / "review.json", rv)
    if verdict == "kill":
        # the slot is re-made from scratch: drop any queue item that claims it
        q = load(HERE / "queue.json", {"items": []}); tail = asset[-3:]
        q["items"] = [i for i in q["items"] if not (asset.startswith(i["run"].split("-")[1], 0) and i["slug"] in asset and f"a{i['target']:02d}" == tail)]
        save(HERE / "queue.json", q)
    import record as R
    st = state()
    u = next((u for u in st["units"] for a in u["assets"] if a["name"] == asset), None)
    if u:
        item = f"{u['run'].split('-')[1]}.{u['slug']}.{asset[-3:]}"
        a = next(a for a in u["assets"] if a["name"] == asset)
        if verdict == "kill":
            R.human(item, "note", "damon", text=f"KILLED — {why or 'no reason given'}")
            if a.get("drive"):
                tr = load(RUNS_ROOT / "_drive-trash.json", []); tr.append({"id": a["drive"], "why": f"killed by Damon: {why}", "path": a["file"]}); save(RUNS_ROOT / "_drive-trash.json", tr)
        else:
            R.human(item, "status", "damon", to="picked", evidence=f"kept on the RUN-01 queue page — {why or 'no note'}")
            if why: R.human(item, "note", "damon", text=f"KEPT — {why}")
    import threading
    threading.Thread(target=lambda: (notes_index(), plan(), sync(f"queue: {verdict} {asset[-30:]} — {why[:50]}")), daemon=True).start()
    return rv[asset]


def notes_index():
    """Damon's own words on every picture, as a page the team can read — the
    LEARN half of the loop. Rewritten from review.json on every verdict."""
    st = state(); lines = ["# RUN-01 — what Damon kept, what he killed, and why", "",
                           "Every line is his note, verbatim, at the moment he clicked. A kill's note becomes the instruction for the next picture of that slot.", ""]
    for v in ("keep", "kill"):
        rows = [n for n in st["notes"] if n["verdict"] == v]
        lines += [f"## {'Kept' if v == 'keep' else 'Killed'} ({len(rows)})", "", "| when | man | look | headline | picture | why |", "|---|---|---|---|---|---|"]
        for n in rows:
            lines.append(f"| {(n['at'] or '')[:16]} | {n['man']} | {n['format']} | {n['headline'][:40]} | {n['asset'][-3:]} | {n['why'].replace('|', '/')} |")
        lines.append("")
    # patterns: the same words said more than once are a rule waiting to be written
    from collections import Counter
    words = Counter(w for n in st["notes"] for w in re.findall(r"[a-z]{4,}", n["why"].lower()) if w not in ("this", "that", "with", "have", "from", "same", "picture", "looks", "like", "just", "very", "more", "than", "into", "over"))
    top = [f"{w} ×{c}" for w, c in words.most_common(12) if c > 1]
    if top: lines += ["## Words he keeps using", "", ", ".join(top), ""]
    (HERE / "notes.md").write_text("\n".join(lines) + "\n")


# ------------------------------------------------------------------- sync ---
PATHS = ["image-production/runs/<brand>", "image-production/queue",
         "creative-ledger/records", "image-production/tools", "components/naming"]
BRANCH = "damon/creative-record"


def sh(*cmd, check=False):
    return subprocess.run(cmd, cwd=WS, capture_output=True, text=True, check=check)


def sync(msg="queue: update"):
    sh("git", "add", "--", *PATHS)
    if sh("git", "diff", "--cached", "--quiet").returncode == 0:
        return "nothing to commit"
    r = sh("git", "commit", "-q", "-m", msg + "\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>")
    if r.returncode: log(f"sync: commit failed — {r.stderr.strip()[:200]}"); return "commit failed"
    sh("git", "fetch", "-q", "origin", BRANCH)
    if sh("git", "merge-base", "--is-ancestor", f"origin/{BRANCH}", "HEAD").returncode != 0:
        log("sync: the branch moved elsewhere — not rebasing over someone else's commits"); return "declined"
    for i in range(3):
        r = sh("git", "push", "-q", "origin", f"HEAD:refs/heads/{BRANCH}")
        if r.returncode == 0: log(f"sync: pushed — {msg}"); return "pushed"
    log(f"sync: push failed — {r.stderr.strip()[:200]}"); return "push failed"


# -------------------------------------------------------------------- kit ---
def kit():
    """Meta's bulk-import kit for the MAIN account, which the connector cannot
    write to: an .xlsx on Meta's own column names (one row per ad; a unit with
    three pictures becomes three rows named <ad_name>-aNN so the record's join
    still holds — drop the last field and you have the unit), plus a folder of
    the pictures named exactly as the sheet says. Imported through Ads Manager
    → Import ads in bulk, in Damon's own Chrome; everything lands PAUSED."""
    import openpyxl
    st = state(); out = HERE / "kit"; (out / "images").mkdir(parents=True, exist_ok=True)
    link = "https://<brand>.com/products/flex"
    # Posters were out on 2026-09-09 ("basically trash" — the device), and back in
    # the same night once every one was re-made with the FLEX Element.
    OUT_OF_RUN = set()
    cols = ["Campaign Name", "Campaign Status", "Campaign Objective", "Buying Type",
            "Ad Set Name", "Ad Set Status", "Ad Set Daily Budget", "Optimization Goal", "Billing Event", "Bid Strategy",
            "Ad Name", "Ad Status", "Image File Name", "Body", "Title", "Link", "Display Link", "Call to Action", "Ad Set Run Status"]
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Ads"; ws.append(cols)
    n = 0
    for u in st["units"]:
        if u["format"] in OUT_OF_RUN: continue
        pics = [a for a in u["assets"] if a["verdict"] != "kill" and not a["flags"]]
        for a in pics:
            shutil.copy2(WS / a["path"], out / "images" / a["file"])
            ws.append(["RUN-01 fed-up-king", "PAUSED", "Outcome Sales", "AUCTION",
                       "RUN-01 fed-up-king", "PAUSED", 50, "OFFSITE_CONVERSIONS", "IMPRESSIONS", "Lowest cost without cap",
                       a["name"], "PAUSED", a["file"], u["headline"], "FLEX\u2122 by <brand>", link, "<brand>.com", "SHOP_NOW", "PAUSED"]); n += 1
    wb.save(out / "run-01-bulk-import.xlsx")
    # the same thing as a page a person reads before uploading
    units = {}
    for u in st["units"]:
        if u["format"] in OUT_OF_RUN: continue
        pics = [a for a in u["assets"] if a["verdict"] != "kill" and not a["flags"]]
        if pics: units[u["ad_name"]] = (u, pics)
    lines = ["# RUN-01 — what goes into Meta", "",
             f"**{sum(len(p) for _, p in units.values())} ads across {len(units)} ideas.** Every ad is PAUSED on import. "
             "Nothing spends until you switch it on.", "",
             "## How to load it", "",
             "1. Ads Manager, the **1. <brand>** account.",
             "2. Import/Export → **Import ads in bulk**.",
             "3. Upload `run-01-bulk-import.xlsx`, then every file in `images/`.",
             "4. Review, publish. Everything lands paused in a campaign called **RUN-01 fed-up-king**.", "",
             "The ad name is the whole record: drop the last piece and you have the idea it belongs to, "
             "so the report joins straight back to who is in it, what it argues and how it is built.", "",
             "## The ads", "", "| man | look | what it says | pictures |", "|---|---|---|---|"]
    for ad, (u, pics) in sorted(units.items(), key=lambda kv: (kv[1][0]["man"], kv[1][0]["format"])):
        h = (u["headline"] or "").replace("\n", " ").replace("|", "/")[:56]
        lines.append(f"| {u['man']} | {u['format']} | {h} | {len(pics)} |")
    lines += ["", "## Not in this run", ""]
    for u in st["units"]:
        pics = [a for a in u["assets"] if a["verdict"] != "kill" and not a["flags"]]
        if not pics: lines.append(f"- **{u['man']} · {u['format']}** — nothing clean yet")
    (out / "WHAT-GOES-IN.md").write_text("\n".join(lines) + "\n")
    (out / "README.md").write_text("# RUN-01 → Meta, main account\n\nAds Manager → Import/Export → Import ads in bulk → upload `run-01-bulk-import.xlsx` and every file in `images/`. Everything is PAUSED; flip on in Ads Manager. Ad names are the 13-field unit name + the picture index, so reports join back to the record.\n")
    log(f"kit: {n} ads across {len(st['units'])} units → queue/kit/run-01-bulk-import.xlsx + images/")
    return n


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd = a[0] if a else "state"
    if cmd == "state": print(json.dumps(state(), indent=1, ensure_ascii=False))
    elif cmd == "plan": plan()
    elif cmd == "run": run(int(a[1]) if len(a) > 1 else None)
    elif cmd == "intake": intake(a[1], Path(a[2]))
    elif cmd == "review": print(review(a[1], a[2], " ".join(a[3:])))
    elif cmd == "sync": print(sync(a[1] if len(a) > 1 else "queue: update"))
    elif cmd == "kit": kit()
