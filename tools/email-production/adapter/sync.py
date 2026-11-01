"""The team's Outlier Emails page (an artifact, not a local server) and the machine behind it.

the owner, 18 Oct 2026: the team's and the team's Outlier is an artifact page, not a local page like his, and every section of an
email can be adjusted on its own. The page (outlier-emails.html in this folder) shows each designed email cut into
its sections; a call names the email and, for section work, the section. the team's Claude moves things between the
page's shared store and the email line with this script:

    sync.py list  [--brand B] [--no-steps]
                                   designed emails as page rows (JSON): sections with their place on the picture,
                                   their words and their picture; `_picture` is the whole email to upload; `_steps`
                                   is the email's full index (design/run_index.py, also written to <run>/index.json):
                                   one page doc per step in the "steps" collection, id <email>__<order>.
                                   The places come from <run>/klaviyo/layout.json, kept by design/build.py, with no
                                   Chrome; `layout_stale` is true when the layout changed since (LD-76 (email layout
                                   file)). --no-steps leaves `_steps` out
    sync.py steps <brand>__<label> one email's `_steps` alone (JSON); exit 2 for an email that is not there
    sync.py apply calls.json       carry out the calls; prints what happened to each (JSON), to write back
    sync.py push-media [--brand B] [--label L]
                                   every designed email's run:media pictures onto its Drive mirror, one line each
                                   (PF-21 (pictures reach every Mac)); exit 1 when a put failed
    sync.py pictures <run> …       the background maker `list` starts: cut pictures from Drive, the whole-email
                                   picture once every cut is here, the received picture (PF-20b (before in background))

Section calls (`section` = its number in design/email.json):
    words     the team: new words for named fields -> written into the layout, rebuilt, checked; a copy learning each
    picture   the team: one change to that section's picture. A picture with a record (design/picture_record.py) is
              edited from it: the current picture goes back in with the same references and only the change; the
              new record names the old one as its parent. One without a record is remade from its brief + the change
    look      the team: a layout or look change for that section -> a design learning, then the email is redesigned with it
    move      the team: "up" or "down" -> the section swaps with its neighbour; rebuilt
    remove    the team: the section comes out; rebuilt; a design learning
    ok        either: this section is right as it is (kept on the card, nothing rebuilt)
Email calls:
    fill      the system fills every gap the brand's files answer (design/gaps.py: offer-bank prices, unmade pictures,
              missing words by a redesign naming them), rebuilds, and reports what still needs a person
    go        the team's Go: the Klaviyo DRAFT is made (approve_klaviyo.approve). Never schedules, never sends.
    send_back a note for the whole email -> a learning, then redesigned, rebuilt and checked (approve_klaviyo.redo)
    scheduled the team scheduled it in Klaviyo herself -> the card is marked scheduled
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EM = HERE.parent
REPO = EM.parents[1]
RUNS = REPO / "runs" / "email-production"
sys.path.append(str(EM))           # appended: this folder has an email.py that would shadow the standard library
sys.path.append(str(EM / "design"))
sys.path.insert(0, str(REPO / "components" / "run-kit"))
_HS = os.path.expanduser("~/Library/Caches/chrome-headless-shell/chrome-headless-shell-mac-arm64/chrome-headless-shell")   # background-only browser: no Dock icon; Chrome is the fallback
CHROME = os.environ.get("CHROME_BIN") or (_HS if os.path.exists(_HS) else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
KIND = {"band": "Header", "mark": "Logo", "poster": "Key visual", "hero_photo": "Hero picture", "hero_type": "Hero words",
        "hero_overlay": "Hero picture with words", "display": "Big words", "headline": "Headline", "letter": "Letter",
        "quote": "Quote", "bigquote": "Big quote", "specs": "Facts", "tiles": "Tiles", "box": "Box", "selfies": "Customer photos",
        "photo_card": "Picture card", "arrows": "Arrow list", "grid": "Picture grid", "picture": "Picture",
        "example": "Customer story", "product": "Product card", "guarantee": "Guarantee", "deal": "Deal", "offer": "Offer",
        "cta": "Button", "rule": "Divider", "sign": "Sign-off", "gif": "Moving picture", "foot": "Footer",
        "photo_row": "Picture row", "callout": "Callout", "timeline": "Timeline", "link": "Link", "ticker": "Ticker"}
NOT_WORDS = {"s", "link", "gif", "photo", "proof", "source", "use", "ratio", "focus", "brief", "todo", "alt", "product", "theme"}
SOURCE = {"made": "made by the picture machine", "photo": "a real product photo", "proof": "a real customer or brand photo"}


def _ak():
    import approve_klaviyo as AK
    AK.RUNS = RUNS
    return AK


def fields(sec):
    """Every piece of words in a section, as (path, value): top-level text, lists of lines, and tile/row items."""
    out = []
    for k, v in sec.items():
        if k in NOT_WORDS or isinstance(v, dict):
            continue
        if isinstance(v, str) and v.strip():
            out.append((k, v))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                if isinstance(x, str) and x.strip():
                    out.append(("%s.%d" % (k, i), x))
                elif isinstance(x, dict):
                    out += [("%s.%d.%s" % (k, i, kk), vv) for kk, vv in x.items()
                            if kk not in NOT_WORDS and isinstance(vv, str) and vv.strip()]
    return out


def _get(sec, path):
    cur = sec
    for p in path.split("."):
        cur = cur[int(p)] if p.isdigit() else cur[p]
    return cur


def _put(sec, path, value):
    parts = path.split(".")
    cur = sec
    for p in parts[:-1]:
        cur = cur[int(p)] if p.isdigit() else cur[p]
    last = parts[-1]
    if last.isdigit():
        cur[int(last)] = value
    else:
        cur[last] = value


def _story(run, x):
    """How one picture came to be, for the page: its record if the machine made it, its origin if it is real."""
    if x.get("record"):
        import picture_record as PR
        r = PR.read(run, x["record"]) or {}
        chain, cur = 0, r
        while cur and cur.get("parent"):
            chain += 1
            cur = PR.read(run, cur["parent"])
        j = r.get("judge") or {}
        return {"made": True, "record": x["record"], "state": r.get("state"), "made_at": r.get("made_at"),
                "purpose": r.get("purpose"), "direction": r.get("direction"), "prompt": r.get("prompt"),
                "model": " · ".join(v for v in ((r.get("model") or {}).get("id"), (r.get("model") or {}).get("vendor_model")) if v),
                "references": [{"kind": f["kind"], "name": Path(f["path"]).name, "pin": (f.get("pinterest") or {}).get("pin"),
                                "pin_title": (f.get("pinterest") or {}).get("title")} for f in r.get("references") or []],
                "judge": "; ".join("%s %s" % (k, v.get("result")) for k, v in j.items() if isinstance(v, dict)) or None,
                "held": r.get("held"), "edits": chain, "edit_of": bool(r.get("edit_of"))}
    if x.get("source") == "made":
        return {"made": True, "record": None, "note": "made before pictures kept their own record"}
    return {"made": False, "from": x.get("photo") or x.get("proof") or ""}


def pictures(sec, run=None):
    out = []
    def walk(x):
        if isinstance(x, dict):
            if "alt" in x and ("photo" in x or "proof" in x or "source" in x or "todo" in x):
                out.append({"alt": x.get("alt") or x.get("todo") or "", "source": SOURCE.get(x.get("source"), x.get("source") or ""),
                            "how": _story(run, x) if run else None})
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(sec)
    return out


def _positions(run, page):
    """Where each section sits in the built email and the whole height, in pixels at 600 wide: the layout.json build
    kept beside it while it matches the email.html (no Chrome), else measured now (LD-76 (email layout file))."""
    import layout_file as LF
    d = LF.read(run)
    if d is not None:
        return LF.positions(d)
    print("layout: measured %s (no fresh layout.json)" % run.name, file=sys.stderr)
    try:
        return LF.measure(page)
    except RuntimeError as e:          # as before: an email that cannot be measured stops the list, by name
        raise SystemExit(str(e))


def _shot_fresh(page, out):
    """A cached whole-email picture counts only when it is newer than email.html AND every cut picture it shows: one
    shot while a cut was missing (the page server's copy, 2026-10-29: alt text in place of pictures) is re-made once
    the cut lands (PF-21 (pictures reach every Mac))."""
    if not out.exists():
        return False
    t = out.stat().st_mtime
    cuts = [page.parent / "assets" / n for n in set(re.findall(r'src="assets/([^"]+)"', page.read_text()))]
    return t > page.stat().st_mtime and all(c.is_file() and t > c.stat().st_mtime for c in cuts)


def _shot(page, out, height):
    if _shot_fresh(page, out):
        return out
    tmp = out.with_suffix(".full.png")
    subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--window-size=600,%d" % int(height + 2),
                    "--screenshot=%s" % tmp, page.as_uri()], capture_output=True, timeout=120)
    from PIL import Image
    im = Image.open(tmp).convert("RGB").crop((0, 0, 600, int(height)))
    im.save(out, quality=82)
    tmp.unlink()
    return out


def rows(brand=None, steps=True):
    import layout_file as LF
    out, missing = [], []
    for f in sorted(RUNS.glob("%s/*/klaviyo/card.json" % (brand or "*"))):
        c = json.loads(f.read_text())
        run = f.parent.parent
        if not (run / "design" / "email.json").is_file():   # a card from before the design line: not a designed email
            continue
        spec = json.loads((run / "design" / "email.json").read_text())
        page = f.parent / "email.html"
        H, pos = _positions(run, page)
        oks = set(c.get("sections_ok") or [])
        secs = []
        for i, s in enumerate(spec["sections"]):
            if i not in pos:
                continue
            top, bot = pos[i]
            secs.append({"i": i, "kind": KIND.get(s["s"], s["s"].replace("_", " ").capitalize()), "type": s["s"],
                         "top": round(top / H, 4), "bottom": round(bot / H, 4),
                         "fields": [{"path": p, "value": v} for p, v in fields(s)], "pictures": pictures(s, run), "ok": i in oks})
        # only a picture problem stops the team; the words and the product are the team's, shown to her (the team, 2026-10-28)
        held, for_steph = __import__("check").holds(c)
        st = "scheduled" if c.get("scheduled") else "draft" if c.get("klaviyo") else "held" if held else "ready"
        s0 = (c.get("subjects") or [{}])[0]
        row = {"id": "%s__%s" % (run.parent.name, run.name), "brand": run.parent.name, "label": run.name,
               "title": s0.get("subject") or spec.get("subject") or run.name, "subject": s0.get("subject") or spec.get("subject") or "",
               "preview": s0.get("preview") or spec.get("preview") or "", "send_day": c.get("date") or "", "eve_due": c.get("eve_due") or "", "status": st,
               "held": held, "for_steph": for_steph, "sections": secs, "ratio": round(H / 600, 4),
               "layout_stale": LF.stale(run)}
        row["gaps"], words = split_gaps(_gaps(run))
        row["for_steph"] = for_steph + [("Promise check: %s" if g.get("type") == "promise" else "Part %d · %s: %%s" % (
            g["section"] + 1, KIND.get(g["type"], g["type"]))) % g["why"] for g in words]
        if steps:
            row["_steps"] = __import__("run_index").index(run)["steps"]
        cuts = LF.assets_missing(run)
        if cuts:                      # never shot with a cut missing: the background maker brings them from Drive first
            row["picture_on_drive"], row["pictures_missing"] = True, cuts
            missing.append(run)
        else:
            row["_picture"] = str(_shot(page, f.parent / "whole-email.jpg", H))
        row.update(_before(run, spec, None if cuts else missing))
        out.append(row)
    if missing:
        try:
            __import__("received").start_maker(missing, argv=[sys.executable, str(Path(__file__).resolve()), "pictures"])
        except Exception as e:  # noqa: BLE001 -- the list still loads; each pending row keeps saying it is being made
            print("received: background maker not started: %s: %s" % (type(e).__name__, e), file=sys.stderr)
    return out


def _before(run, spec, missing=None):
    """The email as the designer received it, for the team's before-and-after (design/received.py): its picture and
    what changed, part by part. From the moment the email reaches the designer (PF-20 (before from arrival)):
    `waiting` while she has no commit on it yet. Never renders (PF-20b (before in background)): a missing picture is
    `pending` and its run is added to `missing` for the background maker. A failure is named on the row, never raised."""
    import received as R
    try:
        f = R.found(run)
        if not f:
            return {}
        p = R.picture_path(run, f)
        ch = R.changes(R.spec_at(run, f["rev"]), spec, lambda t: KIND.get(t, (t or "").replace("_", " ").capitalize()),
                       lambda s: [v for _, v in fields(s)])
        before = {"at": f["at"], "by": f["by"], "changes": ch}
        if f.get("waiting"):
            before["waiting"] = True
        if p.is_file():
            return {"_before": str(p), "before": before}
        err = R.error(run, f)
        if err:
            before["error"] = err
            return {"before": before}
        before["pending"] = True
        if missing is not None:
            missing.append(run)
        return {"_before_pending": str(p), "before": before}
    except Exception as e:  # noqa: BLE001 -- named on the row, never silent
        return {"before": {"error": "%s: %s" % (type(e).__name__, e)}}


def steps(email_id):
    """One email's full step index (design/run_index.py), by its row id <brand>__<label>; None when no such email."""
    brand, _, label = email_id.partition("__")
    run = RUNS / brand / label
    if not (brand and label and "/" not in email_id and (run / "klaviyo" / "card.json").is_file()
            and (run / "design" / "email.json").is_file()):
        return None
    return __import__("run_index").index(run)["steps"]


def split_gaps(gaps):
    """(the team's, the team's): a missing picture is the designer's to make; a missing word, price or promise is the team's to
    settle before the email reaches the team, so it never shows on the team's list (the team, 2026-10-28: "a mi vista")."""
    pic = lambda g: "picture" in (g.get("kind") or "")
    return [g for g in gaps if pic(g)], [g for g in gaps if not pic(g)]


def _gaps(run):
    """What is still missing in the email, each with the question for a person (design/gaps.py)."""
    import gaps as G
    asked = {}
    try:
        for g in json.loads((run / "gaps.json").read_text()).get("open", []):
            asked[(g["section"], g["field"])] = g.get("ask")
    except (OSError, ValueError):
        pass
    return [{"section": g["section"], "type": g["type"], "field": g["field"], "kind": g["kind"], "why": g["why"],
             "ask": asked.get((g["section"], g["field"]))} for g in G.find(run)["gaps"]]


def _learn(brand, stage, rule, by, label, kind="do"):
    from run_kit import learnings as LN
    LN.add(brand, stage, kind, rule, "%s's call on the team Outlier page" % by, by, src=label, chain="email")


def _rebuild(run):
    # build.py rewrites the card and drops the team's Done; prepare.py's keep_card puts it back, so the team's final words
    # after the Done don't send the email back to the team (2026-10-22, oct-20)
    from prepare import keep_card

    def steps():
        for step in (["design/build.py", str(run)], ["design/check.py", str(run)]):
            p = subprocess.run([sys.executable] + step, cwd=EM, capture_output=True, text=True)
            if p.returncode:
                raise RuntimeError("%s stopped: %s" % (step[0], (p.stderr or p.stdout)[-300:]))
    keep_card(run, steps)


def _section_call(k, run, by):
    f = run / "design" / "email.json"
    spec = json.loads(f.read_text())
    i = int(k["section"])
    sec = spec["sections"][i]
    kind = KIND.get(sec["s"], sec["s"])
    b, label, act, note = run.parent.name, run.name, k["action"], (k.get("note") or "").strip()
    if act == "ok":
        cf = run / "klaviyo" / "card.json"
        c = json.loads(cf.read_text())
        c["sections_ok"] = sorted(set(c.get("sections_ok") or []) | {i})
        cf.write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
        return
    if act == "words":
        for e in k.get("edits") or []:
            old = _get(sec, e["path"])
            if old != e["value"]:
                _put(sec, e["path"], e["value"])
                _learn(b, "copy", 'In a %s section, "%s" became "%s"' % (kind.lower(), old, e["value"]), by, label)
    elif act == "move":
        j = i - 1 if note == "up" or k.get("dir") == "up" else i + 1
        if not 0 <= j < len(spec["sections"]):
            raise RuntimeError("it can't move further that way")
        spec["sections"][i], spec["sections"][j] = spec["sections"][j], spec["sections"][i]
        _learn(b, "design", "Moved the %s section %s, next to the %s" % (kind.lower(), "up" if j < i else "down",
               KIND.get(spec["sections"][i]["s"], "").lower()), by, label)
    elif act == "remove":
        spec["sections"].pop(i)
        _learn(b, "design", "Cut a %s section%s" % (kind.lower(), (": " + note) if note else ""), by, label)
    elif act == "picture":
        pics = []
        def walk(x):
            if isinstance(x, dict):
                if "alt" in x and ("photo" in x or "proof" in x):
                    pics.append(x)
                for v in list(x.values()):
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(sec)
        n = int(k.get("picture") or 0)
        if n >= len(pics):
            raise RuntimeError("that picture isn't in this section")
        p = pics[n]
        # edit it from its record: same references, one change, image to image. A call carrying from_brief (the
        # person's yes to LD-81 (portable picture records)'s offer) takes the brief path below instead.
        if p.get("record") and not k.get("from_brief"):
            sys.path.append(str(REPO / "tools" / "image-production"))
            import image_production as IP
            import picture_record as PR
            # PR.CannotRemake (LD-81): its reason, the offer and each missing file come back as this call's result;
            # nothing else runs until the person answers
            new = PR.remake(b, run, p, note, i, IP)
            prev = p.get("record")
            p.update(new)
            p["history"] = (p.get("history") or []) + [prev]
            f.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
            _learn(b, "picture", "%s picture (%s): %s" % (kind, p.get("alt", "")[:120], note), by, label)
            _rebuild(run)
            return
        old = dict(p)
        p.clear()
        p.update({"todo": "%s. CHANGE: %s" % (old.get("alt", ""), note), "brief": old.get("brief", ""), "use": old.get("use") or "story"})
        f.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
        _learn(b, "picture", "%s picture (%s): %s" % (kind, old.get("alt", "")[:120], note), by, label)
        import line
        line.make_pictures(b, run, line.L.load(b))
        _rebuild(run)
        return
    elif act == "look":
        r = _ak().redo(b, label, by, "In the %s section: %s" % (kind.lower(), note), "design")
        if not r.get("ok"):
            raise RuntimeError(r.get("error"))
        return
    else:
        raise RuntimeError("unknown section call")
    f.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    _rebuild(run)


def apply(calls):
    AK = _ak()
    done = []
    for k in sorted(calls, key=lambda x: str(x.get("at"))):
        if k.get("state") == "applied":
            continue
        b, label = k["brand"], k.get("label") or k["email"].split("__", 1)[1]
        run = RUNS / b / label
        act, note, by = k["action"], (k.get("note") or "").strip(), k.get("by") or "graphic-designer"
        try:
            if k.get("section") is not None and act in ("words", "picture", "look", "move", "remove", "ok"):
                _section_call(k, run, by)
                r = {"ok": True}
            elif act == "fill":                   # the system fills what the brand's files answer, then rebuilds
                import gaps as G
                import look as L
                res = G.fill(run, brand=b, lk=L.load(b), redesign=False, pictures_only=True)   # pictures only (the team, 2026-10-28)
                _rebuild(run)
                r = {"ok": True, "error": "filled %d, %d still need a person%s" % (len(res["filled"]), len(res["open"]),
                     (": " + "; ".join(g.get("ask") or g["why"] for g in res["open"]))[:400] if res["open"] else "")}
            elif act == "go":
                # the team, 2026-10-22: her Go comes after she has seen the email, so it means "approved to go
                # out": the draft is made, then scheduled through the guarded step (approver, off-switch, not a
                # machine, final check, unchanged since the draft, 30 minutes ahead). A refusal leaves the
                # draft and says why; the same Go again only schedules it.
                r = AK.approve(b, label, by)
                if r.get("ok") or "already in Klaviyo as draft" in (r.get("error") or ""):
                    s = AK.schedule(b, label, by)
                    r = {"ok": True} if s.get("ok") else \
                        {"ok": False, "error": "the draft is in Klaviyo, NOT scheduled: %s" % s.get("error")}
            elif act == "send_back":
                r = AK.redo(b, label, by, note, "copy" if by == "the team" else "design")
            elif act == "scheduled":
                f = run / "klaviyo" / "card.json"
                c = json.loads(f.read_text())
                c["scheduled"] = {"by": by, "at": k.get("at"), "job": "scheduled by hand in Klaviyo"}
                c["status"] = "scheduled"
                f.write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
                r = {"ok": True}
            else:
                r = {"ok": False, "error": "unknown call"}
        except Exception as e:  # noqa: BLE001 — one call failing never stops the others
            r = {"ok": False, "error": str(e)[:300]}
        done.append({"id": k.get("id"), "state": "applied" if r.get("ok") else "failed", "result": r.get("error") or "done"})
    return done


def make_pictures(runs, pull=None, shoot=None, received=None):
    """The background maker (rows starts it, never waits on it): for each run, its cut pictures from Drive when this Mac
    lacks any (layout_file.pull_build), the whole-email picture only once every cut is here (PF-21 (pictures reach every
    Mac)), then the received picture (PF-20b (before in background)). One run's failure never stops the next.
    Returns {run: what happened}."""
    import layout_file as LF
    import received as R
    pull = pull or LF.pull_build
    shoot = shoot or (lambda run: _shot(run / "klaviyo" / "email.html", run / "klaviyo" / "whole-email.jpg",
                                        _positions(run, run / "klaviyo" / "email.html")[0]))
    received = received or R.make_missing
    said = {}
    for run in [Path(r) for r in runs]:
        try:
            if LF.assets_missing(run):
                got = pull(run.parent.name, run)
                if got.get("error"):
                    print("%s: pictures not brought from Drive — %s" % (run.name, got["error"]))
            left = LF.assets_missing(run)
            if left:
                said[str(run)] = "still missing on Drive: %s" % ", ".join(left)
            else:
                shoot(run)
                said[str(run)] = "shot"
        except Exception as e:  # noqa: BLE001 -- named, and the next run goes on
            said[str(run)] = "%s: %s" % (type(e).__name__, e)
        print("%s: %s" % (run.name, said[str(run)]))
    try:
        received(list(runs))
    except Exception as e:  # noqa: BLE001
        print("received pictures: %s: %s" % (type(e).__name__, e))
    return said


def push_media(brand=None, label=None, reach=None):
    """PF-21 (pictures reach every Mac): every designed email's run:media pictures onto its Drive mirror, one line each.
    How a designer's Claude puts up pictures made before the build did it (the team's 47, 2026-10-29). Returns the lines."""
    import layout_file as LF
    lines = []
    for f in sorted(RUNS.glob("%s/%s/design/email.json" % (brand or "*", label or "*"))):
        run = f.parent.parent
        m = LF.mirror_media(run.parent.name, run, reach=reach)
        if not (m["put"] or m["already"] or m["not_here"] or m["error"]):
            continue
        bits = ["%d put" % len(m["put"]), "%d already up" % len(m["already"])]
        if m["not_here"]:
            bits.append("not on this Mac: %s" % ", ".join(m["not_here"]))
        if m["error"]:
            bits.append("NOT put: %s" % m["error"])
        lines.append("%s/%s: %s" % (run.parent.name, run.name, " · ".join(bits)))
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("list"); a.add_argument("--brand"); a.add_argument("--no-steps", action="store_true")
    s = sub.add_parser("steps"); s.add_argument("id")
    b = sub.add_parser("apply"); b.add_argument("calls")
    p = sub.add_parser("pictures"); p.add_argument("runs", nargs="+")
    m = sub.add_parser("push-media"); m.add_argument("--brand"); m.add_argument("--label")
    x = ap.parse_args()
    if x.cmd == "pictures":
        make_pictures(x.runs)
        return
    if x.cmd == "push-media":
        lines = push_media(x.brand, x.label)
        print("\n".join(lines) or "no designed email names a run:media picture")
        sys.exit(1 if any("NOT put" in l for l in lines) else 0)
    if x.cmd == "list":
        print(json.dumps(rows(x.brand, steps=not x.no_steps), indent=1, ensure_ascii=False))
    elif x.cmd == "steps":
        got = steps(x.id)
        if got is None:
            print("no designed email %r (want <brand>__<label>, as `list` names it)" % x.id, file=sys.stderr)
            sys.exit(2)
        print(json.dumps(got, indent=1, ensure_ascii=False))
    else:
        calls = json.loads(Path(x.calls).read_text())
        print(json.dumps(apply(calls if isinstance(calls, list) else calls.get("calls", [])), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
