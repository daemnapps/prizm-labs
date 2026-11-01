#!/usr/bin/python3
"""mini-debug — anyone's Claude opens a thread to the team's lead from one command,
waits on it, and reads the answer; the lead answers in the same folder
(LD-29 (mini-debug threads)).

    python3 components/run-kit/mini_debug.py open --slug S --ask "…" [--run LABEL]
                [--seen "…"] [--tried "…"] [--machine M] [--to dayu] [--no-push]
    python3 components/run-kit/mini_debug.py reply <thread> --body "…"
    python3 components/run-kit/mini_debug.py close <thread> (--fixed SHA | --needs-dayu "question" | --ruled POINTER)
    python3 components/run-kit/mini_debug.py watch <thread> [--interval 30]
    python3 components/run-kit/mini_debug.py list [--to dayu] [--open]
    python3 components/run-kit/mini_debug.py brief

Why it exists: a teammate's Claude cannot reach the team's sessions (another
account on another Mac), and every mini-run problem travelled through the team as a
relay. A thread in git is what both Claudes can read and write.

A thread is a folder, team/threads/<to>/<YYYYMMDDTHHMMZ>-<from>-<slug>/, of
message files NNN-<writer>.md; NNN-close.md ends it. `from` is the person
`git config user.email` resolves to (mini_run.whoami).

open    prints team/threads/<to>/KNOWN-ISSUES.md and its `## Open` titles first
        (check the known list), then writes 001-<from>.md: the ask, the run
        label, what was seen, what was tried, the machine (`mini` when the
        hostname says so, else `<person>'s Mac`). `--run LABEL` prefills
        status, exit_code and the last 8 lines of stderr_tail from
        platform/data/records/lab-runs/<from>/<label>.json (on disk, else
        origin/main). Publishes that one path to main from a throwaway
        worktree of origin/main (mini_run.publish_one, LD-95 (posts
        off-clone)) — your clone is not touched and gets it on its next pull.
        `--no-push` writes + commits it by pathspec in your clone instead.
reply   the next NNN-<from>.md (numbered from disk and origin/main, after a
        fetch); published as `open` is.
close   NNN-close.md, one line — `fixed: SHA`, `needs-dayu: …` or `ruled: …`
        and who closed it; published as `open` is.
watch   every --interval seconds: git fetch, then one line per new message in
        the thread on origin/main written by someone else (its path and first
        3 non-empty lines), flushed, so Claude Code's Monitor sees each one;
        exits 0 when a -close.md lands. "New" is everything after the caller's
        own last message. A fetch failure is said once and the loop goes on.
list    every thread (disk and origin/main): open / closed, last writer, age.
brief   ONE line when the caller's open threads (opened by them, addressed to
        them, or written in by them) end in someone else's message; else
        nothing. Never fetches, never errors, always exits 0 — it runs in a
        session-start hook.

Refuses (exit 2) any message holding a secret-shaped string — an `sk-`,
`ghp_`, `xox?-` or `AIza` token, `-----BEGIN`, or the value (12+ characters)
of an environment variable whose name ends _KEY, _TOKEN or _SECRET: git keeps
everything. Writes nothing outside team/threads/. A thread is a teammate's
REQUEST, never the team's typed word. Stdlib only, Python 3.9.6.
"""
import argparse
import json
import os
import re
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mini_run as M  # noqa: E402  find_repo, git_run, whoami, publish_one, utc_now, Refused, by_hand

Refused = M.Refused

