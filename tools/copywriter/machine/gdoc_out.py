#!/usr/bin/env python3
"""Finished copy as a Google Doc — the version that leaves the machine.

    /usr/bin/python3 machine/gdoc_out.py <output-slug> --folder <drive-folder-id>
    /usr/bin/python3 machine/gdoc_out.py --all --folder <drive-folder-id>

Damon's ruling (2026-08-31): copy also lives as a Google Doc, the way the
video brief does. This takes a published source from output/<slug>/copy.md,
renders it as a document, and uploads it through the shared Drive plumbing
(service account, update-in-place: same name in the same folder updates
rather than duplicating).

--folder is the Drive folder the docs land in — e.g. the delivery folder the
source videos arrived in, so copy sits next to creative.

DP-1 (2026-09-02) — the ONE change on this side, and it is a deletion. This
file used to `sys.path.insert` into the video machine's internals and
`import drive` out of them; the pipe now lives in
`components/gdrive-creator/` and is imported as a component. The destination
is passed IN rather than derived, which is what retires the second half of
that reach: working out a default folder meant importing the video machine's
`chain` too. `--folder` is now required — it was already how the delivery flow
called this (see ../CLAUDE.md).

Needs the Google client libraries, which live under the system python —
run with /usr/bin/python3 (the shebang path above), not homebrew's.
"""
import argparse, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
# Python puts the script's own folder first on sys.path, where our copy.py
# shadows the stdlib `copy` module and Google's client dies importing
# deepcopy. Strip exactly that entry before anything imports.
sys.path = [q for q in sys.path if Path(q or ".").resolve() != HERE]
# Load md by file instead of by name for the same reason.
import importlib.util
_spec = importlib.util.spec_from_file_location("md", HERE / "md.py")
MD = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(MD)
_COMPONENT = ROOT.parent.parent.parent / "components" / "gdrive-creator"
if not _COMPONENT.is_dir():                  # a workspace mounted elsewhere
    _COMPONENT = Path.home() / "Projects" / "ai-workspace" / "components" / "gdrive-creator"
sys.path.append(str(_COMPONENT))        # appended, never ahead of this machine
from gdrive_creator import engine as drive


STYLE = """<style>
body{font-family:Arial,Helvetica,sans-serif;font-size:11pt;line-height:1.5;max-width:7.5in;color:#202124}
h1{font-size:16pt;margin:0 0 6pt;font-weight:700} h2{font-size:13pt;margin:14pt 0 4pt;font-weight:700}
h3{font-size:11.5pt;margin:10pt 0 3pt;font-weight:700}
table{border-collapse:collapse;font-size:10.5pt} td,th{border:1px solid #dadce0;padding:4pt 8pt}
code{font-family:Arial,Helvetica,sans-serif;background:#f1f3f4;padding:0 3pt}
blockquote{margin:6pt 0 6pt 0;padding:6pt 10pt;background:#f8f9fa;border-left:3px solid #dadce0;color:#3c4043}
hr{border:0;border-top:1px solid #dadce0;margin:12pt 0}
</style>"""


def build_html(slug):
    src = ROOT / "output" / slug / "copy.md"
    if not src.is_file():
        sys.exit(f"no published copy at output/{slug}/copy.md — run publish.py first")
    body = MD.render(src.read_text(encoding="utf-8"))
    title = f"Copy — {slug}"
    html_path = ROOT / "output" / slug / "copy-gdoc.html"
    html_path.write_text(f"<html><head><meta charset='utf-8'>{STYLE}"
                         f"</head><body>{body}</body></html>", encoding="utf-8")
    return html_path, title


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--folder", required=True,
                    help="Drive folder id the docs land in")
    a = ap.parse_args()

    slugs = ([d.name for d in (ROOT / "output").iterdir() if (d / "copy.md").is_file()]
             if a.all else [a.slug])
    if not slugs or slugs == [None]:
        sys.exit("name an output slug, or pass --all")

    svc = drive.service()
    parent = a.folder
    for slug in slugs:
        html_path, title = build_html(slug)
        url, made = drive.upload_doc(html_path, title, parent, svc=svc)
        print(f"  {'created' if made else 'updated'} — {url}")


if __name__ == "__main__":
    main()
