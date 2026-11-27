#!/usr/bin/env python3
"""PF-1c (plain-words changes): the v1.2 contract accepts the reference case
(developer's two requests on outlier-demo), refuses each defect by name, leaves v1
and v1.1 files valid; the converter maps the prototype format and is
idempotent; the three family lists carry no format finding; sync, change and
autosave do what the card says, with git only ever through a fake runner.

    python3 test_pf1c_plain_words.py

Stdlib only, no network, never runs git. Reads the examples, the fixtures in
test_pf1c_fixtures/ and the three family lists; writes only inside its own
temporary folders, removed at the end. Runs under python3 and /usr/bin/python3
(3.9). One PASS/FAIL line per check, then "N/M passed"; exit 1 on any FAIL.
"""
import copy, datetime, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import features  # noqa: E402

V1 = os.path.join(HERE, "examples", "mini-runs-run-detail.features.json")
V1_1 = os.path.join(HERE, "examples", "mini-runs-run-detail.v1-1.features.json")
SCHEMA = os.path.join(HERE, "features.schema.json")
REPORT = os.path.join(HERE, "examples", "family-conversion-findings.md")
FIX = os.path.join(HERE, "test_pf1c_fixtures")
PROTOTYPE = os.path.join(FIX, "prototype.features.json")
PAGE = os.path.join(FIX, "page.html")
TEMPLATES = os.path.join(ROOT, "platform", "views", "viewers", "_templates")
FAMILIES = ["emails", "outlier-demo", "run-detail"]
LOG = os.path.join(ROOT, "platform", "views", "viewers", "developer", "archive", "drafts",  # archived 2026-10-29
                   "outlier-demo--demo.changes.jsonl")
# The content findings the converter cannot clear, by family and number
# (7 /api routes in source.file, one 63-character name, a wired feature with
# no page tag). The family lists keep them as they are. emails-demo (now emails) 34 fixed by its
# owner, 2026-10-21 (after-card, PF-4 (page starter kit)).
CONTENT = {"emails": [], "outlier-demo": [3, 4, 23, 34, 54, 57, 61, 63],
           "run-detail": []}

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
    path = tempfile.mkdtemp(prefix="pf1c-")
    TEMPS.append(path)
    return path


