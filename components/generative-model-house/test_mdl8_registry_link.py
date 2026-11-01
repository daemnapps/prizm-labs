"""MDL-8 (registry-linked house) — the house names each job's model BY REGISTRY ID and still answers what it always did.

    python3 components/generative-model-house/test_mdl8_registry_link.py

No network, no key; must run on /usr/bin/python3 (3.9). Proves: (b) every model-naming row resolves to a
non-deprecated registry entry that sells its door and lists its capability; (c) model() answers the same vendor
strings, under the same keys, for all 23 slots — FROZEN below from the house as it answered before this card — and
so do the three callers' own readers; refusals are by name; (d) choices(); (e) pick(); (f) no file outside this
folder opens the house's models.json.
"""
import copy
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

import model_house as MH

HERE = Path(__file__).resolve().parent
COMPONENTS = HERE.parent
REPO = COMPONENTS.parent

# Today's answers (read off model_house.model() at the card's base, before the registry link): job -> the key the
# vendor's name sits under (None = a bare string; "models" = a list), that name, and every key the answer carried.
FROZEN = {
    "pictures.generate": ("model", "gpt_image_2_5", ["door", "model", "rule"]),
    "pictures.edit": ("model", "gpt_image_2_5", ["door", "model", "rule"]),
    "pictures.backup": ("model", "seedream_v5_pro", ["door", "model", "record", "rule", "verified"]),
    "pictures.object": ("model", "nano_banana_pro", ["door", "model", "rule"]),
    "pictures.safety_net": ("model", "gpt-image-2.5-sunburst", ["door", "model", "rule"]),
    "clips.seedance": ("id", "seedance_2_5", ["bad_at", "door", "good_at", "id"]),
    "clips.backup": ("id", "kling4_0", ["bad_at", "door", "good_at", "id", "role"]),
    "swipe_footage.swap": ("id", "hf_mult_replace_object", ["_api", "api", "door", "id"]),
    "swipe_footage.motion_transfer": ("id", "hf_mult_motion_control", ["door", "id", "when"]),
    "sound.voice": ("model", "eleven_v3", ["door", "how", "model"]),
    "sound.voice_design": ("model", "eleven_ttv_v3", ["door", "how", "model", "ruled"]),
    "sound.music_bed": ("model", "music_v2_5", ["door", "model", "ruled"]),
    "sound.song": ("model", "suno", ["door", "how", "model", "ruled"]),   # 2026-10-28: Suno for every song ad
    "sound.words": ("model", "scribe_v1", ["door", "model"]),
    "sound.speakers": ("model", "scribe_v2", ["door", "how", "model"]),
    "behind.judge": (None, "gemini-3.1-pro-preview", None),
    "behind.upscale": (None, "real-esrgan (local)", None),
    "behind.upscale_alternate": ("model", "bytedance_video_upscale", ["door", "model", "rule"]),
    "behind.3d": (None, "trellis.2 (local)", None),
    "behind.judge_busy": ("models", ["gemini-3.5-flash", "gemini-3-flash-preview"], ["how", "models"]),
    "behind.fast_read": ("model", "gemini-3-flash-preview", ["how", "model"]),
}
FROZEN_DOORS = {
    "pictures.generate": "higgsfield", "pictures.edit": "higgsfield", "pictures.backup": "higgsfield",
    "pictures.object": "higgsfield", "pictures.safety_net": "openai",
    "clips.seedance": "higgsfield", "clips.backup": "higgsfield",
    "swipe_footage.swap": "higgsfield", "swipe_footage.motion_transfer": "higgsfield",
    "sound.voice": "elevenlabs", "sound.voice_design": "elevenlabs", "sound.music_bed": "elevenlabs",
    "sound.song": "suno", "sound.words": "elevenlabs", "sound.speakers": "elevenlabs",
    "behind.upscale_alternate": "higgsfield",
}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rows(node, path=""):
    if isinstance(node, dict) and "registry" in node:
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _rows(v, f"{path}.{k}" if path else k)


class _Patched(unittest.TestCase):
    """Runs model_house against an in-memory house and registry, then puts the real ones back."""

    def patch(self, house=None, registry=None):
        h = copy.deepcopy(house if house is not None else MH.house())
        r = copy.deepcopy(registry if registry is not None else MH.registry())
        real_h, real_r = MH.house, MH.registry
        MH.house, MH.registry = (lambda: copy.deepcopy(h)), (lambda: copy.deepcopy(r))
        self.addCleanup(setattr, MH, "house", real_h)
        self.addCleanup(setattr, MH, "registry", real_r)
        return h, r


