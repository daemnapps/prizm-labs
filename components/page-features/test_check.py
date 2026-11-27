#!/usr/bin/env python3
"""PF-3 (feature check): check.py names every page miss and every dead field,
lists rule features apart, and never calls a non-JSON source dead.

    python3 test_check.py

Stdlib only, no network. Fixtures under test_check_fixtures/ (a tiny root
with a fake team/id-tags.json and data files, passed with --root); variants
of a fixture features file go to temp files only. The last checks run against
the REAL repo and its two run-detail mocks. One PASS/FAIL line per check,
then "N/M passed"; exit 1 on any FAIL.
"""
import copy, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(HERE), "run-kit"))

from run_kit import paths  # noqa: E402

TOOL = os.path.join(HERE, "check.py")
FIX = os.path.join(HERE, "test_check_fixtures")
ROOT = os.path.join(FIX, "root")
CLEAN_PAGE = os.path.join(FIX, "clean.html")
CLEAN = os.path.join(FIX, "clean.features.json")
EXTRA_PAGE = os.path.join(FIX, "extra.html")
VERSIONS_PAGE = os.path.join(FIX, "versions.html")
VERSIONS = os.path.join(FIX, "versions.features.json")
SECTIONS = ["PAGE", "DEAD", "MISSING", "UNCHECKABLE", "LOCATOR NOT CHECKED",
            "NOT ON THIS VERSION", "RULES", "AFTER-CARD", "NOT-BUILT"]

TMP = tempfile.mkdtemp(prefix="pf3-check-")
RESULTS = []
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


def run(page, features_path, *extra, **kw):
    root = kw.get("root", ROOT)
    argv = [sys.executable, TOOL, page, "--features", features_path]
    if root is not None:
        argv += ["--root", root]
    proc = subprocess.run(argv + list(extra), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=50,
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return proc.returncode, proc.stdout.decode("utf-8")


def sections(out):
    """{section: [item lines]} — "(none)" is not an item."""
    found, current = {}, None
    for line in out.splitlines():
        head = line.split(" — ", 1)[0]
        if not line.startswith("  ") and head in SECTIONS:
            current = head
            found[current] = []
        elif current and line.startswith("  ") and line.strip() != "(none)":
            found[current].append(line.strip())
        elif not line.startswith("  "):
            current = None
    return found


def variant(path, change):
    """A temp copy of a fixture features file with `change(doc)` applied."""
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    doc = copy.deepcopy(doc)
    change(doc)
    out = os.path.join(TMP, "v%d.features.json" % len(os.listdir(TMP)))
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, ensure_ascii=False)
    return out


def feature(doc, n):
    return [f for f in doc["features"] if f["n"] == n][0]


def set_field(n, field, file=None):
    def change(doc):
        feature(doc, n)["source"]["field"] = field
        if file:
            feature(doc, n)["source"]["file"] = file
    return change


def expect(code, out, want):
    assert code == want, "exit %d, want %d:\n%s" % (code, want, out)


# 1 — a clean tagged page
def t_clean():
    code, out = run(CLEAN_PAGE, CLEAN)
    expect(code, out, 0)
    s = sections(out)
    for name in ("PAGE", "DEAD", "MISSING", "UNCHECKABLE"):
        assert s[name] == [], "%s not empty: %s" % (name, s[name])
    assert "8 on page · 0 dead · 0 uncheckable · 1 rules · exit 0" in out, out
    assert s["AFTER-CARD"] == ["D7 Waits on a card: card ZZ-1 (fixture card)"], s["AFTER-CARD"]
    assert s["NOT-BUILT"] == ["D8 Not built"], s["NOT-BUILT"]


# 2 — a renamed data field
def t_renamed():
    code, out = run(CLEAN_PAGE, variant(CLEAN, set_field(1, "as_at")))
    expect(code, out, 1)
    dead = sections(out)["DEAD"]
    assert dead == ["D1: data/index.json has no field as_at"], dead


# 3 — a page number missing from features.json, and the reverse
def t_numbers():
    code, out = run(EXTRA_PAGE, CLEAN)
    expect(code, out, 1)
    page = sections(out)["PAGE"]
    assert len(page) == 2, page
    assert any("data-feature=99" in l and "no feature 99" in l for l in page), page
    assert any(l.startswith("D2 Late field: not on the page") for l in page), page


