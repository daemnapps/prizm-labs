#!/usr/bin/env python3
"""PF-4c (emails page loading): a source takes an argument through its declared params map, the emails family
asks for one email's steps by id, and the emails page says it is loading, marks a stale layout, loads steps when
an email opens and polls /stamp and /status instead of the whole list. No network, no real sync.py, no Chrome.

    python3 components/page-features/kit/test_pf4c_emails_loading.py

tree()/up()/get() are copied from test_serve.py (importing it would run its checks and exit).
"""
import json
import os
import re
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

REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TEMPLATES = os.path.join(REPO, "platform", "views", "viewers", "_templates")
ID_RX = "^[a-z0-9][a-z0-9-]*__[A-Za-z0-9][A-Za-z0-9._-]*$"
DECL = {"runs": ["email-production/"],
        "emails": {"argv": ["components/em/sync.py", "list", "--no-steps"], "cache_s": 60},
        "steps": {"argv": ["components/em/sync.py", "steps", "{id}"], "params": {"id": ID_RX}, "cache_s": 300}}
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
                      ("platform/views/viewers/_templates/emails-demo.sources.json", json.dumps(DECL)),
                      ("components/em/sync.py", "print('[]')")):
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


def _params():
    root = tree()
    calls = []
    src = serve.Sources(DECL, root=root, runner=lambda argv: calls.append(argv) or "[]")
    try:
        src.get("steps", {"id": "brand_b__brand_b-nov-02"})
        assert calls == [["components/em/sync.py", "steps", "brand_b__brand_b-nov-02"]], calls
        src.get("steps", {"id": "brand_b__brand_b-nov-02"})
        assert len(calls) == 1, "the same id inside cache_s is a cache hit: %r" % calls
        src.get("steps", {"id": "brand_b__brand_b-nov-03"})
        assert len(calls) == 2 and calls[1][-1] == "brand_b__brand_b-nov-03", "another id runs again: %r" % calls
        for bad in ({"id": "../x"}, {"id": "a b"}, {"id": "brand_b__x;rm"}, {}, None, {"id": "brand_b__a", "x": "1"}):
            try:
                src.get("steps", bad)
                raise AssertionError("ran with %r" % (bad,))
            except ValueError as e:
                assert str(e).startswith("bad parameter "), e
        try:
            src.get("emails", {"id": "brand_b__a"})
            raise AssertionError("params on a source that declares none")
        except ValueError as e:
            assert str(e) == "bad parameter id", e
        assert len(calls) == 2, "a refused request runs nothing: %r" % calls
        sub = serve.Sources({"s": {"argv": ["components/em/sync.py", "x{id}", "{id}y", "{id}"], "params": {"id": "^a$"}}},
                            root=root, runner=lambda argv: calls.append(argv) or "[]")
        sub.get("s", {"id": "a"})
        assert calls[-1] == ["components/em/sync.py", "x{id}", "{id}y", "a"], "only a WHOLE element is replaced: %r" % calls[-1]
    finally:
        shutil.rmtree(root)


def _served():
    root = tree()
    calls = []
    srv, base = up(root, lambda argv: calls.append(argv) or ('[{"order": 1}]' if argv[1] == "steps" else '[{"id": "b__l"}]'))
    try:
        assert get(base + "/data/steps?id=brand_b__brand_b-nov-02") == (200, '[{"order": 1}]')
        assert calls[-1] == ["components/em/sync.py", "steps", "brand_b__brand_b-nov-02"], calls
        n = len(calls)
        code, body = get(base + "/data/steps?id=..%2Fx")
        assert (code, body) == (400, "bad parameter id"), (code, body)
        assert get(base + "/data/steps?id=bad")[0] == 400
        assert get(base + "/data/steps?id=brand_b__a&id=brand_b__b")[0] == 400, "a key given twice"
        assert get(base + "/data/steps?other=1")[0] == 400
        assert get(base + "/data/steps")[0] == 400, "a missing declared key"
        assert get(base + "/data/emails?x=1")[0] == 400, "a query on a source with no params"
        assert len(calls) == n, "a 400 runs nothing: %r" % calls[n:]
        assert get(base + "/data/emails") == (200, '[{"id": "b__l"}]')
        assert calls[-1] == ["components/em/sync.py", "list", "--no-steps"], calls[-1]
        assert get(base + "/data/nope?id=x")[0] == 404
    finally:
        srv.shutdown()
        shutil.rmtree(root)


