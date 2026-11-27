#!/usr/bin/env python3
"""The draft verb (/page-draft): make_draft / main on a fixture person in
temporary roots — a template draft is PV-1 (personal-view skill)'s
personal_text byte for byte, a live draft carries the live log's base, the
refusals write nothing, a name is never overwritten, the git calls are
exactly add / commit / push of the two new paths, PF-8 (show my pages) lists
the result, and the real tree is untouched.

    python3 test_draft.py

Stdlib only, no network, never runs git: a fake runner records argv and
answers config / status / log / hash-object / add / commit / push. One
PASS/FAIL line per check, then "N/M passed"; exit 1 on any FAIL.
"""
import contextlib, hashlib, io, json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import features  # noqa: E402
import live  # noqa: E402
import draft  # noqa: E402
import pages  # noqa: E402

PV = draft._pv()
VIEWERS = os.path.join(ROOT, "platform", "views", "viewers")
T = "platform/views/viewers/_templates/"
P = "platform/views/viewers/fixp/"
NOW = "2026-10-21T10:00:00Z"
BASE = "a" * 40
TEMPLATE = "<!doctype html>\n<html><head><title>alpha</title></head>\n<body>\n" \
           "<div data-feature=\"1\">one</div>\n</body></html>\n"
LIVE_PAGE = "<!doctype html>\n<html><head><title>alpha</title></head>\n<body>\n" \
            "<div data-feature=\"1\">one, live</div>\n</body></html>\n"
FAMILY = {"schema": 1, "schema_minor": 2, "title": "alpha", "status": "draft",
          "kinds": {}, "state_words": {}, "features": []}

RESULTS, TEMPS = [], []
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
    def __init__(self, email="fixp@x.test", push_fail=0):
        self.calls, self.email, self.push_fail = [], email, push_fail

    def __call__(self, argv, cwd):
        self.calls.append(list(argv))
        verb = argv[1]
        if verb == "config":
            return 0, self.email + "\n", ""
        if verb in ("status", "log"):
            return 0, "", ""
        if verb == "hash-object":
            with open(os.path.join(cwd, argv[-1]), "rb") as handle:
                return 0, PV.blob_sha(handle.read()) + "\n", ""
        if verb == "push" and self.push_fail:
            self.push_fail -= 1
            return 1, "", "! [rejected] main -> main (fetch first)"
        if verb in ("add", "commit", "push", "pull"):
            return 0, "", ""
        return 1, "", "unexpected git call"

    def verbs(self):
        return [c[1] for c in self.calls if c[1] != "config"]


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as handle:
        return handle.read()


def make_root(live_page=None, live_log=None):
    root = tempfile.mkdtemp(prefix="pfdraft-")
    TEMPS.append(root)
    write(root, T + "alpha.html", TEMPLATE)
    write(root, T + "alpha.features.json", json.dumps(FAMILY))
    write(root, T + "beta.html", TEMPLATE)  # a page with no family list
    if live_page is not None:
        write(root, P + "alpha.html", live_page)
    if live_log is not None:
        write(root, P + "alpha.live.jsonl", live_log)
    write(root, "platform/views/viewers/editor/alpha.html", LIVE_PAGE)
    # FakeGit's address names fixp through an identity file, never its local
    # part (LD-77 (one person resolver)).
    write(root, "team/people/fixp/identity.json",
          json.dumps({"person": "fixp", "emails": [{"address": "fixp@x.test"}]}))
    return root


def run(root, *args, **kw):
    git = kw.pop("git", None) or FakeGit()
    result = draft.make_draft(*args, root=root, runner=git, now=NOW, **kw)
    return result, git


def assert_refused(result, git, root, before, words):
    assert result["result"] == "refused", result
    assert words in result["lines"][0], result["lines"]
    assert git.verbs() == [], git.calls
    assert tree_hashes(root) == before, "a refusal wrote something"


def live_line(base):
    return json.dumps({"kind": "live", "at": "2026-10-20T09:00:00Z", "by": "fixp",
                       "from": P + "drafts/alpha--x.html", "base": base, "old": None,
                       "changes": 0}) + "\n"


# --- the template draft ----------------------------------------------------------

