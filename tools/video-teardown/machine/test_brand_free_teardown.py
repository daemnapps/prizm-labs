"""The teardown is brand-free (the owner, 2026-09-30: "teardown should always just
be whatever"). No teardown stage (0, 1, 1c, 2) may be handed a brand's name,
product or files — through a variable, or through a shared list it reads."""
import importlib.util, json, sys, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[2]
sys.path.append(str(HERE))
_s = importlib.util.spec_from_file_location("td_run_bf", HERE / "run.py")
R = importlib.util.module_from_spec(_s); _s.loader.exec_module(R)
import chain as C

BRANDS = [p.name.lower() for p in (WS / "brands").iterdir()
          if p.is_dir() and not p.name.startswith(("_", "."))]


class BrandFreeTeardown(unittest.TestCase):
    def test_no_teardown_variable_points_into_a_brand(self):
        for s in C.stages(BRANDS[0], "", "creator", "ORGANIC"):
            if s["key"] not in R.TEARDOWN_KEYS:
                continue
            for var, src in s["vars"].items():
                self.assertFalse(str(src).startswith(("brands/", "?", "~")),
                                 f"{s['key']} reads {var} from {src}")

    def test_element_lists_reach_the_teardown_without_our_brands(self):
        for s in C.stages(BRANDS[0], "", "creator", "ORGANIC"):
            if s["key"] not in R.TEARDOWN_KEYS:
                continue
            for var, src in s["vars"].items():
                if "components/elements/library/" in str(src) and str(src).endswith(".json"):
                    text = R.brand_free_list((WS / src).read_text()).lower()
                    for b in BRANDS:
                        self.assertNotIn(b, text, f"{src} still names {b} for {s['key']}")

    def test_strip_keeps_the_definitions(self):
        out = json.loads(R.brand_free_list(json.dumps(
            {"rows": [{"id": "x", "what": "a thing", "evidence": "runs/ours", "examples": "brand file"}]})))
        self.assertEqual(out, {"rows": [{"id": "x", "what": "a thing"}]})

    def test_each_list_is_pasted_once(self):
        s = next(x for x in C.stages(BRANDS[0], "", "creator", "ORGANIC") if x["key"] == "stage1c")
        f = Path(s["prompt"])
        t = f.read_text()
        for v in ("{video_formats}", "{video_structures}", "{delivery}"):
            self.assertEqual(t.count(v), 1, f"{v} appears {t.count(v)} times in {f.name}")


if __name__ == "__main__":
    unittest.main()
