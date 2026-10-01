#!/usr/bin/env python3
"""Build the knowledge file the site's Ask box answers from.

    python3 tools/build_ask.py

Reads the repo's own guides — README, WALKTHROUGH, ASK, and every tool's
README and SOP — splits them at their headings, and writes
docs/ask/knowledge.json. The Ask box searches it in the browser; the AI
worker (receiver/ask-ai.js), when it is switched on, answers from the same
file and nothing else. Re-run it whenever a guide changes.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/daemnapps/prizm-labs/blob/main/"
# WALKTHROUGH.md is left out: it only points elsewhere now
# A tool's front door is not always called README. Some — the video
# teardown among them, which is the tool the whole site is about — use
# START-HERE, HOW-TO-RUN-IT or CLAUDE instead, and every one of them was
# invisible to the Ask box until 2026-09-26. Anything at a tool's top level
# counts as a guide; everything deeper (prompts, machine internals, the chain)
# does not, so the answers stay in the reader's language.
GUIDES = {"README.md", "SOP.md", "START-HERE.md", "HOW-TO-RUN-IT.md",
          "CLAUDE.md", "WHICH-MODELS.md", "MACHINE-README.md"}
# My Feeds is one tool with three parts (organic, paid, library), so its
# parts' front doors sit one level deeper.
FILES = ["README.md", "ASK.md"] + sorted(
    str(p.relative_to(ROOT)) for pat in ("tools/*/*.md", "tools/my-feeds/*/*.md")
    for p in ROOT.glob(pat) if p.name in GUIDES)
MAX = 1600


def anchor(h):
    return re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-")


def clean(t):
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    # Fenced commands out. The Ask box answers in sentences, and a shell block
    # flattened into prose reads as noise — "python3 machine/line.py teardown
    # <video> --brand <brand> swipe in, spec out python3 …". The source link
    # beside every answer goes to the file that has the command in full.
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"^ {4,}\S.*$", "", t, flags=re.M)              # indented code
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)                 # images
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)              # links → their words
    t = re.sub(r"^\|[\s:|-]+\|\s*$", "", t, flags=re.M)           # table rules
    t = re.sub(r"^\|(.*)\|\s*$", lambda m: " — ".join(c.strip() for c in m.group(1).split("|") if c.strip()) + ".", t, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def chunks(path):
    text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
    tool = path.split("/")[1] if path.startswith("tools/") else ""
    title0 = (re.search(r"^#\s+(.+)$", text, re.M) or [None, path])[1].strip()
    parts = re.split(r"^(#{1,3}\s+.+)$", text, flags=re.M)
    head, out = title0, []
    for p in parts:
        if re.match(r"^#{1,3}\s+", p):
            head = p.lstrip("#").strip(); continue
        body = clean(p)
        if len(body) < 40:
            continue
        for i in range(0, len(body), MAX):
            out.append({"doc": title0, "section": head, "tool": tool, "path": path,
                        "url": REPO + path + ("#" + anchor(head) if head != title0 else ""),
                        "text": body[i:i + MAX]})
    return out


def main():
    items = [c for f in FILES if (ROOT / f).is_file() for c in chunks(f)]
    out = ROOT / "docs/ask/knowledge.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"built": __import__("datetime").date.today().isoformat(),
                               "items": items}, ensure_ascii=False), encoding="utf-8")
    print(f"{len(items)} sections from {len(FILES)} guides -> {out.relative_to(ROOT)} "
          f"({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
