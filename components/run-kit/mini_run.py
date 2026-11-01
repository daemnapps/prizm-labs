#!/usr/bin/python3
"""The mini run filer — one command lists what the mini can run, files a lab
run as the person at the keyboard, and reads its result back (LD-9 (mini run
filer)).

    python3 components/run-kit/mini_run.py list
    python3 components/run-kit/mini_run.py file <component> --brand B [--label L]
                                                [--dry-run] [--no-push | --print] [name=value ...]
    python3 components/run-kit/mini_run.py status [label]
    python3 components/run-kit/mini_run.py watch <label> [--interval 30] [--timeout 5400]

Why it exists: every mini lab run so far was a hand-written JSON record under
platform/data/records/workflow-requests/, and nothing told a person which
arguments a door takes. The grant rows (team/dispatch-grants.json
`components`) already say who may file; this writes the filing.

list    every `components[]` row: component, owner, filers, script, and the
        args its door takes — from the lab_door.json beside the script (a
        routed door lists each route under `--command <route>`), else the
        script's module-level ACCEPTS tuple (read with `ast`, never imported),
        else "see <script>" and its docstring's first line.
file    the requester is `git config user.email` matched (case-insensitively)
        against team/people/*/identity.json; the component must be a row and
        the requester one of its filers (or `*`). A lab_door.json door checks
        the args with run_kit/lab_door.py pick() + command(); an ACCEPTS door
        refuses a name not in ACCEPTS. `--dry-run` adds dry_run=yes and is
        refused for a door that declares no dry_run. Writes ONE request
        record, <UTC stamp>--<person>--<label>.json, carrying only the verdict
        fields platform/workers/mini-worker/lab_run.py ALLOWED_FIELDS accepts,
        committed and pushed to main from a throwaway worktree of origin/main
        (publish_one, LD-95 (posts off-clone)) — never in your clone, which
        gets it on its next pull; a refused push rebases inside that worktree,
        never pulls in yours. `--no-push` writes + commits by pathspec in your
        clone and stops; `--print` writes nothing. A label already on disk or
        on origin/main is refused. A door that needs a label and was given none gets
        label=<label>, so the run lands in $OUT/<label>/. Before writing (not
        under --print), LD-45 (mini-run refuses on RED): mini_compare traces
        the door's dry run and checks every file; a NEW RED (a file you
        changed) or a path the dry run opened outside is refused, every RED
        already in the code is shown (reached lines first) and filing goes on.
status  after `git fetch`, the newest <stamp>--mini-worker--<label>.json on
        origin/main: its status and the detail's last 15 lines; none yet →
        queued. No label: this person's last 10 lab-run requests and each one's
        status.
watch   LD-57 (mini-run watch): one start line, then every --interval seconds
        `git fetch` and the label's newest mini-worker record, as `status`
        reads it — nothing said while queued or running (a fetch failure is
        said once and the watch goes on). Ends with done → `PASSED <label> —
        outputs at <path>`, exit 0; any other status → `FAILED <label>
        (<status>) — <the detail's last non-empty line>` + "say 'status' for
        the full reason", exit 1; nothing terminal within --timeout → the
        timeout line, exit 3.

Never: an action but lab-run; never `scheduled`; never writes a grant, a
brand folder or .claude/ — its one write is the request record.

Refusals exit 2 and say why; a git step that fails exits 1 and prints the
commands to finish by hand. Stdlib only, Python 3.9.6.
"""
import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
from run_kit import lab_door  # noqa: E402  load, pick, command, needs_label, Refused
from run_kit import people  # noqa: E402  person_of, whoami, Refused (LD-77 (one person resolver))

