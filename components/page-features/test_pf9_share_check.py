#!/usr/bin/env python3
"""PF-9 (share check), template mode: the blocker classes on a fixture family,
the verdicts through the scan seam, the template act and its refusals in
temporary roots, the three real families read-only, and the CLI.

    python3 test_pf9_share_check.py

Stdlib only, no network, never runs git: every git call goes to a fake
runner that records argv, answers ls-files from the test's own table (or, on
the real tree, by glob under the repo) and hash-object with the git blob id
of the file's bytes. The fake scan returns fixed strings; this test holds no
address classifier. Writes only under temporary folders it removes, and
proves the real tree untouched with a sha256 of every file under
platform/views/viewers/ before and after. Runs under python3 and
/usr/bin/python3 (3.9). One PASS/FAIL line per check, then "N/M passed";
exit 1 on any FAIL.
"""
import contextlib, copy, glob, hashlib, io, json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import features  # noqa: E402
import live  # noqa: E402
import share  # noqa: E402

FIX = os.path.join(HERE, "test_pf9_fixtures")
VIEWERS = os.path.join(ROOT, "platform", "views", "viewers")
TEMPLATE = "platform/views/viewers/_templates/sharefam.html"
FAMILY = "platform/views/viewers/_templates/sharefam.features.json"
DRAFT = "platform/views/viewers/fixp/drafts/sharefam--mine.html"
PREFS = '{"features": {"1": {"hidden": true}}, "changes": []}'

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
    path = tempfile.mkdtemp(prefix="pf9-")
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


