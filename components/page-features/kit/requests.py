"""The generic request loop, QB-5 (production contract): carry out the request lines a person pasted from a page,
through the page family's production adapter (components/creative-queue/contract.py), in one command.

    requests.py <file> [--family F] [--by NAME]   the pasted text, saved as is
    requests.py <file> --dry-run                  read the lines, say what would run; change nothing

One shared line for every kind of work (the generic half of email-production's ask.py, lifted):

    Request (<item id>, part <n|->): <word> <words…> (from <Name>)

A line that starts with a tab right under a "Request (" line continues it (PF-13b (slow buttons): a note of several
lines from the page kit — kit/serve.py writes each further line of a note tab-first; the tab is dropped and the
line break kept). A tab line that itself starts a request, or holds "Email request (", is a line of its own.

<word> is a change word the adapter's adapter.json lists (shared: words · picture · redo · move · remove · ok · note,
plus its kind's own); `-` is the whole piece. The family's _templates/<family>.actions.json names the adapter
({"adapter": "components/<component>/…/adapter.json", "words_reviewer", "words_lane"}), found beside
<family>.sources.json the way kit/serve.py finds that. --family may be left out when only one actions file exists.
Each line runs the adapter's `apply` in the order pasted; a word change by anyone but the words reviewer files a
components/review request to that reviewer (review_request.file_request). Then ONLY the paths apply reported changed
(and those review records) are committed by pathspec and pushed (creative-queue's qcore.commit_paths: a rejected
push pulls --no-rebase and pushes again). Never forced; a git failure is said, not worked around.

FALLBACK, one release: an old "Email request (" line from the emails page is mapped onto the shared words (family
emails); the four phrases that are not change words (use my own picture, Done, the Go, I scheduled it) stay with
email-production's ask.py and are listed as still to do.

Exit 0 all done · 1 something failed or is still to do · 2 nothing could be read.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent.parent / "run-kit"))           # appended, never ahead
from run_kit import paths  # noqa: E402  the one workspace locator (builder card rule 3)

REPO = paths.repo(HERE)
sys.path.append(str(REPO / "components" / "creative-queue"))
import contract  # noqa: E402  the production contract: load(), command(), REFUSED
import qcore  # noqa: E402  commit_paths: by pathspec, pull --no-rebase on a rejected push

TEMPLATES = REPO / "platform" / "views" / "viewers" / "_templates"
LINE = re.compile(r"^Request \(\s*(?P<id>[^,()\s]+)\s*,\s*part\s+(?P<part>\d+|-)\s*\):\s*(?P<word>[A-Za-z_-]+)"
                  r"(?P<rest>.*)$", re.S)
FROM = re.compile(r"\s*\(from ([\w-]+)\)\s*$")
# the old line, read as ask.py reads it (ask.py:36 LINE), for one release
OLD = re.compile(r"Email request \([^)]*\):\s*(?P<code>[^\[]*?)\s*\[(?P<brand>[\w-]+)/(?P<label>[\w-]+)"
                 r"(?:,\s*section\s+(?P<section>\d+))?(?:,\s*picture\s+(?P<picture>\d+))?\]\s*·\s*(?P<rest>.*)$")
OLD_FAMILY = "emails"
OLD_REST = "components/email-production/adapter/ask.py"
# the old page phrases (ask.py:38 WHAT) onto the shared words; None = not a change word, it stays on ask.py
OLD_WHAT = [("change this picture", "picture"), ("use my own picture", None), ("this part looks right", "ok"),
            ("redesign this part", "redo"), ("move this part", "move"), ("remove this part", "remove"),
            ("change the words", "words"), ("make the missing parts", "fill"), ("done: send to email_lead", None),
            ("make the klaviyo draft", None), ("redo the whole email", "redo"), ("i scheduled it in klaviyo", None)]


def _clean(raw):
    return raw.strip().lstrip("-•* ").strip()


def _who(rest):
    m = FROM.search(rest)
    return (m.group(1), rest[:m.start()]) if m else (None, rest)


def _old(line):
    """One old "Email request (" line as a request on the shared words, or (None, why, todo)."""
    m = OLD.search(line)
    if not m:
        return None, "can't read: %s" % line[:120], False
    who, rest = _who(m.group("rest"))
    low = rest.lower()
    hit = next(((k, w) for k, w in OLD_WHAT if low.startswith(k)), None)
    if not hit:
        return None, "unknown request: %s" % rest[:80], False
    phrase, word = hit
    code = m.group("code").strip() or "%s/%s" % (m.group("brand"), m.group("label"))
    if word is None:
        return None, "%s · %s: not a change word — still to do with %s, this line alone: %s" % (
            code, phrase, OLD_REST, line), True
    after = rest[len(phrase):].strip()
    note = after[1:].strip() if after.startswith(":") else ""
    sec = m.group("section")
    part = "-" if word == "fill" or phrase == "redo the whole email" or sec is None else sec
    if word == "picture":
        payload = "%s: %s" % (m.group("picture") or "0", note)
    elif word == "move":
        payload = "up" if after.lower().startswith("up") else "down"
    elif word == "words":
        payload = after.lstrip(": ").strip()
    else:
        payload = note
    return {"id": "%s__%s" % (m.group("brand"), m.group("label")), "part": part, "word": word, "payload": payload,
            "by": who, "family": OLD_FAMILY, "code": code}, None, False


def joined(text):
    """The text's lines with each tab-continued line put back onto the "Request (" line above it (PF-13b)."""
    out = []
    for raw in text.splitlines():
        lone = _clean(raw)
        if raw.startswith("\t") and out and _clean(out[-1]).startswith("Request (") \
                and not lone.startswith("Request (") and "Email request (" not in raw:
            out[-1] += "\n" + raw[1:]
        else:
            out.append(raw)
    return out


