"""Every person is the swipe's person (2026-10-01): a recast gender is caught."""
import json, tempfile
from pathlib import Path
import cast_match as cm

d = Path(tempfile.mkdtemp()); (d / "stages").mkdir()
(d / "run.json").write_text(json.dumps({"brand": "nobrand-test"}))
(d / "stages" / "1-teardown.md").write_text("""**1. THE OBJECTIVE RECORD**

**CAST**

**Host**
*   Voice: Mid-pitch, American.

**Chef (Dr. A)**
*   Voice: Male, mid-pitch.

**Critic**
*   Voice: Female, calm.

**PLACES**
""")
brief = {"cast": [{"id": "HOST", "bank_id": "NEW", "identity_block": "a woman in her 40s"},
                  {"id": "COOK", "bank_id": "NEW", "identity_block": "a woman, late 30s"},
                  {"id": "JUDGE", "bank_id": "NEW", "identity_block": "a woman, 50s"}],
         "scenes": [{"id": "S1", "who": "HOST", "speaker": "HOST", "source": "Host talks to the lens"},
                    {"id": "S2", "who": "COOK's hands", "speaker": "COOK", "source": "Chef stirs the pot"},
                    {"id": "S3", "who": "JUDGE", "speaker": "JUDGE", "source": "Critic tastes"}]}
(d / "stages" / "5-brief.md").write_text("x\n```json\n" + json.dumps(brief) + "\n```\n")
pairs, found = cm.check(d)
assert pairs == {"COOK": "Chef", "JUDGE": "Critic", "HOST": "Host"}, pairs
assert [f["n"] for f in found] == ["P-COOK"], found
print("OK")

# The brief follows the element (2026-10-01): a recast person's own words are
# caught and repaired; the other person's ("her cheek" = the patient) are not.
import shutil
e = Path(tempfile.mkdtemp()); (e / "stages").mkdir()
shutil.copy(d / "run.json", e / "run.json"); shutil.copy(d / "stages" / "1-teardown.md", e / "stages" / "1-teardown.md")
doc2 = {"cast": [{"id": "PRO", "bank_id": "NEW", "identity_block": "a man in his 50s, glasses"},
                 {"id": "GUEST", "bank_id": "NEW", "identity_block": "a woman in her 40s"}],
        "scenes": [{"id": "S1", "who": "PRO, GUEST", "source": "",
                    "composition": "GUEST centred; PRO behind her, only her right hand in frame",
                    "subject": "PRO's right hand on her cheek"},
                   {"id": "S2", "who": "PRO", "source": "", "beats": [{"do": "turns her hand over"}]}]}
readable = "**PRO** — late 40s; hair in a low bun, pearl studs; she is warm.\nLoad-bearing: her right hand.\n**Bank:** `NEW`.\n"
(e / "stages" / "5-brief.md").write_text(readable + "x\n```json\n" + json.dumps(doc2) + "\n```\n")
_, f2 = cm.check(e)
assert sorted(x["n"] for x in f2) == ["D-S1", "D-S2", "R-PRO"], f2
cm.repair(e)
out = (e / "stages" / "5-brief.md").read_text()
assert "PRO behind her, only his right hand" in out and "on her cheek" in out and "turns his hand over" in out, out
_, f3 = cm.check(e)
assert [x["n"] for x in f3 if x["n"].startswith("D-")] == [], f3
print("OK repair")
