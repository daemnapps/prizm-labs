#!/usr/bin/env python3
"""PF-3c (family compare): compare / render / main on a fixture family with
three versions in temporary roots — the card's case (one changed L9, one
added D67, one untouched), a hidden number, a number the list does not have,
retired numbers left out, --json, the exit codes, the CLI through
features.main, and a read-only pass over every real family.

    python3 test_pf3c_family_compare.py

Stdlib only, no network, never runs git: a fake runner records argv and
answers pages.list_pages' read-only verbs. Every fixture is written from this
file into a temporary root (removed at the end). Proves it writes nothing: the
temp root's listing (paths + sha256) around every call, and every file under
the real platform/views/viewers/ around the whole run. One PASS/FAIL line per
check, then "N/M passed"; exit 1 on any FAIL.
"""
import contextlib, hashlib, io, json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import compare  # noqa: E402
import features  # noqa: E402

VIEWERS = os.path.join(ROOT, "platform", "views", "viewers")
T = "platform/views/viewers/_templates/"
V = "platform/views/viewers/"
ANN, BOB, CY = V + "ann/fam.html", V + "bob/drafts/fam--try.html", V + "cy/fam.html"
IDS = ["ann/live", "bob/try", "cy/live"]
FORBIDDEN = ("add", "commit", "push", "fetch", "reset", "stash", "checkout", "rm")

RESULTS = []
TEMPS = []
ALL_CALLS = []
if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout.reconfigure(encoding="utf-8")


def check(label, fn):
    try:
        fn()
        RESULTS.append(True)
        print("PASS  %s" % label)
    except AssertionError as exc:
        RESULTS.append(False)
        print("FAIL  %s — %s" % (label, exc))
    except Exception as exc:  # a crash is a failure, never a pass
        RESULTS.append(False)
        print("FAIL  %s — raised %s: %s" % (label, type(exc).__name__, exc))


def tree_hashes(top):
    out = {}
    for base, _, names in os.walk(top):
        for name in names:
            path = os.path.join(base, name)
            with open(path, "rb") as handle:
                out[os.path.relpath(path, top)] = hashlib.sha256(handle.read()).hexdigest()
    return out


REAL_BEFORE = tree_hashes(VIEWERS)


class FakeGit(object):
    """Records argv; status and log empty; hash-object the blob id; anything else fails."""

    def __call__(self, argv, cwd):
        ALL_CALLS.append(list(argv))
        verb = argv[1]
        if verb in ("status", "log"):
            return 0, "", ""
        if verb == "hash-object":
            path = os.path.join(cwd, argv[-1])
            if not os.path.isfile(path):
                return 128, "", "fatal: could not open '%s'" % argv[-1]
            with open(path, "rb") as handle:
                data = handle.read()
            return 0, hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() + "\n", ""
        if verb == "config":
            return 0, "fixp@x.test\n", ""
        return 1, "", "unexpected git call"


# ------------------------------------------------------------ the fixture

KINDS = {"data": {"letter": "D", "name": "Data", "means": "a saved value"},
         "rule": {"letter": "R", "name": "Rule", "means": "worked out by the page"},
         "media": {"letter": "M", "name": "Media", "means": "a file on Drive"},
         "layout": {"letter": "L", "name": "Layout", "means": "arrangement"},
         "action": {"letter": "A", "name": "Action", "means": "a button"}}


def layout(n, name):
    return {"n": n, "name": name, "kind": "layout", "state": "wired", "status": "draft",
            "source": None, "anchor": str(n)}


FAMILY_LIST = {
    "schema": 1, "schema_minor": 2, "title": "Fixture family", "status": "draft", "owner": "ann",
    "kinds": KINDS,
    "state_words": {"wired": "exists", "after-card": "waits on a card", "not-built": "no data yet"},
    "page": T + "fam.html",
    "features": [layout(n, "Part %d" % n) for n in range(1, 9)] + [layout(9, "The stage columns")] + [
        {"n": 67, "name": "My own priority", "kind": "data", "state": "not-built", "status": "draft",
         "source": None, "added_by": "bob", "added": "2026-10-21",
         "needs": {"data": "a per-person priority", "where": "runs/queue/priority-bob.json"}}],
    "retired": [{"n": 10, "name": "Old panel", "retired": "2026-10-21", "why": "overlay UI"}],
}
OTHER_LIST = dict(FAMILY_LIST, title="Other family", owner="cy", page=T + "other.html",
                  features=[layout(1, "Title")], retired=[])


