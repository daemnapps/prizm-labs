"""Carry out the requests a person pasted from the emails page, in one command (the team's lab, 2026-10-21).

    ask.py <file>            the pasted text, saved as is: one or more lines starting "Email request ("
    ask.py <file> --dry-run  read the requests and say what would run; change nothing

Each line names its email, part and picture exactly, in brackets: [brand/label, section i, picture k]. What runs:
- change this picture -> a TRY, LD-83 (picture try first): `try_picture.py`'s try_change on the house default model,
  into the run's tries/<P>/ (gitignored): she sees it at once; the email, the build and git are not touched;
- use try N / add try N -> `try_picture.py`'s add: try-N.jpg goes into the email (own_picture.place), its record and
  one picture learning are written, and it is committed with the rest;
- this part looks right, redesign this part, move this part up/down, remove this part,
  change the words, make the missing parts, Done: send to the team, redo the whole email, I scheduled it in Klaviyo
  -> one call each to email-production's own `adapter/sync.py apply`, in the order pasted;
- use my newest (made with <tool>): <what it shows> -> LD-90 (the team takes newest): `own_picture.py`'s take_newest: the
  newest picture in her Shared Assets/team/<person>/email-production/ is MOVED into the run's Drive media and goes into
  the email; the reply names where it went and the drive-move record; both records are committed with the email;
- use my own picture -> not run here (it needs the person's file and an alt text): listed under "still to do",
  for `own_picture.py place`.
Word changes from anyone but the team file a review request to the team (components/review file_request), so she is told.
Then everything that changed is committed in one commit (the emails' run folders, runs/learnings/, the review
record, and after an add platform/data/records/model-outcome/) and pushed after `git pull --rebase`. Pictures are
media and stay out of git (gitignored; on the Drive). A try commits nothing.

Output: one line per request, then what is still to do. Exit 0 all done · 1 something failed or is still to do ·
2 nothing could be read.
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(d for d in HERE.parents if (d / "components" / "run-kit").is_dir()) / "components" / "run-kit"))
from run_kit import paths  # noqa: E402

REPO = paths.repo(HERE)
SYNC = REPO / "tools" / "email-production" / "adapter" / "sync.py"
WORDS_REVIEWER = "pm"     # the words are the team's (README, "Requests from the email page")
LINE = re.compile(r"Email request \([^)]*\):\s*(?P<code>[^\[]*?)\s*\[(?P<brand>[\w-]+)/(?P<label>[\w-]+)"
                  r"(?:,\s*section\s+(?P<section>\d+))?(?:,\s*picture\s+(?P<picture>\d+))?\]\s*·\s*(?P<rest>.*)$")
WHAT = [("change this picture", "picture"), ("use my own picture", "own"), ("this part looks right", "ok"),
        ("redesign this part", "look"), ("move this part", "move"), ("remove this part", "remove"),
        ("change the words", "words"), ("make the missing parts", "fill"), ("done: send to pm", "done"),
        ("make the klaviyo draft", "go"),
        ("redo the whole email", "send_back"), ("i scheduled it in klaviyo", "scheduled"),
        ("add try", "add"), ("use try", "add"), ("use my newest", "newest")]
NEEDS_NOTE = {"picture", "look", "send_back"}
KEEP_MARKS = {"picture", "words", "fill"}   # same parts after the rebuild: keep the parts marked right (prepare.keep_card)


def parse(text):
    """[(request dict, None)] or [(None, why)] per request line; other lines are ignored."""
    out = []
    for raw in text.splitlines():
        if "Email request (" not in raw:
            continue
        m = LINE.search(raw.strip())
        if not m:
            out.append((None, "can't read: %s" % raw.strip()[:120]))
            continue
        rest, who = m.group("rest"), "graphic-designer"     # the role when no name is given, never a person (2026-10-27)
        w = re.search(r"\s*\(from (\w+)\)\s*$", rest)
        if w:
            who, rest = w.group(1), rest[:w.start()]
        low = rest.lower()
        hit = next(((key, a) for key, a in WHAT if low.startswith(key)), None)
        if not hit:
            out.append((None, "unknown request: %s" % rest[:80]))
            continue
        said, act = hit
        k = {"code": m.group("code").strip(), "brand": m.group("brand"), "label": m.group("label"), "action": act, "by": who}
        if m.group("section") is not None:
            k["section"] = int(m.group("section"))
        if m.group("picture") is not None:
            k["picture"] = int(m.group("picture"))
        after = rest[len(said):].strip()
        if act == "add":
            n = re.match(r"(\d+)\b", after)
            if not n:
                out.append((None, "%s: which try? say use try <n>" % k["code"]))
                continue
            k["n"] = int(n.group(1))
        elif act == "move":
            k["dir"] = "up" if after.lower().startswith("up") else "down"
        elif act == "newest":                               # use my newest (made with <tool>): <what it shows>
            mw = re.match(r"\(made with\s+([^)]*)\)\s*", after, re.I)
            if mw:
                k["made_with"], after = mw.group(1).strip(), after[mw.end():]
            if after.startswith(":"):
                k["note"] = after[1:].strip()
        elif act == "words":
            try:
                k["edits"] = json.loads(after.lstrip(": ").strip())
            except ValueError:
                out.append((None, "%s: the new words aren't readable" % k["code"]))
                continue
        elif after.startswith(":"):
            k["note"] = after[1:].strip()
        if act in NEEDS_NOTE and not k.get("note"):
            out.append((None, "%s: %s needs the change in words" % (k["code"], act)))
            continue
        if act in ("picture", "own", "add", "newest") and "picture" not in k:
            out.append((None, "%s: no picture named" % k["code"]))
            continue
        if act == "go" and who != "the team":
            out.append((None, "%s: the team makes the Klaviyo draft, after her words (the team's part is Done)" % k["code"]))
            continue
        if act == "scheduled" and who != "the team":
            out.append((None, "%s: only the team marks an email scheduled" % k["code"]))
            continue
        out.append((k, None))
    return out


def apply_one(k):
    """One call through sync.py apply (its own command), as the page's old request rows were."""
    call = {"id": uuid.uuid4().hex[:12], "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "email": "%s__%s" % (k["brand"], k["label"])}
    call.update({x: k[x] for x in ("brand", "label", "action", "by", "section", "picture", "note", "dir", "edits", "from_brief") if x in k})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump([call], fh)
    p = subprocess.run([sys.executable, str(SYNC), "apply", fh.name], cwd=str(REPO), capture_output=True, text=True)
    Path(fh.name).unlink()
    try:
        r = json.loads(p.stdout)[0]
        return r.get("state") == "applied", r.get("result") or ""
    except (ValueError, IndexError):
        return False, (p.stderr or p.stdout).strip()[-300:]


def _tp():
    sys.path.insert(0, str(HERE))
    import try_picture
    return try_picture


def _code(run, k):
    """The P code of the line's [section i, picture k] (own_picture.slots: the page's picture numbers)."""
    import own_picture
    spec = json.loads((run / "design" / "email.json").read_text())
    for n, i, j, _ in own_picture.slots(spec):
        if (i, j) == (k["section"], k["picture"]):
            return "P%d" % n
    raise SystemExit("no picture %d in section %d" % (k["picture"], k["section"]))


def try_one(k):
    """LD-83 (picture try first): one try of a picture change, on the house default model; nothing committed.
    Returns (ok, what to say)."""
    run = REPO / "runs" / "email-production" / k["brand"] / k["label"]
    try:
        made = _tp().try_change(run, _code(run, k), k["note"], k["by"])
    except KeyError as e:
        return False, e.args[0] if e.args else str(e)
    except (Exception, SystemExit) as e:  # noqa: BLE001 — said, never hidden (CannotRemake carries its offer)
        return False, str(e)[:400]
    if not made:
        return False, "the try made no picture"
    return True, "; ".join("try %d made: %s (%s) — say 'use try %d' to add it"
                           % (t["n"], run / t["made"], (t["judge"] or {}).get("verdict") or "judging…", t["n"])
                           for t in made)


def add_one(k):
    """LD-83 (picture try first): try N goes into the email (try_picture.add); committed with the batch."""
    run = REPO / "runs" / "email-production" / k["brand"] / k["label"]
    try:
        r = _tp().add(run, _code(run, k), k["n"], k["by"])
    except (Exception, SystemExit) as e:  # noqa: BLE001 — said, never hidden
        return False, str(e)[:400]
    bad = [s for s in r.get("rebuilt") or [] if not s.get("ok")]
    if bad:
        return False, "try %d is in, but %s stopped: %s" % (k["n"], bad[0]["step"], bad[0].get("said", "")[-200:])
    return True, "try %d added as %s" % (k["n"], r.get("picture"))


def newest_one(k):
    """LD-90 (the team takes newest): her team folder's newest picture is moved into the run's Drive media and placed
    (own_picture.take_newest). Returns (ok, what to say, the two record paths to commit with the run)."""
    sys.path.insert(0, str(HERE))
    import own_picture
    run = REPO / "runs" / "email-production" / k["brand"] / k["label"]
    try:
        r = own_picture.take_newest(run, _code(run, k), k.get("note") or "", k["by"], k.get("made_with") or "",
                                    role=own_picture.role_of(k["by"]))   # "my": the asker's role's returned/ for this email
    except (Exception, SystemExit) as e:  # noqa: BLE001 — said, never hidden
        return False, "%s (say: use my newest (made with <tool>): <what the new picture shows>)" % str(e)[:400], []
    recs = []
    for p in (r.get("outcome"), (r.get("moved") or {}).get("record")):
        if p:
            try:
                recs.append(str(Path(p).resolve().relative_to(Path(REPO).resolve())))
            except ValueError:
                recs.append(str(p))
    said = "%s (newest in %s) as %s; %s" % (r["newest"]["name"], r["newest"]["folder"], r.get("picture"),
                                            own_picture.moved_line(r))
    bad = [s for s in r.get("rebuilt") or [] if not s.get("ok")]
    if bad:
        return False, "%s is in, but %s stopped: %s" % (said, bad[0]["step"], bad[0].get("said", "")[-200:]), recs
    return True, said, recs


def pictures_up(brand, run, reach=None):
    """PF-21 (pictures reach every Mac): before a Done, every run:media picture the email names goes onto its Drive
    mirror. Returns None when all are up, else why the Done stops, naming each picture."""
    design = str(Path(__file__).resolve().parent.parent / "design")
    if design not in sys.path:
        sys.path.append(design)
    import layout_file as LF
    m = LF.mirror_media(brand, run, reach=reach)
    if m["error"]:
        return "the pictures did not reach Drive (%s), so nobody else can see them: %s; nothing marked done" % (
            m["error"], ", ".join(n for n in LF.media_names(run) if n not in m["put"] and n not in m["already"]))
    if m["not_here"]:
        return "these pictures are not on this Mac and not on Drive, so nobody else can see them: %s; nothing marked " \
               "done" % ", ".join(m["not_here"])
    return None


def mark_done(k, root=REPO):
    """the team's Done: the card says she is done (eve_done), and the team gets a review request. Nothing goes to Klaviyo."""
    run = Path(root) / "runs" / "email-production" / k["brand"] / k["label"]
    f = run / "klaviyo" / "card.json"
    c = json.loads(f.read_text())
    if c.get("klaviyo"):
        return False, "already a Klaviyo draft (%s)" % c["klaviyo"].get("campaign_id")
    stop = pictures_up(k["brand"], run)
    if stop:
        return False, stop
    c["eve_done"] = {"by": k["by"], "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    f.write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    sys.path.insert(0, str(REPO / "components" / "review"))
    from review_request import file_request
    out = file_request(
        asset={"warehouse": "repo", "ref": "runs/email-production/%s/%s/klaviyo/email.html" % (k["brand"], k["label"]),
               "title": "%s: %s is done, ready for your words and the Go" % (k["code"], k["by"])},
        type="text", reviewers=[WORDS_REVIEWER], lane="email-done", requested_by=k["by"].lower(),
        notes="\n".join([
            "What this is: %s finished the pictures and design of %s (%s)." % (k["by"], k["code"], k["label"]),
            "Why you: the final words and the Klaviyo draft are yours.",
            "What I need: your last pass on the words on the emails page, then Make the Klaviyo draft (Go).",
            "What ends your part: the Go, which makes the Klaviyo draft and schedules it."]),
        root=str(root), commit=False)
    return True, out.get("path")


def tell_pm(k, root=REPO):
    """A review request to the team naming each changed line, before -> after. Returns the record's path."""
    sys.path.insert(0, str(REPO / "components" / "review"))
    from review_request import file_request
    lines = "; ".join('%s: "%s" -> "%s"' % (e.get("path"), e.get("before", "?"), e.get("value")) for e in k["edits"])
    out = file_request(
        asset={"warehouse": "repo", "ref": "runs/email-production/%s/%s/design/email.json" % (k["brand"], k["label"]),
               "title": "%s: %s changed the words" % (k["code"], k["by"])},
        type="text", reviewers=[WORDS_REVIEWER], lane="email-words", requested_by=k["by"].lower(),
        notes="\n".join([
            "What this is: %s changed words in %s (%s). %s" % (k["by"], k["code"], k["label"], lines),
            "Why you: the words are yours; %s changes a line only when it's needed." % k["by"],
            "What I need: check the new words read right. Not the design or the pictures.",
            "What ends your part: you leave a verdict, or change the words again from the page."]),
        root=str(root), commit=False)
    return out.get("path")


def share(paths_, message):
    """One commit of exactly these paths, pull --rebase, push. Never force; a failure is said, not worked around."""
    git = lambda *a: subprocess.run(["git"] + list(a), cwd=str(REPO), capture_output=True, text=True)
    git("add", "--", *paths_)
    if not git("diff", "--cached", "--quiet").returncode:
        return "nothing to commit"
    c = git("commit", "-m", message)
    if c.returncode:
        return "not committed: " + (c.stderr or c.stdout).strip().splitlines()[-1]
    p = git("pull", "--rebase")
    if p.returncode:
        git("rebase", "--abort")
        return "committed here, not pushed: git pull --rebase stopped (%s). Tell the team." % (p.stderr or p.stdout).strip().splitlines()[-1]
    s = git("push")
    return "shared" if not s.returncode else "committed, not pushed: %s. Tell the team." % (s.stderr or s.stdout).strip().splitlines()[-1]


def run_paths(reqs):
    out = ["runs/learnings"]
    for k in reqs:
        out.append("runs/email-production/%s/%s" % (k["brand"], k["label"]))
    if any(k.get("action") == "add" for k in reqs):
        out.append("platform/data/records/model-outcome")      # LD-83: the add's record, and the tries' before it
    return sorted(set(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--dry-run", action="store_true")
    x = ap.parse_args(argv)
    got = parse(Path(x.file).read_text(encoding="utf-8"))
    if not got:
        print("no request lines found (each starts with \"Email request (\")")
        return 2
    done, todo, failed, extra = [], [], [], []
    for k, why in got:
        if why:
            failed.append(why)
            print("✗ " + why)
            continue
        say = "%s · %s%s" % (k["code"], k["action"], (": " + k["note"]) if k.get("note") else "")
        if k["action"] == "own":
            todo.append(k)
            print("… %s: needs her file and the alt text (own_picture.py place %s s%d.%d …)"
                  % (k["code"], k["label"], k["section"], k["picture"]))
            continue
        if x.dry_run:
            print("would run: " + say)
            continue
        card = REPO / "runs" / "email-production" / k["brand"] / k["label"] / "klaviyo" / "card.json"
        try:
            drafted = (json.loads(card.read_text()).get("klaviyo") or {}).get("campaign_id")
        except (OSError, ValueError):
            drafted = None
        if drafted and k["action"] not in ("ok", "scheduled", "go", "picture"):
            print("  ! %s is already a Klaviyo draft (%s): this change updates the email here, not the draft in "
                  "Klaviyo. Tell the team to make the same change in the Klaviyo draft." % (k["label"], drafted))
        if k["action"] == "done":
            try:
                ok, res = mark_done(k)
            except Exception as e:  # noqa: BLE001 — said, never hidden
                ok, res = False, str(e)[:200]
            print(("✓ " if ok else "✗ ") + say + ("  (the team has been told)" if ok else " — " + res))
            if ok:
                done.append(k)
                extra.append(res)
            else:
                failed.append(say)
            continue
        if k["action"] == "picture":                    # LD-83: a try, seen at once; nothing to commit
            ok, res = try_one(k)
            print(("✓ " if ok else "✗ ") + say + " — " + res)
            if not ok:
                failed.append(say)
            continue
        if k["action"] == "newest":                     # LD-90 (the team takes newest): moved, placed, records committed
            ok, res, recs = newest_one(k)
            print(("✓ " if ok else "✗ ") + say + " — " + res)
            extra += recs
            if ok:
                done.append(k)
            else:
                failed.append(say)
            continue
        if k["action"] == "add":
            ok, res = add_one(k)
        elif k["action"] in KEEP_MARKS:
            sys.path.insert(0, str(HERE))
            import prepare
            ok, res = prepare.keep_card(REPO / "runs" / "email-production" / k["brand"] / k["label"], lambda: apply_one(k))
            if ok:
                prepare.stamp(REPO / "runs" / "email-production" / k["brand"] / k["label"])
        else:
            ok, res = apply_one(k)
        print(("✓ " if ok else "✗ ") + say + ("" if ok and res in ("", "done") else " — " + res))
        if not ok:
            failed.append(say)
            continue
        done.append(k)
        if k["action"] == "words" and k["by"] != "the team":
            try:
                extra.append(tell_pm(k))
                print("  the team has been sent a review request for these words")
            except Exception as e:  # noqa: BLE001 — the change stays; telling the team is said to have failed
                failed.append("%s: the words changed but the team's review request failed (%s)" % (k["code"], str(e)[:120]))
                print("  ✗ couldn't send the team the review request: %s" % str(e)[:120])
    if done:
        words = [k["code"] for k in done if k["action"] == "words" and k["by"] != "the team"]
        head = ("%s changed words: %s; " % (done[0]["by"], ", ".join(words))) if words else ""
        msg = "%s%s requests: %s" % (head, done[0]["by"], "; ".join("%s %s" % (k["code"], k["action"]) for k in done))
        print("git: " + share(run_paths(done) + [p for p in extra if p], msg[:300]))
    return 0 if not failed and not todo else 1


if __name__ == "__main__":
    sys.exit(main())