class EveryRowResolves(unittest.TestCase):
    def test_b_every_model_naming_row_names_a_live_registry_entry_that_sells_its_door(self):
        models = {m["id"]: m for m in MH.registry()["models"]}
        rows = list(_rows(MH.house()))
        self.assertEqual(sorted(set(FROZEN) - {p for p, _ in rows}), [], "every frozen job is a registry row")
        slots = 0
        for job, row in rows:
            self.assertEqual(sorted(k for k in ("registry", "door", "capability") if k in row),
                             ["capability", "door", "registry"], job)
            for banned in ("model", "id", "models", "key_env", "cost", "vendor_id"):
                self.assertNotIn(banned, row, f"{job} carries a vendor string, key or price of its own")
            ids = row["registry"] if isinstance(row["registry"], list) else [row["registry"]]
            for rid in ids:
                slots += job in FROZEN
                entry = models.get(rid)
                self.assertIsNotNone(entry, f"{job}: {rid}")
                self.assertNotEqual(entry["status"], "deprecated", f"{job}: {rid}")
                if entry.get("doors"):
                    self.assertIn(row["door"], entry["doors"], f"{job}: {rid}")
                else:
                    own = "local" if entry["transport"] == "local" else entry["vendor"]
                    self.assertEqual(row["door"], own, f"{job}: {rid}")
                self.assertIn(row["capability"], entry.get("capability", []), f"{job}: {rid}")
        self.assertEqual(slots, 22)       # +1 on 2026-10-26: the picture ladder (generate, edit, backup, object, safety_net), minus the retired overflow

    def test_rows_that_name_no_model_are_untouched(self):
        self.assertEqual(MH.model("clips.ruled_2026_10_23")["talking"], "seedance")
        self.assertNotIn("registry", MH.house()["clips"]["ruled_2026_10_23"])


class TheReturnShapeHolds(unittest.TestCase):
    def test_c_every_slot_answers_todays_vendor_string_under_todays_key(self):
        for job, (key, vendor, keys) in sorted(FROZEN.items()):
            got = MH.model(job)
            if key is None:
                self.assertEqual(got, vendor, job)
                self.assertIsInstance(got, str, job)
                continue
            self.assertEqual(got[key], vendor, job)
            for k in keys:
                self.assertIn(k, got, f"{job} lost the key {k!r}")
            if job in FROZEN_DOORS:
                self.assertEqual(got["door"], FROZEN_DOORS[job], job)

    def test_dict_answers_add_the_registry_facts(self):
        a = MH.model("pictures.edit")
        self.assertEqual((a["registry_id"], a["key_env"], a["transport"]),
                         ("gpt-image-2.5", ["HIGGSFIELD_KEY_ID", "HIGGSFIELD_KEY_SECRET"], "api"))
        self.assertIn("cost", a)
        o = MH.model("pictures.safety_net")
        self.assertEqual((o["registry_id"], o["key_env"]), ("gpt-image-2.5", "OPENAI_API_KEY"))
        s = MH.model("clips.seedance")
        self.assertEqual(s["key_env"], ["HIGGSFIELD_KEY_ID", "HIGGSFIELD_KEY_SECRET"])
        b = MH.model("behind.judge_busy")
        self.assertEqual(b["registry_id"], ["gemini-3.5-flash", "gemini-3-flash-preview"])
        self.assertEqual(MH.model("behind.judge_busy.models"), ["gemini-3.5-flash", "gemini-3-flash-preview"])
        self.assertEqual(MH.model("pictures.edit.model"), "gpt_image_2_5")

    def test_the_callers_readers_answer_the_same(self):
        vp = _load("mdl8_vp_house", COMPONENTS / "video-production" / "machine" / "house.py")
        self.assertEqual(vp.judge(), "gemini-3.1-pro-preview")
        self.assertEqual(vp.clip("seedance")["id"], FROZEN["clips.seedance"][1])
        self.assertEqual(vp.voice_model(), "eleven_v3")
        self.assertEqual(vp.voice_design_model(), "eleven_ttv_v3")
        self.assertEqual(vp.swap()["id"], "hf_mult_replace_object")
        self.assertEqual(vp.words_model(), "scribe_v1")
        self.assertEqual(vp.picture_model("edit"), "gpt_image_2_5")
        self.assertEqual(vp.picture_overflow(), {})                  # the fal overflow is retired
        self.assertEqual(vp.picture_backup(), "seedream_v5_pro")
        self.assertEqual(vp.picture_object(), "nano_banana_pro")
        self.assertEqual(vp.picture_safety_net(), "gpt-image-2.5-sunburst")
        self.assertEqual(vp.upscale(), "real-esrgan (local)")
        self.assertEqual(vp.upscale_alternate()["model"], "bytedance_video_upscale")
        vt = _load("mdl8_vt_house", COMPONENTS / "video-teardown" / "machine" / "house.py")
        self.assertEqual(vt.model_id("behind.judge"), "gemini-3.1-pro-preview")
        self.assertEqual(vt.model_id("sound.voice"), "eleven_v3")
        self.assertEqual(vt.model_ids("behind.judge_busy"), ["gemini-3.5-flash", "gemini-3-flash-preview"])
        at = _load("mdl8_at_house", COMPONENTS / "audio-teardown" / "house_models.py")
        self.assertEqual(at.model_id("sound.speakers"), "scribe_v2")
        self.assertEqual(at.model_ids("behind.judge_busy"), ["gemini-3.5-flash", "gemini-3-flash-preview"])

    def test_a_tool_gets_the_default_whatever_keys_the_machine_has(self):
        self.assertEqual(MH.model("pictures.edit")["model"], "gpt_image_2_5")


