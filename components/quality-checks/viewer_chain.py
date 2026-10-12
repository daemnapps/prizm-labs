#!/usr/bin/env python3
"""THE VIEWER CHAIN — the viewer check and the phone checks as one run
(the owner, 2026-10-02: "consolidate the viewer check and the ad signal tools …
build a chain now for this process … I think this is literally it").

    python3 viewer_chain.py <brief> --brand <brand> --avatar <avatar> [--sub NAME]
                            [--kind video|"still image"|carousel] [--frames DIR_OR_FILES…] [--label NAME]

One brief in; one folder and one page out, at runs/viewer-check/<brand>/<label>/:

  1 card       the avatar, as a person, from the profile          (cached)
  2 cut        what a viewer actually sees and hears, second by second
  3 feed       9 real posts from that avatar's feed, ours dropped in
  4 scroll     5 fresh viewers, 2 with the sound off (viewer-check v2)
  5 objections their doubts matched to the brand's objection bank, the bank's answer quoted
  6 score      code, against the real posts — never "looks real"
  7 route      a fail goes back to the writing step, carrying 4 and 5
  7b fix       the failing part is rewritten (objection-bank answers, the customers' own words),
               then a fresh 5 scroll it again — up to 3 rewrites, then the owner
  7c learn     a pass after a fail is written to records/learnings/<brand>--<avatar>.md,
               which every later fix and every writing stage reads
  8 hidden     faces, product and words under the TikTok / Reels / Shorts buttons (when frames exist)
  · waiting    where eyes go · will they keep watching · the face — models not installed

The video and statics chains run steps 1–7 at their own gate (viewer.check);
this is the same code, runnable on any brief. Nothing here names a brand.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from marketing_chain_checks import viewer as V   # noqa: E402

IMG = {".png", ".jpg", ".jpeg", ".webp"}
MAX_FIX = 3          # rewrites before it goes to the owner


def passes(r: dict) -> int:
    return sum(1 for c in (r.get("checks") or {}).values() if c.get("passed"))


def frames_of(items):
    out = []
    for x in items or []:
        p = Path(x)
        if p.is_dir():
            out += sorted(f for f in p.iterdir() if f.suffix.lower() in IMG)
        elif p.suffix.lower() in IMG and p.exists():
            out.append(p)
    return out


def _result_from(folder: Path) -> dict:
    """A finished round, read back from its files (for the index page)."""
    run = folder.parent.parent
    st = json.loads((run / "viewer-check" / "STAMP.json").read_text()) if (run / "viewer-check" / "STAMP.json").exists() else {}
    key = json.loads((folder / "key.json").read_text())
    mine = []
    for i, at in enumerate(key.get("ours_at") or []):
        f = folder / f"viewer-{i + 1}-answer.json"
        if f.exists():
            a = json.loads(f.read_text())
            posts = a.get("posts", a) if isinstance(a, dict) else a
            mine += [p for p in posts if int(p.get("n", 0)) == at]
    ob = json.loads((folder / "objections.json").read_text()) if (folder / "objections.json").exists() else {}
    fr = json.loads((folder / "hidden.json").read_text()) if (folder / "hidden.json").exists() else []
    bd = json.loads((folder / "belief.json").read_text()) if (folder / "belief.json").exists() else {}
    rt = V.route({"passed": st.get("passed"), "checks": st.get("checks") or {}, "mine": mine,
                  "left": [V._sec(m.get("left_at"), (st.get("predicted") or {}).get("length_s") or 0) for m in mine],
                  "ad": [V._sec(m.get("ad_at"), 0) for m in mine]}, 0) if not st.get("passed") else {"fix_at": None, "at": None}
    ch = json.loads((run / "chain.json").read_text()) if (run / "chain.json").exists() else {}
    return {"passed": st.get("passed"), "checks": st.get("checks") or {}, "fix_at": st.get("fix_at") or rt.get("fix_at"),
            "at": rt.get("at"), "round": st.get("round"), "predicted": st.get("predicted") or {}, "objections": ob,
            "mine": mine, "frames": fr, "history": ch.get("history") or [], "changes": ch.get("changes") or [], "belief": bd}


def rebuild_index() -> Path:
    """runs/viewer-check/INDEX.html — every run, newest first, one tab each."""
    import re
    root = V.WS / "runs" / "viewer-check"
    tabs, bodies, style = [], [], ""
    rounds = []
    for run in root.glob("*/*"):
        rs = sorted((d for d in (run / "viewer-check").glob("r*") if d.name[1:].isdigit()), key=lambda d: int(d.name[1:]))
        if rs and (rs[-1] / "key.json").exists():
            rounds.append((rs[-1].stat().st_mtime, run, rs[-1]))
    for i, (_, run, rd) in enumerate(sorted(rounds, reverse=True)):
        brand, label = run.parent.name, run.name
        card = (V.CARDS.glob(f"{brand}--*.md"))
        key = json.loads((rd / "key.json").read_text())
        avatar = (key.get("card") or "").replace(".md", "").replace(f"{brand}--", "")
        page = V.report_html(_result_from(rd), brand, avatar, title=label)
        style = style or re.search(r"<style>(.*?)</style>", page, re.S).group(1)
        body = re.search(r'(<div class="w">.*)$', page, re.S).group(1)
        ok = json.loads((run / "viewer-check" / "STAMP.json").read_text()).get("passed") if (run / "viewer-check" / "STAMP.json").exists() else None
        tabs.append(f'<button type="button" class="tab" data-i="{i}" aria-pressed="{str(i == 0).lower()}"><i class="{"p" if ok else "f"}"></i>{label}<small>{brand}</small></button>')
        bodies.append(f'<div class="pane" data-i="{i}"{"" if i == 0 else " hidden"}>{body}</div>')
    html = f"""<title>Viewer Chain</title>