def run_cli(*args):
    proc = subprocess.run([sys.executable, os.path.join(HERE, "features.py")] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    return proc.returncode, proc.stdout.decode("utf-8")


DOC_V1 = features.load(V1)
DOC_V11 = features.load(V1_1)


def v12():
    """The v1.1 example opted in to v1.2, with one retired number."""
    doc = copy.deepcopy(DOC_V11)
    doc["schema_minor"] = 2
    doc["retired"] = [{"n": 99, "name": "The change box", "retired": "2026-10-21",
                       "why": "changes go through the person's own Claude", "by": "developer"}]
    return doc


def feature(doc, n):
    return [e for e in doc["features"] if e["n"] == n][0]


def family(name):
    return features.load(os.path.join(TEMPLATES, "%s.features.json" % name))


def reference_lines():
    return features.read_changes(LOG)


D67_NEEDS = {"data": "a priority that belongs to one person",
             "where": "runs/queue/priority-developer.json",
             "written_by": "the queue store", "component": "Outlier queue store"}


def change_line(**over):
    out = {"n": 3, "said": "make the back link bigger", "at": "2026-10-21T04:23:41Z",
           "by": "developer", "route": "claude-code"}
    out.update(over)
    return out


def one_finding(got, must_contain):
    assert len(got) == 1, "want exactly one finding, got %d: %r" % (len(got), got)
    assert must_contain in got[0], "finding %r does not say %r" % (got[0], must_contain)


# ------------------------------------------------------ v1.2 accepts the reference


def _accepts_d67():
    doc = v12()
    e = feature(doc, 12)
    assert e["state"] == "not-built"
    e.update({"added_by": "developer", "added": "2026-10-21", "needs": dict(D67_NEEDS),
              "frame": "cast", "owns": ["default_view"], "locked": ["hidden"]})
    assert features.validate(doc) == [], features.validate(doc)
    out = family("outlier-demo")
    d67 = feature(out, 67)
    assert (d67["state"], d67["added_by"], sorted(d67["needs"])) == (
        "not-built", "developer", ["component", "data", "where", "written_by"]), d67


def _accepts_reference_changes():
    lines = reference_lines()
    assert len(lines) == 3, lines
    objs = [json.loads(l) for l in lines]
    assert objs[1]["resolved"] == "claude" and objs[1]["match"], objs[1]
    assert objs[2]["kind"] == "missing" and objs[2]["needs"]["data"], objs[2]
    assert features.validate_changes(lines, family("outlier-demo")) == []
    doc = v12()
    doc["changes"] = [change_line(resolved="claude", match="L3 is the back link itself."),
                      change_line(n=12, kind="missing", needs=dict(D67_NEEDS))]
    assert features.validate(doc) == [], features.validate(doc)


# ------------------------------------------------------ one named finding each


def _not_built_added_by_without_needs():
    doc = v12()
    feature(doc, 12)["added_by"] = "developer"
    one_finding(features.validate(doc), "feature 12: a not-built feature added by a person needs `needs`")


def _needs_on_wired():
    doc = v12()
    feature(doc, 3)["needs"] = dict(D67_NEEDS)
    one_finding(features.validate(doc), "feature 3: `needs` is only for a not-built feature, not 'wired'")


def _needs_shape():
    doc = v12()
    feature(doc, 12)["needs"] = {"data": "x", "who": "y"}
    got = features.validate(doc)
    assert "feature 12: needs: unknown key 'who'" in got, got
    assert "feature 12: needs.where is missing" in got, got
    assert len(got) == 2, got


def _resolved_without_match():
    doc = v12()
    doc["changes"] = [change_line(resolved="claude")]
    one_finding(features.validate(doc), "changes 1: `match` is missing")
    one_finding(features.validate_changes([change_line(resolved="claude")], doc),
                "line 1: `match` is missing")


def _kind_missing_without_needs():
    doc = v12()
    doc["changes"] = [change_line(n=12, kind="missing")]
    one_finding(features.validate(doc), "changes 1: `needs` is missing")
    one_finding(features.validate_changes([change_line(n=12, kind="missing")], doc),
                "line 1: `needs` is missing")


def _retired_in_features():
    doc = v12()
    doc["retired"].append({"n": 3, "name": "Back link", "retired": "2026-10-21", "why": "x"})
    one_finding(features.validate(doc), "feature 3: n 3 is retired and must not be a feature")


def _change_on_retired():
    doc = v12()
    one_finding(features.validate_changes([change_line(n=99)], doc), "line 1: n 99 is retired")
    doc["changes"] = [change_line(n=99)]
    one_finding(features.validate(doc), "changes 1: n 99 is retired")


def _bad_values():
    doc = v12()
    doc["changes"] = [change_line(resolved="me", match="x"), change_line(kind="extra")]
    got = features.validate(doc)
    assert got == ["changes 1: resolved 'me' is not 'claude'",
                   "changes 2: kind 'extra' is not 'missing'"], got
    assert features.CHANGE_ROUTES == ["claude-code", "note"]
    one_finding(features.validate_changes([change_line(route="B")], doc),
                "line 1: route 'B' is not one of claude-code | note")


def _v12_keys_need_minor_2():
    doc = copy.deepcopy(DOC_V11)
    feature(doc, 12)["added_by"] = "developer"
    one_finding(features.validate(doc), "feature 12: unknown key 'added_by'")
    doc = copy.deepcopy(DOC_V11)
    doc["changes"] = [change_line(resolved="claude", match="x")]
    got = features.validate(doc)
    assert got == ["changes 1: unknown key 'resolved'", "changes 1: unknown key 'match'"], got


# ------------------------------------------------------ v1 and v1.1 still validate


def _old_examples_valid():
    assert features.validate(DOC_V1) == []
    assert features.validate(DOC_V11) == []
    assert "schema_minor" not in DOC_V1 and DOC_V11["schema_minor"] == 1
    assert features.SCHEMA_MINOR == 2


# ------------------------------------------------------ finding kinds


def _finding_kinds():
    doc = v12()
    feature(doc, 3)["name"] = "x" * 61
    feature(doc, 4)["colour"] = "red"
    got = features.validate_kinds(doc)
    kinds = {k["text"]: k["kind"] for k in got}
    assert kinds == {"feature 3: name is 61 characters, over 60": "content",
                     "feature 4: unknown key 'colour'": "format"}, got
    assert features.finding_kind("feature 3: source.file is not repo-relative: "
                                 "'/api/card' starts with /") == "content"
    assert features.finding_kind("feature 34: a wired feature needs an anchor in v1.1") == "content"
    assert features.finding_kind("file: `state_words` is missing") == "format"


# ------------------------------------------------------ the converter


def _convert_mapping():
    proto = features.load(PROTOTYPE)
    before = copy.deepcopy(proto)
    doc = features.convert(proto, family="prototype")
    assert proto == before, "convert mutated its input"
    assert list(doc)[:5] == ["retired", "title", "schema", "schema_minor", "status"], list(doc)
    assert (doc["schema"], doc["schema_minor"], doc["status"]) == (1, 2, "draft")
    for key in ("demo", "overlay", "exempt", "status_words"):
        assert key not in doc, key
    assert doc["state_words"] == {"wired": "the data exists today",
                                  "after-card": "needs a card first",
                                  "not-built": "no data anywhere yet"}, doc["state_words"]
    assert doc["versions"] == {"A": "platform/views/viewers/_templates/prototype.html"}
    assert doc["retired"] == [
        {"n": 6, "name": "The numbers panel", "retired": "2026-10-21",
         "why": "overlay UI, not a page feature"},
        {"n": 7, "name": "The numbers button", "retired": "2026-10-21",
         "why": "overlay UI, not a page feature", "by": "developer"}], doc["retired"]
    f = {e["n"]: e for e in doc["features"]}
    assert [(f[n]["state"], f[n]["status"]) for n in range(1, 6)] == [
        ("wired", "draft"), ("wired", "draft"), ("after-card", "draft"),
        ("not-built", "draft"), ("not-built", "draft")]
    assert list(f[1])[:5] == ["n", "name", "kind", "state", "status"], list(f[1])
    assert [f[n].get("anchor") for n in range(1, 6)] == ["1", "2", "3", None, None]
    assert all("demo" not in e for e in doc["features"])
    assert "frame" not in f[1] and "owns" not in f[1] and "frame" not in f[3]
    assert "locked" not in f[3]
    assert (f[2]["frame"], f[2]["owns"], f[2]["locked"]) == ("cast", ["default_view"], ["hidden"])
    assert f[5]["added_by"] == "developer" and f[5]["added"] == "2026-10-21"
    assert f[5]["needs"]["where"] == "runs/queue/priority-developer.json"
    assert features.validate(doc) == [], features.validate(doc)


def _convert_idempotent():
    proto = features.load(PROTOTYPE)
    once = features.convert(proto, family="prototype")
    twice = features.convert(once, family="prototype")
    assert twice == once and list(twice) == list(once)
    assert features.dumps(twice) == features.dumps(once)
    for name in FAMILIES:
        doc = family(name)
        assert features.convert(doc, family=name) == doc, "%s is not a fixed point" % name


def _convert_cli():
    out_dir = temp()
    out = os.path.join(out_dir, "prototype.features.json")
    report = os.path.join(out_dir, "findings.md")
    code, text = run_cli("--convert", PROTOTYPE, "--out", out, "--findings", report)
    assert code == 0, (code, text)
    assert "wrote %s: 5 features" % out in text, text
    with open(out, encoding="utf-8") as fh:
        written = fh.read()
    assert written == features.dumps(features.convert(features.load(PROTOTYPE),
                                                      family="prototype"))
    with open(report, encoding="utf-8") as fh:
        assert "## prototype" in fh.read()
    proto = features.load(PROTOTYPE)
    proto["features"][0]["colour"] = "red"
    bad = os.path.join(out_dir, "bad.json")
    with open(bad, "w", encoding="utf-8") as fh:
        json.dump(proto, fh)
    out2 = os.path.join(out_dir, "bad.features.json")
    code, text = run_cli("--convert", bad, "--out", out2, "--findings", report)
    assert code == 2 and "feature 1: unknown key 'colour'" in text, (code, text)
    assert not os.path.exists(out2), "a list with format findings left was written"
    code, text = run_cli("--convert", os.path.join(out_dir, "nope.json"), "--out", out2)
    assert code == 3, (code, text)


def _convert_changes():
    raw = ['{"n": 9, "said": "grid view", "at": "2026-10-21T04:23:41Z", "by": "developer", "route": "B"}',
           {"n": 9, "said": "x", "at": "2026-10-21T04:23:41Z", "by": "developer", "route": "note"}]
    got = features.convert_changes(raw)
    assert [g["route"] for g in got] == ["claude-code", "note"], got
    assert list(got[0]) == ["n", "said", "at", "by", "route"]
    assert features.convert_changes(got) == got
    lines = reference_lines()
    assert all(json.loads(l)["route"] == "claude-code" for l in lines), lines
    with open(LOG, encoding="utf-8") as fh:
        assert fh.read() == features.dumps_changes([json.loads(l) for l in lines])


def _changes_cli():
    outlier = os.path.join(TEMPLATES, "outlier-demo.features.json")
    code, text = run_cli("--changes", LOG, outlier)
    assert code == 0 and "valid: 3 changes" in text, (code, text)
    d = temp()
    bad = os.path.join(d, "x--demo.changes.jsonl")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(change_line(n=40)) + "\n")
    code, text = run_cli("--changes", bad, outlier)
    assert code == 2 and "line 1: n 40 is retired" in text, (code, text)
    code, text = run_cli("--changes", os.path.join(d, "none.jsonl"), outlier)
    assert code == 3, (code, text)


