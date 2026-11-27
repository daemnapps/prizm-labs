#!/usr/bin/env python3
"""PF-8 (show my pages): list_pages / render / main on a fixture person in
temporary roots, the save state from a fake git, drift after a template
change, a prepared page, the robust paths, the CLI through features.main, and
a read-only pass over the real tree.

    python3 test_pf8_show_my_pages.py

Stdlib only, no network, never runs git: a fake runner records argv, answers
`status` and `log` from the test's own strings and `hash-object` with the git
blob id of the file's bytes. Fixtures are copied from test_pf8_fixtures/ into
temporary roots (removed at the end); the blob tokens __BLOB_<family>__ are
filled in on the copy. Proves it writes nothing: the temp root's listing
(paths + sha256) around every call, and every file under the real
platform/views/viewers/ around the whole run. One PASS/FAIL line per check,
then "N/M passed"; exit 1 on any FAIL.
"""
import contextlib, hashlib, io, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import features  # noqa: E402
import live  # noqa: E402
import pages  # noqa: E402

FIX = os.path.join(HERE, "test_pf8_fixtures")
VIEWERS = os.path.join(ROOT, "platform", "views", "viewers")
P = "platform/views/viewers/fixp/"
T = "platform/views/viewers/_templates/"
ALPHA = P + "alpha.html"
ALPHA_RECORD = P + "alpha.live.jsonl"
OLD = P + "drafts/alpha--2026-10-20.html"
BETA = P + "drafts/beta--demo.html"
WENT_LIVE = "2026-10-20T09:00:00Z"
FORBIDDEN = ("add", "commit", "push", "fetch", "reset", "stash")

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


def blob(path):
    with open(path, "rb") as handle:
        data = handle.read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class FakeGit(object):
    """Records argv; status and log from strings; hash-object = the blob id."""

    def __init__(self, status="", log="", status_fail=None, log_fail=None, email="fixp@x.test"):
        self.calls = []
        self.status, self.log, self.email = status, log, email
        self.status_fail, self.log_fail = status_fail, log_fail

    def __call__(self, argv, cwd):
        self.calls.append(list(argv))
        ALL_CALLS.append(list(argv))
        verb = argv[1]
        if verb == "status":
            return (128, "", self.status_fail) if self.status_fail else (0, self.status, "")
        if verb == "log":
            return (128, "", self.log_fail) if self.log_fail else (0, self.log, "")
        if verb == "hash-object":
            path = os.path.join(cwd, argv[-1])
            if not os.path.isfile(path):
                return 128, "", "fatal: could not open '%s'" % argv[-1]
            return 0, blob(path) + "\n", ""
        if verb == "config":
            return 0, self.email + "\n", ""
        return 1, "", "unexpected git call"

    def verbs(self, verb):
        return [c for c in self.calls if c[1] == verb]


def make_root():
    """A temp root: the fixture tree, blob tokens filled in."""
    root = tempfile.mkdtemp(prefix="pf8-")
    TEMPS.append(root)
    shutil.copytree(os.path.join(FIX, "platform"), os.path.join(root, "platform"))
    blobs = {f: blob(os.path.join(root, T + f + ".html")) for f in ("alpha", "beta", "gamma")}
    for base, _, names in os.walk(os.path.join(root, P)):
        for name in names:
            path = os.path.join(base, name)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            new = text
            for fam, sha in blobs.items():
                new = new.replace("__BLOB_%s__" % fam, sha)
            if new != text:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(new)
    return root


def listed(root, **kw):
    """list_pages, asserting the temp root is byte-identical around the call."""
    before = tree_hashes(root)
    result = pages.list_pages(root=root, **kw)
    assert tree_hashes(root) == before, "list_pages changed files under the temp root"
    return result


def fam(result, name):
    return next(f for f in result["families"] if f["family"] == name)


def edit(root, rel, old, new):
    path = os.path.join(root, rel)
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    assert old in text, "%s has no %r" % (rel, old)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text.replace(old, new, 1))


# ------------------------------------------------------------ the card's case


