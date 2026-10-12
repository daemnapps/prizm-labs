#!/usr/bin/env python3
"""python3 machine/test_spoken.py — numbers said as words, and the brand's
protected words: the swap, the voice body, the audio gate and the song. Fakes
only, no network, never reads brands/ (the lexicon root is a temp folder)."""
from __future__ import annotations

import base64
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(f"t_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sn = load("spoken_numbers")
lx = load("lexicon")

ROWS = [
    {"term": "Velune", "say_as": "veh-loon", "kind": "brand", "confirmed": True, "source": "t"},
    {"term": "Centella", "say_as": "sen-TEL-uh", "kind": "ingredient", "confirmed": False, "source": "t"},
    {"term": "Centella Asiatica", "say_as": "sen-TEL-uh uh-SEE-uh-tih-kuh", "kind": "ingredient",
     "confirmed": False, "source": "t"},
    {"term": "Glow Lock", "say_as": "Glow Lock", "kind": "mechanism", "confirmed": True, "source": "t"},
    {"term": "WAR", "say_as": "war", "kind": "product", "confirmed": False, "source": "t"},
    {"term": "Vitamin B3", "say_as": "vitamin B three", "kind": "ingredient", "confirmed": True, "source": "t"},
]


# ------------------------------------------------------------------ numbers

class EveryRuleExample(unittest.TestCase):
    """Every example in spoken-rules.json is said the way the table says —
    the table is what the team reads, so it must be what the machine does."""

    def test_every_example_in_the_table(self):
        for rule in sn.rules()["rules"]:
            for said, want in rule["examples"]:
                with self.subTest(rule=rule["id"], text=said):
                    self.assertEqual(sn.say(said), want)


class Numbers(unittest.TestCase):
    def test_currency(self):
        self.assertEqual(sn.say("$29"), "twenty-nine dollars")
        self.assertEqual(sn.say("$29.99"), "twenty-nine ninety-nine")
        self.assertEqual(sn.say("$1,200"), "twelve hundred dollars")
        self.assertEqual(sn.say("$1,299.99"), "one thousand two hundred ninety-nine dollars and ninety-nine cents")
        self.assertEqual(sn.say("$0.01"), "one cent")
        self.assertEqual(sn.say("£5"), "five pounds")

    def test_percent_range_multiplier(self):
        self.assertEqual(sn.say("87% saw it"), "eighty-seven percent saw it")
        self.assertEqual(sn.say("2–3 weeks"), "two to three weeks")
        self.assertEqual(sn.say("2x"), "two times")

    def test_times_and_durations(self):
        self.assertEqual(sn.say("7:30"), "seven thirty")
        self.assertEqual(sn.say("12:45pm"), "twelve forty-five P M")
        self.assertEqual(sn.say("60-day"), "sixty-day")
        self.assertEqual(sn.say("24/7"), "twenty-four seven")
        self.assertEqual(sn.say("30-day supply"), "thirty-day supply")

    def test_ordinals_years_decimals_fractions(self):
        self.assertEqual(sn.say("1st"), "first")
        self.assertEqual(sn.say("22nd"), "twenty-second")
        self.assertEqual(sn.say("40th"), "fortieth")
        self.assertEqual(sn.say("1998"), "nineteen ninety-eight")
        self.assertEqual(sn.say("2010"), "twenty ten")
        self.assertEqual(sn.say("0.5"), "zero point five")
        self.assertEqual(sn.say("1/4"), "one quarter")

    def test_phone_units_hash(self):
        self.assertEqual(sn.say("(209) 444-2316"), "two oh nine, four four four, two three one six")
        self.assertEqual(sn.say("100 g"), "one hundred grams")
        self.assertEqual(sn.say("SPF 50"), "S P F fifty")
        self.assertEqual(sn.say("#1"), "number one")

    def test_words_and_symbols(self):
        self.assertEqual(sn.say("WAR™ Face Wash"), "WAR Face Wash")
        self.assertEqual(sn.say("no figures here"), "no figures here")
        self.assertEqual(sn.words(0), "zero")
        self.assertEqual(sn.words(1000000), "one million")

    def test_the_figures_the_gate_listens_for(self):
        got = dict(sn.number_phrases("Only $29, every 28–40 days"))
        self.assertEqual(got["$29"], "twenty-nine dollars")
        self.assertEqual(got["28"], "twenty-eight")
        self.assertEqual(got["40"], "forty")
        self.assertNotIn("28–40", got)   # a range row still has digits: not a final word

    def test_figures_heard_as_words_or_digits(self):
        ok = sn.figures_heard("only $29.99", "only twenty nine ninety nine")
        self.assertTrue(ok[0]["heard_ok"])
        ok = sn.figures_heard("only $29.99", "only 29.99")
        self.assertTrue(ok[0]["heard_ok"])
        bad = sn.figures_heard("only $29", "only thirty nine dollars")
        self.assertFalse(bad[0]["heard_ok"])
        bad = sn.figures_heard("only $29", "only $129")
        self.assertFalse(bad[0]["heard_ok"])


# ------------------------------------------------------------------ lexicon

class Swap(unittest.TestCase):
    def test_longest_term_first(self):
        out, subs = lx.apply("Centella Asiatica seed", ROWS)
        self.assertEqual(out, "sen-TEL-uh uh-SEE-uh-tih-kuh seed")
        self.assertEqual([s["term"] for s in subs], ["Centella Asiatica"])

    def test_case_insensitive_and_recorded(self):
        out, subs = lx.apply("VELUNE and centella", ROWS)
        self.assertEqual(out, "veh-loon and sen-TEL-uh")
        self.assertEqual(subs[0]["found"], "VELUNE")

    def test_whole_words_only(self):
        out, _ = lx.apply("warm hardware award WAR", ROWS)
        self.assertEqual(out, "warm hardware award war")
        out, _ = lx.apply("Velune's scrub", ROWS)
        self.assertEqual(out, "veh-loon's scrub")

    def test_never_swapped_twice(self):
        rows = [{"term": "Velune", "say_as": "veh-loon", "kind": "brand", "confirmed": True},
                {"term": "nee", "say_as": "KNEE", "kind": "other", "confirmed": True}]
        out, subs = lx.apply("Velune", rows)
        self.assertEqual(out, "veh-loon")
        self.assertEqual(len(subs), 1)

    def test_trademark_goes_with_the_word(self):
        out, _ = lx.apply("WAR™ Face Wash", ROWS)
        self.assertEqual(out, "war Face Wash")

    def test_a_row_that_says_itself_is_not_recorded(self):
        out, subs = lx.apply("Glow Lock", ROWS)
        self.assertEqual((out, subs), ("Glow Lock", []))

    def test_swap_before_numbers(self):
        said, rec = lx.for_model("Vitamin B3 for $29", ROWS)
        self.assertEqual(said, "vitamin B three for twenty-nine dollars")
        self.assertEqual(rec["said_as"][0]["term"], "Vitamin B3")

    def test_a_broken_list_is_refused_by_name(self):
        probs = lx.validate([{"term": "X", "say_as": "", "kind": "thing", "confirmed": "yes"},
                             {"term": "x", "say_as": "x", "kind": "other", "confirmed": True}])
        self.assertTrue(any("no say_as" in p for p in probs))
        self.assertTrue(any("kind" in p for p in probs))
        self.assertTrue(any("confirmed" in p for p in probs))
        self.assertTrue(any("twice" in p for p in probs))

    def test_the_real_brand_lists_are_valid(self):
        root = HERE.parents[2] / "brands"
        for brand in ("brand-a", "brand-b"):
            p = root / brand / "brand-identity" / "voice" / "pronunciation.json"
            if p.is_file():
                with self.subTest(brand=brand):
                    self.assertEqual(lx.validate(json.loads(p.read_text())["rows"]), [])


class Heard(unittest.TestCase):
    def test_fuzzy_on_the_real_spelling(self):
        got = lx.heard_check("Velune uses centella", "Veluna uses Sentella", ROWS, 0.8)
        self.assertTrue(all(g["heard_ok"] for g in got), got)

    def test_split_word_still_heard(self):
        self.assertGreaterEqual(lx.best_match("Velune", "the vel une scrub"), 0.9)

    def test_a_missing_word_is_named(self):
        got = lx.heard_check("Velune uses centella", "Velune uses oranges", ROWS, 0.8)
        missed = [g["term"] for g in got if not g["heard_ok"]]
        self.assertEqual(missed, ["Centella"])

    def test_unconfirmed_words_listed(self):
        self.assertEqual(lx.unconfirmed_in("Velune and centella", ROWS), ["Centella"])


# ------------------------------------------------------------ the voice body

class VoiceBody(unittest.TestCase):
    def setUp(self):
        self.voice = load("voice")
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-spoken-"))
        (self.tmp / "b" / "brand-identity" / "voice").mkdir(parents=True)
        (self.tmp / "b" / "brand-identity" / "voice" / "pronunciation.json").write_text(json.dumps({"rows": ROWS}))
        self.voice.lexicon_mod = lambda: self._lx()

    def _lx(self):
        m = load("lexicon")
        m.BRANDS_ROOT = self.tmp
        return m

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_body_is_pinned_and_said_out(self):
        body, said = self.voice.body_for("Velune — only $29.", "eleven_multilingual_v2", ROWS)
        self.assertEqual(body["text"], "veh-loon, only twenty-nine dollars.")
        self.assertEqual(body["apply_text_normalization"], "off")
        self.assertEqual(body["seed"], self.voice.pins()["seed"])
        self.assertEqual(said["said_as"][0]["term"], "Velune")

    def test_a_remake_asks_with_the_next_seed(self):
        body, _ = self.voice.body_for("x", "m", [], seed_offset=2)
        self.assertEqual(body["seed"], self.voice.pins()["seed"] + 2)

    def test_the_read_records_the_swap_and_captions_keep_the_script(self):
        run = self.tmp / "run"
        home = self.tmp / "cast" / "kim"
        home.mkdir(parents=True)
        (home / "voice.json").write_text(json.dumps({"voice_id": "V1"}))
        (run / "vo").mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"brand": "b"}))
        (run / "plan.json").write_text(json.dumps({"shape": "scene", "cast": {"name": "kim"}, "scenes": [{"id": "S1"}]}))
        (run / "lines.json").write_text(json.dumps({"S1": "Velune is $29. Try centella."}))
        sent = []

        def fake(method, url, body, headers):
            sent.append(body)
            t = body["text"]
            al = {"characters": list(t), "character_start_times_seconds": [i * 0.05 for i in range(len(t))],
                  "character_end_times_seconds": [i * 0.05 + 0.05 for i in range(len(t))]}
            return json.dumps({"audio_base64": base64.b64encode(b"A").decode(), "alignment": al}).encode(), {"request-id": "r1"}
        self.voice.run_ffmpeg = lambda args: False
        self.voice.level_slice = lambda p, *a, **k: True
        self.voice.breath_of = lambda run: None
        with redirect_stdout(io.StringIO()):
            self.voice.run_for(run, cast_root=str(self.tmp / "cast"), transport=fake, key="k")
        self.assertEqual(sent[0]["text"], "veh-loon is twenty-nine dollars. Try sen-TEL-uh.")
        timing = json.loads((run / "vo" / "timing.json").read_text())
        sc = timing["scenes"]["S1"]
        self.assertEqual([s["term"] for s in sc["said_as"]], ["Velune", "Centella"])
        self.assertEqual([l["text"] for l in sc["lines"]], ["Velune is $29.", "Try centella."])
        self.assertEqual(sc["lines"][0]["said"], "veh-loon is twenty-nine dollars.")
        # the script itself is never touched
        self.assertEqual(json.loads((run / "lines.json").read_text())["S1"], "Velune is $29. Try centella.")