class RefusedByName(_Patched):
    def test_an_unknown_job_is_still_refused(self):
        with self.assertRaises(KeyError):
            MH.model("clips.kling")

    def test_a_registry_id_the_registry_lacks(self):
        h, _ = self.patch()
        h["clips"]["seedance"]["registry"] = "seedance-that-never-was"
        self.patch(house=h)
        with self.assertRaises(KeyError) as ctx:
            MH.model("clips.seedance")
        self.assertIn("clips.seedance", str(ctx.exception))
        self.assertIn("seedance-that-never-was", str(ctx.exception))

    def test_a_deprecated_registry_id(self):
        _, r = self.patch()
        for m in r["models"]:
            if m["id"] == "gemini-3.1-pro-preview":
                m["status"] = "deprecated"
        self.patch(registry=r)
        with self.assertRaises(KeyError) as ctx:
            MH.model("behind.judge")
        self.assertIn("behind.judge", str(ctx.exception))
        self.assertIn("deprecated", str(ctx.exception))

    def test_a_door_the_entry_does_not_sell(self):
        h, _ = self.patch()
        h["pictures"]["edit"]["door"] = "google"
        self.patch(house=h)
        with self.assertRaises(KeyError) as ctx:
            MH.model("pictures.edit")
        self.assertIn("gpt-image-2.5", str(ctx.exception))
        self.assertIn("google", str(ctx.exception))

    def test_a_deprecated_model_is_never_offered(self):
        _, r = self.patch()
        for m in r["models"]:
            if m["id"] == "seedream-5-pro-edit":
                m["status"] = "deprecated"
        self.patch(registry=r)
        self.assertNotIn("seedream-5-pro-edit", [c["registry_id"] for c in MH.choices("pictures.edit")])


class Choices(unittest.TestCase):
    def test_d_the_house_default_first_then_the_open_pool(self):
        c = MH.choices("pictures.edit")
        self.assertEqual((c[0]["registry_id"], c[0]["door"], c[0]["vendor_id"], c[0]["reason"]),
                         ("gpt-image-2.5", "higgsfield", "gpt_image_2_5", "house default"))
        pairs = [(x["registry_id"], x["door"]) for x in c]
        for want in (("seedream-5-pro-edit", "higgsfield"), ("gpt-image-2.5", "openai")):
            self.assertIn(want, pairs)
        self.assertEqual(len(pairs), len(set(pairs)), "one choice per model per door")
        self.assertEqual(pairs[1:], sorted(pairs[1:]), "stable order: registry id, then door")
        for x in c[1:]:
            self.assertEqual(x["reason"], "eligible: image-edit")
        statuses = {m["id"]: m["status"] for m in MH.registry()["models"]}
        self.assertNotIn("deprecated", [statuses[x["registry_id"]] for x in c])
        for x in c:
            self.assertEqual(sorted(x), ["door", "key_env", "reason", "registry_id", "status", "vendor_id"])

    def test_d_purpose_is_accepted_and_ignored(self):
        for job in ("pictures.edit", "clips.seedance", "behind.judge_busy", "behind.upscale"):
            self.assertEqual(MH.choices(job, purpose="anything"), MH.choices(job))

    def test_a_list_row_offers_its_defaults_in_order(self):
        c = MH.choices("behind.judge_busy")
        self.assertEqual([x["registry_id"] for x in c[:2]], ["gemini-3.5-flash", "gemini-3-flash-preview"])
        self.assertEqual([x["reason"] for x in c[:2]], ["house default", "house default"])

    def test_a_row_that_names_no_model_has_no_choices(self):
        with self.assertRaises(KeyError):
            MH.choices("clips.ruled_2026_10_23")


