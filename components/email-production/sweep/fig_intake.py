#!/usr/bin/env python3
"""A Figma file (.fig) → the format bank, the same door the HTML export
went through. the owner drops the .fig in Downloads; this reads it whole.

    python3 sweep/fig_intake.py "<file>.fig" --brand <brand> [--out <bank dir>]

For every page of the file, every top-level frame of email width becomes
one artboard. The frame's tree is written in the shape the rebuild engine
already reads (boards/<board>/nodes.json — tag/style/text nodes with parent
links), every image fill is written out as an asset with a fig-assets.css
mapping, and a reference picture of each artboard is drawn from the same
tree (results/format-bank/<board>/NN.png + rects.json) so the hero crops
have something to crop from. Then the usual steps run: rebuild → qc →
pictures → sheets → the QA page and the team mirror.

Needs the fig-kiwi decoder: `pip install fig2sketch` in the scratch venv
(sweep/intake sets it up on first use).
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SCRATCH = Path(os.environ.get("SWEEP_SCRATCH", "/private/tmp/claude-501/sweep"))
VENV = SCRATCH / "figdec" / "venv"
SHOTS = Path(os.environ["FORMAT_BANK_DIR"]).resolve() if os.environ.get("FORMAT_BANK_DIR") else HERE / "results" / "format-bank"


def ensure_decoder():
    py = VENV / "bin" / "python"
    if not py.is_file():
        VENV.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        subprocess.run([str(VENV / "bin" / "pip"), "install", "-q", "fig2sketch", "pillow"], check=True)
    return py


def decode_with_venv(fig_path, out_json):
    """Run the decode inside the venv (it needs fig2sketch's modules) and
    dump the node list as plain JSON we can read here."""
    code = r'''
import sys, json
sys.path.insert(0, [p for p in sys.path if "site-packages" in p][0])
from figformat import decodefig
fig, z = decodefig.decode(sys.argv[1])
nodes = fig["nodeChanges"]
def plain(o):
    if isinstance(o, dict):
        return {k: plain(v) for k, v in o.items() if k not in ("derivedTextData", "vectorData", "styleOverrideTable")}
    if isinstance(o, (list, tuple)):
        return [plain(x) for x in o]
    if isinstance(o, bytes):
        return None
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return str(o)
out = []
for n in nodes:
    d = {k: plain(n.get(k)) for k in ("guid", "parentIndex", "type", "name", "size", "transform", "visible", "opacity",
                                       "fillPaints", "strokePaints", "cornerRadius", "rectangleCornerRadiiIndependent",
                                       "rectangleTopLeftCornerRadius", "rectangleTopRightCornerRadius",
                                       "rectangleBottomLeftCornerRadius", "rectangleBottomRightCornerRadius",
                                       "fontSize", "fontName", "lineHeight", "letterSpacing", "textAlignHorizontal",
                                       "textCase", "textData", "strokeWeight", "mask", "maskType", "blendMode") if k in n}
    if d.get("guid") is not None:
        d["guid"] = list(d["guid"]) if isinstance(d["guid"], (list, tuple)) else d["guid"]
    out.append(d)
json.dump(out, open(sys.argv[2], "w"))
print(len(out))
'''
    r = subprocess.run([str(ensure_decoder()), "-c", code, str(fig_path), str(out_json)], capture_output=True, text=True)
    if r.returncode:
        sys.exit("decode failed:\n" + r.stderr[-2000:])
    return int(r.stdout.strip().splitlines()[-1])


def rgb(c):
    if not c:
        return None
    return f"rgb({int(round(c.get('r', 0) * 255))},{int(round(c.get('g', 0) * 255))},{int(round(c.get('b', 0) * 255))})"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "page"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fig")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--out", default=None, help="bank dir (default scratch/format-bank-<brand>)")
    ap.add_argument("--skip-pictures", action="store_true")
    a = ap.parse_args()
    from PIL import Image, ImageDraw, ImageFont
    import zipfile

    bank = Path(a.out) if a.out else SCRATCH / f"format-bank-{a.brand}"
    (bank / "boards").mkdir(parents=True, exist_ok=True)
    (bank / "assets").mkdir(exist_ok=True)
    raw = bank / "nodes-raw.json"
    n = decode_with_venv(a.fig, raw)
    nodes = json.loads(raw.read_text())
    print(f"{n} nodes decoded")
    byid = {tuple(x["guid"]): x for x in nodes if x.get("guid") is not None}
    kids = {}
    for x in nodes:
        p = x.get("parentIndex", {}).get("guid")
        if p is not None:
            kids.setdefault(tuple(p), []).append(x)
    for lst in kids.values():
        lst.sort(key=lambda x: str(x.get("parentIndex", {}).get("position", "")))
    z = zipfile.ZipFile(a.fig)
    img_files = {Path(nm).name: nm for nm in z.namelist() if nm.startswith("images/") and not nm.endswith("/")}

    # the wordmark: the brand's identity svg, copied into the bank's assets
    ws = Path(os.environ.get("AI_WORKSPACE", "."))
    sys.path.append(str(ws / "components" / "brandpath"))
    import brandpath as BP  # noqa: E402  brand-identity (was identity/) by plan name
    for svg in sorted(BP.brand_path(a.brand, "brand-identity", root=ws / "brands").glob("*.svg")):
        (bank / "assets" / f"{a.brand}.svg").write_bytes(svg.read_bytes()); break

    def image_hash(paint):
        im = paint.get("image") or {}
        h = im.get("hash")
        if isinstance(h, list):
            return bytes(h).hex()
        if isinstance(h, str):
            return h
        return None

    pages = [x for x in nodes if x.get("type") == "CANVAS"]
    boards_made = []
    for page in pages:
        board = slug(page.get("name"))
        frames = [x for x in kids.get(tuple(page["guid"]), []) if x.get("type") in ("FRAME", "SECTION", "INSTANCE", "SYMBOL")
                  and 550 <= (x.get("size") or {}).get("x", 0) <= 820 and (x.get("size") or {}).get("y", 0) >= 500
                  and x.get("visible", True)]
        # sections hold frames: look one level down too
        for sec in [x for x in kids.get(tuple(page["guid"]), []) if x.get("type") == "SECTION"]:
            frames += [x for x in kids.get(tuple(sec["guid"]), []) if x.get("type") in ("FRAME", "INSTANCE")
                       and 550 <= (x.get("size") or {}).get("x", 0) <= 820 and (x.get("size") or {}).get("y", 0) >= 500]
        if not frames:
            continue
        bdir = bank / "boards" / board
        (bdir / "assets").mkdir(parents=True, exist_ok=True)
        out_nodes, css_rules, asset_seen = [], [], {}
        rects = []
        shots_dir = SHOTS / board
        shots_dir.mkdir(parents=True, exist_ok=True)

        def add(node, parent_idx):
            out_nodes.append(node)
            node["_parent"] = parent_idx
            return len(out_nodes) - 1

        root = add({"tag": "div", "style": {"left": 0, "top": 0, "width": 30000, "height": 30000}, "text": None}, None)

        def walk(x, parent_idx, ox, oy):
            if not x.get("visible", True):
                return
            if x.get("mask"):
                return                      # a mask shapes its siblings; it is not painted
            st = {}
            tr = x.get("transform") or [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
            a_, c_, tx = tr[0]; b_, d_, ty = tr[1]
            sz = x.get("size") or {}
            w, h = float(sz.get("x", 0) or 0), float(sz.get("y", 0) or 0)
            st["left"], st["top"] = 0.0, 0.0
            st["width"], st["height"] = w, h
            if abs(a_ - 1) > 1e-3 or abs(b_) > 1e-3 or abs(c_) > 1e-3 or abs(d_ - 1) > 1e-3:
                st["transform"] = f"matrix({a_:.4f},{b_:.4f},{c_:.4f},{d_:.4f},{tx:.2f},{ty:.2f})"
            else:
                st["left"], st["top"] = float(tx), float(ty)
            if x.get("opacity") is not None and x["opacity"] < 1:
                st["opacity"] = float(x["opacity"])
            tag = "div"
            text = None
            fills = [p for p in (x.get("fillPaints") or []) if p.get("visible", True)]
            solid = next((p for p in fills if p.get("type") == "SOLID"), None)
            grad = next((p for p in fills if p.get("type", "").startswith("GRADIENT")), None)
            image = next((p for p in fills if p.get("type") == "IMAGE"), None)
            if x.get("type") == "TEXT":
                tag = "span"
                text = ((x.get("textData") or {}).get("characters") or "").replace(" ", "\n")
                st["fontSize"] = float(x.get("fontSize") or 16)
                fn = x.get("fontName") or {}
                st["fontFamily"] = f'"{fn.get("family", "")}"'
                style_ = (fn.get("style") or "").lower()
                st["fontWeight"] = 700 if "bold" in style_ else 600 if "semi" in style_ else 500 if "medium" in style_ else 300 if "light" in style_ else 400
                if "italic" in style_:
                    st["fontStyle"] = "italic"
                if solid:
                    st["color"] = rgb(solid.get("color"))
                al = (x.get("textAlignHorizontal") or "LEFT").lower()
                st["textAlign"] = {"left": "left", "center": "center", "right": "right", "justified": "justify"}.get(al, "left")
                if (x.get("textCase") or "") == "UPPER":
                    st["textTransform"] = "uppercase"
                lh = x.get("lineHeight") or {}
                if lh.get("units") == "PIXELS":
                    st["lineHeight"] = f"{lh.get('value')}px"
                elif lh.get("units") == "PERCENT":
                    st["lineHeight"] = f"{lh.get('value')}%"
                ls = x.get("letterSpacing") or {}
                if ls.get("value"):
                    st["letterSpacing"] = f"{ls['value']}px" if ls.get("units") == "PIXELS" else f"{ls['value'] / 100:.3f}em"
            else:
                if image:
                    hsh = image_hash(image)
                    if hsh and hsh in img_files:
                        if hsh not in asset_seen:
                            data = z.read(img_files[hsh])
                            try:
                                im = Image.open(io.BytesIO(data)); fmt = "png" if im.mode in ("RGBA", "P", "LA") else "jpg"
                                fname = f"{hsh[:16]}.{fmt}"
                                (bdir / "assets" / fname).write_bytes(data)
                                (shots_dir / "assets").mkdir(exist_ok=True)
                                (shots_dir / "assets" / fname).write_bytes(data)
                                asset_seen[hsh] = fname
                            except Exception:
                                asset_seen[hsh] = None
                        if asset_seen.get(hsh):
                            cls = f"fig-asset-{len(css_rules) + 1}"
                            css_rules.append((cls, asset_seen[hsh]))
                            st["className"] = cls
                            st["backgroundImage"] = f"url(./assets/{asset_seen[hsh]})"
                elif solid:
                    st["backgroundColor"] = rgb(solid.get("color"))
                    if solid.get("opacity", 1) < 1:
                        st["backgroundColor"] = st["backgroundColor"].replace("rgb(", "rgba(").replace(")", f",{solid['opacity']:.2f})")
                elif grad:
                    stops = grad.get("stops") or []
                    cols = ", ".join(f"{rgb(s_.get('color'))} {int((s_.get('position') or 0) * 100)}%" for s_ in stops[:6]) or "rgba(0,0,0,0), rgba(0,0,0,0.5)"
                    st["backgroundImage"] = f"linear-gradient(180deg, {cols})"
                r = x.get("cornerRadius")
                if r:
                    st["borderRadius"] = f"{float(r)}px"
                if x.get("type") == "ELLIPSE" and w and abs(w - h) < 2:
                    st["borderRadius"] = "50%"
                if x.get("type") in ("VECTOR", "BOOLEAN_OPERATION", "STAR", "REGULAR_POLYGON", "LINE"):
                    # a filled shape the size of a button or a panel is a fill (a pill,
                    # a band); a small one is an icon
                    if solid and w >= 100 and h >= 30 and x.get("type") != "LINE":
                        tag = "div"
                        st["backgroundColor"] = rgb(solid.get("color"))
                        st.setdefault("borderRadius", f"{min(w, h) / 2:.0f}px" if x.get("type") == "BOOLEAN_OPERATION" or (w >= 3 * h) else "0px")
                    else:
                        tag = "svg"
                        if solid and "color" not in st:
                            st["color"] = rgb(solid.get("color"))
            idx = add({"tag": tag, "style": st, "text": text or None}, parent_idx)
            for k in kids.get(tuple(x["guid"]), []):
                walk(k, idx, 0, 0)

        for i, fr in enumerate(frames, 1):
            fx, fy = float(fr["transform"][0][2]), float(fr["transform"][1][2])
            # the artboard sits at its own place on the page; its frame node is the one the engine finds
            walk(fr, root, fx, fy)
            rects.append({"x": fx, "y": fy, "w": float(fr["size"]["x"]), "h": float(fr["size"]["y"]), "name": fr.get("name") or ""})
        # nodes.json: parents by index
        (bdir / "nodes.json").write_text(json.dumps(out_nodes))
        (bdir / "fig-assets.css").write_text("\n".join(f".{c} {{ background-image: url(./assets/{f}); }}" for c, f in css_rules) + "\n")
        (shots_dir / "rects.json").write_text(json.dumps(rects, indent=1))
        boards_made.append((board, len(frames)))
        print(f"{board}: {len(frames)} artboard(s), {len(css_rules)} image placements, {len(asset_seen)} assets")

        # the reference picture of each artboard, drawn from the tree
        def find_font(family, weight, italic):
            cands = []
            for d in (Path.home() / "Library/Fonts", Path("/Library/Fonts"), Path("/System/Library/Fonts"), HERE / "design" / "fonts"):
                if d.is_dir():
                    cands += list(d.glob("*.ttf")) + list(d.glob("*.otf"))
            fam = (family or "").strip('"').lower().replace(" ", "")
            want = ("bold" if weight >= 600 else "medium" if weight >= 500 else "regular")
            best = None
            for c in cands:
                nm = c.stem.lower().replace(" ", "").replace("-", "")
                if fam and fam in nm:
                    score = (want in nm) + (("italic" in nm) == italic)
                    if best is None or score > best[0]:
                        best = (score, c)
            return best[1] if best else None
        font_cache = {}

        def font_for(st):
            key = (st.get("fontFamily"), int(st.get("fontWeight") or 400), st.get("fontStyle") == "italic", int(st.get("fontSize") or 16))
            if key not in font_cache:
                path = find_font(key[0], key[1], key[2])
                try:
                    font_cache[key] = ImageFont.truetype(str(path), key[3]) if path else ImageFont.load_default(size=key[3])
                except Exception:
                    font_cache[key] = ImageFont.load_default()
            return font_cache[key]

        def paint(node_idx, im, draw, ox, oy):
            nd = out_nodes[node_idx]; st = nd["style"]
            m = re.search(r"matrix\(([^)]+)\)", st.get("transform") or "")
            if m:
                a_, b_, c_, d_, tx, ty = [float(v) for v in m.group(1).split(",")]
            else:
                a_, b_, c_, d_, tx, ty = 1, 0, 0, 1, st.get("left", 0), st.get("top", 0)
            x0, y0 = ox + tx, oy + ty
            w, h = st.get("width") or 0, st.get("height") or 0
            if a_ < 0:
                x0 -= w
            if d_ < 0:
                y0 -= h
            box = (int(x0), int(y0), int(x0 + w), int(y0 + h))
            if nd["tag"] == "span" and nd.get("text"):
                f = font_for(st)
                col = st.get("color") or "rgb(0,0,0)"
                txt = nd["text"].upper() if st.get("textTransform") == "uppercase" else nd["text"]
                y = y0
                lh = float(st.get("fontSize") or 16) * 1.25
                # wrap each line to the box width, as the design does
                lines = []
                for para in txt.split("\n"):
                    words, cur = para.split(" "), ""
                    for wd in words:
                        cand = (cur + " " + wd).strip()
                        if w and draw.textlength(cand, font=f) > w and cur:
                            lines.append(cur); cur = wd
                        else:
                            cur = cand
                    lines.append(cur)
                for line in lines:
                    tw = draw.textlength(line, font=f) if hasattr(draw, "textlength") else 0
                    xx = x0 if st.get("textAlign") in (None, "left") else (x0 + (w - tw) / 2 if st.get("textAlign") == "center" else x0 + w - tw)
                    draw.text((xx, y), line, font=f, fill=col)
                    y += lh
            else:
                cls = st.get("className")
                if cls:
                    fname = dict(css_rules).get(cls)
                    try:
                        src = Image.open(bdir / "assets" / fname).convert("RGBA")
                        if w > 0 and h > 0:
                            sc = max(w / src.size[0], h / src.size[1])
                            rs = src.resize((max(1, int(src.size[0] * sc)), max(1, int(src.size[1] * sc))))
                            cx, cy = (rs.size[0] - int(w)) // 2, (rs.size[1] - int(h)) // 2
                            crop = rs.crop((cx, cy, cx + int(w), cy + int(h)))
                            im.paste(crop, (int(x0), int(y0)), crop)
                    except Exception:
                        pass
                elif st.get("backgroundColor"):
                    col = st["backgroundColor"]
                    mm = re.match(r"rgba?\((\d+),(\d+),(\d+)(?:,([\d.]+))?\)", col)
                    if mm:
                        rgba = (int(mm.group(1)), int(mm.group(2)), int(mm.group(3)), int(float(mm.group(4) or 1) * 255))
                        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
                        ImageDraw.Draw(layer).rounded_rectangle(box, radius=int(float(str(st.get("borderRadius") or "0").rstrip("px%")) if "%" not in str(st.get("borderRadius")) else int(w / 2)), fill=rgba)
                        im.alpha_composite(layer)
                elif st.get("backgroundImage", "").startswith("linear-gradient"):
                    cols = re.findall(r"rgb\((\d+),(\d+),(\d+)\)", st["backgroundImage"])
                    if cols and h > 0:
                        c1, c2 = [tuple(int(v) for v in c) for c in (cols[0], cols[-1])]
                        for yy in range(int(h)):
                            t = yy / max(1, h - 1)
                            col = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3)) + (255,)
                            draw.line([(int(x0), int(y0 + yy)), (int(x0 + w), int(y0 + yy))], fill=col)
            for ci, cn in enumerate(out_nodes):
                if cn.get("_parent") == node_idx:
                    paint(ci, im, draw, x0, y0)

        if not a.skip_pictures:
            for i, fr in enumerate(frames, 1):
                W, H = int(fr["size"]["x"]), int(min(fr["size"]["y"], 6500))
                im = Image.new("RGBA", (W, H), (255, 255, 255, 255))
                draw = ImageDraw.Draw(im)
                # the artboard's own node is the (i)th child of root
                art_idx = [k for k, nd in enumerate(out_nodes) if nd.get("_parent") == root][i - 1]
                # paint it at 0,0 (its own transform carries the page offset)
                st = out_nodes[art_idx]["style"]
                saved = dict(st)
                st["left"], st["top"] = 0.0, 0.0
                st.pop("transform", None)
                paint(art_idx, im, draw, 0, 0)
                out_nodes[art_idx]["style"] = saved
                im.convert("RGB").save(shots_dir / f"{i:02d}.png")
            print(f"  {len(frames)} reference picture(s) -> {shots_dir}")
    if not boards_made:
        sys.exit("no email-sized frames found in the file")
    # a Components.bundle.js placeholder so the bank looks like the HTML export to the tools
    for board, _ in boards_made:
        f = bank / "boards" / board / "Components.bundle.js"
        if not f.is_file():
            f.write_text("// from a .fig file — the nodes live in nodes.json\n")
    print("\nbank:", bank)
    print("boards:", ", ".join(f"{b} ({n})" for b, n in boards_made))


if __name__ == "__main__":
    main()
