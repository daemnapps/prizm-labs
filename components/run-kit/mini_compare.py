#!/usr/bin/python3
"""mini-compare: what a mini run of a component would get, against what is on
this machine. Read-only; prints a report; writes nothing; never reaches the mini.

    python3 components/run-kit/mini_compare.py [component ...] [--all] [--detail]

Every run checks EVERY runnable file of the component — "will this component run
on the mini at all" (LD-42 (full check default); --full, which used to ask for
that, is accepted and ignored). A RED is NEW when a file it names is one you
changed (uncommitted, untracked, or differing from origin/main), else it is
ALREADY IN THE CODE: counted, its lines printed only with --detail.

Named component(s): one section each. No component named: one line per
component with any finding, worst first — `<component>  new <n>  already <n>
amber <n>`; --all adds the clean ones; --detail adds the sections.

Library: findings(root, component) -> {"new_red", "old_red", "amber",
"unchecked", "notes"}, the lines main prints; it does not chdir or fetch.

THE FACT IT RESTS ON: a mini lab run is a fresh worktree at origin/main
(platform/workers/mini-worker/lab_run.py:2). So for code and in-repo files the
comparison is exact from git; only what lives OUTSIDE the repo (packages, tools,
models) needs the mini's published list, platform/data/mini-inventory/index.json
(WM-162 (mini inventory)) — until that file exists, those lines say "not checked".

Moved here from .claude/skills/mini-compare/compare.py (which becomes a shim over
this module) by LD-41 (mini-compare false REDs), the LD-29 (mini-debug threads)
pattern, with five false REDs narrowed: in-repo modules outside components/ are
local, a try-guarded import is optional, a home path after `call() or` (or the
no-shared-assets-mount sentinel) is a guarded fallback, the keys component's own
fallbacks are DELIBERATE, and a re.* pattern string is not a path.

LD-43 (new static checks) added six shapes, each feeding findings() with the same
new/old split: RED for data only on one machine (a path built from the component's
own __file__ into a folder git ignores), a local service (an http(s)/ws URL to
localhost or 127.0.0.1, or either with a port), a Drive-app-only feature
(com.google.drivefs, an os.walk over CloudStorage or mount()), an id from hashing
a path, and output inside a component (O4 (output under runs)); AMBER for a try
around a drive / index / reach / mount call whose handler only passes or returns an
empty value. The
component's code — and the local-name set — is what git tracks or could track,
never a gitignored .venv/, work/ or models/; brandpath's drive_index.py joins
DELIBERATE.

LD-44 (dry-run trace) runs what the static checks cannot see:

    python3 components/run-kit/mini_compare.py <component> --trace [--brand B] [name=value ...]

runs the component's grant-row door (team/dispatch-grants.json → its
lab_entry.py) as the worker does — /usr/bin/python3, args as sorted --name value
pairs, cwd the checkout, BRAND, a fresh temp OUT, DRIVE_MOUNT=off, every
key-shaped name outside the mini's lab-run ceiling removed — always with
dry_run=yes, minus the sandbox. A temp sitecustomize.py first on PYTHONPATH
(so every child Python inherits it) logs each path given to open, os.listdir and
os.scandir, and each checkout line run. A path opened outside the checkout, the
temp OUT, the temp dir, the interpreter's own folders, /dev, /System,
/Library/Developer, /usr and a Shared Assets mount is RED "the dry run opened
<path>". LD-44b (trace narrowing): each traced Python never logs its OWN
interpreter (its prefixes, its executable's folder, its sys.path outside the
checkout), and a logged path that does not exist after the run is a probe —
counted ("probed, absent here: N"), never RED. A static path RED whose file:line the run never reached becomes AMBER
"fallback — not reached in the dry run". A door with no dry_run is refused and
nothing runs. A child started with -I, -E or a non-Python binary is not traced.
Library: trace(root, component, brand, args) -> {"opened", "reached", "exit"};
findings(root, component, trace=that) applies it.

Python 3.9-safe on purpose: it runs under /usr/bin/python3 like the mini.
"""

import ast
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

ORIGIN = "origin/main"
MINI_PY = "/usr/bin/python3"
INVENTORY = "platform/data/mini-inventory/index.json"
JOB_ENV_PY = "platform/workers/mini-worker/job_env.py"
# import name -> distribution name, for the common cases where they differ
ALIASES = {"PIL": "pillow", "cv2": "opencv-python", "yaml": "pyyaml",
           "googleapiclient": "google-api-python-client", "google": "google-auth",
           "bs4": "beautifulsoup4", "dotenv": "python-dotenv", "sklearn": "scikit-learn",
           "fitz": "pymupdf", "dateutil": "python-dateutil", "magic": "python-magic"}
# modules that exist only INSIDE Blender's own Python (a script handed to the blender binary),
# never in /usr/bin/python3 — checked as "is Blender on the mini", not as a missing package
BLENDER_MODULES = {"bpy", "bmesh", "mathutils", "bpy_extras", "gpu", "gpu_extras", "aud",
                   "bl_math", "bl_ui", "freestyle", "idprop", "imbuf"}
PATH_HINTS = re.compile(r"""(/Users/[A-Za-z0-9._-]+|~/|Path\.home\(\)|expanduser\(|Library/CloudStorage|GoogleDrive-|My Drive)""")
ENV_READ = re.compile(r"""(?:os\.environ\.get|os\.getenv|environ\.get)\(\s*['"]([A-Z][A-Z0-9_]{2,})['"]|os\.environ\[\s*['"]([A-Z][A-Z0-9_]{2,})['"]\s*\]""")
# files whose home/Drive paths are the point, not a leak (LD-41 (mini-compare false REDs) fix 4):
# their path findings print one "deliberate" line; their key reads and packages are still checked
DELIBERATE = {
    "components/keys/loader.py": "the keys loader reads the environment first; its key files are the deliberate fallback (O6)",
    "components/keys/merge.py": "a person's own --out default; never run on the mini",
    # LD-43 (new static checks) item 0, added at the carding of LD-47 (Drive sweep)
    "components/brandpath/drive_index.py": "it IS the shared Drive-folder finder (accounts()/mount()), "
                                           "off on a worker spawn by LD-26 (mount switch)",
}
# the sentinel a Drive lookup falls back to when no Shared Assets mount is found (fix 3)
NO_MOUNT = "no-shared-assets-mount"
# re.<fn>(pattern, ...): the first argument is a pattern, not a path (fix 5)
RE_FUNCS = {"compile", "search", "match", "fullmatch", "sub", "findall", "finditer", "split"}
# an except clause naming one of these (or a bare one) makes the imports in its try optional (fix 2)
IMPORT_GUARDS = {"ImportError", "ModuleNotFoundError", "Exception"}


def git(*args, ok=(0,), cwd=None):
    p = subprocess.run(["git"] + list(args), capture_output=True, text=True,
                       cwd=None if cwd is None else str(cwd))
    if p.returncode not in ok:
        return None
    return p.stdout


def lines(out):
    return [l for l in (out or "").splitlines() if l.strip()]


def _at(root, f):
    """A repo-relative path, opened from root (or the current folder when no root)."""
    return f if root is None else os.path.join(str(root), f)


