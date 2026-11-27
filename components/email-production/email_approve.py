#!/usr/bin/env python3
"""The email approval page — every checked Klaviyo draft on one card; the owner's
Approve → Schedule schedules it (never sends it now). EP-3 (email approval card).

    python3 email_approve.py              # http://localhost:8797  (launch config "email-approve")
    python3 email_approve.py --root <scratch runs/email-production> --handoffs <staging> \\
        --fake-klaviyo --switch <scratch send-switch.json>   # trials: nothing reaches Klaviyo

Cards: <root>/<brand>/<label>/deliverable/email-card.json (default root
runs/email-production in the workspace), plus every --handoffs
<dir>/klaviyo-uploader/<brand>/<name>/email-card.json. klaviyo_upload.py writes
them; this page never makes one.

**Approve → Schedule** runs klaviyo_upload.schedule_card: every check again,
the draft read back from Klaviyo and refused on any change, a fixed send time
at least 30 minutes away, not the mini and not a worker or lab-run job,
the team's off-switch (send-switch.json) on, and a name on approvers.json.
Then the one Klaviyo call, campaign-send-jobs. A failed call leaves the card
`approved`; Retry is a fresh click. **Send back** needs one or more reasons
(send-back-reasons.json) and a note; the draft stays in Klaviyo.

the owner's own Claude reads GET /api/waiting (plain JSON) and acts on his typed
word through the same POSTs. Nothing here runs on a timer.

Listens on 127.0.0.1 only. Every request must name this page as its Host
(blocks DNS rebinding); every POST must be Content-Type: application/json
(blocks a cross-site form post).
"""
import klaviyo_upload as K      # FIRST: it takes this folder (and its email.py) off sys.path before http.client loads `email` (simple_email.py:44-47)

import argparse                 # noqa: E402
import importlib.util           # noqa: E402
import json                     # noqa: E402
import os                       # noqa: E402
import sys                      # noqa: E402
import threading                # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer   # noqa: E402
from pathlib import Path        # noqa: E402
from urllib.parse import urlparse, parse_qs, unquote                  # noqa: E402

PAGE = K.HERE / "email_approve.html"
PORT = 8797
STATES = ("waiting", "approved", "scheduled", "sent-back")
LOCK = threading.Lock()          # one approve / retry / send-back at a time
ROOT = K.WORKSPACE / "runs" / "email-production"
HANDOFFS = []
FAKE = None                      # --fake-klaviyo: the stand-in Klaviyo
ONLINE = True                    # link fetches at Approve; off with --fake-klaviyo
ENV = None                       # tests only: the env / home the machine-run guard reads
HOME = None


class NotFound(Exception):
    pass


def _fake_module():
    """fake_klaviyo.py, loaded by path: this folder is off sys.path by now."""
    spec = importlib.util.spec_from_file_location("fake_klaviyo", K.HERE / "fake_klaviyo.py")
    mod = sys.modules.get("fake_klaviyo") or importlib.util.module_from_spec(spec)
    if "fake_klaviyo" not in sys.modules:
        spec.loader.exec_module(mod)
        sys.modules["fake_klaviyo"] = mod
    return mod


def card_files():
    """id -> (how, folder, the card file). Run cards are "<brand>/<label>",
    hand-off cards "handoff/<folder name>"."""
    out = {}
    for f in sorted(Path(ROOT).glob(f"*/*/deliverable/{K.CARD}")):
        out[f"{f.parts[-4]}/{f.parts[-3]}"] = ("run", f.parent.parent, f)
    for h in HANDOFFS:
        for f in sorted(Path(h).glob(f"klaviyo-uploader/*/*/{K.CARD}")):
            out[f"handoff/{f.parent.name}"] = ("handoff", f.parent, f)
    if FAKE is not None:
        for _, _, f in out.values():
            FAKE.know(f)
    return out


def job_for(cid):
    hit = card_files().get(cid) if isinstance(cid, str) else None
    if not hit:
        raise NotFound(f"no email card {cid!r}")
    how, folder, _ = hit
    if how == "run":
        return K.from_run(folder, Path(folder).parent.name)
    return K.from_handoff(folder)


def row_of(cid, card):
    checks = card.get("checks") or []
    return {"id": cid, "brand": card.get("brand"), "email": card.get("email"),
            "campaign_id": card.get("campaign_id"), "campaign_name": card.get("campaign_name"),
            "klaviyo_link": card.get("klaviyo_link"), "subject": card.get("subject"),
            "preview": card.get("preview"), "audience": card.get("audience") or [],
            "send": card.get("send") or {}, "checks": checks,
            "checks_ok": bool(checks) and all(r.get("result") != "PROBLEM" for r in checks),
            "state": card.get("state"), "approval": card.get("approval"),
            "scheduled": card.get("scheduled"), "schedule_error": card.get("schedule_error"),
            "preview_url": f"/preview/{cid}"}


def rows(state):
    out = []
    for cid, (_, _, f) in card_files().items():
        try:
            card = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if card.get("state") == state:
            out.append(row_of(cid, card))
    return out


def listing(state, key):
    return {key: rows(state), "state": state, "approvers": K.approvers(), "switch": K.switch_state(),
            "fake": FAKE is not None, "reasons": [{"id": r["id"], "label": r.get("label")} for r in K.reasons()]}


