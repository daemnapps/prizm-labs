#!/usr/bin/env python3
"""PF-7 (working versions): the `critical` contract; the going-live check on
fixture data and on the real detail files; the transform on a copy of the
real run-detail draft; go_live and first_open in temporary roots; the CLI.

    python3 test_pf7_working_versions.py

Stdlib only, no network, never runs git: every git call goes to a fake
runner that records argv. Reads the real draft, template, family list and
platform/data/mini-runs/ (copied into temporary roots, removed at the end);
writes nothing under the repo, and proves it with a sha256 of every file
under platform/views/viewers/ before and after. Runs under python3 and
/usr/bin/python3 (3.9). One PASS/FAIL line per check, then "N/M passed";
exit 1 on any FAIL.
"""
import copy, hashlib, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import features  # noqa: E402
import live  # noqa: E402

FIX = os.path.join(HERE, "test_pf7_fixtures")
FIX_ROOT = os.path.join(FIX, "data")
PREFS_PAGE = os.path.join(FIX, "prefs-page.html")
V1 = os.path.join(HERE, "examples", "mini-runs-run-detail.features.json")
V1_1 = os.path.join(HERE, "examples", "mini-runs-run-detail.v1-1.features.json")
VIEWERS = os.path.join(ROOT, "platform", "views", "viewers")
DRAFT = "platform/views/viewers/developer/drafts/run-detail--demo.html"
DRAFT_LOG = "platform/views/viewers/developer/drafts/run-detail--demo.changes.jsonl"
TEMPLATE = "platform/views/viewers/_templates/run-detail.html"
FAMILY = "platform/views/viewers/_templates/run-detail.features.json"
LIVE = "platform/views/viewers/developer/run-detail.html"
LIVE_LOG = "platform/views/viewers/developer/run-detail.changes.jsonl"
LIVE_RECORD = "platform/views/viewers/developer/run-detail.live.jsonl"
NOW = "2026-10-21T08:00:00Z"

RESULTS = []
TEMPS = []
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


