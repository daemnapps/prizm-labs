#!/usr/bin/env python3
"""The proof view — what we started from, what we asked for, what came back.

Damon, 2026-09-09: "show the example swipe with the generations we make and the
clear injection file so we can confirm there is the removal of slop."

Three columns per picture: the REFERENCE it was edited from, the INJECTION
(the exact instruction sent, verbatim), and the RESULT with the judge's
verdict and the headline-match read. Nothing summarised — the prompt is the
product, so it is printed as it was sent.
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
WS = HERE.parents[3]
sys.path.insert(0, str(HERE)); import queue as Q


def rows():
    q = json.loads((HERE / "queue.json").read_text())["items"]
    reqs = {r["id"]: r for r in json.loads((HERE / "inbox/requests2.json").read_text())} if (HERE / "inbox/requests2.json").is_file() else {}
    review = json.loads((HERE / "review.json").read_text())
    ocr = json.loads((Q.RUNS_ROOT / "_ocr.json").read_text())
    out = []
    for it in q:
        unit = Q.RUNS_ROOT / it["run"] / "ads" / it["slug"]
        man = json.loads((unit / "manifest.json").read_text())
        name = man["ad_name"] + f"-a{it['target']:02d}"
        spec = json.loads((Q.RUNS_ROOT / it["run"] / "batch.json").read_text())
        ad = next((a for a in spec["ads"] if a["slug"] == it["slug"]), {})
        result = unit / f"{name}.png"
        rej = sorted((unit / "rejected").glob(f"{name}*.png")) if (unit / "rejected").is_dir() else []
        whyf = unit / "rejected" / f"{name}-why.md"
        killed = sorted((unit / "killed").glob(f"{name}-*.png")) if (unit / "killed").is_dir() else []
        o = ocr.get(f"{name}.png", {})
        out.append({
            "id": it["id"], "unit": it["slug"], "run": it["run"], "man": man.get("talent"),
            "format": man.get("format"), "kind": it["kind"], "status": it["status"],
            "headline_spec": (ad.get("copy") or {}).get("headline", ""),
            "headline_read": o.get("headline", ""),
            "reference": it.get("source"), "reference_name": it.get("source_name"),
            "injection": (reqs.get(it["id"]) or {}).get("prompt") or it.get("change"),
            "result": str(result.relative_to(WS)) if result.is_file() else None,
            "rejected": str(rej[-1].relative_to(WS)) if rej else None,
            "why": whyf.read_text() if whyf.is_file() else "",
            "killed": str(killed[-1].relative_to(WS)) if killed else None,
            "kill_note": (review.get(name) or {}).get("why", ""),
            "verdict": (review.get(name) or {}).get("verdict"),
        })
    return out


if __name__ == "__main__":
    print(json.dumps(rows(), indent=1, ensure_ascii=False))