def who_am_i(root):
    """(person or None, email): run_kit.people's answer, LD-77 (one person resolver)."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    from run_kit import people
    email = (git("config", "user.email", cwd=root) or "").strip().lower()
    return people.try_person_of(root, email), email


def components(root):
    return sorted(p.name for p in (root / "components").iterdir()
                  if p.is_dir() and not p.name.startswith((".", "_")))


_DRIFT = None   # (root, buckets): asked once per root


def _bucket(paths, key):
    out = {}
    for x in paths:
        parts = x.split("/")
        if len(parts) > 1 and parts[0] == "components":
            out.setdefault(parts[1], []).append(x)
    return out


def _log_bucket(rng, root=None):
    """{component: ["<sha> <subject>", ...]} for commits in rng touching it — one git call."""
    out, head = {}, None
    for l in (git("log", "--format=@@%h %s", "--name-only", rng, "--", "components", cwd=root) or "").splitlines():
        if l.startswith("@@"):
            head = l[2:]
        elif l.strip() and head:
            parts = l.split("/")
            if len(parts) > 1 and parts[0] == "components":
                lst = out.setdefault(parts[1], [])
                if head not in lst:
                    lst.append(head)
    return out


def drift(c, root=None):
    """Five git questions asked ONCE for all of components/, then bucketed."""
    global _DRIFT
    if _DRIFT is None or _DRIFT[0] != str(root):
        ign = [x for x in lines(git("ls-files", "--others", "--ignored", "--exclude-standard",
                                    "--directory", "--", "components", cwd=root))
               if "__pycache__" not in x and not x.endswith((".pyc", ".DS_Store"))]
        _DRIFT = (str(root), {
            "uncommitted": _bucket(lines(git("diff", "--name-only", "HEAD", "--", "components", cwd=root)), 0),
            "untracked": _bucket(lines(git("ls-files", "--others", "--exclude-standard", "--", "components",
                                           cwd=root)), 0),
            "only_here_ignored": _bucket(ign, 0),
            "unpushed": _log_bucket(ORIGIN + "..HEAD", root),
            "unpulled": _log_bucket("HEAD.." + ORIGIN, root),
        })
    return {k: v.get(c, []) for k, v in _DRIFT[1].items()}


def changed_py(c, d, root=None):
    files = set(d["uncommitted"]) | set(d["untracked"])
    for f in lines(git("diff", "--name-only", ORIGIN + "...HEAD", "--", "components/" + c, cwd=root)):
        files.add(f)
    return sorted(f for f in files if f.endswith(".py") and os.path.isfile(_at(root, f)))


def deps(root, c):
    """Other components this one names as a quoted string (inferred, not traced)."""
    names = set(components(root)) - {c}
    found = set()
    for f in (root / "components" / c).rglob("*.py"):
        if any(part.startswith(".") for part in f.parts):
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        for n in names:
            if ('"%s"' % n) in text or ("'%s'" % n) in text or ("components/%s" % n) in text:
                found.add(n)
    return sorted(found)


def compile_39(files, root=None):
    """[(file, line)] — file None when the check itself could not run."""
    if not files:
        return []
    if not os.access(MINI_PY, os.X_OK):
        return [(None, "%s is not on this machine — the 3.9.6 check could not run" % MINI_PY)]
    bad = []
    for f in files:
        p = subprocess.run([MINI_PY, "-m", "py_compile", f], capture_output=True, text=True,
                           cwd=None if root is None else str(root))
        if p.returncode != 0:
            msg = (p.stderr.strip().splitlines() or ["?"])[-1]
            bad.append((f, "%s — %s" % (f, msg[:160])))
    return bad


def union_hints(files, root=None):
    """`X | Y` in a hint the 3.9.6 interpreter EVALUATES (a def's signature, a module- or
    class-level annotation) with no `from __future__ import annotations`: it compiles,
    then raises TypeError the moment the file loads on the mini (builder's card rule 10).
    [(file, line)]."""
    bad = []
    for f in files:
        try:
            tree = ast.parse(open(_at(root, f), errors="replace").read())
        except SyntaxError:
            continue
        if any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
               and any(a.name == "annotations" for a in n.names) for n in tree.body):
            continue

        def has_or(node):
            return node is not None and any(isinstance(x, ast.BinOp) and isinstance(x.op, ast.BitOr)
                                            for x in ast.walk(node))
        hits = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                a = node.args
                for arg in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg]:
                    if arg is not None and has_or(arg.annotation):
                        hits.append(node.lineno)
                if has_or(node.returns):
                    hits.append(node.lineno)
        for scope in [tree] + [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for n in scope.body:
                if isinstance(n, ast.AnnAssign) and has_or(n.annotation):
                    hits.append(n.lineno)
        for ln in sorted(set(hits))[:5]:
            bad.append((f, "%s:%d — an `X | Y` type hint: fails when the file loads on 3.9.6 "
                           "(add `from __future__ import annotations` or use Optional/Union)" % (f, ln)))
    return bad


PATHY = re.compile(r"^(?:/Users/[^/\s]+|~/|.*Library/CloudStorage|.*GoogleDrive-|.*My Drive/)\S*$")


def _is_home(node):
    """`Path.home()` / `pathlib.Path.home()` only — a call named `home` on anything else
    (e.g. a product-kit lookup) is not this machine's home folder."""
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    f = node.func
    if f.attr != "home":
        return False
    v = f.value
    return (isinstance(v, ast.Name) and v.id == "Path") or \
           (isinstance(v, ast.Attribute) and v.attr == "Path")


def _is_tilde_expand(node):
    """expanduser() of a LITERAL starting with "~" — Path("~/x").expanduser() or
    os.path.expanduser("~/x"). expanduser() of a value the caller passes in is not a
    machine path and is never flagged."""
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) \
            or node.func.attr != "expanduser":
        return False
    def tilde(x):
        return isinstance(x, ast.Constant) and isinstance(x.value, str) and x.value.startswith("~")
    if node.args and tilde(node.args[0]):                       # os.path.expanduser("~/…")
        return True
    v = node.func.value                                         # Path("~/…").expanduser()
    return isinstance(v, ast.Call) and bool(v.args) and tilde(v.args[0])


SKIP_PARTS = ("archive", "retired", "tests", "fixtures")


def runs_on_mini(f):
    """Files a mini run never executes: tests and archived/retired code."""
    name = os.path.basename(f)
    if name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py":
        return False
    return not any(part in SKIP_PARTS for part in f.split("/"))


def stdlib_shadows(root, c):
    """A .py file in the component named like one of Python's own modules (platform, copy,
    email, calendar, profile …). When a script in that folder runs, Python puts the folder
    first on the import path, so ANY library in that run that imports the real module gets
    this file instead — the owner's three-doctors-2 died exactly so (video-production's
    platform.py, 2026-10-19; LD-19 (calendar shadow fix) and LD-27 (platform shadow fix)).
    [(file, line)]."""
    if not os.access(MINI_PY, os.X_OK):
        return []
    files = [f for f in (root / "components" / c).rglob("*.py")
             if runs_on_mini(str(f.relative_to(root)))
             and not any(p.startswith(".") for p in f.relative_to(root).parts)]
    stems = sorted({f.stem for f in files})
    if not stems:
        return []
    code = ("import importlib.util,json,sys,os\n"
            "out=[]\n"
            "for n in sys.argv[1:]:\n"
            "    s=importlib.util.find_spec(n)\n"
            "    if s and s.origin and ('/lib/python' in s.origin or s.origin in ('built-in','frozen')):\n"
            "        out.append(n)\n"
            "print(json.dumps(out))")
    p = subprocess.run([MINI_PY, "-I", "-S", "-c", code] + stems, capture_output=True, text=True, cwd="/")
    try:
        hit = set(json.loads(p.stdout))
    except ValueError:
        return []
    out = []
    for f in files:
        if f.stem in hit:
            rel = str(f.relative_to(root))
            out.append((rel, "%s hides Python's own `%s` module from every library in a run started in "
                             "that folder (load the standard one first, or rename it)" % (rel, f.stem)))
    return out


def _regex_patterns(tree):
    """ids of string constants passed FIRST to re.compile/search/match/… — a pattern, not a path."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in RE_FUNCS and isinstance(node.func.value, ast.Name) \
                and node.func.value.id == "re" and node.args and isinstance(node.args[0], ast.Constant):
            out.add(id(node.args[0]))
    return out


def _or_fallbacks(tree):
    """ids of every node inside a non-first operand of an `or` whose first operand is a call —
    `drive_index.mount() or Path.home() / …`: the home path is only the fallback."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) \
                and isinstance(node.values[0], ast.Call):
            for v in node.values[1:]:
                out.update(id(x) for x in ast.walk(v))
    return out


def _names_no_mount(node, parent):
    """The path expression a hit sits in (climbing `/` joins and Path(…)/expanduser() wraps)
    has the segment no-shared-assets-mount — a sentinel that names no real folder."""
    top = node
    while True:
        p = parent.get(id(top))
        if isinstance(p, ast.BinOp) and isinstance(p.op, ast.Div):
            top = p
        elif isinstance(p, ast.Call) and top in p.args and (
                (isinstance(p.func, ast.Name) and p.func.id == "Path")
                or (isinstance(p.func, ast.Attribute) and p.func.attr in ("Path", "expanduser"))):
            top = p
        else:
            break
    return any(isinstance(x, ast.Constant) and isinstance(x.value, str) and NO_MOUNT in x.value.split("/")
               for x in ast.walk(top))


def path_literals(files, root=None):
    """Paths the CODE uses (not prose): a string constant that is itself a home / Drive-mount
    path with no spaces, or a Path.home()/expanduser() joined into a path. Docstrings and
    prompt text that merely mention ~/… are skipped. A file the 3.9 parser refuses falls
    back to a plain line scan. Returns (where, line, shared, guarded): `guarded` when every
    hit on the line is a fallback after `call() or`, or the no-shared-assets-mount sentinel."""
    hits = []
    for f in files:
        try:
            text = open(_at(root, f), errors="replace").read()
        except OSError:
            continue
        src = text.splitlines()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            for n, line in enumerate(src, 1):
                if PATH_HINTS.search(line) and not line.lstrip().startswith("#"):
                    hits.append(("%s:%d" % (f, n), line.strip()[:120], "Shared Assets" in line, False))
            continue
        patterns, fallbacks = _regex_patterns(tree), _or_fallbacks(tree)
        parent = {id(ch): p for p in ast.walk(tree) for ch in ast.iter_child_nodes(p)}
        lines_hit = {}   # line -> [guarded, …], one per hit on it
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and PATHY.match(node.value):
                if id(node) in patterns:
                    continue
                guarded = id(node) in fallbacks
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                homes = [x for x in ast.walk(node.left) if _is_home(x)]
                if not homes:
                    continue
                guarded = all(id(x) in fallbacks for x in homes)
            elif _is_tilde_expand(node):
                guarded = id(node) in fallbacks
            else:
                continue
            guarded = guarded or _names_no_mount(node, parent)
            lines_hit.setdefault(node.lineno, []).append(guarded)
        for n in sorted(lines_hit):
            line = src[n - 1] if n - 1 < len(src) else ""
            hits.append(("%s:%d" % (f, n), line.strip()[:120],
                         "Shared Assets" in line or "Shared drives" in line, all(lines_hit[n])))
    return hits


