"""Measured reject check: how far a printed product strays from its true outline. The true outline is the product-only
render from the set's own camera (product_sets_blender.product_pass), so both are measured in the same frame.

    python3 shape_check.py <print.png> <true-product.png>

For each product: how far the print's nearest edge sits from the true outline, as a percent of the product's width, on
average and at the worst 5% of the outline. An edge is used, not a dark mask, because pad and shadow tones vary by scene.
Rejected past the limits. Needs numpy, scipy and pillow.
"""
import json
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

MAX_MEAN_OFF = 1.5      # percent of product width
MAX_WORST_OFF = 4.0


def check(printed, true):
    t = Image.open(true).convert("RGBA")
    alpha = ndi.binary_fill_holes(ndi.binary_closing(np.asarray(t)[:, :, 3] > 128, iterations=10))
    lum = np.asarray(Image.open(printed).convert("L").resize(t.size, Image.LANCZOS)).astype(float)
    grad = ndi.gaussian_gradient_magnitude(lum, 2)
    lab, n = ndi.label(alpha)
    out = []
    for i in range(1, n + 1):
        tr = lab == i
        if tr.sum() < alpha.size * 0.02:
            continue
        width = 2 * ndi.distance_transform_edt(tr).max()
        ring = ndi.binary_dilation(tr, iterations=int(width * 0.12)) ^ ndi.binary_erosion(tr, iterations=int(width * 0.12))
        edges = (grad > np.percentile(grad[ring], 80)) & ring
        dist = ndi.distance_transform_edt(~edges)
        line = tr ^ ndi.binary_erosion(tr)
        off = dist[line] / width * 100
        row = {"mean_off_pct": round(float(off.mean()), 2), "worst_off_pct": round(float(np.percentile(off, 95)), 2)}
        row["ok"] = row["mean_off_pct"] <= MAX_MEAN_OFF and row["worst_off_pct"] <= MAX_WORST_OFF
        out.append(row)
    return out


if __name__ == "__main__":
    print(json.dumps(check(sys.argv[1], sys.argv[2])))
