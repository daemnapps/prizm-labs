#!/usr/bin/env python3
"""The one page over the whole sweep: every board, its QC score, and the
doors into its QA page, contact sheets and rebuilt emails.

    python3 sweep/qa_index.py <brand>   -> results/format-bank/qa-index.html

The team's mirror, email-sms/design-formats/rebuild-qa.md, is proposed under
runs/email-production/<brand>/facts-<YYYY-MM-DD>/ (K2 (brands write wall)) — a
person folds it into brands/.
"""
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from paths import workspace  # noqa: E402
import facts_proposal  # noqa: E402
import os as _os
root = Path(_os.environ["FORMAT_BANK_DIR"]).resolve() if _os.environ.get("FORMAT_BANK_DIR") else HERE / "results" / "format-bank"
URLBASE = f"/results/{root.name}"


def main(brand):
    recs = json.loads((root / "qc.json").read_text()) if (root / "qc.json").is_file() else []
    by_board = {}
    for r in recs:
        by_board.setdefault(r["board"], []).append(r)
    n = len(recs)
    clean = [r for r in recs if not r["n_missing"] and r["placed"] == r["assets"] and not r["ctas_missing"] and r["order_ok"]]
    rows = []
    for board in sorted(p.name for p in root.iterdir() if p.is_dir()):
        rs = by_board.get(board, [])
        ok = sum(1 for r in rs if not r["n_missing"] and r["placed"] == r["assets"] and not r["ctas_missing"] and r["order_ok"])
        sheets = sorted(p.name for p in (root / board).glob("sheet-*.png"))
        sheet_links = " ".join(f'<a href="{URLBASE}/{board}/{s}" target="_blank">{s[6:8]}</a>' for s in sheets)
        flags = []
        for r in rs:
            f = []
            if r["n_missing"]:
                f.append(f"{r['n_missing']} text")
            if r["placed"] != r["assets"]:
                f.append(f"images {r['placed']}/{r['assets']}")
            if r["ctas_missing"]:
                f.append(f"{len(r['ctas_missing'])} CTA")
            if not r["order_ok"]:
                f.append("order")
            if f:
                flags.append(f"#{r['i']:02d} " + ", ".join(f))
        pct = int(100 * ok / len(rs)) if rs else 0
        bar = f'<div class="bar"><i style="width:{pct}%"></i></div>'
        rows.append(f'''<tr><td><a href="{URLBASE}/{board}/qa.html">{html.escape(board)}</a></td>
<td class="n">{len(rs)}</td><td class="n">{ok}/{len(rs)}</td><td>{bar}</td>
<td class="f">{html.escape("; ".join(flags)) or "clean"}</td><td class="s">{sheet_links}</td></tr>''')
    (root / "qa-index.html").write_text(f'''<!doctype html><meta charset="utf-8"><title>Format bank — sweep QA</title>
<link rel="stylesheet" href="/design/fonts.css"><style>
body{{margin:0;background:#141614;color:#f2f6ea;font:14px/1.5 "Untitled Sans",system-ui,sans-serif}} .wrap{{padding:28px;max-width:1200px}}
h1{{font:400 36px "GT Super Display",Georgia,serif;margin:0 0 6px}} p{{color:#a9ae9f;margin:0 0 18px}}
table{{border-collapse:collapse;width:100%}} th{{text-align:left;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#a9ae9f;padding:8px 10px;border-bottom:1px solid #2b2f2a}}
td{{padding:9px 10px;border-bottom:1px solid #22261f;vertical-align:top}} td.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
td.f{{color:#a9ae9f;font-size:12px;max-width:420px}} td.s a{{margin-right:6px;color:#c7cfad}}
a{{color:#c7cfad}} .bar{{width:120px;height:6px;background:#2b2f2a;border-radius:3px;overflow:hidden}} .bar i{{display:block;height:100%;background:#c7cfad}}
.big{{font:400 54px "GT Super Display",Georgia,serif;margin:6px 0 2px}} .kpi{{display:flex;gap:40px;margin:0 0 26px}} .kpi small{{display:block;color:#a9ae9f;font-size:11px;letter-spacing:.12em;text-transform:uppercase}}
</style><div class="wrap"><h1>Format bank — sweep QA</h1>
<p>Every export in the bank rebuilt as clean HTML on the bedrock, checked against its source: every string of copy present, every recovered picture placed, every button labelled, the reading order kept.</p>
<div class="kpi"><div><div class="big">{len(clean)}/{n}</div><small>clean on every check</small></div>
<div><div class="big">{sum(1 for r in recs if not r["n_missing"])}/{n}</div><small>copy complete</small></div>
<div><div class="big">{sum(1 for r in recs if r["placed"] == r["assets"])}/{n}</div><small>pictures placed</small></div>
<div><div class="big">{sum(1 for r in recs if not r["ctas_missing"])}/{n}</div><small>buttons labelled</small></div></div>
<table><tr><th>Board</th><th>Emails</th><th>Clean</th><th></th><th>What's flagged</th><th>Contact sheets</th></tr>{"".join(rows)}</table>
<p style="margin-top:22px">Each board page shows the export beside the rebuild, with the replication spec for every email. Contact sheets put four pairs on one picture for a fast eye pass.</p></div>''')
    # the team's mirror, for the brand's design-formats folder — proposed,
    # never written there
    mirror_dir = workspace() / "brands" / brand / "email-sms" / "design-formats"
    if mirror_dir.is_dir():
        md = ["# Format bank — the rebuild, checked", "",
              "Every export in the bank rebuilt as clean HTML on the brand's bedrock (wordmark, licensed faces, modules), "
              "with a replication spec per email — the teardown adapted for email: what the export is made of, in build order, "
              "so a designer or the machine can build it without seeing the original. Each rebuild is checked against its "
              "source: every line of copy present, every recovered picture placed, every button labelled, the reading order kept.", "",
              f"**{len(clean)}/{n} clean on every check** · copy complete {sum(1 for r in recs if not r['n_missing'])}/{n} · "
              f"pictures placed {sum(1 for r in recs if r['placed'] == r['assets'])}/{n} · buttons labelled {sum(1 for r in recs if not r['ctas_missing'])}/{n}", "",
              "Where it lives (local, `lab/email-production/results/format-bank/`, not committed — media): "
              "`<board>/NN-clean.html` the email, `NN-spec.md` its replication spec, `NN-clean.png` its picture, "
              "`<board>/qa.html` export beside rebuild, `sheet-NN.png` contact sheets, `qa-index.html` the one page over all boards. "
              "Engine: `sweep/rebuild.py` (extract → spec → render), `sweep/qc.py` (the checks), `sweep/capture_clean.py`, `sweep/sheets.py`.", "",
              "| Board | Emails | Clean | Flagged |", "|---|---|---|---|"]
        for board in sorted(by_board):
            rs = by_board[board]
            ok = sum(1 for r in rs if not r["n_missing"] and r["placed"] == r["assets"] and not r["ctas_missing"] and r["order_ok"])
            flags = [f"#{r['i']:02d}" for r in rs if not (not r["n_missing"] and r["placed"] == r["assets"] and not r["ctas_missing"] and r["order_ok"])]
            md.append(f"| {board} | {len(rs)} | {ok}/{len(rs)} | {', '.join(flags) or '—'} |")
        run = facts_proposal.run_dir(brand)
        print("mirror ->", facts_proposal.write(run, brand, "email-sms/design-formats/rebuild-qa.md", "\n".join(md) + "\n"))
        print("proposal ->", facts_proposal.note(run, brand))
    print("qa-index.html ->", root / "qa-index.html")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("qa_index.py: name the brand — python3 sweep/qa_index.py <brand> (the --brand the sweep ran with; there is no default)")
    main(sys.argv[1])
