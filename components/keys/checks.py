#!/usr/bin/env python3
"""SI-196 (key checks report-only) — two checks over the key NAMES, never a value.

    python3 components/keys/checks.py [--root <repo>]

REPORT-ONLY (G-A2): it prints findings and ALWAYS exits 0 — findings, a
missing file, a failed import, a crash and a bad flag included. Making either
check blocking needs a later word, not an edit here.

Check 1 TEMPLATE vs SCOPE. Every bare NAME line of
platform/workers/mini-worker/env.template (a line holding one NAME and nothing
else; a `{PLACEHOLDER}` suffix is kept as written) that is a CREDENTIAL —
in job_env.VENDOR_KEYS, starting with a job_env.VENDOR_KEY_PREFIXES entry, ending
_KEY, _TOKEN, _SECRET, _KEY_ID or _KEY_SECRET, or named DATABASE_URL or *_DB_URL —
is reported when job_env.is_vendor_key(name) is False: a key the template
documents that scoped_env() would hand to every spawn. Non-credential settings
(locks, timeouts, caps) are skipped. job_env.py is imported read-only by path;
if that fails the check says "check 1 not run" and check 2 goes on with the
suffix rules alone.

Check 2 KEYS ON A COMMAND LINE. A static scan (ast) of components/**/*.py,
skipping tests (test_*.py, *_test.py, conftest.py, tests/ and test/ dirs),
archive/, __pycache__ and dot-dirs. A finding is a subprocess / os / asyncio
spawn whose ARGV carries a credential read: os.environ[NAME],
os.environ.get(NAME), os.getenv(NAME), a key(NAME) / get(NAME) call, a local
name assigned from one, or an f-string / + / % / .format() / str() / list built
from one. env= is never argv — handing a key over in the child's environment
is the safe form and is not flagged; nor is a value passed through any other
call first (pg_argv.for_psql's shape). Taint is per function scope, flow-
insensitive. A file that does not parse under this interpreter is counted as
skipped, never read further.

Every finding is path:line and the NAME. Stdlib only, Python 3.9-clean.
"""

import argparse
import ast
import importlib.util
import os
import re
import sys
import warnings
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path("platform/workers/mini-worker/env.template")
JOB_ENV = Path("platform/workers/mini-worker/job_env.py")

CRED_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "_KEY_ID", "_KEY_SECRET", "_DB_URL")
CRED_EXACT = ("DATABASE_URL",)
BARE_NAME = re.compile(r"^([A-Z][A-Z0-9_]*(?:\{[A-Za-z0-9_]+\})?)\s*$")

# Spawns, by dotted name once import aliases are resolved. The value is the
# positional indexes that are NOT argv (an env mapping), or None for "all
# positionals are argv". subprocess.* takes argv only from args[0] / args=.
SUBPROCESS_FIRST_ONLY = frozenset({
    "subprocess.run", "subprocess.call", "subprocess.check_call",
    "subprocess.check_output", "subprocess.Popen", "subprocess.getoutput",
    "subprocess.getstatusoutput", "os.system", "os.popen",
    "asyncio.create_subprocess_shell",
})
ALL_POSITIONALS = frozenset({
    "os.execl", "os.execlp", "os.execv", "os.execvp",
    "os.spawnl", "os.spawnlp", "os.spawnv", "os.spawnvp",
    "asyncio.create_subprocess_exec",
})
LAST_IS_ENV = frozenset({
    "os.execle", "os.execlpe", "os.execve", "os.execvpe",
    "os.spawnle", "os.spawnlpe", "os.spawnve", "os.spawnvpe",
})
THIRD_IS_ENV = frozenset({"os.posix_spawn", "os.posix_spawnp"})

READ_CALLS = frozenset({"getenv", "get", "key"})
SKIP_DIRS = frozenset({"archive", "__pycache__", "tests", "test", "node_modules"})


