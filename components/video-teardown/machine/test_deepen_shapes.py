"""The visuals pass survives whatever shape the model answers in (2026-09-25).

Observed on tts-midlife-nursing-025118: the model answered with a JSON array,
`dict.update()` raised "dictionary update sequence element #0 has length 1; 2
is required", and the whole visuals leg died — 0/0 shots re-read, every shot
left with its stage-1 one-liner. No network: the shapes go in directly.
"""
import importlib.util, json, shutil, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE))
_s = importlib.util.spec_from_file_location("deepen", HERE / "deepen.py")
D = importlib.util.module_from_spec(_s); _s.loader.exec_module(D)

STAMPS = ["0:00.0 - 0:01.0", "0:01.0 - 0:02.0"]

RECORD = """**CAST**

**Creator** — a woman.

| Timestamp | Roll | Section | Visuals | On-Screen Text | Transcript | Sound | Layers |
|---|---|---|---|---|---|---|---|
| 0:00.0 - 0:01.0 | A | hook | She applies it. | x | y | z | - |
| 0:01.0 - 0:02.0 | G | hook | She keeps going. | x | y | z | - |
"""

LONG_A = "Who: Creator in a black tank and green headband. " + ("word " * 40).strip()
LONG_B = "Who: Creator in a black tank, no headband. " + ("word " * 40).strip()


class ShapeTests(unittest.TestCase):
    def test_the_object_that_was_asked_for(self):
        self.assertEqual(D._shots({STAMPS[0]: LONG_A}, STAMPS), {STAMPS[0]: LONG_A})

    def test_a_bare_array_pairs_back_to_the_chunk_in_order(self):
        # the shape that crashed the pass
        self.assertEqual(D._shots([LONG_A, LONG_B], STAMPS), {STAMPS[0]: LONG_A, STAMPS[1]: LONG_B})

    def test_an_array_of_objects_keeps_its_own_timestamps(self):
        got = D._shots([{"timestamp": STAMPS[1], "visuals": LONG_B}], STAMPS)
        self.assertEqual(got, {STAMPS[1]: LONG_B})

    def test_an_array_of_objects_timestamped_in_its_own_words_pairs_by_order(self):
        got = D._shots([{"shot": "shot one", "description": LONG_A}], STAMPS)
        self.assertEqual(got, {STAMPS[0]: LONG_A})

    def test_a_single_key_wrapper_is_unwrapped(self):
        self.assertEqual(D._shots({"shots": [LONG_A]}, STAMPS), {STAMPS[0]: LONG_A})
        self.assertEqual(D._shots({"visuals": {STAMPS[0]: LONG_A}}, STAMPS), {STAMPS[0]: LONG_A})

    def test_a_single_shot_wrapped_in_a_key(self):
        self.assertEqual(D._shots({"visuals": LONG_A}, STAMPS[:1]), {STAMPS[0]: LONG_A})

    def test_a_single_shot_answered_with_a_bare_string(self):
        self.assertEqual(D._shots(LONG_A, STAMPS[:1]), {STAMPS[0]: LONG_A})

    def test_the_labeled_clauses_as_their_own_fields(self):
        got = D._shots({STAMPS[0]: {"Who": "Creator", "Doing": "applying"}}, STAMPS)
        self.assertEqual(got, {STAMPS[0]: "Who: Creator / Doing: applying"})

    def test_nothing_usable_is_empty_not_an_exception(self):
        self.assertEqual(D._shots(None, STAMPS), {})
        self.assertEqual(D._shots([7, {}], STAMPS), {})


class PassTests(unittest.TestCase):
    """The loop end to end, with `ask` replaced."""

    def setUp(self):
        self.real = D.ask

    def tearDown(self):
        D.ask = self.real

    def _run(self, answers):
        it = iter(answers)

        def fake(video, prompt, want_json=False):
            a = next(it)
            if isinstance(a, Exception):
                raise a
            return a
        D.ask = fake
        return D.visuals_pass("x.mp4", RECORD, "")

    def test_an_array_answer_now_lands_in_the_table(self):
        out, done, total, failed = self._run([[LONG_A, LONG_B]])
        self.assertEqual((done, total, failed), (2, 2, []))
        self.assertIn(LONG_A.strip(), out)
        self.assertIn(LONG_B.strip(), out)

    def test_a_loosely_spelled_timestamp_still_matches_its_row(self):
        out, done, total, failed = self._run([{"0:00": LONG_A, "0:01.0-0:02.0": LONG_B}])
        self.assertEqual((done, total), (2, 2))

    def test_a_shorter_answer_never_replaces_what_is_there(self):
        out, done, total, failed = self._run([{STAMPS[0]: "She applies."}])
        self.assertEqual(done, 0)
        self.assertIn("She applies it.", out)

    def test_one_bad_chunk_does_not_kill_the_rest(self):
        # four shots a call, so two chunks: the first raises, the second lands
        rec = RECORD + "".join(
            f"| 0:0{i}.0 - 0:0{i + 1}.0 | A | body | short. | x | y | z | - |\n" for i in range(2, 7))
        it = iter([RuntimeError("deepen pass failed — boom"), [LONG_A, LONG_B, LONG_A]])

        def fake(video, prompt, want_json=False):
            a = next(it)
            if isinstance(a, Exception):
                raise a
            return a
        D.ask = fake
        out, done, total, failed = D.visuals_pass("x.mp4", rec, "")
        self.assertEqual(total, 7)
        self.assertEqual(done, 3)          # the second chunk's three shots survived
        self.assertEqual(len(failed), 1)
        self.assertIn("0:00.0 - 0:01.0", failed[0])


class TranscriptCheckTests(unittest.TestCase):
    """The transcript check shared the assumption: it did `got.get("corrections")`
    on whatever came back, so a bare array raised AttributeError and every
    correction was lost."""

    def setUp(self):
        self.real = D.ask
        self.d = Path(tempfile.mkdtemp())
        (self.d / "transcript.json").write_text(json.dumps(
            [{"id": "T1", "start": 0.0, "speaker": "Creator", "text": "Vinyl, the last step."}]))

    def tearDown(self):
        D.ask = self.real
        shutil.rmtree(self.d, ignore_errors=True)

    def _with(self, answer):
        D.ask = lambda video, prompt, want_json=False: answer
        return D.transcript_check_pass("x.mp4", self.d)

    CORR = {"id": "T1", "heard": "Vinyl", "correct": "And finally",
            "evidence": "the caption reads And finally"}

    def test_the_object_that_was_asked_for(self):
        self.assertEqual(len(self._with({"corrections": [self.CORR]})), 1)

    def test_a_bare_array_of_corrections(self):
        fixed = self._with([self.CORR])
        self.assertEqual(len(fixed), 1)
        self.assertIn("And finally", json.loads((self.d / "transcript.json").read_text())[0]["text"])

    def test_a_key_of_the_models_own_choosing(self):
        self.assertEqual(len(self._with({"fixes": [self.CORR]})), 1)

    def test_junk_in_the_list_is_skipped_not_raised(self):
        self.assertEqual(self._with(["nonsense", 7, {"id": "T9"}]), [])

    def test_nothing_wrong_is_an_empty_list(self):
        self.assertEqual(self._with({"corrections": []}), [])


if __name__ == "__main__":
    unittest.main()
