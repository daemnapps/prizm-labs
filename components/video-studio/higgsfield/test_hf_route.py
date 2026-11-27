import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hf_route as H  # noqa: E402


def scene(i, **kw):
    return dict({"id": i, "to_camera": True, "speaker": "SAM", "voice": "this is the line he says", "setting_id": "KITCHEN", "props": []}, **kw)


class Route(unittest.TestCase):
    def test_the_brief_s_own_format_picks_the_route(self):
        for fmt, want in (("song-ad", "singing-ads"), ("micro-drama", "drama-ads"), ("remedy", "ugc-video"), ("new:unboxing-deal", "ugc-video"),
                          ("testimonial-montage", "own-footage"), ("text-thread", "code")):
            f = H.facts({"piece": {"format": fmt}, "scenes": [scene("S1")]})
            self.assertEqual(H.choose(f)[0]["id"], want, fmt)

    def test_a_format_with_no_row_is_decided_by_what_the_brief_does(self):
        one = {"piece": {"format": "never-seen"}, "scenes": [scene("S1")]}
        two = {"piece": {}, "scenes": [scene("S1"), scene("S2", speaker="JO")]}
        none = {"piece": {}, "scenes": [scene("S1", to_camera=False)]}
        sung = {"piece": {}, "song": {"sections": [1]}, "scenes": [scene("S1")]}
        self.assertEqual([H.choose(H.facts(d))[0]["id"] for d in (one, two, none, sung)], ["ugc-video", "drama-ads", "own-footage", "singing-ads"])

    def test_a_creator_brief_never_goes_to_ai(self):
        self.assertEqual(H.choose(H.facts({"piece": {"format": "song-ad"}, "scenes": [scene("S1")]}), creator=True)[0]["id"], "creators")

    def test_no_format_is_on_two_routes(self):
        seen = [x for r in json.loads((H.HERE / "routes.json").read_text())["routes"] for x in r["formats"]]
        self.assertEqual(len(seen), len(set(seen)))


class Pack(unittest.TestCase):
    def ws(self, sheet=True):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        ws = Path(t.name)
        (ws / "brands" / "acme").mkdir(parents=True)
        (ws / "components").mkdir()
        b = ws / "runs" / "ai-elements" / "acme"
        for f in ("casting/sam/master.jpg", "sets/kitchen/plates/wide.png", "products/widget-brush/kit.json") + (("products/widget-brush/model/product-sheet.png",) if sheet else ()):
            (b / f).parent.mkdir(parents=True, exist_ok=True)
            (b / f).write_text("{}")
        doc = {"piece": {"format": "remedy", "title": "T"}, "cast": [{"name": "SAM", "bank_id": "sam"}, {"name": "JO", "bank_id": "NEW", "identity_block": "a woman, 40"}],
               "scenes": [scene("S1", happens="he holds the Widget Brush")]}
        f = ws / "runs" / "x" / "acme" / "l" / "5-brief.md"
        f.parent.mkdir(parents=True)
        f.write_text("# b\n\n```json\n" + json.dumps(doc) + "\n```\n")
        return ws, f

    def test_what_we_own_rides_as_files_and_a_new_person_is_made_once(self):
        ws, f = self.ws()
        r, _, _ = H.plan(f, ws=ws)
        self.assertTrue(r["ready"], r["missing"])
        self.assertEqual([len(r["here"][k]) for k in ("people", "places", "product")], [1, 1, 1])
        self.assertEqual([m["name"] for m in r["to_make_once"]], ["JO"])
        self.assertGreater(r["credits"]["seedance"], r["credits"]["wan"])

    def test_no_product_sheet_stops_it(self):
        ws, f = self.ws(sheet=False)
        r, _, _ = H.plan(f, ws=ws)
        self.assertFalse(r["ready"])
        self.assertIn("product", r["missing"][0])


if __name__ == "__main__":
    unittest.main()