def page(numbers, extra=""):
    spans = "\n".join('<div data-feature="%d">part %d</div>' % (n, n) for n in numbers)
    return ('<!doctype html><html><head><style id="page-prefs">[data-feature="5"]{}</style>'
            '</head><body>\n%s\n%s</body></html>\n' % (spans, extra))


def change(n, by, **over):
    line = {"n": n, "said": "make it a grid", "at": "2026-10-29T10:00:00Z", "by": by,
            "route": "claude-code"}
    line.update(over)
    return json.dumps(line, ensure_ascii=False) + "\n"


ALL = list(range(1, 10))
FILES = {
    T + "fam.features.json": json.dumps(FAMILY_LIST, indent=1),
    T + "fam.html": page(ALL),
    T + "other.features.json": json.dumps(OTHER_LIST, indent=1),
    T + "other.html": page([1]),
    ANN: page(ALL),
    V + "ann/fam.changes.jsonl": change(9, "ann"),
    BOB: page(ALL),
    V + "bob/drafts/fam--try.changes.jsonl": change(
        67, "bob", said="add priorities for me", kind="missing",
        needs={"data": "a per-person priority", "where": "runs/queue/priority-bob.json"}),
    CY: page(ALL),
    V + "cy/other.html": page([1]),
}


def make_root(**over):
    """A temp root holding FILES (with `over` replacing or, as None, removing paths)."""
    root = tempfile.mkdtemp(prefix="pf3c-")
    TEMPS.append(root)
    files = dict(FILES)
    files.update(over)
    for rel, text in files.items():
        if text is None:
            continue
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(text if isinstance(text, bytes) else text.encode("utf-8"))
    return root


def compared(root, family="fam"):
    """compare.compare, asserting the temp root is byte-identical around the call."""
    before = tree_hashes(root)
    result = compare.compare(family, root=root, runner=FakeGit())
    assert tree_hashes(root) == before, "compare changed files under the temp root"
    return result


def row(result, tag):
    return next(r for r in result["rows"] if r["tag"] == tag)


def differing(result):
    return [r["tag"] for r in result["rows"]
            if any(c not in (compare.KEPT, compare.NOT_JUDGED) for c in r["cells"].values())]


def run_main(argv, root):
    out = io.StringIO()
    before = tree_hashes(root)
    with contextlib.redirect_stdout(out):
        code = compare.main(argv, root=root, runner=FakeGit())
    assert tree_hashes(root) == before, "main changed files under the temp root"
    return code, out.getvalue()


# ------------------------------------------------------------ the card's case


def _fixture_valid():
    assert features.validate(FAMILY_LIST) == [], features.validate(FAMILY_LIST)
    lines = [FILES[V + "ann/fam.changes.jsonl"], FILES[V + "bob/drafts/fam--try.changes.jsonl"]]
    assert features.validate_changes([l.strip() for l in lines], FAMILY_LIST) == []


check("fixture: the family list and both change logs are valid v1.2", _fixture_valid)


def _card_rows():
    result = compared(make_root())
    assert result["refused"] is None, result
    assert [v["id"] for v in result["versions"]] == IDS, result["versions"]
    assert [v["path"] for v in result["versions"]] == [ANN, BOB, CY], result["versions"]
    assert [(v["kind"], v["person"]) for v in result["versions"]] == [
        ("live", "ann"), ("draft", "bob"), ("live", "cy")], result["versions"]
    assert differing(result) == ["L9", "D67"], differing(result)
    assert row(result, "L9")["cells"] == {"ann/live": "changed", "bob/try": "kept",
                                          "cy/live": "kept"}, row(result, "L9")
    d67 = row(result, "D67")
    assert d67["added_by"] == "bob" and d67["listed"], d67
    assert d67["cells"] == {"ann/live": "—", "bob/try": "added", "cy/live": "—"}, d67
    for r in result["rows"]:
        if r["tag"] not in ("L9", "D67"):
            assert set(r["cells"].values()) == {"kept"}, r
            assert r["added_by"] is None, r
    counts = [(v["id"], v["changed"], v["hidden"], v["added"]) for v in result["versions"]]
    assert counts == [("ann/live", 1, 0, 0), ("bob/try", 0, 0, 1), ("cy/live", 0, 0, 0)], counts