def _card_rows():
    root = make_root()
    git = FakeGit()
    result = listed(root, person="fixp", runner=git)
    assert result["refused"] is None and result["person"] == "fixp", result
    assert [f["family"] for f in result["families"]] == ["alpha", "beta", "gamma"], result
    alpha, beta, gamma = (fam(result, f) for f in ("alpha", "beta", "gamma"))
    page = alpha["live"]
    assert page["path"] == ALPHA and not page["prepared"], page
    assert page["went_live"] == WENT_LIVE and page["drift"] == "no", page
    assert page["base"] == page["now"] == blob(os.path.join(root, T + "alpha.html")), page
    assert page["numbers"] == 3, "distinct numbers 1, 2, 3 (9 is only in page-prefs): %r" % page
    assert page["save"] == "saved", page
    assert [d["name"] for d in alpha["drafts"]] == ["2026-10-20"], alpha["drafts"]
    old = alpha["drafts"][0]
    assert old["path"] == OLD and old["made_from"] == "old live 2026-10-20", old
    assert old["changes"] == 0 and old["newest"] is None and old["drift"] == "unknown", old
    assert beta["live"] is None and [d["name"] for d in beta["drafts"]] == ["demo"], beta
    demo = beta["drafts"][0]
    assert demo["path"] == BETA and demo["made_from"] == "template", demo
    assert demo["changes"] == 2 and demo["drift"] == "no" and demo["save"] == "saved", demo
    assert demo["newest"] == ("2 · 2026-10-21T05:00:00Z · "
                              "turn the list into a grid with three columns and keep the ne"), demo
    assert not alpha["available"] and not beta["available"], result
    assert gamma["available"] and gamma["owner"] == "fixo", gamma
    assert gamma["live"] is None and gamma["drafts"] == [], gamma
    assert result["other"] == [], result["other"]
    for note in pages.STANDING_NOTES:
        assert note in result["notes"], (note, result["notes"])
    assert pages.NOTE_SAVE not in result["notes"], "all saved: no autosave note"


check("card case: one live, two drafts, one available — exactly those rows", _card_rows)


def _card_render():
    root = make_root()
    lines = pages.render(listed(root, person="fixp", runner=FakeGit()))
    text = "\n".join(lines)
    for path in (ALPHA, OLD, BETA):
        opens = [l for l in lines if l.strip() == "open %s" % path]
        assert len(opens) == 1, (path, lines)
    assert "  live      %s · went live %s · drift no · 3 numbers · saved" % (ALPHA, WENT_LIVE) \
        in lines, lines
    assert any(l.startswith("  draft     demo · %s · from template · 2 changes · newest 2 · " % BETA)
               for l in lines), lines
    assert any(l.startswith("  draft     2026-10-20 · %s · from old live 2026-10-20 · 0 changes · saved"
                            % OLD) for l in lines), lines
    assert "available: gamma (owner fixo)" in lines, lines
    assert "note: %s" % pages.NOTE_UPDATE in lines, lines
    assert "available: alpha" not in text and "available: beta" not in text, lines


check("card case: render names each page once in an open line", _card_render)


# ------------------------------------------------------------ drift


def _drift():
    root = make_root()
    edit(root, T + "alpha.html", "<h1", "<h1 class=\"moved\"")
    result = listed(root, person="fixp", runner=FakeGit())
    assert fam(result, "alpha")["live"]["drift"] == "yes", fam(result, "alpha")
    assert fam(result, "beta")["drafts"][0]["drift"] == "no", fam(result, "beta")
    edit(root, T + "beta.html", "<h1", "<h1 class=\"moved\"")
    result = listed(root, person="fixp", runner=FakeGit())
    assert fam(result, "beta")["drafts"][0]["drift"] == "yes", fam(result, "beta")


check("drift: a template change shows drift yes on its live page and its draft", _drift)


# ------------------------------------------------------------ save state


def saves(result):
    out = {}
    for f in result["families"]:
        if f["live"]:
            out[f["live"]["path"]] = f["live"]["save"]
        for d in f["drafts"]:
            out[d["path"]] = d["save"]
    for o in result["other"]:
        out[o["path"]] = o["save"]
    return out


def _not_saved():
    root = make_root()
    git = FakeGit(status="?? %s\n" % BETA)
    result = listed(root, person="fixp", runner=git)
    assert saves(result) == {ALPHA: "saved", OLD: "saved", BETA: "not saved"}, saves(result)
    assert pages.NOTE_SAVE in result["notes"], result["notes"]


check("save: an uncommitted draft reads not saved, the rest saved", _not_saved)


def _not_shared():
    root = make_root()
    git = FakeGit(log="\n%s\n%s\n" % (ALPHA, ALPHA_RECORD))
    result = listed(root, person="fixp", runner=git)
    assert saves(result) == {ALPHA: "not shared", OLD: "saved", BETA: "saved"}, saves(result)
    assert pages.NOTE_SAVE in result["notes"], result["notes"]
    lines = pages.render(result)
    assert any(l.startswith("  live      %s" % ALPHA) and l.endswith("· not shared")
               for l in lines), lines
    assert "note: to save and share: features.py autosave" in lines, lines


check("save: a committed, unpushed live page reads not shared + autosave note", _not_shared)


def _log_rides_on_change_log():
    root = make_root()
    git = FakeGit(status=" M %s\n" % (P + "drafts/beta--demo.changes.jsonl"))
    result = listed(root, person="fixp", runner=git)
    assert saves(result)[BETA] == "not saved", saves(result)


check("save: an uncommitted change log makes its page not saved", _log_rides_on_change_log)