# LD-43 (new static checks): six shapes that run here and not on the mini
# a service URL (file://localhost/… is a file, not a service) or a host with a port
LOCAL_SERVICE = re.compile(r"(?:\b(?:https?|wss?)://(?:localhost|127\.0\.0\.1)\b|"
                           r"\b(?:localhost|127\.0\.0\.1):\d+)", re.I)
DRIVEFS = "com.google." + "drivefs"   # split, so this file does not name it as a constant
SWALLOW_WORDS = ("drive", "index", "reach", "mount")
WRITE_MODES = set("wax")
UNKNOWN = "\0"   # a path segment the code computes at run time
# calls whose result no longer depends on WHERE the checkout sits: hashing what they
# return is not hashing a path (check 4) — a file's contents, a relative path, a base name
PORTABLE_CALLS = {"read_bytes", "read_text", "read", "relative_to", "relpath", "basename"}
PORTABLE_ATTRS = {"name", "stem", "suffix"}
# LD-43b (narrow new checks): what str()/os.fspath() must wrap to count as a path (check 4)
PATH_WORDS = ("path", "file", "src", "dir")
PATH_CALLS = {"Path", "pathlib.Path", "PurePath", "pathlib.PurePath"}
# calls that open a connection (check 2): a URL anywhere else is a print, a link or a note
CONNECT_CALLS = {"urllib.request.urlopen", "urllib.request.Request", "http.client.HTTPConnection",
                 "http.client.HTTPSConnection", "socket.create_connection"}
CONNECT_MODULES = ("requests.", "httpx.")
ARGV_FETCHERS = ("curl", "wget")


def _dotted(node):
    """`a.b.c` for a Name/Attribute chain rooted at a Name, else ""."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ""
    parts.append(node.id)
    return ".".join(reversed(parts))


def _prose(tree):
    """ids of string constants that stand alone as a statement — docstrings, bare strings."""
    return {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr)
            and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}


def _rebound(tree):
    """Names bound by something other than `name = …` (an argument, a loop, a with, an
    except, an import): a name like that is never taken as the component's own folder."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)):
            out.update(x.id for x in ast.walk(n.target) if isinstance(x, ast.Name))
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            out.update(x.id for x in ast.walk(n.optional_vars) if isinstance(x, ast.Name))
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            out.update((a.asname or a.name).split(".")[0] for a in n.names)
        elif isinstance(n, (ast.AugAssign, ast.NamedExpr)) and isinstance(n.target, ast.Name):
            out.add(n.target.id)
    return out


class _Here:
    """Paths the code builds from its own file — `__file__`, `Path(__file__)…`,
    `os.path.dirname(__file__)`, a name every assignment of which is one of those, and
    joins onto them — as repo-relative segments (UNKNOWN for a part computed at run
    time), or None when the expression is not one."""

    def __init__(self, tree, rel):
        self.file = tuple(rel.split("/"))
        self.names = {}
        values = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                targets, v = n.targets, n.value
            elif isinstance(n, ast.AnnAssign) and n.value is not None:
                targets, v = [n.target], n.value
            else:
                continue
            for t in targets:
                if isinstance(t, ast.Name):
                    values.setdefault(t.id, []).append(v)
                else:   # a, b = … : not followed
                    for x in ast.walk(t):
                        if isinstance(x, ast.Name):
                            values.setdefault(x.id, []).append(None)
        skip = _rebound(tree)
        for _ in range(4):   # HERE = Path(__file__).parent; ROOT = HERE.parent; …
            changed = False
            for name, vs in values.items():
                if name in skip or None in vs:
                    continue
                got = {self.eval(v) for v in vs}
                one = got.pop() if len(got) == 1 else None
                if one is not None and self.names.get(name) != one:
                    self.names[name] = one
                    changed = True
            if not changed:
                break

    @staticmethod
    def _up(segs, n):
        if segs is None or len(segs) < n:
            return None
        return segs[:len(segs) - n]

    @staticmethod
    def _join(segs, parts):
        if segs is None:
            return None
        out = list(segs)
        for p in parts:
            if isinstance(p, ast.Constant) and isinstance(p.value, str):
                if p.value.startswith(("/", "~")):
                    return None
                for s in p.value.split("/"):
                    if s in ("", "."):
                        continue
                    if s == "..":
                        if not out:
                            return None
                        out.pop()
                    else:
                        out.append(s)
            else:
                out.append(UNKNOWN)
        return tuple(out)

    def eval(self, node):
        if isinstance(node, ast.Name):
            return self.file if node.id == "__file__" else self.names.get(node.id)
        if isinstance(node, ast.Attribute) and node.attr == "parent":
            return self._up(self.eval(node.value), 1)
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
                and node.value.attr == "parents":
            i = node.slice   # 3.9 and later; 3.8 wrapped it in ast.Index
            if isinstance(i, getattr(ast, "Index", ())):
                i = i.value
            if isinstance(i, ast.Constant) and isinstance(i.value, int) and i.value >= 0:
                return self._up(self.eval(node.value.value), i.value + 1)
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self._join(self.eval(node.left), [node.right])
        if not isinstance(node, ast.Call) or any(isinstance(a, ast.Starred) for a in node.args):
            return None
        fn, a = _dotted(node.func), node.args
        if isinstance(node.func, ast.Attribute):
            attr, recv = node.func.attr, node.func.value
            if attr in ("resolve", "absolute", "expanduser") and not a:
                return self.eval(recv)
            if attr == "joinpath":
                return self._join(self.eval(recv), a)
            if attr == "with_name" and len(a) == 1:
                return self._join(self._up(self.eval(recv), 1), a)
        if len(a) == 1 and fn in ("os.path.dirname", "path.dirname", "dirname"):
            return self._up(self.eval(a[0]), 1)
        if len(a) == 1 and fn in ("os.path.abspath", "os.path.realpath", "os.path.normpath",
                                  "path.abspath", "path.realpath", "abspath", "realpath",
                                  "os.fspath", "str"):
            return self.eval(a[0])
        if a and fn in ("os.path.join", "path.join"):
            return self._join(self.eval(a[0]), a[1:])
        if a and fn in ("Path", "pathlib.Path", "PurePath", "pathlib.PurePath"):
            return self._join(self.eval(a[0]), a[1:])
        return None

    @staticmethod
    def is_join(node):
        """A node that joins something onto a path: `/`, os.path.join, joinpath, Path(a, b)."""
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return True
        if isinstance(node, ast.Call):
            fn = _dotted(node.func)
            if fn in ("os.path.join", "path.join") or (
                    isinstance(node.func, ast.Attribute) and node.func.attr in ("joinpath", "with_name")):
                return True
            return fn in ("Path", "pathlib.Path") and len(node.args) > 1
        return False


def _show(segs):
    return "/".join("…" if s == UNKNOWN else s for s in segs)


def _ignored(paths, root=None):
    """The subset of repo-relative paths `git check-ignore` says are ignored (one call)."""
    if not paths:
        return set()
    p = subprocess.run(["git", "check-ignore", "--stdin", "-z"], input="\0".join(paths) + "\0",
                       capture_output=True, text=True, cwd=None if root is None else str(root))
    if p.returncode not in (0, 1):
        return set()
    return {x for x in p.stdout.split("\0") if x}


def _path_like(n):
    """A value str()/os.fspath() turns into a path (LD-43b (narrow new checks)): a
    name or attribute holding path/file/src/dir, a Path(…) call, or a .resolve() /
    .absolute() / .as_posix() call — never a number or a .stat() field."""
    if isinstance(n, ast.Attribute):
        x = n
        while isinstance(x, (ast.Attribute, ast.Call)):   # v.stat().st_size, os.lstat(p).st_mtime
            f = x.func if isinstance(x, ast.Call) else x
            if isinstance(f, ast.Attribute) and f.attr in ("stat", "lstat"):
                return False
            x = f.value if isinstance(f, ast.Attribute) else None
        if n.attr.startswith("st_"):
            return False
        return any(w in n.attr.lower() for w in PATH_WORDS) and _dotted(n) != "os.path"
    if isinstance(n, ast.Name):
        return any(w in n.id.lower() for w in PATH_WORDS)
    if isinstance(n, ast.Call):
        if _dotted(n.func) in PATH_CALLS:
            return True
        return isinstance(n.func, ast.Attribute) and n.func.attr in ("resolve", "absolute", "as_posix")
    return False


