#!/usr/bin/env python3
"""The sweep — every email in the bank rebuilt as clean HTML on the bedrock,
from its own exact transcription: its text, its type, its grounds, its
images. This is the polish pass the owner asked for (2026-09-02: "run through
EVERY SINGLE FILE and polish each … pixel perfect like a true email designer
would establish").

    python3 sweep/rebuild.py --bank <format-bank dir> [--board jul-2025] [--only 2,5]

What "polish" means here, per email:
  - the layered Figma export (absolute-positioned boxes, font-metric drift,
    clipped lines, leftover solid boxes) becomes a real table-based email:
    text wraps, nothing clips, every block sits on the brand grid
  - every bitmap the bank recovered is placed back at its real size; every
    lost one becomes the bank's own striped IMAGE w×h frame — or the store's
    real product photo when the copy names the product
  - the wordmark is the brand's vector, coloured for the ground it sits on
  - the shared modules (values bar, nav, footer, social row) are the real
    modules, not what the export happened to keep
Out, per board: results/format-bank/<board>/NN-clean.html and a QA page
qa.html — original picture beside the rebuild, with the issues found.
"""
import argparse
import base64
import html
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "sweep"))
sys.path.insert(0, str(HERE))
import board_pass as BP  # noqa: E402
from capture import BOARD_PAGES, OUT as SHOTS, URLBASE, boards_in  # noqa: E402
from paths import WORKSPACE  # noqa: E402

SERIF = "'GT Super Display', 'GT Super Ds Trial', Georgia, 'Times New Roman', serif"
SANS = "'Untitled Sans', Helvetica, Arial, sans-serif"
INK_DARK = "rgb(242,246,234)"        # the light ink, for dark grounds
INK_LIGHT = "rgb(6,43,20)"           # the dark ink, for light grounds
SAGE = "rgb(199,207,173)"            # the accent / button fill


def _hex_rgb(v):
    v = str(v or "").strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", v)
    return f"rgb({int(m.group(1)[0:2], 16)},{int(m.group(1)[2:4], 16)},{int(m.group(1)[4:6], 16)})" if m else v


def set_bedrock(brand):
    """The faces and inks the rebuild renders with come from the brand's
    design bedrock (email-sms/design-formats/components.json); the defaults
    above are Brand B's and stand when a brand has not written its own."""
    global SERIF, SANS, INK_DARK, INK_LIGHT, SAGE
    f = WORKSPACE / "brands" / brand / "email-sms" / "design-formats" / "components.json"
    if not f.is_file():
        return
    try:
        c = json.loads(f.read_text())
    except ValueError:
        return
    t = c.get("typography") or {}
    p = c.get("palette") or {}
    fb = (c.get("formats_bedrock") or {}).get("cta") or {}
    SANS = (t.get("sans") or t.get("stack") or SANS).replace('"', "'")       # style attributes are double-quoted
    SERIF = (t.get("serif") or t.get("display_stack") or SERIF).replace('"', "'")
    if p.get("ink"):
        light_ink = _hex_rgb(p["ink"])          # the ink named for the brand's usual ground
        ground = _hex_rgb(p.get("canvas") or p.get("ground") or "#ffffff")
        # decide which is the dark and which the light ink by the brand's ground
        if is_dark(ground):
            INK_DARK, INK_LIGHT = light_ink, _hex_rgb(p.get("type") or p.get("ink_on_light") or "#111111")
        else:
            INK_LIGHT, INK_DARK = light_ink, _hex_rgb(p.get("ink_on_dark") or "#ffffff")
    SAGE = _hex_rgb(fb.get("fill") or p.get("cta_bg") or p.get("accent") or SAGE)
def product_words(brand):
    """The product names a brief may use for this brand, and the store handle each maps to —
    brand data, read from brands/<brand>/email-sms/product-words.json
    (shape: brands/_TEMPLATE/email-sms/product-words.json). Returns (regex or None, {key: handle})."""
    f = WORKSPACE / "brands" / brand / "email-sms" / "product-words.json"
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError):
        return None, {}
    words = [w for w in d.get("words", []) if w]
    rx = re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.I) if words else None
    return rx, d.get("handles", {})



def e(s):
    return html.escape(str(s if s is not None else ""))


