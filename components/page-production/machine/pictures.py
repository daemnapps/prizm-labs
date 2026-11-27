#!/usr/bin/env python3
"""Page pictures, from image production only. Every picture slot on the written page is matched to a 3D print the
brand has filed and kept (runs/image-production/<brand>/sets/<set>/, the 3D process: scene at true sizes in 3D Jutsu,
printed, filed). A slot no kept print fits is FILED as a request in image production's 3D print queue
(image_production/set_queue.py -> runs/image-production/<brand>/set-requests/), which the 3d-print skill clears. Nothing
is generated here, and nothing outside image production.

    python3 pictures.py --brand <brand> --label <label> [--resume]

Writes pictures.json: {slot: {"set", "print", "why"} | {"queued": request id, "print_brief"}}.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "page-teardown" / "machine"))
import chain_io as C  # noqa: E402

PROMPTS = HERE.parent / "prompts"


def slots_of(page):
    out = []
    for s in page.get("sections", []):
        k = 0
        for b in s.get("blocks", []):
            if b.get("type") == "picture":
                k += 1
                b["slot"] = f"s{s.get('n')}-p{k}"
                out.append({"slot": b["slot"], "section_job": s.get("job"), "shows": b.get("shows") or b.get("text"),
                            "aspect": b.get("aspect")})
    return out


def kept_sets(brand):
    base = C.WS / "runs" / "image-production" / brand / "sets"
    out = {}
    for d in sorted(base.iterdir()) if base.is_dir() else []:
        f = d / "set.json"
        if not f.is_file():
            continue
        s = json.loads(f.read_text())
        prints = s.get("prints") or []
        kept = [p for p in prints if str(p.get("note", "")).lower().startswith(("kept", "approved"))]
        if not kept and s.get("approved") and prints:
            kept = [prints[-1]]
        if not kept or not (d / kept[-1]["file"]).is_file():
            continue
        out[d.name] = {"what": s.get("what") or kept[-1].get("note"), "people": s.get("people") or s.get("person"),
                       "signage": s.get("signage") or [], "style": s.get("style"),
                       "print": str((d / kept[-1]["file"]).relative_to(C.WS)), "note": kept[-1].get("note")}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True); ap.add_argument("--label", required=True)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args(argv)
    run = C.Run(a.brand, a.label)
    page = json.loads((run.dir / "page.json").read_text())
    slots = slots_of(page)
    (run.dir / "page.json").write_text(json.dumps(page, indent=1, ensure_ascii=False))   # slot ids recorded
    sets = kept_sets(a.brand)
    brief = {k: {x: v[x] for x in ("what", "people", "signage", "style")} for k, v in sets.items()}
    pick = run.stage("pictures", PROMPTS, dict(slots=json.dumps(slots, indent=1, ensure_ascii=False),
                                               sets=json.dumps(brief, indent=1, ensure_ascii=False)),
                     tier="checks", resume=a.resume, order=20, component="page-production",
                     title="Production · pictures from filed 3D prints")
    sys.path.append(str(C.WS / "components" / "image-production"))
    from image_production import set_queue as Q
    out = {}
    for p in pick.get("slots", []):
        slot = p.get("slot")
        name = (p.get("set") or "none").strip()
        if name in sets:
            out[slot] = {"set": name, "print": sets[name]["print"], "why": p.get("why")}
        else:
            want = next((s for s in slots if s["slot"] == slot), {})
            f = Q.file(a.brand, what=f"{a.label} page picture {slot}: {want.get('shows')}",
                       name=f"page-{a.label}-{slot}", scene=p.get("print_brief") or want.get("shows"),
                       frame=f"{want.get('aspect') or '4:5'} page picture; no words in frame",
                       resume={"chain": "page-production", "brand": a.brand, "label": a.label, "slot": slot},
                       source=f"runs/page-chain/{a.brand}/{a.label}/page.json")
            out[slot] = {"queued": f.stem, "print_brief": p.get("print_brief"), "shows": want.get("shows"),
                         "why": p.get("why")}
    (run.dir / "pictures.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    used = sum(1 for v in out.values() if "set" in v)
    print(f"pictures: {len(slots)} slots · {used} from filed 3D prints · {len(slots) - used} queued for a 3D print")


if __name__ == "__main__":
    try:
        main()
    except C.UsageLimit as e:
        sys.exit(f"STOPPED — {e}")
