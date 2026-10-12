"""python3 -m unittest discover components/brandpath/tests"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import brandpath as BP  # noqa: E402


class Sandbox(unittest.TestCase):
    """A throwaway brands/ folder so no real brand is read or named."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "brands"
        self.b = self.root / "acme"
        (self.b / "ai-cast" / "casting").mkdir(parents=True)
        (self.b / "ai-cast" / "casting" / "roster.json").write_text("{}")
        (self.b / "elements").mkdir()
        (self.b / "identity").mkdir()
        (self.b / "identity-anchors.md").write_text("# anchors")
        (self.b / "products").mkdir()
        (self.b / "existing-content" / "ads").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults_when_file_missing(self):
        self.assertEqual(BP.folders("acme", root=self.root), BP.DEFAULTS)

    def test_old_folder_wins_today(self):
        self.assertEqual(BP.brand_path("acme", "ai-elements/characters", "casting", root=self.root),
                         self.b / "ai-cast" / "casting")
        self.assertEqual(BP.brand_path("acme", "intake", "ads", root=self.root),
                         self.b / "existing-content" / "ads")

    def test_new_folder_wins_once_it_exists(self):
        (self.b / "ai-elements" / "characters" / "casting").mkdir(parents=True)
        self.assertEqual(BP.brand_path("acme", "ai-elements/characters", "casting", root=self.root),
                         self.b / "ai-elements" / "characters" / "casting")

    def test_library_and_cast_are_two_keys(self):
        # the element library is ai-elements (today elements/); the cast is
        # ai-elements/characters (today ai-cast/) — asking for one never answers the other
        (self.b / "elements" / "index.json").write_text("{}")
        self.assertEqual(BP.brand_path("acme", "ai-elements", "index.json", root=self.root),
                         self.b / "elements" / "index.json")
        self.assertEqual(BP.brand_path("acme", "ai-elements", root=self.root), self.b / "elements")
        self.assertEqual(BP.brand_path("acme", "ai-elements/characters", root=self.root), self.b / "ai-cast")
        self.assertEqual(BP.brand_path("acme", "ai-elements", "casting", root=self.root),
                         self.b / "elements" / "casting")

    def test_second_old_place(self):
        # strategy maps to calendar THEN strategy; the file sits only under strategy
        (self.b / "calendar").mkdir()
        (self.b / "strategy").mkdir()
        (self.b / "strategy" / "angles.json").write_text("{}")
        (self.b / "calendar" / "moments.json").write_text("{}")
        self.assertEqual(BP.brand_path("acme", "strategy", "angles.json", root=self.root),
                         self.b / "strategy" / "angles.json")
        self.assertEqual(BP.brand_path("acme", "strategy", "moments.json", root=self.root),
                         self.b / "calendar" / "moments.json")

    def test_file_standing_in_for_folder(self):
        self.assertEqual(BP.brand_file("acme", "brand-identity", "identity-anchors.md", root=self.root),
                         self.b / "identity-anchors.md")
        # the folder itself, when asked for the folder
        self.assertEqual(BP.brand_path("acme", "brand-identity", root=self.root), self.b / "identity")
        # another file is looked for inside identity/, never inside the .md
        self.assertEqual(BP.brand_path("acme", "brand-identity", "palette.md", root=self.root),
                         self.b / "identity" / "palette.md")

    def test_missing_target_builds_todays_path(self):
        # nothing named "new-person" exists; the folder a tool writes into is ai-cast
        self.assertEqual(BP.brand_path("acme", "ai-elements/characters", "new-person", root=self.root),
                         self.b / "ai-cast" / "new-person")
        # a folder the brand has nowhere -> the new name
        self.assertEqual(BP.brand_path("acme", "learnings", "x.md", root=self.root),
                         self.b / "learnings" / "x.md")
        # a folder today's plan HAS, that this brand has not made yet -> today's place, not the new name
        self.assertEqual(BP.brand_path("acme", "content-creators", "x.md", root=self.root),
                         self.b / "creators" / "x.md")
        # a file standing in for a folder, asked for by name while missing -> where it sits today
        (self.b / "identity-anchors.md").unlink()
        self.assertEqual(BP.brand_file("acme", "brand-identity", "identity-anchors.md", root=self.root),
                         self.b / "identity-anchors.md")

    def test_folders_json_overrides(self):
        (self.b / "FOLDERS.json").write_text(json.dumps({"intake": ["legacy-content"], "extra": ["x"]}))
        (self.b / "legacy-content").mkdir()
        (self.b / "x").mkdir()
        m = BP.folders("acme", root=self.root)
        self.assertEqual(m["intake"], ["legacy-content"])
        self.assertEqual(m["products"], BP.DEFAULTS["products"])
        self.assertEqual(BP.brand_path("acme", "intake", root=self.root), self.b / "legacy-content")
        self.assertEqual(BP.brand_path("acme", "extra", root=self.root), self.b / "x")

    def test_broken_folders_json_falls_back(self):
        (self.b / "FOLDERS.json").write_text("{not json")
        self.assertEqual(BP.folders("acme", root=self.root), BP.DEFAULTS)

    def test_unknown_key(self):
        with self.assertRaises(BP.UnknownFolder):
            BP.brand_path("acme", "nope", root=self.root)

    def test_brand_paths_across_brands(self):
        (self.root / "beta" / "existing-content" / "ads").mkdir(parents=True)
        (self.root / "_TEMPLATE").mkdir()
        got = BP.brand_paths("intake", "ads", root=self.root)
        self.assertEqual(got, [self.b / "existing-content" / "ads",
                               self.root / "beta" / "existing-content" / "ads"])

    def test_rel(self):
        self.assertEqual(BP.rel("acme", "ai-elements/characters", "casting", root=self.root), "acme/ai-cast/casting")

    def test_resolve_rel_maps_todays_paths(self):
        R = lambda r: BP.resolve_rel("acme", r, root=self.root)  # noqa: E731
        self.assertEqual(R("ai-cast/casting"), self.b / "ai-cast" / "casting")
        self.assertEqual(R("existing-content/ads"), self.b / "existing-content" / "ads")
        self.assertEqual(R("identity-anchors.md"), self.b / "identity-anchors.md")
        self.assertEqual(R("identity/palette.md"), self.b / "identity" / "palette.md")
        # a new name is understood too, and moves with the folder
        (self.b / "ai-elements" / "characters" / "casting").mkdir(parents=True)
        self.assertEqual(R("ai-elements/characters/casting"), self.b / "ai-elements" / "characters" / "casting")
        self.assertEqual(R("ai-cast/casting"), self.b / "ai-elements" / "characters" / "casting")
        (self.b / "elements" / "index.json").write_text("{}")
        self.assertEqual(R("elements/index.json"), self.b / "elements" / "index.json")
        # a two-segment place
        (self.b / "channels" / "creators" / "x.md").parent.mkdir(parents=True)
        (self.b / "channels" / "creators" / "x.md").write_text("")
        self.assertEqual(R("channels/creators/x.md"), self.b / "channels" / "creators" / "x.md")
        # nothing in the map -> the plain join, untouched
        self.assertEqual(R("email/ledger.json"), self.b / "email" / "ledger.json")
        self.assertEqual(R("market.md"), self.b / "market.md")
        self.assertEqual(R("channels/other.md"), self.b / "channels" / "other.md")
        self.assertEqual(R("identity-anchors.md/x"), self.b / "identity-anchors.md" / "x")
        self.assertEqual(R(""), self.b)

    def test_no_brand_names_in_code(self):
        src = (HERE.parent / "brandpath.py").read_text().lower()
        repo = BP.repo()
        for p in (repo / "brands").iterdir():
            if p.is_dir() and not p.name.startswith(("_", ".")):
                self.assertNotIn(p.name.lower(), src, f"brand named in brandpath.py: {p.name}")


class RealRepo(unittest.TestCase):
    def test_every_brand_folders_json_parses_and_matches_plan_keys(self):
        repo = BP.repo()
        for p in (repo / "brands").iterdir():
            f = p / BP.FOLDERS_FILE
            if not f.is_file():
                continue
            data = json.loads(f.read_text())
            extra = {k for k in set(data) - set(BP.DEFAULTS) if not k.startswith("_") and k.split("/")[0] not in BP.DEFAULTS}
            self.assertEqual(extra, set(), f"{f} keys not in the plan: {sorted(extra)}")


if __name__ == "__main__":
    unittest.main()
