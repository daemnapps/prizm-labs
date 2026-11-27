"""One brief ledger: every brief with ID, brand, type, production lane, status and hand-off link.

Reads runs/queue/brief-index.json (the queue's own index) and runs/handoffs/*/; the
editor-queue audit verdicts live in ledger-audit.json. Writes runs/queue/brief-ledger.json,
runs/queue/BRIEF-LEDGER.md, and a PACK.md index inside every open video hand-off.
No network, no model. Run: python3 components/briefs/ledger.py
"""
import json, os, glob, sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
import video_delivery
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAGE = {"idea": "Swipe teardown", "brief": "Brief writing", "brief-needs-you": "Approve brief", "making": "Handed off · making",
         "editing": "Editing", "final-needs-you": "Approve ad", "launch": "Sending to Meta", "live": "On Meta · completed"}
TYPE = {"video-ad": "video", "image-ad": "image", "email": "email"}

def packs():
    out = {}
    for d in glob.glob(os.path.join(ROOT, "runs/handoffs/*/*/*_*/")):
        out[os.path.basename(d.rstrip("/"))] = os.path.relpath(d, ROOT)
    return out

def section(folder, files, head, test):
    hits = [f for f in files if test(f)]
    return [f"## {head}", ""] + ([f"- `{f}`" for f in hits] or ["- none in this pack"]) + [""]

def write_pack(key, lane, folder):
    full = os.path.join(ROOT, folder)
    if os.path.isfile(os.path.join(full, "BRIEF.md")) or os.path.isfile(os.path.join(full, "handoff.md")):
        video_delivery.pack(full)
    files = sorted(os.path.relpath(p, full) for p in glob.glob(full + "/**/*", recursive=True)
                   if os.path.isfile(p) and "/returned/" not in "/" + os.path.relpath(p, full) and not p.endswith("PACK.md"))
    lo = lambda f: f.lower()
    lines = [f"# {key}", "", f"Production lane: **{lane}**", "",
             "This folder is the whole job. Pull this, nothing else. Finished files go in `returned/`.", ""]
    lines += section(folder, files, "1 Instructions", lambda f: lo(f).endswith(("brief.md", "run.md", "handoff.md", "edit-notes.md", "study.md", "video-delivery.md")))
    lines += section(folder, files, "2 Storyboard", lambda f: "stills/" in lo(f) or "-start" in lo(f) or "script" in lo(f) or "image-" in lo(f))
    hook_files = [f for f in files if "caption" in lo(f) or "hook" in lo(f)]
    brief_files = [f for f in files if lo(f).endswith("brief.md")]
    brief_where = ", ".join(f"`{f}`" for f in brief_files) or "the brief named in `handoff.md`"
    lines += ["## 3 Captions, openings and thumbnails", "",
              f"Read the openings/hooks and Thumbnail directions inside {brief_where}; separate hook files are not required.",
              "Follow `VIDEO-DELIVERY.md` for the complete version and cover checklist. Two control revisions do not replace requested variations.", ""]
    lines += [f"- `{f}`" for f in hook_files] + [""]
    lane_head = {"all AI": "4 Assets: AI generation (prompts, start pictures, audio)",
                 "AI plus real people": "4 Assets: recorded footage first, AI fills",
                 "all code/animation": "4 Assets: code/animation (song, packshot, source shots)"}[lane]
    lines += section(folder, files, lane_head, lambda f: lo(f).endswith((".png", ".jpg", ".mp3", ".mp4", ".wav", ".json")) and "caption" not in lo(f) and "hook" not in lo(f))
    open(os.path.join(full, "PACK.md"), "w").write("\n".join(lines))


def apply_delivery_states(rows, root):
    """Overlay current maker revision identity without changing unrelated brief stages."""
    for row in rows:
        rel = row.get("handoff")
        if not rel:
            continue
        path = Path(root) / rel / "delivery-state.json"
        if not path.is_file():
            continue
        state = json.loads(path.read_text())
        row["revision_id"] = state.get("revision_id")
        row["revision_round"] = state.get("round", 0)
        row["delivery_state"] = state.get("state")
        row["revision_request"] = state.get("request")
        if state.get("state") == "back-for-revision":
            row["status"] = "Back for revision"
            row["check"] = "incomplete — with maker"
        elif state.get("state") == "ready-for-review":
            row["status"] = "Ready for review"
            row["check"] = "delivery checklist passed"
    return rows


