"""Follow one thing through a clip so a graphic can ride on it.

  python3 track.py clip.mp4 x,y,w,h [start_s]     prints JSON: [[t, cx, cy, w, h], ...] in the clip's pixels, one row per frame
Uses OpenCV's CSRT tracker from the box on the first frame (at start_s). Rows after a lost frame hold the last good box.
"""
import json
import sys

import cv2


def track(path, box, start=0.0):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 23.976
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError("cannot read " + path)
    make = getattr(cv2, "TrackerCSRT_create", None) or cv2.TrackerCSRT.create
    tr = make()
    tr.init(frame, tuple(int(v) for v in box))
    x, y, w, h = box
    rows, i = [[round(start, 3), x + w / 2, y + h / 2, w, h]], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        i += 1
        found, b = tr.update(frame)
        if found:
            x, y, w, h = b
        rows.append([round(start + i / fps, 3), round(x + w / 2, 1), round(y + h / 2, 1), round(w, 1), round(h, 1)])
    return rows


if __name__ == "__main__":
    b = [float(v) for v in sys.argv[2].split(",")]
    print(json.dumps(track(sys.argv[1], b, float(sys.argv[3]) if len(sys.argv) > 3 else 0.0)))