class Pick(unittest.TestCase):
    ENV = {"OPENAI_API_KEY": "fixture", "GEMINI_API_KEY": "fixture", "HIGGSFIELD_KEY_ID": "fixture", "HIGGSFIELD_KEY_SECRET": "fixture"}

    def test_e_no_model_is_the_house_default(self):
        p = MH.pick("pictures.edit", env=self.ENV)
        self.assertEqual((p["registry_id"], p["door"], p["vendor_id"]),
                         ("gpt-image-2.5", "higgsfield", "gpt_image_2_5"))

    def test_e_an_eligible_pick_with_its_key(self):
        p = MH.pick("pictures.edit", "gemini-3-pro-image@google", env=self.ENV)
        self.assertEqual((p["vendor_id"], p["door"], p["key_env"]), ("gemini-3-pro-image", "google", "GEMINI_API_KEY"))

    def test_e_an_ineligible_model_is_refused_by_name(self):
        with self.assertRaises(KeyError) as ctx:
            MH.pick("pictures.edit", "eleven-v3", env=self.ENV)
        self.assertIn("eleven-v3", str(ctx.exception))
        self.assertIn("pictures.edit", str(ctx.exception))

    def test_e_a_missing_key_is_refused_by_name_never_swapped(self):
        with self.assertRaises(KeyError) as ctx:
            MH.pick("pictures.edit", "seedream-5-pro-edit@fal", env=self.ENV)
        self.assertIn("seedream-5-pro-edit@fal needs FAL_KEY, which this machine does not have", str(ctx.exception))
        with self.assertRaises(KeyError) as ctx:
            MH.pick("clips.seedance", env={"HIGGSFIELD_KEY_ID": "fixture"})
        self.assertIn("HIGGSFIELD_KEY_SECRET", str(ctx.exception))
        self.assertNotIn("HIGGSFIELD_KEY_ID and", str(ctx.exception))
        with self.assertRaises(KeyError) as ctx:
            MH.pick("clips.seedance", env={})
        self.assertIn("needs HIGGSFIELD_KEY_ID and HIGGSFIELD_KEY_SECRET", str(ctx.exception))

    def test_e_two_doors_must_be_named(self):
        with self.assertRaises(KeyError) as ctx:
            MH.pick("pictures.edit", "gpt-image-2.5", env={"OPENAI_API_KEY": "x", "FAL_KEY": "x"})
        self.assertIn("gpt-image-2.5@fal", str(ctx.exception))
        p = MH.pick("pictures.edit", "gpt-image-2.5@fal", env={"FAL_KEY": "x"})
        self.assertEqual(p["vendor_id"], "openai/gpt-image-2.5/sunburst/edit")

    def test_a_local_model_needs_no_key(self):
        self.assertEqual(MH.pick("behind.upscale", env={})["vendor_id"], "real-esrgan (local)")


_OPENS = ("open(", "read_text", "load(", " / ", "Path(", "join(", "cat ", "require(", "readFile")


def _opens_house_file(rel, line):
    """A code line (comment stripped) that names the house folder AND its models.json AND a way to read a file."""
    code = line.split("#", 1)[0] if rel.endswith((".py", ".sh")) else line.split("//", 1)[0]
    return "generative-model-house" in code and "models.json" in code and any(o in code for o in _OPENS)


class NobodyElseOpensTheHouseFile(unittest.TestCase):
    def test_the_check_fires_and_releases(self):
        self.assertTrue(_opens_house_file("x.py", 'H = ROOT / "generative-model-house" / "models.json"'))
        self.assertTrue(_opens_house_file("x.js", "readFile('components/generative-model-house/models.json')"))
        self.assertFalse(_opens_house_file("x.py", "that names a model is `components/generative-model-house/"
                                                   "models.json`; this file only opens its public reader,"))
        self.assertFalse(_opens_house_file("x.py", 'R = ROOT / "generative-model-house" / "model_house.py"'))
        self.assertFalse(_opens_house_file("x.py", '# open(ROOT / "generative-model-house" / "models.json")'))

    def test_f_no_file_outside_the_house_opens_its_models_json(self):
        out = subprocess.run(["git", "grep", "-l", "generative-model-house", "--", "*.py", "*.sh", "*.js",
                              "*.mjs", "*.ts"], cwd=str(REPO), stdout=subprocess.PIPE, universal_newlines=True)
        self.assertIn(out.returncode, (0, 1))
        self.assertTrue(out.stdout.split(), "git grep found not even the callers — the check would prove nothing")
        offenders = []
        for rel in out.stdout.split():
            if rel.startswith("components/generative-model-house/"):
                continue
            for line in (REPO / rel).read_text(errors="replace").splitlines():
                if _opens_house_file(rel, line):
                    offenders.append(f"{rel}: {line.strip()}")
        self.assertEqual(offenders, [], "read the house through model_house.model(job), never its file")


if __name__ == "__main__":
    unittest.main()
