#!/usr/bin/env python3
"""PF-1 (page-features skeleton): the validator says valid only when the file
meets the v1 contract, and names exactly one finding for each defect.

    python3 test_features.py

Stdlib only, no network; temp files only. Runs under python3 and
/usr/bin/python3 (3.9). One PASS/FAIL line per check, then "N/M passed";
exit 1 on any FAIL.
"""
import copy, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import features  # noqa: E402

TOOL = os.path.join(HERE, "features.py")
EXAMPLE = os.path.join(HERE, "examples", "mini-runs-run-detail.features.json")
SCHEMA = os.path.join(HERE, "features.schema.json")

BASE = features.load(EXAMPLE)
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


def doc():
    return copy.deepcopy(BASE)


def entry(d, n):
    for e in d["features"]:
        if e["n"] == n:
            return e
    raise KeyError(n)


def one_finding(mutate, prefix, says):
    """`mutate` the example; validate must give exactly one finding, starting
    with `prefix` (the entry it names) and containing `says`."""
    def run():
        d = doc()
        mutate(d)
        got = features.validate(d)
        assert len(got) == 1, "want 1 finding, got %d: %r" % (len(got), got)
        assert got[0].startswith(prefix), "%r does not name %r" % (got[0], prefix)
        assert says in got[0], "%r does not say %r" % (got[0], says)
    return run


def no_findings(d):
    got = features.validate(d)
    assert got == [], "want no findings, got %r" % got


def minimal(*entries):
    d = doc()
    d["features"] = list(entries)
    return d


def feat(n, kind, state, source=None):
    return {"n": n, "name": "Feature %d" % n, "kind": kind, "state": state,
            "status": "draft", "source": source}