GRANTS = "team/dispatch-grants.json"
PEOPLE = "team/people"
REQUESTS = "platform/data/records/workflow-requests"
WORKER = "mini-worker"
ORIGIN_MAIN = "origin/main"
JOB = "lab-run"
VIA = "mini_run"
ANY_FILER = "*"
DRY_RUN = "dry_run"
TAIL = 15
RECENT = 10
SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")    # lab_run.py OUT_RE
ARG_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")    # lab_run.py ARG_RE
NO_PREFLIGHT = "MINI_RUN_NO_PREFLIGHT"    # =1 with no check passed: file without the RED check (tests)
SHOW_REST = 5
AT_LINE = re.compile(r"[\w./-]+\.py:\d+")    # a RED's file:line, as a trace's "reached" holds it
OUTPUTS_AT = re.compile(r"outputs stay at (\S+)")    # lab_run.py's detail, first line
WATCH_INTERVAL = 30
WATCH_TIMEOUT_S = 90 * 60
NOISE = (    # LD-57b (watch skips noise): stderr lines watch never quotes as the error, matched stripped
    re.compile(r"Warning:"),
    re.compile(r"Warning\)$"),
    re.compile(r"^warnings\.warn\("),
    re.compile(r"^research-gatherer: \$"),
)
WATCH_PASSED, WATCH_FAILED, WATCH_TIMEOUT = 0, 1, 3    # 2 stays main's refusal
PUBLISH_ATTEMPTS = 4    # LD-95 (posts off-clone): pushes in all from the throwaway worktree
PUBLISH_PAUSE_S = 2


Refused = people.Refused    # one class: the resolver's refusals are this module's (printed, exit 2)