# ------------------------------------------------------ the three family lists


def _family_lists():
    total = 0
    for name in FAMILIES:
        doc = family(name)
        kinds = features.validate_kinds(doc)
        fmt = [k["text"] for k in kinds if k["kind"] == "format"]
        assert fmt == [], "%s: %r" % (name, fmt)
        nums = sorted(int(re.match(r"feature (\d+):", k["text"]).group(1)) for k in kinds)
        assert nums == CONTENT[name], "%s content %r" % (name, kinds)
        total += len(kinds)
        assert (doc["schema"], doc["schema_minor"], doc["status"]) == (1, 2, "draft"), name
        assert doc["versions"] == {"A": "platform/views/viewers/_templates/%s.html" % name}
        for key in ("demo", "overlay", "exempt", "status_words"):
            assert key not in doc, (name, key)
        path = os.path.join(TEMPLATES, "%s.features.json" % name)
        with open(path, encoding="utf-8") as fh:
            assert fh.read() == features.dumps(doc), "%s is not features.dumps() of itself" % name
        code, text = run_cli(path)
        assert "format 0 · content %d" % len(CONTENT[name]) in text or (
            code == 0 and not CONTENT[name]), (name, code, text)
        assert code == (2 if CONTENT[name] else 0), (name, code, text)
    assert total == 8, total   # 9 until emails-demo 34 was fixed by its owner, 2026-10-21
    outlier = family("outlier-demo")
    assert [r["n"] for r in outlier["retired"]] == [40, 41, 42, 43, 65], outlier["retired"]
    assert all(set(r) == {"n", "name", "retired", "why", "by"} for r in outlier["retired"])
    with open(REPORT, encoding="utf-8") as fh:
        report = fh.read()
    for name in FAMILIES:
        assert "## %s" % name in report, name
        for n in CONTENT[name]:
            assert "- %d: feature %d:" % (n, n) in report, (name, n)


