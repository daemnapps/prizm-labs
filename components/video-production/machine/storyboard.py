#!/usr/bin/env python3
"""
storyboard.py — the production board for one ad.

    python3 machine/storyboard.py <run folder>     # then open the link

Every scene in the brief is a card. A card shows what happens, what is said
and how, and what is standing in the frame right now — a generated take, a
clip we already own, or nothing yet. Regen any card. Swap in owned footage
where it exists. Send the whole thing to Premiere when it holds together.

**A regen is written into a queue** and, since 2026-09-18, drained on the
direct doors by `drain.py` — no session, no house. The board never
pretends a take exists that does not, because a
storyboard that lies about its own state is worse than no storyboard.
"""

from __future__ import annotations

import json
import mimetypes
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenes as SC                                    # noqa: E402

PORT = 8455
INDEX = "http://127.0.0.1:8420"                        # the footage library
RUN: Path = Path()


# ------------------------------------------------------------------ state

def board_file() -> Path:
    return RUN / "storyboard.json"


def load_board(force: bool = False) -> dict:
    f = board_file()
    if f.exists() and not force:
        return json.loads(f.read_text())
    b = SC.load(RUN)
    b["queue"] = []
    save_board(b)
    return b


def save_board(b: dict) -> None:
    board_file().write_text(json.dumps(b, indent=1))


def scene(b: dict, n: int) -> dict | None:
    return next((s for s in b["scenes"] if s["n"] == n), None)


# ------------------------------------------------------- owned footage

def match_footage(s: dict, limit: int = 4) -> list[dict]:
    """What the library already has for this scene.

    A beat we own is a beat nobody pays to generate. The brief's own words are
    the query — what happens for a B, what is said for an A.
    """
    # The query is one dense sentence, not the whole card. A scene's prose runs
    # to sixty words and the match then has to cover all of them, which returns
    # nothing — the first sentence of the action, or the line being said, is
    # what the footage would actually show.
    beat = (s.get("say") or "").strip()
    happens = (s.get("happens") or s.get("product") or s.get("source") or "").strip()
    if happens:
        first = re.split(r"(?<=[.!?])\s+", happens)[0]
        beat = (first + " " + beat).strip() if len(first) < 220 else first
    beat = beat[:260]
    if not beat:
        return []
    body = json.dumps({"beats": [{"n": s["n"], "beat": beat,
                                  "timing": f'{s["start"]}-{s["end"]}'}],
                       "per_beat": limit,
                       # browsing, not answering — show candidates to judge
                       "min_cover": 0.18, "floor": 0.55}).encode()
    try:
        r = urllib.request.Request(INDEX + "/api/recommend", data=body,
                                   headers={"Content-Type": "application/json"})
        d = json.load(urllib.request.urlopen(r, timeout=20))
        return (d.get("beats") or [{}])[0].get("picks") or []
    except Exception:
        return []


# ------------------------------------------------------------------ web

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, payload, ctype="application/json"):
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload).encode()
        elif isinstance(payload, str):
            payload = payload.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return json.loads(self.rfile.read(n)) if n else {}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)

        if u.path in ("/", "/index.html"):
            page = HERE / "storyboard.html"
            return self._send(200, page.read_bytes(), "text/html; charset=utf-8")

        if u.path == "/api/board":
            return self._send(200, load_board())

        if u.path == "/api/match":
            b = load_board()
            s = scene(b, int(q.get("n", ["0"])[0]))
            if not s:
                return self._send(404, {"error": "no such scene"})
            return self._send(200, {"picks": match_footage(s)})

        if u.path == "/api/take":
            # a generated take, or a cut of owned footage, served from disk
            f = RUN / "takes" / Path(q.get("f", [""])[0]).name
            if not f.exists():
                return self._send(404, b"", "text/plain")
            return self._send(200, f.read_bytes(),
                              mimetypes.guess_type(f.name)[0] or "application/octet-stream")

        return self._send(404, {"error": "no such endpoint"})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        body = self._body()
        b = load_board()

        if u.path == "/api/regen":
            # A request; drain.py makes it on the direct doors. The card says
            # "queued" until a take lands, and never before.
            s = scene(b, int(body.get("n", 0)))
            if not s:
                return self._send(404, {"error": "no such scene"})
            b["queue"] = [x for x in b.get("queue", []) if x["n"] != s["n"]]
            b["queue"].append({"n": s["n"], "type": s["type"],
                               "note": body.get("note", ""),
                               "asked": body.get("asked") or ""})
            s["status"] = "queued"
            save_board(b)
            return self._send(200, {"queued": s["n"], "depth": len(b["queue"])})

        if u.path == "/api/use":
            # pin a clip from the footage library to this scene
            s = scene(b, int(body.get("n", 0)))
            if not s:
                return self._send(404, {"error": "no such scene"})
            s["takes"].append({"kind": "owned", "clip_id": body.get("clip_id"),
                               "creator": body.get("creator"),
                               "start": body.get("start"), "end": body.get("end"),
                               "label": body.get("label", "")})
            s["chosen"] = len(s["takes"]) - 1
            s["status"] = "owned"
            save_board(b)
            return self._send(200, {"ok": True, "scene": s["n"]})

        if u.path == "/api/choose":
            s = scene(b, int(body.get("n", 0)))
            if s and 0 <= int(body.get("i", -1)) < len(s["takes"]):
                s["chosen"] = int(body["i"])
                save_board(b)
                return self._send(200, {"ok": True})
            return self._send(400, {"error": "no such take"})

        if u.path == "/api/reset":
            return self._send(200, load_board(force=True))

        return self._send(404, {"error": "no such endpoint"})


def main():
    global RUN
    if len(sys.argv) < 2:
        sys.exit("storyboard.py <run folder>")
    RUN = Path(sys.argv[1]).expanduser().resolve()
    (RUN / "takes").mkdir(exist_ok=True)
    b = load_board()
    print(f"{b['title']} — {len(b['scenes'])} scenes, {b['runtime']}s")
    print(f"storyboard -> http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