def _hash_hits(arg):
    """True when a hash argument holds a path: str()/os.fspath() of a path-like value
    (_path_like), a .resolve()/.absolute()/.as_posix() call, or a name/attribute
    containing `path` — not below a call that makes it portable (contents,
    relative_to/relpath, a base name)."""
    def portable(n):
        if isinstance(n, ast.Constant):
            return True
        if isinstance(n, ast.Attribute):
            return n.attr in PORTABLE_ATTRS
        if isinstance(n, ast.Call):
            last = n.func.attr if isinstance(n.func, ast.Attribute) else _dotted(n.func)
            return last in PORTABLE_CALLS or last == "open"
        return False
    stack = [arg]
    while stack:
        n = stack.pop()
        if portable(n):
            continue
        if isinstance(n, ast.Call):
            fn = _dotted(n.func)
            last = n.func.attr if isinstance(n.func, ast.Attribute) else fn
            if fn in ("str", "os.fspath") and n.args:
                if not portable(n.args[0]) and _path_like(n.args[0]):
                    return True
                continue   # str(size), str(p.stat().st_size): a number, not a path
            if isinstance(n.func, ast.Attribute) and last in ("resolve", "absolute", "as_posix"):
                return True
        elif isinstance(n, ast.Attribute):
            if "path" in n.attr.lower() and _dotted(n) != "os.path":
                return True
        elif isinstance(n, ast.Name) and "path" in n.id.lower():
            return True
        stack.extend(ast.iter_child_nodes(n))
    return False


def _aliases(tree):
    """Local name -> the dotted name it imports: `from urllib.request import urlopen`
    makes `urlopen` urllib.request.urlopen, `import httpx as hx` makes `hx` httpx."""
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out.update((a.asname, a.name) for a in n.names if a.asname)
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            out.update((a.asname or a.name, n.module + "." + a.name) for a in n.names)
    return out


def _url_text(node, names):
    """The text of a URL argument — a constant, an f-string, a concatenation, a % or
    .format() template, a (host, port) pair, or a name assigned one of those — with
    "{}" for a part computed at run time; None when none of it is text."""
    if isinstance(node, ast.Constant):
        v = node.value
        if isinstance(v, str):
            return v
        return str(v) if isinstance(v, int) and not isinstance(v, bool) else None
    if isinstance(node, ast.JoinedStr):
        parts = [_url_text(v.value if isinstance(v, ast.FormattedValue) else v, names) for v in node.values]
        return "".join("{}" if p is None else p for p in parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        l, r = _url_text(node.left, names), _url_text(node.right, names)
        return None if l is None and r is None else (l or "{}") + (r or "{}")
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        return _url_text(node.left, names)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return _url_text(node.func.value, names)
    if isinstance(node, ast.Tuple) and node.elts:
        parts = [_url_text(e, names) for e in node.elts]
        return None if None in parts else ":".join(parts)
    if isinstance(node, (ast.Name, ast.Attribute)):
        return names.get(_dotted(node))
    return None


def _url_names(tree):
    """name (or self.attr) -> the _url_text it is assigned; a name given a local
    service once keeps that text."""
    assigned = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                assigned.setdefault(_dotted(t), []).append(n.value)
        elif isinstance(n, ast.AnnAssign) and n.value is not None:
            assigned.setdefault(_dotted(n.target), []).append(n.value)
    assigned.pop("", None)
    names = {}
    for _ in range(3):   # BASE = "http://localhost:8795"; API = BASE + "/api"; …
        for k, vs in assigned.items():
            texts = sorted({_url_text(v, names) for v in vs} - {None})
            local = [t for t in texts if LOCAL_SERVICE.search(t)]
            if texts:
                names[k] = (local or texts)[0]
    return names


def _service_args(node, aliases):
    """The arguments that name where a connection goes: of a call that opens one
    (CONNECT_CALLS, requests.*, httpx.*, websocket(s).connect), or the rest of an
    argv list that starts with curl or wget. [] for anything else."""
    if isinstance(node, (ast.List, ast.Tuple)) and node.elts:
        first = node.elts[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str) \
                and first.value.rsplit("/", 1)[-1] in ARGV_FETCHERS:
            return list(node.elts[1:])
        return []
    if not isinstance(node, ast.Call):
        return []
    fn = _dotted(node.func)
    head, _, rest = fn.partition(".")
    if head in aliases:
        fn = aliases[head] + ("." + rest if rest else "")
    if not (fn in CONNECT_CALLS or fn.startswith(CONNECT_MODULES)
            or (fn.split(".")[0] in ("websocket", "websockets") and fn.endswith(".connect"))):
        return []
    args = list(node.args) + [k.value for k in node.keywords]
    if fn.startswith("http.client.") and len(node.args) > 1:   # HTTPConnection("localhost", 8797)
        args.append(ast.copy_location(ast.Tuple(elts=node.args[:2], ctx=ast.Load()), node.args[0]))
    return args


def _swallows(h):
    """A handler whose body only passes or returns [], {}, None or ""."""
    for s in h.body:
        if isinstance(s, ast.Pass):
            continue
        if isinstance(s, ast.Return):
            v = s.value
            if v is None or (isinstance(v, ast.Constant) and v.value in (None, "")) \
                    or (isinstance(v, ast.List) and not v.elts) or (isinstance(v, ast.Dict) and not v.keys):
                continue
        return False
    return True


def _reach_call(body):
    """The first call in a try body (not inside a def or lambda there) whose name holds
    drive / index / reach / mount — `lst.index(x)` / `s.rindex(x)`, the list and str
    methods, are not one."""
    stack = list(body)
    while stack:
        n = stack.pop(0)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        if isinstance(n, ast.Call):
            parts, x = [], n.func
            while isinstance(x, ast.Attribute):
                parts.append(x.attr)
                x = x.value
            if isinstance(x, ast.Name):
                parts.append(x.id)
            if parts and isinstance(n.func, ast.Attribute) and parts[0] in ("index", "rindex"):
                parts = parts[1:]
            name = ".".join(reversed(parts))
            if any(w in p.lower() for p in parts for w in SWALLOW_WORDS):
                return name
        stack.extend(ast.iter_child_nodes(n))
    return None


def _write_targets(node, fn, attr, kw):
    """What a call writes to, as candidate expressions: open(t, "w"|"a"|"x"…) and
    t.open("w"…), .write_text/.write_bytes/.mkdir, os.makedirs/os.mkdir, and the
    destination of shutil.copy*/move."""
    a = list(node.args)

    def writes(mode):
        return isinstance(mode, ast.Constant) and isinstance(mode.value, str) \
            and bool(WRITE_MODES & set(mode.value))
    out = []
    if fn in ("open", "io.open") or attr == "open":
        if attr == "open" and writes(a[0] if a else kw.get("mode")):
            out.append(node.func.value)                      # Path(…).open("w")
        if a and writes(a[1] if len(a) > 1 else kw.get("mode")):
            out.append(a[0])                                 # open(path, "w"), gzip.open(path, "wt")
    elif attr in ("write_text", "write_bytes", "mkdir"):
        out.append(node.func.value)
    elif fn in ("os.makedirs", "os.mkdir") and a:
        out.append(a[0])
    elif fn.startswith("shutil.copy") or fn == "shutil.move":
        dst = a[1] if len(a) > 1 else kw.get("dst")
        if dst is not None:
            out.append(dst)
    return out


def static_checks(files, root=None):
    """Checks 1–6 of LD-43 (new static checks), over the AST of each file, narrowed by
    LD-43b (narrow new checks): one finding per file:line, a write's being check 5's.
    Returns (red, amber): red = [(file, "file:line", kind, line)] — kind "drive" for a
    Drive-app-only feature, which a DELIBERATE file keeps as a note — amber = [line]."""
    red, amber, ignore_asks = [], [], []
    wrote = set()   # "file:line" check 5 named: check 1 does not name it again
    for f in files:
        try:
            with open(_at(root, f), errors="replace") as fh:
                tree = ast.parse(fh.read())
        except (OSError, SyntaxError, ValueError):
            continue   # a file the parser refuses is already RED (compile_39)
        prose, patterns = _prose(tree), _regex_patterns(tree)
        here = _Here(tree, f)
        # never the builtin hash(): salted per process, so it is never a stored id
        hashers = {a.asname or a.name for n in ast.walk(tree)
                   if isinstance(n, ast.ImportFrom) and n.module == "hashlib" for a in n.names}
        urls, aliases = _url_names(tree), _aliases(tree)
        drive_names = set()
        for _ in range(3):   # names assigned from a CloudStorage string or a mount() call
            for n in ast.walk(tree):
                if isinstance(n, ast.Assign) and any(
                        (isinstance(x, ast.Constant) and isinstance(x.value, str) and "CloudStorage" in x.value)
                        or (isinstance(x, ast.Call) and (_dotted(x.func) or "").rsplit(".", 1)[-1] == "mount")
                        or (isinstance(x, ast.Name) and x.id in drive_names) for x in ast.walk(n.value)):
                    drive_names.update(t.id for t in n.targets if isinstance(t, ast.Name))
        seen = set()

        def hit(kind, ln, label, tail):
            where = "%s:%d" % (f, ln)
            line = "%s (%s): %s" % (label, where, tail)
            if kind == "output":   # one write finding per file:line
                if where in wrote:
                    return
                wrote.add(where)
            if line not in seen:
                seen.add(line)
                red.append((f, where, kind, line))

        for node in ast.walk(tree):
            ln = getattr(node, "lineno", 0)
            # 2 — a local service, only where the code opens a connection to it
            for x in _service_args(node, aliases):
                m = LOCAL_SERVICE.search(_url_text(x, urls) or "")
                if m:
                    hit("service", getattr(x, "lineno", ln), "a local service",
                        "%s — a mini run reaches only what listens on the mini" % m.group(0))
            # 3 — Drive for desktop's own data folder
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and id(node) not in prose and id(node) not in patterns:
                if DRIVEFS in node.value:
                    hit("drive", ln, "a Drive-app-only feature",
                        "%s — Drive for desktop's own data; the mini has no Drive app" % DRIVEFS)
            # 1 — a path from the component's own folder into an ignored one
            if here.is_join(node):
                segs = here.eval(node)
                if segs is not None:
                    known = segs[:segs.index(UNKNOWN)] if UNKNOWN in segs else segs
                    ignore_asks.append((f, ln, segs, known))
            if not isinstance(node, ast.Call):
                continue
            fn = _dotted(node.func)
            attr = node.func.attr if isinstance(node.func, ast.Attribute) else ""
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            # 3 — os.walk over the Drive mount
            if fn == "os.walk" and (node.args or "top" in kw):
                top = node.args[0] if node.args else kw["top"]
                if any((isinstance(x, ast.Constant) and isinstance(x.value, str) and "CloudStorage" in x.value)
                       or (isinstance(x, ast.Call) and (_dotted(x.func) or "").rsplit(".", 1)[-1] == "mount")
                       or (isinstance(x, ast.Name) and x.id in drive_names) for x in ast.walk(top)):
                    hit("drive", ln, "a Drive-app-only feature",
                        "os.walk over the Drive for desktop folder — a mini run has no mount "
                        "(LD-26 (mount switch))")
            # 4 — an id from hashing a path
            if (fn.startswith("hashlib.") or fn in hashers) and any(
                    _hash_hits(x) for x in list(node.args) + list(kw.values())):
                hit("hash", ln, "an id from hashing a path",
                    "the same file hashes to another id in a mini run's checkout, which sits "
                    "in another folder")
            # 5 — output inside the component
            segs = None
            for target in _write_targets(node, fn, attr, kw):
                segs = here.eval(target)
                if segs is not None:
                    break
            if segs is not None and len(segs) >= 3 and segs[0] == "components":
                hit("output", ln, "output inside the component",
                    "writes %s — output goes under runs/<machine>/<brand>/<label>/, never inside "
                    "a component (O4 (output under runs))" % _show(segs))
        # 6 — a try that turns an unreachable Drive / index into an empty answer
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                name = _reach_call(node.body)
                quiet = [h for h in node.handlers if _swallows(h)]
                if name and quiet:
                    amber.append((f, node.lineno,
                                  "a swallowed error (%s:%d): the try around %s() answers an empty "
                                  "value when it fails — a mini run that cannot reach it looks like "
                                  "\"nothing there\", not a failure" % (f, node.lineno, name)))
    # 1, one git call for every file: the shallowest ignored folder each join reaches
    asks = set()
    for f, ln, segs, known in ignore_asks:
        for i in range(1, len(known) + 1):
            p = "/".join(known[:i])
            asks.update((p + "/", p))   # `work/` matches a folder git cannot see only as "…/work/"
    ignored = _ignored(sorted(asks), root)
    _, _, has, has_dirs = _local(root)
    seen1 = set(wrote)   # one finding per file:line — a write is "output inside the component"
    for f, ln, segs, known in ignore_asks:
        full = "/".join(known)
        if UNKNOWN not in segs and (full in has or full in has_dirs):
            continue   # a file (or folder) git has: a fresh checkout has it too
        for i in range(1, len(known) + 1):
            p = "/".join(known[:i])
            if p + "/" in ignored or p in ignored:
                where = "%s:%d" % (f, ln)
                if where not in seen1:
                    seen1.add(where)
                    red.append((f, where, "data", "data only on one machine (%s): builds a path into %s, "
                                "which git ignores — a mini run's fresh checkout does not have it" % (where, p)))
                break
    red.sort(key=lambda r: (r[0], int(r[1].rsplit(":", 1)[1])))   # file, then line
    return red, [m for f, ln, m in sorted(amber)]


def lab_run_keys(root):
    try:
        tree = ast.parse((root / JOB_ENV_PY).read_text())
    except (OSError, SyntaxError):
        return None, None
    ceiling, vendor = None, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "JOB_ENV" for t in node.targets):
            if isinstance(node.value, ast.Dict):
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant) and k.value == "lab-run":
                        ceiling = {e.value for e in ast.walk(v) if isinstance(e, ast.Constant)
                                   and isinstance(e.value, str)}
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "VENDOR_KEYS" for t in node.targets):
            vendor = {e.value for e in ast.walk(node.value) if isinstance(e, ast.Constant)
                      and isinstance(e.value, str)}
    return ceiling, vendor