def parse(text, family=None):
    """[(request, None, False)] or [(None, why, todo)] per request line, in order; other lines are ignored."""
    out = []
    for raw in joined(text):
        line = _clean(raw)
        if "Email request (" in line:
            out.append(_old(line))
            continue
        if not line.startswith("Request ("):
            continue
        m = LINE.match(line)
        if not m:
            out.append((None, "can't read: %s" % line[:120], False))
            continue
        who, rest = _who(m.group("rest"))
        rest = rest.strip()
        payload = rest[1:].strip() if rest.startswith(":") else rest
        out.append(({"id": m.group("id"), "part": m.group("part"), "word": m.group("word").lower(),
                     "payload": payload, "by": who, "family": family,
                     "code": "%s part %s" % (m.group("id"), m.group("part"))}, None, False))
    return out


def actions_for(family):
    """The family's actions file (dict); ValueError naming what is missing."""
    f = TEMPLATES / ("%s.actions.json" % family)
    try:
        a = json.loads(f.read_text())
    except OSError:
        raise ValueError("no actions file for family %r (%s)" % (family, f.name))
    except ValueError as e:
        raise ValueError("%s is not JSON: %s" % (f.name, e))
    if not isinstance(a, dict) or not isinstance(a.get("adapter"), str):
        raise ValueError("%s names no adapter" % f.name)
    return a


def _names_adapter(p):
    """True for an actions file this loop can carry; content-queue's (PF-13 (direct buttons)) names none."""
    try:
        a = json.loads(p.read_text())
    except (OSError, ValueError):
        return True                    # unreadable: still counted, and actions_for says what is wrong with it
    return isinstance(a, dict) and isinstance(a.get("adapter"), str)


def only_family():
    got = sorted(p.name[:-len(".actions.json")] for p in TEMPLATES.glob("*.actions.json") if _names_adapter(p))
    if len(got) != 1:
        raise ValueError("name the page family with --family (actions files: %s)" % (", ".join(got) or "none"))
    return got[0]


def call_adapter(argv):
    """THE SEAM: one adapter apply, from the repo root; (exit code, its JSON answer)."""
    p = subprocess.run(argv, cwd=str(REPO), capture_output=True, text=True, stdin=subprocess.DEVNULL)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = {"ok": False, "message": (p.stderr or p.stdout).strip()[-300:] or "no answer"}
    return p.returncode, out if isinstance(out, dict) else {"ok": False, "message": "not an object"}


