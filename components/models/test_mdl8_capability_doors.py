"""MDL-8 (registry-linked house) — the registry's `doors` and `capability` fields.

    python3 components/models/test_mdl8_capability_doors.py

Proves, with no network and no key: the real registry validates (exit 0) and the selftest covers a bad door shape,
an unknown capability and a value-shaped door key_env; those three are refused through the same function the real
file goes through; gpt-image-2.5 is ONE entry with TWO doors; every model the Generative Model House names is
filed with the capability and doors the card gives it; every key a door names is declared in the keys register;
and validating writes nothing. Must run on /usr/bin/python3 (3.9).
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATE = os.path.join(HERE, "validate.py")
MODELS = os.path.join(HERE, "models.json")
KEY_NAMES = os.path.join(os.path.dirname(HERE), "keys", "names.json")

_spec = importlib.util.spec_from_file_location("mdl8_validate", VALIDATE)
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

UNPRICED = "not priced at filing; the curator prices it at approval"
HF = ["HIGGSFIELD_KEY_ID", "HIGGSFIELD_KEY_SECRET"]

# The card's new draft entries: id -> (vendor, capability, {door: (vendor_id, key_env)}).
NEW = {
    "seedream-5-pro-edit": ("bytedance", ["image-edit"],
                            {"fal": ("bytedance/seedream/v5/pro/edit", "FAL_KEY")}),
    "seedance-2.5": ("bytedance", ["video-from-image"], {"higgsfield": ("seedance_2_5", HF)}),
    "kling-4.0": ("kling", ["video-from-image"], {"higgsfield": ("kling4_0", HF)}),
    "higgsfield-object-swap": ("higgsfield", ["video-object-swap"],
                               {"higgsfield": ("hf_mult_replace_object", HF)}),
    "higgsfield-motion-control": ("higgsfield", ["video-motion-transfer"],
                                  {"higgsfield": ("hf_mult_motion_control", HF)}),
    "eleven-v3": ("elevenlabs", ["voice-tts"], {"elevenlabs": ("eleven_v3", "ELEVENLABS_API_KEY")}),
    "eleven-ttv-v3": ("elevenlabs", ["voice-design"], {"elevenlabs": ("eleven_ttv_v3", "ELEVENLABS_API_KEY")}),
    "eleven-music-v2.5": ("elevenlabs", ["music"], {"elevenlabs": ("music_v2_5", "ELEVENLABS_API_KEY")}),
    "bytedance-upscaler-video": ("bytedance", ["upscale-video"],
                                 {"fal": ("fal-ai/bytedance-upscaler/upscale/video", "FAL_KEY")}),
    "real-esrgan": (None, ["upscale-video"], {"local": ("real-esrgan (local)", None)}),
}
# Existing entries that gain a capability because the house uses them.
EXISTING = {
    "scribe_v1": ["transcribe"],
    "scribe_v2": ["transcribe", "diarize"],
    "gemini-3.1-pro-preview": ["judge-vision"],
    "gemini-3.5-flash": ["judge-vision"],
    "gemini-3-flash-preview": ["judge-vision"],
    "trellis.2-4b": ["3d-from-image"],
    "gemini-3-pro-image": ["image-generate", "image-edit"],
    "gpt-image-2.5": ["image-generate", "image-edit"],
}

GOOD = {"id": "fixture-doors", "label": "Fixture", "vendor": "fixture", "aliases": [], "modality": ["image"],
        "capability": ["image-edit"], "cost": "unpriced", "cost_reason": "fixture — never called",
        "status": "draft", "key_env": None, "transport": "api",
        "doors": {"fixture-door": {"vendor_id": "fixture/x/edit", "key_env": "FIXTURE_API_KEY"}}}


def _with(**changes):
    out = dict(GOOD)
    out.update(changes)
    return out


def _findings(entry):
    return V.validate_models({"schema": 1, "models": [entry]})


def _real():
    with open(MODELS) as handle:
        return {m["id"]: m for m in json.load(handle)["models"]}


def _door_sold(entry, door):
    if entry.get("doors"):
        return entry["doors"].get(door)
    own = "local" if entry.get("transport") == "local" else entry.get("vendor")
    if door != own:
        return None
    return {"vendor_id": entry.get("vendor_id"), "key_env": entry.get("key_env")}


def _run(*args):
    return subprocess.run([sys.executable, VALIDATE] + list(args), cwd=HERE, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)


class TheValidator(unittest.TestCase):
    def test_the_real_registry_is_valid(self):
        before = hashlib.sha256(open(MODELS, "rb").read()).hexdigest()
        r = _run()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("valid:", r.stdout)
        self.assertEqual(before, hashlib.sha256(open(MODELS, "rb").read()).hexdigest(),
                         "validating must write nothing")

    def test_the_selftest_covers_the_three_new_refusals(self):
        r = _run("--selftest")
        self.assertEqual(r.returncode, 0, r.stdout)
        for label in ("REJECT: a door name that is not door-shaped",
                      "REJECT: an unknown capability",
                      "REJECT: a value-shaped door key_env",
                      "REJECT: a value-shaped name inside a two-part door key",
                      "CONTROL: doors (one two-part key) and a capability list pass"):
            self.assertIn("ok   " + label, r.stdout)

    def test_the_control_passes(self):
        self.assertEqual(_findings(GOOD), [])
        self.assertEqual(_findings(_with(doors={"higgsfield": {"vendor_id": "x_y", "key_env": HF}})), [])

    def test_a_bad_door_shape_is_refused_naming_the_entry(self):
        for doors, says in (({"Fal Door": {"vendor_id": "x", "key_env": "FAL_KEY"}}, "not door-shaped"),
                            ({"fal": "x/y"}, "doors.fal must be an object"),
                            ({"fal": {"vendor_id": "x"}}, "doors.fal.key_env is missing"),
                            ({"fal": {"vendor_id": "x", "key_env": "FAL_KEY", "usd": 1}}, "not a door field"),
                            ({}, "non-empty object")):
            found = _findings(_with(doors=doors))
            self.assertTrue(any(says in f and "fixture-doors" in f for f in found), (doors, found))

    def test_an_unknown_capability_is_refused(self):
        found = _findings(_with(capability=["image-edit", "telepathy"]))
        self.assertTrue(any("capability 'telepathy' is unknown" in f and "fixture-doors" in f for f in found),
                        found)
        self.assertTrue(_findings(_with(capability=[])))
        self.assertTrue(_findings(_with(capability="image-edit")))

    def test_a_value_shaped_door_key_is_refused(self):
        for key in ("zz-fixture-notarealkey-3f9a2b7c1d4e5f60", "ZZQA1234567890ABCD",
                    ["HIGGSFIELD_KEY_ID", "ZZQA1234567890ABCD"], []):
            found = _findings(_with(doors={"fal": {"vendor_id": "x", "key_env": key}}))
            self.assertTrue(any("doors.fal.key_env" in f for f in found), (key, found))

    def test_an_api_door_must_name_its_key_and_a_local_door_none(self):
        self.assertTrue(any("An api door spends a key" in f
                            for f in _findings(_with(doors={"fal": {"vendor_id": "x", "key_env": None}}))))
        local = _with(transport="local", cost={"usd_per_run": 0}, cost_reason="our own machine",
                      doors={"local": {"vendor_id": "x (local)", "key_env": "FAL_KEY"}})
        self.assertTrue(any("Local weights spend no key" in f for f in _findings(local)))

    def test_an_api_entry_with_no_doors_still_names_its_key(self):
        entry = dict(GOOD)
        entry.pop("doors")
        self.assertTrue(any("`key_env` is null" in f for f in _findings(entry)))


class TheRegistry(unittest.TestCase):
    def setUp(self):
        self.m = _real()

    def test_gpt_image_is_one_entry_with_two_doors(self):
        e = self.m["gpt-image-2.5"]
        self.assertIn("gpt-image-2.5-sunburst", e["aliases"])
        self.assertEqual(e["doors"], {
            "openai": {"vendor_id": "gpt-image-2.5-sunburst", "key_env": "OPENAI_API_KEY"},
            "fal": {"vendor_id": "openai/gpt-image-2.5/sunburst/edit", "key_env": "FAL_KEY"}})
        self.assertEqual(e["capability"], ["image-generate", "image-edit"])
        self.assertNotIn("gpt-image-2.5-sunburst", self.m, "sunburst stays an alias, not a second entry")

    def test_the_new_entries_are_drafts_filed_as_the_card_gives_them(self):
        for rid, (vendor, capability, doors) in sorted(NEW.items()):
            e = self.m.get(rid)
            self.assertIsNotNone(e, rid)
            self.assertEqual(e["status"], "draft", rid)
            self.assertEqual(e["capability"], capability, rid)
            if vendor:
                self.assertEqual(e["vendor"], vendor, rid)
            if rid == "real-esrgan":
                self.assertEqual(e["transport"], "local")
                self.assertIsNone(e["key_env"])
                self.assertEqual(e["cost"], {"usd_per_run": 0})
                self.assertTrue(e["cost_reason"])
            else:
                self.assertEqual(e["transport"], "api", rid)
                self.assertEqual(e["cost"], "unpriced", rid)
                self.assertTrue(e["cost_reason"].startswith(UNPRICED), rid)
            self.assertTrue(any("components/generative-model-house/models.json" in s for s in e["sources"]), rid)
            for door, (vendor_id, key_env) in doors.items():
                sold = _door_sold(e, door)
                self.assertIsNotNone(sold, (rid, door))
                self.assertEqual(sold["vendor_id"] or rid, vendor_id, (rid, door))
                self.assertEqual(sold["key_env"], key_env, (rid, door))
            if e.get("doors"):
                self.assertEqual(sorted(e["doors"]), sorted(doors), rid)

    def test_existing_entries_gain_their_capability(self):
        for rid, capability in sorted(EXISTING.items()):
            self.assertEqual(self.m[rid]["capability"], capability, rid)

    def test_every_door_key_is_declared_in_the_keys_register(self):
        with open(KEY_NAMES) as handle:
            declared = set(json.load(handle)["names"])
        named = set()
        for e in self.m.values():
            for spec in (e.get("doors") or {}).values():
                k = spec.get("key_env")
                named.update(k if isinstance(k, list) else ([k] if k else []))
        self.assertTrue(named)
        self.assertEqual(sorted(named - declared), [])

    def test_every_capability_is_on_the_closed_list(self):
        for e in self.m.values():
            for c in e.get("capability", []):
                self.assertIn(c, V.CAPABILITIES, e["id"])


if __name__ == "__main__":
    unittest.main()