# 4 — an empty array under x[]
def t_empty_array():
    code, out = run(CLEAN_PAGE, variant(CLEAN, set_field(5, "empty[].name")))
    expect(code, out, 1)
    dead = sections(out)["DEAD"]
    assert len(dead) == 1 and dead[0].startswith("D5:") and "unproven" in dead[0] \
        and "empty[].name" in dead[0], dead


# 5 — a JSON Schema fixture resolves through properties / items
def t_schema():
    code, out = run(CLEAN_PAGE, CLEAN)
    expect(code, out, 0)
    assert not any("D3" in l for l in sections(out)["DEAD"]), out
    code, out = run(CLEAN_PAGE, variant(CLEAN, set_field(3, "box.size, rows[].nope, box.width")))
    expect(code, out, 1)
    dead = sections(out)["DEAD"]
    assert dead == ["D3: data/schema.json has no field rows[].nope",
                    "D3: data/schema.json has no field box.width"], dead


# 6 — a <run> placeholder, the field only in the SECOND file
def t_placeholder():
    with open(os.path.join(ROOT, "data", "runs", "r1.json"), encoding="utf-8") as h:
        assert "late" not in json.load(h), "fixture r1.json must not carry `late`"
    code, out = run(CLEAN_PAGE, CLEAN)
    expect(code, out, 0)
    assert not any("D2" in l for l in sections(out)["DEAD"]), out
    code, out = run(CLEAN_PAGE, variant(CLEAN, set_field(2, "never")))
    expect(code, out, 1)
    assert sections(out)["DEAD"] == ["D2: data/runs/<run>.json has no field never"], out


# 7 — a rule whose source field does not exist: RULES, never DEAD
def t_rule():
    code, out = run(CLEAN_PAGE, CLEAN)
    expect(code, out, 0)
    s = sections(out)
    assert any(l.startswith("R4 A rule on a missing field: rule in the page — data/index.json")
               for l in s["RULES"]), s["RULES"]
    assert any(l.startswith("a rule lives in the page") for l in s["RULES"]), s["RULES"]
    assert not any("R4" in l for l in s["DEAD"]), s["DEAD"]


# 8 — a .md source: UNCHECKABLE, never DEAD; --strict exits 1
def t_markdown():
    path = variant(CLEAN, set_field(5, "failed checks · items[].name",
                                    "data/notes.md · data/index.json"))
    code, out = run(CLEAN_PAGE, path)
    expect(code, out, 0)
    s = sections(out)
    assert s["UNCHECKABLE"] == ["D5: data/notes.md is not JSON (v1 reads JSON only)"], s
    assert s["DEAD"] == [], s["DEAD"]
    code, out = run(CLEAN_PAGE, path, "--strict")
    expect(code, out, 1)
    # the JSON half of the pair is still checked
    code, out = run(CLEAN_PAGE, variant(CLEAN, set_field(5, "failed checks · items[].gone",
                                                         "data/notes.md · data/index.json")))
    expect(code, out, 1)
    assert sections(out)["DEAD"] == ["D5: data/index.json has no field items[].gone"], out


# 9 — unparsed field text on a JSON file
def t_unparsed():
    code, out = run(CLEAN_PAGE, variant(CLEAN, set_field(1, "failed checks")))
    expect(code, out, 0)
    s = sections(out)
    assert len(s["UNCHECKABLE"]) == 1 and s["UNCHECKABLE"][0].startswith("D1:") \
        and "unparsed field text" in s["UNCHECKABLE"][0], s["UNCHECKABLE"]
    assert s["DEAD"] == [], s["DEAD"]


# 10 — invalid features → 2; a missing page → 3; a glob matching nothing → 3
def t_exits():
    def bad(doc):
        feature(doc, 1)["kind"] = "bogus"
    code, out = run(CLEAN_PAGE, variant(CLEAN, bad))
    expect(code, out, 2)
    assert "INVALID" in out and "feature 1" in out, out
    code, out = run(os.path.join(FIX, "no-such-page.html"), CLEAN)
    expect(code, out, 3)
    assert "MISSING" in out and "no-such-page.html" in out, out
    code, out = run(CLEAN_PAGE, variant(CLEAN, set_field(2, "late", "data/none/<run>.json")))
    expect(code, out, 3)
    assert sections(out)["MISSING"] == [
        "D2: data/none/<run>.json matches no file under %s" % ROOT], out