def _shipped_sources():
    with open(os.path.join(TEMPLATES, "emails.sources.json"), encoding="utf-8") as fh:
        decl = json.load(fh)
    em = decl["emails"]
    assert em["argv"][-2:] == ["list", "--no-steps"], em["argv"]
    assert em["argv"][0] == "components/email-production/adapter/sync.py", em["argv"]
    assert em["cache_s"] == 3600, em
    # PF-21 (pictures reach every Mac) added the whole-email picture: the background maker shoots it once its cut
    # pictures arrive from Drive, and the page offers the update when it lands
    assert em["watch"] == ["runs/email-production/*/*/design/email.json", "runs/email-production/*/*/klaviyo/card.json",
                           "runs/email-production/*/*/klaviyo/email.html", "runs/email-production/*/deadlines.json",
                           "runs/email-production/*/*/klaviyo/whole-email.jpg"], em
    st = decl["steps"]
    assert st["argv"][0] == em["argv"][0] and st["argv"][-2:] == ["steps", "{id}"], st["argv"]
    rx = st["params"]["id"]
    assert re.fullmatch(rx, "brand_b__brand_b-nov-02") and not re.fullmatch(rx, "../x"), rx
    assert set(st["params"]) == {"id"}, st["params"]


def _script():
    with open(os.path.join(TEMPLATES, "emails.html"), encoding="utf-8") as fh:
        page = fh.read()
    return page.split("<!-- page-features overlay: component-owned, do not edit -->")[0]


def fn(src, name):
    """One top-level function's text, from its `function name(` to the next top-level statement."""
    m = re.search(r"(?m)^(?:async )?function %s\(" % re.escape(name), src)
    assert m, "no function %s" % name
    end = re.compile(r"\n(?:async function |function |const |let |/\*|\(async )").search(src, m.end())
    return src[m.start():end.start() if end else len(src)]


def _page():
    s = _script()
    assert "Loading your emails…" in s
    dm = fn(s, "drawMain")
    i, j = dm.find("Loading your emails…"), dm.find("No emails here yet")
    assert 0 <= i < j, "drawMain says Loading before it can say No emails"
    guard = dm[:i].rsplit("\n", 1)[-1]
    assert "!LOADED" in guard, "the Loading branch is gated on the loaded flag: %r" % guard
    assert re.search(r"(?m)^let LOADED=false;", s), "LOADED starts false"
    b0 = s.find("async function boot(")
    assert b0 >= 0, "no boot"
    boot = s[b0:s.find("})();", b0)]
    assert boot.count("LOADED=true") >= 3, "boot sets LOADED on the answer, the error line and the file path"
    ls = fn(s, "loadServed")
    assert "_steps" not in ls, "loadServed no longer reads _steps"
    st = fn(s, "loadSteps")
    assert "/data/steps?id=" in st and "encodeURIComponent(id)" in st and "STEPS_ASKED" in st, st
    assert "if(!db)return;" in st, "the non-served db path stays"
    assert "loadSteps(e.id)" in dm, "the made view asks for the open email's steps"
    ps = fn(s, "pageStamp")
    assert "/stamp/emails" in ps and "/data/emails" not in ps, ps
    assert "card.json" not in ps and "deadlines.json" not in ps, "the watch covers cards and deadlines"
    wc = fn(s, "watchChanges")
    assert '"/status"' in wc and "new on the shared copy — ask your Claude to pull" in wc, wc
    assert "layout_stale" in s
    assert 'e.layout_stale===true?"":S.map(' in dm, "the section outlines are hidden for a stale layout"
    assert "updating…" in s and dm.count("staleTag(e)") == 1 and "staleTag(e)" in fn(s, "drawStrip"), \
        "the badge shows on the strip card and the main header"


check("a source's params: whole-element substitution, cached per value, refused before running", _params)
check("served /data/<name>?<key>=: 200, 400 for a bad, doubled, unknown or missing key, 404 unknown", _served)
check("emails.sources.json: list --no-steps, watch and cache_s unchanged; a steps source by id", _shipped_sources)
check("emails.html: Loading first, steps per email, /stamp and /status, stale layouts marked", _page)
print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