def file_review(k, res, reviewer, lane):
    """A review request to the words reviewer naming the change; the record's path (not committed here)."""
    sys.path.insert(0, str(REPO / "components" / "review"))
    from review_request import file_request
    edits = []
    try:
        edits = json.loads(k["payload"])
    except ValueError:
        pass
    lines = "; ".join('%s: "%s" -> "%s"' % (e.get("path"), e.get("before", "?"), e.get("value"))
                      for e in edits if isinstance(e, dict))
    out = file_request(
        asset={"warehouse": "repo", "ref": res.get("ref") or (res.get("paths") or [""])[0],
               "title": "%s: %s changed the words" % (k["code"], k["by"])},
        type="text", reviewers=[reviewer], lane=lane, requested_by=k["by"].lower(),
        notes="\n".join([
            "What this is: %s changed words in %s. %s" % (k["by"], k["id"], lines),
            "Why you: the words are yours.",
            "What I need: check the new words read right. Not the design or the pictures.",
            "What ends your part: you leave a verdict, or change the words again from the page."]),
        root=str(REPO), commit=False)
    return out.get("path")


def main(argv=None, git=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--family")
    ap.add_argument("--by")
    ap.add_argument("--dry-run", action="store_true")
    x = ap.parse_args(argv)
    got = parse(Path(x.file).read_text(encoding="utf-8"), x.family)
    if not got:
        print("no request lines found (each starts with \"Request (\")")
        return 2
    done, failed, todo, changed, firsts = [], [], [], [], {}
    for k, why, later in got:
        if why:
            (todo if later else failed).append(why)
            print(("… " if later else "✗ ") + why)
            continue
        k["by"] = k["by"] or x.by
        say = "%s · %s%s" % (k["code"], k["word"], (": " + k["payload"][:80]) if k["payload"] else "")
        try:
            fam = k["family"] or firsts.setdefault("family", only_family())
            acts = actions_for(fam)
            m = contract.load(REPO / acts["adapter"])
        except ValueError as e:
            failed.append("%s — %s" % (say, e))
            print("✗ %s — %s" % (say, e))
            continue
        if k["word"] in contract.REFUSED or k["word"] not in m["words"]:
            failed.append(say)
            print("✗ %s — not a change word for %s (words: %s)%s" % (say, fam, " · ".join(m["words"]),
                  "; it stays an approval" if k["word"] in contract.REFUSED else ""))
            continue
        if not k["by"]:
            failed.append(say)
            print("✗ %s — who asked? end the line with (from <Name>) or pass --by" % say)
            continue
        if x.dry_run:
            print("would run: %s (from %s)" % (say, k["by"]))
            continue
        args = [k["id"], k["part"], k["word"]] + ([k["payload"]] if k["payload"] else []) + ["--by", k["by"]]
        code, res = call_adapter(contract.command(m, "apply", args))
        ok = code == 0 and res.get("ok") is True
        msg = str(res.get("message") or "")
        print(("✓ " if ok else "✗ ") + say + ("" if ok and msg in ("", "done") else " — " + msg))
        if not ok:
            failed.append(say)
            continue
        done.append(k)
        changed += [p for p in res.get("paths") or [] if isinstance(p, str)]
        reviewer = acts.get("words_reviewer")
        if k["word"] == "words" and reviewer and k["by"].lower() != str(reviewer).lower():
            try:
                rec = file_review(k, res, reviewer, acts.get("words_lane") or "%s-words" % fam)
                if rec:
                    changed.append(rec)
                print("  %s has been sent a review request for these words" % reviewer)
            except Exception as e:  # noqa: BLE001 — the change stays; the failed review request is said
                failed.append("%s: the words changed but the review request failed (%s)" % (k["code"], str(e)[:120]))
                print("  ✗ couldn't send %s the review request: %s" % (reviewer, str(e)[:120]))
    changed = sorted(set(changed))
    if done and changed:
        msg = "%s requests: %s" % (done[0]["by"], "; ".join("%s %s" % (k["code"], k["word"]) for k in done))
        try:
            sha = qcore.commit_paths([REPO / p for p in changed], msg[:300], REPO, run=git)
            print("git: shared %s (%d paths)" % (sha[:10], len(changed)))
        except RuntimeError as e:
            failed.append("git")
            print("git: not shared — %s. Tell the page's owner; never force." % str(e)[:200])
    elif done:
        print("git: nothing changed on disk to commit")
    return 0 if not failed and not todo else 1


if __name__ == "__main__":
    sys.exit(main())
