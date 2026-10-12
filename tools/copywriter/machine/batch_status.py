#!/usr/bin/env python3
"""One delivery batch, one status page.

    python3 machine/batch_status.py <label-prefix> <title>

Reads the teardown runs and the copy runs for every label starting with the
prefix and draws where each ad stands: record → copy stages → published.
Written for an editor's 7-ad delivery; works for any ads_to_copy.sh batch.
"""
import html, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import paths as P                                # noqa: E402  both run homes


def _vt_workdir():
    """video-teardown's working-folder module, loaded by file (SI-56)."""
    m = sys.modules.get("vt_workdir")
    if m is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "vt_workdir", P.repo() / "tools" / "video-teardown" / "machine" / "workdir.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules["vt_workdir"] = m
        spec.loader.exec_module(m)
    return m


# Found from the repo root, not counted up from this file — the count went
# stale when this tool moved from lab/ to components/ (2026-09-19).
# The teardown's live runs: runs/video-teardown/_work/ (SI-56, 2026-10-08).
VT_RUNS = _vt_workdir().root(P.repo())

COPY_STAGES = ["stage0", "stage1", "stage1b", "stage2", "stage3", "stage4",
               "stage5", "stage7", "stage8", "stage9"]
NAMES = {"stage0": "triage", "stage1": "read", "stage1b": "scout", "stage2": "spec",
         "stage3": "inject", "stage4": "place", "stage5": "hooks",
         "stage7": "close", "stage8": "render", "stage9": "brief"}


def esc(s):
    return html.escape(str(s))


def _filed_teardown(label):
    """The filed shelf's teardown record for this label, or None."""
    kit = str(P.repo() / "components" / "run-kit")
    if kit not in sys.path:
        sys.path.append(kit)
    from run_kit import index as RKI
    for row in RKI.scan():
        if row["machine"] == "video-teardown" and row["label"] == label:
            f = P.repo() / row["path"] / "stages" / "1-teardown.md"
            if f.is_file():
                return f
    return None


def ad_state(label):
    rec = None
    for cand in (VT_RUNS / label / "stages" / "1-teardown.md",
                 VT_RUNS / label / "1-teardown.md"):
        if cand.is_file():
            rec = cand
            break
    if rec is None:
        rec = _filed_teardown(label)
    home = P.find_run(label)          # runs/copywriter/<brand>/<label>, else results/<label>
    r = (home or ROOT / "results" / label) / "run.json"
    stages = {}
    if r.is_file():
        try:
            stages = json.loads(r.read_text()).get("stages", {})
        except Exception:
            pass
    published = any(p.is_dir() and label.split("-", 1)[-1] in p.name.replace("-", "")
                    for _n, p in P.all_deliverables())
    # publish naming is slug-of-reference; simpler: copy.md fresh within batch
    return dict(label=label, record=bool(rec), stages=stages, published=published)


def build(prefix, title):
    labels = sorted({d.name for d in (VT_RUNS.iterdir() if VT_RUNS.is_dir() else [])
                     if d.name.startswith(prefix)}
                    | {d.name for d in P.all_runs() if d.name.startswith(prefix)})
    ads = [ad_state(l) for l in labels]
    now = time.strftime("%H:%M:%S")
    done = sum(1 for a in ads
               if a["stages"].get("stage9", {}).get("status") == "done"
               or a["stages"].get("stage8", {}).get("status") == "done")

    p = [f'<title>{esc(title)}</title>',
         '<meta http-equiv="refresh" content="5">',
         '<style>:root{--bg:#F2F1EF;--s:#FFF;--ink:#1B1917;--body:#3C3934;--dim:#6E6A63;'
         '--line:#E1DED8;--ok:#2C6B60;--oks:#E3EFEC;--run:#8A5A1F;--runs:#F7EEDF;'
         '--wait:#B9B5AD;--mono:ui-monospace,Menlo,monospace}'
         '@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#151412;--s:#1D1B19;'
         '--ink:#EFEBE3;--body:#D3CEC5;--dim:#98938A;--line:#302D28;--ok:#5FB3A4;--oks:#162925;'
         '--run:#D9A85D;--runs:#2B2114;--wait:#57534C}}'
         ':root[data-theme=dark]{--bg:#151412;--s:#1D1B19;--ink:#EFEBE3;--body:#D3CEC5;'
         '--dim:#98938A;--line:#302D28;--ok:#5FB3A4;--oks:#162925;--run:#D9A85D;'
         '--runs:#2B2114;--wait:#57534C}'
         '*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--body);'
         'font:16px/1.55 Georgia,serif;padding:40px 20px 80px}'
         '.w{max-width:46rem;margin:0 auto}h1{color:var(--ink);font-size:26px;margin:0 0 4px}'
         '.sub{color:var(--dim);font-size:14px;margin:0 0 22px}'
         '.ad{background:var(--s);border:1px solid var(--line);border-radius:9px;'
         'padding:14px 18px;margin:10px 0}'
         '.h{display:flex;gap:10px;align-items:baseline}'
         '.h b{color:var(--ink);font-size:15.5px}'
         '.st{margin-left:auto;font:600 11px var(--mono)}'
         '.st.done{color:var(--ok)}.st.run{color:var(--run)}.st.wait{color:var(--wait)}'
         '.pips{display:flex;gap:5px;margin-top:9px;flex-wrap:wrap}'
         '.pip{font:600 9.5px var(--mono);padding:3px 8px;border-radius:9px;'
         'border:1px solid var(--line);color:var(--wait)}'
         '.pip.done{background:var(--oks);color:var(--ok);border-color:var(--ok)}'
         '.pip.run{background:var(--runs);color:var(--run);border-color:var(--run)}'
         'footer{margin-top:26px;font:11.5px var(--mono);color:var(--dim);line-height:1.7}'
         '</style>',
         f'<div class="w"><h1>{esc(title)}</h1>',
         f'<p class="sub">{done} of {len(ads)} through the copy chain · snapshot {now} · '
         'the live-live view is the board on :8778</p>']
    for a in ads:
        st = a["stages"]
        last_done = [k for k in COPY_STAGES if st.get(k, {}).get("status") == "done"]
        running = next((k for k in COPY_STAGES if st.get(k, {}).get("status")
                        not in ("done", None)), None)
        if st.get("stage8", {}).get("status") == "done" or st.get("stage9", {}).get("status") == "done":
            badge, cls = "COPY DONE", "done"
        elif st:
            badge, cls = f"writing · {NAMES.get(running or (last_done[-1] if last_done else ''), '…')}", "run"
        elif a["record"]:
            badge, cls = "record ready — copy queued", "wait"
        else:
            badge, cls = "tearing down", "run"
        p.append(f'<div class="ad"><div class="h"><b>{esc(a["label"])}</b>'
                 f'<span class="st {cls}">{esc(badge)}</span></div>')
        p.append('<div class="pips">'
                 + f'<span class="pip {"done" if a["record"] else "run"}">record</span>')
        for k in COPY_STAGES:
            s = st.get(k, {}).get("status")
            c = "done" if s == "done" else ("run" if s else "")
            p.append(f'<span class="pip {c}">{NAMES[k]}</span>')
        p.append('</div></div>')
    p.append('<footer>generated by machine/batch_status.py — republished at every '
             'completion; refresh for the newest snapshot<br>record = teardown record '
             '(no brief, by design) · then the copy chain · docs land in the delivery '
             'folder at the end</footer></div>')
    out = ROOT / "pages" / "batch-status.html"
    out.write_text("".join(p), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "jax-",
          sys.argv[2] if len(sys.argv) > 2 else "an editor's 7 — teardown to copy")
