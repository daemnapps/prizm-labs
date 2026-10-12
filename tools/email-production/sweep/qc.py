#!/usr/bin/env python3
"""QC every rebuild against its source, objectively, before any eye goes on it.

    python3 sweep/qc.py --bank <format-bank dir> --brand <brand> [--board jul-2025]

Per email:
  text      every string the export carries (each text span) must appear in
            the rebuild — missing copy is the worst defect and the easiest
            to measure
  images    every recovered bitmap (fig-asset) the export places must be
            placed in the rebuild; lost images must have a frame or a photo
  ctas      every button label in the export must sit on a real CTA
  order     the text bands must appear in the same order (a band = texts
            within 80px of each other; their internal order is free)
Writes results/format-bank/qc.json + qc.md (worst first) so the engine is
fixed where it fails most, and results/format-bank/<board>/NN-clean.qc.json.
"""
import argparse
import html as html_mod
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "sweep"))
sys.path.insert(0, str(HERE))
import board_pass as BP  # noqa: E402
import rebuild as RB  # noqa: E402
from capture import BOARD_PAGES, OUT as SHOTS, boards_in  # noqa: E402


def norm(s):
    s = html_mod.unescape(s or "")
    if "\\u" in s or "\\r" in s or "\\n" in s:
        try:
            s = s.encode("utf-8", "ignore").decode("unicode_escape", "ignore")
        except Exception:
            pass
    s = s.replace("\r", " ").replace("\n", " ")
    s = s.replace("’", "'").replace("—", "-").replace("–", "-").replace(" ", " ")
    s = re.sub(r"[™®]", "", s)
    return re.sub(r"[^a-z0-9$%]+", " ", s.lower()).strip()


def strip_tags(h, keep_alt=True):
    h = re.sub(r"<style.*?</style>", " ", h, flags=re.S)
    if keep_alt:
        h = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>', r" \1 ", h)    # copy baked into a picture counts as present
    h = re.sub(r"<[^>]+>", " ", h)
    return norm(h)


