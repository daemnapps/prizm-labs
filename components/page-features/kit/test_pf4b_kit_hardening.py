#!/usr/bin/env python3
"""PF-4b (kit hardening): serve.py answers only its own Mac's names, serves only the runs/ folders a family
declares, answers /stamp without running the source, says when the clone is behind, and refuses to start without
what its commands need. No network, no real git, no real Chrome.

    python3 components/page-features/kit/test_pf4b_kit_hardening.py

tree()/up()/get() are copied from test_serve.py (importing it would run its checks and exit).
"""
import contextlib
import http.client
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402

RESULTS = []
WATCH = ["runs/email-production/*/*/klaviyo/email.html"]


def check(name, fn):
    try:
        fn()
        RESULTS.append(True)
        print("PASS  " + name)
    except Exception as e:  # noqa: BLE001
        RESULTS.append(False)
        print("FAIL  %s — %r" % (name, e))


def tree(decl=None):
    decl = decl if decl is not None else {"runs": ["email-production/"],
                                          "emails": {"argv": ["components/em/sync.py", "list"], "cache_s": 60,
                                                     "watch": WATCH}}
    root = tempfile.mkdtemp()
    for rel, text in (("platform/views/viewers/email_lead/emails-demo.html", "<p>page</p>"),
                      ("platform/views/viewers/_templates/emails-demo.sources.json", json.dumps(decl)),
                      ("components/em/sync.py", "print('[]')"),
                      ("runs/email-production/b/l/klaviyo/email.html", "<table></table>"),
                      ("runs/other/b/x.json", "{}")):
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)
    return root


def up(root, runner, status=None):
    src = serve.Sources(lambda: serve.sources("emails-demo", root), root=root, runner=runner)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), serve.handler("email_lead/emails-demo.html", src, root=root, status=status))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def get(url):
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def get_as(port, path, host):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        c.request("GET", path, headers={"Host": host})
        r = c.getresponse()
        return r.status, r.read().decode()
    finally:
        c.close()


class FakeGit(object):
    def __init__(self, revlist=(0, "3\n")):
        self.calls, self.revlist = [], revlist

    def __call__(self, argv):
        self.calls.append(argv)
        return (0, "") if "fetch" in argv else self.revlist

    def count(self, word):
        return sum(1 for a in self.calls if word in a)


def _allowed_host():
    for h in ("127.0.0.1:8765", "localhost:8765", "LOCALHOST:8765"):
        assert serve.allowed_host(h, 8765) is True, h
    for h in ("evil.example:8765", "127.0.0.1:9999", "", "127.0.0.1", None):
        assert serve.allowed_host(h, 8765) is False, h


def _foreign_host():
    root = tree()
    calls = []
    git = FakeGit()
    srv, base = up(root, lambda argv: calls.append(argv) or "[]", status=serve.Status(root, runner=git))
    port = srv.server_address[1]
    try:
        for path in ("/data/emails", "/runs/email-production/b/l/klaviyo/email.html", "/stamp/emails", "/status",
                     "/p/email_lead/emails-demo.html", "/"):
            code, body = get_as(port, path, "evil.example:%d" % port)
            assert code == 403, (path, code)
            assert body == "refused: this kit answers only http://127.0.0.1:%d/" % port, body
        assert calls == [] and git.calls == [], "a refused request runs nothing: %r %r" % (calls, git.calls)
        assert get_as(port, "/data/emails", "localhost:%d" % port)[0] == 200, "the kit's own name still answers"
    finally:
        srv.shutdown()
        shutil.rmtree(root)


def _runs_prefixes():
    root = tree()
    srv, base = up(root, lambda argv: "[]")
    try:
        assert get(base + "/runs/email-production/b/l/klaviyo/email.html") == (200, "<table></table>")
        assert get(base + "/runs/other/b/x.json")[0] == 404, "outside the declared prefixes"
        assert get(base + "/runs/email-production/../other/b/x.json")[0] == 404
        assert get(base + "/runs/email-production/%2e%2e/other/b/x.json")[0] == 404, "no encoded way sideways"
    finally:
        srv.shutdown()
        shutil.rmtree(root)
    root = tree({"emails": {"argv": ["components/em/sync.py", "list"]}})
    srv, base = up(root, lambda argv: "[]")
    try:
        for path in ("/runs/email-production/b/l/klaviyo/email.html", "/runs/other/b/x.json"):
            assert get(base + path)[0] == 404, "no runs key, no /runs/: " + path
    finally:
        srv.shutdown()
        shutil.rmtree(root)
    assert serve.runs_prefixes({"runs": ["../x/", "/abs/", "email-production", "learnings/", "a/../b/", 7]}) == \
        ["email-production/", "learnings/"]
    assert serve.runs_prefixes({}) == [] and serve.runs_prefixes({"runs": "email-production/"}) == []


