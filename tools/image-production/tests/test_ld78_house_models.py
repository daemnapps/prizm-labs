#!/usr/bin/env python3
"""LD-78 (house picture models) — image-production asks the Generative Model House which model does each picture
job and the judge, instead of keeping its own model ids.

    python3 tools/image-production/tests/test_ld78_house_models.py

(a) route.table() fills each picture row's and the judge's `vendor_model` from the house and names the job;
(b) changing the house's pictures.edit changes finish_entry() — and image_queue.py reaches that row only through the route —
    with no edit to image-production/models.json; (c) a missing house job, or a house door that is not the row's
    provider, is refused by name; (d) image-production/models.json names no vendor model on those rows and no file
    outside the route opens it; (e) asset-index tag.judge_entry() is the house's judge.

Fixtures: a temp copy of BOTH the house's models.json and the registry (components/models/models.json), pointed at
through model_house's own HOUSE and REGISTRY. Stdlib only; no network, no key, nothing written outside tempfile.
"""
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LANE = HERE.parent
REPO = LANE.parent.parent
sys.path.append(str(LANE))                         # APPEND — never insert at 0
import image_production as IP                      # noqa: E402
from image_production import route as R           # noqa: E402

JOBS = {("models", "gpt-image-person"): "pictures.generate", ("models", "gpt-image-edit"): "pictures.edit",
        ("models", "seedream-higgsfield"): "pictures.backup", ("models", "nano-banana-higgsfield"): "pictures.object",
        ("models", "gpt-image-openai-net"): "pictures.safety_net", ("judge",): "behind.judge"}
TABLE = LANE / "models.json"
QUEUE = LANE / "static" / "queue" / "image_queue.py"
TAG = REPO / "tools" / "asset-index" / "machine" / "tag.py"


def _row(t, where):
    for k in where:
        t = t[k]
    return t


def _vendor(answer):
    return answer if isinstance(answer, str) else answer["model"]


class _FixtureHouse(unittest.TestCase):
    """The route's own model_house, pointed at temp copies of the house and the registry for one test."""

    def setUp(self):
        self.mh = R._house()
        self.tmp = Path(tempfile.mkdtemp(prefix="ld78-"))
        self.house = json.loads(Path(self.mh.HOUSE).read_text())
        self.registry = json.loads(Path(self.mh.REGISTRY).read_text())
        real = (self.mh.HOUSE, self.mh.REGISTRY)
        self.mh.HOUSE, self.mh.REGISTRY = self.tmp / "house.json", self.tmp / "registry.json"
        self.addCleanup(lambda: (setattr(self.mh, "HOUSE", real[0]), setattr(self.mh, "REGISTRY", real[1])))
        self.write()

    def write(self):
        (self.tmp / "house.json").write_text(json.dumps(self.house))
        (self.tmp / "registry.json").write_text(json.dumps(self.registry))

    def add_edit_model(self, vendor_id):
        """A fixture registry entry sold at the higgsfield door (HOUSE-PIC-2), named by the house's pictures.edit."""
        self.registry["models"].append({"id": "ld78-fixture-edit", "vendor": "openai", "capability": ["image-edit"],
                                        "status": "draft", "transport": "api",
                                        "doors": {"higgsfield": {"vendor_id": vendor_id,
                                                                 "key_env": ["HIGGSFIELD_KEY_ID", "HIGGSFIELD_KEY_SECRET"]}}})
        self.house["pictures"]["edit"]["registry"] = "ld78-fixture-edit"
        self.write()


class A_TheHouseNamesEveryModel(_FixtureHouse):
    def test_a_every_row_carries_the_houses_model_and_its_job(self):
        t = R.table()
        for where, job in JOBS.items():
            row = _row(t, where)
            self.assertEqual(row["vendor_model"], _vendor(self.mh.model(job)), job)
            self.assertEqual(row["house_job"], job)

    def test_a_the_real_house_answers_todays_ids(self):
        self.mh.HOUSE, self.mh.REGISTRY = self.mh.HERE / "models.json", self.mh.HERE.parent / "models" / "models.json"
        t = R.table()
        self.assertEqual(t["models"]["gpt-image-person"]["vendor_model"], "gpt_image_2_5")     # the Higgsfield door, 2026-10-26
        self.assertEqual(t["models"]["gpt-image-edit"]["vendor_model"], "gpt_image_2_5")
        self.assertEqual(t["models"]["seedream-higgsfield"]["vendor_model"], "seedream_v5_pro")
        self.assertEqual(t["models"]["nano-banana-higgsfield"]["vendor_model"], "nano_banana_pro")
        self.assertEqual(R.judge_entry()["vendor_model"], "gemini-3.1-pro-preview")

    def test_a_a_callers_own_table_is_overlaid_too_unless_it_says_house_false(self):
        own = self.tmp / "own.json"
        own.write_text(TABLE.read_text())
        self.assertEqual(R.table(own)["models"]["gpt-image-edit"]["house_job"], "pictures.edit")
        bare = R.table(own, house=False)
        self.assertNotIn("vendor_model", bare["models"]["gpt-image-edit"])
        self.assertNotIn("house_job", bare["judge"])