def _untracked_folder():
    root = make_root()
    git = FakeGit(status="?? %s\n" % P)
    result = listed(root, person="fixp", runner=git)
    assert set(saves(result).values()) == {"not saved"}, saves(result)


check("save: an untracked person folder makes every page not saved", _untracked_folder)


def _status_fails():
    root = make_root()
    git = FakeGit(status_fail="fatal: not a git repository")
    result = listed(root, person="fixp", runner=git)
    want = "unknown (fatal: not a git repository)"
    assert set(saves(result).values()) == {want}, saves(result)
    git = FakeGit(log_fail="fatal: bad revision 'origin/main..HEAD'")
    result = listed(root, person="fixp", runner=git)
    assert set(saves(result).values()) == {"unknown (fatal: bad revision 'origin/main..HEAD')"}, \
        saves(result)


check("save: a failing status or log call reads unknown (…) on every page", _status_fails)


def _one_call_each():
    root = make_root()
    git = FakeGit(status="?? %s\n" % BETA, log="%s\n" % ALPHA)
    listed(root, person="fixp", runner=git)
    assert len(git.verbs("status")) == 1 and len(git.verbs("log")) == 1, git.calls
    assert git.verbs("status")[0] == ["git", "status", "--porcelain", "--", P], git.calls
    assert git.verbs("log")[0] == ["git", "log", "--name-only", "--format=",
                                   "origin/main..HEAD", "--", P], git.calls
    assert set(c[1] for c in git.calls) <= {"status", "log", "hash-object"}, git.calls
    for argv in git.verbs("hash-object"):
        assert argv[:3] == ["git", "hash-object", "--"] and argv[3].startswith(T), argv


check("git: exactly one status and one log per run, only read-only verbs", _one_call_each)


# ------------------------------------------------------------ prepared


def _prepared():
    root = make_root()
    edit(root, ALPHA, "<head>", "<head>\n" + live.PREPARED_META)
    result = listed(root, person="fixp", runner=FakeGit())
    assert fam(result, "alpha")["live"]["prepared"] is True, fam(result, "alpha")
    lines = pages.render(result)
    assert ("  prepared  %s · goes live on first open: features.py first-open %s · saved"
            % (ALPHA, ALPHA)) in lines, lines
    assert ("            open %s" % ALPHA) in lines, lines


check("prepared: the mark in <head> → prepared, render names features.py first-open", _prepared)


# ------------------------------------------------------------ robust


def _bad_live_line():
    root = make_root()
    with open(os.path.join(root, ALPHA_RECORD), "a", encoding="utf-8") as handle:
        handle.write("not json at all\n")
        handle.write('{"kind": "gone", "at": "2026-10-21T00:00:00Z"}\n')
    result = listed(root, person="fixp", runner=FakeGit())
    assert fam(result, "alpha")["live"]["went_live"] == WENT_LIVE, fam(result, "alpha")
    named = [n for n in result["notes"] if ALPHA_RECORD in n]
    assert len(named) == 1 and "2 invalid lines skipped" in named[0], result["notes"]


check("robust: invalid .live.jsonl lines → one note naming the file, no exception",
      _bad_live_line)


def _bad_change_line():
    root = make_root()
    with open(os.path.join(root, P + "drafts/beta--demo.changes.jsonl"), "a",
              encoding="utf-8") as handle:
        handle.write("{broken\n")
    result = listed(root, person="fixp", runner=FakeGit())
    demo = fam(result, "beta")["drafts"][0]
    assert demo["changes"] == 3 and demo["newest"] is None, demo
    assert any("beta--demo.changes.jsonl" in n for n in result["notes"]), result["notes"]


check("robust: an unparseable change line is a note, never an exception", _bad_change_line)


def _missing_live_log():
    root = make_root()
    os.remove(os.path.join(root, ALPHA_RECORD))
    result = listed(root, person="fixp", runner=FakeGit())
    page = fam(result, "alpha")["live"]
    assert page["went_live"] is None and page["drift"] == "unknown", page
    assert any(ALPHA_RECORD in n for n in result["notes"]), result["notes"]


check("robust: no .live.jsonl → went live unknown and a note", _missing_live_log)


def _no_person():
    root = make_root()
    git = FakeGit(email="")
    result = listed(root, runner=git)
    assert result["refused"] == "no person — pass --person or set git config user.email", result
    assert result["families"] == [] and result["other"] == [], result
    assert pages.render(result) == ["refused: %s" % result["refused"]]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = pages.main([], root=root, runner=FakeGit(email=""))
    assert code == 2 and out.getvalue().startswith("refused: "), (code, out.getvalue())


check("robust: no person (empty git email) → refused, exit 2", _no_person)


