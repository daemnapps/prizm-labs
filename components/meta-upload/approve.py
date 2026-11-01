#!/usr/bin/env python3
"""The approval page — every finished ad on one standard card; the owner's click sends it into Meta.

    python3 approve.py                 # http://localhost:8795  (launch config "meta-approve")
    python3 approve.py --port 8795 --root <scratch meta tree> --fake-meta   # trials: nothing reaches Meta

Shows every card in `meta/<brand>/1-check/<lane>/` (cards.py), both brands,
four lanes, with its media, words, pages, where it goes in Meta and its machine
checks. **Approve → Meta** (refused while a check fails) writes the approval
on the card, moves it to 2-approved and runs the card uploader (upload.py
upload_card) — live ids on the card and the folder in 3-live, or Meta's error
on the card and the folder left in 2-approved for a retry. **Disapprove** needs
one or more reasons (reasons.json — each names the upstream step and tool that
caused it) plus a note; it moves the card to sent-back carrying the reasons and
writes one line to `meta/learnings.jsonl` (learnings.py), which rebuilds the
per-step digests the upstream tools read. The **Learnings** tab shows them by
step and tool.

Who is deciding: one name from approvers.json, picked once per browser and
written on every approve / disapprove.

The click on this page is the only thing that writes an approval. Nothing here
runs on a timer, and nothing else in the repo approves a card. Listens on
127.0.0.1 only — unless `--tailscale` (or APPROVE_TAILSCALE=1) is given, when it
also listens on this Mac's Tailscale address (100.64.0.0/10, the private network
only the owner's own devices join), checked every 30 s so it picks the address up
whenever Tailscale comes on. Never 0.0.0.0, never a public tunnel.

Phone: the page installs to a home screen as "Approve" (/manifest.webmanifest,
/icon-180.png, /icon-512.png — drawn here, no files).
"""
import argparse, io, ipaddress, json, mimetypes, os, queue, re, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
os.environ.setdefault("CARDS_ROUTE", "mount")   # Meta approve moves card folders: the Drive folder itself (shared_drive.py)
from urllib.parse import urlparse, parse_qs, unquote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cards as C
import learnings as L
import upload as U
from brand import Brand

PAGE = HERE / "approve.html"
VIEWS = {"check": "1-check", "approved": "2-approved", "live": "3-live", "sent-back": "sent-back"}
LOCK = threading.Lock()          # one approve / upload / send-back at a time
FAKE = None                      # --fake-meta: a stand-in Meta for trials
_thumbs = {}
# The upload queue (the owner, 24 Oct 2026: "I'm clicking upload, but some things don't get uploaded. I don't want to
# keep pulling and reading from Meta"). An approve is written and the card moved at once; the upload goes on this
# queue and one worker sends them into Meta one at a time. Each ad's result (queued, uploading, live, failed and
# why) is kept here by ad name and shown on the page, so nothing is dropped and nobody has to look in Meta.
UPQ = queue.Queue()
JOBS = {}                        # ad folder name -> {state, at, error, ad_name, headline, cid, thumb, start}
UPLOADING = set()                # ad folder names the worker is sending right now (a disapprove waits)


def meta_for(brand):
    return FAKE(brand) if FAKE else None


def brand_label(name):
    """The brand's own label from its account file ("label"), else its spelling."""
    try:
        b = Brand(name)
        return b.d.get("label") or b.pretty(name) or name
    except SystemExit:
        return name