# ------------------------------------------------------ sync (fixtures only)


def _sync_text():
    with open(PAGE, encoding="utf-8") as fh:
        html = fh.read()
    doc = {"title": "a <b> title </script>", "features": [{"n": 1, "name": "Run title"}]}
    new = features.sync_text(html, doc)
    block = re.search(r'id="fo-features">(.*?)</script>', new, re.S).group(1)
    assert "<" not in block and "\\u003c/script>" in block, block
    assert json.loads(block) == doc
    before, after = html.split('id="fo-features">')[0], html.split("</script>", 2)[2]
    assert new.startswith(before) and new.endswith(after.split("</script>", 1)[1])
    assert '{"keep": "this block is not the catalog"}' in new
    assert new.count('id="fo-features">') == 1
    assert features.sync_text(new, doc) == new
    for bad in (html.replace('id="fo-features"', 'id="fo-x"'),
                html + '<script type="application/json" id="fo-features">{}</script>'):
        try:
            features.sync_text(bad, doc)
        except ValueError:
            continue
        raise AssertionError("no ValueError for a page with 0 or 2 blocks")


def _sync_cli():
    d = temp()
    page = os.path.join(d, "page.html")
    shutil.copy(PAGE, page)
    code, text = run_cli("sync", page, PROTOTYPE)
    assert code == 0 and "synced %s: 5 features" % page in text, (code, text)
    code, text = run_cli("sync", page, PROTOTYPE)
    assert code == 0 and "unchanged %s" % page in text, (code, text)
    with open(page, "a", encoding="utf-8") as fh:
        fh.write('<script type="application/json" id="fo-features">{}</script>')
    code, text = run_cli("sync", page, PROTOTYPE)
    assert code == 2, (code, text)