def qc_board(bank, board, brand):
    src_f = bank / "boards" / board / "Components.bundle.js"
    nodes, src = BP.load_nodes(src_f)
    B = RB.Bank(bank, brand)
    css = B.board_css(board)
    out = []
    for i, ab in enumerate(RB.artboards(nodes), 1):
        clean_f = SHOTS / board / f"{i:02d}-clean.html"
        if not clean_f.is_file():
            continue
        body = strip_tags(clean_f.read_text())
        kids = [n for n in nodes if BP.within(n, ab)]
        # every text the export carries
        texts_y = []
        for n in kids:
            ny = BP.abs_pos(n)[1]
            if n.get("text") and n["style"].get("fontSize"):
                t = RB.full_text(src, n) or n["text"]
                for line in re.split(r"\n+", t):
                    if len(norm(line)) >= 3:
                        texts_y.append((ny, norm(line)))
            elif n.get("text") and n["tag"] == "span" and len(norm(n["text"])) >= 3:
                texts_y.append((ny, norm(n["text"])))
        texts_y.sort(key=lambda t: t[0])
        texts = list(dict.fromkeys(t for _, t in texts_y))
        if not texts:
            continue                      # an empty frame is not an email
        missing = [t for t in texts if t not in body]
        # images the export places (recovered bitmaps)
        assets = [str(n["style"].get("className") or "") for n in kids
                  if css.get(str(n["style"].get("className") or ""), {}).get("kind") == "asset"]
        assets = [css[a]["file"] for a in assets if css[a].get("file")]
        # a bitmap parked at the artboard origin or thinner than 60px is a
        # stray layer, not a placed picture — reported apart, never counted
        ax0, ay0 = BP.abs_pos(ab)
        stray = set()
        for n in kids:
            rule = css.get(str(n["style"].get("className") or ""), {})
            if rule.get("kind") == "asset" and rule.get("file"):
                nx, ny = BP.abs_pos(n)
                nw = n["style"].get("width") or 0
                Wb_ = ab["style"].get("width") or 600
                if (nx - ax0 <= 0 and ny - ay0 <= 0) or nw < 60 or (nx - ax0) >= Wb_ - 10 or (nx - ax0) + nw <= 10:
                    stray.add(rule["file"])          # at the origin, a sliver, or parked off the canvas
        real_assets = [f for f in set(assets) if f not in stray or f in clean_f.read_text()]
        assets = real_assets
        placed = sum(1 for f in set(assets) if f in clean_f.read_text())
        # CTA labels: uppercase short texts sitting on button-sized rects
        ax, ay = BP.abs_pos(ab)
        Wb, Hb = (ab["style"].get("width") or 600), (ab["style"].get("height") or 0)
        def faint(c):
            m = re.match(r"rgba\([^)]*,\s*([\d.]+)\)", c or "")
            return bool(m) and float(m.group(1)) < 0.25
        rects = [n for n in kids if n["style"].get("backgroundColor") and not faint(n["style"].get("backgroundColor"))
                 and 44 <= (n["style"].get("height") or 0) <= 90
                 and 200 <= (n["style"].get("width") or 0) <= Wb - 100
                 and 0 <= BP.abs_pos(n)[0] - ax and BP.abs_pos(n)[0] - ax + (n["style"].get("width") or 0) <= Wb + 4
                 and 0 <= BP.abs_pos(n)[1] - ay <= Hb]
        # two same-size rects side by side are tiles, not buttons
        def twin(r):
            rx, ry = BP.abs_pos(r)
            return any(o is not r and abs(BP.abs_pos(o)[1] - ry) < 6 and abs((o["style"].get("width") or 0) - (r["style"].get("width") or 0)) < 4
                       and abs(BP.abs_pos(o)[0] - rx) >= (r["style"].get("width") or 0) - 4 for o in rects)
        rects = [r for r in rects if not twin(r)]
        labels = []
        for r in rects:
            rx, ry = BP.abs_pos(r); rx -= ax; ry -= ay
            rw = r["style"].get("width") or 0
            for t in kids:
                if t.get("text") and t["style"].get("fontSize") and (t["style"].get("fontSize") or 0) <= 26:
                    tx, ty = BP.abs_pos(t); tx -= ax; ty -= ay
                    tw = t["style"].get("width") or 0
                    # a button label is uppercase and centred on its button;
                    # sentence copy on a bar, or copy beside an icon, is not
                    caps = (t["style"].get("textTransform") == "uppercase") or (t["text"] == t["text"].upper() and any(ch.isalpha() for ch in t["text"]))
                    centred = (not tw) or abs((tx + tw / 2) - (rx + rw / 2)) < 40
                    if caps and centred and rx - 4 <= tx <= rx + rw and ry - 4 <= ty <= ry + (r["style"].get("height") or 0):
                        labels.append(norm(t["text"]))
        labels = [l for l in dict.fromkeys(labels) if l]
        html_txt = clean_f.read_text()
        cta_html = re.findall(r'text-transform:uppercase;color:[^"]*">([^<]+)</a>', html_txt)
        cta_norm = [norm(c) for c in cta_html]
        ctas_missing = [l for l in labels if l not in cta_norm]
        # order of the first texts
        # order: walk the rebuild forward; a text is in order if it appears
        # after the previous one. Ties at one y (a block the export split)
        # count as one group, so their internal order is free.
        # reading order is judged on the live copy only (baked alt text sits
        # wherever its picture sits)
        body_live = strip_tags(clean_f.read_text(), keep_alt=False)
        groups, last_y = [], None
        for y, t in texts_y:
            if t not in body_live:
                continue
            if last_y is not None and abs(y - last_y) < 80:      # one band
                groups[-1].append(t)
            else:
                groups.append([t])
            last_y = y
        cursor, inversions = 0, 0
        for grp in groups[:12]:
            hits = [body_live.find(t, cursor) for t in grp]
            hits = [h for h in hits if h != -1]
            if not hits:
                inversions += 1
                continue
            cursor = max(hits)
        order_ok = inversions == 0
        score = (len(texts) - len(missing)) / max(1, len(texts))
        rec = dict(board=board, i=i, w=int(ab["style"].get("width") or 0), h=int(ab["style"].get("height") or 0),
                   texts=len(texts), missing=missing[:12], n_missing=len(missing),
                   assets=len(set(assets)), placed=placed, ctas=labels, ctas_missing=ctas_missing,
                   order_ok=order_ok, text_score=round(score, 3))
        out.append(rec)
        (SHOTS / board / f"{i:02d}-clean.qc.json").write_text(json.dumps(rec, indent=1) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--board", default=None)
    ap.add_argument("--brand", required=True)
    a = ap.parse_args()
    bank = Path(a.bank)
    allrec = []
    for b in ([a.board] if a.board else boards_in(a.bank)):
        allrec += qc_board(bank, b, a.brand)
    allrec.sort(key=lambda r: (r["text_score"], -(r["assets"] - r["placed"])))
    (SHOTS / "qc.json").write_text(json.dumps(allrec, indent=1) + "\n")
    n = len(allrec)
    perfect = sum(1 for r in allrec if not r["n_missing"] and r["placed"] == r["assets"] and not r["ctas_missing"] and r["order_ok"])
    md = [f"# QC — {n} emails", "",
          f"- text complete: {sum(1 for r in allrec if not r['n_missing'])}/{n}",
          f"- all recovered images placed: {sum(1 for r in allrec if r['placed'] == r['assets'])}/{n}",
          f"- all CTAs present: {sum(1 for r in allrec if not r['ctas_missing'])}/{n}",
          f"- order intact: {sum(1 for r in allrec if r['order_ok'])}/{n}",
          f"- **clean on every check: {perfect}/{n}**", "", "## Worst first", ""]
    for r in allrec[:40]:
        md.append(f"- {r['board']} #{r['i']:02d} · text {r['text_score']:.0%} ({r['n_missing']} missing) · images {r['placed']}/{r['assets']} · "
                  f"CTAs missing {len(r['ctas_missing'])} · order {'ok' if r['order_ok'] else 'OFF'}")
        for m in r["missing"][:4]:
            md.append(f"    - missing: “{m[:80]}”")
        for c in r["ctas_missing"][:3]:
            md.append(f"    - CTA missing: “{c}”")
    (SHOTS / "qc.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:8]))


if __name__ == "__main__":
    main()
