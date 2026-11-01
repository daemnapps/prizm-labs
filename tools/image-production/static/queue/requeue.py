#!/usr/bin/env python3
"""Rejects go back in the queue with the judge's reason folded into the ask."""
import json, sys; from pathlib import Path
HERE = Path(__file__).resolve().parent
q = json.loads((HERE / "queue.json").read_text()); n = 0
FIX = {"BRISTLE": " The FLEX is held with its bristle face pressed flat against the skin, so the camera sees only the smooth black back of the pod and the hand over it — never the bristles.",
       "offer bar": " The bottom bar sits fully inside the frame with a clear margin below it.",
       "READABLE": " Every word is spelled correctly and printed cleanly.",
       "recognisably": " The device is the matte black teardrop pod with a rounded base and no handle."}
for it in q["items"]:
    if it["status"] == "failed" and it.get("attempts", 0) < 3:
        why = it.get("log", "")
        add = "".join(v for k, v in FIX.items() if k in why)
        it["change"] = it["change"].split(" The FLEX is held")[0].split(" The bottom bar sits")[0] + (add or " " + why[:120])
        it["status"] = "queued"; it.pop("filed", None); n += 1
(HERE / "queue.json").write_text(json.dumps(q, indent=1, ensure_ascii=False) + "\n")
print(f"{n} rejects re-queued with the judge's reason folded in")