# ------------------------------------------------------------ the audio gate

def ear(*texts):
    said = list(texts)

    def t(method, url, headers, body):
        return 200, {}, json.dumps({"text": said.pop(0) if len(said) > 1 else said[0]}).encode()
    return t


class AudioGate(unittest.TestCase):
    def setUp(self):
        self.ac = load("audiocheck")
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-spoken-gate-"))
        (self.tmp / "b" / "brand-identity" / "voice").mkdir(parents=True)
        (self.tmp / "b" / "brand-identity" / "voice" / "pronunciation.json").write_text(json.dumps({"rows": ROWS}))
        real = self.ac._load

        def _load(name):
            m = real(name)
            if name == "lexicon":
                m.BRANDS_ROOT = self.tmp
            if name == "voice":
                m.remake_scene = lambda *a, **k: self.remakes.append(a[1])
            if name == "preflight":
                m.verdict = lambda *a, **k: None
            return m
        self.ac._load = _load
        self.remakes = []
        self.run = self.tmp / "run"
        (self.run / "vo").mkdir(parents=True)
        (self.run / "run.json").write_text(json.dumps({"brand": "b"}))
        (self.run / "lines.json").write_text(json.dumps({"S1": "Velune has centella for $29."}))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
                        "-af", "volume=2.0", str(self.run / "vo" / "S1.mp3")], check=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check(self, *heard):
        with redirect_stdout(io.StringIO()):
            return self.ac.check_run(self.run, fix=True, transport=ear(*heard), key="k")

    def test_all_heard_passes_with_a_warning_for_the_unconfirmed_word(self):
        out = self.check("Velune has centella for twenty-nine dollars.")
        self.assertTrue(out["pass"], out)
        self.assertEqual(self.remakes, [])
        self.assertIn("Centella", out["warnings"][0])

    def test_a_protected_word_missed_is_remade_once_then_stops_naming_it(self):
        out = self.check("Velune has oranges for twenty-nine dollars.")
        self.assertFalse(out["pass"])
        self.assertEqual(self.remakes, ["S1"])   # one voice-only remake, then stop
        self.assertTrue(any("protected word not heard: 'Centella'" in p for p in out["scenes"]["S1"]["problems"]))

    def test_a_miss_fixed_by_the_remake_passes(self):
        out = self.check("Velune has oranges for twenty-nine dollars.", "Velune has centella for $29.")
        self.assertTrue(out["pass"], out)
        self.assertEqual(self.remakes, ["S1"])

    def test_a_wrong_number_stops_naming_it(self):
        out = self.check("Velune has centella for thirty-nine dollars.")
        self.assertFalse(out["pass"])
        self.assertTrue(any("number not heard as said: '$29'" in p for p in out["scenes"]["S1"]["problems"]))


