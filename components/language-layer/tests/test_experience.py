"""The experience index: fresh moments each run, none in the fixed files (2026-11-02)."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from language_layer import experience as X


class Experience(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        h = self.root / "runs" / "language-layer" / "b" / "experience"
        h.mkdir(parents=True)
        rows = [{"id": f"x{i}", "quote": f"moment {i}", "scene": f"s{i}",
                 "theme": ["a", "b", "c", "d"][i % 4]} for i in range(40)]
        rows[17]["scene"] = "pool-party"
        (h / "av.json").write_text(json.dumps({"rows": rows}))
        (h / "strip.json").write_text(json.dumps({
            "lines": ["She wore the thing."], "terms": ["coat"]}))

    def ids(self, run, hint=""):
        return {r["id"] for r in X.pick("b", "av", hint, run, root=self.root)}

    def test_next_run_gets_different_moments(self):
        self.assertFalse(self.ids("r1") & self.ids("r2"))

    def test_rerun_keeps_its_set(self):
        self.assertEqual(self.ids("r1"), self.ids("r1"))

    def test_rerun_preserves_exact_prompt_order_even_if_index_order_changes(self):
        first = X.pick("b", "av", "a pool party", "r1", root=self.root)
        self.assertEqual(first[0]["id"], "x17")
        expected = X.render(first)
        self.assertEqual(X.render(X.pick("b", "av", "a pool party", "r1", root=self.root)), expected)
        index = self.root / "runs/language-layer/b/experience/av.json"
        data = json.loads(index.read_text())
        data["rows"].reverse()
        index.write_text(json.dumps(data))
        self.assertEqual(X.render(X.pick("b", "av", "a pool party", "r1", root=self.root)), expected)

    def test_no_theme_crowds_a_set(self):
        got = X.pick("b", "av", "", "r1", root=self.root)
        self.assertLessEqual(max(sum(r["theme"] == t for r in got) for t in "abcd"), 2)

    def test_swipe_fit_comes_first(self):
        self.assertEqual(X.pick("b", "av", "a pool party", "r1", n=1, root=self.root)[0]["id"], "x17")

    def test_fixed_lifts_moments_and_keeps_the_rest(self):
        text = "# Title\nThe mechanism works this way.\nShe wore the thing.\nA coat in heat. The offer stays.\n| Hide | a coat | x |"
        out = X.fixed(text, "b", root=self.root)
        self.assertIn("The mechanism works", out)
        self.assertIn("The offer stays.", out)
        self.assertNotIn("She wore", out)
        self.assertNotIn("coat", out)
        self.assertIn("| Hide |", out)

    def test_fixed_removes_quoted_and_unquoted_overlaps(self):
        strip = self.root / "runs/language-layer/b/experience/strip.json"
        strip.write_text(json.dumps({
            "lines": ["temporary scene", '"temporary scene"', "temporary scene"],
            "terms": []}))
        text = ('# Title\n'
                'A permanent mechanism stays beside "temporary scene".\n'
                'A permanent offer stays beside temporary scene.\n'
                '"temporary scene"')
        self.assertEqual(X.fixed(text, "b", root=self.root),
                         '# Title\n'
                         'A permanent mechanism stays beside .\n'
                         'A permanent offer stays beside .')

    def test_fixed_overlap_preserves_mixed_line_threshold(self):
        strip = self.root / "runs/language-layer/b/experience/strip.json"
        strip.write_text(json.dumps({
            "lines": ["temporary scene", '"temporary scene"'], "terms": []}))
        text = ('# Title\n"temporary scene" ' + 'a' * 24 +
                '\n"temporary scene" ' + 'b' * 25 +
                '\nPermanent facts stay on this separate line.')
        self.assertEqual(X.fixed(text, "b", root=self.root),
                         '# Title\n ' + 'b' * 25 +
                         '\nPermanent facts stay on this separate line.')

    def test_fixed_is_identical_across_process_hash_seeds(self):
        import os
        import subprocess
        strip = self.root / "runs/language-layer/b/experience/strip.json"
        strip.write_text(json.dumps({
            "lines": ["temporary scene", '"temporary scene"',
                      'The whole "temporary scene" line.'], "terms": []}))
        text = ('# Title\nThe whole "temporary scene" line.\n'
                'A permanent mechanism stays beside "temporary scene".\n'
                '"temporary scene" ' + 'a' * 24 +
                '\n"temporary scene" ' + 'b' * 25)
        expected = '# Title\nA permanent mechanism stays beside .\n ' + 'b' * 25
        probe = ("import json,sys; from pathlib import Path; "
                 "sys.path.insert(0, sys.argv[1]); "
                 "from language_layer import experience as x; "
                 "print(json.dumps(x.fixed(sys.argv[3], 'b', root=Path(sys.argv[2]))))")
        outputs = []
        for seed in ("0", "1", "2", "3", "4", "5", "6", "7", "8"):
            env = os.environ.copy()
            env["PYTHONHASHSEED"] = seed
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            result = subprocess.check_output(
                [sys.executable, "-c", probe, str(Path(__file__).resolve().parents[1]),
                 str(self.root), text], env=env, universal_newlines=True)
            outputs.append(json.loads(result))
        self.assertEqual(set(outputs), {expected})

    def test_no_strip_list_changes_nothing(self):
        self.assertEqual(X.fixed("a coat", "other", root=self.root), "a coat")

    def test_empty_index_says_so(self):
        self.assertIn("no lived experiences", X.render([]))


if __name__ == "__main__":
    unittest.main()