def t_template():
    root = make_root()
    result, git = run(root, "alpha")
    html = P + "drafts/alpha--20261021.html"
    log = P + "drafts/alpha--20261021.changes.jsonl"
    assert result["result"] == "draft", result
    assert result["written"] == [html, log], result["written"]
    blob = PV.blob_sha(TEMPLATE.encode("utf-8"))
    assert read(root, html) == PV.personal_text(TEMPLATE, "alpha", blob), "not personal_text"
    assert live.SHA_RE.search(read(root, html)).group(1) == blob, "base stamp"
    assert read(root, log) == "", "the change log is not empty"
    assert git.verbs() == ["add", "commit", "push"], git.verbs()
    assert git.calls[1][-2:] == [html, log] and git.calls[2][-2:] == [html, log], git.calls
    assert "page: draft alpha--20261021 (fixp)" in git.calls[2], git.calls[2]
    assert result["shared"] == "shared", result["shared"]
    assert result["lines"][0] == "draft: %s · from the alpha template" % html, result["lines"]
    assert read(root, T + "alpha.html") == TEMPLATE, "the template moved"


def t_template_path():
    root = make_root()
    result, _ = run(root, T + "alpha.html", name="grid")
    assert result["written"][0] == P + "drafts/alpha--grid.html", result


def t_default_name_never_overwrites():
    root = make_root()
    run(root, "alpha")
    first = read(root, P + "drafts/alpha--20261021.html")
    write(root, P + "drafts/alpha--20261021.html", first + "<!-- edited -->\n")
    result, _ = run(root, "alpha")
    assert result["written"][0] == P + "drafts/alpha--20261021-2.html", result
    assert read(root, P + "drafts/alpha--20261021.html").endswith("<!-- edited -->\n")


def t_named_taken():
    root = make_root()
    run(root, "alpha", name="grid")
    before = tree_hashes(root)
    result, git = run(root, "alpha", name="grid")
    assert_refused(result, git, root, before, "already exists; a draft is never overwritten")


def t_log_alone_taken():
    root = make_root()
    write(root, P + "drafts/alpha--grid.changes.jsonl", '{"n": 1}\n')
    before = tree_hashes(root)
    result, git = run(root, "alpha", name="grid")
    assert_refused(result, git, root, before, "alpha--grid.changes.jsonl already exists")


def t_bad_name():
    root = make_root()
    before = tree_hashes(root)
    result, git = run(root, "alpha", name="My Grid")
    assert_refused(result, git, root, before, "is not lowercase words")


# --- the live draft ----------------------------------------------------------------

def t_own_live():
    root = make_root(LIVE_PAGE, live_line(BASE))
    result, git = run(root, "alpha", from_live=True, name="tweak")
    html = P + "drafts/alpha--tweak.html"
    assert result["result"] == "draft", result
    assert read(root, html) == PV.place_strip(LIVE_PAGE, PV.banner("alpha", BASE)), "strip"
    assert PV.stamped_sha(read(root, html)) == BASE, "base"
    assert read(root, P + "alpha.html") == LIVE_PAGE, "the live page moved"
    assert any(draft.NOTE_NO_SIDEBAR in line for line in result["lines"]), result["lines"]
    assert git.verbs() == ["add", "commit", "push"], git.verbs()


def t_own_live_by_path():
    root = make_root(LIVE_PAGE, live_line(BASE))
    result, _ = run(root, P + "alpha.html")
    assert result["result"] == "draft" and "your live page" in result["lines"][0], result


def t_live_no_base():
    root = make_root(LIVE_PAGE)
    result, _ = run(root, "alpha", from_live=True)
    assert read(root, result["written"][0]) == LIVE_PAGE, "no base, no strip"
    assert any("no base recorded" in line for line in result["lines"]), result["lines"]


def t_other_persons_live():
    root = make_root()
    before = tree_hashes(root)
    result, git = run(root, "platform/views/viewers/editor/alpha.html")
    assert_refused(result, git, root, before, "is editor's live page")


def t_no_live():
    root = make_root()
    before = tree_hashes(root)
    result, git = run(root, "alpha", from_live=True)
    assert_refused(result, git, root, before, "you have no live alpha page")


def t_prepared():
    root = make_root(LIVE_PAGE.replace("<title>", live.PREPARED_META + "\n<title>"))
    before = tree_hashes(root)
    result, git = run(root, "alpha", from_live=True)
    assert_refused(result, git, root, before, "is prepared, not yet opened")