def view_of(folder, card, run_checks):
    """One card as the page shows it."""
    cid = C.card_id(folder)
    w = C.where(folder)
    if run_checks:
        try:
            # offline: listing a page never calls Meta or fetches a page (the Page ad count is read at Approve)
            card = C.check_and_save(folder, online=False)
        except Exception as e:
            card = dict(card, checks={"checks": {"ok": False, "why": f"the checks could not run: {e}"}})
    goes, account, b = [], "", None
    try:
        b = Brand(card.get("brand") or w["brand"])
        account = b.d.get("account_name") or b.account_id
        p = U.card_plan(folder, card)
        for r in p["ads"] + [h for h in p["held"] if h.get("link_id") is not None]:
            goes.append({k: r.get(k) for k in ("link_id", "url", "meta_ad_name", "campaign", "ad_set", "funnel")})
    except SystemExit as e:
        goes.append({"error": str(e)})
    media = []
    for f in card.get("media") or []:
        kind = "video" if Path(f).suffix.lower() in C.VIDEO else "image"
        cover = (card.get("thumbs") or {}).get(f)
        v = lambda n: int((Path(folder) / n).stat().st_mtime) if (Path(folder) / n).exists() else 0
        # ?v=<file time>: a re-filed card reuses its file names, so without it the phone replays the old video (10-12)
        media.append({"name": f, "kind": kind, "src": f"/media/{cid}/{f}?v={v(f)}", "thumb": f"/thumb/{cid}/{f}?v={v(f)}",
                      **({"cover": f"/media/{cid}/{cover}?v={v(cover)}"} if cover else {})})
    checks = [{"key": k, "label": C.LABELS.get(k, k), **v} for k, v in (card.get("checks") or {}).items()]
    return {"id": cid, **w, "brand_label": brand_label(w["brand"]), "format": card.get("format", "flexible"),
            "ad_name": card.get("ad_name"), "words": __import__("to_check").clean_words(card.get("words")),  # as Meta will show it
            "pages": card.get("pages") or [],
            "account": account, "account_id": b.account_id if b else "",
            "goes": goes, "media": media, "checks": checks, "passed": C.passed(card) if checks else False,
            "approval": card.get("approval"), "meta": card.get("meta") or [], "upload_error": card.get("upload_error"),
            "campaign_pick": card.get("campaign"),
            "made_by": card.get("made_by"), "made_at": card.get("made_at"), "checked_at": card.get("checked_at"),
            "copy_checked": bool(card.get("copy_checked")),
            "headline": ((card.get("words") or {}).get("headlines") or [""])[0], "job": JOBS.get(Path(folder).name)}


def cards_json(view, brand=None, lane=None):
    state = VIEWS.get(view, "1-check")
    folders = C.listing(state=state, brand=brand or None, lane=lane or None)
    run = state in ("1-check", "2-approved")
    # a card whose brief was replaced (stage-check marks it superseded_by the new brief) leaves the list;
    # its folder stays where it is
    folders = [f for f in folders if not (C.load(f) or {}).get("superseded_by")]
    with ThreadPoolExecutor(6) as ex:
        out = list(ex.map(lambda f: view_of(f, C.load(f), run), folders))
    camps = {b: U.campaign_options(b) for b in {c["brand"] for c in out}}
    return {"view": view, "cards": out, "counts": counts(brand, lane), "campaigns": camps, "brands": [{"id": b, "label": brand_label(b)} for b in C.brands()],
            "lanes": list(C.LANES), "root": str(C.root()), "fake": bool(FAKE),
            "approvers": approvers(), "reasons": reasons_for_page(),
            "jobs": sorted(({"name": k, **v} for k, v in JOBS.items()), key=lambda j: j.get("at") or "", reverse=True)[:80],
            "queue": UPQ.qsize()}


def counts(brand=None, lane=None):
    return {v: len([f for f in C.listing(state=s, brand=brand or None, lane=lane or None)
                    if not (C.load(f) or {}).get("superseded_by")]) for v, s in VIEWS.items()}


def approvers():
    return U.approvers()


def who(by):
    """The approver the page sent, checked against approvers.json (one approver -> that one)."""
    names = approvers()
    if by in names:
        return by
    if not by and len(names) == 1:
        return names[0]
    raise SystemExit(f"pick who is approving first ({', '.join(names)})")


def reasons_for_page():
    cfg = L.config()
    return [{"id": r["id"], "label": r["label"],
             "steps": [f"{u['step']} {cfg['steps'].get(str(u['step']), 'Not sorted')}" if u["step"] else "not sorted"
                       for u in r["upstream"]]} for r in cfg["reasons"]]


def now():
    return datetime.now().isoformat(timespec="seconds")


def run_upload(folder):
    """The uploader on an approved card -> the page's answer."""
    try:
        new, card = U.upload_card(folder, m=meta_for(C.where(folder)["brand"]), log=lambda *_: None)
        return {"ok": True, "state": "3-live", "id": C.card_id(new), "meta": card["meta"]}
    except SystemExit as e:
        return {"ok": False, "state": C.where(folder)["state"], "id": C.card_id(folder), "error": str(e)}


def score_diversity(folder):
    """Meta strategy (7 Oct 2026): before an approve, read the ad itself and score it
    against the running library (creative-diversity/check.py — never calls Meta).
    Cached on the card by media, so it runs once per ad. A scorer failure never
    blocks the upload (the owner, 12 Oct 2026: "I just need ads uploaded"): the reason
    goes on the card as an `unscored` verdict and the approve carries on."""
    if FAKE:
        return ""
    why = ""
    try:
        sys.path.insert(0, str(HERE.parent / "creative-diversity"))
        import check as D
        D.score_card(folder)
    except Exception as e:  # noqa: BLE001
        print(f"diversity not scored for {folder.name}: {e}", file=sys.stderr, flush=True)
        why = f"{type(e).__name__}: {e}"[:300]
    card = C.load(folder)
    if not card.get("diversity"):
        card["diversity"] = {"verdict": "unscored", "why": f"not scored ({why or 'the scorer gave no score'}) — sent anyway",
                             "scored_at": now()}
        C.save(folder, card)
    return why


