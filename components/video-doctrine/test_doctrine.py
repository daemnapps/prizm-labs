#!/usr/bin/env python3
"""The video doctrine's declared test. Stdlib only.

    python3 components/video-doctrine/test_doctrine.py

Proves: every bank format has one shape row of the same kind, no shape is
missing or invented, slices match the JSON, and every source key resolves.
"""

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import render  # noqa: E402

d = json.loads((HERE / "frameworks.json").read_text())
bank = json.loads((HERE.parent / "video-production/formats/bank.json").read_text())
want = {f["id"]: f.get("format_type") for f in bank["formats"]}
got = {r["format"]: r["kind"] for r in d["shapes"]["rows"]}
assert got == want, (got, want)

for block in ("shot_language", "look", "staging", "cutting"):
    for g in d[block]["groups"]:
        assert g["ref"] in d["sources"], g["ref"]
for r in d["consistency"]["rows"]:
    assert r["ref"] in d["sources"], r["ref"]

for name, lines in render.render_all(d).items():
    assert (HERE / "slices" / name).read_text() == "\n".join(lines), name
print("ok")
