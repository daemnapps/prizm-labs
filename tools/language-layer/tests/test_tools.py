#!/usr/bin/env python3
"""The tools, the CLI and the component's hygiene — fixture trees only: no
model call, no network, no key, nothing written outside a temp folder.

    python3 -m unittest discover -s tests          # from tools/language-layer
"""
import ast, importlib.util, json, os, re, subprocess, sys, tempfile, unittest
HOME_X = "/" + "Users" + "/x/"   # a made-up laptop home, built so no real path is written here
from pathlib import Path

COMP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMP))
from language_layer import engine as E  # noqa: E402

PY = sorted(p for p in COMP.rglob("*.py") if "__pycache__" not in p.parts)


def tool(name):
    """Load tools/<name>.py as a module, the way a caller would (research-gatherer
    loads label.py by path)."""
    spec = importlib.util.spec_from_file_location(f"_ll_{name}", COMP / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(COMP / "tools"))
    spec.loader.exec_module(m)
    return m


class Roots:
    """Point the engine's root probe at a fixture tree for one test."""
    def __init__(self, root):
        self.root = root

    def __enter__(self):
        self.saved = list(E._ROOTS)
        E.configure(roots=[lambda: self.root])

    def __exit__(self, *a):
        E.configure(roots=self.saved)


def bank(root, brand="fx", avatar="a1", rows=None):
    lang = Path(root) / "brands" / brand / "core-avatars" / avatar / "language"
    lang.mkdir(parents=True)
    rows = rows or [
        dict(id="p-1", text="my spots came back", funnel="prospect", use="problem-language",
             source=dict(name="Survey — Q: what bothers you most?", type="survey", ref="sheets/fx-survey.csv")),
        dict(id="p-2", text="saw this on tiktok", funnel="prospect", use="hook",
             source=dict(name="creator post", type="comment",
                         ref="https://www.tiktok.com/@some.creator/video/7312345678901234567")),
    ]
    (lang / "prospects.json").write_text(json.dumps({"schema": 1, "avatar": avatar, "funnel": "prospect",
                                                     "entries": rows}, indent=1) + "\n")
    return lang


class Hygiene(unittest.TestCase):
    def test_every_file_compiles_on_this_interpreter(self):
        # run under /usr/bin/python3 (3.9.6, the mini's) this is the 3.9 rail
        for p in PY:
            with self.subTest(p.name):
                compile(p.read_text(), str(p), "exec")

    def test_no_home_folder_or_personal_path_in_code(self):
        bad = re.compile(r"Path\.home\(\)|expanduser\(\s*['\"]~|['\"]/Users/[a-z]|\.daemn")
        for p in PY:
            if p.parent.name == "tests":
                continue
            for n, line in enumerate(p.read_text().splitlines(), 1):
                code = line.split("#", 1)[0]
                if bad.search(code) and "startswith(" not in code and "re.search" not in code:
                    self.fail(f"{p.relative_to(COMP)}:{n}: {line.strip()}")

    def test_no_brand_name_in_code_or_prompts(self):
        ws = COMP.parents[1]
        names = [d.name for d in (ws / "brands").iterdir() if d.is_dir() and not d.name.startswith("_")]
        if not names:
            self.skipTest("no brands/ tree beside this checkout")
        pat = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b", re.I)
        files = [p for p in PY if p.parent.name != "tests"] + sorted((COMP / "prompts").glob("*.md"))
        for p in files:
            for n, line in enumerate(p.read_text().splitlines(), 1):
                self.assertIsNone(pat.search(line), f"{p.relative_to(COMP)}:{n} names a brand")

    def test_keys_are_read_by_name_only(self):
        names = set()
        for p in PY:
            names |= set(re.findall(r"environ(?:\.get)?\(?\[?['\"]([A-Z_]{4,})['\"]", p.read_text()))
        self.assertLessEqual(names, {"LANGUAGE_ROOT", "AI_WORKSPACE", "GEMINI_API_KEY"})

    def test_the_engine_imports_no_network_module(self):
        tree = ast.parse((COMP / "language_layer" / "engine.py").read_text())
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertFalse(mods & {"urllib", "http", "socket", "requests", "subprocess"})


class CheckNames(unittest.TestCase):
    def test_row_and_source_ids(self):
        m = tool("check_names")
        self.assertIsNone(m.check_row_id("language_fx_a1_prospect_0001", "fx"))
        self.assertIn("4+ digits", m.check_row_id("language_fx_a1_prospect_1", "fx"))
        self.assertIsNone(m.check_source_id("post_tiktok_some-creator_7312345678901234567"))
        self.assertIn("unknown kind", m.check_source_id("blog_x_y"))

    def test_run_reports_a_fixture_bank(self):
        m = tool("check_names")
        with tempfile.TemporaryDirectory() as t, Roots(Path(t)):
            bank(t)
            rep = m.run("fx")
        self.assertEqual(rep["rows"], 2)
        self.assertEqual(rep["row_ids_off_standard"], 2)