def load_job_env(root):
    """job_env as a module, or (None, reason). Never registered in sys.modules."""
    path = root / JOB_ENV
    if not path.is_file():
        return None, "job_env.py not found at %s" % JOB_ENV
    try:
        spec = importlib.util.spec_from_file_location("_si196_job_env", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.is_vendor_key  # noqa: B018 — the one attribute check 1 needs
    except Exception as e:  # report-only: any failure is a line, never a crash
        return None, "job_env import failed (%s)" % type(e).__name__
    return mod, None


def is_credential(name, job_env=None):
    if job_env is not None:
        if name in getattr(job_env, "VENDOR_KEYS", ()):
            return True
        for p in getattr(job_env, "VENDOR_KEY_PREFIXES", ()):
            if name.startswith(p):
                return True
    return name in CRED_EXACT or name.endswith(CRED_SUFFIXES)


# ---- check 1 ---------------------------------------------------------------

def template_names(path):
    """[(line_no, NAME)] for each bare NAME line."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            m = BARE_NAME.match(line)
            if m:
                out.append((n, m.group(1)))
    return out


def check_template(root, job_env, job_env_error):
    """(findings, not_run_reason). findings = [(path, line, NAME)]."""
    if job_env is None:
        return [], job_env_error
    path = root / TEMPLATE
    if not path.is_file():
        return [], "env.template not found at %s" % TEMPLATE
    findings = []
    for line, name in template_names(path):
        if is_credential(name, job_env) and not job_env.is_vendor_key(name):
            findings.append((str(TEMPLATE), line, name))
    return findings, None


# ---- check 2 ---------------------------------------------------------------

def _aliases(tree):
    """local name -> dotted name, from this file's imports."""
    names = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names[a.asname or a.name.split(".")[0]] = (
                    a.name if a.asname else a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for a in node.names:
                names[a.asname or a.name] = node.module + "." + a.name
    return names


def _dotted(expr, aliases):
    parts = []
    while isinstance(expr, ast.Attribute):
        parts.append(expr.attr)
        expr = expr.value
    if not isinstance(expr, ast.Name):
        return None
    parts.append(aliases.get(expr.id, expr.id))
    return ".".join(reversed(parts))


def _const_str(expr):
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    return None


def _is_environ(expr):
    return ((isinstance(expr, ast.Attribute) and expr.attr == "environ")
            or (isinstance(expr, ast.Name) and expr.id == "environ"))


class _Scan:
    def __init__(self, job_env):
        self.job_env = job_env

    def read_name(self, expr):
        """The credential NAME `expr` reads directly from the environment."""
        if isinstance(expr, ast.Subscript) and _is_environ(expr.value):
            name = _const_str(expr.slice)
        elif isinstance(expr, ast.Call) and expr.args:
            f = expr.func
            attr = f.attr if isinstance(f, ast.Attribute) else (
                f.id if isinstance(f, ast.Name) else None)
            name = _const_str(expr.args[0]) if attr in READ_CALLS else None
        else:
            name = None
        if name and is_credential(name, self.job_env):
            return name
        return None

    def carries(self, expr, tainted):
        """The credential NAME this expression's value is built from, or None."""
        if expr is None:
            return None
        hit = self.read_name(expr)
        if hit:
            return hit
        if isinstance(expr, ast.Name):
            return tainted.get(expr.id)
        if isinstance(expr, ast.JoinedStr):
            subs = expr.values
        elif isinstance(expr, ast.FormattedValue):
            subs = [expr.value]
        elif isinstance(expr, ast.BinOp) and isinstance(expr.op, (ast.Add, ast.Mod)):
            subs = [expr.left, expr.right]
        elif isinstance(expr, (ast.List, ast.Tuple, ast.Set)):
            subs = expr.elts
        elif isinstance(expr, ast.Starred):
            subs = [expr.value]
        elif isinstance(expr, ast.IfExp):
            subs = [expr.body, expr.orelse]
        elif isinstance(expr, ast.BoolOp):
            subs = expr.values
        elif isinstance(expr, ast.Subscript):
            subs = [expr.value]
        elif isinstance(expr, ast.Call):
            f = expr.func
            if isinstance(f, ast.Attribute) and f.attr == "format":
                subs = [f.value] + list(expr.args) + [k.value for k in expr.keywords]
            elif isinstance(f, ast.Name) and f.id == "str":
                subs = list(expr.args)
            else:
                return None  # any other call is a transform we do not follow
        else:
            return None
        for s in subs:
            hit = self.carries(s, tainted)
            if hit:
                return hit
        return None


def _scope_nodes(scope):
    """Every node in `scope`, not descending into nested function bodies."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _targets(node):
    """(target names, value) for an assignment-like statement."""
    if isinstance(node, ast.Assign):
        tgts, value = node.targets, node.value
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        tgts, value = [node.target], node.value
    elif isinstance(node, ast.NamedExpr):
        tgts, value = [node.target], node.value
    elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
          and node.func.attr in ("append", "extend", "insert")
          and isinstance(node.func.value, ast.Name)):
        tgts, value = [node.func.value], ast.List(elts=list(node.args), ctx=ast.Load())
    else:
        return [], None
    names = []
    for t in tgts:
        for n in ast.walk(t):
            if isinstance(n, ast.Name):
                names.append(n.id)
    return names, value


def _argv_exprs(dotted, call):
    pos = list(call.args)
    if dotted in SUBPROCESS_FIRST_ONLY:
        argv = pos[:1]
    elif dotted in ALL_POSITIONALS:
        argv = pos
    elif dotted in LAST_IS_ENV:
        argv = pos[:-1]
    elif dotted in THIRD_IS_ENV:
        argv = pos[:2]
    else:
        return None
    argv += [k.value for k in call.keywords if k.arg in ("args", "argv", "cmd")]
    return argv


def scan_source(source, relpath, job_env):
    """[(relpath, line, NAME)] for one file's text. Raises SyntaxError."""
    with warnings.catch_warnings():  # another file's bad escapes are not ours to print
        warnings.simplefilter("ignore")
        tree = ast.parse(source)
    aliases = _aliases(tree)
    scan = _Scan(job_env)
    findings = []
    scopes = [tree] + [n for n in ast.walk(tree)
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for scope in scopes:
        nodes = list(_scope_nodes(scope))
        tainted = {}
        changed = True
        while changed:  # fixed point over the scope's assignments
            changed = False
            for node in nodes:
                names, value = _targets(node)
                if not names:
                    continue
                hit = scan.carries(value, tainted)
                if hit:
                    for n in names:
                        if n not in tainted:
                            tainted[n] = hit
                            changed = True
        for node in nodes:
            if not isinstance(node, ast.Call):
                continue
            dotted = _dotted(node.func, aliases)
            argv = _argv_exprs(dotted, node) if dotted else None
            for expr in argv or ():
                hit = scan.carries(expr, tainted)
                if hit:
                    findings.append((relpath, node.lineno, hit))
                    break
    return sorted(set(findings), key=lambda f: (f[0], f[1], f[2]))


def _skip_file(name):
    return (name.startswith("test_") or name.endswith("_test.py")
            or name == "conftest.py")


def check_argv(root, job_env):
    """(findings, skipped relpaths) over components/**/*.py."""
    base = root / "components"
    findings, skipped = [], []
    if not base.is_dir():
        return findings, skipped
    for dirpath, dirnames, filenames in os.walk(str(base)):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(filenames):
            if not fn.endswith(".py") or _skip_file(fn):
                continue
            full = Path(dirpath) / fn
            rel = full.relative_to(root).as_posix()
            try:
                with open(str(full), encoding="utf-8") as fh:
                    source = fh.read()
                findings.extend(scan_source(source, rel, job_env))
            except (SyntaxError, UnicodeDecodeError, ValueError, OSError):
                skipped.append(rel)
    return findings, skipped


# ---- report ----------------------------------------------------------------

def report(root, out=None):
    out = out or sys.stdout
    w = lambda s="": out.write(s + "\n")  # noqa: E731
    job_env, err = load_job_env(root)
    w("keys checks (SI-196) — REPORT-ONLY (G-A2): findings never fail this run; exit is always 0.")
    w("root: %s" % root)
    w()
    c1, not_run = check_template(root, job_env, err)
    if not_run:
        w("== Check 1 — template vs scope: not run ==")
        w("check 1 not run — %s" % not_run)
    else:
        w("== Check 1 — template vs scope: %d finding(s) ==" % len(c1))
        w("  (a credential NAME in env.template that job_env.is_vendor_key() does not hold back)")
        for path, line, name in c1:
            w("%s:%d  %s" % (path, line, name))
        if not c1:
            w("none")
    w()
    c2, skipped = check_argv(root, job_env)
    w("== Check 2 — keys on a command line: %d finding(s) ==" % len(c2))
    w("  (a spawn whose argv carries a credential read; env= is not argv)")
    if job_env is None:
        w("  (job_env unavailable — credential names matched by suffix rules only)")
    for path, line, name in c2:
        w("%s:%d  %s" % (path, line, name))
    if not c2:
        w("none")
    if skipped:
        w("skipped, did not parse under Python %d.%d: %d file(s)"
          % (sys.version_info[0], sys.version_info[1], len(skipped)))
        for rel in skipped:
            w("  %s" % rel)
    return c1, c2


def main(argv=None):
    try:
        ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
        ap.add_argument("--root", default=str(DEFAULT_ROOT),
                        help="repo root (default: this file's checkout)")
        args = ap.parse_args(argv)
        report(Path(args.root).resolve())
    except SystemExit as e:
        if e.code not in (0, None):
            print("keys checks: bad arguments — nothing checked (report-only, exit 0)")
    except Exception as e:  # report-only: a crash is a line, never an exit code
        print("keys checks crashed (%s) — nothing more checked (report-only, exit 0)"
              % type(e).__name__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