# ------------------------------------------------------ change = commit (fake git)


class FakeGit:
    """Records every argv; never runs git. `push_fail` pushes are rejected."""

    def __init__(self, push_fail=0, email="developer@example.com", status=""):
        self.calls, self.push_fail, self.email, self.status = [], push_fail, email, status

    def __call__(self, argv, cwd):
        self.calls.append(list(argv))
        if argv[:3] == ["git", "config", "user.email"]:
            return 0, self.email + "\n", ""
        if argv[:2] == ["git", "push"] and self.push_fail:
            self.push_fail -= 1
            return 1, "", ("To origin\n ! [rejected]        main -> main (fetch first)\n"
                           "error: failed to push some refs")
        if argv[:2] == ["git", "status"]:
            return 0, self.status, ""
        return 0, "", ""

    def git_calls(self):
        return [c for c in self.calls if c[:3] != ["git", "config", "user.email"]]


def workspace():
    """A temporary root with one family list and drafts for two people."""
    root = temp()
    tpl = os.path.join(root, "platform", "views", "viewers", "_templates")
    os.makedirs(tpl)
    doc = features.convert(features.load(PROTOTYPE), family="fam")
    with open(os.path.join(tpl, "fam.features.json"), "w", encoding="utf-8") as fh:
        fh.write(features.dumps(doc))
    with open(os.path.join(tpl, "fam.html"), "w", encoding="utf-8") as fh:
        fh.write("<html></html>\n")
    for person in ("developer", "editor"):
        drafts = os.path.join(root, "platform", "views", "viewers", person, "drafts")
        os.makedirs(drafts)
        for name in ("fam--demo.html", os.path.join("..", "fam.html")):
            with open(os.path.join(drafts, name), "w", encoding="utf-8") as fh:
                fh.write("<html></html>\n")
    os.makedirs(os.path.join(root, ".git"))
    # FakeGit's address names developer through an identity file, never its local
    # part (LD-77 (one person resolver)).
    os.makedirs(os.path.join(root, "team", "people", "developer"))
    with open(os.path.join(root, "team", "people", "developer", "identity.json"), "w", encoding="utf-8") as fh:
        json.dump({"person": "developer", "emails": [{"address": "developer@example.com"}]}, fh)
    return root


NOW = datetime.datetime(2026, 10, 21, 4, 23, 41)
DRAFT = "platform/views/viewers/developer/drafts/fam--demo.html"
DRAFT_LOG = "platform/views/viewers/developer/drafts/fam--demo.changes.jsonl"
FORBIDDEN = ("reset", "stash", "rebase", "--force", "-f", "--force-with-lease", "checkout", "clean")


def assert_safe(calls):
    for c in calls:
        for word in FORBIDDEN:
            assert word not in c, "forbidden git call %r" % c
        assert c[:2] != ["git", "pull"] or c == ["git", "pull", "--no-rebase"], c


def _change_refuses():
    root = workspace()
    for page, says in (("platform/views/viewers/developer/fam.html", "is a live page"),
                       ("platform/views/viewers/_templates/fam.html", "_templates/"),
                       ("platform/views/viewers/editor/drafts/fam--demo.html", "is editor's draft, not developer's"),
                       ("../elsewhere/fam--demo.html", "outside the workspace")):
        git = FakeGit()
        got = features.change(page, 1, "bigger", root=root, runner=git, now=NOW)
        assert got.startswith("refused:") and says in got, (page, got)
        assert git.git_calls() == [], git.calls
    assert not os.path.exists(os.path.join(root, DRAFT_LOG))
    git = FakeGit()
    got = features.change(DRAFT, 6, "bring back the panel", root=root, runner=git, now=NOW)
    assert got == "refused: line 1: n 6 is retired", got
    got = features.change(DRAFT, 2, "x", root=root, runner=git, now=NOW, resolved="claude")
    assert got.startswith("refused: line 1: `match` is missing"), got
    assert git.git_calls() == [] and not os.path.exists(os.path.join(root, DRAFT_LOG))


