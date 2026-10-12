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
127.0.0.1 only.
"""
import argparse, io, json, mimetypes, os, sys, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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
            card = C.check_and_save(folder, meta=meta_for(w["brand"]))
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
        media.append({"name": f, "kind": kind, "src": f"/media/{cid}/{f}", "thumb": f"/thumb/{cid}/{f}",
                      **({"cover": f"/media/{cid}/{cover}"} if cover else {})})
    checks = [{"key": k, "label": C.LABELS.get(k, k), **v} for k, v in (card.get("checks") or {}).items()]
    return {"id": cid, **w, "brand_label": brand_label(w["brand"]), "format": card.get("format", "flexible"),
            "ad_name": card.get("ad_name"), "words": __import__("to_check").clean_words(card.get("words")),  # as Meta will show it
            "pages": card.get("pages") or [],
            "account": account, "account_id": b.account_id if b else "",
            "goes": goes, "media": media, "checks": checks, "passed": C.passed(card) if checks else False,
            "approval": card.get("approval"), "meta": card.get("meta") or [], "upload_error": card.get("upload_error"),
            "made_by": card.get("made_by"), "made_at": card.get("made_at"), "checked_at": card.get("checked_at"),
            "copy_checked": bool(card.get("copy_checked"))}


def cards_json(view, brand=None, lane=None):
    state = VIEWS.get(view, "1-check")
    folders = C.listing(state=state, brand=brand or None, lane=lane or None)
    run = state in ("1-check", "2-approved")
    with ThreadPoolExecutor(6) as ex:
        out = list(ex.map(lambda f: view_of(f, C.load(f), run), folders))
    return {"view": view, "cards": out, "counts": counts(brand, lane), "brands": [{"id": b, "label": brand_label(b)} for b in C.brands()],
            "lanes": list(C.LANES), "root": str(C.root()), "fake": bool(FAKE),
            "approvers": approvers(), "reasons": reasons_for_page()}


def counts(brand=None, lane=None):
    return {v: len(C.listing(state=s, brand=brand or None, lane=lane or None)) for v, s in VIEWS.items()}


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
    against the running library (creative-diversity/check.py). Cached on the card by
    media, so it runs once per ad. A failure to score leaves the check red, never green."""
    if FAKE:
        return ""
    try:
        sys.path.insert(0, str(HERE.parent / "creative-diversity"))
        import check as D
        D.score_card(folder)
        return ""
    except Exception as e:  # noqa: BLE001
        print(f"diversity not scored for {folder.name}: {e}", file=sys.stderr, flush=True)
        return f"{type(e).__name__}: {e}"


def approve(cid, start, by=None):
    # the owner, 7 Oct 2026: no silent default. The NOVA face scrub ad sat paused
    # for three days because the page started every approve as Paused.
    if start not in ("ACTIVE", "PAUSED"):
        return 400, {"ok": False, "error": "pick On or Paused — the approve needs one"}
    folder = C.folder_of(cid)
    if C.where(folder)["state"] != "1-check" or not (folder / "card.json").is_file():
        return 409, {"ok": False, "error": "this card is not waiting in 1-check any more — reload"}
    by = who(by)
    why = score_diversity(folder)
    card = C.check_and_save(folder, meta=meta_for(C.where(folder)["brand"]))
    if not FAKE and not card.get("diversity"):
        # the reason goes on the page (9 Oct 2026: two clicks refused with no reason the owner could act on)
        return 409, {"ok": False, "error": "couldn't read this ad to score it against what's running"
                     + (f" ({why})" if why else " (the scorer gave no score)") + " — nothing was sent to Meta"}
    if not C.passed(card):
        bad = [f"{C.LABELS.get(k, k)}: {v['why']}" for k, v in card["checks"].items() if not v["ok"]]
        return 409, {"ok": False, "error": "a machine check is failing — " + "; ".join(bad)}
    card["approval"] = {"by": by, "at": now(), "decision": "approve",
                        "start": start}
    C.save(folder, card)
    folder = C.move(folder, "2-approved")
    return 200, run_upload(folder)


def retry(cid):
    folder = C.folder_of(cid)
    if C.where(folder)["state"] != "2-approved":
        return 409, {"ok": False, "error": "only an approved card can be retried"}
    return 200, run_upload(folder)


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
                    code, out = approve(body.get("id"), body.get("start"), body.get("by"))
                elif u.path == "/api/retry":
                    code, out = retry(body.get("id"))
                elif u.path == "/api/disapprove":
                    code, out = disapprove(body.get("id"), body.get("reasons"), body.get("note"), body.get("by"))
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
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