def blob_id(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class FakeGit(object):
    """Records every argv. ls-files answers from `listed` (pattern → paths),
    or by glob under the root when `listed` is None; hash-object gives the
    blob id of the file's bytes; everything else answers 0."""

    def __init__(self, listed=None):
        self.calls = []
        self.listed = listed

    def __call__(self, argv, cwd):
        self.calls.append(list(argv))
        if argv[:3] == ["git", "ls-files", "--"]:
            if self.listed is None:
                hits = sorted(os.path.relpath(h, cwd) for h in glob.glob(os.path.join(cwd, argv[3]))
                              if os.path.isfile(h))
            else:
                hits = self.listed.get(argv[3], [])
            return 0, "".join(h + "\n" for h in hits), ""
        if argv[:3] == ["git", "hash-object", "--"]:
            with open(os.path.join(cwd, argv[3]), "rb") as handle:
                return 0, blob_id(handle.read()) + "\n", ""
        return 0, "", ""

    def words(self):
        return [argv[1] for argv in self.calls]


RUN_LISTED = {"runs/fix/*.json": ["runs/fix/a.json"]}


def assert_safe(calls):
    for argv in calls:
        words = " ".join(argv)
        for bad in ("reset", "stash", "--force", "fetch", "checkout", "rebase"):
            assert bad not in words, words


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


DOC = features.load(os.path.join(FIX, "sharefam.features.json"))
PAGE = read(os.path.join(FIX, "sharefam.html"))


def only(doc, *numbers):
    doc = copy.deepcopy(doc)
    doc["features"] = [e for e in doc["features"] if e["n"] in numbers]
    return doc


CLEAR = (2, 4, 7, 9)  # a lab-page rule (note), a run file in git, not-built, layout


def draft_of(template, sha):
    """The template as a person's draft: the personal-view strip carrying the
    base sha, the person's own prefs, and one edit of their own."""
    text = template.replace("<body>\n", '<body>\n<div data-personal-view="sharefam" '
                            'data-template-sha="%s" style="x">your personal sharefam</div>\n'
                            % sha, 1)
    text = text.replace('{"features": {}, "changes": []}', PREFS, 1)
    return text.replace("<p id=\"hello\">Hello</p>", "<p id=\"hello\">Hello from fixp</p>", 1)


def make_root(doc=None, draft=DRAFT, page_text=None):
    """A temporary root with the fixture template, the family list (`doc`)
    and a draft cut from the template at its current blob."""
    root = temp()
    write(os.path.join(root, TEMPLATE), PAGE)
    write(os.path.join(root, FAMILY), features.dumps(DOC if doc is None else doc))
    sha = blob_id(PAGE.encode("utf-8"))
    write(os.path.join(root, draft), draft_of(PAGE, sha) if page_text is None else page_text)
    return root


def by_tag(result, t):
    return [b for b in result["blockers"] if b["tag"] == t]


# --- the classes -----------------------------------------------------------

def _fixture_valid():
    assert features.validate(only(DOC, 2, 3, 4, 5, 6, 7, 8, 9)) == []
    findings = features.validate(DOC)
    assert findings and all(features.finding_kind(f) == "content" for f in findings), findings


def _classes():
    root = make_root()
    git = FakeGit(listed={})
    r = share.share_check(TEMPLATE, root=root, runner=git, scan=lambda t: [])
    assert r["refused"] is None and r["family"] == "sharefam" and r["page"] == TEMPLATE, r
    d1 = by_tag(r, "D1")
    assert len(d1) == 1 and d1[0]["level"] == "VIEW" and d1[0]["owner"] == "fixq", d1
    assert "lab/fixq/serve.py" in d1[0]["what"] and "rule 12" in d1[0]["what"], d1
    assert "/system-fit" in d1[0]["fix"], d1
    assert len([n for n in r["notes"] if n.startswith("D1:") and "/api/x" in n]) == 1, r["notes"]
    assert by_tag(r, "R2") == [], by_tag(r, "R2")
    assert [n for n in r["notes"] if n.startswith("R2:") and "lab/fixq/page.html" in n], r["notes"]
    m3 = by_tag(r, "M3")
    assert len(m3) == 1 and m3[0]["level"] == "VIEW" and "after-card" in m3[0]["what"], m3
    assert "Drive ids recorded by LD-64" in m3[0]["fix"] and m3[0]["owner"] == "fix pictures", m3
    d4 = by_tag(r, "D4")
    assert len(d4) == 1 and "not in git" in d4[0]["what"] and d4[0]["owner"] == "fix runs", d4
    assert ["git", "ls-files", "--", "runs/fix/*.json"] in git.calls, git.calls
    a5 = by_tag(r, "A5")
    assert len(a5) == 1 and a5[0]["level"] == "USE" and a5[0]["owner"] == "fixq", a5
    assert "lab server" in a5[0]["what"] and "share to view" in a5[0]["fix"], a5
    # PF-9c (share warns): a lab door is the one hard blocker here; a
    # components/ door is no blocker, it goes through the person's own Claude
    assert a5[0]["hard"] is True, a5
    assert all(b["hard"] is False for b in r["blockers"] if b["tag"] != "A5"), r["blockers"]
    assert by_tag(r, "A6") == [], by_tag(r, "A6")
    assert share.NOTE_BUTTONS % 1 in r["notes"], r["notes"]
    for t in ("D7", "D8", "L9"):
        assert by_tag(r, t) == [] and not [n for n in r["notes"] if n.startswith(t + ":")], t
    assert not [c for c in git.calls if "runs/fix/other.json" in " ".join(c)], git.calls
    assert all(c[1] == "ls-files" for c in git.calls), git.calls
    # the content finding of feature 1 blocks VIEW too, and stops nothing
    page = by_tag(r, "page")
    assert len(page) == 1 and page[0]["what"].startswith("the family list — feature 1:"), page
    assert r["view"] == "blocked" and r["use"] == "blocked", r


def _listed_run_is_reachable():
    root = make_root()
    r = share.share_check(TEMPLATE, root=root, runner=FakeGit(listed=RUN_LISTED))
    assert by_tag(r, "D4") == [], by_tag(r, "D4")


def _format_finding_stops():
    doc = only(DOC, 4)
    doc["features"][0]["kind"] = "widget"
    root = make_root(doc)
    git = FakeGit(listed={})
    r = share.share_check(TEMPLATE, root=root, runner=git, scan=lambda t: [])
    assert r["blockers"] and all(b["tag"] == "page" for b in r["blockers"]), r["blockers"]
    assert all(b["what"].startswith("the family list — ") for b in r["blockers"]), r["blockers"]
    assert git.calls == [] and r["view"] == "blocked" and r["use"] == "blocked", (git.calls, r)
    assert share.render(r)[1].startswith("  page: the family list — "), share.render(r)


def _check_refusals():
    root = make_root()
    os.remove(os.path.join(root, FAMILY))
    r = share.share_check(TEMPLATE, root=root, runner=FakeGit())
    assert r["refused"] and "does not exist" in r["refused"], r
    assert share.render(r) == ["refused: %s" % r["refused"]], share.render(r)
    root = make_root()
    write(os.path.join(root, FAMILY), "{not json")
    r = share.share_check(DRAFT, root=root, runner=FakeGit())
    assert r["refused"] and "UNREADABLE" in r["refused"], r
    r = share.share_check("components/page-features/README.md", root=make_root(), runner=FakeGit())
    assert r["refused"], r


# --- the verdicts ------------------------------------------------------------

def _verdicts():
    root = make_root(only(DOC, *CLEAR))
    r = share.share_check(DRAFT, root=root, runner=FakeGit(listed=RUN_LISTED))
    assert r["blockers"] == [] and r["view"] == "not proven" and r["use"] == "not proven", r
    assert share.NOTE_NO_SCAN in r["notes"], r["notes"]
    assert "system-integration has no check that takes a page" in share.NOTE_NO_SCAN
    r = share.share_check(DRAFT, root=root, runner=FakeGit(listed=RUN_LISTED), scan=lambda t: [])
    assert r["view"] == "pass" and r["use"] == "pass" and r["blockers"] == [], r
    assert share.NOTE_NO_SCAN not in r["notes"], r["notes"]
    seen = []
    r = share.share_check(DRAFT, root=root, runner=FakeGit(listed=RUN_LISTED),
                          scan=lambda t: seen.append(t) or ["127.0.0.1:8870 in a link"])
    assert seen == [read(os.path.join(root, DRAFT))], "the scan gets the page text"
    assert r["view"] == "blocked" and r["use"] == "blocked", r
    assert [(b["level"], b["tag"], b["what"]) for b in r["blockers"]] == [
        ("VIEW", "page", "127.0.0.1:8870 in a link")], r["blockers"]
    assert "  page: 127.0.0.1:8870 in a link" in share.render(r), share.render(r)


def _render():
    root = make_root()
    r = share.share_check(TEMPLATE, root=root, runner=FakeGit(listed={}))
    lines = share.render(r)
    assert lines[0] == "VIEW blocked", lines
    assert "USE blocked" in lines and lines.index("USE blocked") > lines.index("  D1: %s"
                                                                             % by_tag(r, "D1")[0]["what"]), lines
    assert "  A5: %s" % by_tag(r, "A5")[0]["what"] in lines, lines
    steps = lines[lines.index("fix steps:") + 1:]
    lab = [s for s in steps if "(owner fixq) — D1" in s]
    assert len(lab) == 1 and lab[0].startswith("  "), steps
    assert [s for s in steps if s.endswith("(owner fixq) — A5")], steps
    assert not [s for s in steps if s.endswith("— A6")], steps  # PF-9c: no longer a blocker
    assert "note: %s" % (share.NOTE_BUTTONS % 1) in lines, lines
    assert share.SNAPSHOT in lines and "snapshot only" in share.SNAPSHOT, lines
    assert lines.index(share.SNAPSHOT) < lines.index("note: %s" % share.NOTE_NO_SCAN), lines
    assert "note: %s" % share.NOTE_KEYS in lines, lines


# --- template mode -----------------------------------------------------------

def _template_all_clear():
    root = make_root(only(DOC, *CLEAR))
    draft = read(os.path.join(root, DRAFT))
    git = FakeGit(listed=RUN_LISTED)
    out = share.share_template(DRAFT, person="fixp", root=root, runner=git, scan=lambda t: [])
    assert out["result"] == "template" and out["written"] == [TEMPLATE], out
    assert out["check"]["use"] == "pass" and out["shared"] == "shared", out
    want = PAGE.replace("<p id=\"hello\">Hello</p>", "<p id=\"hello\">Hello from fixp</p>")
    got = read(os.path.join(root, TEMPLATE))
    assert got == want, "template form differs"
    assert "data-personal-view" not in got and PREFS not in got and PREFS in draft
    assert read(os.path.join(root, DRAFT)) == draft, "the draft is untouched"
    acts = [c for c in git.calls if c[1] in ("add", "commit", "push")]
    assert acts == [["git", "add", "--", TEMPLATE],
                    ["git", "commit", "-m", "page: template sharefam from fixp", "--", TEMPLATE],
                    ["git", "push"]], acts
    assert_safe(git.calls)


def _template_no_share():
    root = make_root(only(DOC, *CLEAR))
    git = FakeGit(listed=RUN_LISTED)
    out = share.share_template(DRAFT, person="fixp", root=root, runner=git, scan=lambda t: [],
                               share=False)
    assert out["result"] == "template" and out["shared"] == "not shared", out
    assert set(git.words()) <= {"ls-files", "hash-object"}, git.calls


def _unchanged(doc, fn, **kw):
    root = make_root(doc, **kw)
    before = tree_hashes(root)
    git = FakeGit(listed=RUN_LISTED)
    out = fn(root, git)
    assert tree_hashes(root) == before, "the temp root changed"
    assert out["written"] == [] and set(git.words()) <= {"ls-files", "hash-object"}, (out, git.calls)
    return out, git


def _written(doc, scan):
    root = make_root(doc)
    out = share.share_template(DRAFT, person="fixp", root=root, runner=FakeGit(listed=RUN_LISTED),
                               scan=scan, share=False)
    assert out["result"] == "template" and out["written"] == [TEMPLATE], out
    assert "data-personal-view" not in read(os.path.join(root, TEMPLATE)), "template form"
    return out


def _template_component_door():
    # PF-9c (share warns): a components/ door goes through the person's own
    # Claude, so it no longer stops the template
    out = _written(only(DOC, *(CLEAR + (6,))), lambda t: [])
    assert out["check"]["view"] == "pass" and out["check"]["use"] == "pass", out["check"]
    text = "\n".join(out["lines"])
    assert "A6:" not in text and "note: %s" % (share.NOTE_BUTTONS % 1) in out["lines"], text


def _template_blocked():
    # PF-9c (share warns): a non-hard finding (after-card, no scan) is a warning
    # and the template is written; a lab door still blocks with nothing written
    out = _written(only(DOC, *(CLEAR + (3,))), lambda t: [])
    assert out["check"]["view"] == "blocked", out
    assert [l for l in out["lines"] if l.startswith("  M3: ")], out["lines"]
    out = _written(only(DOC, *CLEAR), None)
    assert out["check"]["view"] == "not proven", out
    assert "note: %s" % share.NOTE_NO_SCAN in out["lines"], out["lines"]
    out, _ = _unchanged(only(DOC, *(CLEAR + (5,))), lambda root, git: share.share_template(
        DRAFT, person="fixp", root=root, runner=git, scan=lambda t: []))
    assert out["result"] == "blocked" and out["check"]["use"] == "blocked", out
    assert "  A5: %s" % by_tag(out["check"], "A5")[0]["what"] in out["lines"], out["lines"]


def _template_refusals():
    def run(person="fixp", page=DRAFT):
        return lambda root, git: share.share_template(page, person=person, root=root,
                                                      runner=git, scan=lambda t: [])
    clear = only(DOC, *CLEAR)
    no_owner = copy.deepcopy(clear)
    del no_owner["owner"]
    out, _ = _unchanged(no_owner, run())
    assert out["result"] == "refused" and "has no owner" in out["lines"][0], out
    assert "owner only" in out["lines"][0] and out["check"] is not None, out
    other = dict(clear, owner="fixo")
    out, _ = _unchanged(other, run())
    assert out["result"] == "refused" and out["lines"] == [
        "refused: only fixo shares sharefam as its template"], out
    for page, why in (("platform/views/viewers/fixz/drafts/sharefam--mine.html", "fixz's draft"),
                      (TEMPLATE, "family template"),
                      ("platform/views/viewers/fixp/sharefam.html", "live page")):
        out, git = _unchanged(clear, run(page=page), draft=page if page != TEMPLATE else DRAFT)
        assert out["result"] == "refused" and why in out["lines"][0], out
        assert git.calls == [] and out["check"] is None, git.calls
    stale = draft_of(PAGE, "0" * 40)
    out, _ = _unchanged(clear, run(), page_text=stale)
    assert out["result"] == "refused" and "the template changed since this draft was cut" \
        in out["lines"][0] and "base 0000000 → now " in out["lines"][0], out
    edited = draft_of(PAGE, blob_id(PAGE.encode("utf-8"))).replace(
        "/* the overlay */", "/* mine */")
    out, _ = _unchanged(clear, run(), page_text=edited)
    assert out["result"] == "blocked", out
    assert [b for b in out["check"]["blockers"] if b["level"] == "VIEW" and b["tag"] == "page"
            and b["what"] == "the overlay block was edited; it is component-owned"], out["check"]
    assert "  page: the overlay block was edited; it is component-owned" in out["lines"], out


def _no_person():
    git = FakeGit()
    out = share.share_template(DRAFT, root=make_root(), runner=git)
    assert out["result"] == "refused" and "no person" in out["lines"][0], out
    assert git.calls == [["git", "config", "user.email"]], git.calls


# --- the real families, read-only ---------------------------------------------

REAL = "platform/views/viewers/_templates/%s.html"


def _expect(result, t, level, *words, owner=None):
    """True when feature `t` has a `level` blocker naming `words`; a feature
    that moved on prints a note instead of failing."""
    hits = [b for b in by_tag(result, t) if b["level"] == level
            and all(w in b["what"] or w in b["fix"] for w in words)
            and (owner is None or b["owner"] == owner)]
    if not hits:
        print("      note: %s %s moved on (%s); not asserted" % (result["family"], t,
                                                                  by_tag(result, t)))
    return bool(hits)


def _real_families():
    seen = {}
    for family in ("outlier-demo", "emails", "run-detail"):
        git = FakeGit(listed=None)
        r = share.share_check(REAL % family, root=ROOT, runner=git)
        assert r["refused"] is None, r
        assert r["view"] != "pass" and r["use"] != "pass", (family, r["view"], r["use"])
        assert set(git.words()) <= {"ls-files"}, git.calls
        seen[family] = r
    od = seen["outlier-demo"]
    assert od["view"] == "blocked" and od["use"] == "blocked", od
    _expect(od, "M12", "VIEW", "after-card")
    _expect(od, "R18", "VIEW", "lab code", owner="owner")
    _expect(od, "D3", "VIEW", "lab code", owner="owner")
    if _expect(od, "A14", "USE", "lab/owner/suite/suite_serve.py", owner="owner"):
        assert by_tag(od, "A14")[0]["hard"] is True, by_tag(od, "A14")
    ed = seen["emails"]
    assert ed["use"] == "blocked", ed
    # PF-9c (share warns): a components/ door is no blocker on any family
    for r in seen.values():
        assert not [b for b in r["blockers"] if "act(n)" in b["what"]], r["blockers"]


# --- the CLI ------------------------------------------------------------------

def _cli():
    calls = []
    real_git = features.run_git
    features.run_git = lambda argv, cwd: calls.append(argv) or (1, "", "no git in tests")
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = features.main(["share", REAL % "run-detail", "--person", "developer"])
    finally:
        features.run_git = real_git
    assert code == 2 and "refused" in out.getvalue() and calls == [], (code, out.getvalue(), calls)
    assert "features.py share <draft page>" in features.USAGE
    # PF-9c (share warns): no scan is a warning, not a block; a lab door blocks
    root = make_root(only(DOC, *(CLEAR + (5,))))
    before = tree_hashes(root)
    git = FakeGit(listed=RUN_LISTED)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = share.main([DRAFT, "--person", "fixp", "--no-share"], root=root, runner=git)
    assert code == 2 and "blocked" in out.getvalue(), (code, out.getvalue())
    assert share.NOTE_NO_SCAN in out.getvalue() and tree_hashes(root) == before, out.getvalue()
    root = make_root(only(DOC, *CLEAR))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = share.main([DRAFT, "--person", "fixp", "--no-share"], root=root, runner=git)
    assert code == 0 and share.NOTE_NO_SCAN in out.getvalue(), (code, out.getvalue())
    root = make_root(only(DOC, *CLEAR))
    with contextlib.redirect_stdout(io.StringIO()):
        code = share.main([DRAFT, "--person", "fixp", "--no-share"], root=root, runner=git,
                          scan=lambda t: [])
    assert code == 0, code
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        assert share.main(["--bogus"], root=root, runner=git) == 2
    write(os.path.join(root, FAMILY), "{not json")
    with contextlib.redirect_stdout(io.StringIO()):
        assert share.main([DRAFT, "--person", "fixp"], root=root, runner=git) == 3


check("the fixture family validates, but for feature 1's content finding", _fixture_valid)
check("classes: lab data → VIEW blocker owner fixq + note for /api/x; lab page rule → note; "
      "after-card → blocker with its note; run file not in git → blocker (pattern "
      "runs/fix/*.json); lab door → hard USE blocker, component door → buttons note; "
      "not-built and off-page → not checked", _classes)
check("a run file ls-files lists is reachable", _listed_run_is_reachable)
check("a format finding blocks VIEW and stops the rest, no git", _format_finding_stops)
check("share_check refuses a missing or unreadable list and a page of no family",
      _check_refusals)
check("verdicts: scan None → not proven with the system-integration note; [] → pass; "
      "a finding → VIEW blocked with page: <finding>", _verdicts)
check("render: verdicts with blockers, fix steps by (fix, owner), snapshot, notes", _render)
check("template mode, all clear: the template form written; add, commit -- path, push",
      _template_all_clear)
check("template mode --no-share runs no add, commit or push", _template_no_share)
check("template mode: a component door → template written, buttons note",
      _template_component_door)
check("template mode: after-card or scan None → written with warnings; a lab door → "
      "blocked, nothing written", _template_blocked)
check("template mode refuses, nothing written: no owner, another owner, another person's "
      "draft, a template, a live page, a stale stamp; an edited overlay blocks",
      _template_refusals)
check("template mode refuses with no person", _no_person)
check("the real families: outlier-demo and emails blocked with the named numbers; "
      "none passes VIEW or USE (snapshots only)", _real_families)
check("CLI: features.py share on a template exits 2 refused with no git; share.main exit "
      "codes 2 (lab door), 0 (no scan), 0, 2 and 3", _cli)


def _folder_source_pattern():
    """A folder source (ending in /) is checked as the files under it: real git
    in a temp repo lists a tracked file under <brand>-journey/ (the D10 false
    alarm, 2026-11-25), and an empty folder pattern still finds nothing."""
    import subprocess
    assert share._pattern("platform/data/metrics/<brand>-journey/") == "platform/data/metrics/*-journey/*"
    assert share._pattern("runs/fix/<x>.json") == "runs/fix/*.json"
    tmp = tempfile.mkdtemp(prefix="pf9-folder-")
    TEMPS.append(tmp)
    os.makedirs(os.path.join(tmp, "data", "a-journey"))
    write(os.path.join(tmp, "data", "a-journey", "data.json"), "{}")
    git = lambda *a: subprocess.run(["git", "-C", tmp] + list(a), capture_output=True, text=True)
    git("init", "-q"); git("add", "data/a-journey/data.json")
    hit = git("ls-files", "--", share._pattern("data/<brand>-journey/")).stdout.split()
    assert hit == ["data/a-journey/data.json"], hit
    miss = git("ls-files", "--", share._pattern("data/<brand>-other/")).stdout.split()
    assert miss == [], miss


check("a folder source (ending in /) matches the tracked files under it", _folder_source_pattern)


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
