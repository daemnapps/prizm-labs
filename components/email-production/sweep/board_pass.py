#!/usr/bin/env python3
"""The sweep, step 2: one full pass over one board. (Handoff missions 1+2.)

    python3 sweep/board_pass.py --bank <format-bank> --board jan-2025 \
        --out runs/email-production/<brand>/facts-<YYYY-MM-DD>/email-sms/design-formats

Parses the board's pre-transpiled React bundle into an element tree, finds
every email artboard, measures it fully (type, images, grounds, primitives),
and runs the handoff's artifact detectors:

  - dead image boxes  — large solid rectangles with no text and no image,
    the baked-in remains of dropped fills (handoff sweep item 2)
  - text overlaps     — absolutely-positioned text boxes that intersect
    heavily (handoff sweep item 1)
  - missing assets    — patch.json restorations whose file is absent
    (includes the two known lost assets, handoff sweep item 3)

Writes sweep/<board>.json + <board>.md into --out, which may never sit under
brands/ (K2 (brands write wall)): write it in a run folder and a person folds
it into the brand's design-formats home. Deterministic, no model.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import refuse_brand_write  # noqa: E402

CALL = "React.createElement("
STYLE_KEYS = re.compile(
    r'(left|top|width|height|fontSize|opacity|fontWeight): (-?[\d.]+)|'
    r'(fontFamily|backgroundColor|fontStyle|backgroundImage|background|boxShadow|className|textTransform|color|textAlign|letterSpacing|lineHeight|borderRadius|transform): "((?:[^"\\]|\\.)*)"')



def load_nodes(src_file):
    """The node list for a board: parsed from Components.bundle.js, or read
    from a sibling nodes.json when the board came from a .fig file
    (sweep/fig_intake.py). Both give the same shape: tag / style / text,
    with parent links."""
    import json as _json
    from pathlib import Path as _P
    src_file = _P(src_file)
    nj = src_file.parent / "nodes.json"
    if nj.is_file():
        raw = _json.loads(nj.read_text())
        nodes = []
        for d in raw:
            nodes.append({"tag": d.get("tag", "div"), "style": d.get("style", {}), "text": d.get("text"), "parent": None, "_pi": d.get("_parent")})
        for n in nodes:
            pi = n.pop("_pi", None)
            n["parent"] = nodes[pi] if pi is not None else None
        return nodes, ""
    src = src_file.read_text(errors="replace")
    return parse(src), src


def parse(src):
    """All createElement calls -> flat node list with parent links."""
    nodes = []

    def walk(i, parent):
        while True:
            j = src.find(CALL, i)
            if j == -1:
                return
            depth_end = match_paren(src, j + len(CALL) - 1)
            if depth_end == -1:
                return
            inner = src[j + len(CALL): depth_end]
            i = depth_end
            node = make_node(inner, parent)
            if node is not None:
                nodes.append(node)
                # recurse into this call's children region only once: the
                # scanner naturally visits nested calls later in the stream,
                # so instead of true recursion we track parents by spans.
            if j > 10_000_000:
                return

    def match_paren(s, open_idx):
        depth, i, n = 0, open_idx, len(s)
        in_str = None
        while i < n:
            c = s[i]
            if in_str:
                if c == "\\":
                    i += 2
                    continue
                if c == in_str:
                    in_str = None
            elif c in "\"'`":
                in_str = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    # Simpler robust approach: record every call with its span, then assign
    # parents by span containment.
    spans = []
    i = 0
    while True:
        j = src.find(CALL, i)
        if j == -1:
            break
        end = match_paren(src, j + len(CALL) - 1)
        if end == -1:
            break
        spans.append((j, end))
        i = j + len(CALL)
    spans.sort()
    stack = []
    for (start, end) in spans:
        while stack and stack[-1][1] < start:
            stack.pop()
        parent = stack[-1][2] if stack else None
        node = make_node(src[start + len(CALL): min(end, start + len(CALL) + 4000)],
                         parent)
        node["span"] = (start, end)
        nodes.append(node)
        stack.append((start, end, node))
    return nodes


def own_props(inner):
    """The call's OWN props object — brace-matched, so nested children's
    styles can never bleed into the parent (the pass-1 bug)."""
    start = inner.find("{")
    if start == -1:
        return ""
    depth, i, in_str = 0, start, None
    while i < len(inner):
        c = inner[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif c in "\"'`":
            in_str = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return inner[start:i + 1]
        i += 1
    return inner[start:start + 2500]


def make_node(inner, parent):
    tagm = re.match(r'\s*"?([A-Za-z][A-Za-z0-9]*)"?\s*,', inner)
    node = {"tag": tagm.group(1) if tagm else "?", "parent": parent, "style": {},
            "text": None}
    props = own_props(inner)
    for m in STYLE_KEYS.finditer(props):
        if m.group(1):
            node["style"][m.group(1)] = float(m.group(2))
        else:
            node["style"][m.group(3)] = m.group(4)
    after = inner[inner.find(props) + len(props):] if props else inner
    tm = re.match(r'\s*,\s*"((?:[^"\\]|\\.){2,600})"', after)
    if tm:
        node["text"] = tm.group(1)
    return node


def _matrix(st):
    """transform: matrix(a,b,c,d,tx,ty) -> (a, d, tx, ty); identity if none."""
    m = re.search(r"matrix\(\s*(-?[\d.]+),\s*-?[\d.]+,\s*-?[\d.]+,\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)\)", st.get("transform") or "")
    if not m:
        m2 = re.search(r"translate\(\s*(-?[\d.]+)px?,\s*(-?[\d.]+)px?\)", st.get("transform") or "")
        return (1.0, 1.0, float(m2.group(1)), float(m2.group(2))) if m2 else (1.0, 1.0, 0.0, 0.0)
    return float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))


def _full_matrix(st):
    """transform as a 2x3 affine (a, b, c, d, tx, ty); identity if none"""
    m = re.search(r"matrix\(\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)\)", st.get("transform") or "")
    if m:
        return tuple(float(v) for v in m.groups())
    m2 = re.search(r"translate\(\s*(-?[\d.]+)px?,\s*(-?[\d.]+)px?\)", st.get("transform") or "")
    if m2:
        return (1.0, 0.0, 0.0, 1.0, float(m2.group(1)), float(m2.group(2)))
    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _mul(p, q):
    """p ∘ q for 2x3 affines (apply q, then p)"""
    a1, b1, c1, d1, e1, f1 = p; a2, b2, c2, d2, e2, f2 = q
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2, a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def affine(node):
    """the node's full transform to the page: every ancestor's left/top and
    transform (rotation, scale, mirror) composed, outermost first"""
    chain = []
    n = node
    while n:
        chain.append(n); n = n["parent"]
    M = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for n in reversed(chain):
        st = n["style"]
        T = (1.0, 0.0, 0.0, 1.0, float(st.get("left", 0) or 0), float(st.get("top", 0) or 0))
        M = _mul(_mul(M, T), _full_matrix(st))
    return M


def bbox(node):
    """axis-aligned box of the node's own rect on the page, with any
    rotation, scale or mirror in the chain applied: (x, y, w, h)"""
    st = node["style"]
    w, h = float(st.get("width") or 0), float(st.get("height") or 0)
    a, b, c, d, e, f = affine(node)
    pts = [(a * px + c * py + e, b * px + d * py + f) for px, py in ((0, 0), (w, 0), (0, h), (w, h))]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def abs_pos(node):
    """Position on the page: left/top up the chain, plus any transform the
    export used to place (or mirror) a layer. A mirrored layer (a = -1)
    occupies [tx - width, tx]."""
    x = y = 0.0
    n = node
    while n:
        st = n["style"]
        a, d, tx, ty = _matrix(st)
        x += (st.get("left", 0) or 0) + (tx - (st.get("width") or 0) if a < 0 else tx)
        y += (st.get("top", 0) or 0) + (ty - (st.get("height") or 0) if d < 0 else ty)
        n = n["parent"]
    return x, y


def within(node, board):
    n = node["parent"]
    while n:
        if n is board:
            return True
        n = n["parent"]
    return False


SOLIDS = {"rgb(0,0,0)", "rgb(255,255,255)", "rgb(242,246,234)", "rgb(8,8,8)",
          "rgb(46,46,46)", "rgb(217,217,217)"}


def pass_board(bank, outdir, board_slug):
    bdir = bank / "boards" / board_slug
    src = (bdir / "Components.bundle.js").read_text(errors="replace")
    nodes = parse(src)
    def email_sized(n):
        return (550 <= (n["style"].get("width") or 0) <= 820
                and (n["style"].get("height") or 0) >= 700)

    def has_email_ancestor(n):
        p = n["parent"]
        while p:
            if email_sized(p):
                return True
            p = p["parent"]
        return False

    candidates = [n for n in nodes if email_sized(n) and not has_email_ancestor(n)]
    # CALIBRATION (pass 2): the census registry anchors WHICH nodes are
    # emails — match candidates to registered (w,h) pairs, taking at most as
    # many nodes of a size as the registry carries. Everything else is an
    # interior section, not an email. measured ⊆ registered, by construction.
    reg_f = outdir / "census.json"
    if reg_f.is_file():
        reg = [x for x in json.loads(reg_f.read_text())["emails"]
               if x["board"] == board_slug]
        pool = [dict(x) for x in reg]          # consumable copies
        picked = []
        for n in sorted(candidates, key=lambda n: (abs_pos(n)[1], abs_pos(n)[0])):
            w = n["style"].get("width") or 0
            h = n["style"].get("height") or 0
            hit = next((x for x in pool
                        if abs(x["w"] - w) <= 3 and abs(x["h"] - h) <= 6), None)
            if hit:
                pool.remove(hit)
                n["_census_name"] = hit["name"]
                picked.append(n)
        artboards = picked
    else:
        artboards = candidates
    patch = {}
    pf = bdir / "patch.json"
    if pf.is_file():
        patch = json.loads(pf.read_text())
    missing_assets = sorted({g["file"] for g in patch.get("geo", [])
                             if not (bdir / "assets" / g["file"]).is_file()})

    emails, artifacts = [], []
    for ab in artboards:
        kids = [n for n in nodes if within(n, ab)]
        texts = [n for n in kids if n["text"] and n["style"].get("fontSize")]
        fonts = Counter()
        for n in texts:
            fam = n["style"].get("fontFamily", "?").split(",")[0].strip('"')
            fonts[fam] += 1
        sizes = [n["style"]["fontSize"] for n in texts]
        images = [n for n in kids if "backgroundImage" in n["style"]
                  or "url(" in str(n["style"].get("background", ""))]
        # dead image boxes
        dead = []
        for n in kids:
            st = n["style"]
            w, h = st.get("width") or 0, st.get("height") or 0
            if (w >= 180 and h >= 120 and st.get("backgroundColor") in SOLIDS
                    and "backgroundImage" not in st
                    and not any(t for t in texts
                                if t is not n and overlap_frac(n, t) > 0.5)):
                dead.append(f"{int(w)}x{int(h)} {st['backgroundColor']}")
        # text overlaps
        overlaps = 0
        boxes = []
        for n in texts:
            x, y = abs_pos(n)
            w = n["style"].get("width") or len(n["text"]) * n["style"]["fontSize"] * 0.5
            h = n["style"].get("height") or n["style"]["fontSize"] * 1.25
            boxes.append((x, y, w, h))
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                if rect_overlap(boxes[a], boxes[b]) > 0.45:
                    overlaps += 1
        name = ab.get("_census_name") or ab["style"].get("data-name") or \
            f"artboard@{int(ab['style'].get('left', 0))},{int(ab['style'].get('top', 0))}"
        e = dict(name=name, w=int(ab["style"]["width"]), h=int(ab["style"]["height"]),
                 bg=ab["style"].get("backgroundColor", ""),
                 texts=len(texts), images=len(images),
                 serif_uses=sum(v for k, v in fonts.items() if "GT Super" in k or "Gt Super" in k),
                 sans_uses=sum(v for k, v in fonts.items() if "Untitled" in k),
                 other_fonts={k: v for k, v in fonts.items()
                              if "GT Super" not in k and "Untitled" not in k and k != "?"},
                 max_font=max(sizes) if sizes else 0,
                 dead_boxes=dead, text_overlaps=overlaps)
        emails.append(e)
        if dead:
            artifacts.append(f"{name}: {len(dead)} dead image box(es) — {', '.join(dead[:4])}")
        if overlaps:
            artifacts.append(f"{name}: {overlaps} heavy text overlap(s)")
    return emails, artifacts, missing_assets


def overlap_frac(n, t):
    ax, ay = abs_pos(n)
    bx, by = abs_pos(t)
    aw, ah = n["style"].get("width") or 0, n["style"].get("height") or 0
    bw = t["style"].get("width") or len(t["text"] or "") * (t["style"].get("fontSize") or 12) * 0.5
    bh = t["style"].get("height") or (t["style"].get("fontSize") or 12) * 1.25
    return rect_overlap((ax, ay, aw, ah), (bx, by, bw, bh))


def rect_overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    small = min(aw * ah, bw * bh) or 1
    return (ix * iy) / small


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--board", required=True)
    a = ap.parse_args()
    outdir = refuse_brand_write(a.out)
    bank = Path(a.bank).expanduser()
    emails, artifacts, missing = pass_board(bank, outdir, a.board)
    # The census (vfs exact transcriptions) is the REGISTRY — names and counts
    # are anchored there; the bundle pass adds deep measurement where its
    # geometry matches. Two sources, one honest join.
    census_f = outdir / "census.json"
    registered = []
    if census_f.is_file():
        registered = [x for x in json.loads(census_f.read_text())["emails"]
                      if x["board"] == a.board]
    reg_sizes = {(x["w"], x["h"]) for x in registered}
    for e in emails:
        e["in_census"] = (e["w"], e["h"]) in reg_sizes
    matched = sum(1 for e in emails if e["in_census"])
    sw = outdir / "sweep"
    sw.mkdir(exist_ok=True)
    (sw / f"{a.board}.json").write_text(json.dumps(
        dict(board=a.board, registered=len(registered), measured=len(emails),
             census_matched=matched, emails=emails, artifacts=artifacts,
             missing_assets=missing), indent=1) + "\n")
    L = [f"# Sweep — {a.board}", "",
         f"{len(emails)} emails measured · {len(artifacts)} artifact finding(s) · "
         f"{len(missing)} missing asset(s)", ""]
    if missing:
        L += ["## Missing assets (placeholders stay, per the handoff)", ""]
        L += [f"- {x}" for x in missing] + [""]
    if artifacts:
        L += ["## Artifacts to fix", ""] + [f"- {x}" for x in artifacts] + [""]
    L += ["## Emails", "", "| Email | Size | Texts | Images | Serif | MaxFont | Dead | Overlaps |",
          "|---|---|---|---|---|---|---|---|"]
    for e in emails:
        L.append(f"| {e['name']} | {e['w']}×{e['h']} | {e['texts']} | {e['images']} | "
                 f"{e['serif_uses']} | {int(e['max_font'])} | {len(e['dead_boxes'])} | {e['text_overlaps']} |")
    (sw / f"{a.board}.md").write_text("\n".join(L) + "\n")
    print(f"{a.board}: {len(emails)} emails · {len(artifacts)} artifacts · "
          f"{len(missing)} missing assets")


if __name__ == "__main__":
    main()
