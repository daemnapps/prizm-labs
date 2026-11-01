#!/usr/bin/env python3
"""The tree page — every leaf of a Variation video tree on one page.

Five awareness levels × six hooks: for each leaf, its hook line and scroll
stopper, the full script, where the brief stands (done, held by the swipe
match, waiting), how much language it marked used, and the audit's verdict.
Everything is read from the run folders; nothing is summarised by a model.

    python3 tree_page.py <source slug>      → <root run>/tree.html
"""
import html, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain as C  # noqa: E402
import variation as V  # noqa: E402

E = html.escape


def stage_text(d, st, key):
    rec = (st.get("stages") or {}).get(key) or {}
    if rec.get("out") and (d / rec["out"]).is_file():
        return (d / rec["out"]).read_text()
    return ""


def full_script(close_text):
    m = re.search(r"\*\*6\. THE FULL SCRIPT\*\*(.*?)(?=\n\*\*7\.|\Z)", close_text, re.S)
    return (m.group(1).strip() if m else "").strip()


def verdict(audit_text):
    m = re.search(r"VERDICT[^A-Z]*(SHIP|RE-RUN[^\n]*|STOP)", audit_text)
    return m.group(1).strip() if m else ""


def dial(audit_text):
    m = re.search(r"## THE DIAL TEST(.*?)(?=\n## |\Z)", audit_text, re.S)
    if not m:
        return ""
    moved = re.findall(r"MOVED:[^\n]*", m.group(1))
    return "only awareness moved" if not moved else "; ".join(moved)


def build(src):
    root = V.runs() / V.slug_for(src)
    tree = V.fan_in(root, src)
    m = tree["map"]
    rst = V.load(root)
    proof = rst.get("proven_proof") or []
    cards = []
    for lv in m["levels"]:
        level = lv["level"]
        ld = V.runs() / V.slug_for(src, level)
        hooks = stage_text(ld, V.load(ld), "stage4b") if (ld / "run.json").is_file() else ""
        rows = []
        for n in range(6):
            leaf = tree["leaves"].get(f"{V.CODE[level]}{n}")
            hl = C.hook_lines(hooks, f"V{n}") if hooks else ""
            line = re.search(r"LINE V\d: (.*)", hl); card = re.search(r"CARD V\d: (.*)", hl)
            script = aud = ""
            status = "not written yet"
            used = None
            if leaf:
                d = V.runs() / leaf["run"]; st = V.load(d)
                script = full_script(stage_text(d, st, "stage4d"))
                aud = stage_text(d, st, "stage4e")
                status = {"done": "brief done", "held": "brief held — swipe match / manifest",
                          "error": "stopped"}.get(leaf.get("brief_status"), "writing")
                used = leaf.get("used")
            if not (line or card or leaf):
                continue
            rows.append(f"""<article class="leaf">
 <header><b>V{n}</b>{' <span class="ctl">control hook</span>' if n == 0 else ''}<span class="st">{E(status)}</span></header>
 <p class="line">{E(line.group(1)) if line else '—'}</p>
 <p class="card">{E(card.group(1)) if card else ''}</p>
 {f'<details><summary>Full script</summary><pre>{E(script)}</pre></details>' if script else ''}
 <footer>{f'audit: {E(verdict(aud))}' if aud else ''}{f' · {E(dial(aud))}' if aud and dial(aud) else ''}{f' · {used} language rows marked used' if used is not None else ''}</footer>
</article>""")
        added = ", ".join(a["id"] for a in lv.get("added") or []) or "—"
        dropped = ", ".join(x["id"] for x in lv.get("dropped") or []) or "—"
        cards.append(f"""<section class="level{' is-ctl' if level == m['control_level'] else ''}">
 <h2>{E(level)}{' <span class="ctl">control level</span>' if level == m['control_level'] else ''}</h2>
 <p class="open">{E(lv.get('opening') or '')}</p>
 <p class="secs"><b>Sections</b> {E(' → '.join(lv.get('sections') or []))}<br><b>Added</b> {E(added)} · <b>Dropped</b> {E(dropped)}</p>
 <div class="leaves">{''.join(rows) or '<p class="none">hooks not written yet</p>'}</div>
</section>""")
    nums = "; ".join(", ".join(f"{k} {p[k]:,}" for k in ("views", "saves", "spend", "purchases")
                                if isinstance(p.get(k), (int, float))) for p in proof)
    done = sum(1 for x in tree["leaves"].values() if x.get("brief_status") == "done")
    page = f"""<title>Variation tree · {E(src)}</title>
<style>
:root{{color-scheme:light;--bg:#f4f2ee;--panel:#fffdf9;--ink:#191714;--ink2:#5a554c;--ink3:#8a8478;--line:#e2ddd3;--acc:#e0482f;--lock:#2f6f5e}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#121110;--panel:#1b1a18;--ink:#f0ece4;--ink2:#b3ada1;--ink3:#827c71;--line:#2e2c28;--acc:#ff6a4d;--lock:#5bb89d}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#121110;--panel:#1b1a18;--ink:#f0ece4;--ink2:#b3ada1;--ink3:#827c71;--line:#2e2c28;--acc:#ff6a4d;--lock:#5bb89d}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding-inline:16px;padding-block:32px 64px}}
h1{{font-size:clamp(30px,5vw,46px);margin:0 0 6px}} h2{{margin:0 0 4px;font-size:24px;text-transform:capitalize}}
.sub{{color:var(--ink2);margin:0 0 20px}}
.level{{margin-top:28px;padding-top:18px;border-top:1px solid var(--line)}}
.level.is-ctl h2{{color:var(--lock)}}
.ctl{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;border:1px solid var(--lock);color:var(--lock);border-radius:999px;padding:1px 8px;margin-left:8px;vertical-align:middle}}
.open{{color:var(--ink2);margin:0 0 6px}} .secs{{font-size:13px;color:var(--ink2);margin:0 0 12px}}
.leaves{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}}
.leaf{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:grid;gap:6px;align-content:start}}
.leaf header{{display:flex;gap:8px;align-items:center}} .leaf header b{{color:var(--acc)}}
.leaf .st{{margin-left:auto;font-size:12px;color:var(--ink3)}}
.line{{margin:0;font-weight:600}} .card{{margin:0;color:var(--ink2);font-style:italic}}
.leaf footer{{font-size:12px;color:var(--ink3)}}
pre{{white-space:pre-wrap;font-size:12.5px;background:var(--bg);padding:10px;border-radius:8px;overflow-x:auto}}
.none{{color:var(--ink3)}}
</style>
<div class="wrap">
<h1>Variation tree</h1>
<p class="sub">{E(src)} · control level <b>{E(m['control_level'])}</b> · {E(nums)} · {done} of {len(tree['leaves'])} briefs done</p>
{''.join(cards)}
</div>
"""
    out = root / "tree.html"
    out.write_text(page)
    return out


if __name__ == "__main__":
    print(build(sys.argv[1]))