check("card case: one changed L9, one added D67, one untouched — exactly those rows", _card_rows)


def _retired_and_order():
    result = compared(make_root())
    assert [r["n"] for r in result["rows"]] == ALL + [67], [r["n"] for r in result["rows"]]
    assert 10 not in [r["n"] for r in result["rows"]], "retired 10 is a row"
    root = make_root(**{V + "cy/fam.changes.jsonl": change(10, "cy")})
    assert 10 not in [r["n"] for r in compared(root)["rows"]], "a retired n in a log became a row"


check("retired numbers are never rows, even when a log names one; rows in number order",
      _retired_and_order)


def _hidden():
    root = make_root(**{CY: page([1, 2, 4, 5, 6, 7, 8, 9])})
    result = compared(root)
    assert differing(result) == ["L3", "L9", "D67"], differing(result)
    assert row(result, "L3")["cells"] == {"ann/live": "kept", "bob/try": "kept",
                                          "cy/live": "hidden"}, row(result, "L3")
    cy = result["versions"][2]
    assert (cy["changed"], cy["hidden"], cy["added"]) == (0, 1, 0), cy


check("hidden: a number on the team page and not on a version's page is hidden there only", _hidden)


def _prefs_style_not_an_anchor():
    root = make_root(**{CY: page([1, 2, 3, 4, 6, 7, 8, 9])})
    assert row(compared(root), "L5")["cells"]["cy/live"] == "hidden", \
        "the page-prefs style's [data-feature=\"5\"] counted as an anchor"


check("the baked page-prefs style is not an anchor (as pages.py counts)", _prefs_style_not_an_anchor)


def _script_anchor_counts():
    script = '<script>el.innerHTML = \'<b data-feature="3">x</b>\';</script>'
    root = make_root(**{CY: page([1, 2, 4, 5, 6, 7, 8, 9], extra=script)})
    assert row(compared(root), "L3")["cells"]["cy/live"] == "kept"


check("an anchor written by the page's own script counts as on the page", _script_anchor_counts)


def _unlisted_number():
    root = make_root(**{BOB: page(ALL + [70])})
    result = compared(root)
    r70 = row(result, "?70")
    assert not r70["listed"] and r70["name"] is None and r70["added_by"] is None, r70
    assert r70["cells"] == {"ann/live": "—", "bob/try": "added", "cy/live": "—"}, r70
    assert result["versions"][1]["added"] == 2, result["versions"][1]
    assert "70 is not on fam.features.json: a version carries it" in result["notes"], result["notes"]


check("a number a version carries that the list does not have: a row, added there", _unlisted_number)


def _added_by_other_person_is_changed():
    root = make_root(**{V + "cy/fam.changes.jsonl": change(67, "cy")})
    assert row(compared(root), "D67")["cells"]["cy/live"] == "changed"


check("a number added by someone else that a version's log names is changed, not added",
      _added_by_other_person_is_changed)


# ------------------------------------------------------------ output


def _render():
    root = make_root()
    code, out = run_main(["fam"], root)
    lines = out.splitlines()
    assert code == 0, out
    assert lines[0] == ("fam — 3 versions, 10 numbers; the team page is "
                        "platform/views/viewers/_templates/fam.html"), lines[0]
    head = lines[1].split()
    assert head == ["number", "name", "added", "by"] + IDS, head
    l9 = next(l for l in lines if l.startswith("L9 "))
    assert l9.split() == ["L9", "The", "stage", "columns", "changed", "kept", "kept"], l9
    d67 = next(l for l in lines if l.startswith("D67 "))
    assert d67.split() == ["D67", "My", "own", "priority", "bob", "—", "added", "—"], d67
    for want in ("ann/live: 1 changed, 0 hidden, 0 added · " + ANN,
                 "bob/try: 0 changed, 0 hidden, 1 added · " + BOB,
                 "cy/live: 0 changed, 0 hidden, 0 added · " + CY):
        assert want in lines, (want, lines)
    assert "key: %s" % compare.LEGEND in lines, lines


