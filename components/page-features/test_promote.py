#!/usr/bin/env python3
"""promote.py: a reviewed draft, anyone's, becomes its family's template on
the family owner's act; every refusal writes nothing.

    python3 test_promote.py

Stdlib only, no network, never runs git: every git call goes to a fake
runner that records argv and answers hash-object with the git blob id of the
file's bytes. Builds temporary roots from a copy of the real run-detail
draft, template, family list and platform/data/mini-runs/ (the going-live
check needs real data), with the draft moved into another person's folder
and stamped with the template's current blob id. Writes nothing under the
repo, and proves it with a sha256 of every file under
platform/views/viewers/ before and after. Runs under python3 and
/usr/bin/python3 (3.9). One PASS/FAIL line per check, then "N/M passed";
exit 1 on any FAIL.
"""
import hashlib, json, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import features  # noqa: E402
import live  # noqa: E402
import promote  # noqa: E402

VIEWERS = os.path.join(ROOT, "platform", "views", "viewers")
SRC_DRAFT = "platform/views/viewers/developer/drafts/run-detail--demo.html"
TEMPLATE = "platform/views/viewers/_templates/run-detail.html"
FAMILY = "platform/views/viewers/_templates/run-detail.features.json"
DRAFT = "platform/views/viewers/editor/drafts/run-detail--idea.html"
DRAFT_LOG = "platform/views/viewers/editor/drafts/run-detail--idea.changes.jsonl"
T_LOG = "platform/views/viewers/_templates/run-detail.changes.jsonl"
T_RECORD = "platform/views/viewers/_templates/run-detail.live.jsonl"
EDIT = "<!-- editor's idea -->"
CHANGE = {"n": 1, "said": "make the title bigger", "at": "2026-10-21T20:00:00Z",
          "by": "editor", "route": "claude-code"}

RESULTS, TEMPS = [], []


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