def _looks_key(name, vendor):
    """A name in VENDOR_KEYS, or one ending KEY|TOKEN|SECRET|PASSWORD."""
    return name in vendor or bool(re.search(r"(KEY|TOKEN|SECRET|PASSWORD)$", name))


def key_reads(files, ceiling, vendor, root=None):
    """[(file, line)] sorted by line — file None when the key list could not be read."""
    if ceiling is None:
        return [(None, "the mini's key list (%s) could not be read" % JOB_ENV_PY)]
    out = {}
    for f in files:
        try:
            text = open(_at(root, f), errors="replace").read()
        except OSError:
            continue
        for m in ENV_READ.finditer(text):
            name = m.group(1) or m.group(2)
            if _looks_key(name, vendor) and name not in ceiling:
                out["%s reads %s — the mini does not hand that key to lab runs" % (f, name)] = f
    return [(out[l], l) for l in sorted(out)]


def _guarded_imports(tree):
    """ids of imports in the body of a `try:` whose handler is bare or catches ImportError,
    ModuleNotFoundError or Exception — the code runs on without them. An import inside a
    function defined in that body runs later, outside the try, and is not guarded."""
    def catches(h):
        if h.type is None:
            return True
        types = h.type.elts if isinstance(h.type, ast.Tuple) else [h.type]
        return any((isinstance(t, ast.Name) and t.id in IMPORT_GUARDS)
                   or (isinstance(t, ast.Attribute) and t.attr in IMPORT_GUARDS) for t in types)
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and any(catches(h) for h in node.handlers):
            stack = list(node.body)
            while stack:
                n = stack.pop()
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    out.add(id(n))
                elif not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    stack.extend(ast.iter_child_nodes(n))
    return out