def git_run(args, repo):
    """The one place git runs: (exit code, stdout, stderr). Tests pass their own."""
    p = subprocess.run(["git"] + list(args), cwd=str(repo), capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def find_repo(start=None):
    """The checkout: the first folder upward holding team/dispatch-grants.json."""
    here = Path(start or __file__).resolve()
    for d in [here, *here.parents]:
        if (d / GRANTS).is_file():
            return d
    raise Refused("no checkout found upward of {0} (looked for {1})".format(here, GRANTS))


def utc_now():
    return datetime.now(timezone.utc)


# ── the grant rows and the people ────────────────────────────────────────────

def rows(repo):
    try:
        doc = json.loads((repo / GRANTS).read_text())
    except (OSError, ValueError) as e:
        raise Refused("{0} does not read: {1}".format(GRANTS, e))
    found = doc.get("components") if isinstance(doc, dict) else None
    if not isinstance(found, list):
        raise Refused("{0} has no components list".format(GRANTS))
    return [r for r in found if isinstance(r, dict) and r.get("component")]


def row_of(repo, component):
    all_rows = rows(repo)
    for r in all_rows:
        if r["component"] == component:
            return r
    raise Refused("{0!r} is not a component row in {1} (rows: {2})".format(
        component, GRANTS, ", ".join(sorted(r["component"] for r in all_rows))))


# The one answer to "who is this" (LD-77 (one person resolver)): the person whose
# team/people/<id>/identity.json lists the git email, never its local part.
person_of = people.person_of
whoami = people.whoami


# ── the doors ────────────────────────────────────────────────────────────────

def manifest_of(repo, row):
    """The door file beside the stub: lab_entry.py -> lab_door.json, lab_entry_v2.py -> lab_door_v2.json
    (a second door beside a component's first, 2026-10-19)."""
    script = repo / row["script"]
    return script.with_name(script.stem.replace("lab_entry", "lab_door", 1) + ".json")


def module_of(path):
    try:
        return ast.parse(path.read_text())
    except (OSError, SyntaxError, ValueError):
        return None


def accepts_of(path):
    """The module-level ACCEPTS tuple, read without importing; None if absent."""
    tree = module_of(path)
    if tree is None:
        return None
    for node in tree.body:
        targets, value = [], None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        if any(isinstance(t, ast.Name) and t.id == "ACCEPTS" for t in targets):
            try:
                got = ast.literal_eval(value)
            except ValueError:
                return None
            if isinstance(got, (tuple, list)) and all(isinstance(x, str) for x in got):
                return tuple(got)
            return None
    return None


def first_doc_line(path):
    tree = module_of(path)
    doc = ast.get_docstring(tree) if tree is not None else None
    for line in (doc or "").splitlines():
        if line.strip():
            return line.strip()
    return "(no docstring)"


def door_of(repo, row):
    """("lab_door", manifest) | ("accepts", names) | ("plain", first doc line).
    A manifest that does not load is Refused."""
    manifest = manifest_of(repo, row)
    if manifest.is_file():
        return "lab_door", lab_door.load(manifest)
    script = repo / row["script"]
    names = accepts_of(script) if script.is_file() else None
    if names is not None:
        return "accepts", names
    if not script.is_file():
        return "plain", "(script not in this checkout)"
    return "plain", first_doc_line(script)


def route_args(m):
    """One route's arguments, as the door's --name pairs."""
    out = ["--{0} <path>".format(n) for n in m["positionals"]]
    out += ["[--{0} <value>]".format(n) for n in m["flags"]]
    out += ["[--{0} yes|no]".format(n) for n in m["bool_flags"]]
    if lab_door.needs_label(m) and "label" not in m["flags"]:
        out.append("--label <name>")
    return " ".join(out) or "(none)"


def list_rows(repo, say):
    say("What the mini can run (args are the door's --name value pairs; "
        "file them as name=value, e.g. --command start → command=start):")
    for row in rows(repo):
        filers = ", ".join(row.get("filers") or []) or "(none)"
        say("")
        say("{0} — owner {1} · filers {2}".format(row["component"], row.get("owner", "?"), filers))
        say("  script  {0}".format(row.get("script", "?")))
        try:
            kind, door = door_of(repo, row)
        except lab_door.Refused as e:
            say("  args    door does not load: {0}".format(e))
            continue
        if kind == "lab_door" and "routes" in door:
            say("  door    {0} (routed, default --command {1})".format(
                manifest_of(repo, row).relative_to(repo), door["default_route"]))
            for name, route in door["routes"].items():
                say("  --command {0}  {1}".format(name, route_args(route)))
        elif kind == "lab_door":
            say("  door    {0}".format(manifest_of(repo, row).relative_to(repo)))
            say("  args    {0}".format(route_args(door)))
        elif kind == "accepts":
            say("  args    {0}  (ACCEPTS in the script)".format(
                " ".join("--{0} <value>".format(n) for n in door) or "(none)"))
        else:
            say("  args    see {0} — {1}".format(row.get("script", "?"), door))
    return 0


def checked_args(repo, row, kind, door, args, brand):
    """The args the request carries, checked against the door. Refused when they
    do not fit. A door that needs a label and got none is handed the run's."""
    if kind == "lab_door":
        try:
            route, rest = lab_door.pick(door, args)
            if DRY_RUN in args and DRY_RUN not in route["flags"] and DRY_RUN not in route["bool_flags"]:
                raise Refused("--dry-run: {0}'s door{1} declares no dry_run, so every run "
                              "of it spends — refused".format(
                                  row["component"],
                                  "" if "routes" not in door else
                                  " route " + args.get(lab_door.SELECTOR, door["default_route"])))
            lab_door.command(route, rest, repo, brand, Path("<dest>"), Path("<runs-root>"))
        except lab_door.Refused as e:
            raise Refused(str(e))
        return lab_door.needs_label(route)
    if kind == "accepts":
        if DRY_RUN in args and DRY_RUN not in door:
            raise Refused("--dry-run: {0}'s door declares no dry_run (ACCEPTS {1}) — refused"
                          .format(row["component"], ", ".join(door) or "none"))
        unknown = sorted(set(args) - set(door))
        if unknown:
            raise Refused("unknown argument(s) {0} — {1}'s door accepts {2}".format(
                ", ".join(unknown), row["component"], ", ".join(door) or "none"))
        return "label" in door
    # A hand-written door (no lab_door.json, no ACCEPTS): read the script's own argparse flags,
    # so a door that REQUIRES --label is handed the run's (2026-10-19: the kojic-acid-doctor run
    # was refused on the mini for exactly this) and a declared --dry_run is honoured.
    flags = script_flags(repo / row["script"])
    if DRY_RUN in args and DRY_RUN not in flags:
        raise Refused("--dry-run: {0} declares no dry_run (no door manifest or ACCEPTS; see {1}) — refused"
                      .format(row["component"], row["script"]))
    unknown = sorted(set(args) - set(flags)) if flags else []
    if unknown:
        raise Refused("unknown argument(s) {0} — {1}'s door takes {2}".format(
            ", ".join(unknown), row["component"], ", ".join(sorted(flags))))
    return flags.get("label") is True


FLAG = re.compile(r"""add_argument\(\s*["']--([A-Za-z_][A-Za-z0-9_-]*)["']([^)]*)\)""")


def script_flags(path):
    """{flag name: required?} from a door script's argparse calls; {} when it cannot be read."""
    try:
        text = Path(path).read_text()
    except OSError:
        return {}
    return {m.group(1).replace("-", "_"): "required=True" in m.group(2).replace(" ", "")
            for m in FLAG.finditer(text)}


def parse_pairs(pairs):
    args = {}
    for p in pairs:
        name, eq, value = p.partition("=")
        name = name.strip().lstrip("-").replace("-", "_")
        if not eq or not ARG_NAME.match(name):
            raise Refused("{0!r} is not name=value".format(p))
        if name in args:
            raise Refused("{0} given twice".format(name))
        args[name] = value
    return args


# ── file ─────────────────────────────────────────────────────────────────────

def stamp(now):
    return now.strftime("%Y%m%dT%H%M%SZ")


def already_filed(repo, person, label, git=None):
    """Repo-relative paths of this person's requests under `label`: on disk, and, given `git`,
    at origin/main too — a record published off-clone is not on disk until the next pull."""
    tail = "--{0}--{1}.json".format(person, label)
    found = {p.relative_to(repo).as_posix() for p in (repo / REQUESTS).glob("*" + tail)}
    if git is not None:
        code, out, _ = git(["ls-tree", "--name-only", ORIGIN_MAIN, "--", REQUESTS + "/"], repo)
        if code == 0:
            found.update("{0}/{1}".format(REQUESTS, Path(line.strip()).name)
                         for line in out.splitlines() if line.strip().endswith(tail))
    return sorted(found)


def request(person, row, args, brand, label, now, dry_run):
    # Only fields lab_run.py ALLOWED_FIELDS accepts — never `scheduled`, mini-worker's alone.
    verdict = {"action": JOB, "component": row["component"], "script": row["script"],
               "args": args, "brand": brand, "out": label, "requested_by": person,
               "machine": row["component"]}
    return {"schema": 1, "kind": "workflow-requests", "reviewer": person, "item": label,
            "verdict": verdict,
            "notes": "{0} lab run{1}, filed with mini_run by {2}".format(
                row["component"], " (dry run)" if dry_run else "", person),
            "created": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "via": VIA}


def by_hand(cmds, say):
    say("finish by hand, from the checkout:")
    for c in cmds:
        say("  " + c)


def push(repo, git, say):
    """Push the caller's main. A refusal is said, never pulled in the caller's clone
    (LD-95 (posts off-clone)): a pull there once left a merge and orphan files in the mini's clone."""
    code, _, err = git(["push", "origin", "main"], repo)
    if code == 0:
        return True
    say("push refused — nothing pulled or merged in this clone: {0}".format(err.strip()))
    by_hand(["git fetch origin main", "git rebase origin/main   (or merge it, as you choose)",
             "git push origin main"], say)
    return False


def publish_one(repo, git, rel, body, msg, say, sleep=time.sleep):
    """LD-95 (posts off-clone): commit ONE file to origin/main from a throwaway worktree of
    origin/main, never in `repo`. 0 once origin/main holds the commit, else 1 with one refusal.

    Fetch; `worktree add --detach` origin/main; write `body` at `rel` there, add + commit by
    pathspec (the repo's own hooks run); `push origin HEAD:main`, and on a refusal fetch and
    rebase INSIDE the worktree (clean by construction) and push again, PUBLISH_ATTEMPTS in all;
    the worktree is always removed and pruned. Never writes `rel` into `repo`'s working tree,
    never touches its index, never runs pull, merge, rebase, stash, reset or checkout there:
    the caller's clone receives the file on its next ordinary pull."""
    tmp = Path(tempfile.mkdtemp(prefix="run-kit-publish-"))
    sha, added, last = None, False, ""
    try:
        code, _, last = git(["fetch", "-q", "origin", "main"], repo)
        if code == 0:
            code, _, last = git(["worktree", "add", "-q", "--detach", str(tmp), ORIGIN_MAIN], repo)
            added = code == 0
        if added:
            path = tmp / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
            say("wrote {0}".format(rel))
            for step in (["add", "--", rel], ["commit", "-q", "-m", msg, "--", rel]):
                code, _, last = git(step, tmp)
                if code != 0:
                    break
        if added and code == 0:
            say("committed {0} in a throwaway worktree of {1} — your clone is not touched".format(
                rel, ORIGIN_MAIN))
            for attempt in range(1, PUBLISH_ATTEMPTS + 1):
                code, _, last = git(["push", "origin", "HEAD:main"], tmp)
                if code == 0 or attempt == PUBLISH_ATTEMPTS:
                    break
                say("push refused (attempt {0} of {1}) — rebasing onto {2} in the throwaway worktree"
                    .format(attempt, PUBLISH_ATTEMPTS, ORIGIN_MAIN))
                sleep(PUBLISH_PAUSE_S)
                code, _, err = git(["fetch", "-q", "origin", "main"], tmp)
                if code != 0:
                    last = err
                    continue
                code, _, err = git(["rebase", "-q", ORIGIN_MAIN], tmp)
                if code != 0:    # a conflict does not clear by retrying
                    last = err or "rebase onto {0} failed".format(ORIGIN_MAIN)
                    git(["rebase", "--abort"], tmp)
                    break
            code, out, _ = git(["rev-parse", "HEAD"], tmp)
            sha = out.strip() if code == 0 and out.strip() else None
    finally:
        if added:
            git(["worktree", "remove", "--force", str(tmp)], repo)
        git(["worktree", "prune"], repo)
        if tmp.exists():    # our own temp folder, when the worktree never registered
            shutil.rmtree(str(tmp), ignore_errors=True)
    if sha is not None:
        git(["fetch", "-q", "origin", "main"], repo)
        if git(["merge-base", "--is-ancestor", sha, ORIGIN_MAIN], repo)[0] == 0:
            say("pushed {0} to main from that worktree — your clone gets it on its next pull".format(rel))
            return 0
        last = last or "the commit is not on {0} after the push".format(ORIGIN_MAIN)
    say("not published: {0} — git: {1} — nothing was written, committed or pulled in your clone".format(
        rel, " ".join((last or "").split()) or "?"))
    by_hand(["run the same command again once `git fetch origin main` works",
             "or, in a clean clone on main: write {0}, then `git add -- {0}`, "
             "`git commit -m '{1}' -- {0}`, `git push origin main`".format(rel, msg)], say)
    return 1


def _refusals():
    """Refused as raised by mini_compare: run as a script this module is __main__, and
    mini_compare's own `import mini_run` loads a second copy with its own class."""
    return tuple({Refused, getattr(sys.modules.get("mini_run"), "Refused", Refused)})


def _reached(line, reached):
    return any(w in reached for w in AT_LINE.findall(line))


def preflight(repo, component, brand, args):
    """LD-45 (mini-run refuses on RED): (refuse, show), two lists of lines. The component's
    dry run is traced (LD-44 (dry-run trace)) and every file checked (LD-42 (full check
    default)). Refuses on a NEW RED (a file the person changed) and on what the dry run
    opened outside; every RED already in the code is shown, those at a reached file:line
    first. A door with no dry run, or a dry run that fails or times out, is not traced."""
    import mini_compare   # here, not at the top: mini_compare imports this module
    show = []
    try:
        t = mini_compare.trace(repo, component, brand, {**args, DRY_RUN: "yes"})
    except _refusals() as e:
        t = None
        show.append("not traced: {0}".format(e))
    if t is not None and (t.get("timed_out") or t.get("exit")):
        show.append("not traced: the dry run {0}".format(
            "did not finish in {0} s".format(t.get("timeout")) if t.get("timed_out")
            else "exited {0}".format(t["exit"])))
        t = None
    f = mini_compare.findings(repo, component, trace=t)
    refuse = ["new RED: " + r for r in f["new_red"]] + (list(f.get("trace_red") or []) if t else [])
    reached = (t.get("reached") or set()) if t else set()
    first = [r for r in f["old_red"] if _reached(r, reached)]
    rest = [r for r in f["old_red"] if not _reached(r, reached)]
    show += ["already in the code, reached in the dry run: " + r for r in first]
    if rest:
        show.append("already in the code: {0} RED(s){1}".format(
            len(rest), ":" if len(rest) <= SHOW_REST else ", the first {0}:".format(SHOW_REST)))
        show += ["  " + r for r in rest[:SHOW_REST]]
    show += ["amber: " + a for a in f["amber"]]
    return refuse, show


def file_run(repo, git, ns, now, say, check=None):
    row = row_of(repo, ns.component)
    person = whoami(repo, git)
    filers = row.get("filers") or []
    if ANY_FILER not in filers and person not in filers:
        raise Refused("{0} is not a filer on {1}'s row (filers: {2})".format(
            person, row["component"], ", ".join(filers) or "none"))
    if not SEGMENT.match(ns.brand):
        raise Refused("--brand {0!r} is not a plain name".format(ns.brand))
    label = ns.label or "{0}-{1}".format(row["component"], now.strftime("%Y%m%d-%H%M"))
    if not SEGMENT.match(label) or "--" in label:
        raise Refused("--label {0!r} is not a plain name".format(label))
    hit = already_filed(repo, person, label)
    if hit:
        raise Refused("{0} already filed label {1!r} ({2}) — pick another --label".format(
            person, label, hit[0]))
    args = parse_pairs(ns.pairs)
    if ns.dry_run:
        args[DRY_RUN] = "yes"
    for name, value in args.items():
        if not value:
            raise Refused("{0}= has no value".format(name))
    try:
        kind, door = door_of(repo, row)
    except lab_door.Refused as e:
        raise Refused("{0}'s door does not load: {1}".format(row["component"], e))
    if checked_args(repo, row, kind, door, args, ns.brand) and "label" not in args:
        args["label"] = label
    if not ns.print and not (check is None and os.environ.get(NO_PREFLIGHT) == "1"):
        refuse, show = (check or preflight)(repo, row["component"], ns.brand, args)
        for line in show:
            say(line)
        if refuse:
            raise Refused("{0} RED(s) a mini run of {1} would hit — nothing written:\n  {2}".format(
                len(refuse), row["component"], "\n  ".join(refuse)))
    rec = request(person, row, args, ns.brand, label, now, ns.dry_run)
    rel = "{0}/{1}--{2}--{3}.json".format(REQUESTS, stamp(now), person, label)
    body = json.dumps(rec, indent=2, ensure_ascii=False) + "\n"
    if ns.print:
        say(rel)
        say(body.rstrip())
        say("(--print: nothing written)")
        return 0
    msg = "lab-run: {0} on {1} as {2} — {3} (mini_run)".format(row["component"], ns.brand, person, label)
    if not ns.no_push:
        code, out, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
        if code != 0 or out.strip() != "main":
            raise Refused("this checkout is on {0!r}, not main — a lab run is filed on main; "
                          "switch to main, or use --no-push".format(out.strip() or "?"))
        hit = already_filed(repo, person, label, git)
        if hit:
            raise Refused("{0} already filed label {1!r} ({2}) — pick another --label".format(
                person, label, hit[0]))
        if publish_one(repo, git, rel, body, msg, say) != 0:    # LD-95 (posts off-clone)
            return 1
        say("the mini picks it up; `mini_run.py status {0}` reads it back".format(label))
        return 0
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    say("wrote {0}".format(rel))
    for step in (["add", "--", rel], ["commit", "-m", msg, "--", rel]):
        code, _, err = git(step, repo)
        if code != 0:
            say("git {0} failed: {1}".format(step[0], err.strip()))
            by_hand(["git add -- " + rel, "git commit -m '{0}' -- {1}".format(msg, rel),
                     "git push origin main"], say)
            return 1
    say("committed {0}".format(rel))
    say("--no-push: not pushed — `git push origin main` sends it to the mini")
    return 0


# ── status ───────────────────────────────────────────────────────────────────

def on_main(repo, git):
    """File names in the requests folder at origin/main."""
    code, out, err = git(["ls-tree", "--name-only", ORIGIN_MAIN, "--", REQUESTS + "/"], repo)
    if code != 0:
        raise Refused("cannot list {0} on {1}: {2}".format(REQUESTS, ORIGIN_MAIN, err.strip()))
    return sorted(Path(line).name for line in out.splitlines() if line.strip())


def read_main(repo, git, name):
    code, out, _ = git(["show", "{0}:{1}/{2}".format(ORIGIN_MAIN, REQUESTS, name)], repo)
    if code != 0:
        return {}
    try:
        doc = json.loads(out)
    except ValueError:
        return {}
    return doc if isinstance(doc, dict) else {}


def newest_result(names, label):
    mine = [n for n in names if n.endswith("--{0}--{1}.json".format(WORKER, label))]
    return mine[-1] if mine else None


def detail_text(detail):
    if isinstance(detail, str):
        return detail
    return json.dumps(detail, indent=2, ensure_ascii=False)


def status(repo, git, label, say):
    code, _, err = git(["fetch", "origin", "main"], repo)
    if code != 0:
        say("git fetch failed ({0}) — reading {1} as last fetched".format(err.strip(), ORIGIN_MAIN))
    names = on_main(repo, git)
    if label:
        res = newest_result(names, label)
        if res is None:
            filed = [n for n in names if n.endswith("--{0}.json".format(label))]
            say("{0}: queued — no {1} record on {2} yet{3}".format(
                label, WORKER, ORIGIN_MAIN,
                "" if filed else " (and no request for it there: was it pushed?)"))
            return 0
        verdict = read_main(repo, git, res).get("verdict") or {}
        say("{0}: {1}  ({2})".format(label, verdict.get("status", "?"), res))
        lines = detail_text(verdict.get("detail", "")).splitlines()
        for line in lines[-TAIL:]:
            say("  " + line)
        if verdict.get("status") == "failed":    # LD-29 (mini-debug threads)
            say('mini-debug this run: python3 components/run-kit/mini_debug.py open --run {0} '
                '--slug {0} --ask "…"'.format(label))
        return 0
    person = whoami(repo, git)
    shown = 0
    for name in reversed([n for n in names if n.split("--")[1:2] == [person]]):
        req = read_main(repo, git, name)
        if (req.get("verdict") or {}).get("action") != JOB:
            continue
        item = str(req.get("item") or "")
        res = newest_result(names, item)
        word = ((read_main(repo, git, res).get("verdict") or {}).get("status", "?")
                if res else "queued")
        say("{0:<16} {1}  ({2})".format(word, item, name))
        shown += 1
        if shown == RECENT:
            break
    if not shown:
        say("{0} has no lab-run requests on {1}".format(person, ORIGIN_MAIN))
    return 0


# ── watch ────────────────────────────────────────────────────────────────────

def minutes(seconds):
    return "{0:g}".format(seconds / 60.0)


def last_line(text):
    """LD-57b (watch skips noise): the last non-empty line that is not NOISE, else the last one."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return "(no detail)"
    kept = [l for l in lines if not any(p.search(l.strip()) for p in NOISE)]
    return (kept or lines)[-1]


def outputs_at(verdict, name):
    first = (detail_text(verdict.get("detail", "")).splitlines() or [""])[0]
    m = OUTPUTS_AT.search(first)
    return m.group(1) if m else (verdict.get("run_record") or name)


def watch(repo, git, ns, say, sleep, clock):
    """LD-57 (mini-run watch): silent until the label's run ends or --timeout passes."""
    if ns.interval < 1:
        raise Refused("--interval must be at least 1 second")
    label = ns.label
    say("watching {0} on {1} every {2}s, up to {3} min — one line when it ends".format(
        label, ORIGIN_MAIN, ns.interval, minutes(ns.timeout)))
    start, told = clock(), False
    while True:
        code, _, err = git(["fetch", "origin", "main"], repo)
        if code != 0 and not told:
            say("git fetch failed ({0}) — still watching, reading {1} as last fetched".format(
                err.strip(), ORIGIN_MAIN))
            told = True
        res = newest_result(on_main(repo, git), label)
        verdict = (read_main(repo, git, res).get("verdict") or {}) if res else {}
        word = verdict.get("status") or ""
        if word == "done":
            say("PASSED {0} — outputs at {1}".format(label, outputs_at(verdict, res)))
            return WATCH_PASSED
        if word and word != "running":
            say("FAILED {0} ({1}) — {2}".format(label, word, last_line(detail_text(verdict.get("detail", "")))))
            say("say 'status' for the full reason")
            return WATCH_FAILED
        if clock() - start >= ns.timeout:
            say("stopped watching after {0} min — {1} still {2}; say 'status'".format(
                minutes(ns.timeout), label, "running" if res else "queued"))
            return WATCH_TIMEOUT
        sleep(ns.interval)


# ── the command ──────────────────────────────────────────────────────────────

def parser():
    p = argparse.ArgumentParser(prog="mini_run.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="what the mini can run, and the args each door takes")
    f = sub.add_parser("file", help="file a lab run as the person at the keyboard")
    f.add_argument("component")
    f.add_argument("--brand", required=True)
    f.add_argument("--label")
    f.add_argument("--dry-run", action="store_true")
    once = f.add_mutually_exclusive_group()
    once.add_argument("--no-push", action="store_true", help="commit, do not push")
    once.add_argument("--print", action="store_true", help="print the record, write nothing")
    f.add_argument("pairs", nargs="*", metavar="name=value")
    s = sub.add_parser("status", help="read a run's result back")
    s.add_argument("label", nargs="?")
    w = sub.add_parser("watch", help="say one line when a filed run ends (or --timeout passes)")
    w.add_argument("label")
    w.add_argument("--interval", type=int, default=WATCH_INTERVAL, help="seconds between reads")
    w.add_argument("--timeout", type=int, default=WATCH_TIMEOUT_S, help="seconds before giving up")
    return p


def main(argv=None, repo=None, git=git_run, now=None, say=print, check=None,
         sleep=time.sleep, clock=time.monotonic):
    # parse_known_args, not parse_args: on 3.9 (the mini's interpreter) a
    # nargs="*" positional placed after options is consumed empty before them,
    # so trailing name=value pairs come back as unrecognized. Taken back here.
    p = parser()
    ns, extra = p.parse_known_args(argv)
    if extra:
        if ns.cmd == "file" and all("=" in x and not x.startswith("-") for x in extra):
            ns.pairs = list(ns.pairs or []) + extra
        else:
            p.error("unrecognized arguments: " + " ".join(extra))
    try:
        repo = Path(repo).resolve() if repo else find_repo()
        if ns.cmd == "list":
            return list_rows(repo, say)
        if ns.cmd == "file":
            return file_run(repo, git, ns, now or utc_now(), say, check)
        if ns.cmd == "watch":
            return watch(repo, git, ns, say, sleep, clock)
        return status(repo, git, ns.label, say)
    except Refused as e:
        say("mini_run: refused — {0}".format(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
