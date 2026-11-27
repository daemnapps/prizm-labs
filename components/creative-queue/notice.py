#!/usr/bin/env python3
"""owner's session-start notice: creator's cuts that came back since he last heard (email_lead, 2026-11-06; owner's since
2026-11-11: "yo solo estoy de facilitadora ... owner los revisa", then "Solo el aviso a owner, por ahora").

email_lead: "creator no debería tener un botón de que me mande a mí cuando esté done, sino que me llegue a claude", and,
asked how, "Al abrir sesión". So creator presses nothing: when his cut is in returned/ on Drive, email_lead's next Claude
session opens with one line naming it.

    python3 components/creative-queue/notice.py brief

Reads only. It asks the person's own page server (PF-14 (page server)) for /data/videos, the same list creator's view
shows (statics.py list --role video-editor, cached there), so a session start never waits on Drive. It prints for
TOLD only ("owner", who checks the cuts), and only what is new: a hand-off whose files in returned/ grew since the last
notice. What it has told is kept beside the page server's own state, outside git (<caches>/<person>/notice-seen.json),
the one file it writes. No page server, no answer, an unknown person: it prints nothing and exits 0, never an error
into a session (the task-greeting hook's contract).
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))                    # appended, never ahead of this component
from run_kit import paths  # noqa: E402
REPO = paths.repo(HERE)
sys.path.append(str(REPO / "components" / "page-features" / "kit"))

PAGE = "/v/_templates/content-queue.html"
TOLD = "owner"                                                    # who hears that a cut is back: the one who checks it                         # the family whose /data/videos the server answers
SEEN = "notice-seen.json"
TIMEOUT = 4


def fetch_videos(port, timeout=TIMEOUT):
    """The page server's video hand-offs, or None."""
    req = urllib.request.Request("http://127.0.0.1:%d/data/videos" % port,
                                 headers={"Referer": "http://127.0.0.1:%d%s" % (port, PAGE)})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def new_backs(rows, seen):
    """(lines, seen after): each hand-off whose returned/ files grew since `seen` {key: files}."""
    out, after = [], dict(seen)
    for r in sorted(rows or [], key=lambda x: str(x.get("key"))):
        if not isinstance(r, dict) or not r.get("key"):
            continue
        n = r.get("returned_files") or 0
        if (r.get("returned_work") or 0) and n > (seen.get(r["key"]) or 0):
            out.append("%s (%s, %d files back) %s" % (r.get("title") or r["key"], str(r.get("brand") or "").upper(), n,
                                                      r.get("drive_url") or ""))
        after[r["key"]] = n
    return out, after


def brief(person, state_dir, fetch=fetch_videos, say=print):
    """Print the notice for `person`; returns how many cuts it named."""
    if person != TOLD:
        return 0
    try:
        port = json.loads((state_dir / "config.json").read_text())["port"]
        got = fetch(int(port))
    except Exception:
        return 0
    try:
        seen = json.loads((state_dir / SEEN).read_text())
        seen = seen if isinstance(seen, dict) else {}
    except Exception:
        seen = {}
    lines, after = new_backs((got or {}).get("rows"), seen)
    try:
        (state_dir / SEEN).write_text(json.dumps(after, indent=1, sort_keys=True) + "\n")
    except OSError:
        pass
    if lines:
        say("creator: %d video%s back in returned/, for you to check: %s" % (
            len(lines), "" if len(lines) == 1 else "s", " · ".join(lines)))
    return len(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] != ["brief"]:
        print(__doc__.strip().split("\n\n")[1].strip())
        return 0
    try:
        from run_kit import people
        import server
        person = people.whoami(REPO)
        brief(person, server.state_of(person))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