def importers(files, required=None, root=None):
    """{top-level import name: [files importing it]}. `required`, when a set is passed, gets
    every name imported at least once OUTSIDE a guarding try; a name never added is optional."""
    by = {}
    for f in files:
        try:
            text = open(_at(root, f), errors="replace").read()
        except OSError:
            continue
        found, needed = set(), set()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            # a file the 3.9 parser refuses still has its imports listed (plain text)
            found.update(m.group(1) for m in
                         re.finditer(r"^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M))
            needed = set(found)
        else:
            guarded = _guarded_imports(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    names = [node.module.split(".")[0]]
                else:
                    continue
                found.update(names)
                if id(node) not in guarded:
                    needed.update(names)
        for n in found:
            by.setdefault(n, []).append(f)
        if required is not None:
            required.update(needed)
    return by


_LOCAL = None   # (root, names, files, their folders): built once per root


def _local(root):
    """(root, local names, files) for one checkout, asked of git once. files = every file
    under components/ that a fresh checkout has or that you could commit: tracked, plus
    untracked-not-ignored — never a gitignored .venv/, work/ or models/ (LD-43 (new static
    checks) item 0b: a components/<c>/.venv of numpy, cv2 … hid 23 real package REDs).
    names = each of those files' stems and folders, plus every tracked .py stem and
    tracked package folder in the repo."""
    global _LOCAL
    if _LOCAL is None or _LOCAL[0] != str(root):
        out = git("ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "components",
                  cwd=root) or ""
        files = sorted({f for f in out.split("\0") if f})
        local, dirs = set(), set()
        for f in files:
            parts = f.split("/")
            local.update(parts[1:-1])
            local.add(parts[-1][:-3] if parts[-1].endswith(".py") else parts[-1])
            dirs.update("/".join(parts[:i]) for i in range(1, len(parts)))
        for f in (git("ls-files", "-z", "--", "*.py", cwd=root) or "").split("\0"):
            if f:
                p = Path(f)
                local.add(p.stem)
                if p.name == "__init__.py" and len(p.parts) > 1:
                    local.add(p.parent.name)
        _LOCAL = (str(root), local, files, dirs)
    return _LOCAL


def third_party(names, root, c):
    """Names that are neither stdlib (asked of /usr/bin/python3 with site off) nor local files:
    anything git tracks (or could) under components/, plus every tracked .py stem and tracked
    package folder in the repo. A gitignored folder is not local: a mini run never has it."""
    local = _local(root)[1]
    cand = [n for n in names if n not in local]
    if not cand or not os.access(MINI_PY, os.X_OK):
        return cand
    code = ("import importlib.util,json,sys;"
            "print(json.dumps([n for n in sys.argv[1:] if importlib.util.find_spec(n) is None]))")
    p = subprocess.run([MINI_PY, "-I", "-S", "-c", code] + cand, capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except ValueError:
        return cand


def norm(n):
    return re.sub(r"[-_.]+", "-", n).lower()


def _context(root):
    """What every component's check reads the same: the mini's installed list and its key list."""
    inv = None
    if (root / INVENTORY).is_file():
        try:
            inv = json.loads((root / INVENTORY).read_text())
        except ValueError:
            inv = None
    have = {norm(p.get("name", "")) for p in (inv or {}).get("python", {}).get("packages", [])}
    ceiling, vendor = lab_run_keys(root)
    return {"inv": inv, "have": have, "ceiling": ceiling, "vendor": vendor}


def findings(root, component, trace=None):
    """Every check over EVERY runnable file of one component, as the lines main prints
    (no prefixes): {"new_red", "old_red", "amber", "unchecked", "notes"}, each a list of
    strings. A RED is new_red when any file it names is in changed_py's set (uncommitted,
    untracked, or differing from origin/main), else old_red. root is the checkout's top
    folder; nothing here changes folder or fetches — main does the fetch.

    trace=, a trace() result (LD-44 (dry-run trace)): a static path RED whose file:line
    is not in its "reached" moves to amber as "fallback — not reached in the dry run",
    and a sixth key, "trace_red", carries what the dry run opened outside."""
    root = Path(root)
    return _findings(root, component, _context(root), trace)


# the static REDs that name one path at one file:line — what a dry run can show is never reached
PATH_REDS = ("a path on this machine only (", "data only on one machine (")


def _path_where(line):
    for p in PATH_REDS:
        if line.startswith(p):
            return line[len(p):].split(")", 1)[0]
    return None


def _apply_trace(red, amber, notes, t):
    """LD-44 (dry-run trace): the downgrade, in place; returns the trace's own REDs."""
    reached = t.get("reached") or set()
    kept = []
    for names, r in red:
        where = _path_where(r)
        if where is not None and where not in reached:
            amber.append("fallback — not reached in the dry run: " + r)
        else:
            kept.append((names, r))
    red[:] = kept
    out = ["the dry run opened %s" % p for p in t.get("opened") or []]
    if t.get("timed_out"):
        out.append("the dry run did not finish in %d s" % t.get("timeout", TRACE_TIMEOUT))
    elif t.get("exit"):
        amber.append("the dry run exited %d — it stopped early, so \"not reached\" covers only what ran"
                     % t["exit"])
    notes.append("dry run traced: exit %s, %d checkout line(s) reached, %d path(s) opened outside; "
                 "probed, absent here: %d"
                 % (t.get("exit"), len(reached), len(t.get("opened") or []), len(t.get("absent") or [])))
    return out


def _findings(root, c, ctx, trace=None):
    inv, have = ctx["inv"], ctx["have"]
    d = drift(c, root)
    changed = set(changed_py(c, d, root))
    # the component's code is what git has or could have: a .py inside an ignored work/ or
    # models/ is not the component's code (LD-43 (new static checks) item 0b)
    files = [f for f in _local(root)[2]
             if f.startswith("components/%s/" % c) and f.endswith(".py")
             and not any(part.startswith(".") for part in f.split("/"))
             and os.path.isfile(_at(root, f))]
    files = [f for f in files if runs_on_mini(f)]
    red = []   # (the files it names, line)
    red += [((f,) if f else (), "breaks on the mini's Python 3.9.6: " + b) for f, b in compile_39(files, root)]
    red += [((f,), "breaks on the mini's Python 3.9.6: " + b) for f, b in union_hints(files, root)]
    guarded, deliberate = [], {}
    for where, line, shared, fallback in path_literals(files, root):
        if shared:
            continue
        f = where.rsplit(":", 1)[0]
        if f in DELIBERATE:
            deliberate.setdefault(f, []).append(where)
        elif fallback:
            guarded.append(where)
        else:
            red.append(((f,), "a path on this machine only (%s): %s" % (where, line)))
    st_red, st_amber = static_checks(files, root)
    for f, where, kind, x in st_red:
        if kind == "drive" and f in DELIBERATE:   # the Drive finder's own Drive features (item 0)
            deliberate.setdefault(f, []).append(where)
    notes = []
    if guarded:
        notes.append("guarded fallback: %d (%s)" % (len(guarded), ", ".join(guarded[:5])))
    for f in sorted(deliberate):
        notes.append("deliberate: %d — %s" % (len(deliberate[f]), DELIBERATE[f]))
    red += [((f,) if f else (), x) for f, x in key_reads(files, ctx["ceiling"], ctx["vendor"], root)]
    red += [((f,), "shadows the standard library: " + x) for f, x in stdlib_shadows(root, c)]
    red += [((f,), x) for f, where, kind, x in st_red if not (kind == "drive" and f in DELIBERATE)]
    missing, optional = [], []
    required = set()
    by = importers(files, required, root)
    blender = sorted(n for n in by if n in BLENDER_MODULES)
    for n in [x for x in third_party(sorted(by), root, c) if x not in BLENDER_MODULES]:
        dist = norm(ALIASES.get(n, n))
        where = ", ".join(by.get(n, [])[:3])
        if n not in required:
            if inv is None or dist not in have:
                optional.append("%s — optional (imported only inside a try that handles its absence), %s — "
                                "imported by %s" % (n, "not checked (no mini list yet)" if inv is None
                                                    else "not in the mini's installed list", where))
        elif inv is None:
            missing.append((n, "%s — not checked (no mini list yet) — imported by %s" % (n, where)))
        elif dist not in have:
            missing.append((n, "%s — not in the mini's installed list — imported by %s" % (n, where)))
    # a package RED names every file importing it, not only the three it prints
    red += [(tuple(by.get(n, [])), "package " + m) for n, m in missing if "not checked" not in m]
    amber = []
    if d["uncommitted"]:
        amber.append("edited, not committed — the mini runs the old version: " + ", ".join(d["uncommitted"][:8]))
    if d["untracked"]:
        amber.append("new files git does not track — they do not exist in a mini run: " + ", ".join(d["untracked"][:8]))
    if d["only_here_ignored"]:
        amber.append("ignored folders/files that exist only here (a mini run is a fresh checkout): " + ", ".join(d["only_here_ignored"][:8]))
    amber += st_amber
    if d["unpushed"]:
        amber.append("%d commit(s) not pushed — the mini cannot see them: %s" % (len(d["unpushed"]), "; ".join(d["unpushed"][:3])))
    if d["unpulled"]:
        amber.append("%d commit(s) on origin you have not pulled — you are testing older code than the mini runs: %s" % (len(d["unpulled"]), "; ".join(d["unpulled"][:3])))
    unchecked = [m for n, m in missing if "not checked" in m] + optional
    if blender:
        tools = (inv or {}).get("tools", {})
        if "blender" in tools and tools["blender"] and not str(tools["blender"]).startswith("BROKEN"):
            pass   # the mini lists a working Blender
        else:
            unchecked.append("%s — runs inside Blender, not Python; the mini's tool list %s Blender — "
                             "imported by %s" % ("/".join(blender),
                                                 "shows a BROKEN" if "blender" in tools else "does not cover",
                                                 ", ".join(by[blender[0]][:2])))
    trace_red = None if trace is None else _apply_trace(red, amber, notes, trace)
    out = {"new_red": [r for names, r in red if any(n in changed for n in names)],
           "old_red": [r for names, r in red if not any(n in changed for n in names)],
           "amber": amber,
           "unchecked": ["package " + u for u in unchecked],
           "notes": notes}
    if trace_red is not None:
        out["trace_red"] = trace_red
    return out


# ── LD-44 (dry-run trace) ────────────────────────────────────────────────────

TRACE_TIMEOUT = 240
TRACE_ENV = "MINI_COMPARE_TRACE"        # the log of opened paths, one per line
REACHED_ENV = "MINI_COMPARE_REACHED"    # the log of checkout lines run, "file:line"
ROOTS_ENV = "MINI_COMPARE_ROOTS"        # the checkout, so "file" is repo-relative
DRY_RUN = "dry_run"
TRACE_LABEL = "trace"
OUTPUT_TAIL = 40
FIXED_ROOTS = ("/private/var/folders", "/dev", "/System", "/Library/Developer", "/usr")
# Loaded by every Python started with this folder first on PYTHONPATH. Never raises: an
# exception in an audit hook would abort the open it watches.
SITECUSTOMIZE = '''\
# mini-compare --trace, LD-44 (dry-run trace): logs paths opened and checkout lines run
import os
import sys


def _under(p, roots):
    return any(p == r or p.startswith(r + os.sep) for r in roots)


def _own_roots(checkout):
    """LD-44b (trace narrowing): this process's OWN interpreter — its prefixes, the folder
    of its executable and every absolute sys.path entry outside the checkout, each as given
    and as its realpath. Never "/", HOME, a checkout or a folder holding one of them."""
    cand = [sys.prefix, sys.base_prefix, sys.exec_prefix,
            os.path.dirname(os.path.realpath(sys.executable)) if sys.executable else ""]
    cand += [p for p in sys.path if isinstance(p, str) and os.path.isabs(p)]
    tops = [os.path.realpath(r) for r in checkout]
    keep = tops + ([os.path.realpath(os.environ["HOME"])] if os.environ.get("HOME") else [])
    out = []
    for c in cand:
        try:
            forms = (os.path.abspath(c), os.path.realpath(c)) if c else ()
        except Exception:
            continue
        if any(_under(f, tops) for f in forms) or any(_under(k, forms) for k in keep):
            continue
        for f in forms:
            if f != os.sep and f not in out:
                out.append(f)
    return out


def _mini_compare_trace():
    log = os.environ.get("%(trace)s")
    if not log or not hasattr(sys, "addaudithook"):
        return
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    fd = os.open(log, flags, 0o600)
    seen = set()
    roots = [r for r in os.environ.get("%(roots)s", "").split(os.pathsep) if r]
    own = _own_roots(roots)

    def hook(event, args):
        if event not in ("open", "os.listdir", "os.scandir"):
            return
        try:
            p = args[0] if args else None
            if p is None and event != "open":
                p = "."
            if p is None or isinstance(p, int):
                return
            p = os.path.abspath(os.fsdecode(p))
            if p not in seen:
                seen.add(p)
                if _under(p, own) or _under(os.path.realpath(p), own):
                    return
                os.write(fd, (p + "\\n").encode("utf-8", "surrogateescape"))
        except Exception:
            pass

    sys.addaudithook(hook)
    rlog = os.environ.get("%(reached)s")
    if not rlog or not roots:
        return
    rfd = os.open(rlog, flags, 0o600)
    rel, done = {}, set()

    def where(fn):
        if fn in rel:
            return rel[fn]
        got = None
        if fn and not fn.startswith("<"):
            for cand in (os.path.abspath(fn), os.path.realpath(fn)):
                for r in roots:
                    if cand.startswith(r + os.sep):
                        got = cand[len(r) + 1:]
                        break
                if got:
                    break
        rel[fn] = got
        return got

    def local(frame, event, arg):
        if event == "line":
            try:
                key = (frame.f_code.co_filename, frame.f_lineno)
                if key not in done:
                    done.add(key)
                    w = where(key[0])
                    if w:
                        os.write(rfd, ("%%s:%%d\\n" %% (w, key[1])).encode("utf-8", "surrogateescape"))
            except Exception:
                pass
        return local

    def call(frame, event, arg):
        try:
            return local if event == "call" and where(frame.f_code.co_filename) else None
        except Exception:
            return None

    sys.settrace(call)
    import threading
    threading.settrace(call)


_mini_compare_trace()
''' % {"trace": TRACE_ENV, "reached": REACHED_ENV, "roots": ROOTS_ENV}


def _mini_run():
    """run-kit's mini_run (row_of, door_of, checked_args), imported only when a trace asks."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    import mini_run
    return mini_run


def _has_dry_run(mr, root, row, kind, door, args):
    if kind == "lab_door":
        route, _ = mr.lab_door.pick(door, args)
        return DRY_RUN in route["flags"] or DRY_RUN in route["bool_flags"]
    if kind == "accepts":
        return DRY_RUN in door
    return DRY_RUN in mr.script_flags(root / row["script"])


def _default_brand(root):
    """No --brand: the first brand folder in the checkout, else the label word."""
    found = sorted(p.name for p in (root / "brands").iterdir()
                   if p.is_dir() and not p.name.startswith((".", "_"))) if (root / "brands").is_dir() else []
    return found[0] if found else TRACE_LABEL


def trace_plan(root, component, brand=None, args=None):
    """The dry run the worker would start, checked — every refusal before anything runs.
    Raises mini_run.Refused: no grant row, a door that does not load, a door with no
    dry_run, an argument the door refuses, no /usr/bin/python3."""
    mr = _mini_run()
    root = Path(root).resolve()
    row = mr.row_of(root, component)
    args = {str(k): str(v) for k, v in (args or {}).items()}
    if args.get(DRY_RUN, "yes").strip().lower() not in mr.lab_door.YES:
        raise mr.Refused("the trace runs a door only with dry_run=yes")
    args[DRY_RUN] = "yes"
    try:
        kind, door = mr.door_of(root, row)
        if not _has_dry_run(mr, root, row, kind, door, args):
            raise mr.Refused("no dry run door: the trace is skipped")
        brand = brand or _default_brand(root)
        if mr.checked_args(root, row, kind, door, args, brand) and "label" not in args:
            args["label"] = TRACE_LABEL
    except mr.lab_door.Refused as e:
        raise mr.Refused(str(e))
    if not os.access(MINI_PY, os.X_OK):
        raise mr.Refused("%s is not on this machine — the trace runs the door on it" % MINI_PY)
    script = root / row["script"]
    if not script.is_file():
        raise mr.Refused("%s is not in this checkout" % row["script"])
    argv = []
    for name in sorted(args):   # platform/workers/mini-worker/lab_run.py _args(): sorted pairs
        argv += ["--" + name, args[name]]
    return {"root": root, "component": component, "brand": brand, "args": args,
            "argv": [MINI_PY, str(script)] + argv}


def _child_env(root, brand, out, hook, log, reached):
    """This process's environment, every key-shaped name outside the mini's lab-run
    ceiling removed (the mini's own hand-out, never more), set as the worker sets it."""
    ceiling, vendor = lab_run_keys(root)
    ceiling, vendor = ceiling or set(), vendor or set()
    env = {k: v for k, v in os.environ.items() if k in ceiling or not _looks_key(k, vendor)}
    env.update({"BRAND": brand, "OUT": str(out), "AI_WORKSPACE": str(root),
                "DRIVE_MOUNT": "off",   # job_env.py: every worker spawn, LD-26 (mount switch)
                TRACE_ENV: str(log), REACHED_ENV: str(reached), ROOTS_ENV: str(root)})
    env["PYTHONPATH"] = os.pathsep.join([str(hook)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    return env


def _interpreter_dirs(env):
    """MINI_PY's own prefixes, site-packages folders and .pyc cache (as the child's HOME
    names them). Apple's /usr/bin/python3 keeps its stdlib .pyc files under
    ~/Library/Caches/com.apple.python (sys.pycache_prefix): the interpreter's, not the door's."""
    code = ("import json,site,sys;print(json.dumps([sys.prefix,sys.base_prefix,sys.exec_prefix]"
            "+list(site.getsitepackages())+[site.getusersitepackages(),"
            "getattr(sys,'pycache_prefix',None) or '']))")
    # not -I: Apple's site sets pycache_prefix only in a normal start; the hook stays off
    env = {k: v for k, v in env.items() if k not in (TRACE_ENV, REACHED_ENV, ROOTS_ENV, "PYTHONPATH")}
    try:
        p = subprocess.run([MINI_PY, "-c", code], capture_output=True, text=True, env=env,
                           cwd="/", timeout=30)
        return [str(x) for x in json.loads(p.stdout) if x]
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def _shared_assets(root):
    """The Shared Assets mount brandpath's drive_index.mount() answers here, or None."""
    f = root / "components" / "brandpath" / "drive_index.py"
    if not f.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("mini_compare_drive_index", str(f))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        m = mod.mount()
    except Exception:
        return None
    return str(m) if m else None


def allowed_roots(root, out, base, interpreter=()):
    """Where a dry run may open: the checkout, its OUT, the trace's temp dir, the temp
    folder, the interpreter's own folders, /dev, /System, /Library/Developer, /usr and a
    Shared Assets mount — each as its real path."""
    import site
    cand = [str(root), str(out), str(base), tempfile.gettempdir(), sys.prefix, sys.base_prefix,
            sys.exec_prefix, getattr(sys, "pycache_prefix", None) or ""] + list(FIXED_ROOTS) + list(interpreter)
    try:
        cand += list(site.getsitepackages())
    except AttributeError:
        pass
    sa = _shared_assets(Path(root))
    if sa:
        cand.append(sa)
    out_roots = []
    for c in cand:
        r = os.path.realpath(c) if c else ""
        if r and r != "/" and r not in out_roots:
            out_roots.append(r)
    return out_roots


def _inside(path, roots):
    rp = os.path.realpath(path)
    return any(rp == r or rp.startswith(r + "/") for r in roots)


def _read_lines(p):
    try:
        with open(str(p), encoding="utf-8", errors="replace") as fh:
            return [l.rstrip("\n") for l in fh if l.strip()]
    except OSError:
        return []


def run_trace(plan, timeout=TRACE_TIMEOUT):
    """Runs a trace_plan() under the hook; everything it writes is under one temp dir,
    removed after. {"opened", "absent", "reached", "exit", "timed_out", "timeout", "output", "argv"}."""
    root = plan["root"]
    base = Path(tempfile.mkdtemp(prefix="mini-compare-trace-"))
    try:
        hook, out = base / "hook", base / "out"
        hook.mkdir()
        out.mkdir()
        (hook / "sitecustomize.py").write_text(SITECUSTOMIZE)
        log, reached = base / "opened.log", base / "reached.log"
        env = _child_env(root, plan["brand"], out, hook, log, reached)
        roots = allowed_roots(root, out, base, _interpreter_dirs(env))
        p = subprocess.Popen(plan["argv"], cwd=str(root), env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        timed_out = False
        try:
            output, _ = p.communicate(timeout=timeout)
            code = p.returncode
        except subprocess.TimeoutExpired:
            timed_out, code = True, 124
            try:
                os.killpg(p.pid, signal.SIGKILL)   # the door and every child it started
            except OSError:
                p.kill()
            try:
                output, _ = p.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                output = b""
        text = (output or b"").decode("utf-8", "replace")
        outside = sorted({x for x in _read_lines(log) if not _inside(x, roots)})
        # LD-44b (trace narrowing): a path that is not there after the run was a probe, not a dependency
        opened = [x for x in outside if os.path.lexists(x)]
        absent = [x for x in outside if not os.path.lexists(x)]
        return {"opened": opened, "absent": absent, "reached": set(_read_lines(reached)), "exit": int(code),
                "timed_out": timed_out, "timeout": timeout,
                "output": text.splitlines()[-OUTPUT_TAIL:], "argv": plan["argv"]}
    finally:
        shutil.rmtree(str(base), ignore_errors=True)   # the trace's own temp dir only


def trace(root, component, brand=None, args=None, timeout=TRACE_TIMEOUT):
    """The component's mini dry run, here, under the hook: {"opened": [abs paths outside
    the allowed roots that exist], "absent": [those that do not — probes], "reached":
    {"file:line", ...} the run executed, "exit": int, ...}.
    Raises mini_run.Refused before anything runs (see trace_plan)."""
    return run_trace(trace_plan(root, component, brand, args), timeout)


def _trace_main(root, argv):
    """`<component> --trace [--brand B] [--detail] [name=value ...]`: one component."""
    mr = _mini_run()
    names, pairs, brand, detail = [], [], None, False
    rest = [a for a in argv if a != "--trace"]
    i = 0
    while i < len(rest):
        a = rest[i]
        if a == "--brand":
            if i + 1 >= len(rest):
                print("mini-compare --trace: --brand needs a brand name")
                return 2
            brand, i = rest[i + 1], i + 2
            continue
        if a.startswith("--brand="):
            brand = a.split("=", 1)[1]
        elif a == "--detail":
            detail = True
        elif a in ("--full", "--all"):
            pass
        elif a.startswith("-"):
            print("mini-compare --trace: %s is not a --trace option" % a)
            return 2
        elif "=" in a:
            pairs.append(a)
        else:
            names.append(a)
        i += 1
    if len(names) != 1:
        print("mini-compare --trace: name exactly one component (got %d)" % len(names))
        return 2
    try:
        plan = trace_plan(root, names[0], brand, mr.parse_pairs(pairs))
    except mr.Refused as e:
        print("mini-compare --trace: %s" % e)
        return 2
    c = names[0]
    fetched = git("fetch", "-q", "origin", cwd=root) is not None
    ctx = _context(root)
    _header(root, fetched, ctx)
    print("dry run (LD-44 (dry-run trace)): %s" % " ".join(plan["argv"]))
    print("  BRAND=%s, OUT a temp folder, cwd %s, killed at %d s\n" % (plan["brand"], root, TRACE_TIMEOUT))
    t = run_trace(plan)
    print("its output (last %d lines, exit %d):" % (OUTPUT_TAIL, t["exit"]))
    for l in t["output"]:
        print("  | " + l)
    print()
    _section(root, c, _findings(root, c, ctx, t), detail)
    return 0


def _header(root, fetched, ctx):
    person, email = who_am_i(root)
    inv = ctx["inv"]
    print("mini-compare — this machine vs what a mini run gets (origin/main%s)"
          % ("" if fetched else ", NOT FETCHED — origin may be stale"))
    print("you: %s (%s)" % (person or "UNMATCHED — mini-run would refuse this email", email))
    print("mini's installed list: %s\n" % (("as of " + str(inv.get("as_of"))) if inv else
          "not published yet (WM-162 (mini inventory)) — package checks say 'not checked'"))


def _section(root, c, f, detail):
    red = f["new_red"] + f["old_red"] + f.get("trace_red", [])
    verdict = "WON'T RUN THE SAME" if red else ("DIFFERENT CODE" if f["amber"] else
                                                ("NOT FULLY CHECKED" if f["unchecked"] else "SAME"))
    print("== %s — %s" % (c, verdict))
    for r in f.get("trace_red", []) + f["new_red"]:
        print("  RED    " + r)
    if f["old_red"]:
        print("  ALREADY IN THE CODE: %d RED" % len(f["old_red"]))
        if detail:
            for r in f["old_red"]:
                print("  RED    " + r)
    for a in f["amber"]:
        print("  AMBER  " + a)
    for u in f["unchecked"]:
        print("  ?      " + u)
    for n in f["notes"]:
        print("  NOTE   " + n)
    ds = deps(root, c)
    dirty = [x for x in ds if any(drift(x, root).values())]
    if dirty:
        print("  NOTE   it names other components that also differ here (inferred dependency): " + ", ".join(dirty))
    print()


def main(argv):
    root = Path(git("rev-parse", "--show-toplevel").strip())
    os.chdir(str(root))
    if "--trace" in argv:   # LD-44 (dry-run trace)
        return _trace_main(root, argv)
    show_all = "--all" in argv
    detail = "--detail" in argv
    # --full is accepted and ignored: every run checks every runnable file (LD-42 (full check default))
    wanted = [a for a in argv if not a.startswith("--")]
    fetched = git("fetch", "-q", "origin", cwd=root) is not None
    ctx = _context(root)
    _header(root, fetched, ctx)

    shown = []
    for c in wanted or components(root):
        if not (root / "components" / c).is_dir():
            print("%s: no such component\n" % c)
            continue
        f = _findings(root, c, ctx)
        if any(f.values()) or show_all:
            shown.append((c, f))
            if wanted:
                _section(root, c, f, detail)
    if not wanted:   # one line per component, worst first: new, then already, then name
        shown.sort(key=lambda x: (-len(x[1]["new_red"]), -len(x[1]["old_red"]), x[0]))
        for c, f in shown:
            print("%s  new %d  already %d  amber %d" % (c, len(f["new_red"]), len(f["old_red"]), len(f["amber"])))
        if shown:
            print()
        if detail:
            for c, f in shown:
                _section(root, c, f, detail)
    if not shown:
        print("No differences: every component%s here matches what a mini run gets.\n"
              "A dry run on the mini is still the last proof — a path built at runtime is invisible to this check."
              % ("" if not wanted else " named"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
