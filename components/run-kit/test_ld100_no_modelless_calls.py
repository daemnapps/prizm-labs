#!/usr/bin/env python3
"""python3 test_ld100_no_modelless_calls.py — LD-100 (chain model explicit): the repo check that
refuses a new `claude -p` argv naming no model. Scans components/**/*.py and
platform/workers/**/*.py (tests, .venv and site-packages left out) for every list whose
"-p" follows a claude command, and fails naming path:line for each one that has no
"--model", no model_args(), no starred argument list that names "--model", and no
`argv += ["--model", ...]` after it. The door (run_kit/claude_door.py) adds the model itself;
its own argv starts with binary() and is tested in test_ld100_model_args.py.
Stdlib unittest, no network, no model call."""
import ast
import sys
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GLOBS = ("components", "platform/workers")
SKIP_PARTS = {".venv", "venv", "site-packages", "node_modules", "__pycache__", "tests", "test"}


def _is_test(path):
    n = path.name
    return n.startswith("test_") or n.endswith("_test.py") or n == "conftest.py"


def files():
    for g in GLOBS:
        for p in sorted((ROOT / g).rglob("*.py")):
            rel = p.relative_to(ROOT)
            if SKIP_PARTS & set(rel.parts[:-1]) or _is_test(p):
                continue
            yield p


def _src(src, node):
    return ast.get_source_segment(src, node) or ""


def _names_model(src, node):
    """True when an argv element names the model."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value == "--model" or node.value.startswith("--model=")
    return "model_args(" in _src(src, node)


def _list_names_model(src, node):
    return isinstance(node, (ast.List, ast.Tuple)) and any(_names_model(src, e) for e in node.elts)


class _Scope(ast.NodeVisitor):
    """Per function (and the module): what each name is assigned, and what is added to it."""

    def __init__(self):
        self.assigned, self.added = {}, {}

    def visit_Assign(self, node):
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.assigned.setdefault(t.id, []).append(node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        if isinstance(node.target, ast.Name) and isinstance(node.op, ast.Add):
            self.added.setdefault(node.target.id, []).append(node.value)
        self.generic_visit(node)

    def visit_Call(self, node):
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "extend" and isinstance(f.value, ast.Name) and node.args:
            self.added.setdefault(f.value.id, []).append(node.args[0])
        self.generic_visit(node)


def _scopes(tree):
    """{node id: (enclosing scope's _Scope, module _Scope)} for every list in the tree."""
    module = _Scope()
    module.visit(tree)
    out = {}

    def walk(node, scope):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                s = _Scope()
                s.visit(child)
                walk(child, s)
            else:
                if isinstance(child, (ast.List, ast.Tuple)):
                    out[id(child)] = scope
                walk(child, scope)

    walk(tree, module)
    return out, module


def _claude_like(src, node, scopes):
    text = _src(src, node).lower()
    if "claude" in text:
        return True
    if isinstance(node, ast.Name):
        return any("claude" in _src(src, v).lower() for s in scopes for v in s.assigned.get(node.id, []))
    return False


def _parent_target(tree):
    """{list node id: the Name it is assigned to}, for `argv = [...]` statements."""
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, (ast.List, ast.Tuple)):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[id(n.value)] = t.id
    return out


def scan_source(src, name="<src>"):
    """[path:line] for every claude -p argv in `src` that names no model."""
    tree = ast.parse(src)
    scopes, module = _scopes(tree)
    targets = _parent_target(tree)
    found = []
    for n in ast.walk(tree):
        if not isinstance(n, (ast.List, ast.Tuple)):
            continue
        idx = [i for i, e in enumerate(n.elts) if isinstance(e, ast.Constant) and e.value == "-p"]
        if not idx or idx[0] == 0:
            continue
        local = scopes.get(id(n), module)
        both = (local, module)
        if not _claude_like(src, n.elts[idx[0] - 1], both):
            continue
        if any(_names_model(src, e) for e in n.elts):
            continue
        starred = [e.value.id for e in n.elts if isinstance(e, ast.Starred) and isinstance(e.value, ast.Name)]
        if any(_list_names_model(src, v) for s in both for nm in starred for v in s.assigned.get(nm, [])):
            continue
        var = targets.get(id(n))
        if var and any(_list_names_model(src, v) or "model_args(" in _src(src, v)
                       for s in both for v in s.added.get(var, [])):
            continue
        found.append("%s:%d" % (name, n.lineno))
    return found


def scan_repo():
    out = []
    for p in files():
        try:
            src = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")      # other files' escape-sequence warnings are not ours
                out += scan_source(src, str(p.relative_to(ROOT)))
        except SyntaxError:
            continue
    return out


class NoModellessCalls(unittest.TestCase):
    def test_repo_has_none(self):
        bad = scan_repo()
        self.assertEqual(bad, [], "claude -p with no model (LD-100 (chain model explicit)) — "
                                  "add *model_args() from run_kit.claude_flags right after \"-p\":\n  "
                                  + "\n  ".join(bad))

    def test_scan_reaches_the_known_sites(self):
        # the scan must actually see the call sites it guards, or a green run means nothing
        rels = {str(p.relative_to(ROOT)) for p in files()}
        for site in ("components/swipe-organic/app.py", "tools/video-teardown/machine/run.py",
                     "platform/workers/mini-worker/worker.py", "platform/workers/slack-pusher/push.py"):
            self.assertIn(site, rels)


class TheCheckCatches(unittest.TestCase):
    """The fixtures live here, in the test file."""

    def test_bare_call_is_caught(self):
        src = 'import subprocess\nsubprocess.run(["claude", "-p", prompt, "--output-format", "json"])\n'
        self.assertEqual(scan_source(src, "x.py"), ["x.py:2"])

    def test_named_variable_is_caught(self):
        src = 'import shutil\nCLAUDE = shutil.which("claude")\ndef f(p):\n    return [CLAUDE, "-p", p]\n'
        self.assertEqual(scan_source(src, "x.py"), ["x.py:4"])

    def test_model_named_passes(self):
        for argv in ('["claude", "-p", "--model", m]', '["claude", "-p", "--model=claude-opus-5-5"]',
                     '["claude", "-p", *model_args(), p]',
                     '["claude", "-p", *([] if "--model" in a else model_args()), *a]'):
            self.assertEqual(scan_source("x = %s\n" % argv), [], argv)

    def test_starred_list_naming_model_passes(self):
        src = 'def f(m, p):\n    args = ["--model", m, "--output-format", "json"]\n    return ["claude", "-p", *args]\n'
        self.assertEqual(scan_source(src), [])

    def test_starred_parameter_is_caught(self):
        src = 'def f(args):\n    return ["claude", "-p", *args]\n'
        self.assertEqual(scan_source(src, "x.py"), ["x.py:2"])

    def test_model_added_after_passes(self):
        src = 'def f(p, mdl):\n    args = ["claude", "-p", p]\n    if mdl:\n        args += ["--model", mdl]\n    return args\n'
        self.assertEqual(scan_source(src), [])

    def test_other_dash_p_ignored(self):
        src = 'a = ["xattr", "-p", "k", f]\nb = ["git", "cat-file", "-p", sha]\nc = [str(SANDBOX), "-p", prof]\n'
        self.assertEqual(scan_source(src), [])


if __name__ == "__main__":
    unittest.main()
