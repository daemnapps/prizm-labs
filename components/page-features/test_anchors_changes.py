#!/usr/bin/env python3
"""PF-1b (feature anchors): the v1.1 contract — `schema_minor`, a feature's
`anchor` and the page's `changes` log — validates, refuses each defect by
name, and leaves every v1 file valid.

    python3 test_anchors_changes.py

Stdlib only, no network; reads the two examples and the schema, writes
nothing. Runs under python3 and /usr/bin/python3 (3.9). One PASS/FAIL line per
check, then "N/M passed"; exit 1 on any FAIL.
"""
import copy, json, os, subprocess, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import features  # noqa: E402

V1 = os.path.join(HERE, "examples", "mini-runs-run-detail.features.json")
V1_1 = os.path.join(HERE, "examples", "mini-runs-run-detail.v1-1.features.json")
SCHEMA = os.path.join(HERE, "features.schema.json")
CHROME = [38, 39, 40, 41, 42]

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


DOC_V1 = features.load(V1)
DOC = features.load(V1_1)


def v11():
    return copy.deepcopy(DOC)


def feature(doc, n):
    return [e for e in doc["features"] if e["n"] == n][0]


def change(**over):
    out = {"n": 3, "said": "make the back link bigger", "at": "2026-10-21T02:40:00Z",
           "by": "viewer-7f3a", "route": "claude-code"}
    out.update(over)
    return out


def one_finding(doc, must_contain):
    got = features.validate(doc)
    assert len(got) == 1, "want exactly one finding, got %d: %r" % (len(got), got)
    assert must_contain in got[0], "finding %r does not say %r" % (got[0], must_contain)


# ------------------------------------------------------ the v1.1 example


def _example_valid():
    got = features.validate(DOC)
    assert got == [], got
    assert DOC["schema"] == 1 and DOC["schema_minor"] == 1
    assert len(DOC["features"]) == 42, len(DOC["features"])
    states = dict(Counter(e["state"] for e in DOC["features"]))
    assert states == {"wired": 31, "after-card": 4, "not-built": 7}, states
    layout = sum(1 for e in DOC["features"] if e["kind"] == "layout")
    assert layout == 10, layout
    for e in DOC["features"]:
        if e["state"] == "wired":
            assert e.get("anchor") == str(e["n"]), "feature %d anchor %r" % (e["n"], e.get("anchor"))
    for n in CHROME:
        e = feature(DOC, n)
        assert (e["kind"], e["state"], e["status"]) == ("layout", "wired", "draft"), e
    assert DOC["changes"] == []
    assert list(DOC)[:3] == ["title", "schema", "schema_minor"], list(DOC)
    assert list(DOC)[-1] == "changes", list(DOC)


def _no_change_box():
    files = [((e.get("source") or {}).get("file"), (e.get("source") or {}).get("field"))
             for e in DOC["features"]]
    assert ("components/page-features/marks.js", "change-box") not in files
    assert ("components/page-features/overlay.js", "popover") in files


def _written_by_dumps():
    with open(V1_1, encoding="utf-8") as f:
        text = f.read()
    assert text == features.dumps(DOC), "the v1.1 example is not features.dumps() of itself"


def _strip_equals_v1():
    doc = v11()
    del doc["schema_minor"]
    del doc["changes"]
    doc["features"] = [e for e in doc["features"] if e["n"] not in CHROME]
    for e in doc["features"]:
        e.pop("anchor", None)
    assert doc == DOC_V1, "the v1.1 example drifted from the v1 example"
    assert list(doc) == list(DOC_V1)
    for a, b in zip(doc["features"], DOC_V1["features"]):
        assert list(a) == list(b), "feature %d key order" % a["n"]


# ------------------------------------------------------ v1 still validates


def _v1_valid():
    assert "schema_minor" not in DOC_V1
    assert not any("anchor" in e for e in DOC_V1["features"])
    got = features.validate(DOC_V1)
    assert got == [], got
    doc = copy.deepcopy(DOC_V1)
    feature(doc, 3)["anchor"] = "3"
    got = features.validate(doc)
    assert got == [], got


def _v1_anchor_still_checked():
    doc = copy.deepcopy(DOC_V1)
    feature(doc, 3)["anchor"] = "4"
    one_finding(doc, "feature 3: anchor '4' is not '3'")


# ------------------------------------------------------ one named finding each


def _missing_anchor():
    doc = v11()
    del feature(doc, 3)["anchor"]
    one_finding(doc, "feature 3: a wired feature needs an anchor in v1.1")


def _not_built_needs_no_anchor():
    doc = v11()
    e = feature(doc, 12)
    assert e["state"] == "not-built" and "anchor" not in e
    assert features.validate(doc) == []


def _wrong_anchor():
    doc = v11()
    feature(doc, 3)["anchor"] = "4"
    one_finding(doc, "feature 3: anchor '4' is not '3' (the data-feature value is the feature's number)")


def _int_anchor():
    doc = v11()
    feature(doc, 3)["anchor"] = 3
    one_finding(doc, "feature 3: anchor is not a string")


def _schema_minor_2():
    # PF-1c (plain-words changes): 2 is v1.2 now, so the v1.1 example opts
    # in cleanly and the minor past the newest is the one refused by name.
    doc = v11()
    doc["schema_minor"] = 2
    assert features.validate(doc) == [], features.validate(doc)
    doc["schema_minor"] = features.SCHEMA_MINOR + 1
    one_finding(doc, "file: schema_minor 3 is not 0, 1 or 2")