def _change_on_draft():
    root = workspace()
    git = FakeGit()
    got = features.change(DRAFT, 2, "Turn the queue into a grid view", root=root, runner=git,
                          now=NOW, resolved="claude", match="L2 is the queue's layout.")
    assert got == "saved and shared", got
    paths = [DRAFT, DRAFT_LOG]
    assert git.calls[0] == ["git", "config", "user.email"], git.calls
    assert git.git_calls() == [["git", "add", "--"] + paths,
                               ["git", "commit", "-m", "page: fam 2 (developer)", "--"] + paths,
                               ["git", "push"]], git.calls
    assert_safe(git.calls)
    lines = features.read_changes(os.path.join(root, DRAFT_LOG))
    assert json.loads(lines[0]) == {"n": 2, "said": "Turn the queue into a grid view",
                                    "at": "2026-10-21T04:23:41Z", "by": "developer",
                                    "route": "claude-code", "resolved": "claude",
                                    "match": "L2 is the queue's layout."}, lines
    doc = features.load(os.path.join(root, "platform/views/viewers/_templates/fam.features.json"))
    assert features.validate_changes(lines, doc) == []
    git = FakeGit()
    fam = "platform/views/viewers/_templates/fam.features.json"
    got = features.change(DRAFT, 5, "Add priorities for me", person="developer", root=root,
                          runner=git, now=NOW, missing=True, needs=dict(D67_NEEDS),
                          family_list=fam)
    assert got == "saved and shared", got
    assert git.calls[0] == ["git", "add", "--", DRAFT, DRAFT_LOG, fam], git.calls
    assert git.calls[1][-4:] == ["--", DRAFT, DRAFT_LOG, fam], git.calls
    lines = features.read_changes(os.path.join(root, DRAFT_LOG))
    assert len(lines) == 2 and json.loads(lines[1])["kind"] == "missing", lines
    assert features.validate_changes(lines, doc) == []


def _change_push_rejected():
    root = workspace()
    git = FakeGit(push_fail=1)
    got = features.change(DRAFT, 1, "bigger", root=root, runner=git, now=NOW)
    assert got == "saved and shared", got
    assert [c[:2] for c in git.git_calls()] == [["git", "add"], ["git", "commit"],
                                                ["git", "push"], ["git", "pull"],
                                                ["git", "push"]], git.calls
    assert git.git_calls()[3] == ["git", "pull", "--no-rebase"]
    assert_safe(git.calls)
    git = FakeGit(push_fail=2)
    got = features.change(DRAFT, 1, "bigger", root=root, runner=git, now=NOW)
    assert got == "saved, not shared: To origin", got
    assert len([c for c in git.calls if c[:2] == ["git", "push"]]) == 2, git.calls
    assert_safe(git.calls)


# ------------------------------------------------------ autosave (fake git)


def _autosave():
    root = workspace()
    git = FakeGit(status="")
    assert features.autosave(root, runner=git) == ""
    assert git.git_calls() == [["git", "status", "--porcelain", "--",
                                "platform/views/viewers/developer/"]], git.calls
    git = FakeGit()
    assert features.autosave(root, person="nobody", runner=git) == ""
    assert git.calls == [], git.calls
    with open(os.path.join(root, ".git", "MERGE_HEAD"), "w") as fh:
        fh.write("abc\n")
    git = FakeGit(status=" M platform/views/viewers/developer/fam.html\n")
    assert features.autosave(root, person="developer", runner=git) == "skipped: a merge is in progress"
    assert git.calls == [], git.calls
    os.remove(os.path.join(root, ".git", "MERGE_HEAD"))
    status = (" M platform/views/viewers/developer/fam.html\n"
              "?? platform/views/viewers/developer/drafts/fam--demo.changes.jsonl\n"
              " M platform/views/viewers/editor/fam.html\n")
    git = FakeGit(status=status, push_fail=1)
    got = features.autosave(root, person="developer", runner=git)
    assert got == "saved and shared (2 files)", got
    paths = ["platform/views/viewers/developer/fam.html",
             "platform/views/viewers/developer/drafts/fam--demo.changes.jsonl"]
    assert git.calls == [["git", "status", "--porcelain", "--", "platform/views/viewers/developer/"],
                         ["git", "add", "--"] + paths,
                         ["git", "commit", "-m", "page: autosave (developer)", "--"] + paths,
                         ["git", "push"], ["git", "pull", "--no-rebase"], ["git", "push"]], git.calls
    assert_safe(git.calls)


