#!/usr/bin/env python3
"""Make It Rain — the UMW talk. The one copy everyone edits is docs/umw/index.html
(served at daemn.co/umw). This makes a self-contained copy for a claude.ai artifact:
the site paths become files shipped beside the page.

    python3 tools/umw_artifact.py OUT_DIR
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
HERE = os.path.join(DOCS, "umw")
SITE = "https://daemn.co"


def build(out):
    src = open(os.path.join(HERE, "index.html")).read()
    covers = ['control', 'g01-h2', 'g01-h3', 'g01-h4', 'g01-h5', 'g01-h6']
    media = ['swipe.mp4', 'swipe.jpg', 'cast-doctors.jpg'] + [f'sw-{i}.jpg' for i in (1, 2, 4, 5, 7, 9)] \
        + [f'p-{x}-f1.jpg' for x in ('s1', 's8', 's21', 's2', 's6', 's16', 's26', 's34', 's40')] \
        + [f'cover-{c}.jpg' for c in covers] + [f'open-{c}.mp4' for c in covers]
    page = src.replace("/studio.css?v=prizm16", "studio.css").replace("/studio.js?v=8", "studio.js") \
              .replace("const M = '/three-doctors/m/';", "const M = 'm/';")
    page = re.sub(r'href="/(?!/)', f'href="{SITE}/', page)
    os.makedirs(os.path.join(out, "m"), exist_ok=True)
    open(os.path.join(out, "index.html"), "w").write(page)
    shutil.copy(os.path.join(DOCS, "studio.css"), out)
    open(os.path.join(out, "studio.js"), "w").write(open(os.path.join(DOCS, "studio.js")).read().replace("'/objects3d.js?v=2'", "'objects3d.js'"))
    shutil.copy(os.path.join(DOCS, "objects3d.js"), out)
    for m in sorted(set(media)):
        p = os.path.join(DOCS, "three-doctors", "m", m)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(out, "m", m))
        else:
            print("missing media:", m)
    shutil.copytree(os.path.join(HERE, "media"), os.path.join(out, "media"), dirs_exist_ok=True)
    print("artifact copy:", out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    build(os.path.abspath(sys.argv[1]))
