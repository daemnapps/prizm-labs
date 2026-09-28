#!/usr/bin/env python3
"""The used lane and row ids — a fixture tree, no network, no real brand.

    python3 components/language-layer/tests/test_used_lane.py
"""
import json, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import engine as E  # noqa: E402

FAILS = []
def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        FAILS.append(what)

with tempfile.TemporaryDirectory() as t:
    root = Path(t)
    lang = root / "brands" / "fx" / "core-avatars" / "a1" / "language"
    (lang / "used").mkdir(parents=True)
    rows = [dict(id="r1", text="first line", use="hook", status="active"),
            dict(id="r2", text="second line", use="hook", status="active"),
            dict(id="r3", text="burned line", use="hook", status="burned"),
            dict(id="r4", text="retired line", use="hook", status="retired")]
    (lang / "leads.json").write_text(json.dumps({"schema": 1, "avatar": "a1", "funnel": "lead", "entries": rows}))
    before = (lang / "leads.json").read_text()
    (lang / "used" / "run1--h0.json").write_text(json.dumps({
        "schema": 1, "kind": "language-used", "asset": "run1--h0", "chain": "new-video",
        "used": [{"row_id": "r1", "text": "first line", "where": "4b", "how": "cited"}]}))

    loaded = E.load("fx", root=root)
    check(len(loaded) == 4, "the used lane is not read as bank rows")
    check(E.used_ids("fx", root=root) == {"r1"}, "used_ids finds the used row")
    got = {r["id"] for r in E.query(loaded)}
    check(got == {"r1", "r2"}, "burned and retired rows never come back")
    spent = E.used_ids("fx", root=root)
    check({r["id"] for r in E.query(loaded, used="no", spent=spent)} == {"r2"}, "used='no' holds back used rows")
    check({r["id"] for r in E.query(loaded, used="yes", spent=spent)} == {"r1"}, "used='yes' returns only used rows")
    out = E.for_stage("fx", "hooks", root=root, stage_use={"hooks": ["hook"]}, used="no")
    check("[r2]" in out and "[r1]" not in out, "for_stage(used='no') renders unused rows with their id")
    check("never used before" in out, "the header says used rows were held back")
    out2 = E.for_stage("fx", "hooks", root=root, stage_use={"hooks": ["hook"]})
    check("[r1]" in out2 and "[r2]" in out2, "without used=, nothing is held back")
    check((lang / "leads.json").read_text() == before, "no bank file was edited")

print(f"\n{'FAILED ' + str(len(FAILS)) if FAILS else 'all passed'}")
sys.exit(1 if FAILS else 0)