def cli(*args):
    proc = subprocess.run([sys.executable, TOOL] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def write_temp(t, name, text):
    path = os.path.join(t, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


# ------------------------------------------------------------------ the example

check("the committed example validates with zero findings",
      lambda: no_findings(doc()))

# ------------------------------------------------------------- one finding each


def _dup(d):
    entry(d, 2)["n"] = 1


def _set(n, key, value):
    def m(d):
        entry(d, n)[key] = value
    return m


def _source_file(n, value):
    def m(d):
        entry(d, n)["source"]["file"] = value
    return m


def _del_status(d):
    del entry(d, 1)["status"]


def _where_c(d):
    entry(d, 1)["where"]["C"] = {"sel": ".x", "text": None}


def _no_rule(d):
    del d["kinds"]["rule"]


def _rule_letter(d):
    d["kinds"]["rule"]["letter"] = "X"


def _no_not_built(d):
    del d["state_words"]["not-built"]


def _colour(d):
    entry(d, 1)["colour"] = "red"


def _no_page(d):
    del d["versions"]


check("duplicate n", one_finding(_dup, "feature 1:", "used twice"))
check("n = 0", one_finding(_set(1, "n", 0), "entry 1:", "n 0"))
check('kind "ui"', one_finding(_set(1, "kind", "ui"), "feature 1:", "kind 'ui'"))
check('state "after card"', one_finding(_set(20, "state", "after card"),
                                        "feature 20:", "state 'after card'"))
check('"status": "wired"', one_finding(_set(1, "status", "wired"),
                                       "feature 1:", "a state word"))
check("an entry with no status", one_finding(_del_status, "feature 1:", "`status` is missing"))
check("a wired data entry with source null",
      one_finding(_set(2, "source", None), "feature 2:", "needs a source"))
check("an after-card media entry with source null",
      one_finding(_set(32, "source", None), "feature 32:", "needs a source"))
check('source.file "~/a.json"',
      one_finding(_source_file(2, "~/a.json"), "feature 2:", "starts with /"))
check('source.file "a.json · ../b.json"',
      one_finding(_source_file(2, "a.json · ../b.json"), "feature 2:", "contains .."))
check('a where label "C" not in versions',
      one_finding(_where_c, "feature 1:", "where 'C' is not a label"))
check('kinds without "rule"', one_finding(_no_rule, "file:", "missing 'rule'"))
check('kinds with rule\'s letter "X"', one_finding(_rule_letter, "file:", "letter 'X'"))
check('state_words without "not-built"',
      one_finding(_no_not_built, "file:", "missing 'not-built'"))
check('an unknown entry key "colour"', one_finding(_colour, "feature 1:", "unknown key 'colour'"))
check("a file with neither page nor versions",
      one_finding(_no_page, "file:", "neither `page` nor `versions`"))

# ---------------------------------------------------- valid with source null

check("a wired layout with source null is valid",
      lambda: no_findings(minimal(feat(1, "layout", "wired"))))
check("a wired action with source null is valid",
      lambda: no_findings(minimal(feat(1, "action", "wired"))))
check("a wired rule with source null is valid",
      lambda: no_findings(minimal(feat(1, "rule", "wired"))))
check("a not-built data entry with source null is valid",
      lambda: no_findings(minimal(feat(1, "data", "not-built"))))
check("all four together are valid",
      lambda: no_findings(minimal(feat(1, "layout", "wired"), feat(2, "action", "wired"),
                                  feat(3, "rule", "after-card"), feat(4, "data", "not-built"))))

# ----------------------------------------------------------------------- CLI


def _cli_valid():
    code, out = cli(EXAMPLE)
    assert code == 0, "exit %d: %s" % (code, out)
    assert "valid: 37 features (D 21 · R 7 · M 3 · L 5 · A 1)" in out, out


def _cli_invalid():
    d = doc()
    _dup(d)
    with tempfile.TemporaryDirectory() as t:
        path = write_temp(t, "bad.features.json", json.dumps(d, ensure_ascii=False))
        code, out = cli(path)
    assert code == 2, "exit %d: %s" % (code, out)
    assert "feature 1: n 1 is used twice" in out, "finding not printed: %s" % out


def _cli_missing():
    with tempfile.TemporaryDirectory() as t:
        code, out = cli(os.path.join(t, "absent.features.json"))
    assert code == 3, "exit %d: %s" % (code, out)
    assert "MISSING" in out, out


def _cli_not_json():
    with tempfile.TemporaryDirectory() as t:
        path = write_temp(t, "broken.features.json", "{ not json")
        code, out = cli(path)
    assert code == 3, "exit %d: %s" % (code, out)
    assert "not valid JSON" in out, out


check("CLI exits 0 on the example", _cli_valid)
check("CLI exits 2 on a bad file and prints the finding", _cli_invalid)
check("CLI exits 3 on a missing path", _cli_missing)
check("CLI exits 3 on a non-JSON file", _cli_not_json)

# ------------------------------------------------- schema words = constants


def _schema_words():
    with open(SCHEMA, encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["status"] == "draft", schema["status"]
    assert schema["status_words"] == features.STATUS_WORDS, schema["status_words"]
    assert schema["state_words"] == features.STATE_WORDS, schema["state_words"]
    assert list(schema["kinds"].items()) == list(features.KINDS.items()), schema["kinds"]
    props = schema["properties"]
    entry_props = schema["$defs"]["feature"]["properties"]
    assert props["status"]["enum"] == features.STATUS_WORDS
    assert entry_props["status"]["enum"] == features.STATUS_WORDS
    assert entry_props["state"]["enum"] == features.STATE_WORDS
    assert entry_props["kind"]["enum"] == list(features.KINDS)
    assert list(props["state_words"]["properties"]) == features.STATE_WORDS
    kinds = props["kinds"]["properties"]
    assert list(kinds) == list(features.KINDS), list(kinds)
    for name, letter in features.KINDS.items():
        got = kinds[name]["properties"]["letter"]["const"]
        assert got == letter, "%s letter %r, constant %r" % (name, got, letter)
    assert list(features.KINDS.values()) == ["D", "R", "M", "L", "A"]


check("the schema file's word lists equal the constants", _schema_words)

passed = sum(RESULTS)
print("%d/%d passed" % (passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
