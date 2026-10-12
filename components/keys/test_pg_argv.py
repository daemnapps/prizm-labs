#!/usr/bin/env python3
"""WM-108b (other argv sites) — the one psql-argv helper, and a repo scan.

Declared test for card WM-108b. PURE PYTHON: no network, no database, no psql.

  (a) split_password — WM-108 (no argv credential)'s cases, now against the
      shared module: userinfo, `?password=`, both (userinfo wins), none,
      query order kept, fragment kept.
  (b) for_psql       — PGPASSWORD only when a password was found; the
      caller's dict unchanged; env=None starts from a COPY of os.environ.
  (c) REPO SCAN      — every *.py under the repo root (skipping .git,
      node_modules, __pycache__, .claude and test_* files): no
      `subprocess.run(` / `subprocess.Popen(` whose argv list literal starts
      with "psql" (or a bare name `psql`) and passes, second, a bare name not
      bound from `for_psql(...)` in the same function or one enclosing it.
      Read with `ast`, never a regex. PINNED holds the known exceptions by
      exact path; a pin that no longer offends FAILS (the list only shrinks —
      the 2026-09-26 pinned-by-name ruling).

Every fixture URL is built by string concatenation, never written as one
literal: the repo's wall scanner refuses a literal URL carrying a password,
and these are fake credentials, not keys.

Run: python3 components/keys/test_pg_argv.py
"""
import ast
import os
import sys
import unittest
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import pg_argv  # noqa: E402

SCHEME = "postgresql" + "://"
USER = "plane_rw"
HOSTPORT = "db.example.internal:6543"
PATH = "/postgres"
QUERY = "sslmode=require&pgbouncer=true"
# ! $ ^ ride as themselves; @ and % are percent-encoded, as a URL must carry them.
PW_DECODED = "s3cr!t$^" + "@" + "x%9"
PW_IN_URL = "s3cr!t$^" + "%40" + "x%259"
OTHER_DECODED = "second" + "Secret1"
SAFE = SCHEME + USER + "@" + HOSTPORT + PATH + "?" + QUERY


def userinfo_url(query=QUERY, pw=PW_IN_URL):
    url = SCHEME + USER + ":" + pw + "@" + HOSTPORT + PATH
    return url + ("?" + query if query else "")


def query_url(pw=PW_IN_URL):
    return (SCHEME + USER + "@" + HOSTPORT + PATH + "?sslmode=require&"
            + "password" + "=" + pw + "&pgbouncer=true")


# ------------------------------------------------------------ (a) split ----
class SplitPassword(unittest.TestCase):
    def test_userinfo_password_is_taken_out_and_decoded(self):
        safe, pw = pg_argv.split_password(userinfo_url())
        self.assertEqual((safe, pw), (SAFE, PW_DECODED))

    def test_query_password_is_taken_out_and_decoded(self):
        safe, pw = pg_argv.split_password(query_url())
        self.assertEqual((safe, pw), (SAFE, PW_DECODED))

    def test_both_sources_userinfo_wins_and_both_are_stripped(self):
        other = quote(OTHER_DECODED, safe="")
        url = (SCHEME + USER + ":" + PW_IN_URL + "@" + HOSTPORT + PATH
               + "?sslmode=require&" + "password" + "=" + other
               + "&pgbouncer=true")
        safe, pw = pg_argv.split_password(url)
        self.assertEqual(pw, PW_DECODED)
        self.assertEqual(safe, SAFE)
        self.assertNotIn(OTHER_DECODED, safe)

    def test_no_password_returns_the_input_unchanged(self):
        for url in (SAFE, SCHEME + HOSTPORT, SCHEME + HOSTPORT + PATH, "", None):
            self.assertEqual(pg_argv.split_password(url), (url, None))

    def test_query_order_is_kept(self):
        url = (SCHEME + USER + "@" + HOSTPORT + PATH + "?b=2&" + "password"
               + "=" + PW_IN_URL + "&a=1&c=3")
        safe, _pw = pg_argv.split_password(url)
        self.assertTrue(safe.endswith("?b=2&a=1&c=3"), safe)

    def test_a_query_of_only_the_password_leaves_no_dangling_mark(self):
        url = SCHEME + USER + "@" + HOSTPORT + PATH + "?" + "password" + "=" + PW_IN_URL
        self.assertEqual(pg_argv.split_password(url),
                         (SCHEME + USER + "@" + HOSTPORT + PATH, PW_DECODED))

    def test_the_fragment_and_a_socket_host_are_kept(self):
        url = (SCHEME + "/postgres?host=%2Ftmp&" + "password" + "="
               + PW_IN_URL + "#frag")
        safe, pw = pg_argv.split_password(url)
        self.assertEqual(pw, PW_DECODED)
        self.assertEqual(safe, SCHEME + "/postgres?host=%2Ftmp#frag")

    def test_plane_loader_still_exports_the_same_function(self):
        sys.path.insert(0, str(REPO / "platform" / "workers" / "mini-worker"))
        import plane_loader  # noqa: PLC0415
        self.assertIs(plane_loader.split_password, pg_argv.split_password)


