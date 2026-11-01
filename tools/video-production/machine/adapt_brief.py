#!/usr/bin/env python3
"""Translate a teardown-machine brief into the dialect scenes.py parses.

    adapt_brief.py <source brief.md> <run folder>

Two machines, two brief shapes, and they do not agree — which is the thing
asset-index/CLAUDE.md warns about: "they must agree on words, or the two
machines produce two incompatible vocabularies for the same footage."

  teardown stage-5 writes   ### Scene 1 · 0:00 – 0:01.8 · 1.8 s
                            **On screen.** …   **You say.** …   **How.** …
                            > **Prompt** … the generation prompt, verbatim

  scenes.py reads           **Scene 1 · 0:00 – 0:01.8 · 1.8s · TYPE B**
                            **Happens:** …   > **Say:** …   **Delivery:** …

This adapter is the seam, not a rewrite of either. Nothing is invented: a
field the source brief did not write comes out empty, because a storyboard
that fills its own gaps hides the ones worth fixing.

TYPE, from what the scene actually does:
  A  someone speaks on camera        — none here; this ad is voice-over
  B  a generated clip or owned footage
  C  a product packshot, moved
"""
import re, sys
from pathlib import Path


def adapt(text: str) -> str:
    head = text.split("### Scene 1", 1)[0]
    out = [head.rstrip(), "\n---\n"]
    blocks = re.findall(r"^### Scene (\d+) · ([0-9:.]+) – ([0-9:.]+) · ([\d.]+) ?s\n(.*?)(?=^### Scene |\Z)",
                        text, re.M | re.S)
    for n, a, b, secs, body in blocks:
        screen = re.search(r"\*\*On screen\.\*\*\s*(.+?)(?=\n\n|\Z)", body, re.S)
        say = re.search(r"\*\*You say\.\*\*\s*(.+?)(?=\n\n|\Z)", body, re.S)
        how = re.search(r"\*\*How\.\*\*\s*(.+?)(?=\n\n|\Z)", body, re.S)
        prompt = re.search(r"^> \*\*Prompt\*\*[^\n]*\n((?:^>.*\n)+)", body, re.M)
        pl = ""
        if prompt:
            pl = " ".join(re.sub(r"^> ?", "", l).strip()
                          for l in prompt.group(1).splitlines()).strip()
        refs = " ".join(re.findall(r"<<<[0-9a-f]{8}…?>>>", pl))
        pl = re.sub(r"<<<[0-9a-f]{8}…?>>>", "", pl).replace("**+ THE TAIL**", "").strip()
        one = lambda m: " ".join(m.group(1).split()) if m else ""
        # a product hold with no action is a C; everything else here is a B
        t = "C" if re.search(r"held (?:up )?(?:still|to|into) the lens|label square to camera",
                             one(screen), re.I) else "B"
        out += [f"**Scene {n} · {a} – {b} · {secs}s · TYPE {t}**", ""]
        out += [f"**Happens:** {one(screen)}", ""]
        if say:
            out += [f"> **Say:** {one(say)}", ""]
        if how:
            out += [f"**Delivery:** {one(how)}", ""]
        if refs:
            out += [f"**Refs:** {refs}", ""]
        if pl:
            out += [f"**Still:** {pl}", ""]
        out += ["---", ""]
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, run = Path(sys.argv[1]), Path(sys.argv[2])
    (run / "stages").mkdir(parents=True, exist_ok=True)
    dest = run / "stages" / "5-brief.md"
    dest.write_text(adapt(src.read_text()))
    print(f"adapted -> {dest}")