class B_ChangingTheHouseChangesTheRun(_FixtureHouse):
    def test_b_the_houses_edit_model_reaches_finish_entry_with_no_edit_to_the_table(self):
        before = hashlib.sha256(TABLE.read_bytes()).hexdigest()
        self.add_edit_model("ld78-edit-model-x")
        self.assertEqual(IP.finish_entry()["vendor_model"], "ld78-edit-model-x")
        self.assertEqual(R.table()["models"]["gpt-image-edit"]["vendor_model"], "ld78-edit-model-x")
        self.assertEqual(R.table()["models"]["gpt-image-person"]["vendor_model"],
                         _vendor(self.mh.model("pictures.generate")), "only the edit job moved")
        self.assertEqual(hashlib.sha256(TABLE.read_bytes()).hexdigest(), before)

    def test_b_queue_reaches_the_edit_row_only_through_the_route(self):
        src = QUEUE.read_text()
        self.assertNotIn("image-production/models.json", src)
        self.assertNotIn("models.json\").read_text", src)
        line = [x for x in src.splitlines() if re.search(r"\bentry = .*gpt-image-edit", x)]
        self.assertEqual(len(line), 1, line)
        self.assertIn('R.table()["models"]["gpt-image-edit"]', line[0])
        self.assertIn("from image_production import route as R", line[0])
        # ...and that route row is the house's: the same change moves it.
        self.add_edit_model("ld78-edit-model-y")
        self.assertEqual(R.table()["models"]["gpt-image-edit"]["vendor_model"], "ld78-edit-model-y")


class C_RefusedByName(_FixtureHouse):
    def test_c_a_missing_house_job_is_refused_naming_it(self):
        del self.house["pictures"]["object"]
        self.write()
        with self.assertRaises(R.NoRoute) as e:
            R.table()
        self.assertIn("pictures.object", str(e.exception))
        self.assertIn("MODEL-HOUSE.md", str(e.exception))

    def test_c_a_missing_judge_is_refused_naming_it(self):
        del self.house["behind"]["judge"]
        self.write()
        with self.assertRaises(R.NoRoute) as e:
            R.judge_entry()
        self.assertIn("behind.judge", str(e.exception))

    def test_c_a_house_door_that_is_not_the_rows_provider_is_refused(self):
        self.house["pictures"]["edit"]["door"] = "fal"      # the same model, sold by fal: not this row's door
        self.write()
        with self.assertRaises(R.NoRoute) as e:
            R.table()
        self.assertIn("pictures.edit", str(e.exception))
        self.assertIn("'fal'", str(e.exception))
        self.assertIn("MODEL-HOUSE.md", str(e.exception))

    def test_c_never_a_silent_fallback_to_a_local_id(self):
        del self.house["pictures"]["generate"]
        self.write()
        own = self.tmp / "own.json"
        t = json.loads(TABLE.read_text())
        t["models"]["gpt-image-person"]["vendor_model"] = "a-local-id"
        own.write_text(json.dumps(t))
        with self.assertRaises(R.NoRoute):
            R.table(own)


class D_OneReader(unittest.TestCase):
    def test_d_the_table_names_no_vendor_model_on_the_house_rows(self):
        t = json.loads(TABLE.read_text())
        for where, job in JOBS.items():
            self.assertNotIn("vendor_model", _row(t, where), job)
        self.assertIn("generative-model-house", t["_what"])

    def test_d_no_file_outside_the_route_opens_image_production_models_json(self):
        out = subprocess.run(["git", "grep", "-n", "-E", r"image-production[\"' /,]*models\.json", "--",
                              "components/*.py"], cwd=str(REPO), capture_output=True, text=True)
        self.assertIn(out.returncode, (0, 1), out.stderr)
        opens = [x for x in out.stdout.splitlines()
                 if re.search(r"read_text|read_bytes|open\(|json\.load", x)
                 and not x.startswith("tools/image-production/tests/test_ld78_house_models.py")]
        self.assertEqual(opens, [])


def _load_tag():
    """asset-index's tag.py, by path. It draws contact sheets with PIL at import; an interpreter without PIL gets a
    stand-in — judge_entry() never draws."""
    try:
        import PIL  # noqa: F401
    except ImportError:
        pil = types.ModuleType("PIL")
        for name in ("Image", "ImageDraw", "ImageFont"):
            sub = types.ModuleType("PIL." + name)
            setattr(pil, name, sub)
            sys.modules["PIL." + name] = sub
        pil.ImageFont.load_default = lambda *a, **k: None
        sys.modules["PIL"] = pil
    spec = importlib.util.spec_from_file_location("ld78_tag", TAG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class E_AssetIndexJudge(_FixtureHouse):
    def test_e_tag_judge_entry_is_the_houses_judge(self):
        tag = _load_tag()
        self.assertEqual(tag.judge_entry()["vendor_model"], self.mh.model("behind.judge"))
        self.assertEqual(tag.judge_entry()["house_job"], "behind.judge")
        self.assertNotIn("models.json", Path(TAG).read_text().split("def judge_entry")[1].split("\ndef ")[0])

    def test_e_moving_the_houses_judge_moves_tag(self):
        self.registry["models"].append(copy.deepcopy(next(m for m in self.registry["models"]
                                                          if m["id"] == "gemini-3.1-pro-preview")))
        self.registry["models"][-1].update(id="ld78-fixture-judge", vendor_id="ld78-judge-model")
        self.house["behind"]["judge"]["registry"] = "ld78-fixture-judge"
        self.write()
        self.assertEqual(_load_tag().judge_entry()["vendor_model"], "ld78-judge-model")


if __name__ == "__main__":
    unittest.main()
