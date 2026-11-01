"""The email line's door to the chain's learnings (components/run-kit/run_kit/learnings.py, any chain, any brand).

Kept here so the email line keeps one import; the store, the rules and the CLI are run-kit's. What this adds:
the Klaviyo approval page's Send back notes (runs/email-production/<brand>/learnings.jsonl) ride along in the block.

    python3 -m run_kit.learnings add --stage picture --kind never --rule "…" [--brand b] [--chain email]   (from components/run-kit)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent.parent / "run-kit"))
from run_kit import learnings as RL  # noqa: E402
from run_kit import paths  # noqa: E402

add = lambda brand, stage, kind, rule, why="", by="", src="": RL.add(brand, stage, kind, rule, why, by, src, "email")  # noqa: E731
load = RL.load


def _sent_back(brand):
    f = Path(paths.repo()) / "runs" / "email-production" / (brand or "_none") / "learnings.jsonl"
    out = []
    if f.exists():
        for x in f.read_text().splitlines():
            try:
                r = json.loads(x)
            except ValueError:
                continue
            if "reasons" in r:
                out.append("- SENT BACK (%s, %s): %s%s" % (r.get("label", "?"), r.get("by", "?"), ", ".join(r.get("reasons") or []),
                                                          (" — " + r["note"]) if r.get("note") else ""))
    return out[::-1][:20]


def block(brand, stages):
    return RL.block(brand, stages, "email", extra=_sent_back(brand))