def approve(cid, start, by=None):
    # the owner, 7 Oct 2026: no silent default. The Creator-A face scrub ad sat paused
    # for three days because the page started every approve as Paused.
    if start not in ("ACTIVE", "PAUSED"):
        return 400, {"ok": False, "error": "pick On or Paused — the approve needs one"}
    folder = C.folder_of(cid)
    if C.where(folder)["state"] != "1-check" or not (folder / "card.json").is_file():
        return 409, {"ok": False, "error": "this card is not waiting in 1-check any more — reload"}
    by = who(by)
    score_diversity(folder)
    # online: the pages are fetched and the Page ad count read (cached an hour per brand, never blocking)
    card = C.check_and_save(folder, online=True, meta=meta_for(C.where(folder)["brand"]))
    if not C.passed(card):
        bad = [f"{C.LABELS.get(k, k)}: {v['why']}" for k, v in card["checks"].items() if not v["ok"]]
        return 409, {"ok": False, "error": "a machine check is failing — " + "; ".join(bad)}
    card["approval"] = {"by": by, "at": now(), "decision": "approve",
                        "start": start}
    C.save(folder, card)
    folder = C.move(folder, "2-approved")
    return 200, run_upload(folder)


def _job(name, **kw):
    j = JOBS.setdefault(name, {})
    j.update(kw, at=now())
    return j


def _remember(folder, card, state, **kw):
    media = (card.get("media") or [""])[0]
    _job(folder.name, state=state, cid=C.card_id(folder), ad_name=card.get("ad_name"),
         headline=((card.get("words") or {}).get("headlines") or [""])[0],
         thumb=f"/thumb/{C.card_id(folder)}/{media}" if media else "", start=(card.get("approval") or {}).get("start"), **kw)


def queue_approve(cid, start, by=None):
    """The approve every button uses: the approval written and the card moved to 2-approved now, the upload queued.
    The page never waits on Meta, and a second click while an ad is uploading is never lost."""
    if start not in ("ACTIVE", "PAUSED"):
        return 400, {"ok": False, "error": "pick On or Paused — the approve needs one"}
    folder = C.folder_of(cid)
    if C.where(folder)["state"] != "1-check" or not (folder / "card.json").is_file():
        return 409, {"ok": False, "error": "this card is not waiting in 1-check any more — reload"}
    by = who(by)
    card = C.check_and_save(folder, online=False)
    if not C.passed(card):
        bad = [f"{C.LABELS.get(k, k)}: {v['why']}" for k, v in card["checks"].items() if not v["ok"]]
        return 409, {"ok": False, "error": "a machine check is failing — " + "; ".join(bad)}
    card["approval"] = {"by": by, "at": now(), "decision": "approve", "start": start}
    C.save(folder, card)
    folder = C.move(folder, "2-approved")
    _remember(folder, card, "queued", error="")
    UPQ.put(folder.name)
    return 200, {"ok": True, "queued": C.card_id(folder)}


def queue_retry(cid):
    folder = C.folder_of(cid)
    if C.where(folder)["state"] != "2-approved":
        return 409, {"ok": False, "error": "only an approved card can be retried"}
    _remember(folder, C.load(folder), "queued", error="")
    UPQ.put(folder.name)
    return 200, {"ok": True, "queued": C.card_id(folder)}


def _approved_folder(name):
    for f in C.listing(state="2-approved"):
        if f.name == name:
            return f
    return None


# Two failures that are only timing never count as "didn't go in" (the owner, 2026-10-27, on four approved ads that
# stopped: "we need to fix what was failing seriously"): a card's pictures not there yet because the Drive is still
# moving the folder into Approved (three ads, 25 Oct), and Meta's request limit for the ad account (one ad). Each waits
# and goes back on the queue by itself; only after its last try is it "didn't go in".
RETRY = {"media": (90, 6, "The Drive was still moving this card's pictures into Approved"),
         "limit": (900, 8, "Meta's request limit for the ad account was reached")}
META_LIMIT = re.compile(r"request limit|too many (?:api )?calls|\"code\"\s*:\s*(?:4|17|32|613|80004)\b|\"is_transient\"\s*:\s*true", re.I)


