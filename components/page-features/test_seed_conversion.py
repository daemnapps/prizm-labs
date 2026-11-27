#!/usr/bin/env python3
"""PF-1 (page-features skeleton): from_seed() turns the committed run-detail
seed into exactly the committed example, in the v1 contract, without touching
the seed.

    python3 test_seed_conversion.py

Stdlib only, no network; reads the seed and the example, writes nothing. Runs
under python3 and /usr/bin/python3 (3.9). One PASS/FAIL line per check, then
"N/M passed"; exit 1 on any FAIL.
"""
import copy, json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import features  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
SEED = os.path.join(ROOT, "new-workflow-design", "builds", "page-features", "seed",
                    "features.json")
EXAMPLE = os.path.join(HERE, "examples", "mini-runs-run-detail.features.json")

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


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


SEED_BYTES = read_bytes(SEED)
SEED_DOC = json.loads(SEED_BYTES.decode("utf-8"))
SEED_BEFORE = copy.deepcopy(SEED_DOC)
DOC = features.from_seed(SEED_DOC)


def strings_in(value):
    """Every key and string value anywhere in `value`."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            for s in strings_in(v):
                yield s
    elif isinstance(value, list):
        for v in value:
            for s in strings_in(v):
                yield s
    elif isinstance(value, str):
        yield value


def _bytes_equal():
    want = read_bytes(EXAMPLE)
    got = json.dumps(DOC, indent=1, ensure_ascii=False).encode("utf-8") + b"\n"
    assert got == features.dumps(DOC).encode("utf-8"), "dumps() is not the CLI's form"
    assert got == want, "from_seed differs from the committed example (%d vs %d bytes)" % (
        len(got), len(want))


def _count():
    assert len(DOC["features"]) == 37, len(DOC["features"])


def _states():
    got = Counter(e["state"] for e in DOC["features"])
    want = {"wired": 26, "after-card": 4, "not-built": 7}
    assert dict(got) == want, dict(got)


def _kinds():
    got = Counter(e["kind"] for e in DOC["features"])
    want = {"data": 21, "rule": 7, "media": 3, "layout": 5, "action": 1}
    assert dict(got) == want, dict(got)


def _letters():
    got = [DOC["kinds"][k]["letter"] for k in DOC["kinds"]]
    assert got == ["D", "R", "M", "L", "A"], got
    assert list(DOC["kinds"]) == ["data", "rule", "media", "layout", "action"], list(DOC["kinds"])


def _status_draft():
    assert DOC["status"] == "draft", DOC["status"]
    bad = [e["n"] for e in DOC["features"] if e.get("status") != "draft"]
    assert not bad, "entries not draft: %r" % bad


def _no_seed_words():
    left = [s for s in strings_in(DOC) if s in ("after card", "not built")]
    assert not left, "seed state words left: %r" % left
    assert "status_words" not in DOC
    assert list(DOC["state_words"]) == features.STATE_WORDS, list(DOC["state_words"])


def _order():
    assert list(DOC) == ["title", "schema", "status", "checked_against", "versions",
                         "state_words", "kinds", "features"], list(DOC)
    for e in DOC["features"]:
        assert list(e) == ["n", "name", "kind", "state", "status", "place", "source",
                           "note", "where"], "feature %s: %r" % (e.get("n"), list(e))


def _validates():
    got = features.validate(DOC)
    assert got == [], got


def _no_mutation():
    assert SEED_DOC == SEED_BEFORE, "from_seed changed the seed it was given"
    assert read_bytes(SEED) == SEED_BYTES, "the seed file changed"


check("from_seed(seed) equals the committed example byte for byte", _bytes_equal)
check("37 features", _count)
check("states 26 wired / 4 after-card / 7 not-built", _states)
check("kinds 21 data / 7 rule / 3 media / 5 layout / 1 action", _kinds)
check("kinds letters D R M L A, in that order", _letters)
check("the file and every entry carry status draft", _status_draft)
check('no "after card" or "not built" left anywhere', _no_seed_words)
check("keys kept in order, state and status where the seed had status", _order)
check("validate() returns []", _validates)
check("the seed is unchanged after the call (no mutation)", _no_mutation)

passed = sum(RESULTS)
print("%d/%d passed" % (passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
