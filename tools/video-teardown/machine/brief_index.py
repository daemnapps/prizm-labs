#!/usr/bin/env python3
"""The brief index — one row per brief, every station it touched one link away.

    python3 brief_index.py            rebuild runs/video-writing/INDEX.md + index.json

the owner, 2026-09-30: "The big thing is I just need to be able to index briefs at
a high level. If I ever need to refer back to any of these runs folders, we
can always do that per brief. That contains all the information we need to
make an analysis on ads, which is the whole point."

A brief is a writing run: `runs/video-writing/<brand>/<slug>/`. Its row carries
what an analysis groups ads by — route, product, avatar, awareness, the swipe's
format and framework, the kind of source — its three stamps, and the paths of
its teardown (same slug), its production runs and their edits. Production and
edit runs are joined by what they record (`brief_from`, the edit kit's
`from_run`), never guessed from a label; a run from before those were
recorded shows as not joined.

Rebuilt at the end of every filed run (file_run.py) and by hand. Reads only;
writes only the two index files.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C                                            # noqa: E402


def _json(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def _stamps(brief_text):
    t = brief_text or ""
    sm = re.search(r"<!-- swipe-match: (\w+)", t)
    rd = re.search(r"<!-- brief-read: (\w+)", t)
    mf = re.findall(r"^MANIFEST: (\w+)", t, re.M)
    return {"swipe_match": sm.group(1) if sm else None,
            "read": rd.group(1) if rd else None,
            "manifest": mf[-1] if mf else None}


def _brief_file(wdir):
    for rel in ("deliverable/7-final-brief.md", "deliverable/5-brief.md",
                "stages/7-final-brief.md", "stages/5-brief.md"):
        if (wdir / rel).is_file():
            return wdir / rel
    return None


def _joins(runs):
    """{writing-run path: [production runs]}, {production path: [edit runs]}."""
    prod, edit = {}, {}
    for f in sorted((runs / "video-production").glob("*/*/run.json")):
        src = (_json(f, {}) or {}).get("brief_from") or ""
        m = re.search(r"runs/video-(?:writing|teardown)/([^/]+)/([^/]+)/", src)
        if m:
            prod.setdefault(f"{m.group(1)}/{m.group(2)}", []).append(f.parent)
    for f in sorted((runs / "video-edit").glob("*/*/kit/edit-kit.json")):
        src = (_json(f, {}) or {}).get("from_run") or ""
        m = re.search(r"runs/video-production/([^/]+)/([^/]+)", src)
        if m:
            edit.setdefault(f"{m.group(1)}/{m.group(2)}", []).append(f.parent.parent)
    return prod, edit


def rows(repo=None):
    repo = Path(repo) if repo else C.workspace()
    runs = repo / "runs"
    prod, edit = _joins(runs)
    out = []
    for wdir in sorted((runs / "video-writing").glob("*/*")):
        if not (wdir / "run.json").is_file():
            continue
        brand, slug = wdir.parent.name, wdir.name
        st = _json(wdir / "run.json", {}) or {}
        tdir = runs / "video-teardown" / brand / slug
        doc = _json(tdir / "doctrine.json", {}) or {}
        ms = st.get("market_state") or {}
        aud = st.get("audience") or {}
        bf = _brief_file(wdir)
        p_runs = prod.get(f"{brand}/{slug}", [])
        e_runs = [e for p in p_runs for e in edit.get(f"{brand}/{p.name}", [])]
        rel = lambda p: p.relative_to(repo).as_posix()          # noqa: E731
        out.append({
            "brief": f"{brand}/{slug}",
            "status": "brief" if bf else "torn down — no brief yet",
            "brand": brand,
            "date": (st.get("opened") or "")[:10],
            "route": st.get("production_route"),
            "product": st.get("product"),
            "avatar": aud.get("_avatar") or aud.get("avatar"),
            "awareness": ms.get("awareness"),
            "sophistication": ms.get("sophistication"),
            "source": st.get("triage_lane"),
            "format": doc.get("format"),
            "framework": doc.get("framework"),
            "swipe": st.get("video_url") or st.get("origin_url") or st.get("source"),
            **_stamps(bf.read_text() if bf else ""),
            "brief_file": rel(bf) if bf else None,
            "teardown": rel(tdir) if tdir.is_dir() else None,
            "writing": rel(wdir),
            "production": [rel(p) for p in p_runs],
            "edit": [rel(e) for e in e_runs],
        })
    return out


def _cell(v, n=40):
    v = "" if v is None else str(v)
    v = v.replace("|", "/").replace("\n", " ")
    return v if len(v) <= n else v[:n - 1] + "…"


def build(repo=None):
    repo = Path(repo) if repo else C.workspace()
    rs = rows(repo)
    home = repo / "runs" / "video-writing"
    home.mkdir(parents=True, exist_ok=True)
    (home / "index.json").write_text(json.dumps(rs, indent=1, ensure_ascii=False) + "\n")
    ok = lambda r: "✔" if (r["swipe_match"] == "PASSED" and r["manifest"] == "COMPLETE") else "—"  # noqa: E731
    lines = [
        "# Briefs — the index",
        "",
        "One row per brief. Rebuilt by `tools/video-teardown/machine/brief_index.py`",
        "at the end of every filed run — never hand-edited. The same rows, every field,",
        "are in `index.json` beside this file, for analysis.",
        "",
        f"{sum(1 for r in rs if r['status'] == 'brief')} briefs · "
        f"{sum(1 for r in rs if r['status'] != 'brief')} torn down with no brief yet · "
        f"{sum(1 for r in rs if r['production'])} produced · {sum(1 for r in rs if r['edit'])} edited",
        "",
        "| Brief | Date | Route | Product | Avatar | Awareness | Format | Source | Stamped | Produced | Edited |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rs, key=lambda r: (r["status"] == "brief", r["date"], r["brief"]), reverse=True):
        link = f"[{r['brief']}]({r['brief_file'][len('runs/video-writing/'):]})" if r["brief_file"] else r["brief"]
        lines.append("| " + " | ".join([
            link, r["date"], _cell(r["route"]), _cell(r["product"], 28), _cell(r["avatar"], 24),
            _cell(r["awareness"], 20), _cell(r["format"], 24), _cell(r["source"], 14), ok(r),
            str(len(r["production"])) if r["production"] else "—",
            str(len(r["edit"])) if r["edit"] else "—"]) + " |")
    (home / "INDEX.md").write_text("\n".join(lines) + "\n")
    return home / "INDEX.md", len(rs)


if __name__ == "__main__":
    f, n = build()
    print(f"{n} briefs → {f}")