def _email_person():
    root = make_root()
    # Narrowed to intent by LD-77 (one person resolver): the address names the
    # folder through team/people/<id>/identity.json, never by its local part.
    os.makedirs(os.path.join(root, "team", "people", "fixp"))
    with open(os.path.join(root, "team", "people", "fixp", "identity.json"), "w", encoding="utf-8") as handle:
        handle.write('{"person": "fixp", "emails": [{"address": "fixp@example.test"}]}\n')
    result = listed(root, runner=FakeGit(email="fixp@example.test"))
    assert result["person"] == "fixp" and fam(result, "alpha")["live"], result
    result = listed(root, runner=FakeGit(email="fixp@elsewhere.test"))
    assert result["person"] == "" and result["refused"], result


check("person: the git email names the folder through identity.json, never its local part", _email_person)


def _no_folder():
    root = make_root()
    git = FakeGit()
    result = listed(root, person="nobody", runner=git)
    assert git.calls == [], git.calls
    assert all(f["available"] for f in result["families"]), result
    assert result["other"] == [] and result["refused"] is None, result
    for note in pages.STANDING_NOTES:
        assert note in result["notes"], result["notes"]


check("robust: a person with no folder → zero git calls, every family available", _no_folder)


def _other_page():
    root = make_root()
    with open(os.path.join(root, P + "notes.html"), "w", encoding="utf-8") as handle:
        handle.write("<html><body>notes</body></html>\n")
    os.makedirs(os.path.join(root, P + "tests"))
    with open(os.path.join(root, P + "tests", "t.html"), "w", encoding="utf-8") as handle:
        handle.write("<html></html>\n")
    result = listed(root, person="fixp", runner=FakeGit())
    assert result["other"] == [{"path": P + "notes.html", "save": "saved"}], result["other"]
    lines = pages.render(result)
    assert "other pages:" in lines and "  %snotes.html · saved" % P in lines, lines


check("other: a non-family page is listed, other folders ignored", _other_page)


def _bad_list():
    root = make_root()
    with open(os.path.join(root, T + "delta.features.json"), "w", encoding="utf-8") as handle:
        handle.write("{not json")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = pages.main(["--person", "fixp"], root=root, runner=FakeGit())
    assert code == 3 and "delta.features.json" in out.getvalue(), (code, out.getvalue())


check("cli: an unreadable family list exits 3", _bad_list)


# ------------------------------------------------------------ CLI wiring


def _features_main():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = features.main(["pages", "--person", "zz-pf8-nobody"])
    assert code == 0, (code, out.getvalue())
    assert "available: run-detail" in out.getvalue(), out.getvalue()
    assert "features.py pages [--person P]" in features.USAGE


check("cli: features.main pages --person <nobody> exits 0, lists run-detail available",
      _features_main)


def _pages_main():
    root = make_root()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = pages.main(["--person", "fixp"], root=root, runner=FakeGit())
    assert code == 0 and ("open %s" % BETA) in out.getvalue(), (code, out.getvalue())
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        code = pages.main(["--bogus"], root=root, runner=FakeGit())
    assert code == 2, code


check("cli: pages.main --person fixp exits 0; a bad argument exits 2", _pages_main)


# ------------------------------------------------------------ the real tree


def _real_tree():
    git = FakeGit()
    result = pages.list_pages(person="developer", root=ROOT, runner=git)
    real = sorted(features.family_of(n) for n in os.listdir(os.path.join(ROOT, T))
                  if n.endswith(".features.json"))
    assert [f["family"] for f in result["families"]] == real, result["families"]
    for f in result["families"]:
        assert f["available"] == (f["live"] is None and not f["drafts"]), f
    names = set(d["path"] for f in result["families"] for d in f["drafts"])
    want = set("platform/views/viewers/developer/drafts/%s--demo.html" % x
               for x in ("emails", "outlier-demo", "run-detail"))
    missing = want - names
    if missing:
        print("      note: developer's drafts moved on; not found now: %s" % ", ".join(sorted(missing)))
    print("      --- render(list_pages(person='developer', root=<repo>, runner=<fake clean>)) ---")
    for line in pages.render(result):
        print("      " + line)
    assert set(c[1] for c in git.calls) <= {"status", "log", "hash-object"}, git.calls


check("real tree: developer's pages list every real family once, read-only", _real_tree)


# ------------------------------------------------------------ nothing written


def _no_forbidden():
    assert ALL_CALLS, "no git calls were recorded at all"
    for argv in ALL_CALLS:
        for word in FORBIDDEN:
            assert word not in argv, argv


check("git: no argv ever carries add, commit, push, fetch, reset or stash", _no_forbidden)


for path in TEMPS:
    shutil.rmtree(path, ignore_errors=True)


def _real_untouched():
    assert tree_hashes(VIEWERS) == REAL_BEFORE, "files under platform/views/viewers/ changed"


check("nothing written: every file under the real platform/views/viewers/ unchanged",
      _real_untouched)

print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