# ------------------------------------------------------ the schema file


def _schema():
    with open(SCHEMA, encoding="utf-8") as fh:
        schema = json.load(fh)
    assert "v1_1" in schema and "v1_2" in schema
    assert schema["properties"]["schema_minor"]["enum"] == [0, 1, 2]
    assert schema["properties"]["retired"]["items"] == {"$ref": "#/$defs/retired"}
    ch = schema["$defs"]["change"]
    assert ch["required"] == features.CHANGE_KEYS
    assert list(ch["properties"]) == features.CHANGE_KEYS + features.CHANGE_OPTIONAL
    assert ch["properties"]["resolved"] == {"const": "claude", "description": ch["properties"]["resolved"]["description"]}
    assert ch["dependentRequired"] == {"resolved": ["match"]}
    assert schema["$defs"]["needs"]["required"] == features.NEEDS_REQUIRED
    assert list(schema["$defs"]["needs"]["properties"]) == features.NEEDS_REQUIRED + features.NEEDS_OPTIONAL
    assert list(schema["$defs"]["retired"]["properties"]) == features.RETIRED_REQUIRED + features.RETIRED_OPTIONAL
    entry = schema["$defs"]["feature"]["properties"]
    for key in features.ENTRY_OPTIONAL_V1_2:
        assert key in entry, key


check("v1.2 accepts D67: not-built with added_by + needs (and frame, owns, locked)", _accepts_d67)
check("v1.2 accepts the reference log: a resolved change with match, a kind missing "
      "change with needs", _accepts_reference_changes)
check("refused by name: not-built + added_by without needs", _not_built_added_by_without_needs)
check("refused by name: needs on a wired feature", _needs_on_wired)
check("refused by name: a needs block with an unknown key and no where", _needs_shape)
check("refused by name: resolved without match", _resolved_without_match)
check("refused by name: kind missing without needs", _kind_missing_without_needs)
check("refused by name: a retired n in features", _retired_in_features)
check("refused by name: a change on a retired n", _change_on_retired)
check("refused by name: resolved 'me', kind 'extra', route 'B'", _bad_values)
check("the v1.2 keys are unknown keys in a v1.1 file", _v12_keys_need_minor_2)
check("the v1 and v1.1 examples still validate", _old_examples_valid)
check("each finding is classed format or content", _finding_kinds)
check("convert() maps the prototype fixture to v1.2 and never mutates it", _convert_mapping)
check("convert() is idempotent, and the three family lists are its fixed points",
      _convert_idempotent)
check("--convert CLI: writes and reports; refuses format findings (2); unreadable (3)",
      _convert_cli)
check("convert_changes maps route B to claude-code; the reference log is converted",
      _convert_changes)
check("--changes CLI: 0 valid, 2 retired n, 3 missing", _changes_cli)
check("the three family lists: zero format findings, the 8 content findings by number, "
      "written by dumps(), listed in the report", _family_lists)
check("sync_text replaces exactly the one block and escapes <; ValueError on 0 or 2",
      _sync_text)
check("sync CLI on a temporary copy: synced, then unchanged, then 2", _sync_cli)
check("change() refuses a live page, _templates/, another person's draft, outside, "
      "a retired n, resolved without match — before any git", _change_refuses)
check("change() on a draft: a valid line, then add / commit / push with one pathspec",
      _change_on_draft)
check("change() on a rejected push: pull --no-rebase, push once more; never reset, "
      "stash or --force", _change_push_rejected)
check("autosave: silent when clean or no folder, skipped on MERGE_HEAD, commits only "
      "viewers/<person>/", _autosave)
check("the schema file says v1.2: enum [0, 1, 2], retired, needs, the change keys", _schema)

for path in TEMPS:
    shutil.rmtree(path, ignore_errors=True)
passed = sum(RESULTS)
print("%d/%d passed" % (passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
