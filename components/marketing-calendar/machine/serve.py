#!/usr/bin/env python3
"""Serves a planned month for review, and does what the reviewer asks.

    python3 serve.py                      # newest run, → http://127.0.0.1:8786
    python3 serve.py --run <brand>/2026-09      # or a path to the month
    python3 serve.py --port 8790

Two things make it a workbench rather than a page:

- **It rebuilds before it serves.** Every load of the board re-renders from
  `slots.json` + `review.json`, so it can never show a stale month just
  because nobody remembered to regenerate it. No-cache headers too — a
  browser holding yesterday's HTML looks exactly like a broken tool.
- **It writes the reviewer's decisions down**, into `review.json` beside the
  run, never into the planner's own record.

The hand-off — "write the copy" — is deliberately NOT hardcoded. What writes
copy for an email month is not what builds a static ad, and this component
plans both. `handoff.json` in the component root names the command; the board
just asks for it by slot id.
"""
import argparse
import html
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import paths
from paths import COMPONENT, RUNS, WORKSPACE
import month as MONTH
import board
import review as R

# 8785–8787 and 8791–8792 already belong to his other boards; two boards
# fighting over one port is a confusing way to find that out.
DEFAULT_PORT = 8788
HANDOFF = COMPONENT / "handoff.json"


def newest_run():
    runs = paths.months()
    if not runs:
        sys.exit(f"no planned months in {RUNS} — run calendar.py first")
    return max(runs, key=lambda d: (d / "slots.json").stat().st_mtime)


def handoff_for(run_dir, slot_ids):
    """The command that turns approved slots into copy, per `handoff.json`:

        {"<pattern>": {"cwd": "...", "argv": ["python3","run_month.py","{run}",
                                              "--only","{slots}"]}}

    A pattern matching `<brand>/<YYYY-MM>` wins; `default` is the fallback.
    `{run}` is the run folder, `{slots}` the comma-joined ids, `{run_name}`
    its bare name.
    """
    try:
        conf = json.loads(HANDOFF.read_text())
    except (FileNotFoundError, ValueError):
        return None, "No hand-off is configured — set one in handoff.json."
    name = Path(run_dir).name
    where = f"{Path(run_dir).parent.name}/{name}"      # <brand>/<YYYY-MM>
    spec = None
    for pattern, s in conf.items():
        if pattern != "default" and pattern in where:
            spec = s
            break
    spec = spec or conf.get("default")
    if not spec:
        return None, f"No hand-off configured for {name}."
    subs = {"run": str(run_dir), "run_name": name, "slots": ",".join(slot_ids)}
    argv = [a.format(**subs) for a in spec["argv"]]
    cwd = Path(spec.get("cwd", ".").format(**subs))
    if not cwd.is_absolute():
        cwd = (WORKSPACE / cwd).resolve()     # workspace-relative, never file-relative
    if not cwd.is_dir():
        return None, f"The hand-off's folder is missing: {cwd}"
    return (argv, cwd), None


def send_target(want):
    """The send file a /source?path= value names, or None."""
    m = re.fullmatch(r"brands/([^/]+)/([^/]+)/sends/([^/]+\.md)", want or "")
    if not m or m.group(1).startswith(".") or m.group(3).startswith("."):
        return None
    brand, fname = m.group(1), m.group(3)
    target = (WORKSPACE / want).resolve()
    if not (str(target).startswith(str(WORKSPACE.resolve())) and target.is_file()):
        return None
    BP = MONTH.CH.BP
    allowed = {c.resolve() for c in BP.candidates(brand, "email-sms", "sends", fname,
                                                  root=WORKSPACE / "brands")}
    if target not in allowed:
        return None
    return target


