#!/usr/bin/env python3
"""PF-18e (panel opens): clicking a Dev-queue tile opens its card panel, in a real browser.

    python3 components/page-features/test_pf18e_panel_opens.py

    The template platform/views/viewers/_templates/dev-queue.html, as it is in git, loaded in headless Chrome
    (CHROME_BIN, else /Applications/Google Chrome.app) from a stub server on 127.0.0.1 that answers /data/dev-queue
    with a fixture board: up next, in progress, shipped (with marks), flagged, reviewed and pre-cutoff cards, plus
    issues. Every card tile and every card chip is clicked with a real mouse press at its centre (Input.dispatchMouseEvent,
    so a layer sitting over the tile is caught too); each time the panel opens on that card, its Details list holds
    dt/dd pairs, and no page exception is logged (Runtime.exceptionThrown). A Shipped card's panel carries Understood,
    Question and Issue; a Flagged card's adds the open mark's Resolve, so all four marks (20 to 23) are reached; a card
    not shipped carries Question and Issue only (PF-18k (people views page)).

    Chrome is driven over the DevTools protocol by a small websocket client in this file (stdlib socket only), no node.
    No Chrome → prints SKIPPED with the reason; exits 0 only when CI_NO_CHROME=1 is set, else 1.

The fixture board is built by the real data command (dev_queue.build) from the fixture repos kept in the PF-18
(dev-queue view), PF-18b (review marks) and PF-18c (issue queue) test files, plus one more card here; no .md fixtures
under components/. Stdlib only, Python 3.9. Writes only in temp folders; no network beyond 127.0.0.1.
"""
import base64
import http.server
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "kit"))
import dev_queue  # noqa: E402
import features  # noqa: E402
import test_pf18_dev_queue as pf18  # noqa: E402  the fixture repo
import test_pf18b_review_marks as pf18b  # noqa: E402  the fixture repo with the review module, for marks
import test_pf18c_issue_queue as pf18c  # noqa: E402  the session list the issues are filed from

REAL = features.ROOT
PAGE = os.path.join(REAL, "platform/views/viewers/_templates/dev-queue.html")
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BUILD_AT = "2026-10-29T09:00:00Z"
# one more shipped card, so Reviewed holds a card both reviewers understood while Shipped and Flagged keep theirs
DECK_MORE = "### PF-17 — fixture card: both reviewers understood it (carded 2026-10-28; owner email_lead; DISPATCHED)\n"


def chrome_bin():
    """The browser to drive, or (None, why)."""
    path = os.environ.get("CHROME_BIN") or MAC_CHROME
    if not os.path.isfile(path) or not os.access(path, os.X_OK):
        return None, "no Chrome at %s (%s)" % (path, "CHROME_BIN" if os.environ.get("CHROME_BIN") else "default path")
    return path, ""


def board():
    """The fixture board: every column, marks and issues, from the real data command."""
    root = pf18b.workspace()
    try:
        deck = os.path.join(root, "new-workflow-design/builds/page-features/task-cards.md")
        with open(deck, "a", encoding="utf-8") as fh:
            fh.write(DECK_MORE)
        git = pf18.Repo(root)
        git.commit("lead: card PF-17 (fixture card)", "2026-10-28T16:30:00Z")
        git.merge("merge PF-17 (fixture card) — developer typed to the lead: \"merge PF-17\"", "2026-10-28T17:00:00Z")
        code, _out, err = pf18c.file_items(root)
        assert code == 0, err
        ids = pf18c.ids_by_title(root)
        code, _out, err = pf18c.run(root, "discussing", ids["A fresh copy has no email pictures"], "--by", "developer",
                                    "--with", "email_lead", "--now", "2026-10-29T07:30:00Z")
        assert code == 0, err
        env = dict((k, v) for k, v in os.environ.items() if k not in pf18b.NO_KEY)
        marks = [("PF-16", "understood", "email_lead", None), ("PF-15", "understood", "email_lead", None),
                 ("PF-15", "question", "designer", "why quick?"), ("PF-17", "understood", "email_lead", None),
                 ("PF-17", "understood", "designer", None)]
        for i, (card, word, by, note) in enumerate(marks):
            dev_queue.mark(root, card, word, by, note=note, env=env, commit=False, now="2026-10-29T08:00:%02dZ" % i)
        return dev_queue.build(root, now=BUILD_AT)
    finally:
        shutil.rmtree(root, True)


