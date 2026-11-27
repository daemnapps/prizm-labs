"""FACE-KEEPING COVERS (2026-11-13): a cover made from a video's own frame keeps that frame's faces pixel for pixel.

Why: the picture model redraws every face it is given, and a redrawn face is a coin flip against the person the
video shows (an ad's covers came back "a different person" run after run). People who come from the video are not
redrawn: the frame's faces and lips are put back over the made picture, exactly, and the model may change everything
around them (the concept, the product from its kit, the room).

    keep(picture, frame, read)    after the picture is made, before the words: each face of the frame (the face reader's
                                  face and lips boxes, merged, padded by PAD) is matched to the made picture's own face
                                  nearest it at a like size (MOVE_MAX, SIZE_MIN), and the frame's face is laid there at
                                  that face's size, with a soft edge. A person the made picture lost or moved too far
                                  is not pasted: the record says so and the cover is not fit to file.
    verify(picture, rec)          on the finished cover (after the words): every kept face's core pixels are still
                                  what was laid, exactly. A changed pixel (a headline over a face, any later edit) fails.
    clear_band(...)               the headline is set in a band clear of the kept faces when its own band covers one.

Records `kept_faces` on the cover's record: {"pass", "faces": [{"frame_box", "box", "shift", "ring_diff",
"core_sha256"}], "why"}.
"""
from __future__ import annotations

import hashlib

PAD = 0.30          # a face box grows by this share of its size on each side (hair line, jaw, ears)
FEATHER = 0.12      # the soft edge outside the kept core, as a share of the box's smaller side
MOVE_MAX = 0.18     # how far (share of the picture) the made picture may have moved a person and still be the same one
SIZE_MIN = 0.45     # the made face's area against the frame's: within this and its inverse, the same person


def _merge(boxes):
    """Face and lips boxes as one box per person (overlapping boxes merged)."""
    out = []
    for b in sorted(boxes, key=lambda b: -(b[2] - b[0]) * (b[3] - b[1])):
        for i, o in enumerate(out):
            if b[0] < o[2] and b[2] > o[0] and b[1] < o[3] and b[3] > o[1]:
                out[i] = (min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3]))
                break
        else:
            out.append(tuple(b))
    return out


def _pad(b, size, pad=PAD):
    w, h = b[2] - b[0], b[3] - b[1]
    return (max(0, int(b[0] - w * pad)), max(0, int(b[1] - h * pad)),
            min(size[0], int(b[2] + w * pad)), min(size[1], int(b[3] + h * pad)))


def _core_sha(im, box):
    return hashlib.sha256(im.convert("RGB").crop(box).tobytes()).hexdigest()


def _match(f, faces, size):
    """The made picture's face that stands for frame face `f`: the nearest centre, a like size."""
    W, H = size
    cx, cy, fw, fh = (f[0] + f[2]) / 2, (f[1] + f[3]) / 2, f[2] - f[0], f[3] - f[1]
    best = None
    for g in faces:
        gx, gy, gw, gh = (g[0] + g[2]) / 2, (g[1] + g[3]) / 2, g[2] - g[0], g[3] - g[1]
        d = ((gx - cx) / W) ** 2 + ((gy - cy) / H) ** 2
        ratio = (gw * gh) / max(1.0, fw * fh)
        if d <= MOVE_MAX ** 2 and SIZE_MIN <= ratio <= 1 / SIZE_MIN and (best is None or d < best[0]):
            best = (d, g)
    return best[1] if best else None


def keep(picture, frame, read, save=True):
    """Lay the frame's faces over the made picture, each where the made picture's own face reader finds that person,
    at that size. Returns the record; writes the picture when `save`."""
    from PIL import Image, ImageDraw, ImageFilter
    cov = Image.open(picture).convert("RGB")
    W, H = cov.size
    src = Image.open(frame).convert("RGB").resize(cov.size, Image.LANCZOS)
    fw0, fh0 = Image.open(frame).size
    sx, sy = W / float(fw0), H / float(fh0)

    def faces_of(pic, kx=1.0, ky=1.0):
        found = [tuple(float(x) for x in b) for b in (read(str(pic)) or [])]
        clipped = [(max(0, b[0] * kx), max(0, b[1] * ky), min(W, b[2] * kx), min(H, b[3] * ky)) for b in found]
        return _merge([b for b in clipped if b[2] - b[0] >= 4 and b[3] - b[1] >= 4])
    try:
        want = faces_of(frame, sx, sy)
        got = faces_of(picture)
    except Exception as ex:                                          # noqa: BLE001
        return {"pass": False, "faces": [], "why": "the face reader stopped (%s)" % type(ex).__name__}
    if not want:
        return {"pass": True, "faces": [], "why": "no face in the frame: nothing to keep"}
    rec = {"pass": True, "faces": []}
    for f in want:
        g = _match(f, got, cov.size)
        row = {"frame_box": [int(v) for v in _pad(f, cov.size)]}
        if g is None:
            row.update(lined_up=False, why="the made picture lost or moved this person (no face of its own near the "
                                           "frame's, at a like size)")
            rec["pass"] = False
            rec["faces"].append(row)
            continue
        box = _pad(g, cov.size)
        w, h = box[2] - box[0], box[3] - box[1]
        piece = src.crop(tuple(row["frame_box"])).resize((w, h), Image.LANCZOS)
        edge = max(3, int(min(w, h) * FEATHER))
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rectangle((edge, edge, w - edge - 1, h - edge - 1), fill=255)
        soft = mask.filter(ImageFilter.GaussianBlur(edge / 2.0))
        core = (edge * 2, edge * 2, w - edge * 2, h - edge * 2)       # well inside the soft edge: the frame's, exactly
        soft.paste(255, core)
        cov.paste(piece, (box[0], box[1]), soft)
        row.update(lined_up=True, box=list(box), core=[box[0] + core[0], box[1] + core[1], box[0] + core[2],
                                                       box[1] + core[3]],
                   core_sha256=hashlib.sha256(piece.crop(core).tobytes()).hexdigest())
        rec["faces"].append(row)
    if save:
        cov.save(picture)
    if not rec["pass"]:
        rec["why"] = "; ".join(f["why"] for f in rec["faces"] if f.get("why"))
    return rec


def verify(picture, rec, frame=None):
    """Every kept face's core on the finished picture is still what was laid, pixel for pixel."""
    from PIL import Image
    if not rec or not rec.get("faces"):
        return dict(rec or {}, verified=bool(rec and rec.get("pass")))
    cov = Image.open(picture).convert("RGB")
    out = dict(rec, verified=True)
    for f in rec["faces"]:
        if not f.get("lined_up"):
            out["verified"] = False
            continue
        if _core_sha(cov, tuple(f["core"])) != f["core_sha256"]:
            f["changed"] = True
            out["verified"] = False
    if not out["verified"]:
        out["pass"] = False
        out["why"] = out.get("why") or "a kept face changed after it was laid (words or an edit over it)"
    return out


def boxes_of(rec):
    """The kept faces' boxes on the cover, for the words step to keep clear of."""
    return [tuple(f["box"]) for f in (rec or {}).get("faces") or [] if f.get("lined_up")]