def t_draft_source():
    root = make_root()
    run(root, "alpha", name="grid")
    before = tree_hashes(root)
    result, git = run(root, P + "drafts/alpha--grid.html")
    assert_refused(result, git, root, before, "is a draft")


def t_no_family_list():
    root = make_root()
    before = tree_hashes(root)
    result, git = run(root, "beta")
    assert_refused(result, git, root, before, "is not a page family")


def t_live_flag_on_template():
    root = make_root()
    before = tree_hashes(root)
    result, git = run(root, T + "alpha.html", from_live=True)
    assert_refused(result, git, root, before, "drop --live")


def t_no_person():
    root = make_root()
    result, _ = run(root, "alpha", git=FakeGit(email=""))
    assert result["lines"][0].startswith("refused: no person"), result


# --- sharing, the CLI, PF-8 ----------------------------------------------------------

def t_push_rejected_once():
    root = make_root()
    result, git = run(root, "alpha", git=FakeGit(push_fail=1))
    assert git.verbs() == ["add", "commit", "push", "pull", "push"], git.verbs()
    assert ["git", "pull", "--no-rebase"] in git.calls, git.calls
    assert result["shared"] == "shared", result


def t_push_rejected_twice():
    root = make_root()
    result, _ = run(root, "alpha", git=FakeGit(push_fail=2))
    assert result["result"] == "draft", result
    assert result["shared"].startswith("not shared: ! [rejected]"), result["shared"]
    assert os.path.isfile(os.path.join(root, result["written"][0])), "the draft is kept"


def t_cli():
    assert features.SUBCOMMANDS.get("draft") is features._main_draft, "not wired"
    assert "features.py draft" in features.USAGE, "not in USAGE"
    root = make_root()
    git = FakeGit()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = draft.main(["alpha", "--name", "cli", "--no-share"], root=root, runner=git, now=NOW)
    assert code == 0, out.getvalue()
    assert out.getvalue().splitlines()[-1] == "not shared", out.getvalue()
    assert git.verbs() == [], git.calls
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = draft.main(["alpha", "--name", "cli"], root=root, runner=git, now=NOW)
    assert code == 2 and out.getvalue().startswith("refused:"), out.getvalue()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        assert draft.main(["--bogus"], root=root, runner=git) == 2


def t_pages_lists_it():
    root = make_root()
    run(root, "alpha", name="grid")
    result = pages.list_pages(person="fixp", root=root, runner=FakeGit())
    fam = [f for f in result["families"] if f["family"] == "alpha"][0]
    names = [(d["name"], d["made_from"], d["drift"], d["changes"]) for d in fam["drafts"]]
    assert names == [("grid", "template", "no", 0)], names


def t_real_tree_untouched():
    assert tree_hashes(VIEWERS) == REAL_BEFORE, "the real viewers tree changed"


for label, fn in [
        ("template draft = personal_text, empty log, add/commit/push of the two paths", t_template),
        ("template by path, --name", t_template_path),
        ("default name taken → -2, the first draft untouched", t_default_name_never_overwrites),
        ("explicit name taken → refused, nothing written", t_named_taken),
        ("a taken change log alone refuses the name", t_log_alone_taken),
        ("a bad name → refused", t_bad_name),
        ("own live page → strip with the live log's base, live untouched", t_own_live),
        ("own live page by path", t_own_live_by_path),
        ("live with no recorded base → no strip, said", t_live_no_base),
        ("another person's live page → refused", t_other_persons_live),
        ("no live page → refused, points at the template", t_no_live),
        ("a prepared live page → refused", t_prepared),
        ("a draft as the source → refused", t_draft_source),
        ("no family list → refused", t_no_family_list),
        ("--live on the template path → refused", t_live_flag_on_template),
        ("no person → refused", t_no_person),
        ("push rejected once → pull --no-rebase, push", t_push_rejected_once),
        ("push rejected twice → draft kept, not shared", t_push_rejected_twice),
        ("CLI: wired in features.py, --no-share, refusal exit 2", t_cli),
        ("PF-8 (show my pages) lists the new draft", t_pages_lists_it),
        ("the real platform/views/viewers tree is untouched", t_real_tree_untouched)]:
    check(label, fn)

for path in TEMPS:
    shutil.rmtree(path, ignore_errors=True)
print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