def hexc(rgb):
    m = re.search(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", rgb or "")
    return "#%02x%02x%02x" % tuple(int(v) for v in m.groups()) if m else (rgb or "#000000")


def is_dark(rgb):
    m = re.search(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", rgb or "")
    if not m:
        return True
    r, g, b = map(int, m.groups())
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128


ANNOTATION_FACES = ("Instrument Sans", "Spline Sans", "Fraunces", "Roboto Mono", "SF Pro", "Figma Hand")


class Bank:
    def __init__(self, bank, brand):
        self.bank = bank
        ws = WORKSPACE
        sys.path.append(str(ws / "components" / "brandpath"))
        import brandpath as BP  # noqa: E402  brand-identity (was identity/) by plan name
        cands = [bank / "assets" / f"{brand}.svg", bank / "assets" / "brand-b.svg"] + sorted(BP.brand_path(brand, "brand-identity", root=ws / "brands").glob("*.svg"))
        self.logo_svg = next((c.read_text() for c in cands if c.is_file()), "")
        pi = WORKSPACE / "brands" / brand / "products" / "images.json"
        self.products = json.loads(pi.read_text())["products"] if pi.is_file() else {}
        self.product_rx, self.product_handles = product_words(brand)
        self.css = {}
        # the brand's own faces (from its design bedrock) — copy set in them is the email's
        self.brand_faces = ["GT Super", "Gt Super", "Untitled", "Test Untitled", "Inter", "Helvetica", "Arial"]
        try:
            comp = json.loads((WORKSPACE / "brands" / brand / "email-sms" / "design-formats" / "components.json").read_text())
            for v in (comp.get("typography") or {}).values():
                if isinstance(v, str):
                    self.brand_faces += [f.strip().strip('"') for f in v.split(",") if f.strip().strip('"') and len(f.strip()) < 40]
        except Exception:
            pass

    def board_css(self, board):
        if board not in self.css:
            m = {}
            f = self.bank / "boards" / board / "fig-assets.css"
            if f.is_file():
                for ln in f.read_text().splitlines():
                    mm = re.match(r"\.(fig-(?:asset|mask)-[0-9a-f-]+)\s*\{\s*(.*)\}", ln)
                    if mm:
                        url = re.search(r"url\(\./assets/([^)]+)\)", mm.group(2))
                        m[mm.group(1)] = dict(kind="mask" if "mask" in mm.group(1) else "asset",
                                              file=url.group(1) if url else None, rule=mm.group(2))
            self.css[board] = m
        return self.css[board]

    def logo(self, ink):
        svg = re.sub(r'fill="(?!none)[^"]*"', f'fill="{ink}"', self.logo_svg)
        svg = re.sub(r'<path(?![^>]*fill=)', f'<path fill="{ink}"', svg)
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

    def product_image(self, text):
        m = self.product_rx.search(text or "") if self.product_rx else None
        if not m:
            return None
        key = m.group(1).lower().replace(" ", "-")
        key = self.product_handles.get(key, key)
        rec = self.products.get(key)
        return (rec or {}).get("hero")


# ------------------------------------------------------------ extraction ---

def artboards(nodes):
    def email_sized(n):
        return 550 <= (n["style"].get("width") or 0) <= 820 and (n["style"].get("height") or 0) >= 500

    def has_anc(n):
        p = n["parent"]
        while p:
            if email_sized(p):
                return True
            p = p["parent"]
        return False
    return sorted([n for n in nodes if email_sized(n) and not has_anc(n)],
                  key=lambda n: (round(BP.abs_pos(n)[1] / 400), BP.abs_pos(n)[0]))


def unescape_u(raw):
    """\\uXXXX sequences the export left in the copy become their characters
    (surrogate pairs joined into one emoji); real characters are untouched."""
    if "\\u" not in raw and "\\x" not in raw:
        return raw
    def one(m):
        return chr(int(m.group(1), 16))
    out = re.sub(r"\\u([0-9a-fA-F]{4})", one, raw)
    out = re.sub(r"\\x([0-9a-fA-F]{2})", one, out)
    try:
        out = out.encode("utf-16", "surrogatepass").decode("utf-16", "ignore")
    except Exception:
        pass
    return out


def full_text(src, n):
    """Every string the call passes as a child, in order — a paragraph the
    export split into several literals (and <br>s) comes back whole."""
    start, end = n.get("span", (None, None))
    if start is None:
        return ""
    seg = src[start:end]
    # skip the tag and the props object
    i = seg.find(",")
    depth, j, in_str = 0, seg.find("{", i), None
    if j == -1:
        return ""
    k = j
    while k < len(seg):
        c = seg[k]
        if in_str:
            if c == "\\":
                k += 2; continue
            if c == in_str:
                in_str = None
        elif c in "\"'`":
            in_str = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        k += 1
    rest = seg[k + 1:]
    out, depth, k, in_str, buf = [], 0, 0, None, None
    # depth 0 = the owner's own child strings; a nested createElement("span")
    # (a coloured or bold word) opens a level whose strings also belong to
    # this text; a nested props object {…} does not
    take = [True]                      # per open paren: are strings text here?
    brace = 0
    while k < len(rest):
        c = rest[k]
        if in_str:
            if c == "\\":
                buf.append(rest[k:k + 2]); k += 2; continue
            if c == in_str:
                if take[-1] and brace == 0:
                    out.append("".join(buf))
                in_str, buf = None, None
            else:
                buf.append(c)
        elif c == '"':
            in_str, buf = c, []
        elif c == "{":
            brace += 1
        elif c == "}":
            brace -= 1
        elif c == "(":
            head = rest[max(0, k - 24):k].rstrip()
            nxt = rest[k + 1:k + 7]
            if head.endswith("createElement") and nxt.startswith('"br"'):
                out.append("\n"); take.append(False)
            elif head.endswith("createElement") and (nxt.startswith('"span"') or nxt.startswith('"b"') or nxt.startswith('"i"') or nxt.startswith('"strong"') or nxt.startswith('"em"')):
                take.append(take[-1])
            else:
                take.append(False if head.endswith("createElement") else take[-1])
            depth += 1
        elif c == ")":
            depth -= 1
            if len(take) > 1:
                take.pop()
        k += 1
    # the tag string of a nested call ("span") is not text
    out = [o for o in out if o not in ("span", "b", "i", "strong", "em", "br")]
    raw = "".join(out)
    raw = raw.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\u2019", "’").replace("\\u2014", "—").replace('\\"', '"')
    raw = unescape_u(raw)
    return raw.encode("utf-8", "ignore").decode("utf-8").strip()


def text_of(n, nodes_by_parent):
    """A text span with child spans: the children carry the lines and the
    coloured words, in order."""
    parts = []
    if n.get("text"):
        parts.append(n["text"])
    for c in nodes_by_parent.get(id(n), []):
        if c["tag"] == "span" and c.get("text"):
            parts.append(c["text"])
    raw = "".join(parts)
    raw = raw.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\u2019", "’").replace("\\u2014", "—").replace('\\"', '"').replace("\\'", "'")
    raw = unescape_u(raw)
    return raw.strip()


def attach_labels(seq):
    """a CTA rect owns the uppercase label sitting on it — at the top
    level and inside every card alike"""
    out = []
    for b in seq:
        caps = b["kind"] == "text" and (b["upper"] or (b["text"] == b["text"].upper() and any(ch.isalpha() for ch in b["text"])))
        if caps and b["size"] <= 26 and len(b["text"]) <= 48:
            # the CTA this label sits on — a full-width image may lie
            # between them in the sorted stream
            owner = next((c for c in reversed(out[-14:]) if c["kind"] == "cta"
                          and c["y"] - 6 <= b["y"] <= c["y"] + c["h"] and c["x"] - 6 <= b["x"] <= c["x"] + c["w"]), None)
            if owner is not None and not owner.get("label"):
                owner["label"] = b["text"]
                continue
        if b["kind"] == "text" and out and out[-1]["kind"] == "text" and b["text"] == out[-1]["text"]:
            continue
        out.append(b)
    return out



class _TraceList(list):
    """SWEEP_TRACE=1: every block created or dropped in extract, printed"""
    def append(self, b):
        print("  + %-7s y%5d h%5d x%5d w%5d %s" % (b["kind"], b.get("y", 0), b.get("h") or 0, b.get("x", 0), b.get("w") or 0, (b.get("text") or b.get("file") or b.get("bg") or "")[:40].replace("\n", "|")))
        super().append(b)
    def remove(self, b):
        print("  - %-7s y%5d h%5d %s" % (b["kind"], b.get("y", 0), b.get("h") or 0, (b.get("text") or b.get("file") or b.get("bg") or "")[:40].replace("\n", "|")))
        super().remove(b)


def _ancestors(n):
    p_ = n["parent"]
    while p_:
        yield p_
        p_ = p_["parent"]


def extract(nodes, ab, css, bank, src=""):
    """The artboard as semantic blocks, top to bottom."""
    ax, ay = BP.abs_pos(ab)
    W = ab["style"].get("width") or 600
    kids = [n for n in nodes if BP.within(n, ab)]
    by_parent = defaultdict(list)
    for n in kids:
        by_parent[id(n["parent"])].append(n)
    blocks = _TraceList() if os.environ.get('SWEEP_TRACE') else []
    used_text = set()
    image_ids = set()
    disc_ids = set()
    for n in kids:
        st = n["style"]
        x, y = BP.abs_pos(n)
        y, x = y - ay, x - ax
        w, h = st.get("width") or 0, st.get("height") or 0
        if any(k_ in str(st.get("transform") or "") for k_ in ("matrix", "translate")) or any(
                "matrix" in str(p_["style"].get("transform") or "") for p_ in _ancestors(n)):
            # rotated, scaled or mirrored somewhere up the chain: use the true box
            bx_, by_, bw_, bh_ = BP.bbox(n)
            x, y = bx_ - ax, by_ - ay
            if w and h and n["tag"] != "span":
                w, h = bw_, bh_
            elif w and h:
                w, h = bw_, bh_
        fs = st.get("fontSize")
        has_kids_text = any(c["tag"] == "span" and c.get("text") for c in by_parent.get(id(n), []))
        short = n.get("text") and len(n["text"]) <= 48
        fam_s = str(st.get("fontFamily", ""))
        if fs and fam_s and any(k in fam_s for k in ANNOTATION_FACES) and not any(k in fam_s for k in bank.brand_faces):
            continue                      # a board annotation (Instrument Sans etc.), not the email
        if fs and (n.get("text") or has_kids_text) and id(n) not in used_text and n["tag"] == "span" \
                and (st.get("width") or has_kids_text or short):
            # the outer span (with fontSize + width) owns its child spans
            txt = full_text(src, n) if src else ""
            kids_txt = text_of(n, by_parent)
            if len(kids_txt) > len(txt):
                txt = kids_txt
            for c in by_parent.get(id(n), []):
                used_text.add(id(c))
                for cc in by_parent.get(id(c), []):
                    used_text.add(id(cc))
            if not txt:
                continue
            txt = txt.replace('\\"', '"').replace("\\'", "'")     # escapes the export left in the copy
            fam = "serif" if ("GT Super" in str(st.get("fontFamily", "")) or "Gt Super" in str(st.get("fontFamily", ""))) else "sans"
            par = n.get("parent") or {}
            pst = par.get("style", {}) if isinstance(par, dict) else {}
            pm = re.search(r"matrix\(\s*(-?[\d.]+),\s*(-?[\d.]+),", str(pst.get("transform") or ""))
            if pm and abs(float(pm.group(2))) > 0.02 and 150 <= (pst.get("width") or 0) <= 320 and 44 <= (pst.get("height") or 0) <= 90 \
                    and len(txt.split()) <= 3 and (fs or 0) <= 40:
                px_, py_ = BP.abs_pos(par); px_ -= ax; py_ -= ay
                blocks.append(dict(y=py_, x=px_, w=pst["width"], h=pst["height"], kind="pill", text=txt.strip(),
                                   size=fs or 24, upper=True, color=st.get("color") or ""))
                continue
            words = txt.split()
            ticker = None
            for unit in (2, 3, 4):
                if len(words) >= unit * 3 and all(words[j] == words[j % unit] for j in range(len(words))):
                    ticker = " ".join(words[:unit]); break
            if ticker:
                blocks.append(dict(y=y, x=0, w=W, h=h or 40, kind="ticker", text=ticker, src_text=txt))
                continue
            fam = "serif" if ("GT Super" in str(st.get("fontFamily", "")) or "Gt Super" in str(st.get("fontFamily", ""))) else "sans"
            if (re.fullmatch(r"\d{1,2}", txt.strip()) and (w or 0) <= 90) or \
                    (re.fullmatch(r"(?i)(step|day|tip|myth|no\.?)\s*#?\s*\d{1,2}", txt.strip().replace("\n", " ")) and (w or 0) <= 130):
                blocks.append(dict(y=y, x=x, w=w or 60, h=h or 60, kind="badge", text=txt.strip().replace("\n", " "), src_text=txt.strip(), auto=False))
                continue
            first_kid = next((c for c in by_parent.get(id(n), []) if c["tag"] == "span" and c.get("text")), None)
            kids_sp = [c for c in by_parent.get(id(n), []) if c["tag"] == "span" and c.get("text") and c["text"].strip()]
            for c in kids_sp:
                if not c["style"].get("fontSize"):
                    c["style"]["fontSize"] = fs          # inherits the parent's size
            sizes = sorted(set(int(c["style"]["fontSize"]) for c in kids_sp))
            stacked = len(kids_sp) >= 2 and (max(BP.abs_pos(c)[1] for c in kids_sp) - min(BP.abs_pos(c)[1] for c in kids_sp)) > 6
            if len(sizes) >= 2 and stacked and (sizes[-1] - sizes[0]) >= 6:
                # stacked runs of different sizes: one block per run, in order
                runs = []
                for c in sorted(kids_sp, key=lambda c: BP.abs_pos(c)[1]):
                    cs = int(c["style"]["fontSize"]); ct = unescape_u(c["text"]).replace("\\n", "\n")
                    if runs and runs[-1][0] == cs:
                        runs[-1][1] += ("" if runs[-1][1].endswith("\n") or ct.startswith("\n") else "\n") + ct
                    else:
                        runs.append([cs, ct, BP.abs_pos(c)[1] - ay, c["style"].get("color") or st.get("color") or "", c["style"].get("fontWeight") or st.get("fontWeight")])
                for cs, ct, cy, ccol, cwt in runs:
                    if ct.strip():
                        blocks.append(dict(y=cy, x=x, w=w or W, h=int(cs * 1.25 * (ct.count("\n") + 1)), kind="text", text=ct.strip(), family=fam, size=cs,
                                           color=ccol, upper=(st.get("textTransform") == "uppercase"), italic=(st.get("fontStyle") == "italic"),
                                           weight=cwt, align=st.get("textAlign") or "", tracking=st.get("letterSpacing") or "", leading=st.get("lineHeight")))
                for c in by_parent.get(id(n), []):
                    used_text.add(id(c))
                continue
            # inline kids set bigger than the parent's own multi-line copy are
            # the copy's later lines at their own size: one run per size
            own = (n.get("text") or "")
            own_multi = ("\n" in own or "\u2028" in own or "\\u2028" in own or len(own.strip()) >= 40)
            own_fs = int(fs or min(int(c["style"]["fontSize"]) for c in kids_sp)) if kids_sp else int(fs or 0)
            # the whole text split at each inline kid: plain stretches keep the
            # parent's size, kids keep theirs — interleaving handled by position
            def _clean(t_):
                return unescape_u(t_ or "").replace("\\u2028", "\n").replace("\u2028", "\n").replace("\\n", "\n").replace("\\r", "")
            runs = []
            if kids_sp and all(c["style"].get("top") is None for c in kids_sp) \
                    and max(abs(int(c["style"]["fontSize"]) - own_fs) for c in kids_sp) >= 6:
                whole = _clean(txt); pos = 0
                for c in kids_sp:
                    ct = _clean(c["text"]); key_ = ct.strip(); idx = whole.find(key_, pos) if key_ else -1
                    if idx == -1:
                        continue
                    if idx > pos:
                        if whole[pos:idx].strip():
                            runs.append([own_fs, whole[pos:idx], st.get("color") or "", st.get("fontWeight")])
                        elif runs:
                            runs[-1][1] += whole[pos:idx]        # a line break between kids
                    end_ = idx + len(key_)
                    # keep the spacing the export had around the kid
                    while end_ < len(whole) and whole[end_] == " ":
                        end_ += 1
                    runs.append([int(c["style"]["fontSize"]), whole[idx:end_], c["style"].get("color") or st.get("color") or "", c["style"].get("fontWeight") or st.get("fontWeight")])
                    pos = end_
                if whole[pos:].strip():
                    runs.append([own_fs, whole[pos:], st.get("color") or "", st.get("fontWeight")])
                # a tiny kid (™, ®, a digit) belongs to the run around it
                fixed = []
                for r_ in runs:
                    if fixed and len(r_[1].strip()) <= 2:
                        fixed[-1][1] += r_[1]
                    elif len(r_[1].strip()) <= 2 and not fixed:
                        fixed.append([own_fs, r_[1], r_[2], r_[3]])
                    else:
                        fixed.append(list(r_))
                runs = fixed
                # merge neighbours of one size; neighbours on one line (no break
                # between them) are one line at the larger size
                merged_ = []
                for r_ in runs:
                    if merged_ and not merged_[-1][1].rstrip(" ").endswith("\n") and not r_[1].lstrip(" ").startswith("\n"):
                        # the previous run's last line and this run share a line
                        head, _, tail = merged_[-1][1].rpartition("\n")
                        if len(tail.strip()) <= 3 and head:
                            merged_[-1][1] = head + "\n"          # the earlier lines stay
                            r_ = [r_[0], tail + r_[1], r_[2], r_[3]]  # the "$" joins its number
                    same_line = (len(merged_[-1][1].strip()) <= 3 or len(r_[1].strip()) <= 3) and not merged_[-1][1].rstrip(" ").endswith("\n") and not r_[1].lstrip(" ").startswith("\n") if merged_ else False
                    if merged_ and (merged_[-1][0] == r_[0] or same_line):
                        if r_[0] > merged_[-1][0]:
                            merged_[-1][0], merged_[-1][2], merged_[-1][3] = r_[0], r_[2], r_[3]
                        merged_[-1][1] += r_[1]
                    else:
                        merged_.append(list(r_))
                runs = merged_
                if len(runs) >= 2 and "\n" not in whole.strip():
                    runs = []                       # a mixed one-liner stays whole
            if len(runs) >= 2:
                cy = y
                for cs, ct, ccol, cwt in runs:
                    ct = ct.strip("\n ").strip()
                    if ct:
                        lines = ct.count("\n") + 1
                        blocks.append(dict(y=cy, x=x, w=w or W, h=int(cs * 1.25 * lines), kind="text", text=ct, family=fam, size=cs,
                                           color=ccol, upper=(st.get("textTransform") == "uppercase"), italic=(st.get("fontStyle") == "italic"),
                                           weight=cwt, align=st.get("textAlign") or "", tracking=st.get("letterSpacing") or "", leading=st.get("lineHeight")))
                        cy += int(cs * 1.25 * lines) + 6
                for c in by_parent.get(id(n), []):
                    used_text.add(id(c))
                continue
            later_big = first_kid is not None and not stacked and any(c is not first_kid and c["tag"] == "span" and c.get("text")
                                                      and (c["style"].get("fontSize") or 0) >= (first_kid["style"].get("fontSize") or 0) - 2
                                                      for c in by_parent.get(id(n), []))
            if later_big:
                fs = max(fs, max((c["style"].get("fontSize") or 0) for c in by_parent.get(id(n), []) if c["tag"] == "span" and c.get("text")))
            if first_kid and not later_big and (first_kid["style"].get("fontSize") or 0) > fs + 4 and txt.startswith(first_kid["text"].strip()[:20]):
                title = first_kid["text"].strip()
                rest = txt[len(title):].strip()
                blocks.append(dict(y=y, x=x, w=w or W, h=h, kind="text", text=title, family=fam, size=first_kid["style"]["fontSize"],
                                   color=st.get("color") or "", upper=False, italic=False, weight=500,
                                   align=st.get("textAlign") or "", tracking="", leading=None))
                if rest:
                    blocks.append(dict(y=y + 2, x=x, w=w or W, h=h, kind="text", text=rest, family=fam, size=fs,
                                       color=st.get("color") or "", upper=(st.get("textTransform") == "uppercase"),
                                       italic=False, weight=st.get("fontWeight"), align=st.get("textAlign") or "",
                                       tracking="", leading=None))
                for c in by_parent.get(id(n), []):
                    used_text.add(id(c))
                continue
            blocks.append(dict(y=y, x=x, w=w or W, h=h, kind="text", text=txt, family=fam, size=fs,
                               color=st.get("color") or "", upper=(st.get("textTransform") == "uppercase"),
                               italic=(st.get("fontStyle") == "italic"), weight=st.get("fontWeight"),
                               align=st.get("textAlign") or "", tracking=st.get("letterSpacing") or "",
                               leading=st.get("lineHeight")))
            continue
        if n.get("text"):
            continue                      # a child span — folded into its parent
        cls = str(st.get("className") or "")
        bg = str(st.get("backgroundColor") or "")
        bgi = str(st.get("backgroundImage") or "") + str(st.get("background") or "")
        if not bg:
            mcol = re.fullmatch(r"\s*(rgba?\([^)]*\)|#[0-9a-fA-F]{3,8})\s*", str(st.get("background") or ""))
            if mcol:
                bg = mcol.group(1)
        rule = css.get(cls)
        if rule and rule["kind"] == "asset" and rule["file"]:
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="image", file=rule["file"], real=True))
            continue
        if rule and rule["kind"] == "mask" and rule["file"] and w >= W * 0.4 and h >= 60:
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="art", file=rule["file"], color=st.get("color") or ""))
            continue
        if rule and rule["kind"] == "mask" and rule["file"]:
            # a disc behind it? (a solid square/circle box holding this mask)
            disc = next((d for d in kids if d is not n and d["tag"] == "div" and (d["style"].get("backgroundColor") or "")
                         and 80 <= (d["style"].get("width") or 0) <= 220 and abs((d["style"].get("width") or 0) - (d["style"].get("height") or 0)) < 4
                         and BP.abs_pos(d)[0] - ax - 6 <= x <= BP.abs_pos(d)[0] - ax + (d["style"].get("width") or 0)
                         and BP.abs_pos(d)[1] - ay - 6 <= y <= BP.abs_pos(d)[1] - ay + (d["style"].get("height") or 0)), None)
            blk = dict(y=y, x=x, w=w, h=h, kind="icon", file=rule["file"], color=bg or INK_DARK)
            if disc is not None:
                blk.update(disc_bg=disc["style"]["backgroundColor"], disc_w=int(disc["style"]["width"]),
                           y=BP.abs_pos(disc)[1] - ay, x=BP.abs_pos(disc)[0] - ax)
                disc_ids.add(id(disc))
            blocks.append(blk)
            continue
        if n["tag"] == "svg" and w >= 90 and 20 <= h <= 60 and abs(x + w / 2 - W / 2) < 40:
            Hb = ab["style"].get("height") or 0
            top_ok = y < 300 and not any(b["kind"] == "logo" and b["y"] < 300 for b in blocks)
            foot_ok = y > Hb - 520 and not any(b["kind"] == "logo" and b["y"] > Hb - 520 for b in blocks)
            if top_ok or foot_ok:
                blocks.append(dict(y=y, x=x, w=w, h=h, kind="logo", color=st.get("color") or ""))
            continue
        if "linear-gradient" in bgi and "rgba(12,16,15,0.5)" in bgi and w >= 300 and 100 <= h <= 800:
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="glass"))
            continue
        def label_on(bx, by, bw, bh):
            def caps(t):
                # a button label is set in caps — or it is a short call on a pill
                # (a brand that sets its buttons in sentence case, radius ≥ 20)
                pill = str(st.get("borderRadius") or "").rstrip("px").replace(".", "").isdigit() and float(str(st.get("borderRadius")).rstrip("px")) >= 20
                short_call = len(t["text"].split()) <= 4 and len(t["text"]) <= 28
                return t["style"].get("textTransform") == "uppercase" or (t["text"] == t["text"].upper() and any(ch.isalpha() for ch in t["text"])) or (pill and short_call)
            return any(t["tag"] == "span" and t.get("text") and t["style"].get("fontSize")
                       and (t["style"].get("fontSize") or 0) <= 26 and caps(t)
                       and bx - 4 <= BP.abs_pos(t)[0] - ax <= bx + bw and by - 4 <= BP.abs_pos(t)[1] - ay <= by + bh
                       for t in kids)
        if bg and not bg.startswith("rgba") and 44 <= h <= 90 and 200 <= w <= W - 100 and label_on(x, y, w, h):
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="cta", bg=bg))
            continue
        if bg and not bg.startswith("rgba") and 34 <= h <= 64 and 110 <= w < 200 and label_on(x, y, w, h):
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="cta", bg=bg, small=True))     # a tile's own small button
            continue
        band_text = any(t["tag"] == "span" and t.get("text") and t["style"].get("fontSize")
                        and y - 2 <= BP.abs_pos(t)[1] - ay <= y + h for t in kids)
        if bg and w >= W - 20 and (h >= 150 or (30 <= h < 150 and band_text)):
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="ground", bg=bg))
            continue
        if "linear-gradient" in bgi and "rgba(12,16,15,0.5)" not in bgi and w >= W - 20 and h >= 150:
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="ground", bg=bgi.strip()))     # a gradient section
            continue
        if bg and w >= W - 120 and h <= 2:
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="divider", bg=bg))
            continue
        if id(n) in disc_ids:
            continue
        if bg in (SAGE, "rgb(187,199,158)") and 56 <= w <= 100 and abs(w - h) < 3 and str(st.get("borderRadius") or "").endswith("%"):
            num = next((c["text"].strip() for c in kids if c.get("text") and re.fullmatch(r"\d{1,2}", c["text"].strip())
                        and x - 2 <= BP.abs_pos(c)[0] - ax <= x + w and y - 2 <= BP.abs_pos(c)[1] - ay <= y + h), "")
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="badge", text=num or "1", src_text=num, auto=not num))
            continue
        inside_bounds = x >= -6 and y >= -6 and x + w <= W + 6
        big_square = w >= 560 and abs(w - h) < 12 and not inside_bounds      # a glow, half off the board
        if big_square:
            continue
        holds_text = any(t["tag"] == "span" and t["style"].get("fontSize") and
                         x - 4 <= BP.abs_pos(t)[0] - ax <= x + w and y - 4 <= BP.abs_pos(t)[1] - ay <= y + h
                         for t in kids)
        faint = bool(re.match(r"rgba\([^)]*,\s*0?\.(0\d|1\d|2[0-4])\)", bg or ""))
        grad = bgi if ("linear-gradient" in bgi and "rgba(12,16,15,0.5)" not in bgi) else ""
        fill = bg or grad
        if (fill or (n["tag"] == "svg" and st.get("color"))) and not faint and 150 <= w < 300 and h >= 100 and holds_text:
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="tile", bg=fill or st.get("color"),
                               radius=st.get("borderRadius")))
            continue
        if (fill or (n["tag"] == "svg" and st.get("color"))) and w >= 300 and 80 <= h <= 220 and w < W - 20 and holds_text \
                and (any(css.get(str(c["style"].get("className") or ""), {}).get("kind") == "mask" for c in kids
                         if x - 4 <= BP.abs_pos(c)[0] - ax <= x + 120 and y - 4 <= BP.abs_pos(c)[1] - ay <= y + h)):
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="row", bg=fill or st.get("color"), radius=st.get("borderRadius")))
            continue
        svg_icon = any(c["tag"] == "svg" and 30 <= (c["style"].get("width") or 0) <= 90
                       and x - 4 <= BP.abs_pos(c)[0] - ax <= x + 150 and y - 4 <= BP.abs_pos(c)[1] - ay <= y + h
                       for c in kids)
        if (fill or (n["tag"] == "svg" and st.get("color"))) and not faint and w >= 300 and 80 <= h <= 260 and w < W - 20 \
                and holds_text and svg_icon:
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="row", bg=fill or st.get("color"), radius=st.get("borderRadius"),
                               disc=True))
            continue
        Hab = ab["style"].get("height") or 10 ** 6
        if fill and not faint and w >= W - 80 and (h >= Hab * 0.5 or h >= 1200):
            blocks.append(dict(y=y, x=0, w=W, h=h, kind="ground", bg=fill))
            continue
        if (fill or (n["tag"] == "svg" and st.get("color"))) and not faint and w >= 300 and h >= 100 and w < W - 20 and holds_text:
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="panel", bg=fill or st.get("color"),
                               radius=st.get("borderRadius")))
            continue
        if (bg in BP.SOLIDS or (bg and w >= 180)) and w >= 150 and h >= 100 and inside_bounds and not holds_text:
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="image", file=None, real=False))
            continue
        def empty_tree(m):
            return all(not c.get("text") and not c["style"].get("backgroundColor") and not c["style"].get("className")
                       and c["tag"] == "div" and empty_tree(c) for c in by_parent.get(id(m), []))
        def inside_image_box(m):
            p_ = m["parent"]
            while p_ is not None and p_ is not ab:
                if id(p_) in image_ids:
                    return True
                p_ = p_["parent"]
            return False
        # an unfilled box that carries copy plus a badge or an icon is a card
        # whose background bitmap the export lost (the bank paints its
        # striped stand-in there): it gets the glass fill
        def holds_kind(pred):
            return any(pred(c) for c in kids if x - 4 <= BP.abs_pos(c)[0] - ax <= x + w and y - 4 <= BP.abs_pos(c)[1] - ay <= y + h)
        has_badge = holds_kind(lambda c: c.get("text") and re.fullmatch(r"\d{1,2}", c["text"].strip() or "") and (c["style"].get("width") or 99) <= 90)
        has_icon = holds_kind(lambda c: css.get(str(c["style"].get("className") or ""), {}).get("kind") == "mask")
        def in_text_box(m):
            p_ = m["parent"]
            while p_ is not None and p_ is not ab:
                ps = p_["style"]
                if not ps.get("backgroundColor") and 150 <= (ps.get("width") or 0) < W * 0.55 and (ps.get("height") or 0) >= 200:
                    return True
                p_ = p_["parent"]
            return False
        if not bg and not rule and 150 <= w < W * 0.55 and 200 <= h <= 700 and inside_bounds and holds_text \
                and not inside_image_box(n) and not in_text_box(n) and id(n) not in image_ids and n["tag"] == "div":
            image_ids.add(id(n))
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="glass", lost_card=True))
            continue
        if not bg and not rule and 300 <= w < W - 20 and 120 <= h <= 640 and inside_bounds and holds_text \
                and (has_badge or has_icon) and not inside_image_box(n) and id(n) not in image_ids:
            image_ids.add(id(n))
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="glass", lost_card=True))
            continue
        # a lost full-width hero the copy sits on: the frame lands after the
        # copy it carried (an email cannot overlay text on a lost picture)
        page_box = h >= (ab["style"].get("height") or 10 ** 6) * 0.6      # a container the size of the page is layout, not a picture
        if not bg and not rule and w >= W - 20 and h >= 400 and not page_box and inside_bounds and holds_text \
                and not inside_image_box(n) and id(n) not in image_ids and n["tag"] == "div":
            image_ids.add(id(n))
            own = [c for c in kids if c.get("text") and c["style"].get("fontSize")
                   and x - 4 <= BP.abs_pos(c)[0] - ax <= x + w and y - 4 <= BP.abs_pos(c)[1] - ay <= y + h]
            first_txt = min([BP.abs_pos(c)[1] - ay for c in own] or [y])
            if first_txt - y >= h * 0.4:
                # the copy sits at the foot of the picture: the picture stands above it
                blocks.append(dict(y=y, x=x, w=w, h=int(first_txt - y - 24), kind="image", file=None, real=False))
            else:
                # the copy sits on the picture's top: the frame lands after the
                # copy it carried (an email cannot overlay text on a lost picture)
                last_txt = max([BP.abs_pos(c)[1] - ay + (c["style"].get("height") or 40) for c in own
                                if BP.abs_pos(c)[1] - ay <= y + h * 0.6] or [y])
                blocks.append(dict(y=last_txt + 1, x=x, w=w, h=min(int(h * 0.55), 720), kind="image", file=None, real=False))
            continue
        if not bg and not rule and 150 <= w <= W and h >= 250 and not page_box and n["tag"] == "div" and empty_tree(n) \
                and inside_bounds and not holds_text and not inside_image_box(n):
            image_ids.add(id(n))
            # an empty sized box the bank paints its IMAGE placeholder over
            blocks.append(dict(y=y, x=x, w=w, h=h, kind="image", file=None, real=False))
            continue
    blocks.sort(key=lambda b: (round(b["y"] / 6), b["x"]))
    # step badges count in reading order, not drawing order
    n_badge = 0
    for b in blocks:
        if b["kind"] == "badge" and b.get("auto", True) and not re.fullmatch(r"\d{1,2}", b.get("src_text") or ""):
            n_badge += 1
            b["text"] = str(n_badge)
    # overlapping crops of one picture are one picture — keep the larger
    imgs = [b for b in blocks if b["kind"] == "image" and b.get("real")]
    for a in imgs:
        for c in imgs:
            if a is c or a not in blocks or c not in blocks:
                continue
            ox = max(0, min(a["x"] + a["w"], c["x"] + c["w"]) - max(a["x"], c["x"]))
            oy = max(0, min(a["y"] + a["h"], c["y"] + c["h"]) - max(a["y"], c["y"]))
            area_a, area_c = a["w"] * a["h"], c["w"] * c["h"]
            small, big = min(area_a, area_c) or 1, max(area_a, area_c) or 1
            # near-duplicates only: almost the same footprint, neither a
            # backdrop the other sits on (a product over a photo stays)
            if ox * oy / small >= 0.85 and small / big >= 0.4 and not (max(a["w"], c["w"]) >= W - 20 and min(a["w"], c["w"]) < W * 0.6):
                loser, keeper = (a, c) if area_a < area_c else (c, a)
                keeper.setdefault("merged", []).append(loser.get("file"))
                blocks.remove(loser)
    for k_, b_ in enumerate(blocks):
        b_["_ord"] = k_                    # drawing order in the export (later paints over earlier)
    # a picture parked beside the page (x beyond the width) is not on the page
    blocks = [b for b in blocks if not (b["kind"] == "image" and (b["x"] >= W - 10 or b["x"] + b["w"] <= 10))]
    # a phantom hero frame inside a painted section is not a picture
    grounds_ = [b for b in blocks if b["kind"] == "ground"]
    for b in list(blocks):
        if b["kind"] == "image" and not b.get("real") and b["w"] >= W - 20:
            if any(abs(g["y"] - b["y"]) <= 20 and abs(g["h"] - (b["h"] or 0)) <= 40 for g in grounds_):
                blocks.remove(b)              # the same box as the ground: not a picture
    # a button, copy or cut-out that a later-drawn photo or full-width ground
    # covers entirely was hidden in the design
    covers_ = [b for b in blocks if (b["kind"] == "image" and b.get("real") and b["w"] >= W * 0.6 and (b["h"] or 0) >= 300)
               or (b["kind"] == "ground" and b["w"] >= W - 20 and not str(b.get("bg", "")).startswith("rgba"))]
    for b in list(blocks):
        if b["kind"] in ("cta", "text", "image") and not b.get("layers"):
            for cv in covers_:
                if cv is not b and cv.get("_ord", -1) > b.get("_ord", 10 ** 9) and cv["x"] - 4 <= b["x"] and b["x"] + (b["w"] or 0) <= cv["x"] + cv["w"] + 4 \
                        and cv["y"] + 10 <= b["y"] and b["y"] + (b["h"] or 30) <= cv["y"] + (cv["h"] or 0) - 10:
                    blocks.remove(b); break
    # a picture that a later-drawn ground covers entirely was hidden in the design
    for b in list(blocks):
        if b["kind"] == "image" and b.get("real"):
            for g in grounds_:
                if g.get("_ord", -1) > b.get("_ord", 10 ** 9) and g["y"] - 4 <= b["y"] and b["y"] + (b["h"] or 0) <= g["y"] + g["h"] + 4 and g["w"] >= W - 20:
                    b["kind"] = "decor"; b["covered"] = True
                    break
    # A. small decorations laid over copy, and corner art behind the header,
    #    are not pictures of their own (they live in the export's render only)
    texts_ = [b for b in blocks if b["kind"] in ("text", "logo")]
    for b in list(blocks):
        if b["kind"] != "image" or not b.get("real"):
            continue
        small = b["w"] < 140 and (b["h"] or 0) < 140
        header_art = b["y"] < 150 and b["w"] < W - 20 and any(t["kind"] == "logo" and t["y"] < b["y"] + (b["h"] or 0) for t in texts_)
        over_copy = any(t["x"] < b["x"] + b["w"] and t["x"] + (t["w"] or 0) > b["x"] and t["y"] < b["y"] + (b["h"] or 0) and t["y"] + (t["h"] or 30) > b["y"] for t in texts_)
        behind_headline = False
        if b["w"] < W - 20 and not (b["w"] >= W * 0.4 or (b["h"] or 0) >= 300):
            area = max(1, b["w"] * (b["h"] or 1))
            for t in texts_:
                if t["kind"] == "text" and t["size"] >= 40:
                    ox = max(0, min(b["x"] + b["w"], t["x"] + (t["w"] or 0)) - max(b["x"], t["x"]))
                    oy = max(0, min(b["y"] + (b["h"] or 0), t["y"] + (t["h"] or 30)) - max(b["y"], t["y"]))
                    if ox * oy >= 0.25 * area:
                        behind_headline = True; break
        if (small and over_copy) or header_art or behind_headline:
            b["kind"] = "decor"
    # the same bitmap placed several times close together (a photo and its
    # crops) is one image — keep the largest
    seen_files = {}
    for b in list(blocks):
        if b["kind"] == "image" and b.get("file"):
            prev = seen_files.get(b["file"])
            if prev is not None and abs(prev["y"] - b["y"]) < 900 \
                    and prev["x"] < b["x"] + b["w"] and b["x"] < prev["x"] + prev["w"] \
                    and prev["y"] < b["y"] + (b["h"] or 0) and b["y"] < prev["y"] + (prev["h"] or 0):
                if b["w"] * b["h"] > prev["w"] * prev["h"]:
                    blocks.remove(prev); seen_files[b["file"]] = b
                else:
                    blocks.remove(b)
            else:
                seen_files[b["file"]] = b
    # buttons claim their labels first — a label a card could also reach
    # belongs to the button it sits on
    blocks = attach_labels(blocks)
    # a lost card lying inside another card is that card's copy box, not a card
    cards_all = [b for b in blocks if b["kind"] in ("glass", "panel")]
    for b in list(blocks):
        if b["kind"] == "glass" and b.get("lost_card"):
            for c in cards_all:
                if c is not b and c["x"] - 6 <= b["x"] and b["x"] + b["w"] <= c["x"] + c["w"] + 6 and c["y"] - 6 <= b["y"] and b["y"] + b["h"] <= c["y"] + c["h"] + 6:
                    blocks.remove(b); break
    # a card as tall as half the page is the page's ground (a panel) or a
    # decorative fade (glass) — never a content card
    Hab = ab["style"].get("height") or 10 ** 6
    for b in list(blocks):
        if b["kind"] in ("glass", "panel") and (b["h"] >= Hab * 0.45 or b["h"] >= 1400):
            if b["kind"] == "panel" and b.get("bg"):
                b.update(kind="ground", x=0, w=W)
            else:
                blocks.remove(b)
    # a card owns the texts and images sitting inside it — the smallest
    # card that holds a thing gets it, so nested cards never repeat copy
    taken = set()
    for card in sorted([b for b in blocks if b["kind"] in ("glass", "panel", "tile", "row")], key=lambda c: c["w"] * c["h"]):
        def overlap(t):
            top, bot = max(t["y"], card["y"]), min(t["y"] + (t["h"] or 30), card["y"] + card["h"])
            fits = (t["w"] or 0) <= card["w"] + 8          # copy wider than the card is not its copy
            lead = 90 if t["kind"] in ("badge", "icon") else 4   # a number or icon may hang off the left edge
            if t["kind"] == "image" and card["kind"] in ("glass", "panel") and (t["w"] or 0) < card["w"] * 1.1:
                # a product picture whose centre sits in the card is the card's picture, overhang or not
                cx_ = t["x"] + t["w"] / 2; cy_ = t["y"] + (t["h"] or 0) / 2
                return card["x"] - 10 <= cx_ <= card["x"] + card["w"] + 10 and card["y"] - 10 <= cy_ <= card["y"] + card["h"] + 10
            return fits and (bot - top) / max(1, (t["h"] or 30)) >= 0.5 and card["x"] - lead <= t["x"] <= card["x"] + card["w"]
        owned = ("text", "image", "icon", "badge") + (("cta",) if card["kind"] in ("glass", "panel", "tile") else ())
        inside = [t for t in blocks if t is not card and t["kind"] in owned and id(t) not in taken and overlap(t)]
        if card["kind"] == "tile":
            imgs = [t for t in inside if t["kind"] == "image" and card["x"] <= t["x"] + t["w"] / 2 <= card["x"] + card["w"]]
            others = [t for t in inside if t["kind"] == "image" and t not in imgs[:1]]
            card["dropped"] = [t["file"] for t in others if t.get("file")]
            for t in others:
                t["_in_card"] = True; taken.add(id(t))
            inside = [t for t in inside if t["kind"] != "image"] + imgs[:1]
        for t in inside:
            if t["kind"] == "image" and not t.get("real") and (card.get("lost_card") or (t["w"] or 0) >= card["w"] * 0.8):
                t["_in_card"] = True              # the card's own lost background, not content
                taken.add(id(t))
        inside = [t for t in inside if not (t["kind"] == "image" and not t.get("real") and t.get("_in_card"))]
        card["inside"] = sorted(inside, key=lambda t: t["y"])
        for t in inside:
            t["_in_card"] = True
            taken.add(id(t))
    cards_ = [b for b in blocks if b["kind"] in ("glass", "panel", "tile", "row")]
    for b in list(blocks):
        if b["kind"] == "image" and not b.get("real") and not b.get("_in_card"):
            for c in cards_:
                ox = max(0, min(b["x"] + b["w"], c["x"] + c["w"]) - max(b["x"], c["x"]))
                oy = max(0, min(b["y"] + (b["h"] or 0), c["y"] + c["h"]) - max(b["y"], c["y"]))
                if ox * oy >= 0.5 * b["w"] * max(1, b["h"] or 1):
                    b["_in_card"] = True          # a glow or shadow layer under the card
                    break
    blocks = [b for b in blocks if not b.get("_in_card")]

    seen_t = []
    for b in list(blocks):
        if b["kind"] in ("text", "pill"):
            if any(o["text"] == b["text"] and abs(o["y"] - b["y"]) < 6 and abs(o["x"] - b["x"]) < 6 for o in seen_t):
                blocks.remove(b)              # a shadow copy of the same words
            else:
                seen_t.append(b)
    out = attach_labels(blocks)
    for b in out:
        if b.get("inside"):
            b["inside"] = attach_labels(b["inside"])
    out = join_lines(out)
    return out, W, ab["style"].get("height") or 0, ab["style"].get("backgroundColor") or "rgb(12,16,15)"