# 11 — versions
def t_versions():
    code, out = run(VERSIONS_PAGE, VERSIONS)
    expect(code, out, 2)
    assert "A, B" in out, out
    code, out = run(VERSIONS_PAGE, VERSIONS, "--version", "C")
    expect(code, out, 2)
    code, out = run(VERSIONS_PAGE, VERSIONS, "--version", "A")
    expect(code, out, 0)
    s = sections(out)
    assert s["PAGE"] == [], s["PAGE"]
    assert s["NOT ON THIS VERSION"] == ["D2 Absent here: declared absent from version A"], s
    assert "L3 Built by script: version A selector '.built' — built by script" \
        in s["LOCATOR NOT CHECKED"], s["LOCATOR NOT CHECKED"]
    assert any(l.startswith("R4") and "too complex" in l for l in s["LOCATOR NOT CHECKED"]), s
    assert "3 on page" in out, out
    code, out = run(VERSIONS_PAGE, VERSIONS, "--version", "B")
    expect(code, out, 0)
    assert any(l.startswith("R4") and "too complex" in l      # a text filter
               for l in sections(out)["LOCATOR NOT CHECKED"]), out

    def gone(doc):
        feature(doc, 6)["where"]["A"]["sel"] = ".gone"
    code, out = run(VERSIONS_PAGE, variant(VERSIONS, gone), "--version", "A")
    expect(code, out, 1)
    assert sections(out)["PAGE"] == [
        "L6 A class selector: version A selector '.gone' found nowhere on the page"], out


# 12 — the REAL repo, both run-detail mocks
REAL = str(paths.repo(HERE))
EXAMPLE = os.path.join(HERE, "examples", "mini-runs-run-detail.features.json")
MOCKS = {
    "A": "new-workflow-design/builds/design-bench/runs/mini-runs-run-detail-merge-1020b/out/claude-fable-5-1.rebuilt.html",
    "B": "new-workflow-design/builds/design-bench/runs/mini-runs-run-detail-merge-1020/out/gpt-6-astra.html",
}
RULE_TAGS = ["R7", "R8", "R9", "R10", "R17", "R19", "R25"]


def real(version, root):
    def t():
        code, out = run(os.path.join(REAL, MOCKS[version]), EXAMPLE,
                        "--version", version, root=root)
        expect(code, out, 0)
        s = sections(out)
        assert s["DEAD"] == [], s["DEAD"]
        assert s["MISSING"] == [], s["MISSING"]
        assert len(s["UNCHECKABLE"]) == 1, s["UNCHECKABLE"]
        assert s["UNCHECKABLE"][0].startswith("D24:") and "AUDIT-HOLD.md" in s["UNCHECKABLE"][0], \
            s["UNCHECKABLE"]
        rules = [l.split(" ", 1)[0] for l in s["RULES"] if l[:1] == "R"]
        assert rules == RULE_TAGS, rules
    return t


check("1 clean tagged page + features → exit 0", t_clean)
check("2 renamed data field → exit 1, DEAD names tag, file and field", t_renamed)
check("3 page number not in features.json, and a feature not on the page → exit 1, both named", t_numbers)
check("4 empty array under x[] → exit 1, unproven", t_empty_array)
check("5 JSON Schema field resolves through properties / items", t_schema)
check("6 <run> placeholder resolves when only the second file carries the field", t_placeholder)
check("7 rule on a missing field → RULES, never DEAD, exit 0", t_rule)
check("8 .md source → UNCHECKABLE, never DEAD, exit 0; --strict → 1", t_markdown)
check("9 unparsed field text → UNCHECKABLE, exit 0", t_unparsed)
check("10 invalid features → 2; missing page → 3; glob matching nothing → 3", t_exits)
check("11 versions: none chosen → 2; null → NOT ON THIS VERSION; script-only → not checked; nowhere → miss", t_versions)
check("12a REAL repo, version A mock, default --root → exit 0, only D24 uncheckable, 7 rules", real("A", None))
check("12b REAL repo, version B mock, --root repo() → exit 0, only D24 uncheckable, 7 rules", real("B", REAL))

shutil.rmtree(TMP, ignore_errors=True)
print("%d/%d passed" % (sum(RESULTS), len(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