def answer(path, body):
    """One POST -> (code, body). Runs under LOCK."""
    if path not in ("/api/approve", "/api/retry", "/api/send-back"):
        return 404, {"ok": False, "error": "not found"}
    cid = body.get("id")
    if not isinstance(cid, str) or not cid:
        return 400, {"ok": False, "error": "name the card: {\"id\": \"<brand>/<label>\"}"}
    by = body.get("by")
    if by is not None and not isinstance(by, str):
        return 400, {"ok": False, "error": "\"by\" is a name"}
    job = job_for(cid)
    if path == "/api/send-back":
        reasons, note = body.get("reasons"), body.get("note")
        if not isinstance(reasons, list) or not all(isinstance(r, str) for r in reasons) \
                or (note is not None and not isinstance(note, str)):
            return 400, {"ok": False, "error": "send back takes {\"reasons\": [ids], \"note\": \"why\"}"}
        card = K.send_back(job, by, reasons, note)
        campaign = card.get("campaign_id")
    else:
        if path == "/api/retry":
            card = K.read_card(job) or {}
            if card.get("state") != "approved":
                raise K.Held(["only an approved card whose schedule failed can be retried"])
        campaign, card = K.schedule_card(job, by, env=ENV, home=HOME, online=ONLINE)
    return 200, {"ok": True, "state": card.get("state"), "id": cid, "campaign_id": campaign}


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

    def host_ok(self):
        """Only this page by its own name — a rebound DNS name is refused."""
        port = self.server.server_address[1]
        return (self.headers.get("Host") or "").strip().lower() in (f"127.0.0.1:{port}", f"localhost:{port}")

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self.host_ok():
            return self.send(403, {"ok": False, "error": "this page answers only to localhost"})
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if u.path == "/api/waiting":
                return self.send(200, listing("waiting", "waiting"))
            if u.path == "/api/cards":
                state = q.get("state", "waiting")
                if state not in STATES:
                    return self.send(400, {"ok": False, "error": f"state is one of {', '.join(STATES)}"})
                return self.send(200, listing(state, "cards"))
            if u.path.startswith("/preview/"):
                cid = unquote(u.path[len("/preview/"):])
                hit = card_files().get(cid)
                if not hit:
                    raise NotFound(f"no email card {cid!r}")
                f = hit[2].parent / K.CARD_HTML
                # Klaviyo's HTML, shown sandboxed: no script runs on this page's origin
                return self.send(200, f.read_bytes(), "text/html; charset=utf-8",
                                 {"Content-Security-Policy": "sandbox"})
        except (NotFound, FileNotFoundError) as e:
            return self.send(404, {"ok": False, "error": str(e)})
        self.send(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if not self.host_ok():
            return self.send(403, {"ok": False, "error": "this page answers only to localhost"})
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return self.send(415, {"ok": False, "error": "send Content-Type: application/json"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("not an object")
        except ValueError:
            return self.send(400, {"ok": False, "error": "bad request — a JSON object"})
        try:
            with LOCK:
                code, out = answer(urlparse(self.path).path, body)
        except K.Held as h:
            code, out = 409, {"ok": False, "error": "; ".join(h.args[0])}
        except NotFound as e:
            code, out = 404, {"ok": False, "error": str(e)}
        except SystemExit as e:          # an engine refusal (a brand file missing, …)
            code, out = 409, {"ok": False, "error": str(e.code)}
        self.send(code, out)


def server(argv=None):
    """Parse the line and make the server (not started) — main() and the tests."""
    global ROOT, HANDOFFS, FAKE, ONLINE
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT") or PORT))
    ap.add_argument("--root", default=str(ROOT), help="the runs/email-production tree to read cards from")
    ap.add_argument("--handoffs", action="append", default=[],
                    help="a staging folder holding klaviyo-uploader hand-offs (repeatable)")
    ap.add_argument("--fake-klaviyo", action="store_true", help="trials: a stand-in Klaviyo, nothing is sent")
    ap.add_argument("--switch", help="--fake-klaviyo only: a scratch send-switch.json")
    a = ap.parse_args(argv)
    if a.switch and not a.fake_klaviyo:
        ap.error("--switch is for trials only (with --fake-klaviyo); the real switch is send-switch.json")
    ROOT = Path(a.root).resolve()
    HANDOFFS = [Path(h).resolve() for h in a.handoffs]
    if a.fake_klaviyo:
        FAKE = _fake_module().FakeKlaviyo.from_cards([f for _, _, f in card_files().values()],
                                                    html_name=K.CARD_HTML)
        K.S.kl = FAKE.kl
        K.S.kl_key = lambda lk: "fake"
        ONLINE = False
        if a.switch:
            K.SWITCH_F = Path(a.switch).resolve()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    srv.daemon_threads = True
    return srv


def main(argv=None):
    srv = server(argv)
    print(f"email approval page on http://localhost:{srv.server_address[1]}  cards: {ROOT}"
          + "".join(f" + {h}" for h in HANDOFFS)
          + (f"  (FAKE Klaviyo — nothing reaches Klaviyo; switch {K.SWITCH_F})" if FAKE else ""), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