# ---------------------------------------------------------- (b) for_psql ----
class ForPsql(unittest.TestCase):
    ENV = {"PATH": "/usr/bin:/bin", "HOME": "/tmp"}

    def test_pgpassword_is_set_when_a_password_was_found(self):
        for url in (userinfo_url(), query_url()):
            safe, child = pg_argv.for_psql(url, dict(self.ENV))
            self.assertEqual(safe, SAFE)
            self.assertEqual(child["PGPASSWORD"], PW_DECODED)
            for k, v in self.ENV.items():
                self.assertEqual(child[k], v)

    def test_no_pgpassword_when_there_is_no_password(self):
        safe, child = pg_argv.for_psql(SAFE, dict(self.ENV))
        self.assertEqual(safe, SAFE)
        self.assertEqual(child, self.ENV)
        self.assertNotIn("PGPASSWORD", child)

    def test_the_callers_dict_is_not_mutated(self):
        env = dict(self.ENV)
        before = dict(env)
        _safe, child = pg_argv.for_psql(userinfo_url(), env)
        self.assertEqual(env, before)
        self.assertIsNot(child, env)
        self.assertNotIn("PGPASSWORD", env)

    def test_env_none_copies_os_environ(self):
        _safe, child = pg_argv.for_psql(userinfo_url())
        self.assertIsNot(child, os.environ)
        self.assertEqual(child["PGPASSWORD"], PW_DECODED)
        for k, v in os.environ.items():
            if k != "PGPASSWORD":
                self.assertEqual(child[k], v)
        self.assertNotEqual(os.environ.get("PGPASSWORD"), PW_DECODED)


# --------------------------------------------------------- (c) repo scan ----
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".claude"}

# Known exceptions, by exact repo-relative path. The list only shrinks: a pin
# that stops offending fails the test so it gets removed.
_REPRO = ("URL is a module constant naming a local scratch Postgres with NO "
          "password (verified by the lead: plane14_2_skipped.py:9)")
PINNED = {
    "new-workflow-design/builds/review-component/sweep/repro/plane14_2_skipped.py": _REPRO,
    "new-workflow-design/builds/review-component/sweep/repro/cp19c_sides.py": _REPRO,
    "new-workflow-design/builds/review-component/sweep/repro/pm54_meta_order.py": _REPRO,
    "new-workflow-design/builds/review-component/sweep/repro/rc2_plane14.py": _REPRO,
}

_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _is_for_psql(call):
    if not isinstance(call, ast.Call):
        return False
    f = call.func
    return ((isinstance(f, ast.Name) and f.id == "for_psql")
            or (isinstance(f, ast.Attribute) and f.attr == "for_psql"))


def _own_nodes(scope):
    """Every node in `scope`'s own body — nested functions and classes are
    their own scopes and are not descended into."""
    todo = list(ast.iter_child_nodes(scope))
    while todo:
        node = todo.pop()
        yield node
        if not isinstance(node, _SCOPES):
            todo.extend(ast.iter_child_nodes(node))


def _bound_from_for_psql(scope):
    """Names bound as the SAFE URL from for_psql(...) in this scope:
    `safe, child = for_psql(...)` binds `safe`."""
    names = set()
    for node in _own_nodes(scope):
        if isinstance(node, ast.Assign) and _is_for_psql(node.value):
            for target in node.targets:
                if isinstance(target, (ast.Tuple, ast.List)) and target.elts \
                        and isinstance(target.elts[0], ast.Name):
                    names.add(target.elts[0].id)
    return names


def _is_psql_spawn(call):
    f = call.func
    if not (isinstance(f, ast.Attribute) and f.attr in ("run", "Popen")
            and isinstance(f.value, ast.Name) and f.value.id == "subprocess"):
        return None
    if not call.args or not isinstance(call.args[0], ast.List):
        return None
    elts = call.args[0].elts
    if len(elts) < 2:
        return None
    first = elts[0]
    if not ((isinstance(first, ast.Constant) and first.value == "psql")
            or (isinstance(first, ast.Name) and first.id == "psql")):
        return None
    return elts[1]