def retry_later(name, kind):
    """Put the card back on the queue after the wait for `kind`; False when it has had all its tries."""
    wait, most, why = RETRY[kind]
    j = JOBS.get(name) or {}
    tries = dict(j.get("tries") or {})
    tries[kind] = tries.get(kind, 0) + 1
    if tries[kind] > most:
        return False
    _job(name, state="waiting", tries=tries,
         error=f"{why}. Trying again by itself at {time.strftime('%H:%M', time.localtime(time.time() + wait))} "
               f"(try {tries[kind]} of {most}).")
    threading.Timer(wait, UPQ.put, args=(name,)).start()
    return True


def only_missing_media(card):
    bad = {k: v for k, v in (card.get("checks") or {}).items() if not v["ok"]}
    return set(bad) == {"media"} and bad["media"]["why"].startswith("missing:")


def upload_one(name):
    """One queued ad into Meta: the diversity score and the online checks, then the uploader. The result is kept."""
    with LOCK:
        folder = _approved_folder(name)
        if folder is None:
            j = JOBS.get(name) or {}
            if j.get("state") in ("queued", "uploading"):
                _job(name, state="gone", error="the card left Approved before it was sent (sent back or moved)")
            return
        UPLOADING.add(name)
        _remember(folder, C.load(folder), "uploading", error="")
    try:
        score_diversity(folder)
        card = C.check_and_save(folder, online=True, meta=meta_for(C.where(folder)["brand"]))
        if not C.passed(card):
            if only_missing_media(card) and retry_later(name, "media"):
                return
            bad = [f"{C.LABELS.get(k, k)}: {v['why']}" for k, v in card["checks"].items() if not v["ok"]]
            _job(name, state="failed", error="a machine check is failing — " + "; ".join(bad))
            return
        r = run_upload(folder)     # not under LOCK: the page keeps answering while Meta works (UPLOADING guards it)
        if not r["ok"] and META_LIMIT.search(r.get("error") or "") and retry_later(name, "limit"):
            return
        if r["ok"]:
            j = JOBS.get(name) or {}
            _job(name, state="live", error="", cid=r["id"], ads=len(r.get("meta") or []),
                 thumb=(j.get("thumb") or "").replace(j.get("cid") or "\0", r["id"]))
        else:
            _job(name, state="failed", error=r.get("error") or "Meta said no")
    except Exception as e:  # noqa: BLE001 — the queue never dies on one ad
        _job(name, state="failed", error=f"{type(e).__name__}: {e}"[:400])
    finally:
        UPLOADING.discard(name)


def upload_worker():
    while True:
        name = UPQ.get()
        upload_one(name)


def resume_queue():
    """On start: every approved card that never reached Meta goes back on the queue (the old page dropped some)."""
    for f in C.listing(state="2-approved"):
        card = C.load(f)
        if (card.get("approval") or {}).get("decision") == "approve" and not card.get("meta"):
            _remember(f, card, "queued", error="")
            UPQ.put(f.name)


def batch(ids, action, by=None, note=None):
    """Many cards in one go (the owner, 24 Oct 2026: "some sort of batch approval"): approve On, approve Paused, or send
    back. A send-back from the list carries the reason 'Something else' and the note given, or a plain one."""
    if action not in ("live", "paused", "back", "drop"):
        return 400, {"ok": False, "error": "pick approve on, approve paused or send back"}
    results = []
    for cid in ids or []:
        try:
            if action == "drop":
                code, r = drop(cid, note, by)
            elif action == "back":
                code, r = disapprove(cid, ["other"], (note or "").strip() or "Not good enough (sent back from the list)", by)
            else:
                code, r = queue_approve(cid, "ACTIVE" if action == "live" else "PAUSED", by)
        except (ValueError, FileNotFoundError, SystemExit) as e:
            r = {"ok": False, "error": str(e)}
        results.append({"id": cid, "ok": bool(r.get("ok")), "error": r.get("error", "")})
    return 200, {"ok": all(x["ok"] for x in results), "results": results}