def temp():
    path = tempfile.mkdtemp(prefix="pf7-")
    TEMPS.append(path)
    return path


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
    """Records every argv; answers 0 to all."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, cwd):
        self.calls.append(list(argv))
        return 0, "", ""


def assert_safe(calls):
    for argv in calls:
        words = " ".join(argv)
        for bad in ("reset", "stash", "--force", "-f ", "checkout", "rebase"):
            assert bad not in words, words


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


DOC = features.load(os.path.join(ROOT, FAMILY))


def with_critical(doc, *numbers):
    doc = copy.deepcopy(doc)
    for entry in doc["features"]:
        if entry["n"] in numbers:
            entry["critical"] = True
    return doc


def entry(doc, n):
    return next(e for e in doc["features"] if e["n"] == n)


def make_root(doc=None):
    """A temporary root holding a copy of the developer run-detail draft and its
    log, the family template, the family list (`doc`, default critical on 6
    only) and the whole platform/data/mini-runs/ folder."""
    root = temp()
    for rel in (DRAFT, DRAFT_LOG, TEMPLATE):
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), os.path.join(root, rel))
    write(os.path.join(root, FAMILY), features.dumps(doc or with_critical(DOC, 6)))
    shutil.copytree(os.path.join(ROOT, "platform", "data", "mini-runs"),
                    os.path.join(root, "platform", "data", "mini-runs"))
    return root


# ------------------------------------------------------------ the contract


def _critical_valid():
    assert features.validate(with_critical(DOC, 6)) == []
    assert "critical" in features.ENTRY_OPTIONAL_V1_2 and features.SCHEMA_MINOR == 2
    with open(os.path.join(HERE, "features.schema.json"), encoding="utf-8") as fh:
        schema = json.load(fh)
    assert schema["$defs"]["feature"]["properties"]["critical"]["const"] is True
    assert "critical" in schema["v1_2"]


def _critical_refused():
    found = features.validate(with_critical(DOC, 16))
    assert found == ["feature 16: `critical` is only for a wired feature, not 'not-built'"], found
    found = features.validate(with_critical(DOC, 3))
    assert found == ["feature 3: `critical` is not for a layout feature"], found
    doc = copy.deepcopy(DOC)
    entry(doc, 6)["critical"] = "yes"
    found = features.validate(doc)
    assert len(found) == 1 and found[0].startswith("feature 6: critical 'yes' is not true"), found
    entry(doc, 6)["critical"] = False
    assert features.validate(doc)[0].startswith("feature 6: critical False is not true")


def _old_versions():
    v1, v11 = features.load(V1), features.load(V1_1)
    assert features.validate(v1) == [] and features.validate(v11) == []
    v11 = copy.deepcopy(v11)
    v11["features"][0]["critical"] = True
    found = features.validate(v11)
    assert any("unknown key 'critical'" in f for f in found), found


# ------------------------------------------------------------ the data check

FIXTURE_DOC = {"features": [
    {"n": 1, "kind": "data", "state": "wired", "critical": True,
     "source": {"component": "c", "file": "platform/data/mini-runs/runs/<run>.json", "field": "alpha"}},
    {"n": 2, "kind": "data", "state": "wired", "critical": True,
     "source": {"component": "c", "file": "platform/data/mini-runs/runs/<run>.json", "field": "beta"}},
    {"n": 3, "kind": "data", "state": "wired", "critical": True,
     "source": {"component": "c", "file": "platform/data/mini-runs/runs/<run>.json", "field": "gamma"}},
    {"n": 4, "kind": "data", "state": "wired", "critical": True,
     "source": {"component": "c", "file": "platform/data/mini-runs/runs/<run>.json", "field": "delta"}},
    {"n": 5, "kind": "rule", "state": "wired",
     "source": {"component": "c", "file": "platform/data/mini-runs/runs/<run>.json", "field": "epsilon"}},
    {"n": 6, "kind": "rule", "state": "wired", "source": None},
    {"n": 7, "kind": "data", "state": "wired", "critical": True,
     "source": {"component": "c", "file": "platform/data/mini-runs/index.json", "field": "count"}},
    {"n": 8, "kind": "data", "state": "wired", "critical": True,
     "source": {"component": "c", "file": "platform/data/mini-runs/runs/<run>/notes.md", "field": "the whole file"}},
    {"n": 9, "kind": "data", "state": "wired", "critical": True,
     "source": {"component": "c", "file": "platform/data/mini-runs/nowhere.json", "field": "x"}},
    {"n": 10, "kind": "data", "state": "wired",
     "source": {"component": "c", "file": "platform/data/mini-runs/runs/<run>.json", "field": "zeta"}},
]}


def _fixture_data():
    failures, notes = live.data_check_live(FIXTURE_DOC, FIX_ROOT)
    assert failures == ["D2: beta missing on 1 of 2 refused runs",
                        "D3: gamma empty on every refused run (2)",
                        "R5: epsilon missing on 1 of 1 held runs",
                        "D9: platform/data/mini-runs/nowhere.json matches no file"], failures
    # D1 found everywhere, D4 empty on some done runs only, D7 found in index.json,
    # D10 is not critical and not a rule: none of them fails.
    assert "running: no run to sample (platform/data/mini-runs/runs/<run>.json)" in notes, notes
    assert "R6: page-only rule, not checked in data" in notes, notes
    assert any(n.startswith("D8: platform/data/mini-runs/runs/<run>/notes.md is not JSON")
               for n in notes), notes
    assert not any(n.startswith(("done:", "failed:", "held:", "refused:")) for n in notes), notes


def _classify():
    assert live.classify({"a": {"b": 1}}, "a.b") == "found"
    assert live.classify({"a": {"b": []}}, "a.b") == "empty"
    assert live.classify({"a": None}, "a.b") == "empty"
    assert live.classify({"a": {}}, "a.b") == "absent"
    assert live.classify({"a": []}, "a[].b") == "empty"
    assert live.classify({"a": [{"b": 2}]}, "a[].b") == "found"
    assert live.classify({}, "a") == "absent"


def _real_data():
    failures, notes = live.data_check_live(with_critical(DOC, 6), ROOT)
    assert not any(f.startswith("D6:") for f in failures), failures
    doc = with_critical(DOC, 6)
    e16 = entry(doc, 16)
    e16.update(state="wired", critical=True, anchor="16")
    failures, notes = live.data_check_live(doc, ROOT)
    runs = os.path.join(ROOT, "platform", "data", "mini-runs", "runs")
    refused = []
    for name in sorted(os.listdir(runs)):
        with open(os.path.join(runs, name), encoding="utf-8") as fh:
            run = json.load(fh)
        if (run.get("result") or {}).get("status") == "refused":
            refused.append(run)
    if refused and all(not r.get("steps") for r in refused):
        want = "D16: steps empty on every refused run (%d)" % len(refused)
        assert want in failures, failures
    else:
        print("      note: the real refused runs now carry steps (the data moved on); "
              "D16 not asserted")


# ------------------------------------------------------------ the transform


def _transform_real():
    root = make_root()
    html = read(os.path.join(root, DRAFT))
    assert html.count('data-feature="') == 71
    out = live.transform(html)
    for marker in (live.OVERLAY_START, live.OVERLAY_END, 'id="fo-features"',
                   'id="fo-prefs"', 'id="ov-', "data-personal-view"):
        assert marker not in out, marker
    assert live._live_form_problems(out, 69) == [], live._live_form_problems(out, 69)
    assert out.count('data-feature="') == 69, out.count('data-feature="')
    assert "const DATA" in out
    assert out.splitlines()[1] == html.splitlines()[1]  # the family comment
    assert "page-prefs" not in out  # run-detail's fo-prefs is empty
    assert live.transform(out) == out
    assert live.transform(live.transform(out)) == out


def _transform_errors():
    html = read(PREFS_PAGE)
    for bad in (html.replace(live.OVERLAY_END, ""), html.replace(live.OVERLAY_START, ""),
                html.replace(live.OVERLAY_END, live.OVERLAY_END + live.OVERLAY_END),
                html.replace(live.DEMO_END, "")):
        try:
            live.transform(bad)
        except ValueError:
            continue
        raise AssertionError("no ValueError")
    for bad in ("", "platform/views/viewers/developer/run-detail.html",
                "platform/views/viewers/_templates/run-detail.html"):
        try:
            live.live_path(bad)
        except ValueError:
            continue
        raise AssertionError("live_path accepted %r" % bad)
    assert live.live_path(DRAFT) == LIVE
    assert live.live_path("platform/views/viewers/owner/drafts/emails-demo--two.html") == \
        "platform/views/viewers/owner/emails-demo.html"


def _prefs_bake():
    html = read(PREFS_PAGE)
    out = live.transform(html)
    assert out.count('<style id="page-prefs">') == 1, out
    for want in ('[data-feature="1"]{display:none!important}', '[data-feature="3"]{order:-1}',
                 '[data-feature="3"]{font-size:1.22em}', ":root{--accent:#8a4fb8!important}"):
        assert want in out, (want, out)
    assert '[data-feature="2"]{display:none' not in out, out  # locked hidden
    assert out.index('<style id="page-prefs">') < out.index("</head>")
    for gone in ("Third", "pinned", "Demo:", "demo-banner", "data-personal-view", "ov-main"):
        assert gone not in out, (gone, out)  # labels, pinned: overlay-only
    assert live.feature_count(out) == 3, out
    assert live._live_form_problems(out, 3) == [], live._live_form_problems(out, 3)
    assert live.transform(out) == out, "not idempotent"
    assert live.transform(html, {"features": {}}).count("page-prefs") == 0


# ------------------------------------------------------------ check_live, go_live


def _check_live_real_copy():
    root = make_root()
    result = live.check_live(DRAFT, person="developer", root=root, runner=FakeGit())
    print("      check_live (temp copy, critical on 6 only): ok=%s" % result["ok"])
    for line in result["failures"]:
        print("        failure: %s" % line)
    for line in result["notes"]:
        print("        note: %s" % line)
    assert result["ok"] and result["failures"] == [], result["failures"]
    assert result["live"] == LIVE and result["family"] == "run-detail"
    assert live.NOTE_COVERAGE in result["notes"]
    assert live.NOTE_DATA in result["notes"]
    assert any("run-detail.assets picture reference" in n for n in result["notes"])
    # A draft with page settings bakes them and still passes the live-form count.
    path = os.path.join(root, DRAFT)
    write(path, read(path).replace('id="fo-prefs">{"features": {}',
                                   'id="fo-prefs">{"features": {"6": {"text_size": "large"}}', 1))
    result = live.check_live(DRAFT, person="developer", root=root, runner=FakeGit())
    assert result["ok"], result["failures"]
    assert '[data-feature="6"]{font-size:1.22em}' in live.transform(read(path))


def _go_live_first_and_second():
    root = make_root()
    git = FakeGit()
    result = live.go_live(DRAFT, person="developer", root=root, runner=git, now=NOW)
    assert result["result"] == "live", result
    assert result["lines"][0] == "live: %s · first live" % LIVE, result["lines"]
    assert result["lines"][1] == "0 change lines logged", result["lines"]
    assert result["written"] == [LIVE, LIVE_LOG, LIVE_RECORD], result["written"]
    assert result["shared"] == "shared"
    for rel in result["written"]:
        assert os.path.isfile(os.path.join(root, rel)), rel
    page = read(os.path.join(root, LIVE))
    assert page == live.transform(read(os.path.join(root, DRAFT)))
    assert page.count('data-feature="') == 69
    lines = features.read_changes(os.path.join(root, LIVE_RECORD))
    assert live.validate_live_log(lines) == [], live.validate_live_log(lines)
    record = json.loads(lines[0])
    # the base is whatever the draft is stamped with (it moves when the family base is
    # re-stamped, e.g. the 2026-10-21 sidebar-prefs patch), never a hard-coded sha
    stamp = re.search(r'data-template-sha="([0-9a-f]{40})"',
                      read(os.path.join(root, DRAFT))).group(1)
    assert record == {"kind": "live", "at": NOW, "by": "developer", "from": DRAFT,
                      "base": stamp, "old": None, "changes": 0,
                      "actions": live.actions_blob("run-detail", root)}, record   # PF-19 (behind notice)
    paths = result["written"]
    assert git.calls == [["git", "add", "--"] + paths,
                         ["git", "commit", "-m", "page: live run-detail (developer)", "--"] + paths,
                         ["git", "push"]], git.calls
    assert_safe(git.calls)
    # The draft is untouched.
    assert read(os.path.join(root, DRAFT)) == read(os.path.join(ROOT, DRAFT))

    git = FakeGit()
    result = live.go_live(DRAFT, person="developer", root=root, runner=git, now=NOW)
    archived = "platform/views/viewers/developer/drafts/run-detail--2026-10-21.html"
    assert result["lines"][0] == "live: %s · old live kept at %s" % (LIVE, archived), result
    assert read(os.path.join(root, archived)) == page
    assert result["written"] == [LIVE, LIVE_LOG, LIVE_RECORD, archived], result["written"]
    assert git.calls[0] == ["git", "add", "--"] + result["written"], git.calls
    result = live.go_live(DRAFT, person="developer", root=root, runner=FakeGit(), now=NOW)
    assert result["written"][-1] == archived[:-len(".html")] + "-2.html", result["written"]
    lines = features.read_changes(os.path.join(root, LIVE_RECORD))
    assert len(lines) == 3 and live.validate_live_log(lines) == []
    assert json.loads(lines[1])["old"] == archived


def _change_lines_once():
    root = make_root()
    line = {"n": 6, "said": "make the state bigger", "at": "2026-10-21T07:00:00Z",
            "by": "developer", "route": "claude-code"}
    write(os.path.join(root, DRAFT_LOG), features.dumps_changes([line]))
    result = live.go_live(DRAFT, person="developer", root=root, runner=FakeGit(), now=NOW)
    assert result["lines"][1] == "1 change line logged", result["lines"]
    result = live.go_live(DRAFT, person="developer", root=root, runner=FakeGit(), now=NOW)
    assert result["lines"][1] == "0 change lines logged", result["lines"]
    logged = features.read_changes(os.path.join(root, LIVE_LOG))
    assert [json.loads(x) for x in logged] == [line], logged
    record = [json.loads(x) for x in features.read_changes(os.path.join(root, LIVE_RECORD))]
    assert [r["changes"] for r in record] == [1, 0], record
    # A draft line the family list refuses is a failure before anything moves.
    write(os.path.join(root, DRAFT_LOG), features.dumps_changes([dict(line, n=999)]))
    before = tree_hashes(root)
    result = live.go_live(DRAFT, person="developer", root=root, runner=FakeGit(), now=NOW)
    assert result["result"] == "not live" and tree_hashes(root) == before, result
    assert any(f.startswith("page: ") and "999" in f for f in result["lines"][1:]), result


def _failing_writes_nothing():
    # An edited overlay block.
    root = make_root()
    path = os.path.join(root, DRAFT)
    html = read(path)
    write(path, html.replace(live.OVERLAY_START + "\n", live.OVERLAY_START + "\n<!-- mine -->\n"))
    before, git = tree_hashes(root), FakeGit()
    result = live.go_live(DRAFT, person="developer", root=root, runner=git, now=NOW)
    assert result["result"] == "not live" and result["written"] == [], result
    assert "page: the overlay block was edited; it is component-owned" in result["lines"], result
    assert result["lines"][0].startswith("not live: ")
    assert tree_hashes(root) == before and git.calls == []
    # A wired action on the page.
    root = make_root()
    doc = with_critical(DOC, 6)
    e37 = entry(doc, 37)
    e37.update(state="wired", anchor="37", where={"A": {"sel": '[data-feature="37"]', "text": None}})
    write(os.path.join(root, FAMILY), features.dumps(doc))
    path = os.path.join(root, DRAFT)
    write(path, read(path).replace('<header class="topbar">',
                                   '<button data-feature="37">Run it again</button>\n'
                                   '<header class="topbar">', 1))
    before = tree_hashes(root)
    result = live.go_live(DRAFT, person="developer", root=root, runner=FakeGit(), now=NOW)
    assert result["result"] == "not live", result
    assert "A37: actions wait for PF-4 (page starter kit)'s router; act(n) is not built" \
        in result["lines"], result["lines"]
    assert tree_hashes(root) == before
    for line in result["lines"][1:]:
        assert line.startswith("page:") or line[:1] in "DRMLA" and line[1:2].isdigit(), line
    # A critical number that fails on the data: tag first.
    root = make_root(with_critical(DOC, 6, 2))
    with open(os.path.join(root, "platform", "data", "mini-runs", "index.json"), "w") as fh:
        json.dump({"runs": []}, fh)
    before = tree_hashes(root)
    result = live.go_live(DRAFT, person="developer", root=root, runner=FakeGit(), now=NOW)
    assert result["result"] == "not live" and tree_hashes(root) == before
    assert "D2: as_of is absent in platform/data/mini-runs/index.json" in result["lines"], result


def _refusals():
    root = make_root()
    git = FakeGit()
    for page, person in ((DRAFT, "owner"), (TEMPLATE, "developer"), (LIVE, "developer"),
                         ("platform/views/viewers/developer/drafts/emails-demo--demo.html", "developer")):
        before = tree_hashes(root)
        result = live.go_live(page, person=person, root=root, runner=git, now=NOW)
        assert result["result"] == "refused" and result["written"] == [], (page, result)
        assert result["lines"][0].startswith("refused: "), result
        assert tree_hashes(root) == before
    assert git.calls == []
    result = live.check_live(DRAFT, person="owner", root=root, runner=git)
    assert result["refused"] and not result["ok"]


def _no_share():
    root = make_root()
    git = FakeGit()
    result = live.go_live(DRAFT, person="developer", root=root, runner=git, now=NOW, share=False)
    assert result["result"] == "live" and result["shared"] == "not shared", result
    assert git.calls == []


# ------------------------------------------------------------ first_open


def _prepared_root():
    root = make_root()
    page = live.transform(read(os.path.join(root, DRAFT)))
    page = page.replace("<head>\n", "<head>\n%s\n" % live.PREPARED_META, 1)
    write(os.path.join(root, LIVE), page)
    return root, page


def _first_open_pass():
    root, page = _prepared_root()
    git = FakeGit()
    result = live.first_open(LIVE, person="developer", root=root, runner=git, now=NOW)
    assert result["result"] == "live", result
    after = read(os.path.join(root, LIVE))
    assert live.PREPARED_META not in after and after == page.replace(live.PREPARED_META + "\n", "")
    lines = features.read_changes(os.path.join(root, LIVE_RECORD))
    assert live.validate_live_log(lines) == []
    record = json.loads(lines[0])
    assert record["kind"] == "first-open" and record["from"] == LIVE and record["old"] is None \
        and record["changes"] == 0 and record["at"] == NOW, record
    paths = [LIVE, LIVE_RECORD]
    assert git.calls == [["git", "add", "--"] + paths,
                         ["git", "commit", "-m", "page: first open run-detail (developer)", "--"] + paths,
                         ["git", "push"]], git.calls


def _first_open_already_and_failing():
    root, page = _prepared_root()
    plain = page.replace(live.PREPARED_META + "\n", "")
    write(os.path.join(root, LIVE), plain)
    before, git = tree_hashes(root), FakeGit()
    result = live.first_open(LIVE, person="developer", root=root, runner=git, now=NOW)
    assert result["result"] == "already live" and tree_hashes(root) == before and git.calls == []
    write(os.path.join(root, LIVE), page.replace("</body>", '<div id="fo-panel"></div>\n</body>'))
    before = tree_hashes(root)
    result = live.first_open(LIVE, person="developer", root=root, runner=git, now=NOW)
    assert result["result"] == "not live" and tree_hashes(root) == before, result
    assert any(l.startswith("page: ") and "fo-panel" in l for l in result["lines"]), result
    for page_rel, person in ((LIVE, "owner"), (DRAFT, "developer"), (TEMPLATE, "developer")):
        result = live.first_open(page_rel, person=person, root=root, runner=git, now=NOW)
        assert result["result"] == "refused", (page_rel, result)
    assert git.calls == []


def _live_log_validation():
    good = {"kind": "live", "at": NOW, "by": "developer", "from": DRAFT, "base": None,
            "old": None, "changes": 0}
    assert live.validate_live_log([good, json.dumps(good)]) == []
    bad = dict(good, kind="sideways", base="abc", changes=-1, by="", extra=1)
    found = live.validate_live_log([good, bad, "{"])
    assert all(f.startswith(("line 2:", "line 3:")) for f in found), found
    for word in ("kind 'sideways'", "base 'abc'", "changes -1", "`by`", "unknown key 'extra'",
                 "line 3: not JSON"):
        assert any(word in f for f in found), (word, found)


# ------------------------------------------------------------ the CLI


def run_cli(*args):
    proc = subprocess.run([sys.executable, os.path.join(HERE, "features.py")] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    return proc.returncode, proc.stdout.decode("utf-8")


def _cli():
    code, out = run_cli("check-live", os.path.join(ROOT, DRAFT), "--person", "developer")
    first = out.splitlines()[0]
    if code == 0:
        assert first == "ready to go live: %s → %s" % (DRAFT, LIVE), out
        assert "note: %s" % live.NOTE_COVERAGE in out
    else:
        assert code == 2 and first.startswith("not ready to go live: "), (code, out)
        print("      note: check-live on the real draft is not ready today:\n%s" % out)
    code, out = run_cli("check-live", os.path.join(ROOT, DRAFT), "--person", "owner")
    assert code == 2 and out.startswith("refused: "), (code, out)
    code, out = run_cli("live", os.path.join(ROOT, DRAFT), "--person", "owner", "--no-share")
    assert code == 2 and out.startswith("refused: "), (code, out)
    code, out = run_cli("first-open", os.path.join(ROOT, DRAFT), "--person", "developer", "--no-share")
    assert code == 2 and out.startswith("refused: "), (code, out)
    code, out = run_cli("check-live")
    assert code == 2, (code, out)
    code, out = run_cli("--bogus")
    assert "check-live <draft page>" in out and "first-open <live page>" in out, out


def _unreadable():
    root = make_root()
    with open(os.path.join(root, FAMILY), "w") as fh:
        fh.write("{not json")
    result = live.check_live(DRAFT, person="developer", root=root, runner=FakeGit())
    assert result["unreadable"] and result["unreadable"].startswith("UNREADABLE"), result


check("contract: critical true on a wired D validates; the schema carries it", _critical_valid)
check("contract: critical refused by name on not-built 16, layout 3, 'yes' and false",
      _critical_refused)
check("contract: v1 and v1.1 examples still validate; critical is unknown before v1.2",
      _old_versions)
check("data: per-file classifier — found, empty, absent", _classify)
check("data on fixtures: absent in one refused run fails with the count; empty on every "
      "refused run fails; empty on some passes; missing outcome, page-only rule and a "
      "non-JSON part are notes", _fixture_data)
check("data on the real runs: critical 6 passes; wired + critical 16 fails on refused "
      "runs while they carry no steps", _real_data)
check("transform on a copy of the real draft: no overlay, no fo-/ov- ids, no strip, 69 "
      "data-feature, const DATA kept, idempotent", _transform_real)
check("transform: one marker without its pair and a demo span without end raise; "
      "live_path", _transform_errors)
check("transform: the prefs bake gives one <style id=\"page-prefs\">, hidden unless locked",
      _prefs_bake)
check("check_live on a temp copy, critical on 6: ok, notes", _check_live_real_copy)
check("go_live: first live writes page + logs and shares exactly them; second keeps the "
      "old live under drafts/, a third takes -2", _go_live_first_and_second)
check("go_live: a draft change line is logged once; a refused line stops everything",
      _change_lines_once)
check("go_live: an edited overlay, a wired action, a failing critical number write "
      "nothing and list failures tag-first", _failing_writes_nothing)
check("go_live: refuses another person's draft, a template, a live page, a missing draft",
      _refusals)
check("go_live --no-share runs no git", _no_share)
check("first_open: a prepared page that passes loses the mark and logs first-open",
      _first_open_pass)
check("first_open: no mark is 'already live'; a failing page is unchanged; refusals",
      _first_open_already_and_failing)
check("validate_live_log names each defect by line", _live_log_validation)
check("check_live: an unreadable family list is reported, not raised", _unreadable)
check("CLI: check-live, live and first-open exit codes and lines", _cli)
def _real_tree_untouched():
    after = tree_hashes(VIEWERS)
    changed = sorted(k for k in set(after) | set(REAL_BEFORE) if after.get(k) != REAL_BEFORE.get(k))
    assert not changed, changed


check("the real tree is untouched: sha256 of every file under platform/views/viewers/",
      _real_tree_untouched)

for path in TEMPS:
    shutil.rmtree(path, ignore_errors=True)
print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