def refresh_delivery_states(root=None):
    """Refresh the existing ledger from handoff state; no generation or index rebuild."""
    from datetime import datetime, timezone
    root = Path(root or ROOT)
    path = root / "runs/queue/brief-ledger.json"
    if not path.is_file():
        return None
    doc = json.loads(path.read_text())
    rows = apply_delivery_states(doc.get("briefs", []), root)
    doc["revision_updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    md = ["# Brief ledger", "", "Every brief: ID, type, title, production lane, state, delivery check, revision and handoff.",
          "Revision state comes from the handoff's delivery-state.json; each R01/R02 request is kept under revisions/.", ""]
    for brand in sorted({r.get("brand") or "unassigned" for r in rows}):
        md += ["## " + brand.upper(), "", "| ID | Type | Title | Lane | State | Check | Revision | Hand-off |", "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            if (r.get("brand") or "unassigned") != brand:
                continue
            revision = (r.get("revision_id") or "").rsplit("-", 1)[-1]
            fields = [r.get("id"), r.get("type"), (r.get("title") or "")[:60], r.get("lane"), r.get("status"), r.get("check"), revision, r.get("handoff")]
            md.append("| " + " | ".join(str(x or "").replace("|", "/") for x in fields) + " |")
        md.append("")
    (root / "runs/queue/BRIEF-LEDGER.md").write_text("\n".join(md) + "\n")
    return doc


def main():
    idx = json.load(open(os.path.join(ROOT, "runs/queue/brief-index.json")))["briefs"]
    audit = json.load(open(os.path.join(os.path.dirname(__file__), "ledger-audit.json")))
    P = packs(); rows = []
    verdict = {**audit["not_for_editor"], **audit["old_folders"], **audit["open_video"]}
    for k, e in idx.items():
        key = e.get("entry") or k
        v = verdict.get(key, {})
        rows.append({"id": e.get("brief_id") or key, "key": key, "brand": e.get("brand"), "type": TYPE.get(e.get("type"), e.get("type")),
                     "title": e.get("title"), "lane": v.get("lane", ""), "status": STAGE.get(e.get("stage"), e.get("stage")),
                     "check": v.get("verdict", ""), "handoff": P.get(key, ""), "thumb": e.get("thumb", "")})
    for key, v in audit["open_video"].items():
        if not any(r["key"] == key for r in rows):
            rows.append({"id": key.rsplit("_", 1)[-1], "key": key, "brand": key.split("_")[0], "type": "video", "title": "",
                         "lane": v["lane"], "status": "Production", "check": "ready", "handoff": P.get(key, ""), "thumb": ""})
        if P.get(key): write_pack(key, v["lane"], P[key])
    rows.sort(key=lambda r: (r["brand"] or "", r["type"] or "", r["status"] or "", r["key"]))
    json.dump({"built": idx and audit["audited"], "count": len(rows), "briefs": rows},
              open(os.path.join(ROOT, "runs/queue/brief-ledger.json"), "w"), indent=1)
    md = ["# Brief ledger", "", "Every brief: ID, brand, type, production lane, status, hand-off. Built by `components/briefs/ledger.py`.",
          "The video editor pulls only rows marked **ready** with a hand-off.", ""]
    for brand in ("brand_a", "brand_b"):
        md += [f"## {brand.upper()}", "", "| ID | Type | Title | Lane | Status | Check | Hand-off |", "|---|---|---|---|---|---|---|"]
        md += [f"| {r['id']} | {r['type']} | {(r['title'] or '').replace('|','/')[:60]} | {r['lane']} | {r['status']} | {r['check']} | {r['handoff']} |"
               for r in rows if r["brand"] == brand]
        md.append("")
    open(os.path.join(ROOT, "runs/queue/BRIEF-LEDGER.md"), "w").write("\n".join(md))
    refresh_delivery_states()
    print(len(rows), "briefs;", len(audit["open_video"]), "packs indexed")

if __name__ == "__main__":
    main()
