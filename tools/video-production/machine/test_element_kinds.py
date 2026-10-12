"""The three ways a brief can show an element (7 Oct): a voice-only speaker needs
only a voice, a background person only a look sheet, and a brand that keeps its
product as a flat file is checked against the product's truth kit."""
import json
import tempfile
from pathlib import Path

import element_paths as EP
import elements_check as EC

BRIEF = """```json
{"piece": {"product": "brush"},
 "cast": [{"id": "HOST", "bank_id": "host"}, {"id": "CROWD", "bank_id": "crowd"}],
 "scenes": [{"id": "S1", "who": "CROWD", "speaker": "HOST", "voice": "Welcome.", "product": true,
             "looks": {"CROWD": "look-1"}}]}
```"""


def _ws():
    ws = Path(tempfile.mkdtemp())
    (ws / "brands/acme/products").mkdir(parents=True)
    (ws / "brands/acme/products/brush.md").write_text("the brush")
    (ws / "brands/acme/products/brush-case.md").write_text("its case, a product of its own")
    for kit in ("brush-device", "brush-case"):
        k = ws / f"runs/ai-elements/acme/products/{kit}"
        (k / "sources").mkdir(parents=True)
        (k / "kit.json").write_text("{}")
        (k / "sources/packshot_front.jpg").write_text("x")
    host = ws / "runs/ai-elements/acme/casting/host"
    host.mkdir(parents=True)
    (host / "character.md").write_text("an off-camera host")
    (host / "voice.json").write_text(json.dumps({"voice_id": "v1"}))
    crowd = ws / "runs/ai-elements/acme/casting/crowd"
    (crowd / "sheets").mkdir(parents=True)
    (crowd / "character.md").write_text("a crowd from behind")
    (crowd / "sheets/look-1.jpg").write_text("x")
    (crowd / "looks.json").write_text(json.dumps({"looks": {"look-1": {}}}))
    (crowd / "spec.json").write_text(json.dumps({"shown": "background"}))
    (crowd / "provenance.json").write_text("{}")
    return ws


def test_kinds():
    ws = _ws()
    out = {i["id"]: i for i in EC.sheet(BRIEF, "acme", root=ws)["items"]}
    assert out["HOST"]["status"] == "banked", out["HOST"]["missing"]
    assert out["brush"]["status"] == "banked", out["brush"]["missing"]
    assert EP.product_kit("acme", "brush", ws).name == "brush-device"
    # the crowd's provenance is empty, so it is held for documentation only — never for face sheets
    assert not any("master" in m or "turnaround" in m for m in out["CROWD"]["missing"]), out["CROWD"]["missing"]


if __name__ == "__main__":
    test_kinds()
    print("OK")