class Stub(object):
    """127.0.0.1 on a free port: / is the template as it is on disk, /data and /stamp answer the fixture."""

    def __init__(self, page, doc):
        self.asked = []
        stub = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                path = self.path.split("?")[0]
                stub.asked.append(path)
                if path in ("/", "/dev-queue.html"):
                    self.answer(200, "text/html; charset=utf-8", page)
                elif path == "/data/dev-queue":
                    self.answer(200, "application/json", json.dumps(doc).encode("utf-8"))
                elif path == "/stamp/dev-queue":
                    self.answer(200, "application/json", b'{"name": "dev-queue", "stamp": [1, 1]}')
                else:
                    self.answer(404, "text/plain", b"no")

            def answer(self, code, kind, body):
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/" % self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class Socket(object):
    """The smallest websocket client the DevTools protocol needs: text frames out (masked), frames in."""

    def __init__(self, url):
        rest = url.split("://", 1)[1]
        hostport, path = rest.split("/", 1)
        host, port = hostport.rsplit(":", 1)
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        self.sock.sendall(("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key))
                          .encode("ascii"))
        head = b""
        while b"\r\n\r\n" not in head:
            got = self.sock.recv(1)
            if not got:
                raise IOError("websocket handshake closed")
            head += got
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise IOError("websocket handshake refused: %r" % head[:200])

    def _exact(self, n):
        buf = b""
        while len(buf) < n:
            got = self.sock.recv(n - len(buf))
            if not got:
                raise IOError("websocket closed")
            buf += got
        return buf

    def send(self, text):
        data = text.encode("utf-8")
        n = len(data)
        head = bytes([0x81])
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        parts = []
        while True:
            b0, b1 = self._exact(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._exact(8))[0]
            mask = self._exact(4) if b1 & 0x80 else None
            data = self._exact(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            op = b0 & 0x0F
            if op == 0x8:
                raise IOError("websocket closed by the browser")
            if op == 0x9:                                   # ping: answer, keep reading
                continue
            parts.append(data)
            if b0 & 0x80:
                return b"".join(parts).decode("utf-8")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class Chrome(object):
    """Headless Chrome on its own temp profile, one page, driven over CDP; every page exception is kept."""

    def __init__(self, binary):
        self.profile = tempfile.mkdtemp(prefix="pf18e-chrome-")
        # --no-sandbox: Chrome's own sandbox cannot start inside another one (a worker's session sandbox says
        # "sandbox initialization failed: Operation not permitted" and the GPU process dies); the browser only ever
        # loads this repo's own template from 127.0.0.1, on a throwaway profile.
        self.proc = subprocess.Popen([binary, "--headless=new", "--remote-debugging-port=0", "--user-data-dir=" + self.profile,
                                      "--no-sandbox", "--no-first-run", "--no-default-browser-check", "--disable-gpu",
                                      "--disable-extensions", "--window-size=1600,1000", "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        self.ws = None
        try:
            self._connect()
        except Exception:
            self.quit()
            raise

    def _connect(self):
        port = None
        marker = os.path.join(self.profile, "DevToolsActivePort")
        for _ in range(300):
            if os.path.exists(marker):
                lines = pf18.read(marker).split("\n")
                if lines and lines[0].strip().isdigit():
                    port = int(lines[0])
                    break
            if self.proc.poll() is not None:
                break
            time.sleep(0.1)
        if not port:
            raise RuntimeError("Chrome did not open its debugging port (exit %s)" % self.proc.poll())
        page = None
        for _ in range(100):
            with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=10) as r:
                page = [t for t in json.loads(r.read().decode("utf-8")) if t.get("type") == "page"]
            if page:
                break
            time.sleep(0.1)
        if not page:
            raise RuntimeError("Chrome lists no page to drive")
        self.ws = Socket(page[0]["webSocketDebuggerUrl"])
        self.next_id = 0
        self.exceptions = []
        self.call("Runtime.enable")
        self.call("Page.enable")

    def _event(self, msg):
        if msg.get("method") == "Runtime.exceptionThrown":
            d = msg["params"]["exceptionDetails"]
            self.exceptions.append(((d.get("exception") or {}).get("description") or d.get("text", "")).split("\n")[0])

    def call(self, method, **params):
        self.next_id += 1
        mine = self.next_id
        self.ws.send(json.dumps({"id": mine, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mine:
                if "error" in msg:
                    raise RuntimeError("%s: %s" % (method, msg["error"]))
                return msg.get("result", {})
            self._event(msg)

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError("evaluate: %s" % r["exceptionDetails"].get("text"))
        return r["result"].get("value")

    def wait(self, expr, seconds=20):
        end = time.time() + seconds
        while time.time() < end:
            if self.js(expr):
                return True
            time.sleep(0.1)
        return False

    def press(self, x, y):
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left" if kind != "mouseMoved" else "none",
                      clickCount=1 if kind != "mouseMoved" else 0)

    def quit(self):
        try:
            if self.ws:
                self.ws.close()
        finally:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(10)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            shutil.rmtree(self.profile, True)


# Every clickable that opens a card: tile buttons on the board, card chips (issue tiles, decisions). Each target is
# found again by its index after every re-render, scrolled to the centre, and pressed where a person would press it.
TARGETS = "Array.from(document.querySelectorAll('button.tile-open, button.card-chip')).filter(b => !b.closest('#panel'))"
AIM = """(() => {
  const p = document.getElementById('panel'); if (p.open) p.close();
  const at = %%d;
  let b = %s[at];
  const fold = b.closest('details'); if (fold && !fold.open) fold.open = true;
  // narrowed for DQ-7 (folded columns): a folded column hides its tiles, so a person opens it first (its header
  // button); the board redraws, so the target is found again by its index
  const col = b.closest('section.column.folded');
  if (col) { col.querySelector('button.column-toggle').click(); b = %s[at]; }
  b.scrollIntoView({block: 'center', inline: 'center'});
  const r = b.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
  const hit = document.elementFromPoint(x, y);
  return {x: x, y: y, label: b.getAttribute('aria-label'), kind: b.className,
    column: (b.closest('section.column') || {}).id || (b.closest('[id]') || {}).id || '',
    on_top: hit && !b.contains(hit) ? (hit.id || hit.className || hit.tagName) : null};
})()""" % (TARGETS, TARGETS)
PANEL = """(() => {
  const p = document.getElementById('panel'), body = document.getElementById('panel-content');
  const dl = body.querySelector('dl.detail-list');
  return {open: p.open, ref: (body.querySelector('.panel-ref') || {}).textContent || '',
    title: (body.querySelector('.panel-title') || {}).textContent || '',
    details: dl ? Array.from(dl.children).map(e => e.tagName) : null,
    terms: dl ? Array.from(dl.querySelectorAll('dt')).map(e => e.textContent) : [],
    history: !!Array.from(body.querySelectorAll('h3')).find(e => e.textContent === 'History'),
    decisions: !!Array.from(body.querySelectorAll('h3')).find(e => e.textContent.indexOf('Decisions naming this card') === 0),
    marks: Array.from(body.querySelectorAll('button.mark-button')).map(e => e.getAttribute('data-mark'))};
})()"""


class PanelOpens(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        binary, _why = chrome_bin()
        cls.doc = board()
        cls.cards = pf18.by_id(cls.doc)
        with open(PAGE, "rb") as fh:
            cls.stub = Stub(fh.read(), cls.doc)
        cls.chrome = Chrome(binary)
        cls.chrome.call("Page.navigate", url=cls.stub.url)
        cls.ready = cls.chrome.wait("document.readyState === 'complete' && "
                                    "document.querySelectorAll('button.tile-open').length > 0")

    @classmethod
    def tearDownClass(cls):
        cls.chrome.quit()
        cls.stub.stop()

    def test_the_fixture_fills_every_column(self):
        cols = dict((c, sorted(k for k, v in self.cards.items() if v["column"] == c))
                    for c in ("up-next", "in-progress", "shipped", "flagged", "reviewed"))
        for c, got in cols.items():
            self.assertTrue(got, "fixture: nothing in %s" % c)
        # narrowed by the lead for PF-18f (earlier PF review): earlier PF cards now join Shipped, so membership, not the whole list
        self.assertIn("PF-16", cols["shipped"])
        self.assertEqual(cols["flagged"], ["PF-15"])
        self.assertIn("PF-17", cols["reviewed"], "both reviewers understood")
        # narrowed by the lead for PF-18f (earlier PF review): Reviewed holds only reviewed cards; a pre-cutoff PF card sits in Shipped
        self.assertFalse([k for k in cols["reviewed"] if not self.cards[k]["review"]], "Reviewed holds only reviewed cards")
        self.assertTrue([k for k in cols["shipped"] if k in ("PF-3", "PF-4b")], "a pre-cutoff PF card in Shipped")
        self.assertTrue(self.cards["PF-16"]["marks"], "a shipped card with marks")
        self.assertTrue(self.doc["issues"], "issues")

    def test_every_tile_opens_its_panel(self):
        self.assertTrue(self.ready, "the board never drew; page exceptions: %s" % self.chrome.exceptions)
        c = self.chrome
        self.assertEqual(c.exceptions, [], "the board loads without an exception")
        n = c.js(TARGETS + ".length")
        tiles = c.js(TARGETS + ".filter(b => b.className === 'tile-open').length")
        self.assertEqual(tiles, len(self.doc["cards"]), "one tile per card, pre-cutoff fold included")
        self.assertGreater(n, tiles, "card chips on issue tiles and decisions are clicked too")
        seen = {}
        for i in range(n):
            aim = c.js(AIM % i)
            where = "%s %r in %s" % (aim["kind"], aim["label"], aim["column"])
            self.assertIsNone(aim["on_top"], "%s: %s sits over it, a press never reaches it" % (where, aim["on_top"]))
            before = len(c.exceptions)
            c.press(aim["x"], aim["y"])
            got = c.js(PANEL)
            self.assertEqual(c.exceptions[before:], [], "%s: the press threw" % where)
            self.assertTrue(got["open"], "%s: the panel did not open" % where)
            card = aim["label"][len("Open "):].split(" (")[0]
            if card.startswith("on "):
                card = card[3:]
            self.assertIn(card, self.cards, where)
            self.assertTrue(got["ref"].startswith(card), "%s: the panel is on %s" % (where, got["ref"]))
            self.assertTrue(got["title"] and got["history"] and got["decisions"], (where, got))
            self.assertIsNotNone(got["details"], "%s: no Details list" % where)
            self.assertTrue(got["details"] and len(got["details"]) % 2 == 0 and
                            got["details"] == ["DT", "DD"] * (len(got["details"]) // 2),
                            "%s: Details is dt/dd pairs, got %s" % (where, got["details"]))
            # narrowed by the lead for PF-18g (built by): the panel names the builder and the build owner
            self.assertEqual(got["terms"][:2], ["Deck", "Family"], where)
            self.assertIn("Asked by", got["terms"], where)   # renamed from Built by by DQ-6 (built by label)
            self.assertIn("Build owner", got["terms"], where)
            seen[card] = got
        self.assertEqual(sorted(seen), sorted(self.cards), "every card's panel opened")
        self.assertEqual(c.exceptions, [], "zero page exceptions")
        self.assertEqual(seen["PF-16"]["marks"], ["understood", "question", "issue"], "a Shipped card's marks")
        self.assertEqual(seen["PF-15"]["marks"], ["resolve", "understood", "question", "issue"],
                         "a Flagged card: the open mark's Resolve plus the three, all four marks")
        # narrowed for PF-18k (people views page): Question and Issue on any card on the board, Understood only once
        # shipped (PF-18j (people data)'s rule); a card with no marks yet that is not shipped offers no Understood
        for k, v in seen.items():
            if self.cards[k]["marks"] is None:
                self.assertEqual(v["marks"], ["question", "issue"], "%s is not shipped: no Understood" % k)
        self.assertIn("Merge commit", seen["PF-16"]["terms"])
        self.assertIn("Request", seen["PF-12"]["terms"])
        self.assertEqual([p for p in self.stub.asked if p.startswith("/data/") or p.startswith("/stamp/")],
                         ["/data/dev-queue", "/stamp/dev-queue"], "opening panels reads nothing more")


def main():
    binary, why = chrome_bin()
    if not binary:
        print("SKIPPED: %s; set CHROME_BIN to a Chrome or Chromium binary" % why)
        sys.exit(0 if os.environ.get("CI_NO_CHROME") == "1" else 1)
    unittest.main()


if __name__ == "__main__":
    main()
