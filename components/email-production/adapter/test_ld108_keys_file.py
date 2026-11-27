"""LD-108 (picture tries keys file): a picture try reads the door keys from the one key file
(~/.upright-keys.env, through components/keys/loader.py), not only the shell's environment.

Found 2026-11-11 by editor's Claude: on a Mac whose Higgsfield keys lived only in the key file, try_picture.choose()
refused "no HIGGSFIELD_KEY_ID", because selectable() and model_house.pick read os.environ alone.
Run: /usr/bin/python3 -m unittest test_ld108_keys_file  (from this folder)
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import try_picture as TP  # noqa: E402

PICK = "gpt-image-2.5@higgsfield"
NAMES = ("HIGGSFIELD_KEY_ID", "HIGGSFIELD_KEY_SECRET", "HF_API_KEY_ID", "HF_API_KEY_SECRET")


class KeysFile(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        base = {k: v for k, v in os.environ.items() if k not in NAMES and k != "KEYS_NO_FALLBACK"}
        base["HOME"] = self.home
        p = mock.patch.dict(os.environ, base, clear=True)
        p.start()
        self.addCleanup(p.stop)

    def _file(self, text):
        Path(self.home, ".upright-keys.env").write_text(text)

    def test_1_a_key_only_in_the_key_file_is_found(self):
        self._file("HIGGSFIELD_KEY_ID=fake-id\nHIGGSFIELD_KEY_SECRET=fake-secret\n")
        got = TP.choose(PICK)
        self.assertEqual((got["registry_id"], got["door"]), ("gpt-image-2.5", "higgsfield"))
        sel = {s["label"]: s for s in TP.selectable()}
        self.assertTrue(sel[PICK]["has_key"])

    def test_2_a_key_found_nowhere_is_still_refused_by_name(self):
        self._file("SOME_OTHER_KEY=x\n")                       # a key file exists, so no old places are read
        with self.assertRaises(KeyError) as e:
            TP.choose(PICK)
        self.assertIn("HIGGSFIELD_KEY_ID", str(e.exception))
        self.assertFalse({s["label"]: s for s in TP.selectable()}[PICK]["has_key"])

    def test_3_an_env_passed_in_is_used_as_given(self):
        self._file("HIGGSFIELD_KEY_ID=fake-id\nHIGGSFIELD_KEY_SECRET=fake-secret\n")
        with self.assertRaises(KeyError):
            TP.choose(PICK, env={})                           # callers (and the LD-83 tests) keep full control

    def test_4_no_value_reaches_the_refusal(self):
        self._file("HIGGSFIELD_KEY_ID=fake-id\n")             # the secret is missing
        with self.assertRaises(KeyError) as e:
            TP.choose(PICK)
        self.assertNotIn("fake-id", str(e.exception))


if __name__ == "__main__":
    unittest.main()