def link_options(brand):
    """The brand's live landing pages from the catalog (components/naming/page_pick), for the launch picker."""
    import page_pick as PP
    offer = C.strategy_offer(brand)              # his one-offer Meta rule (components/meta-strategy/rules.json, 7 Oct)
    out = []
    for k, v in PP.records(brand).items():
        if k.startswith("link_") and v.get("url") and v.get("status", "live") == "live":
            ok = (not offer) or any(m in v["url"] for m in offer["match"])
            out.append({"link_id": k, "url": v["url"], "label": v.get("page") or v.get("label") or k,
                        "type": PP.link_type(v), "group": v.get("group") or "", "live_ads": PP.live_ads(v),
                        "allowed": ok, "why": "" if ok else f"not the {offer['product']} offer page — your one-offer rule"})
    have = {o["url"].rstrip("/") for o in out}
    try:                                         # portal pages sit in the funnel map, not the catalog (the owner, 30 Oct 2026)
        tr = json.loads((Path(__file__).resolve().parents[2] / "brands" / brand / "web/funnels/tracking.json").read_text())
    except (OSError, ValueError):
        tr = {}
    for fn in tr.get("funnels") or []:
        for pg in fn.get("pages") or []:
            if "/portal-" not in pg.get("path", ""):
                continue
            url = f"https://{(fn.get('hosts') or [''])[0]}{pg['path']}"
            if url.rstrip("/") in have:
                continue
            ok = (not offer) or any(m in url for m in offer["match"])
            slug = pg["path"].strip("/").split("/")[-1]
            out.append({"link_id": f"link_{brand}_{pg['path'].strip('/').split('/')[0].replace('brand-b-', '').replace('-cpk', '')}_{slug}",
                        "url": url, "label": f"{fn.get('name', '')} portal · {slug.replace('portal-', '')}", "type": "quiz",
                        "group": fn.get("name") or "", "live_ads": 0, "allowed": ok,
                        "why": "" if ok else f"not the {offer['product']} offer page — your one-offer rule"})
    return sorted(out, key=lambda x: (not x["allowed"], -(x["live_ads"] or 0)))


def set_pages(cid, link_ids):
    """the owner picks where the ad sends traffic before he launches it (15 Oct 2026: "on launch to meta I want to
    add the ability to select the links to send traffic to"). Each picked page becomes its own Meta ad at upload,
    named for that page, exactly as a card's `pages` always has. Only catalog links of the card's brand."""
    folder = C.folder_of(cid)
    if C.where(folder)["state"] != "1-check":
        return 409, {"ok": False, "error": "this card is not waiting in 1-check any more — reload"}
    card = C.load(folder)
    brand = C.where(folder)["brand"]
    opts = {o["link_id"]: o for o in link_options(brand)}
    ids = [i for i in (link_ids or []) if i in opts]
    if not ids:
        return 400, {"ok": False, "error": "pick at least one landing page"}
    blocked = [opts[i]["label"] for i in ids if not opts[i]["allowed"]]
    if blocked:
        return 409, {"ok": False, "error": "; ".join(f"{b}: {opts[next(k for k in ids if opts[k]['label']==b)]['why']}" for b in blocked)}
    card["pages"] = [{"link_id": i, "url": opts[i]["url"]} for i in ids]
    card.setdefault("history", []).append({"at": now(), "what": "pages picked at launch", "pages": ids})
    C.save(folder, card)
    return 200, {"ok": True, "pages": card["pages"]}


def set_campaign(cid, campaign):
    """the owner picks the campaign a new ad goes into (17 Oct 2026); empty = the one its landing page gives."""
    folder = C.folder_of(cid)
    if C.where(folder)["state"] != "1-check":
        return 409, {"ok": False, "error": "this card is not waiting in 1-check any more — reload"}
    card = C.load(folder)
    brand = C.where(folder)["brand"]
    if campaign and campaign not in {o["name"] for o in U.campaign_options(brand)}:
        return 400, {"ok": False, "error": f"{campaign} is not one of this brand's campaigns"}
    if campaign:
        card["campaign"] = campaign
    else:
        card.pop("campaign", None)
    card.setdefault("history", []).append({"at": now(), "what": "campaign picked", "campaign": campaign or "by page"})
    C.save(folder, card)
    return 200, {"ok": True}


def move(cid, campaign, by=None):
    """Copy a live ad into another campaign (the originals stay as they are)."""
    folder = C.folder_of(cid)
    card = U.move_card(folder, campaign, who(by), m=meta_for(C.where(folder)["brand"]))
    return 200, {"ok": True, "copied": [r for r in card["meta"] if r.get("campaign") == campaign]}


def campaign_status(brand, campaign, status, by=None):
    cid = U.set_campaign_status(brand, campaign, status, who(by), m=meta_for(brand))
    return 200, {"ok": True, "campaign_id": cid, "status": status}


def retry(cid):
    folder = C.folder_of(cid)
    if C.where(folder)["state"] != "2-approved":
        return 409, {"ok": False, "error": "only an approved card can be retried"}
    return 200, run_upload(folder)


WORD_KEYS = ("primary", "headlines", "descriptions")
PIC_EXT = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}