<style>{style}
[hidden]{{display:none!important}}
.top{{max-width:960px;margin:0 auto;padding-inline:18px;padding-block:28px 0;display:flex;flex-direction:column;gap:12px}}
.top h1{{font:800 clamp(2rem,6vw,3rem)/1.05 system-ui;margin:0}}.top p{{margin:0;color:var(--muted)}}
.tabs{{display:flex;flex-wrap:wrap;gap:8px}}.tab{{display:flex;align-items:center;gap:8px;font:600 .9rem/1 system-ui;padding:10px 14px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--fg);cursor:pointer}}
.tab small{{color:var(--muted);font-weight:500}}.tab[aria-pressed="true"]{{border-color:var(--fg);box-shadow:inset 0 0 0 1px var(--fg)}}.tab i{{width:10px;height:10px;border-radius:50%}}.tab i.p{{background:var(--pass)}}.tab i.f{{background:var(--fail)}}
.tab:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
</style>
<div class="top"><h1>Viewer Chain</h1><p>Every ad run through the chain, newest first. Green passed, red goes back. Each tab is one ad.</p><div class="tabs" id="tabs">{"".join(tabs)}</div></div>
{"".join(bodies)}
<script>document.getElementById("tabs").addEventListener("click",e=>{{const b=e.target.closest(".tab");if(!b)return;document.querySelectorAll(".tab").forEach(t=>t.setAttribute("aria-pressed",t===b));document.querySelectorAll(".pane").forEach(p=>p.hidden=p.dataset.i!==b.dataset.i);}});</script>"""
    out = root / "INDEX.html"
    out.write_text(html)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="The viewer chain: one brief in, one page out.")
    ap.add_argument("brief")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--avatar", required=True)
    ap.add_argument("--sub")
    ap.add_argument("--kind", default="video")
    ap.add_argument("--frames", nargs="*")
    ap.add_argument("--label")
    a = ap.parse_args(argv)
    brief = Path(a.brief).resolve()
    label = a.label or brief.parent.parent.name if brief.parent.name in ("stages", "deliverable", "out") else (a.label or brief.stem)
    run = V.WS / "runs" / "viewer-check" / a.brand / label
    run.mkdir(parents=True, exist_ok=True)
    print(f"viewer chain · {a.brand} · {a.sub or a.avatar} · {brief.name} → {run.relative_to(V.WS)}")
    who = a.sub or a.avatar
    r, text = V.run_loop(run, a.brand, a.avatar, brief.read_text(), kind=a.kind, sub=a.sub, label=label, max_fix=MAX_FIX)
    fr = frames_of(a.frames)
    if fr:
        print(f"  hidden by the app: {len(fr)} frame(s)")
        r["frames"] = V.hidden_by_app(fr)
        (Path(r["folder"]) / "hidden.json").write_text(json.dumps(r["frames"], indent=1, ensure_ascii=False) + "\n")
    page = V.report_html(r, a.brand, a.sub or a.avatar, title=label)
    (Path(r["folder"]) / "REPORT.html").write_text(page)
    (run / "REPORT.html").write_text(page)
    print(("  PASSED — worth making" if r["passed"] else f"  FAILED — back to {V.say(r['fix_at'])}")
          + f"\n  page: {(run / 'REPORT.html').relative_to(V.WS)}")
    idx = rebuild_index()
    print(f"  all runs: {idx.relative_to(V.WS)}")
    return 0 if r["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
