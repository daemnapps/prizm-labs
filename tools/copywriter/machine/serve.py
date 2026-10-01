#!/usr/bin/env python3
"""Serves the copy board, always current, cache off.

    python3 serve.py            # → http://127.0.0.1:8778/board.html
    python3 serve.py 9000       # another port

Two things make it current rather than a snapshot:

- **It rebuilds before it serves.** Opening the page runs `board.py` first,
  so the board can never show yesterday's runs just because nobody
  remembered to regenerate it.
- **It sends no-cache headers.** The plain server sends none, so a browser
  holds the last board.html it saw — which looks exactly like a tool that
  has stopped working. Same trap the swipe machine's serve.py fixes.

Port 8778 on purpose: the swipe machine owns 8777, and two boards fighting
over one port is a confusing way to find out.
"""
import http.server
import importlib
import os
import re
import socketserver
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # machine/
PAGES = HERE.parent / "pages"
DEFAULT_PORT = 8778


class Board(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(PAGES), **kw)

    def send_head(self):
        """Byte-range support. Without it a browser will not scrub a video and
        Safari often refuses to play one at all — the same fix the swipe
        machine's serve.py carries, for the same reason."""
        rng = self.headers.get("Range")
        if not rng:
            return super().send_head()
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        if not m:
            return super().send_head()
        start = int(m.group(1)) if m.group(1) else 0
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end:
            self.send_error(416)
            return None
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self._limit = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        """Honour the range window set above; the default copies to EOF."""
        limit = getattr(self, "_limit", None)
        if limit is None:
            return super().copyfile(source, outputfile)
        self._limit = None
        while limit > 0:
            chunk = source.read(min(64 * 1024, limit))
            if not chunk:
                break
            outputfile.write(chunk)
            limit -= len(chunk)

    def do_GET(self):
        # Rebuild on every board request. The runs are small and local; the
        # cost is milliseconds and the alternative is a page that lies.
        if self.path.split("?")[0] in ("/", "/board.html"):
            try:
                sys.path.insert(0, str(HERE))
                import board
                # RELOAD, don't just import. Python caches modules, so a
                # long-running server keeps rebuilding with whatever code it
                # first imported — edit board.py or a prompt, refresh, and see
                # no change. That is indistinguishable from a broken tool, and
                # it cost a session to find. Reload the chain's modules too:
                # board reads STAGES from copy, and copy reads context.
                for name in ("paths", "context", "copy", "md", "board"):
                    mod = sys.modules.get(name)
                    if mod is not None:
                        importlib.reload(mod)
                sys.modules["board"].build()
            except Exception as e:
                print(f"  ! rebuild failed, serving the last good page: {e}")
            if self.path.split("?")[0] == "/":
                self.path = "/board.html"
        # The batch page gets the same treatment: rebuilt per request so it
        # never lies, refreshed by its own meta tag so nobody has to reload.
        if self.path.split("?")[0] == "/batch-status.html":
            try:
                sys.path.insert(0, str(HERE))
                import batch_status
                importlib.reload(batch_status)
                batch_status.build("ugc-andrea-v2", "Andrea v2 — voice fingerprint test")
            except Exception as e:
                print(f"  ! batch page rebuild failed, serving last good: {e}")
        return super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # the board is polled; the access log is noise


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("127.0.0.1", port), Board) as httpd:
            print(f"The Copy Machine → http://127.0.0.1:{port}/board.html")
            print("rebuilds on every load · ctrl-c to stop")
            httpd.serve_forever()
    except OSError as e:
        sys.exit(f"port {port} is busy ({e}). Try: python3 serve.py {port + 1}")
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