def edit_words(cid, words, by=None):
    """Rewrite a waiting card's words in place (the owner, 15 Oct: rewrite lines before approving). Up to five of each;
    the copy check runs again on the next look."""
    f = C.folder_of(cid)
    if C.where(f)["state"] != "1-check":
        return 409, {"ok": False, "error": "only an ad still waiting for approval can be edited"}
    card = C.load(f)
    w = card.setdefault("words", {})
    for k in WORD_KEYS:
        if isinstance((words or {}).get(k), list):
            w[k] = [str(x).strip() for x in words[k] if str(x).strip()][:5]
    card.pop("copy_checked", None)
    card.setdefault("edits", []).append({"by": by or "the owner", "at": datetime.now().isoformat(timespec="seconds"), "what": "words"})
    C.save(f, card)
    return 200, {"ok": True}


def replace_picture(cid, key, new_file, by=None):
    """Put a new picture where one of the card's pictures was — same name, same format. The old one is kept under
    runs/meta-upload/replaced/ first. new_file must be a picture already on this Mac under the workspace's runs/."""
    f = C.folder_of(cid)
    if C.where(f)["state"] != "1-check":
        return 409, {"ok": False, "error": "only an ad still waiting for approval can be edited"}
    card = C.load(f)
    target = f / str(key)
    if key not in (card.get("media") or []) or Path(key).name != key or target.suffix.lower() not in PIC_EXT or not target.is_file():
        return 404, {"ok": False, "error": "not a picture on this card"}
    runs = (HERE.parents[1] / "runs").resolve()
    src = Path(new_file or "").resolve()
    if not str(src).startswith(str(runs)) or not src.is_file():
        return 400, {"ok": False, "error": "the new picture isn't where it should be"}
    from PIL import Image
    keep = runs / "meta-upload" / "replaced" / cid.replace("/", "__")
    keep.mkdir(parents=True, exist_ok=True)
    gi = keep.parents[1] / ".gitignore"
    if not gi.is_file():
        gi.write_text("# pictures an edit replaced, kept for undo — media, never in git\n*\n")
    (keep / f"{datetime.now():%Y%m%d-%H%M%S}--{key}").write_bytes(target.read_bytes())
    fmt = PIC_EXT[target.suffix.lower()]
    im = Image.open(src)
    tmp = target.with_name("." + target.name + ".tmp")
    (im.convert("RGB") if fmt == "JPEG" else im).save(tmp, fmt, **({"quality": 95} if fmt == "JPEG" else {}))
    os.replace(tmp, target)
    card.setdefault("edits", []).append({"by": by or "the owner", "at": datetime.now().isoformat(timespec="seconds"), "what": f"picture {key}"})
    C.save(f, card)
    _thumbs.clear()
    return 200, {"ok": True}


def disapprove(cid, reasons, note, by=None):
    """Disapprove: at least one reason and a note. The card carries the reasons to
    sent-back; one line goes to learnings.jsonl for the upstream steps."""
    note = (note or "").strip()
    if not reasons:
        return 400, {"ok": False, "error": "pick at least one reason"}
    if not note:
        return 400, {"ok": False, "error": "say why — a disapprove needs a note"}
    by = who(by)
    folder = C.folder_of(cid)
    w = C.where(folder)
    if w["state"] not in ("1-check", "2-approved"):
        return 409, {"ok": False, "error": "this card can't be disapproved from here"}
    if folder.name in UPLOADING:
        return 409, {"ok": False, "error": "this ad is being sent into Meta right now — wait for it to finish"}
    try:
        rs = L.resolve(reasons, w["lane"])
    except ValueError as e:
        return 400, {"ok": False, "error": str(e)}
    card = C.load(folder)
    at = now()
    card["approval"] = {"by": by, "at": at, "decision": "disapprove", "note": note,
                        "reasons": [{k: r[k] for k in ("id", "label", "step", "tool")} for r in rs]}
    C.save(folder, card)
    new = C.move(folder, "sent-back")
    L.record(card, w, by, rs, note, at=at)
    return 200, {"ok": True, "state": "sent-back", "id": C.card_id(new),
                 "to": [f"{r['step']} {r['step_name']} · {r['tool']}" for r in rs]}


def drop(cid, note, by=None):
    """Drop a card that is not worth running (the owner, 30 Oct 2026: "allow me to delete certain briefs as well beyond
    send back"). It leaves every list and nothing goes upstream — no remake, no learning. The folder is renamed into
    meta/<brand>/dropped/, never deleted, so it can be restored."""
    by = who(by)
    folder = C.folder_of(cid)
    w = C.where(folder)
    if w["state"] not in ("1-check", "sent-back"):
        return 409, {"ok": False, "error": "only a card waiting for you (or one already sent back) can be dropped"}
    if folder.name in UPLOADING:
        return 409, {"ok": False, "error": "this ad is being sent into Meta right now — wait for it to finish"}
    card = C.load(folder)
    card["approval"] = {"by": by, "at": now(), "decision": "drop", "note": (note or "").strip() or "Not worth running"}
    C.save(folder, card)
    C.move(folder, "dropped")
    return 200, {"ok": True, "state": "dropped", "id": cid}