def _schema_minor_not_int():
    for bad in ("1", True, 1.0):
        doc = v11()
        doc["schema_minor"] = bad
        one_finding(doc, "file: schema_minor")


def _change_unknown_n():
    doc = v11()
    doc["changes"] = [change(), change(n=99)]
    one_finding(doc, "changes 2: n 99 is not a feature number")


def _change_route_email():
    doc = v11()
    doc["changes"] = [change(route="email")]
    one_finding(doc, "changes 1: route 'email' is not one of claude-code | note")


def _change_route_box():
    doc = v11()
    doc["changes"] = [change(route="box")]
    one_finding(doc, "changes 1: route 'box' is not one of")


def _change_at():
    doc = v11()
    doc["changes"] = [change(at="2026-10-21 02:40")]
    one_finding(doc, "changes 1: at '2026-10-21 02:40' is not a UTC time")


def _change_said_empty():
    doc = v11()
    doc["changes"] = [change(said="")]
    one_finding(doc, "changes 1: `said` is empty or not a string")


def _change_said_long():
    doc = v11()
    doc["changes"] = [change(said="x" * (features.SAID_MAX + 1))]
    one_finding(doc, "changes 1: said is 2001 characters, over 2000")


def _change_missing_by():
    doc = v11()
    c = change()
    del c["by"]
    doc["changes"] = [c]
    one_finding(doc, "changes 1: `by` is missing")


def _change_extra_key():
    doc = v11()
    doc["changes"] = [change(who="developer")]
    one_finding(doc, "changes 1: unknown key 'who'")


def _changes_object():
    doc = v11()
    doc["changes"] = {"n": 3}
    one_finding(doc, "file: `changes` is not a list")


# ------------------------------------------------------ valid changes, CLI, schema


def _two_changes_valid():
    doc = v11()
    doc["changes"] = [change(), change(n=38, said="the banner should be shorter",
                                       at="2026-10-21T02:41Z", route="note")]
    got = features.validate(doc)
    assert got == [], got


def _cli():
    proc = subprocess.run([sys.executable, os.path.join(HERE, "features.py"), V1_1],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    out = proc.stdout.decode("utf-8")
    assert proc.returncode == 0, (proc.returncode, out, proc.stderr.decode("utf-8"))
    assert "valid: 42 features (D 21 · R 7 · M 3 · L 10 · A 1)" in out, out


def _schema():
    with open(SCHEMA, encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["status"] == "draft", schema["status"]
    assert schema["properties"]["schema"]["const"] == 1
    assert schema["properties"]["schema_minor"]["enum"] == list(range(features.SCHEMA_MINOR + 1))
    assert schema["properties"]["changes"]["items"] == {"$ref": "#/$defs/change"}
    ch = schema["$defs"]["change"]
    assert ch["required"] == features.CHANGE_KEYS, ch["required"]
    assert list(ch["properties"]) == features.CHANGE_KEYS + features.CHANGE_OPTIONAL, list(ch["properties"])
    assert ch["additionalProperties"] is False
    assert ch["properties"]["route"]["enum"] == features.CHANGE_ROUTES
    assert ch["properties"]["at"]["pattern"] == features.AT_RE.pattern
    assert ch["properties"]["said"]["maxLength"] == features.SAID_MAX
    assert "anchor" in schema["$defs"]["feature"]["properties"]
    assert "v1_1" in schema


def _constants():
    assert features.SCHEMA_MINOR == 2
    assert features.CHANGE_ROUTES == ["claude-code", "note"]
    assert features.CHANGE_KEYS == ["n", "said", "at", "by", "route"]
    assert features.SAID_MAX == 2000


check("v1.1 example validates: 42 features, 31 wired / 4 after-card / 7 not-built, "
      "10 layout, every wired anchor == str(n)", _example_valid)
check("v1.1 example: the popover is numbered, no change box", _no_change_box)
check("v1.1 example is written by features.dumps()", _written_by_dumps)
check("v1.1 example minus schema_minor, changes, anchors and 38-42 equals the v1 example",
      _strip_equals_v1)
check("v1 example still validates, and so does a v1 copy with one anchor", _v1_valid)
check("an anchor in a v1 file is still checked", _v1_anchor_still_checked)
check("one finding: a wired feature with no anchor in v1.1", _missing_anchor)
check("a not-built feature needs no anchor in v1.1", _not_built_needs_no_anchor)
check("one finding: anchor '4' on feature 3", _wrong_anchor)
check("one finding: anchor given as the integer 3", _int_anchor)
check("schema_minor 2 (v1.2) validates; one finding: schema_minor 3", _schema_minor_2)
check("one finding: schema_minor '1', true, 1.0", _schema_minor_not_int)
check("one finding: a change with n 99", _change_unknown_n)
check("one finding: a change with route email", _change_route_email)
check("one finding: a change with route box (dropped at re-filing)", _change_route_box)
check("one finding: a change with at '2026-10-21 02:40'", _change_at)
check('one finding: a change with said ""', _change_said_empty)
check("one finding: a change with said over 2000 characters", _change_said_long)
check("one finding: a change missing by", _change_missing_by)
check("one finding: a change with an extra key who", _change_extra_key)
check("one finding: changes given as an object", _changes_object)
check("two valid changes (claude-code and note) validate", _two_changes_valid)
check("the CLI exits 0 on the v1.1 example", _cli)
check("the schema carries schema_minor, $defs.change and anchor, equal to the constants",
      _schema)
check("the v1.1 constants", _constants)

passed = sum(RESULTS)
print("%d/%d passed" % (passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