def blob_id(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class FakeGit(object):
    def __init__(self):
        self.calls = []

    def __call__(self, argv, cwd):
        self.calls.append(list(argv))
        if argv[:3] == ["git", "hash-object", "--"]:
            with open(os.path.join(cwd, argv[3]), "rb") as handle:
                return 0, blob_id(handle.read()) + "\n", ""
        if argv[:3] == ["git", "ls-files", "--"]:
            return 0, "", ""
        return 0, "", ""


def read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as handle:
        return handle.read()


def write(root, rel, text):
    os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
    with open(os.path.join(root, rel), "w", encoding="utf-8") as handle:
        handle.write(text)


def make_root(stale=False, overlay_edit=False):
    """editor's draft of run-detail, cut from the template as it is now (or from
    an older one), with one edit of her own and one change line."""
    root = tempfile.mkdtemp(prefix="promote-")
    TEMPS.append(root)
    for rel in (TEMPLATE, FAMILY):
        write(root, rel, read(ROOT, rel))
    shutil.copytree(os.path.join(ROOT, "platform", "data", "mini-runs"),
                    os.path.join(root, "platform", "data", "mini-runs"))
    with open(os.path.join(root, TEMPLATE), "rb") as handle:
        sha = "0" * 40 if stale else blob_id(handle.read())
    text = re.sub(r'data-template-sha="[0-9a-f]{40}"', 'data-template-sha="%s"' % sha,
                  read(ROOT, SRC_DRAFT), count=1)
    text = text.replace("</head>", EDIT + "</head>", 1)
    if overlay_edit:
        text = text.replace(live.OVERLAY_START, live.OVERLAY_START + "<!-- x -->", 1)
    write(root, DRAFT, text)
    write(root, DRAFT_LOG, json.dumps(CHANGE) + "\n")
    return root


def unchanged(root, fn):
    before = tree_hashes(root)
    out = fn()
    assert tree_hashes(root) == before, "a refusal wrote something"
    return out


def _stamp_present():
    assert live.SHA_RE.search(read(ROOT, SRC_DRAFT)), "the source draft carries no base stamp"


def _not_owner():
    root, git = make_root(), FakeGit()
    out = unchanged(root, lambda: promote.promote(DRAFT, person="editor", root=root, runner=git))
    assert out["result"] == "refused" and "only developer promotes" in out["lines"][0], out


def _check_only():
    root, git = make_root(), FakeGit()
    out = unchanged(root, lambda: promote.promote(DRAFT, person="developer", root=root, runner=git,
                                                  check_only=True))
    assert out["result"] == "would promote" and "1 change line" in out["lines"][0], out


def _promotes():
    root, git = make_root(), FakeGit()
    out = promote.promote(DRAFT, person="developer", root=root, runner=git,
                          now="2026-10-21T21:00:00Z")
    assert out["result"] == "promoted" and out["shared"] == "shared", out
    assert out["written"] == [TEMPLATE, T_LOG, T_RECORD], out["written"]
    text = read(root, TEMPLATE)
    assert EDIT in text, "the draft's edit is not in the template"
    assert "data-personal-view" not in text, "the personal strip went into the template"
    assert [json.loads(l) for l in read(root, T_LOG).splitlines()] == [CHANGE]
    record = json.loads(read(root, T_RECORD))
    assert record["by"] == "developer" and record["from"] == DRAFT and record["changes"] == 1, record
    assert read(root, DRAFT).count(EDIT) == 1, "the draft was touched"
    adds = [c for c in git.calls if c[1] in ("add", "commit")]
    assert adds[0] == ["git", "add", "--", TEMPLATE, T_LOG, T_RECORD], adds
    for argv in git.calls:
        for bad in ("reset", "stash", "--force", "checkout", "rebase"):
            assert bad not in " ".join(argv), argv


def _twice():
    root, git = make_root(), FakeGit()
    promote.promote(DRAFT, person="developer", root=root, runner=git, share_it=False)
    out = unchanged(root, lambda: promote.promote(DRAFT, person="developer", root=root, runner=git))
    assert out["result"] == "refused" and "template changed since" in out["lines"][0], out


def _stale():
    root, git = make_root(stale=True), FakeGit()
    out = unchanged(root, lambda: promote.promote(DRAFT, person="developer", root=root, runner=git))
    assert out["result"] == "refused" and "editor cuts a new draft" in out["lines"][0], out


def _overlay():
    root, git = make_root(overlay_edit=True), FakeGit()
    out = unchanged(root, lambda: promote.promote(DRAFT, person="developer", root=root, runner=git))
    assert out["result"] == "refused" and "going-live check" in out["lines"][0], out
    assert any("overlay block was edited" in l for l in out["lines"]), out


def _not_a_draft():
    root, git = make_root(), FakeGit()
    out = unchanged(root, lambda: promote.promote(TEMPLATE, person="developer", root=root,
                                                  runner=git))
    assert out["result"] == "refused" and "is not a draft" in out["lines"][0], out


def _cli():
    root = make_root()
    code = promote.main([DRAFT, "--person", "developer", "--check"], root=root, runner=FakeGit())
    assert code == 0, code
    code = promote.main([DRAFT, "--person", "editor"], root=root, runner=FakeGit())
    assert code == 2, code


def _real_untouched():
    assert tree_hashes(VIEWERS) == REAL_BEFORE, "the real viewers tree changed"


check("the source draft carries a base stamp", _stamp_present)
check("only the family owner promotes", _not_owner)
check("--check says what would happen and writes nothing", _check_only)
check("another person's draft becomes the template; its change lines and a record go with it",
      _promotes)
check("the same draft twice: the second is refused (the template moved)", _twice)
check("a draft cut from an older template is refused", _stale)
check("a draft that fails the going-live check is refused", _overlay)
check("a template is not a draft", _not_a_draft)
check("CLI exit codes", _cli)
check("the real viewers tree is untouched", _real_untouched)
for path in TEMPS:
    shutil.rmtree(path, ignore_errors=True)
print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