class RenameIds(unittest.TestCase):
    def test_plan_keeps_free_numbers_and_writes_nothing(self):
        m = tool("rename_ids")
        with tempfile.TemporaryDirectory() as t, Roots(Path(t)):
            lang = bank(t)
            before = (lang / "prospects.json").read_text()
            files, lookup = m.plan("fx")
            self.assertEqual((lang / "prospects.json").read_text(), before)
        self.assertEqual(sorted(v[1] for v in lookup.values()),
                         ["language_fx_a1_prospect_0001", "language_fx_a1_prospect_0002"])


class MapSources(unittest.TestCase):
    def test_survey_and_tiktok_ids(self):
        m = tool("map_sources")
        with tempfile.TemporaryDirectory() as t, Roots(Path(t)):
            lang = bank(t)
            rows = json.loads((lang / "prospects.json").read_text())["entries"]
            mp = m.mapper("fx")
            got = [mp(r) for r in rows]
        self.assertEqual(got[0]["id"], "survey_fx_fx")
        self.assertTrue(got[0]["question"].startswith("q-01_"))
        self.assertEqual(got[1]["id"], "post_tiktok_some-creator_7312345678901234567")

    def test_a_laptop_path_never_survives(self):
        m = tool("map_sources")
        self.assertEqual(m.clean_ref(HOME_X + "devel/daemn/a/b.csv"), "damon-sandbox:a/b.csv")
        self.assertEqual(m.clean_ref(HOME_X + "elsewhere.csv"), "local file (path withheld)")


class Label(unittest.TestCase):
    """label.py without a model: import, the pure reads, where output goes, the key."""
    def setUp(self):
        self.m = tool("label")

    def test_import_needs_no_model_and_finds_the_newest_prompt(self):
        self.assertTrue(callable(self.m.label))
        self.assertRegex(self.m.prompt_file().name, r"label-awareness-v\d+\.md")
        self.assertTrue((self.m.SLICES / "awareness.md").is_file(), "doctrine slice missing")

    def test_parse_labels(self):
        self.assertEqual(self.m.parse_labels('x ```json\n{"labels": [{"id": "a"}]}\n``` y'), [{"id": "a"}])
        self.assertEqual(self.m.parse_labels('noise {"labels": []} noise'), [])

    def test_origin_voice_lane(self):
        self.assertEqual(self.m.origin_of({"source": {"type": "survey"}}, "fx"), "internal")
        self.assertEqual(self.m.origin_of({"source": {"type": "comment", "name": "reddit r/x",
                                                      "ref": "https://reddit.com/r/x"}}, "fx"), "external")
        self.assertEqual(self.m.voice_of({"speaker": "creator"}), "brand")
        self.assertEqual(self.m.lane_of({"_file": "leads.json"}), "lead")

    def test_output_goes_under_runs_language_layer(self):
        d = self.m.run_dir("fx", "test-set")
        self.assertEqual(d, E.WORKSPACE / "runs" / "language-layer" / "fx" / "test-set")

    def test_the_key_is_read_by_name(self):
        old = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "fixture-not-a-key"
        try:
            self.assertEqual(self.m.gemini_key(), "fixture-not-a-key")
        finally:
            if old is None:
                del os.environ["GEMINI_API_KEY"]
            else:
                os.environ["GEMINI_API_KEY"] = old


class Pages(unittest.TestCase):
    def test_bank_page_and_review_page_build_from_fixtures(self):
        with tempfile.TemporaryDirectory() as t, Roots(Path(t)):
            bank(t)
            bp = tool("bank_page")
            self.assertIn("FX", bp.brand_block("fx"))
            (Path(t) / "test-set.json").write_text(json.dumps(
                {"brand": "fx", "sampled": 1, "per_level": {"unaware": 1},
                 "test": {"unaware": [{"text": "x", "lane": "lead", "lane_words": "lead"}]}}))
            out = tool("review_page").build(t)
            self.assertTrue(out.is_file())


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(COMP / "query_language.py"), *args],
                              capture_output=True, text=True, timeout=60)

    def test_avatars_and_stage_query(self):
        with tempfile.TemporaryDirectory() as t:
            bank(t)
            r = self.run_cli("--brand", "fx", "--root", t, "--avatars")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("a1", r.stdout)
            prof = Path(t) / "profile.json"
            prof.write_text(json.dumps({"stage_use": {"hooks": ["hook"]}, "widen": "ladder"}))
            r = self.run_cli("--brand", "fx", "--root", t, "--stage", "hooks", "--profile", str(prof),
                             "--awareness", "problem-aware", "--unused")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("saw this on tiktok", r.stdout)
            self.assertIn("problem-aware level first", r.stdout)


if __name__ == "__main__":
    unittest.main()