THREADS = "team/threads"
KNOWN = "KNOWN-ISSUES.md"
LAB_RUNS = "platform/data/records/lab-runs"
DEFAULT_TO = "dayu"
SUBJECT = "mini-debug:"
STDERR_LINES = 8
PREVIEW_LINES = 3
MESSAGE = re.compile(r"^(\d{3})-([A-Za-z0-9][A-Za-z0-9._-]*)\.md$")
CLOSE = "close"
CLOSED_BY = re.compile(r"closed by ([A-Za-z0-9][A-Za-z0-9._-]*),")
SHA = re.compile(r"^[0-9a-f]{7,40}$")
SECRET_SHAPES = (
    ("sk-", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{8,}")),
    ("ghp_", re.compile(r"(?<![A-Za-z0-9])ghp_[A-Za-z0-9]{8,}")),
    ("xox", re.compile(r"(?<![A-Za-z0-9])xox[a-z]?-[A-Za-z0-9-]{6,}")),
    ("AIza", re.compile(r"(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{10,}")),
    ("-----BEGIN", re.compile(r"-----BEGIN")),
)
SECRET_ENV_ENDS = ("_KEY", "_TOKEN", "_SECRET")
SECRET_ENV_MIN = 12


def say_flushed(line):
    print(line, flush=True)


# ── where things are ─────────────────────────────────────────────────────────

def plain(value, what):
    if not M.SEGMENT.match(value or "") or ".." in value:
        raise Refused("{0} {1!r} is not a plain name".format(what, value))
    return value


def inside_threads(repo, rel):
    """The one write gate: `rel` must resolve under team/threads/."""
    root = (repo / THREADS).resolve()
    path = (repo / rel).resolve()
    if root not in path.parents:
        raise Refused("{0} is outside {1}/ — mini-debug writes nowhere else".format(rel, THREADS))
    return path


def message_files(repo, git, ref=M.ORIGIN_MAIN, disk=True):
    """{rel path: None} for every message file under team/threads/<to>/<thread>/,
    on disk (when `disk`) and at `ref` (when given; a ref that does not exist is empty)."""
    found = {}
    if disk:
        for f in (repo / THREADS).glob("*/*/*.md"):
            if MESSAGE.match(f.name):
                found[f.relative_to(repo).as_posix()] = None
    if ref:
        code, out, _ = git(["ls-tree", "-r", "--name-only", ref, "--", THREADS + "/"], repo)
        if code == 0:
            for line in out.splitlines():
                parts = line.strip().split("/")
                if len(parts) == 5 and MESSAGE.match(parts[4]):
                    found[line.strip()] = None
    return found


def threads_of(files):
    """{thread rel: [message names, oldest first]}."""
    out = {}
    for rel in files:
        thread, _, name = rel.rpartition("/")
        out.setdefault(thread, []).append(name)
    return {t: sorted(names, key=order) for t, names in out.items()}


def order(name):
    m = MESSAGE.match(name)
    return (int(m.group(1)), m.group(2)) if m else (0, name)


def read_text(repo, git, rel, ref=M.ORIGIN_MAIN):
    path = repo / rel
    if path.is_file():
        try:
            return path.read_text()
        except OSError:
            pass
    code, out, _ = git(["show", "{0}:{1}".format(ref, rel)], repo)
    return out if code == 0 else ""


def read_ref(repo, git, rel, ref=M.ORIGIN_MAIN):
    code, out, _ = git(["show", "{0}:{1}".format(ref, rel)], repo)
    return out if code == 0 else ""


def is_close(name):
    return MESSAGE.match(name).group(2) == CLOSE


def writer_of(name, text_of):
    """The person who wrote a message: from its name, or, for a close, its 'closed by' line."""
    who = MESSAGE.match(name).group(2)
    if who != CLOSE:
        return who
    m = CLOSED_BY.search(text_of() or "")
    return m.group(1) if m else "?"


def resolve_thread(repo, git, arg):
    """team/threads/<to>/<name> from a full path, `<to>/<name>`, or `<name>` alone."""
    raw = (arg or "").strip().rstrip("/")
    p = Path(raw)
    if p.is_absolute():
        try:
            raw = p.resolve().relative_to(repo).as_posix()
        except ValueError:
            raise Refused("{0} is not inside this checkout".format(arg))
    if raw.startswith(THREADS + "/"):
        raw = raw[len(THREADS) + 1:]
    parts = [x for x in raw.split("/") if x]
    known = threads_of(message_files(repo, git))
    if len(parts) == 1:
        hits = sorted(t for t in known if t.rsplit("/", 1)[1] == parts[0])
        if len(hits) != 1:
            raise Refused("thread {0!r}: {1}".format(
                arg, "no such thread" if not hits else "more than one ({0}) — give <to>/<name>"
                .format(", ".join(hits))))
        return hits[0]
    if len(parts) != 2:
        raise Refused("thread {0!r} is not team/threads/<to>/<name>".format(arg))
    rel = "{0}/{1}/{2}".format(THREADS, plain(parts[0], "thread"), plain(parts[1], "thread"))
    if rel not in known:
        raise Refused("no thread {0} on disk or on {1} (pull, or check the name with `list`)"
                      .format(rel, M.ORIGIN_MAIN))
    return rel


# ── secrets ──────────────────────────────────────────────────────────────────

def refuse_secrets(text, env):
    """Refused when the text holds a secret-shaped string; the value is never echoed."""
    for label, rx in SECRET_SHAPES:
        if rx.search(text):
            raise Refused("the message holds a secret-shaped string ({0}…) and git keeps "
                          "everything — take it out and say where the key lives instead".format(label))
    for name, value in sorted(env.items()):
        if name.upper().endswith(SECRET_ENV_ENDS) and len(value or "") >= SECRET_ENV_MIN and value in text:
            raise Refused("the message holds the value of ${0} and git keeps everything — "
                          "take it out".format(name))


# ── writing one message ──────────────────────────────────────────────────────

def on_main_or_refuse(repo, git):
    code, out, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    if code != 0 or out.strip() != "main":
        raise Refused("this checkout is on {0!r}, not main — threads travel on main; "
                      "switch to main".format(out.strip() or "?"))


def commit_one(repo, git, rel, text, msg, push, say):
    """ONE message file under team/threads/. With `push`: published to main from a throwaway
    worktree of origin/main (M.publish_one, LD-95 (posts off-clone)), never written or committed
    in this clone. Without (`open --no-push`): written, added + committed by pathspec here."""
    path = inside_threads(repo, rel)
    if push:
        return M.publish_one(repo, git, rel, text, msg, say)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    say("wrote {0}".format(rel))
    for step in (["add", "--", rel], ["commit", "-m", msg, "--", rel]):
        code, _, err = git(step, repo)
        if code != 0:
            say("git {0} failed: {1}".format(step[0], err.strip()))
            M.by_hand(["git add -- " + rel, "git commit -m '{0}' -- {1}".format(msg, rel),
                       "git push origin main"], say)
            return 1
    say("committed {0}".format(rel))
    say("--no-push: not pushed — `git push origin main` sends it")
    return 0


def iso(now):
    return now.strftime("%Y-%m-%dT%H:%MZ")


def fetch(repo, git, say):
    code, _, err = git(["fetch", "origin", "main"], repo)
    if code != 0:
        say("git fetch failed ({0}) — reading {1} as last fetched".format(err.strip(), M.ORIGIN_MAIN))
    return code == 0


# ── open ─────────────────────────────────────────────────────────────────────

def known_open(repo, to, say):
    """Print the known-issues file and the titles of its `## Open` entries."""
    rel = "{0}/{1}/{2}".format(THREADS, to, KNOWN)
    try:
        lines = (repo / rel).read_text().splitlines()
    except OSError:
        return
    titles, inside = [], False
    for line in lines:
        if line.startswith("## "):
            inside = line[3:].strip().lower().startswith("open")
            continue
        m = re.match(r"^(\d+\.|[-*])\s+(.*)$", line) if inside else None
        if m:
            bold = re.search(r"\*\*(.+?)\*\*", m.group(2))
            titles.append(bold.group(1) if bold else m.group(2).strip())
    say("check the known list first: {0}{1}".format(rel, " — open:" if titles else " (no open entries)"))
    for i, t in enumerate(titles, 1):
        say("  {0}. {1}".format(i, t))
    say("(opening the thread anyway — say in --tried if one of these is it)")


def default_machine(person, host):
    return "mini" if "mini" in (host or "").lower() else "{0}'s Mac".format(person)


def lab_run(repo, git, person, label):
    """(rel, record dict or None) — the lab-run record on disk, else on origin/main."""
    rel = "{0}/{1}/{2}.json".format(LAB_RUNS, person, plain(label, "--run"))
    text = read_text(repo, git, rel)
    try:
        doc = json.loads(text) if text else None
    except ValueError:
        doc = None
    return rel, doc if isinstance(doc, dict) else None


def opening(person, to, ns, machine, now, run_rel, run_doc):
    lines = ["# {0} — {1} to {2}, {3}".format(ns.slug, person, to, iso(now)),
             "ask: {0}".format(ns.ask.strip())]
    if ns.run and run_doc is not None:
        lines.append("run: {0} — status {1}, exit_code {2}".format(
            ns.run, run_doc.get("status", "?"), run_doc.get("exit_code", "?")))
    elif ns.run:
        lines.append("run: {0} — no lab-run record at {1} (not pulled yet, or another label?)"
                     .format(ns.run, run_rel))
    else:
        lines.append("run: (none given)")
    lines += ["seen: {0}".format((ns.seen or "").strip() or "(not given)"),
              "tried: {0}".format((ns.tried or "").strip() or "(not given)"),
              "machine: {0}".format(machine)]
    if run_doc is not None:
        tail = str(run_doc.get("stderr_tail") or "").splitlines()[-STDERR_LINES:]
        lines += ["", "stderr_tail (last {0} lines, {1}):".format(STDERR_LINES, run_rel)]
        lines += ["    " + t for t in tail] or ["    (empty)"]
    return "\n".join(lines) + "\n"


def open_thread(repo, git, ns, now, say, env, host):
    person = M.whoami(repo, git)
    to = plain(ns.to, "--to")
    if not (repo / M.PEOPLE / to / "identity.json").is_file():
        raise Refused("--to {0!r} is nobody in {1}/".format(to, M.PEOPLE))
    slug = plain(ns.slug, "--slug")    # a run label is a valid slug: mini_run status suggests --slug <label>
    if not ns.ask.strip():
        raise Refused("--ask is empty — say what you need")
    known_open(repo, to, say)
    run_rel, run_doc = lab_run(repo, git, person, ns.run) if ns.run else (None, None)
    machine = (ns.machine or "").strip() or default_machine(person, host)
    text = opening(person, to, ns, machine, now, run_rel, run_doc)
    refuse_secrets(text, env)
    thread = "{0}/{1}/{2}-{3}-{4}".format(THREADS, to, now.strftime("%Y%m%dT%H%MZ"), person, slug)
    on_main = any(f.startswith(thread + "/") for f in message_files(repo, git, disk=False))
    if (repo / thread).exists() or on_main:    # a published thread is on origin/main before it is on disk
        raise Refused("{0} already exists — pick another --slug".format(thread))
    if not ns.no_push:
        on_main_or_refuse(repo, git)
    rel = "{0}/001-{1}.md".format(thread, person)
    msg = "{0} {1} opens {2}".format(SUBJECT, person, thread[len(THREADS) + 1:])
    code = commit_one(repo, git, rel, text, msg, not ns.no_push, say)
    if code == 0:
        say("thread: {0}".format(thread))
        say("wait on it: python3 components/run-kit/mini_debug.py watch {0}".format(thread))
    return code


# ── reply and close ──────────────────────────────────────────────────────────

def next_number(repo, git, thread):
    names = threads_of(message_files(repo, git)).get(thread, [])
    if any(is_close(n) for n in names):
        raise Refused("{0} is closed — open a new thread".format(thread))
    return max([order(n)[0] for n in names] or [0]) + 1


def add_message(repo, git, ns, say, env, kind, text_for):
    person = M.whoami(repo, git)
    fetch(repo, git, say)
    thread = resolve_thread(repo, git, ns.thread)
    n = next_number(repo, git, thread)
    text = text_for(person)
    refuse_secrets(text, env)
    on_main_or_refuse(repo, git)
    who = CLOSE if kind == "closes" else person
    rel = "{0}/{1:03d}-{2}.md".format(thread, n, who)
    msg = "{0} {1} {2} {3} ({4:03d})".format(SUBJECT, person, kind, thread[len(THREADS) + 1:], n)
    return commit_one(repo, git, rel, text, msg, True, say)


def reply(repo, git, ns, now, say, env):
    if not ns.body.strip():
        raise Refused("--body is empty")
    return add_message(repo, git, ns, say, env, "replies in",
                       lambda person: "# reply — {0}, {1}\n{2}\n".format(person, iso(now), ns.body.strip()))


def close(repo, git, ns, now, say, env):
    if ns.fixed is not None:
        if not SHA.match(ns.fixed.strip()):
            raise Refused("--fixed {0!r} is not a commit sha".format(ns.fixed))
        what = "fixed: " + ns.fixed.strip()
    elif ns.needs_dayu is not None:
        what = "needs-dayu: " + " ".join(ns.needs_dayu.split())
    else:
        what = "ruled: " + " ".join(ns.ruled.split())
    if what.endswith(": "):
        raise Refused("the close line is empty")
    return add_message(repo, git, ns, say, env, "closes",
                       lambda person: "{0} — closed by {1}, {2}\n".format(what, person, iso(now)))


# ── watch ────────────────────────────────────────────────────────────────────

def preview(text):
    return " | ".join([l.strip() for l in text.splitlines() if l.strip()][:PREVIEW_LINES])


def watch(repo, git, ns, say, sleep):
    person = M.whoami(repo, git)
    fetched = fetch(repo, git, say)
    thread = resolve_thread(repo, git, ns.thread)
    say("watching {0} on {1} every {2}s — one line per message from the other side; "
        "ends when the thread closes".format(thread, M.ORIGIN_MAIN, ns.interval))
    seen, failing, first = set(), not fetched, True
    while True:
        if not first:
            ok = git(["fetch", "origin", "main"], repo)
            if ok[0] != 0 and not failing:
                say("git fetch failed ({0}) — still watching, reading {1} as last fetched"
                    .format(ok[2].strip(), M.ORIGIN_MAIN))
            failing = ok[0] != 0
        names = threads_of(message_files(repo, git, disk=False)).get(thread, [])
        if first:
            if not names:
                say("{0} is not on {1} yet — push it (`git push origin main`)".format(thread, M.ORIGIN_MAIN))
            mine = [i for i, n in enumerate(names) if writer_of(n, lambda n=n: read_ref(
                repo, git, thread + "/" + n)) == person]
            seen.update(names[:mine[-1] + 1] if mine else [])
            first = False
        closed = False
        for n in names:
            if n in seen:
                continue
            seen.add(n)
            rel = thread + "/" + n
            text = read_ref(repo, git, rel)
            if is_close(n):
                closed = True
            if writer_of(n, lambda: text) != person:
                say("{0}: {1}".format(rel, preview(text)))
        if closed:
            say("{0} is closed — watch ends".format(thread))
            return 0
        sleep(ns.interval)


# ── list and brief ───────────────────────────────────────────────────────────

def age(name, now):
    try:
        opened = datetime.strptime(name.split("-", 1)[0], "%Y%m%dT%H%MZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return "?"
    mins = max(0, int((now - opened).total_seconds() // 60))
    if mins < 60:
        return "{0}m".format(mins)
    if mins < 48 * 60:
        return "{0}h{1:02d}m".format(mins // 60, mins % 60)
    return "{0}d".format(mins // (24 * 60))


def list_threads(repo, git, ns, now, say):
    fetch(repo, git, say)
    if ns.to:
        plain(ns.to, "--to")
    shown = 0
    for thread, names in sorted(threads_of(message_files(repo, git)).items()):
        to, name = thread.split("/")[2:4]
        if ns.to and to != ns.to:
            continue
        closed = any(is_close(n) for n in names)
        if ns.open and closed:
            continue
        last = writer_of(names[-1], lambda: read_text(repo, git, thread + "/" + names[-1]))
        say("{0:<7} {1}/{2}  last {3} · {4} message(s) · age {5}".format(
            "closed" if closed else "open", to, name, last, len(names), age(name, now)))
        shown += 1
    if not shown:
        say("no {0}threads{1}".format("open " if ns.open else "", " to " + ns.to if ns.to else ""))
    return 0


def brief_line(repo, git):
    person = M.whoami(repo, git)
    total, where = 0, []
    for thread, names in sorted(threads_of(message_files(repo, git)).items()):
        if any(is_close(n) for n in names):
            continue
        writers = [MESSAGE.match(n).group(2) for n in names]
        to = thread.split("/")[2]
        if not names or (to != person and person not in writers) or writers[-1] == person:
            continue
        after = [i for i, w in enumerate(writers) if w == person]
        total += len(names) - (after[-1] + 1 if after else 0)
        where.append(thread[len(THREADS) + 1:])
    if not total:
        return None
    return "mini-debug: {0} new {1} in your open threads ({2})".format(
        total, "reply" if total == 1 else "replies", ", ".join(where))


def brief(repo, git, say):
    """Never raises, always 0: it runs in a session-start hook."""
    try:
        line = brief_line(Path(repo).resolve() if repo else M.find_repo(), git)
    except Exception:  # noqa: BLE001 — a hook must never fail a session
        return 0
    if line:
        say(line)
    return 0


# ── the command ──────────────────────────────────────────────────────────────

def parser():
    p = argparse.ArgumentParser(prog="mini_debug.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open", help="open a thread to the lead")
    o.add_argument("--slug", required=True)
    o.add_argument("--ask", required=True)
    o.add_argument("--run", help="a lab-run label: prefill from its result record")
    o.add_argument("--seen", help="what was seen — the error line")
    o.add_argument("--tried", help="what was tried")
    o.add_argument("--machine", help="default: mini when the hostname says so, else <you>'s Mac")
    o.add_argument("--to", default=DEFAULT_TO)
    o.add_argument("--no-push", action="store_true", help="commit, do not push")
    r = sub.add_parser("reply", help="answer in a thread")
    r.add_argument("thread")
    r.add_argument("--body", required=True)
    c = sub.add_parser("close", help="close a thread with one line")
    c.add_argument("thread")
    how = c.add_mutually_exclusive_group(required=True)
    how.add_argument("--fixed", metavar="SHA")
    how.add_argument("--needs-dayu", metavar="QUESTION")
    how.add_argument("--ruled", metavar="POINTER")
    w = sub.add_parser("watch", help="wait on a thread; one line per message from the other side")
    w.add_argument("thread")
    w.add_argument("--interval", type=int, default=30)
    li = sub.add_parser("list", help="every thread: open/closed, last writer, age")
    li.add_argument("--to")
    li.add_argument("--open", action="store_true")
    sub.add_parser("brief", help="one line when your open threads have new replies (session start)")
    return p


def main(argv=None, repo=None, git=M.git_run, now=None, say=say_flushed, env=None,
         host=None, sleep=time.sleep):
    ns = parser().parse_args(argv)
    if ns.cmd == "brief":
        return brief(repo, git, say)
    try:
        repo = Path(repo).resolve() if repo else M.find_repo()
        now = now or M.utc_now()
        env = os.environ if env is None else env
        if ns.cmd == "open":
            return open_thread(repo, git, ns, now, say, env, socket.gethostname() if host is None else host)
        if ns.cmd == "reply":
            return reply(repo, git, ns, now, say, env)
        if ns.cmd == "close":
            return close(repo, git, ns, now, say, env)
        if ns.cmd == "watch":
            if ns.interval < 1:
                raise Refused("--interval must be at least 1 second")
            return watch(repo, git, ns, say, sleep)
        return list_threads(repo, git, ns, now, say)
    except Refused as e:
        say("mini_debug: refused — {0}".format(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