class Handler(http.server.SimpleHTTPRequestHandler):
    run_dir = None

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(self.run_dir), **kw)

    def log_message(self, fmt, *a):        # one line per action, not per asset
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    # ---------------------------------------------------------------- GET ---
    def do_GET(self):
        # THE CALENDAR IS THE FRONT PAGE. the owner, 2026-09-14: "I just need to see
        # the days the emails and such — we don't need this big page with the
        # buttons to generate text just yet, just a calendar." The review board
        # is still one click away, for the day the reviewing starts.
        route = self.path.split("?", 1)[0]          # a cache-buster is not a path
        if route in ("/", "/index.html", "/calendar.html"):
            MONTH.build(paths.SYSTEM / "calendar.html", quiet=True)
            self.directory = str(paths.SYSTEM)
            self.path = "/calendar.html"
            return super().do_GET()
        if route == "/source":
            return self.serve_source()
        self.directory = str(self.run_dir)
        if route == "/board.html":
            board.build(self.run_dir, quiet=True)
        return super().do_GET()

    def serve_source(self):
        """The email a send is written off, readable.

        the owner, 2026-09-14: "I need a deep link into... the format. Where is it
        coming from? I need you to make it so those links are actually
        clickable, so that way we can actually see what the copy would be
        based on."

        Only ever a brand's own send library, and only markdown — the path is
        checked against that shape before anything is opened, because a query
        string is a stranger's input even on a local page.
        """
        from urllib.parse import urlparse, parse_qs, unquote
        want = unquote((parse_qs(urlparse(self.path).query).get("path") or [""])[0])
        target = send_target(want)
        if target is None:
            return self._page("Not a send", f"<p>No readable send at "
                              f"<code>{html.escape(want)}</code>.</p>")
        body = html.escape(target.read_text())
        return self._page(target.name, f"<pre>{body}</pre>",
                          sub=f"{want} · {target.stat().st_size:,} bytes")

    def _page(self, title, body, sub=""):
        doc = f"""<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{--bg:#F1F0EA;--card:#fff;--ink:#191B1D;--mut:#676C73;--line:#DBD9D2;--acc:#2E5D50}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0E1012;--card:#16191C;--ink:#E6E8EA;
  --mut:#8E959D;--line:#272B30;--acc:#74B4A2}}}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.6 "Instrument Sans",system-ui,sans-serif}}
.w{{max-width:820px;margin:0 auto;padding:34px 22px 80px}}
h1{{font:640 27px/1.1 Fraunces,Georgia,serif;margin:0 0 4px;letter-spacing:-.015em}}
.s{{font:11px/1.5 "Spline Sans Mono",ui-monospace,monospace;color:var(--mut);
 word-break:break-all;margin-bottom:20px}}
a{{color:var(--acc)}}
pre{{background:var(--card);border:1px solid var(--line);border-radius:12px;
 padding:20px;white-space:pre-wrap;word-wrap:break-word;
 font:13px/1.65 "Spline Sans Mono",ui-monospace,monospace;margin:0}}
</style>
<div class="w"><a href="/">&larr; the calendar</a>
<h1>{html.escape(title)}</h1><div class="s">{html.escape(sub)}</div>{body}</div>"""
        blob = doc.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    # --------------------------------------------------------------- POST ---
    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _json(self, obj, code=200):
        blob = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def do_POST(self):
        try:
            b = self._body()
            if self.path == "/api/status":
                R.set_status(self.run_dir, b["slot"], b["status"])
                print(f"  {b['slot']}  → {b['status']}")
                return self._json({"ok": True})
            if self.path == "/api/note":
                R.set_note(self.run_dir, b["slot"], b.get("note", ""))
                print(f"  {b['slot']}  note")
                return self._json({"ok": True})
            if self.path == "/api/edit":
                R.set_edit(self.run_dir, b["slot"], b["field"], b.get("value", ""))
                print(f"  {b['slot']}  {b['field']} rewritten")
                return self._json({"ok": True})
            if self.path == "/api/write":
                return self._json(self.write_copy(b.get("slots") or []))
            return self._json({"error": "no such action"}, 404)
        except Exception as e:                              # noqa: BLE001
            return self._json({"error": str(e)}, 400)

    def write_copy(self, slot_ids):
        if not slot_ids:
            return {"message": "Nothing selected.", "refused": []}
        # Only a send the board shows as approved goes to the writer — read
        # through applied(), so an approval made for another send does not
        # count (CAL-1 (calendar gates hold), SI-148, 2026-10-08).
        status = {s["id"]: s["_review"]["status"]
                  for s in R.applied(R.month_slots(self.run_dir), R.load(self.run_dir))}
        refused = [s for s in slot_ids if status.get(s) != "approved"]
        slot_ids = [s for s in slot_ids if s not in refused]
        why = (f" Not approved, not written: {', '.join(refused)}." if refused else "")
        if refused:
            print(f"  refused (not approved): {' '.join(refused)}")
        if not slot_ids:
            return {"message": "Nothing approved to write." + why, "refused": refused}
        got, err = handoff_for(self.run_dir, slot_ids)
        if err:
            return {"message": err + why, "refused": refused}
        argv, cwd = got
        d = R.load(self.run_dir)
        for s in slot_ids:
            d["copy"][s] = {"state": "running", "at": R.now()}
        R.save(self.run_dir, d)
        print(f"  writing copy for {len(slot_ids)}: {' '.join(argv)}")

        def run():
            log = Path(self.run_dir) / "copy.log"
            with log.open("a") as f:
                f.write(f"\n=== {R.now()}  {' '.join(argv)}\n")
                rc = subprocess.run(argv, cwd=str(cwd), stdout=f,
                                    stderr=subprocess.STDOUT).returncode
            d = R.load(self.run_dir)
            for s in slot_ids:
                d["copy"][s] = {"state": "done" if rc == 0 else "failed",
                                "at": R.now()}
            R.save(self.run_dir, d)
            print(f"  copy {'done' if rc == 0 else 'FAILED'} "
                  f"({len(slot_ids)} sends) — see copy.log")

        threading.Thread(target=run, daemon=True).start()
        n = len(slot_ids)
        return {"message": f"Writing {n} send{'' if n == 1 else 's'} — "
                           f"the board shows each one as it lands." + why,
                "refused": refused}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="<brand>/<YYYY-MM> under runs/marketing-calendar/, or a path")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()

    if a.run:
        p = Path(a.run)
        run_dir = p if p.is_dir() else RUNS / a.run
        if not (run_dir / "slots.json").is_file():
            sys.exit(f"{run_dir} is not a planned month (no slots.json)")
    else:
        run_dir = newest_run()

    Handler.run_dir = run_dir
    board.build(run_dir, quiet=True)
    url = f"http://127.0.0.1:{a.port}/"
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", a.port), Handler) as httpd:
        print(f"the calendar     {url}\n"
              f"the review board {url}board.html   ({run_dir.parent.name}/{run_dir.name})\n"
              f"ctrl-c to stop\n")
        if not a.no_open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


if __name__ == "__main__":
    main()
