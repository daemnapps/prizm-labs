#!/usr/bin/env python3
"""Put finished copy where a person goes to get it.

    python3 publish.py                  # every run that has finished copy
    python3 publish.py <label>          # one run

`results/` is the machine's working record — eleven stages, the prompt as
sent, timings, the lot. Nobody trafficking an ad wants to open that. This
writes the finished copy, and only the finished copy, into `output/`.

The layout is the video library's, deliberately (components/video-teardown/
machine/library.py): one folder per source, one file per version, a new
version never overwrites an old one, and an index file that makes the folder
readable on its own without opening anything else.

    output/
      <source-slug>/
        copy.md            what shipped: every format, headlines, descriptions
        v1.md, v2.md       one file per version — a re-run never overwrites
        source.md          what it was built from, and what was open

Text only, and in git. Unlike the teardowns there is no media here worth
mirroring to Drive — copy is words, and words belong in the repo where they
can be diffed.
"""

import json
import re
import sys
from datetime import datetime

import paths as P
from paths import HERE

RESULTS = HERE / "results"          # history; new runs file under runs/ — see paths.all_runs()
OUTPUT = HERE / "output"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def slug(s, n=48):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s or "").strip("-").lower()
    return s[:n] or "untitled"


def next_version(d):
    """Versions count up and never reuse a number — the point is being able to
    see what a prompt change did to the copy for the same source."""
    n = 0
    for f in d.glob("v*.md"):
        m = re.match(r"v(\d+)\.md$", f.name)
        if m:
            n = max(n, int(m.group(1)))
    return n + 1


def copy_block(render_text):
    """Everything up to the machine's own notes. The CHECKS receipt and the
    per-format commentary are real and worth keeping in results/, but they are
    not copy and a buyer should not have to scroll past them."""
    if not render_text:
        return ""
    cut = re.search(r"^#{1,3}\s*CHECKS\b", render_text, re.M)
    return (render_text[:cut.start()] if cut else render_text).rstrip()


def publish(run_dir):
    rj = run_dir / "run.json"
    if not rj.is_file():
        return None
    st = json.loads(rj.read_text())
    render = run_dir / "stage8--render.md"
    brief = run_dir / "stage9--brief.md"
    if not render.is_file():
        return None  # nothing finished to publish

    # A source_reference that is only a stage file name ("01-teardown") names
    # the kind of record, not the source. Nine different <brand> statics all
    # carried "01-teardown" and were filed as nine versions of one piece
    # (2026-09-16). Those fall back to the run's own slug, which is unique.
    ref = st.get("source_reference") or ""
    if not ref or re.fullmatch(r"\d{2}-[a-z-]+(\.md)?", ref.strip()):
        ref = st.get("slug")
    dest = OUTPUT / slug(ref)
    dest.mkdir(parents=True, exist_ok=True)
    v = next_version(dest)

    body = copy_block(render.read_text())
    head = (f"<!-- {st.get('slug')} · v{v} · {now()} · "
            f"{st.get('brand','?')} · {st.get('format','?')} · "
            f"lane {st.get('lane','?')} -->\n\n")
    (dest / f"v{v}.md").write_text(head + body + "\n")
    # copy.md is always the newest — the file a person opens without choosing
    (dest / "copy.md").write_text(head + body + "\n")

    # what it came from, so the folder explains itself
    stages = st.get("stages", {})
    ctx = (st.get("context") or {}).get("picked") or []
    src = [
        f"# {st.get('source_reference') or st.get('slug')}",
        "",
        f"**Built from** `{st.get('source_path','?')}`  ",
        f"**Brand** {st.get('brand','?')} · **lane** {st.get('lane','?')} · "
        f"**source format** {st.get('format','?')}  ",
        f"**Written as** {st.get('output_formats','?')} for {st.get('channel','?')}  ",
        f"**Run** `{st.get('slug')}` · {st.get('generated_at','?')}",
        "",
        "## Brand context this copy was written from", "",
    ]
    src += [f"- `{p}`" for p in ctx] or ["- (none selected)"]
    src += ["", "## Versions here", ""]
    src += [f"- `v{i}.md`" for i in range(1, v + 1)]
    if brief.is_file():
        b = brief.read_text()
        m = re.search(r"^#{1,3}\s*BEFORE YOU RUN IT.*?$(.+)", b, re.M | re.S)
        if m:
            src += ["", "## Open before this runs", "", m.group(1).strip()[:2000]]
    (dest / "source.md").write_text("\n".join(src) + "\n")
    return dest, v


def main():
    OUTPUT.mkdir(exist_ok=True)
    want = sys.argv[1] if len(sys.argv) > 1 else None
    done = 0
    # Oldest run first, so version numbers follow the order the copy was
    # actually written and copy.md ends up holding the newest. Sorting by
    # folder name published an older, worse run over a newer one.
    def when(d):
        try:
            return json.loads((d / "run.json").read_text()).get("generated_at") or ""
        except Exception:
            return ""

    runs = P.all_runs()              # both homes: runs/copy-machine/<brand>/ and results/
    for d in sorted(runs, key=when):
        if want and d.name != want:
            continue
        got = publish(d)
        if got:
            dest, v = got
            print(f"  {d.name}  ->  output/{dest.name}/copy.md  (v{v})")
            done += 1
    if not done:
        print("nothing to publish — no run has finished copy yet")


if __name__ == "__main__":
    main()
