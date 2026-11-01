#!/usr/bin/env python3
"""SI-141 (brand names out of code): the copy library takes its brands and its
saves pool as flags and names none of them.

    /usr/bin/python3 tools/copywriter/library/test_si141_brand_arg.py

Offline. The refusals run the real script as a sub-process (it exits before
any write); the reach tests call the real readers against a temp workspace,
so nothing under the real runs/ or brands/ is written. The names that must
not appear are read off brands/ and sources.json, never typed here
(workspace rule 7). Stdlib only.
"""
import contextlib, importlib.util, io, json, re, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SRC = HERE / "build_library.py"
REPO = next(d for d in HERE.parents if (d / "components").is_dir() and (d / "brands").is_dir())
READERS = ("emails", "captions", "angles", "raw_ads", "pages", "teardowns", "our_pages", "machine")
FLAGS = ("--email-brand", "--pages-brand", "--pool")


def load():
    spec = importlib.util.spec_from_file_location("_si141_build_library", SRC)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(m)
    return m


build = load()
# brandpath is imported by our_pages() from WS/components; a temp WS has no
# copy, so the real one is put on the path once, here.
if str(REPO / "components" / "brandpath") not in sys.path:
    sys.path.append(str(REPO / "components" / "brandpath"))


def run_cli(*args):
    return subprocess.run([sys.executable, str(SRC)] + list(args),
                          capture_output=True, text=True, timeout=60)


def forbidden_names():
    """Every brand folder name, plus the source keys today's build filed by
    name: the saves pool (kind saved-posts-capture) and the brand halves of
    the shipped-sends and our-pages keys."""
    names = {p.name for p in (REPO / "brands").iterdir()
             if p.is_dir() and not p.name.startswith((".", "_"))}
    sources = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))["sources"]
    for key, s in sources.items():
        if s.get("kind") == "saved-posts-capture":
            names.add(key)
        elif s.get("kind") == "our-shipped-sends":
            names.add(key.rsplit("-email", 1)[0])
        elif s.get("kind") == "our-pages":
            names.add(key.rsplit("-pages", 1)[0])
    return sorted(n for n in names if n)


class Refusals(unittest.TestCase):

    def test_no_flags_exits_2_with_usage(self):
        r = run_cli()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("usage:", r.stderr)
        for f in FLAGS:
            self.assertIn(f, r.stderr)

    def test_each_flag_alone_missing_exits_2(self):
        full = {"--email-brand": "zz-a", "--pages-brand": "zz-b", "--pool": "zz-pool"}
        for missing in FLAGS:
            args = [x for k, v in full.items() if k != missing for x in (k, v)]
            r = run_cli(*args)
            self.assertEqual(r.returncode, 2, (missing, r.stderr))
            self.assertIn("usage:", r.stderr, missing)
            self.assertIn(missing, r.stderr, missing)

    def test_no_repeatable_brand_flag(self):
        r = run_cli("--brand", "zz-a", "--email-brand", "zz-a", "--pages-brand", "zz-b", "--pool", "zz-pool")
        self.assertEqual(r.returncode, 2, r.stderr)


class FlagsReachTheirSections(unittest.TestCase):

    def test_each_flag_reaches_its_reader_and_every_other_runs_once(self):
        calls = []

        def rec(name):
            return lambda *a, **k: calls.append((name, a, k))

        a = build.parse_args(["--email-brand", "zz-mail", "--pages-brand", "zz-page", "--pool", "zz-pool"])
        with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as st:
            st.enter_context(mock.patch.object(build, "INDEX", Path(td) / "index.json"))
            for r in READERS:
                st.enter_context(mock.patch.object(build, r, rec(r)))
            st.enter_context(contextlib.redirect_stdout(io.StringIO()))
            build.main(a.email_brand, a.pages_brand, a.pool)
        self.assertEqual([c[0] for c in calls], list(READERS))
        got = {c[0]: c for c in calls}
        self.assertEqual(got["emails"][1], ("zz-mail",))
        self.assertEqual(got["our_pages"][1], ("zz-page",))
        self.assertEqual(got["captions"][1], ("zz-pool",))
        for r in ("angles", "raw_ads", "pages", "teardowns", "machine"):
            self.assertEqual(got[r][1:], ((), {}), r)

    def test_the_command_line_wires_the_flags_into_main(self):
        tail = SRC.read_text(encoding="utf-8").split('if __name__ == "__main__":', 1)[1]
        self.assertIn("parse_args()", tail)
        self.assertIn("main(a.email_brand, a.pages_brand, a.pool)", tail)

    def test_readers_have_no_default(self):
        import inspect
        for name, param in (("emails", "brand"), ("our_pages", "brand"), ("captions", "pool")):
            p = inspect.signature(getattr(build, name)).parameters[param]
            self.assertIs(p.default, inspect.Parameter.empty, name)


class RealReadersOnATempWorkspace(unittest.TestCase):

    def setUp(self):
        build.rows[:] = []
        build.notes[:] = []

    def test_emails_files_the_given_brand(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            sends = ws / "brands" / "zz-mail" / "email-sms" / "sends"
            sends.mkdir(parents=True)
            (sends / "s1.md").write_text("# A send\n- preview: hello there\n", encoding="utf-8")
            with mock.patch.object(build, "WS", ws), contextlib.redirect_stdout(io.StringIO()):
                build.emails("zz-mail")
        self.assertEqual(len(build.rows), 1, build.notes)
        r = build.rows[0]
        self.assertEqual((r["brand"], r["channel"]), ("zz-mail", "email"))
        self.assertEqual(r["audience"]["source"], "zz-mail-email")
        self.assertEqual(r["path"], "brands/zz-mail/email-sms/sends/s1.md")

    def test_our_pages_files_the_given_brand(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            lp = ws / "brands" / "zz-page" / "existing-content" / "landing-pages"
            lp.mkdir(parents=True)
            (lp / "p1.md").write_text("page words", encoding="utf-8")
            with mock.patch.object(build, "WS", ws), contextlib.redirect_stdout(io.StringIO()):
                build.our_pages("zz-page")
        self.assertEqual(len(build.rows), 1, build.notes)
        r = build.rows[0]
        self.assertEqual((r["brand"], r["channel"], r["format"]), ("zz-page", "owned-pages", "landing-page"))
        self.assertEqual(r["audience"]["source"], "zz-page-pages")
        self.assertTrue(r["path"].startswith("brands/zz-page/"), r["path"])

    def test_captions_read_the_given_pool(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            org = ws / "components" / "swipe-organic"
            cat = org / "records" / "zz-pool" / "catalog.json"
            cat.parent.mkdir(parents=True)
            cat.write_text(json.dumps({"rows": [{"caption": "first line\nmore", "author": "a"}]}))
            with mock.patch.object(build, "WS", ws), mock.patch.object(build, "SWIPE_ORGANIC", org), \
                    contextlib.redirect_stdout(io.StringIO()):
                build.captions("zz-pool")
        self.assertEqual(len(build.rows), 1, build.notes)
        r = build.rows[0]
        self.assertEqual(r["audience"]["source"], "zz-pool")
        self.assertEqual(r["path"], "components/swipe-organic/records/zz-pool/catalog.json")


class NoNamesInTheCode(unittest.TestCase):

    def test_no_brand_or_pool_name_in_build_library(self):
        names = forbidden_names()
        self.assertGreaterEqual(len(names), 3, names)   # the fixture itself found something
        text = SRC.read_text(encoding="utf-8")
        hits = [(n, i + 1) for i, line in enumerate(text.splitlines()) for n in names
                if re.search(re.escape(n), line, re.I)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
