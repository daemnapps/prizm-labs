#!/usr/bin/env python3
"""PF-4 (page starter kit), minimal form: serve.py's routes, its source door and its cache.

    python3 components/page-features/kit/test_serve.py
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import serve  # noqa: E402

RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append(True)
        print("PASS  " + name)
    except Exception as e:  # noqa: BLE001
        RESULTS.append(False)
        print("FAIL  %s — %r" % (name, e))


def tree():
    root = tempfile.mkdtemp()
    for rel, text in (("platform/views/viewers/email_lead/emails-demo.html", "<p>page</p>"),
                      ("platform/views/viewers/_templates/emails-demo.sources.json",
                       json.dumps({"_about": "x", "runs": ["email-production/"], "emails": {"argv": ["components/em/sync.py", "list"], "cache_s": 60},
                                   "bad": {"argv": ["lab/email_lead/x.py"]}})),
                      ("components/em/sync.py", "print('[]')"),
                      ("lab/email_lead/x.py", "print('[]')"),
                      ("runs/email-production/b/l/klaviyo/email.html", "<table></table>"),
                      ("runs/email-production/b/l/secret.env", "K=V"),
                      ("brands/b/x.html", "<p>brand</p>")):
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)
    return root


def up(root, runner):
    src = serve.Sources(serve.sources("emails-demo", root), root=root, runner=runner)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), serve.handler("email_lead/emails-demo.html", src, root=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def get(url):
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _routes():
    root = tree()
    calls = []
    srv, base = up(root, lambda argv: calls.append(argv) or '[{"id": "b__l"}]')
    try:
        assert get(base + "/p/email_lead/emails-demo.html") == (200, "<p>page</p>")
        assert get(base + "/runs/email-production/b/l/klaviyo/email.html")[0] == 200
        assert get(base + "/runs/email-production/b/l/secret.env")[0] == 404, "only page and picture types"
        assert get(base + "/runs/../brands/b/x.html")[0] == 404, "no way out of runs/"
        assert get(base + "/p/../../../brands/b/x.html")[0] == 404, "no way out of viewers/"
        assert get(base + "/runs/%2e%2e/brands/b/x.html")[0] == 404, "no encoded way out"
        assert json.loads(get(base + "/data/emails")[1]) == [{"id": "b__l"}]
        get(base + "/data/emails")
        assert calls == [["components/em/sync.py", "list"]], "a second call inside cache_s runs nothing: %r" % calls
        assert get(base + "/data/bad")[0] == 502, "argv outside components/ is refused"
        assert get(base + "/data/_about")[0] == 404 and get(base + "/data/nope")[0] == 404
    finally:
        srv.shutdown()
        shutil.rmtree(root)


def _cache_expires():
    root = tree()
    now = [1000.0]
    calls = []
    src = serve.Sources(serve.sources("emails-demo", root), root=root,
                        runner=lambda argv: calls.append(1) or "[]", clock=lambda: now[0])
    src.get("emails")
    now[0] += 61
    src.get("emails")
    assert len(calls) == 2, calls
    shutil.rmtree(root)


def _watch():
    root = tree()
    calls = []
    decl = {"emails": {"argv": ["components/em/sync.py"], "cache_s": 999,
                       "watch": ["runs/email-production/*/*/klaviyo/email.html"]}}
    src = serve.Sources(decl, root=root, runner=lambda argv: calls.append(1) or "[]")
    src.get("emails")
    src.get("emails")
    f = os.path.join(root, "runs/email-production/b/l/klaviyo/email.html")
    os.utime(f, (os.path.getmtime(f) + 5, os.path.getmtime(f) + 5))
    src.get("emails")
    assert len(calls) == 2, "a watched file changing runs the source again: %r" % calls
    shutil.rmtree(root)


def _json_only():
    root = tree()
    src = serve.Sources(serve.sources("emails-demo", root), root=root, runner=lambda argv: "not json")
    try:
        src.get("emails")
        raise AssertionError("non-JSON output was served")
    except ValueError:
        pass
    shutil.rmtree(root)


def _writes_nothing():
    root = tree()
    before = sorted(os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs)
    srv, base = up(root, lambda argv: "[]")
    try:
        for u in ("/", "/p/email_lead/emails-demo.html", "/data/emails", "/runs/email-production/b/l/klaviyo/email.html"):
            get(base + u)
    finally:
        srv.shutdown()
    after = sorted(os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs)
    shutil.rmtree(root)
    assert before == after


def _family():
    assert serve.family_of("/x/emails-demo.html") == "emails-demo"
    assert serve.family_of("/x/drafts/emails-demo--final.html") == "emails-demo"


check("routes: the page, runs/ files, a declared source; nothing outside, no other file types", _routes)
check("a source is run again once cache_s has passed", _cache_expires)
check("a watched file that changes runs the source again, inside cache_s", _watch)
check("a source that prints anything but JSON is not served", _json_only)
check("serving writes nothing", _writes_nothing)
check("the family comes from the page's file name, live or draft", _family)
print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