def thumb(path):
    """A 270-px-wide JPEG of a picture, kept in memory."""
    key = (str(path), path.stat().st_mtime)
    if key not in _thumbs:
        from PIL import Image
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((270, 480))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=82)
        _thumbs[key] = buf.getvalue()
    return _thumbs[key]


MANIFEST = {"name": "Approve", "short_name": "Approve", "start_url": "/", "scope": "/", "display": "standalone",
            "background_color": "#11141a", "theme_color": "#11141a",
            "icons": [{"src": "/icon-180.png", "sizes": "180x180", "type": "image/png"},
                      {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}
_icons = {}


def icon(size):
    """The home-screen icon: a green tick on the page's dark ground (full bleed; iOS rounds it)."""
    if size not in _icons:
        from PIL import Image, ImageDraw
        k = 4                                            # draw big, shrink smooth
        n = size * k
        im = Image.new("RGB", (n, n), "#11141a")
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([n * .2, n * .2, n * .8, n * .8], radius=n * .12, fill="#183327")
        w = max(1, int(n * .075))
        d.line([(n * .33, n * .52), (n * .45, n * .64), (n * .68, n * .38)], fill="#74d39c", width=w, joint="curve")
        for x, y in ((n * .33, n * .52), (n * .68, n * .38)):
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill="#74d39c")
        im = im.resize((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "PNG")
        _icons[size] = buf.getvalue()
    return _icons[size]


TAILNET = ipaddress.ip_network("100.64.0.0/10")


def tailscale_ip():
    """This Mac's Tailscale IPv4, or None. The Tailscale CLI if there is one, else the utun interfaces."""
    for cli in ("/Applications/Tailscale.app/Contents/MacOS/Tailscale", "/opt/homebrew/bin/tailscale",
                "/usr/local/bin/tailscale"):
        if os.path.exists(cli):
            try:
                out = subprocess.run([cli, "ip", "-4"], capture_output=True, text=True, timeout=5).stdout.split()
                if out and ipaddress.ip_address(out[0]) in TAILNET:
                    return out[0]
            except Exception:  # noqa: BLE001 — fall through to the interfaces
                pass
    try:
        out = subprocess.run(["/sbin/ifconfig"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return None
    for block in re.split(r"\n(?=\S)", out):
        if block.startswith("utun"):
            for ip in re.findall(r"inet (\d+\.\d+\.\d+\.\d+)", block):
                if ipaddress.ip_address(ip) in TAILNET:
                    return ip
    return None


def serve_tailscale(port):
    """Also listen on the Tailscale address while there is one (checked every 30 s)."""
    bound = {}
    while True:
        ip = tailscale_ip()
        for old in [x for x in bound if x != ip]:
            bound.pop(old).shutdown()
        if ip and ip not in bound:
            try:
                srv = ThreadingHTTPServer((ip, port), Handler)
                srv.daemon_threads = True
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                bound[ip] = srv
                print(f"approval page also on http://{ip}:{port}  (Tailscale)", flush=True)
            except OSError as e:
                print(f"could not listen on Tailscale {ip}:{port}: {e}", file=sys.stderr, flush=True)
        time.sleep(30)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json", extra=None):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def file_in_card(self, rest):
        """/<brand>/<state>/<lane>/<name>/<file> -> a file the card lists."""
        parts = unquote(rest).strip("/").split("/")
        if len(parts) != 5:
            raise ValueError("bad path")
        folder = C.folder_of("/".join(parts[:4]))
        name = parts[4]
        card = C.load(folder)
        if name not in (card.get("media") or []) and name not in (card.get("thumbs") or {}).values():
            raise ValueError("not on the card")
        return folder / name

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if u.path == "/manifest.webmanifest":
                return self.send(200, MANIFEST, "application/manifest+json")
            if u.path in ("/icon-180.png", "/apple-touch-icon.png", "/icon-512.png"):
                return self.send(200, icon(512 if "512" in u.path else 180), "image/png")
            if u.path == "/api/links":
                return self.send(200, {"links": link_options((parse_qs(u.query).get("brand") or [""])[0])})
            if u.path == "/api/learnings":
                return self.send(200, dict(L.summary(q.get("brand"), q.get("lane")),
                                           brands=[{"id": b, "label": brand_label(b)} for b in C.brands()],
                                           lanes=list(C.LANES), approvers=approvers(), fake=bool(FAKE),
                                           root=str(C.root()), counts=counts(q.get("brand"), q.get("lane"))))
            if u.path == "/api/cards":
                return self.send(200, cards_json(q.get("view", "check"), q.get("brand"), q.get("lane")))
            if u.path.startswith("/thumb/"):
                p = self.file_in_card(u.path[len("/thumb"):])
                if p.suffix.lower() in C.VIDEO:
                    return self.send(404, {"error": "video"})
                return self.send(200, thumb(p), "image/jpeg")
            if u.path.startswith("/media/"):
                return self.serve_file(self.file_in_card(u.path[len("/media"):]))
        except (ValueError, FileNotFoundError) as e:
            return self.send(404, {"error": str(e)})
        self.send(404, {"error": "not found"})

    def serve_file(self, p):
        """A file with byte ranges (Safari will not play a video without them)."""
        size = p.stat().st_size
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].split(",")[0].partition("-")
            if a:
                start, end = int(a), int(b) if b else size - 1
            else:
                start = max(0, size - int(b))
            end = min(end, size - 1)
        n = end - start + 1
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(n))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if self.command == "HEAD":
            return
        with p.open("rb") as f:
            f.seek(start)
            left = n
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except json.JSONDecodeError:
            return self.send(400, {"ok": False, "error": "bad request"})
        try:
            with LOCK:
                if u.path == "/api/approve":
                    code, out = queue_approve(body.get("id"), body.get("start"), body.get("by"))
                elif u.path == "/api/batch":
                    code, out = batch(body.get("ids"), body.get("action"), body.get("by"), body.get("note"))
                elif u.path == "/api/pages":
                    code, out = set_pages(body.get("id"), body.get("pages"))
                elif u.path == "/api/retry":
                    code, out = queue_retry(body.get("id"))
                elif u.path == "/api/campaign":
                    code, out = set_campaign(body.get("id"), body.get("campaign"))
                elif u.path == "/api/move":
                    code, out = move(body.get("id"), body.get("campaign"), body.get("by"))
                elif u.path == "/api/campaign-status":
                    code, out = campaign_status(body.get("brand"), body.get("campaign"), body.get("status"), body.get("by"))
                elif u.path == "/api/drop":
                    code, out = drop(body.get("id"), body.get("note"), body.get("by"))
                elif u.path == "/api/disapprove":
                    code, out = disapprove(body.get("id"), body.get("reasons"), body.get("note"), body.get("by"))
                elif u.path == "/api/words":
                    code, out = edit_words(body.get("id"), body.get("words"), body.get("by"))
                elif u.path == "/api/replace-picture":
                    code, out = replace_picture(body.get("id"), body.get("key"), body.get("file"), body.get("by"))
                elif u.path == "/api/check":
                    f = C.folder_of(body.get("id"))
                    C._cache.clear()
                    code, out = 200, view_of(f, C.load(f), True)
                else:
                    code, out = 404, {"ok": False, "error": "not found"}
        except (ValueError, FileNotFoundError) as e:
            code, out = 404, {"ok": False, "error": str(e)}
        except SystemExit as e:
            code, out = 409, {"ok": False, "error": str(e)}
        self.send(code, out)


def main():
    global FAKE
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT") or 8795))
    ap.add_argument("--root", help="a scratch meta/ tree instead of the Drive's (trials)")
    ap.add_argument("--fake-meta", action="store_true", help="trials: a stand-in Meta, nothing is sent")
    ap.add_argument("--tailscale", action="store_true", default=os.environ.get("APPROVE_TAILSCALE") == "1",
                    help="also listen on this Mac's Tailscale address (private network only); or APPROVE_TAILSCALE=1")
    a = ap.parse_args()
    if a.root:
        os.environ["META_CARDS_ROOT"] = str(Path(a.root).resolve())
    if a.fake_meta:
        sys.path.insert(0, str(HERE / "tests"))
        from fake_meta import FakeMeta
        FAKE = FakeMeta
        U.LIVE = C.root() / "live.jsonl"            # trial ids never reach the real live list
    C.ensure_tree()
    print(f"approval page on http://localhost:{a.port}  cards: {C.root()}" + ("  (FAKE Meta)" if FAKE else ""), flush=True)
    if a.tailscale:
        threading.Thread(target=serve_tailscale, args=(a.port,), daemon=True).start()
    threading.Thread(target=upload_worker, daemon=True).start()
    resume_queue()
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