# ------------------------------------------------------------ the song

class Song(unittest.TestCase):
    def setUp(self):
        self.song = load("song")
        self.tmp = Path(tempfile.mkdtemp(prefix="vm-spoken-song-"))
        (self.tmp / "b" / "brand-identity" / "voice").mkdir(parents=True)
        (self.tmp / "b" / "brand-identity" / "voice" / "pronunciation.json").write_text(json.dumps({"rows": ROWS}))
        real = self.song._load

        def _load(name):
            m = real(name)
            if name == "lexicon":
                m.BRANDS_ROOT = self.tmp
            return m
        self.song._load = _load
        self.block = {"style_id": "s", "vocal": "female", "sections": [
            {"name": "verse", "seconds": 10, "lines": ["Velune with centella", "only $29 a tube"]}]}
        self.plan = {"brand": "b", "song": self.block,
                     "scenes": [{"id": "S1", "lyrics": ["Velune with centella", "only $29 a tube"]}]}
        self.styles = {"s": {"id": "s", "status": "approved", "vocal": "female", "positive_styles": ["soul"],
                             "negative_styles": [], "section_styles": {"verse": "soft"}}}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_lyrics_are_sent_said_out_and_the_brief_is_untouched(self):
        rows = self.song._load("lexicon").load("b")
        req = self.song.build_request(self.block, self.plan, styles=self.styles, rows=rows)
        self.assertEqual(req["body"]["composition_plan"]["chunks"][0]["text"],
                         "veh-loon with sen-TEL-uh\nonly twenty-nine dollars a tube")
        self.assertEqual(self.block["sections"][0]["lines"][1], "only $29 a tube")
        self.assertEqual(req["said"][0]["said_as"][0]["term"], "Velune")
        self.assertNotIn("said", req["body"])

    def test_the_song_gate_hears_protected_words_and_numbers(self):
        rows = self.song._load("lexicon").load("b")
        ok = self.song.gate(self.block, {"text": "Velune with centella only twenty nine dollars a tube"}, rows)
        self.assertTrue(ok["pass"], ok["problems"])
        self.assertEqual(ok["unconfirmed"], ["Centella"])
        bad = self.song.gate(self.block, {"text": "Velune with Maria only twenty nine dollars a tube"}, rows)
        self.assertFalse(bad["pass"])
        self.assertTrue(any("'Centella'" in p for p in bad["problems"]))


if __name__ == "__main__":
    unittest.main()