def offenders_in(source, filename="<src>"):
    """Line numbers of psql spawns in `source` handing a raw URL on argv."""
    tree = ast.parse(source, filename=filename)
    found = []

    def walk(node, bound):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            bound = bound | _bound_from_for_psql(node)
        if isinstance(node, ast.Call):
            second = _is_psql_spawn(node)
            if isinstance(second, ast.Name) and second.id not in bound:
                found.append(node.lineno)
        for child in ast.iter_child_nodes(node):
            walk(child, bound)

    walk(tree, _bound_from_for_psql(tree))
    return sorted(found)


def scan_repo(root=REPO):
    """`(offenders as ['path:line'], unparsed psql files as ['path'])`."""
    offenders, unparsed = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith(".py") or name.startswith("test_"):
                continue
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            try:
                source = path.read_bytes()
            except OSError:
                continue
            if b"psql" not in source:
                continue
            try:
                lines = offenders_in(source, rel)
            except (SyntaxError, ValueError):
                unparsed.append(rel)
                continue
            offenders.extend("%s:%d" % (rel, n) for n in lines)
    return offenders, unparsed


class ScannerUnit(unittest.TestCase):
    """The scanner's own rules, on snippets — so a green scan means something."""

    def test_a_raw_url_offends(self):
        src = ("import subprocess\n"
               "def q(url, sql):\n"
               "    return subprocess.run(['psql', url, '-c', sql])\n")
        self.assertEqual(offenders_in(src), [3])

    def test_a_bare_psql_name_and_popen_offend(self):
        src = ("import subprocess\n"
               "def q(url, psql):\n"
               "    return subprocess.Popen([psql, url])\n")
        self.assertEqual(offenders_in(src), [3])

    def test_a_url_from_for_psql_is_clean(self):
        src = ("import subprocess\n"
               "def q(url, sql):\n"
               "    safe, child = for_psql(url)\n"
               "    return subprocess.run(['psql', safe, '-c', sql], env=child)\n")
        self.assertEqual(offenders_in(src), [])

    def test_a_closure_over_the_enclosing_functions_binding_is_clean(self):
        src = ("import subprocess\n"
               "def runner_for(url, env):\n"
               "    safe_url, child = pg_argv.for_psql(url, env)\n"
               "    def runner(sql):\n"
               "        return subprocess.run(['psql', safe_url], input=sql, env=child)\n"
               "    return runner\n")
        self.assertEqual(offenders_in(src), [])

    def test_a_binding_in_another_function_does_not_count(self):
        src = ("import subprocess\n"
               "def a(url):\n"
               "    safe, child = for_psql(url)\n"
               "def b(safe):\n"
               "    return subprocess.run(['psql', safe])\n")
        self.assertEqual(offenders_in(src), [5])

    def test_the_child_env_is_not_a_safe_url(self):
        src = ("import subprocess\n"
               "def q(url):\n"
               "    safe, child = for_psql(url)\n"
               "    return subprocess.run(['psql', child])\n")
        self.assertEqual(offenders_in(src), [4])

    def test_other_programs_and_literal_urls_are_not_this_scan(self):
        src = ("import subprocess\n"
               "def q(url):\n"
               "    subprocess.run(['pg_dump', url])\n"
               "    subprocess.run(['psql', '-c', 'select 1'])\n")
        self.assertEqual(offenders_in(src), [])


class RepoScan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.offenders, cls.unparsed = scan_repo()

    def paths(self):
        return {o.rsplit(":", 1)[0] for o in self.offenders}

    def test_no_psql_spawn_outside_the_pins_carries_a_raw_url(self):
        stray = [o for o in self.offenders if o.rsplit(":", 1)[0] not in PINNED]
        self.assertEqual(stray, [], "psql spawned with a raw URL — route it "
                         "through components/keys/pg_argv.for_psql")

    def test_every_pin_still_offends(self):
        gone = sorted(set(PINNED) - self.paths())
        self.assertEqual(gone, [], "pinned exception no longer offends — "
                         "remove it from PINNED (the list only shrinks)")

    def test_every_file_mentioning_psql_was_read(self):
        self.assertEqual(self.unparsed, [], "could not parse, so could not "
                         "prove clean")

    def test_the_seven_routed_callers_are_scanned_and_clean(self):
        for rel in ("platform/workers/mini-worker/plane_loader.py",
                    "components/metrics/refresh.py",
                    "components/cs-metrics/refresh.py",
                    "components/metrics/load_brand_files.py",
                    "new-workflow-design/builds/dashboard/check_spend_stock.py",
                    "new-workflow-design/builds/dashboard/check_orders_chain.py",
                    "new-workflow-design/builds/fulfillment-routes/check_routes_namespace.py"):
            source = (REPO / rel).read_bytes()
            self.assertIn(b"for_psql(", source, rel)
            self.assertEqual(offenders_in(source, rel), [], rel)


if __name__ == "__main__":
    unittest.main(verbosity=2)