check("plain table: rows by number, columns <person>/live and <person>/<draft>, a summary per version",
      _render)


def _json_same_data():
    root = make_root()
    code, out = run_main(["fam", "--json"], root)
    assert code == 0, out
    assert json.loads(out) == compared(root), "--json is not compare()'s result"


check("--json prints compare()'s result as data", _json_same_data)


def _cli_through_features():
    root = make_root()
    saved = features.ROOT, features.run_git
    features.ROOT, features.run_git = root, FakeGit()
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = features.main(["compare", "fam"])
    finally:
        features.ROOT, features.run_git = saved
    assert code == 0, out.getvalue()
    assert "ann/live: 1 changed, 0 hidden, 0 added · " + ANN in out.getvalue(), out.getvalue()
    assert "features.py compare <family> [--json]" in features.USAGE


check("CLI: features.py compare <family> reaches compare.main", _cli_through_features)


def _no_versions():
    result = compared(make_root(), family="other")
    assert [v["id"] for v in result["versions"]] == ["cy/live"], result["versions"]
    root = make_root(**{V + "cy/other.html": None})
    code, out = run_main(["other"], root)
    assert code == 0, out
    assert "no one has a live page or a draft of other yet" in out, out


check("a family no one has a version of prints that, exit 0", _no_versions)


# ------------------------------------------------------------ exit codes


def _unknown_family():
    code, out = run_main(["nope"], make_root())
    assert code == 2, (code, out)
    assert out.strip() == "refused: 'nope' is not a page family (families: fam, other)", out


check("exit 2: an unknown family is named, with the families that exist", _unknown_family)


def _bad_argument():
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        code, _ = run_main([], make_root())
    assert code == 2, code


check("exit 2: no family given", _bad_argument)


def _unreadable():
    code, out = run_main(["fam"], make_root(**{T + "fam.features.json": "{not json"}))
    assert code == 3 and "UNREADABLE" in out and "fam.features.json" in out, (code, out)
    code, out = run_main(["fam"], make_root(**{BOB: b"\xff\xfe not utf-8"}))
    assert code == 3 and "UNREADABLE: %s" % BOB in out, (code, out)
    code, out = run_main(["fam"], make_root(**{T + "fam.html": None}))
    assert code == 3 and "UNREADABLE: %sfam.html" % T in out, (code, out)


check("exit 3: an unreadable family list, version page or team page", _unreadable)


# ------------------------------------------------------------ the real tree


def _real_tree():
    families = sorted(features.family_of(p) for p in os.listdir(os.path.join(ROOT, T))
                      if p.endswith(".features.json"))
    assert families, "no real families"
    for family in families:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = compare.main([family, "--json"], root=ROOT, runner=FakeGit())
        assert code == 0, (family, out.getvalue()[:300])
        result = json.loads(out.getvalue())
        for r in result["rows"]:
            assert set(r["cells"]) == set(v["id"] for v in result["versions"]), (family, r)
            assert set(r["cells"].values()) <= set(compare.CELLS), (family, r)


check("real tree: every real family compares, exit 0, read-only", _real_tree)


def _no_forbidden():
    assert ALL_CALLS, "no git calls were recorded at all"
    for argv in ALL_CALLS:
        assert argv[1] in ("status", "log", "hash-object", "config"), argv
        for word in FORBIDDEN:
            assert word not in argv[1:2], argv


check("git: only status, log, hash-object and config — never a writing verb", _no_forbidden)


for path in TEMPS:
    shutil.rmtree(path, ignore_errors=True)


def _real_untouched():
    assert tree_hashes(VIEWERS) == REAL_BEFORE, "files under platform/views/viewers/ changed"


check("nothing written: every file under the real platform/views/viewers/ unchanged",
      _real_untouched)

print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