def join_lines(blocks):
    """Texts sitting on one baseline side by side (a headline set in two
    faces, "Buy It" + "ONCE.") are one line. They join in x order; the
    line keeps the larger face and notes the mix for the spec."""
    out = []
    for b in sorted(blocks, key=lambda b: (b["y"], b["x"])):
        if (b["kind"] == "text" and out and out[-1]["kind"] == "text" and abs(out[-1]["y"] - b["y"]) < 10
                and "\n" not in out[-1]["text"] and "\n" not in b["text"] and len(b["text"]) <= 40 and len(out[-1]["text"]) <= 40
                and b["x"] >= out[-1]["x"] + (out[-1]["w"] or 0) - 30 and b["x"] <= out[-1]["x"] + (out[-1]["w"] or 0) + 40):
            a = out[-1]
            a["text"] = a["text"].rstrip() + " " + b["text"].lstrip()
            a["w"] = (b["x"] + (b["w"] or 0)) - a["x"]
            if b["size"] > a["size"]:
                a["size"], a["family"], a["italic"] = b["size"], b["family"], b.get("italic")
            a["mixed"] = True
            continue
        out.append(b)
    return out



def compose_heroes(blocks, W, H, shot, out_dir, board, i, tag=""):
    """Layered pictures — a backdrop, a product cut-out, a glow, an arch —
    stacked on one spot in the export are ONE picture in an email. Every
    cluster of overlapping top-level images becomes a single crop of the
    export's own render; small labels sitting on it are baked in and kept
    as the picture's alt text. A headline in the lower part of the cluster
    stays live copy: the crop stops above it."""
    if shot is None or not Path(shot).is_file():
        return blocks
    from PIL import Image
    page = None
    for b in list(blocks):
        if b["kind"] == "image" and b.get("real") and b["w"] >= W - 20 and b["y"] < 120 and (b["h"] or 0) >= (H or 10 ** 6) * 0.6:
            page = page or Image.open(shot).convert("RGB")
            src_ = out_dir / "assets" / (b.get("file") or "")
            try:
                edge = Image.open(src_).convert("RGB").resize((8, 8)) if src_.is_file() else None
            except Exception:
                edge = None
            if edge is None:
                gy0, gy1 = int(max(0, b["y"])), int(min(page.size[1], b["y"] + (b["h"] or 0)))
                edge = page.crop((0, gy0, page.size[0], gy1)).resize((8, 8))
            px = list(edge.getdata())
            r = sorted(p_[0] for p_ in px)[4]; gch = sorted(p_[1] for p_ in px)[4]; bch = sorted(p_[2] for p_ in px)[4]
            blocks.remove(b)
            blocks.append(dict(y=b["y"], x=0, w=W, h=(b["h"] or 0), kind="ground", bg=f"rgb({r},{gch},{bch})", from_backdrop=True,
                               backdrop_file=b.get("file")))
    imgs = [b for b in blocks if b["kind"] == "image"]
    # a lone wide photo with a headline laid on it composes on its own
    solo = [b for b in imgs if b.get("real") and b["w"] >= W * 0.6 and (b["h"] or 0) >= 500
            and any(t["kind"] == "text" and t["size"] >= 28 and b["y"] + 20 <= t["y"] <= b["y"] + (b["h"] or 0) - 60 for t in blocks)]
    if len(imgs) < 2 and not solo:
        blocks.sort(key=lambda b: (b["y"], b["x"]))
        return blocks

    def hit(a, c):
        if not (a["x"] < c["x"] + c["w"] - 4 and c["x"] < a["x"] + a["w"] - 4
                and a["y"] < c["y"] + (c["h"] or 0) - 4 and c["y"] < a["y"] + (a["h"] or 0) - 4):
            return False
        # two wide photos that barely touch are two scenes, not one
        if a.get("real") and c.get("real") and a["w"] >= W * 0.6 and c["w"] >= W * 0.6:
            oy = min(a["y"] + (a["h"] or 0), c["y"] + (c["h"] or 0)) - max(a["y"], c["y"])
            if oy < 0.15 * min(a["h"] or 1, c["h"] or 1):
                return False
        return True
    parent = {id(b): id(b) for b in imgs}

    def is_backdrop(m):
        return (m["h"] or 0) >= (H or 10 ** 6) * 0.6 or (m["y"] < 120 and (m["h"] or 0) > 900 and (m["h"] or 0) >= (H or 10 ** 6) * 0.45)

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]; k = parent[k]
        return k
    for a in imgs:
        for c in imgs:
            # a page backdrop joins a cluster but never links two pictures
            # that do not touch each other
            if a is not c and hit(a, c) and not (is_backdrop(a) and is_backdrop(c)):
                if is_backdrop(a) or is_backdrop(c):
                    continue
                parent[find(id(a))] = find(id(c))
    # every backdrop joins the cluster(s) it lies under; a backdrop under a
    # lone picture makes that picture a scene of its own (see below)
    for bd in [m for m in imgs if is_backdrop(m)]:
        touched = {find(id(c)) for c in imgs if c is not bd and not is_backdrop(c) and hit(bd, c)}
        if len(touched) == 1:
            parent[find(id(bd))] = touched.pop()
    groups = {}
    for b in imgs:
        groups.setdefault(find(id(b)), []).append(b)
    # a lost box whose render is one flat colour is a fill behind copy, not a picture
    for b in list(blocks):
        if b["kind"] == "image" and not b.get("real") and b["w"] < W - 20:
            page = page or Image.open(shot).convert("RGB")
            bx0, by0 = int(max(0, b["x"])), int(max(0, b["y"]))
            bx1, by1 = int(min(page.size[0], b["x"] + b["w"])), int(min(page.size[1], b["y"] + (b["h"] or 0)))
            if bx1 - bx0 > 20 and by1 - by0 > 20:
                sm = page.crop((bx0, by0, bx1, by1)).resize((12, 12))
                px = list(sm.getdata())
                spread = max(max(c) - min(c) for c in zip(*px))
                if spread < 24:
                    blocks.remove(b)
    k = 0
    for members in groups.values():
        members = [m for m in members if m in blocks]      # a picture already folded elsewhere is gone
        if len(members) < 2 and not (len(members) == 1 and members[0] in solo):
            continue
        # a layer the size of the page is a backdrop: it sits under the crop
        # but never sets its extent, and it is not a picture of its own
        def backdrop(m):
            # a layer is the page's backdrop only when it spans a good part of the page
            return (m["h"] or 0) >= (H or 10 ** 6) * 0.6 or (m["y"] < 120 and (m["h"] or 0) > 900 and (m["h"] or 0) >= (H or 10 ** 6) * 0.45)
        fg = [m for m in members if not backdrop(m)]
        bds = [m for m in members if backdrop(m)]
        if not fg:
            continue
        x0 = max(0, min(m["x"] for m in fg)); y0 = max(0, min(m["y"] for m in fg))
        x1 = min(W, max(m["x"] + m["w"] for m in fg)); y1 = min(H or 10 ** 6, max(m["y"] + (m["h"] or 0) for m in fg))
        on_gradient = any(b_["kind"] == "ground" and "gradient" in str(b_["bg"]) and b_["y"] - 4 <= y0 and y1 <= b_["y"] + b_["h"] + 4 for b_ in blocks)
        if not bds and not tag and ((x1 - x0) >= W * 0.6 or ((x1 - x0) >= W * 0.4 and on_gradient)):
            x0, x1 = 0, W                      # a hero this wide bleeds edge to edge
        if bds:
            # the backdrop shows around the foreground: the picture is the
            # full width, reaching up to the header and down to the copy
            bd_top = max(0, min(m["y"] for m in bds)); bd_bot = min(H or 10 ** 6, max(m["y"] + (m["h"] or 0) for m in bds))
            above = [t for t in blocks if t["kind"] in ("text", "cta", "logo", "ticker", "pill", "art") and t["y"] + (t["h"] or 30) <= y0 + 4 and (t["kind"] != "text" or t["size"] >= 18)]
            below = [t for t in blocks if t["kind"] in ("text", "cta", "logo", "ticker", "pill", "art") and t["y"] >= y1 - 40 and (t["kind"] != "text" or t["size"] >= 14)]
            y0 = max(bd_top, max([t["y"] + (t["h"] or 30) + 10 for t in above] + [bd_top]))
            y1 = min(bd_bot, min([t["y"] - 12 for t in below] + [bd_bot]))
            x0, x1 = 0, W
        # live copy, buttons and the wordmark are never baked into a picture:
        # anything of that kind in the upper part of the cluster pushes the
        # crop down below it; a headline or button in the lower part stops
        # the crop above it. Only small labels left inside get baked in.
        def fg_area(a, b_):
            return sum(max(0, min(m["y"] + (m["h"] or 0), b_) - max(m["y"], a)) * m["w"] for m in fg)
        for _ in range(6):
            live = [t for t in blocks if t["kind"] in ("text", "cta", "logo", "ticker", "pill", "art") and y0 - 4 <= t["y"] <= y1 and t["x"] < x1 and t["x"] + (t["w"] or 0) > x0
                    and (t["kind"] != "text" or t["size"] >= 28)]
            if not live:
                break
            t = sorted(live, key=lambda t: t["y"])[0]
            tb = t["y"] + (t["h"] or 30)
            # cut on the side that keeps more of the picture
            if fg_area(y0, t["y"]) >= fg_area(tb, y1):
                y1 = t["y"] - 12
            else:
                y0 = tb + 10
        # copy that only partly crosses the crop's edge is never cut in
        # half: the crop stops above it (bottom) or starts below it (top)
        for t in sorted([t for t in blocks if t["kind"] in ("text", "cta", "ticker", "pill") and t["x"] < x1 and t["x"] + (t["w"] or 0) > x0], key=lambda t: t["y"]):
            tb = t["y"] + (t["h"] or 30)
            if t["y"] < y1 - 4 and tb > y1 + 4 and t["y"] > y0 + 120:
                y1 = t["y"] - 12
            elif t["y"] < y0 - 4 and tb > y0 + 4 and tb < y1 - 120:
                y0 = tb + 10
        if y1 - y0 < 120:
            continue
        live = [t for t in blocks if t["kind"] in ("text", "cta", "logo") and y0 - 4 <= t["y"] <= y1 and t["x"] < x1 and t["x"] + (t["w"] or 0) > x0]
        texts = [t for t in live if t["kind"] == "text" and y0 <= t["y"] and t["y"] + (t["h"] or 30) <= y1 + 4]
        baked = [t for t in texts if t["size"] < 28]
        # a headline set over a real photo is how the design composed it: it
        # travels with the picture (and stays readable in the alt text)
        photos = [m for m in fg if m.get("real") and m["w"] >= W * 0.6]
        if page is None:
            page = Image.open(shot).convert("RGB")
        for t in [t for t in blocks if t["kind"] == "text" and t["size"] >= 28 and t not in baked]:
            host = next((m for m in photos if m["x"] - 4 <= t["x"] and t["x"] + (t["w"] or 0) <= m["x"] + m["w"] + 4
                         and m["y"] + 60 <= t["y"] and t["y"] + (t["h"] or 30) <= m["y"] + (m["h"] or 0) - 60), None)
            if host is not None:
                # only when the render shows a photo behind the words, not a flat ground
                tx0, ty0 = int(max(0, t["x"])), int(max(0, t["y"]))
                tx1, ty1 = int(min(page.size[0], t["x"] + (t["w"] or W))), int(min(page.size[1], t["y"] + (t["h"] or 30)))
                if tx1 - tx0 > 20 and ty1 - ty0 > 10:
                    sm = page.crop((tx0, ty0, tx1, ty1)).resize((16, 8))
                    px = list(sm.getdata())
                    lum = sorted(0.299 * a_ + 0.587 * b_ + 0.114 * c_ for a_, b_, c_ in px)
                    # the darkest third of the box: a photo varies there, a flat ground does not
                    dark = lum[:len(lum) // 3]
                    if dark and (dark[-1] - dark[0]) >= 28:
                        baked.append(t)
                        y0 = min(y0, max(0, t["y"] - 12))            # the crop reaches up to cover it
                        glyph_h = max(t["h"] or 30, t["size"] * 1.2 * (t["text"].count("\n") + 1))
                        y1 = max(y1, t["y"] + glyph_h + 10)          # never slice a baked headline
        # a headline the crop's bottom edge would slice keeps the crop above it
        for _ in range(4):
            cut = False
            for t in sorted([t for t in blocks if t["kind"] == "text" and t["size"] >= 28 and t not in baked
                             and t["x"] < x1 and t["x"] + (t["w"] or 0) > x0], key=lambda t: t["y"]):
                th = t["h"] or 30
                if t["y"] < y1 - 4 and t["y"] + th > y1 + 4 and t["y"] - 12 > y0 + 120:
                    y1 = t["y"] - 12; cut = True; break
            if not cut:
                break
        # a live button, wordmark, pill or ticker inside the box splits it:
        # the picture runs above and below, the element stays live between
        cuts = sorted([c for c in blocks if c["kind"] in ("cta", "logo", "pill", "ticker") and c["x"] < x1 and c["x"] + (c["w"] or 0) > x0
                       and c["y"] > y0 + 20 and c["y"] + (c["h"] or 40) < y1 - 20], key=lambda c: c["y"])
        segments, top_ = [], y0
        for c in cuts:
            segments.append((top_, c["y"] - 12)); top_ = c["y"] + (c["h"] or 40) + 10
        segments.append((top_, y1))
        if page is None:
            page = Image.open(shot).convert("RGB")
        made_any = False
        for sy0, sy1 in segments:
            if sy1 - sy0 < 120:
                continue
            # only a segment that actually holds picture layers becomes one
            if not any(m["y"] < sy1 and m["y"] + (m["h"] or 0) > sy0 for m in fg):
                continue
            # whatever copy this segment covers travels with it — the picture
            # shows those words already, so they never render twice
            seg_baked = [t for t in baked if t["y"] < sy1 and t["y"] + (t["h"] or 30) > sy0]
            for t in [t for t in blocks if t["kind"] == "text" and t not in seg_baked and t["x"] < x1 and t["x"] + (t["w"] or 0) > x0]:
                th = t["h"] or 30
                oy_ = max(0, min(t["y"] + th, sy1) - max(t["y"], sy0))
                if oy_ >= 0.7 * th:
                    seg_baked.append(t)
            crop = page.crop((int(x0), int(sy0), int(min(x1, page.size[0])), int(min(sy1, page.size[1]))))
            if crop.size[0] < 40 or crop.size[1] < 40:
                continue
            k += 1
            (out_dir / "assets").mkdir(parents=True, exist_ok=True)
            f = f"hero-{i:02d}-{tag}{k}.png"
            crop.save(out_dir / "assets" / f)
            seg_members = [m for m in members if m["y"] < sy1 and m["y"] + (m["h"] or 0) > sy0] or members
            comp = dict(y=sy0, x=int(max(0, x0)), w=crop.size[0], h=crop.size[1], kind="image", file=f, real=True,
                        layers=[(m.get("file") or "lost box") + (" (page backdrop)" if backdrop(m) else "") for m in seg_members],
                        merged=[m["file"] for m in members if m.get("file")] + [f_ for m in members for f_ in m.get("merged", [])],
                        alt=" · ".join(t["text"].replace("\n", " ") for t in sorted(seg_baked, key=lambda t: (t["y"], t["x"]))),
                        _ord=max([m.get("_ord", 0) for m in members] or [0]))
            for t in seg_baked:
                if t in blocks:
                    blocks.remove(t)
            # any other picture lying inside this crop is already in it
            for o in list(blocks):
                if o["kind"] == "image" and o is not comp and o not in members:
                    ox_ = max(0, min(o["x"] + o["w"], x1) - max(o["x"], x0)); oy_ = max(0, min(o["y"] + (o["h"] or 0), sy1) - max(o["y"], sy0))
                    if ox_ * oy_ >= 0.5 * max(1, o["w"] * (o["h"] or 1)):
                        blocks.remove(o)
                        if o.get("file"):
                            comp["merged"].append(o["file"]); comp["layers"].append(o["file"])
            blocks.append(comp)
            made_any = True
        if not made_any:
            continue
        for m in members:
            if m in blocks:
                blocks.remove(m)
        # the backdrop's own colour becomes the section ground where no
        # ground is painted, so the page stays dark around the picture
        for m in bds:
            covered = any(b["kind"] == "ground" and b["y"] - 4 <= m["y"] and b["y"] + b["h"] >= m["y"] + (m["h"] or 0) - 4 for b in blocks)
            if covered:
                continue
            src_ = out_dir / "assets" / (m.get("file") or "")
            if m.get("file") and src_.is_file():
                try:
                    edge = Image.open(src_).convert("RGB").resize((8, 8))
                except Exception:
                    edge = None
            else:
                edge = None
            if edge is None:
                gx0, gy0 = int(max(0, m["x"])), int(max(0, m["y"]))
                gx1, gy1 = int(min(page.size[0], m["x"] + m["w"])), int(min(page.size[1], m["y"] + (m["h"] or 0)))
                if gx1 - gx0 < 10 or gy1 - gy0 < 10:
                    continue
                edge = page.crop((gx0, gy0, gx1, gy1)).resize((8, 8))
            px = list(edge.getdata())
            r = sorted(p[0] for p in px)[4]; gch = sorted(p[1] for p in px)[4]; bch = sorted(p[2] for p in px)[4]
            blocks.append(dict(y=m["y"], x=0, w=W, h=(m["h"] or 0), kind="ground", bg=f"rgb({r},{gch},{bch})", from_backdrop=True))
    # a second placement of a picture already folded into a scene is a
    # hidden duplicate layer, not another picture
    folded = set()
    for b in blocks:
        if b["kind"] == "image" and b.get("layers"):
            folded.update(b.get("merged", []))
    for b in list(blocks):
        if b["kind"] == "image" and b.get("real") and not b.get("layers") and b.get("file") in folded:
            blocks.remove(b)
    blocks.sort(key=lambda b: (b["y"], b["x"]))
    return blocks


def fit_assets(blocks, out_dir):
    """Every recovered picture is delivered at the size the design placed
    it: a file larger than its box gets a fitted copy (aspect kept), so no
    cut-out ever renders bigger than it was laid out."""
    from PIL import Image
    def fit(b):
        if b.get("kind") != "image" or not b.get("real") or not b.get("file") or b.get("layers"):
            return
        src = out_dir / "assets" / b["file"]
        if not src.is_file() or not b.get("w") or not b.get("h"):
            return
        try:
            im = Image.open(src)
        except Exception:
            return
        bw, bh = int(b["w"]), int(b["h"])
        if im.size[0] <= bw * 1.1 and im.size[1] <= bh * 1.1:
            return
        scale = min(bw / im.size[0], bh / im.size[1])
        nw, nh = max(1, int(im.size[0] * scale)), max(1, int(im.size[1] * scale))
        name = f"fit-{nw}x{nh}-{b['file'].rsplit('.', 1)[0]}.png"
        dst = out_dir / "assets" / name
        if not dst.is_file():
            im.convert("RGBA").resize((nw, nh), Image.LANCZOS).save(dst, "PNG")
        b.setdefault("merged", []).append(b["file"])      # the original stays on the record
        b["file"] = name
        b["w"], b["h"] = nw, nh
    for b in blocks:
        fit(b)
        for x in b.get("inside", []) or []:
            fit(x)
    return blocks


# ---------------------------------------------------------------- spec ---

def spec_of(blocks, W, H, canvas, board, i, name):
    """Stage 2 of the teardown, adapted for email: the replication spec.
    Everything the build needs, in the order it is built, in plain terms —
    the record a designer could build from without seeing the original."""
    grounds = sorted([b for b in blocks if b["kind"] == "ground"], key=lambda b: b["y"])

    def ground_at(y):
        g = canvas
        for gb in grounds:
            if gb["y"] <= y <= gb["y"] + gb["h"]:
                g = gb["bg"]
        return g
    sections, cur = [], None
    for b in blocks:
        if b["kind"] == "ground":
            continue
        g = ground_at(b["y"] + (b.get("h") or 0) / 2)      # the ground under the block's middle
        if cur is None or cur["ground"] != g:
            gb_ = next((gb for gb in grounds if gb["bg"] == g and gb.get("backdrop_file")), None)
            cur = dict(ground=g, ink=(INK_DARK if is_dark(g) else INK_LIGHT), from_y=int(b["y"]), blocks=[],
                       **({"ground_from": f"the export's backdrop picture {gb_['backdrop_file']} (its colour carried; the picture itself is the page background)"} if gb_ else {}))
            sections.append(cur)
        k = b["kind"]
        if k == "text":
            cur["blocks"].append(dict(block="text", role=("display" if b["size"] >= 44 else "headline" if b["size"] >= 28 else "body" if b["size"] >= 19 else "small"),
                                      family=("serif (GT Super Display)" if b["family"] == "serif" else "sans (Untitled Sans)"),
                                      size_px=int(b["size"]), case=("uppercase" if b["upper"] else "as written"),
                                      italic=bool(b["italic"]), align=b.get("align") or "center",
                                      measure_px=int(b["w"] or 0), color=b["color"] or "ink", text=b["text"]))
        elif k == "ticker":
            cur["blocks"].append(dict(block="ticker", text=b["text"]))
        elif k == "pill":
            cur["blocks"].append(dict(block="pill", text=b["text"], size=f"{int(b['w'])}×{int(b['h'])}"))
        elif k == "cta":
            cur["blocks"].append(dict(block="cta", label=b.get("label") or "(label not read)", fill=b["bg"], size=f"{int(b['w'])}×{int(b['h'])}"))
        elif k == "image":
            cur["blocks"].append(dict(block="image", size=f"{int(b['w'])}×{int(b['h'])}",
                                      source=(f"composed hero — {len(b['layers'])} layers of the export as one picture ({', '.join(b['layers'])})"
                                              + (f"; baked-in copy: “{b['alt']}”" if b.get("alt") else "")) if b.get("layers") else
                                      ("recovered bitmap " + b["file"]) if b.get("real") and b.get("file") else "LOST in the export — needs the real picture"))
        elif k == "art":
            cur["blocks"].append(dict(block="artwork", size=f"{int(b['w'])}×{int(b['h'])}", file=b.get("file"),
                                      note="a drawn headline or lettering, set in the section's ink"))
        elif k == "decor":
            cur["blocks"].append(dict(block="decoration", size=f"{int(b['w'])}×{int(b['h'])}", file=b.get("file"),
                                      note="art laid behind or over the copy in the design; not carried as a picture of its own"))
        elif k == "icon":
            cur["blocks"].append(dict(block="icon", size=f"{int(b['w'])}×{int(b['h'])}", mask=b.get("file")))
        elif k == "logo":
            cur["blocks"].append(dict(block="wordmark", width_px=int(b["w"])))
        elif k in ("glass", "panel", "tile", "row"):
            cur["blocks"].append(dict(block=k, fill=(b.get("bg") or "glass gradient"), size=f"{int(b['w'])}×{int(b['h'])}",
                                      contains=[(x["kind"] + (": " + x["text"][:60] if x["kind"] == "text" else (": “" + (x.get("label") or "(label not read)") + "”" if x["kind"] == "cta" else ""))) for x in b.get("inside", [])]))
        elif k == "divider":
            cur["blocks"].append(dict(block="divider", color=b["bg"]))
    return dict(board=board, index=i, name=name, canvas=dict(width=int(W), height=int(H), ground=canvas),
                sections=sections)


def spec_md(sp):
    out = [f"# Replication spec — {sp['board']} #{sp['index']:02d} {sp['name']}", "",
           f"Canvas {sp['canvas']['width']}×{sp['canvas']['height']}, ground {sp['canvas']['ground']}. "
           f"{len(sp['sections'])} section(s). Built top to bottom; every value below is read off the export.", ""]
    for n, sec in enumerate(sp["sections"], 1):
        out.append(f"## Section {n} — ground {sec['ground']} · ink {sec['ink']}")
        for b in sec["blocks"]:
            if b["block"] == "text":
                out.append(f"- **{b['role']}** · {b['family']} {b['size_px']}px · {b['case']}{' · italic' if b['italic'] else ''} · {b['align']} · measure {b['measure_px']}px")
                out.append(f"  > {b['text'].replace(chr(10), ' / ')}")
            elif b["block"] == "ticker":
                out.append(f"- **ticker strip** · “{b['text']}” repeated across the width")
            elif b["block"] == "pill":
                out.append(f"- **pill sticker** · “{b['text']}” · {b['size']} (set at a slight tilt in the design)")
            elif b["block"] == "cta":
                out.append(f"- **CTA** · “{b['label']}” · fill {b['fill']} · {b['size']}")
            elif b["block"] == "image":
                out.append(f"- **image** {b['size']} · {b['source']}")
            elif b["block"] == "decoration":
                out.append(f"- **decoration** {b['size']} · {b['file']} — {b['note']}")
            elif b["block"] == "artwork":
                out.append(f"- **artwork** {b['size']} · {b['file']} — {b['note']}")
            elif b["block"] in ("glass", "panel", "tile", "row"):
                out.append(f"- **{b['block']}** {b['size']} · fill {b['fill']}")
                for c in b["contains"]:
                    out.append(f"  - {c}")
            else:
                out.append(f"- **{b['block']}** " + ", ".join(f"{k} {v}" for k, v in b.items() if k != "block"))
        out.append("")
    return "\n".join(out)




def wrap_gradients(rows):
    """Consecutive rows on the same gradient ground become one section:
    the gradient paints once over all of them, not afresh on every row."""
    out, run, run_g = [], [], None
    pat = re.compile(r'<td([^>]*?)style="background:(linear-gradient\([^"]*?\));')

    def flush():
        nonlocal run, run_g
        if not run:
            return
        if len(run) == 1:
            out.extend(run)
        else:
            inner = "".join(pat.sub(r'<td\1style="background:transparent;', r, count=1) for r in run)
            out.append(f'<tr><td style="background:{run_g}"><table role="presentation" cellpadding="0" cellspacing="0" width="100%">{inner}</table></td></tr>')
        run, run_g = [], None
    for r in rows:
        m = pat.search(r)
        g = m.group(2) if m else None
        if g and g == run_g:
            run.append(r)
        else:
            flush()
            if g:
                run, run_g = [r], g
            else:
                out.append(r)
    flush()
    return out

# -------------------------------------------------------------- render ---

def render(blocks, W, H, canvas, board, name, bank, brand):
    ink = INK_DARK if is_dark(canvas) else INK_LIGHT
    rows = []
    cur_ground, cur_ink = canvas, ink
    # grounds: a full-width band changes the section colour from its y down
    grounds = sorted([b for b in blocks if b["kind"] == "ground"], key=lambda b: b["y"])
    bd_files = [gb.get("backdrop_file") for gb in grounds if gb.get("backdrop_file")]
    if bd_files:
        rows.append("<!-- page backdrop pictures in the export, their colour carried as the ground: " + ", ".join(bd_files) + " -->")

    def ground_at(y):
        g = canvas
        for gb in grounds:
            if gb["y"] <= y <= gb["y"] + gb["h"]:
                g = gb["bg"]
        return g

    pad = 50 if W <= 660 else 60
    inner = W - 2 * pad
    cta_w = min(500 if W <= 660 else 600, inner)

    def block_h(b):
        if b.get("h"):
            return b["h"]
        if b["kind"] == "text":
            return b["size"] * 1.3 * (b["text"].count("\n") + 1)
        return 40

    class Rows(list):
        """rows carry the export's gap: the first top padding of a row is
        rewritten to the space the design left above the block"""
        gap = None
        spacer = None

        def append(self, row):
            if self.spacer:
                super().append(self.spacer); self.spacer = None
            if self.gap is not None and "<!--" not in row[:4]:
                row = re.sub(r"padding:(\d+)px 0 0", f"padding:{self.gap}px 0 0", row, count=1) + f"<!-- gap {self.gap} -->"
                self.gap = None
            super().append(row)
    rows = Rows(rows)
    last_bottom = None
    last_g = None
    i_prev = 0
    i = 0
    values_done = False
    while i < len(blocks):
        b = blocks[i]
        g = ground_at(b["y"] + (b.get("h") or 0) / 2)      # the ground under the block's middle
        tink = INK_DARK if is_dark(g) else INK_LIGHT
        td = f'style="background:{g};padding:0 {pad}px"'
        # the space the design left above this block
        for pb in blocks[i_prev:i]:
            if pb["kind"] not in ("ground", "decor"):
                last_bottom = max(last_bottom or 0, pb["y"] + block_h(pb))
        i_prev = i
        if last_bottom is not None and b["kind"] != "ground":
            gap_total = int(max(0, min(320, b["y"] - last_bottom)))
            if last_g is not None and g != last_g:
                edge = next((gb["y"] for gb in grounds if gb["bg"] == g and gb["y"] >= last_bottom - 4), None)
                if edge is None:
                    edge = next((gb["y"] + gb["h"] for gb in grounds if gb["bg"] == last_g and gb["y"] + gb["h"] <= b["y"] + 4), None)
                if edge is not None and last_bottom <= edge <= b["y"]:
                    below_ = int(max(0, min(320, edge - last_bottom)))
                    if below_:
                        rows.spacer = f'<tr><td style="background:{last_g};height:{below_}px;line-height:{below_}px;font-size:0">&nbsp;</td></tr>'
                    gap_total = int(max(0, min(320, b["y"] - edge)))
            rows.gap = gap_total
        last_g = g
        k = b["kind"]
        if k == "ground":
            i += 1; continue
        if k == "art":
            aw = int(min(b["w"], inner)); ah = int(b["h"] * aw / max(1, b["w"]))
            ink_a = b.get("color") or tink
            if is_dark(ink_a) == is_dark(g):
                ink_a = tink
            rows.append(f'<tr><td align="center" {td}><div style="padding:24px 0 0"><div style="width:{aw}px;height:{ah}px;margin:0 auto;background:{ink_a};'
                        f'-webkit-mask:url({URLBASE}/{board}/assets/{b["file"]}) center/contain no-repeat;mask:url({URLBASE}/{board}/assets/{b["file"]}) center/contain no-repeat"></div></div></td></tr>')
            i += 1; continue
        if k == "decor":
            folded = [f_ for f_ in (b.get("merged") or []) if f_ != b.get("file")]
            rows.append(f"<!-- decoration in the design, not carried: {b.get('file')}" + (" (with " + ", ".join(folded) + ")" if folded else "") + " -->")
            i += 1; continue
        if k == "logo":
            top = int(b["y"]) if not rows else 44
            rows.append(f'<tr><td align="center" {td}><div style="padding:{top}px 0 0"><img src="{bank.logo(tink)}" width="{int(b["w"])}" alt="{e(brand)}" style="display:block;width:{int(b["w"])}px;height:auto;margin:0 auto"></div></td></tr>')
            i += 1; continue
        if k == "text" and b["upper"] and b["size"] <= 26 and 2 <= len(b["text"].split("\n")) <= 5 \
                and all(len(x.split()) <= 2 for x in b["text"].split("\n")):
            # the footer nav — short uppercase lines with hairlines between
            items = [x.strip() for x in b["text"].split("\n") if x.strip()]
            lis = "".join(f'<tr><td align="center" style="padding:14px 0;border-top:1px solid rgba(150,150,150,0.35);font-family:{SANS};font-size:{int(b["size"])}px;letter-spacing:0.08em;text-transform:uppercase;color:{tink}"><a href="#" style="color:{tink};text-decoration:none">{e(it)}</a></td></tr>' for it in items)
            rows.append(f'<tr><td align="center" {td}><div style="padding:22px 0 0"><table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="border-bottom:1px solid rgba(150,150,150,0.35)">{lis}</table></div></td></tr>')
            i += 1; continue
        if k == "text" and b["text"].strip().lower() == "stay connected":
            socials = " · ".join(f'<a href="#" style="color:{tink};text-decoration:none">{n_}</a>' for n_ in ("Facebook", "Instagram", "TikTok", "YouTube"))
            rows.append(f'<tr><td align="center" {td}><div style="padding:30px 0 0;font-family:{SERIF};font-size:{int(b["size"])}px;color:{tink}">Stay Connected</div>'
                        f'<div style="padding:14px 0 0;font-family:{SANS};font-size:13px;letter-spacing:0.1em;text-transform:uppercase;color:{tink}">{socials}</div></td></tr>')
            i += 1; continue
        if k == "text":
            fam = SERIF if b["family"] == "serif" else SANS
            size = b["size"]
            col = b["color"] or tink
            if b["color"] and is_dark(b["color"]) == is_dark(g):
                col = tink                         # ink that vanished on its ground
            up = "text-transform:uppercase;" if b["upper"] else ""
            it = "font-style:italic;" if b["italic"] else ""
            wt = f"font-weight:{int(b['weight'])};" if b.get("weight") else ""
            lh = 0.95 if size >= 60 else (1.05 if size >= 40 else (1.2 if size >= 24 else 1.35))
            ld = str(b.get("leading") or "")
            if re.fullmatch(r"\d+(\.\d+)?px", ld):
                lh = round(float(ld[:-2]) / max(1, size), 2)
            elif re.fullmatch(r"\d+(\.\d+)?%", ld):
                lh = round(float(ld[:-1]) / 100, 2)
            tr = str(b.get("tracking") or "")
            trk = f"letter-spacing:{tr};" if re.fullmatch(r"-?\d+(\.\d+)?(px|em)", tr) else ""
            # the box's own width and centring decide alignment
            centred = abs((b["x"] + (b["w"] or 0) / 2) - W / 2) < 30
            align = b.get("align") or ("center" if centred else "left")
            width = min(int(b["w"] or inner), inner) if b["w"] else inner
            paras = ([b["text"]] if size >= 30 else [p for p in re.split(r"\n\s*\n", b["text"]) if p.strip()])
            oneline = "\n" not in b["text"] and len(b["text"]) <= 24 and b["upper"]
            if oneline:
                width = inner
            body = "".join(f'<div style="margin:0 0 {max(8, int(size * 0.5))}px">{e(p).replace(chr(10), "<br>")}</div>' for p in paras)
            gap = 26 if size >= 40 else 18
            rows.append(f'<tr><td align="{align}" {td}><div style="padding:{gap}px 0 0;max-width:{width}px;margin:0 auto;'
                        f'font-family:{fam};font-size:{int(size)}px;line-height:{lh};color:{col};{up}{it}{wt}{trk}{"white-space:nowrap;" if oneline else ""}text-align:{align}">{body}</div></td></tr>')
            i += 1; continue
        if k == "pill":
            ph = int(min(b["h"], 64))
            rows.append(f'<tr><td align="center" {td}><div style="padding:18px 0 0"><div style="display:inline-block;padding:0 30px;height:{ph}px;line-height:{ph}px;border-radius:999px;'
                        f'background:{INK_DARK};font-family:{SANS};font-size:{int(min(b["size"], 30))}px;font-weight:500;letter-spacing:-0.01em;text-transform:uppercase;color:{INK_LIGHT}">{e(b["text"])}</div></div></td></tr>')
            i += 1; continue
        if k == "ticker":
            rows.append(f'<tr><td align="center" style="background:{SAGE};padding:16px 0"><div style="width:{int(W)}px;max-width:100%;overflow:hidden;white-space:nowrap;font-family:{SANS};font-size:20px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:{INK_LIGHT};text-align:center">'
                        + " &nbsp;·&nbsp; ".join([e(b["text"])] * 5) + "</div></td></tr>")
            i += 1; continue
        if k == "cta":
            label = b.get("label") or "SHOP NOW"
            bg = b["bg"]
            lab_ink = INK_LIGHT if not is_dark(bg) else INK_DARK
            if bg == "rgb(0,0,0)":
                lab_ink = INK_DARK
            bw_ = int(min(b["w"], inner)) if b.get("w") else cta_w
            rows.append(f'<tr><td align="center" {td}><div style="padding:30px 0 0">'
                        f'<table role="presentation" cellpadding="0" cellspacing="0" width="{bw_}" style="width:{bw_}px;max-width:100%;margin:0 auto"><tr>'
                        f'<td align="center" bgcolor="{hexc(bg)}" style="background:{bg};height:{int(b["h"])}px"><a href="#" style="display:block;line-height:{int(b["h"])}px;'
                        f'font-family:{SANS};font-size:18px;font-weight:500;letter-spacing:-0.02em;text-transform:uppercase;color:{lab_ink};text-decoration:none">{e(label)}</a></td></tr></table></div></td></tr>')
            i += 1; continue
        if k == "image" and (b["h"] or 0) >= 350 and b["w"] < W * 0.62:
            side_right = b["x"] >= W * 0.42
            beside = [t for t in blocks[i + 1:i + 9] if t["kind"] in ("text", "cta") and t["y"] < b["y"] + (b["h"] or 0) - 20 and t["y"] + (t["h"] or 30) > b["y"] + 20
                      and ((t["x"] + min(t["w"] or 0, 40) <= b["x"] + 24 and (t.get("align") in ("left", "", None))) if side_right
                           else (t["x"] >= b["x"] + b["w"] - 24))]
            if len(beside) >= 2:
                # picture column and copy column, side by side as designed
                col_html = ""
                for t in beside:
                    if t["kind"] == "cta":
                        c_bg = t["bg"]; c_ink = INK_LIGHT if not is_dark(c_bg) else INK_DARK
                        cw_ = int(min(t["w"], W - b["w"] - 2 * pad - 20))
                        col_html += (f'<table role="presentation" cellpadding="0" cellspacing="0" width="{cw_}" style="width:{cw_}px;max-width:100%;margin:18px 0 0"><tr><td align="center" bgcolor="{hexc(c_bg)}" style="background:{c_bg};height:{int(t["h"])}px">'
                                     f'<a href="#" style="display:block;line-height:{int(t["h"])}px;font-family:{SANS};font-size:16px;font-weight:500;text-transform:uppercase;color:{c_ink};text-decoration:none">{e(t.get("label") or "SHOP NOW")}</a></td></tr></table>')
                    else:
                        fam_t = SERIF if t["family"] == "serif" else SANS
                        wt_ = f"font-weight:{int(t['weight'])};" if t.get("weight") else ""
                        up_ = "text-transform:uppercase;" if t["upper"] else ""
                        lh_ = 0.95 if t["size"] >= 60 else (1.05 if t["size"] >= 40 else (1.2 if t["size"] >= 24 else 1.35))
                        col_html += f'<div style="font-family:{fam_t};font-size:{int(t["size"])}px;line-height:{lh_};color:{t.get("color") or tink};{wt_}{up_}margin:0 0 {max(8, int(t["size"] * 0.5))}px;text-align:left">{e(t["text"]).replace(chr(10), "<br>")}</div>'
                pic_w = int(min(b["w"], W * 0.5))
                if b.get("real") and b.get("file"):
                    pic = f'<img src="{URLBASE}/{board}/assets/{b["file"]}" width="{pic_w}" alt="{e(b.get("alt") or "")}" style="display:block;width:{pic_w}px;height:auto">'
                    folded = list(b.get("layers", [])) + [f_ for f_ in b.get("merged", []) if f_ not in b.get("layers", [])]
                    if folded:
                        pic += "<!-- one picture from the export's layers: " + ", ".join(folded) + " -->"
                else:
                    pimg = bank.product_image(" ".join(t["text"] for t in beside if t["kind"] == "text"))
                    pic = (f'<img src="{pimg}" width="{pic_w}" alt="" style="display:block;width:{pic_w}px;height:auto">' if pimg else
                           f'<div style="width:{pic_w}px;height:{int(b["h"] or 300)}px;background:repeating-linear-gradient(135deg,rgba(199,207,173,0.12) 0 14px,rgba(199,207,173,0.05) 14px 28px);box-shadow:inset 0 0 0 1px rgba(150,160,140,0.35)"></div>')
                left, right = (col_html, pic) if side_right else (pic, col_html)
                rows.append(f'<tr><td align="center" {td}><div style="padding:20px 0 0"><table role="presentation" cellpadding="0" cellspacing="0" width="{inner}" style="width:{inner}px;max-width:100%;margin:0 auto"><tr>'
                            f'<td valign="top" style="padding-right:18px">{left}</td><td valign="middle" width="{pic_w}">{right}</td></tr></table></div></td></tr>')
                ids_ = {id(t) for t in beside}
                blocks[i + 1:i + 9] = [t for t in blocks[i + 1:i + 9] if id(t) not in ids_]
                i += 1; continue
        if k == "image" and b["w"] < W * 0.45 and i + 1 < len(blocks) and blocks[i + 1]["kind"] in ("icon", "text", "badge") \
                and blocks[i + 1]["x"] > b["x"] + b["w"] - 10 and abs(blocks[i + 1]["y"] - b["y"]) < (b["h"] or 100) + 40 \
                and not (blocks[i + 1]["kind"] == "text" and (blocks[i + 1]["size"] >= 44 or (blocks[i + 1]["w"] or 0) > W * 0.6)):
            # picture | (icon) | copy — a media row; consecutive rows are a list
            items, j = [], i
            while j < len(blocks) and blocks[j]["kind"] == "image" and blocks[j]["w"] < W * 0.45:
                im = blocks[j]
                right = []
                jj = j + 1
                while jj < len(blocks) and blocks[jj]["kind"] in ("icon", "text", "badge") and blocks[jj]["x"] > im["x"] + im["w"] - 10 \
                        and im["y"] - 20 <= blocks[jj]["y"] + (blocks[jj].get("h") or 30) / 2 <= im["y"] + (im["h"] or 100) + 20 and len(right) < 4:
                    right.append(blocks[jj]); jj += 1
                if not right:
                    break
                if im.get("real") and im.get("file"):
                    pic = f'<img src="{URLBASE}/{board}/assets/{im["file"]}" width="{int(im["w"])}" alt="{e(im.get("alt") or "")}" style="display:block;width:{int(im["w"])}px;height:auto;border-radius:12px">'
                    folded = list(im.get("layers", [])) + [f_ for f_ in im.get("merged", []) if f_ not in im.get("layers", [])]
                    if folded:
                        pic += "<!-- one picture from the export's layers: " + ", ".join(folded) + " -->"
                else:
                    pimg = bank.product_image(" ".join(t["text"] for t in right if t["kind"] == "text"))
                    pic = (f'<img src="{pimg}" width="{int(im["w"])}" alt="" style="display:block;width:{int(im["w"])}px;height:auto;border-radius:12px">' if pimg else
                           f'<div style="width:{int(im["w"])}px;height:{int(im["h"] or 100)}px;border-radius:12px;background:repeating-linear-gradient(135deg,rgba(199,207,173,0.12) 0 14px,rgba(199,207,173,0.05) 14px 28px);box-shadow:inset 0 0 0 1px rgba(150,160,140,0.35)"></div>')
                lead = ""
                ic = next((r_ for r_ in right if r_["kind"] == "icon"), None)
                if ic is not None and ic.get("file"):
                    lead = f'<div style="width:{int(ic["w"])}px;height:{int(ic["h"])}px;background:{tink};-webkit-mask:url({URLBASE}/{board}/assets/{ic["file"]}) center/contain no-repeat;mask:url({URLBASE}/{board}/assets/{ic["file"]}) center/contain no-repeat"></div>'
                copy = ""
                for t in right:
                    if t["kind"] == "text":
                        fam_t = SERIF if t["family"] == "serif" else SANS
                        copy += f'<div style="font-family:{fam_t};font-size:{int(t["size"])}px;line-height:1.3;color:{t.get("color") or tink};{"font-weight:500;" if t["size"] >= 20 else ""}margin:0 0 4px;text-align:left">{e(t["text"]).replace(chr(10), "<br>")}</div>'
                    elif t["kind"] == "badge":
                        copy = f'<div style="font-family:{SANS};font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:{SAGE};margin:0 0 6px">{e(t["text"])}</div>' + copy
                items.append(f'<tr><td width="{int(im["w"]) + 18}" valign="middle" style="padding:10px 18px 10px 0">{pic}</td>'
                             + (f'<td width="{int(ic["w"]) + 12}" valign="middle" style="padding-right:12px">{lead}</td>' if lead else "")
                             + f'<td valign="middle" style="padding:10px 0">{copy}</td></tr>')
                j = jj
            if items:
                rows.append(f'<tr><td align="center" {td}><div style="padding:12px 0 0"><table role="presentation" cellpadding="0" cellspacing="0" width="{inner}" style="width:{inner}px;max-width:100%;margin:0 auto">{"".join(items)}</table></div></td></tr>')
                i = j; continue
        if k == "image":
            # images sharing a band, each narrower than half the board = a row
            band = [b]
            j = i + 1
            while j < len(blocks) and blocks[j]["kind"] == "image" and abs(blocks[j]["y"] - b["y"]) < 120 \
                    and blocks[j]["w"] < W * 0.5 and b["w"] < W * 0.5:
                band.append(blocks[j]); j += 1
            cells = []
            fit_each = int((inner - 12 * (len(band) - 1)) / len(band)) if len(band) > 1 else inner
            for im in band:
                w, h = int(im["w"]), int(im["h"])
                w = int(min(w, inner) if w < W - 10 else W)
                if len(band) > 1:
                    w = min(w, fit_each)
                full = w >= W - 10 and len(band) == 1
                if im.get("real") and im.get("file"):
                    src = f"{URLBASE}/{board}/assets/{im['file']}"
                    tag = f'<img src="{src}" width="{w}" alt="{e(im.get("alt") or "")}" style="display:block;width:{w}px;max-width:100%;height:auto;margin:0 auto;border-radius:{0 if (full or im.get("layers")) else 20}px">'
                    if im.get("layers"):
                        extra = [f_ for f_ in im.get("merged", []) if f_ not in im["layers"]]
                        tag += ("<!-- one picture composed from the export's layers: " + ", ".join(im["layers"])
                                + ("; same-footprint crops folded in: " + ", ".join(extra) if extra else "") + " -->")
                    elif im.get("merged"):
                        tag += "<!-- merged into this picture: " + ", ".join(im["merged"]) + " (same footprint in the export) -->"
                elif full and h < 160:
                    tag = f'<div style="width:{w}px;max-width:100%;height:{max(24, min(h, 80))}px;margin:0 auto;background:repeating-linear-gradient(90deg,rgba(199,207,173,0.10) 0 18px,rgba(199,207,173,0.04) 18px 36px)"></div>'
                else:
                    near = " ".join(x["text"] for x in blocks if x["kind"] == "text" and abs(x["y"] - im["y"]) < 900)
                    pimg = bank.product_image(near)
                    if pimg:
                        tag = f'<img src="{pimg}" width="{w}" alt="" style="display:block;width:{w}px;max-width:100%;height:auto;margin:0 auto;border-radius:{0 if full else 20}px">'
                    else:
                        tag = (f'<div style="width:{w}px;max-width:100%;height:{h}px;margin:0 auto;border-radius:{0 if full else 20}px;'
                               f'background:repeating-linear-gradient(135deg,rgba(199,207,173,0.12) 0 14px,rgba(199,207,173,0.05) 14px 28px);'
                               f'box-shadow:inset 0 0 0 1px rgba(150,160,140,0.35);display:flex;align-items:center;justify-content:center;'
                               f'font-family:{SANS};font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:{tink};opacity:.8">IMAGE {w}×{h}</div>')
                cells.append((tag, full))
            # small labels sitting on the pictures (Before / After) become
            # captions under each picture, one per column
            caps = []
            if len(band) > 1:
                band_bot = max(im["y"] + (im["h"] or 0) for im in band)
                jj = j
                while jj < len(blocks) and blocks[jj]["kind"] == "text" and blocks[jj]["size"] <= 26 and blocks[jj]["y"] <= band_bot + 40 \
                        and any(im["x"] - 6 <= blocks[jj]["x"] <= im["x"] + im["w"] for im in band):
                    caps.append(blocks[jj]); jj += 1
                if len(caps) == len(band):
                    j = jj
                else:
                    caps = []
            if len(cells) == 1:
                tag, full = cells[0]
                rows.append(f'<tr><td align="center" style="background:{g};padding:{0 if full else 28}px {0 if full else pad}px 0">{tag}</td></tr>')
            else:
                tds = "".join(f'<td align="center" valign="bottom" style="padding:0 6px">{t}</td>' for t, _ in cells)
                cap_tr = ""
                if caps:
                    cap_by_x = sorted(caps, key=lambda c: c["x"])
                    cap_tr = "<tr>" + "".join(f'<td align="center" style="padding:10px 6px 0;font-family:{SANS};font-size:{int(c["size"])}px;font-weight:500;color:{tink};{"text-transform:uppercase;" if c["upper"] else ""}">{e(c["text"])}</td>' for c in cap_by_x) + "</tr>"
                rows.append(f'<tr><td align="center" style="background:{g};padding:28px {pad}px 0"><table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto"><tr>{tds}</tr>{cap_tr}</table></td></tr>')
            i = j; continue
        if k == "badge" and i + 1 < len(blocks) and blocks[i + 1]["kind"] == "text" \
                and abs(blocks[i + 1]["y"] - b["y"]) < 80 and blocks[i + 1]["x"] > b["x"] + b["w"] * 0.8:
            items, j = [], i
            while j + 1 < len(blocks) and blocks[j]["kind"] == "badge" and blocks[j + 1]["kind"] == "text" \
                    and abs(blocks[j + 1]["y"] - blocks[j]["y"]) < 80 and blocks[j + 1]["x"] > blocks[j]["x"] + blocks[j]["w"] * 0.8:
                bd, tx = blocks[j], blocks[j + 1]
                word = len(bd["text"]) > 2
                disc = (f'<div style="width:52px;height:52px;border-radius:50%;background:{SAGE};font-family:{SANS};font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;line-height:1.1;display:flex;align-items:center;justify-content:center;text-align:center;color:{INK_LIGHT}">{e(bd["text"]).replace(" ", "<br>")}</div>'
                        if word else f'<div style="width:44px;height:44px;border-radius:50%;background:{SAGE};font-family:{SANS};font-size:20px;font-weight:500;line-height:44px;text-align:center;color:{INK_LIGHT}">{e(bd["text"])}</div>')
                fam_t = SERIF if tx["family"] == "serif" else SANS
                items.append(f'<tr><td width="70" valign="middle" style="padding:8px 16px 8px 0">{disc}</td>'
                             f'<td valign="middle" style="padding:8px 0;font-family:{fam_t};font-size:{int(tx["size"])}px;line-height:1.3;color:{tx.get("color") or tink};text-align:left">{e(tx["text"]).replace(chr(10), "<br>")}</td></tr>')
                j += 2
            rows.append(f'<tr><td align="center" {td}><div style="padding:16px 0 0"><table role="presentation" cellpadding="0" cellspacing="0" width="{inner}" style="width:{inner}px;max-width:100%;margin:0 auto">{"".join(items)}</table></div></td></tr>')
            i = j; continue
        if k == "icon" and i + 1 < len(blocks) and blocks[i + 1]["kind"] == "text" \
                and abs(blocks[i + 1]["y"] - b["y"]) < 80 and blocks[i + 1]["x"] > b["x"] + b["w"] * 0.8 \
                and not (i + 2 < len(blocks) and blocks[i + 2]["kind"] == "icon" and abs(blocks[i + 2]["y"] - b["y"]) < 40):
            # icon (or icon-in-disc) with its text beside it: a list item;
            # consecutive ones become one list
            items, j = [], i
            while j + 1 < len(blocks) and blocks[j]["kind"] == "icon" and blocks[j + 1]["kind"] == "text" \
                    and abs(blocks[j + 1]["y"] - blocks[j]["y"]) < 80 and blocks[j + 1]["x"] > blocks[j]["x"] + blocks[j]["w"] * 0.8:
                ic, tx = blocks[j], blocks[j + 1]
                texts = [tx]
                jj = j + 2
                while jj < len(blocks) and blocks[jj]["kind"] == "text" and blocks[jj]["x"] >= tx["x"] - 10 and blocks[jj]["y"] - tx["y"] < 160 \
                        and blocks[jj]["size"] <= tx["size"]:
                    texts.append(blocks[jj]); jj += 1
                pic_html = ""
                if jj < len(blocks) and blocks[jj]["kind"] == "image" and blocks[jj]["w"] < W * 0.45 and blocks[jj]["x"] < ic["x"] \
                        and blocks[jj]["y"] < ic["y"] + 200:
                    im = blocks[jj]; jj += 1
                    if im.get("real") and im.get("file"):
                        pic_html = f'<img src="{URLBASE}/{board}/assets/{im["file"]}" width="{int(im["w"])}" alt="" style="display:block;width:{int(im["w"])}px;height:auto;border-radius:12px">'
                        folded = list(im.get("layers", [])) + [f_ for f_ in im.get("merged", []) if f_ not in im.get("layers", [])]
                        if folded:
                            pic_html += "<!-- one picture from the export's layers: " + ", ".join(folded) + " -->"
                    else:
                        pimg = bank.product_image(" ".join(t["text"] for t in texts))
                        pic_html = (f'<img src="{pimg}" width="{int(im["w"])}" alt="" style="display:block;width:{int(im["w"])}px;height:auto;border-radius:12px">' if pimg else
                                    f'<div style="width:{int(im["w"])}px;height:{int(im["h"] or 100)}px;border-radius:12px;background:repeating-linear-gradient(135deg,rgba(199,207,173,0.12) 0 14px,rgba(199,207,173,0.05) 14px 28px);box-shadow:inset 0 0 0 1px rgba(150,160,140,0.35)"></div>')
                    pic_html = f'<td width="{int(im["w"]) + 20}" valign="middle" style="padding:0 20px 26px 0">{pic_html}</td>'
                src = f"{URLBASE}/{board}/assets/{ic['file']}"
                dw = ic.get("disc_w") or int(ic["w"]) + 24
                d_bg = ic.get("disc_bg") or "transparent"
                d_ink = INK_DARK if is_dark(d_bg) else INK_LIGHT
                if d_bg == "transparent":
                    d_ink = tink
                icon = (f'<div style="width:{dw}px;height:{dw}px;border-radius:50%;background:{d_bg};display:flex;align-items:center;justify-content:center">'
                        f'<div style="width:{int(ic["w"])}px;height:{int(ic["h"])}px;background:{d_ink};-webkit-mask:url({src}) center/contain no-repeat;mask:url({src}) center/contain no-repeat"></div></div>')
                body_html = "".join(f'<div style="font-family:{SERIF if t["family"] == "serif" else SANS};font-size:{int(t["size"])}px;line-height:1.25;color:{tink};{"font-weight:500;" if t.get("weight") and int(t["weight"]) >= 500 else ""}margin:0 0 6px">{e(t["text"]).replace(chr(10), "<br>")}</div>' for t in texts)
                items.append(f'<tr>{pic_html}<td width="{dw + 24}" valign="top" style="padding:0 24px 26px 0">{icon}</td><td valign="middle" style="padding:0 0 26px">{body_html}</td></tr>')
                j = jj
            rows.append(f'<tr><td align="center" {td}><div style="padding:22px 0 0"><table role="presentation" cellpadding="0" cellspacing="0" width="{inner}" style="width:{inner}px;max-width:100%">{"".join(items)}</table></div></td></tr>')
            i = j; continue
        if k == "icon":
            # a row of icons with labels = the values bar; gather the run
            run = [b]
            j = i + 1
            while j < len(blocks) and blocks[j]["kind"] in ("icon", "text") and abs(blocks[j]["y"] - b["y"]) < 40 and blocks[j].get("size", 0) <= 22:
                run.append(blocks[j]); j += 1
            # icons on one band with their captions on the band below: columns
            icons_ = [r_ for r_ in run if r_["kind"] == "icon"]
            if len(icons_) >= 2 and all(r_["kind"] == "icon" for r_ in run):
                caps_ = []
                jj = j
                while jj < len(blocks) and blocks[jj]["kind"] == "text" and blocks[jj]["size"] <= 30 and len(caps_) < len(icons_) \
                        and (not caps_ or abs(blocks[jj]["y"] - caps_[0]["y"]) < 40) and blocks[jj]["y"] - b["y"] < 400:
                    caps_.append(blocks[jj]); jj += 1
                if len(caps_) == len(icons_):
                    cols = []
                    for ic_, tx_ in zip(sorted(icons_, key=lambda r_: r_["x"]), sorted(caps_, key=lambda r_: r_["x"])):
                        mask = (f'<div style="width:{int(ic_["w"])}px;height:{int(ic_["h"])}px;margin:0 auto 14px;background:{tink};-webkit-mask:url({URLBASE}/{board}/assets/{ic_["file"]}) center/contain no-repeat;mask:url({URLBASE}/{board}/assets/{ic_["file"]}) center/contain no-repeat"></div>'
                                if ic_.get("file") else "")
                        cols.append(f'<td align="center" valign="top" width="{int(inner / len(icons_))}" style="padding:0 8px">{mask}<div style="font-family:{SANS};font-size:{int(tx_["size"])}px;line-height:1.3;color:{tx_.get("color") or tink};text-align:center">{e(tx_["text"]).replace(chr(10), "<br>")}</div></td>')
                    rows.append(f'<tr><td align="center" {td}><div style="padding:30px 0 0"><table role="presentation" cellpadding="0" cellspacing="0" width="{inner}" style="width:{inner}px;max-width:100%;margin:0 auto"><tr>{"".join(cols)}</tr></table></div></td></tr>')
                    i = jj; continue
            icons = [x for x in run if x["kind"] == "icon"]
            labels = [x for x in run if x["kind"] == "text"]
            if len(icons) >= 2 and labels and not values_done:
                cells = []
                for ic, lb in zip(icons, labels):
                    src = f"{URLBASE}/{board}/assets/{ic['file']}"
                    cells.append(f'<td align="center" style="padding:0 10px"><table role="presentation" cellpadding="0" cellspacing="0"><tr>'
                                 f'<td style="padding-right:10px"><div style="width:{int(ic["w"])}px;height:{int(ic["h"])}px;background:{tink};'
                                 f'-webkit-mask:url({src}) center/contain no-repeat;mask:url({src}) center/contain no-repeat"></div></td>'
                                 f'<td style="font-family:{SANS};font-size:{int(lb["size"])}px;line-height:1.25;color:{tink}">{e(lb["text"]).replace(chr(10), "<br>")}</td></tr></table></td>')
                rows.append(f'<tr><td align="center" {td}><div style="padding:26px 0"><table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto"><tr>{"".join(cells)}</tr></table></div></td></tr>')
                values_done = True
                i = j; continue
            i += 1; continue
        if k == "divider":
            rows.append(f'<tr><td {td}><div style="height:1px;background:{b["bg"]};margin:26px 0 0"></div></td></tr>')
            i += 1; continue
        if k == "badge":
            rows.append(f'<tr><td align="center" {td}><div style="padding:22px 0 0"><div style="width:56px;height:56px;border-radius:50%;background:{SAGE};margin:0 auto;font-family:{SANS};font-size:26px;font-weight:500;line-height:56px;text-align:center;color:{INK_LIGHT}">{e(b["text"])}</div></div></td></tr>')
            i += 1; continue
        if k == "tile":
            band = [b]
            j = i + 1
            while j < len(blocks) and blocks[j]["kind"] == "tile" and abs(blocks[j]["y"] - b["y"]) < 60:
                band.append(blocks[j]); j += 1
            cells = []
            fit_w = int((inner - 12 * (len(band) - 1)) / len(band))
            for t_ in band:
                t_ = dict(t_, w=min(t_["w"], fit_w))
                t_ink = INK_DARK if is_dark(t_.get("bg", g)) else INK_LIGHT
                parts = []
                for x in t_.get("inside", []):
                    if x["kind"] == "image":
                        src = f"{URLBASE}/{board}/assets/{x['file']}" if x.get("real") and x.get("file") else (bank.product_image(" ".join(t["text"] for t in t_.get("inside", []) if t["kind"] == "text")) or "")
                        if src:
                            iw = int(min(x["w"], t_["w"] - 24))
                            folded = list(x.get("layers", [])) + [f_ for f_ in x.get("merged", []) if f_ not in x.get("layers", [])]
                            note = ("<!-- one picture from the export's layers: " + ", ".join(folded) + " -->") if folded else ""
                            parts.append(f'<div style="height:{int(min(max(x["h"] or 120, 90), 200))}px;display:flex;align-items:center;justify-content:center;margin:8px auto 0"><img src="{src}" alt="{e(x.get("alt") or "")}" style="display:block;max-width:{iw}px;max-height:100%;width:auto;height:auto"></div>' + note)
                    elif x["kind"] == "text":
                        fam = SERIF if x["family"] == "serif" else SANS
                        parts.append(f'<div style="font-family:{fam};font-size:{int(x["size"])}px;line-height:1.15;color:{x.get("color") or t_ink};{"font-weight:500;" if x["size"] >= 20 else ""}margin:0 0 6px;text-align:center">{e(x["text"]).replace(chr(10), "<br>")}</div>')
                    elif x["kind"] == "cta":
                        c_bg = x["bg"]; c_ink = INK_LIGHT if not is_dark(c_bg) else INK_DARK
                        parts.append(f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:10px 0 0"><tr><td align="center" bgcolor="{hexc(c_bg)}" style="background:{c_bg};height:{int(min(x["h"], 48))}px">'
                                     f'<a href="#" style="display:block;line-height:{int(min(x["h"], 48))}px;font-family:{SANS};font-size:13px;font-weight:500;letter-spacing:-0.01em;text-transform:uppercase;color:{c_ink};text-decoration:none">{e(x.get("label") or "SHOP NOW")}</a></td></tr></table>')
                if t_.get("dropped"):
                    parts.append("<!-- other pictures the export stacked in this tile, folded into the one shown: " + ", ".join(t_["dropped"]) + " -->")
                r_ = int(float(t_["radius"])) if str(t_.get("radius") or "").replace(".", "").isdigit() else 16
                cells.append(f'<td valign="top" style="padding:0 6px"><div style="width:{int(t_["w"])}px;max-width:100%;border-radius:{r_}px;background:{t_["bg"]};padding:18px 12px;box-sizing:border-box">{"".join(parts)}</div></td>')
            rows.append(f'<tr><td align="center" {td}><div style="padding:26px 0 0"><table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto"><tr>{"".join(cells)}</tr></table></div></td></tr>')
            i = j; continue
        if k == "row":
            run = [b]
            j = i + 1
            while j < len(blocks) and blocks[j]["kind"] == "row":
                run.append(blocks[j]); j += 1
            items = []
            for r_ in run:
                r_ink = INK_DARK if is_dark(r_.get("bg", g)) else INK_LIGHT
                ic = next((x for x in r_.get("inside", []) if x["kind"] == "icon"), None)
                txt = "".join(f'<div style="font-family:{SANS};font-size:{int(x["size"])}px;line-height:1.3;color:{r_ink};{"font-weight:500;" if x["size"] >= 22 else ""}margin:0 0 4px">{e(x["text"]).replace(chr(10), "<br>")}</div>'
                              for x in r_.get("inside", []) if x["kind"] == "text")
                icon = (f'<div style="width:{int(ic["w"])}px;height:{int(ic["h"])}px;background:{r_ink};-webkit-mask:url({URLBASE}/{board}/assets/{ic["file"]}) center/contain no-repeat;mask:url({URLBASE}/{board}/assets/{ic["file"]}) center/contain no-repeat"></div>'
                        if ic and ic.get("file") else
                        (f'<div style="width:64px;height:64px;border-radius:50%;background:{SAGE};opacity:.85"></div>' if r_.get("disc") else ""))
                row_bg = r_["bg"] if r_["bg"] != g else "rgba(199,207,173,0.28)"
                rad = int(float(r_["radius"])) if str(r_.get("radius") or "").replace(".", "").isdigit() else 60
                items.append(f'<table role="presentation" cellpadding="0" cellspacing="0" width="{int(min(r_["w"], inner))}" style="width:{int(min(r_["w"], inner))}px;max-width:100%;margin:0 auto 14px;background:{row_bg};border-radius:{rad}px"><tr>'
                             f'<td width="{max(int((ic or {}).get("w", 0)), 64 if r_.get("disc") else 0) + 40}" valign="middle" style="padding:18px 8px 18px 28px">{icon}</td><td valign="middle" style="padding:18px 24px 18px 8px">{txt}</td></tr></table>')
            rows.append(f'<tr><td align="center" {td}><div style="padding:24px 0 0">{"".join(items)}</div></td></tr>')
            i = j; continue
        if k in ("glass", "panel"):
            # cards sharing a band, each narrower than half the board, sit
            # side by side (US vs THEM, two offers) — one row, one cell each
            band = [b]
            jb = i + 1
            while jb < len(blocks) and blocks[jb]["kind"] in ("glass", "panel") and abs(blocks[jb]["y"] - b["y"]) < 60 \
                    and blocks[jb]["w"] <= W * 0.55 and b["w"] <= W * 0.55:
                band.append(blocks[jb]); jb += 1
            divs = []
            for b in band:
                k = b["kind"]
                inside = b.get("inside", [])
                card_bg = (b.get("bg") if k == "panel" else
                           "linear-gradient(270deg,rgba(12,16,15,0.5),rgba(199,207,173,0.3))")
                if k == "panel" and card_bg == g:
                    card_bg = "rgba(199,207,173,0.28)"
                card_ink = tink if k == "glass" else (INK_DARK if is_dark(b.get("bg", g)) else INK_LIGHT)
                radius = int(float(b["radius"])) if str(b.get("radius") or "").replace(".", "").isdigit() else 20
                parts = []
                # an icon or number with its copy to its right is one row
                paired_lead, paired_text = {}, set()
                for x in inside:
                    if x["kind"] in ("icon", "badge"):
                        ts = [t for t in inside if t["kind"] == "text" and id(t) not in paired_text
                              and abs(t["y"] - x["y"]) < 110 and t["x"] > x["x"] + (x["w"] or 30) * 0.8]
                        if ts:
                            ts.sort(key=lambda t: t["y"])
                            lead_t = dict(ts[0])
                            lead_t["text"] = "\n".join(t["text"] for t in ts[:2])    # title + its line
                            paired_lead[id(x)] = lead_t
                            for t in ts[:2]:
                                paired_text.add(id(t))
                for x in inside:
                    if id(x) in paired_text:
                        parts.append("")             # rendered inside its row; keeps parts aligned with inside
                        continue
                    if id(x) in paired_lead:
                        t = paired_lead[id(x)]
                        if x["kind"] == "badge":
                            word = len(x["text"]) > 2
                            lead = (f'<div style="width:52px;height:52px;border-radius:50%;background:{SAGE};font-family:{SANS};font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;line-height:1.1;display:flex;align-items:center;justify-content:center;text-align:center;color:{INK_LIGHT}">{e(x["text"]).replace(" ", "<br>")}</div>'
                                    if word else
                                    f'<div style="width:44px;height:44px;border-radius:50%;background:{SAGE};font-family:{SANS};font-size:20px;font-weight:500;line-height:44px;text-align:center;color:{INK_LIGHT}">{e(x["text"])}</div>')
                            lw = 52 if word else 44
                        elif x.get("file"):
                            dw = x.get("disc_w") or 0
                            mask = f'<div style="width:{int(x["w"])}px;height:{int(x["h"])}px;background:{t.get("color") or card_ink};-webkit-mask:url({URLBASE}/{board}/assets/{x["file"]}) center/contain no-repeat;mask:url({URLBASE}/{board}/assets/{x["file"]}) center/contain no-repeat"></div>'
                            lead = (f'<div style="width:{dw}px;height:{dw}px;border-radius:50%;background:{x.get("disc_bg") or SAGE};display:flex;align-items:center;justify-content:center">{mask}</div>' if dw else mask)
                            lw = dw or int(x["w"])
                        else:
                            lead = f'<div style="width:36px;height:36px;border-radius:50%;background:{SAGE};opacity:.85"></div>'
                            lw = 36
                        fam_t = SERIF if t["family"] == "serif" else SANS
                        ink_t = t.get("color") or card_ink
                        parts.append(f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 14px"><tr>'
                                     f'<td width="{lw + 16}" valign="middle" style="padding-right:16px">{lead}</td>'
                                     f'<td valign="middle" style="font-family:{fam_t};font-size:{int(t["size"])}px;line-height:1.3;color:{ink_t};text-align:left">{e(t["text"]).replace(chr(10), "<br>")}</td></tr></table>')
                        continue
                    if x["kind"] == "cta":
                        c_bg = x["bg"]
                        c_ink = INK_LIGHT if not is_dark(c_bg) else INK_DARK
                        if c_bg == "rgb(0,0,0)":
                            c_ink = INK_DARK
                        c_w = min(int(x["w"]), int(b["w"]) - 60)
                        parts.append(f'<table role="presentation" cellpadding="0" cellspacing="0" width="{c_w}" style="width:{c_w}px;max-width:100%;margin:8px auto 4px"><tr>'
                                     f'<td align="center" bgcolor="{hexc(c_bg)}" style="background:{c_bg};height:{int(x["h"])}px"><a href="#" style="display:block;line-height:{int(x["h"])}px;'
                                     f'font-family:{SANS};font-size:18px;font-weight:500;letter-spacing:-0.02em;text-transform:uppercase;color:{c_ink};text-decoration:none">{e(x.get("label") or "SHOP NOW")}</a></td></tr></table>')
                        continue
                    if x["kind"] == "badge":
                        parts.append(f'<div style="width:56px;height:56px;border-radius:50%;background:{SAGE};margin:0 auto 14px;font-family:{SANS};font-size:26px;font-weight:500;line-height:56px;text-align:center;color:{INK_LIGHT}">{e(x["text"])}</div>')
                        continue
                    if x["kind"] == "icon":
                        if x.get("file"):
                            parts.append(f'<div style="width:{int(x["w"])}px;height:{int(x["h"])}px;margin:0 auto 12px;background:{card_ink};-webkit-mask:url({URLBASE}/{board}/assets/{x["file"]}) center/contain no-repeat;mask:url({URLBASE}/{board}/assets/{x["file"]}) center/contain no-repeat"></div>')
                        else:
                            parts.append("")
                        continue
                    if x["kind"] == "image" and x.get("_rowed"):
                        parts.append("")             # rendered in the picture row; keeps alignment
                        continue
                    if x["kind"] == "image":
                        mates = [m for m in inside if m is not x and m["kind"] == "image" and not m.get("_rowed") and abs(m["y"] - x["y"]) < 40]
                        if mates:
                            group = sorted([x] + mates, key=lambda m: m["x"])
                            cell_w = int((int(b["w"]) - 60) / len(group)) - 8
                            cells_ = []
                            for m in group:
                                m["_rowed"] = True
                                mw = min(int(m["w"]), cell_w)
                                if m.get("real") and m.get("file"):
                                    folded = list(m.get("layers", [])) + [f_ for f_ in m.get("merged", []) if f_ not in m.get("layers", [])]
                                    note = ("<!-- one picture from the export's layers: " + ", ".join(folded) + " -->") if folded else ""
                                    cells_.append(f'<td align="center" valign="bottom" style="padding:0 4px"><img src="{URLBASE}/{board}/assets/{m["file"]}" width="{mw}" alt="{e(m.get("alt") or "")}" style="display:block;width:{mw}px;height:auto">{note}</td>')
                                else:
                                    pimg = bank.product_image(" ".join(t["text"] for t in inside if t["kind"] == "text"))
                                    cells_.append(f'<td align="center" valign="bottom" style="padding:0 4px">' + (f'<img src="{pimg}" alt="" style="display:block;max-width:{mw}px;max-height:200px;width:auto;height:auto">' if pimg else "") + "</td>")
                            parts.append(f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto 16px"><tr>{"".join(cells_)}</tr></table>')
                            continue
                        w = min(int(x["w"]), int(b["w"]) - 60)
                        if x.get("real") and x.get("file"):
                            note = ("<!-- one picture composed from the export's layers: " + ", ".join(x["layers"] + [f_ for f_ in x.get("merged", []) if f_ not in x["layers"]]) + " -->") if x.get("layers") else \
                                   ("<!-- merged into this picture: " + ", ".join(x["merged"]) + " (same footprint in the export) -->") if x.get("merged") else ""
                            parts.append(f'<img src="{URLBASE}/{board}/assets/{x["file"]}" width="{w}" alt="{e(x.get("alt") or "")}" style="display:block;width:{w}px;height:auto;margin:0 auto 16px;border-radius:12px">' + note)
                        else:
                            pimg = bank.product_image(" ".join(t["text"] for t in inside if t["kind"] == "text"))
                            if pimg:
                                hh = int(min(max(x["h"] or 160, 120), 240))
                                parts.append(f'<div style="height:{hh}px;display:flex;align-items:center;justify-content:center;margin:0 auto 16px"><img src="{pimg}" alt="" style="display:block;max-width:{w}px;max-height:100%;width:auto;height:auto"></div>')
                            else:
                                parts.append(f'<div style="width:{w}px;height:{int(min(x["h"], 180))}px;margin:0 auto 16px;border-radius:12px;background:repeating-linear-gradient(135deg,rgba(120,120,120,0.18) 0 14px,rgba(120,120,120,0.06) 14px 28px);box-shadow:inset 0 0 0 1px rgba(120,120,120,0.35)"></div>')
                        continue
                    fam = SERIF if x["family"] == "serif" else SANS
                    up = "text-transform:uppercase;" if x["upper"] else ""
                    wt = f"font-weight:{int(x['weight'])};" if x.get("weight") else ""
                    al = x.get("align") or ("center" if abs((x["x"] + (x["w"] or 0) / 2) - (b["x"] + b["w"] / 2)) < 30 else "left")
                    ink = x.get("color") or card_ink            # the export's own ink, when it carried one
                    paras = [pp for pp in re.split(r"\n\s*\n", x["text"]) if pp.strip()]
                    parts.append("".join(f'<div style="font-family:{fam};font-size:{int(x["size"])}px;line-height:{1.05 if x["size"] >= 40 else (1.2 if x["size"] >= 24 else 1.35)};color:{ink};{up}{wt}margin:0 0 12px;text-align:{al}">{e(pp).replace(chr(10), "<br>")}</div>' for pp in paras))
                cw = min(int(b["w"]), inner)
                imgs_all = [x for x in inside if x["kind"] == "image" and x["w"] >= 30 and (x["h"] or 0) >= 60]
                imgs = [x for x in inside if x["kind"] == "image" and x["w"] >= 90 and (x["h"] or 0) >= 90]
                if imgs_all and not imgs:
                    # a cluster of narrow cut-outs is one picture for the layout
                    gx0 = min(x["x"] for x in imgs_all); gx1 = max(x["x"] + x["w"] for x in imgs_all)
                    gy0 = min(x["y"] for x in imgs_all); gy1 = max(x["y"] + (x["h"] or 0) for x in imgs_all)
                    grp = dict(imgs_all[0], x=gx0, w=gx1 - gx0, y=gy0, h=gy1 - gy0, _group=[x for x in imgs_all])
                    imgs = [grp]
                txts = [x for x in inside if x["kind"] == "text"]
                icons = [x for x in inside if x["kind"] == "icon"]
                if len(icons) == 1 and txts and icons[0]["x"] > b["x"] + b["w"] * 0.6:
                    ic = icons[0]
                    dw = ic.get("disc_w") or int(ic["w"]) + 24
                    d_bg = ic.get("disc_bg") or SAGE
                    d_ink = INK_DARK if is_dark(d_bg) else INK_LIGHT
                    icon_html = (f'<div style="width:{dw}px;height:{dw}px;border-radius:50%;background:{d_bg};display:flex;align-items:center;justify-content:center;margin:0 auto">'
                                 f'<div style="width:{int(ic["w"])}px;height:{int(ic["h"])}px;background:{d_ink};-webkit-mask:url({URLBASE}/{board}/assets/{ic["file"]}) center/contain no-repeat;mask:url({URLBASE}/{board}/assets/{ic["file"]}) center/contain no-repeat"></div></div>')
                    txt_html = "".join(pp for j, pp in enumerate(parts) if inside[j]["kind"] in ("text", "badge", "cta"))
                    body_html = (f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr>'
                                 f'<td valign="middle" style="padding-right:18px">{txt_html}</td>'
                                 f'<td valign="middle" width="{dw}">{icon_html}</td></tr></table>')
                elif len(imgs) == 1 and txts and imgs[0]["x"] + imgs[0]["w"] < b["x"] + b["w"] * 0.55 \
                        and any(t["x"] > imgs[0]["x"] + imgs[0]["w"] - 10 and t["y"] < imgs[0]["y"] + (imgs[0]["h"] or 0) and t["y"] + (t["h"] or 30) > imgs[0]["y"] for t in txts):
                    # picture on the left of the copy: two columns, picture first
                    grp_ = imgs[0].get("_group")
                    pis = [inside.index(x) for x in grp_] if grp_ else [inside.index(imgs[0])]
                    pi = pis[0]
                    img_html = "".join(parts[j] for j in pis)
                    txt_html = "".join(pp for j, pp in enumerate(parts) if j not in pis)
                    iw = min(int(imgs[0]["w"]), int(cw * 0.42))
                    if not grp_:
                        img_html = re.sub(r"width:\d+px", f"width:{iw}px", img_html)
                    body_html = (f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr>'
                                 f'<td valign="middle" width="{iw}" style="padding-right:18px">{img_html}</td>'
                                 f'<td valign="middle">{txt_html}</td></tr></table>')
                elif len(imgs) == 1 and txts and imgs[0]["x"] > b["x"] + b["w"] * 0.45 \
                        and any(t["x"] + (t["w"] or 0) < imgs[0]["x"] + 10 and t["y"] < imgs[0]["y"] + (imgs[0]["h"] or 0) and t["y"] + (t["h"] or 30) > imgs[0]["y"] for t in txts):
                    # image on the right of the copy: two columns
                    grp_ = imgs[0].get("_group")
                    pis = [inside.index(x) for x in grp_] if grp_ else [inside.index(imgs[0])]
                    pi = pis[0]
                    img_html = "".join(parts[j] for j in pis)
                    txt_html = "".join(pp for j, pp in enumerate(parts) if j not in pis)
                    iw = min(int(imgs[0]["w"]), int(cw * 0.42))
                    if not grp_:
                        img_html = re.sub(r"width:\d+px", f"width:{iw}px", img_html)
                    body_html = (f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr>'
                                 f'<td valign="top" style="padding-right:18px">{txt_html}</td>'
                                 f'<td valign="middle" width="{iw}">{img_html}</td></tr></table>')
                else:
                    body_html = "".join(parts)
                divs.append((cw, f'<div style="width:{cw}px;max-width:100%;margin:0 auto;border-radius:{radius}px;'
                                 f'background:{card_bg};{"box-shadow:inset 0 0 0 1px rgba(242,246,234,0.3);" if k == "glass" else ""}padding:28px 30px;box-sizing:border-box">{body_html}</div>'))
            if len(divs) == 1:
                rows.append(f'<tr><td align="center" {td}><div style="padding:24px 0 0">{divs[0][1]}</div></td></tr>')
            else:
                band_h = int(max(cb["h"] for cb in band))
                cells = "".join(f'<td valign="top" style="padding:0 6px">{d.replace("box-sizing:border-box", f"box-sizing:border-box;min-height:{band_h}px", 1)}</td>' for _, d in divs)
                rows.append(f'<tr><td align="center" {td}><div style="padding:24px 0 0"><table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto"><tr>{cells}</tr></table></div></td></tr>')
            i = jb; continue
        i += 1
    # the last section's bottom room, as the design left it
    for pb in blocks[i_prev:]:
        if pb["kind"] not in ("ground", "decor"):
            last_bottom = max(last_bottom or 0, pb["y"] + block_h(pb))
    if last_bottom is not None and last_g is not None:
        end_ = next((gb["y"] + gb["h"] for gb in grounds if gb["bg"] == last_g and gb["y"] <= last_bottom <= gb["y"] + gb["h"] + 4), None)
        tail = int(max(0, min(320, (end_ if end_ is not None else (H or last_bottom)) - last_bottom)))
        if tail:
            rows.append(f'<tr><td style="background:{last_g};height:{tail}px;line-height:{tail}px;font-size:0">&nbsp;</td></tr>')
    fonts_css = (HERE / "design" / "fonts.css").read_text().replace("url('fonts/", "url('/design/fonts/") \
        if (HERE / "design" / "fonts.css").is_file() else ""
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(name)}</title><style>{fonts_css} body{{margin:0;background:{canvas}}}</style></head>
<body style="margin:0;background:{canvas}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{canvas}"><tr><td align="center">
<table role="presentation" width="{int(W)}" cellpadding="0" cellspacing="0" style="width:{int(W)}px;max-width:100%;table-layout:fixed;background:{canvas}">
{"".join(wrap_gradients(rows))}
<tr><td style="height:60px;background:{ground_at(H - 1)}"></td></tr>
</table></td></tr></table></body></html>'''


# ------------------------------------------------------------------ run ---

def run_board(bank, board, brand, only=None):
    set_bedrock(brand)
    B = Bank(bank, brand)
    src_f = bank / "boards" / board / "Components.bundle.js"
    nodes, src_text = BP.load_nodes(src_f)
    css = B.board_css(board)
    abs_ = artboards(nodes)
    out_dir = SHOTS / board
    out_dir.mkdir(parents=True, exist_ok=True)
    shots = sorted(out_dir.glob("[0-9][0-9].png"))
    rects_f = out_dir / "rects.json"
    rects = json.loads(rects_f.read_text()) if rects_f.is_file() else []
    qa, n = [], 0
    for i, ab in enumerate(abs_, 1):
        if only and i not in only:
            continue
        blocks, W, H, canvas = extract(nodes, ab, css, B, src_text)
        if not any(b["kind"] == "text" for b in blocks):
            for stale in out_dir.glob(f"{i:02d}-clean.*"):
                stale.unlink()            # an empty frame on the board is not an email
            for stale in out_dir.glob(f"{i:02d}-spec.*"):
                stale.unlink()
            continue
        # the export's own render of this artboard, matched by size
        shot = None
        abx, aby = BP.abs_pos(ab)
        # the board's render lists artboards in the same left-to-right order
        # as the DOM: same count → same rank, checked by size
        if len(rects) == len(abs_):
            rank = sorted(range(len(abs_)), key=lambda k_: BP.abs_pos(abs_[k_])[0]).index(i - 1)
            rc = sorted(rects, key=lambda r_: r_["x"])[rank]
            if abs(rc["w"] - W) <= 3 and abs(rc["h"] - H) <= 6:
                shot = f"{rects.index(rc) + 1:02d}.png"
        for j, rc in enumerate(rects, 1):
            if shot is None and abs(rc["w"] - W) <= 3 and abs(rc["h"] - H) <= 6 and abs(rc["x"] - abx) <= 3 and abs(rc["y"] - aby) <= 3:
                shot = f"{j:02d}.png"; break
        if shot is None:
            for j, rc in enumerate(rects, 1):
                if abs(rc["w"] - W) <= 3 and abs(rc["h"] - H) <= 6 and not rc.get("_u"):
                    rc["_u"] = True; shot = f"{j:02d}.png"; break
        blocks = compose_heroes(blocks, W, H, (out_dir / shot) if shot else None, out_dir, board, i)
        for cb in blocks:
            if cb["kind"] in ("glass", "panel", "tile") and sum(1 for x in cb.get("inside", []) if x["kind"] == "image") >= 2:
                cb["inside"] = compose_heroes(cb["inside"], W, H, (out_dir / shot) if shot else None, out_dir, board, i, tag=f"c{int(cb['y'])}")
        blocks = fit_assets(blocks, out_dir)
        name = ab["style"].get("data-name") or f"{board} #{i}"
        sp = spec_of(blocks, W, H, canvas, board, i, name)
        sp["export_picture"] = shot
        (out_dir / f"{i:02d}-spec.json").write_text(json.dumps(sp, indent=1, default=str) + "\n")
        (out_dir / f"{i:02d}-spec.md").write_text(spec_md(sp).encode("utf-8", "ignore").decode("utf-8") + "\n")
        doc = render(blocks, W, H, canvas, board, name, B, brand)
        (out_dir / f"{i:02d}-clean.html").write_text(doc.encode("utf-8", "ignore").decode("utf-8"))
        n += 1
        issues = []
        lost = [b for b in blocks if b["kind"] == "image" and not b.get("real")]
        if lost:
            issues.append(f"{len(lost)} image(s) lost in the export — placeholders / store photo")
        if not any(b["kind"] == "logo" for b in blocks):
            issues.append("no wordmark found")
        if not any(b["kind"] == "cta" for b in blocks):
            issues.append("no CTA found")
        qa.append(dict(i=i, name=name, w=int(W), h=int(H), shot=shot, issues=issues,
                       blocks=[f"{b['kind']}{' ' + str(int(b.get('size', 0))) + 'px' if b.get('size') else ''}" for b in blocks]))
    # the QA page
    cards = []
    for q in qa:
        orig = f'<img src="{URLBASE}/{board}/{q["shot"]}" loading="lazy">' if q["shot"] else '<div class="none">no picture</div>'
        iss = "".join(f"<li>{e(x)}</li>" for x in q["issues"]) or "<li>clean</li>"
        cards.append(f'''<section class="pair"><h2>#{q["i"]:02d} {e(q["name"])} <span>{q["w"]}×{q["h"]}</span></h2>
<div class="cols"><div><div class="lbl">Original (export)</div>{orig}</div>
<div><div class="lbl">Rebuilt (clean HTML) · <a href="{URLBASE}/{board}/{q["i"]:02d}-clean.html" target="_blank">open</a> · <a href="{URLBASE}/{board}/{q["i"]:02d}-spec.md" target="_blank">the replication spec</a></div>
<iframe src="{URLBASE}/{board}/{q["i"]:02d}-clean.html" loading="lazy" style="width:{q["w"]}px;height:{min(q["h"] + 80, 6600)}px"></iframe></div></div>
<details><summary>Issues · blocks read</summary><ul>{iss}</ul><p class="k">{e(" → ".join(q["blocks"]))}</p></details></section>''')
    (out_dir / "qa.html").write_text(f'''<!doctype html><meta charset="utf-8"><title>Sweep QA — {e(board)}</title>
<link rel="stylesheet" href="/design/fonts.css"><style>
body{{margin:0;background:#141614;color:#f2f6ea;font:14px/1.5 "Untitled Sans",system-ui,sans-serif}} .wrap{{padding:24px}}
h1{{font:400 34px "GT Super Display",Georgia,serif;margin:0 0 4px}} h2{{font:400 20px "GT Super Display",Georgia,serif;margin:0 0 10px}} h2 span{{color:#a9ae9f;font:13px "Untitled Sans",sans-serif;margin-left:8px}}
.pair{{border-top:1px solid #2b2f2a;padding:22px 0}} .cols{{display:flex;gap:28px;align-items:flex-start;overflow-x:auto}}
.cols img{{display:block;width:auto;max-width:820px;height:auto}} iframe{{border:1px solid #2b2f2a;background:#0c100f}} .lbl{{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:#a9ae9f;margin-bottom:8px}}
details{{margin-top:10px;color:#a9ae9f}} summary{{cursor:pointer;color:#c7cfad}} .k{{font-size:12px}} .none{{width:600px;height:400px;display:grid;place-items:center;color:#a9ae9f;border:1px dashed #2b2f2a}}
</style><div class="wrap"><h1>Sweep QA — {e(board)}</h1><p>{n} emails rebuilt. Left: the bank's export. Right: the same email as clean HTML on the bedrock.</p>{"".join(cards)}</div>''')
    print(f"{board}: {n} rebuilt -> {out_dir}/qa.html")
    return qa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--board", default=None)
    ap.add_argument("--only", default=None, help="artboard numbers, e.g. 2,5")
    ap.add_argument("--brand", required=True)
    a = ap.parse_args()
    only = {int(x) for x in a.only.split(",")} if a.only else None
    for b in ([a.board] if a.board else boards_in(a.bank)):
        run_board(Path(a.bank), b, a.brand, only)


if __name__ == "__main__":
    main()