def _stamp():
    root = tree()
    calls = []
    srv, base = up(root, lambda argv: calls.append(argv) or "[]")
    try:
        code, body = get(base + "/stamp/emails")
        assert code == 200, (code, body)
        first = json.loads(body)
        f = os.path.join(root, "runs/email-production/b/l/klaviyo/email.html")
        assert first == {"name": "emails", "stamp": [os.path.getmtime(f), 1]}, first
        os.utime(f, (os.path.getmtime(f) + 5, os.path.getmtime(f) + 5))
        second = json.loads(get(base + "/stamp/emails")[1])
        assert second["stamp"] != first["stamp"] and second["stamp"][0] == os.path.getmtime(f), second
        assert get(base + "/stamp/nope")[0] == 404
        assert calls == [], "/stamp runs nothing: %r" % calls
    finally:
        srv.shutdown()
        shutil.rmtree(root)
    src = serve.Sources({"emails": {"argv": ["components/em/sync.py"]}}, root=tempfile.gettempdir())
    for name in ("emails", "nope"):
        try:
            src.stamp(name)
            raise AssertionError("stamp of %s without watch did not raise" % name)
        except KeyError:
            pass


def _status():
    now = [1000.0]
    git = FakeGit()
    st = serve.Status("/repo", runner=git, clock=lambda: now[0], every=300)
    a = st.get()
    now[0] += 299
    b = st.get()
    assert git.count("fetch") == 1 and git.count("rev-list") == 2, git.calls
    assert a["behind"] == 3 and b["behind"] == 3 and "why" not in a, (a, b)
    assert a["checked"] == "1970-01-01T00:16:40Z", a
    assert git.calls[0] == ["git", "-C", "/repo", "fetch", "-q"], git.calls[0]
    assert git.calls[1] == ["git", "-C", "/repo", "rev-list", "--count", "HEAD..@{upstream}"], git.calls[1]
    now[0] += 1
    st.get()
    assert git.count("fetch") == 2, "a fetch again once `every` has passed: %r" % git.calls
    assert not any(w in argv for argv in git.calls for w in ("pull", "merge", "reset", "checkout")), git.calls
    bad = serve.Status("/repo", runner=FakeGit((128, "fatal: no upstream configured for branch 'x'")))
    r = bad.get()
    assert r["behind"] is None and "no upstream" in r["why"], r
    boom = serve.Status("/repo", runner=lambda argv: (_ for _ in ()).throw(OSError("no git")))
    r = boom.get()
    assert r["behind"] is None and "no git" in r["why"], r
    root = tree()
    srv, base = up(root, lambda argv: "[]", status=serve.Status(root, runner=FakeGit((0, "0\n"))))
    try:
        code, body = get(base + "/status")
        assert code == 200 and json.loads(body)["behind"] == 0, (code, body)
    finally:
        srv.shutdown()
        shutil.rmtree(root)


def _preflight():
    with mock.patch("importlib.util.find_spec", return_value=None):
        p = serve.preflight({"needs": ["PIL"]})
    assert len(p) == 1 and "Pillow" in p[0] and sys.executable in p[0] and "pip install --user Pillow" in p[0], p
    missing = os.path.join(tempfile.gettempdir(), "no-such-chrome-pf4b")
    with mock.patch.dict(os.environ, {"CHROME_BIN": missing}), mock.patch.object(serve, "CHROME_APP", missing):
        p = serve.preflight({"needs": ["chrome"]})
    assert p == ["Google Chrome is missing: install it, or set CHROME_BIN"], p
    with mock.patch.dict(os.environ, {"CHROME_BIN": sys.executable}):
        assert serve.preflight({"needs": ["chrome"]}) == [], "an executable CHROME_BIN passes"
    assert serve.preflight({"needs": ["nope"]}) == ["unknown need nope"]
    assert serve.preflight({}) == []
    root = tree({"needs": ["chrome"], "emails": {"argv": ["components/em/sync.py"]}})
    started = []
    out = io.StringIO()
    try:
        with mock.patch.object(serve, "ROOT", root), mock.patch.object(serve, "CHROME_APP", missing), \
                mock.patch.dict(os.environ, {"CHROME_BIN": missing}), \
                mock.patch.object(serve, "ThreadingHTTPServer", lambda *a, **k: started.append(a)), \
                contextlib.redirect_stdout(out):
            code = serve.main([os.path.join(root, "platform/views/viewers/email_lead/emails-demo.html")])
    finally:
        shutil.rmtree(root)
    assert code == 2 and started == [], (code, started)
    assert out.getvalue().strip() == "refused: Google Chrome is missing: install it, or set CHROME_BIN", out.getvalue()


def _shipped_family():
    decl = serve.sources("emails")
    assert serve.runs_prefixes(decl) == ["email-production/", "learnings/"], decl.get("runs")
    assert decl.get("needs") == ["PIL", "chrome"] and decl["emails"]["cache_s"] == 3600, decl


check("allowed_host: only 127.0.0.1:<port> and localhost:<port>", _allowed_host)
check("a foreign Host gets 403 on every route and runs nothing", _foreign_host)
check("/runs/ serves only the declared prefixes; none declared = no /runs/", _runs_prefixes)
check("/stamp answers the watch stamp without running the source, and moves when a watched file changes", _stamp)
check("/status: fetch at most once per `every`, rev-list each time, never a pull; a failure says why", _status)
check("preflight names the fix for a missing need; main() refuses with exit 2 and serves nothing", _preflight)
check("emails.sources.json declares its runs prefixes, its needs and cache_s 3600", _shipped_family)
print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
